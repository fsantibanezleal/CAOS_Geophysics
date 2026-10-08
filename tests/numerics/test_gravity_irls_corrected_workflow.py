"""Real complete calibration/export/refit/evaluation, sealed outer controls."""
from copy import deepcopy

import numpy as np
import pytest

import gravity_irls_corrected as corrected
import gravity_irls_corrected_workflow as workflow
import gravity_irls_pool as pool
import gravity_workflow_io as transport
from test_gravity_irls import policy
from test_gravity_l2_selection import calibration_request, outer_request


def request():
    value = calibration_request()
    value.update(schema=workflow.REQUEST_SCHEMA, runtime_epoch=corrected.RUNTIME_EPOCH)
    value['policy'].update(name=corrected.POLICY, irls=policy())
    return value


@pytest.fixture(scope='module')
def actual():
    req = request()
    result = workflow.calibrate(req)
    return req, result


def test_complete_original_folds_refit_and_lossless_replay(actual, tmp_path):
    req, result = actual
    assert len(result['fits']) == 25 and result['selected_index'] == 7 and result['selection_status'] == 'selected'
    assert all(c['eligible'] and c['score_q'] == 0. for c in result['candidates'])
    for index, encoded in enumerate(result['fits']):
        raw = pool.decode(encoded)
        assert raw['terminal']['status'] == 'converged' and len(raw['stages']) == 21
        assert raw['iterations'] == 0 and raw['auxiliary_calls'] == 0
        rows = req['plan']['folds'][index%3]['fit_rows'] if index < 24 else req['plan']['development_rows']
        assert np.array_equal(raw['initialization']['fit_rows'], rows)
        assert not set(rows) & set(req['plan']['outer_rows'])
    workflow.validate(result, req)
    wrapper = dict(schema='gravity-calibration-archive-1', request=req, result=result)
    path = transport.publish_archive(tmp_path/'data', tmp_path/'temp', 'corrected.gza', wrapper)
    restored = transport.read_archive(tmp_path/'data', path.name)
    workflow.validate(restored['result'], restored['request'])


def test_outer_never_refits_or_changes_recipe(actual, monkeypatch):
    req, result = actual
    def denied(*args, **kwargs):
        pytest.fail('frozen evaluation called optimization/refit')
    monkeypatch.setattr(corrected, 'solve_partition', denied)
    monkeypatch.setattr(workflow, 'calibrate', denied)
    outer = outer_request(result)
    outer.update(schema=workflow.EVALUATION_SCHEMA, calibration_request=req)
    first = workflow.evaluate(outer)
    assert first['wrms'] == 0.
    outer['observations']['gz_up_mgal'][:] = .03
    outer['observations']['values_sha256'] = workflow.survey._digest({k:v for k,v in outer['observations'].items() if k != 'values_sha256'})
    second = workflow.evaluate(outer)
    assert second['wrms'] == 3. and second['prediction_quality'] == 'poor_under_declared_noise'
    np.testing.assert_array_equal(first['predicted_mgal'], second['predicted_mgal'])
    assert first['calibration_sha256'] == second['calibration_sha256'] == result['result_sha256']


@pytest.mark.parametrize('fault', ['score', 'status', 'source', 'scope', 'scope_int', 'candidate_bool', 'fold_bool', 'selected_float'])
def test_rehashed_workflow_refusal(actual, fault):
    req, result = actual
    changed = deepcopy(result)
    if fault == 'score':
        changed['candidates'][0]['score_q'] = 1.
    if fault == 'status':
        changed['candidates'][0]['folds'][0]['status'] = 'failed'
    if fault == 'source':
        changed['source_inventory']['gravity_irls_corrected_workflow'] = 'f'*64
    if fault == 'scope':
        changed['scope']['full_M02_accepted'] = True
    if fault == 'scope_int':
        changed['scope']['full_M02_accepted'] = 0
    if fault == 'candidate_bool':
        changed['candidates'][0]['index'] = False
    if fault == 'fold_bool':
        changed['candidates'][0]['folds'][0]['solve'] = False
    if fault == 'selected_float':
        changed['selected_index'] = 7.
    changed['result_sha256'] = workflow.survey._digest({k:v for k,v in changed.items() if k != 'result_sha256'})
    with pytest.raises(ValueError):
        workflow.validate(changed, req)


def test_whole_clock_expiry_no_native_optimizer(monkeypatch):
    clock_calls = []
    def clock():
        clock_calls.append(1)
        return 0. if len(clock_calls) == 1 else 1801.
    monkeypatch.setattr(workflow, 'monotonic', clock)
    monkeypatch.setattr(corrected, 'solve_partition', lambda *args: pytest.fail('expired workflow launched optimizer'))
    req = request()
    result = workflow.calibrate(req)
    assert result['selection_status'] == 'insufficient_candidates' and len(result['fits']) == 24
    assert all(pool.decode(f)['schema'] == 'gravity-corrected-unstarted-1' for f in result['fits'])
    workflow.validate(result, req)


def test_actual_cli_calibration_verify_and_frozen_evaluation(tmp_path, monkeypatch, capsys):
    root, temp = tmp_path/'data', tmp_path/'temp'
    req = request()
    transport.publish_archive(root, temp, 'request.gza', req)
    args = ['--data-root', str(root), '--temp-root', str(temp)]
    assert transport.main(['calibrate', *args, '--input', 'request.gza', '--output', 'calibration.gza']) == 0
    actual = transport.read_archive(root, 'calibration.gza')
    assert actual['result']['selection_status'] == 'selected' and len(actual['result']['fits']) == 25
    monkeypatch.setattr(corrected, 'solve_partition', lambda *args: pytest.fail('replay/evaluation launched solver'))
    assert transport.main(['verify', *args, '--input', 'calibration.gza']) == 0
    outer = outer_request(actual['result'])
    outer.update(schema=workflow.EVALUATION_SCHEMA, calibration_request=req)
    transport.publish_archive(root, temp, 'outer.gza', outer)
    assert transport.main(['evaluate', *args, '--input', 'outer.gza', '--output', 'evaluation.gza']) == 0
    assert transport.main(['verify', *args, '--input', 'evaluation.gza']) == 0
    assert transport.read_archive(root, 'evaluation.gza')['result']['wrms'] == 0.
    assert 'transport_replay' in capsys.readouterr().out
    with pytest.raises(FileExistsError):
        transport.main(['evaluate', *args, '--input', 'outer.gza', '--output', 'evaluation.gza'])
