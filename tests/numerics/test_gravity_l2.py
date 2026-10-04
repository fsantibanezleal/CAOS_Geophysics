"""Authored tiny engine/J/volume/noise/optimizer controls, never field truth."""

from copy import deepcopy
import builtins
import hashlib
import importlib.metadata
import json
from pathlib import Path
from types import SimpleNamespace
import socket
import subprocess

import choclo
import numpy as np
import pytest
import scipy.linalg as la
import scipy.sparse as sp
from scipy.optimize import lsq_linear

import gravity_forward as forward
import gravity_l2 as l2
import gravity_survey_l2 as survey


def tiny():
    origin = np.array([-140., -180., -260.])
    widths = [np.array([40., 70.]), np.array([30., 50., 90.]), np.array([60., 110.])]
    active = np.zeros(12, dtype=bool)
    active[[0, 2, 3, 7, 11]] = True
    mesh = dict(zip(('origin_m', 'hx_m', 'hy_m', 'hz_m', 'active'), (origin, *widths, active)))
    points = np.array([[0., 0., 100.], [230., -50., 40.], [-400., 60., -350.], [70., 260., -150.]])
    # Explicit nested x-fast prism traversal, independent of production geometry.
    edges = [o + np.r_[0., np.cumsum(w)] for o, w in zip(origin, widths)]
    bounds = []
    for k in range(2):
        for j in range(3):
            for i in range(2):
                if active[i + 2*j + 6*k]:
                    bounds.append([edges[0][i], edges[0][i+1], edges[1][j], edges[1][j+1], edges[2][k], edges[2][k+1]])
    bounds = np.array(bounds)
    g_rho = np.array([[choclo.prism.gravity_u(*point, *box, 1.) * 1e5 for box in bounds] for point in points])
    truth = np.array([400., -600., 900., -300., 1200.])
    background = np.array([.002, -.003, 0., .001])
    observations = g_rho @ truth + background
    req = {'mesh': mesh, 'frame': dict(forward.FRAME), 'engine': forward.ENGINE,
           'stations': {'receivers_m': points}, 'background_mgal': background}
    prior = {'lower_kg_m3': np.full(5, -1500.), 'upper_kg_m3': np.full(5, 1500.), 'start_kg_m3': np.zeros(5),
             'reference_kg_m3': np.array([10., -20., 30., -40., 50.]), 'density_scale_kg_m3': 1000.,
             'lengths_m': np.array([80., 90., 70.]), 'reference_in_smooth': True, 'spatial_weights': 'none',
             'basis': 'Frozen tiny control', 'geometry_sha256': 'a' * 64}
    return req, observations, prior, bounds, g_rho


def independent_r(bounds, lengths, scale):
    volume = np.prod(bounds[:, 1::2] - bounds[:, ::2], axis=1)
    centre = (bounds[:, ::2] + bounds[:, 1::2]) / 2
    norm = volume.sum() * scale**2
    rows = [np.eye(len(bounds))[i] * np.sqrt(volume[i] / norm) for i in range(len(bounds))]
    # Pairwise BOTH-active shared faces, no exterior or inactive bridges.
    for axis in range(3):
        others = [a for a in range(3) if a != axis]
        for i in range(len(bounds)):
            for j in range(len(bounds)):
                same_cross = all(np.array_equal(bounds[i, [2*a, 2*a+1]], bounds[j, [2*a, 2*a+1]]) for a in others)
                if same_cross and bounds[i, 2*axis+1] == bounds[j, 2*axis]:
                    row = np.zeros(len(bounds))
                    weight = lengths[axis] * np.sqrt((volume[i]+volume[j]) / (2*norm)) / (centre[j, axis]-centre[i, axis])
                    row[i], row[j] = -weight, weight
                    rows.append(row)
    return np.array(rows)


def noise(kind='full_covariance'):
    return {'kind': kind, 'values': .0001 * (.8*np.eye(4)+.2*np.ones((4, 4))) if kind == 'full_covariance'
            else np.full(4, .01)}


@pytest.mark.parametrize('kind', ['diagonal_sd', 'full_covariance'])
def test_real_engine_forward_and_geometry_identity(kind):
    req, d, prior, bounds, oracle = tiny()
    problem = l2._build_problem(req, d, noise(kind), prior, np.arange(4, dtype=np.int64), .01)
    assert type(problem['simulation']) is forward.gravity.simulation.Simulation3DIntegral
    assert type(problem['misfit']) is l2.data_misfit.L2DataMisfit
    assert type(problem['regularization']) is l2.regularization.WeightedLeastSquares
    np.testing.assert_array_equal(problem['geometry']['active_cell_bounds_m'], bounds)
    np.testing.assert_allclose(problem['simulation'].G / 1000, oracle, rtol=1e-7, atol=1e-10)
    assert problem['beta_engine'] == .04
    q = np.array([.4, -.6, .9, -.3, 1.2])
    predicted = problem['simulation'].dpred(q) + req['background_mgal']
    np.testing.assert_allclose(predicted, d, rtol=1e-7, atol=1e-10)
    np.testing.assert_allclose(problem['misfit'].residual(q), predicted-d, rtol=1e-10, atol=1e-12)


def test_covariance_whitening_hessian_and_marginals():
    req, d, prior, bounds, oracle = tiny()
    problem = l2._build_problem(req, d, noise(), prior, np.arange(4, dtype=np.int64), .01)
    w = problem['misfit'].W
    assert type(w) is sp.csr_matrix
    np.testing.assert_array_equal(w.toarray(), w.toarray().T)
    c = noise()['values']
    np.testing.assert_allclose(w @ c @ w.T, np.eye(4), rtol=1e-10, atol=1e-12)
    q, v = np.full(5, .1), np.array([1., -.3, .4, -.6, .2])
    g = problem['simulation'].G
    expected = 2*g.T @ la.solve(c, g @ v, assume_a='pos')
    np.testing.assert_allclose(problem['misfit'].deriv2(q, v), expected, rtol=1e-10, atol=1e-12)
    chol_w = la.solve_triangular(la.cholesky(c, lower=True), np.eye(4), lower=True)
    problem['misfit'].W = sp.csr_matrix(chol_w)
    assert not np.allclose(problem['misfit'].deriv2(q, v), expected, rtol=1e-6, atol=1e-12)
    # Expected negative: pinned triangular W disagrees; production cannot use it.
    problem['misfit'].W = w
    selected = np.array([0, 2, 3])
    marginal_w = l2._weights({'kind': 'full_covariance', 'values': c}, selected)
    principal = c[np.ix_(selected, selected)]
    np.testing.assert_allclose(marginal_w @ principal @ marginal_w.T, np.eye(3), rtol=1e-10, atol=1e-12)


@pytest.mark.parametrize('kind', ['diagonal_sd', 'full_covariance'])
def test_objective_regularization_and_physical_derivatives(kind):
    req, d, prior, bounds, oracle = tiny()
    problem = l2._build_problem(req, d, noise(kind), prior, np.arange(4, dtype=np.int64), .1)
    reg, misfit = problem['regularization'], problem['misfit']
    r = independent_r(bounds, prior['lengths_m'], 1.)
    q, v = np.array([.1, -.2, .3, -.4, .5]), np.array([.2, .3, -.2, .4, -.1])
    delta = q - prior['reference_kg_m3']/1000
    w, g = misfit.W.toarray(), problem['simulation'].G
    residual = g @ q + req['background_mgal'] - d
    expected_d, expected_m = np.dot(w@residual, w@residual), np.dot(r@delta, r@delta)
    np.testing.assert_allclose([misfit(q), reg(q)], [expected_d, expected_m], rtol=1e-10, atol=1e-12)
    gradient = 2*g.T@w.T@w@residual + 2*problem['beta_engine']*r.T@r@delta
    hess_v = 2*g.T@w.T@w@g@v + 2*problem['beta_engine']*r.T@r@v
    np.testing.assert_allclose(misfit.deriv(q)+problem['beta_engine']*reg.deriv(q), gradient, rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(misfit.deriv2(q, v)+problem['beta_engine']*reg.deriv2(q, v), hess_v, rtol=1e-10, atol=1e-12)
    def objective(x): return misfit(x) + problem['beta_engine']*reg(x)
    errors = []
    for step in (1e-2, 1e-3, 1e-4):
        finite = (objective(q+step*v)-objective(q-step*v))/(2*step)
        errors.append(abs(finite-gradient@v)/max(1., abs(gradient@v)))
    assert any(errors[i] <= 1e-6 and errors[i+1] <= 1e-6 for i in range(2)), errors
    rho = q*1000
    physical_fd = (objective((rho+v)/1000)-objective((rho-v)/1000))/2
    np.testing.assert_allclose(physical_fd, gradient@v/1000, rtol=1e-6, atol=1e-12)
    np.testing.assert_allclose((misfit.deriv((rho+v)/1000)+problem['beta_engine']*reg.deriv((rho+v)/1000)
                               -misfit.deriv((rho-v)/1000)-problem['beta_engine']*reg.deriv((rho-v)/1000))/2000,
                              hess_v/1e6, rtol=1e-6, atol=1e-12)


@pytest.mark.parametrize('kind', ['nonsymmetric', 'indefinite', 'ill_conditioned', 'zero_sd', 'nonfinite'])
def test_invalid_noise_no_jitter_or_diagonal_fallback(kind):
    spec = noise()
    if kind == 'nonsymmetric': spec['values'][0, 1] += 1e-8
    if kind == 'indefinite': spec['values'][0, 0] = -1.
    if kind == 'ill_conditioned': spec['values'] = np.diag([1., 1., 1., 1e-10])
    if kind == 'zero_sd': spec = {'kind': 'diagonal_sd', 'values': np.array([0., .01, .01, .01])}
    if kind == 'nonfinite': spec['values'][0, 0] = np.nan
    before = deepcopy(spec)
    with pytest.raises(ValueError): l2._weights(spec, np.arange(4, dtype=np.int64))
    np.testing.assert_array_equal(spec['values'], before['values'])


@pytest.mark.parametrize('kind', ['coupled_condition_1e4', 'diagonal_condition_1e8'])
def test_frozen_covariance_conditioning_controls(kind):
    basis = np.array([[1., 1., 1., 1.], [1., -1., 1., -1.],
                      [1., 1., -1., -1.], [1., -1., -1., 1.]]) / 2
    covariance = (basis @ np.diag([1e-4, .01, .1, 1.]) @ basis.T if kind == 'coupled_condition_1e4'
                  else np.diag([1e-8, 1e-5, .01, 1.]))
    before = covariance.copy()
    w = l2._weights({'kind': 'full_covariance', 'values': covariance}, np.arange(4, dtype=np.int64)).toarray()
    residual = np.array([.2, -.3, .4, -.1])
    tol = 1e-10 if kind == 'coupled_condition_1e4' else 1e-7
    np.testing.assert_allclose(w @ covariance @ w.T, np.eye(4), rtol=tol, atol=1e-12)
    chol = la.cholesky(covariance, lower=True)
    independent = la.solve_triangular(chol, residual, lower=True)
    np.testing.assert_allclose(np.dot(w@residual, w@residual), np.dot(independent, independent), rtol=tol, atol=1e-12)
    np.testing.assert_array_equal(covariance, before)


def test_nonuniform_full_active_stencil_all_directions():
    req, _, prior, _, _ = tiny()
    req['mesh']['active'][:] = True
    a = 12
    for key in ('lower_kg_m3', 'upper_kg_m3', 'start_kg_m3', 'reference_kg_m3'):
        prior[key] = np.full(a, prior[key][0])
    prior['reference_kg_m3'] = np.linspace(-40., 50., a)
    edges = [o + np.r_[0., np.cumsum(req['mesh'][key])]
             for o, key in zip(req['mesh']['origin_m'], ('hx_m', 'hy_m', 'hz_m'))]
    bounds = np.array([[edges[0][i], edges[0][i+1], edges[1][j], edges[1][j+1], edges[2][k], edges[2][k+1]]
                       for k in range(2) for j in range(3) for i in range(2)])
    problem = l2._build_problem(req, np.zeros(4), noise(), prior, np.arange(4, dtype=np.int64), .01)
    independent = independent_r(bounds, prior['lengths_m'], 1.)
    ref = prior['reference_kg_m3']/1000
    q = np.linspace(-.5, .8, a)
    np.testing.assert_allclose(problem['regularization'](q), np.linalg.norm(independent@(q-ref))**2,
                               rtol=1e-10, atol=1e-12)
    assert problem['regularization'](ref) == 0.
    for direction in (np.ones(a), np.tile([-1., 1.], 6), np.repeat([-1., 0., 1.], 4)):
        np.testing.assert_allclose(problem['regularization'].deriv2(q, direction),
                                   2*independent.T@independent@direction, rtol=1e-10, atol=1e-12)


def test_private_compact_fit_rows_never_create_sealed_values():
    req, d, prior, _, oracle = tiny()
    supplied = np.array([0, 2, 3], dtype=np.int64)
    fit = np.array([2, 3], dtype=np.int64)
    compact_d = d[supplied]
    compact_cov = noise()['values'][np.ix_(supplied, supplied)]
    spec = {'kind': 'full_covariance', 'values': compact_cov}
    problem = l2._build_problem(req, compact_d, spec, prior, fit, .01, observation_rows=supplied)
    np.testing.assert_array_equal(problem['rows'], fit)
    np.testing.assert_array_equal(problem['observations'], d[fit])
    np.testing.assert_allclose(problem['simulation'].G/1000., oracle[fit], rtol=1e-7, atol=1e-10)
    w = problem['misfit'].W.toarray()
    principal = compact_cov[1:, 1:]
    np.testing.assert_allclose(w@principal@w.T, np.eye(2), rtol=1e-10, atol=1e-12)
    q = np.array([.4, -.6, .9, -.3, 1.2])
    np.testing.assert_allclose(problem['misfit'].residual(q), oracle[fit]@(q*1000)+req['background_mgal'][fit]-d[fit],
                               rtol=1e-10, atol=1e-12)
    # Poison the supplied development row that is NOT part of this fit.
    compact_d[0] += 1000.
    changed = l2._build_problem(req, compact_d, spec, prior, fit, .01, observation_rows=supplied)
    np.testing.assert_array_equal(problem['observations'], changed['observations'])
    np.testing.assert_array_equal(problem['misfit'].deriv(q), changed['misfit'].deriv(q))
    assert problem['beta_engine'] == .02


@pytest.mark.parametrize('bad', ['missing', 'duplicate', 'unordered', 'length'])
def test_private_compact_identity_rejects_before_engine(monkeypatch, bad):
    req, d, prior, _, _ = tiny()
    supplied = np.array([0, 2, 3], dtype=np.int64)
    fit = np.array([2, 3], dtype=np.int64)
    if bad == 'missing': fit = np.array([1, 2], dtype=np.int64)
    if bad == 'duplicate': supplied[1] = supplied[0]
    if bad == 'unordered': supplied = supplied[::-1].copy()
    if bad == 'length': supplied = supplied[:2]
    def deny(*args, **kwargs): raise AssertionError('fit engine before compact identity rejected')
    monkeypatch.setattr(forward, 'forward_gravity', deny)
    with pytest.raises(ValueError):
        l2._build_problem(req, d[[0, 2, 3]], {'kind': 'diagonal_sd', 'values': np.full(3, .01)},
                          prior, fit, .01, observation_rows=supplied)


@pytest.mark.parametrize('bound,start', [(1500., 0.), (1500., 100.), (1500., -100.), (250., 0.)])
def test_bounded_l2_independent_bvls_and_kkt(bound, start):
    req, d, prior, bounds, oracle = tiny()
    prior['lower_kg_m3'][:] = -bound
    prior['upper_kg_m3'][:] = bound
    prior['start_kg_m3'][:] = start
    problem = l2._build_problem(req, d, noise(), prior, np.arange(4, dtype=np.int64), .01)
    result = l2._solve_partition(problem, prior)
    assert result['status'] == 'converged', result
    assert result['reason'] in ('kkt_stable', 'absolute_stationary')
    assert result['kkt_normalized'] <= 1e-5
    r = independent_r(bounds, prior['lengths_m'], 1.)
    chol = la.cholesky(noise()['values'], lower=True)
    w = la.solve_triangular(chol, np.eye(4), lower=True)
    a = np.vstack([w @ (oracle*1000), np.sqrt(problem['beta_engine'])*r])
    target = np.r_[w@(d-req['background_mgal']), np.sqrt(problem['beta_engine'])*r@(prior['reference_kg_m3']/1000)]
    oracle_solve = lsq_linear(a, target, bounds=(-bound/1000, bound/1000), method='bvls', lsq_solver='exact',
                              tol=1e-12, max_iter=1000)
    assert oracle_solve.success
    density = result['model_kg_m3']
    assert np.all(density >= -bound) and np.all(density <= bound)
    assert np.max(np.abs(density - oracle_solve.x*1000))/max(1., np.max(np.abs(oracle_solve.x*1000))) <= 1e-5
    oracle_prediction = oracle @ (oracle_solve.x*1000) + req['background_mgal']
    assert np.max(np.abs(result['predicted_mgal']-oracle_prediction))/max(1., np.max(np.abs(oracle_prediction))) <= 1e-5
    np.testing.assert_allclose(result['phi_engine'], 2*oracle_solve.cost, rtol=1e-5, atol=1e-12)
    np.testing.assert_array_equal(result['residual_observed_minus_predicted_mgal'], d-result['predicted_mgal'])
    if bound == 250.: assert np.any(np.isclose(np.abs(oracle_solve.x), .25, rtol=0., atol=1e-12))
    trace = result['trace']
    assert len(trace['phi_engine']) == result['iterations']+1
    np.testing.assert_array_equal(trace['models_kg_m3'][-1], density)
    for rho, pd, pm in zip(trace['models_kg_m3'], trace['phi_d'], trace['phi_m']):
        np.testing.assert_allclose([pd, pm], [problem['misfit'](rho/1000), problem['regularization'](rho/1000)],
                                   rtol=1e-10, atol=1e-12)
    assert np.all(np.diff(trace['phi_engine']) <= 1e-12*np.maximum(1., np.abs(trace['phi_engine'][:-1])))
    assert np.all(trace['cg_counts'] <= 200) and np.all(trace['line_search_counts'] <= 20)
    assert not density.flags.writeable


def test_private_optimizer_delegates_official_algorithms_and_fixed_parameters():
    req, d, prior, _, _ = tiny()
    problem = l2._build_problem(req, d, noise(), prior, np.arange(4, dtype=np.int64), .01)
    opt = l2._RecordedProjectedGNCG(problem, prior, l2.monotonic()+120.)
    for name in ('projection', 'scaleSearchDirection', 'minimize', 'activeSet', 'bindingSet'):
        assert getattr(type(opt), name) is getattr(l2.optimization.ProjectedGNCG, name)
    assert type(opt).findSearchDirection is not l2.optimization.ProjectedGNCG.findSearchDirection
    expected = {'maxIter': 200, 'maxIterLS': 20, 'cg_maxiter': 200, 'cg_rtol': 1e-6, 'cg_atol': 0.,
                'step_active_set': True, 'active_set_grad_scale': .01, 'LSreduction': 1e-4,
                'LSshorten': .5, 'use_WolfeCurvature': False, 'require_decrease': True, 'maxStep': np.inf}
    for name, value in expected.items(): assert getattr(opt, name) == value
    np.testing.assert_array_equal(opt.lower, prior['lower_kg_m3']/1000.)
    np.testing.assert_array_equal(opt.upper, prior['upper_kg_m3']/1000.)


def test_private_optimizer_nonfinite_inverse_diagonal_rejects_before_run(monkeypatch):
    req, d, prior, _, _ = tiny()
    problem = l2._build_problem(req, d, noise(), prior, np.arange(4, dtype=np.int64), .01)
    # Inject a finite positive but unrepresentably invertible Hessian diagonal.
    # This is an arithmetic guard, not a claim about a naturally observed survey.
    problem['misfit'].W = sp.diags(np.full(4, 1e-160), format='csr')
    monkeypatch.setattr(problem['regularization'], 'deriv2', lambda q: sp.diags(np.full(5, 1e-320)))
    def deny(*args, **kwargs): raise AssertionError('nonfinite preconditioner reached official run')
    monkeypatch.setattr(l2.inversion.BaseInversion, 'run', deny)
    with pytest.raises(ValueError, match='preconditioner'):
        l2._solve_partition(problem, prior)


@pytest.mark.parametrize('failure', ['cg_residual', 'nonfinite_direction', 'engine_error', 'line_search'])
def test_private_optimizer_injected_failures_never_claim_convergence(monkeypatch, failure):
    # Bounded diagnostic fault injection, NOT naturally occurring physics results.
    req, d, prior, _, _ = tiny()
    problem = l2._build_problem(req, d, noise(), prior, np.arange(4, dtype=np.int64), .01)
    official_direction = l2.optimization.ProjectedGNCG.findSearchDirection
    seen = {'cg': 0, 'ls': 0}
    def direction(opt):
        seen['cg'] += 1
        if failure == 'engine_error': raise RuntimeError('injected official engine failure')
        step = official_direction(opt)
        if failure == 'cg_residual':
            opt.cg_abs_resid = max(opt.cg_rtol*opt._initial_free_residual, opt.cg_atol)+1.
        if failure == 'nonfinite_direction': step[0] = np.nan
        return step
    monkeypatch.setattr(l2.optimization.ProjectedGNCG, 'findSearchDirection', direction)
    official_certificate = l2._RecordedProjectedGNCG._certify_trial
    def certificate(opt):
        seen['ls'] += 1
        if failure == 'line_search':
            # The cpu-4 predicate replaces native absolute-Phi stoppers.
            # Inject unavailability at its real owned seam, not an unused vendor hook.
            r = l2.precision._record(int(opt.iter),int(opt.iterLS),opt.f,opt._LS_ft)
            r.update(cause='range_unsupported',displacement_inf_q=float(np.max(np.abs(opt._LS_xt-opt.xc))))
            return r
        return official_certificate(opt)
    monkeypatch.setattr(l2._RecordedProjectedGNCG, '_certify_trial', certificate)
    result = l2._solve_partition(problem, prior)
    reason = {'cg_residual': 'cg_cap', 'nonfinite_direction': 'nonfinite',
              'engine_error': 'engine_error', 'line_search': 'line_search_failed'}[failure]
    assert seen['cg'] == 1
    assert result['reason'] == reason
    assert result['status'] == ('failed' if failure in ('nonfinite_direction', 'engine_error') else 'nonconverged')
    assert result['iterations'] == 0 and len(result['trace']['phi_engine']) == 1
    np.testing.assert_array_equal(result['model_kg_m3'], prior['start_kg_m3'])
    assert result['failed_trial']['reason'] == reason
    if failure == 'line_search':
        assert seen['ls'] == 20
        assert len(problem['optimizer_evidence']['trial_objectives']) == 20
    else:
        assert seen['ls'] == 0


def test_private_optimizer_terminal_return_tamper_is_not_success(monkeypatch):
    req, d, prior, _, _ = tiny()
    problem = l2._build_problem(req, d, noise(), prior, np.arange(4, dtype=np.int64), .01)
    official_run = l2.inversion.BaseInversion.run
    def tampered(runner, start):
        terminal = official_run(runner, start)
        return terminal + .001
    monkeypatch.setattr(l2.inversion.BaseInversion, 'run', tampered)
    result = l2._solve_partition(problem, prior)
    assert result['status'] == 'failed' and result['reason'] == 'state_mismatch'
    np.testing.assert_array_equal(result['trace']['models_kg_m3'][-1], result['model_kg_m3'])


def test_private_optimizer_deadline_precedence_after_failed_line_search(monkeypatch):
    req, d, prior, _, _ = tiny()
    problem = l2._build_problem(req, d, noise(), prior, np.arange(4, dtype=np.int64), .01)
    clock = [0.]
    monkeypatch.setattr(l2, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(l2.precision, 'monotonic', lambda: clock[0])
    official_ls = l2.optimization.ProjectedGNCG.modifySearchDirection
    def rejected(opt, direction):
        trial, _ = official_ls(opt, direction)
        clock[0] = 121.
        return trial, False
    monkeypatch.setattr(l2.optimization.ProjectedGNCG, 'modifySearchDirection', rejected)
    result = l2._solve_partition(problem, prior)
    assert result['status'] == 'nonconverged' and result['reason'] == 'line_search_failed'
    assert result['wall_seconds'] == 121.


@pytest.mark.parametrize('failure', ['exception', 'arithmetic', 'nonfinite'])
def test_private_optimizer_prediction_export_failure_retains_record(monkeypatch, failure):
    req, d, prior, _, _ = tiny()
    problem = l2._build_problem(req, d, noise(), prior, np.arange(4, dtype=np.int64), .01)
    official_run = l2.inversion.BaseInversion.run
    official_prediction = problem['simulation'].dpred
    complete = [False]
    def run(runner, start):
        terminal = official_run(runner, start)
        complete[0] = True
        return terminal
    def prediction(*args, **kwargs):
        if complete[0]:
            if failure == 'exception': raise RuntimeError('injected export engine failure')
            if failure == 'arithmetic': raise FloatingPointError('injected export arithmetic failure')
            return np.full(4, np.inf)
        return official_prediction(*args, **kwargs)
    monkeypatch.setattr(l2.inversion.BaseInversion, 'run', run)
    monkeypatch.setattr(problem['simulation'], 'dpred', prediction)
    result = l2._solve_partition(problem, prior)
    assert result['status'] == 'failed'
    assert result['reason'] == ('engine_error' if failure == 'exception' else 'nonfinite')
    assert result['predicted_mgal'] is None and result['residual_observed_minus_predicted_mgal'] is None
    assert len(result['trace']['phi_engine']) >= 1
    assert np.isfinite(result['model_kg_m3']).all()


def test_private_optimizer_injected_iteration_cap_not_native_tolerance_success(monkeypatch):
    req, d, prior, _, _ = tiny()
    problem = l2._build_problem(req, d, noise(), prior, np.arange(4, dtype=np.int64), .01)
    official_record = l2._RecordedProjectedGNCG._record
    def capped(opt):
        absolute, kkt = official_record(opt)
        assert absolute > 1e-12 and kkt > 1e-5
        opt.f0 = opt.f_last = opt.f
        opt.x_last = opt.xc.copy()  # Complete native diagnostic-print state.
        opt.iter = 200  # Diagnostic injection, NOT a claim of200 actual accepted steps.
        return absolute, kkt
    monkeypatch.setattr(l2._RecordedProjectedGNCG, '_record', capped)
    result = l2._solve_partition(problem, prior)
    assert result['status'] == 'nonconverged' and result['reason'] == 'iteration_cap'
    assert result['iterations'] == 0 and result['failed_trial']['iteration'] == 200


def test_pinned_stopping_null_and_terminal_state(monkeypatch):
    req, _, prior, _, _ = tiny()
    prior['reference_kg_m3'][:] = prior['start_kg_m3'][:] = 0.
    problem = l2._build_problem(req, req['background_mgal'], noise(), prior, np.arange(4, dtype=np.int64), .01)
    def deny(*args, **kwargs): raise AssertionError('stationary null entered CG')
    with monkeypatch.context() as guard:
        guard.setattr(l2.optimization.ProjectedGNCG, 'findSearchDirection', deny)
        result = l2._solve_partition(problem, prior)
    assert result['status'] == 'converged' and result['reason'] == 'absolute_stationary'
    assert result['iterations'] == 0 and len(result['trace']['phi_engine']) == 1
    assert result['phi_d'] == result['phi_m'] == result['phi_engine'] == result['wrms'] == 0.
    np.testing.assert_array_equal(result['model_kg_m3'], np.zeros(5))
    expired = l2._solve_partition(problem, prior, deadline=l2.monotonic()-1)
    assert expired['status'] == 'nonconverged' and expired['reason'] == 'wall_cap'


def test_nonstationary_zero_free_set_uses_approved_release():
    req, d, prior, _, _ = tiny()
    prior['start_kg_m3'][:] = prior['lower_kg_m3']
    problem = l2._build_problem(req, d, noise(), prior, np.arange(4, dtype=np.int64), .01)
    result = l2._solve_partition(problem, prior)
    assert result['status'] == 'converged'
    assert result['iterations'] > 0
    np.testing.assert_array_equal(result['trace']['models_kg_m3'][0], prior['start_kg_m3'])
    assert problem['optimizer_evidence']['direction_kinds'][0] == 1


def six_cell_control(kind, bound, start='zero'):
    """MAIN's retained physical specification, independently assembled in tests.

    This is not a second author-independent control or field data. Direct Choclo,
    explicit pairwise R and separate Cholesky avoid production G/W/R reuse.
    """
    origin = np.array([-320., -140., -510.])
    widths = [np.array([70., 110., 90.]), np.array([80., 140.]), np.array([120., 60.])]
    active = np.zeros(12, dtype=bool)
    active[[0, 1, 4, 6, 9, 11]] = True
    edges = [o + np.r_[0., np.cumsum(w)] for o, w in zip(origin, widths)]
    boxes = np.array([[edges[0][i], edges[0][i+1], edges[1][j], edges[1][j+1], edges[2][k], edges[2][k+1]]
                      for k in range(2) for j in range(2) for i in range(3) if active[i+3*j+6*k]])
    points = np.array([[-100., 50., 140.], [500., -450., 80.], [-450., 300., -900.],
                       [20., -200., 350.], [100., 200., 220.]])
    jacobian = np.array([[choclo.prism.gravity_u(*p, *b, 1.)*1e5 for b in boxes] for p in points])
    background = np.array([.002, -.003, .001, .004, -.002])
    observed = jacobian@np.array([250., -450., 600., -800., 300., 1000.])+background
    reference = np.array([10., -15., 25., -40., 5., 0.])
    starts = {'zero': np.zeros(6), 'all_lower': np.full(6, -bound), 'all_upper': np.full(6, bound),
              'lower_upper': np.tile([-bound, bound], 3), 'upper_lower': np.tile([bound, -bound], 3),
              'lower_reference': np.where(np.arange(6) % 2 == 0, -bound, reference),
              'upper_reference': np.where(np.arange(6) % 2 == 0, bound, reference)}
    prior = {'lower_kg_m3': np.full(6, -bound), 'upper_kg_m3': np.full(6, bound),
             'start_kg_m3': starts[start], 'reference_kg_m3': reference, 'density_scale_kg_m3': 750.,
             'lengths_m': np.array([60., 110., 75.]), 'reference_in_smooth': True, 'spatial_weights': 'none'}
    covariance = .005**2*(np.eye(5) if kind == 'diagonal_sd' else .65*np.eye(5)+.35*np.ones((5, 5)))
    noise_spec = {'kind': kind, 'values': np.full(5, .005) if kind == 'diagonal_sd' else covariance}
    request = {'frame': dict(forward.FRAME), 'engine': forward.ENGINE,
               'mesh': dict(zip(('origin_m', 'hx_m', 'hy_m', 'hz_m', 'active'), (origin, *widths, active))),
               'stations': {'receivers_m': points}, 'background_mgal': background}
    independent = independent_r(boxes, prior['lengths_m'], .750)
    whitening = la.solve_triangular(la.cholesky(covariance, lower=True), np.eye(5), lower=True)
    augmented = np.vstack((whitening@(jacobian*1000.), np.sqrt(.05)*independent))
    target = np.r_[whitening@(observed-background), np.sqrt(.05)*independent@(reference/1000.)]
    return request, observed, noise_spec, prior, jacobian, augmented, target


def assert_six_cell_optimum(kind, bound, start):
    req, observed, spec, prior, jacobian, augmented, target = six_cell_control(kind, bound, start)
    problem = l2._build_problem(req, observed, spec, prior, np.arange(5, dtype=np.int64), .01)
    result = l2._solve_partition(problem, prior)
    oracle = lsq_linear(augmented, target, bounds=(-bound/1000., bound/1000.),
                        method='bvls', lsq_solver='exact', tol=1e-12, max_iter=1000)
    assert oracle.success
    assert result['status'] == 'converged', (kind, bound, start, result['reason'], result['kkt_normalized'])
    q = result['model_kg_m3']/1000.
    assert np.all(q >= -bound/1000.) and np.all(q <= bound/1000.)
    model_relative = np.linalg.norm(q-oracle.x)/max(1., np.linalg.norm(oracle.x))
    objective_relative = abs(np.linalg.norm(augmented@q-target)**2-2*oracle.cost)/max(1., 2*oracle.cost)
    prediction_absolute = np.max(np.abs(jacobian@((q-oracle.x)*1000.)))
    assert model_relative <= 1e-3 and objective_relative <= 1e-6 and prediction_absolute <= 1e-6
    assert np.max(np.abs((q-oracle.x)*1000.))/max(1., np.max(np.abs(oracle.x*1000.))) <= 1e-5
    assert prediction_absolute/max(1., np.max(np.abs(jacobian@(oracle.x*1000.)))) <= 1e-5
    initial_g = 2*augmented.T@(augmented@(prior['start_kg_m3']/1000.)-target)
    gradient = 2*augmented.T@(augmented@q-target)
    projected = gradient.copy()
    projected[(q <= -bound/1000.+1e-12) & (gradient > 0)] = 0.
    projected[(q >= bound/1000.-1e-12) & (gradient < 0)] = 0.
    assert np.linalg.norm(projected, ord=np.inf)/max(1., np.linalg.norm(initial_g, ord=np.inf)) <= 1e-5
    trace, evidence = result['trace'], problem['optimizer_evidence']
    np.testing.assert_array_equal(trace['models_kg_m3'][0], prior['start_kg_m3'])
    for rho, phi in zip(trace['models_kg_m3'], trace['phi_engine']):
        np.testing.assert_allclose(phi, np.linalg.norm(augmented@(rho/1000.)-target)**2, rtol=1e-10, atol=1e-12)
    assert np.all(np.diff(trace['phi_engine']) <= 1e-12*np.maximum(1., abs(trace['phi_engine'][:-1])))
    np.testing.assert_array_equal(result['residual_observed_minus_predicted_mgal'], observed-result['predicted_mgal'])
    assert evidence['direction_kinds'].shape == (result['iterations'],)
    assert not evidence['direction_kinds'].flags.writeable
    assert np.all(trace['cg_counts'][evidence['direction_kinds'] == 1] == 0)
    assert np.all(trace['line_search_counts'] <= 20) and result['iterations'] <= 200
    return result, problem


@pytest.mark.parametrize('kind', ['diagonal_sd', 'full_covariance'])
@pytest.mark.parametrize('bound', [1500., 75.])
def test_independent_six_cell_bvls_tight_and_wide(kind, bound):
    assert_six_cell_optimum(kind, bound, 'zero')


@pytest.mark.parametrize('kind', ['diagonal_sd', 'full_covariance'])
@pytest.mark.parametrize('bound', [75., 1500.])
@pytest.mark.parametrize('start', ['all_lower', 'all_upper', 'lower_upper', 'upper_lower',
                                  'lower_reference', 'upper_reference'])
def test_independent_six_cell_bound_starts(kind, bound, start):
    assert_six_cell_optimum(kind, bound, start)


def diagnostic_opt(monkeypatch, q, g, inverse, lower, upper):
    """Trusted bounded arithmetic injection, not a physical engine substitute."""
    q, g, inverse, lower, upper = (np.array(x, dtype=float) for x in (q, g, inverse, lower, upper))
    prior = {'lower_kg_m3': lower*1000., 'upper_kg_m3': upper*1000.}
    opt = l2._RecordedProjectedGNCG({}, prior, l2.monotonic()+120.)
    opt.xc, opt.g, opt.f, opt.iter = q, g, 1., 0
    opt.approxHinv = sp.diags(inverse, format='csr')
    monkeypatch.setattr(opt, '_record', lambda: (float(np.linalg.norm(g, ord=np.inf)), 1.))
    return opt


def diagnostic_quadratic_operands(opt, h):
    """Test-only explicit SPD residual factors for the old arithmetic controls.

    No production callback/fallback. The toy constant objective offset cancels
    in delta; factors reproduce its gradient/Hessian to ordinary binary roundoff.
    """
    g = np.linalg.cholesky(np.asarray(h,dtype=np.float64)/2).T
    target = g@opt.xc-np.linalg.solve(g.T,opt.g/2)
    opt._problem = {'simulation':SimpleNamespace(G=g),
                    'misfit':SimpleNamespace(W=sp.eye(len(g),format='csr'),data=SimpleNamespace(dobs=target)),
                    'regularization':SimpleNamespace(multipliers=(),objfcts=()),
                    'reference_q':np.zeros(len(opt.xc)), 'beta_engine':1.}


@pytest.mark.parametrize('mixed', [False, True])
def test_degenerate_release_exact_trigger_and_certificate(monkeypatch, mixed):
    q, g = ([0., 1.], [-2., 0.]) if mixed else ([0., 0.], [-2., -3.])
    opt = diagnostic_opt(monkeypatch, q, g, [.25, .5], [0., 0.], [4., 4.])
    def deny(*args, **kwargs): raise AssertionError('exact zero-free release entered native CG')
    monkeypatch.setattr(l2.optimization.ProjectedGNCG, 'findSearchDirection', deny)
    assert not opt.stoppingCriteria()
    direction = opt.findSearchDirection()
    expected = np.clip(np.array(q)-np.array([.25, .5])*g, 0., 4.)-q
    np.testing.assert_array_equal(direction, expected)
    assert np.dot(g, direction) <= -np.sum(direction**2/np.array([.25, .5]))
    assert opt.cg_count == 0 and opt.cg_abs_resid is None and opt.cg_rel_resid is None


def test_nonzero_underflow_free_gradient_with_binding_active_is_not_release(monkeypatch):
    opt = diagnostic_opt(monkeypatch, [0., 1.], [2., 1e-300], [.25, .5], [0., 0.], [4., 4.])
    assert opt.stoppingCriteria() and opt._reason == 'zero_free_direction'


@pytest.mark.parametrize('null', [False, True])
def test_stationary_bound_and_null_do_not_release(monkeypatch, null):
    req, _, prior, _, _ = tiny()
    prior['reference_kg_m3'][:] = prior['start_kg_m3'][:] = (0. if null else prior['lower_kg_m3'][0])
    d = tiny()[4]@prior['start_kg_m3']+req['background_mgal']
    problem = l2._build_problem(req, d, noise(), prior, np.arange(4, dtype=np.int64), .01)
    def deny(*args, **kwargs): raise AssertionError('stationary bound/null entered any direction')
    monkeypatch.setattr(l2._RecordedProjectedGNCG, 'findSearchDirection', deny)
    result = l2._solve_partition(problem, prior)
    assert result['status'] == 'converged' and result['iterations'] == 0
    evidence = problem['optimizer_evidence']
    assert evidence['last_direction_kind'] == 'not_run'
    assert evidence['last_cg_absolute_residual'] is evidence['last_cg_relative_residual'] is None


@pytest.mark.parametrize('rounded', [False, True])
def test_release_official_armijo_counts_and_rounded_trial(monkeypatch, rounded):
    if rounded:
        opt = diagnostic_opt(monkeypatch, [1e16], [-4.], [.5], [1e16], [1e16+8.])
        opt.lower, opt.upper = np.array([1e16]), np.array([1e16+8.])
        opt.evalFunction = lambda *args, **kwargs: 2.
    else:
        opt = diagnostic_opt(monkeypatch, [0.]*3, [-2.]*3, [.5]*3, [0.]*3, [2.]*3)
        h = np.full((3, 3), 1.9)+np.eye(3)*.1
        diagnostic_quadratic_operands(opt,h)
        opt.f = 5.
        opt.evalFunction = lambda q, **kwargs: float(.5*q@h@q-2*np.sum(q)+5)
    assert not opt.stoppingCriteria()
    direction = opt.findSearchDirection()
    if rounded:
        with pytest.raises(l2._SolveFailure, match='zero_free_direction'): opt.modifySearchDirection(direction)
    else:
        trial, accepted = opt.modifySearchDirection(direction)
        assert accepted and opt.iterLS == 1 and len(opt._trials) == 2
        np.testing.assert_array_equal(trial, np.full(3, .5))
        assert opt._LS_ft <= opt.f+1e-4*opt._LS_descent


@pytest.mark.parametrize('failure', ['nonnegative_slope', 'nonfinite_slope', 'line_search_cap'])
def test_release_trial_faults_never_enter_native_or_retry(monkeypatch, failure):
    # Supplemental post-code diagnostic injections; not a claim that these
    # projections/objectives occurred naturally in the physical BVLS controls.
    opt = diagnostic_opt(monkeypatch, [0.], [-2.], [.5], [0.], [4.])
    assert not opt.stoppingCriteria()
    direction = opt.findSearchDirection()
    opt.evalFunction = lambda *args, **kwargs: 2.
    if failure == 'nonfinite_slope':
        monkeypatch.setattr(opt, 'projection', lambda q: np.array([-1. if failure == 'nonnegative_slope' else 1e308]))
        with pytest.raises(l2._SolveFailure, match='nonfinite'):
            opt.modifySearchDirection(direction)
    else:
        if failure == 'nonnegative_slope': monkeypatch.setattr(opt, 'projection', lambda q: np.array([-1.]))
        _, accepted = opt.modifySearchDirection(direction)
        assert not accepted and opt._reason == 'line_search_failed'
        assert len(opt._trials) == 20 and opt.iterLS == 20
    assert opt.cg_count == 0 and opt.cg_abs_resid is opt.cg_rel_resid is None


@pytest.mark.parametrize('failure', ['overflow', 'rounded_zero', 'wrong_projection'])
def test_release_finite_failure_no_jitter_or_retry(monkeypatch, failure):
    opt = diagnostic_opt(monkeypatch, [0.], [-2.], [1e308 if failure == 'overflow' else .5], [0.], [4.])
    if failure == 'rounded_zero':
        opt.xc = opt.lower = np.array([1e16])
        opt.upper = np.array([1e16+8.])
        opt.g[:] = -1.
        opt.approxHinv = sp.diags([.25])
    if failure == 'wrong_projection': monkeypatch.setattr(opt, 'projection', lambda q: np.array([-1.]))
    assert not opt.stoppingCriteria()
    with pytest.raises(l2._SolveFailure, match='nonfinite' if failure == 'overflow' else 'zero_free_direction'):
        opt.findSearchDirection()


def test_native_failure_never_invokes_release(monkeypatch):
    opt = diagnostic_opt(monkeypatch, [1.], [-2.], [.5], [0.], [4.])
    assert not opt.stoppingCriteria()
    def failed(*args, **kwargs): raise RuntimeError('retained native CG failure')
    def deny(*args, **kwargs): raise AssertionError('ordinary failure entered release projection')
    monkeypatch.setattr(l2.optimization.ProjectedGNCG, 'findSearchDirection', failed)
    monkeypatch.setattr(opt, 'projection', deny)
    with pytest.raises(RuntimeError, match='retained native CG failure'): opt.findSearchDirection()


def test_release_trace_identity_and_not_run_cg():
    result, problem = assert_six_cell_optimum('full_covariance', 75., 'zero')
    evidence = problem['optimizer_evidence']
    np.testing.assert_array_equal(evidence['direction_kinds'], [0, 1])
    assert evidence['last_direction_kind'] == 'binding_release'
    assert evidence['last_cg_count'] == 0
    assert evidence['last_cg_absolute_residual'] is evidence['last_cg_relative_residual'] is None
    assert result['trace']['line_search_counts'][-1] == 1


@pytest.mark.parametrize('upper', [False, True])
@pytest.mark.parametrize('free_gradient', [0., 1e-300, 1e-11, 3., -3.])
def test_binding_release_any_inward_before_native_cg(monkeypatch, upper, free_gradient):
    q, g = ([4., 1.], [2., free_gradient]) if upper else ([0., 1.], [-2., free_gradient])
    diagonal_inverse = np.array([.25, .5])
    opt = diagnostic_opt(monkeypatch, q, g, diagonal_inverse, [0., 0.], [4., 4.])
    def deny(*args, **kwargs): raise AssertionError('inward binding release ran native CG first')
    monkeypatch.setattr(l2.optimization.ProjectedGNCG, 'findSearchDirection', deny)
    assert not opt.stoppingCriteria()
    direction = opt.findSearchDirection()
    expected = np.clip(np.array(q)-diagonal_inverse*g, 0., 4.)-q
    np.testing.assert_array_equal(direction, expected)
    metric = np.sum(direction**2/diagonal_inverse)
    assert float(np.dot(g, direction)) < 0 and metric > 0
    assert np.dot(g, direction) <= -metric
    assert opt._last_direction_kind == 'binding_release'
    assert opt.cg_count == 0 and opt.cg_abs_resid is opt.cg_rel_resid is None
    decision = opt._direction_decisions[-1]
    assert decision['active_count'] == decision['inward_active_count'] == 1
    assert decision['cg_executed'] is False and decision['kind'] == 'binding_release'
    np.testing.assert_allclose(decision['pg_metric_norm_squared'], metric, rtol=1e-10, atol=1e-12)


def test_binding_face_delegation_actual_projected_armijo_shortening(monkeypatch):
    # Exact SPD mathematical control, real pinned native CG/LS; not a field fixture.
    q, g = np.array([.99, .01]), np.array([-1., 2.])
    h = np.array([[1., -1.5], [-1.5, 2.5]])
    opt = diagnostic_opt(monkeypatch, q, g, 1/np.diag(h), [0., 0.], [1., 1.])
    opt.H, opt.f = sp.csr_matrix(h), 5.
    diagnostic_quadratic_operands(opt,h)
    def objective(x, **kwargs):
        delta = x-q
        return float(5.+g@delta+.5*delta@h@delta)
    opt.evalFunction = objective
    assert not opt.stoppingCriteria()
    direction = opt.findSearchDirection()
    np.testing.assert_allclose(direction, [-2., -2.], rtol=1e-10, atol=1e-12)
    assert opt.cg_count == 2 and opt._last_direction_kind == 'native_CG'
    trial, accepted = opt.modifySearchDirection(direction)
    assert accepted and opt.iterLS == 7
    checks = np.array(opt._trial_checks)
    assert checks.shape == (8, 5) and checks[0, 3] > 0 and checks[-1, 3] < 0
    np.testing.assert_array_equal(checks[:, 4], [0., 0., 0., 0., 0., 0., 0., 1.])
    np.testing.assert_allclose(checks[:, 2], 2.**-np.arange(8), rtol=0., atol=0.)
    np.testing.assert_allclose(checks[-1, 3], g@(trial-q), rtol=1e-10, atol=1e-12)
    assert objective(trial) <= opt.f+1e-4*checks[-1, 3]
    assert opt._direction_decisions[-1]['pg_metric_norm_squared'] is None
    assert opt._direction_decisions[-1]['cg_executed'] is True


def test_binding_feasible_chord_is_not_projected_gradient_arc(monkeypatch):
    opt = diagnostic_opt(monkeypatch, [0.], [-10.], [1.], [0.], [1.])
    opt.f = 1.
    opt.evalFunction = lambda q, **kwargs: float(1.-10*q[0]+20*q[0]**2)
    diagnostic_quadratic_operands(opt,[[40.]])
    assert not opt.stoppingCriteria()
    direction = opt.findSearchDirection()
    trial, accepted = opt.modifySearchDirection(direction)
    assert accepted and opt.iterLS == 2
    np.testing.assert_array_equal(trial, [.25])
    assert np.clip(opt.xc-.25*(opt.approxHinv@opt.g), 0., 1.)[0] == 1.
    assert opt._last_trial_check['decision'] == 'accepted'
    assert opt._last_trial_check['slope'] == -2.5


@pytest.mark.parametrize('kind', ['native_CG', 'binding_release'])
def test_binding_both_branch_positive_actual_slope_exhausts_same_direction(monkeypatch, kind):
    opt = diagnostic_opt(monkeypatch, [1.] if kind == 'native_CG' else [0.], [-2.], [.5], [0.], [4.])
    opt.H = sp.csr_matrix([[2.]])
    opt.f, opt.evalFunction = 5., lambda *args, **kwargs: 0.
    assert not opt.stoppingCriteria()
    direction = opt.findSearchDirection()
    count = opt.cg_count
    monkeypatch.setattr(opt, 'projection', lambda q: np.array([-1.]))
    _, accepted = opt.modifySearchDirection(direction)
    assert not accepted and opt._reason == 'line_search_failed'
    assert opt.iterLS == len(opt._trials) == len(opt._trial_checks) == 20
    assert opt.cg_count == count
    assert np.all(np.array(opt._trial_checks)[:, 3] > 0.)
    assert np.all(np.array(opt._trial_checks)[:, 4] == 0.)
    assert opt._last_trial_check['cause'] == 'line_search_failed'
    assert opt._last_trial_check['decision'] == 'failure'


@pytest.mark.parametrize('kind', ['native_CG', 'binding_release'])
@pytest.mark.parametrize('fault', ['noop', 'nonfinite_model', 'nonfinite_objective', 'deadline'])
def test_binding_both_branch_trial_fault_no_false_acceptance(monkeypatch, kind, fault):
    opt = diagnostic_opt(monkeypatch, [1.], [-2.], [.5], [0.], [4.])
    opt._last_direction_kind = kind
    opt._LS_xt, opt._LS_ft, opt.iterLS = np.array([2.]), 0., 0
    opt._LS_t, opt._LS_descent = 1., -2.  # Complete native nominal LS state before the fault.
    if fault == 'noop': opt._LS_xt = opt.xc.copy()
    if fault == 'nonfinite_model': opt._LS_xt[0] = np.inf
    if fault == 'nonfinite_objective': opt._LS_ft = np.nan
    if fault == 'deadline': opt._deadline = -np.inf
    reason = 'zero_free_direction' if fault == 'noop' else 'wall_cap' if fault == 'deadline' else 'nonfinite'
    with pytest.raises(l2._SolveFailure, match=reason): opt.stoppingCriteria(inLS=True)
    assert opt._last_trial_check['decision'] == 'failure'
    assert opt._last_trial_check['cause'] == reason


def test_binding_trace_cpu4_eleven_keys_and_unavailable_cg_not_success():
    result, problem = assert_six_cell_optimum('full_covariance', 75., 'zero')
    e = problem['optimizer_evidence']
    assert set(e) == {'trial_objectives', 'direction_kinds', 'last_direction_kind', 'last_cg_count',
                      'last_cg_absolute_residual', 'last_cg_relative_residual', 'last_cg_residual_status',
                      'direction_decisions', 'trial_checks', 'last_trial_check','precision_trials'}
    decisions = e['direction_decisions']
    assert type(decisions) is tuple and len(decisions) == result['iterations'] <= 200
    assert e['last_cg_residual_status'] == 'not_run'
    assert e['last_cg_absolute_residual'] is e['last_cg_relative_residual'] is None
    for decision in decisions:
        assert set(decision) == {'state_index', 'kind', 'active_count', 'inward_active_count',
                                 'free_residual_inf', 'candidate_slope', 'pg_metric_norm_squared', 'cg_executed'}
        assert decision['candidate_slope'] < 0.
        if decision['kind'] == 'binding_release':
            assert decision['inward_active_count'] > 0 and not decision['cg_executed']
            assert decision['pg_metric_norm_squared'] > 0.
        else:
            assert decision['inward_active_count'] == 0 and decision['cg_executed']
            assert decision['pg_metric_norm_squared'] is None
    for name, columns in [('trial_objectives', 3), ('trial_checks', 5)]:
        array = e[name]
        assert array.shape[1] == columns and len(array) <= 4000
        assert np.isfinite(array).all() and not array.flags.writeable
    assert len(e['trial_checks']) == sum(result['trace']['line_search_counts'])
    assert set(e['last_trial_check']) == {'iteration', 'trial', 't', 'phi_trial', 'slope', 'decision', 'cause'}


@pytest.mark.parametrize('kind', ['diagonal_sd', 'full_covariance'])
@pytest.mark.parametrize('rows', [[0, 0, 2], [2, 0, 1], [-1, 0, 2], [0, 2, 4]])
def test_private_whitening_rejects_duplicate_marginal_indices(monkeypatch, kind, rows):
    indices = np.array(rows, dtype=np.int64)
    def deny(*args, **kwargs): raise AssertionError('factorization before invalid row identity rejected')
    monkeypatch.setattr(l2.la, 'cholesky', deny)
    monkeypatch.setattr(l2.la, 'eigh', deny)
    monkeypatch.setattr(l2.np, 'isfinite', deny)
    with pytest.raises(ValueError, match='rows'):
        l2._weights(noise(kind), indices)


def test_no_io_hooks_runtime_or_legacy_mutation(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    assert hashlib.sha256((root/'data-pipeline/gravity_forward.py').read_bytes()).hexdigest() == (
        '46d205a453147cc18697464e4a6deda2920d0d88307e366b6fd336d9a1ac07d5')
    old = json.loads((root/'docs/design/features/m02-prism-operator/runtime-pins.json').read_text())
    new = json.loads((root/'docs/research/m02-survey-l2-evidence-2026-10-03.json').read_text())
    sources = {**old['targeted_source_sha256'], **{k:v['sha256'] for k,v in new['installed_sources'].items()}}
    assert len(sources) == 28
    for rel, expected in sources.items():
        path = importlib.metadata.distribution(rel.split('/')[0]).locate_file(rel)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, rel
    req, d, prior, bounds, oracle = tiny()
    from test_gravity_l2_selection import request as authored_request
    planning_req = authored_request()
    def deny(*args, **kwargs): raise AssertionError('application I/O or installed metadata scan inside callable')
    with monkeypatch.context() as guard:
        guard.setattr(builtins, 'open', deny)
        guard.setattr(Path, 'open', deny)
        guard.setattr(socket, 'socket', deny)
        guard.setattr(subprocess, 'Popen', deny)
        guard.setattr(importlib.metadata, 'version', deny)
        guard.setattr(importlib.metadata, 'distribution', deny)
        problem = l2._build_problem(req, d, noise(), prior, np.arange(4, dtype=np.int64), .01)
        assert problem['misfit'](np.zeros(5)) >= 0
        solved = l2._solve_partition(problem, prior)
        assert solved['status'] == 'converged'
        planned = survey.plan_gravity_l2(planning_req)
        assert len(planned['outer_rows']) == 36
        old_version = forward.simpeg.__version__
        guard.setattr(forward.simpeg, '__version__', 'unreviewed')
        with pytest.raises(RuntimeError, match='loaded package versions'): forward._runtime()
        guard.setattr(forward.simpeg, '__version__', old_version)
