"""Deterministic bounds only; no writes, compile, native process or clocks."""
import ctypes as C
import struct

import pytest

from test_contract import Core, sample, I64, U64


@pytest.fixture
def core():
    return Core()


@pytest.mark.parametrize("length", [4161, U64])
def test_cap_before_pointer_read(core, length):
    out = C.c_uint32(999)
    assert core.dll.ncc_frame_preflight(None, length, C.byref(out)) == 11
    assert out.value == 999


def test_null_arithmetic_output_safe(core):
    assert core.dll.ncc_windows_cpu(0, 0, None) == 10


@pytest.mark.parametrize("capacity", [0, 1023, 1025, U64])
def test_state_capacity_before_access(core, capacity):
    assert core.dll.ncc_apply(None, capacity, 1, None, U64) == 11


@pytest.mark.parametrize("platform,payload", [
    (1, sample(native=(I64 + 1, 0, 0), cpu=0)),
    (1, sample(native=(0, 0, 1), cpu=0)),
    (1, sample(active=(33, 33, 0))),
    (1, sample(active=(1, 0, 0))),
    (1, sample(active=(1, 1, 2))),
    (1, sample(active=(1, 2**32, 0))),
    (1, sample(cpu=1)),
    (1, sample(reserved=1)),
    (2, sample(2, active=(2, 0, 0))),
    (2, sample(2, active=(1, 2, 0))),
    (2, sample(2, active=(1, 0, 2))),
    (2, sample(2, native=(0, U64, 1), cpu=0)),
])
def test_bad_sample_not_committed(core, platform, payload):
    s = core.session(platform).running()
    assert s.send(8, payload) != 0
    assert s.snap()[0] == 10 and s.snap()[5] == 0


@pytest.mark.parametrize("channel,cap", [
    (1, 65536), (2, 65536), (3, 65536), (4, 67108864),
    (5, 268435456), (6, 16777216),
])
def test_backpressure_bounded_fail_closed(core, channel, cap):
    s = core.session()
    assert core.dll.ncc_account_bytes(s.state, 1024, channel, cap) == 0
    before = s.snap()
    slot = {1: 13, 2: 14, 3: 15, 4: 16, 5: 17, 6: 12}[channel]
    assert before[slot] == cap
    assert core.dll.ncc_account_bytes(s.state, 1024, channel, 1) == 11
    assert s.snap()[slot] == cap
    assert core.dll.ncc_account_bytes(s.state, 1024, channel, 0) == 11


def test_transform_scratch_constant(core):
    s = core.session(lane=2)
    assert core.dll.ncc_account_bytes(s.state, 1024, 5, 536870912) == 0
    assert core.dll.ncc_account_bytes(s.state, 1024, 5, 1) == 11


@pytest.mark.parametrize("channel", [0, 7, 2**32 - 1])
def test_unknown_resource_channel(core, channel):
    s = core.session()
    assert core.dll.ncc_account_bytes(s.state, 1024, channel, 0) == 10


def test_queue_four_then_five_held(core):
    s = core.session()
    for count in range(1, 5):
        assert core.dll.ncc_queue(s.state, 1024, 1) == 0
        assert s.snap()[11] == count
    assert core.dll.ncc_queue(s.state, 1024, 1) == 11
    assert s.snap()[11] == 4


def test_queue_decrement_underflow(core):
    s = core.session()
    assert core.dll.ncc_queue(s.state, 1024, 1) == 0
    assert core.dll.ncc_queue(s.state, 1024, 2) == 0
    assert core.dll.ncc_queue(s.state, 1024, 2) == 14


def test_sample_count_checked_before_update(core):
    s = core.session().running()
    for at in range(1, 32769):
        assert s.send(8, sample(at=at)) == 0
    assert s.snap()[5] == 32768
    assert s.send(8, sample(at=32769)) == 11
    assert s.snap()[5] == 32768


@pytest.mark.parametrize("lane,cap", [(1, 5_000_000_000), (2, 10_000_000_000)])
def test_parent_checked_sum_and_cap(core, lane, cap):
    assert core.dll.ncc_parent_cpu(lane, cap - 1, 1, cap) == 0
    assert core.dll.ncc_parent_cpu(lane, cap, 1, cap + 1) == 9
    assert core.dll.ncc_parent_cpu(lane, 0, 1, 0) == 17
    assert core.dll.ncc_parent_cpu(lane, I64, 1, I64) == 13


@pytest.mark.parametrize("at", [70_000_000, 2_000_000_002])
def test_final_spacing_deadline_retains_failed_observation(core, at):
    s = core.session().running().drain()
    assert s.send(8, sample(at=50_000_001, active=(0, 1, 0), phase=3, index=1)) == 0
    assert s.send(8, sample(at=at, active=(0, 1, 0), phase=3, index=2)) == 5
    assert s.snap()[0] == 10 and s.snap()[5] == 2


def test_final_mismatch_rejected_atomically(core):
    s = core.session().running().drain()
    assert s.send(8, sample(at=50_000_001, active=(0, 1, 0), phase=3, index=1)) == 0
    assert s.send(8, sample(at=70_000_001, native=(1, 0, 0),
                            active=(0, 1, 0), phase=3, index=2)) == 3
    assert s.snap()[5:7] == (1, 1)


@pytest.mark.parametrize("kind,payload,direction", [
    (7, struct.pack("<Q", 0), 2),
    (2, b"", 1), (3, b"", 1), (4, bytes(32), 1),
    (5, bytes(32), 1), (6, struct.pack("<Q", 0), 1),
    (12, struct.pack("<Q", 0), 2),
])
def test_phase_and_direction_not_defaults(core, kind, payload, direction):
    s = core.session()
    assert s.send(kind, payload, direction=direction) != 0
    assert s.snap()[0] == 10


@pytest.mark.parametrize("platform", [1, 2])
def test_required_stop_cleanup_keeps_failed_verdict(core, platform):
    unit = 100 if platform == 1 else 1000
    native = (57_000_000_000 // unit, 0, 0)
    s = core.session(platform).running()
    assert s.send(8, sample(platform, native=native)) == 0
    assert s.send(2, direction=1) == 0  # heartbeat while STOP_REQUIRED
    assert s.send(9, struct.pack("<IIQ", 1, 0, 2)) == 0
    assert s.send(8, sample(platform, at=3, native=native, phase=2)) == 0
    s.drain(stopped=2, drained=4).final(native=native, start=50_000_004)
    token = bytes([8]) * 32
    assert s.send(5, token, direction=1) == 0
    assert s.send(4, token, direction=1) == 0
    assert s.send(12, struct.pack("<Q", 1)) == 0
    assert s.snap()[:5] == (9, 4, 1, 0, 0)


@pytest.mark.parametrize("drained,code", [(250_000_002, 0), (250_000_003, 7)])
def test_supplied_kill_interval_boundary(core, drained, code):
    s = core.session().running()
    assert s.send(9, struct.pack("<IIQ", 5, 0, 2)) == 0
    assert s.send(10, struct.pack("<IIQQ", 0, 0, 2, drained)) == code
    assert s.snap()[0] == (5 if code == 0 else 10)


def test_requested_stop_time_cannot_be_replaced(core):
    s = core.session().running()
    assert s.send(9, struct.pack("<IIQ", 5, 0, 2)) == 0
    assert s.send(10, struct.pack("<IIQQ", 0, 0, 3, 4)) == 3
    assert s.snap()[19:21] == (2, 0)


@pytest.mark.parametrize("platform,exit_raw", [(1, 2**32 - 1), (2, 2**32 - 9)])
def test_natural_nonzero_exit_never_success(core, platform, exit_raw):
    s = core.session(platform).running().drain(exit_raw=exit_raw).final()
    assert s.snap()[:5] == (6, 3, 1, 0, 0)
    assert s.snap()[21] == exit_raw


def test_unknown_queue_action_does_not_increment(core):
    s = core.session()
    assert core.dll.ncc_queue(s.state, 1024, 3) == 10
    assert s.snap()[11] == 0


def test_state_alignment_and_zero_initialization(core):
    raw = (C.c_uint64 * 129)()
    a, o = C.create_string_buffer(bytes(range(1, 17))), C.create_string_buffer(bytes(range(17, 33)))
    assert core.dll.ncc_state_init(C.byref(raw, 1), 1024, a, o) == 10
    raw[0] = 1
    assert core.dll.ncc_state_init(raw, 1024, a, o) == 16
    assert raw[0] == 1


@pytest.mark.parametrize("which", [0, 1])
def test_nonnil_bound_uuid_required(core, which):
    state = (C.c_uint64 * 128)()
    zero, nonzero = C.create_string_buffer(bytes(16)), C.create_string_buffer(bytes(range(1, 17)))
    a, o = (zero, nonzero) if which == 0 else (nonzero, zero)
    assert core.dll.ncc_state_init(state, 1024, a, o) == 15
    assert tuple(state) == (0,) * 128


def test_cancel_before_start_cannot_invent_started_final_sample(core):
    s = core.session()
    assert s.send(6, struct.pack("<Q", 0)) == 0
    assert s.send(3, direction=1) == 0
    assert s.send(9, struct.pack("<IIQ", 5, 0, 1)) == 0
    s.drain(stopped=1, drained=1)
    assert s.send(8, sample(at=50_000_001, active=(0, 1, 0), phase=3, index=1)) == 16
    assert s.snap()[5:7] == (0, 0)
