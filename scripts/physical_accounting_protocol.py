"""Bounded supplied-stream consistency only. No OS/I/O/clock or runtime authority.

Approval/design: docs/design/features/physical-accounting-protocol/approval.md.
Native platforms remain CLOSED; this module does not observe native counters.
"""

import dataclasses as _d
import enum as _enum
import hashlib as _hashlib
import json as _json

__all__ = (
    "RecordKind", "Platform", "LaneLimits", "SafeError", "ProtocolError",
    "ProtocolDecision", "ProtocolEligibility", "ProtocolSession", "StartRecord",
    "ControlRecord", "SampleRecord", "ReceiptRecord", "ReleaseRecord", "limits_for",
    "decode_record", "windows_cpu_ns", "linux_cpu_ns", "checked_delta_ns", "safe_error",
)

_I64 = 9223372036854775807
_U64 = 18446744073709551615
_U32 = 4294967295
_GAP = 20000000
_DRAIN = 2000000000
_KILL = 250000000
_RECORDS = 32768
_BYTES = 16777216
_HEX = "0123456789abcdef"
_MESSAGES = {
    "accounting_admission_closed": "Physical CPU accounting admission is closed",
    "accounting_launch_failed": "Contained execution could not start",
    "accounting_counter_invalid": "CPU accounting could not be verified",
    "accounting_cpu_limit": "Aggregate CPU budget was reached",
    "accounting_observation_gap": "CPU observation timing could not be verified",
    "accounting_containment_failed": "Execution containment could not be verified",
    "accounting_termination_uncertain": "Execution termination could not be verified",
    "accounting_receipt_unavailable": "Final CPU receipt is unavailable",
    "accounting_parent_limit": "Controller resource budget was reached",
    "accounting_protocol_invalid": "Private accounting protocol is invalid",
    "accounting_bounds_exceeded": "Private accounting record exceeds its bounds",
    "accounting_integer_invalid": "Accounting integer type or range is invalid",
    "accounting_counter_overflow": "Accounting counter conversion would overflow",
    "accounting_counter_underflow": "Accounting counter difference would underflow",
    "accounting_identity_mismatch": "Accounting identity does not match the attempt",
    "accounting_transition_invalid": "Accounting protocol transition is invalid",
    "accounting_release_invalid": "Accounting release acknowledgment is invalid",
}
_LIMIT_KEYS = ("cpu_ceiling_ns", "cpu_stop_ns", "cpu_margin_ns", "wall_ns",
               "rss_bytes", "scratch_bytes", "result_bytes")
_PARENT_KEYS = ("cpu_ceiling_ns", "control_bytes", "receipt_bytes", "stdout_bytes", "stderr_bytes")
_LANES = {
    "gravity.station-corrections/v1": (60000000000, 57000000000, 3000000000,
        120000000000, 805306368, 268435456, 67108864, 5000000000, 16384, 65536, 65536, 65536),
    "gravity.equivalent-source-transform/v1": (240000000000, 237000000000, 3000000000,
        300000000000, 1610612736, 536870912, 67108864, 10000000000, 16384, 65536, 65536, 65536),
}
_REASONS = ("clean_exit", "cpu_limit", "wall_limit", "memory_limit", "scratch_limit",
            "user_cancelled", "output_limit", "worker_lost", "controller_lost",
            "unexpected_descendants", "identity_changed", "counter_invalid", "observe_gap",
            "kill_timeout", "startup_failed", "receipt_lost")


class RecordKind(_enum.Enum):
    START = "physical-accounting-start-1"
    CONTROL = "physical-accounting-control-1"
    SAMPLE = "physical-accounting-sample-1"
    RECEIPT = "physical-accounting-receipt-1"
    RELEASE = "physical-accounting-release-1"


class Platform(_enum.Enum):
    WINDOWS_JOB_X64_1 = "windows-job-x64-1"
    LINUX_CGROUP2_X64_1 = "linux-cgroup2-x64-1"


_CAPS = {RecordKind.START: 16384, RecordKind.CONTROL: 1024, RecordKind.SAMPLE: 4096,
         RecordKind.RECEIPT: 16384, RecordKind.RELEASE: 4096}


class ProtocolError(Exception):
    """Fixed application fields only; tracebacks are NOT safe public evidence."""

    def __init__(self, code):
        if type(code) is not str or len(code) > 48 or code not in _MESSAGES:
            code = "accounting_protocol_invalid"
        self.code = code
        self.message = _MESSAGES[code]
        super().__init__(self.code, self.message)


def _fail(code="accounting_protocol_invalid"):
    raise ProtocolError(code) from None


def _require(condition, code="accounting_protocol_invalid"):
    if not condition:
        _fail(code)


def _integer(value, low=0, high=_I64):
    _require(type(value) is int and low <= value <= high, "accounting_integer_invalid")
    return value


def _boolean(value, expected=None):
    _require(type(value) is bool)
    if expected is not None:
        _require(value is expected)
    return value


def _string(value, cap=128):
    _require(type(value) is str)
    _require(len(value) <= cap, "accounting_bounds_exceeded")
    return value


def _digest(value, length=64):
    _string(value, length)
    _require(len(value) == length and all(char in _HEX for char in value))
    return value


def _uuid(value):
    _string(value, 36)
    _require(len(value) == 36)
    positions = (8, 13, 18, 23)
    nonzero = False
    for index, char in enumerate(value):
        _require(char == "-" if index in positions else char in _HEX)
        if index not in positions and char != "0":
            nonzero = True
    _require(nonzero)
    return value


def _choice(value, allowed):
    _string(value)
    _require(value in allowed)
    return value


@_d.dataclass(frozen=True, slots=True)
class SafeError:
    code: str
    message: str
    retryable: bool = False

    def __post_init__(self):
        _string(self.code, 48)
        _string(self.message, 96)
        _require(self.code in _MESSAGES and self.message == _MESSAGES[self.code]
                 and type(self.message) is str)
        _boolean(self.retryable, False)


def safe_error(code):
    _require(type(code) is str)
    if len(code) > 48 or code not in _MESSAGES:
        code = "accounting_protocol_invalid"
    return SafeError(code, _MESSAGES[code], False)


@_d.dataclass(frozen=True, slots=True)
class LaneLimits:
    method_id: str
    cpu_ceiling_ns: int
    cpu_stop_ns: int
    cpu_margin_ns: int
    wall_ns: int
    rss_bytes: int
    scratch_bytes: int
    result_bytes: int
    parent_cpu_ceiling_ns: int
    control_bytes: int
    receipt_bytes: int
    stdout_bytes: int
    stderr_bytes: int

    def __post_init__(self):
        _string(self.method_id)
        _require(self.method_id in _LANES)
        fields = _LIMIT_KEYS + ("parent_cpu_ceiling_ns", "control_bytes", "receipt_bytes",
                               "stdout_bytes", "stderr_bytes")
        for key, expected in zip(fields, _LANES[self.method_id]):
            _require(_integer(getattr(self, key)) == expected)


def limits_for(method_id):
    _string(method_id)
    _require(method_id in _LANES)
    return LaneLimits(method_id, *_LANES[method_id])


def _sum(a, b, ceiling=_I64):
    _require(a <= ceiling - b, "accounting_counter_overflow")
    return a + b


def _multiply(value, factor):
    _require(value <= _I64 // factor, "accounting_counter_overflow")
    return value * factor


def windows_cpu_ns(user_ticks, kernel_ticks):
    return _multiply(_sum(_integer(user_ticks), _integer(kernel_ticks)), 100)


def linux_cpu_ns(usage_usec, user_usec, system_usec):
    usage = _integer(usage_usec, high=_U64)
    user = _integer(user_usec, high=_U64)
    system = _integer(system_usec, high=_U64)
    return _multiply(max(usage, _sum(user, system, _U64)), 1000)


def checked_delta_ns(current, previous):
    _integer(current)
    _integer(previous)
    _require(current >= previous, "accounting_counter_underflow")
    return current - previous


def _scan_string(frame, index, cap):
    index += 1
    count = 0
    while index < len(frame):
        char = frame[index]
        if char == 34:
            return index + 1
        _require(32 <= char <= 126 and char != 92)
        count += 1
        _require(count <= cap, "accounting_bounds_exceeded")
        index += 1
    _fail()


def _scan_number(frame, index):
    negative = frame[index] == 45
    first = index + 1 if negative else index
    index = first
    _require(index < len(frame) and 48 <= frame[index] <= 57)
    while index < len(frame) and 48 <= frame[index] <= 57:
        index += 1
        _require(index - first <= 20, "accounting_bounds_exceeded")
    digits = index - first
    _require(not (digits > 1 and frame[first] == 48))
    _require(not (negative and frame[first] == 48))
    bound = b"2147483648" if negative else b"18446744073709551615"
    _require(digits <= len(bound), "accounting_integer_invalid")
    if digits == len(bound):
        for offset in range(digits):
            if frame[first + offset] < bound[offset]:
                break
            _require(frame[first + offset] <= bound[offset], "accounting_integer_invalid")
    return index


def _preflight(kind, frame):
    """Fixed six-level byte scanner; never copies/decodes tokens or converts ints."""
    _require(type(kind) is RecordKind and type(frame) is bytes)
    _require(len(frame) <= _CAPS[kind], "accounting_bounds_exceeded")
    index = 0
    while index < len(frame) and frame[index] in (9, 10, 13, 32):
        index += 1
    _require(index < len(frame) and frame[index] == 123)
    states, members = [0] * 6, [0] * 6
    depth, nodes = 1, 1
    index += 1
    while index < len(frame):
        char = frame[index]
        if char in (9, 10, 13, 32):
            index += 1
            continue
        _require(depth > 0)
        level = depth - 1
        state = states[level]
        if state in (0, 4):  # initial key/end, or required key after comma
            if char == 125 and state == 0:
                depth -= 1
                index += 1
                continue
            _require(char == 34)
            members[level] += 1
            _require(members[level] <= 32, "accounting_bounds_exceeded")
            index = _scan_string(frame, index, 64)
            nodes += 1
            states[level] = 1
        elif state == 1:
            _require(char == 58)
            states[level] = 2
            index += 1
        elif state == 2:
            nodes += 1
            states[level] = 3
            if char == 123:
                _require(depth < 6, "accounting_bounds_exceeded")
                states[depth], members[depth] = 0, 0
                depth += 1
                index += 1
            elif char == 34:
                index = _scan_string(frame, index, 128)
            elif char == 45 or 48 <= char <= 57:
                index = _scan_number(frame, index)
            else:
                literal = {116: b"true", 102: b"false", 110: b"null"}.get(char)
                _require(literal is not None and len(frame) - index >= len(literal))
                for offset, expected in enumerate(literal):
                    _require(frame[index + offset] == expected)
                index += len(literal)
        else:
            if char == 125:
                depth -= 1
                index += 1
            else:
                _require(char == 44)
                states[level] = 4
                index += 1
        _require(nodes <= 256, "accounting_bounds_exceeded")
    _require(depth == 0)


def _parse_int(token):
    # The JSON decoder creates this token ONLY after preflight bounded it.
    _require(type(token) is str and 0 < len(token) <= 21)
    negative = token[0] == "-"
    first = 1 if negative else 0
    digits = len(token) - first
    _require(0 < digits <= 20, "accounting_bounds_exceeded")
    bound = "2147483648" if negative else "18446744073709551615"
    _require(digits <= len(bound), "accounting_integer_invalid")
    if digits == len(bound):
        for offset in range(digits):
            if token[first + offset] < bound[offset]:
                break
            _require(token[first + offset] <= bound[offset], "accounting_integer_invalid")
    return int(token)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _reject_numeric(value):
    _fail()


def _decode_json(frame):
    error_code = None
    try:
        result = _json.loads(frame.decode("ascii"), object_pairs_hook=_pairs,
                             parse_int=_parse_int, parse_float=_reject_numeric,
                             parse_constant=_reject_numeric)
    except ProtocolError as error:
        error_code = error.code
    except (_json.JSONDecodeError, UnicodeDecodeError):
        error_code = "accounting_protocol_invalid"
    # Raise OUTSIDE the parser handler; do not keep JSONDecodeError.doc/context.
    if error_code is not None:
        _fail(error_code)
    return result


def _keys(obj, keys):
    _require(type(obj) is dict and obj.keys() == set(keys))


def _schema(obj, kind):
    _require(type(obj.get("schema")) is str and obj["schema"] == kind.value)


def _limits(data, method=None):
    _keys(data, _LIMIT_KEYS)
    values = tuple(_integer(data[key]) for key in _LIMIT_KEYS)
    if method is None:
        _require(any(values == lane[:7] for lane in _LANES.values()))
    else:
        _require(values == _LANES[method][:7])


def _platform(value):
    return _choice(value, (Platform.WINDOWS_JOB_X64_1.value, Platform.LINUX_CGROUP2_X64_1.value))


def _native(native, platform):
    if platform == Platform.WINDOWS_JOB_X64_1.value:
        _keys(native, ("total_user_ticks", "total_kernel_ticks"))
        return windows_cpu_ns(native["total_user_ticks"], native["total_kernel_ticks"])
    _keys(native, ("usage_usec", "user_usec", "system_usec"))
    return linux_cpu_ns(native["usage_usec"], native["user_usec"], native["system_usec"])


def _active(active, platform):
    if platform == Platform.WINDOWS_JOB_X64_1.value:
        _keys(active, ("active_processes", "total_processes", "limit_terminated_processes"))
        for value in active.values():
            _integer(value, high=_U32)
        _require(active["active_processes"] <= 32 and
                 active["active_processes"] <= active["total_processes"] and
                 active["limit_terminated_processes"] <= active["total_processes"],
                 "accounting_counter_invalid")
    else:
        _keys(active, ("populated", "root_reaped", "adopted_reaped"))
        _integer(active["populated"], high=1)
        _boolean(active["root_reaped"])
        _boolean(active["adopted_reaped"])


def _exit(value, platform):
    return _integer(value, 0 if platform == Platform.WINDOWS_JOB_X64_1.value else -2147483648,
                    _U32 if platform == Platform.WINDOWS_JOB_X64_1.value else 2147483647)


def _validate_start(data):
    _keys(data, ("schema", "attempt_id", "job_id", "method_id", "input_sha256",
        "request_sha256", "source_commit", "runtime_sha256", "module_set_sha256",
        "profile_sha256", "object_token", "limits", "parent_limits"))
    for key in ("attempt_id", "job_id", "object_token"):
        _uuid(data[key])
    for key in ("input_sha256", "request_sha256", "runtime_sha256", "module_set_sha256", "profile_sha256"):
        _digest(data[key])
    _digest(data["source_commit"], 40)
    lane = limits_for(data["method_id"])
    _limits(data["limits"], lane.method_id)
    _keys(data["parent_limits"], _PARENT_KEYS)
    values = tuple(_integer(data["parent_limits"][key]) for key in _PARENT_KEYS)
    _require(values == _LANES[lane.method_id][7:])


def _validate_control(data):
    _keys(data, ("schema", "attempt_id", "sequence", "action"))
    _uuid(data["attempt_id"])
    _integer(data["sequence"], 1, _U64)
    _choice(data["action"], ("heartbeat", "cancel"))


def _validate_sample(data):
    _keys(data, ("schema", "attempt_id", "object_token", "sequence", "platform", "monotonic_ns",
                 "query_duration_ns", "native", "cpu_ns", "active"))
    _uuid(data["attempt_id"])
    _uuid(data["object_token"])
    _integer(data["sequence"], 1, _U64)
    _platform(data["platform"])
    for key in ("monotonic_ns", "query_duration_ns", "cpu_ns"):
        _integer(data[key])
    _require(_native(data["native"], data["platform"]) == data["cpu_ns"], "accounting_counter_invalid")
    _active(data["active"], data["platform"])


def _validate_receipt(data):
    _keys(data, ("schema", "attempt_id", "job_id", "object_token", "platform", "binding", "verdict",
        "stop_reason", "limits", "final", "timing", "samples", "controller", "cleanup", "nonclaims"))
    for key in ("attempt_id", "job_id", "object_token"):
        _uuid(data[key])
    platform = _platform(data["platform"])
    _keys(data["binding"], ("input_sha256", "request_sha256", "source_commit", "runtime_sha256",
                            "module_set_sha256", "controller_sha256", "profile_sha256"))
    for key, value in data["binding"].items():
        _digest(value, 40 if key == "source_commit" else 64)
    _choice(data["verdict"], ("complete_within_budget", "failed_final_overbudget", "failed_control", "uncertain"))
    _choice(data["stop_reason"], _REASONS)
    _limits(data["limits"])
    final, timing = data["final"], data["timing"]
    _keys(final, ("status", "native", "cpu_ns", "empty_verified", "root_exit_code", "final_reads", "monotonic_ns"))
    _choice(final["status"], ("complete", "unavailable"))
    complete = final["status"] == "complete"
    _integer(final["final_reads"], high=3)
    _boolean(final["empty_verified"], complete)
    if complete:
        _require(final["final_reads"] == 3)
        _integer(final["cpu_ns"])
        _integer(final["monotonic_ns"])
        _exit(final["root_exit_code"], platform)
        _require(_native(final["native"], platform) == final["cpu_ns"], "accounting_counter_invalid")
        _require(data["verdict"] != "uncertain")
        over = final["cpu_ns"] > data["limits"]["cpu_ceiling_ns"]
        _require((data["verdict"] == "failed_final_overbudget") is over)
    else:
        _require(final["final_reads"] == 0 and data["verdict"] == "uncertain" and
                 data["stop_reason"] != "clean_exit")
        for key in ("native", "cpu_ns", "root_exit_code", "monotonic_ns"):
            _require(final[key] is None)
    time_keys = ("started_ns", "stopped_ns", "drained_ns", "finalized_ns",
                 "max_observe_gap_ns", "max_query_duration_ns", "kill_interval_ns")
    _keys(timing, time_keys + ("visibility_evidence_sha256",))
    for key in time_keys:
        if timing[key] is None:
            _require(not complete and key not in ("max_observe_gap_ns", "max_query_duration_ns"))
        else:
            _integer(timing[key])
    if complete:
        _require(timing["started_ns"] <= timing["stopped_ns"] <= timing["drained_ns"] <= timing["finalized_ns"])
        _require(timing["finalized_ns"] == final["monotonic_ns"])
    else:
        _require(timing["finalized_ns"] is None)
        known = [timing[key] for key in time_keys[:3] if timing[key] is not None]
        _require(all(known[i] <= known[i + 1] for i in range(len(known) - 1)))
    if timing["visibility_evidence_sha256"] is None:
        _require(not complete)
    else:
        _digest(timing["visibility_evidence_sha256"])
    _keys(data["samples"], ("sha256", "record_count", "byte_count"))
    _digest(data["samples"]["sha256"])
    _integer(data["samples"]["record_count"], high=_RECORDS)
    _integer(data["samples"]["byte_count"], high=_BYTES)
    _keys(data["controller"], ("cpu_ns", "wall_ns", "peak_private_bytes"))
    for value in data["controller"].values():
        _integer(value)
    if complete:
        _require(data["controller"]["wall_ns"] >= timing["finalized_ns"])
    _keys(data["cleanup"], ("object_drained", "object_released", "receipt_acknowledged", "filesystem_debt_resolved"))
    for key, value in data["cleanup"].items():
        _boolean(value, complete if key == "object_drained" else False)
    _keys(data["nonclaims"], ("production_approved", "physics_certified", "recovery_adapter_approved",
                              "hard_zero_overshoot_guaranteed"))
    for value in data["nonclaims"].values():
        _boolean(value, False)


def _validate_release(data):
    _keys(data, ("schema", "attempt_id", "object_token", "receipt_sha256", "object_released",
                 "controller_cpu_ns", "worker_cpu_ns", "parent_total_cpu_ns", "parent_budget_passed"))
    _uuid(data["attempt_id"])
    _uuid(data["object_token"])
    _digest(data["receipt_sha256"])
    _boolean(data["object_released"], True)
    _boolean(data["parent_budget_passed"], True)
    for key in ("controller_cpu_ns", "worker_cpu_ns", "parent_total_cpu_ns"):
        _integer(data[key])
    _require(_sum(data["controller_cpu_ns"], data["worker_cpu_ns"]) == data["parent_total_cpu_ns"],
             "accounting_release_invalid")


@_d.dataclass(frozen=True, slots=True)
class _FrozenFields:
    _items: tuple

    def __getattr__(self, name):
        for key, value in self._items:
            if key == name:
                return value
        raise AttributeError("Unknown frozen protocol field")


def _freeze(value):
    if type(value) is dict:
        return _FrozenFields(tuple((key, _freeze(value[key])) for key in sorted(value)))
    return value


@_d.dataclass(frozen=True, slots=True)
class StartRecord:
    schema: str
    attempt_id: str
    job_id: str
    method_id: str
    input_sha256: str
    request_sha256: str
    source_commit: str
    runtime_sha256: str
    module_set_sha256: str
    profile_sha256: str
    object_token: str
    limits: _FrozenFields
    parent_limits: _FrozenFields


@_d.dataclass(frozen=True, slots=True)
class ControlRecord:
    schema: str
    attempt_id: str
    sequence: int
    action: str


@_d.dataclass(frozen=True, slots=True)
class SampleRecord:
    schema: str
    attempt_id: str
    object_token: str
    sequence: int
    platform: str
    monotonic_ns: int
    query_duration_ns: int
    native: _FrozenFields
    cpu_ns: int
    active: _FrozenFields


@_d.dataclass(frozen=True, slots=True)
class ReceiptRecord:
    schema: str
    attempt_id: str
    job_id: str
    object_token: str
    platform: str
    binding: _FrozenFields
    verdict: str
    stop_reason: str
    limits: _FrozenFields
    final: _FrozenFields
    timing: _FrozenFields
    samples: _FrozenFields
    controller: _FrozenFields
    cleanup: _FrozenFields
    nonclaims: _FrozenFields


@_d.dataclass(frozen=True, slots=True)
class ReleaseRecord:
    schema: str
    attempt_id: str
    object_token: str
    receipt_sha256: str
    object_released: bool
    controller_cpu_ns: int
    worker_cpu_ns: int
    parent_total_cpu_ns: int
    parent_budget_passed: bool


_VALIDATORS = {RecordKind.START: _validate_start, RecordKind.CONTROL: _validate_control,
               RecordKind.SAMPLE: _validate_sample, RecordKind.RECEIPT: _validate_receipt,
               RecordKind.RELEASE: _validate_release}
_CLASSES = {RecordKind.START: StartRecord, RecordKind.CONTROL: ControlRecord,
            RecordKind.SAMPLE: SampleRecord, RecordKind.RECEIPT: ReceiptRecord,
            RecordKind.RELEASE: ReleaseRecord}


def _canonical_size(value):
    if type(value) is dict:
        return 2 + max(0, len(value) - 1) + sum(
            len(key) + 3 + _canonical_size(child) for key, child in value.items())
    if type(value) is str:
        return len(value) + 2
    if type(value) is bool:
        return 4 if value else 5
    if value is None:
        return 4
    return len(str(value))  # Only already validated bounded builtin integers.


def decode_record(kind, frame):
    _preflight(kind, frame)
    data = _decode_json(frame)
    _require(type(data) is dict)
    _schema(data, kind)
    _VALIDATORS[kind](data)
    _require(_canonical_size(data) <= _CAPS[kind], "accounting_bounds_exceeded")
    canonical = _json.dumps(data, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=True, allow_nan=False).encode("ascii")
    _require(canonical == frame)
    return _CLASSES[kind](**{key: _freeze(value) for key, value in data.items()})


_PHASES = ("PREPARED", "CONTAINMENT_ASSERTED", "RUNNING_ASSERTED", "STOP_REQUIRED",
           "STOP_ASSERTED", "DRAIN_ASSERTED", "FINAL_CHECKED", "RECEIPT_BOUND", "ACK_CHECKED", "FAILED_HELD")


@_d.dataclass(frozen=True, slots=True)
class ProtocolDecision:
    phase: str
    stop_required: bool
    computation_failed: bool
    reason_code: str

    def __post_init__(self):
        _choice(self.phase, _PHASES)
        _boolean(self.stop_required, self.phase in ("STOP_REQUIRED", "STOP_ASSERTED", "FAILED_HELD"))
        _boolean(self.computation_failed)
        _choice(self.reason_code, tuple(_MESSAGES) + ("protocol_consistent",))
        _require(not self.stop_required or self.computation_failed)
        _require(self.computation_failed is (self.reason_code != "protocol_consistent"))

    def __bool__(self):
        _fail()  # Explicit fields only, never default object truthiness as permission.


@_d.dataclass(frozen=True, slots=True)
class ProtocolEligibility:
    protocol_eligible: bool
    runtime_authorized: bool
    reason_code: str

    def __post_init__(self):
        _boolean(self.protocol_eligible)
        _boolean(self.runtime_authorized, False)
        _choice(self.reason_code, tuple(_MESSAGES) + ("protocol_consistent",))
        _require(self.protocol_eligible is (self.reason_code == "protocol_consistent"))

    def __bool__(self):
        _fail()  # A consistency record is not an implicit authorization boolean.


def _guard(method):
    """Internal fixed mutator wrapper, not an accepted caller hook."""
    def guarded(self, *args, **kwargs):
        error_code = None
        try:
            names = _MUTATOR_ARGUMENTS[method.__name__]
            _require(len(args) <= len(names) and len(args) + len(kwargs) == len(names))
            _require(all(type(key) is str and key in names[len(args):] for key in kwargs))
            result = method(self, *args, **kwargs)
        except ProtocolError as error:
            error_code = error.code
        if error_code is not None:
            self._hold(error_code)
            _fail(error_code)
        return result
    guarded.__name__ = method.__name__
    return guarded


_MUTATOR_ARGUMENTS = {
    "assert_contained": ("attempt_id", "object_token", "at_ns"),
    "assert_started": ("attempt_id", "object_token", "at_ns"),
    "consume_control": ("frame",), "consume_sample": ("frame",),
    "request_stop": ("reason", "at_ns"),
    "assert_drained": ("attempt_id", "object_token", "stopped_ns", "drained_ns", "empty_verified", "root_exit_code"),
    "consume_final_sample": ("frame",), "accept_receipt": ("frame",), "accept_release": ("frame",),
}


class ProtocolSession:
    """One deterministic asserted trace. No reset, clocks, I/O or admission."""

    __slots__ = ("_start", "_platform", "_controller_sha256", "_lane", "_phase", "_failed",
        "_held_error", "_outcome_error", "_overbudget", "_required_reason", "_stop_reason",
        "_contained", "_started", "_stopped", "_drained", "_root_exit", "_last_sample",
        "_final_samples", "_sample_sequence", "_control_sequence", "_record_count",
        "_byte_count", "_digest", "_max_gap", "_max_query", "_receipt", "_receipt_sha256")

    def __init__(self):
        _fail()

    @classmethod
    def from_start(cls, start_frame, platform, controller_sha256):
        _require(cls is ProtocolSession and type(platform) is Platform)
        _digest(controller_sha256)
        record = decode_record(RecordKind.START, start_frame)
        self = object.__new__(cls)
        self._start, self._platform, self._controller_sha256 = record, platform, controller_sha256
        self._lane = limits_for(record.method_id)
        self._phase, self._failed, self._overbudget = "PREPARED", False, False
        self._held_error = self._outcome_error = self._required_reason = self._stop_reason = None
        self._contained = self._started = self._stopped = self._drained = self._root_exit = None
        self._last_sample = self._receipt = self._receipt_sha256 = None
        self._final_samples = ()
        self._sample_sequence = self._control_sequence = self._record_count = self._byte_count = 0
        self._max_gap = self._max_query = 0
        self._digest = _hashlib.sha256()
        return self

    @property
    def phase(self):
        return self._phase

    def _hold(self, code):
        if self._held_error is None:
            self._held_error = safe_error(code)
        self._phase, self._failed = "FAILED_HELD", True

    def _fail_computation(self, code, reason=None):
        self._failed = True
        if self._outcome_error is None:
            self._outcome_error = safe_error(code)
        if reason is not None and self._required_reason is None:
            self._required_reason = reason

    def _reason_code(self):
        if self._held_error is not None:
            return self._held_error.code
        if self._overbudget:
            return "accounting_cpu_limit"
        if self._outcome_error is not None:
            return self._outcome_error.code
        return "protocol_consistent"

    def _decision(self):
        return ProtocolDecision(self._phase, self._phase in ("STOP_REQUIRED", "STOP_ASSERTED", "FAILED_HELD"),
                                self._failed, self._reason_code())

    def _phase_is(self, *allowed):
        _require(self._phase in allowed, "accounting_transition_invalid")

    def _attempt_identity(self, attempt_id):
        _uuid(attempt_id)
        _require(attempt_id == self._start.attempt_id, "accounting_identity_mismatch")
    def _identity(self, attempt_id, object_token):
        self._attempt_identity(attempt_id)
        _uuid(object_token)
        _require(object_token == self._start.object_token, "accounting_identity_mismatch")

    @_guard
    def assert_contained(self, attempt_id, object_token, at_ns):
        self._phase_is("PREPARED")
        self._identity(attempt_id, object_token)
        _integer(at_ns)
        self._contained, self._phase = at_ns, "CONTAINMENT_ASSERTED"
        return self._decision()

    @_guard
    def assert_started(self, attempt_id, object_token, at_ns):
        self._phase_is("CONTAINMENT_ASSERTED")
        self._identity(attempt_id, object_token)
        _integer(at_ns)
        _require(at_ns >= self._contained, "accounting_transition_invalid")
        self._started, self._phase = at_ns, "RUNNING_ASSERTED"
        return self._decision()

    def _next_sequence(self, supplied, previous):
        _require(previous < _U64, "accounting_transition_invalid")
        _require(supplied == previous + 1, "accounting_transition_invalid")

    @_guard
    def consume_control(self, frame):
        self._phase_is("RUNNING_ASSERTED", "STOP_REQUIRED", "STOP_ASSERTED")
        record = decode_record(RecordKind.CONTROL, frame)
        self._attempt_identity(record.attempt_id)
        self._next_sequence(record.sequence, self._control_sequence)
        if record.action == "cancel":
            self._phase_is("RUNNING_ASSERTED")
        self._control_sequence = record.sequence
        if record.action == "cancel":
            self._fail_computation("accounting_counter_invalid", "user_cancelled")
            self._phase = "STOP_REQUIRED"
        return self._decision()

    def _check_sample(self, record, frame):
        self._identity(record.attempt_id, record.object_token)
        _require(record.platform == self._platform.value, "accounting_counter_invalid")
        self._next_sequence(record.sequence, self._sample_sequence)
        previous = self._last_sample
        if previous is not None:
            _require(record.monotonic_ns > previous.monotonic_ns, "accounting_counter_invalid")
            for key, value in previous.native._items:
                _require(getattr(record.native, key) >= value, "accounting_counter_invalid")
            if self._platform is Platform.WINDOWS_JOB_X64_1:
                for key in ("total_processes", "limit_terminated_processes"):
                    _require(getattr(record.active, key) >= getattr(previous.active, key), "accounting_counter_invalid")
            else:
                for key in ("root_reaped", "adopted_reaped"):
                    _require(not getattr(previous.active, key) or getattr(record.active, key), "accounting_counter_invalid")
        _require(record.monotonic_ns >= self._started, "accounting_counter_invalid")
        _require(self._record_count < _RECORDS and self._byte_count <= _BYTES - (len(frame) + 1),
                 "accounting_bounds_exceeded")

    def _commit_sample(self, record, frame, running):
        digest = self._digest.copy()
        digest.update(frame)
        digest.update(b"\n")
        if running:
            previous = self._last_sample.monotonic_ns if self._last_sample is not None else self._started
            self._max_gap = max(self._max_gap, checked_delta_ns(record.monotonic_ns, previous))
        self._max_query = max(self._max_query, record.query_duration_ns)
        self._digest = digest
        self._record_count += 1
        self._byte_count += len(frame) + 1
        self._sample_sequence = record.sequence
        self._last_sample = record

    @_guard
    def consume_sample(self, frame):
        self._phase_is("RUNNING_ASSERTED", "STOP_REQUIRED", "STOP_ASSERTED")
        record = decode_record(RecordKind.SAMPLE, frame)
        self._check_sample(record, frame)
        previous = self._last_sample.monotonic_ns if self._last_sample is not None else self._started
        _require(record.monotonic_ns > previous, "accounting_counter_invalid")
        gap = checked_delta_ns(record.monotonic_ns, previous)
        self._commit_sample(record, frame, True)
        if record.cpu_ns > self._lane.cpu_ceiling_ns:
            self._overbudget = True
        if record.cpu_ns >= self._lane.cpu_stop_ns:
            self._fail_computation("accounting_cpu_limit", "cpu_limit")
        elif gap > _GAP or record.query_duration_ns > _GAP:
            self._fail_computation("accounting_observation_gap", "observe_gap")
        elif record.monotonic_ns > self._lane.wall_ns:
            self._fail_computation("accounting_counter_invalid", "wall_limit")
        if self._failed and self._phase == "RUNNING_ASSERTED":
            self._phase = "STOP_REQUIRED"
        return self._decision()

    @_guard
    def request_stop(self, reason, at_ns):
        self._phase_is("RUNNING_ASSERTED", "STOP_REQUIRED")
        _choice(reason, _REASONS[1:])
        _integer(at_ns)
        previous = self._last_sample.monotonic_ns if self._last_sample is not None else self._started
        _require(at_ns >= previous, "accounting_transition_invalid")
        if self._required_reason is not None:
            _require(reason == self._required_reason, "accounting_transition_invalid")
        code = {"cpu_limit": "accounting_cpu_limit", "observe_gap": "accounting_observation_gap"}.get(
            reason, "accounting_counter_invalid")
        self._fail_computation(code)
        self._stopped, self._stop_reason, self._phase = at_ns, reason, "STOP_ASSERTED"
        return self._decision()

    @_guard
    def assert_drained(self, attempt_id, object_token, stopped_ns, drained_ns, empty_verified, root_exit_code):
        self._phase_is("RUNNING_ASSERTED", "STOP_ASSERTED")
        self._identity(attempt_id, object_token)
        _integer(stopped_ns)
        _integer(drained_ns)
        _boolean(empty_verified, True)
        _exit(root_exit_code, self._platform.value)
        _require(self._started <= stopped_ns <= drained_ns, "accounting_transition_invalid")
        if self._last_sample is not None:
            _require(drained_ns >= self._last_sample.monotonic_ns, "accounting_transition_invalid")
        requested = self._phase == "STOP_ASSERTED"
        if requested:
            _require(stopped_ns == self._stopped, "accounting_transition_invalid")
        self._stopped, self._drained, self._root_exit = stopped_ns, drained_ns, root_exit_code
        self._phase = "DRAIN_ASSERTED"
        if root_exit_code != 0:
            self._fail_computation("accounting_counter_invalid")
        if requested and checked_delta_ns(drained_ns, stopped_ns) > _KILL:
            self._hold("accounting_termination_uncertain")
        return self._decision()

    @_guard
    def consume_final_sample(self, frame):
        self._phase_is("DRAIN_ASSERTED")
        record = decode_record(RecordKind.SAMPLE, frame)
        self._check_sample(record, frame)
        _require(record.monotonic_ns >= self._drained, "accounting_counter_invalid")
        if self._platform is Platform.WINDOWS_JOB_X64_1:
            empty = record.active.active_processes == 0
        else:
            empty = record.active.populated == 0 and record.active.root_reaped and record.active.adopted_reaped
        _require(empty, "accounting_counter_invalid")
        if self._final_samples:
            _require(record.native == self._final_samples[0].native, "accounting_counter_invalid")
        spacing_bad = bool(self._final_samples) and checked_delta_ns(
            record.monotonic_ns, self._final_samples[-1].monotonic_ns) < _GAP
        timing_bad = (spacing_bad or record.query_duration_ns > _GAP or
                      checked_delta_ns(record.monotonic_ns, self._drained) > _DRAIN)
        wall_bad = record.monotonic_ns > self._lane.wall_ns
        self._commit_sample(record, frame, False)
        if record.cpu_ns > self._lane.cpu_ceiling_ns:
            self._overbudget = True
            self._fail_computation("accounting_cpu_limit")
        if timing_bad or wall_bad:
            self._hold("accounting_observation_gap" if timing_bad else "accounting_counter_invalid")
        else:
            self._final_samples += (record,)
            if len(self._final_samples) == 3:
                self._phase = "FINAL_CHECKED"
        return self._decision()

    def _receipt_identity(self, record):
        self._identity(record.attempt_id, record.object_token)
        _require(record.job_id == self._start.job_id and record.platform == self._platform.value,
                 "accounting_identity_mismatch")
        for key, value in record.binding._items:
            expected = self._controller_sha256 if key == "controller_sha256" else getattr(self._start, key)
            _require(value == expected, "accounting_identity_mismatch")
        _require(record.limits == self._start.limits)
        _require(record.samples.record_count == self._record_count and
                 record.samples.byte_count == self._byte_count and
                 record.samples.sha256 == self._digest.hexdigest(), "accounting_counter_invalid")

    def _timing_matches(self, timing, finalized):
        expected = (self._started, self._stopped, self._drained, finalized,
                    self._max_gap, self._max_query,
                    None if self._drained is None else checked_delta_ns(self._drained, self._stopped)
                    if self._stop_reason is not None else 0)
        keys = ("started_ns", "stopped_ns", "drained_ns", "finalized_ns",
                "max_observe_gap_ns", "max_query_duration_ns", "kill_interval_ns")
        _require(all(getattr(timing, key) == value for key, value in zip(keys, expected)),
                 "accounting_counter_invalid")

    def _unavailable_reason(self):
        if self._stop_reason is not None:
            return self._stop_reason
        if self._held_error is not None:
            return {"accounting_counter_invalid": "counter_invalid",
                    "accounting_counter_overflow": "counter_invalid",
                    "accounting_counter_underflow": "counter_invalid",
                    "accounting_integer_invalid": "counter_invalid",
                    "accounting_identity_mismatch": "identity_changed",
                    "accounting_observation_gap": "observe_gap"}.get(self._held_error.code, "receipt_lost")
        return "receipt_lost"

    @_guard
    def accept_receipt(self, frame):
        record = decode_record(RecordKind.RECEIPT, frame)
        _require(self._receipt is None, "accounting_transition_invalid")
        self._receipt_identity(record)
        if record.final.status == "unavailable":
            self._timing_matches(record.timing, None)
            _require(record.stop_reason == self._unavailable_reason())
            self._receipt, self._receipt_sha256 = record, _hashlib.sha256(frame).hexdigest()
            self._hold("accounting_receipt_unavailable")
            return self._decision()
        self._phase_is("FINAL_CHECKED")
        last = self._final_samples[-1]
        _require(record.final.native == last.native and record.final.cpu_ns == last.cpu_ns and
                 record.final.root_exit_code == self._root_exit and record.final.monotonic_ns == last.monotonic_ns,
                 "accounting_counter_invalid")
        self._timing_matches(record.timing, last.monotonic_ns)
        reason = self._stop_reason or "clean_exit"
        _require(record.stop_reason == reason)
        parent_failed = (record.controller.cpu_ns > self._lane.parent_cpu_ceiling_ns or
                         record.controller.peak_private_bytes > 67108864 or
                         record.controller.wall_ns > self._lane.wall_ns)
        verdict = ("failed_final_overbudget" if last.cpu_ns > self._lane.cpu_ceiling_ns
                   else "failed_control" if self._failed or parent_failed else "complete_within_budget")
        _require(record.verdict == verdict)
        self._receipt, self._receipt_sha256 = record, _hashlib.sha256(frame).hexdigest()
        if parent_failed:
            self._fail_computation("accounting_parent_limit")
        self._phase = "RECEIPT_BOUND"
        return self._decision()

    @_guard
    def accept_release(self, frame):
        self._phase_is("RECEIPT_BOUND")
        record = decode_record(RecordKind.RELEASE, frame)
        self._identity(record.attempt_id, record.object_token)
        _require(record.receipt_sha256 == self._receipt_sha256 and
                 self._receipt.controller.cpu_ns <= record.parent_total_cpu_ns <= self._lane.parent_cpu_ceiling_ns,
                 "accounting_release_invalid")
        self._phase = "ACK_CHECKED"
        return self._decision()

    def eligibility(self):
        if self._phase == "ACK_CHECKED" and not self._failed:
            return ProtocolEligibility(True, False, "protocol_consistent")
        code = self._reason_code()
        if code == "protocol_consistent":
            code = "accounting_release_invalid" if self._phase == "RECEIPT_BOUND" else "accounting_receipt_unavailable"
        return ProtocolEligibility(False, False, code)
