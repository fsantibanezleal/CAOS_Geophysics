"""I01 supplied-data tests. No compiler/probe/controller launch in this module.

DLL loading occurs ONLY in a requested fixture after MAIN source-read execution
authority. Missing explicit path/hash fails, never skips or builds a fallback.
"""
import ctypes as C
import hashlib
import importlib.util
import os
from pathlib import Path
import random
import re
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
I64, U64, U32 = 2**63 - 1, 2**64 - 1, 2**32 - 1
ATTEMPT, OBJECT = bytes(range(1, 17)), bytes(range(17, 33))
ERRORS = (
    "admission_closed", "launch_failed", "counter_invalid", "cpu_limit",
    "observation_gap", "containment_failed", "termination_uncertain",
    "receipt_unavailable", "parent_limit", "protocol_invalid",
    "bounds_exceeded", "integer_invalid", "counter_overflow",
    "counter_underflow", "identity_mismatch", "transition_invalid",
    "release_invalid",
)


def integer(value):
    if type(value) is not int or not 0 <= value <= U64:
        raise ValueError("Accounting integer type or range is invalid")
    return value


def frame(kind, payload=b"", *, sequence=1, attempt=ATTEMPT, obj=OBJECT,
          magic=b"NC01", version=1, declared=None, reserved=bytes(12)):
    assert type(payload) is bytes
    return struct.pack("<4sHHIQ16s16s12s", magic, version, kind,
                       len(payload) if declared is None else declared,
                       sequence, attempt, obj, reserved) + payload


def sample(platform=1, *, at=1, query=0, native=(0, 0, 0), active=None,
           cpu=None, phase=1, index=0, reserved=0):
    if active is None:
        active = (1, 1, 0) if platform == 1 else (1, 0, 0)
    if cpu is None:
        cpu = ((native[0] + native[1]) * 100 if platform == 1
               else max(native[0], native[1] + native[2]) * 1000)
    return struct.pack("<12Q", at, query, *native, *active,
                       cpu, phase, index, reserved)


class Core:
    """Test-only, strict scalar/path adapter; never a production bridge."""
    def __init__(self):
        raw, digest = os.environ.get("NCC_TEST_CORE_PATH"), os.environ.get("NCC_TEST_CORE_SHA256")
        assert raw and digest, "Explicit reviewed core path and hash required"
        assert len(raw) <= 1024 and re.fullmatch("[0-9a-f]{64}", digest)
        path = Path(raw)
        assert path.is_absolute() and path.name == "core.dll"
        for part in (path, *path.parents):
            info = part.lstat()
            assert not part.is_symlink()
            assert not getattr(info, "st_file_attributes", 0) & 0x400
        assert path.is_file() and path.stat().st_size <= 64 * 1024 * 1024
        h = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(65536):
                h.update(chunk)
        assert h.hexdigest() == digest, "Core binary hash mismatch"
        # Exact file, restricted directory/System32 search; no discovery/build.
        self.dll = C.CDLL(str(path), winmode=0x900)
        u, p, i = C.c_uint64, C.c_void_p, C.c_uint32
        signatures = {
            "windows_cpu": [u, u, p], "linux_cpu": [u, u, u, p],
            "delta": [u, u, p], "qpc_ns": [u, u, u, p],
            "time_ns": [u, u, u, p], "next_sequence": [u, u],
            "parent_cpu": [i, u, u, u], "limits": [i, p, u],
            "frame_preflight": [p, u, p], "state_init": [p, u, p, p],
            "apply": [p, u, i, p, u], "account_bytes": [p, u, i, u],
            "queue": [p, u, i], "snapshot": [p, u, p, u],
        }
        for name, args in signatures.items():
            fn = getattr(self.dll, "ncc_" + name)
            fn.argtypes, fn.restype = args, i
        self.dll.ncc_error_text.argtypes = [i, i]
        self.dll.ncc_error_text.restype = C.c_char_p

    def math(self, name, *values):
        values = tuple(integer(v) for v in values)
        out = C.c_uint64(0xABCDEF)
        code = getattr(self.dll, "ncc_" + name)(*values, C.byref(out))
        return code, out.value

    def preflight(self, data):
        assert type(data) is bytes
        out = C.c_uint32(999)
        buf = C.create_string_buffer(data)
        code = self.dll.ncc_frame_preflight(buf, len(data), C.byref(out))
        return code, out.value

    def limits(self, lane):
        lane = integer(lane)
        assert lane <= U32
        out = (C.c_uint64 * 8)(*[999] * 8)
        code = self.dll.ncc_limits(lane, out, 8)
        return code, tuple(out)

    def session(self, platform=1, lane=1):
        return Session(self, platform, lane)


class Session:
    def __init__(self, core, platform=1, lane=1):
        self.core, self.platform = core, platform
        self.state = (C.c_uint64 * 128)()
        a, o = C.create_string_buffer(ATTEMPT), C.create_string_buffer(OBJECT)
        assert core.dll.ncc_state_init(self.state, 1024, a, o) == 0
        self.sequence = {1: 0, 2: 0}
        assert self.send(1, struct.pack("<II", platform, lane), direction=1) == 0

    def send(self, kind, payload=b"", *, direction=2, sequence=None, **headers):
        direction = integer(direction)
        assert direction <= U32
        if sequence is None:
            self.sequence[direction] += 1
            sequence = self.sequence[direction]
        return self.apply(frame(kind, payload, sequence=sequence, **headers), direction)

    def apply(self, data, direction=2):
        assert type(data) is bytes
        buf = C.create_string_buffer(data)
        return self.core.dll.ncc_apply(self.state, 1024, direction, buf, len(data))

    def snap(self):
        out = (C.c_uint64 * 22)()
        assert self.core.dll.ncc_snapshot(self.state, 1024, out, 22) == 0
        return tuple(out)

    def running(self, start=0):
        assert self.send(6, struct.pack("<Q", 0)) == 0
        assert self.send(7, struct.pack("<Q", start)) == 0
        return self

    def drain(self, *, stopped=1, drained=1, exit_raw=0):
        assert self.send(10, struct.pack("<IIQQ", exit_raw, 0, stopped, drained)) == 0
        return self

    def final(self, *, native=(0, 0, 0), start=50_000_001):
        active = (0, 1, 0) if self.platform == 1 else (0, 1, 1)
        for index in (1, 2, 3):
            assert self.send(8, sample(self.platform, at=start + (index - 1) * 20_000_000,
                                      native=native, active=active, phase=3, index=index)) == 0
        return self


@pytest.fixture
def core():
    return Core()


@pytest.fixture
def pure():
    name = "_ncc_unchanged_pure_reference"
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/physical_accounting_protocol.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("values,expected", [
    ((0, 0), 0), ((1, 2), 300),
    ((I64 // 100, 0), (I64 // 100) * 100),
])
def test_windows_golden(core, pure, values, expected):
    assert core.math("windows_cpu", *values) == (0, expected)
    assert pure.windows_cpu_ns(*values) == expected


@pytest.mark.parametrize("values,expected", [
    ((0, 0, 0), 0), ((1, 2, 3), 5000), ((8, 2, 3), 8000),
    ((I64 // 1000, 0, 0), (I64 // 1000) * 1000),
])
def test_linux_golden(core, pure, values, expected):
    assert core.math("linux_cpu", *values) == (0, expected)
    assert pure.linux_cpu_ns(*values) == expected


@pytest.mark.parametrize("name,values,code", [
    ("windows_cpu", (I64 + 1, 0), 12),
    ("windows_cpu", (I64, 1), 13),
    ("windows_cpu", (I64 // 100 + 1, 0), 13),
    ("linux_cpu", (0, U64, 1), 13),
    ("linux_cpu", (I64 // 1000 + 1, 0, 0), 13),
    ("delta", (0, 1), 14), ("delta", (I64 + 1, 0), 12),
    ("qpc_ns", (1, 0, 0), 12), ("qpc_ns", (0, 1, 1), 14),
    ("qpc_ns", (I64, 0, 1), 13),
    ("time_ns", (0, 1_000_000_000, 1), 12),
    ("time_ns", (0, 1_000_000, 1000), 12),
    ("time_ns", (I64 // 1_000_000_000 + 1, 0, 1), 13),
    ("time_ns", (0, 0, 2), 12),
])
def test_checked_errors_preserve_out(core, name, values, code):
    assert core.math(name, *values) == (code, 0xABCDEF)


@pytest.mark.parametrize("current,previous,frequency", [
    (0, 0, 1), (1, 0, 3), (I64, I64 - 1, I64),
    (I64, 0, I64), (10_000_000_001, 0, 1_000_000_000),
])
def test_qpc_integer_ceil(core, current, previous, frequency):
    delta = current - previous
    expected = (delta * 1_000_000_000 + frequency - 1) // frequency
    assert core.math("qpc_ns", current, previous, frequency) == (0, expected)


def test_qpc_near_width_independent_bigint_oracle(core):
    rng = random.Random(20261003)
    for _ in range(2000):
        current = rng.randrange(I64 + 1)
        previous = rng.randrange(current + 1)
        frequency = rng.randrange(1, I64 + 1)
        expected = ((current - previous) * 1_000_000_000 + frequency - 1) // frequency
        assert core.math("qpc_ns", current, previous, frequency) == (
            (13, 0xABCDEF) if expected > I64 else (0, expected))


@pytest.mark.parametrize("seconds,fraction,quantum", [
    (0, 0, 1), (1, 999_999_999, 1), (1, 999_999, 1000),
    (I64 // 1_000_000_000, I64 % 1_000_000_000, 1),
])
def test_timeval_timespec_units(core, seconds, fraction, quantum):
    assert core.math("time_ns", seconds, fraction, quantum) == (
        0, seconds * 1_000_000_000 + fraction * quantum)


@pytest.mark.parametrize("value", [True, False, -1, 1.0, "1", None, U64 + 1])
def test_adapter_denies_coercion_before_ctypes(value):
    with pytest.raises(ValueError, match="^Accounting integer type or range is invalid$"):
        integer(value)


@pytest.mark.parametrize("previous,supplied,code", [
    (0, 1, 0), (0, 0, 16), (1, 1, 16), (1, 3, 16),
    (U64 - 1, U64, 0), (U64, 0, 16),
])
def test_sequence_exhaustion(core, previous, supplied, code):
    assert core.dll.ncc_next_sequence(previous, supplied) == code


@pytest.mark.parametrize("lane,method", [
    (1, "gravity.station-corrections/v1"),
    (2, "gravity.equivalent-source-transform/v1"),
])
def test_frozen_limits_cross_pure(core, pure, lane, method):
    limits = pure.limits_for(method)
    expected = tuple(getattr(limits, key) for key in (
        "cpu_ceiling_ns", "cpu_stop_ns", "cpu_margin_ns", "wall_ns",
        "rss_bytes", "scratch_bytes", "result_bytes", "parent_cpu_ceiling_ns"))
    assert core.limits(lane) == (0, expected)


@pytest.mark.parametrize("lane", [0, 3, U32])
def test_unknown_lane_never_defaults(core, lane):
    assert core.limits(lane) == (1, (999,) * 8)


@pytest.mark.parametrize("kind,length", [(1, 8), (2, 0), (3, 0), (4, 32), (5, 32),
                                        (6, 8), (7, 8), (8, 96), (9, 16),
                                        (10, 24), (11, 16), (12, 8)])
def test_fixed_wire_lengths(core, kind, length):
    assert core.preflight(frame(kind, bytes(length))) == (0, kind)


@pytest.mark.parametrize("data,code", [
    (b"", 10), (bytes(63), 10), (bytes(4161), 11),
    (frame(0), 10), (frame(13), 10),
    (frame(1, bytes(8), magic=b"BAD!"), 10),
    (frame(1, bytes(8), version=2), 10),
    (frame(1, bytes(8), reserved=b"x" + bytes(11)), 10),
    (frame(1, bytes(8), declared=4097), 11),
    (frame(10, bytes(16)), 10),
    (frame(1, bytes(9)), 10),
    (frame(1, bytes(8)) + b"x", 10),
    (frame(1, bytes(8), sequence=0), 16),
])
def test_wire_abi_units_errors(core, data, code):
    assert core.preflight(data) == (code, 999)


@pytest.mark.parametrize("platform,lane", [(1, 1), (1, 2), (2, 1), (2, 2)])
def test_clean_wire_lifecycle_never_authorizes(core, platform, lane):
    s = core.session(platform, lane).running().drain().final()
    assert s.snap()[:7] == (6, 0, 0, 0, 0, 3, 3)
    digest = bytes([0xA5]) * 32
    assert s.send(5, digest, direction=1) == 0
    assert s.send(4, digest, direction=1) == 0
    assert s.send(12, struct.pack("<Q", 0)) == 0
    assert s.snap()[:5] == (9, 0, 0, 0, 0)


@pytest.mark.parametrize("headers,code", [
    ({"attempt": bytes(16)}, 15), ({"obj": bytes(16)}, 15),
    ({"sequence": 2}, 16), ({"version": 2}, 10),
])
def test_atomic_held_identity_sequence(core, headers, code):
    s = core.session().running()
    before = s.snap()
    assert s.send(8, sample(), **headers) == code
    after = s.snap()
    assert after[:5] == (10, code, 1, 1, 0)
    assert after[5:11] == before[5:11]
    assert s.send(11, struct.pack("<4I", 1, 1, U32, 0)) == code
    assert s.snap() == after


@pytest.mark.parametrize("platform", [1, 2])
def test_available_zero_not_unavailable(core, platform):
    s = core.session(platform).running()
    assert s.send(8, sample(platform)) == 0
    assert s.snap()[5:9] == (1, 0, 0, 1)
    assert s.send(11, struct.pack("<4I", 5, 8, U32, 0)) == 8
    assert s.snap()[:7] == (10, 8, 1, 1, 0, 1, 0)


@pytest.mark.parametrize("platform", [1, 2])
def test_component_regression_even_rising_total(core, platform):
    s = core.session(platform).running()
    a = (2, 2, 0) if platform == 1 else (2, 2, 2)
    b = (1, 4, 0) if platform == 1 else (1, 4, 2)
    assert s.send(8, sample(platform, native=a)) == 0
    assert s.send(8, sample(platform, at=2, native=b)) == 3
    assert s.snap()[5] == 1


@pytest.mark.parametrize("platform", [1, 2])
@pytest.mark.parametrize("lane,stop", [(1, 57_000_000_000), (2, 237_000_000_000)])
def test_exact_stop_retained_not_repaired(core, platform, lane, stop):
    unit = 100 if platform == 1 else 1000
    s = core.session(platform, lane).running()
    assert s.send(8, sample(platform, native=(stop // unit, 0, 0))) == 0
    assert s.snap()[:6] == (3, 4, 1, 1, 0, 1)
    assert s.send(9, struct.pack("<IIQ", 16, 0, 1)) == 16
    assert s.snap()[2] == 1


@pytest.mark.parametrize("platform", [1, 2])
@pytest.mark.parametrize("lane,ceiling", [(1, 60_000_000_000), (2, 240_000_000_000)])
def test_final_ceiling_next_native_quantum_always_failed(core, platform, lane, ceiling):
    unit = 100 if platform == 1 else 1000
    s = core.session(platform, lane).running().drain()
    s.final(native=(ceiling // unit + 1, 0, 0))
    assert s.snap()[:7] == (6, 4, 1, 0, 0, 3, 3)


@pytest.mark.parametrize("offset", [49_999_999, 50_000_000])
def test_premature_final_visibility_wait_fails(core, offset):
    s = core.session().running().drain()
    assert s.send(8, sample(at=offset, active=(0, 1, 0), phase=3, index=1)) == 5
    assert s.snap()[0] == 10


@pytest.mark.parametrize("query,at", [(20_000_001, 1), (0, 20_000_001)])
def test_well_formed_bad_running_timing_retained(core, query, at):
    s = core.session().running()
    assert s.send(8, sample(at=at, query=query)) == 0
    assert s.snap()[:6] == (3, 5, 1, 1, 0, 1)


def test_wrong_receipt_ack_stays_held(core):
    s = core.session().running().drain().final()
    assert s.send(5, bytes(32), direction=1) == 0
    assert s.send(4, bytes([1]) * 32, direction=1) == 17
    assert s.send(12, struct.pack("<Q", 0)) == 17
    assert s.snap()[4] == 0


def test_reinit_cannot_clear_failure(core):
    s = core.session().running()
    assert s.apply(b"bad") == 10
    a, o = C.create_string_buffer(ATTEMPT), C.create_string_buffer(OBJECT)
    assert core.dll.ncc_state_init(s.state, 1024, a, o) == 10
    assert s.snap()[:5] == (10, 10, 1, 1, 0)


@pytest.mark.parametrize("code", range(1, 18))
def test_fixed_safe_errors_cross_pure(core, pure, code):
    expected = pure.safe_error("accounting_" + ERRORS[code - 1])
    assert core.dll.ncc_error_text(code, 0).decode("ascii") == expected.code
    assert core.dll.ncc_error_text(code, 1).decode("ascii") == expected.message
    assert len(expected.code) <= 48 and len(expected.message) <= 96


@pytest.mark.parametrize("code", [0, 18, U32])
def test_unknown_error_never_echoes(core, code):
    assert core.dll.ncc_error_text(code, 0) == b"accounting_protocol_invalid"
