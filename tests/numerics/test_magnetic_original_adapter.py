"""Native original-noise precision and closed M04 boundary, not host admission."""
from dataclasses import replace
import importlib.util
from pathlib import Path
from time import monotonic

import numpy as np
import pytest
from scipy.linalg import solve_triangular
from scipy.optimize import lsq_linear

import magnetic_original_adapter as adapter
from magnetic_optimizer_adapter import MagneticObjective
from magnetic_survey_json import digest
import physical_original_optimizer as core

spec = importlib.util.spec_from_file_location('original_independent_magnetic',
    Path(__file__).with_name('test_magnetic_optimizer_adapter.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@pytest.fixture(scope='module')
def physical():
    return control.physical.__wrapped__()


def make(physical, quantity='secondary_enu_nT', covariance=False):
    obj, kernel, data, noise, r, _ = control.make(physical, quantity, covariance)
    plan = adapter.allocation(90, data.size, 7, covariance, 1000000, obj.operator.components)
    fresh = MagneticObjective(obj.operator, obj.regularizer, obj.observed, obj.noise,
        obj.lower, obj.upper, obj.beta, obj.inventory, digest(plan), obj.stage)
    return fresh, plan, kernel, data, noise, r


def arguments(obj, plan):
    return dict(objective=obj, lower=obj.lower, upper=obj.upper, start=np.zeros(7), plan=plan,
        binding=adapter.binding_for_sources(adapter.source_binding(), obj.inventory),
        budget=core.ConditionedBudget(monotonic()+120., 200, adapter.LIMIT,
            plan['admitted_bytes'], digest(plan)))


@pytest.mark.parametrize('quantity', ['secondary_enu_nT', 'linear_tmi_nT'])
@pytest.mark.parametrize('covariance', [False, True])
@pytest.mark.parametrize('start_value', [0., 1.])
def test_actual_original_native_independent_precision(physical, quantity, covariance, start_value):
    obj, plan, kernel, data, noise, r = make(physical, quantity, covariance)
    if covariance:
        factor = np.linalg.cholesky(noise['values'])
        wk, wd = solve_triangular(factor, kernel, lower=True), solve_triangular(factor, data.ravel(), lower=True)
    else:
        wk, wd = kernel/.5, data.ravel()/.5
    matrix = np.vstack([wk, np.sqrt(.3)*r])
    rhs = np.r_[wd, np.sqrt(.3)*r@control.control.QREF]
    oracle = lsq_linear(matrix, rhs, bounds=(0., 10.), method='bvls', tol=1e-12, max_iter=10000)
    assert oracle.success
    started = monotonic()
    result = adapter.solve_original(**dict(arguments(obj, plan), start=np.full(7, start_value)))
    assert result['status'] == 'converged', result['reason']
    assert monotonic()-started <= 120.
    np.testing.assert_allclose(result['q'], oracle.x, rtol=0., atol=1e-6)
    optimum = np.linalg.norm(matrix@oracle.x-rhs)**2
    assert abs(result['phi_engine']-optimum)/max(1., optimum) <= 1e-8
    assert np.sqrt(np.mean((kernel@(result['q']-oracle.x))**2)) <= 1e-6
    assert result['runtime_epoch'] == core.LINEAR_EPOCH
    terminal = result['terminal_audits'][-1]['check']
    assert terminal['passed'] and terminal['disposed']
    assert terminal['allocation']['maximum'] <= adapter.LIMIT
    assert result['iterations'] <= 200
    phases = {}
    for row in result['conditioning_attempts']:
        assert row['failure'] is None and row['true_relative_residual'] <= 1e-6
        phases[row['iteration']] = phases.get(row['iteration'], 0)+row['iterations']
    assert max(phases.values(), default=0) <= 200
    assert all(row['trial'] < 20 for row in result['line_search_trials'])
    assert all(row['passed'] for row in result['magnetic_domain_checks'])


@pytest.mark.parametrize('bad', [True, 0, -1, 1.5])
def test_literal_allocation_counts(bad):
    with pytest.raises(ValueError):
        adapter.allocation(864, 432, bad, False, 100000000, 3)


def test_source_quota_bound_precedes_kernel():
    plan = adapter.allocation(864, 432, 528, False, 100000000, 3)
    assert plan['minimum_phase_bytes'] == 690057120 < adapter.LIMIT
    assert plan['admitted_bytes'] == adapter.LIMIT
    assert plan['source_binding'] == adapter.source_binding()
    with pytest.raises(ValueError):
        adapter.allocation(864, 432, 528, False, adapter.LIMIT, 3)
    with pytest.raises(ValueError):
        adapter.allocation(90, 91, 7, False, 1000000, 1)


def test_original_plan_binding_budget_and_box_drift(physical):
    obj, plan, *_ = make(physical)
    args = arguments(obj, plan)
    for bad in (replace(args['binding'], accepted_export='physical_reduced_optimizer.solve_bounded_linear'),
        replace(args['binding'], certificate_source_sha256='f'*64)):
        with pytest.raises(ValueError, match='binding'):
            adapter.solve_original(**dict(args, binding=bad))
    for bad in (replace(args['budget'], remaining_steps=201),
        replace(args['budget'], admitted_bytes=adapter.LIMIT-1),
        replace(args['budget'], allocation_plan_sha256='f'*64)):
        with pytest.raises(ValueError, match='binding'):
            adapter.solve_original(**dict(args, budget=bad))
    with pytest.raises(ValueError, match='binding'):
        adapter.solve_original(**dict(args, lower=np.full(7, .1)))
    changed = dict(plan, original_bytes=plan['original_bytes']+1)
    with pytest.raises(ValueError, match='binding'):
        adapter.solve_original(**dict(args, plan=changed))


def test_expiry_and_nonlinear_remain_refused(physical):
    obj, plan, *_ = make(physical)
    args = arguments(obj, plan)
    # Public original-source validation expires before native initialization;
    # do not fabricate a converged or synthetic failed native trace.
    with pytest.raises(core.source.intervals._Expired):
        adapter.solve_original(**dict(args, budget=replace(args['budget'], deadline=monotonic()-1.)))
    nonlinear, *_ = control.make(physical, 'exact_total_anomaly_nT', False)
    with pytest.raises(ValueError, match='LINEAR'):
        adapter.solve_original(**dict(args, objective=nonlinear))
