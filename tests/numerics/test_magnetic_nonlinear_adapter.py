"""Independent exact-total-field physical derivative and native fit audits."""

from decimal import Decimal, localcontext
import importlib.util
import json
from pathlib import Path
from time import monotonic

import numpy as np
import pytest
from scipy.optimize import least_squares
from scipy.linalg import solve_triangular

from magnetic_optimizer_adapter import MagneticObjective
from magnetic_nonlinear_adapter import MagneticNonlinearObjective, solve_nonlinear
import physical_nonlinear_optimizer as core

spec = importlib.util.spec_from_file_location('nonlinear_control', Path(__file__).with_name('test_magnetic_optimizer_adapter.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@pytest.fixture(scope='module')
def physical():
    return control.physical.__wrapped__()


def make(physical, covariance=False, start=None):
    original, _, _, noise, r, _ = control.make(physical, 'exact_total_anomaly_nT', covariance)
    # Choclo physical columns, independently retained arithmetic/direct sqrt.
    ab = (.01*physical[2]).reshape(30, 3, 7)
    b0 = 50000.*physical[3]

    def prediction(q):
        secondary = np.einsum('nca,a->nc', ab, q)
        with localcontext() as ctx:
            ctx.prec = 80
            background = [Decimal.from_float(float(v)) for v in b0]
            return np.array([float(sum((a+Decimal.from_float(float(v)))**2
                for a, v in zip(background, row)).sqrt()-Decimal(50000)) for row in secondary])

    observed = prediction(control.control.Q)[:, None]
    base = MagneticObjective(original.operator, original.regularizer, observed, noise, np.zeros(7), np.full(7, 10.),
                             .3, 'a'*64, 'b'*64, 0)
    obj = MagneticNonlinearObjective(base, np.zeros(7) if start is None else start)
    return obj, prediction, noise, r


@pytest.mark.parametrize('covariance', [False, True])
def test_exact_hessian_and_refreshed_psd_gn_independent_derivatives(physical, covariance):
    obj, prediction, noise, _ = make(physical, covariance)
    q, v = control.control.Q.copy(), control.control.V.copy()
    value, gradient, gn = obj.evaluate(q, True, True)
    exact = obj.exact_hessian(q)
    assert exact is not gn
    assert obj.identity()['physical_unit'] == 'si' and obj.identity()['physical_scale'] == (.01,)
    assert obj.identity()['beta_engine'] == 1.
    terms = obj.components(q)['engine_terms']
    assert (((terms[0]+terms[1])+terms[2])+terms[3])+terms[4] == value
    assert terms[0] == terms[2] == terms[4] == 0.
    h = 1e-5
    fd = (obj.evaluate(q+h*v, True, False)[1]-obj.evaluate(q-h*v, True, False)[1])/(2*h)
    np.testing.assert_allclose(exact@v, fd, rtol=2e-6, atol=1e-6)
    assert float(v@(gn@v)) >= 0.
    independent_fd = (prediction(q+h*v)-prediction(q-h*v))/(2*h)
    np.testing.assert_allclose(obj.operator.evaluate(q)['jacobian_nT_per_q']@v, independent_fd, rtol=2e-6, atol=1e-6)
    diagonal = obj.binding_diagonal(q)
    np.testing.assert_array_equal(diagonal, obj.binding_diagonal(q+.01*v))
    assert not np.array_equal(obj.base.binding_diagonal(q), obj.base.binding_diagonal(q+.01*v))
    free = np.array([0, 2, 6], dtype=np.int64)
    expected = np.zeros(7)
    expected[free] = (1./diagonal)[free]*v[free]
    np.testing.assert_array_equal(obj.free_metric(q, free)@v, expected)
    # Adjoint/symmetry, not a claim that GN equals the exact Hessian.
    u = np.arange(1., 8.)/9.
    assert abs(u@(exact@v)-v@(exact@u)) <= 1e-10*max(1., abs(u@(exact@v)))
    assert np.isfinite(gradient).all()


@pytest.mark.parametrize('start_value', [0., .2, 1.])
def test_actual_native_three_starts_against_independent_bounded_choclo(physical, tmp_path, start_value):
    start = np.full(7, start_value)
    obj, prediction, noise, r = make(physical, True, start)
    factor = np.linalg.cholesky(noise['values'])
    observed = obj.base.observed.ravel()

    def residual(q):
        return np.r_[solve_triangular(factor, prediction(q)-observed, lower=True),
                     np.sqrt(.3)*r@(q-control.control.QREF)]

    oracle = least_squares(residual, start, bounds=(0., 10.), ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=10000)
    binding = core.NonlinearBinding('physical_nonlinear_optimizer.solve_bounded_nonlinear', core.SOURCE_SHA256,
        core.VENDOR_SOURCE_SHA256, 'a'*64, core.RUNTIME_EPOCH, core.POLICY)
    budget = core.NonlinearBudget(monotonic()+120., 200, 805306368, 1000000, 'b'*64)
    result = solve_nonlinear(obj, np.zeros(7), np.full(7, 10.), start, budget=budget, binding=binding)
    trace = result['trace']
    assert result['q'] is not None and len(trace['models_q']) == result['iterations']+1
    assert np.all(trace['armijo_margins'] <= 0.) and np.all(trace['projected_slopes'] < 0.)
    assert np.all(trace['cg_relative_residuals'][trace['cg_residuals_available']] <= 1e-6)
    proofs = trace['magnetic_norm_proofs']
    if result['status'] == 'converged':
        assert len(proofs) == result['iterations'] and all(p['decision'] == 'certified_accept' for p in proofs)
    else:
        assert result['reason'] is not None
    objective_gap = abs(obj.evaluate(result['q'])-np.dot(oracle.fun, oracle.fun))/max(1., np.dot(oracle.fun, oracle.fun))
    discrepancy = float(np.sqrt(np.mean((prediction(result['q'])-prediction(oracle.x))**2)))
    evidence = dict(kind='authored_tiny_nonlinear_control_only', start_q=start.tolist(),
        status=result['status'], reason=result['reason'], iterations=result['iterations'],
        q=result['q'].tolist(), independent_objective=float(oracle.fun@oracle.fun),
        relative_objective_gap=objective_gap, independent_prediction_rms_nT=discrepancy,
        native_kkt_normalized=result['kkt_normalized'], norm_proofs=proofs,
        field_accepted=False, global_optimum_claimed=False)
    (tmp_path/'actual-nonlinear-audit.json').write_text(json.dumps(evidence, allow_nan=False), encoding='utf-8')
    assert objective_gap <= 1e-8 and discrepancy <= 1e-6


def test_public_nonlinear_gate_retains_expired_failure(physical):
    obj, _, _, _ = make(physical)
    binding = core.NonlinearBinding('physical_nonlinear_optimizer.solve_bounded_nonlinear', core.SOURCE_SHA256,
        core.VENDOR_SOURCE_SHA256, 'a'*64, core.RUNTIME_EPOCH, core.POLICY)
    budget = core.NonlinearBudget(monotonic()-1., 200, 805306368, 1000000, 'b'*64)
    result = solve_nonlinear(obj, np.zeros(7), np.full(7, 10.), np.zeros(7), budget=budget, binding=binding)
    assert result['status'] != 'converged' and result['reason'] == 'wall_cap' and result['q'] is None
    assert result['trace']['magnetic_norm_proofs'] == []


@pytest.mark.parametrize('beta', [.1, 3.])
def test_actual_nonzero_partition_history_lossless_beta_once(physical, beta):
    from magnetic_calibration import descriptor, fit_partition
    from magnetic_result_bundle import _encode_history, _decode_history, _validate_history
    obj, _, noise, _ = make(physical)
    sim = physical[0]
    geometry = dict(origin_m=np.array(control.control.ORIGIN),
        hx_m=np.array(control.control.WIDTHS[0]), hy_m=np.array(control.control.WIDTHS[1]),
        hz_m=np.array(control.control.WIDTHS[2]), active=sim.active_cells.copy())
    prior = {key: descriptor(value) for key, value in dict(
        reference_si=.01*control.control.QREF, lower_si=np.zeros(7),
        upper_si=np.full(7, .1), start_si=np.zeros(7),
        lengths_m=np.array(control.control.LENGTHS)).items()}
    binding = core.NonlinearBinding('physical_nonlinear_optimizer.solve_bounded_nonlinear', core.SOURCE_SHA256,
        core.VENDOR_SOURCE_SHA256, 'a'*64, core.RUNTIME_EPOCH, core.POLICY)
    result = fit_partition(obj.operator, geometry, prior, obj.base.observed, noise, beta, 'l2',
        binding=binding, deadline=monotonic()+120., admitted_bytes=1000000,
        allocation_sha256='b'*64, source_inventory_sha256='a'*64)
    history = [dict(candidate='b00-l2', fold=0, **row) for row in result['history']]
    assert len(history) > 1 and history[0]['phi_regularizer'] > 0.
    # Actual native history remains exportable even if a stricter fit gate fails.
    assert result['status'] in ('converged', 'failed')
    assert all(row['objective'] == row['phi_d']+beta*row['phi_regularizer'] for row in history)
    assert history[0]['objective'] != history[0]['phi_d']+beta**2*history[0]['phi_regularizer']
    candidates = [dict(id=f'b{i:02d}-{p}', beta=beta, penalty='l2' if p == 'l2' else 'sparse_smallness')
                  for i in range(8) for p in ('l2', 'sparse')]
    _validate_history(history, candidates, allow_empty=False)
    assert _decode_history(_encode_history(history)) == history


@pytest.mark.parametrize('epsilon', [0., .1, .05, .025, .0125, .00625, .003125, .0015625, .001])
def test_literal_nonlinear_history_operand_and_corruption_refusal(physical, epsilon):
    from magnetic_calibration import recorded_objective_terms
    from magnetic_survey_json import InputError
    base, _, _, _, _, _ = control.make(physical, 'exact_total_anomaly_nT', False,
        'sparse_smallness' if epsilon else 'l2', epsilon)
    obj = MagneticNonlinearObjective(base, control.control.Q)
    q = control.control.Q.copy()
    native = obj.components(q)
    trace = {k: np.array([native[k]]) for k in ('phi_d', 'phi_m', 'phi_engine')}
    trace['models_q'] = np.array([q])
    terms = recorded_objective_terms(obj, trace, 0, nonlinear=True)
    assert terms['phi_regularizer'] == float(obj.regularizer.vendor(q)) > 0.
    assert terms['objective'] == terms['phi_d']+obj.beta*terms['phi_regularizer']
    trace['phi_m'][0] = np.nextafter(trace['phi_m'][0], np.inf)
    with pytest.raises(InputError, match='weighted regularizer operand mismatch'):
        recorded_objective_terms(obj, trace, 0, nonlinear=True)
    trace['phi_m'][0] = native['phi_m']
    trace['phi_engine'][0] = np.nextafter(trace['phi_engine'][0], np.inf)
    with pytest.raises(InputError, match='Actual objective terms mismatch'):
        recorded_objective_terms(obj, trace, 0, nonlinear=True)
