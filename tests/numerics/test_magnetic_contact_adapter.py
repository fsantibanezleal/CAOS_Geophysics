"""Public source-owned contact, original Choclo/BVLS and unchanged precision."""
from dataclasses import replace
import hashlib
import importlib.util
from pathlib import Path
from time import monotonic

import numpy as np
import pytest
from scipy.linalg import solve_triangular
from scipy.optimize import lsq_linear

import magnetic_conditioned_adapter as adapter
import physical_conditioned_optimizer as conditioned
import physical_feasible_optimizer as core

spec = importlib.util.spec_from_file_location('contact_physical_control',
    Path(__file__).with_name('test_magnetic_optimizer_adapter.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@pytest.fixture(scope='module')
def physical():
    return control.physical.__wrapped__()


def arguments(obj, start):
    identity = obj.identity()
    sources = {'magnetic_inverse_precision': hashlib.sha256(Path(control.adapter.certificate_source()).read_bytes()).hexdigest()}
    binding = adapter.binding_for_sources(sources, identity['source_inventory_sha256'], nonlinear=False, feasible=True)
    phase = adapter.allocation(obj.source_components, obj.operator.rows*obj.operator.components,
        obj.operator.parameters, True, 1000000)
    return dict(objective=obj, lower=np.zeros(7), upper=np.full(7, 10.), start=start,
        binding=binding, budget=core.ConditionedBudget(monotonic()+120., 200, adapter.LIMIT,
            phase['admitted_bytes'], identity['allocation_plan_sha256']))


@pytest.mark.parametrize('quantity', ['secondary_enu_nT', 'linear_tmi_nT'])
@pytest.mark.parametrize('covariance', [False, True])
@pytest.mark.parametrize('start_value', [0., 1.])
def test_actual_contact_against_original_independent_bvls(physical, quantity, covariance, start_value):
    base, kernel, data, noise, regularizer, _ = control.make(physical, quantity, covariance)
    obj = adapter.MagneticConditionedObjective(base, 90, feasible=True)
    if covariance:
        factor = np.linalg.cholesky(noise['values'])
        wk = solve_triangular(factor, kernel, lower=True)
        wd = solve_triangular(factor, data.ravel(), lower=True)
    else:
        wk, wd = kernel/.5, data.ravel()/.5
    stacked = np.vstack([wk, np.sqrt(.3)*regularizer])
    rhs = np.r_[wd, np.sqrt(.3)*regularizer@control.control.QREF]
    independent = lsq_linear(stacked, rhs, bounds=(0., 10.), method='bvls', tol=1e-12, max_iter=10000)
    result = adapter.solve_conditioned(**arguments(obj, np.full(7, start_value)))
    assert result['status'] == 'converged', result['reason']
    np.testing.assert_allclose(result['q'], independent.x, rtol=0., atol=1e-6)
    optimum = np.linalg.norm(stacked@independent.x-rhs)**2
    assert abs(result['phi_engine']-optimum)/max(1., optimum) <= 1e-8
    assert np.sqrt(np.mean((kernel@(result['q']-independent.x))**2)) <= 1e-6
    assert result['runtime_epoch'] == core.LINEAR_EPOCH
    assert result['source_binding']['optimizer'] == core.SOURCE_SHA256
    assert result['source_binding']['conditioned_dependency'] == conditioned.SOURCE_SHA256
    assert result['terminal_audits'][-1]['check']['passed']
    assert all(a['true_relative_residual'] <= 1e-6 for a in result['conditioning_attempts'] if a['branch'] == 'cg')
    assert all(t['effective_alpha'] == t['ray_alpha0']*t['alpha'] for t in result['line_search_trials'])
    assert result['iterations'] <= 200


def test_binding_mismatch_and_no_implicit_nonlinear_contact(physical):
    base, *_ = control.make(physical, 'secondary_enu_nT', False)
    obj = adapter.MagneticConditionedObjective(base, 90, feasible=True)
    args = arguments(obj, np.zeros(7))
    with pytest.raises(ValueError, match='binding'):
        adapter.solve_conditioned(**dict(args, binding=replace(args['binding'],
            accepted_export='physical_conditioned_optimizer.solve_bounded_linear')))
    from magnetic_nonlinear_adapter import MagneticNonlinearObjective
    base, *_ = control.make(physical, 'exact_total_anomaly_nT', False)
    with pytest.raises(ValueError, match='LINEAR-only'):
        adapter.MagneticConditionedObjective(MagneticNonlinearObjective(base, np.zeros(7)), 90, feasible=True)
    with pytest.raises(ValueError, match='LINEAR-only'):
        adapter.binding_for_sources({}, 'a'*64, nonlinear=True, feasible=True)
