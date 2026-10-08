"""New-policy original science; historical cpu1 assertion is not rewritten."""
from copy import deepcopy
from time import monotonic

import numpy as np
import pytest

import gravity_irls_corrected as corrected
import gravity_irls as plain
from test_gravity_irls import native_problem, policy


def test_corrected_original_positive(record_property):
    problem, prior = native_problem(null=False)
    result = corrected.solve_partition(problem, prior, policy(), monotonic()+120.)
    record_property('native_outcome', result['terminal']['status']+'/'+result['terminal']['reason'])
    record_property('actual_combined_steps', result['iterations'])
    assert result['terminal']['status'] == 'converged', result['terminal']
    assert result['terminal']['reason'] == 'irls_fixed_point'
    assert result['initialization']['status'] == 'converged'
    assert len(result['stages']) == 21 and result['terminal']['weight_updates'] == 20
    assert all(s['inner']['status'] == 'converged' for s in result['stages'])
    assert all(s['epsilon'] == policy()['epsilon_floor'] for s in result['stages'][17:])
    assert all(c['model_relative'] <= 1e-6 and c['weights_relative'] <= 1e-6
               for c in result['terminal']['stage_changes'][-3:])
    assert result['stages'][-1]['canonical_weight_mismatch'] <= 1e-6
    assert result['stages'][-1]['canonical_absolute_kkt'] <= 1e-12
    anchors = sum(a['outcome'] == 'adopted' for a in result['attempts'])
    calls = sum(len(a.get('cg', ())) for a in result['attempts'])
    assert result['iterations'] == result['initialization']['iterations']+anchors+sum(
        s['inner']['iterations'] for s in result['stages'])
    assert result['iterations'] <= 200 and anchors <= 63 and calls <= 126
    assert len(result['models_q']) == result['iterations']+1
    assert len(result['event_stages']) == len(result['models_q'])
    assert len(result['event_kinds']) == len(result['models_q'])
    for a in result['attempts']:
        for c in a.get('cg', ()):
            assert c['relative_residual'] <= 1e-6 and c['info'] == 0
            assert 0 <= c['iterations'] <= 200 and c['seconds'] >= 0
        if a['outcome'] == 'adopted':
            assert a['denominator'] > 0 and a['conditioning_ratio'] >= np.sqrt(np.finfo(float).eps)
            assert a['merit_slope'] < 0 and a['trials'][-1]['merit_margin'] < 0
    corrected.validate_partition(result, problem, prior, policy())


@pytest.mark.parametrize('reference_offset', [0., .137])
@pytest.mark.parametrize('sign', [1., -1.])
def test_matrixfree_independent_jacobian(reference_offset, sign):
    problem, prior = native_problem(null=False)
    problem = dict(problem, reference_q=np.full(12, reference_offset))
    # Update the actual native L2 reference as well; no fake derived gradient.
    problem['regularization'].reference_model = problem['reference_q'].copy()
    x = sign*np.linspace(-.31, .61, 12)
    q = problem['reference_q']+x
    stage = corrected._stage(problem, q, policy(), 17, policy()['epsilon_floor'])
    obj = corrected._Objective(stage, 17, prior['lower_kg_m3']/1000.,
                               prior['upper_kg_m3']/1000., 'b'*64)
    m, u, j, diagonal = corrected._linearization(problem, stage, obj, q, monotonic()+120.)
    identity = np.eye(len(q))
    actual_m = np.column_stack([m@v for v in identity])
    # Independent likelihood/prior rows, not production linearization/H replay.
    w = problem['misfit'].W.toarray()
    g = problem['simulation'].G
    h0 = (w@g).T@(w@g)
    reg = stage['problem']['regularization']
    for alpha, child in zip(reg.multipliers[1:], reg.objfcts[1:]):
        b = (child.W@child.f_m_deriv(problem['reference_q'])).toarray()
        h0 += problem['beta_engine']*alpha*(b.T@b)
    v = problem['beta_engine']*problem['regularization'].multipliers[0]*problem['regularization'].objfcts[0].W.diagonal()**2
    eps = stage['epsilon'][0]
    s, d = np.sqrt(x[j]**2+eps**2), np.sqrt(x*x+eps*eps)
    expected_m = h0+np.diag(v*s*eps**2/d**3)
    expected_u = v*x*x[j]/(d*s)
    np.testing.assert_allclose(actual_m, expected_m, rtol=1e-13, atol=1e-13)
    np.testing.assert_allclose(u, expected_u, rtol=1e-14, atol=1e-15)
    np.testing.assert_allclose(diagonal, np.diag(expected_m), rtol=1e-13, atol=1e-13)
    assert np.linalg.eigvalsh(expected_m).min() > 0
    jac = expected_m.copy()
    jac[:, j] += expected_u
    assert (jac[j, j]-h0[j, j]) == pytest.approx(v[j], rel=1e-10, abs=1e-13)
    b = g.T@(w.T@(w@problem['misfit'].data.dobs))
    def residual(value):
        zz = value-problem['reference_q']
        ss = np.sqrt(np.max(abs(zz))**2+eps**2)
        return h0@zz+v*ss*zz/np.sqrt(zz*zz+eps*eps)-b
    direction = np.linspace(.31, -.17, 12)
    finite = (residual(q+1e-5*direction)-residual(q-1e-5*direction))/(2e-5)
    np.testing.assert_allclose(jac@direction, finite, rtol=1e-8, atol=1e-8)


@pytest.mark.parametrize('case,expected', [('null','disabled_null'), ('tie','disabled_tied_max'),
    ('active_max','disabled_bound_face_active_max'), ('free_max','disabled_bound_face_free_max')])
def test_branch_disable(case, expected):
    q = np.array([.1, .2, .3])
    ref = np.zeros(3)
    lower, upper = np.full(3, -1.), np.ones(3)
    if case == 'null':
        q[:] = 0.
    if case == 'tie':
        q[:] = [.3, -.3, .1]
    if case == 'active_max':
        q[0] = -1.
    if case == 'free_max':
        lower[0] = q[0]
    branch, j = corrected._branch(q, ref, lower, upper)
    assert branch == expected
    assert j is None if case in ('null', 'tie') else j is not None


@pytest.mark.parametrize('c,j', [(np.array([-1., 0.]),0), (np.array([-2., 0.]),0),
    (np.array([0., 1e12]),0), (np.array([np.nan, 0.]),0)])
def test_guard_reject(c, j):
    with pytest.raises(corrected._Failure):
        corrected._denominator(c, j)


def test_caps():
    budget = corrected._Budget(monotonic()+120.)
    budget.steps = 200
    with pytest.raises(corrected._Failure, match='iteration_cap'):
        budget.adopt()
    budget.steps = 0
    budget.calls = 126
    with pytest.raises(corrected._Failure, match='auxiliary_call_cap'):
        budget.begin_call()
    with pytest.raises(corrected._Failure, match='wall_cap'):
        corrected._Budget(monotonic()-1.).check()


@pytest.mark.parametrize('failure', ['cg_info', 'cg_true_residual'])
def test_actual_auxiliary_failure_no_native_or_retry(monkeypatch, failure):
    problem, prior = native_problem(null=False)
    actual_cg = corrected.cg
    calls = []
    def failed(*args, **kwargs):
        calls.append(1)
        value, info = actual_cg(*args, **kwargs)
        return (value, 200) if failure == 'cg_info' else (np.zeros_like(value), info)
    def native_denied(*args, **kwargs):
        raise AssertionError('failed auxiliary call entered native stage/fallback')
    monkeypatch.setattr(corrected, 'cg', failed)
    monkeypatch.setattr(plain.optimizer, 'solve_bounded_physical', native_denied)
    result = corrected.solve_partition(problem, prior, policy(), monotonic()+120.)
    assert result['terminal']['status'] == 'nonconverged'
    assert result['terminal']['reason'] == 'auxiliary_cg_cap'
    assert len(calls) == 1 and result['auxiliary_calls'] == 1 and not result['stages']
    assert result['iterations'] == result['initialization']['iterations']
    assert result['attempts'][0]['cg'][0]['seconds'] >= 0.
    corrected.validate_partition(result, problem, prior, policy())


def test_ledger_replay():
    problem, prior = native_problem(null=False)
    result = corrected.solve_partition(problem, prior, policy(), monotonic()+120.)
    corrected.validate_partition(result, problem, prior, policy())
    for name in ('model', 'timing', 'residual', 'weight', 'lineage'):
        changed = deepcopy(result)
        if name == 'model':
            changed['models_q'][1, 0] += .01
        if name == 'timing':
            changed['attempts'][0]['cg'][0]['seconds'] = -1.
        if name == 'residual':
            changed['attempts'][0]['cg'][0]['relative_residual'] = 0.
        if name == 'weight':
            changed['stages'][-1]['canonical_weight_mismatch'] = .1
        if name == 'lineage':
            changed['iterations'] += 1
        changed['result_sha256'] = plain.survey._digest({k:v for k,v in changed.items() if k != 'result_sha256'})
        with pytest.raises((TypeError, ValueError)):
            corrected.validate_partition(changed, problem, prior, policy())


def test_epoch_separation():
    assert corrected.RUNTIME_EPOCH == 'm02-survey-irls-cpu-2'
    assert corrected.POLICY == 'safeguarded-irls-interior-threepair-log17-stage-1'
    assert corrected.RUNTIME_EPOCH != plain.RUNTIME_EPOCH and corrected.POLICY != plain.POLICY
    problem, prior = native_problem()
    result = corrected.solve_partition(problem, prior, policy(), monotonic()+120.)
    assert result['terminal']['status'] == 'converged'
    assert result['terminal']['reason'] == 'irls_stationary_null'
    assert len(result['stages']) == 21 and result['iterations'] == 0
    assert all(a['branch'] == 'disabled_null' for a in result['attempts'])
    assert all(not a.get('cg') for a in result['attempts'])
    result['runtime_epoch'] = plain.RUNTIME_EPOCH
    result['result_sha256'] = plain.survey._digest({k:v for k,v in result.items() if k != 'result_sha256'})
    with pytest.raises(ValueError):
        corrected.validate_partition(result, problem, prior, policy())
