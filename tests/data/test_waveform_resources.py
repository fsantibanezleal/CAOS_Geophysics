"""Test-first A4 contracts; deterministic tests do not prove native safety."""

import ctypes
import importlib
import json
from pathlib import Path
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "data-pipeline"))


def module():
    return importlib.import_module("waveform_m08_windows")


@pytest.mark.parametrize("user,kernel,expected", [(0, 0, 0), (1, 2, 300), (570000000, 0, 57000000000)])
def test_windows_lifetime_units(user, kernel, expected):
    assert module().cpu_ns(user, kernel) == expected


@pytest.mark.parametrize(
    "user,kernel", [(True, 0), (0, False), (-1, 0), (1.0, 0), (None, 0), (2**63, 0), (2**63 - 1, 0)]
)
def test_invalid_counter_never_becomes_zero(user, kernel):
    with pytest.raises(module().ControlError):
        module().cpu_ns(user, kernel)


def test_exact_signed_ns_boundary_and_overflow():
    # The approved pure protocol's converted-nanosecond domain is signed64;
    # wire storage remains unsigned64, never a wider CPU conversion fallback.
    maximum = (2**63 - 1) // 100
    assert module().cpu_ns(maximum, 0) == maximum * 100
    with pytest.raises(module().ControlError):
        module().cpu_ns(maximum + 1, 0)
    with pytest.raises(module().ControlError):
        module().cpu_ns(maximum, 1)


def test_authored_ctypes_layouts_are_not_measured_abi():
    m = module()
    values = m.layout_values()
    assert values["BASIC_LIMIT.size"] == 64
    assert values["ACCOUNT.size"] == 48
    assert values["EXTENDED.size"] == 144
    assert values["STARTUP.size"] == 104
    assert values["STARTUP_EX.size"] == 112
    assert values["SECURITY.size"] == 24
    assert values["PID_LIST.size"] == 24
    assert values["PID_LIST.ids"] == 8
    assert values["EXTENDED.peak_job"] == 136
    assert values["ACCOUNT.period_kernel"] == 24
    assert ctypes.sizeof(m.FILETIME) == 8
    # No packing directive, no ctypes long inference, no native call here.
    assert "_pack_" not in m.BASIC_LIMIT.__dict__


def test_wire_identity_sequence_phase_and_header_before_payload():
    m = module()
    run = "ab" * 16
    raw = m.frame(run, 1, "hello", struct.pack("<Q", 123))
    assert len(raw) == 40
    assert m.header(raw[:32], run, 1) == ("hello", 8)
    for bad in (raw[:31], raw[:32] + b"x", raw[:8] + bytes(16) + raw[24:32]):
        with pytest.raises(m.ControlError):
            m.header(bad, run, 1)
    for seq in (0, 2, True):
        with pytest.raises(m.ControlError):
            m.header(raw[:32], run, seq)
    altered = bytearray(raw[:32])
    altered[28:32] = struct.pack("<I", 65537)
    with pytest.raises(m.ControlError):
        m.header(bytes(altered), run, 1)


@pytest.mark.parametrize(
    "phase,payload", [("hello", bytes(9)), ("drained", bytes(23)), ("ack", bytes(1)), ("unknown", b"")]
)
def test_wire_exact_phase_sizes(phase, payload):
    with pytest.raises(module().ControlError):
        module().frame("01" * 16, 1, phase, payload)


def test_checked_monitor_limits_and_final_wait():
    m = module()
    monitor = m.Lifetime()
    monitor.sample(1000000000, 0, 0, 0, 0, 0)
    monitor.sample(1050000000, 1, 2, 1, 1, 128)
    monitor.drained(1050000000)
    monitor.sample(1100000000, 2, 2, 0, 2, 256)
    assert not monitor.final_ready
    monitor.sample(1150000000, 2, 2, 0, 2, 256)
    assert monitor.final_ready
    assert monitor.final_cpu_ns == 400
    assert monitor.max_gap_ns == 50000000
    assert monitor.failure is None


@pytest.mark.parametrize("change", ["gap", "clock", "user", "kernel", "peak", "active", "total", "stop", "over", "bad"])
def test_monitor_failure_absorbing(change):
    m = module()
    monitor = m.Lifetime()
    monitor.sample(1000000000, 10, 10, 1, 1, 256)
    row = [1050000000, 10, 10, 0, 2, 256]
    if change == "gap":
        row[0] = 1100000001
    if change == "clock":
        row[0] = 999999999
    if change == "user":
        row[1] = 9
    if change == "kernel":
        row[2] = 9
    if change == "peak":
        row[5] = 255
    if change == "active":
        row[3] = 3
    if change == "total":
        row[4] = 3
    if change == "stop":
        row[1] = 570000000
    if change == "over":
        row[1] = 600000001
    if change == "bad":
        row[1] = True
    monitor.sample(*row)
    assert monitor.failure is not None
    monitor.drained(1050000000)
    monitor.sample(1100000000, 10, 10, 0, 2, 256)
    monitor.sample(1150000000, 10, 10, 0, 2, 256)
    assert not monitor.final_ready


def test_drain_not_backdated_or_reset_and_no_late_membership():
    m = module()
    for bad in (999999999, 1100000001, True):
        state = m.Lifetime()
        state.sample(1000000000, 0, 0, 1, 1, 0)
        with pytest.raises(m.ControlError):
            state.drained(bad)
    state = m.Lifetime()
    state.sample(1000000000, 0, 0, 1, 1, 0)
    state.drained(1000000000)
    with pytest.raises(m.ControlError):
        state.drained(1000000000)
    state.sample(1050000000, 0, 0, 0, 2, 0)
    state.sample(1100000000, 0, 0, 1, 2, 0)
    assert not state.final_ready and state.failure is not None


def test_safe_errors_have_no_caller_or_native_payload():
    m = module()
    assert str(m.ControlError("sample_gap")) == "sample_gap"
    assert str(m.ControlError("SECRET pathname")) == "native_contract"


def test_probe_parser_demands_every_field_and_exact_expected_value():
    m = module()
    output = "".join(f"{key}={value}\n" for key, value in sorted(m.layout_values().items())).encode()
    assert m.parse_abi(output) == m.layout_values()
    for raw in (output[:-1], output + b"unknown=1\n", output + output[: output.index(b"\n") + 1], b"x" * 4097):
        with pytest.raises(m.ControlError):
            m.parse_abi(raw)


def test_argv_and_child_environment_are_bounded_fixed_not_shell(tmp_path):
    m = module()
    command = m.command_line([str(tmp_path / "python.exe"), "-B", "a b", 'a"b', "tail\\"])
    assert '"a b"' in command and 'a\\"b' in command
    for argv in (["x" * 16385], ["a\0b"], [True], []):
        with pytest.raises(m.ControlError):
            m.command_line(argv)
    env = m.environment(str(tmp_path))
    assert env.endswith("\0\0")
    assert "PYTHONPATH=" not in env and "PYTHONSTARTUP=" not in env
    assert "OPENBLAS_NUM_THREADS=1" in env


def test_spec_bound_unknown_flags_bool_and_receipt_identity(tmp_path):
    m = module()
    spec = {
        "schema": "caos.m08-windows-transaction.v1",
        "run_id": "01" * 16,
        "source_revision": "0" * 40,
        "closure_manifest_sha256": "0" * 64,
        "mseed": str(tmp_path / "counts.ms"),
        "stationxml": str(tmp_path / "response.xml"),
        "request": str(tmp_path / "request.json"),
        "out": str(tmp_path / "out"),
        "python": sys.executable,
        "evaluate_with": None,
        "private_parent_receipt": {"path": str(tmp_path / "admission.json"), "sha256": "0" * 64},
    }
    assert m.validate_spec(spec) is spec
    for name, value in (
        ("run_id", True),
        ("source_revision", "short"),
        ("evaluate_with", {}),
        ("private_parent_receipt", True),
    ):
        other = dict(spec, **{name: value})
        with pytest.raises(m.ControlError):
            m.validate_spec(other)
    with pytest.raises(m.ControlError):
        m.validate_spec(dict(spec, cpu_limit=100))
    with pytest.raises(m.ControlError):
        m.validate_spec(dict(spec, run_id="x" * 1000000))


def test_no_native_call_or_output_for_unmeasured_admission(tmp_path):
    m = module()
    result = m.run_windows_transaction({})
    assert result == {"status": "rejected", "reason": "native_contract", "runtime_authorized": False}
    assert not list(tmp_path.iterdir())


def test_streamed_controller_copy_preserves_calculation_and_adds_only_postseal_evaluation(tmp_path):
    from test_waveform_input import source, inventory, request
    from waveform_m08_child import calculate_bytes
    from waveform_m08_export import plan_export, write_export, verify_export, copy_export
    from waveform_evaluation import evaluate_waveform_candidates
    from waveform_m08_files import create_output

    result, seal = calculate_bytes(source(), inventory(), json.dumps(request()).encode())
    reference = {
        "schema": "caos.waveform-analyst-references.v1",
        "event_id": "1",
        "source": {"raw_sha256": "0" * 64, "citation": "authored control", "rights": "private-use-attested"},
        "selection_sealed_before_scoring": True,
        "references": [],
    }
    with create_output(tmp_path / "stage", trusted_parent=tmp_path) as stage:
        write_export(plan_export(result, seal), stage)
        reopened = verify_export(stage)
        evaluation = json.dumps(evaluate_waveform_candidates(reopened, json.dumps(reference).encode())).encode()
        with create_output(tmp_path / "final", trusted_parent=tmp_path) as final:
            receipt = copy_export(stage, final, evaluation=evaluation, scratch_input_bytes=1024)
            assert verify_export(final) == seal
            assert receipt["runtime_authorized"] is False
        assert "evaluation.json" not in stage.names(55)
    assert (tmp_path / "stage/calculation.json").read_bytes() == (tmp_path / "final/calculation.json").read_bytes()


def test_copy_scratch_preflight_and_invalid_seal_leave_new_target_empty(tmp_path):
    from test_waveform_input import source, inventory, request
    from waveform_m08_child import calculate_bytes
    from waveform_m08_export import plan_export, write_export, copy_export
    from waveform_m08_files import create_output
    from waveform_input import WaveformInputError

    result, seal = calculate_bytes(source(), inventory(), json.dumps(request()).encode())
    with create_output(tmp_path / "stage", trusted_parent=tmp_path) as stage:
        write_export(plan_export(result, seal), stage)
        with create_output(tmp_path / "final", trusted_parent=tmp_path) as final:
            for size in (True, -1, 52690944, None):
                with pytest.raises(WaveformInputError):
                    copy_export(stage, final, scratch_input_bytes=size)
                assert final.names(55) == []
            with pytest.raises(WaveformInputError):
                copy_export(stage, final, evaluation=b"{}", scratch_input_bytes=0)
            assert final.names(55) == []


def test_exact_cli_admission_dispatch_has_no_user_resource_or_provider_override(tmp_path, monkeypatch, capsys):
    import process_waveform_m08 as cli

    m = module()
    from test_waveform_cli import fixtures

    args = fixtures(tmp_path)
    admission = tmp_path / "admission.json"
    admission.write_bytes(b"{}")
    called = []

    def run_paths(paths, reference, admission_path):
        called.append((paths, reference, admission_path))
        return {"status": "rejected", "reason": "abi_unmeasured", "runtime_authorized": False}

    monkeypatch.setattr(m, "run_cli", run_paths)
    assert cli.main(args + ["--admission", str(admission)]) == 3
    assert len(called) == 1 and called[0][2] == admission
    assert json.loads(capsys.readouterr().out)["reason"] == "abi_unmeasured"
    assert cli.main(args + ["--admission", str(admission), "--cpu-limit", "999"]) == 3
    assert len(called) == 1


@pytest.mark.parametrize("bad", [0, 1, 16, 145])
def test_query_exact_record_length_and_false_return_deny(bad):
    from types import SimpleNamespace

    m = module()
    native = m.Native.__new__(m.Native)

    def query(job, kind, record, length, returned):
        returned._obj.value = bad
        return 1

    native.api = SimpleNamespace(QueryInformationJobObject=query)
    with pytest.raises(m.ControlError):
        native.query(10, 9, m.EXTENDED)
    native.api.QueryInformationJobObject = lambda *args: 0
    with pytest.raises(m.ControlError):
        native.query(10, 1, m.ACCOUNT)


@pytest.mark.parametrize(
    "assigned,count,length,ids,valid",
    [
        (1, 1, 16, (123, 0), True),
        (2, 2, 24, (123, 456), True),
        (2, 1, 16, (123, 0), False),
        (2, 2, 16, (123, 456), False),
        (2, 2, 24, (123, 123), False),
        (2, 2, 24, (123, 0), False),
        (3, 3, 24, (123, 456), False),
    ],
)
def test_bounded_membership_snapshot_no_truncation_or_pid_reuse(assigned, count, length, ids, valid):
    from types import SimpleNamespace

    m = module()
    native = m.Native.__new__(m.Native)

    def query(job, kind, record, supplied, returned):
        assert supplied == 24 and kind == 3
        value = record._obj
        value.assigned, value.count = assigned, count
        value.ids[:] = ids
        returned._obj.value = length
        return 1

    native.api = SimpleNamespace(QueryInformationJobObject=query)
    if valid:
        assert native.members(10) == ids[:count]
    else:
        with pytest.raises(m.ControlError):
            native.members(10)


@pytest.mark.parametrize("wait,code", [(258, 0), (0, 259), (0xFFFFFFFF, 0), (128, 0)])
def test_signalled_exit_checks_never_treat_still_active_as_final(wait, code):
    from types import SimpleNamespace

    m = module()
    native = m.Native.__new__(m.Native)

    def exit_code(handle, output):
        output._obj.value = code
        return 1

    native.api = SimpleNamespace(WaitForSingleObject=lambda *args: wait, GetExitCodeProcess=exit_code)
    with pytest.raises(m.ControlError):
        native.exit_code(10)


def test_native_handle_ownership_no_double_close_no_borrowed_close():
    from types import SimpleNamespace

    m = module()
    native = m.Native.__new__(m.Native)
    closed = []
    native.handles = set()
    native.api = SimpleNamespace(CloseHandle=lambda h: closed.append(h) or 1)
    assert native.owned(123) == 123
    for h in (0, 2**64 - 1, 123, True):
        with pytest.raises(m.ControlError):
            native.owned(h)
    with pytest.raises(m.ControlError):
        native.close(456)
    native.close(123)
    with pytest.raises(m.ControlError):
        native.close(123)
    assert closed == [123]


def test_incomplete_wire_eof_and_unknown_phase_are_absorbing_deny():
    from types import SimpleNamespace

    m = module()
    wire = m.WireReader("01" * 16)
    raw = m.frame("01" * 16, 1, "hello", struct.pack("<Q", 123))
    parts = [raw[:32], raw[32:]]
    fake = SimpleNamespace(available=lambda h: len(parts[0]) if parts else None, read=lambda h, size: parts.pop(0))
    assert wire.poll(fake, 1) is None
    assert wire.poll(fake, 1) == ("hello", struct.pack("<Q", 123))
    assert wire.poll(fake, 1) is None and wire.eof
    wire = m.WireReader("01" * 16)
    wire.pending = b"x"
    with pytest.raises(m.ControlError):
        wire.poll(fake, 1)


def test_role_arguments_reject_script_injection_integer_bool_unbounded_digits():
    m = module()
    assert m.role_arguments(["--controller", "123", "456", "789"]) == ("--controller", [123, 456, 789])
    for argv in (
        ["--provider", "1", "2", "3"],
        ["--science", "0", "2", "3"],
        ["--science", "1" * 10000, "2", "3"],
        ["--science", True, "2", "3"],
    ):
        with pytest.raises(m.ControlError):
            m.role_arguments(argv)


def test_probe_is_layout_only_no_native_control_calls_or_unbounded_input():
    text = (ROOT / "tests/fixtures/waveform_m08/abi_probe.c").read_text()
    assert "int main(void)" in text and "_Generic(&K32EnumProcessModules" in text
    for name in ("CreateProcessW(", "CreateJobObjectW(", "TerminateJobObject(", "scanf(", "argv"):
        assert name not in text


def test_protocol_json_uint64_and_4096_string_preflight_not_scientific_53bit_limit():
    m = module()
    assert m.decode_control(b'{"value":18446744073709551615}') == {"value": 2**64 - 1}
    assert m.canonical({"value": 2**64 - 1}) == b'{"value":18446744073709551615}'
    assert m.decode_control(m.canonical({"path": "x" * 4096}))["path"] == "x" * 4096
    for raw in (
        b'{"v":18446744073709551616}',
        b'{"v":-1}',
        b'{"v":1.1}',
        b'{"v":1e1}',
        b'{"v":1,"v":2}',
        b'{"v":NaN}',
        b"[" * 9 + b"]" * 9,
        b'{"v":"' + b"x" * 4097 + b'"}',
    ):
        with pytest.raises(m.ControlError):
            m.decode_control(raw)
    for value in ({"v": 2**64}, {"v": "x" * 4097}):
        with pytest.raises(m.ControlError):
            m.canonical(value)


def test_observer_drains_queued_export_after_controller_signal_before_final_receipt(tmp_path, monkeypatch):
    """Authored native boundary double only. No Job/process launched by this test."""
    from types import SimpleNamespace
    from waveform_m08_files import open_output

    m = module()
    clock = [1000000000]
    monkeypatch.setattr(
        m,
        "time",
        SimpleNamespace(monotonic_ns=lambda: clock[0], sleep=lambda n: clock.__setitem__(0, clock[0] + int(n * 1e9))),
    )
    run = "01" * 16
    outcome = {
        "manifest_sha256": "0" * 64,
        "calculation_sha256": "1" * 64,
        "bytes": 100,
        "runtime_authorized": False,
        "scientific_status": "computed",
    }

    class Fake(m.Native):
        def __init__(self):
            self.handles, self.next, self.started, self.acks, self.queue = set(), 10, False, 0, b""
            self.api = SimpleNamespace(
                CreateJobObjectW=lambda *a: 999,
                SetHandleInformation=lambda *a: 1,
                GetCurrentProcess=lambda: 1000,
                GetProcessTimes=lambda *a: 1,
                CloseHandle=lambda *a: 1,
                TerminateJobObject=lambda *a: 1,
            )

        def closure(self, allowed):
            return "0" * 64

        def capacity(self, disk_free):
            return {"snapshot_not_reservation": True, "production_floor": None}

        def limits(self, job):
            pass

        def sample(self, job):
            return (
                clock[0],
                int(self.started),
                int(self.started),
                0 if self.acks == 2 or not self.started else 1,
                0 if not self.started else 2 if self.acks == 2 else 1,
                0 if not self.started else 1024,
            )

        def pipe(self, inherit_read):
            a, b = self.owned(self.next), self.owned(self.next + 1)
            self.next += 2
            return a, b

        def launch(self, *a, **k):
            self.started = True
            return m.PROCESS(self.owned(100), self.owned(101), 123, 1)

        def membership(self, *args):
            pass

        def members(self, job):
            return (123,) if not self.acks else (123, 456)

        def resume(self, process):
            self.close(process.thread)
            self.queue = m.frame(run, 1, "hello", struct.pack("<Q", 123))

        def write(self, handle, raw):
            self.acks += 1
            if self.acks == 1:
                self.queue += m.frame(run, 2, "child", struct.pack("<Q", 456))
            else:
                self.queue += m.frame(run, 3, "drained", struct.pack("<QQQ", clock[0], 456, 1))
                self.queue += m.frame(run, 4, "export", m.canonical(outcome))

        def available(self, handle):
            return len(self.queue) if handle == 10 and self.queue else None if self.acks == 2 else 0

        def read(self, handle, size):
            raw, self.queue = self.queue[:size], self.queue[size:]
            return raw

        def signalled(self, handle):
            return self.acks == 2

        def exit_code(self, handle):
            return 0

    monkeypatch.setattr(m, "Native", Fake)
    with open_output(tmp_path) as parent:
        identity = list(parent.identity)
    admission = {"parent": {"identity": identity}, "runtime": []}
    spec = {
        "out": str(tmp_path / "new"),
        "run_id": run,
        "source_revision": "0" * 40,
        "closure_manifest_sha256": "0" * 64,
        "private_parent_receipt": {"sha256": "0" * 64},
        "python": sys.executable,
    }
    result = m.observe(spec, admission)
    assert result["status"] == "computed"
    evidence = tmp_path / ("new.a4-" + run)
    receipt = json.loads((evidence / "eligibility.json").read_bytes())
    released = json.loads((evidence / "release.json").read_bytes())
    assert receipt["active_processes"] == 0 and receipt["runtime_authorized"] is False
    assert (
        released["receipt_sha256"] == result["receipt_sha256"] and released["all_native_owned_handles_closed"] is True
    )
    assert not (evidence / "failure.json").exists()


@pytest.mark.parametrize(
    "status,code",
    [
        ("computed", 0),
        ("qc_only", 2),
        ("rejected", 3),
        ("engine_unavailable", 4),
        ("failed", 5),
        ("resource_exceeded", 6),
        ("timed_out", 124),
        ("cancelled", 130),
    ],
)
def test_fixed_cli_terminal_codes(status, code):
    assert module().exit_status({"status": status}) == code


def test_final_original_hash_is_bounded_rechecked_and_never_changes_bytes(tmp_path):
    from waveform_m08_files import open_input

    m = module()
    path = tmp_path / "original"
    path.write_bytes(b"unchanged original")
    with open_input(path, 1024) as held:
        assert held.read_bytes() == b"unchanged original"
        m.verify_original(held)
    assert path.read_bytes() == b"unchanged original"


def test_control_budget_preflight_no_overwrite_and_profile_bounds(tmp_path):
    from waveform_m08_files import create_output

    m = module()
    with create_output(tmp_path / "scratch", trusted_parent=tmp_path) as directory:
        fd = m.control_file(directory, "observer.json", b"x" * 65535)
        import os

        os.close(fd)
        with pytest.raises(m.ControlError):
            m.control_file(directory, "eligibility.json", b"xx")
        assert not (directory.path / "eligibility.json").exists()
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "generated").write_bytes(b"private runtime bytes")
    assert m.environment_bytes(cache) == 21
    import os

    os.link(cache / "generated", cache / "linked")
    with pytest.raises(m.ControlError):
        m.environment_bytes(cache)


def test_measured_capacity_uses_bytes_no_percentage_or_production_floor():
    from types import SimpleNamespace

    m = module()
    native = m.Native.__new__(m.Native)

    def memory(record):
        assert record._obj.length == 64
        value = record._obj
        value.total_physical = value.total_commit = 4 * m.MEMORY
        value.available_physical = value.available_commit = 2 * m.MEMORY
        return 1

    native.api = SimpleNamespace(GlobalMemoryStatusEx=memory)
    result = native.capacity(2 * m.SCRATCH + 67108864)
    assert result["available_physical_bytes"] == 2 * m.MEMORY
    for space in (True, 0, m.SCRATCH + 67108863):
        with pytest.raises(m.ControlError):
            native.capacity(space)

    def insufficient(record):
        memory(record)
        record._obj.available_physical = m.MEMORY
        return 1

    native.api.GlobalMemoryStatusEx = insufficient
    with pytest.raises(m.ControlError):
        native.capacity(2 * m.SCRATCH + 67108864)
