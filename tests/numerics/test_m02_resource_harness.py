"""Receipt custody controls, not substituted scientific measurements."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

_path=Path(__file__).resolve().parents[2]/'scripts/validate_m02_resources.py'
_spec=importlib.util.spec_from_file_location('_m02_resource_harness',_path)
harness=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)


def receipts(prefix,*,fault=None):
    record={'kind':'cap','index':0,'exit_code':0,'hard_timeout':False,
        'sampled_process_tree_peak_rss_bytes':100,'wall_seconds':1.,
        'sampling_complete':True,'sampling_errors':[]}
    source=harness.ROOT/'data-pipeline/gravity_l2.py'
    result={'status':'passed','source_sha256':{'gravity_l2.py':hashlib.sha256(source.read_bytes()).hexdigest()}}
    if fault=='source': result['source_sha256']['gravity_l2.py']='0'*64
    elif fault=='status': result['status']='failed'
    elif fault=='exit_bool': record['exit_code']=True
    elif fault=='rss': record['sampled_process_tree_peak_rss_bytes']=0
    elif fault=='index': record['index']=1
    elif fault=='sampling': record['sampling_errors']=[{'type':'OSError','winerror':1455}]
    elif fault=='hard_timeout': record['hard_timeout']=True
    harness._write(prefix.with_suffix('.resource.json'),record)
    harness._write(prefix.with_suffix('.json'),result)


def test_completed_resource_resume_requires_both_actual_receipts(tmp_path):
    prefix=tmp_path/'cap-00'
    assert harness._completed(prefix,'cap',0) is None
    harness._write(prefix.with_suffix('.json'),{'status':'passed'})
    assert harness._completed(prefix,'cap',0) is None
    other=tmp_path/'complete'
    receipts(other)
    assert harness._completed(other,'cap',0)['sampled_process_tree_peak_rss_bytes']==100


@pytest.mark.parametrize('fault',['source','status','exit_bool','rss','index','sampling','hard_timeout'])
def test_completed_resource_receipt_rejects_inconsistency(tmp_path,fault):
    prefix=tmp_path/'cap-00';receipts(prefix,fault=fault)
    with pytest.raises(ValueError): harness._completed(prefix,'cap',0)


def test_sampler_error_retained_as_failed_measurement(tmp_path):
    prefix=tmp_path/'cap-00';receipts(prefix)
    import json
    with prefix.with_suffix('.resource.json').open() as stream: record=json.load(stream)
    record.update(sampling_complete=False,sampling_errors=[{'type':'OSError','winerror':1455}])
    replacement=tmp_path/'error'
    harness._write(replacement.with_suffix('.resource.json'),record)
    with prefix.with_suffix('.json').open() as stream: science=json.load(stream)
    harness._write(replacement.with_suffix('.json'),science)
    assert harness._completed(replacement,'cap',0)['sampling_complete'] is False


def test_resume_reruns_failed_sampling_without_overwriting_receipts(tmp_path):
    import json
    prefix=tmp_path/'cap-00'
    receipts(prefix)
    resource=prefix.with_suffix('.resource.json')
    record=json.loads(resource.read_text())
    record.update(sampling_complete=False,sampling_errors=[{'type':'OSError','winerror':1455}])
    resource.unlink()  # Test fixture only, never a real measurement receipt.
    harness._write(resource,record)
    original=resource.read_bytes()
    retry,completed=harness._resume_attempt(tmp_path,'cap',0)
    assert retry==tmp_path/'cap-00-retry-1' and completed is None
    assert resource.read_bytes()==original
    receipts(retry)
    selected,completed=harness._resume_attempt(tmp_path,'cap',0)
    assert selected==retry and completed['sampling_complete'] is True
    assert resource.read_bytes()==original


def test_resume_summary_keeps_previous_failed_measurement(tmp_path):
    original=tmp_path/'summary.json'
    harness._write(original,{'nominal':{'sampling_complete_count':19}})
    old=original.read_bytes()
    target=harness._summary_target(tmp_path)
    assert target==tmp_path/'summary-retry-1.json'
    harness._write(target,{'nominal':{'sampling_complete_count':20}})
    assert original.read_bytes()==old
    assert harness._summary_target(tmp_path)==tmp_path/'summary-retry-2.json'
