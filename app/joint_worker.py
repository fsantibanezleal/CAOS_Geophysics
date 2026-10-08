"""Fixed child-tree execution seam for the existing singleton claimant."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import time

import psutil

from app import joint_execution as execution


def directory_bytes(root):
    execution.ordinary(root,directory=True,external=True)
    total=0
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in dirs: execution.ordinary(Path(directory)/name,directory=True,external=True)
        for name in files: total+=execution.ordinary(Path(directory)/name,external=True).stat().st_size
    return total


def rss_tree(pid):
    try:
        parent=psutil.Process(pid)
        processes=[parent,*parent.children(recursive=True)]
    except psutil.NoSuchProcess: return 0
    total=0
    for process in processes:
        try: total+=process.memory_info().rss
        except psutil.NoSuchProcess: pass
    return total


def terminate_tree(process):
    # Canonical lifecycle mechanism, never an independently copied kill policy.
    from app.worker import _terminate_tree
    try:
        _terminate_tree(process.pid)
        return True
    except (OSError,psutil.Error):
        # The owned Popen handle is still usable if process enumeration fails.
        # Do not claim descendant termination was verified in that adverse case.
        if process.poll() is None: process.kill()
        process.wait(timeout=5)
        return False


def validate_child_receipt(receipt,control,context,stage):
    execution.fields(receipt,('schema','state','reason','job_id','owner_id','project_id',
        'dataset_id','dataset_sha256','control_sha256','context_sha256','product_source_hashes',
        'native_source_inventory','loaded_transitive_closure_verified','phases',
        'scientific_acceptance_verified','host_admission','public_activation','loaded_module_sha256'))
    execution.require(receipt['schema']=='geophysics.joint-fixed-execution/v1'
        and receipt['state']=='execution_completed' and receipt['reason'] is None,'joint_child_receipt_state')
    for key in ('job_id','owner_id','project_id','dataset_id','dataset_sha256','context_sha256'):
        execution.require(receipt[key]==control[key],'joint_child_receipt_binding')
    for key in ('scientific_acceptance_verified','host_admission','public_activation','loaded_transitive_closure_verified'):
        execution.require(receipt[key] is False,'joint_child_receipt_claim')
    execution.require(receipt['product_source_hashes']==context['source_hashes']==execution.source_inventory(),
                      'joint_product_source_changed')
    closure,raw=execution.read_json(stage/'loaded-modules.json',cap=256*1024)
    execution.require(execution.digest(raw)==execution.sha(receipt['loaded_module_sha256']) and
        type(closure) is dict and closure,'joint_loaded_receipt_binding')
    for key,value in closure.items():
        execution.require(type(key) is str and not key.startswith('/') and '\\' not in key
            and all(part not in ('','..','.') for part in key.split('/')),'joint_loaded_receipt_path')
        execution.sha(value)
    execution.fields(receipt['phases'],('solve','original_replay','instrument_export','instrument_replay'))
    phases=receipt['phases'];solved=phases['solve'];replayed=phases['original_replay']
    execution.require(solved['status']=='completed' and solved['mode']=='solve' and solved['inverse_completed'] is True
        and solved['field_eligible'] is False and solved['public_activation'] is False
        and replayed['validated'] is True and replayed['inverse_completed'] is True,'joint_child_phase_binding')
    for key in ('instrument_export','instrument_replay'):
        execution.require(phases[key]['validated'] is True and phases[key]['refit'] is False
            and phases[key]['scientific_acceptance_verified'] is False and phases[key]['public_activation'] is False,
            'joint_child_phase_claim')
    execution.require(phases['instrument_export']['instrument_manifest_sha256']==
        phases['instrument_replay']['instrument_manifest_sha256'],'joint_child_instrument_binding')
    execution.require(execution.digest(execution.ordinary(stage/'export/instrument/instrument.json',external=True).read_bytes())==
        phases['instrument_replay']['instrument_manifest_sha256'],'joint_child_instrument_digest')


def completed_child(control_sha256, control, context, stage):
    """Post-exit validation, never a successful child digest on a failed check."""
    try:
        receipt,encoded=execution.read_json(stage/'receipt.json')
        execution.require(receipt['control_sha256']==control_sha256,'joint_child_receipt_binding')
        validate_child_receipt(receipt,control,context,stage)
        execution.validate_context(context)
        execution.validate_control(control,context)
        if time.monotonic()>=control['deadline']: return None,'job_timeout'
        return execution.digest(encoded),None
    except (OSError,ValueError,TypeError,KeyError,UnicodeError):
        return None,('job_timeout' if time.monotonic()>=control['deadline']
                     else 'joint_child_validation_failed')


def write_supervisor(stage, scratch, outcome, *, started=None):
    """Count the exclusive receipt itself; rejection bytes remain charged.

    The stopped child's private stage has one writer. Unexpected tree drift
    fails finalization and retains the file for recovery, never DB promotion.
    This is not an OS reservation or permission to release rejected bytes.
    """
    current=directory_bytes(stage)+directory_bytes(scratch)
    value=dict(outcome)
    if started is not None: value['wall_seconds']=time.monotonic()-started
    for _ in range(16):
        if value['execution_completed'] and time.monotonic()>=value['deadline']:
            value.update(execution_completed=False,reason='job_timeout')
        encoded=execution.canonical(value)
        execution.require(len(encoded)<=65536,'joint_metadata_cap')
        peak=max(outcome['peak_sum_stage_scratch_bytes'],current+len(encoded))
        if peak>value['limits']['scratch_bytes'] and value['execution_completed']:
            value.update(execution_completed=False,reason='job_scratch_limit')
        if value['peak_sum_stage_scratch_bytes']==peak:
            final=execution.canonical(value)
            if max(outcome['peak_sum_stage_scratch_bytes'],current+len(final))==peak: break
        value['peak_sum_stage_scratch_bytes']=peak
    else: raise ValueError('joint_supervisor_byte_fixed_point')
    execution.write_json(stage/'supervisor.json',value)
    observed=directory_bytes(stage)+directory_bytes(scratch)
    execution.require(observed==current+len(final) and observed<=value['peak_sum_stage_scratch_bytes'],
                      'joint_supervisor_tree_changed_requires_recovery')
    execution.require(not value['execution_completed'] or time.monotonic()<value['deadline'],
                      'joint_supervisor_deadline_requires_recovery')
    return value


async def run_fixed_child(control_path, control_sha256, *, cancel, poll_interval=.05):
    """Actual execution, not DB promotion. Parent unions result/source lifecycle.

    cancel is the canonical internal job-row check, not an upload callback or
    scientific operator. No cleanup: failed/uncertain stage bytes are retained.
    """
    execution.require(type(poll_interval) is float and .01<=poll_interval<=1.,'joint_poll_interval')
    control,raw=execution.read_json(control_path)
    execution.require(execution.digest(raw)==execution.sha(control_sha256),'joint_control_changed')
    context,_=execution.read_json(control['context_path'])
    python,_=execution.validate_context(context)
    data,stage,scratch=execution.validate_control(control,context)
    command=[str(python),'-B','-S',str(execution.ROOT/'scripts'/'joint_processing_child.py'),
        '--control',str(control_path),'--sha256',control_sha256]
    environment={'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8',
        'TEMP':str(scratch),'TMP':str(scratch),'TMPDIR':str(scratch),
        'NUMBA_CACHE_DIR':str(scratch/'numba'),'MPLCONFIGDIR':str(scratch/'mpl'),
        **{key:'1' for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')}}
    if os.name=='nt':
        for key in ('SYSTEMROOT','SYSTEMDRIVE','WINDIR','LOCALAPPDATA'):
            if key in os.environ: environment[key]=os.environ[key]
    stdout=stage/'stdout.txt';stderr=stage/'stderr.txt'
    peak=0;disk_peak=0;samples=0;failure=None;process=None;started=time.monotonic();tree_termination_verified=None
    try:
        with stdout.open('xb') as out,stderr.open('xb') as err:
            if await cancel(): failure='user_cancelled'
            if not failure and time.monotonic()>=control['deadline']: failure='job_timeout'
            if not failure:
                process=subprocess.Popen(command,cwd=stage,env=environment,stdin=subprocess.DEVNULL,
                    stdout=out,stderr=err,shell=False,start_new_session=os.name=='posix')
                while process.poll() is None:
                    try:
                        peak=max(peak,rss_tree(process.pid))
                        disk_peak=max(disk_peak,directory_bytes(stage)+directory_bytes(scratch));samples+=1
                        if await cancel(): failure='user_cancelled'
                        elif time.monotonic()>=control['deadline']: failure='job_timeout'
                        elif peak>control['limits']['memory_bytes']: failure='job_memory_limit'
                        elif disk_peak>control['limits']['scratch_bytes']: failure='job_scratch_limit'
                        elif max(stdout.stat().st_size,stderr.stat().st_size)>65536: failure='joint_log_limit'
                    except (OSError,ValueError,psutil.Error): failure='joint_resource_measurement_failed'
                    if failure:
                        tree_termination_verified=terminate_tree(process);break
                    await asyncio.sleep(poll_interval)
                process.wait(timeout=5)
        disk_peak=max(disk_peak,directory_bytes(stage)+directory_bytes(scratch))
        if not failure and time.monotonic()>=control['deadline']: failure='job_timeout'
        if not failure and disk_peak>control['limits']['scratch_bytes']: failure='job_scratch_limit'
        if not failure and await cancel(): failure='user_cancelled'
        if not failure and max(stdout.stat().st_size,stderr.stat().st_size)>65536: failure='joint_log_limit'
        if not failure and process.returncode!=0: failure='joint_native_child_failed'
        child_sha=None
        if not failure:
            # Reopen exact selected context and every opaque original AFTER the
            # process exits; publication still rechecks actual SQL source rows.
            child_sha,failure=completed_child(control_sha256,control,context,stage)
            disk_peak=max(disk_peak,directory_bytes(stage)+directory_bytes(scratch))
            if not failure and time.monotonic()>=control['deadline']: failure='job_timeout'
            elif not failure and disk_peak>control['limits']['scratch_bytes']: failure='job_scratch_limit'
        outcome={'schema':'geophysics.joint-supervisor-receipt/v1','execution_completed':failure is None,
            'reason':failure,'returncode':None if process is None else process.returncode,
            'job_id':control['job_id'],'control_sha256':control_sha256,'wall_seconds':time.monotonic()-started,
            'deadline':control['deadline'],'limits':control['limits'],'peak_sampled_tree_rss_bytes':peak,
            'peak_sum_stage_scratch_bytes':disk_peak,'samples':samples,'child_receipt_sha256':
                child_sha,'os_reservation':False,
            'tree_termination_verified':tree_termination_verified,
            'scientific_acceptance_verified':False,'host_admission':False,'public_activation':False}
        return write_supervisor(stage,scratch,outcome,started=started)
    finally:
        if process is not None and process.poll() is None:
            terminate_tree(process);process.wait(timeout=5)
