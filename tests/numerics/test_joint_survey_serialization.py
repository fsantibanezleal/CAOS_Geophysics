"""Actual source-bound external serialization and no hidden storage defaults."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

import joint_survey_serialization as serialization
import joint_survey_plan as planner
from test_joint_survey_intake import fixture


def writer_request(directory,covariance=False,provided=False):
    source=directory/'source';source.mkdir()
    doc,_=fixture(source,covariance,provided)
    from joint_survey_intake import load_joint_development
    admitted=load_joint_development(str(source))
    originals={m:{'raw':(source/(m+'.raw')).read_bytes(),
                   'correction':(source/(m+'.corrections.json')).read_bytes()}
               for m in ('gravity','magnetic')} if provided else None
    return {'schema':'joint-survey-write-request-1','survey_request':admitted['survey_request'],
        'development':admitted['development'],'sealed_manifest':doc['sealed_manifest'],'originals':originals}


@pytest.mark.parametrize('covariance',[False,True])
@pytest.mark.parametrize('provided',[False,True])
def test_original_roundtrip(tmp_path,covariance,provided):
    request=writer_request(tmp_path,covariance,provided)
    before=planner._digest(request['survey_request']);result=serialization.write_joint_development(str(tmp_path/'export'),request)
    assert result['plan']['plan_sha256']==request['development']['plan_sha256']
    assert planner._digest(result['development'])==planner._digest(request['development'])
    assert planner._digest(request['survey_request'])==before
    assert result['diagnostics']['source_bytes_verified']=={'gravity':provided,'magnetic':provided}
    assert not result['diagnostics']['sealed_values_loaded']
    if provided:
        for m in ('gravity','magnetic'):
            assert (tmp_path/'export'/(m+'.raw')).read_bytes()==request['originals'][m]['raw']
    assert sum(p.stat().st_size for p in (tmp_path/'export').iterdir())<256*1024**2


@pytest.mark.parametrize('change',['source','commitment','extra','noise','repository','existing'])
def test_prewrite_rejection(tmp_path,change):
    request=writer_request(tmp_path,provided=True);target=tmp_path/'export'
    if change=='source': request['originals']['gravity']['raw']=b'x'*len(request['originals']['gravity']['raw'])
    elif change=='commitment': request['sealed_manifest']['gravity']['rows_sha256']='0'*64
    elif change=='extra': request['callback']='module'
    elif change=='noise':
        request=deepcopy(request);request['development']['gravity']['noise_values'][:]=-1.
        d=request['development']['gravity'];s=request['survey_request']['gravity']
        d['noise_sha256']=planner._digest({'rows':d['rows'],'noise_values':d['noise_values'],'unit':s['noise']['unit'],
            'kind':s['noise']['kind'],'plan_sha256':request['development']['plan_sha256']})
    elif change=='repository':
        (tmp_path/'.git').mkdir()
    else: target.mkdir()
    with pytest.raises((ValueError,TypeError,FileExistsError,np.linalg.LinAlgError)):
        serialization.write_joint_development(str(target),request)
    assert target.exists()==(change=='existing')


def test_explicit_root(tmp_path,monkeypatch):
    monkeypatch.delenv('GEOPHYSICS_LOCAL_DATA_ROOT',raising=False)
    with pytest.raises(ValueError): serialization.local_joint_data_root()
    monkeypatch.setenv('GEOPHYSICS_LOCAL_DATA_ROOT',str(tmp_path))
    assert serialization.local_joint_data_root()==tmp_path
    assert serialization.local_joint_data_root(str(tmp_path))==tmp_path
    for candidate in ('','relative','https://provider.invalid'):
        with pytest.raises(ValueError): serialization.local_joint_data_root(candidate)
    repo=Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError): serialization.local_joint_data_root(str(repo))
