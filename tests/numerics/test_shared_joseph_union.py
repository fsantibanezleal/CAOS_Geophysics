"""Default and complete construction coexist without phase-policy selection."""
from time import monotonic

import numpy as np
import pytest

import gravity_l2_metric as kernel
import physical_owned_spd as owned
import physical_original_quadratic as original
import magnetic_original_optimizer as magnetic
from test_physical_owned_spd import Physical


def test_default_owned_metric_keeps_exact_original_dictionary_and_numeric_class():
    source = Physical()
    try:
        q, identity = source.start, source.identity()
        dto = source.metric_operands(q)
        default = owned.OwnedMetric(dto, identity, q, np.arange(len(q), dtype=np.int64),
            monotonic()+120., 2*1024**3)
        try:
            assert type(default._numeric) is kernel.JosephMetric
            assert default.allocation == kernel.allocation(dto.source_components,
                dto.fit_components, dto.parameters, dto.covariance)
            assert 'complete_prior_workspace_bytes' not in default.allocation
            old_l, old_d = kernel._factor(dto.regularizer, monotonic()+120.)
            np.testing.assert_array_equal(default._numeric.lower.toarray(), old_l.toarray())
            np.testing.assert_array_equal(default._numeric.pivots, old_d)
        finally:
            default.close()
        complete = owned.OwnedCompletePriorMetric(dto, identity, q,
            np.arange(len(q), dtype=np.int64), monotonic()+120., 2*1024**3)
        try:
            assert type(complete._numeric) is kernel.CompleteFirstOrderJosephMetric
            assert complete.allocation['maximum'] == default.allocation['maximum']+kernel.complete_prior_workspace(len(q))
            assert complete.allocation['complete_prior_workspace_bytes'] == kernel.complete_prior_workspace(len(q))
        finally:
            complete.close()
        assert default.live_payload_bytes == complete.live_payload_bytes == 0
    finally:
        source.release_state()


def test_source_phase_epoch_remains_literal_default_no_automatic_complete_selection():
    plan = magnetic.allocation_plan(864, 648, 528, False, 120112128, 3)
    phase = plan['owned_source_phases']
    assert plan['epoch'] == original.SOURCE_PHASE_NATIVE_EPOCH
    assert phase['epoch'] == original.ALLOCATION_EPOCH
    assert phase['factory_bytes'] == 714986144
    assert phase['original_certificate_bytes'] == 680188848
    assert plan['minimum_phase_bytes'] == 723407520
    assert plan['admitted_bytes'] == 805306368
    assert 'complete_prior_workspace_bytes' not in plan['native_phases']


@pytest.mark.parametrize('base', [owned.OwnedMetric, owned.OwnedCompletePriorMetric])
def test_no_caller_subclass_can_choose_another_owned_numeric_factor(base, monkeypatch):
    class Foreign(base):
        pass
    source = Physical()
    try:
        monkeypatch.setattr(kernel, '_factor', lambda *a: pytest.fail('foreign class reached default factor'))
        monkeypatch.setattr(kernel, '_factor_complete', lambda *a: pytest.fail('foreign class reached complete factor'))
        with pytest.raises(TypeError, match='exact owned class'):
            Foreign(source.metric_operands(source.start), source.identity(), source.start,
                np.arange(len(source.start), dtype=np.int64), monotonic()+120., 2*1024**3)
    finally:
        source.release_state()
