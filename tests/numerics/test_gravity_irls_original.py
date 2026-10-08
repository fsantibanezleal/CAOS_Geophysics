"""Prospective original-noise IRLS: unchanged positive assertions/caps."""
import json
import os
from pathlib import Path
from time import monotonic

import numpy as np
import pytest

import gravity_irls_original as public
import gravity_irls_pool as pool
from test_gravity_irls import policy
from test_gravity_l2 import tiny, noise
from test_gravity_l2_selection import locked_request


def checks(result):
    assert result['runtime_epoch'] == public.RUNTIME_EPOCH
    assert result['terminal']['status'] == 'converged', result['terminal']
    assert result['initialization']['status'] == 'converged'
    assert result['wall_seconds'] <= 120.
    assert result['iterations'] <= 200 and len(result['models_q']) == result['iterations']+1
    assert len(result['stages']) == 21 and result['terminal']['weight_updates'] == 20
    assert all(s['inner']['status'] == 'converged' for s in result['stages'])
    assert all(s['epsilon'] == policy()['epsilon_floor'] for s in result['stages'][17:])
    assert all(c['model_relative'] <= 1e-6 and c['weights_relative'] <= 1e-6
        for c in result['terminal']['stage_changes'][-3:])
    assert result['stages'][-1]['canonical_weight_mismatch'] <= 1e-6
    assert result['stages'][-1]['canonical_absolute_kkt'] <= 1e-12 or result['stages'][-1]['canonical_normalized_kkt'] <= 1e-5
    assert result['allocation_plan']['admitted_bytes'] <= 2*1024**3
    anchors = sum(a['outcome'] == 'adopted' for a in result['attempts'])
    calls = sum(len(a['cg']) for a in result['attempts'])
    assert anchors <= 63 and calls <= 126
    assert result['iterations'] == result['initialization']['iterations']+anchors+sum(s['inner']['iterations'] for s in result['stages'])
    for raw in map(pool.decode, (result['initialization_evidence'], *result['native_evidence'])):
        counts = {}
        for phase in raw['conditioning_attempts']:
            assert phase['failure'] is None and phase['true_relative_residual'] <= 1e-6
            counts[phase['iteration']] = counts.get(phase['iteration'], 0)+phase['iterations']
        assert max(counts.values(), default=0) <= 200
        assert all(t['trial'] < 20 for t in raw['line_search_trials'])
        assert raw['terminal_audits'][-1]['check']['passed']
        assert raw['terminal_audits'][-1]['check']['disposed']
    for a in result['attempts']:
        if a['branch'] != 'interior_unique_nonzero_max':
            assert not a['cg'] and not a['trials'] and a['outcome'] == 'disabled'
        for c in a['cg']:
            assert c['relative_residual'] <= 1e-6 and c['info'] == 0 and c['iterations'] <= 200


@pytest.mark.parametrize('null', [True, False])
def test_original_positive_and_null(null, record_property):
    req, observed, prior, _, _ = tiny()
    req['mesh']['active'][:] = True
    for key, v in [('lower_kg_m3', -1500.), ('upper_kg_m3', 1500.),
                   ('start_kg_m3', 0.), ('reference_kg_m3', 0.)]:
        prior[key] = np.full(12, v)
    if null:
        observed = req['background_mgal'].copy()
    result = public.solve_partition(req, observed, noise(), prior, np.arange(4, dtype=np.int64), .01,
        policy=policy(), deadline=monotonic()+120.)
    record_property('actual_outcome', json.dumps(dict(terminal=result['terminal'],
        steps=result['iterations'], calls=result['auxiliary_calls'], wall=result['wall_seconds'])))
    checks(result)
    assert result['terminal']['reason'] == ('irls_stationary_null' if null else 'irls_fixed_point')
    if not null:
        # The original positive regression's absolute assertion remains literal.
        assert result['stages'][-1]['canonical_absolute_kkt'] <= 1e-12


def test_locked_original48_firstfold(record_property):
    req, _, _ = locked_request(0, 0)
    plan = req['plan']
    result = public.solve_partition(plan['request'], req['observations']['gz_up_mgal'],
        {k:req['noise'][k] for k in ('kind', 'values')}, req['prior'],
        plan['folds'][0]['fit_rows'], .0001, policy=policy(),
        observation_rows=plan['development_rows'], deadline=monotonic()+120.)
    outcome = dict(schema='original-irls-firstfold-1', source_pin=public.SOURCE_SHA256,
        runtime_epoch=public.RUNTIME_EPOCH, request_sha256=public.original.physics.survey._digest(req),
        terminal=result['terminal'], iterations=result['iterations'],
        calls=result['auxiliary_calls'], wall_seconds=result['wall_seconds'],
        initialization_status=result['initialization']['status'],
        stage_statuses=[dict(index=s['index'], status=s['inner']['status'], reason=s['inner']['reason'],
            steps=s['inner']['iterations'], kkt=s['canonical_normalized_kkt'],
            weight_mismatch=s['canonical_weight_mismatch']) for s in result['stages']])
    record_property('original_firstfold_actual', json.dumps(outcome, allow_nan=False))
    receipt = Path(os.environ['GEOPHYSICS_M02_IRLS_FIRSTFOLD_RECEIPT'])
    with receipt.open('x', encoding='utf8') as f:
        json.dump(outcome, f, sort_keys=True, allow_nan=False)
    checks(result)


def test_closed_no_callback_or_post_disposal_action():
    req, obs, prior, _, _ = tiny()
    with pytest.raises(TypeError):
        public.solve_partition(req, obs, noise(), prior, np.arange(4, dtype=np.int64), .01,
            policy=policy(), deadline=monotonic()+120., metric=lambda q: q)
    owner = public.GravityIRLSPartition(req, obs, noise(), prior, np.arange(4, dtype=np.int64), .01,
        deadline=monotonic()+120.)
    owner.close()
    with pytest.raises(ValueError, match='disposed'):
        owner.initialize()
