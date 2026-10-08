"""Ordinary packet/counter tests; never evidence of native Linux containment."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data-pipeline"))
from waveform_m08_linux import LinuxLifetime, parse_cpu, packet, read_packet
from waveform_m08_windows import ControlError, B, S, MEMORY, GAP, POLL


def test_exact_linux_microsecond_domain():
    assert parse_cpu(b"usage_usec 13\nuser_usec 5\nsystem_usec 8\n") == (13000, 5000, 8000)


@pytest.mark.parametrize("raw", [b"", b"usage_usec 1\nuser_usec 0\n", b"usage_usec -1\nuser_usec 0\nsystem_usec 0\n", b"usage_usec 1.0\nuser_usec 0\nsystem_usec 0\n", b"usage_usec 1\nusage_usec 2\nuser_usec 0\nsystem_usec 0\n", b"usage_usec 9223372036854776\nuser_usec 0\nsystem_usec 0\n", b"usage_usec 1\nuser_usec 2\nsystem_usec 0\n"])
def test_bad_cpu_is_not_zero_or_smoothed(raw):
    with pytest.raises(ControlError):
        parse_cpu(raw)


def test_exited_cpu_stable_final_and_no_reset():
    life = LinuxLifetime()
    life.sample(1000000000, 0, 0, 0, 0, 0)
    life.sample(1000000000 + POLL, 13000, 5000, 8000, 1, 1234)
    life.drained(1000000000 + POLL)
    life.sample(1000000000 + 2 * POLL, 15000, 6000, 9000, 0, 1234)
    assert not life.final_ready
    life.sample(1000000000 + 3 * POLL, 15000, 6000, 9000, 0, 1234)
    assert life.final_ready and life.final_cpu_ns == 15000
    life.sample(1000000000 + 4 * POLL, 0, 0, 0, 0, 0)
    assert not life.final_ready and life.failure == "counter_invalid"


@pytest.mark.parametrize("change,reason", [("cpu", "resource_stop"), ("budget", "resource_exceeded"), ("memory", "resource_exceeded"), ("tasks", "resource_exceeded"), ("gap", "sample_gap"), ("regression", "counter_invalid")])
def test_original_caps_failure_absorbs_later_good_samples(change, reason):
    life = LinuxLifetime()
    life.sample(1, 10000, 1000, 9000, 0, 100)
    row = [1 + POLL, 11000, 1000, 10000, 1, 100]
    if change == "cpu": row[1] = S
    if change == "budget": row[1] = B + 1
    if change == "memory": row[-1] = MEMORY + 1
    if change == "tasks": row[-2] = 3
    if change == "gap": row[0] = 1 + GAP + 1
    if change == "regression": row[1] = 9999
    life.sample(*row)
    assert life.failure == reason
    life.sample(row[0] + POLL, max(row[1], 11000), 1000, 10000, 0, max(row[-1], 100))
    assert life.failure is not None and not life.final_ready


def test_fixed_packet_run_sequence_and_no_extra_keys():
    run = "1" * 32
    raw = packet(run, 1, "hello", {"pid": 100})
    assert read_packet(raw, run, 1, "hello") == {"pid": 100}
    for bad in [raw + b" ", raw.replace(b'"sequence":1', b'"sequence":1.0'), raw.replace(b'"sequence":1', b'"sequence":true'), raw.replace(b'"pid":100', b'"pid":100,"pid":100'), raw.replace(b'"schema":', b'"unknown":1,"schema":')]:
        with pytest.raises(ControlError):
            read_packet(bad, run, 1, "hello")
    with pytest.raises(ControlError):
        read_packet(raw, "2" * 32, 1, "hello")


def test_native_identity_and_clock_uint64_not_scientific_float_domain():
    run = "3" * 32
    payload = {"initial": [[1, 9007199254740992], 1024, 1, False, 1780882222333444555]}
    assert read_packet(packet(run, 1, "ack", payload), run, 1, "ack") == payload
    for raw in [packet(run, 1, "ack", payload).replace(b"1780882222333444555", b"18446744073709551616"),
                packet(run, 1, "ack", payload).replace(b"1780882222333444555", b"1e18")]:
        with pytest.raises(ControlError):
            read_packet(raw, run, 1, "ack")


def final_monitor(monkeypatch):
    from waveform_m08_linux import Monitor
    monitor = Monitor(None)
    life = monitor.life
    life.sample(1000000000,10000,1000,9000,1,1234)
    life.drained(1000000000)
    life.sample(1000000000+POLL,15000,6000,9000,0,1234)
    life.sample(1000000000+2*POLL,15000,6000,9000,0,1234)
    monkeypatch.setattr(monitor,"close",lambda:None)  # Authored final-state control, not native proof.
    monkeypatch.setattr(monitor,"counters",lambda:tuple(life.last[1:]))
    return monitor


def test_final_seal_keeps_exact_scientific_row_after_postexit_publication(monkeypatch):
    monitor = final_monitor(monkeypatch)
    row = monitor.seal_final()
    assert row == monitor.life.last and row[4] == 0 and monitor.life.final_ready
    # Post-exit observer publication does not invent a scientific sample timestamp.
    monitor.confirm_final(row)
    assert monitor.life.last == row and monitor.life.max_gap_ns == POLL


@pytest.mark.parametrize("change",["late-gap","not-final","changed-cpu","new-task","changed-peak"])
def test_final_seal_refuses_late_failure_or_changed_held_scope(monkeypatch,change):
    monitor = final_monitor(monkeypatch)
    row = tuple(monitor.life.last)
    if change == "late-gap":
        monitor.life.sample(row[0]+551294670,*row[1:])
    elif change == "not-final":
        monitor.life.final_ready = False
    else:
        values = list(row[1:])
        values[{"changed-cpu":0,"new-task":3,"changed-peak":4}[change]] += 1
        monkeypatch.setattr(monitor,"counters",lambda:tuple(values))
    with pytest.raises(ControlError):
        monitor.seal_final()


def test_failed_owned_service_reset_requires_retained_kernel_and_manager_zero(monkeypatch):
    import waveform_m08_linux as lane
    unit = 'm08-'+'a'*32+'.service'
    commands = []
    monkeypatch.setattr(lane,'_read_at',lambda fd,key:b'0\n')
    monkeypatch.setattr(lane,'_show',lambda unit,key:{'ActiveState':'failed','MainPID':'0',
        'ControlPID':'0','ControlGroup':''}[key])
    monkeypatch.setattr(lane,'_command',lambda argv:commands.append(argv))
    monkeypatch.setattr(lane,'_released_unit',lambda unit:commands.append(('released',unit)))
    lane.retire_failed_service(17,unit)
    assert commands == [[lane.TOOLS['ctl'],'reset-failed',unit],('released',unit)]


@pytest.mark.parametrize('changed',['tasks','MainPID','ControlPID','ControlGroup','name'])
def test_failed_owned_service_no_reset_with_live_unbound_or_missing_evidence(monkeypatch,changed):
    import waveform_m08_linux as lane
    unit = 'm08-'+'a'*32+'.service'
    values = {'ActiveState':'failed','MainPID':'0','ControlPID':'0','ControlGroup':''}
    if changed in values:
        values[changed] = '/retained-group' if changed == 'ControlGroup' else '8'
    monkeypatch.setattr(lane,'_read_at',lambda fd,key:b'1\n' if changed == 'tasks' else b'0\n')
    monkeypatch.setattr(lane,'_show',lambda unit,key:values[key])
    monkeypatch.setattr(lane,'_command',lambda argv:pytest.fail('unproved reset'))
    monkeypatch.setattr(lane,'_released_unit',lambda unit:pytest.fail('unproved release'))
    with pytest.raises(ControlError):
        lane.retire_failed_service(17,'other.service' if changed == 'name' else unit)


@pytest.mark.parametrize('part,reason',[(b'CANCEL\n','cancelled'),(b'','caller_lost'),
    (b'CANC',None),(b'INVALID\n',None)])
def test_pending_caller_frame_on_refused_native_operation_never_invents_cancel(monkeypatch,part,reason):
    import waveform_m08_linux as lane
    caller = object.__new__(lane.LinuxCallerControl)
    caller.fd,caller.buffer,caller.reason,caller.started_ns = 17,b'',None,None
    monkeypatch.setattr(lane.select,'select',lambda *args:([17],[],[]))
    monkeypatch.setattr(lane.os,'read',lambda fd,cap:part)
    assert lane.refused_caller_reason(caller) == reason
    assert caller.reason == reason
    assert (caller.started_ns is not None) == (reason is not None)
