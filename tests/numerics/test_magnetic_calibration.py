"""Actual local fitting controls; synthetic tests do not certify field geology."""

import hashlib
import importlib.util
from pathlib import Path
from time import monotonic

import numpy as np
import pytest

import magnetic_calibration as calibration
import magnetic_optimizer_adapter as adapter
import physical_optimizer as core

spec = importlib.util.spec_from_file_location('calibration_control', Path(__file__).with_name('test_magnetic_optimizer_adapter.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@pytest.fixture(scope='module')
def physical():
    return control.physical.__wrapped__()


def setup(physical, null=False):
    obj, _, observed, noise, _, _ = control.make(physical, 'linear_tmi_nT', False)
    if null:
        observed = np.zeros_like(observed)
    mesh = dict(origin_m=np.array(control.control.ORIGIN), hx_m=np.array(control.control.WIDTHS[0]),
                hy_m=np.array(control.control.WIDTHS[1]), hz_m=np.array(control.control.WIDTHS[2]), active=physical[0].active_cells.copy())
    prior = {k: dict(data=v.tolist()) for k, v in (
        ('reference_si', np.zeros(7) if null else .01*control.control.QREF), ('start_si', np.zeros(7)),
        ('lower_si', np.zeros(7)), ('upper_si', np.full(7, .1)), ('lengths_m', np.array(control.control.LENGTHS)))}
    binding = core.OptimizerBinding('physical_optimizer.solve_bounded_physical', core.SOURCE_SHA256,
        hashlib.sha256(Path(adapter.certificate_source()).read_bytes()).hexdigest(), 'a'*64, core.RUNTIME_EPOCH, core.POLICY)
    return obj.operator, mesh, prior, observed, noise, binding


@pytest.mark.parametrize('penalty', ['l2', 'sparse_smallness'])
def test_actual_null_fit_all_eight_sparse_thresholds(physical, penalty):
    operator, mesh, prior, observed, noise, binding = setup(physical, True)
    result = calibration.fit_partition(operator, mesh, prior, observed, noise, .3, penalty, binding=binding,
        deadline=monotonic()+120., admitted_bytes=1000000, allocation_sha256='b'*64, source_inventory_sha256='a'*64)
    assert result['status'] == 'converged', result['reason']
    np.testing.assert_array_equal(result['q'], np.zeros(7))
    assert result['kkt_inf'] == 0.
    if penalty == 'sparse_smallness':
        fixed = [h for h in result['history'] if h['phase'] == 'irls_fixed']
        assert tuple(h['epsilon_q'] for h in fixed) == adapter.EPSILONS
        assert all(h['objective'] == 0. and h['status'] == 'converged' for h in fixed)


def test_actual_nonzero_l2_and_fixed_beta(physical):
    operator, mesh, prior, observed, noise, binding = setup(physical)
    result = calibration.fit_partition(operator, mesh, prior, observed, noise, .3, 'l2', binding=binding,
        deadline=monotonic()+120., admitted_bytes=1000000, allocation_sha256='b'*64, source_inventory_sha256='a'*64)
    assert result['status'] == 'converged', result['reason']
    assert np.any(result['q'] > 0.)
    assert all(h['beta'] == .3 for h in result['history'])


@pytest.mark.parametrize('beta', [.3, 3.])
def test_nonzero_sparse_all_thresholds_independent_true_stationarity(physical, beta):
    operator, mesh, prior, observed, noise, binding = setup(physical)
    result = calibration.fit_partition(operator, mesh, prior, observed, noise, beta, 'sparse_smallness', binding=binding,
        deadline=monotonic()+120., admitted_bytes=1000000, allocation_sha256='b'*64, source_inventory_sha256='a'*64)
    assert result['status'] == 'converged', result['reason']
    fixed = [h for h in result['history'] if h['phase'] == 'irls_fixed']
    assert tuple(dict.fromkeys(h['epsilon_q'] for h in fixed)) == adapter.EPSILONS
    for epsilon in adapter.EPSILONS:
        series = [h for h in fixed if h['epsilon_q'] == epsilon]
        assert series[-1]['status'] == 'converged'
        assert all(b['objective']-a['objective'] <= 64*np.finfo(float).eps*max(1., abs(a['objective']), abs(b['objective']))
                   for a, b in zip(series, series[1:]))
    # Independent Choclo columns and pairwise physical faces; not the vendor
    # fixed-weight gradient which cannot certify true-p1 stationarity.
    _, _, independent, direction, _, _, _, r, volumes = physical
    kernel = np.einsum('c,nca->na', direction, (.01*independent).reshape(30, 3, 7))
    wk = kernel/.5
    delta = result['q']-control.control.QREF
    fraction = volumes/volumes.sum()
    gradient = 2*wk.T@((kernel@result['q']-observed.ravel())/.5)
    gradient += beta*(2*fraction*delta/np.sqrt(delta**2+.001**2)+2*r[7:].T@(r[7:]@delta))
    g_initial = 2*wk.T@(-observed.ravel()/.5)-2*beta*r.T@(r@control.control.QREF)
    projected = gradient.copy()
    projected[(result['q'] <= 32*np.finfo(float).eps)&(gradient > 0.)] = 0.
    projected[(result['q'] >= 10.-320*np.finfo(float).eps)&(gradient < 0.)] = 0.
    assert np.linalg.norm(projected, np.inf) <= 1e-7*max(1., np.linalg.norm(g_initial, np.inf))


def test_caps_preserve_failure_no_optimization_fallback(physical):
    operator, mesh, prior, observed, noise, binding = setup(physical)
    result = calibration.fit_partition(operator, mesh, prior, observed, noise, .3, 'l2', binding=binding,
        deadline=monotonic()-1., admitted_bytes=1000000, allocation_sha256='b'*64, source_inventory_sha256='a'*64)
    assert result['status'] == 'failed' and result['reason'] == 'wall_cap'
    assert result['history'] == [] and result['q'] is None


def test_selection_ties_and_failed_candidate_score_not_averaged():
    candidates = [dict(id='b00-sparse', beta=.0001, penalty='sparse_smallness', status='complete', score=1.),
                  dict(id='b02-l2', beta=.01, penalty='l2', status='complete', score=1.),
                  dict(id='b03-l2', beta=.1, penalty='l2', status='complete', score=1.),
                  dict(id='b04-l2', beta=1., penalty='l2', status='failed', score=None)]
    assert calibration.select_candidate(candidates)['id'] == 'b03-l2'
    with pytest.raises(ValueError, match='No complete'):
        calibration.select_candidate(candidates[-1:])
