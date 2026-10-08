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
    """Consume the PUBLIC original source plan; do not reproduce its formula."""
    import magnetic_original_optimizer as bridge
    import physical_original_optimizer as core
    import physical_original_quadratic as source
    loaded = source_binding()
    if (LIMIT != 805306368
            or core.LINEAR_EPOCH != 'physical-gncg-original-noise-reduced-joseph-candidate-10'
            or core.POLICY != 'closed-original-noise-reduced-joseph-free-face-residual-owned-phases-3'
            or not callable(getattr(bridge, 'allocation_plan', None))):
        raise ValueError('original magnetic: reviewed public allocation source epoch required')
    actual = bridge.allocation_plan(source_components, fit_components, parameters,
        covariance, original_bytes, observation_components)
    fields = set(('schema source_components fit_components parameters covariance '
        'observation_components original_bytes native_phases owned_source_phases '
        'source_payload_upper_bytes source_arithmetic_upper minimum_phase_bytes '
        'actual_terminal_phase_gate admitted_bytes source_binding epoch policy').split())
    identity = dict(source_components=source_components, fit_components=fit_components,
        parameters=parameters, covariance=covariance, original_bytes=original_bytes,
        observation_components=observation_components)
    if (type(actual) is not dict or set(actual) != fields
            or actual['schema'] != 'magnetic-original-allocation-2'
            or any(type(actual[k]) is not type(v) or actual[k] != v for k, v in identity.items())
            or type(actual['admitted_bytes']) is not int or actual['admitted_bytes'] != LIMIT
            or LIMIT != 805306368
            or actual['source_binding'] != loaded or source_binding() != loaded
            or actual['epoch'] != core.LINEAR_EPOCH or actual['policy'] != core.POLICY
            or actual['actual_terminal_phase_gate'] != 'public-owned-source-face-audit-before-allocation'):
        raise ValueError('original magnetic: closed public allocation identity/source contract')
    phase = actual['owned_source_phases']
    native = actual['native_phases']
    arithmetic = actual['source_arithmetic_upper']
    if (type(native) is not dict or set(native) != {
            'native', 'interval', 'setup', 'action', 'line_search', 'maximum', 'ceiling'}
            or any(type(v) is not int or v <= 0 for v in native.values())
            or type(phase) is not dict or set(phase) != {'epoch', 'original_native_phases',
            'factory_bytes', 'original_certificate_bytes', 'original_arithmetic_bytes', 'maximum'}
            or phase['epoch'] != source.ALLOCATION_EPOCH
            or phase['original_native_phases'] != actual['native_phases']
            or any(type(phase[k]) is not int or phase[k] <= 0 for k in (
                'factory_bytes', 'original_certificate_bytes', 'original_arithmetic_bytes', 'maximum'))
            or type(arithmetic) is not dict or set(arithmetic) != {
                'operand_and_sparse_copy_bytes', 'endpoint_bytes', 'native_row_scratch_bytes', 'metadata_bytes'}
            or any(type(v) is not int or v <= 0 for v in arithmetic.values())
            or type(actual['source_payload_upper_bytes']) is not int
            or not 0 < actual['source_payload_upper_bytes'] <= source.RESERVE_BYTES
            or type(actual['minimum_phase_bytes']) is not int
            or not phase['maximum'] <= actual['minimum_phase_bytes'] <= LIMIT):
        raise ValueError('original magnetic: closed public allocation phase contract')
    # Return the owner's complete dictionary unchanged. The actual public DTO
    # and terminal independently recompute source/backing/free-face storage.
    return actual


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
