"""Actual original physical operands and unchanged independent error gates."""
from dataclasses import replace
import hashlib
import importlib.util
from pathlib import Path
from time import monotonic

import numpy as np
import pytest
from scipy.linalg import solve_triangular
from scipy.optimize import least_squares

import magnetic_conditioned_adapter as adapter
from magnetic_optimizer_adapter import certificate_source
import physical_conditioned_optimizer as core
import physical_owned_spd as spd

spec = importlib.util.spec_from_file_location('conditioned_nonlinear_control',
    Path(__file__).with_name('test_magnetic_nonlinear_adapter.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@pytest.fixture(scope='module')
def physical():
    return control.physical.__wrapped__()


def arguments(obj, start, steps=200, deadline=None):
    identity = obj.identity()
    nonlinear = identity['mode'] == 'nonlinear_gauss_newton'
    binding = core.ConditionedBinding('physical_conditioned_optimizer.solve_bounded_'+('nonlinear' if nonlinear else 'linear'),
        core.SOURCE_SHA256, spd.SOURCE_SHA256, spd.KERNEL_SHA256, core.VENDOR_SOURCE_SHA256,
        hashlib.sha256(Path(certificate_source()).read_bytes()).hexdigest(),
        identity['source_inventory_sha256'], identity['runtime_epoch'], core.POLICY)
    envelope = adapter.allocation(obj.source_components, obj.operator.rows*obj.operator.components,
        obj.operator.parameters, True, 1000000)
    budget = core.ConditionedBudget(monotonic()+120. if deadline is None else deadline, steps,
        adapter.LIMIT, envelope['admitted_bytes'], identity['allocation_plan_sha256'])
    return dict(objective=obj, lower=np.zeros(len(start)), upper=np.full(len(start), 10.), start=start,
                budget=budget, binding=binding)


@pytest.mark.parametrize('quantity', ['secondary_enu_nT', 'linear_tmi_nT', 'exact_total_anomaly_nT'])
@pytest.mark.parametrize('covariance', [False, True])
def test_same_original_physical_operands_and_noise_principal(physical, quantity, covariance):
    base, *_ = control.control.make(physical, quantity, covariance)
    if quantity == 'exact_total_anomaly_nT':
        base = control.MagneticNonlinearObjective(base, control.control.control.Q)
    wrapped = adapter.MagneticConditionedObjective(base, 90)
    q = control.control.control.Q.copy()
    dto = wrapped.metric_operands(q)
    assert dto.source_components == 90 and dto.fit_components == 30*(3 if quantity == 'secondary_enu_nT' else 1)
    assert dto.covariance is covariance and dto.likelihood_scale == 1.
    assert dto.binding == spd.binding_for(wrapped.identity(), q)
    np.testing.assert_array_equal(dto.regularizer.toarray(), wrapped.beta*wrapped.regularizer.vendor.deriv2(q).toarray())
    np.testing.assert_array_equal(dto.whitened_jacobian, base.whiten(wrapped.operator.evaluate(q)['jacobian_nT_per_q']))
    np.testing.assert_array_equal(wrapped.whiten(np.ones(dto.fit_components), transpose=True),
                                 base.whiten(np.ones(dto.fit_components), transpose=True))
    np.testing.assert_array_equal(wrapped.evaluate(q, True, False)[1], base.evaluate(q, True, False)[1])
    assert wrapped.evaluate(q) == base.evaluate(q)
    refreshed = wrapped.metric_operands(q+.001*control.control.control.V)
    assert refreshed.binding.model_sha256 != dto.binding.model_sha256
    assert np.array_equal(refreshed.whitened_jacobian, dto.whitened_jacobian) is (quantity != 'exact_total_anomaly_nT')


@pytest.mark.parametrize('epsilon', [.1, .05, .025, .0125, .00625, .003125, .0015625, .001])
def test_actual_fixed_sparse_surrogates_without_reweighting_or_floor(physical, epsilon):
    base, *_ = control.control.make(physical, 'secondary_enu_nT', False, 'sparse_smallness', epsilon)
    obj = adapter.MagneticConditionedObjective(base, 90)
    dto = obj.metric_operands(control.control.control.Q)
    np.testing.assert_array_equal(dto.regularizer.toarray(), base.beta*base.regularizer.vendor.deriv2(control.control.control.Q).toarray())
    assert base.regularizer.epsilon == epsilon
    assert spd.validate_operands(dto, obj.identity(), control.control.control.Q, adapter.LIMIT)['maximum'] < adapter.LIMIT


@pytest.mark.parametrize('start_value', [0., .2, 1.])
def test_original_three_start_choclo_objective_and_prediction_precision(physical, tmp_path, start_value):
    start = np.full(7, start_value)
    base, prediction, noise, r = control.make(physical, True, start)
    obj = adapter.MagneticConditionedObjective(base, 90)
    factor = np.linalg.cholesky(noise['values'])
    observed = base.base.observed.ravel()
    def residual(q):
        return np.r_[solve_triangular(factor, prediction(q)-observed, lower=True),
                     np.sqrt(.3)*r@(q-control.control.control.QREF)]
    oracle = least_squares(residual, start, bounds=(0., 10.), ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=10000)
    result = adapter.solve_conditioned(**arguments(obj, start))
    assert result['q'] is not None
    gap = abs(obj.evaluate(result['q'])-oracle.fun@oracle.fun)/max(1., oracle.fun@oracle.fun)
    discrepancy = float(np.sqrt(np.mean((prediction(result['q'])-prediction(oracle.x))**2)))
    from magnetic_survey_json import canonical
    (tmp_path/'conditioned-original-precision.json').write_bytes(canonical(dict(
        start_q=start_value, status=result['status'], reason=result['reason'],
        objective_gap=float(gap), independent_prediction_rms_nT=discrepancy,
        actual_iterations=result['iterations'], field_accepted=False)))
    assert gap <= 1e-8 and discrepancy <= 1e-6
    if result['status'] == 'converged':
        assert result['terminal_audits'][-1]['check']['passed']
        assert all(p['decision'] == 'certified_accept' for p in result['trace']['magnetic_norm_proofs'])


def test_original_full_resource_counts_and_no_capacity_increase():
    envelope = adapter.allocation(864, 432, 528, False, 100000000)
    assert envelope['admitted_bytes'] == 761838864 < adapter.LIMIT
    with pytest.raises(ValueError):
        adapter.allocation(864, 432, 528, True, adapter.LIMIT+1)


def test_binding_cap_and_expired_failure_retained(physical):
    base, *_ = control.control.make(physical, 'secondary_enu_nT', False)
    obj = adapter.MagneticConditionedObjective(base, 90)
    start = np.zeros(7)
    args = arguments(obj, start, deadline=monotonic()-1.)
    result = adapter.solve_conditioned(**args)
    assert result['status'] != 'converged' and result['reason'] == 'wall_cap' and result['q'] is None
    args = arguments(obj, start)
    with pytest.raises(ValueError):
        adapter.solve_conditioned(**dict(args, binding=replace(args['binding'], certificate_source_sha256='f'*64)))
    with pytest.raises(ValueError):
        adapter.solve_conditioned(**dict(args, budget=replace(args['budget'], remaining_steps=201)))
    with pytest.raises(ValueError):
        adapter.MagneticConditionedObjective(base, 30)


def test_complete_failed_solver_diagnostics_durable_and_exclusive(physical, tmp_path):
    import json
    from magnetic_survey_json import InputError
    base, *_ = control.control.make(physical, 'secondary_enu_nT', False)
    obj = adapter.MagneticConditionedObjective(base, 90)
    result = adapter.solve_conditioned(**arguments(obj, np.zeros(7), deadline=monotonic()-1.))
    audit = adapter.OptimizerAudit(tmp_path/'optimizer.jsonl', 'a'*64)
    try:
        audit.append('b00-l2', 0, result)
        audit.used = 64*1024**2
        with pytest.raises(InputError, match='capacity'):
            audit.append('b00-l2', 1, result)
    finally:
        audit.close()
    record = json.loads((tmp_path/'optimizer.jsonl').read_bytes())
    assert record['actual_result']['reason'] == 'wall_cap'
    assert record['actual_result']['conditioning_attempts'] == []
    assert record['actual_result']['source_binding']['optimizer'] == core.SOURCE_SHA256
    with pytest.raises(FileExistsError):
        adapter.OptimizerAudit(tmp_path/'optimizer.jsonl', 'a'*64)


def test_resource_refusal_before_any_full_source_kernel(monkeypatch):
    support_spec = importlib.util.spec_from_file_location('conditioned_source_resource_control',
        Path(__file__).parents[1]/'data'/'magnetic_survey_support.py')
    support = importlib.util.module_from_spec(support_spec)
    support_spec.loader.exec_module(support)
    from magnetic_survey_json import InputError
    import magnetic_calibration as calibration
    sources = {'magnetic_inverse_precision': hashlib.sha256(Path(certificate_source()).read_bytes()).hexdigest()}
    binding = adapter.binding_for_sources(sources, 'a'*64, nonlinear=False)
    doc = support.request()
    doc['policy']['optimizer_binding'] = dict(accepted_source=binding.optimizer_source_sha256,
        accepted_export=binding.accepted_export, epoch=binding.runtime_epoch)
    def refuse(*args):
        raise ValueError('public full-source allocation refusal')
    monkeypatch.setattr(adapter, 'allocation', refuse)
    monkeypatch.setattr(calibration, 'build_operator', lambda *a, **k: pytest.fail('kernel born before resource gate'))
    with pytest.raises(InputError, match='full-source allocation refusal'):
        calibration.calibrate(support.encode(doc), binding=binding, source_inventory_sha256='a'*64,
                              deadline=monotonic()+120.)
