"""Fixed local magnetic child in a Windows Job; never hosted admission.

Compose the reviewed public provisional M03 Win32 observation types/functions.
No native controller binary, arbitrary executable payload or production profile
is installed/activated. Native security/tail/cross-platform admission is separate.
"""

import ctypes as c
from ctypes import wintypes as w
import hashlib
import os
from pathlib import Path
import subprocess
import time

from magnetic_local_paths import external_path
from magnetic_survey_json import canonical, fail


def run_local_survey(executable, package_root, dependency_roots, plan_path, *, cancel_after=None):
    from magnetic_line_survey_runtime import apis, query, counters, Limits, Security, REQUIRED_FLAGS
    plan_path = external_path(plan_path)
    scratch = plan_path.parent
    executable = Path(executable).resolve(strict=True)
    packages = Path(package_root).resolve(strict=True)
    roots = tuple(Path(p).resolve(strict=True) for p in dependency_roots)
    if not roots or not executable.is_file() or not packages.is_dir():
        fail('resource', '$/native', 'Explicit existing interpreter/packages/dependency roots required')
    if cancel_after is not None and (type(cancel_after) is not float or not 0. < cancel_after <= 7200.):
        fail('resource', '$/native', 'Bounded explicit cancellation time required')
    worker = Path(__file__).with_name('magnetic_native_worker.py')
    pins = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (executable, worker, Path(__file__))}
    api, psapi = apis()
    security = Security(c.sizeof(Security), None, True)
    job = api.CreateJobObjectW(c.byref(security), None)
    if not job:
        fail('resource', '$/native', 'Job creation failed before scientific birth')
    process = None
    clock, parent_cpu = time.monotonic(), time.process_time()
    cause, stopped = None, None
    try:
        limits = Limits()
        limits.basic.flags, limits.basic.active = REQUIRED_FLAGS, 1
        limits.basic.job_cpu, limits.job_memory = 3600*10000000, 805306368
        if not api.SetInformationJobObject(job, 9, c.byref(limits), c.sizeof(limits)):
            fail('resource', '$/native', 'Actual job limits unavailable before birth')
        retained = query(api, job, 9, Limits())
        if (retained.basic.flags != REQUIRED_FLAGS or retained.basic.active != 1
                or retained.basic.job_cpu != limits.basic.job_cpu or retained.job_memory != limits.job_memory):
            fail('resource', '$/native', 'Actual job readback mismatch before birth')
        startup = subprocess.STARTUPINFO()
        startup.lpAttributeList = {'handle_list': [int(job)]}
        env = dict(os.environ)
        env.update(TEMP=str(scratch), TMP=str(scratch), TMPDIR=str(scratch),
                   NUMBA_CACHE_DIR=str(scratch/'numba'), PYTHONDONTWRITEBYTECODE='1')
        for key in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS', 'NUMBA_NUM_THREADS'):
            env[key] = '1'
        command = [str(executable), '-B', '-S', str(worker), '--packages', str(packages),
                   '--job-handle', str(int(job)), '--plan', str(plan_path), '--dependencies', *map(str, roots)]
        with (scratch/'native.stdout').open('xb') as stdout, (scratch/'native.stderr').open('xb') as stderr:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                env=env, cwd=scratch, startupinfo=startup, close_fds=True, creationflags=0x4|0x08000000)
            if not api.AssignProcessToJobObject(job, int(process._handle)):
                fail('resource', '$/native', 'Suspended child assignment failed; no running fallback')
            nt = c.WinDLL('ntdll')
            nt.NtResumeProcess.argtypes, nt.NtResumeProcess.restype = [w.HANDLE], c.c_long
            if nt.NtResumeProcess(int(process._handle)) != 0:
                fail('resource', '$/native', 'Assigned child release failed')
            peak_rss, peak_private, peak_scratch = 0, 0, 0
            while True:
                status = api.WaitForSingleObject(int(process._handle), 50)
                if status not in (0, 258):
                    fail('resource', '$/native', 'Actual retained process observation failed')
                sample = counters(api, psapi, job, int(process._handle))
                peak_rss = max(peak_rss, sample['peak_rss_bytes'])
                peak_private = max(peak_private, sample['peak_committed_bytes'])
                size = 0
                for directory, folders, files in os.walk(scratch, followlinks=False):
                    for name in folders+files:
                        path = external_path(Path(directory)/name)
                        if name in files:
                            try:
                                size += path.stat().st_size
                            except FileNotFoundError:
                                # Producer can finish/rename a pending file.
                                # Final after-drain inventory below is strict.
                                if status == 0:
                                    raise
                peak_scratch = max(peak_scratch, size)
                elapsed = time.monotonic()-clock
                if status == 0:
                    break
                if cause is None:
                    if cancel_after is not None and elapsed >= cancel_after:
                        cause = 'cancelled'
                    elif elapsed >= 7200. or sample['cpu_s'] >= 3600. or peak_rss > 805306368 or peak_scratch > 536870912:
                        cause = 'resource'
                    if cause:
                        stopped = time.monotonic()
                        if not api.TerminateJobObject(job, 4):
                            fail('resource', '$/native', 'Whole-job stop failed')
                if stopped is not None and time.monotonic()-stopped > 10.:
                    fail('resource', '$/native', 'Whole-job stop did not drain within reserve')
            final = counters(api, psapi, job, int(process._handle))
            if final['active_processes'] != 0 or final['total_processes'] != 1:
                fail('resource', '$/native', 'Actual whole-job drain/process-count proof failed')
            code = w.DWORD()
            if not api.GetExitCodeProcess(int(process._handle), c.byref(code)) or code.value == 259:
                fail('resource', '$/native', 'Actual retained exit unavailable')
            if pins != {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (executable, worker, Path(__file__))}:
                fail('dependency', '$/native', 'Loaded local worker/interpreter changed')
            receipt = dict(schema='magnetic-local-lifetime-1', execution='actual_windows_job_component',
                exit_code=int(code.value), cause=cause, wall_s=time.monotonic()-clock, cpu_s=final['cpu_s'],
                peak_rss_bytes=peak_rss, peak_private_committed_bytes=peak_private, peak_scratch_bytes=peak_scratch,
                active_processes=final['active_processes'], total_processes=final['total_processes'],
                stop_drain_s=None if stopped is None else time.monotonic()-stopped,
                parent_cpu_s=time.process_time()-parent_cpu, source_pins=pins,
                native_security_admitted=False, online_admitted=False)
            with (scratch/'native-lifetime.json').open('xb') as stream:
                stream.write(canonical(receipt))
                stream.flush()
                os.fsync(stream.fileno())
            return receipt
    finally:
        if process is not None and api.WaitForSingleObject(int(process._handle), 0) != 0:
            api.TerminateJobObject(job, 4)
            if api.WaitForSingleObject(int(process._handle), 10000) != 0:
                api.CloseHandle(job)
                fail('resource', '$/native', 'Failed worker did not drain')
        api.CloseHandle(job)
