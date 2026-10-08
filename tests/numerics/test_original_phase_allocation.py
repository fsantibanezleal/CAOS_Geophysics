"""No-fit source-owned phase controls; not RSS, native or method acceptance."""
from dataclasses import replace
from time import monotonic

import pytest

import magnetic_original_optimizer as magnetic
import physical_original_quadratic as source
from test_physical_original_quadratic import operands


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
