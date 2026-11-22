"""Closed source epoch/workflow, original sealed outer and transport controls."""
from copy import deepcopy

import pytest

import gravity_irls_original as public
import gravity_irls_pool as pool
import gravity_irls_corrected_workflow as workflow
import gravity_workflow_io as transport
from test_gravity_irls import policy
from test_gravity_l2_selection import calibration_request, outer_request


def request():
    req = calibration_request()
    req.update(schema=public.REQUEST_SCHEMA, runtime_epoch=public.RUNTIME_EPOCH)
    req['policy'].update(name=public.POLICY, irls=policy())
    return req


@pytest.fixture(scope='module')
def actual():
    req = request()
    return req, public.calibrate(req)


def test_expired_original24_clock_exports_wall_cap_without_solver(monkeypatch):
    clock_calls = []

    def clock():
        clock_calls.append(1)
        return 0. if len(clock_calls) == 1 else 1801.

    monkeypatch.setattr(workflow, 'monotonic', clock)
    monkeypatch.setattr(public, 'solve_partition',
        lambda *args, **kwargs: pytest.fail('expired original24 workflow launched optimizer'))
    result = public.calibrate(request())
    assert result['wall_seconds'] == 1801.
    assert result['selection_status'] == 'insufficient_candidates'
    assert len(result['fits']) == 24
    raw = [pool.decode(fit) for fit in result['fits']]
    assert all(fit['schema'] == 'gravity-corrected-unstarted-1'
        and fit['reason'] == 'wall_cap' for fit in raw)


def test_source_correct_all25_null_fits_export_and_frozen_outer(actual, tmp_path, monkeypatch):
    req, result = actual
    assert result['schema'] == public.RESULT_SCHEMA and result['runtime_epoch'] == public.RUNTIME_EPOCH
    assert result['selection_status'] == 'selected' and result['selected_index'] == 7 and len(result['fits']) == 25
    for encoded in result['fits']:
        raw = pool.decode(encoded)
        assert raw['terminal']['status'] == 'converged' and len(raw['stages']) == 21
        assert raw['iterations'] == 0 and raw['wall_seconds'] <= 120.
    public.validate(result, req)
    wrapper = dict(schema='gravity-calibration-archive-1', request=req, result=result)
    archive = transport.publish_archive(tmp_path/'data', tmp_path/'temp', 'actual.gza', wrapper)
    transport.verify_calibration(transport.read_archive(tmp_path/'data', archive.name))
    monkeypatch.setattr(public, 'solve_partition', lambda *a, **k: pytest.fail('replay/outer called optimizer'))
    monkeypatch.setattr(public.original.reduced.core, '_solve', lambda *a, **k: pytest.fail('replay/outer called minimize'))
    outer = outer_request(result)
    outer.update(schema=public.EVALUATION_SCHEMA, calibration_request=req)
    evaluated = public.evaluate(outer)
    assert evaluated['wrms'] == 0. and evaluated['schema'] == public.EVALUATION_RESULT_SCHEMA
    assert evaluated['calibration_sha256'] == result['result_sha256']


@pytest.mark.parametrize('fault', ['source','score','scope','cpu2_epoch'])
def test_actual_rehashed_denials(actual, fault):
    req, result = actual
    changed = deepcopy(result)
    if fault == 'source':
        changed['source_inventory']['gravity_irls_original.py'] = 'f'*64
    if fault == 'score':
        changed['candidates'][0]['score_q'] = 1.
    if fault == 'scope':
        changed['scope']['full_M02_accepted'] = True
    if fault == 'cpu2_epoch':
        changed['runtime_epoch'] = 'm02-survey-irls-cpu-2'
    changed['result_sha256'] = public.original.physics.survey._digest({k:v for k,v in changed.items() if k!='result_sha256'})
    with pytest.raises(ValueError):
        public.validate(changed, req)
