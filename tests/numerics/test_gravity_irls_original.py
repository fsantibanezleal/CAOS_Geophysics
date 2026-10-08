"""Prospective original-noise IRLS: unchanged positive assertions/caps."""
import json
import os
from pathlib import Path
from time import monotonic

import numpy as np
import pytest
import choclo
from scipy.optimize import lsq_linear

import gravity_irls_original as public
import gravity_irls_pool as pool
import gravity_workflow_io as transport
from test_gravity_irls import policy
from test_gravity_l2 import tiny, noise, independent_r
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
    public.validate_partition(result, req, observed, noise(), prior, np.arange(4, dtype=np.int64), .01,
        policy=policy())


def test_locked_original48_firstfold(record_property, tmp_path):
    req, _, _ = locked_request(0, 0)
    plan = req['plan']
    result = public.solve_partition(plan['request'], req['observations']['gz_up_mgal'],
        {k:req['noise'][k] for k in ('kind', 'values')}, req['prior'],
        plan['folds'][0]['fit_rows'], .0001, policy=policy(),
        observation_rows=plan['development_rows'], deadline=monotonic()+120.)
    outcome = dict(schema='original-irls-firstfold-1', accepted=False, source_pin=public.SOURCE_SHA256,
        runtime_epoch=public.RUNTIME_EPOCH, request_sha256=public.original.physics.survey._digest(req),
        terminal=result['terminal'], iterations=result['iterations'],
        calls=result['auxiliary_calls'], wall_seconds=result['wall_seconds'],
        initialization_status=result['initialization']['status'],
        stage_statuses=[dict(index=s['index'], status=s['inner']['status'], reason=s['inner']['reason'],
            steps=s['inner']['iterations'], kkt=s['canonical_normalized_kkt'],
            weight_mismatch=s['canonical_weight_mismatch']) for s in result['stages']])
    receipt = Path(os.environ['GEOPHYSICS_M02_IRLS_FIRSTFOLD_RECEIPT'])
    try:
        # Preserve ALL actual states/failed trials before science/replay can fail.
        saved = transport.publish_archive(tmp_path/'data', tmp_path/'temp', 'original48.gza',
            dict(schema='gravity-original-partition-archive-1', request=req,
                policy=policy(), partition=pool.encode_compact(result)))
        outcome['native_archive'] = str(saved)
        outcome['native_archive_sha256'] = public.hashlib.sha256(saved.read_bytes()).hexdigest()
        checks(result)
        public.validate_partition(result, plan['request'], req['observations']['gz_up_mgal'],
            {k:req['noise'][k] for k in ('kind', 'values')}, req['prior'], plan['folds'][0]['fit_rows'],
            .0001, policy=policy(), observation_rows=plan['development_rows'])
        rows, prior = plan['folds'][0]['fit_rows'], req['prior']
        bounds = plan['geometry']['active_cell_bounds_m']
        j = np.array([[choclo.prism.gravity_u(*p, *b, 1.)*1e5 for b in bounds]
                      for p in plan['request']['stations']['receivers_m'][rows]])
        r = independent_r(bounds, prior['lengths_m'], prior['density_scale_kg_m3']/1000.)
        positions = np.searchsorted(plan['development_rows'], rows)
        sd = req['noise']['values'][positions]
        whitened = j*1000./sd[:, None]
        data = (req['observations']['gz_up_mgal'][positions]-plan['request']['background_mgal'][rows])/sd
        reference = prior['reference_kg_m3']/1000.
        errors = []
        for stage in result['stages']:
            adopted = result['models_q'][stage['adopted_row']]
            x, epsilon = adopted-reference, stage['epsilon'][0]
            weights = np.sqrt(float(np.max(abs(x)))**2+epsilon**2)/np.sqrt(x*x+epsilon**2)
            np.testing.assert_allclose(weights, stage['adopted_weights'], rtol=1e-14, atol=0.)
            factor_r = r.copy()
            factor_r[:len(reference)] *= np.sqrt(weights)[:, None]
            factor = np.vstack([whitened, np.sqrt(len(rows)*.0001)*factor_r])
            rhs = np.r_[data, np.sqrt(len(rows)*.0001)*factor_r@reference]
            oracle = lsq_linear(factor, rhs, bounds=(prior['lower_kg_m3']/1000., prior['upper_kg_m3']/1000.),
                method='bvls', lsq_solver='exact', tol=1e-12, max_iter=1000)
            assert oracle.success
            q = stage['inner']['q']
            error = q-oracle.x
            e = dict(model_relative=float(np.linalg.norm(error)/max(1., np.linalg.norm(oracle.x))),
                physical_model_relative=float(np.max(abs(error*1000.))/max(1., np.max(abs(oracle.x*1000.)))),
                objective_relative=float(abs(np.linalg.norm(factor@q-rhs)**2-2*oracle.cost)/max(1., 2*oracle.cost)),
                physical_prediction_absolute=float(np.max(abs(j@(1000.*error)))))
            errors.append(e)
            assert e['model_relative'] <= 1e-3 and e['physical_model_relative'] <= 1e-5
            assert e['objective_relative'] <= 1e-6 and e['physical_prediction_absolute'] <= 1e-6
        outcome.update(accepted=True, independent_stage_errors=errors)
    finally:
        record_property('original_firstfold_actual', json.dumps(outcome, allow_nan=False))
        with receipt.open('x', encoding='utf8') as f:
            json.dump(outcome, f, sort_keys=True, allow_nan=False)


def test_closed_no_callback_or_post_disposal_action():
    req, obs, prior, _, _ = tiny()
    with pytest.raises(TypeError):
        public.solve_partition(req, obs, noise(), prior, np.arange(4, dtype=np.int64), .01,
            policy=policy(), deadline=monotonic()+120., metric=lambda q: q)
    owner = public.GravityIRLSPartition(req, obs, noise(), prior, np.arange(4, dtype=np.int64), .01,
        deadline=monotonic()+120.)
    owner.close()
    assert owner.problem is owner.prior is owner.noise is owner.positions is None
    with pytest.raises(ValueError, match='disposed'):
        owner.initialize()
