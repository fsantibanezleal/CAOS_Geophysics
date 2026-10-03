"""Authored tiny engine/J/volume/noise/optimizer controls, never field truth."""

from copy import deepcopy
import builtins
import hashlib
import importlib.metadata
import json
from pathlib import Path
import socket
import subprocess

import choclo
import numpy as np
import pytest
import scipy.linalg as la
import scipy.sparse as sp

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
        planned = survey.plan_gravity_l2(planning_req)
        assert len(planned['outer_rows']) == 36
        old_version = forward.simpeg.__version__
        guard.setattr(forward.simpeg, '__version__', 'unreviewed')
        with pytest.raises(RuntimeError, match='loaded package versions'): forward._runtime()
        guard.setattr(forward.simpeg, '__version__', old_version)
