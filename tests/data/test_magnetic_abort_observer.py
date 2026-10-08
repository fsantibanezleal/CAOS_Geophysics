"""Authored observer refusal controls, not actual OS/scientific qualification."""

import ctypes as c
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'data-pipeline'))
sys.path.insert(0, str(ROOT/'scripts'))
from magnetic_line_survey_runtime import Accounting, Limits

spec = importlib.util.spec_from_file_location('m04_abort_observer', ROOT/'scripts/magnetic_abort_observer.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Api:
    def __init__(self):
        self.flags, self.samples, self.calls = 0x2000, [(0, 0)], []
        self.reader, self.assign, self.member, self.set_limits = True, True, True, True

    def CreateJobObjectW(self, security, name):
        assert security is None and name is None
        return 81

    def SetInformationJobObject(self, *_):
        return self.set_limits

    def QueryInformationJobObject(self, handle, code, record, *_):
        assert handle == 81
        if not self.reader:
            return False
        if code == 9:
            c.cast(record, c.POINTER(Limits)).contents.basic.flags = self.flags
        else:
            active, total = self.samples.pop(0) if len(self.samples) > 1 else self.samples[0]
            value = c.cast(record, c.POINTER(Accounting)).contents
            value.active, value.total = active, total
        return True

    def AssignProcessToJobObject(self, job, process):
        self.calls.append(('assign', job, process))
        return self.assign

    def IsProcessInJob(self, process, job, member):
        c.cast(member, c.POINTER(c.wintypes.BOOL)).contents.value = self.member
        return True

    def TerminateJobObject(self, job, code):
        self.calls.append(('terminate', job, code))
        self.samples = [(0, self.samples[-1][1])]
        return True

    def CloseHandle(self, handle):
        self.calls.append(('close', handle))
        return True


class Process:
    _handle = 567
    def __init__(self, *_, **options):
        assert options['creationflags'] == 0x4 | 0x8
        assert options['close_fds'] is True
        self.alive = True
    def poll(self):
        return None if self.alive else 2
    def kill(self):
        self.alive = False
    def wait(self, timeout):
        assert timeout > 0
        self.alive = False


def observer(api, **options):
    return module.AbortObserver(api=api, resume=lambda held: api.calls.append(('resume', held)) or 0, **options)


def test_suspended_exact_handle_before_release(monkeypatch):
    api = Api()
    owned = observer(api)
    api.samples = [(1, 1)]
    monkeypatch.setattr(module.subprocess, 'Popen', Process)
    owned.launch(['fixed-controller'])
    assert api.calls == [('assign', 81, 567), ('resume', 567)]
    owned.cleanup()
    assert api.calls[-1] == ('close', 81)


@pytest.mark.parametrize('attack', ['flags', 'set_limits', 'reader'])
def test_setup_refusal_before_birth(attack):
    api = Api()
    setattr(api, attack, 0x2800 if attack == 'flags' else False)
    with pytest.raises(Exception):
        observer(api)
    assert api.calls == [('close', 81)]


@pytest.mark.parametrize('attack', ['assign', 'member', 'census', 'resume'])
def test_no_release_after_setup_refusal(monkeypatch, attack):
    api = Api()
    owned = observer(api)
    api.samples = [(1, 2 if attack == 'census' else 1)]
    if attack in ('assign', 'member'):
        setattr(api, attack, False)
    if attack == 'resume':
        owned.resume = lambda _: 1
    monkeypatch.setattr(module.subprocess, 'Popen', Process)
    with pytest.raises(RuntimeError):
        owned.launch(['fixed-controller'])
    assert ('resume', 567) not in api.calls
    owned.cleanup()
    assert api.calls[-1] == ('close', 81)


def test_delayed_actual_empty_without_termination():
    api = Api()
    ticks = [0.]
    owned = observer(api, clock=lambda: ticks[0], sleep=lambda dt: ticks.__setitem__(0, ticks[0]+dt))
    api.samples = [(1, 2), (0, 2)]
    assert owned.empty(.1, expected_total=2)['active_processes'] == 0
    assert api.calls == []
    owned.cleanup()


@pytest.mark.parametrize('kind', ['foreign', 'reader', 'deadline'])
def test_no_zero_or_new_reserve(kind):
    api = Api()
    ticks = [0.]
    owned = observer(api, clock=lambda: ticks[0], sleep=lambda dt: ticks.__setitem__(0, ticks[0]+dt))
    api.samples = [(1, 3 if kind == 'foreign' else 2)]
    api.reader = kind != 'reader'
    with pytest.raises(Exception):
        owned.empty(.03, expected_total=2)
    assert api.calls == []  # Failure is not converted to forced successful drain.
    api.reader = True
    owned.cleanup()


@pytest.mark.parametrize('failure', ['reader', 'terminate', 'process_wait'])
def test_cleanup_cannot_close_unknown_alive_lease(failure):
    api = Api()
    owned = observer(api)
    owned.process, owned.assigned = Process(creationflags=0x4|0x8,close_fds=True), True
    api.samples = [(1, 1)]
    if failure == 'reader':
        api.reader = False
    elif failure == 'terminate':
        api.TerminateJobObject = lambda *_: False
    else:
        owned.process.wait = lambda **_: (_ for _ in ()).throw(TimeoutError('authored wait refusal'))
    with pytest.raises(Exception):
        owned.cleanup()
    assert owned.job == 81 and ('close', 81) not in api.calls


def qualification():
    from magnetic_original_adapter import PUBLIC_SOURCES
    from magnetic_survey_json import digest
    sources = {name:'a'*64 for name in PUBLIC_SOURCES}
    # Authored protocol ONLY, never a passed actual numerical fit.
    record = dict(schema='magnetic-original-final-fit-qualification-1', case='S2-A', quantity='secondary_enu_nT',
        active_cells=528, source_components=864, final_rows=216, fit_components=648, epsilon_stages=8,
        request_sha256='b'*64, original_sha256='c'*64, source_inventory_sha256=digest(sources), sources=sources,
        status='passed',caps=dict(wall_s=120,accepted=200,cg_per_direction=200,line_search=20,admitted_bytes=805306368),
        fit_wall_s=119.,independent_precision=dict(model_inf_q=1e-6,objective_relative=1e-8,prediction_rms_nT=1e-6,normalized_kkt_inf=1e-7))
    return sources,record


def test_authored_final_qualification_literal_boundary_only():
    sources,record = qualification()
    assert module.verify_final_qualification(record,sources=sources,request_sha256='b'*64,original_sha256='c'*64) is record


@pytest.mark.parametrize('attack', ['first432', 'floated_count', 'unknown', 'source', 'original', 'time', 'boolean_time', 'nan', 'precision', 'epsilon', 'cap'])
def test_final_qualification_refuses_partial_drift_and_original_cap_changes(attack):
    import copy
    sources,record = qualification()
    record = copy.deepcopy(record)
    if attack == 'first432':record['fit_components'] = 432
    elif attack == 'floated_count':record['fit_components'] = 648.
    elif attack == 'unknown':record['unverified'] = True
    elif attack == 'source':record['sources'][next(iter(sources))] = 'd'*64
    elif attack == 'original':record['original_sha256'] = 'd'*64
    elif attack == 'time':record['fit_wall_s'] = 120.001
    elif attack == 'boolean_time':record['fit_wall_s'] = True
    elif attack == 'nan':record['independent_precision']['model_inf_q'] = float('nan')
    elif attack == 'precision':record['independent_precision']['objective_relative'] = 1.001e-8
    elif attack == 'epsilon':record['epsilon_stages'] = 7
    elif attack == 'cap':record['caps']['cg_per_direction'] = 512
    with pytest.raises(ValueError):
        module.verify_final_qualification(record,sources=sources,request_sha256='b'*64,original_sha256='c'*64)
