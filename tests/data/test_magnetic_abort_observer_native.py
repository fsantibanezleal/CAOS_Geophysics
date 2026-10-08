"""Actual Windows nested-Job primitive, explicitly not scientific admission."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from magnetic_line_survey_runtime import Accounting, query
import magnetic_line_survey_runtime as public
from magnetic_abort_observer import AbortObserver, process_ids
import magnetic_abort_observer as observer_source


WORKER = '''
import ctypes as c,sys,json,os,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from ctypes import wintypes as w
from magnetic_line_survey_runtime import apis
api,_=apis(); inner=int(sys.argv[2]); member=w.BOOL()
if not api.IsProcessInJob(api.GetCurrentProcess(),inner,c.byref(member)) or not member.value:
    raise RuntimeError('Primitive inner membership refused')
if not api.CloseHandle(inner):raise RuntimeError('Primitive inherited lease close refused')
with Path(sys.argv[3]).open('xb') as stream:
    stream.write(json.dumps(dict(inner_job_verified=True,inherited_lease_closed=True,
        actual_python=sys.executable,actual_pid=os.getpid(),actual_parent_pid=os.getppid())).encode())
    stream.flush();os.fsync(stream.fileno())
time.sleep(30)
'''

CONTROLLER = '''
import ctypes as c,sys,subprocess,time
sys.path.insert(0,sys.argv[1])
from ctypes import wintypes as w
from magnetic_line_survey_runtime import apis,Security,Limits,query
api,_=apis();security=Security(c.sizeof(Security),None,True)
inner=api.CreateJobObjectW(c.byref(security),None)
if not inner:raise RuntimeError('Primitive inner Job refused')
process=None
try:
    limits=Limits();limits.basic.flags=0x2000
    if not api.SetInformationJobObject(inner,9,c.byref(limits),c.sizeof(limits)):
        raise RuntimeError('Primitive inner limits refused')
    startup=subprocess.STARTUPINFO();startup.lpAttributeList={'handle_list':[int(inner)]}
    process=subprocess.Popen([sys.executable,'-B','-S','-c',sys.argv[3],sys.argv[1],str(int(inner)),sys.argv[2]],
        stdin=subprocess.DEVNULL,startupinfo=startup,close_fds=True,creationflags=0x4|0x8)
    if not api.AssignProcessToJobObject(inner,int(process._handle)):
        raise RuntimeError('Primitive child inner assignment refused')
    member=w.BOOL()
    if not api.IsProcessInJob(int(process._handle),inner,c.byref(member)) or not member.value:
        raise RuntimeError('Primitive actual child membership refused')
    nt=c.WinDLL('ntdll');nt.NtResumeProcess.argtypes=[w.HANDLE];nt.NtResumeProcess.restype=c.c_long
    if nt.NtResumeProcess(int(process._handle))!=0:raise RuntimeError('Primitive child resume refused')
    time.sleep(30)
finally:
    if process is not None and process.poll() is None:
        api.TerminateJobObject(inner,2);process.wait(timeout=10)
    api.CloseHandle(inner)
'''


def test_actual_owned_nested_job_controller_death(tmp_path):
    assert sys.platform == 'win32', 'Actual OS primitive required; no skipped native claim'
    executable = Path(os.environ['GEOPHYSICS_MAGNETIC_NATIVE_EXECUTABLE']).resolve(strict=True)
    dependency = Path(public.__file__).parent
    marker = tmp_path/'actual-worker-ready.json'
    source_sha = hashlib.sha256(Path(public.__file__).read_bytes()).hexdigest()
    executable_sha = hashlib.sha256(executable.read_bytes()).hexdigest()
    observer = AbortObserver()
    with (tmp_path/'controller.stdout').open('xb') as stdout, (tmp_path/'controller.stderr').open('xb') as stderr:
        try:
            controller = observer.launch([str(executable), '-B', '-S', '-c', CONTROLLER,
                str(dependency), str(marker), WORKER], stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                cwd=tmp_path, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TEMP=str(tmp_path), TMP=str(tmp_path)))
            deadline = time.monotonic()+10.
            while not marker.exists():
                assert controller.poll() is None, (tmp_path/'controller.stderr').read_text()
                assert time.monotonic() < deadline, 'Actual nested child readiness reserve exhausted'
                time.sleep(.01)
            ready = json.loads(marker.read_bytes())
            assert ready['inner_job_verified'] is True and ready['inherited_lease_closed'] is True
            active = query(observer.api, observer.job, 1, Accounting())
            import psutil
            diagnostic_ids = process_ids(observer.api,observer.job)
            with (tmp_path/'actual-pre-kill-census.json').open('xb') as stream:
                stream.write(json.dumps(dict(total=int(active.total),active=int(active.active),
                    nested_unique_process_ids=diagnostic_ids,
                    diagnostic_process_names={pid:psutil.Process(pid).name() for pid in diagnostic_ids},
                    retained_controller_pid=controller.pid,ready=ready,passed=False,
                    scientific_worker_started=False)).encode())
                stream.flush();os.fsync(stream.fileno())
            assert active.total == 2 and active.active == 2
            stopped = time.monotonic()
            controller.kill()  # Creation-retained process handle, never discovered PID.
            controller.wait(timeout=10.)
            terminal = observer.empty(stopped+10., expected_total=2)
            drained = time.monotonic()-stopped
            assert observer.job is not None and terminal['active_processes'] == 0
            assert source_sha == hashlib.sha256(Path(public.__file__).read_bytes()).hexdigest()
            assert executable_sha == hashlib.sha256(executable.read_bytes()).hexdigest()
            record = dict(schema='magnetic-abort-observer-native-primitive-1', status='passed',
                ancestor_held_before_birth=True, actual_pre_kill=dict(active_processes=2,total_processes=2),
                actual_post_kill=terminal, stop_drain_s=drained, ancestor_forced_termination_before_proof=False,
                public_runtime_sha256=source_sha, actual_executable_sha256=executable_sha,
                observer_sha256=hashlib.sha256(Path(observer_source.__file__).read_bytes()).hexdigest(),
                primitive_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scientific_worker_started=False, scientific_acceptance=False, native_security_admitted=False)
            with (tmp_path/'actual-primitive.json').open('xb') as stream:
                stream.write(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
                stream.flush();os.fsync(stream.fileno())
        finally:
            observer.cleanup()
