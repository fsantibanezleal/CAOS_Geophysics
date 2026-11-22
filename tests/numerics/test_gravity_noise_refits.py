"""Actual fixed-development refits and scientific/transport negative gates."""
from copy import deepcopy

import numpy as np
import pytest

import gravity_l2 as l2
import gravity_irls as irls
import gravity_noise_refits as refits
import gravity_survey_l2 as survey
from test_gravity_l2_selection import calibration_request
from test_gravity_irls_workflow import request as irls_request


@pytest.fixture(scope='module')
def actual():
    req=calibration_request()
    frozen=l2.calibrate_gravity_l2(req)
    return req,frozen,refits.refit_gravity_noise(req,frozen)


def test_actual_frozen_refits(actual,monkeypatch):
    req,frozen,result=actual
    fits=refits._decode_records(result['records'])['fits']
    assert result['count']==32 and len(fits)==32
    assert np.any(result['targets_mgal']!=req['observations']['gz_up_mgal'])
    assert all(f['beta_candidate']==1000. for f in fits)
    assert all(np.array_equal(f['fit_rows'],frozen['plan']['development_rows']) for f in fits)
    assert all(np.array_equal(f['trace']['models_kg_m3'][0],req['prior']['start_kg_m3']) for f in fits)
    assert any(f['iterations']>0 for f in fits)
    before=frozen['result_sha256']
    def denied(*args,**kwargs): raise AssertionError('refit replay optimized')
    monkeypatch.setattr(l2,'_solve_partition',denied)
    refits.validate_noise_refits(result,req,frozen)
    assert before==frozen['result_sha256']
    assert result['posterior'] is result['coverage_calibrated'] is False
    assert result['field_truth'] is None


@pytest.mark.parametrize('fault',('target','beta','missing','success','coverage'))
def test_rehashed_refit_negatives(actual,fault):
    req,frozen,value=actual
    bad=deepcopy(value)
    if fault=='target': bad['targets_mgal'][0,0]+=.01
    if fault=='beta': bad['beta_candidate']=1.
    if fault=='missing':
        decoded=refits._decode_records(bad['records'])
        bad['records']=refits._records(decoded['fits'][:-1],decoded['stage_books'])
    if fault=='success': bad['successful'][0]=not bad['successful'][0]
    if fault=='coverage': bad['coverage_calibrated']=True
    bad['result_sha256']=survey._digest({k:v for k,v in bad.items() if k!='result_sha256'})
    with pytest.raises(ValueError): refits.validate_noise_refits(bad,req,frozen)


def test_refits_refuse_unselected_before_drawing(monkeypatch):
    req=calibration_request()
    frozen=l2.calibrate_gravity_l2(req)
    monkeypatch.setattr(refits.workflow,'verify_calibration',lambda value:value)
    frozen['selection_status']='insufficient_candidates'
    def denied(*args,**kwargs): raise AssertionError('unselected result drew noise or fit')
    monkeypatch.setattr(refits,'_targets',denied)
    monkeypatch.setattr(l2,'_run_fit',denied)
    with pytest.raises(ValueError): refits.refit_gravity_noise(req,frozen)


def test_actual_irls_failed_refits_retained_and_replayed(tmp_path):
    req=irls_request()
    frozen=irls.calibrate_gravity_irls(req)
    actual=refits.refit_gravity_noise(req,frozen)
    records=refits._decode_records(actual['records'])
    assert len(records['fits'])==len(records['stage_books'])==32
    assert any(f['status']!='converged' for f in records['fits'])
    refits.workflow.publish_archive(tmp_path/'data',tmp_path/'temp','actual-refits.gza',actual)
    # Plumbing verification of literal failures is not a passing convergence
    # expectation. The existing positive nonnull scientific gate remains red.
    refits.validate_noise_refits(actual,req,frozen)
    assert not np.all(actual['successful'])


@pytest.mark.parametrize('fault',['node_code','cycle','edge','node_padding','float_padding',
    'pool_span','duplicate_string','unused_string','dtype','length'])
def test_record_codec_complete_barrier(fault):
    book=deepcopy(refits._records(({'model':np.array([.1,.2]),'metric':.5},),()))
    if fault=='node_code': book['nodes'][0][0,0]=10
    elif fault=='cycle': book['edges'][0,1]=0
    elif fault=='edge': book['nodes'][0][0,1]=1
    elif fault=='node_padding': book['nodes'][0][-1,0]=1
    elif fault=='float_padding': book['floats'][-1,-1]=1.
    elif fault=='pool_span':
        nodes=book['nodes'][0]
        index=int(np.flatnonzero(nodes[:,0]==5)[0]);nodes[index,1]=1
    elif fault=='duplicate_string': book['strings']=(*book['strings'],book['strings'][0])
    elif fault=='unused_string': book['strings']=(*book['strings'],'unused')
    elif fault=='dtype': book['edges']=book['edges'].astype(np.int32)
    else: book['lengths'][0]=65537
    with pytest.raises((ValueError,TypeError)): refits._decode_records(book)


def test_record_codec_exact_float_bits_and_no_numeric_deduplication():
    array=np.array([np.nextafter(1.,2.),-0.,1e-300])
    value=({'one':array,'two':array.copy(),'tuple':(None,False,1,1.,'text')},)
    book=refits._records(value,())
    restored=refits._decode_records(book)
    np.testing.assert_array_equal(restored['fits'][0]['one'].view(np.uint64),array.view(np.uint64))
    assert not np.shares_memory(restored['fits'][0]['one'],restored['fits'][0]['two'])
    assert restored['fits'][0]['tuple']==(None,False,1,1.,'text')


def test_actual_l2_cli_refit_archive_and_no_optimizer_verification(actual,tmp_path,monkeypatch):
    req,frozen,_=actual
    data,temp=tmp_path/'data',tmp_path/'temp'
    refits.workflow.publish_archive(data,temp,'calibration.gza',
        {'schema':'gravity-calibration-archive-1','request':req,'result':frozen})
    args=['--data-root',str(data),'--temp-root',str(temp)]
    assert refits.workflow.main(['refit',*args,'--input','calibration.gza','--output','refits.gza']) in (0,2)
    retained=refits.workflow.read_archive(data,'refits.gza')
    assert len(refits._decode_records(retained['records'])['fits'])==32
    def denied(*a,**k): raise AssertionError('CLI verify optimized')
    monkeypatch.setattr(l2,'_solve_partition',denied)
    monkeypatch.setattr(irls,'_solve_partition',denied)
    assert refits.workflow.main(['verify',*args,'--input','refits.gza','--calibration','calibration.gza'])==0


def test_actual_full_covariance_refits_regenerated_principal_noise(tmp_path):
    req=calibration_request();rows=req['observations']['rows'];n=len(rows)
    covariance=.01**2*(.8*np.eye(n)+.2*np.ones((n,n)))
    req['noise'].update(kind='full_covariance',values=covariance,unit='mGal^2',
        cross_partition_dependence='possible_not_removed')
    req['noise']['values_sha256']=survey._digest({k:req['noise'][k] for k in ('kind','unit','values')}|{'rows':rows})
    frozen=l2.calibrate_gravity_l2(req)
    assert frozen['selection_status']=='selected'
    actual=refits.refit_gravity_noise(req,frozen)
    generator=np.random.Generator(np.random.PCG64(refits.SEED))
    expected=generator.standard_normal((32,n))@np.linalg.cholesky(covariance).T+req['observations']['gz_up_mgal']
    np.testing.assert_array_equal(actual['targets_mgal'],expected)
    refits.validate_noise_refits(actual,req,frozen)
    refits.workflow.publish_archive(tmp_path/'data',tmp_path/'temp','full-covariance.gza',actual)
