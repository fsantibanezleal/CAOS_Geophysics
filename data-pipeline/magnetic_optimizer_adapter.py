"""Physical magnetic likelihood and actual SimPEG fixed regularizers.

Trusted in-process composition only. Source hashes identify loaded code; they
do not constitute independent source admission or online execution authority.
The separately reviewed M02 optimizer is a dependency, never copied here.
"""

import hashlib
from pathlib import Path
import re

import numpy as np
from scipy.linalg import solve_triangular
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import LinearOperator

from magnetic_inverse import MagneticQuantity, native_array, owned, finite_float
from magnetic_inverse_precision import MagneticCertificate


EPSILONS = (.1, .05, .025, .0125, .00625, .003125, .0015625, .001)
_HASH = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)


def certificate_source():
    import magnetic_inverse_precision
    return magnetic_inverse_precision.__file__


def _hash_array(value):
    return hashlib.sha256(value.astype(value.dtype.newbyteorder('<'), copy=False).tobytes()).hexdigest()


class MagneticRegularizer:
    """One actual vendor regularizer with weights frozen at an explicit model."""

    def __init__(self, mesh, reference_q, lengths_m, penalty, epsilon_q, weight_model):
        if type(mesh) is not dict or set(mesh) != {'origin_m', 'hx_m', 'hy_m', 'hz_m', 'active'}:
            raise TypeError('mesh: exact closed physical mesh required')
        native_array(mesh['origin_m'], (3,), 'origin')
        widths = [mesh[k] for k in ('hx_m', 'hy_m', 'hz_m')]
        for w in widths:
            if type(w) is not np.ndarray or w.dtype != np.float64 or w.ndim != 1 or not 1 <= len(w) <= 64:
                raise TypeError('mesh widths: exact bounded float64 arrays')
        count = int(np.prod([len(w) for w in widths]))
        mask = mesh['active']
        if count > 4096 or type(mask) is not np.ndarray or mask.dtype != bool or mask.shape != (count,):
            raise ValueError('mesh active: bounded native full-cell bool mask')
        a = int(np.count_nonzero(mask))
        if not 1 <= a <= 2048:
            raise ValueError('mesh: active cell cap')
        native_array(reference_q, (a,), 'reference')
        native_array(weight_model, (a,), 'weight model')
        native_array(lengths_m, (3,), 'lengths')
        finite_float(epsilon_q, 'epsilon')
        if type(penalty) is not str or penalty not in ('l2', 'sparse_smallness'):
            raise ValueError('penalty: closed physical penalty')
        if epsilon_q not in (EPSILONS if penalty == 'sparse_smallness' else (0.,)):
            raise ValueError('epsilon: frozen positive schedule or L2 zero required')
        self.reference = owned(reference_q)
        self.lengths = owned(lengths_m)
        frozen_model = owned(weight_model)
        if (np.any(self.reference < 0.) or np.any(self.reference > 10.) or
                np.any(frozen_model < 0.) or np.any(frozen_model > 10.) or
                np.any(self.lengths <= 0.) or np.any(self.lengths > 1e5)):
            raise ValueError('regularizer: physical reference/model/length range')
        origin, widths = owned(mesh['origin_m']), [owned(w) for w in widths]
        if (np.any(abs(origin) > 1e7) or any(np.any((w < .001) | (w > 1e5)) or np.sum(w) > 1e5 for w in widths)):
            raise ValueError('mesh: physical coordinate/width/span range')
        edges = [o+np.r_[0., np.cumsum(w)] for o, w in zip(origin, widths)]
        if any(np.any(abs(e) > 1e7) or np.any(np.diff(e) <= 0.) for e in edges):
            raise ValueError('mesh: unrepresentable edges')
        from discretize import TensorMesh
        from simpeg import maps, regularization
        import magnetic_forward
        magnetic_forward._runtime()
        tensor = TensorMesh(widths, origin=origin)
        ijk = np.unravel_index(np.arange(count), tuple(map(len, widths)), order='F')
        declared = np.column_stack([e[i+s] for e, i in zip(edges, ijk) for s in (0, 1)])
        _, _, volumes = magnetic_forward._tensor_state(tensor, edges, widths, declared)
        self.fractions = owned(volumes[mask]/volumes[mask].sum())
        self.penalty, self.epsilon = penalty, epsilon_q
        kwargs = dict(active_cells=mask.copy(), mapping=maps.IdentityMap(nP=a),
            reference_model=self.reference.copy(), reference_model_in_smooth=True,
            alpha_s=1., alpha_x=float(self.lengths[0]**2), alpha_y=float(self.lengths[1]**2),
            alpha_z=float(self.lengths[2]**2), weights={'total_volume': np.full(a, 1./volumes[mask].sum())})
        if penalty == 'l2':
            self.vendor = regularization.WeightedLeastSquares(tensor, alpha_xx=0., alpha_yy=0., alpha_zz=0., **kwargs)
        else:
            self.vendor = regularization.Sparse(tensor, norms=[1., 2., 2., 2.],
                gradient_type='components', irls_scaled=False, irls_threshold=epsilon_q, **kwargs)
            for child, ell in zip(self.vendor.objfcts[1:], self.lengths):
                child.irls_threshold = epsilon_q/float(ell)
            self.vendor.update_weights(frozen_model)
        terms = []
        for alpha, child in zip(self.vendor.multipliers, self.vendor.objfcts):
            if alpha == 0.:
                continue
            derivative = csr_matrix(child.f_m_deriv(self.reference), dtype=np.float64)
            derivative.sum_duplicates()
            derivative.sort_indices()
            if derivative.shape[0] == 0:
                continue
            weights = child.W.diagonal()
            if not np.isfinite(weights).all() or np.any(weights <= 0.):
                raise ValueError('regularizer: positive actual vendor weights')
            terms.append(dict(alpha=float(alpha), weights=owned(weights), derivative=derivative.copy()))
        self._terms = tuple(terms)
        payload = repr((penalty, epsilon_q)).encode()+self.reference.tobytes()+self.lengths.tobytes()
        for term in self._terms:
            d = term['derivative']
            payload += np.array([term['alpha']], dtype='<f8').tobytes()+term['weights'].tobytes()
            payload += d.data.tobytes()+d.indices.tobytes()+d.indptr.tobytes()
        self.sha256 = hashlib.sha256(payload).hexdigest()

    def terms(self):
        return tuple(dict(alpha=t['alpha'], weights=owned(t['weights']), derivative=t['derivative'].copy()) for t in self._terms)

    def true_value_gradient(self, q):
        """Independent true smoothed p1, never a relabelled surrogate value."""
        native_array(q, self.reference.shape, 'q')
        delta = q-self.reference
        if self.penalty == 'l2':
            return float(self.vendor(q)), owned(self.vendor.deriv(q))
        e = self.epsilon
        root = np.sqrt(delta*delta+e*e)
        value = float(2*np.sum(self.fractions*delta*delta/(root+e)))
        gradient = 2*self.fractions*delta/root
        for t in self._terms[1:]:
            r = t['weights']*(t['derivative']@delta)
            value += float(t['alpha']*(r@r))
            gradient += 2*t['alpha']*(t['derivative'].T@(t['weights']*r))
        return value, owned(gradient)


class MagneticObjective:
    """Full principal whitening and GN action, in q=chi/.01 coordinates."""

    def __init__(self, operator, regularizer, observed, noise, lower_q, upper_q,
                 beta, source_inventory_sha256, allocation_plan_sha256, stage_index):
        if type(operator) is not MagneticQuantity or type(regularizer) is not MagneticRegularizer:
            raise TypeError('objective: exact magnetic operator/regularizer required')
        if (any(type(s) is not str or _HASH.fullmatch(s) is None for s in (source_inventory_sha256, allocation_plan_sha256))
                or type(stage_index) is not int or not 0 <= stage_index <= 20):
            raise ValueError('objective: source/allocation digests and bounded stage required')
        # Certificate validates ALL likelihood metadata/capacities before copies.
        self._certificate = MagneticCertificate(operator, observed, noise, regularizer.reference,
                                                lower_q, upper_q, beta, regularizer.terms())
        self.operator, self.regularizer = operator, regularizer
        self.observed = owned(observed)
        self.noise = dict(kind=noise['kind'], values=owned(noise['values']))
        self.lower, self.upper = owned(lower_q), owned(upper_q)
        self.beta = beta
        self.inventory, self.allocation, self.stage = source_inventory_sha256, allocation_plan_sha256, stage_index
        self.factor = owned(np.linalg.cholesky(self.noise['values'])) if noise['kind'] == 'full_covariance' else None
        payload = (operator.operand_sha256+regularizer.sha256+source_inventory_sha256+allocation_plan_sha256).encode()
        payload += self.observed.tobytes()+self.noise['values'].tobytes()+self.lower.tobytes()+self.upper.tobytes()
        payload += repr((beta, stage_index, noise['kind'])).encode()
        self.sha256 = hashlib.sha256(payload).hexdigest()
        self._cache = None

    def identity(self):
        import physical_optimizer
        return dict(mode='nonlinear_gauss_newton' if self.operator.quantity == 'exact_total_anomaly_nT' else 'fixed_linear_quadratic',
            runtime_epoch=physical_optimizer.RUNTIME_EPOCH, objective_sha256=self.sha256,
            source_inventory_sha256=self.inventory, q_unit='chi_over_0.01', physical_unit='SI', physical_scale=.01,
            parameter_count=self.operator.parameters, observation_rows=self.operator.rows,
            observation_components=self.operator.components, beta_engine=self.beta, stage_index=self.stage,
            allocation_plan_sha256=self.allocation)

    def whiten(self, value, transpose=False):
        if self.factor is not None:
            return solve_triangular(self.factor.T if transpose else self.factor, value, lower=not transpose)
        sd = self.noise['values'].ravel()
        return value/sd if value.ndim == 1 else value/sd[:, None]

    def _state(self, q):
        native_array(q, (self.operator.parameters,), 'q')
        if not np.isfinite(q).all() or np.any(q < self.lower) or np.any(q > self.upper):
            raise ValueError('q: objective bounds')
        if self._cache is not None and np.array_equal(q, self._cache[0]):
            return self._cache[1:]
        values = self.operator.evaluate(q)
        residual = values['prediction_nT'].ravel()-self.observed.ravel()
        wr = self.whiten(residual)
        wj = self.whiten(values['jacobian_nT_per_q'])
        pd, pm = float(wr@wr), float(self.regularizer.vendor(q))
        phi = float(pd+self.beta*pm)
        gradient = 2*wj.T@wr+self.beta*self.regularizer.vendor.deriv(q)
        self._cache = (owned(q), pd, pm, phi, owned(gradient), owned(wj))
        return self._cache[1:]

    def components(self, q):
        pd, pm, phi, _, _ = self._state(q)
        return dict(phi_d=pd, phi_m=pm, phi_engine=phi)

    def evaluate(self, q, return_g=False, return_H=False):
        if type(return_g) is not bool or type(return_H) is not bool:
            raise TypeError('evaluate: exact bool flags')
        _, _, phi, gradient, wj = self._state(q)
        values = [phi]
        if return_g:
            values.append(owned(gradient))
        if return_H:
            frozen = owned(q)
            values.append(LinearOperator((len(q), len(q)), dtype=np.float64,
                matvec=lambda v: 2*wj.T@(wj@v)+self.beta*self.regularizer.vendor.deriv2(frozen, v)))
        return tuple(values) if return_g or return_H else phi

    def binding_diagonal(self, q):
        wj = self._state(q)[-1]
        diagonal = 2*np.sum(wj*wj, axis=0)+self.beta*self.regularizer.vendor.deriv2(q).diagonal()
        if not np.isfinite(diagonal).all() or np.any(diagonal <= 0.):
            raise ValueError('objective: positive full GN diagonal, no floor')
        return owned(diagonal)

    def free_metric(self, q, free_indices):
        a = self.operator.parameters
        if (type(free_indices) is not np.ndarray or free_indices.dtype != np.int64 or free_indices.ndim != 1
                or len(free_indices) > a or np.any(free_indices < 0) or np.any(free_indices >= a)
                or np.any(np.diff(free_indices) <= 0)):
            raise ValueError('metric: exact increasing native free indices')
        indices = free_indices.copy()
        diagonal = self.binding_diagonal(q)
        inverse = 1./diagonal
        def action(v):
            out = np.zeros(a)
            # The public core binds this literal native arithmetic order.
            out[indices] = inverse[indices]*v[indices]
            return out
        return LinearOperator((a, a), matvec=action, dtype=np.float64)

    def certify(self, *args):
        return self._certificate.certify(*args)

    def release_state(self):
        self._cache = None


def solve_linear(objective, lower_q, upper_q, start_q, *, budget, binding):
    import physical_optimizer as core
    if type(objective) is not MagneticObjective:
        raise TypeError('solver: actual trusted magnetic objective required')
    if (type(binding) is not core.OptimizerBinding or binding.optimizer_source_sha256 != core.SOURCE_SHA256
            or binding.certificate_source_sha256 != hashlib.sha256(Path(certificate_source()).read_bytes()).hexdigest()):
        raise ValueError('solver: reviewed loaded optimizer/certificate source binding required')
    if objective.identity()['mode'] != 'fixed_linear_quadratic':
        raise ValueError('solver: nonlinear source registration dependency unavailable')
    return core.solve_bounded_physical(objective, lower_q, upper_q, start_q, budget=budget, binding=binding)
