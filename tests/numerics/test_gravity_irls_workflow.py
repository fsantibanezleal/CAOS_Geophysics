"""Complete actual supplied IRLS workflow, including retained failure controls."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from dataclasses import replace
from time import monotonic

import pytest

import gravity_irls as irls
import gravity_l2 as l2
import gravity_survey_l2 as survey


def _controls(name):
    spec = importlib.util.spec_from_file_location('_workflow_'+name,
        Path(__file__).with_name(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request():
    value = _controls('test_gravity_l2_selection').calibration_request()
    value['schema'] = 'gravity-survey-irls-calibration-request-1'
    value['runtime_epoch'] = irls.RUNTIME_EPOCH
    value['policy']['name'] = irls.POLICY
    value['policy']['irls'] = _controls('test_gravity_irls').policy()
    return value


@pytest.fixture(scope='module')
def native_result():
    req = request()
    return req, irls.calibrate_gravity_irls(req)


def outer_request(req, result):
    value = _controls('test_gravity_l2_selection').outer_request(result)
    value['schema'] = 'gravity-survey-irls-evaluation-request-3'
    value['calibration_request'] = req
    return value


def test_full_native_null_selection_refit_and_replay(native_result):
    req, result = native_result
    assert result['schema'] == 'gravity-survey-irls-calibration-result-3'
    assert len(result['candidates']) == 8 and len(result['stage_books']) == 25
    assert result['selection_status'] == 'selected' and result['selected_index'] == 7
    assert result['fits'][result['final_solve']]['reason'] == 'irls_stationary_null'
    assert all(c['eligible'] and c['score_q'] == 0. for c in result['candidates'])
    for i,candidate in enumerate(result['candidates']):
        for j,fold in enumerate(candidate['folds']):
            solved = result['fits'][fold['solve']]
            assert solved['stages'] == 3*i+j
            assert solved['iterations'] == 0
            assert result['stage_books'][solved['stages']]['count'] == 21
            assert solved['irls_terminal']['weight_updates'] == 20
    l2._result_native_metadata(result)
    assert irls.validate_gravity_irls(result,req)['result_sha256'] == result['result_sha256']
    assert result['scope']['field_eligible'] is result['scope']['full_M02_accepted'] is False


@pytest.mark.parametrize('fault',['fold','refit'])
def test_failed_fold_and_selected_refit_retained(monkeypatch,fault):
    native = irls._solve_partition
    calls = []
    def failed(*args,**kwargs):
        solved = native(*args,**kwargs)
        index = len(calls)
        calls.append(index)
        if index == (0 if fault == 'fold' else 24):
            solved['irls_terminal'].update(status='nonconverged',reason='wall_cap')
        return solved
    monkeypatch.setattr(irls,'_solve_partition',failed)
    result = irls.calibrate_gravity_irls(request())
    assert len(calls) == 25
    if fault == 'fold':
        assert result['candidates'][0]['score_q'] is None
        assert not result['candidates'][0]['eligible']
        assert result['selection_status'] == 'selected'
    else:
        assert result['selection_status'] == 'final_nonconverged'
        assert result['selected_index'] == 7
        with pytest.raises(ValueError): irls.evaluate_gravity_irls(outer_request(request(),result))


def test_outer_evaluation_no_refit_and_rehashed_tamper(native_result,monkeypatch):
    req, result = native_result
    def denied(*args,**kwargs): raise AssertionError('evaluation ran optimizer')
    monkeypatch.setattr(irls,'_solve_partition',denied)
    monkeypatch.setattr(irls.optimizer,'solve_bounded_physical',denied)
    monkeypatch.setattr(l2,'_solve_partition',denied)
    value = outer_request(req,result)
    evaluated = irls.evaluate_gravity_irls(value)
    assert evaluated['wrms'] == 0. and evaluated['field_truth'] is None
    value = deepcopy(value)
    value['observations']['gz_up_mgal'][:] = .03
    value['observations']['values_sha256'] = survey._digest({
        k:v for k,v in value['observations'].items() if k!='values_sha256'})
    assert irls.evaluate_gravity_irls(value)['wrms'] == 3.
    for fault in ('weight','metric','terminal','prediction'):
        bad = deepcopy(result)
        if fault == 'weight': bad['stage_books'][0]['smallness_weights'][0,0] *= 2.
        if fault == 'metric': bad['stage_books'][0]['metrics']['values'][0] = 1.
        if fault == 'terminal': bad['fits'][bad['final_solve']]['irls_terminal']['stage_changes'][-1]['weights_relative'] = .1
        if fault == 'prediction': bad['predictions']['gz_up_mgal'][0] += .1
        bad['result_sha256'] = survey._digest({k:v for k,v in bad.items() if k!='result_sha256'})
        with pytest.raises(ValueError): irls.validate_gravity_irls(bad,req)


@pytest.mark.parametrize('fault',['duplicate','missing','unused','oversize','legacy'])
def test_complete_guard_and_book_reference_negatives(native_result,fault):
    req, result = native_result
    bad = deepcopy(result)
    if fault == 'duplicate': bad['candidates'][0]['folds'][1]['solve'] = 0
    if fault == 'missing': bad['stage_books'] = bad['stage_books'][:-1]
    if fault == 'unused': bad['stage_books'] += (bad['stage_books'][0],)
    if fault == 'oversize': bad['extra'] = 'a'*262145
    if fault == 'legacy': bad['schema'] = 'gravity-survey-l2-calibration-result-1'
    bad['result_sha256'] = survey._digest({k:v for k,v in bad.items() if k!='result_sha256'})
    with pytest.raises((ValueError,TypeError)): irls.validate_gravity_irls(bad,req)


def test_native_unstarted_terminal_stage_has_no_fabricated_metrics(monkeypatch):
    req=request();admitted=irls._admit_request(req)
    native=irls.optimizer.solve_bounded_physical
    def expired(*args,**kwargs):
        kwargs['budget']=replace(kwargs['budget'],deadline=monotonic()-1.)
        return native(*args,**kwargs)
    monkeypatch.setattr(irls.optimizer,'solve_bounded_physical',expired)
    rows=admitted['plan']['development_rows']
    fit,book=irls._workflow_fit(admitted['plan']['request'],admitted['observations']['gz_up_mgal'],
        {k:admitted['noise'][k] for k in ('kind','values')},admitted['prior'],rows,1000.,rows,
        admitted['policy']['irls'],monotonic()+60.,0)
    assert fit['status']=='nonconverged' and fit['reason']=='wall_cap'
    assert fit['model_kg_m3'] is not None and fit['phi_d'] is fit['kkt_normalized'] is None
    assert fit['iterations']==0 and book['count']==1
    irls._fit_metadata(fit,len(admitted['prior']['start_kg_m3']),rows,1000.)
    irls._replay_fit(fit,book,admitted,rows,1000.)
