"""Exact total-field physical composition of the public nonlinear M02 seam.

The public native Armijo solver is not an interval solver. Independently audit
every actual accepted chord with the existing norm certificate before allowing
M04 success. No solver/private helper/CG is copied or replaced here.
"""

import numpy as np
from scipy.sparse.linalg import LinearOperator

from magnetic_inverse import native_array, owned
from magnetic_optimizer_adapter import MagneticObjective


class MagneticNonlinearObjective:
    """Single SI property block, exact Hessian distinct from refreshed PSD GN."""

    def __init__(self, objective, start_q):
        if type(objective) is not MagneticObjective or objective.operator.quantity != 'exact_total_anomaly_nT':
            raise TypeError('nonlinear: actual exact-total-field magnetic objective required')
        native_array(start_q, (objective.operator.parameters,), 'start')
        self.base = objective
        for key in ('operator', 'regularizer', 'lower', 'upper', 'beta'):
            setattr(self, key, getattr(objective, key))
        # The reviewed native seam binds INITIAL diagonal for the whole fit.
        # This is not a stale Jacobian: evaluate() refreshes the GN search H.
        self.diagonal = owned(objective.binding_diagonal(start_q))

    def identity(self):
        import physical_nonlinear_optimizer as core
        value = self.base.identity()
        value.update(runtime_epoch=core.RUNTIME_EPOCH, physical_unit='si',
                     physical_scale=(.01,), beta_engine=1., observation_components=1)
        return value

    def components(self, q):
        value = self.base.components(q)
        terms = (0., value['phi_d'], 0., float(self.beta*value['phi_m']), 0.)
        phi = (((terms[0]+terms[1])+terms[2])+terms[3])+terms[4]
        return dict(phi_d=terms[0]+terms[1], phi_m=(terms[2]+terms[3])+terms[4],
                    phi_engine=phi, engine_terms=terms)

    def evaluate(self, q, return_g=False, return_H=False):
        return self.base.evaluate(q, return_g, return_H)

    def binding_diagonal(self, q):
        native_array(q, self.diagonal.shape, 'q')
        return owned(self.diagonal)

    def free_metric(self, q, free_indices):
        n = len(self.diagonal)
        if (type(free_indices) is not np.ndarray or free_indices.dtype != np.int64 or free_indices.ndim != 1
                or len(free_indices) > n or np.any(free_indices < 0) or np.any(free_indices >= n)
                or np.any(np.diff(free_indices) <= 0)):
            raise ValueError('nonlinear: increasing native free indices required')
        indices = free_indices.copy()
        inverse = 1./self.binding_diagonal(q)

        def action(v):
            result = np.zeros(n)
            result[indices] = inverse[indices]*v[indices]
            return result
        return LinearOperator((n, n), matvec=action, dtype=np.float64)

    def exact_hessian(self, q):
        state = self.operator.evaluate(q)
        ab, b0, _, _, _ = self.operator.operand_snapshot()
        ab = ab.reshape(self.operator.rows, 3, self.operator.parameters)
        total = b0+state['secondary_enu_nT']
        norm = state['total_norm_nT']
        direction = total/norm[:, None]
        residual = state['prediction_nT'].ravel()-self.base.observed.ravel()
        weighted = self.base.whiten(self.base.whiten(residual), transpose=True)
        gn = self.base.evaluate(q, False, True)[1]

        def action(v):
            av = np.einsum('nca,a->nc', ab, v)
            transverse = av-direction*np.sum(direction*av, axis=1)[:, None]
            curvature = 2*np.einsum('nca,nc,n->a', ab, transverse, weighted/norm)
            return gn@v+curvature
        return LinearOperator((len(q), len(q)), matvec=action, dtype=np.float64)

    def whiten(self, value, transpose=False):
        return self.base.whiten(value, transpose)

    def release_state(self):
        self.base.release_state()


def solve_nonlinear(objective, lower_q, upper_q, start_q, *, budget, binding):
    import physical_nonlinear_optimizer as core
    if type(objective) is not MagneticNonlinearObjective:
        raise TypeError('nonlinear: actual trusted magnetic composition required')
    result = core.solve_bounded_nonlinear(objective, lower_q, upper_q, start_q, budget=budget, binding=binding)
    proofs = []
    models = result['trace']['models_q']
    # Audits use actual accepted models/gradient/F, never proposed search steps.
    # Retain the complete native trace even when our stronger proof rejects.
    for before, after in zip(models, models[1:]):
        phi, gradient = objective.base.evaluate(before, True, False)
        trial = objective.base.evaluate(after)
        proof = objective.base.certify(before, after, gradient, phi, trial, len(proofs), 1, budget.deadline)
        proofs.append(proof)
        if proof['decision'] != 'certified_accept':
            result.update(status='failed', reason='magnetic_norm_'+proof['cause'])
            result['failed_trial'] = dict(iteration=len(proofs)-1, reason=result['reason'])
            break
    result['trace']['magnetic_norm_proofs'] = proofs
    objective.release_state()
    return result
