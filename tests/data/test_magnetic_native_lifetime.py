"""Native pre-birth death controls plus explicitly authored counter negatives."""

import ctypes
import os
from pathlib import Path
import sys

import pytest

import magnetic_native_runtime as runtime
from magnetic_survey_json import InputError, canonical


@pytest.mark.parametrize('changed', [
    {'cpu_s': 3600.}, {'peak_rss_bytes': 805306369}, {'peak_committed_bytes': 805306369},
])
def test_terminal_resource_counters_do_not_bypass_caps(changed):
    # Pure authored counters, not native or resource admission evidence.
    sample = dict(cpu_s=1., peak_rss_bytes=4096, peak_committed_bytes=8192)
    assert not runtime.resource_exceeded(sample, 1., 1024)
    sample.update(changed)
    assert runtime.resource_exceeded(sample, 1., 1024)


def test_terminal_wall_and_scratch_caps_are_literal():
    sample = dict(cpu_s=1., peak_rss_bytes=805306368, peak_committed_bytes=805306368)
    assert not runtime.resource_exceeded(sample, 7199., 536870912)
    assert runtime.resource_exceeded(sample, 7200., 1)
    assert runtime.resource_exceeded(sample, 1., 536870913)


def test_actual_scratch_bytes_and_loaded_observation_sources(tmp_path):
    (tmp_path/'one').write_bytes(b'actual scratch')
    (tmp_path/'inner').mkdir()
    (tmp_path/'inner'/'two').write_bytes(b'ab')
    assert runtime.scratch_bytes(tmp_path, settled=True) == 16
    pins = runtime.observation_pins()
    assert len(pins) == 5 and all(len(v) == 64 and Path(k).is_file() for k, v in pins.items())


@pytest.mark.parametrize('fault', ['assign', 'membership', 'resume'])
def test_actual_suspended_native_child_refusal_is_drained_without_birth(tmp_path, monkeypatch, fault):
    assert sys.platform == 'win32', 'This gate requires actual Windows, not a skip or authored native counter'
    from ctypes import wintypes as w
    import magnetic_line_survey_runtime as observed
    api, psapi = observed.apis()
    held, final_job = [], []
    real_create, real_popen, real_windll = api.CreateJobObjectW, runtime.subprocess.Popen, ctypes.WinDLL

    class Proxy:
        job = None

        def __getattr__(self, name):
            return getattr(api, name)

        def CreateJobObjectW(self, *args):
            self.job = real_create(*args)
            return self.job

        def AssignProcessToJobObject(self, job, process):
            # Actual kernel refusal with an invalid target handle, not a mocked
            # success or injected numeric process observation.
            return api.AssignProcessToJobObject(job, 0 if fault == 'assign' else process)

        def IsProcessInJob(self, process, job, member):
            return api.IsProcessInJob(0 if fault == 'membership' else process, job, member)

        def CloseHandle(self, handle):
            if handle == self.job:
                value = observed.query(api, handle, 1, observed.Accounting())
                final_job.append(dict(active=int(value.active), total=int(value.total)))
            return api.CloseHandle(handle)

    proxy = Proxy()
    monkeypatch.setattr(observed, 'apis', lambda: (proxy, psapi))

    def popen(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        held.append(process)
        return process

    monkeypatch.setattr(runtime.subprocess, 'Popen', popen)
    if fault == 'resume':
        nt = real_windll('ntdll')
        original = nt.NtResumeProcess
        original.argtypes, original.restype = [w.HANDLE], ctypes.c_long

        class RefusedResume:
            def __call__(self, handle):
                return original(0)  # Actual invalid-handle NT refusal.

        class RefusedLibrary:
            NtResumeProcess = RefusedResume()

        monkeypatch.setattr(ctypes, 'WinDLL', lambda name, *a, **kw:
                            RefusedLibrary() if name == 'ntdll' else real_windll(name, *a, **kw))
    configured = os.environ.get('GEOPHYSICS_TEST_NATIVE_EXECUTABLE')
    assert configured, 'Set the explicit installed CPython executable, not a Windows Store launch alias'
    executable = Path(configured).resolve(strict=True)
    packages = Path(sys.prefix)/'Lib'/'site-packages'
    dependency = Path(observed.__file__).parent
    plan = tmp_path/'plan.json'
    plan.write_bytes(canonical({}))  # Refused BEFORE worker can parse or import science.
    with pytest.raises(InputError, match={'assign': 'assignment failed', 'membership': 'membership unavailable',
                                         'resume': 'release failed'}[fault]):
        runtime.run_local_survey(executable, packages, (dependency,), plan)
    assert len(held) == 1 and api.WaitForSingleObject(int(held[0]._handle), 0) == 0
    assert final_job == [dict(active=0, total=0 if fault == 'assign' else 1)]
    assert not (tmp_path/'worker-born.json').exists() and not (tmp_path/'native-lifetime.json').exists()
    (tmp_path/'actual-prebirth-proof.json').write_bytes(canonical(dict(
        schema='magnetic-actual-prebirth-control-1', fault=fault, retained_process_signalled=True,
        actual_terminal_job=final_job[0], no_worker_birth=True, no_scientific_import=True,
        actual_kernel_refusal=True, native_security_admitted=False)))
