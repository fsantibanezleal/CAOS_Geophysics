"""Candidate optimizer composition check; this is not M04 acceptance evidence.

The test-owned fixed linear objective uses vector fields from the real magnetic
forward path. M04 still requires its accepted M02 binding, physical adapter,
independent Choclo validation, and field/user-data gates.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from time import monotonic

import numpy as np
import pytest
from scipy.sparse.linalg import LinearOperator

import magnetic_forward
import physical_nonlinear_optimizer as optimizer


def _request(chi: float) -> dict:
    return {
        "schema": "magnetic-prism-forward-request-1",
        "engine": magnetic_forward.ENGINE,
        "frame": dict(magnetic_forward.FRAME),
        "mesh": {
            "origin_m": np.array([0.0, 0.0, -3.0]),
            "hx_m": np.array([1.0]), "hy_m": np.array([1.2]), "hz_m": np.array([1.0]),
            "active": np.array([True]),
        },
        "receivers_m": np.array([[0.2, 0.3, 0.8], [1.3, 0.5, 0.7], [0.4, 1.5, 0.9]]),
        "susceptibility_si": np.array([chi], dtype=np.float64),
        "inducing_field": {"amplitude_nt": 50000.0, "inclination_deg": 58.0, "declination_deg": 17.0},
    }


class MagneticVectorObjective:
    """One-parameter ENU residual using the actual SimPEG/Geoana prism path."""
    def __init__(self):
        self.unit_response = magnetic_forward.forward_magnetic(_request(0.01))["field_components_nt"].reshape(-1)
        # q is a normalized susceptibility multiplier: physical chi = 0.01*q.
        self.a = self.unit_response.copy()
        self.sigma = np.full(self.a.shape, 0.2, dtype=np.float64)
        self.aw = self.a / self.sigma
        self.truth = 0.45
        self.dw = self.aw * self.truth
        self.reference = 0.15
        self.beta = 0.002
        self.start = np.array([0.9], dtype=np.float64)
        self.diagonal = np.array([self.aw @ self.aw + self.beta], dtype=np.float64)
        self.evaluations = 0
        self.released = False
        source_hash = hashlib.sha256(Path(magnetic_forward.__file__).read_bytes()).hexdigest()
        objective_hash = hashlib.sha256(self.aw.tobytes() + self.dw.tobytes()).hexdigest()
        self._identity = {
            "mode": "nonlinear_gauss_newton", "runtime_epoch": optimizer.RUNTIME_EPOCH,
            "objective_sha256": objective_hash, "source_inventory_sha256": source_hash,
            "q_unit": "normalized_susceptibility_0.01", "physical_unit": "si",
            "physical_scale": (0.01,), "parameter_count": 1, "observation_rows": 3,
            "observation_components": 3, "beta_engine": 1.0, "stage_index": 0,
            "allocation_plan_sha256": "a" * 64,
        }

    def identity(self):
        return dict(self._identity)

    def components(self, q):
        residual = self.aw * q[0] - self.dw
        delta = q[0] - self.reference
        data = float(0.5 * (residual @ residual))
        regularization = float(0.5 * self.beta * delta * delta)
        return {"phi_d": data, "phi_m": regularization, "phi_engine": data + regularization,
                "engine_terms": (data, 0.0, regularization, 0.0, 0.0)}

    def _hessian(self):
        value = float(self.diagonal[0])
        return LinearOperator((1, 1), dtype=np.float64, matvec=lambda v: np.array([value * v[0]]))

    def evaluate(self, q, return_g=False, return_H=False):
        self.evaluations += 1
        values = [self.components(q)["phi_engine"]]
        if return_g:
            values.append(np.array([float(self.aw @ (self.aw * q[0] - self.dw) + self.beta * (q[0] - self.reference))]))
        if return_H:
            values.append(self._hessian())
        return tuple(values) if len(values) > 1 else values[0]

    def exact_hessian(self, q):
        return self._hessian()

    def binding_diagonal(self, q):
        return self.diagonal.copy()

    def free_metric(self, q, free_indices):
        inverse = np.zeros(1, dtype=np.float64)
        inverse[free_indices] = 1.0 / self.diagonal[free_indices]
        return LinearOperator((1, 1), dtype=np.float64, matvec=lambda v: inverse * v)

    def release_state(self):
        self.released = True


def _binding(obj):
    return optimizer.NonlinearBinding(
        "physical_nonlinear_optimizer.solve_bounded_nonlinear", optimizer.SOURCE_SHA256,
        optimizer.VENDOR_SOURCE_SHA256, obj.identity()["source_inventory_sha256"],
        optimizer.RUNTIME_EPOCH, optimizer.POLICY,
    )


def _run(obj):
    budget = optimizer.NonlinearBudget(monotonic() + 60.0, 80, 2 * 1024**3, 1024**2,
                                      obj.identity()["allocation_plan_sha256"])
    return optimizer.solve_bounded_nonlinear(obj, np.zeros(1), np.ones(1), obj.start.copy(),
                                             budget=budget, binding=_binding(obj))


def test_quantity_specific_physics_and_jacobian():
    obj = MagneticVectorObjective()
    # The three ENU component observations are independent rows of the actual
    # vendor Jacobian. A central difference checks the scaled susceptibility.
    step = 1e-5
    plus = magnetic_forward.forward_magnetic(_request(0.01 * (obj.truth + step)))["field_components_nt"].reshape(-1)
    minus = magnetic_forward.forward_magnetic(_request(0.01 * (obj.truth - step)))["field_components_nt"].reshape(-1)
    np.testing.assert_allclose((plus - minus) / (2 * step), obj.unit_response, rtol=2e-6, atol=2e-9)

    result = _run(obj)
    assert result["status"] == "converged", result["reason"]
    assert result["reason"] == "kkt"
    assert result["kkt_normalized"] <= optimizer.KKT_TOLERANCE
    assert obj.released and result["iterations"] > 0
    # Independent closed-form minimizer for the frozen whitened ENU objective.
    expected = float((obj.aw @ obj.dw + obj.beta * obj.reference) / obj.diagonal[0])
    np.testing.assert_allclose(result["q"], [expected], rtol=2e-7, atol=1e-9)
    predicted = magnetic_forward.forward_magnetic(_request(0.01 * result["q"][0]))["field_components_nt"].reshape(-1)
    np.testing.assert_allclose(predicted, obj.a * result["q"][0], rtol=1e-12, atol=2e-10)
    assert obj.identity()["observation_components"] == 3


def test_vector_component_cap_rejects_before_engine_or_objective():
    obj = MagneticVectorObjective()
    obj._identity["observation_components"] = 4
    before = obj.evaluations
    with pytest.raises(ValueError, match="count caps"):
        # The exact preflight is exercised by the solver, with a valid binding
        # source but an inadmissible native component count.
        solver_binding = optimizer.NonlinearBinding(
            "physical_nonlinear_optimizer.solve_bounded_nonlinear", optimizer.SOURCE_SHA256,
            optimizer.VENDOR_SOURCE_SHA256, obj.identity()["source_inventory_sha256"],
            optimizer.RUNTIME_EPOCH, optimizer.POLICY,
        )
        budget = optimizer.NonlinearBudget(monotonic() + 60.0, 80, 2 * 1024**3, 1024**2,
                                           obj.identity()["allocation_plan_sha256"])
        optimizer.solve_bounded_nonlinear(obj, np.array([0.0]), np.array([1.0]), obj.start.copy(),
                                          budget=budget, binding=solver_binding)
    assert obj.evaluations == before and not obj.released
