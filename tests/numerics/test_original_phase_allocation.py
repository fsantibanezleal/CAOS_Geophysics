"""No-fit source-owned phase controls; not RSS, native or method acceptance."""
from dataclasses import replace, fields
from time import monotonic

import pytest

import magnetic_original_optimizer as magnetic
import physical_original_quadratic as source
from test_physical_original_quadratic import operands as historical_operands


def operands():
    old, identity, q = historical_operands()
    identity = dict(identity, runtime_epoch=source.SOURCE_PHASE_NATIVE_EPOCH)
    value = source.SourcePhaseQuadraticOperands(**{field.name: getattr(old, field.name)
        for field in fields(old)})
    value = replace(value, binding=source.owned.binding_for(identity, q))
    return value, identity, q


@pytest.mark.parametrize('components,fit', [(3, 432), (3, 648), (1, 144), (1, 216)])
def test_literal_original528_fold_and_final_phase_sum_without_generic_deduction(components, fit):
    plan = magnetic.allocation_plan(864, fit, 528, False, 120112128, components)
    native, phase = plan['native_phases'], plan['owned_source_phases']
    payload = plan['source_payload_upper_bytes']
    arithmetic = sum(plan['source_arithmetic_upper'].values())
    assert phase['original_native_phases'] == native == source.owned.kernel.allocation(864, fit, 528, False)
    assert native['native'] == 633176064  # The full original native reserve remains.
    assert phase['factory_bytes'] == native['setup']+2*payload+32768
    assert phase['original_certificate_bytes'] == native['action']+max(8*1024**2, arithmetic)
    assert phase['maximum'] == max(phase['factory_bytes'], phase['original_certificate_bytes'])
    assert plan['minimum_phase_bytes'] == max(120112128, phase['maximum'])+8*1024**2+32768
    assert plan['minimum_phase_bytes'] <= plan['admitted_bytes'] == 805306368
    assert plan['schema'] == 'magnetic-original-allocation-2'
    assert plan['epoch'] == 'physical-gncg-original-noise-reduced-joseph-candidate-10'
    assert phase['epoch'] == source.ALLOCATION_EPOCH
    assert plan['source_binding']['physical_original_quadratic'] == source.SOURCE_SHA256
    if components == 3 and fit == 648:
        assert native['maximum'] == 774308112
        assert native['interval'] == 127008768
        assert arithmetic == 32889504
        assert native['maximum']+arithmetic+8*1024**2+32768 == 815618992
        assert phase['factory_bytes'] == 714986144
        assert phase['original_certificate_bytes'] == 680188848
        assert plan['minimum_phase_bytes'] == 723407520


@pytest.mark.parametrize('fault', ['count_type', 'source_rows', 'fit_rows', 'noise',
    'components', 'original_bytes', 'covariance512', 'oversize', 'source', 'constants'])
def test_original_public_plan_refusals_do_not_construct_metric_or_compute_certificate(fault, monkeypatch):
    arguments = [864, 648, 528, False, 120112128, 3]
    monkeypatch.setattr(source.owned, 'OwnedMetric', lambda *a, **k: pytest.fail('no-fit gate constructed metric'))
    monkeypatch.setattr(source, 'certify_chord', lambda *a, **k: pytest.fail('no-fit gate computed certificate'))
    if fault == 'count_type':
        arguments[0] = True
    elif fault == 'source_rows':
        arguments[0] = 863
    elif fault == 'fit_rows':
        arguments[1] = 647
    elif fault == 'noise':
        arguments[3] = 1
    elif fault == 'components':
        arguments[5] = 2
    elif fault == 'original_bytes':
        arguments[4] = 805306369
    elif fault == 'covariance512':
        arguments[3] = True
    elif fault == 'oversize':
        arguments[2] = 4096
    elif fault == 'source':
        monkeypatch.setattr(source, 'SOURCE_SHA256', '0'*64)
    else:
        monkeypatch.setattr(source, 'ENDPOINT_PAIR_BYTES', 1024)
    with pytest.raises((ValueError, TypeError)):
        magnetic.allocation_plan(*arguments)


def test_actual_source_phase_minimum_and_one_byte_short_use_ultimate_backing():
    dto, identity, q = operands()
    kwargs = dict(deadline=monotonic()+120., resource_limit_bytes=805306368, admitted_bytes=805306368)
    result = source.validate(dto, identity, q, **kwargs)
    minimum = result['maximum']
    exact = source.validate(dto, identity, q, **dict(kwargs, admitted_bytes=minimum))
    assert exact == result
    with pytest.raises(ValueError, match='source-bound original phases'):
        source.validate(dto, identity, q, **dict(kwargs, admitted_bytes=minimum-1))
    # Aliased original source/prediction occurrences still get charged twice.
    assert dto.sensitivity is dto.prediction_sensitivity
    arrays = (dto.sensitivity, dto.prediction_sensitivity, dto.observations,
        dto.reference, dto.lower, dto.upper, dto.whitening.values)
    payload = sum(source._backing_bytes(v) for v in arrays)
    payload += sum(source._backing_bytes(v) for term in dto.terms
        for matrix in (term.weights, term.derivative)
        for v in (matrix.data, matrix.indices, matrix.indptr))
    assert payload == result['operand_payload_bytes']
    assert result['arithmetic_phase']['operand_and_sparse_copy_bytes'] == 2*payload


def test_actual_source_clock_and_resource_refuse_before_arithmetic(monkeypatch):
    dto, identity, q = operands()
    monkeypatch.setattr(source, '_gradient', lambda *a: pytest.fail('refusal reached source arithmetic'))
    with pytest.raises(source.intervals._Expired):
        source.source_gradient(dto, identity, q, deadline=monotonic()-1.,
            resource_limit_bytes=805306368, admitted_bytes=805306368)
    with pytest.raises(ValueError):
        source.source_gradient(dto, identity, q, deadline=monotonic()+120.,
            resource_limit_bytes=805306368, admitted_bytes=1)
    with pytest.raises(TypeError):
        magnetic.allocation_plan(864, 648, 528, False, 120112128, 3, disjoint=True)


def test_actual_endpoint_capacity_and_new_allocation_identity_not_self_approval():
    dto, identity, q = operands()
    result = source.validate(dto, identity, q, deadline=monotonic()+120.,
        resource_limit_bytes=805306368, admitted_bytes=805306368)
    phase = result['owned_source_phases']
    assert phase['maximum'] >= phase['factory_bytes']
    assert phase['maximum'] >= phase['original_certificate_bytes']
    assert result['arithmetic_phase']['endpoint_bytes'] == 2048*(6*3+6*6+4*3)
    changed = replace(dto, binding=replace(dto.binding, allocation_plan_sha256='0'*64))
    with pytest.raises(ValueError, match='source/model binding'):
        source.validate(changed, identity, q, deadline=monotonic()+120.,
            resource_limit_bytes=805306368, admitted_bytes=805306368)


def test_explicit_source10_dto_does_not_upgrade_original_dto_or_wrong_epoch():
    historical, identity, q = historical_operands()
    kwargs = dict(deadline=monotonic()+120., resource_limit_bytes=805306368, admitted_bytes=805306368)
    old = source.validate(historical, identity, q, **kwargs)
    assert old['owned_source_phases'] is None
    assert old['maximum'] == old['original']['maximum']+max(8*1024**2, sum(old['arithmetic_phase'].values()))
    prospective, current, point = operands()
    new = source.validate(prospective, current, point, **kwargs)
    assert new['maximum'] == new['owned_source_phases']['maximum']
    assert new['owned_source_phases']['epoch'] == source.ALLOCATION_EPOCH
    changed = replace(prospective, binding=source.owned.binding_for(identity, q))
    with pytest.raises(ValueError, match='literal source10 original phase DTO epoch'):
        source.validate(changed, identity, q, **kwargs)
    class Foreign(source.SourcePhaseQuadraticOperands):
        pass
    wrong = Foreign(**{field.name: getattr(prospective, field.name) for field in fields(prospective)})
    with pytest.raises(ValueError, match='closed source/count'):
        source.validate(wrong, current, point, **kwargs)


def test_source10_native_residual_epoch_owns_proof_without_old_fallback(monkeypatch):
    # New prospective epoch contract. The historical source9 contract/assertion
    # remains unmodified and belongs to its independently pinned source9 node.
    import numpy as np
    import physical_original_optimizer as optimizer
    from test_physical_original_optimizer import native_control, binding_for, assert_caps
    control = native_control()
    objective, *_ = control.make(control.physical.__wrapped__(), 'secondary_enu_nT', False)
    def forbidden(*args, **kwargs):
        pytest.fail('source10 residual production cannot select old Neumann terminal')
    monkeypatch.setattr(optimizer.accuracy, 'OwnedOriginalTerminal', forbidden)
    started = monotonic()
    try:
        result = magnetic.solve_magnetic_original(objective, np.zeros(7), source_components=90,
            budget=optimizer.ConditionedBudget(started+120., 200, 805306368, 805306368, objective.allocation),
            binding=binding_for(objective), terminal=source.owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
        assert result['status'] == 'converged', result['reason']
        assert_caps(result, monotonic()-started)
        assert result['runtime_epoch'] == source.SOURCE_PHASE_NATIVE_EPOCH
        assert result['policy'] == 'closed-original-noise-reduced-joseph-free-face-residual-owned-phases-3'
        assert result['source_binding']['original_residual_terminal'] == optimizer.RESIDUAL_TERMINAL_SHA256
        for row in result['terminal_audits']:
            if row['check'] is not None:
                check = row['check']
                assert check['proof_basis'] == 'original_physical_residual_strong_convexity'
                assert check['actions'] == (1 if check['free_indices'] else 0) and check['disposed']
                original = check['allocation']['original']
                assert original['owned_source_phases']['epoch'] == source.ALLOCATION_EPOCH
    finally:
        objective.release_state()
