"""Original magnetic physics through the PUBLIC reduced-native linear export.

Only source-bound operands and budgets cross this seam. No private CG/active
mask/factor, fallback, nonlinear admission or scientific tolerance replacement.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
from time import monotonic

import magnetic_conditioned_adapter as conditioned
from magnetic_optimizer_adapter import MagneticObjective, certificate_source
from magnetic_survey_json import digest


LIMIT = conditioned.LIMIT


def allocation(source_components, fit_components, parameters, covariance, original_bytes):
    """Conservative complete public phase reserve, BEFORE full kernel creation."""
    import physical_reduced_optimizer as core
    if (type(core.WORKSPACE_BYTES) is not int or core.WORKSPACE_BYTES != 8*1024**2
        or type(core.PHASE_METADATA_BYTES) is not int or core.PHASE_METADATA_BYTES != 8192
        or type(core.PHASE_LIMIT) is not int or core.PHASE_LIMIT != 512
        or core.SOURCE_SHA256 != hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest()):
        raise ValueError('reduced magnetic: reviewed public source/constants required')
    original = conditioned.allocation(source_components, fit_components, parameters, covariance, original_bytes)
    reserve = dict(workspace_bytes=core.WORKSPACE_BYTES, phase_metadata_bytes=core.PHASE_METADATA_BYTES,
        phase_limit=core.PHASE_LIMIT, direction_limit=200, phase_direction_bytes=8*parameters,
        direction_model_gradient_bytes=16*parameters, direction_frozen_delta_bytes=8*parameters,
        prospective_delta_bytes=8*parameters)
    extra = (reserve['workspace_bytes']+reserve['phase_limit']*(reserve['phase_direction_bytes']+
        reserve['phase_metadata_bytes'])+reserve['direction_limit']*(reserve['direction_model_gradient_bytes']+
        reserve['direction_frozen_delta_bytes'])+reserve['prospective_delta_bytes'])
    admitted = original['admitted_bytes']+extra
    if admitted > LIMIT:
        raise ValueError('reduced magnetic: original 768MiB complete allocation cap')
    return dict(schema='magnetic-reduced-allocation-1', source_components=source_components,
        fit_components=fit_components, parameters=parameters, covariance=covariance,
        original=original, reserve=reserve, admitted_bytes=admitted,
        source_binding=dict(optimizer=core.SOURCE_SHA256, policy=core.POLICY, epoch=core.LINEAR_EPOCH))


def binding_for_sources(sources, inventory_sha256):
    import physical_reduced_optimizer as core
    import physical_owned_spd as spd
    return core.ConditionedBinding('physical_reduced_optimizer.solve_bounded_linear',
        core.SOURCE_SHA256, spd.SOURCE_SHA256, spd.KERNEL_SHA256, core.VENDOR_SOURCE_SHA256,
        sources['magnetic_inverse_precision'], inventory_sha256, core.LINEAR_EPOCH, core.POLICY)


class MagneticReducedObjective(conditioned.MagneticConditionedObjective):
    """Same original objective; privately owned complete public allocation plan."""
    def __init__(self, physical, plan):
        if type(physical) is not MagneticObjective or physical.identity()['mode'] != 'fixed_linear_quadratic':
            raise ValueError('reduced magnetic: actual LINEAR physical objective only')
        if type(plan) is not dict:
            raise ValueError('reduced magnetic: closed allocation plan')
        try:
            expected = allocation(plan['source_components'], physical.operator.rows*physical.operator.components,
                physical.operator.parameters, physical.noise['kind'] == 'full_covariance',
                plan['original']['original_bytes'])
        except (KeyError, TypeError) as error:
            raise ValueError('reduced magnetic: closed allocation plan') from error
        if plan != expected or physical.identity()['allocation_plan_sha256'] != digest(expected):
            raise ValueError('reduced magnetic: exact source/count/allocation digest required')
        self.__plan = deepcopy(expected)
        super().__init__(physical, plan['source_components'])

    def allocation_plan(self):
        return deepcopy(self.__plan)

    def identity(self):
        import physical_reduced_optimizer as core
        return dict(self.physical.identity(), runtime_epoch=core.LINEAR_EPOCH)


def solve_reduced(objective, lower, upper, start, *, budget, binding):
    import physical_reduced_optimizer as core
    import physical_owned_spd as spd
    if type(objective) is not MagneticReducedObjective:
        raise TypeError('reduced magnetic: exact physical wrapper required')
    plan = objective.allocation_plan()
    identity = objective.identity()
    sources = {'magnetic_inverse_precision': hashlib.sha256(Path(certificate_source()).read_bytes()).hexdigest()}
    if type(binding) is not core.ConditionedBinding or binding != binding_for_sources(sources, identity['source_inventory_sha256']):
        raise ValueError('reduced magnetic: exact public/certificate/identity binding')
    if (type(budget) is not core.ConditionedBudget or type(budget.remaining_steps) is not int
        or not 0 <= budget.remaining_steps <= 200 or budget.resource_limit_bytes != LIMIT
        or budget.admitted_bytes != plan['admitted_bytes'] or budget.allocation_plan_sha256 != digest(plan)
        or identity['allocation_plan_sha256'] != digest(plan)):
        raise ValueError('reduced magnetic: complete original source-bound budget required')
    bounded = core.ConditionedBudget(min(budget.deadline, monotonic()+120.), budget.remaining_steps,
        budget.resource_limit_bytes, budget.admitted_bytes, budget.allocation_plan_sha256)
    try:
        return core.solve_bounded_linear(objective, lower, upper, start, budget=bounded,
            binding=binding, terminal=spd.TerminalPolicy(1e-7))
    finally:
        objective.release_state()
