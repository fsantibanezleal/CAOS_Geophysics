"""Real external audit-byte closure and retained historical receipt denials.

No new scientific fit or historical successful receipt is promoted. The
standalone resource checks are scalar/file controls, not accepted inverse jobs.
"""
from copy import deepcopy
import os
from pathlib import Path
import time

import pytest

from app import joint_execution as execution
from app import joint_worker as worker


@pytest.fixture
def retained():
    stage=execution.ordinary(os.environ['GEOPHYSICS_JOINT_RETAINED_CHILD'],directory=True,external=True)
    receipt,encoded=execution.read_json(stage/'receipt.json')
    control,_=execution.read_json(stage/'control.json')
    context,_=execution.read_json(control['context_path'])
    supervisor,_=execution.read_json(stage/'supervisor.json')
    assert receipt['scientific_acceptance_verified'] is False
    assert receipt['product_source_hashes']!=execution.source_inventory()
    return stage,receipt,encoded,control,context,supervisor


def directories(tmp_path):
    stage=tmp_path/'stage';stage.mkdir()
    scratch=tmp_path/'scratch';scratch.mkdir()
    (stage/'retained.txt').write_bytes(b'original accepted states remain')
    (scratch/'retained.txt').write_bytes(b'original scratch remains')
    return stage,scratch


def outcome(retained):
    value=deepcopy(retained[-1])
    value['peak_sum_stage_scratch_bytes']=0
    value['deadline']=time.monotonic()+120.
    return value


def test_actual_receipt_counts_its_own_exclusive_bytes(tmp_path,retained):
    stage,scratch=directories(tmp_path);value=outcome(retained)
    result=worker.write_supervisor(stage,scratch,value)
    original,encoded=execution.read_json(stage/'supervisor.json')
    assert original==result and encoded==execution.canonical(result)
    assert result['peak_sum_stage_scratch_bytes']==worker.directory_bytes(stage)+worker.directory_bytes(scratch)
    assert result['execution_completed'] and not result['scientific_acceptance_verified']
    assert value['peak_sum_stage_scratch_bytes']==0  # Caller record is not silently changed.
    before=(stage/'supervisor.json').read_bytes()
    with pytest.raises(FileExistsError): worker.write_supervisor(stage,scratch,value)
    assert (stage/'supervisor.json').read_bytes()==before


def test_one_byte_final_receipt_deficit_rejects_without_new_allowance(tmp_path,retained):
    value=outcome(retained)
    first=tmp_path/'exact';first.mkdir();stage,scratch=directories(first)
    current=worker.directory_bytes(stage)+worker.directory_bytes(scratch)
    # Independent exhaustive scalar length equation, not the writer's loop.
    matches=[]
    for cap in range(current+1,current+4096):
        trial=deepcopy(value);trial['limits']['scratch_bytes']=cap
        trial['peak_sum_stage_scratch_bytes']=cap
        if current+len(execution.canonical(trial))==cap: matches.append(cap)
    assert len(matches)==1
    cap=matches[0]
    assert len(str(cap))==len(str(cap-1))
    value['limits']['scratch_bytes']=cap
    result=worker.write_supervisor(stage,scratch,value)
    assert result['execution_completed'] and result['peak_sum_stage_scratch_bytes']==cap
    second=tmp_path/'one-byte-short';second.mkdir();stage,scratch=directories(second)
    value['limits']['scratch_bytes']=cap-1
    result=worker.write_supervisor(stage,scratch,value)
    assert not result['execution_completed'] and result['reason']=='job_scratch_limit'
    assert result['limits']['scratch_bytes']==cap-1
    assert result['peak_sum_stage_scratch_bytes']==worker.directory_bytes(stage)+worker.directory_bytes(scratch)>cap-1
    assert (stage/'retained.txt').read_bytes()==b'original accepted states remain'
    assert (scratch/'retained.txt').read_bytes()==b'original scratch remains'


def test_retained_rejection_and_prior_peak_are_never_dropped(tmp_path,retained):
    stage,scratch=directories(tmp_path);value=outcome(retained)
    value.update(execution_completed=False,reason='user_cancelled',peak_sum_stage_scratch_bytes=1234567)
    value['limits']['scratch_bytes']=1
    result=worker.write_supervisor(stage,scratch,value)
    assert result['reason']=='user_cancelled' and not result['execution_completed']
    assert result['peak_sum_stage_scratch_bytes']==1234567
    assert (stage/'supervisor.json').is_file() and (scratch/'retained.txt').is_file()


def test_metadata_admission_precedes_receipt_write(tmp_path,retained):
    stage,scratch=directories(tmp_path);value=outcome(retained)
    value['reason']='x'*65536
    with pytest.raises(ValueError,match='metadata_cap'): worker.write_supervisor(stage,scratch,value)
    assert not (stage/'supervisor.json').exists()


def test_actual_foreign_byte_drift_requires_recovery(tmp_path,retained,monkeypatch):
    stage,scratch=directories(tmp_path);value=outcome(retained)
    write=execution.write_json
    def foreign(path,record):
        write(path,record)
        (scratch/'uncertain.txt').write_bytes(b'new unbound foreign byte')
    monkeypatch.setattr(execution,'write_json',foreign)
    with pytest.raises(ValueError,match='tree_changed_requires_recovery'):
        worker.write_supervisor(stage,scratch,value)
    assert (stage/'supervisor.json').is_file() and (scratch/'uncertain.txt').is_file()


def test_prewrite_expiry_is_failed_and_uses_original_wall_snapshot(tmp_path,retained):
    stage,scratch=directories(tmp_path);value=outcome(retained)
    value['deadline']=time.monotonic()-1.
    started=time.monotonic()-2.
    result=worker.write_supervisor(stage,scratch,value,started=started)
    assert result['reason']=='job_timeout' and not result['execution_completed']
    assert result['wall_seconds']>=2. and result['deadline']==value['deadline']


def test_expiry_during_actual_final_write_never_returns_success(tmp_path,retained,monkeypatch):
    stage,scratch=directories(tmp_path);value=outcome(retained)
    write=execution.write_json
    def expires(path,record):
        write(path,record)
        # Genuine absolute monotonic-clock boundary after exclusive write.
        monkeypatch.setattr(worker.time,'monotonic',lambda:record['deadline'])
    monkeypatch.setattr(execution,'write_json',expires)
    with pytest.raises(ValueError,match='deadline_requires_recovery'):
        worker.write_supervisor(stage,scratch,value)
    assert (stage/'supervisor.json').is_file() and (scratch/'retained.txt').is_file()


@pytest.mark.parametrize('fault',['missing','json','array','binding','source','expired'])
def test_actual_historical_receipt_is_never_a_new_source_pass(tmp_path,retained,fault):
    historical,receipt,encoded,control,context,_=retained
    stage=tmp_path/'stage';stage.mkdir()
    control=deepcopy(control);control['deadline']=time.monotonic()+120.
    if fault=='json': encoded=b'{"unterminated":'
    elif fault=='array': encoded=b'[]'
    elif fault=='binding':
        receipt=deepcopy(receipt);receipt['control_sha256']='0'*64
        encoded=execution.canonical(receipt)
    if fault!='missing': (stage/'receipt.json').write_bytes(encoded)
    if fault=='expired': control['deadline']=time.monotonic()-1.
    before={p.name:execution.digest(p.read_bytes()) for p in stage.iterdir()}
    digest,reason=worker.completed_child(retained[1]['control_sha256'],control,context,stage)
    assert digest is None and reason==('job_timeout' if fault=='expired' else 'joint_child_validation_failed')
    assert {p.name:execution.digest(p.read_bytes()) for p in stage.iterdir()}==before
    assert execution.digest((historical/'receipt.json').read_bytes())==execution.digest(retained[2])


def test_same_deadline_expiring_during_postexit_validation_is_literal(tmp_path,retained,monkeypatch):
    _,_,encoded,control,context,_=retained
    stage=tmp_path/'stage';stage.mkdir();(stage/'receipt.json').write_bytes(encoded)
    control=deepcopy(control);control['deadline']=time.monotonic()+120.
    def expired(*args):
        control['deadline']=time.monotonic()-1.
        raise ValueError('joint_product_source_changed')
    monkeypatch.setattr(worker,'validate_child_receipt',expired)
    digest,reason=worker.completed_child(retained[1]['control_sha256'],control,context,stage)
    assert digest is None and reason=='job_timeout'
