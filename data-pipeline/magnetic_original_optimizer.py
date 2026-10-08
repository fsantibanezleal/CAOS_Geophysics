"""Actual magnetic physical DTO bridge to the public original-noise solver.

This additive bridge requires the actual native MagneticObjective, never a
private optimizer/certificate replacement. Acquisition, likelihood sealing,
source authority and the original allocation plan remain the workflow owner's.
"""
import hashlib
from pathlib import Path

import numpy as np
import scipy.sparse as sp

import physical_original_optimizer as optimizer
import physical_original_quadratic as original
import physical_owned_spd as owned


SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
RESIDUAL_TERMINAL_SHA256 = 'a9bf32a6c4e932d7d4efa1f38540778e2993f74982adb9f29985d921ecb5ddf7'


def allocation_plan(source_components, fit_components, parameters, covariance,
        original_bytes, observation_components):
    """PUBLIC pre-G upper plan for literal original M04 physical construction.

    Four native first-order terms have <=a rows, diagonal W and <=2a D entries.
    Actual original operands/free face/audits are independently checked by the
    public owner before any certificate/factory. No caller byte deduction,
    supplied phase flag, native callback or RSS-based permission is accepted.
    """
    import importlib
    limit = 805306368
    if (type(original_bytes) is not int or not 0 < original_bytes <= limit
            or type(observation_components) is not int or observation_components not in (1, 3)
            or type(source_components) is not int or source_components % 3
            or type(fit_components) is not int or fit_components % observation_components
            or type(parameters) is not int or type(covariance) is not bool):
        raise ValueError('original magnetic allocation: literal source/count/noise metadata')
    native = owned.kernel.allocation(source_components, fit_components, parameters, covariance)
    raw_rows = 3*(fit_components//observation_components)
    if raw_rows > source_components or covariance and fit_components > 512:
        raise ValueError('original magnetic allocation: whole source or original covariance cap')
    if original.RESERVE_BYTES != 8*1024**2 or original.ENDPOINT_PAIR_BYTES != 2048:
        raise ValueError('original magnetic allocation: literal reviewed arithmetic constants')
    # Both occurrences are charged even when aliased; no identity deduction.
    payload = (16*raw_rows*parameters+16*fit_components+24*parameters+48
        +4*(44*parameters+8)+(16*fit_components*fit_components if covariance else 0))
    arithmetic = dict(operand_and_sparse_copy_bytes=2*payload,
        endpoint_bytes=2048*(10*parameters+6*source_components),
        native_row_scratch_bytes=128*(2*parameters+source_components), metadata_bytes=32768)
    phases = original._owned_source_allocation(source_components, fit_components,
        parameters, covariance, payload, arithmetic)
    minimum = max(original_bytes, phases['maximum'])+original.RESERVE_BYTES+32768
    if minimum > limit:
        raise ValueError('original magnetic allocation: original source arithmetic quota exceeded')
    names = ('physical_original_optimizer', 'physical_original_terminal',
        'magnetic_original_optimizer', 'physical_original_quadratic', 'physical_owned_spd',
        'physical_reduced_optimizer', 'physical_original_residual_terminal', 'physical_original_rows')
    sources = {}
    for name in names:
        module = importlib.import_module(name)
        sha = hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        if sha != module.SOURCE_SHA256:
            raise ValueError('original magnetic allocation: loaded public source drift')
        sources[name] = sha
    return dict(schema='magnetic-original-allocation-2', source_components=source_components,
        fit_components=fit_components, parameters=parameters, covariance=covariance,
        observation_components=observation_components, original_bytes=original_bytes,
        native_phases=native, owned_source_phases=phases,
        source_payload_upper_bytes=payload, source_arithmetic_upper=arithmetic,
        minimum_phase_bytes=minimum,
        actual_terminal_phase_gate='public-owned-source-face-audit-before-allocation',
        admitted_bytes=limit, source_binding=sources, epoch=optimizer.LINEAR_EPOCH,
        policy=optimizer.POLICY)


class _MagneticDTO:
    def __init__(self, objective, source_components):
        from magnetic_optimizer_adapter import MagneticObjective
        if type(objective) is not MagneticObjective:
            raise TypeError('original magnetic bridge: actual native objective only')
        if (objective.operator.quantity not in ('secondary_enu_nT', 'linear_tmi_nT')
            or type(source_components) is not int
            or not 3*objective.operator.rows <= source_components <= 2048):
            raise ValueError('original magnetic bridge: original linear source COMPONENTS')
        self.native, self.source_components = objective, source_components

    def __getattr__(self, name):
        return getattr(self.native, name)

    def identity(self):
        return dict(self.native.identity(), runtime_epoch=optimizer.LINEAR_EPOCH)

    def metric_operands(self, q):
        o = self.native
        return owned.MetricOperands(owned.binding_for(self.identity(), q),
            self.source_components, o.observed.size, len(q), o.factor is not None,
            (o.beta*o.regularizer.vendor.deriv2(q)).tocsr().sorted_indices(),
            np.ascontiguousarray(o._state(q)[-1]))

    def quadratic_operands(self, q):
        o = self.native
        g, _, direction, _, quantity = o.operator.operand_snapshot()
        projection = direction if quantity == 'linear_tmi_nT' else None
        whitening = (original.OriginalWhitening('stored_lower_cholesky', o.factor, o.noise['values'])
            if o.factor is not None else original.OriginalWhitening('diagonal_sd', o.noise['values'].ravel()))
        terms = tuple(owned.QuadraticTerm(t['alpha'], sp.diags(t['weights'], format='csr'),
            t['derivative']) for t in o.regularizer.terms())
        return original.OriginalQuadraticOperands(owned.binding_for(self.identity(), q),
            self.source_components, g, projection, whitening, o.observed.ravel(),
            o.regularizer.reference, o.lower, o.upper, 1., o.beta, terms, g, projection)

    def magnetic_domain(self, q):
        _, background, direction, field_norm, quantity = self.native.operator.operand_snapshot()
        return optimizer.OriginalMagneticDomain(owned.binding_for(self.identity(), q),
            background, field_norm, direction, quantity)


def solve_magnetic_original(objective, start_q, *, source_components, budget, binding, terminal):
    """No new clock or step allowance; same native original physical solve."""
    dto = _MagneticDTO(objective, source_components)
    return optimizer.solve_bounded_linear(dto, objective.lower, objective.upper, start_q,
        budget=budget, binding=binding, terminal=terminal)


def certify_magnetic_original_state(objective, q, *, source_components, budget, binding, terminal):
    """Closed original state proof only; never a restarted native fit acceptance.

    Native source/G/g/box and free principal metric are owned here. No caller
    gradient, normalization, mask, inverse, certificate or solver hook exists.
    A research/read caller's proof clock does not reset an archived fit clock.
    """
    return _certify_magnetic_state(objective, q, source_components=source_components,
        budget=budget, binding=binding, terminal=terminal, residual=False)


def certify_magnetic_original_residual_state(objective, q, *, source_components, budget, binding, terminal):
    """Separate original convex residual state proof, not production fit policy."""
    return _certify_magnetic_state(objective, q, source_components=source_components,
        budget=budget, binding=binding, terminal=terminal, residual=True)


def _certify_magnetic_state(objective, q, *, source_components, budget, binding, terminal, residual):
    dto = _MagneticDTO(objective, source_components)
    factory = optimizer.accuracy.OwnedOriginalTerminal
    if residual:
        import physical_original_residual_terminal as module
        if (module.SOURCE_SHA256 != RESIDUAL_TERMINAL_SHA256 or
                hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() != RESIDUAL_TERMINAL_SHA256):
            raise ValueError('original magnetic state: closed residual source drift')
        factory = module.OwnedOriginalResidualTerminal
    identity, budget = optimizer.reduced.core._preflight(dto,
        objective.lower, objective.upper, q, budget, binding, terminal,
        'fixed_linear_quadratic', ('physical_original_optimizer',
            optimizer.SOURCE_SHA256, optimizer.POLICY, optimizer.LINEAR_EPOCH))
    if binding.certificate_source_sha256 != original.SOURCE_SHA256:
        raise ValueError('original magnetic state: literal original certificate source')
    operands = dto.quadratic_operands(q)
    original.validate(operands, identity, q, deadline=budget.deadline,
        resource_limit_bytes=budget.resource_limit_bytes, admitted_bytes=budget.admitted_bytes)
    domain = dto.magnetic_domain(q)
    passed, ratio = optimizer.magnetic_domain_check(domain, operands, q, q, deadline=budget.deadline)
    if not passed:
        raise ValueError('original magnetic state: strict original field domain')
    try:
        gradient = np.ascontiguousarray(objective.evaluate(q, True, False)[1])
        # This state-only diagnostic has no fit-start authority. Absolute KKT
        # is stricter than max(1, ||g(start)||inf); never replace fit policy.
        owner = factory(dto.metric_operands(q), operands,
            identity, q, gradient, 1., deadline=budget.deadline,
            resource_limit_bytes=budget.resource_limit_bytes, admitted_bytes=budget.admitted_bytes)
        check = owner.certify(terminal)
        if residual and (module.SOURCE_SHA256 != RESIDUAL_TERMINAL_SHA256 or
                hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() != RESIDUAL_TERMINAL_SHA256):
            raise ValueError('original magnetic state: residual source changed during proof')
    finally:
        objective.release_state()
    return dict(schema='magnetic-original-state-proof-1', identity=identity,
        model_sha256=owned.digest(q), domain_ratio_lower=ratio, check=check,
        normalization='absolute_unit_state_only',
        native_fit_accepted=False, full_method_accepted=False, host_accepted=False)
