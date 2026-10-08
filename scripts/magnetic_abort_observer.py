"""Abort-test custody: a held unnamed ancestor Job, never late PID lookup.

Uses public M03 Job types and query. This observer imposes only kill-on-close;
it cannot establish any scientific or hosted resource/security acceptance.
"""

import ctypes as c
from ctypes import wintypes as w
import subprocess
import time
import math

from magnetic_line_survey_runtime import Accounting, Limits, apis, query


class ProcessList(c.Structure):
    _fields_ = [('assigned', w.DWORD), ('returned', w.DWORD), ('ids', c.c_size_t*8)]


def process_ids(api, job):
    """Read-only exact bounded nested census, NEVER PID acquisition/signalling."""
    sample = query(api, job, 3, ProcessList())
    if sample.assigned != sample.returned or sample.returned > 8:
        raise RuntimeError('Complete bounded nested process census refused')
    ids = [int(sample.ids[k]) for k in range(sample.returned)]
    if any(value <= 0 for value in ids) or len(set(ids)) != len(ids):
        raise RuntimeError('Unique complete nested process census refused')
    return ids


def verify_final_qualification(record, *, sources, request_sha256, original_sha256):
    """Trusted operator source-bound evidence, not scientific truth from JSON."""
    from magnetic_original_adapter import PUBLIC_SOURCES
    from magnetic_survey_json import digest
    expected = dict(schema='magnetic-original-final-fit-qualification-1', case='S2-A',
        quantity='secondary_enu_nT', active_cells=528, source_components=864,
        final_rows=216, fit_components=648, epsilon_stages=8,
        request_sha256=request_sha256, original_sha256=original_sha256,
        source_inventory_sha256=digest(sources),
        sources={name: sources[name] for name in PUBLIC_SOURCES}, status='passed',
        caps=dict(wall_s=120, accepted=200, cg_per_direction=200, line_search=20, admitted_bytes=805306368))
    def exact(value, wanted):
        if type(value) is not type(wanted):
            return False
        if type(wanted) is dict:
            return set(value) == set(wanted) and all(exact(value[k], wanted[k]) for k in wanted)
        return value == wanted
    if type(record) is not dict or set(record) != set(expected) | {'fit_wall_s', 'independent_precision'} \
            or any(not exact(record[key], value) for key, value in expected.items()):
        raise ValueError('Exact current original final648 fit qualifier required')
    seconds = record['fit_wall_s']
    precision = record['independent_precision']
    limits = dict(model_inf_q=1e-6, objective_relative=1e-8, prediction_rms_nT=1e-6, normalized_kkt_inf=1e-7)
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 120 \
            or type(precision) is not dict or set(precision) != set(limits) \
            or any(type(precision[k]) not in (int, float) or not math.isfinite(precision[k])
                   or not 0 <= precision[k] <= bound for k, bound in limits.items()):
        raise ValueError('Original final-fit deadline or independent precision refused')
    return record


class AbortObserver:
    def __init__(self, *, api=None, resume=None, clock=time.monotonic, sleep=time.sleep):
        self.api = apis()[0] if api is None else api
        if resume is None:
            nt = c.WinDLL('ntdll')
            nt.NtResumeProcess.argtypes, nt.NtResumeProcess.restype = [w.HANDLE], c.c_long
            resume = nt.NtResumeProcess
        self.resume, self.clock, self.sleep = resume, clock, sleep
        self.job, self.process, self.assigned = None, None, False
        self.job = self.api.CreateJobObjectW(None, None)
        if not self.job:
            raise RuntimeError('Observer Job creation refused')
        try:
            limits = Limits()
            limits.basic.flags = 0x2000
            if not self.api.SetInformationJobObject(self.job, 9, c.byref(limits), c.sizeof(limits)):
                raise RuntimeError('Observer Job limits refused')
            actual = query(self.api, self.job, 9, Limits())
            if actual.basic.flags != 0x2000 or any((actual.basic.job_cpu,
                    actual.basic.process_cpu, actual.basic.active, actual.job_memory, actual.process_memory)):
                raise RuntimeError('Observer must not introduce resource/breakaway limits')
            self.empty(self.clock()+10., expected_total=0)
        except BaseException:
            # There has been no process birth; closing cannot manufacture drain.
            self.api.CloseHandle(self.job)
            self.job = None
            raise

    def launch(self, command, **options):
        if self.process is not None or self.job is None:
            raise RuntimeError('One creation-retained controller only')
        self.process = subprocess.Popen(command, creationflags=0x4 | 0x8,
                                        close_fds=True, **options)
        held = int(self.process._handle)
        if not self.api.AssignProcessToJobObject(self.job, held):
            raise RuntimeError('Suspended controller Job assignment refused')
        self.assigned = True
        member = w.BOOL()
        if not self.api.IsProcessInJob(held, self.job, c.byref(member)) or not member.value:
            raise RuntimeError('Actual controller ancestor membership refused')
        sample = query(self.api, self.job, 1, Accounting())
        if sample.active != 1 or sample.total != 1:
            raise RuntimeError('Exact single suspended controller birth required')
        if self.resume(held) != 0:
            raise RuntimeError('Held controller release refused')
        return self.process

    def empty(self, deadline, *, expected_total):
        # A read failure is never zero; do not restart the caller's reserve.
        while self.clock() < deadline:
            sample = query(self.api, self.job, 1, Accounting())
            if sample.total != expected_total:
                raise RuntimeError('Unexpected ancestor process census')
            if sample.active == 0:
                return dict(active_processes=0, total_processes=int(sample.total),
                            cpu_s=(sample.user+sample.kernel)/10000000)
            self.sleep(.01)
        raise RuntimeError('Ancestor group extinction reserve exhausted')

    def cleanup(self):
        if self.job is None:
            return
        deadline = self.clock()+10.
        if self.process is not None and self.process.poll() is None:
            if self.assigned:
                if not self.api.TerminateJobObject(self.job, 2):
                    raise RuntimeError('Exact owned ancestor cleanup refused; lease retained')
            else:
                # Assignment failed while this exact retained process was suspended.
                self.process.kill()
            self.process.wait(timeout=max(.001, deadline-self.clock()))
        sample = query(self.api, self.job, 1, Accounting())
        if sample.active:
            if not self.api.TerminateJobObject(self.job, 2):
                raise RuntimeError('Owned descendant cleanup refused; lease retained')
        self.empty(deadline, expected_total=int(sample.total))
        if not self.api.CloseHandle(self.job):
            raise RuntimeError('Observer handle close refused')
        self.job = None
