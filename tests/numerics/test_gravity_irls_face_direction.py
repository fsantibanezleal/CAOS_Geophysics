"""Closed native direction controls, not native fit/recurrence acceptance."""
from time import monotonic
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest
from fractions import Fraction

import gravity_irls_face as face
import gravity_irls_face_direction as direction
from test_gravity_irls_face_source import owner_and_model, policy


def _retain_native_record(branch, phase, record, budget):
    """Optional immutable external evidence, including actual failed rows.

    This TEST-only transport is not a solver/certificate authority. It keeps
    exact float bits, array dtype/shape/bytes, every attempted CG/trial and the
    actual combined counters before an assertion can truncate a failure.
    """
    output_name = os.environ.get('GEOPHYSICS_M02_FACE_DIRECTION_OUTPUT')
    if output_name is None:
        return
    root_name = os.environ.get('GEOPHYSICS_M02_FACE_RESEARCH_TEMP_ROOT')
    assert root_name and Path(root_name).is_absolute() and Path(output_name).is_absolute()
    root, output = Path(root_name).resolve(), Path(output_name).resolve()
    repository = Path(__file__).resolve().parents[2]
    assert root.is_dir() and not root.is_relative_to(repository)
    assert not repository.is_relative_to(root)
    assert output.is_relative_to(root) and output != root
    assert branch in ('binding_plateau', 'binding_unique', 'free_unique', 'free_unique_with_binding')
    assert phase in ('direction', 'merit_direction', 'merit_candidate')
    def encode(value):
        if isinstance(value, np.ndarray):
            assert value.dtype.kind in 'bifu' and value.nbytes <= 2*1024**2
            return {'array_dtype': value.dtype.str, 'shape': list(value.shape),
                'bytes_hex': value.tobytes(order='C').hex()}
        if type(value) is float:
            return {'float_hex': value.hex()}
        if value is None or type(value) in (str, bool, int):
            return value
        if type(value) is dict:
            assert all(type(key) is str for key in value)
            return {key: encode(item) for key, item in value.items()}
        if type(value) in (list, tuple):
            return {'sequence_kind': type(value).__name__, 'values': [encode(v) for v in value]}
        raise TypeError('literal native research transport type')
    body = encode(dict(branch=branch, phase=phase, record=record,
        combined_counters=dict(calls=budget.calls, steps=budget.steps,
            evaluations=budget.evaluations,
            stage_proposals=tuple(getattr(budget, '_face_stage_calls', {}).items()))))
    # Stage counter integer keys are not a product DTO. Preserve their literal
    # identity in this research envelope instead of silently string-coercing.
    payload = json.dumps(body, sort_keys=True, allow_nan=False, indent=2).encode('utf-8')
    assert len(payload) <= 2*1024**2
    output.mkdir(parents=True, exist_ok=True)
    with (output/f'{branch}-{phase}.json').open('xb') as stream:
        stream.write(payload)
    with (output/f'{branch}-{phase}.sha256').open('x', encoding='ascii') as stream:
        stream.write(hashlib.sha256(payload).hexdigest()+'\n')


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
        _retain_native_record(branch, 'direction', record, budget)
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


def test_external_record_is_exact_immutable_and_never_repo_or_device_root(tmp_path, monkeypatch):
    # Test-owned temporary fixture only; this function executes no native CG.
    external = tmp_path.resolve()
    monkeypatch.setenv('GEOPHYSICS_M02_FACE_RESEARCH_TEMP_ROOT', str(external))
    output = external/'records'
    monkeypatch.setenv('GEOPHYSICS_M02_FACE_DIRECTION_OUTPUT', str(output))
    budget = face.interior._Budget(monotonic()+120.)
    budget._face_stage_calls = {17: 1}
    record = dict(status='failed', reason='actual_refusal', disposed=True,
        cg=(dict(rhs=np.array([.1, -.0]), solution=None, info=None),),
        seconds=.25, trials=())
    _retain_native_record('binding_plateau', 'direction', record, budget)
    payload = (output/'binding_plateau-direction.json').read_bytes()
    body = json.loads(payload)
    assert body['record']['seconds'] == {'float_hex': .25.hex()}
    rhs = body['record']['cg']['values'][0]['rhs']
    assert rhs == dict(array_dtype='<f8', shape=[2], bytes_hex=np.array([.1, -.0]).tobytes().hex())
    assert body['combined_counters']['stage_proposals']['values'][0]['values'] == [17, 1]
    assert (output/'binding_plateau-direction.sha256').read_text().strip() == hashlib.sha256(payload).hexdigest()
    with pytest.raises(FileExistsError):
        _retain_native_record('binding_plateau', 'direction', record, budget)
    monkeypatch.setenv('GEOPHYSICS_M02_FACE_DIRECTION_OUTPUT', str(external))
    with pytest.raises(AssertionError):
        _retain_native_record('binding_plateau', 'direction', record, budget)
    monkeypatch.setenv('GEOPHYSICS_M02_FACE_DIRECTION_OUTPUT', str(Path(__file__).resolve().parents[2]/'records'))
    with pytest.raises(AssertionError):
        _retain_native_record('binding_plateau', 'direction', record, budget)


@pytest.mark.parametrize('branch', ['binding_unique', 'free_unique', 'free_unique_with_binding'])
def test_actual_library_cg_merit_alltrial_replay_and_adversaries(branch):
    owner, q = owner_and_model(branch)
    try:
        budget = face.interior._Budget(owner.deadline)
        native = direction._native_direction(owner, q, policy(), 17, policy()['epsilon_floor'], budget)
        _retain_native_record(branch, 'merit_direction', native, budget)
        assert native['status'] == 'direction', native
        calls = budget.calls
        candidate = direction._merit_candidate(owner, native, policy(), policy()['epsilon_floor'], budget)
        _retain_native_record(branch, 'merit_candidate', candidate, budget)
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


def test_principal_metric_keeps_full_native_vector_abi():
    owner, q = owner_and_model('binding_plateau')
    derivative = None
    try:
        derivative = face._CanonicalFaceLinearization(owner, q, policy(), 17, policy()['epsilon_floor'])
        free = derivative.face['free']
        assert 0 < len(free) < len(q)
        metric = derivative.metric()
        value = np.linspace(.017, -.023, len(free))
        # Exact source ABI refusal explains the prior failed first direction;
        # it is not a reason to change native shape authority or solve H dense.
        with pytest.raises(ValueError, match='exact native CG vector'):
            metric.apply(value)
        embedded = np.zeros(len(q)); embedded[free] = value
        result = metric.apply(embedded)
        assert result.shape == q.shape and np.all(result[derivative.face['binding']] == 0.)
        # Natural IC0/Joseph is SPD, not the exact inverse of native M.
        # True M residual1e-6 belongs to each ACTUAL CG, not this metric ABI.
        assert np.inner(value, result[free]) > 0.
        other = np.linspace(-.011, .037, len(free))
        embedded_other = np.zeros(len(q)); embedded_other[free] = other
        transformed_other = metric.apply(embedded_other)[free]
        np.testing.assert_allclose(np.inner(value, transformed_other),
            np.inner(other, result[free]), rtol=1e-12, atol=1e-13)
        assert not derivative.record['native_fit_accepted']
    finally:
        if derivative is not None:
            derivative.close()
        owner.close()
