"""ONE coordinated cold reproduction of an already-opened immutable QR epoch.

The plain stdlib dispatcher can use a different Python version; the fixed
scientific child retains its exact original interpreter/packages/source bytes.
No new holdout, retune, export-original licence, host grant or field PASS.
"""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

PRODUCT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PRODUCT/'data-pipeline'))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io
import magnetic_line_survey_qr_execution as execution
import magnetic_line_survey_runtime as runtime


def require(value):
    if not value:raise core.SurveyError('custody_mismatch','replay')


def read(path,limit=2097152):
    return base.read_bounded(core._plain_path(io.external_path(path,directory=False)),limit)


def dispatcher_ancestry(owner_pid):
    """Read-only actual Windows process ancestry, not a caller lock assertion."""
    require(os.name=='nt')
    class Entry(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('pid',wintypes.DWORD),
            ('heap',ctypes.c_size_t),('module',wintypes.DWORD),('threads',wintypes.DWORD),
            ('parent',wintypes.DWORD),('priority',ctypes.c_long),('flags',wintypes.DWORD),('image',wintypes.WCHAR*260)]
    native=ctypes.WinDLL('kernel32',use_last_error=True)
    native.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]
    native.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    native.CloseHandle.argtypes=[wintypes.HANDLE];native.CloseHandle.restype=wintypes.BOOL
    for name in ('Process32FirstW','Process32NextW'):
        call=getattr(native,name);call.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)];call.restype=wintypes.BOOL
    handle=native.CreateToolhelp32Snapshot(2,0)
    require(handle not in (None,ctypes.c_void_p(-1).value))
    parents={};images={}
    try:
        entry=Entry();entry.size=ctypes.sizeof(entry)
        active=native.Process32FirstW(handle,ctypes.byref(entry))
        while active:
            parents[int(entry.pid)]=int(entry.parent);images[int(entry.pid)]=str(entry.image)
            active=native.Process32NextW(handle,ctypes.byref(entry))
    finally:require(native.CloseHandle(handle))
    chain=[];pid=os.getpid()
    while pid and pid not in chain and len(chain)<128:
        chain.append(pid);pid=parents.get(pid,0)
    require(owner_pid in chain)
    occupancy=[dict(pid=pid,parent_pid=parents[pid],image=image,**process_readback(pid)) for pid,image in sorted(images.items())
        if image.lower().startswith(('python','node'))]
    return dict(actual_ancestor_pids=chain,python_node_process_inventory=occupancy,
        observed_utc=datetime.now(timezone.utc).isoformat(),cpu_exclusivity='not_inferred_from_process_names')


def process_readback(pid):
    """Actual cumulative CPU and current RSS; denied queries are not zero."""
    native=ctypes.WinDLL('kernel32',use_last_error=True);memory=ctypes.WinDLL('psapi',use_last_error=True)
    native.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];native.OpenProcess.restype=wintypes.HANDLE
    native.CloseHandle.argtypes=[wintypes.HANDLE];native.CloseHandle.restype=wintypes.BOOL
    native.GetProcessTimes.argtypes=[wintypes.HANDLE,*[ctypes.POINTER(wintypes.FILETIME)]*4]
    native.GetProcessTimes.restype=wintypes.BOOL
    class Memory(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in
            ('peak_rss','rss','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private')]
    memory.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Memory),wintypes.DWORD]
    memory.GetProcessMemoryInfo.restype=wintypes.BOOL
    handle=native.OpenProcess(0x410,False,pid)
    if not handle:return dict(counter_status='unavailable',cpu_s=None,rss_bytes=None)
    try:
        created,ended,kernel,user=(wintypes.FILETIME() for _ in range(4));sample=Memory();sample.cb=ctypes.sizeof(sample)
        if not native.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kernel),ctypes.byref(user)) or \
           not memory.GetProcessMemoryInfo(handle,ctypes.byref(sample),sample.cb):
            return dict(counter_status='unavailable',cpu_s=None,rss_bytes=None)
        ticks=lambda item:(item.dwHighDateTime<<32)+item.dwLowDateTime
        return dict(counter_status='observed',cpu_s=(ticks(kernel)+ticks(user))/10000000,rss_bytes=int(sample.rss))
    finally:require(native.CloseHandle(handle))


def native_startup_receipt(root):
    """Require actual value-free contained refusal, never a posted host grant."""
    from run_m03_native_context import IMAGE_SHA,PARENT_SHA
    root=io.external_path(root)
    receipt=base.strict_json(read(root/'native-context-result.json'))
    drain=base.strict_json(read(root/'parent-context-drain.json'))
    core._closed(receipt,'schema verdict native_parent_image parent_redirector_sha256 lifetime expected_worker_refusal '
        'source_sha256 occupancy native_fit_count original_data_access magnetic_value_access host_admission','replay')
    core._closed(drain,'schema bootstrap_exit bootstrap_wall_s receipt_sha256 scientific_job_active_processes '
        'scientific_job_total_processes bootstrap_not_scientific_child host_admission bootstrap_owned_bytes','replay')
    lifetime=receipt['lifetime']
    require(type(receipt['native_fit_count']) is int and
        all(type(lifetime[key]) is int for key in ('exit_code','active_processes','total_processes',
            'peak_rss_bytes','peak_committed_bytes','scratch_bytes')) and
        all(type(lifetime[key]) in (int,float) for key in ('cpu_s','wall_s','parent_cpu_s')))
    require(receipt['schema']=='m03-native-parent-context/1' and receipt['verdict']=='component_pass' and
        receipt['native_parent_image']['sha256']==IMAGE_SHA and receipt['parent_redirector_sha256']==PARENT_SHA and
        receipt['source_sha256']==sha256(Path(__file__).with_name('run_m03_native_context.py').read_bytes()).hexdigest() and
        receipt['native_fit_count']==0 and receipt['original_data_access']=='not_opened' and
        receipt['magnetic_value_access']=='not_opened' and receipt['host_admission']=='not_established' and
        receipt['expected_worker_refusal']==core.SurveyError('invalid_contract','seal').error and
        lifetime['actual_executable_sha256']==IMAGE_SHA and lifetime['verdict']=='resource_refused' and
        lifetime['exit_code']==2 and lifetime['active_processes']==0 and lifetime['total_processes']==1 and
        lifetime['enforced_limits']==dict(memory_bytes=512*1024**2,scratch_bytes=16*1024**2,cpu_s=10,wall_s=30,parent_cpu_s=10) and
        0<lifetime['cpu_s']<=10 and 0<lifetime['wall_s']<=30 and 0<=lifetime['parent_cpu_s']<=10 and
        0<lifetime['peak_rss_bytes']<=512*1024**2 and 0<lifetime['peak_committed_bytes']<=512*1024**2 and
        0<lifetime['scratch_bytes']<=16*1024**2 and lifetime['stop_cpu_s'] is None and lifetime['stop_wall_s'] is None and
        drain['schema']=='m03-native-parent-context-drain/2' and drain['bootstrap_exit']==0 and
        drain['receipt_sha256']==base.digest(receipt) and drain['scientific_job_active_processes']==0 and
        drain['scientific_job_total_processes']==1 and drain['bootstrap_not_scientific_child'] is True and
        type(drain['bootstrap_owned_bytes']) is int and
        0<drain['bootstrap_owned_bytes']<=16*1024**2 and runtime.owned_bytes(root)==drain['bootstrap_owned_bytes'])
    pins=execution.source_identity()
    require(all(lifetime['source_sha256'].get(name)==pin for name,pin in pins.items()))
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('retained-root','output','native-executable','packages','dispatcher-lock','parent-executable','context-root'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--native-parent',action='store_true')
    args=parser.parse_args()
    retained=io.external_path(args.retained_root)
    output=Path(args.output)
    require(not output.exists());io.external_path(output.parent)
    lock_path=io.external_path(args.dispatcher_lock,directory=False)
    lock=base.strict_json(read(lock_path,65536))
    require(type(lock) is dict and set(lock)=={'pid','token'} and type(lock['pid']) is int and lock['pid']>0 and
        type(lock['token']) is str and len(lock['token'])==32)
    occupancy=dispatcher_ancestry(lock['pid'])
    from run_m03_native_context import IMAGE_SHA,PARENT_SHA,image_identity
    parent=Path(args.parent_executable).resolve(strict=True)
    require(sha256(parent.read_bytes()).hexdigest()==PARENT_SHA)
    startup=native_startup_receipt(args.context_root)
    if not args.native_parent:
        # The shared dispatcher still executes ordinary CP313; its rule against
        # a Store venv node executable is unchanged. The already qualified
        # bootstrap remains in that SAME outer Job, never outside containment.
        require(sys.version_info[:2]==(3,13))
        bootstrap=output.with_name(output.name+'-parent-context')
        require(not bootstrap.exists());io.external_path(bootstrap.parent);bootstrap.mkdir()
        command=[str(parent),'-B','-S',str(Path(__file__).resolve()),'--native-parent']
        for name in ('retained-root','output','native-executable','packages','dispatcher-lock','parent-executable','context-root'):
            command.extend(['--'+name,getattr(args,name.replace('-','_'))])
        core._write_member(bootstrap,'seal.json',base.canonical_bytes(dict(schema='m03-qr-native-parent-seal/1',
            argv=command,dispatcher_lock=lock,occupancy=occupancy,startup_receipt_sha256=base.digest(startup),
            source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),native_image_sha256=IMAGE_SHA,
            parent_redirector_sha256=PARENT_SHA,host_admission='not_established')))
        started=time.perf_counter()
        completed=subprocess.run(command,cwd=bootstrap,check=False,timeout=1750)
        core._write_member(bootstrap,'drain.json',base.canonical_bytes(dict(schema='m03-qr-native-parent-drain/1',
            bootstrap_exit=completed.returncode,bootstrap_wall_s=time.perf_counter()-started,
            bootstrap_not_scientific_child=True,host_admission='not_established')))
        return completed.returncode
    require(sys.version_info[:3]==(3,12,10) and image_identity()['sha256']==IMAGE_SHA)
    # The shared harness owns process containment and the lock. This script
    # records it, never acquires/deletes/adopts a separate lock or fresh cache.
    control_bytes=read(retained/'qualified-controls.json')
    controls=base.strict_json(control_bytes)
    require(sha256(control_bytes).hexdigest()=='d72c7bdf273672cec70b5001ac17f5df5b4ad0db62568af5254e78cca16d06c3')
    require(controls['tests']==43 and controls['verdict']=='component_pass' and
        controls['source_sha256']==execution.source_identity())
    require(sha256(read(retained/'qualified-controls.xml')).hexdigest()==controls['xml_sha256'])
    for name,pin in controls['test_sha256'].items():
        require(Path(name).name==name and sha256((PRODUCT/'tests/data'/name).read_bytes()).hexdigest()==pin)
    expected_bytes=read(retained/'worker/result/result.json')
    require(sha256(expected_bytes).hexdigest()=='275ae3a46c287f4d44db95608bff0fb674e7f4bf752a47e75c56be768f0d4c76')
    expected=base.strict_json(expected_bytes)
    require(expected['fit']['fit_count']==97 and expected['inventory']['original_rows']==363 and
        expected['partitions']['evaluation_count']==1 and expected['verdict']['overall']=='unresolved')
    previous=base.strict_json(read(retained/'worker/lifetime.json'))
    executable=io.external_path(args.native_executable,directory=False)
    # Installed environments are allowed product venvs, not raw-data custody.
    packages=Path(args.packages).resolve(strict=True);require(packages.is_dir())
    require(sha256(executable.read_bytes()).hexdigest()==previous['actual_executable_sha256'])
    plan_bytes=read(retained/'worker/plan.json')
    plan=base.strict_json(plan_bytes)
    require(plan['schema']=='m03-resolution-qr-fit-plan/1')
    csv=io.external_path(plan['csv_path'],directory=False)
    require(csv.stat().st_size==expected['input']['original']['csv_bytes'])
    # Private PROCESSING of separately held original remains distinct from
    # denied original mirroring in the unchanged export closure.
    require(plan['metadata']['rights']['private_processing']=='allowed')
    digest=sha256()
    with csv.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):digest.update(chunk)
    require(digest.hexdigest()==expected['input']['original']['csv_sha256'])
    output.mkdir();worker=output/'worker';worker.mkdir()
    core._write_member(output,'reproduction-seal.json',base.canonical_bytes(dict(schema='m03-qr-reproduction-seal/1',
        source_sha256=execution.source_identity(),original_result_sha256=sha256(expected_bytes).hexdigest(),
        plan_sha256=sha256(plan_bytes).hexdigest(),controls_sha256=sha256(control_bytes).hexdigest(),
        dispatcher_lock=lock,occupancy=occupancy,parent_pid=os.getppid(),pid=os.getpid(),
        startup_receipt_sha256=base.digest(startup),native_parent_image=image_identity(),
        epoch='augmented_direct_qr_v3',outer='reproduction_of_already_opened_authored_diagnostic',
        new_tuning='not_permitted',field8201='not_verified',host_admission='not_established')))
    core._write_member(worker,'plan.json',plan_bytes)
    lifetime=runtime.run_worker(executable,packages,worker,worker/'plan.json')
    require(lifetime['verdict']=='component_pass')
    reproduced=read(worker/'result/result.json')
    # Complete Result byte identity, not a weakened numerical comparison.
    require(reproduced==expected_bytes)
    verify=output/'cold-selected-verification';verify.mkdir()
    core._write_member(verify,'plan.json',base.canonical_bytes(dict(schema='m03-qr-result-verification-plan/1',result_root=str(worker/'result'))))
    cold=runtime.run_worker(executable,packages,verify,verify/'plan.json')
    require(cold['verdict']=='component_pass')
    verification=base.strict_json(read(verify/'verification.json'))
    require(verification['selected_model_recomputation']=='pass')
    receipt=dict(schema='m03-qr-reproduction/1',epoch='augmented_direct_qr_v3',fit_count=97,rows=363,
        original_result_sha256=sha256(expected_bytes).hexdigest(),reproduced_result_sha256=sha256(reproduced).hexdigest(),
        complete_result_byte_identity='pass',native_lifetime=lifetime,cold_selected_model=cold,
        predictive_verdict='unresolved',outer='reproduction_of_already_opened_authored_diagnostic',
        field8201='not_verified',host_admission='not_established',export_raw_disposition='denied_unchanged')
    core._write_member(output,'reproduction-result.json',base.canonical_bytes(receipt))
    print(json.dumps(receipt,sort_keys=True),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
