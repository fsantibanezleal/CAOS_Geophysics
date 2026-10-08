"""Exact native M04 objective through the public original-noise magnetic bridge.

No objective subclass/private DTO, numerical solver, supplied face or fallback.
The immutable plan binds a quota; native simultaneous-phase checks remain gates.
"""
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np

from magnetic_optimizer_adapter import MagneticObjective
from magnetic_survey_json import digest


LIMIT = 805306368
PUBLIC_SOURCES = ('physical_original_optimizer', 'physical_original_terminal',
    'magnetic_original_optimizer', 'physical_original_quadratic', 'physical_owned_spd',
    'physical_reduced_optimizer', 'physical_original_residual_terminal', 'physical_original_rows')


def source_binding():
    import importlib
    result = {}
    for name in PUBLIC_SOURCES:
        module = importlib.import_module(name)
        actual = hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        if actual != module.SOURCE_SHA256:
            raise ValueError('original magnetic: public loaded source drift')
        result[name] = actual
    return result


def allocation(source_components, fit_components, parameters, covariance,
               original_bytes, observation_components):
    """Pre-G original source bound; actual face/audits checked by PUBLIC owner.

    Four M04 terms have <=a rows, diagonal weights and <=2a derivative nnz.
    The native source validator independently checks the actual stored operands.
    Reserving the original quota is not claiming measured peak/RSS containment.
    """
    import gravity_l2_metric as kernel
    import physical_original_quadratic as source
    import physical_original_optimizer as core
    if (type(original_bytes) is not int or not 0 < original_bytes <= LIMIT
        or type(observation_components) is not int or observation_components not in (1, 3)
        or type(source_components) is not int or source_components % 3
        or type(fit_components) is not int or fit_components % observation_components
        or type(parameters) is not int or type(covariance) is not bool):
        raise ValueError('original magnetic: literal source/count/noise metadata')
    native = kernel.allocation(source_components, fit_components, parameters, covariance)
    raw_rows = 3*(fit_components//observation_components)
    if raw_rows > source_components or (covariance and fit_components > 512):
        raise ValueError('original magnetic: whole source or original covariance cap')
    if source.RESERVE_BYTES != 8*1024**2 or source.ENDPOINT_PAIR_BYTES != 2048:
        raise ValueError('original magnetic: reviewed source arithmetic constants')
    # Both sensitivity/prediction occurrences are charged, even when aliased.
    payload = (16*raw_rows*parameters + 16*fit_components + 24*parameters + 48
        + 4*(44*parameters+8))
    if covariance:
        payload += 16*fit_components*fit_components
    arithmetic = dict(operand_and_sparse_copy_bytes=2*payload,
        endpoint_bytes=2048*(10*parameters+6*source_components),
        native_row_scratch_bytes=128*(2*parameters+source_components), metadata_bytes=32768)
    minimum = max(original_bytes, native['maximum'])+max(source.RESERVE_BYTES, sum(arithmetic.values()))
    minimum += source.RESERVE_BYTES+32768
    if payload > source.RESERVE_BYTES or minimum > LIMIT:
        raise ValueError('original magnetic: original source arithmetic quota exceeded')
    return dict(schema='magnetic-original-allocation-1', source_components=source_components,
        fit_components=fit_components, parameters=parameters, covariance=covariance,
        observation_components=observation_components, original_bytes=original_bytes,
        native_phases=native, source_payload_upper_bytes=payload,
        source_arithmetic_upper=arithmetic, minimum_phase_bytes=minimum,
        actual_terminal_phase_gate='public-owned-source-face-audit-before-allocation',
        admitted_bytes=LIMIT, source_binding=source_binding(), epoch=core.LINEAR_EPOCH,
        policy=core.POLICY)


def binding_for_sources(sources, inventory_sha256):
    import physical_original_optimizer as core
    import physical_owned_spd as spd
    loaded = source_binding()
    if any(sources.get(name) != sha for name, sha in loaded.items()):
        raise ValueError('original magnetic: complete public original source inventory')
    return core.ConditionedBinding('physical_original_optimizer.solve_bounded_linear',
        core.SOURCE_SHA256, spd.SOURCE_SHA256, spd.KERNEL_SHA256, core.VENDOR_SOURCE_SHA256,
        loaded['physical_original_quadratic'], inventory_sha256, core.LINEAR_EPOCH, core.POLICY)


def solve_original(objective, lower, upper, start, *, budget, binding, plan):
    import physical_original_optimizer as core
    import physical_owned_spd as spd
    import magnetic_original_optimizer as bridge
    if type(objective) is not MagneticObjective or objective.operator.quantity not in (
        'secondary_enu_nT', 'linear_tmi_nT'):
        raise ValueError('original magnetic: exact native LINEAR objective only')
    try:
        expected = allocation(plan['source_components'], objective.observed.size,
            objective.operator.parameters, objective.noise['kind'] == 'full_covariance',
            plan['original_bytes'], objective.operator.components)
    except (KeyError, TypeError) as error:
        raise ValueError('original magnetic: closed allocation plan') from error
    identity = objective.identity()
    if plan != expected or identity['allocation_plan_sha256'] != digest(expected):
        raise ValueError('original magnetic: exact original plan binding')
    if type(binding) is not core.ConditionedBinding or binding != binding_for_sources(
        expected['source_binding'], identity['source_inventory_sha256']):
        raise ValueError('original magnetic: exact public source binding')
    if (type(budget) is not core.ConditionedBudget or type(budget.remaining_steps) is not int
        or not 0 <= budget.remaining_steps <= 200 or budget.resource_limit_bytes != LIMIT
        or budget.admitted_bytes != expected['admitted_bytes']
        or budget.allocation_plan_sha256 != digest(expected)
        or not np.array_equal(lower, objective.lower) or not np.array_equal(upper, objective.upper)):
        raise ValueError('original magnetic: unchanged original budget/box binding')
    bounded = core.ConditionedBudget(min(budget.deadline, monotonic()+120.), budget.remaining_steps,
        budget.resource_limit_bytes, budget.admitted_bytes, budget.allocation_plan_sha256)
    try:
        return bridge.solve_magnetic_original(objective, start,
            source_components=expected['source_components'], budget=bounded, binding=binding,
            terminal=spd.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    finally:
        objective.release_state()
