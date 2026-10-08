"""Actual installed physical CG; independent TEST-ONLY small dense oracle."""
from dataclasses import replace
from fractions import Fraction
from itertools import product
from time import monotonic

import numpy as np
import pytest
from scipy.optimize import lsq_linear

import physical_reduced_optimizer as reduced
from test_physical_owned_spd import Physical, arguments


class ReducedPhysical(Physical):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.identity_value['runtime_epoch'] = reduced.LINEAR_EPOCH


def kwargs(obj, **options):
    result = arguments(obj, **options)
    result['binding'] = replace(result['binding'],
        accepted_export='physical_reduced_optimizer.solve_bounded_linear',
        optimizer_source_sha256=reduced.SOURCE_SHA256, policy=reduced.POLICY)
    return result


def run(obj, **options):
    return reduced.solve_bounded_linear(obj, obj.lower, obj.upper, obj.start,
        **kwargs(obj, **options))


@pytest.mark.parametrize('bounded', [False, True])
@pytest.mark.parametrize('kind', ['diagonal_sd', 'full_covariance'])
def test_actual_native_caps_and_original_independent_accuracy(monkeypatch, bounded, kind):
    obj = ReducedPhysical(bounded=bounded, kind=kind)
    actual = reduced.core.optimization.ProjectedGNCG.findSearchDirection
    calls = []
    def observe(opt):
        calls.append((opt.cg_maxiter, opt.cg_rtol, opt.cg_atol,
            opt.maxIterLS, opt.maxIter, opt.step_active_set))
        return actual(opt)
    monkeypatch.setattr(reduced.core.optimization.ProjectedGNCG, 'findSearchDirection', observe)
    result = run(obj, bounds=True)
    assert result['status'] == 'converged', result['reason']
    assert calls and all(0 < c[0] <= 200 and c[1:] == (1e-6, 0., 20, 200, False) for c in calls)
    assert result['iterations'] <= 200
    assert len(result['trace']['models_q']) == result['iterations']+1
    assert result['terminal_audits'][-1]['check']['passed']
    g, w = obj.problem['simulation'].G, obj.problem['misfit'].W.toarray()
    matrix = np.vstack((w@g, np.sqrt(obj.beta)*obj.r))
    rhs = np.r_[w@obj.problem['misfit'].data.dobs,
        np.sqrt(obj.beta)*obj.r@obj.problem['reference_q']]
    oracle = lsq_linear(matrix, rhs, bounds=(obj.lower, obj.upper), method='bvls', tol=1e-13)
    assert oracle.success
    np.testing.assert_allclose(result['q'], oracle.x, rtol=1e-7, atol=1e-8)
    np.testing.assert_allclose(g@result['q'], g@oracle.x, rtol=1e-7, atol=1e-9)
    for row in result['conditioning_attempts']:
        assert row['branch'] == 'cg' and row['true_relative_residual'] <= 1e-6
        assert row['cumulative_CG'] <= 200 and row['resource']['prospective_peak_bytes'] <= 2*1024**3
        assert ('q' in row) == (row['phase'] == 0)
        assert ('gradient' in row) == (row['phase'] == 0)
        assert 'free_indices' not in row
    assert all(t['effective_alpha'] == t['alpha']*t['ray_alpha0'] for t in result['line_search_trials'])
    assert obj.released == 1


def original_outward_state(obj):
    # TEST ONLY exhaust a tiny5-cell physical box; no runtime oracle or fixture
    # fit is manufactured. Native g/H define the independent dense direction.
    h = obj.evaluate(obj.start, True, True)[2]
    dense = np.column_stack([h@np.eye(5)[i] for i in range(5)])
    choices = zip(obj.lower, (obj.lower+obj.upper)/2., obj.upper)
    for coordinates in product(*choices):
        q = np.array(coordinates, dtype=np.float64)
        _, g, h = obj.evaluate(q, True, True)
        binding = ((q == obj.lower) & (g >= 0.)) | ((q == obj.upper) & (g <= 0.))
        free = ~binding
        if not np.any(free):
            continue
        p = np.zeros(5)
        p[free] = np.linalg.solve(dense[np.ix_(free, free)], -g[free])
        if np.any(((q == obj.lower) & (p < 0.)) | ((q == obj.upper) & (p > 0.))):
            return q, g, h
    raise AssertionError('Actual physical tiny box must expose outward released Newton coordinates')


def direction_optimizer(obj):
    q, g, h = original_outward_state(obj)
    args = kwargs(obj)
    opt = reduced._Linear(obj, obj.identity(), obj.lower, obj.upper, args['budget'])
    opt.prepare_owned(args['terminal'], 'fixed_linear_quadratic',
        ('physical_reduced_optimizer', reduced.SOURCE_SHA256, reduced.POLICY, reduced.LINEAR_EPOCH))
    opt.xc, opt.g, opt.H, opt.iter = q, g, h, 0
    return opt


def test_actual_working_face_reconstruction_true_H_and_disposal(monkeypatch):
    obj = ReducedPhysical(bounded=True)
    opt = direction_optimizer(obj)
    actual = reduced.core.spd.OwnedMetric
    live = []
    class Observe(actual):
        def __init__(self, *args, **kw):
            assert all(m.live_payload_bytes == 0 for m in live)
            super().__init__(*args, **kw)
            live.append(self)
    monkeypatch.setattr(reduced.core.spd, 'OwnedMetric', Observe)
    p = opt.findSearchDirection()
    assert len(opt.conditioning_attempts) >= 2
    working = opt.bindingSet(opt.xc)
    used = 0
    for row in opt.conditioning_attempts:
        assert not np.any(working[row['frozen_delta']])
        working[row['frozen_delta']] = True
        assert reduced.core.spd.digest(working) == row['working_mask_sha256']
        direction = row['direction']
        assert np.all(direction[working] == 0.)
        residual = (-opt.g-opt.H@direction)[~working]
        rhs = np.linalg.norm(opt.g[~working])
        assert np.linalg.norm(residual) <= 1e-6*rhs
        used += row['iterations']
        assert row['cumulative_CG'] == used
    assert opt.cg_count == used <= 200
    assert not np.any(((opt.xc == obj.lower) & (p < 0.)) | ((opt.xc == obj.upper) & (p > 0.)))
    assert np.inner(opt.g, p) < 0.
    assert opt._working is None and np.array_equal(opt.activeSet(opt.xc), opt.bindingSet(opt.xc))
    assert all(m.live_payload_bytes == 0 for m in live)


def test_sum_cap_not_reset_and_no_proposal(monkeypatch):
    opt = direction_optimizer(ReducedPhysical(bounded=True))
    native = reduced.core.optimization.ProjectedGNCG.findSearchDirection
    calls = []
    def exhausted(actual):
        calls.append(actual.cg_maxiter)
        p = native(actual)
        actual.cg_count = 200  # Deliberate cap fault injection, not science data.
        return p
    monkeypatch.setattr(reduced.core.optimization.ProjectedGNCG, 'findSearchDirection', exhausted)
    with pytest.raises(reduced.core.linear._Failure, match='cg_cap'):
        opt.findSearchDirection()
    assert calls == [200] and opt.cg_count == 200
    assert opt.conditioning_attempts[0]['cumulative_CG'] == 200
    assert opt.ray_initializations == [] and opt._working is None


def test_actual_failed_residual_no_refinement_or_proposal(monkeypatch):
    obj = ReducedPhysical()
    monkeypatch.setattr(reduced.core.optimization.ProjectedGNCG, 'findSearchDirection', lambda opt: -opt.g*1e-12)
    result = run(obj)
    assert result['reason'] == 'cg_cap' and result['iterations'] == 0
    assert len(result['conditioning_attempts']) == 1
    assert result['conditioning_attempts'][0]['true_relative_residual'] > 1e-6
    assert not result['ray_initializations'] and not result['line_search_trials']


def test_extra_resource_reserve_before_actual_native_call(monkeypatch):
    obj = ReducedPhysical()
    args = kwargs(obj)
    base = reduced.core.spd.validate_operands(obj.metric_operands(obj.start), obj.identity(),
        obj.start, args['budget'].resource_limit_bytes)['maximum']
    args['budget'] = replace(args['budget'], admitted_bytes=base)
    def forbidden(opt):
        raise AssertionError('Native CG must not run without NEW source-bound reserve')
    monkeypatch.setattr(reduced.core.optimization.ProjectedGNCG, 'findSearchDirection', forbidden)
    result = reduced.solve_bounded_linear(obj, obj.lower, obj.upper, obj.start, **args)
    assert result['reason'] == 'resource_cap' and result['iterations'] == 0
    row = result['conditioning_attempts'][0]
    assert row['branch'] == 'admission_refusal' and row['resource']['prospective_bytes'] > base
    assert not result['ray_initializations'] and obj.released == 1


@pytest.mark.parametrize('q,p', [([-1., 1.], [3., -2.]), ([.123, .432], [1e308, 9e307])])
def test_exact_inward_released_contact(q, p):
    q, p = np.array(q), np.array(p)
    lo, hi = -np.ones(2), np.ones(2)
    alpha, _ = reduced.initial_ray(q, p, -np.sign(p)/len(p), lo, hi, deadline=monotonic()+120.)
    ratios = [(Fraction(float(hi[i] if p[i] > 0 else lo[i]))-Fraction(float(q[i])))/Fraction(float(p[i])) for i in range(2)]
    best = min(Fraction(1), *ratios)
    assert Fraction(alpha) >= best and Fraction(float(np.nextafter(alpha, 0.))) < best


def test_outward_null_clock_and_binding_before_proposal():
    q, p = np.array([-1., 1.]), np.array([-1., -1.])
    with pytest.raises(ValueError, match='outward'):
        reduced.initial_ray(q, p, -p, -np.ones(2), np.ones(2), deadline=monotonic()+120.)
    with pytest.raises(ValueError, match='descent'):
        reduced.initial_ray(q, np.zeros(2), p, -np.ones(2), np.ones(2), deadline=monotonic()+120.)
    with pytest.raises(reduced.core.spd.kernel.DeadlineExceeded):
        reduced.initial_ray(np.zeros(2), p, -p, -np.ones(2), np.ones(2), deadline=monotonic()-1.)
    obj = ReducedPhysical()
    with pytest.raises(ValueError, match='binding'):
        reduced.solve_bounded_linear(obj, obj.lower, obj.upper, obj.start, **arguments(obj))
    result = run(obj, deadline=monotonic()-1.)
    assert result['reason'] == 'wall_cap' and result['q'] is None
    assert not result['conditioning_attempts'] and not result['ray_initializations']


def test_zero_accepted_cap_no_factor_or_restart(monkeypatch):
    obj = ReducedPhysical()
    def forbidden(*args):
        raise AssertionError('No factor allowed after original accepted cap')
    monkeypatch.setattr(reduced.core.spd, 'OwnedMetric', forbidden)
    result = run(obj, steps=0)
    assert result['reason'] == 'iteration_cap' and result['iterations'] == 0
    assert not result['conditioning_attempts'] and not result['ray_initializations']


def test_deadline_during_source_preflight_keeps_wall_cause(monkeypatch):
    obj = ReducedPhysical()
    actual = obj.metric_operands
    def expire(q):
        result = actual(q)
        monkeypatch.setattr(reduced.core, 'monotonic', lambda: monotonic()+1000.)
        return result
    obj.metric_operands = expire
    result = run(obj)
    assert result['reason'] == 'wall_cap' and result['iterations'] == 0
    assert not result['ray_initializations'] and not result['line_search_trials']
    assert obj.released == 1


def test_source_drift_during_preflight_keeps_identity_cause():
    obj = ReducedPhysical()
    actual = obj.metric_operands
    def drift(q):
        result = actual(q)
        obj.identity_value['source_inventory_sha256'] = 'f'*64
        return result
    obj.metric_operands = drift
    result = run(obj)
    assert result['reason'] == 'state_mismatch' and result['iterations'] == 0
    assert not result['ray_initializations'] and obj.released == 1
