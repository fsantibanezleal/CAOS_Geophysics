"""Closed native direction controls, not native fit/recurrence acceptance."""
from time import monotonic

import numpy as np
import pytest
from fractions import Fraction

import gravity_irls_face as face
import gravity_irls_face_direction as direction
from test_gravity_irls_face_source import owner_and_model, policy


@pytest.mark.parametrize('branch', ['binding_plateau', 'binding_unique', 'free_unique', 'free_unique_with_binding'])
def test_actual_library_cg_free_direction_against_independent_source_rows(branch):
    owner, q = owner_and_model(branch)
    derivative = None
    try:
        derivative = face._CanonicalFaceLinearization(owner, q, policy(), 17, policy()['epsilon_floor'])
        free = derivative.face['free'].copy()
        problem, stage = owner.problem, derivative._stage
        G, W = problem['simulation'].G, problem['misfit'].W.toarray()
        h0 = (W@G).T@(W@G)
        for alpha, child in zip(stage['problem']['regularization'].multipliers[1:],
                stage['problem']['regularization'].objfcts[1:]):
            B = (child.W@child.f_m_deriv(problem['reference_q'])).toarray()
            h0 += problem['beta_engine']*alpha*(B.T@B)
        x = q-problem['reference_q']; eps = stage['epsilon'][0]
        v = problem['beta_engine']*problem['regularization'].multipliers[0]*problem['regularization'].objfcts[0].W.diagonal()**2
        scale = np.sqrt(max(abs(x))**2+eps**2)
        M = h0+np.diag(v*scale*eps**2/(x*x+eps*eps)**1.5)
        J = M[np.ix_(free, free)].copy()
        if not derivative.face['constant_scale']:
            j = derivative.face['maximum_index']
            u = v*x*x[j]/(np.sqrt(x*x+eps*eps)*scale)
            J[:, int(np.flatnonzero(free == j)[0])] += u[free]
        root = derivative.root[free].copy()
        # Independent dense TEST-only solve; no production native H substitute.
        expected = np.linalg.solve(J, -root)
        derivative.close(); derivative = None
        budget = face.interior._Budget(owner.deadline)
        record = direction._native_direction(owner, q, policy(), 17, policy()['epsilon_floor'], budget)
        assert record['status'] == 'direction', record
        assert record['disposed'] and record['seconds'] > 0.
        assert len(record['cg']) == (1 if branch in ('binding_plateau', 'binding_unique') else 2)
        assert budget.calls == len(record['cg']) and budget.steps == 0
        assert not record['recurrence_enabled'] and not record['native_fit_accepted']
        assert record['merit_slope'] < 0.
        assert direction._validate_direction(owner, record, policy(), policy()['epsilon_floor']) is record
        assert np.all(record['direction'][record['binding']] == 0.)
        np.testing.assert_allclose(record['direction'][free], expected, rtol=1e-6, atol=1e-12)
        for row in record['cg']:
            assert row['status'] == 'returned' and row['info'] == 0
            assert row['iterations'] <= 200 and row['relative_residual'] <= 1e-6
            actual = np.linalg.norm(M[np.ix_(free, free)]@row['solution']-row['rhs'])
            assert abs(actual-row['absolute_residual']) <= 1e-12*max(1., np.linalg.norm(row['rhs']))
        # Rehashed evidence is not authority: reconstruct the original native
        # face, CG residual and source-owned metric operand, without another CG.
        for kind in ('rhs', 'solution', 'mask', 'metric', 'denominator',
                'iterations', 'matvecs', 'metric_actions', 'time'):
            changed = face.interior.plain.survey._snapshot(record)
            if kind in ('rhs', 'solution'):
                value = changed['cg'][0][kind].copy(); value[0] += .1
                changed['cg'][0][kind] = value
            elif kind == 'mask':
                value = changed['binding'].copy(); value[0] = not value[0]
                changed['binding'] = value
            elif kind == 'metric':
                changed['metric_operand_sha256'] = '0'*64
            elif kind in ('iterations', 'matvecs', 'metric_actions'):
                changed['cg'][0][kind] = 0
            elif kind == 'time':
                changed['cg'][0]['seconds'] = changed['seconds']+1.
            else:
                changed['denominator'] = 2.
            with pytest.raises(ValueError):
                direction._validate_direction(owner, changed, policy(), policy()['epsilon_floor'])
    finally:
        if derivative is not None:
            derivative.close()
        owner.close()


@pytest.mark.parametrize('branch', ['binding_unique', 'free_unique', 'free_unique_with_binding'])
def test_actual_library_cg_merit_alltrial_replay_and_adversaries(branch):
    owner, q = owner_and_model(branch)
    try:
        budget = face.interior._Budget(owner.deadline)
        native = direction._native_direction(owner, q, policy(), 17, policy()['epsilon_floor'], budget)
        assert native['status'] == 'direction', native
        calls = budget.calls
        candidate = direction._merit_candidate(owner, native, policy(), policy()['epsilon_floor'], budget)
        assert candidate['status'] == 'candidate', candidate
        assert direction._validate_merit_candidate(owner, native, candidate,
            policy(), policy()['epsilon_floor']) is candidate
        assert budget.calls == calls and budget.steps == 0
        assert not candidate['native_fit_accepted'] and not candidate['recurrence_enabled']
        assert 1 <= len(candidate['trials']) <= 20
        assert candidate['trials'][-1]['merit_margin'] < 0.
        assert all(row['disposed'] for row in candidate['trials'])
        np.testing.assert_array_equal(candidate['q'][native['binding']], q[native['binding']])
        # Replay uses actual canonical native gradients, not trusted stored
        # signs/merit or a hash of a fabricated candidate. No CG in replay.
        for kind in ('gradient', 'binding', 'branch', 'margin', 'candidate', 'scale',
                'stage', 'epsilon', 'disposal', 'extra_trial'):
            changed = face.interior.plain.survey._snapshot(candidate)
            last = changed['trials'][-1]
            if kind in ('gradient', 'binding'):
                field = 'native_'+kind
                value = last[field].copy()
                value[0] = not value[0] if kind == 'binding' else value[0]+.1
                last[field] = value
            elif kind == 'branch':
                last['face_preserved'] = False
            elif kind == 'margin':
                last['merit_margin'] -= 1.
            elif kind == 'candidate':
                value = changed['q'].copy(); value[0] += .01; changed['q'] = value
            elif kind == 'scale':
                changed['feasible_initialization']['alpha0'] *= .5
            elif kind == 'stage':
                last['stage_sha256'] = '0'*64
            elif kind == 'epsilon':
                last['epsilon'] = tuple(v*2 for v in last['epsilon'])
            elif kind == 'disposal':
                last['disposed'] = False
            else:
                changed['trials'] = (*changed['trials'], last.copy())
            with pytest.raises(ValueError):
                direction._validate_merit_candidate(owner, native, changed,
                    policy(), policy()['epsilon_floor'])
        assert budget.calls == calls and budget.steps == 0
    finally:
        owner.close()


def test_actual_free_tie_disables_before_cg_and_factory(monkeypatch):
    owner, q = owner_and_model('free_tie')
    try:
        monkeypatch.setattr(face._CanonicalFaceLinearization, 'metric', lambda *a: pytest.fail('disabled face built metric'))
        budget = face.interior._Budget(owner.deadline)
        record = direction._native_direction(owner, q, policy(), 17, policy()['epsilon_floor'], budget)
        assert record['status'] == 'disabled' and record['reason'] == 'disabled_free_tied_max'
        assert not record['cg'] and budget.calls == budget.steps == 0 and record['disposed']
    finally:
        owner.close()


@pytest.mark.parametrize('kind', ['source', 'clock', 'accepted_cap', 'call_cap', 'stage_cap'])
def test_refused_prerequisite_has_no_native_cg_or_fallback(kind, monkeypatch):
    owner, q = owner_and_model('free_unique')
    try:
        budget = face.interior._Budget(owner.deadline)
        if kind == 'source':
            monkeypatch.setattr(direction, 'SOURCE_SHA256', '0'*64)
        elif kind == 'clock':
            budget.deadline = monotonic()-1.
        elif kind == 'accepted_cap':
            budget.steps = 200
        elif kind == 'call_cap':
            budget.calls = 126
        else:
            budget._face_stage_calls = {17: 3}
        record = direction._native_direction(owner, q, policy(), 17, policy()['epsilon_floor'], budget)
        assert record['status'] == 'failed' and record['disposed']
        assert not record['cg'] and record['direction'] is None and record['accepted_moves'] == 0
        assert not record['native_fit_accepted'] and not record['recurrence_enabled']
    finally:
        owner.close()


def test_no_caller_operator_or_mask_entry():
    with pytest.raises(TypeError, match='closed physical owner'):
        direction._native_direction(object(), np.zeros(12), policy(), 17,
            policy()['epsilon_floor'], face.interior._Budget(monotonic()+120.))


def test_merit_does_not_turn_a_failed_direction_into_fallback():
    owner, q = owner_and_model('free_unique')
    try:
        budget = face.interior._Budget(owner.deadline)
        with pytest.raises(ValueError, match='prospective exact source'):
            direction._merit_candidate(owner, {'status': 'failed'}, policy(),
                policy()['epsilon_floor'], budget)
        assert budget.calls == budget.steps == budget.evaluations == 0
    finally:
        owner.close()


def test_lower_budget_clamps_owner_before_derivative_construction(monkeypatch):
    owner, q = owner_and_model('free_unique')
    try:
        budget = face.interior._Budget(owner.deadline)
        budget.deadline = monotonic()-1.
        monkeypatch.setattr(face, '_CanonicalFaceLinearization', lambda *a: pytest.fail('expired budget constructed derivative'))
        record = direction._native_direction(owner, q, policy(), 17, policy()['epsilon_floor'], budget)
        assert owner.deadline == budget.deadline
        assert record['status'] == 'failed' and record['reason'] == 'wall_cap'
        assert record['disposed'] and not record['cg']
    finally:
        owner.close()


def test_feasible_scale_exact_fraction_and_outward_bound_refusal():
    owner, q = owner_and_model('free_unique')
    try:
        p = np.full(len(q), 7.)
        budget = face.interior._Budget(owner.deadline)
        result = direction._feasible_scale(owner, q, p, budget)
        expected = min(Fraction(1), *((Fraction(1.5)-Fraction(float(v)))/7 for v in q))
        assert Fraction(result['exact_ratio']) == expected
        assert Fraction(result['alpha0']) <= expected
        assert np.all(q+result['alpha0']*.5*p <= 1.5)
        q[0] = -1.5; p[0] = -1.
        result = direction._feasible_scale(owner, q, p, budget)
        assert result['alpha0'] == 0. and result['exact_ratio'] == '0'
        assert budget.calls == budget.steps == 0
    finally:
        owner.close()
