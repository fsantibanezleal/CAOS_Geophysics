"""Receipt custody controls, not substituted scientific measurements."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

_path=Path(__file__).resolve().parents[2]/'scripts/validate_m02_resources.py'
_spec=importlib.util.spec_from_file_location('_m02_resource_harness',_path)
harness=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)

_corrected_path=Path(__file__).resolve().parents[2]/'scripts/validate_m02_corrected_resources.py'
_corrected_spec=importlib.util.spec_from_file_location('_m02_corrected_resource_harness',_corrected_path)
corrected_harness=importlib.util.module_from_spec(_corrected_spec)
_corrected_spec.loader.exec_module(corrected_harness)


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


def corrected_receipts(prefix, sources, *, sampling_complete=True, exit_code=0,
                       science_status='passed'):
    corrected_harness._write(prefix.with_suffix('.json'),
        {'status':science_status,'source_hashes':sources})
    corrected_harness._write(prefix.with_suffix('.resource.json'),
        {'kind':'cap','index':0,'exit_code':exit_code,'hard_timeout':False,
         'sampled_process_tree_peak_rss_bytes':100,'wall_seconds':1.,
         'sampling_complete':sampling_complete,
         'sampling_errors':[] if sampling_complete else [{'type':'OSError','winerror':1455}]})


def test_corrected_resume_retries_only_sampler_failure_and_preserves_receipts(tmp_path):
    sources=corrected_harness._source_hashes()
    base=tmp_path/'cap-00'
    corrected_receipts(base,sources,sampling_complete=False)
    original=(base.with_suffix('.json').read_bytes(),base.with_suffix('.resource.json').read_bytes())
    retry,completed=corrected_harness._resume_attempt(tmp_path,'cap',0,sources)
    assert retry==tmp_path/'cap-00-retry-1' and completed is None
    assert original==(base.with_suffix('.json').read_bytes(),base.with_suffix('.resource.json').read_bytes())
    corrected_receipts(retry,sources)
    selected,completed=corrected_harness._resume_attempt(tmp_path,'cap',0,sources)
    assert selected==retry and completed['sampling_complete'] is True


def test_corrected_resume_accepts_only_pinned_prior_sampler_version():
    sources=corrected_harness._source_hashes()
    legacy=dict(sources)
    legacy[corrected_harness.RESOURCE_RUNNER_PATH]=next(iter(corrected_harness.LEGACY_RESOURCE_RUNNER_SHA256))
    assert corrected_harness._same_sources(legacy,sources)
    legacy['data-pipeline\\gravity_l2.py']='0'*64
    assert not corrected_harness._same_sources(legacy,sources)


@pytest.mark.parametrize('fault', ['solver_failure','source_mismatch'])
def test_corrected_resume_fails_closed_for_non_sampler_receipt_errors(tmp_path,fault):
    sources=corrected_harness._source_hashes()
    if fault=='solver_failure':
        corrected_receipts(tmp_path/'cap-00',sources,sampling_complete=False,
                           exit_code=1,science_status='failed')
    else:
        bad=dict(sources); bad['data-pipeline/gravity_l2.py']='0'*64
        corrected_receipts(tmp_path/'cap-00',bad,sampling_complete=False)
    with pytest.raises(ValueError):
        corrected_harness._resume_attempt(tmp_path,'cap',0,sources)


def test_corrected_resume_retains_orphan_log_and_uses_new_attempt(tmp_path):
    sources=corrected_harness._source_hashes()
    log=tmp_path/'cap-00.log'
    log.write_text('interrupted attempt\n')
    old=log.read_bytes()
    retry,completed=corrected_harness._resume_attempt(tmp_path,'cap',0,sources)
    assert retry==tmp_path/'cap-00-retry-1' and completed is None
    assert log.read_bytes()==old


def test_corrected_resume_refuses_to_duplicate_live_child(tmp_path,monkeypatch):
    sources=corrected_harness._source_hashes()
    log=tmp_path/'cap-00.log'
    log.write_text('live child\n')
    monkeypatch.setattr(corrected_harness,'_child_running',lambda _path: True)
    with pytest.raises(ValueError,match='still running'):
        corrected_harness._resume_attempt(tmp_path,'cap',0,sources)


def test_corrected_resume_summary_never_overwrites_prior_summary(tmp_path):
    original=tmp_path/'summary.json'
    corrected_harness._write(original,{'kept':True})
    old=original.read_bytes()
    target=corrected_harness._summary_target(tmp_path)
    assert target==tmp_path/'summary-retry-1.json'
    corrected_harness._write(target,{'new':True})
    assert original.read_bytes()==old
