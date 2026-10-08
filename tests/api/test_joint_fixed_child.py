"""Real fixed full26 solve/replays plus source/control/lower-budget negatives."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import time
import uuid

import pytest

from app import joint_execution as execution
from app.joint_worker import run_fixed_child


@pytest.fixture
def launch(tmp_path):
    root=execution.ordinary(os.environ['GEOPHYSICS_JOINT_EXECUTION_DATA_ROOT'],directory=True,external=True)
    data=root/str(uuid.uuid4());data.mkdir()
    job=str(uuid.uuid4());stage=data/job;stage.mkdir()
    scratch=tmp_path/'scratch';scratch.mkdir()
    source=Path(os.environ['GEOPHYSICS_JOINT_MATRIX_FIXTURE'])/'joint-control-00'
    members={}
    for role in ('development','sealed'):
        shutil.copytree(source/role,stage/'inputs'/role)
        members[role]={path.name:{'bytes':path.stat().st_size,'sha256':execution.digest(path.read_bytes())}
                       for path in (stage/'inputs'/role).iterdir()}
    python=Path(os.environ['GEOPHYSICS_JOINT_EXECUTION_PYTHON'])
    context={'schema':'geophysics.joint-fixed-context/v1','source_root':str(execution.ROOT),
        'python':str(python),'python_sha256':execution.digest(python.read_bytes()),
        'site_root':str(python.parent.parent/'Lib'/'site-packages'),'source_hashes':execution.source_inventory()}
    context_path=data/'context.json';execution.write_json(context_path,context)
    control={'schema':'geophysics.joint-fixed-control/v1','job_id':job,'owner_id':str(uuid.uuid4()),
        'project_id':str(uuid.uuid4()),'dataset_id':str(uuid.uuid4()),'dataset_sha256':'a'*64,
        'context_path':str(context_path),'context_sha256':execution.digest(context_path.read_bytes()),
        'data_root':str(data),'stage':str(stage),'scratch':str(scratch),'deadline':time.monotonic()+600.,
        'limits':{'wall_seconds':600,'memory_bytes':2*1024**3,'scratch_bytes':256*1024**2},'members':members}
    path=stage/'control.json';execution.write_json(path,control)
    return context,control,path,stage,scratch


def test_actual_full26_child_solve_and_native_replay(launch):
    context,control,path,stage,scratch=launch
    async def cancel(): return False
    outcome=asyncio.run(run_fixed_child(path,execution.digest(path.read_bytes()),cancel=cancel))
    assert outcome['execution_completed'],(outcome,(stage/'stderr.txt').read_text())
    assert outcome['samples']>0 and outcome['peak_sampled_tree_rss_bytes']>0
    assert not outcome['scientific_acceptance_verified'] and not outcome['host_admission']
    receipt,raw=execution.read_json(stage/'receipt.json')
    assert execution.digest(raw)==outcome['child_receipt_sha256']
    assert receipt['phases']['solve']['inverse_completed'] is True
    ledger=json.loads((stage/'original/calibration/calibration.json').read_bytes())
    assert len(ledger['payload']['candidates'])==26
    assert receipt['phases']['instrument_export']['instrument_manifest_sha256']==receipt['phases']['instrument_replay']['instrument_manifest_sha256']
    closure=(stage/'loaded-modules.json').read_bytes()
    assert execution.digest(closure)==receipt['loaded_module_sha256']
    loaded=json.loads(closure)
    assert 'simpeg/potential_fields/magnetics/simulation.py' in loaded
    assert loaded and not receipt['loaded_transitive_closure_verified']
    from app.joint_worker import validate_child_receipt
    for key,value in (('host_admission',True),('owner_id',str(uuid.uuid4())),('loaded_module_sha256','0'*64)):
        wrong=deepcopy(receipt);wrong[key]=value
        with pytest.raises(ValueError): validate_child_receipt(wrong,control,context,stage)
    wrong=deepcopy(receipt);wrong['phases']['instrument_replay']['refit']=True
    with pytest.raises(ValueError): validate_child_receipt(wrong,control,context,stage)
    # Every original member remains unchanged, including sealed input bytes.
    execution.validate_control(control,context)
    assert execution.source_inventory()==context['source_hashes']


def test_closed_source_and_interpreter_controls(launch):
    context,control,path,stage,scratch=launch
    assert execution.validate_context(context)
    for key,value in (('source_root',str(stage)),('python_sha256','0'*64),('site_root',str(stage))):
        wrong=deepcopy(context);wrong[key]=value
        with pytest.raises(ValueError): execution.validate_context(wrong)
    wrong=deepcopy(context);wrong['source_hashes']['data-pipeline/magnetic_forward.py']='0'*64
    with pytest.raises(ValueError,match='product_source_changed'): execution.validate_context(wrong)
    wrong=deepcopy(context);wrong['callback']='arbitrary'
    with pytest.raises(ValueError,match='closed_fields'): execution.validate_context(wrong)


def test_original_lower_caps_and_input_mutation(launch):
    context,control,path,stage,scratch=launch
    now=time.monotonic()
    for key,value in (('wall_seconds',601),('memory_bytes',2*1024**3+1),('scratch_bytes',256*1024**2+1)):
        wrong=deepcopy(control);wrong['limits'][key]=value
        with pytest.raises(ValueError,match='original_lower_limits'): execution.validate_control(wrong,context,now=now)
    wrong=deepcopy(control);wrong['deadline']=now-1.
    with pytest.raises(ValueError,match='same_job_deadline'): execution.validate_control(wrong,context,now=now)
    wrong=deepcopy(control);wrong['scratch']=str(stage)
    with pytest.raises(ValueError,match='scratch_overlap'): execution.validate_control(wrong,context,now=now)
    changed=stage/'inputs/sealed/gravity_observed.npy'
    with changed.open('r+b') as stream:
        stream.seek(-1,2);value=stream.read(1);stream.seek(-1,2);stream.write(bytes([value[0]^1]))
    with pytest.raises(ValueError,match='input_digest_changed'): execution.validate_control(control,context)
    assert not (stage/'original').exists()


def test_actual_cancel_before_launch_preserves_all_inputs(launch):
    context,control,path,stage,scratch=launch
    async def cancel(): return True
    outcome=asyncio.run(run_fixed_child(path,execution.digest(path.read_bytes()),cancel=cancel))
    assert outcome['reason']=='user_cancelled' and outcome['returncode'] is None
    assert not outcome['execution_completed'] and not (stage/'original').exists()
    execution.validate_control(control,context)


def test_actual_child_deadline_terminates_and_keeps_stage(launch):
    context,control,path,stage,scratch=launch
    # Same production command/import path; small genuine lower wall budget.
    control['limits']['wall_seconds']=1;control['deadline']=time.monotonic()+1.
    replacement=stage/'short-control.json';execution.write_json(replacement,control)
    async def cancel(): return False
    outcome=asyncio.run(run_fixed_child(replacement,execution.digest(replacement.read_bytes()),cancel=cancel))
    assert outcome['reason']=='job_timeout' and not outcome['execution_completed']
    assert (stage/'stdout.txt').is_file() and (stage/'stderr.txt').is_file()
    assert (stage/'inputs/sealed/gravity_observed.npy').is_file()


@pytest.mark.parametrize('condition',['memory','scratch','cancel','log'])
def test_actual_child_tree_adverse_resources(launch,condition):
    context,control,path,stage,scratch=launch
    if condition=='memory': control['limits']['memory_bytes']=1
    if condition=='scratch': control['limits']['scratch_bytes']=1
    changed=stage/'adverse-control.json';execution.write_json(changed,control)
    calls=0
    async def cancel():
        nonlocal calls
        calls+=1
        if condition=='log' and calls==2:
            # Genuine adverse bytes in the isolated child's held log; no script
            # substitution, invented scientific output or changed production cap.
            with (stage/'stdout.txt').open('ab') as stream: stream.write(b'x'*65537)
        return condition=='cancel' and calls>=2
    outcome=asyncio.run(run_fixed_child(changed,execution.digest(changed.read_bytes()),cancel=cancel))
    assert outcome['reason']=={'memory':'job_memory_limit','scratch':'job_scratch_limit',
        'cancel':'user_cancelled','log':'joint_log_limit'}[condition]
    assert not outcome['execution_completed'] and outcome['returncode'] is not None
    assert outcome['tree_termination_verified'] is True
    assert (stage/'inputs/development/request.json').is_file() and (stage/'supervisor.json').is_file()


def test_whole_input_cap_precedes_any_original_hash(launch,monkeypatch):
    context,control,path,stage,scratch=launch
    control['members']['development']['request.json']['bytes']=execution.CAP
    monkeypatch.setattr(execution.hashlib,'file_digest',lambda *args:pytest.fail('original hashed before whole cap'))
    with pytest.raises(ValueError,match='whole_input_cap'): execution.validate_control(control,context)
