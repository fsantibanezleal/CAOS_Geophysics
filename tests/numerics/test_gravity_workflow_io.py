"""Real native local workflow transport, replay and external custody gates."""
from copy import deepcopy
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pytest

import gravity_irls as irls
import gravity_l2 as l2
import gravity_survey_l2 as survey
import gravity_workflow_io as workflow
from test_gravity_irls_workflow import request as irls_request
from test_gravity_l2_selection import calibration_request, locked_request, outer_request


@pytest.fixture(scope='module',params=('l2','irls'))
def calibrated(request):
    req = calibration_request() if request.param=='l2' else irls_request()
    result = l2.calibrate_gravity_l2(req) if request.param=='l2' else irls.calibrate_gravity_irls(req)
    return {'schema':'gravity-calibration-archive-1','request':req,'result':result}


def test_full_archive_roundtrip_and_cli(calibrated,tmp_path,monkeypatch):
    data, temp = tmp_path/'data',tmp_path/'temp'
    decoded = workflow.native_from_archive(workflow.archive_bytes(calibrated))
    assert survey._digest(decoded)==survey._digest(calibrated)
    workflow.verify_calibration(decoded)
    monkeypatch.setenv('GEOPHYSICS_LOCAL_DATA_ROOT',str(data))
    monkeypatch.setenv('GEOPHYSICS_LOCAL_TEMP_ROOT',str(temp))
    workflow.publish_archive(data,temp,'request.gza',calibrated['request'])
    assert workflow.main(['calibrate','--input','request.gza','--output','calibration.gza'])==0
    assert workflow.main(['verify','--input','calibration.gza'])==0
    assert workflow.read_archive(data,'calibration.gza')['result']['selection_status']=='selected'
    frozen = workflow.read_archive(data,'calibration.gza')['result']
    outer = outer_request(frozen)
    if frozen['schema']=='gravity-survey-irls-calibration-result-3':
        outer['schema']='gravity-survey-irls-evaluation-request-3'
    else:
        outer['schema']='gravity-survey-l2-evaluation-request-2'
    outer['calibration_request']=calibrated['request']
    workflow.publish_archive(data,temp,'outer.gza',outer)
    assert workflow.main(['evaluate','--input','outer.gza','--output','score.gza'])==0
    scored = workflow.read_archive(data,'score.gza')['result']
    assert scored['wrms']==0. and scored['field_truth'] is None
    assert workflow.main(['verify','--input','score.gza'])==0


@pytest.mark.parametrize('fault',('trailing','prefix','truncated','duplicate','unused','compressed','local_name','hash','shape','dtype','json_duplicate','nan','bool'))
def test_archive_negatives(fault):
    original = {'x':np.array([1.,2.]),'b':np.array([True,False]),'t':(1,False,None,1.)}
    raw = workflow.archive_bytes(original)
    if fault=='trailing': raw += b'junk'
    elif fault=='prefix': raw = b'junk'+raw
    elif fault=='truncated': raw = raw[:-1]
    elif fault=='local_name': raw = raw[:30]+b'X'+raw[31:]
    else:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = [(info.filename,archive.read(info)) for info in archive.infolist()]
        manifest = json.loads(members[0][1])
        descriptor = manifest['value']['dict'][0][1]
        if fault=='hash': descriptor['sha256']='0'*64
        elif fault=='shape': descriptor['shape']=[4096,4096]
        elif fault=='dtype': descriptor['dtype']='O'
        if fault in ('hash','shape','dtype'): members[0]=(members[0][0],json.dumps(manifest).encode())
        if fault=='json_duplicate': members[0]=(members[0][0],b'{"schema":"a","schema":"b","value":null}')
        if fault=='nan': members[0]=(members[0][0],b'{"schema":"gravity-native-archive-1","value":NaN}')
        if fault=='bool':
            from hashlib import sha256
            invalid=b'\x02\x00'
            manifest['value']['dict'][1][1]['sha256']=sha256(invalid).hexdigest()
            members[0]=(members[0][0],json.dumps(manifest).encode())
            members[2]=(members[2][0],invalid)
        if fault=='duplicate': members.append(members[-1])
        if fault=='unused': members.append(('a9999.bin',b''))
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED if fault=='compressed' else zipfile.ZIP_STORED) as archive:
            for name,value in members: archive.writestr(name,value)
        raw=buffer.getvalue()
    with pytest.raises((ValueError,TypeError,zipfile.BadZipFile)):
        workflow.native_from_archive(raw)


def test_external_roots_and_no_overwrite(tmp_path,monkeypatch):
    monkeypatch.delenv('GEOPHYSICS_LOCAL_DATA_ROOT',raising=False)
    with pytest.raises(ValueError): workflow.external_root(None,'GEOPHYSICS_LOCAL_DATA_ROOT')
    with pytest.raises(ValueError): workflow.external_root('relative','GEOPHYSICS_LOCAL_DATA_ROOT')
    repo = Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError): workflow.external_root(repo/'data','GEOPHYSICS_LOCAL_DATA_ROOT')
    data,temp = tmp_path/'data',tmp_path/'temp'
    target=workflow.publish_archive(data,temp,'one.gza',{'v':np.array([1.])})
    before=target.read_bytes()
    with pytest.raises(FileExistsError): workflow.publish_archive(data,temp,'one.gza',{'v':np.array([2.])})
    assert target.read_bytes()==before
    with pytest.raises(ValueError): workflow.publish_archive(data,temp,'../bad.gza',{})
    assert not list(temp.iterdir())


@pytest.mark.parametrize('fault',('metric','prediction','prior','warning','score'))
def test_l2_replay_rehashed_tamper(calibrated,fault):
    if calibrated['result']['schema']!='gravity-survey-l2-calibration-result-1': return
    req,result=deepcopy(calibrated['request']),deepcopy(calibrated['result'])
    if fault=='metric':
        solve=result['candidates'][0]['folds'][0]['solve']
        solve['trace']['phi_m'][0]=solve['phi_m']=1.
        solve['trace']['phi_engine'][0]=solve['phi_engine']=solve['beta_engine']
    elif fault=='prediction': result['predictions']['gz_up_mgal'][0]=1.
    elif fault=='prior':
        req['prior']['reference_kg_m3'][0]=10.
        result['provenance']['prior_sha256']=survey._digest(req['prior'])
    elif fault=='warning': result['diagnostics']['warnings']=('admitted_fixed_geometry',)
    elif fault=='score': result['candidates'][0]['folds'][0]['validation_rmse_mgal']=1.
    result['result_sha256']=survey._digest({k:v for k,v in result.items() if k!='result_sha256'})
    with pytest.raises(ValueError): workflow.validate_l2(result,req)


def test_l2_failed_selection_export_and_exit_two(tmp_path,monkeypatch):
    native=l2._solve_partition
    def failed(*args,**kwargs):
        solve=native(*args,**kwargs)
        solve.update(status='nonconverged',reason='wall_cap',failed_trial={'iteration':solve['iterations'],'reason':'wall_cap'})
        return solve
    monkeypatch.setattr(l2,'_solve_partition',failed)
    data,temp=tmp_path/'data',tmp_path/'temp'
    workflow.publish_archive(data,temp,'request.gza',calibration_request())
    assert workflow.main(['calibrate','--data-root',str(data),'--temp-root',str(temp),
        '--input','request.gza','--output','failed.gza'])==2
    failed=workflow.read_archive(data,'failed.gza')
    workflow.verify_calibration(failed)
    assert failed['result']['selection_status']=='insufficient_candidates'
    assert all(f['solve']['reason']=='wall_cap' for c in failed['result']['candidates'] for f in c['folds'])


def test_original_nonnull_l2_complete_replay_and_archive(tmp_path):
    req,_,_=locked_request(0,0)
    result=l2.calibrate_gravity_l2(req)
    assert result['selection_status']=='selected'
    workflow.validate_l2(result,req)
    complete={'schema':'gravity-calibration-archive-1','request':req,'result':result}
    data,temp=tmp_path/'data',tmp_path/'temp'
    workflow.publish_archive(data,temp,'nonnull.gza',complete)
    decoded=workflow.read_archive(data,'nonnull.gza')
    assert survey._digest(decoded)==survey._digest(complete)
    workflow.verify_calibration(decoded)
