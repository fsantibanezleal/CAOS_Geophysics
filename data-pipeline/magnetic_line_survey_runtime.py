"""Windows cold-process lifetime control for the provisional local M03 lane.

This is not VPS admission. A real Job, not JSON claiming containment, gates
large native work. Only the fixed sibling worker can execute in this Job.
"""
from __future__ import annotations

import ctypes as c
from ctypes import wintypes as w
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from magnetic_line_survey import SurveyError, RSS_LIMIT, SCRATCH_LIMIT
from magnetic_line_survey_io import external_path

CPU_LIMIT = 21600
WALL_LIMIT = 43200
REQUIRED_FLAGS = 0x2000 | 0x200 | 0x8 | 0x4  # kill/Job memory/active count/Job time


class Basic(c.Structure):
    _fields_ = [('process_cpu', c.c_longlong), ('job_cpu', c.c_longlong), ('flags', w.DWORD),
                ('min_working', c.c_size_t), ('max_working', c.c_size_t), ('active', w.DWORD),
                ('affinity', c.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]


class IO(c.Structure):
    _fields_ = [('counter'+str(i), c.c_ulonglong) for i in range(6)]


class Limits(c.Structure):
    _fields_ = [('basic', Basic), ('io', IO), ('process_memory', c.c_size_t),
                ('job_memory', c.c_size_t), ('peak_process_memory', c.c_size_t), ('peak_job_memory', c.c_size_t)]


class Accounting(c.Structure):
    _fields_ = [('user', c.c_longlong), ('kernel', c.c_longlong), ('period_user', c.c_longlong),
                ('period_kernel', c.c_longlong), ('faults', w.DWORD), ('total', w.DWORD),
                ('active', w.DWORD), ('terminated', w.DWORD)]


class Memory(c.Structure):
    _fields_ = [('cb', w.DWORD), ('faults', w.DWORD), ('peak_rss', c.c_size_t), ('rss', c.c_size_t),
                ('peak_paged', c.c_size_t), ('paged', c.c_size_t), ('peak_nonpaged', c.c_size_t),
                ('nonpaged', c.c_size_t), ('pagefile', c.c_size_t), ('peak_pagefile', c.c_size_t),
                ('private', c.c_size_t)]


class Security(c.Structure):
    _fields_ = [('length', w.DWORD), ('descriptor', c.c_void_p), ('inherit', w.BOOL)]


def apis():
    if sys.platform != 'win32':
        raise SurveyError('resource_refused', 'fit')
    api = c.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'CreateJobObjectW': ([c.POINTER(Security), w.LPCWSTR], w.HANDLE),
        'SetInformationJobObject': ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD], w.BOOL),
        'QueryInformationJobObject': ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p], w.BOOL),
        'AssignProcessToJobObject': ([w.HANDLE, w.HANDLE], w.BOOL),
        'IsProcessInJob': ([w.HANDLE, w.HANDLE, c.POINTER(w.BOOL)], w.BOOL),
        'GetCurrentProcess': ([], w.HANDLE),
        'TerminateJobObject': ([w.HANDLE, w.UINT], w.BOOL),
        'CloseHandle': ([w.HANDLE], w.BOOL),
        'WaitForSingleObject': ([w.HANDLE, w.DWORD], w.DWORD),
        'GetExitCodeProcess': ([w.HANDLE, c.POINTER(w.DWORD)], w.BOOL),
    }
    for name, (args, result) in signatures.items():
        function = getattr(api, name)
        function.argtypes, function.restype = args, result
    psapi = c.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, c.POINTER(Memory), w.DWORD]
    psapi.GetProcessMemoryInfo.restype = w.BOOL
    return api, psapi


def query(api, handle, code, record):
    if not api.QueryInformationJobObject(handle, code, c.byref(record), c.sizeof(record), None):
        raise SurveyError('resource_refused', 'fit')
    return record


def require_job(handle):
    if type(handle) is not int or handle <= 0:
        raise SurveyError('resource_refused', 'fit')
    api, _ = apis()
    member = w.BOOL()
    limits = query(api, handle, 9, Limits())
    if not api.IsProcessInJob(api.GetCurrentProcess(), handle, c.byref(member)) or not member.value or \
       limits.basic.flags & REQUIRED_FLAGS != REQUIRED_FLAGS or limits.basic.flags & (0x800 | 0x1000) or \
       limits.basic.active != 1 or not 0 < limits.job_memory <= RSS_LIMIT or \
       not 0 < limits.basic.job_cpu <= CPU_LIMIT*10000000:
        raise SurveyError('resource_refused', 'fit')


def owned_bytes(root):
    total = 0
    for directory, folders, files in os.walk(root, followlinks=False):
        for name in folders + files:
            item = Path(directory) / name
            external_path(item, directory=name in folders)
        total += sum((Path(directory)/name).stat().st_size for name in files)
    return total


def counters(api, psapi, job, process):
    accounting = query(api, job, 1, Accounting())
    limits = query(api, job, 9, Limits())
    memory = Memory(cb=c.sizeof(Memory))
    if not psapi.GetProcessMemoryInfo(process, c.byref(memory), memory.cb):
        raise SurveyError('resource_refused', 'fit')
    return dict(cpu_s=(accounting.user+accounting.kernel)/10000000,
                peak_rss_bytes=int(memory.peak_rss), peak_committed_bytes=int(limits.peak_job_memory),
                active_processes=int(accounting.active), total_processes=int(accounting.total))


def run_worker(executable, package_root, scratch, plan_path, *, cancel_after=None, cancel_when_ready=False):
    """Start suspended; assign before imports; retain counters through drain.

    Explicit real CPython executable and existing package root (not a virtualenv
    redirector). Worker source/executable/package byte provenance is retained by
    the caller's receipt. A provisional component pass is not full acceptance.
    """
    api, psapi = apis()
    executable = Path(executable).resolve(strict=True)
    packages = Path(package_root).resolve(strict=True)
    scratch = external_path(scratch)
    plan_path = external_path(plan_path, directory=False)
    source_names = ('magnetic_line_contract.py', 'magnetic_line_survey.py', 'magnetic_line_survey_contract.py',
                    'magnetic_line_survey_io.py', 'magnetic_line_survey_runtime.py', 'magnetic_line_survey_worker.py',
                    'magnetic_line_survey_geometry.py', 'magnetic_line_survey_measurements.py',
                    'magnetic_line_survey_crossovers.py', 'magnetic_line_survey_support.py', 'magnetic_line_survey_seal.py')
    def source_identity():
        return {name: sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in source_names}
    sources_before = source_identity()
    executable_hash = sha256(executable.read_bytes()).hexdigest()
    if plan_path.parent != scratch or cancel_after is not None and \
       (type(cancel_after) not in (int, float) or not 0 < cancel_after <= WALL_LIMIT-60):
        raise SurveyError('invalid_contract', 'seal')
    if shutil.disk_usage(scratch).free < 268435456:
        raise SurveyError('resource_refused', 'seal')
    security = Security(c.sizeof(Security), None, True)
    job = api.CreateJobObjectW(c.byref(security), None)
    if not job:
        raise SurveyError('resource_refused', 'fit')
    process = None
    start, parent_start = time.perf_counter(), time.process_time()
    stopped = None
    cause = None
    ready_at = None
    try:
        limits = Limits()
        limits.basic.flags = REQUIRED_FLAGS
        limits.basic.active = 1
        limits.basic.job_cpu = CPU_LIMIT*10000000
        limits.job_memory = RSS_LIMIT
        if not api.SetInformationJobObject(job, 9, c.byref(limits), c.sizeof(limits)):
            raise SurveyError('resource_refused', 'fit')
        startup = subprocess.STARTUPINFO()
        startup.lpAttributeList = {'handle_list': [int(job)]}
        environment = dict(os.environ)
        for key in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS', 'NUMBA_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
            environment[key] = '1'
        environment['NUMBA_CACHE_DIR'] = str(scratch/'numba')
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        # -S skips all startup hooks; only these fixed sibling and explicit
        # pre-existing scientific directories enter the worker import path.
        worker = Path(__file__).with_name('magnetic_line_survey_worker.py').resolve(strict=True)
        with (scratch/'stdout.log').open('xb') as stdout, (scratch/'stderr.log').open('xb') as stderr:
            process = subprocess.Popen([str(executable), '-B', '-S', str(worker), '--packages', str(packages),
                '--job-handle', str(int(job)), '--plan', str(plan_path)], stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, env=environment, cwd=str(scratch),
                startupinfo=startup, close_fds=True, creationflags=0x4 | 0x08000000)
            if not api.AssignProcessToJobObject(job, int(process._handle)):
                raise SurveyError('resource_refused', 'fit')
            nt = c.WinDLL('ntdll')
            nt.NtResumeProcess.argtypes, nt.NtResumeProcess.restype = [w.HANDLE], c.c_long
            if nt.NtResumeProcess(int(process._handle)) != 0:
                raise SurveyError('resource_refused', 'fit')
            sample = None
            next_disk = start
            while True:
                state = api.WaitForSingleObject(int(process._handle), 100)
                if state not in (0, 258):
                    raise SurveyError('resource_refused', 'fit')
                sample = counters(api, psapi, job, int(process._handle))
                now = time.perf_counter()
                if state == 0:
                    break
                disk_bad = False
                if now >= next_disk:
                    disk_bad = owned_bytes(scratch) > SCRATCH_LIMIT or shutil.disk_usage(scratch).free < 67108864
                    next_disk = now + 1
                if cancel_when_ready and ready_at is None and (scratch/'native-ready.json').is_file():
                    ready_at = now
                cancel_start = ready_at if cancel_when_ready else start
                cancelled = cancel_after is not None and cancel_start is not None and now-cancel_start >= cancel_after
                if stopped is None and (cancelled or disk_bad or sample['cpu_s'] >= CPU_LIMIT-60 or
                    now-start >= WALL_LIMIT-60 or sample['peak_rss_bytes'] > RSS_LIMIT or
                    sample['peak_committed_bytes'] > RSS_LIMIT or time.process_time()-parent_start > 300):
                    cause = 'cancelled' if cancelled else 'resource_refused'
                    stopped = (now, sample['cpu_s'])
                    if not api.TerminateJobObject(job, 2):
                        raise SurveyError('resource_refused', 'fit')
            # Query terminal retained lifetime information, never infer zero.
            sample = counters(api, psapi, job, int(process._handle))
            code = w.DWORD()
            if not api.GetExitCodeProcess(int(process._handle), c.byref(code)) or code.value == 259:
                raise SurveyError('resource_refused', 'fit')
            wall = time.perf_counter()-start
            parent_cpu = time.process_time()-parent_start
            size = owned_bytes(scratch)
            stop_wall = time.perf_counter()-stopped[0] if stopped else None
            stop_cpu = sample['cpu_s']-stopped[1] if stopped else None
            if sources_before != source_identity() or executable_hash != sha256(executable.read_bytes()).hexdigest():
                raise SurveyError('custody_mismatch', 'export')
            passed = code.value == 0 and cause is None and sample['total_processes'] == 1 and sample['active_processes'] == 0 and \
                sample['cpu_s'] > 0 and sample['peak_rss_bytes'] > 0 and sample['peak_committed_bytes'] > 0 and \
                sample['peak_rss_bytes'] <= RSS_LIMIT and sample['peak_committed_bytes'] <= RSS_LIMIT and \
                sample['cpu_s'] <= CPU_LIMIT and wall <= WALL_LIMIT and parent_cpu <= 300 and size <= SCRATCH_LIMIT
            if stopped and (stop_cpu > 10 or stop_wall > 10):
                cause = 'resource_refused'
            receipt = dict(schema='m03-local-lifetime/1', verdict='component_pass' if passed else cause or 'resource_refused',
                exit_code=int(code.value), **sample, wall_s=wall, scratch_bytes=size,
                parent_cpu_s=parent_cpu, stop_wall_s=stop_wall, stop_cpu_s=stop_cpu,
                admission='not_established', source_sha256=sources_before, actual_executable_sha256=executable_hash)
            from magnetic_line_survey import _write_member
            from magnetic_line_contract import canonical_bytes
            # Count the terminal receipt itself in the owned scratch inventory.
            # Only the digit width changes; require an exact serialization fixed
            # point rather than report the pre-receipt directory as total bytes.
            for _ in range(8):
                final_size = size + len(canonical_bytes(receipt))
                if receipt['scratch_bytes'] == final_size:
                    break
                receipt['scratch_bytes'] = final_size
            else:
                raise SurveyError('resource_refused', 'export')
            if receipt['scratch_bytes'] > SCRATCH_LIMIT:
                raise SurveyError('resource_refused', 'export')
            write_cpu, write_wall = time.process_time(), time.perf_counter()
            _write_member(scratch, 'lifetime.json', canonical_bytes(receipt))
            # Parent receipt serialization is explicitly outside child lifetime;
            # report it separately rather than padding the cold-worker timings.
            receipt['receipt_write_cpu_s'] = time.process_time()-write_cpu
            receipt['receipt_write_wall_s'] = time.perf_counter()-write_wall
            return receipt
    finally:
        if process is not None and process.poll() is None:
            api.TerminateJobObject(job, 2)
            # No indefinite wait on a failed controller; successful termination
            # must drain within the cancellation reserve.
            if api.WaitForSingleObject(int(process._handle), 10000) != 0:
                api.CloseHandle(job)
                raise SurveyError('resource_refused', 'fit')
        api.CloseHandle(job)
