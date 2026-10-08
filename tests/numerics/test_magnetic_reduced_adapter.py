"""Original independent Choclo/BVLS gates, not full-survey acceptance."""
from dataclasses import replace
import hashlib
import importlib.util
from pathlib import Path
from time import monotonic

import numpy as np
import pytest
from scipy.linalg import solve_triangular
from scipy.optimize import lsq_linear

import magnetic_reduced_adapter as adapter
from magnetic_optimizer_adapter import MagneticObjective, certificate_source
from magnetic_survey_json import digest
import physical_reduced_optimizer as core
import physical_owned_spd as spd

spec = importlib.util.spec_from_file_location('reduced_independent_magnetic',
    Path(__file__).with_name('test_magnetic_optimizer_adapter.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@pytest.fixture(scope='module')
def physical():
    return control.physical.__wrapped__()


def make(physical, quantity='secondary_enu_nT', covariance=False):
    base, kernel, observed, noise, r, _ = control.make(physical, quantity, covariance)
    plan = adapter.allocation(90, observed.size, 7, covariance, 1000000)
    fresh = MagneticObjective(base.operator, base.regularizer, base.observed, base.noise,
        base.lower, base.upper, base.beta, base.inventory, digest(plan), base.stage)
    obj = adapter.MagneticReducedObjective(fresh, plan)
    return obj, plan, kernel, observed, noise, r


def arguments(obj, plan, start):
    sources = {'magnetic_inverse_precision': hashlib.sha256(Path(certificate_source()).read_bytes()).hexdigest()}
    binding = adapter.binding_for_sources(sources, obj.identity()['source_inventory_sha256'])
    return dict(objective=obj, lower=obj.lower, upper=obj.upper, start=start, binding=binding,
        budget=core.ConditionedBudget(monotonic()+120., 200, adapter.LIMIT,
            plan['admitted_bytes'], digest(plan)))


@pytest.mark.parametrize('quantity', ['secondary_enu_nT', 'linear_tmi_nT'])
@pytest.mark.parametrize('covariance', [False, True])
@pytest.mark.parametrize('start_value', [0., 1.])
def test_original_independent_precision_and_actual_public_native(physical, quantity, covariance, start_value):
    obj, plan, kernel, data, noise, r = make(physical, quantity, covariance)
    if covariance:
        factor = np.linalg.cholesky(noise['values'])
        wk = solve_triangular(factor, kernel, lower=True)
        wd = solve_triangular(factor, data.ravel(), lower=True)
    else:
        wk, wd = kernel/.5, data.ravel()/.5
    matrix = np.vstack([wk, np.sqrt(.3)*r])
    rhs = np.r_[wd, np.sqrt(.3)*r@control.control.QREF]
    oracle = lsq_linear(matrix, rhs, bounds=(0., 10.), method='bvls', tol=1e-12, max_iter=10000)
    assert oracle.success
    result = adapter.solve_reduced(**arguments(obj, plan, np.full(7, start_value)))
    assert result['status'] == 'converged', result['reason']
    np.testing.assert_allclose(result['q'], oracle.x, rtol=0., atol=1e-6)
    optimum = np.linalg.norm(matrix@oracle.x-rhs)**2
    assert abs(result['phi_engine']-optimum)/max(1., optimum) <= 1e-8
    assert np.sqrt(np.mean((kernel@(result['q']-oracle.x))**2)) <= 1e-6
    assert result['runtime_epoch'] == core.LINEAR_EPOCH
    assert result['source_binding']['optimizer'] == core.SOURCE_SHA256
    assert result['terminal_audits'][-1]['check']['passed']
    assert result['iterations'] <= 200
    for phase in result['conditioning_attempts']:
        if phase['branch'] == 'cg':
            assert phase['true_relative_residual'] <= 1e-6
            assert phase['cumulative_CG'] <= 200
            assert phase['resource']['prospective_peak_bytes'] <= plan['admitted_bytes']
    assert all(t['effective_alpha'] == t['alpha']*t['ray_alpha0'] for t in result['line_search_trials'])


def test_full_source_conservative_public_reserve_before_kernel():
    plan = adapter.allocation(864, 432, 528, False, 100000000)
    assert plan['original']['metric_phases']['maximum'] == 761838864
    assert plan['reserve']['workspace_bytes'] == core.WORKSPACE_BYTES
    assert plan['reserve']['phase_limit'] == core.PHASE_LIMIT
    assert plan['admitted_bytes'] == 779123088 < adapter.LIMIT
    assert plan['source_binding']['optimizer'] == core.SOURCE_SHA256
    assert plan['reserve']['direction_limit'] == 200
    with pytest.raises(ValueError):
        adapter.allocation(864, 432, 528, False, adapter.LIMIT)


@pytest.mark.parametrize('bad', [True, 0, -1, 1.5])
def test_literal_allocation_counts(bad):
    with pytest.raises(ValueError):
        adapter.allocation(864, 432, bad, False, 1000000)


def test_source_constant_drift_refuses(monkeypatch):
    monkeypatch.setattr(core, 'PHASE_LIMIT', 513)
    with pytest.raises(ValueError, match='public'):
        adapter.allocation(864, 432, 528, False, 1000000)


def test_original_physical_methods_and_owned_plan(physical):
    obj, plan, *_ = make(physical)
    q = control.control.Q.copy()
    np.testing.assert_array_equal(obj.evaluate(q, True, False)[1], obj.physical.evaluate(q, True, False)[1])
    dto = obj.metric_operands(q)
    assert dto.binding == spd.binding_for(obj.identity(), q)
    np.testing.assert_array_equal(dto.regularizer.toarray(), obj.beta*obj.regularizer.vendor.deriv2(q).toarray())
    plan['reserve']['phase_limit'] = 1
    assert obj.allocation_plan()['reserve']['phase_limit'] == core.PHASE_LIMIT
    changed = obj.allocation_plan()
    changed['reserve']['phase_limit'] = 1
    assert obj.allocation_plan()['reserve']['phase_limit'] == core.PHASE_LIMIT


def test_binding_budget_plan_drift_before_solve(physical):
    obj, plan, *_ = make(physical)
    args = arguments(obj, plan, np.zeros(7))
    for bad in (replace(args['binding'], accepted_export='physical_feasible_optimizer.solve_bounded_linear'),
                replace(args['binding'], certificate_source_sha256='f'*64)):
        with pytest.raises(ValueError, match='binding'):
            adapter.solve_reduced(**dict(args, binding=bad))
    for bad in (replace(args['budget'], allocation_plan_sha256='f'*64),
                replace(args['budget'], admitted_bytes=plan['admitted_bytes']-1),
                replace(args['budget'], remaining_steps=201)):
        with pytest.raises(ValueError, match='budget'):
            adapter.solve_reduced(**dict(args, budget=bad))


def test_original_expiry_retained_and_nonlinear_refused(physical):
    obj, plan, *_ = make(physical)
    args = arguments(obj, plan, np.zeros(7))
    result = adapter.solve_reduced(**dict(args, budget=replace(args['budget'], deadline=monotonic()-1.)))
    assert result['reason'] == 'wall_cap' and result['status'] != 'converged'
    base, *_ = control.make(physical, 'exact_total_anomaly_nT', False)
    with pytest.raises(ValueError, match='LINEAR'):
        adapter.MagneticReducedObjective(base, plan)
