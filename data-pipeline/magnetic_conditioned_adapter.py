"""Original magnetic physics through the public owned-Joseph source epoch.

Only physical DTOs cross this seam. The public core owns factors, CG and terminal
checks. No source/native/field admission or private optimizer is supplied here.
"""
import hashlib
import os
from pathlib import Path
from time import monotonic

import numpy as np

from magnetic_inverse import native_array
from magnetic_optimizer_adapter import MagneticObjective, certificate_source
from magnetic_nonlinear_adapter import MagneticNonlinearObjective


LIMIT = 805306368


def binding_for_sources(sources, inventory_sha256, *, nonlinear, feasible=False):
    import physical_conditioned_optimizer as core
    import physical_owned_spd as spd
    if type(feasible) is not bool or (feasible and nonlinear):
        raise ValueError('contact magnetic: explicit LINEAR-only source')
    if feasible:
        import physical_feasible_optimizer as core
    module = 'physical_feasible_optimizer' if feasible else 'physical_conditioned_optimizer'
    return core.ConditionedBinding(module+'.solve_bounded_'+('nonlinear' if nonlinear else 'linear'),
        core.SOURCE_SHA256, spd.SOURCE_SHA256, spd.KERNEL_SHA256, core.VENDOR_SOURCE_SHA256,
        sources['magnetic_inverse_precision'], inventory_sha256,
        core.NONLINEAR_EPOCH if nonlinear else core.LINEAR_EPOCH, core.POLICY)


class OptimizerAudit:
    """Exclusive bounded external, complete per-solve receipts; no acceptance."""
    def __init__(self, path, inventory_sha256):
        from magnetic_local_paths import external_path
        self.path = external_path(path)
        self.inventory = inventory_sha256
        self.used = self.solves = 0
        self.stream = self.path.open('xb')

    def append(self, candidate, fold, solved):
        from magnetic_survey_json import canonical, fail
        def native(value):
            if type(value) is np.ndarray:
                return value.tolist()
            if isinstance(value, np.generic):
                return value.item()
            if type(value) is dict:
                return {k: native(v) for k, v in value.items()}
            if type(value) in (tuple, list):
                return [native(v) for v in value]
            return value
        raw = canonical(dict(schema='magnetic-conditioned-solve-audit-1',
            source_inventory_sha256=self.inventory, candidate=candidate, fold=fold,
            solve=self.solves, actual_result=native(solved), field_accepted=False, online_admitted=False))+b'\n'
        if len(raw) > 16*1024**2 or self.used+len(raw) > 64*1024**2:
            fail('resource', '$/optimizer-audit', 'Complete immutable optimizer audit capacity exceeded')
        if self.stream.write(raw) != len(raw):
            fail('durability', '$/optimizer-audit', 'Complete optimizer audit write failed')
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.used += len(raw)
        self.solves += 1

    def close(self):
        self.stream.close()


def allocation(source_components, fit_components, parameters, covariance, original_bytes):
    """Public phase dictionary plus the unchanged source envelope, before G."""
    import gravity_l2_metric
    if type(original_bytes) is not int or not 0 < original_bytes <= LIMIT:
        raise ValueError('conditioned magnetic: original bounded source envelope')
    phases = gravity_l2_metric.allocation(source_components, fit_components, parameters, covariance)
    admitted = max(original_bytes, phases['maximum'])
    if admitted > LIMIT:
        raise ValueError('conditioned magnetic: original 768MiB cap')
    return dict(original_bytes=original_bytes, metric_phases=phases, admitted_bytes=admitted)


class MagneticConditionedObjective:
    """Exact original physical methods with new public identity/closed operands."""
    def __init__(self, physical, source_components, *, feasible=False):
        if type(physical) not in (MagneticObjective, MagneticNonlinearObjective):
            raise TypeError('conditioned magnetic: actual original physical objective')
        if type(feasible) is not bool or (feasible and type(physical) is MagneticNonlinearObjective):
            raise ValueError('contact magnetic: explicit LINEAR-only source')
        self.feasible = feasible
        self.physical = physical
        for key in ('operator', 'regularizer', 'lower', 'upper', 'beta'):
            setattr(self, key, getattr(physical, key))
        if (type(source_components) is not int or not 3*self.operator.rows <= source_components <= 2048
                or source_components % 3):
            raise ValueError('conditioned magnetic: actual full source kernel components')
        self.source_components = source_components

    def identity(self):
        import physical_conditioned_optimizer as core
        value = self.physical.identity()
        if self.feasible:
            import physical_feasible_optimizer as core
        value['runtime_epoch'] = core.NONLINEAR_EPOCH if value['mode'] == 'nonlinear_gauss_newton' else core.LINEAR_EPOCH
        return value

    def metric_operands(self, q):
        import physical_owned_spd as spd
        native_array(q, (self.operator.parameters,), 'metric model')
        # Same-q physical Jacobian, including nonlinear total-vector direction.
        jacobian = self.operator.evaluate(q)['jacobian_nT_per_q']
        whitened = np.ascontiguousarray(self.physical.whiten(jacobian))
        regularizer = (self.beta*self.regularizer.vendor.deriv2(q)).tocsr()
        regularizer.sum_duplicates()
        regularizer.sort_indices()
        noise = self.physical.base.noise if type(self.physical) is MagneticNonlinearObjective else self.physical.noise
        return spd.MetricOperands(spd.binding_for(self.identity(), q), self.source_components,
            self.operator.rows*self.operator.components, self.operator.parameters,
            noise['kind'] == 'full_covariance', regularizer, whitened, 1.)

    def evaluate(self, q, return_g=False, return_H=False):
        return self.physical.evaluate(q, return_g, return_H)

    def components(self, q):
        return self.physical.components(q)

    def whiten(self, value, transpose=False):
        return self.physical.whiten(value, transpose=transpose)

    def binding_diagonal(self, q):
        return self.physical.binding_diagonal(q)

    def certify(self, *args):
        physical = self.physical.base if type(self.physical) is MagneticNonlinearObjective else self.physical
        return physical.certify(*args)

    def exact_hessian(self, q):
        if type(self.physical) is not MagneticNonlinearObjective:
            raise ValueError('conditioned magnetic: exact norm Hessian only')
        return self.physical.exact_hessian(q)

    def release_state(self):
        self.physical.release_state()


def solve_conditioned(objective, lower, upper, start, *, budget, binding):
    import physical_conditioned_optimizer as core
    import physical_owned_spd as spd
    if type(objective) is not MagneticConditionedObjective:
        raise TypeError('conditioned magnetic: exact physical wrapper')
    if (type(binding) is not core.ConditionedBinding
            or binding.certificate_source_sha256 != hashlib.sha256(Path(certificate_source()).read_bytes()).hexdigest()
            or type(budget) is not core.ConditionedBudget or budget.remaining_steps > 200
            or budget.resource_limit_bytes != LIMIT):
        raise ValueError('conditioned magnetic: original certificate/step/resource binding')
    nonlinear = objective.identity()['mode'] == 'nonlinear_gauss_newton'
    if objective.feasible:
        import physical_feasible_optimizer as core
    budget = core.ConditionedBudget(min(budget.deadline, monotonic()+120.), budget.remaining_steps,
        budget.resource_limit_bytes, budget.admitted_bytes, budget.allocation_plan_sha256)
    function = core.solve_bounded_nonlinear if nonlinear else core.solve_bounded_linear
    result = function(objective, lower, upper, start, budget=budget, binding=binding,
                      terminal=spd.TerminalPolicy(1e-7))
    if nonlinear:
        proofs = []
        models = result['trace']['models_q']
        for before, after in zip(models, models[1:]):
            phi, gradient = objective.evaluate(before, True, False)
            trial = objective.evaluate(after)
            proof = objective.certify(before, after, gradient, phi, trial, len(proofs), 1, budget.deadline)
            proofs.append(proof)
            if proof['decision'] != 'certified_accept':
                result.update(status='failed', reason='magnetic_norm_'+proof['cause'])
                result['failed_trial'] = dict(iteration=len(proofs)-1, reason=result['reason'])
                break
        result['trace']['magnetic_norm_proofs'] = proofs
    objective.release_state()
    return result
