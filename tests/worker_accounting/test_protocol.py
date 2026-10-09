"""Synthetic supplied-stream tests only; no OS, clocks, source or file measurements."""

import dataclasses
import hashlib
import json

import pytest

from scripts import physical_accounting_protocol as p


ATTEMPT = "11111111-1111-4111-8111-111111111111"
JOB = "22222222-2222-4222-8222-222222222222"
TOKEN = "33333333-3333-4333-8333-333333333333"
OTHER = "44444444-4444-4444-8444-444444444444"
I64 = 9223372036854775807
U64 = 18446744073709551615
CORRECTION = "gravity.station-corrections/v1"
TRANSFORM = "gravity.equivalent-source-transform/v1"
WINDOWS = "windows-job-x64-1"
LINUX = "linux-cgroup2-x64-1"
NS20 = 20000000
LIMIT_NAMES = ("cpu_ceiling_ns", "cpu_stop_ns", "cpu_margin_ns", "wall_ns",
               "rss_bytes", "scratch_bytes", "result_bytes")
LANES = {
    CORRECTION: (60000000000, 57000000000, 3000000000, 120000000000,
                 805306368, 268435456, 67108864),
    TRANSFORM: (240000000000, 237000000000, 3000000000, 300000000000,
                1610612736, 536870912, 67108864),
}
ERRORS = {
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


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def start(method=CORRECTION):
    return dict(schema="physical-accounting-start-1", attempt_id=ATTEMPT,
                job_id=JOB, method_id=method, input_sha256="1" * 64,
                request_sha256="2" * 64, source_commit="3" * 40,
                runtime_sha256="4" * 64, module_set_sha256="5" * 64,
                profile_sha256="6" * 64, object_token=TOKEN,
                limits=dict(zip(LIMIT_NAMES, LANES[method])),
                parent_limits=dict(cpu_ceiling_ns=5000000000 if method == CORRECTION
                                   else 10000000000, control_bytes=16384,
                                   receipt_bytes=65536, stdout_bytes=65536,
                                   stderr_bytes=65536))


def control(sequence=1, action="heartbeat"):
    return dict(schema="physical-accounting-control-1", attempt_id=ATTEMPT,
                sequence=sequence, action=action)


def sample(platform=WINDOWS, sequence=1, at=10000000, cpu=1000, empty=False):
    # Independent literal-unit fixture construction, not converter-under-test.
    if platform == WINDOWS:
        assert cpu % 100 == 0
        native = dict(total_user_ticks=cpu // 100, total_kernel_ticks=0)
        active = dict(active_processes=0 if empty else 1,
                      total_processes=1, limit_terminated_processes=0)
    else:
        assert cpu % 1000 == 0
        native = dict(usage_usec=cpu // 1000, user_usec=cpu // 1000, system_usec=0)
        active = dict(populated=0 if empty else 1, root_reaped=empty,
                      adopted_reaped=empty)
    return dict(schema="physical-accounting-sample-1", attempt_id=ATTEMPT,
                object_token=TOKEN, sequence=sequence, platform=platform,
                monotonic_ns=at, query_duration_ns=100, native=native,
                cpu_ns=cpu, active=active)


class Trace:
    """Test-only bounded in-memory producer; assertions are NOT actual OS facts."""

    def __init__(self, platform=WINDOWS, method=CORRECTION, started=0):
        self.platform = platform
        self.start = start(method)
        enum = p.Platform.WINDOWS_JOB_X64_1 if platform == WINDOWS else p.Platform.LINUX_CGROUP2_X64_1
        self.session = p.ProtocolSession.from_start(encoded(self.start), enum, "7" * 64)
        self.session.assert_contained(ATTEMPT, TOKEN, 0)
        self.session.assert_started(ATTEMPT, TOKEN, started)
        self.started = started
        self.stopped = None
        self.drained = None
        self.root_exit = 0
        self.reason = "clean_exit"
        self.frames = []
        self.records = []
        self.max_gap = 0
        self.max_query = 0
        self.final = []
        self.requested = False

    def observe(self, record, final=False):
        raw = encoded(record)
        if final:
            decision = self.session.consume_final_sample(raw)
            self.final.append(record)
        else:
            decision = self.session.consume_sample(raw)
            previous = self.records[-1]["monotonic_ns"] if self.records else self.started
            self.max_gap = max(self.max_gap, record["monotonic_ns"] - previous)
        self.max_query = max(self.max_query, record["query_duration_ns"])
        self.frames.append(raw)
        self.records.append(record)
        return decision

    def stop(self, reason, at):
        decision = self.session.request_stop(reason, at)
        self.reason, self.stopped, self.requested = reason, at, True
        return decision

    def drain(self, stopped=10000000, drained=20000000, exit_code=0):
        self.session.assert_drained(ATTEMPT, TOKEN, stopped, drained, True, exit_code)
        self.stopped, self.drained, self.root_exit = stopped, drained, exit_code

    def finish(self, cpu=1000, running=True, exit_code=0):
        if running:
            self.observe(sample(self.platform, cpu=cpu))
        self.drain(exit_code=exit_code)
        for at in (30000000, 50000000, 70000000):
            self.observe(sample(self.platform, len(self.frames) + 1, at, cpu, True), final=True)
        return self.receipt()

    def receipt(self, unavailable=False):
        binding = {key: self.start[key] for key in ("input_sha256", "request_sha256",
                   "source_commit", "runtime_sha256", "module_set_sha256", "profile_sha256")}
        binding["controller_sha256"] = "7" * 64
        if unavailable:
            final = dict(status="unavailable", native=None, cpu_ns=None,
                         empty_verified=False, root_exit_code=None, final_reads=0,
                         monotonic_ns=None)
            verdict, reason, finalized = "uncertain", "receipt_lost", None
        else:
            last = self.final[-1]
            final = dict(status="complete", native=last["native"].copy(),
                         cpu_ns=last["cpu_ns"], empty_verified=True,
                         root_exit_code=self.root_exit, final_reads=3,
                         monotonic_ns=last["monotonic_ns"])
            verdict = ("failed_final_overbudget" if final["cpu_ns"] > self.start["limits"]["cpu_ceiling_ns"]
                       else "failed_control" if self.requested or self.root_exit != 0
                       else "complete_within_budget")
            reason, finalized = self.reason, last["monotonic_ns"]
        digest = hashlib.sha256(b"".join(raw + b"\n" for raw in self.frames)).hexdigest()
        return dict(schema="physical-accounting-receipt-1", attempt_id=ATTEMPT, job_id=JOB,
                    object_token=TOKEN, platform=self.platform, binding=binding,
                    verdict=verdict, stop_reason=reason, limits=self.start["limits"].copy(),
                    final=final, timing=dict(started_ns=self.started, stopped_ns=self.stopped,
                    drained_ns=self.drained, finalized_ns=finalized,
                    max_observe_gap_ns=self.max_gap, max_query_duration_ns=self.max_query,
                    kill_interval_ns=(self.drained - self.stopped if self.requested else 0)
                    if self.drained is not None else None,
                    visibility_evidence_sha256=None if unavailable else "8" * 64),
                    samples=dict(sha256=digest, record_count=len(self.frames),
                                 byte_count=sum(len(raw) + 1 for raw in self.frames)),
                    controller=dict(cpu_ns=100, wall_ns=finalized or 0, peak_private_bytes=100),
                    cleanup=dict(object_drained=not unavailable, object_released=False,
                                 receipt_acknowledged=False, filesystem_debt_resolved=False),
                    nonclaims=dict(production_approved=False, physics_certified=False,
                                   recovery_adapter_approved=False, hard_zero_overshoot_guaranteed=False))


def release(receipt):
    return dict(schema="physical-accounting-release-1", attempt_id=ATTEMPT,
                object_token=TOKEN, receipt_sha256=hashlib.sha256(encoded(receipt)).hexdigest(),
                object_released=True, controller_cpu_ns=100, worker_cpu_ns=100,
                parent_total_cpu_ns=200, parent_budget_passed=True)


def rejected(call, code=None):
    with pytest.raises(p.ProtocolError) as caught:
        call()
    if code:
        assert caught.value.code == code
    assert caught.value.message == ERRORS[caught.value.code]
    return caught.value


@pytest.mark.parametrize("platform", [WINDOWS, LINUX])
@pytest.mark.parametrize("method", [CORRECTION, TRANSFORM])
def test_pure_boundary_and_no_authority(platform, method):
    trace = Trace(platform, method)
    assert trace.session.eligibility().runtime_authorized is False
    receipt = trace.finish()
    trace.session.accept_receipt(encoded(receipt))
    assert not trace.session.eligibility().protocol_eligible
    trace.session.accept_release(encoded(release(receipt)))
    verdict = trace.session.eligibility()
    assert verdict == p.ProtocolEligibility(True, False, "protocol_consistent")
    with pytest.raises(dataclasses.FrozenInstanceError):
        verdict.runtime_authorized = True
    with pytest.raises(AttributeError):
        trace.session.phase = "ACK_CHECKED"
    assert not hasattr(trace.session, "activate_profile")
    assert not hasattr(trace.session, "reset")


BOUNDED_BAD = [
    b'{"x":' * 6 + b'{}' + b'}' * 6,
    encoded({"x" * 65: 0}), encoded({"x": "v" * 129}),
    encoded({str(n): 0 for n in range(33)}),
    encoded({str(n): {str(k): 0 for k in range(31)} for n in range(4)}),
    b'{"x":123456789012345678901}',
]


@pytest.mark.parametrize("bad", BOUNDED_BAD)
def test_bounds_precede_decode_and_conversion(monkeypatch, bad):
    def forbidden(*args, **kwargs):
        raise AssertionError("Tree/int allocation reached before preflight")
    monkeypatch.setattr(p, "_decode_json", forbidden)
    monkeypatch.setattr(p, "_parse_int", forbidden)
    rejected(lambda: p.decode_record(p.RecordKind.START, bad), "accounting_bounds_exceeded")


@pytest.mark.parametrize("kind,cap", [("START", 16384), ("CONTROL", 1024),
                                     ("SAMPLE", 4096), ("RECEIPT", 16384), ("RELEASE", 4096)])
def test_bounds_precede_decode_and_conversion_ingress(monkeypatch, kind, cap):
    enum = getattr(p.RecordKind, kind)
    for size in (cap - 1, cap):
        p._preflight(enum, b'{}' + b' ' * (size - 2))
    def forbidden(*args, **kwargs):
        raise AssertionError("Oversize tree reached")
    monkeypatch.setattr(p, "_decode_json", forbidden)
    rejected(lambda: p.decode_record(enum, b'{}' + b' ' * (cap - 1)),
             "accounting_bounds_exceeded")
    for value in (bytearray(b'{}'), memoryview(b'{}'), '{}', None):
        rejected(lambda: p.decode_record(enum, value), "accounting_protocol_invalid")


@pytest.mark.parametrize("raw", [b'{"x":' * 5 + b'{}' + b'}' * 5,
                                encoded({"x" * 64: 0}), encoded({"x": "v" * 128}),
                                encoded({str(n): 0 for n in range(32)}),
                                encoded({str(n): {str(k): 0 for k in range(31 if n < 3 else 30)}
                                         for n in range(4)}),
                                b'{"x":18446744073709551615}', b'{"x":-2147483648}'])
def test_bounds_precede_decode_and_conversion_lexical_boundary(raw):
    p._preflight(p.RecordKind.START, raw)


@pytest.mark.parametrize("raw", [b'[]', b'{', b'{"x":}', b'{"x":1,}',
    b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1.0}',
    b'{"x":1e2}', b'{"x":+1}', b'{"x":01}', b'{"x":-0}', b'{"x":"\\u0061"}',
    b'{"x":"\\n"}', b'{"x":"\x7f"}', b'{"x":"\xc3\xa9"}', b'\xef\xbb\xbf{}',
    b'{"x":18446744073709551616}', b'{"x":-2147483649}'])
def test_strict_shapes_and_canonical_records(raw):
    rejected(lambda: p.decode_record(p.RecordKind.START, raw))


@pytest.mark.parametrize("which", ["start", "control", "sample", "receipt", "release"])
def test_strict_shapes_and_canonical_records_all_keys(which):
    trace = Trace()
    receipt = trace.finish()
    record, kind = {"start": (start(), p.RecordKind.START),
                    "control": (control(), p.RecordKind.CONTROL),
                    "sample": (sample(), p.RecordKind.SAMPLE),
                    "receipt": (receipt, p.RecordKind.RECEIPT),
                    "release": (release(receipt), p.RecordKind.RELEASE)}[which]
    assert dataclasses.is_dataclass(p.decode_record(kind, encoded(record)))
    for key in record:
        missing = record.copy()
        del missing[key]
        rejected(lambda: p.decode_record(kind, encoded(missing)))
    for bad in (dict(record, unknown=0), dict(record, schema="future-1")):
        rejected(lambda: p.decode_record(kind, encoded(bad)))
    for raw in (encoded(record) + b'\n', b' ' + encoded(record),
                json.dumps(record).encode("ascii")):
        rejected(lambda: p.decode_record(kind, raw), "accounting_protocol_invalid")
    for key, nested in record.items():
        if type(nested) is dict:
            for subkey in nested:
                bad = {**record, key: {**nested, subkey: None}}
                # Legitimate null only in unavailable, absent from these complete fixtures.
                rejected(lambda: p.decode_record(kind, encoded(bad)))
            rejected(lambda: p.decode_record(kind, encoded({**record, key: {**nested, "unknown": 0}})))


@pytest.mark.parametrize("args,expected", [((0, 0), 0), ((1, 2), 300), ((10, 0), 1000),
    ((92233720368547758, 0), 9223372036854775800),
    ((92233720368547758, 1), "accounting_counter_overflow"),
    ((I64, 0), "accounting_counter_overflow"), ((I64, 1), "accounting_counter_overflow")])
def test_golden_units_and_native_maxima(args, expected):
    if type(expected) is str:
        rejected(lambda: p.windows_cpu_ns(*args), expected)
    else:
        assert p.windows_cpu_ns(*args) == expected


@pytest.mark.parametrize("args,expected", [((0, 0, 0), 0), ((1, 0, 0), 1000),
    ((8, 3, 4), 8000), ((2, 3, 4), 7000),
    ((9223372036854775, 0, 0), 9223372036854775000),
    ((9223372036854776, 0, 0), "accounting_counter_overflow"),
    ((0, U64, 1), "accounting_counter_overflow"),
    ((U64 + 1, 0, 0), "accounting_integer_invalid")])
def test_golden_units_and_native_maxima_linux(args, expected):
    if type(expected) is str:
        rejected(lambda: p.linux_cpu_ns(*args), expected)
    else:
        assert p.linux_cpu_ns(*args) == expected


@pytest.mark.parametrize("bad", [True, False, 1.0, "1", None, -1, I64 + 1])
def test_regression_overflow_underflow_and_bool(bad):
    for position in (0, 1):
        args = [0, 0]
        args[position] = bad
        rejected(lambda: p.windows_cpu_ns(*args), "accounting_integer_invalid")
        rejected(lambda: p.checked_delta_ns(*args), "accounting_integer_invalid")
    assert p.checked_delta_ns(0, 0) == 0
    assert p.checked_delta_ns(I64, 0) == I64
    rejected(lambda: p.checked_delta_ns(0, 1), "accounting_counter_underflow")
    class IntegerSubclass(int):
        pass
    rejected(lambda: p.windows_cpu_ns(IntegerSubclass(1), 0), "accounting_integer_invalid")
    for position in range(3):
        args = [0, 0, 0]
        args[position] = bad if bad != I64 + 1 else U64 + 1
        rejected(lambda: p.linux_cpu_ns(*args), "accounting_integer_invalid")


@pytest.mark.parametrize("platform", [WINDOWS, LINUX])
def test_regression_overflow_underflow_and_bool_component(platform):
    trace = Trace(platform)
    first = sample(platform, cpu=10000)
    trace.observe(first)
    later = sample(platform, 2, NS20, 20000)
    if platform == WINDOWS:
        later["native"] = dict(total_user_ticks=99, total_kernel_ticks=101)
    else:
        later["native"] = dict(usage_usec=20, user_usec=9, system_usec=11)
    before = (trace.session._record_count, trace.session._byte_count)
    rejected(lambda: trace.session.consume_sample(encoded(later)), "accounting_counter_invalid")
    assert before == (trace.session._record_count, trace.session._byte_count)
    assert trace.session.phase == "FAILED_HELD"


@pytest.mark.parametrize("method", [CORRECTION, TRANSFORM])
def test_exact_lane_limits_and_no_override(method):
    limits = p.limits_for(method)
    assert tuple(getattr(limits, key) for key in LIMIT_NAMES) == LANES[method]
    assert limits.parent_cpu_ceiling_ns == (5000000000 if method == CORRECTION else 10000000000)
    with pytest.raises(dataclasses.FrozenInstanceError):
        limits.cpu_ceiling_ns += 1
    for section in ("limits", "parent_limits"):
        for key in start(method)[section]:
            for delta in (-1, 1):
                record = start(method)
                record[section][key] += delta
                rejected(lambda: p.decode_record(p.RecordKind.START, encoded(record)))
    for unknown in ("gravity.station-corrections/v2", "mt.screen/v1", "", None, True):
        rejected(lambda: p.limits_for(unknown))


@pytest.mark.parametrize("bad_event", ["before_containment", "identity", "sample_skip", "control_skip",
                                     "sample_replay", "control_replay", "platform", "early_release",
                                     "premature_final", "cancel_twice", "wrong_stop"])
def test_transition_identity_and_replay(bad_event):
    trace = Trace()
    s = trace.session
    if bad_event == "before_containment":
        s = p.ProtocolSession.from_start(encoded(start()), p.Platform.WINDOWS_JOB_X64_1, "7" * 64)
        call = lambda: s.assert_started(ATTEMPT, TOKEN, 0)
    elif bad_event == "identity":
        call = lambda: s.assert_drained(OTHER, TOKEN, 1, 2, True, 0)
    elif bad_event == "sample_skip":
        call = lambda: s.consume_sample(encoded(sample(sequence=2)))
    elif bad_event == "control_skip":
        call = lambda: s.consume_control(encoded(control(sequence=2)))
    elif bad_event == "sample_replay":
        trace.observe(sample())
        call = lambda: s.consume_sample(encoded(sample()))
    elif bad_event == "control_replay":
        s.consume_control(encoded(control()))
        call = lambda: s.consume_control(encoded(control()))
    elif bad_event == "platform":
        call = lambda: s.consume_sample(encoded(sample(LINUX)))
    elif bad_event == "early_release":
        call = lambda: s.accept_release(encoded(release(Trace().finish())))
    elif bad_event == "premature_final":
        call = lambda: s.consume_final_sample(encoded(sample(empty=True)))
    elif bad_event == "cancel_twice":
        s.consume_control(encoded(control(action="cancel")))
        call = lambda: s.consume_control(encoded(control(2, "cancel")))
    else:
        s.consume_control(encoded(control(action="cancel")))
        call = lambda: s.request_stop("cpu_limit", 1)
    error = rejected(call)
    assert s.phase == "FAILED_HELD"
    before = s.eligibility()
    rejected(lambda: s.assert_contained(ATTEMPT, TOKEN, 0))
    assert s.eligibility() == before
    assert before.reason_code == error.code and not before.protocol_eligible
    assert before.runtime_authorized is False


@pytest.mark.parametrize("bad", ["spacing", "deadline", "query", "unequal", "nonempty", "before_drain",
                                "record_cap", "byte_cap"])
def test_bounded_trace_and_final_consistency(bad):
    trace = Trace()
    trace.observe(sample())
    trace.drain()
    trace.observe(sample(sequence=2, at=30000000, empty=True), final=True)
    record = sample(sequence=3, at=50000000, empty=True)
    if bad == "spacing":
        record["monotonic_ns"] -= 1
    elif bad == "deadline":
        record["monotonic_ns"] = 2020000001
    elif bad == "query":
        record["query_duration_ns"] = NS20 + 1
    elif bad == "unequal":
        record = sample(sequence=3, at=50000000, cpu=1100, empty=True)
    elif bad == "nonempty":
        record["active"]["active_processes"] = 1
    elif bad == "before_drain":
        record["monotonic_ns"] = 19999999
    elif bad == "record_cap":
        trace.session._record_count = 32768
    else:
        trace.session._byte_count = 16777216
    before = (trace.session._record_count, trace.session._byte_count)
    if bad in ("spacing", "deadline", "query"):
        trace.session.consume_final_sample(encoded(record))
        assert trace.session._record_count == before[0] + 1  # diagnostic preserved
    else:
        rejected(lambda: trace.session.consume_final_sample(encoded(record)))
        assert (trace.session._record_count, trace.session._byte_count) == before
    assert trace.session.phase == "FAILED_HELD"
    assert not trace.session.eligibility().protocol_eligible


@pytest.mark.parametrize("platform", [WINDOWS, LINUX])
def test_bounded_trace_and_final_consistency_digest(platform):
    trace = Trace(platform)
    receipt = trace.finish(cpu=0)
    assert trace.session._record_count == 4
    assert len(trace.session._final_samples) == 3
    assert trace.session._digest.hexdigest() == receipt["samples"]["sha256"]
    trace.session.accept_receipt(encoded(receipt))
    assert trace.session.phase == "RECEIPT_BOUND"
    # There is no full trace retained by the implementation; fixtures above are test-only.
    assert not hasattr(trace.session, "_frames")


@pytest.mark.parametrize("changed", [None, "native", "cpu_ns", "root_exit_code", "monotonic_ns",
                                    "empty_verified", "final_reads", "verdict", "cleanup", "finalized"])
def test_unavailable_is_not_final_zero(changed):
    trace = Trace()
    receipt = trace.receipt(unavailable=True)
    if changed in ("native", "cpu_ns", "root_exit_code", "monotonic_ns"):
        receipt["final"][changed] = {} if changed == "native" else 0
    elif changed == "empty_verified":
        receipt["final"][changed] = True
    elif changed == "final_reads":
        receipt["final"][changed] = False
    elif changed == "verdict":
        receipt[changed] = "complete_within_budget"
    elif changed == "cleanup":
        receipt[changed]["object_drained"] = True
    elif changed == "finalized":
        receipt["timing"]["finalized_ns"] = 0
    if changed is not None:
        rejected(lambda: trace.session.accept_receipt(encoded(receipt)))
    else:
        parsed = p.decode_record(p.RecordKind.RECEIPT, encoded(receipt))
        assert parsed.final.cpu_ns is None and parsed.final.native is None
        trace.session.accept_receipt(encoded(receipt))
    assert trace.session.phase == "FAILED_HELD"
    rejected(lambda: trace.session.accept_release(encoded(release(receipt))))
    assert not trace.session.eligibility().protocol_eligible


@pytest.mark.parametrize("method", [CORRECTION, TRANSFORM])
@pytest.mark.parametrize("platform", [WINDOWS, LINUX])
@pytest.mark.parametrize("offset", [0, 1])
def test_receipt_release_and_eligibility(method, platform, offset):
    trace = Trace(platform, method)
    step = 100 if platform == WINDOWS else 1000
    # Threshold is not observed while running: final-only B may be consistent.
    receipt = trace.finish(cpu=LANES[method][0] + offset * step, running=False)
    trace.session.accept_receipt(encoded(receipt))
    trace.session.accept_release(encoded(release(receipt)))
    verdict = trace.session.eligibility()
    assert verdict.protocol_eligible is (offset == 0)
    assert verdict.runtime_authorized is False
    assert receipt["verdict"] == ("failed_final_overbudget" if offset else "complete_within_budget")
    assert receipt["cleanup"]["receipt_acknowledged"] is False


@pytest.mark.parametrize("bad", ["hash", "identity", "released", "passed", "sum", "overflow",
                                "budget", "preliminary", "integer_bool"])
def test_receipt_release_and_eligibility_bad_ack(bad):
    trace = Trace()
    receipt = trace.finish()
    trace.session.accept_receipt(encoded(receipt))
    ack = release(receipt)
    if bad == "hash":
        ack["receipt_sha256"] = "a" * 64
    elif bad == "identity":
        ack["object_token"] = OTHER
    elif bad == "released":
        ack["object_released"] = False
    elif bad == "passed":
        ack["parent_budget_passed"] = False
    elif bad == "sum":
        ack["parent_total_cpu_ns"] += 1
    elif bad == "overflow":
        ack["controller_cpu_ns"], ack["worker_cpu_ns"] = I64, 1
    elif bad == "budget":
        ack.update(controller_cpu_ns=5000000000, worker_cpu_ns=1, parent_total_cpu_ns=5000000001)
    elif bad == "preliminary":
        ack.update(controller_cpu_ns=0, worker_cpu_ns=0, parent_total_cpu_ns=0)
    else:
        ack["worker_cpu_ns"] = True
    rejected(lambda: trace.session.accept_release(encoded(ack)))
    assert trace.session.phase == "FAILED_HELD"
    assert not trace.session.eligibility().protocol_eligible


@pytest.mark.parametrize("stop", ["user_cancelled", "cpu_limit", "observe_gap", "wall_limit"])
def test_receipt_release_and_eligibility_stop_is_sticky(stop):
    trace = Trace()
    trace.observe(sample())
    trace.stop(stop, 11000000)
    trace.drain(11000000, 20000000)
    for at in (30000000, 50000000, 70000000):
        trace.observe(sample(sequence=len(trace.frames) + 1, at=at, empty=True), final=True)
    receipt = trace.receipt()
    trace.session.accept_receipt(encoded(receipt))
    trace.session.accept_release(encoded(release(receipt)))
    assert not trace.session.eligibility().protocol_eligible


@pytest.mark.parametrize("code,message", list(ERRORS.items()))
def test_safe_errors_and_forged_authority(code, message):
    error = p.safe_error(code)
    assert error == p.SafeError(code, message, False)
    assert len(error.code.encode("ascii")) <= 48
    assert len(error.message.encode("ascii")) <= 96
    with pytest.raises(dataclasses.FrozenInstanceError):
        error.retryable = True
    assert p.safe_error("private-attacker-secret").code == "accounting_protocol_invalid"
    malformed = rejected(lambda: p.decode_record(p.RecordKind.START, b'{"private-secret":}'))
    assert "private-secret" not in str(malformed)
    assert malformed.__cause__ is None and malformed.__context__ is None
    assert not hasattr(malformed, "doc")


@pytest.mark.parametrize("nonclaim", ["production_approved", "physics_certified",
                                    "recovery_adapter_approved", "hard_zero_overshoot_guaranteed"])
def test_safe_errors_and_forged_authority_nonclaims(nonclaim):
    trace = Trace()
    receipt = trace.finish()
    receipt["nonclaims"][nonclaim] = True
    rejected(lambda: trace.session.accept_receipt(encoded(receipt)))
    assert not trace.session.eligibility().protocol_eligible
    assert trace.session.eligibility().runtime_authorized is False


def test_public_surface_and_exports():
    expected = {"RecordKind", "Platform", "LaneLimits", "SafeError", "ProtocolError",
                "ProtocolDecision", "ProtocolEligibility", "ProtocolSession", "StartRecord",
                "ControlRecord", "SampleRecord", "ReceiptRecord", "ReleaseRecord", "limits_for",
                "decode_record", "windows_cpu_ns", "linux_cpu_ns", "checked_delta_ns", "safe_error"}
    assert set(p.__all__) == expected
    assert {n for n in vars(p) if not n.startswith("_")} == expected
    assert {v.name for v in p.RecordKind} == {"START", "CONTROL", "SAMPLE", "RECEIPT", "RELEASE"}
    assert {v.value for v in p.Platform} == {WINDOWS, LINUX}
    for name in ("main", "run", "launch", "activate_profile", "measure", "open", "os", "time"):
        assert not hasattr(p, name)
    for value in ("windows-job-x64-1", None, True):
        rejected(lambda: p.ProtocolSession.from_start(encoded(start()), value, "7" * 64))
    rejected(lambda: p.decode_record("START", encoded(start())))
    class Hostile:
        def __str__(self):
            raise AssertionError("Coercion hook called")
        def __int__(self):
            raise AssertionError("Integer hook called")
    rejected(lambda: p.limits_for(Hostile()))
    rejected(lambda: p.windows_cpu_ns(Hostile(), 0))
    rejected(lambda: p.decode_record(p.RecordKind.START, Hostile()))


@pytest.mark.parametrize("bad", [None, True, 0, "", OTHER,
                                "00000000-0000-0000-0000-000000000000"])
@pytest.mark.parametrize("method", ["assert_contained", "assert_started", "assert_drained"])
def test_transition_identity_and_replay_explicit_token(method, bad):
    s = p.ProtocolSession.from_start(encoded(start()), p.Platform.WINDOWS_JOB_X64_1, "7" * 64)
    if method != "assert_contained":
        s.assert_contained(ATTEMPT, TOKEN, 0)
    if method == "assert_drained":
        s.assert_started(ATTEMPT, TOKEN, 0)
        call = lambda: s.assert_drained(ATTEMPT, bad, 0, 0, True, 0)
    else:
        call = lambda: getattr(s, method)(ATTEMPT, bad, 0)
    rejected(call)
    assert s.phase == "FAILED_HELD" and not s.eligibility().protocol_eligible


@pytest.mark.parametrize("raw", [b'{"private-secret":1,"private-secret":2}',
                                b'{"private-secret":true,"private-secret":false}'])
def test_safe_errors_and_forged_authority_parser_context(raw):
    error = rejected(lambda: p.decode_record(p.RecordKind.START, raw))
    assert error.__cause__ is None and error.__context__ is None
    assert "private-secret" not in str(error)
    assert not hasattr(error, "doc")


@pytest.mark.parametrize("variant", ["missing", "extra", "unknown_kw", "duplicate_kw"])
def test_transition_identity_and_replay_call_shape(variant):
    trace = Trace()
    s = trace.session
    if variant == "missing":
        call = lambda: s.consume_sample()
    elif variant == "extra":
        call = lambda: s.consume_sample(encoded(sample()), "private-secret")
    elif variant == "unknown_kw":
        call = lambda: s.consume_sample(private_secret=encoded(sample()))
    else:
        call = lambda: s.consume_sample(encoded(sample()), frame=encoded(sample()))
    rejected(call, "accounting_protocol_invalid")
    assert s.phase == "FAILED_HELD"
    assert not s.eligibility().protocol_eligible


@pytest.mark.parametrize("platform", [WINDOWS, LINUX])
@pytest.mark.parametrize("field", ["sequence", "monotonic_ns", "query_duration_ns", "cpu_ns"])
@pytest.mark.parametrize("value", [True, False, -1, None, "1", 1.0])
def test_strict_shapes_and_canonical_records_numeric_fields(platform, field, value):
    record = sample(platform)
    record[field] = value
    rejected(lambda: p.decode_record(p.RecordKind.SAMPLE, encoded(record)))


@pytest.mark.parametrize("field", ["root_reaped", "adopted_reaped"])
@pytest.mark.parametrize("value", [0, 1, None, "true"])
def test_strict_shapes_and_canonical_records_strict_booleans(field, value):
    record = sample(LINUX)
    record["active"][field] = value
    rejected(lambda: p.decode_record(p.RecordKind.SAMPLE, encoded(record)))


@pytest.mark.parametrize("case", ["active32", "active33", "active_gt_total", "terminated_gt_total",
                                 "total_regresses", "terminated_regresses", "root_regresses", "adopted_regresses"])
def test_regression_overflow_underflow_and_bool_active(case):
    if case.startswith(("root", "adopted")):
        trace = Trace(LINUX)
        first, second = sample(LINUX), sample(LINUX, 2, NS20, cpu=2000)
        key = "root_reaped" if case.startswith("root") else "adopted_reaped"
        first["active"][key] = True
        trace.observe(first)
        rejected(lambda: trace.session.consume_sample(encoded(second)), "accounting_counter_invalid")
        return
    record = sample()
    if case in ("active32", "active33"):
        record["active"].update(active_processes=32 if case == "active32" else 33, total_processes=33)
    elif case == "active_gt_total":
        record["active"]["total_processes"] = 0
    elif case == "terminated_gt_total":
        record["active"]["limit_terminated_processes"] = 2
    else:
        trace = Trace()
        record["active"].update(total_processes=2, limit_terminated_processes=1)
        trace.observe(record)
        second = sample(sequence=2, at=NS20, cpu=2000)
        if case == "total_regresses":
            second["active"]["limit_terminated_processes"] = 1
        else:
            second["active"]["total_processes"] = 2
        rejected(lambda: trace.session.consume_sample(encoded(second)), "accounting_counter_invalid")
        return
    if case == "active32":
        p.decode_record(p.RecordKind.SAMPLE, encoded(record))
    else:
        rejected(lambda: p.decode_record(p.RecordKind.SAMPLE, encoded(record)), "accounting_counter_invalid")


@pytest.mark.parametrize("method", [CORRECTION, TRANSFORM])
@pytest.mark.parametrize("platform", [WINDOWS, LINUX])
@pytest.mark.parametrize("which", ["gap", "query", "cpu", "wall"])
@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_bounded_trace_and_final_consistency_running_boundaries(which, delta, method, platform):
    trace = Trace(platform, method)
    record = sample(platform, at=NS20)
    if which == "gap":
        record["monotonic_ns"] += delta
        should_stop = delta > 0
    elif which == "query":
        record["query_duration_ns"] = NS20 + delta
        should_stop = delta > 0
    elif which == "cpu":
        # Raw B/S +/-1 is impossible native granularity; +/-one tick is the valid boundary.
        record = sample(platform, at=NS20, cpu=LANES[method][1] + delta * (100 if platform == WINDOWS else 1000))
        should_stop = delta >= 0
    else:
        trace = Trace(platform, method, started=LANES[method][3] - NS20)
        record["monotonic_ns"] = LANES[method][3] + delta
        # At +1 both the gap and wall limit fail; first required reason is timing.
        should_stop = delta > 0
    decision = trace.observe(record)
    assert decision.stop_required is should_stop
    assert decision.computation_failed is should_stop
    assert trace.session._record_count == 1
    assert trace.session.phase == ("STOP_REQUIRED" if should_stop else "RUNNING_ASSERTED")


@pytest.mark.parametrize("kill_delta", [-1, 0, 1])
def test_bounded_trace_and_final_consistency_kill(kill_delta):
    trace = Trace()
    trace.stop("user_cancelled", 1)
    trace.drain(stopped=1, drained=250000001 + kill_delta)
    assert trace.session.phase == ("FAILED_HELD" if kill_delta > 0 else "DRAIN_ASSERTED")
    assert not trace.session.eligibility().protocol_eligible


@pytest.mark.parametrize("bad", ["attempt_id", "job_id", "object_token", "platform",
    "binding.input_sha256", "binding.request_sha256", "binding.source_commit",
    "binding.runtime_sha256", "binding.module_set_sha256", "binding.profile_sha256",
    "binding.controller_sha256", "samples.sha256", "samples.record_count", "samples.byte_count",
    "timing.started_ns", "timing.max_observe_gap_ns", "timing.max_query_duration_ns",
    "timing.kill_interval_ns", "final.root_exit_code", "final.cpu_ns", "cleanup.object_released"])
def test_receipt_release_and_eligibility_receipt_mutation(bad):
    trace = Trace()
    receipt = trace.finish()
    keys = bad.split(".")
    obj, key = (receipt[keys[0]], keys[1]) if len(keys) == 2 else (receipt, keys[0])
    old = obj[key]
    obj[key] = (not old if type(old) is bool else old + 1 if type(old) is int
                else LINUX if key == "platform" else OTHER if key.endswith("id") or key == "object_token"
                else "a" * len(old))
    rejected(lambda: trace.session.accept_receipt(encoded(receipt)))
    assert trace.session.phase == "FAILED_HELD"
    assert not trace.session.eligibility().protocol_eligible


@pytest.mark.parametrize("field", ["cpu_ns", "wall_ns", "peak_private_bytes"])
def test_receipt_release_and_eligibility_parent_preliminary(field):
    trace = Trace()
    receipt = trace.finish()
    receipt["controller"][field] = {"cpu_ns": 5000000001,
        "wall_ns": 120000000001, "peak_private_bytes": 67108865}[field]
    receipt["verdict"] = "failed_control"
    trace.session.accept_receipt(encoded(receipt))
    assert not trace.session.eligibility().protocol_eligible
    assert trace.session.eligibility().runtime_authorized is False


@pytest.mark.parametrize("platform", [WINDOWS, LINUX])
def test_receipt_release_and_eligibility_exit_codes(platform):
    trace = Trace(platform)
    receipt = trace.finish(exit_code=4294967295 if platform == WINDOWS else -2147483648)
    trace.session.accept_receipt(encoded(receipt))
    trace.session.accept_release(encoded(release(receipt)))
    assert not trace.session.eligibility().protocol_eligible
    for value in ((-1, 4294967296) if platform == WINDOWS else (-2147483649, 2147483648)):
        bad = receipt.copy()
        bad["final"] = dict(receipt["final"], root_exit_code=value)
        rejected(lambda: p.decode_record(p.RecordKind.RECEIPT, encoded(bad)))


@pytest.mark.parametrize("platform", [WINDOWS, LINUX])
def test_receipt_release_and_eligibility_b_plus_one(platform):
    trace = Trace(platform)
    trace.drain()
    record = sample(platform, cpu=60000000000, at=30000000, empty=True)
    record["cpu_ns"] += 1
    rejected(lambda: trace.session.consume_final_sample(encoded(record)), "accounting_counter_invalid")
    assert not trace.session.eligibility().protocol_eligible


@pytest.mark.parametrize("channel", ["sample", "control"])
def test_transition_identity_and_replay_sequence_exhaustion(channel):
    trace = Trace()
    if channel == "sample":
        trace.session._sample_sequence = U64
        call = lambda: trace.session.consume_sample(encoded(sample(sequence=U64)))
    else:
        trace.session._control_sequence = U64
        call = lambda: trace.session.consume_control(encoded(control(U64)))
    rejected(call, "accounting_transition_invalid")
    assert trace.session.phase == "FAILED_HELD"


@pytest.mark.parametrize("platform", [WINDOWS, LINUX])
def test_unavailable_is_not_final_zero_known_trace(platform):
    trace = Trace(platform)
    trace.observe(sample(platform))
    trace.stop("user_cancelled", 11000000)
    trace.drain(11000000, 20000000)
    receipt = trace.receipt(unavailable=True)
    receipt["stop_reason"] = "user_cancelled"
    trace.session.accept_receipt(encoded(receipt))
    assert trace.session._receipt.final.cpu_ns is None
    assert trace.session._receipt.samples.record_count == 1
    assert trace.session.phase == "FAILED_HELD"
    assert not trace.session.eligibility().protocol_eligible


PHASE_EVENTS = {
    "contain": {"PREPARED"}, "start": {"CONTAINMENT_ASSERTED"},
    "control": {"RUNNING_ASSERTED", "STOP_REQUIRED", "STOP_ASSERTED"},
    "sample": {"RUNNING_ASSERTED", "STOP_REQUIRED", "STOP_ASSERTED"},
    "stop": {"RUNNING_ASSERTED", "STOP_REQUIRED"},
    "drain": {"RUNNING_ASSERTED", "STOP_ASSERTED"}, "final": {"DRAIN_ASSERTED"},
    "receipt": {"FINAL_CHECKED"}, "release": {"RECEIPT_BOUND"},
}
PHASES = ("PREPARED", "CONTAINMENT_ASSERTED", "RUNNING_ASSERTED", "STOP_REQUIRED",
          "STOP_ASSERTED", "DRAIN_ASSERTED", "FINAL_CHECKED", "RECEIPT_BOUND",
          "ACK_CHECKED", "FAILED_HELD")


@pytest.mark.parametrize("phase,event", [(phase, event) for phase in PHASES
    for event, permitted in PHASE_EVENTS.items() if phase not in permitted])
def test_transition_identity_and_replay_entire_phase_table(phase, event):
    # Known phase setup is internal to this synthetic test, never a public setter.
    trace = Trace()
    receipt = trace.finish()
    if event == "release":
        trace.session.accept_receipt(encoded(receipt))
    # Receipt events get a valid final trace with NO prior receipt: the forbidden
    # phase must be the reason for rejection, not an unrelated duplicate guard.
    trace.session._phase = phase
    calls = {"contain": lambda: trace.session.assert_contained(ATTEMPT, TOKEN, 0),
        "start": lambda: trace.session.assert_started(ATTEMPT, TOKEN, 0),
        "control": lambda: trace.session.consume_control(encoded(control())),
        "sample": lambda: trace.session.consume_sample(encoded(sample(sequence=5, at=NS20 * 5))),
        "stop": lambda: trace.session.request_stop("user_cancelled", NS20 * 5),
        "drain": lambda: trace.session.assert_drained(ATTEMPT, TOKEN, NS20 * 5, NS20 * 6, True, 0),
        "final": lambda: trace.session.consume_final_sample(encoded(sample(sequence=5, at=NS20 * 5, empty=True))),
        "receipt": lambda: trace.session.accept_receipt(encoded(receipt)),
        "release": lambda: trace.session.accept_release(encoded(release(receipt)))}
    rejected(calls[event], "accounting_transition_invalid")
    assert trace.session.phase == "FAILED_HELD"
    assert not trace.session.eligibility().protocol_eligible


def test_transition_identity_and_replay_positive_stop_channels():
    trace = Trace()
    trace.session.consume_control(encoded(control(action="cancel")))
    assert trace.session.phase == "STOP_REQUIRED"
    trace.session.consume_control(encoded(control(2)))
    trace.observe(sample())
    assert trace.session.phase == "STOP_REQUIRED"
    trace.stop("user_cancelled", 11000000)
    trace.session.consume_control(encoded(control(3)))
    trace.observe(sample(sequence=2, at=NS20, cpu=2000))
    assert trace.session.phase == "STOP_ASSERTED"
    trace.drain(11000000, 25000000)
    for at in (30000000, 50000000, 70000000):
        trace.observe(sample(sequence=len(trace.frames) + 1, at=at, cpu=2000, empty=True), final=True)
    receipt = trace.receipt()
    trace.session.accept_receipt(encoded(receipt))
    trace.session.accept_release(encoded(release(receipt)))
    assert trace.session.phase == "ACK_CHECKED"
    assert not trace.session.eligibility().protocol_eligible


@pytest.mark.parametrize("bad", ["gap", "started", "stopped", "drained", "visibility"])
def test_unavailable_is_not_final_zero_known_timing_mutation(bad):
    trace = Trace()
    trace.observe(sample())
    receipt = trace.receipt(unavailable=True)
    key = {"gap": "max_observe_gap_ns", "started": "started_ns", "stopped": "stopped_ns",
           "drained": "drained_ns", "visibility": "visibility_evidence_sha256"}[bad]
    receipt["timing"][key] = "not-a-digest" if bad == "visibility" else 1
    rejected(lambda: trace.session.accept_receipt(encoded(receipt)))
    assert trace.session.phase == "FAILED_HELD"
    assert not trace.session.eligibility().protocol_eligible


@pytest.mark.parametrize("code", [None, True, 0, b"accounting_cpu_limit"])
def test_safe_errors_and_forged_authority_wrong_code_type(code):
    rejected(lambda: p.safe_error(code), "accounting_protocol_invalid")


def test_safe_errors_and_forged_authority_no_equality_hook():
    class Hostile:
        def __eq__(self, other):
            raise AssertionError("Equality hook reached")
    rejected(lambda: p.SafeError("accounting_cpu_limit", Hostile(), False))
    rejected(lambda: p.ProtocolEligibility(True, True, "protocol_consistent"))
    assert p.safe_error("s" * 100000).message == ERRORS["accounting_protocol_invalid"]


@pytest.mark.parametrize("boundary", ["records", "bytes"])
def test_bounded_trace_and_final_consistency_exact_trace_caps(boundary):
    trace = Trace()
    raw = encoded(sample())
    if boundary == "records":
        trace.session._record_count = 32767
    else:
        trace.session._byte_count = 16777216 - len(raw) - 1
    trace.session.consume_sample(raw)
    assert (trace.session._record_count if boundary == "records" else trace.session._byte_count) == (
        32768 if boundary == "records" else 16777216)
    digest = trace.session._digest.hexdigest()
    rejected(lambda: trace.session.consume_sample(encoded(sample(sequence=2, at=NS20))),
             "accounting_bounds_exceeded")
    assert trace.session._digest.hexdigest() == digest


@pytest.mark.parametrize("changed", ["scalar_type", "digests", "uuids", "nested_freeze", "unknown_variant"])
def test_strict_shapes_and_canonical_records_typed_identity(changed):
    record = start()
    if changed == "scalar_type":
        record["source_commit"] = 3
    elif changed == "digests":
        record["input_sha256"] = "A" * 64
    elif changed == "uuids":
        record["attempt_id"] = "00000000-0000-0000-0000-000000000000"
    elif changed == "unknown_variant":
        record["schema"] = "physical-accounting-profile-1"
    else:
        parsed = p.decode_record(p.RecordKind.START, encoded(record))
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError, TypeError)):
            parsed.limits.cpu_ceiling_ns = 1
        record["limits"]["cpu_ceiling_ns"] = 1
        assert parsed.limits.cpu_ceiling_ns == 60000000000
        return
    rejected(lambda: p.decode_record(p.RecordKind.START, encoded(record)))


def test_bounds_precede_decode_and_conversion_no_subclass_hooks(monkeypatch):
    class HostileBytes(bytes):
        def decode(self, *args, **kwargs):
            raise AssertionError("Untrusted decode hook reached")
        def __len__(self):
            raise AssertionError("Untrusted length hook reached")
    class HostileStr(str):
        def __len__(self):
            raise AssertionError("Untrusted string length hook reached")
    rejected(lambda: p.decode_record(p.RecordKind.START, HostileBytes(encoded(start()))))
    rejected(lambda: p.limits_for(HostileStr(CORRECTION)))
    for raw in (b'{"x":18446744073709551616}', b'{"x":-2147483649}'):
        def forbidden(*args, **kwargs):
            raise AssertionError("Integer range failed after tree/int allocation")
        with monkeypatch.context() as patched:
            patched.setattr(p, "_decode_json", forbidden)
            patched.setattr(p, "_parse_int", forbidden)
            rejected(lambda: p.decode_record(p.RecordKind.START, raw), "accounting_integer_invalid")


@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_bounded_trace_and_final_consistency_last_deadline(offset):
    trace = Trace()
    trace.drain()
    for seq, at in ((1, 30000000), (2, 50000000), (3, 2020000000 + offset)):
        trace.observe(sample(sequence=seq, at=at, empty=True), final=True)
    assert trace.session.phase == ("FAILED_HELD" if offset > 0 else "FINAL_CHECKED")
    if offset <= 0:
        receipt = trace.receipt()
        trace.session.accept_receipt(encoded(receipt))
        trace.session.accept_release(encoded(release(receipt)))
        assert trace.session.eligibility().protocol_eligible
    assert trace.session.eligibility().runtime_authorized is False


@pytest.mark.parametrize("invalid", ["counter", "identity", "timing"])
def test_unavailable_is_not_final_zero_held_diagnostic(invalid):
    trace = Trace()
    record = sample()
    if invalid == "counter":
        record["cpu_ns"] += 1
        rejected(lambda: trace.session.consume_sample(encoded(record)))
        reason = "counter_invalid"
    elif invalid == "identity":
        record["attempt_id"] = OTHER
        rejected(lambda: trace.session.consume_sample(encoded(record)))
        reason = "identity_changed"
    else:
        trace.drain()
        record = sample(at=30000000, empty=True)
        record["query_duration_ns"] = NS20 + 1
        trace.observe(record, final=True)
        reason = "observe_gap"
    prior = trace.session.eligibility()
    receipt = trace.receipt(unavailable=True)
    receipt["stop_reason"] = reason
    trace.session.accept_receipt(encoded(receipt))
    assert trace.session.eligibility() == prior
    assert trace.session.phase == "FAILED_HELD"
    rejected(lambda: trace.session.accept_receipt(encoded(Trace().finish())))
    assert trace.session.eligibility() == prior


def test_bounds_precede_decode_and_conversion_serialization(monkeypatch):
    raw = encoded(start())
    def forbidden(*args, **kwargs):
        raise AssertionError("Serialization reached before bounded length check")
    monkeypatch.setattr(p, "_canonical_size", lambda value: 16385)
    monkeypatch.setattr(p._json, "dumps", forbidden)
    rejected(lambda: p.decode_record(p.RecordKind.START, raw), "accounting_bounds_exceeded")


def test_safe_errors_and_forged_authority_constructor_variants():
    rejected(lambda: p.ProtocolEligibility(True, False, "accounting_cpu_limit"))
    rejected(lambda: p.ProtocolEligibility(False, False, "protocol_consistent"))
    rejected(lambda: p.ProtocolDecision("FAILED_HELD", True, False, "protocol_consistent"))
    rejected(lambda: p.ProtocolDecision("FINAL_CHECKED", False, True, "protocol_consistent"))
    rejected(lambda: bool(p.ProtocolEligibility(True, False, "protocol_consistent")))
    rejected(lambda: bool(p.ProtocolEligibility(False, False, "accounting_cpu_limit")))
    rejected(lambda: bool(p.ProtocolDecision("PREPARED", False, False, "protocol_consistent")))
