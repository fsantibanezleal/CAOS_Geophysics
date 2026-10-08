"""Exact independent breakpoint guards and actual installed native controls."""
from dataclasses import replace
from fractions import Fraction
from time import monotonic

import numpy as np
import pytest

import physical_feasible_optimizer as ray
from test_physical_owned_spd import Physical, arguments


def choose(q, p, lo=None, hi=None, pg=False, seconds=120.):
    q, p = np.array(q, dtype=np.float64), np.array(p, dtype=np.float64)
    lo = np.full(len(q), -1.) if lo is None else np.array(lo, dtype=np.float64)
    hi = np.ones(len(q)) if hi is None else np.array(hi, dtype=np.float64)
    # Finite actual slope even in the deliberate near-max/subnormal fixture.
    return ray.initial_ray(q, p, -np.sign(p)/len(p), lo, hi, pg=pg, deadline=monotonic()+seconds)


@pytest.mark.parametrize('q,p', [([.4, -.2], [3., -2.]),
    ([np.nextafter(1., 0.), 0.], [1.e8, 2.]), ([0., 0.], [.1, -.2]),
    ([.123, .432], [1.e308, 9.e307])])
def test_exact_independent_first_bound(q, p):
    alpha, coordinate = choose(q, p)
    # TEST ONLY exact-real oracle, independently enumerate all box distances.
    bounds = [Fraction(1 if v > 0 else -1)-Fraction(float(x)) for x, v in zip(q, p)]
    ratios = [d/Fraction(float(v)) for d, v in zip(bounds, p)]
    best = min(Fraction(1), *ratios)
    assert Fraction(alpha) <= best
    assert alpha == 1. or Fraction(float(np.nextafter(alpha, np.inf))) > best
    assert coordinate == (-1 if best == 1 else ratios.index(best))
    assert all(Fraction(-1) <= Fraction(float(x))+Fraction(alpha)*Fraction(float(v)) <= Fraction(1)
               for x, v in zip(q, p))


@pytest.mark.parametrize('q,p,message', [([1., 0.], [-1., 1.], 'active'),
    ([-1., 0.], [1., 1.], 'active'), ([0., 0.], [0., 0.], 'descent'),
    ([2., 0.], [-1., 1.], 'feasible'), ([0., 0.], [np.inf, 1.], 'finite')])
def test_guards_before_proposal(q, p, message):
    with pytest.raises(ValueError, match=message):
        choose(q, p)


def test_non_descent_underflow_clock_and_pg():
    q, p, lo, hi = np.zeros(1), np.ones(1), -np.ones(1), np.ones(1)
    with pytest.raises(ValueError, match='descent'):
        ray.initial_ray(q, p, p, lo, hi, pg=False, deadline=monotonic()+120.)
    tiny = np.nextafter(0., 1.)
    with pytest.raises(ValueError, match='representable'):
        choose([0.], [1.e308], lo=[-tiny], hi=[tiny])
    with pytest.raises(ray.core.spd.kernel.DeadlineExceeded):
        choose([0.], [1.], seconds=-1.)
    assert choose([1., -1.], [-.3, .2], pg=True) == (1., -1)
    with pytest.raises(ValueError, match='literal'):
        choose([0.], [1.], pg=1)


class FeasiblePhysical(Physical):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.identity_value['runtime_epoch'] = ray.LINEAR_EPOCH


def kwargs(obj, **options):
    result = arguments(obj, **options)
    result['binding'] = replace(result['binding'],
        accepted_export='physical_feasible_optimizer.solve_bounded_linear',
        optimizer_source_sha256=ray.SOURCE_SHA256, policy=ray.POLICY)
    return result


@pytest.mark.parametrize('bounded', [False, True])
def test_actual_native_original_caps_and_precision(monkeypatch, bounded):
    obj = FeasiblePhysical(bounded=bounded)
    native = ray.core.optimization.ProjectedGNCG.findSearchDirection
    calls = []
    def observe(opt):
        calls.append((opt.cg_maxiter, opt.cg_rtol, opt.cg_atol, opt.maxIterLS, opt.maxIter))
        return native(opt)
    monkeypatch.setattr(ray.core.optimization.ProjectedGNCG, 'findSearchDirection', observe)
    result = ray.solve_bounded_linear(obj, obj.lower, obj.upper, obj.start, **kwargs(obj, bounds=True))
    assert result['status'] == 'converged', result['reason']
    assert calls and all(c == (200, 1e-6, 0., 20, 200) for c in calls)
    assert result['iterations'] <= 200 and len(result['trace']['models_q']) == result['iterations']+1
    assert result['terminal_audits'][-1]['check']['passed']
    for attempt in result['conditioning_attempts']:
        if attempt['branch'] == 'cg':
            assert attempt['true_relative_residual'] <= 1e-6
    assert len(result['ray_initializations']) == result['iterations']
    for init in result['ray_initializations']:
        assert init['failure'] is None and 0. < init['alpha0'] <= 1.
        if init['branch'] == 'pg':
            assert init['alpha0'] == 1.
    assert all(t['effective_alpha'] == t['alpha']*t['ray_alpha0'] for t in result['line_search_trials'])
    assert obj.released == 1


def test_original_failure_never_constructs_ray(monkeypatch):
    obj = FeasiblePhysical()
    monkeypatch.setattr(ray.core.optimization.ProjectedGNCG, 'findSearchDirection', lambda opt: -opt.g*1e-12)
    result = ray.solve_bounded_linear(obj, obj.lower, obj.upper, obj.start, **kwargs(obj))
    assert result['reason'] == 'cg_cap' and result['iterations'] == 0
    assert result['conditioning_attempts'][0]['true_relative_residual'] > 1e-6
    assert result['ray_initializations'] == () and not result['line_search_trials']


def test_separate_epoch_binding_and_lower_clock():
    obj = FeasiblePhysical()
    with pytest.raises(ValueError, match='binding'):
        ray.solve_bounded_linear(obj, obj.lower, obj.upper, obj.start, **arguments(obj))
    result = ray.solve_bounded_linear(obj, obj.lower, obj.upper, obj.start,
        **kwargs(obj, deadline=monotonic()-1.))
    assert result['reason'] == 'wall_cap' and not result['ray_initializations']
    assert result['q'] is None and result['iterations'] == 0
