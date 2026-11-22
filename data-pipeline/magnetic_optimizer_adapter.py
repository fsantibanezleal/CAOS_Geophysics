"""Bind magnetic L2 likelihood and SimPEG regularization to the M02 core.

Only affine secondary-ENU and linear-TMI objectives are admitted by the
original-noise solver. The exact total-field anomaly has a nonlinear Jacobian
and remains refused until a separately accepted nonlinear M02 binding exists.
Sparse IRLS uses a frozen actual-SimPEG quadratic for each M02 inner solve;
the caller owns epsilon scheduling and the true fixed-epsilon outer checks.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import LinearOperator

import magnetic_likelihood
import magnetic_original_optimizer
import magnetic_regularization
import physical_original_optimizer
import physical_original_quadratic
import physical_owned_spd


_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
LINEAR_QUANTITIES = ("secondary_enu_nT", "linear_tmi_nT")


def _digest(value, name):
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ValueError(f"{name}: expected lowercase SHA-256")


class MagneticRegularizer:
    """Closed frozen L2 or sparse-surrogate adapter over actual SimPEG terms."""

    def __init__(self, mesh, reference_q, lengths_m, penalty="l2", epsilon_q=0., weight_model=None):
        if type(mesh) is not dict or set(mesh) != {"origin_m", "hx_m", "hy_m", "hz_m", "active"}:
            raise TypeError("mesh: expected exact origin/widths/active mapping")
        if (type(penalty) is not str or penalty not in ("l2", "sparse")
                or type(epsilon_q) not in (int, float)):
            raise ValueError("regularizer: expected the frozen L2 or sparse-IRLS policy")
        if penalty == "l2" and epsilon_q != 0.:
            raise ValueError("regularizer: fixed L2 requires epsilon_q=0")
        if penalty == "sparse" and (type(epsilon_q) is not float
                or epsilon_q not in magnetic_regularization.SPARSE_EPSILON_Q):
            raise ValueError("regularizer: sparse epsilon must be in the frozen positive schedule")
        origin = mesh["origin_m"]
        widths = tuple(mesh[key] for key in ("hx_m", "hy_m", "hz_m"))
        active = mesh["active"]
        if type(origin) is not np.ndarray or origin.dtype != np.float64 or origin.shape != (3,):
            raise TypeError("mesh origin: expected native float64 ENU vector")
        if any(type(width) is not np.ndarray or width.dtype != np.float64 or width.ndim != 1 for width in widths):
            raise TypeError("mesh widths: expected native float64 vectors")
        if any(not 1 <= len(width) <= 64 for width in widths):
            raise ValueError("mesh widths: each axis must contain 1..64 cells")
        full_cells = int(np.prod([len(width) for width in widths]))
        if full_cells > 4096:
            raise ValueError("mesh: full-cell cap is 4096")
        if type(active) is not np.ndarray or active.dtype != np.bool_ or active.ndim != 1:
            raise TypeError("mesh active: expected native bool vector")
        if full_cells != len(active):
            raise ValueError("mesh: active-cell count disagrees with tensor geometry")
        active_count = int(np.count_nonzero(active))
        if not 1 <= active_count <= 2048:
            raise ValueError("mesh: active-cell count must be in 1..2048")
        if (type(reference_q) is not np.ndarray or reference_q.dtype != np.float64
                or reference_q.shape != (active_count,)):
            raise TypeError("reference: expected native float64 active-cell vector")
        if type(lengths_m) is not np.ndarray or lengths_m.dtype != np.float64 or lengths_m.shape != (3,):
            raise TypeError("lengths: expected native float64 ENU vector")
        if penalty == "sparse":
            if type(weight_model) is not np.ndarray or weight_model.dtype != np.float64:
                raise TypeError("weight model: sparse IRLS requires a native float64 refresh model")
            if weight_model.shape != (active_count,):
                raise ValueError("weight model: shape mismatch")
        elif weight_model is not None:
            if type(weight_model) is not np.ndarray or weight_model.dtype != np.float64:
                raise TypeError("weight model: expected native float64 vector")
            if weight_model.shape != (active_count,):
                raise ValueError("weight model: shape mismatch")
        if (not np.isfinite(origin).all() or np.any(np.abs(origin) > 1e7)
                or any(not np.isfinite(width).all() or np.any((width < .001) | (width > 1e5))
                       or float(np.sum(width)) > 1e5 for width in widths)
                or not np.isfinite(reference_q).all() or np.any((reference_q < 0.) | (reference_q > 10.))
                or not np.isfinite(lengths_m).all() or np.any((lengths_m <= 0.) | (lengths_m > 1e5))
                or (weight_model is not None and
                    (not np.isfinite(weight_model).all()
                     or np.any((weight_model < 0.) | (weight_model > 10.))))):
            raise ValueError("mesh/reference/lengths: finite bounded physical values required")
        from discretize import TensorMesh
        tensor = TensorMesh([width.copy() for width in widths], x0=origin.copy())
        self.source = magnetic_regularization.MagneticRegularizer(
            tensor, active, reference_q, lengths_m
        )
        self.engine_epoch = magnetic_regularization.ENGINE_EPOCH
        self.reference = self.source.reference_q
        self.lengths_m = self.source.lengths_m
        self.parameter_count = self.source.parameter_count
        self.penalty = penalty
        self.epsilon_q = float(epsilon_q)
        self.weight_model = None
        self.smallness_irls_weights = None
        self._terms = self.source.terms()
        self.vendor = self.source.simpeg
        self.hessian = self.source.hessian
        self.hessian_diagonal = self.source.hessian_diagonal
        if penalty == "sparse":
            self.weight_model = np.array(weight_model, dtype=np.float64, copy=True, order="C")
            self.weight_model.flags.writeable = False
            refreshed = self.source.evaluate_sparse(self.weight_model, self.epsilon_q)
            self.vendor = self.source.sparse
            irls_weights = np.array(refreshed["smallness_irls_weights"], dtype=np.float64, copy=True)
            irls_weights.flags.writeable = False
            self.smallness_irls_weights = irls_weights
            first = dict(self._terms[0])
            first["weights"] = np.asarray(first["weights"] * np.sqrt(irls_weights), dtype=np.float64)
            first["weights"].flags.writeable = False
            self._terms = (first, *self._terms[1:])
            volume_fraction = self.source.volumes / self.source.total_volume
            smooth = self.source.hessian * .5 - sp.diags(volume_fraction, format="csr")
            hessian = (2. * (smooth + sp.diags(volume_fraction * irls_weights, format="csr"))).tocsr()
            hessian.sum_duplicates()
            hessian.sort_indices()
            if (hessian.shape != (active_count, active_count)
                    or not np.isfinite(hessian.data).all()
                    or np.any(hessian.diagonal() <= 0.)):
                raise FloatingPointError("sparse surrogate: invalid frozen positive-definite Hessian")
            hessian.data.flags.writeable = False
            hessian.indices.flags.writeable = False
            hessian.indptr.flags.writeable = False
            self.hessian = hessian
            diagonal = np.asarray(hessian.diagonal(), dtype=np.float64)
            diagonal.flags.writeable = False
            self.hessian_diagonal = diagonal
        self.sha256 = self._identity_digest()

    def _identity_digest(self):
        payload = [self.source.active_cells.tobytes(), self.reference.astype("<f8", copy=False).tobytes(),
                   self.lengths_m.astype("<f8", copy=False).tobytes()]
        for term in self.terms():
            derivative = term["derivative"]
            payload.extend((term["weights"].astype("<f8", copy=False).tobytes(),
                            derivative.data.astype("<f8", copy=False).tobytes(),
                            derivative.indices.tobytes(), derivative.indptr.tobytes()))
        if self.penalty == "sparse":
            payload.extend((b"sparse", repr(self.epsilon_q).encode("ascii"),
                            self.weight_model.astype("<f8", copy=False).tobytes()))
        return hashlib.sha256(b"".join(payload)).hexdigest()

    def terms(self):
        return tuple({"alpha": term["alpha"],
                      "weights": term["weights"].copy(),
                      "derivative": term["derivative"].copy()}
                     for term in self._terms)

    def evaluate(self, q):
        if self.penalty == "l2":
            return self.source.evaluate(q)
        if (type(q) is not np.ndarray or q.dtype != np.float64
                or q.shape != (self.parameter_count,)):
            raise TypeError("q: expected native float64 active-cell vector")
        if not np.isfinite(q).all() or np.any((q < 0.) | (q > 10.)):
            raise ValueError("q: finite normalized susceptibility values in [0,10] required")
        delta = q - self.reference
        gradient = np.asarray(self.hessian @ delta, dtype=np.float64)
        phi = float(.5 * (delta @ gradient))
        if not np.isfinite(phi) or not np.isfinite(gradient).all():
            raise FloatingPointError("sparse surrogate: nonfinite objective or gradient")
        return {"phi": phi, "gradient_q": gradient,
                "hessian_action": lambda direction: self.hessian @ direction,
                "independent_phi": phi, "independent_gradient_q": gradient.copy(),
                "unit": "dimensionless", "parameter_unit": "q=chi_si/0.01",
                "engine_epoch": self.engine_epoch}


class MagneticObjective:
    """Frozen original-row Gaussian objective plus one fixed quadratic penalty."""

    def __init__(self, operator, regularizer, observed_nT, noise, lower_q, upper_q,
                 beta, source_inventory_sha256, allocation_plan_sha256, stage_index=0):
        from magnetic_inverse import MagneticQuantity
        if type(operator) is not MagneticQuantity or type(regularizer) is not MagneticRegularizer:
            raise TypeError("objective: expected owned magnetic quantity and frozen regularizer")
        if operator.quantity not in LINEAR_QUANTITIES:
            raise ValueError("objective: this source-bound M02 adapter accepts affine magnetic quantities only")
        _digest(source_inventory_sha256, "source inventory")
        _digest(allocation_plan_sha256, "allocation plan")
        if type(stage_index) is not int or not 0 <= stage_index <= 20:
            raise ValueError("stage: expected integer in 0..20")
        count = operator.rows * operator.components
        if (type(observed_nT) is not np.ndarray or observed_nT.dtype != np.float64
                or observed_nT.shape not in ((count,), (operator.rows, operator.components))):
            raise TypeError("observations: expected native float64 original-order rows")
        if not np.isfinite(observed_nT).all():
            raise ValueError("observations: finite nT values required")
        for name, value in (("lower", lower_q), ("upper", upper_q)):
            if type(value) is not np.ndarray or value.dtype != np.float64 or value.shape != (operator.parameters,):
                raise TypeError(f"{name}: expected native float64 parameter vector")
        if (not np.isfinite(lower_q).all() or not np.isfinite(upper_q).all()
                or np.any(lower_q < 0.) or np.any(upper_q > 10.) or np.any(lower_q >= upper_q)):
            raise ValueError("bounds: finite ordered normalized-susceptibility bounds in [0, 10]")
        if regularizer.parameter_count != operator.parameters:
            raise ValueError("regularizer: active-cell count disagrees with forward kernel")
        if type(beta) is not float or not np.isfinite(beta) or beta <= 0.:
            raise ValueError("beta: finite positive dimensionless value required")
        if type(noise) is not dict or set(noise) != {"kind", "values"}:
            raise TypeError("noise: exact kind/values mapping required")
        values = noise["values"]
        if type(values) is not np.ndarray or values.dtype != np.float64:
            raise TypeError("noise values: expected native float64 array")
        indices = np.arange(count, dtype=np.int64)
        self.whitener = magnetic_likelihood.GaussianWhitener(noise["kind"], values, indices)
        if self.whitener.dimension != count:
            raise ValueError("noise: whitening row count mismatch")
        self.operator, self.regularizer = operator, regularizer
        self.observed = np.array(observed_nT, dtype=np.float64, copy=True, order="C").reshape(-1)
        self.observed.flags.writeable = False
        self.noise = {"kind": noise["kind"],
                      "values": np.array(values, dtype=np.float64, copy=True, order="C")}
        self.noise["values"].flags.writeable = False
        self.factor = (np.linalg.cholesky(self.noise["values"])
                       if noise["kind"] == "full_covariance" else None)
        if self.factor is not None:
            self.factor.flags.writeable = False
        self.lower, self.upper = lower_q.copy(), upper_q.copy()
        self.lower.flags.writeable = False
        self.upper.flags.writeable = False
        # The admitted quantities are affine, so SimPEG's source-bound
        # component kernel yields one constant Jacobian for the whole solve.
        # Derive it once through the canonical quantity implementation and
        # reuse its exact whitened form at every accepted/trial model.
        linear_state = self.operator.evaluate(self.lower)
        self.linear_jacobian = np.array(linear_state["jacobian_nT_per_q"],
                                        dtype=np.float64, copy=True, order="C")
        if self.linear_jacobian.shape != (count, operator.parameters):
            raise ValueError("objective: canonical affine Jacobian shape mismatch")
        self.linear_jacobian.flags.writeable = False
        self.weighted_linear_jacobian = self.whitener.whiten(self.linear_jacobian)
        self.weighted_linear_jacobian.flags.writeable = False
        self.beta, self.inventory = beta, source_inventory_sha256
        self.allocation, self.stage = allocation_plan_sha256, stage_index
        self.sha256 = self._identity_digest()
        self._cache = None

    def _identity_digest(self):
        payload = (self.operator.operand_sha256, self.regularizer.sha256,
                   self.inventory, self.allocation,
                   self.observed.astype("<f8", copy=False).tobytes(),
                   self.noise["values"].astype("<f8", copy=False).tobytes(),
                   self.lower.astype("<f8", copy=False).tobytes(),
                   self.upper.astype("<f8", copy=False).tobytes(),
                   repr((self.beta, self.stage, self.noise["kind"])))
        digest = hashlib.sha256()
        for item in payload:
            block = item if type(item) is bytes else item.encode("ascii")
            digest.update(len(block).to_bytes(8, "big"))
            digest.update(block)
        return digest.hexdigest()

    def identity(self):
        return {
            "mode": "fixed_linear_quadratic",
            "runtime_epoch": physical_original_optimizer.LINEAR_EPOCH,
            "objective_sha256": self.sha256,
            "source_inventory_sha256": self.inventory,
            "q_unit": "q=chi_si/0.01",
            "physical_unit": "SI",
            "physical_scale": .01,
            "parameter_count": self.operator.parameters,
            "observation_rows": self.operator.rows,
            "observation_components": self.operator.components,
            "beta_engine": self.beta,
            "stage_index": self.stage,
            "allocation_plan_sha256": self.allocation,
        }

    def _state(self, q):
        if type(q) is not np.ndarray or q.dtype != np.float64 or q.shape != (self.operator.parameters,):
            raise TypeError("q: expected native float64 normalized-susceptibility vector")
        if not np.isfinite(q).all() or np.any(q < self.lower) or np.any(q > self.upper):
            raise ValueError("q: model outside the frozen objective bounds")
        if self._cache is not None and np.array_equal(q, self._cache[0]):
            return self._cache[1:]
        residual = self.linear_jacobian @ q - self.observed
        weighted_residual = self.whitener.whiten(residual)
        weighted_jacobian = self.weighted_linear_jacobian
        phi_d = float(weighted_residual @ weighted_residual)
        regularization = self.regularizer.evaluate(q)
        phi_m = float(regularization["phi"])
        phi = float(phi_d + self.beta * phi_m)
        gradient = (2. * weighted_jacobian.T @ weighted_residual
                    + self.beta * regularization["gradient_q"])
        if not np.isfinite([phi_d, phi_m, phi]).all() or not np.isfinite(gradient).all():
            raise FloatingPointError("objective: nonfinite Gaussian or SimPEG result")
        self._cache = (q.copy(), phi_d, phi_m, phi, gradient.copy(), weighted_jacobian)
        return self._cache[1:]

    def components(self, q):
        phi_d, phi_m, phi, _, _ = self._state(q)
        return {"phi_d": phi_d, "phi_m": phi_m, "phi_engine": phi}

    def evaluate(self, q, return_g=False, return_H=False):
        if type(return_g) is not bool or type(return_H) is not bool:
            raise TypeError("evaluate: exact bool derivative flags required")
        _, _, phi, gradient, weighted_jacobian = self._state(q)
        result = [phi]
        if return_g:
            result.append(gradient.copy())
        if return_H:
            regularizer_hessian = self.regularizer.hessian
            result.append(LinearOperator(
                (len(q), len(q)), dtype=np.float64,
                matvec=lambda direction: 2. * weighted_jacobian.T @ (weighted_jacobian @ direction)
                + self.beta * (regularizer_hessian @ direction),
            ))
        return tuple(result) if return_g or return_H else phi

    def binding_diagonal(self, q):
        weighted_jacobian = self._state(q)[-1]
        regularizer_diagonal = self.regularizer.hessian_diagonal
        diagonal = 2. * np.sum(weighted_jacobian * weighted_jacobian, axis=0) + self.beta * regularizer_diagonal
        if not np.isfinite(diagonal).all() or np.any(diagonal <= 0.):
            raise ValueError("objective: actual positive Gauss-Newton diagonal required")
        return diagonal

    def free_metric(self, q, free_indices):
        count = self.operator.parameters
        if (type(free_indices) is not np.ndarray or free_indices.dtype != np.int64
                or free_indices.ndim != 1 or len(free_indices) > count
                or np.any(free_indices < 0) or np.any(free_indices >= count)
                or np.any(np.diff(free_indices) <= 0)):
            raise ValueError("metric: expected strictly increasing native int64 free indices")
        indices = free_indices.copy()
        inverse = 1. / self.binding_diagonal(q)

        def apply(direction):
            result = np.zeros(count, dtype=np.float64)
            result[indices] = inverse[indices] * direction[indices]
            return result

        return LinearOperator((count, count), matvec=apply, dtype=np.float64)

    def release_state(self):
        self._cache = None


def binding_for(objective):
    if type(objective) is not MagneticObjective:
        raise TypeError("binding: exact trusted magnetic objective required")
    if objective.operator.quantity not in LINEAR_QUANTITIES:
        raise ValueError("binding: nonlinear total-field quantity is not registered")
    optimizer = physical_original_optimizer
    owned = physical_owned_spd
    return optimizer.ConditionedBinding(
        "physical_original_optimizer.solve_bounded_linear",
        optimizer.SOURCE_SHA256,
        owned.SOURCE_SHA256,
        owned.KERNEL_SHA256,
        optimizer.VENDOR_SOURCE_SHA256,
        physical_original_quadratic.SOURCE_SHA256,
        objective.inventory,
        optimizer.LINEAR_EPOCH,
        optimizer.POLICY,
    )


def solve_linear(objective, start_q, *, source_components, budget, terminal):
    """Run the registered M02 source-bound original-noise linear solver."""
    if type(objective) is not MagneticObjective:
        raise TypeError("solver: exact owned MagneticObjective required")
    if objective.operator.quantity not in LINEAR_QUANTITIES:
        raise ValueError("solver: nonlinear magnetic inversion binding is unavailable")
    return magnetic_original_optimizer.solve_magnetic_original(
        objective, start_q, source_components=source_components, budget=budget,
        binding=binding_for(objective), terminal=terminal,
    )
