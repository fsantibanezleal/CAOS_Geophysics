"""Fixed M08 Windows observer/controller. Local evidence is not runtime authority.

Imports define layouts only. Native bindings are constructed after admission,
never during import. No assignment-after-execution or in-process science fallback.
"""

import ctypes as C
from contextlib import ExitStack
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from waveform_input import WaveformInputError
from waveform_m08_files import validate_path, external_work_path, open_input
import waveform_m08_files as files

B = 60000000000
S = 57000000000
POLL = 50000000
GAP = 100000000
MEMORY = 1073741824
SCRATCH = 52690944
UINT64 = 2**64 - 1
REASONS = frozenset(
    (
        "native_contract",
        "abi_unmeasured",
        "closure_mismatch",
        "platform_unavailable",
        "native_unavailable",
        "membership",
        "sample_gap",
        "counter_invalid",
        "resource_stop",
        "resource_exceeded",
        "drain_invalid",
        "timeout",
        "cancelled",
        "child_failed",
        "export_invalid",
        "wire_invalid",
        "log_limit",
        "termination_unresolved",
        "parent_mismatch",
        "scientific_rejected",
        "scientific_engine",
        "science_failed",
    )
)


class ControlError(Exception):
    def __init__(self, reason):
        self.reason = reason if type(reason) is str and reason in REASONS else "native_contract"
        super().__init__(self.reason)


def require(condition, reason="native_contract"):
    if not condition:
        raise ControlError(reason)


def integer(value, maximum=UINT64):
    require(type(value) is int and 0 <= value <= maximum, "counter_invalid")
    return value


def cpu_ns(user, kernel):
    user, kernel = integer(user, 2**63 - 1), integer(kernel, 2**63 - 1)
    # Match the approved pure protocol's signed64 nanosecond ceiling.
    # A uint64 wire field does not widen the CPU arithmetic domain.
    require(user <= (2**63 - 1) - kernel and user + kernel <= (2**63 - 1) // 100, "counter_invalid")
    return (user + kernel) * 100


class Lifetime:
    """Measured-clock stream checker. A failure cannot be cleared by later rows."""

    def __init__(self):
        self.last = None
        self.started = None
        self.drain = None
        self.stable = None
        self.max_gap_ns = 0
        self.final_ready = False
        self.final_cpu_ns = None
        self.failure = None
        self.samples = 0

    def drained(self, stamp):
        integer(stamp)
        require(
            self.drain is None and self.started is not None and self.started <= stamp <= self.last[0] + GAP,
            "drain_invalid",
        )
        self.drain = stamp

    def sample(self, stamp, user, kernel, active, total, peak):
        try:
            row = tuple(integer(x) for x in (stamp, user, kernel, active, total, peak))
            cpu = cpu_ns(user, kernel)
            require(active <= 2 and active <= total <= 2 and peak <= MEMORY, "resource_exceeded")
            if self.last is not None:
                require(stamp >= self.last[0], "counter_invalid")
                gap = stamp - self.last[0]
                self.max_gap_ns = max(gap, self.max_gap_ns)
                require(gap <= GAP, "sample_gap")
                require(
                    user >= self.last[1] and kernel >= self.last[2] and total >= self.last[4] and peak >= self.last[5],
                    "counter_invalid",
                )
                if self.stable is not None:
                    require(row[1:] == self.stable[1:], "drain_invalid")
            require(cpu <= B, "resource_exceeded")
            require(cpu < S, "resource_stop")
            if self.started is None:
                self.started = stamp
            if self.drain is not None and stamp >= self.drain + POLL and active == 0:
                if self.stable is None:
                    self.stable = row
                elif stamp >= self.stable[0] + POLL and self.failure is None:
                    self.final_ready, self.final_cpu_ns = True, cpu
            self.last = row
            self.samples += 1
        except ControlError as error:
            # Final >B remains visible even when S already caused termination.
            if self.failure is None or error.reason == "resource_exceeded":
                self.failure = error.reason
            self.final_ready = False


D = C.c_uint32
H = C.c_void_p
Q = C.c_uint64
I64 = C.c_int64
BOOL = C.c_int32


class FILETIME(C.Structure):
    _fields_ = [("low", D), ("high", D)]


class SECURITY(C.Structure):
    _fields_ = [("length", D), ("descriptor", H), ("inherit", BOOL)]


class MEMORY_STATUS(C.Structure):
    _fields_ = [
        ("length", D),
        ("load", D),
        ("total_physical", Q),
        ("available_physical", Q),
        ("total_commit", Q),
        ("available_commit", Q),
        ("total_virtual", Q),
        ("available_virtual", Q),
        ("reserved", Q),
    ]


class BASIC_LIMIT(C.Structure):
    _fields_ = [
        ("process_user", I64),
        ("job_user", I64),
        ("flags", D),
        ("min_ws", Q),
        ("max_ws", Q),
        ("active", D),
        ("affinity", Q),
        ("priority", D),
        ("scheduling", D),
    ]


class ACCOUNT(C.Structure):
    _fields_ = [
        ("user", I64),
        ("kernel", I64),
        ("period_user", I64),
        ("period_kernel", I64),
        ("faults", D),
        ("total", D),
        ("active", D),
        ("terminated", D),
    ]


class IO_COUNTERS(C.Structure):
    _fields_ = [
        (name, Q) for name in ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")
    ]


class EXTENDED(C.Structure):
    _fields_ = [
        ("basic", BASIC_LIMIT),
        ("io", IO_COUNTERS),
        ("process_memory", Q),
        ("job_memory", Q),
        ("peak_process", Q),
        ("peak_job", Q),
    ]


class STARTUP(C.Structure):
    _fields_ = [
        ("cb", D),
        ("reserved", H),
        ("desktop", H),
        ("title", H),
        ("x", D),
        ("y", D),
        ("x_size", D),
        ("y_size", D),
        ("x_chars", D),
        ("y_chars", D),
        ("fill", D),
        ("flags", D),
        ("show", C.c_uint16),
        ("reserved_bytes", C.c_uint16),
        ("reserved_ptr", H),
        ("stdin", H),
        ("stdout", H),
        ("stderr", H),
    ]


class STARTUP_EX(C.Structure):
    _fields_ = [("startup", STARTUP), ("attributes", H)]


class PROCESS(C.Structure):
    _fields_ = [("process", H), ("thread", H), ("pid", D), ("tid", D)]


class PID_LIST(C.Structure):
    _fields_ = [("assigned", D), ("count", D), ("ids", Q * 2)]


RECORDS = {
    "MEMORY_STATUS": MEMORY_STATUS,
    "FILETIME": FILETIME,
    "SECURITY": SECURITY,
    "BASIC_LIMIT": BASIC_LIMIT,
    "ACCOUNT": ACCOUNT,
    "IO_COUNTERS": IO_COUNTERS,
    "EXTENDED": EXTENDED,
    "STARTUP": STARTUP,
    "STARTUP_EX": STARTUP_EX,
    "PROCESS": PROCESS,
    "PID_LIST": PID_LIST,
}


def layout_values():
    result = {
        "HANDLE.size": C.sizeof(H),
        "SIZE_T.size": C.sizeof(Q),
        "BOOL.size": C.sizeof(BOOL),
        "DWORD.size": C.sizeof(D),
    }
    for name, record in RECORDS.items():
        result[name + ".size"] = C.sizeof(record)
        result[name + ".align"] = C.alignment(record)
        for field, _ in record._fields_:
            result[name + "." + field] = getattr(record, field).offset
    return result


def parse_abi(raw):
    require(type(raw) is bytes and 0 < len(raw) <= 4096 and raw.endswith(b"\n"), "abi_unmeasured")
    result = {}
    for line in raw.splitlines():
        require(re.fullmatch(rb"[A-Z_a-z0-9.]+=[0-9]{1,4}", line) is not None, "abi_unmeasured")
        key, value = line.split(b"=")
        key = key.decode("ascii")
        require(key not in result, "abi_unmeasured")
        result[key] = int(value)
    require(result == layout_values(), "abi_unmeasured")
    return result


PHASES = {"hello": (1, 8), "child": (2, 8), "drained": (3, 24), "export": (4, None), "error": (5, None), "ack": (6, 0)}
HEADER = struct.Struct("<4sBBH16sII")


def _phase(phase, length):
    require(type(phase) is str and phase in PHASES and type(length) is int and 0 <= length <= 65536, "wire_invalid")
    expected = PHASES[phase][1]
    require(length == expected if expected is not None else 0 < length <= 65536, "wire_invalid")


def frame(run, sequence, phase, payload):
    require(type(run) is str and re.fullmatch("[a-f0-9]{32}", run) is not None, "wire_invalid")
    require(type(sequence) is int and 1 <= sequence <= 2**32 - 1 and type(payload) is bytes, "wire_invalid")
    _phase(phase, len(payload))
    return HEADER.pack(b"M08W", 1, PHASES[phase][0], 0, bytes.fromhex(run), sequence, len(payload)) + payload


def header(raw, run, sequence):
    require(
        type(raw) is bytes and len(raw) == 32 and type(sequence) is int and 1 <= sequence <= 2**32 - 1, "wire_invalid"
    )
    require(type(run) is str and re.fullmatch("[a-f0-9]{32}", run) is not None, "wire_invalid")
    magic, version, code, reserved, identity, seq, size = HEADER.unpack(raw)
    require((magic, version, reserved, identity, seq) == (b"M08W", 1, 0, bytes.fromhex(run), sequence), "wire_invalid")
    phase = next((name for name, value in PHASES.items() if value[0] == code), None)
    _phase(phase, size)
    return phase, size


def canonical(value, cap=65536):
    precount(value, cap, max_nodes=4096 if cap <= 65536 else 2097152, max_depth=8 if cap <= 65536 else 16)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    require(len(raw) <= cap)
    return raw


def precount(value, cap=65536, *, max_nodes=4096, max_depth=8):
    """Exact native graph bounds before encoder/copy; uint64 protocol, no bool counters."""
    active, nodes = set(), 0

    def visit(item, depth, key=False):
        nonlocal nodes
        nodes += 1
        require(nodes <= max_nodes)
        kind = type(item)
        if kind is str:
            require(len(item) <= (64 if key else 4096))
            count = 2
            for char in item:
                point = ord(char)
                require(not 0xD800 <= point <= 0xDFFF)
                count += (
                    2
                    if char in '"\\\b\f\n\r\t'
                    else 6
                    if point < 32 or 127 <= point <= 65535
                    else 12
                    if point > 65535
                    else 1
                )
        elif kind in (dict, list):
            require(depth < max_depth and id(item) not in active)
            active.add(id(item))
            count = 2
            for index, entry in enumerate(item.items() if kind is dict else item):
                count += int(index > 0)
                if kind is dict:
                    name, val = entry
                    require(type(name) is str)
                    count += visit(name, depth + 1, True) + 1 + visit(val, depth + 1)
                else:
                    count += visit(entry, depth + 1)
                require(count <= cap)
            active.remove(id(item))
        elif kind is int:
            require(0 <= item <= UINT64)
            count = len(str(item))
        elif kind is float:
            require(math.isfinite(item))
            count = len(repr(item))
        elif item is None:
            count = 4
        elif kind is bool:
            count = 4 if item else 5
        else:
            raise ControlError("native_contract")
        require(count <= cap)
        return count

    return visit(value, 0)


def decode_control(raw, cap=65536):
    """Bounded protocol grammar pass BEFORE full tree or integer conversion.

    Control JSON has unsigned decimal uint64 only: no float/exponent/negative
    counter or duplicate key. Scientific request/reference JSON stays separate.
    """
    require(type(cap) is int and 0 < cap <= 65536)
    require(type(raw) is bytes and 0 < len(raw) <= cap and not raw.startswith(b"\xef\xbb\xbf"))
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        raise ControlError("native_contract") from None
    position, nodes = 0, 0

    def whitespace():
        nonlocal position
        while position < len(text) and text[position] in " \t\r\n":
            position += 1

    def string(key=False):
        nonlocal position
        require(position < len(text) and text[position] == '"')
        start, escaped = position, False
        position += 1
        bound = 64 if key else 4096
        while position < len(text):
            char = text[position]
            position += 1
            require(position - start <= bound * 12 + 2)
            if not escaped and char == '"':
                try:
                    result = json.loads(text[start:position])
                except (ValueError, UnicodeError):
                    raise ControlError("native_contract") from None
                require(type(result) is str and len(result) <= bound)
                precount(result)
                return result
            require(escaped or ord(char) >= 32)
            escaped = not escaped if char == "\\" else False
        raise ControlError("native_contract")

    def value(depth=0):
        nonlocal position, nodes
        nodes += 1
        require(nodes <= 4096 and depth <= 8)
        whitespace()
        require(position < len(text))
        char = text[position]
        if char == '"':
            string()
            return
        if char in "[{":
            require(depth < 8)
            position += 1
            end, seen = ("]" if char == "[" else "}"), set()
            whitespace()
            if position < len(text) and text[position] == end:
                position += 1
                return
            while True:
                whitespace()
                if char == "{":
                    nodes += 1
                    require(nodes <= 4096)
                    name = string(True)
                    require(name not in seen)
                    seen.add(name)
                    whitespace()
                    require(position < len(text) and text[position] == ":")
                    position += 1
                value(depth + 1)
                whitespace()
                require(position < len(text))
                separator = text[position]
                position += 1
                if separator == end:
                    return
                require(separator == ",")
        start = position
        while position < len(text) and text[position] not in " \t\r\n,]}:":
            position += 1
            require(position - start <= 20)
        token = text[start:position]
        if token in ("true", "false", "null"):
            return
        require(re.fullmatch(r"(?:0|[1-9][0-9]{0,19})", token) is not None)
        require(len(token) < 20 or token <= "18446744073709551615")

    value()
    whitespace()
    require(position == len(text))
    return json.loads(text)


def validate_spec(spec):
    try:
        precount(spec, 65536, max_nodes=4096, max_depth=8)
        require(
            type(spec) is dict
            and set(spec)
            == set(
                "schema run_id source_revision closure_manifest_sha256 mseed "
                "stationxml request out python evaluate_with private_parent_receipt".split()
            )
        )
        require(spec["schema"] == "caos.m08-windows-transaction.v1")
        for key, length in (("run_id", 32), ("source_revision", 40), ("closure_manifest_sha256", 64)):
            require(type(spec[key]) is str and re.fullmatch("[a-f0-9]{" + str(length) + "}", spec[key]) is not None)
        paths = [(validate_path if key == "python" else external_work_path)(spec[key])
                 for key in ("mseed", "stationxml", "request", "out", "python")]
        if spec["evaluate_with"] is not None:
            paths.append(external_work_path(spec["evaluate_with"]))
        receipt = spec["private_parent_receipt"]
        require(type(receipt) is dict and set(receipt) == {"path", "sha256"})
        paths.append(external_work_path(receipt["path"]))
        require(type(receipt["sha256"]) is str and re.fullmatch("[a-f0-9]{64}", receipt["sha256"]) is not None)
        require(len(set(paths)) == len(paths))
        return spec
    except (WaveformInputError, ValueError, TypeError):
        raise ControlError("native_contract") from None


def command_line(argv):
    require(type(argv) in (tuple, list) and 0 < len(argv) <= 24)
    require(all(type(s) is str and 0 < len(s) <= 4096 and "\0" not in s for s in argv))
    result = subprocess.list2cmdline(argv)
    require(len(result.encode("utf-16-le")) // 2 <= 16384)
    return result


def environment(private_root):
    root = str(validate_path(private_root) / "environment")
    values = {
        "SystemRoot": os.environ.get("SystemRoot", "C:\\Windows"),
        "SystemDrive": Path(os.environ.get("SystemRoot", "C:\\Windows")).drive,
        "PROGRAMDATA": root + "\\system-profile",
        "ALLUSERSPROFILE": root + "\\system-profile",
        "TEMP": root,
        "TMP": root,
        "USERPROFILE": root,
        "LOCALAPPDATA": root,
        "APPDATA": root,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    }
    require(all(type(v) is str and "\0" not in v and len(v) <= 4096 for v in values.values()))
    block = "\0".join(k + "=" + v for k, v in sorted(values.items(), key=lambda item: item[0].upper())) + "\0\0"
    require(len(block.encode("utf-16-le")) // 2 <= 32768)
    return block


class Native:
    """Exact kernel32 inventory; construction is gated, all handles are owned."""

    def __init__(self):
        require(os.name == "nt" and C.sizeof(H) == 8, "platform_unavailable")
        self.api = C.WinDLL("kernel32", use_last_error=True)
        p = C.POINTER
        signatures = {
            "CreateJobObjectW": ([H, C.c_wchar_p], H),
            "SetInformationJobObject": ([H, BOOL, H, D], BOOL),
            "QueryInformationJobObject": ([H, BOOL, H, D, p(D)], BOOL),
            "InitializeProcThreadAttributeList": ([H, D, D, p(Q)], BOOL),
            "UpdateProcThreadAttribute": ([H, D, Q, H, Q, H, p(Q)], BOOL),
            "DeleteProcThreadAttributeList": ([H], None),
            "CreateProcessW": ([C.c_wchar_p, H, H, H, BOOL, D, H, C.c_wchar_p, p(STARTUP_EX), p(PROCESS)], BOOL),
            "IsProcessInJob": ([H, H, p(BOOL)], BOOL),
            "ResumeThread": ([H], D),
            "TerminateJobObject": ([H, D], BOOL),
            "GetProcessTimes": ([H, p(FILETIME), p(FILETIME), p(FILETIME), p(FILETIME)], BOOL),
            "WaitForSingleObject": ([H, D], D),
            "GetExitCodeProcess": ([H, p(D)], BOOL),
            "GetCurrentProcess": ([], H),
            "CloseHandle": ([H], BOOL),
            "CreatePipe": ([p(H), p(H), p(SECURITY), D], BOOL),
            "SetHandleInformation": ([H, D, D], BOOL),
            "ReadFile": ([H, H, D, p(D), H], BOOL),
            "WriteFile": ([H, H, D, p(D), H], BOOL),
            "PeekNamedPipe": ([H, H, D, p(D), p(D), p(D)], BOOL),
            # Read-only loaded-module closure; not RSS or process polling CPU.
            "K32EnumProcessModules": ([H, p(H), D, p(D)], BOOL),
            "K32GetModuleFileNameExW": ([H, H, H, D], D),
            "GlobalMemoryStatusEx": ([p(MEMORY_STATUS)], BOOL),
        }
        try:
            for name, (args, result) in signatures.items():
                function = getattr(self.api, name)
                function.argtypes, function.restype = args, result
        except AttributeError:
            raise ControlError("native_unavailable") from None
        self.handles = set()

    def owned(self, handle):
        require(type(handle) is int and handle not in (0, UINT64) and handle not in self.handles, "native_unavailable")
        self.handles.add(handle)
        return handle

    def close(self, handle):
        require(handle in self.handles, "native_contract")
        require(self.api.CloseHandle(handle) != 0, "native_unavailable")
        self.handles.remove(handle)

    def cleanup(self):
        failed = False
        for handle in list(self.handles):
            try:
                self.close(handle)
            except ControlError:
                failed = True
        require(not failed, "termination_unresolved")

    def query(self, job, kind, record):
        value, length = record(), D()
        require(
            self.api.QueryInformationJobObject(job, kind, C.byref(value), C.sizeof(value), C.byref(length)) != 0,
            "native_unavailable",
        )
        require(length.value == C.sizeof(value), "native_unavailable")
        return value

    def limits(self, job):
        value = EXTENDED()
        value.basic.flags = 0x4 | 0x8 | 0x200 | 0x2000
        value.basic.job_user, value.basic.active, value.job_memory = 600000000, 2, MEMORY
        require(self.api.SetInformationJobObject(job, 9, C.byref(value), C.sizeof(value)) != 0, "native_unavailable")
        actual = self.query(job, 9, EXTENDED)
        require(
            # Priority/scheduling classes are reported as Windows defaults even
            # when their flags are absent. They are not configured limits. Read
            # back every selected limit and every field that could enable one;
            # never mistake default NORMAL_PRIORITY_CLASS/5 for a failed ceiling.
            all(getattr(actual.basic, name) == getattr(value.basic, name)
                for name in ("process_user", "job_user", "flags", "min_ws", "max_ws", "active", "affinity"))
            and actual.job_memory == MEMORY
            and actual.process_memory == 0,
            "native_unavailable",
        )

    def capacity(self, disk_free):
        integer(disk_free)
        value = MEMORY_STATUS()
        value.length = C.sizeof(value)
        require(
            self.api.GlobalMemoryStatusEx(C.byref(value)) != 0
            and value.length == C.sizeof(value)
            and value.load <= 100,
            "native_unavailable",
        )
        require(
            value.available_physical <= value.total_physical and value.available_commit <= value.total_commit,
            "counter_invalid",
        )
        require(
            value.available_physical >= MEMORY + 67108864
            and value.available_commit >= MEMORY + 67108864
            and disk_free >= SCRATCH + 67108864,
            "resource_exceeded",
        )
        return {
            "available_physical_bytes": value.available_physical,
            "available_process_commit_bytes": value.available_commit,
            "disk_free_bytes": disk_free,
            "observer_margin_bytes": 67108864,
            "snapshot_not_reservation": True,
            "production_floor": None,
        }

    def current_limits(self):
        value = self.query(None, 9, EXTENDED)
        require(
            value.basic.flags == 0x220C
            and value.basic.job_user == 600000000
            and value.basic.active == 2
            and value.job_memory == MEMORY
            and value.process_memory == 0,
            "membership",
        )

    def sample(self, job):
        account, limit = self.query(job, 1, ACCOUNT), self.query(job, 9, EXTENDED)
        cpu_ns(account.user, account.kernel)
        require(account.active <= account.total <= 2 and account.terminated <= account.total, "membership")
        return (time.monotonic_ns(), account.user, account.kernel, account.active, account.total, limit.peak_job)

    def members(self, job):
        value, length = PID_LIST(), D()
        require(
            self.api.QueryInformationJobObject(job, 3, C.byref(value), C.sizeof(value), C.byref(length)) != 0,
            "membership",
        )
        require(value.assigned == value.count and value.count <= 2, "membership")
        require(length.value == 8 + value.count * 8, "membership")
        values = tuple(value.ids[: value.count])
        require(all(0 < pid <= 2**32 - 1 for pid in values) and len(set(values)) == len(values), "membership")
        return values

    def membership(self, process, job):
        answer = BOOL()
        require(self.api.IsProcessInJob(process, job, C.byref(answer)) != 0 and answer.value == 1, "membership")

    def resume(self, process):
        require(self.api.ResumeThread(process.thread) == 1, "native_unavailable")
        self.close(process.thread)

    def signalled(self, process):
        result = self.api.WaitForSingleObject(process, 0)
        require(result in (0, 258), "native_unavailable")
        return result == 0

    def exit_code(self, process):
        value = D()
        require(
            self.signalled(process)
            and self.api.GetExitCodeProcess(process, C.byref(value)) != 0
            and value.value != 259,
            "native_unavailable",
        )
        return value.value

    def pipe(self, inherit_read):
        read, write = H(), H()
        security = SECURITY(C.sizeof(SECURITY), None, 1)
        require(self.api.CreatePipe(C.byref(read), C.byref(write), C.byref(security), 65536) != 0, "native_unavailable")
        read, write = self.owned(read.value), self.owned(write.value)
        require(self.api.SetHandleInformation(write if inherit_read else read, 1, 0) != 0, "native_unavailable")
        return read, write

    def write(self, handle, raw):
        require(type(raw) is bytes and 0 < len(raw) <= 65568, "wire_invalid")
        written = D()
        require(
            self.api.WriteFile(handle, raw, len(raw), C.byref(written), None) != 0 and written.value == len(raw),
            "wire_invalid",
        )

    def available(self, handle):
        available = D()
        if not self.api.PeekNamedPipe(handle, None, 0, None, C.byref(available), None):
            require(C.get_last_error() == 109, "wire_invalid")
            return None
        require(available.value <= 131136, "wire_invalid")
        return available.value

    def read(self, handle, size):
        require(type(size) is int and 0 < size <= 65536, "wire_invalid")
        buffer, count = C.create_string_buffer(size), D()
        require(
            self.api.ReadFile(handle, buffer, size, C.byref(count), None) != 0 and 0 < count.value <= size,
            "wire_invalid",
        )
        return buffer.raw[: count.value]

    def launch(self, python, argv, inherited, stdio, cwd, *, job=None):
        require(type(inherited) is tuple and 1 <= len(inherited) <= 8 and len(set(inherited)) == len(inherited))
        require(all(type(h) is int and 0 < h < UINT64 for h in inherited) and job not in inherited)
        count, size = (2 if job is not None else 1), Q()
        require(
            not self.api.InitializeProcThreadAttributeList(None, count, 0, C.byref(size))
            and C.get_last_error() == 122
            and 0 < size.value <= 65536,
            "native_unavailable",
        )
        backing = C.create_string_buffer(size.value)
        require(self.api.InitializeProcThreadAttributeList(backing, count, 0, C.byref(size)) != 0, "native_unavailable")
        try:
            handles = (H * len(inherited))(*inherited)
            require(
                self.api.UpdateProcThreadAttribute(backing, 0, 0x20002, handles, C.sizeof(handles), None, None) != 0,
                "native_unavailable",
            )
            if job is not None:
                jobs = (H * 1)(job)
                require(
                    self.api.UpdateProcThreadAttribute(backing, 0, 0x2000D, jobs, C.sizeof(jobs), None, None) != 0,
                    "native_unavailable",
                )
            startup, process = STARTUP_EX(), PROCESS()
            startup.startup.cb, startup.startup.flags = C.sizeof(STARTUP_EX), 0x100
            startup.startup.stdin, startup.startup.stdout, startup.startup.stderr = stdio
            require(all(handle in inherited for handle in stdio))
            startup.attributes = C.cast(backing, H).value
            command = C.create_unicode_buffer(command_line([str(validate_path(python)), *argv]))
            env = C.create_unicode_buffer(environment(cwd))
            require(
                self.api.CreateProcessW(
                    str(python),
                    command,
                    None,
                    None,
                    1,
                    0x4 | 0x80000 | 0x400,
                    env,
                    str(validate_path(cwd)),
                    C.byref(startup),
                    C.byref(process),
                )
                != 0,
                "native_unavailable",
            )
            self.owned(process.process)
            self.owned(process.thread)
            require(process.pid > 0 and process.tid > 0, "native_unavailable")
            return process
        finally:
            self.api.DeleteProcThreadAttributeList(backing)

    def loaded_paths(self):
        process, handles, needed = self.api.GetCurrentProcess(), (H * 512)(), D()
        require(
            self.api.K32EnumProcessModules(process, handles, C.sizeof(handles), C.byref(needed)) != 0,
            "closure_mismatch",
        )
        require(0 < needed.value <= C.sizeof(handles) and needed.value % C.sizeof(H) == 0, "closure_mismatch")
        paths = []
        for handle in handles[: needed.value // C.sizeof(H)]:
            text = C.create_unicode_buffer(4096)
            length = self.api.K32GetModuleFileNameExW(process, handle, text, 4096)
            require(0 < length < 4095, "closure_mismatch")
            path = str(validate_path(text.value))
            require(path not in paths, "closure_mismatch")
            paths.append(path)
        return tuple(sorted(paths, key=str.casefold))

    def closure(self, allowed):
        paths = self.loaded_paths()
        require(len(paths) <= 256, "closure_mismatch")
        for path in paths:
            require(path.casefold() in allowed and binary_sha(path) == allowed[path.casefold()], "closure_mismatch")
        require(self.loaded_paths() == paths, "closure_mismatch")
        return hashlib.sha256(canonical(list(paths))).hexdigest()


def run_windows_transaction(spec):
    try:
        validate_spec(spec)
        # Admission is verified before constructing Native or creating any output.
        admission = read_admission(spec)
        with ExitStack() as pins:
            for row in admission["code"]:
                handle = pins.enter_context(open_input(row["path"], 16777216))
                require(hashlib.sha256(handle.read_bytes()).hexdigest() == row["sha256"], "closure_mismatch")
            for row in admission["runtime"]:
                require(binary_sha(row["path"], keeper=pins) == row["sha256"], "closure_mismatch")
            return observe(spec, admission)
    except (ControlError, WaveformInputError, OSError, ValueError, TypeError) as error:
        reason = error.reason if type(error) is ControlError else "native_contract"
        return terminal(reason)


def read_admission(spec):
    pointer = spec["private_parent_receipt"]
    with open_input(pointer["path"], 65536) as source:
        raw = source.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == pointer["sha256"], "parent_mismatch")
    value = decode_control(raw)
    require(
        type(value) is dict
        and set(value) == {"schema", "source_revision", "parent", "abi", "code", "runtime", "review_receipt_sha256", "scientific_site_packages"}
    )
    require(value["schema"] == "caos.m08-private-admission.v1" and value["source_revision"] == spec["source_revision"])
    digest(value["review_receipt_sha256"])
    with files.open_output(validate_path(value["scientific_site_packages"])):
        pass
    parent = value["parent"]
    require(type(parent) is dict and set(parent) == {"path", "identity", "context_receipt_sha256"})
    digest(parent["context_receipt_sha256"])
    require(validate_path(parent["path"]) == validate_path(spec["out"]).parent, "parent_mismatch")
    require(
        type(parent["identity"]) is list
        and len(parent["identity"]) == 3
        and all(type(x) is int and 0 <= x <= 2**32 - 1 for x in parent["identity"]),
        "parent_mismatch",
    )
    with files.open_output(parent["path"]) as directory:
        require(tuple(parent["identity"]) == directory.identity, "parent_mismatch")
    abi = value["abi"]
    require(
        type(abi) is dict
        and set(abi)
        == {
            "source",
            "source_sha256",
            "executable",
            "executable_sha256",
            "stdout",
            "stdout_sha256",
            "review_receipt_sha256",
        }
    )
    for key in ("source_sha256", "executable_sha256", "stdout_sha256", "review_receipt_sha256"):
        digest(abi[key])
    for path, key, cap in (
        ("source", "source_sha256", 65536),
        ("executable", "executable_sha256", 16777216),
        ("stdout", "stdout_sha256", 4096),
    ):
        with open_input(abi[path], cap) as handle:
            data = handle.read_bytes()
        require(hashlib.sha256(data).hexdigest() == abi[key], "abi_unmeasured")
        if path == "stdout":
            parse_abi(data)
    require(
        validate_path(abi["source"]) == Path(__file__).resolve().parents[1] / "tests/fixtures/waveform_m08/abi_probe.c",
        "abi_unmeasured",
    )
    require(type(value["code"]) is list and 1 <= len(value["code"]) <= 32)
    expected = code_paths()
    actual = {}
    for row in value["code"]:
        require(type(row) is dict and set(row) == {"path", "sha256"})
        path = str(validate_path(row["path"]))
        digest(row["sha256"])
        require(path not in actual)
        actual[path] = row["sha256"]
    require(set(actual) == expected, "closure_mismatch")
    for path, sha in actual.items():
        with open_input(path, 16777216) as handle:
            require(hashlib.sha256(handle.read_bytes()).hexdigest() == sha, "closure_mismatch")
    require(type(value["runtime"]) is list and 1 <= len(value["runtime"]) <= 256)
    runtime = {}
    for row in value["runtime"]:
        require(type(row) is dict and set(row) == {"path", "sha256"})
        path = str(validate_path(row["path"]))
        digest(row["sha256"])
        require(path.casefold() not in runtime, "closure_mismatch")
        runtime[path.casefold()] = row["sha256"]
    require(
        hashlib.sha256(canonical(value["runtime"])).hexdigest() == spec["closure_manifest_sha256"], "closure_mismatch"
    )
    require(
        str(validate_path(spec["python"])).casefold() in runtime
        and binary_sha(spec["python"]) == runtime[str(validate_path(spec["python"])).casefold()],
        "closure_mismatch",
    )
    require(os.name == "nt", "platform_unavailable")
    return value


def digest(value):
    require(type(value) is str and re.fullmatch("[a-f0-9]{64}", value) is not None)
    return value


def code_paths():
    root = Path(__file__).resolve().parents[1]
    return {
        str(root / path)
        for path in (
            "scripts/waveform_m08_windows.py",
            "scripts/waveform_m08_files.py",
            "scripts/waveform_m08_export.py",
            "scripts/waveform_m08_child.py",
            "scripts/process_waveform_m08.py",
            "data-pipeline/waveform_input.py",
            "data-pipeline/waveform_processing.py",
            "data-pipeline/waveform_evaluation.py",
        )
    }


def binary_sha(path, *, keeper=None):
    """Read-only image pinning. System DLL hardlinks are not user-data inputs."""
    path = validate_path(path)
    held = files._lease(path.parent)
    handle, fd, success = None, None, False
    try:
        if os.name == "nt":
            import msvcrt

            api, _ = files._win_api()
            handle = api.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x00200000, None)
            require(handle not in (None, C.c_void_p(-1).value), "closure_mismatch")
            fd = msvcrt.open_osfhandle(handle, os.O_BINARY | os.O_RDONLY | os.O_NOINHERIT)
            handle = None
        else:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        info = files._info(fd)
        require(not info[3] and 0 < info[1] <= 134217728, "closure_mismatch")
        value, count = hashlib.sha256(), 0
        while count < info[1]:
            chunk = os.read(fd, min(65536, info[1] - count))
            require(bool(chunk), "closure_mismatch")
            count += len(chunk)
            value.update(chunk)
        require(not os.read(fd, 1) and files._info(fd) == info, "closure_mismatch")
        success = True
        return value.hexdigest()
    finally:
        if fd is not None:
            if keeper is not None and success:
                keeper.callback(os.close, fd)
            else:
                os.close(fd)
        if handle is not None:
            api.CloseHandle(handle)
        for item in reversed(held):
            if keeper is not None and success:
                keeper.callback(os.close, item)
            else:
                os.close(item)


CONTROL_NAMES = frozenset(
    (
        "observer.json",
        "child.json",
        "counts.ms",
        "response.xml",
        "request.json",
        "eligibility.json",
        "release.json",
        "failure.json",
    )
)


def control_file(directory, name, raw=None):
    require(name in CONTROL_NAMES)
    directory.check_identity()
    if raw is not None and name.endswith(".json"):
        require(type(raw) is bytes and 0 < len(raw) <= 65536)
        total = len(raw)
        for existing in directory.names(55):
            require(existing in CONTROL_NAMES or existing in ("science", "environment"))
            if existing in CONTROL_NAMES and existing.endswith(".json"):
                fd_existing = files._open_fd(directory.path / existing, parent_fd=directory.fd)
                try:
                    total += files._info(fd_existing)[1]
                finally:
                    os.close(fd_existing)
        require(total <= 65536)
    fd = files._open_fd(directory.path / name, create=raw is not None, parent_fd=directory.fd)
    try:
        if raw is not None:
            require(type(raw) is bytes and 0 < len(raw) <= 16777216)
            with os.fdopen(fd, "w+b", buffering=0, closefd=False) as handle:
                require(handle.write(raw) == len(raw))
                os.fsync(fd)
                handle.seek(0)
        return fd
    except BaseException:
        os.close(fd)
        raise


def inherited_handle(native, fd):
    import msvcrt

    handle = msvcrt.get_osfhandle(fd)
    require(native.api.SetHandleInformation(handle, 1, 1) != 0, "native_unavailable")
    return handle


def sealed_control_input(directory, name, raw):
    """Close the exclusive writer before leasing the immutable input read-only.

    Windows denies a second read-only lease while the original write-capable
    handle is open with FILE_SHARE_READ. Keep that protection, not SHARE_WRITE.
    """
    fd = control_file(directory, name, raw)
    os.close(fd)
    return control_file(directory, name)


def read_inherited(handle, cap, expected=None):
    import msvcrt

    require(type(handle) is int and 0 < handle < UINT64)
    require(type(cap) is int and 0 < cap <= 16777216)
    fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT)
    with os.fdopen(fd, "rb", buffering=0) as file:
        info = files._info(file.fileno())
        require(not info[3] and info[2] == 1 and 0 < info[1] <= cap)
        raw = file.read(cap + 1)
        require(len(raw) == info[1] and files._info(file.fileno()) == info)
    if expected is not None:
        require(hashlib.sha256(raw).hexdigest() == digest(expected), "closure_mismatch")
    return raw


def read_wire(native, handle, run, sequence, deadline):
    # Poll the 32-byte header before allocating its bounded payload.
    pending = b""
    phase, length = None, 32
    while time.monotonic_ns() < deadline:
        count = native.available(handle)
        require(count is not None, "wire_invalid")
        if count:
            pending += native.read(handle, min(count, length - len(pending)))
            if len(pending) == length:
                if phase is not None:
                    return phase, pending
                phase, length = header(pending, run, sequence)
                pending = b""
                if length == 0:
                    return phase, pending
        else:
            time.sleep(0.005)
    raise ControlError("timeout")


class WireReader:
    def __init__(self, run):
        self.run, self.sequence, self.phase, self.length, self.pending = run, 1, None, 32, b""
        self.eof = False

    def poll(self, native, handle):
        count = native.available(handle)
        if count is None:
            require(not self.pending and self.phase is None, "wire_invalid")
            self.eof = True
            return None
        if count == 0:
            return None
        self.pending += native.read(handle, min(count, self.length - len(self.pending)))
        if len(self.pending) != self.length:
            return None
        if self.phase is None:
            self.phase, self.length = header(self.pending, self.run, self.sequence)
            self.pending = b""
            if self.length:
                return None
        result = (self.phase, self.pending)
        self.sequence += 1
        self.phase, self.length, self.pending = None, 32, b""
        return result


def observe(spec, admission):
    require(not validate_path(spec["out"]).exists())
    native, job, controller = Native(), None, None
    state, reason, outcome = Lifetime(), None, None
    made_root = False
    bootstrap_diagnostics = set()
    hello, child, drained, exported = False, None, False, False
    observer_start = process_cpu(native)
    start = time.monotonic_ns()
    root_path = validate_path(spec["out"]).with_name(validate_path(spec["out"]).name + ".a4-" + spec["run_id"])
    try:
        native.closure(runtime_map(admission))
        capacity = native.capacity(shutil.disk_usage(validate_path(spec["out"]).parent).free)
        with files.create_output(root_path, trusted_parent=validate_path(spec["out"]).parent) as root:
            made_root = True
            require(root.identity != tuple(admission["parent"]["identity"]), "parent_mismatch")
            with ExitStack() as stack:
                stack.enter_context(files.create_output(root.path / "environment", trusted_parent=root.path))
                bootstrap_lease = stack.enter_context(ExitStack())
                bootstrap = sealed_control_input(root, "observer.json", canonical({"spec": spec, "scratch": str(root.path)}))
                bootstrap_lease.callback(os.close, bootstrap)
                bootstrap_handle = inherited_handle(native, bootstrap)
                events_r, events_w = native.pipe(False)
                ack_r, ack_w = native.pipe(True)
                stdout_r, stdout_w = native.pipe(False)
                stderr_r, stderr_w = native.pipe(False)
                job = native.owned(native.api.CreateJobObjectW(None, None))
                native.limits(job)
                baseline = native.sample(job)
                require(baseline[1:] == (0, 0, 0, 0, 0), "counter_invalid")
                state.sample(*baseline)
                argv = [
                    "-I",
                    "-B",
                    str(Path(__file__).resolve()),
                    "--controller",
                    str(bootstrap_handle),
                    str(events_w),
                    str(ack_r),
                ]
                controller = native.launch(
                    spec["python"],
                    argv,
                    (bootstrap_handle, events_w, ack_r, stdout_w, stderr_w),
                    (bootstrap_handle, stdout_w, stderr_w),
                    root.path,
                    job=job,
                )
                bootstrap_lease.close()
                native.membership(controller.process, job)
                require(native.members(job) == (controller.pid,), "membership")
                # Parent copies of child-side pipes must be closed for real EOF.
                for h in (events_w, ack_r, stdout_w, stderr_w):
                    native.close(h)
                native.resume(controller)
                wire, logs = WireReader(spec["run_id"]), {stdout_r: 0, stderr_r: 0}
                hello, child, drained, exported, child_started = False, None, False, False, None
                ack_seq = 1
                deadline = start + 120000000000
                while time.monotonic_ns() < deadline:
                    row = native.sample(job)
                    state.sample(*row)
                    if state.failure is not None:
                        raise ControlError(state.failure)
                    if state.drain is not None:
                        require(row[0] <= state.drain + 5000000000, "timeout")
                    if child_started is not None and not drained:
                        require(row[0] <= child_started + 60000000000, "timeout")
                    for handle in logs:
                        count = native.available(handle)
                        if count:
                            chunk = native.read(handle, min(count, 65536))
                            logs[handle] += len(chunk)
                            bootstrap_diagnostics.update(code.decode("ascii") for code in
                                re.findall(rb"M08_BOOTSTRAP:([A-Za-z0-9_]{1,40})\r?\n", chunk))
                            require(len(bootstrap_diagnostics) <= 16, "log_limit")
                            require(logs[handle] <= 65536, "log_limit")
                    event = wire.poll(native, events_r)
                    if event is not None:
                        phase, payload = event
                        if phase == "hello":
                            require(
                                not hello and child is None and struct.unpack("<Q", payload)[0] == controller.pid,
                                "wire_invalid",
                            )
                            hello = True
                        elif phase == "child":
                            require(hello and child is None, "wire_invalid")
                            child = struct.unpack("<Q", payload)[0]
                            require(set(native.members(job)) == {controller.pid, child}, "membership")
                            child_started = time.monotonic_ns()
                        elif phase == "drained":
                            stamp, pid, sequence = struct.unpack("<QQQ", payload)
                            require(
                                child is not None and not drained and pid == child and sequence == 1, "drain_invalid"
                            )
                            state.drained(stamp)
                            drained = True
                        elif phase == "export":
                            require(drained and not exported, "wire_invalid")
                            outcome = decode_control(payload)
                            require(
                                type(outcome) is dict
                                and set(outcome)
                                == {
                                    "manifest_sha256",
                                    "calculation_sha256",
                                    "bytes",
                                    "runtime_authorized",
                                    "scientific_status",
                                },
                                "export_invalid",
                            )
                            digest(outcome["manifest_sha256"])
                            digest(outcome["calculation_sha256"])
                            require(
                                type(outcome["bytes"]) is int
                                and 0 < outcome["bytes"] <= 33554432
                                and outcome["runtime_authorized"] is False,
                                "export_invalid",
                            )
                            require(outcome["scientific_status"] in ("computed", "qc_only"), "export_invalid")
                            exported = True
                        elif phase == "error":
                            raise ControlError(payload.decode("ascii") if len(payload) <= 32 else "wire_invalid")
                        else:
                            raise ControlError("wire_invalid")
                        if phase in ("hello", "child"):
                            native.write(ack_w, frame(spec["run_id"], ack_seq, "ack", b""))
                            ack_seq += 1
                    if native.signalled(controller.process):
                        if wire.eof:
                            require(native.exit_code(controller.process) == 0 and exported, "child_failed")
                        if state.final_ready and wire.eof and all(native.available(h) is None for h in logs):
                            break
                    time.sleep(0.01)
                else:
                    raise ControlError("timeout")
                require(state.final_ready and state.last[3] == 0 and child is not None, "drain_invalid")
                observer_end = process_cpu(native)
                require(observer_end >= observer_start, "counter_invalid")
                receipt = {
                    "schema": "caos.m08-local-resources.v1",
                    "run_id": spec["run_id"],
                    "status": "measured",
                    "source_revision": spec["source_revision"],
                    "prelaunch_capacity": capacity,
                    "closure_manifest_sha256": spec["closure_manifest_sha256"],
                    "admission_sha256": spec["private_parent_receipt"]["sha256"],
                    "export": outcome,
                    "cpu_ns": state.final_cpu_ns,
                    "budget_ns": B,
                    "stop_ns": S,
                    "sample_count": state.samples,
                    "max_sample_gap_ns": state.max_gap_ns,
                    "drained_ns": state.drain,
                    "stable_final_ns": state.last[0],
                    "peak_committed_bytes": state.last[5],
                    "experimental_memory_limit_bytes": MEMORY,
                    "rss": "unavailable",
                    "controller_pid": controller.pid,
                    "child_pid": child,
                    "active_processes": 0,
                    "observer_cpu_delta_ns": observer_end - observer_start,
                    "observer_lifetime_cpu_at_entry_ns": observer_start,
                    "observer_lifetime_cpu_prefinal_ns": observer_end,
                    "observer_preflight_in_delta": False,
                    "observer_receipt_tail_cpu": "not_in_delta",
                    "runtime_authorized": False,
                    "method_accepted": False,
                    "host_admitted": False,
                }
                fd = control_file(root, "eligibility.json", canonical(receipt))
                os.close(fd)
                # Receipt alone is provisional. A separate, exclusive release acknowledgment
                # binds it after every native owned handle (including the sole job) closes.
                native.cleanup()
                released = {
                    "schema": "caos.m08-local-release.v1",
                    "run_id": spec["run_id"],
                    "receipt_sha256": hashlib.sha256(canonical(receipt)).hexdigest(),
                    "all_native_owned_handles_closed": True,
                    "runtime_authorized": False,
                }
                fd = control_file(root, "release.json", canonical(released))
                os.close(fd)
                return {
                    "status": outcome["scientific_status"],
                    "reason": "measured",
                    "runtime_authorized": False,
                    "run_id": spec["run_id"],
                    "receipt_sha256": released["receipt_sha256"],
                    "release_sha256": hashlib.sha256(canonical(released)).hexdigest(),
                }
    except BaseException as error:
        reason = (
            "cancelled"
            if isinstance(error, KeyboardInterrupt)
            else error.reason
            if type(error) is ControlError
            else "native_contract"
        )
        final_row, stop_elapsed = None, None
        if job is not None and job in native.handles:
            stop_start = time.monotonic_ns()
            if not native.api.TerminateJobObject(job, 3):
                reason = "termination_unresolved"
            until = stop_start + 5000000000
            try:
                final_row = native.sample(job)
                while final_row[3] and time.monotonic_ns() < until:
                    time.sleep(0.01)
                    final_row = native.sample(job)
                require(final_row[3] == 0, "termination_unresolved")
                stop_elapsed = time.monotonic_ns() - stop_start
                if cpu_ns(final_row[1], final_row[2]) > B:
                    reason = "resource_exceeded"
            except ControlError:
                reason = "termination_unresolved"
        if made_root:
            failure = {
                "schema": "caos.m08-local-failure.v1",
                "run_id": spec["run_id"],
                "status": "failed",
                "reason": reason,
                "final_sample": list(final_row) if final_row is not None else None,
                "stop_to_empty_ns": stop_elapsed,
                "cancel_target_met": stop_elapsed is not None and stop_elapsed <= 2000000000,
                "runtime_authorized": False,
                "method_accepted": False,
                "host_admitted": False,
                "bootstrap_failure_codes": sorted(bootstrap_diagnostics),
                "protocol_progress": {"hello": hello, "child_started": child is not None,
                                      "drained": drained, "exported": exported},
                "wall_elapsed_ns": time.monotonic_ns() - start,
            }
            try:
                with files.open_output(root_path) as directory:
                    fd = control_file(directory, "failure.json", canonical(failure))
                    os.close(fd)
            except (ControlError, WaveformInputError, OSError):
                reason = "termination_unresolved"
        return terminal(reason)
    finally:
        # Sole job ownership persists through final samples/receipt. Last close kills on observer death.
        try:
            native.cleanup()
        except ControlError:
            pass


def process_cpu(native):
    records = [FILETIME() for _ in range(4)]
    require(
        native.api.GetProcessTimes(native.api.GetCurrentProcess(), *(C.byref(r) for r in records)) != 0,
        "counter_invalid",
    )
    return cpu_ns((records[3].high << 32) | records[3].low, (records[2].high << 32) | records[2].low)


def runtime_map(admission):
    return {row["path"].casefold(): row["sha256"] for row in admission["runtime"]}


def run_cli(paths, reference, admission_path):
    try:
        with open_input(admission_path, 65536) as handle:
            raw = handle.read_bytes()
        admission = decode_control(raw)
        require(type(admission) is dict and type(admission.get("runtime")) is list and len(admission["runtime"]) <= 256)
        # No resource/provider/profile flags; only a fresh local run identity.
        spec = {
            "schema": "caos.m08-windows-transaction.v1",
            "run_id": os.urandom(16).hex(),
            "source_revision": admission.get("source_revision"),
            "closure_manifest_sha256": hashlib.sha256(canonical(admission["runtime"])).hexdigest(),
            **{key: str(value) for key, value in paths.items()},
            "evaluate_with": str(reference) if reference is not None else None,
            "private_parent_receipt": {"path": str(admission_path), "sha256": hashlib.sha256(raw).hexdigest()},
        }
        return run_windows_transaction(spec)
    except (ControlError, WaveformInputError, OSError, ValueError, TypeError):
        return {"status": "rejected", "reason": "native_contract", "runtime_authorized": False}


def terminal(reason):
    mapping = {
        "abi_unmeasured": ("engine_unavailable", "supervisor_unavailable"),
        "native_unavailable": ("engine_unavailable", "supervisor_unavailable"),
        "platform_unavailable": ("engine_unavailable", "supervisor_unavailable"),
        "parent_mismatch": ("engine_unavailable", "supervisor_unavailable"),
        "closure_mismatch": ("engine_unavailable", "supervisor_unavailable"),
        "counter_invalid": ("failed", "resource_unavailable"),
        "sample_gap": ("failed", "resource_unavailable"),
        "drain_invalid": ("failed", "resource_unavailable"),
        "membership": ("failed", "containment"),
        "resource_stop": ("resource_exceeded", "cpu_stop"),
        "resource_exceeded": ("resource_exceeded", "resource_exceeded"),
        "timeout": ("timed_out", "wall_cap"),
        "cancelled": ("cancelled", "cancelled"),
        "child_failed": ("failed", "child_crash"),
        "wire_invalid": ("failed", "child_protocol"),
        "export_invalid": ("failed", "export_validation"),
        "termination_unresolved": ("failed", "termination_unresolved"),
        "log_limit": ("failed", "child_protocol"),
        "scientific_rejected": ("rejected", "waveform_contract"),
        "scientific_engine": ("engine_unavailable", "waveform_engine"),
        "science_failed": ("failed", "calculation_failed"),
    }
    status, literal = mapping.get(reason, ("rejected", "native_contract"))
    return {"status": status, "reason": literal, "runtime_authorized": False}


def exit_status(result):
    return {
        "computed": 0,
        "qc_only": 2,
        "rejected": 3,
        "engine_unavailable": 4,
        "failed": 5,
        "resource_exceeded": 6,
        "timed_out": 124,
        "cancelled": 130,
    }.get(result.get("status"), 5)


def acknowledge(native, handle, run, sequence, deadline):
    phase, payload = read_wire(native, handle, run, sequence, deadline)
    require(phase == "ack" and payload == b"", "wire_invalid")


def role_arguments(argv):
    require(type(argv) is list and len(argv) == 4 and argv[0] in ("--controller", "--science"))
    values = []
    for text in argv[1:]:
        require(type(text) is str and re.fullmatch(r"[1-9][0-9]{0,19}", text) is not None)
        values.append(integer(int(text)))
    return argv[0], values


def controller_role(control, event_handle, ack_handle):
    value = decode_control(read_inherited(control, 65536))
    require(type(value) is dict and set(value) == {"spec", "scratch"})
    spec = validate_spec(value["spec"])
    admission = read_admission(spec)
    native, child = Native(), None
    run, until = spec["run_id"], time.monotonic_ns() + 60000000000
    native.membership(native.api.GetCurrentProcess(), None)
    native.current_limits()
    native.closure(runtime_map(admission))
    native.write(event_handle, frame(run, 1, "hello", struct.pack("<Q", os.getpid())))
    acknowledge(native, ack_handle, run, 1, until)
    import msvcrt
    from waveform_m08_export import verify_export, copy_export
    from waveform_evaluation import evaluate_waveform_candidates

    event_seq, checkpoint = 2, "controller_inputs"
    try:
        with files.open_output(value["scratch"]) as scratch, ExitStack() as stack:
            staging = stack.enter_context(files.create_output(scratch.path / "science", trusted_parent=scratch.path))
            # Originals held and hashed by the accounted controller; child sees only NEW staging handles.
            inputs, stack_inputs, total = [], [], 0
            for key, name, cap in (
                ("mseed", "counts.ms", 16777216),
                ("stationxml", "response.xml", 2097152),
                ("request", "request.json", 65536),
            ):
                original = stack.enter_context(open_input(spec[key], cap))
                stack_inputs.append(original)
                raw = original.read_bytes()
                total += len(raw)
                require(total <= 18939904)
                fd = sealed_control_input(scratch, name, raw)
                stack.callback(os.close, fd)
                inputs.append({"handle": inherited_handle(native, fd), "cap": cap, "sha256": original.sha256})
            child_events_r, child_events_w = native.pipe(False)
            stdout = msvcrt.get_osfhandle(sys.stdout.fileno())
            stderr = msvcrt.get_osfhandle(sys.stderr.fileno())
            child_info = {
                "run_id": run,
                "inputs": inputs,
                "out": str(staging.path),
                "out_identity": list(staging.identity),
                "out_handle": inherited_handle(native, staging.fd),
                "runtime": admission["runtime"],
                "scientific_site_packages": admission["scientific_site_packages"],
            }
            fd = sealed_control_input(scratch, "child.json", canonical(child_info))
            stack.callback(os.close, fd)
            bootstrap = inherited_handle(native, fd)
            inherited = tuple(row["handle"] for row in inputs) + (
                child_info["out_handle"],
                bootstrap,
                child_events_w,
                stdout,
                stderr,
            )
            child = native.launch(
                spec["python"],
                [
                    "-I",
                    "-B",
                    str(Path(__file__).resolve()),
                    "--science",
                    str(bootstrap),
                    str(child_events_w),
                    str(child_events_w),
                ],
                inherited,
                (bootstrap, stdout, stderr),
                scratch.path,
            )
            native.membership(child.process, None)
            native.write(event_handle, frame(run, event_seq, "child", struct.pack("<Q", child.pid)))
            event_seq += 1
            acknowledge(native, ack_handle, run, 2, until)
            native.close(child_events_w)
            native.resume(child)
            checkpoint = "controller_drain"
            phase, payload = read_wire(native, child_events_r, run, 1, until)
            if phase == "error":
                require(len(payload) <= 32, "wire_invalid")
                raise ControlError(payload.decode("ascii"))
            require(phase == "drained", "drain_invalid")
            stamp, pid, seq = struct.unpack("<QQQ", payload)
            require(pid == child.pid and seq == 1, "drain_invalid")
            native.write(event_handle, frame(run, event_seq, "drained", payload))
            event_seq += 1
            print("M08_BOOTSTRAP:controller_child_exit_wait", file=sys.stderr, flush=True)
            while not native.signalled(child.process) and time.monotonic_ns() < until:
                time.sleep(0.005)
            require(native.exit_code(child.process) == 0 and native.available(child_events_r) is None, "child_failed")
            print("M08_BOOTSTRAP:controller_child_exited", file=sys.stderr, flush=True)
            checkpoint = "controller_export_verify"
            sealed = verify_export(staging)
            evaluation = None
            # Reference acquisition begins only after the independent sealed export reopens.
            if spec["evaluate_with"] is not None:
                with open_input(spec["evaluate_with"], 1048576) as reference:
                    evaluation = canonical(evaluate_waveform_candidates(sealed, reference.read_bytes()), 2097152)
            with files.create_output(spec["out"], trusted_parent=validate_path(spec["out"]).parent) as destination:
                checkpoint = "controller_environment"
                profile_bytes = environment_bytes(scratch.path / "environment")
                checkpoint = "controller_export_copy"
                outcome = copy_export(
                    staging,
                    destination,
                    evaluation=evaluation,
                    scratch_input_bytes=total,
                    environment_bytes=profile_bytes,
                )
            from waveform_input import bounded_json

            outcome["scientific_status"] = bounded_json(
                sealed.metadata_bytes, 2097152, max_nodes=2097152, max_depth=16
            )["status"]
            checkpoint = "controller_originals"
            for original in stack_inputs:
                verify_original(original)
            native.closure(runtime_map(admission))
            native.write(event_handle, frame(run, event_seq, "export", canonical(outcome)))
            event_seq += 1
            return 0
    except (ControlError, WaveformInputError, OSError, ValueError, TypeError) as error:
        reason = error.reason if type(error) is ControlError else "export_invalid"
        # Fixed class/control codes only: never expose exception text or paths.
        code = reason if type(error) is ControlError else type(error).__name__
        print("M08_BOOTSTRAP:" + checkpoint, file=sys.stderr, flush=True)
        print("M08_BOOTSTRAP:" + code, file=sys.stderr, flush=True)
        try:
            native.write(event_handle, frame(run, event_seq, "error", reason.encode("ascii")))
        except ControlError:
            pass
        return 3
    finally:
        # No job handle in this process. Observer alone terminates the contained group.
        native.cleanup()


def science_role(control, event_handle, unused_ack):
    value = decode_control(read_inherited(control, 65536))
    require(type(value) is dict and set(value) == {"run_id", "inputs", "out", "out_identity", "out_handle", "runtime", "scientific_site_packages"})
    require(type(value["run_id"]) is str and re.fullmatch("[a-f0-9]{32}", value["run_id"]) is not None)
    require(type(value["inputs"]) is list and len(value["inputs"]) == 3)
    native = Native()
    native.membership(native.api.GetCurrentProcess(), None)
    native.current_limits()
    try:
        return scientific_work(value, native, event_handle)
    except Exception as error:
        reason = (
            "scientific_engine"
            if isinstance(error, WaveformInputError) and error.code == "waveform_engine"
            else "scientific_rejected"
            if isinstance(error, WaveformInputError)
            else error.reason
            if type(error) is ControlError
            else "science_failed"
        )
        native.write(event_handle, frame(value["run_id"], 1, "error", reason.encode("ascii")))
        return 3


def scientific_work(value, native, event_handle):
    # Science imports happen within the job, then actual loaded closure is checked before decode.
    site = validate_path(value["scientific_site_packages"])
    with files.open_output(site):
        pass
    sys.path.insert(0, str(site))
    from waveform_m08_child import calculate_bytes
    from waveform_m08_export import plan_export, write_export

    prepare_engine()
    native.closure(runtime_map(value))
    sources = []
    for row, cap in zip(value["inputs"], (16777216, 2097152, 65536), strict=True):
        require(
            type(row) is dict
            and set(row) == {"handle", "cap", "sha256"}
            and type(row["cap"]) is int
            and row["cap"] == cap
        )
        sources.append(read_inherited(row["handle"], cap, row["sha256"]))
    import msvcrt

    fd = msvcrt.open_osfhandle(integer(value["out_handle"]), os.O_RDONLY | os.O_NOINHERIT)
    with files.OwnedDirectory(validate_path(value["out"]), [fd]) as destination:
        require(type(value["out_identity"]) is list and tuple(value["out_identity"]) == destination.identity)
        result, sealed = calculate_bytes(*sources)
        write_export(plan_export(result, sealed), destination)
        native.closure(runtime_map(value))
    native.write(
        event_handle, frame(value["run_id"], 1, "drained", struct.pack("<QQQ", time.monotonic_ns(), os.getpid(), 1))
    )
    # No scientific work/output after DRAINED; process-exit CPU is still counted by the observer.
    return 0


def verify_original(original):
    original.handle.seek(0)
    count, value = 0, hashlib.sha256()
    while count < original.initial[1]:
        chunk = original.handle.read(min(65536, original.initial[1] - count))
        require(bool(chunk), "closure_mismatch")
        count += len(chunk)
        value.update(chunk)
    require(
        not original.handle.read(1)
        and files._info(original.fd) == original.initial
        and value.hexdigest() == original.sha256,
        "closure_mismatch",
    )


def cache_file_info(path):
    """Metadata-only accounting for caches still open inside the contained job.

    Cache writers are allowed to retain their write handles. This does not
    change the exclusive held-byte readers for originals/scientific exports.
    FILE_SHARE_DELETE is never granted; reparse/hardlink checks remain exact.
    """
    if os.name != "nt":
        fd = files._open_fd(validate_path(path))
        try:
            return files._info(fd)
        finally:
            os.close(fd)
    api, Info = files._win_api()
    handle = api.CreateFileW(str(validate_path(path)), 0x80, 3, None, 3, 0x00200000, None)
    require(handle not in (None, C.c_void_p(-1).value))
    try:
        info = Info()
        require(api.GetFileType(handle) == 1 and api.GetFileInformationByHandle(handle, info)
                and not info.attributes & (0x400 | 0x10) and info.links == 1)
        return ((info.volume, info.index_high, info.index_low), (info.size_high << 32) | info.size_low,
                info.links, False, (info.written.high << 32) | info.written.low)
    finally:
        require(api.CloseHandle(handle) != 0)


def environment_bytes(path):
    """Bounded cold-start cache accounting; not a filesystem quota/sandbox."""
    total, entries = 0, 0

    def visit(directory, depth):
        nonlocal total, entries
        require(depth <= 8)
        with os.scandir(directory) as stream:
            for item in stream:
                entries += 1
                require(entries <= 1024 and not item.is_symlink())
                info = item.stat(follow_symlinks=False)
                require(not getattr(info, "st_file_attributes", 0) & 0x400)
                if item.is_dir(follow_symlinks=False):
                    visit(item.path, depth + 1)
                else:
                    require(item.is_file(follow_symlinks=False))
                    # Windows DirEntry's cached stat may report an unavailable link
                    # count. Use the existing held native file-information path;
                    # never treat a missing/zero cached count as a measured one.
                    measured = cache_file_info(item.path)
                    require(not measured[3] and measured[2] == 1 and 0 <= measured[1] <= SCRATCH)
                    total += measured[1]
                    require(total <= SCRATCH)

    visit(path, 0)
    return total


def prepare_engine():
    """Fixed lazy-reader/response/filter imports inside containment, before decode."""
    from waveform_processing import _engine_modules

    _engine_modules()
    import importlib

    for name in (
        "obspy.io.mseed.core",
        "obspy.io.stationxml.core",
        "obspy.signal.headers",
        "obspy.signal.invsim",
        "obspy.signal.util",
        "obspy.signal.trigger",
        "scipy.signal",
    ):
        importlib.import_module(name)


if __name__ == "__main__":
    try:
        role, arguments = role_arguments(sys.argv[1:])
        raise SystemExit(controller_role(*arguments) if role == "--controller" else science_role(*arguments))
    except Exception as error:
        code = error.reason if type(error) is ControlError else type(error).__name__
        if re.fullmatch(r"[A-Za-z0-9_]{1,40}", code) is None:
            code = "native_contract"
        print("M08_BOOTSTRAP:" + code, file=sys.stderr, flush=True)
        raise SystemExit(3) from None
