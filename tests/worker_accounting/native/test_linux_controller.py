"""Transport unit controls plus explicit, unexecuted-until-host native gates.

Run local pure controls with -k transport. Host gates require the retained real
matrix via plugin scripts.run_linux_cpu_controls --linux-cpu-results. Missing
host evidence is an error, NOT a skip or synthetic passing replacement.
"""
import hashlib
import json
from pathlib import Path
import struct

import pytest

from scripts.run_linux_cpu_controls import (CASES, COMMON_FLAGS, FRAME, ControlError,
                                           Transcript, build_recipe, frame)
import scripts.run_linux_cpu_controls as runner

ATTEMPT = "01" * 16
OBJECT = "02" * 16


def test_transport_no_heartbeat_after_custody_bind():
    import inspect
    source = inspect.getsource(runner.run_control)
    assert "not process.stdin.closed and not custody and" in source
    assert source.index("send(5,") < source.index("custody = True")


def output(kind, seq, body):
    return FRAME.pack(b"LCP1", 1, kind, len(body), 0, seq, 100 + seq,
                      bytes.fromhex(ATTEMPT), bytes.fromhex(OBJECT)) + body


def authored_packets():
    sample = (100, 105, 60, 40, 20, 60000, 0, 1, 0, 5, 5, 0)
    final = (*sample, 50, 0, 0, 1, 40, 20, 0, 0, 0, 0, 4)
    a = output(256, 1, struct.pack("<12Q", *sample))
    b = output(257, 2, struct.pack("<23Q", *final))
    c = output(258, 3, hashlib.sha256(a + b).digest())
    d = output(259, 4, struct.pack("<Q", 0))
    return a + b + c + d, sample, final


@pytest.mark.parametrize("chunk", [1, 3, 63, 64, 65, 159, 184, 1024, 4160])
def test_transport_fragmentation_digest_and_native_integers(chunk):
    raw, sample, final = authored_packets()
    t = Transcript(ATTEMPT, OBJECT)
    for offset in range(0, len(raw), chunk):
        t.feed(raw[offset:offset + chunk])
    assert t.samples == 1 and t.last == sample and t.final == final
    assert t.release == 0 and not t.pending
    assert type(t.final[0]) is int


def unavailable_packets(values=None):
    values = values or (0,) * 11 + (7, 0, 200, 201, 0) + (0,) * 6 + (4,)
    a = output(257, 1, struct.pack("<23Q", *values))
    b = output(258, 2, hashlib.sha256(a).digest())
    return a + b, values


@pytest.mark.parametrize("chunk", [1, 63, 64, 159, 4160])
def test_transport_unavailable_before_first_sample_is_failure_custody(chunk):
    raw, values = unavailable_packets()
    t = Transcript(ATTEMPT, OBJECT)
    for offset in range(0, len(raw), chunk):
        t.feed(raw[offset:offset + chunk])
    assert t.final == values and t.final[15] == 0 and t.final[11] == 7
    assert t.samples == 0 and t.last is None and t.release is None
    assert t.native_digest == hashlib.sha256(raw[:248]).digest()
    assert not t.pending  # zero words are unavailable, not an observed sample
    with pytest.raises(ControlError):
        t.feed(output(259, 3, struct.pack("<Q", 7)))


@pytest.mark.parametrize("index,value", [
    *((i, 1) for i in range(11)), (11, 0), (11, 24), (12, 1),
    (13, 0), (14, 199), (15, 1), (15, 2),
    *((i, 1) for i in range(16, 22)), (22, 0), (22, 2**32),
])
def test_transport_unavailable_before_sample_rejects_false_observation(index, value):
    raw, values = unavailable_packets()
    changed = list(values); changed[index] = value
    with pytest.raises(ControlError):
        Transcript(ATTEMPT, OBJECT).feed(unavailable_packets(changed)[0])


def test_transport_unavailable_digest_and_terminal_order_still_strict():
    raw, values = unavailable_packets()
    with pytest.raises(ControlError):
        Transcript(ATTEMPT, OBJECT).feed(raw[:-1] + bytes([raw[-1] ^ 1]))
    t = Transcript(ATTEMPT, OBJECT); t.feed(raw)
    for packet in (output(257, 3, struct.pack("<23Q", *values)),
                   output(258, 3, t.native_digest),
                   output(256, 3, struct.pack("<12Q", *([0] * 12)))):
        with pytest.raises(ControlError):
            t.feed(packet)
        t = Transcript(ATTEMPT, OBJECT); t.feed(raw)


def test_transport_unavailable_custody_cannot_send_bind_or_ack():
    import inspect
    source = inspect.getsource(runner.run_control)
    assert 'if trace.final[15] == 1 and case != "no_ack":' in source


@pytest.mark.parametrize("offset", [0, 4, 6, 8, 12, 16, 32, 48, 64 + 40])
def test_transport_corrupt_source_bytes_are_not_repaired(offset):
    raw, unused, ignored = authored_packets()
    changed = bytearray(raw)
    changed[offset] ^= 1
    with pytest.raises(ControlError):
        Transcript(ATTEMPT, OBJECT).feed(bytes(changed))


def test_transport_limit_checked_before_pending_copy():
    t = Transcript(ATTEMPT, OBJECT)
    with pytest.raises(ControlError):
        t.feed(b"x" * 4161)
    assert not t.pending and t.bytes == 0


def test_transport_unknown_control_and_wrong_bind_length():
    for kind, payload in ((0, b""), (4, b"x" * 32), (5, b"x" * 64)):
        with pytest.raises(ControlError):
            frame(kind, 1, ATTEMPT, OBJECT, payload)


def test_transport_exact_recipe_no_install_or_shell():
    commands = build_recipe("/owned/source", "/owned/build")
    assert len(commands) == 8
    assert all(type(argv) is list and argv[0] == "/usr/bin/cc" for argv in commands)
    assert all(flag in commands[0] for flag in COMMON_FLAGS)
    assert "-MD" in commands[0] and "-MMD" not in commands[0]
    assert "-pthread" in commands[4] and "-pthread" in commands[7]
    assert all("-pie" in argv and "-Wl,-z,relro,-z,now" in argv for argv in commands[5:])
    with pytest.raises(ControlError):
        build_recipe("/owned/source", "/owned/build", "/alternate/compiler")


def build_fields():
    return dict(schema="linux-native-build-1", source_commit_claim="a" * 40,
                authority_sha256="b" * 64, attempt=ATTEMPT, source="/owned/source",
                output="/owned/output", scratch="/owned/scratch", outcome="/owned/outcome",
                source_hashes={name: "c" * 64 for name in runner.BUILD_SOURCE_FILES},
                tool_hashes={name: "d" * 64 for name in runner.BUILD_TOOLS},
                header_hashes={"/usr/include/linux/sched.h": "e" * 64},
                library_hashes={"/usr/lib/x86_64-linux-gnu/libc.so.6": "f" * 64},
                execute_build=True)


def test_build_transport_exact_manifest_fields_without_execution():
    assert runner.validate_build_fields(build_fields()) is None
    assert len(runner.BUILD_SOURCE_FILES) == 12 and len(runner.BUILD_TOOLS) == 8


@pytest.mark.parametrize("field,value", [
    ("source_commit_claim", 1), ("authority_sha256", None), ("attempt", "00" * 16),
    ("execute_build", 1), ("schema", "future"), ("source", "/owned/source/"),
    ("output", "/owned/source/sub"), ("scratch", "/owned/output"),
    ("outcome", "relative"), ("outcome", "/owned/../other"),
    ("source_hashes", {"unknown.c": "c" * 64}), ("tool_hashes", {}),
    ("library_hashes", {}), ("header_hashes", {"relative": "f" * 64}),
    ("header_hashes", {"/usr/include/a": True}),
    ("header_hashes", {"/usr/include/" + str(i): "f" * 64 for i in range(257)}),
])
def test_build_transport_rejects_manifest_before_files_or_launch(field, value, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("shape rejection must precede filesystem/launch")
    monkeypatch.setattr(runner, "safe_path", forbidden)
    monkeypatch.setattr(runner, "file_digest", forbidden)
    monkeypatch.setattr(runner.subprocess, "Popen", forbidden)
    fields = build_fields()
    fields[field] = value
    with pytest.raises(ControlError):
        runner.validate_build_fields(fields)


def test_build_transport_unknown_field_and_source_are_not_adopted():
    fields = build_fields()
    fields["arbitrary"] = 0
    with pytest.raises(ControlError):
        runner.validate_build_fields(fields)
    fields = build_fields()
    fields["source_hashes"]["scripts/unknown.py"] = "c" * 64
    with pytest.raises(ControlError):
        runner.validate_build_fields(fields)


def test_build_transport_input_cap_before_whole_read(tmp_path):
    path = tmp_path / "input"
    path.write_bytes(b"x" * 65)
    with pytest.raises(ControlError):
        runner.bounded_read(path, 64)
    assert runner.bounded_read(path, 65) == b"x" * 65


def test_build_transport_inventory_unknown_and_combined_cap(tmp_path):
    out, scratch = tmp_path / "out", tmp_path / "scratch"
    out.mkdir(); scratch.mkdir()
    (out / "core.o").write_bytes(b"c")
    (scratch / "ccABC123.s").write_bytes(b"s")
    assert runner.inventory(out, scratch)["bytes"] == 2
    unknown = scratch / "unexpected"
    unknown.write_bytes(b"private")
    with pytest.raises(ControlError):
        runner.inventory(out, scratch)
    assert unknown.read_bytes() == b"private"  # no cleanup/unknown adoption
    observed = runner.observe_inventory(out, scratch)
    assert any(entry["name"] == "unexpected" for entry in observed["entries"])
    assert observed["invalid"] is True


def test_build_transport_inventory_links_are_not_followed(tmp_path, monkeypatch):
    out, scratch = tmp_path / "out", tmp_path / "scratch"
    out.mkdir(); scratch.mkdir()
    entry = out / "core.o"
    entry.write_bytes(b"x")
    original = runner.Path.lstat
    import stat
    from types import SimpleNamespace
    def linked(self):
        if self == entry:
            return SimpleNamespace(st_mode=stat.S_IFLNK | 0o600, st_uid=0,
                                   st_nlink=1, st_size=1)
        return original(self)
    monkeypatch.setattr(runner.Path, "lstat", linked)
    with pytest.raises(ControlError):
        runner.inventory(out, scratch)


@pytest.mark.parametrize("name,linker", [("ccABC123.s", False), ("ccABC123.res", True)])
def test_build_exact_temporary_unlink_race_is_retained(tmp_path, monkeypatch, name, linker):
    out, scratch = tmp_path / "out", tmp_path / "scratch"
    out.mkdir(); scratch.mkdir()
    entry = scratch / name
    entry.write_bytes(b"temporary")
    original = runner.Path.lstat
    def vanished(self):
        if self == entry:
            raise FileNotFoundError
        return original(self)
    monkeypatch.setattr(runner.Path, "lstat", vanished)
    observed = runner.observe_inventory(out, scratch, linker=linker)
    assert observed["invalid"] is False and observed["bytes"] == 0
    assert observed["vanished_scratch"] == [name]


@pytest.mark.parametrize("kind,name,linker", [
    ("output", "core.o", False), ("scratch", "unknown", True),
    ("scratch", "ccABC123.res", False)])
def test_build_unknown_or_artifact_unlink_race_remains_failure(tmp_path, monkeypatch, kind, name, linker):
    out, scratch = tmp_path / "out", tmp_path / "scratch"
    out.mkdir(); scratch.mkdir()
    entry = (out if kind == "output" else scratch) / name
    entry.write_bytes(b"retained")
    original = runner.Path.lstat
    def vanished(self):
        if self == entry:
            raise FileNotFoundError
        return original(self)
    monkeypatch.setattr(runner.Path, "lstat", vanished)
    with pytest.raises(FileNotFoundError):
        runner.observe_inventory(out, scratch, linker=linker)


def test_build_transport_inventory_combined_bytes_and_leaves(tmp_path):
    out, scratch = tmp_path / "out", tmp_path / "scratch"
    out.mkdir(); scratch.mkdir()
    with (out / "core.o").open("wb") as stream:
        stream.truncate(32 * 1024**2)
    (scratch / "ccABC123.s").write_bytes(b"x")
    with pytest.raises(ControlError):
        runner.inventory(out, scratch)
    assert runner.observe_inventory(out, scratch)["bytes"] == 32 * 1024**2 + 1
    for i in range(129):
        (scratch / ("cc" + str(i).zfill(6) + ".o")).write_bytes(b"")
    observed = runner.observe_inventory(out, scratch)
    assert observed["truncated"] and observed["invalid"] and observed["leaves"] == 128


def test_build_transport_no_overwrite_preserves_existing_bytes(tmp_path):
    entry = tmp_path / "existing"
    entry.write_bytes(b"original")
    with pytest.raises(ControlError):
        runner.exclusive(entry, b"replacement")
    assert entry.read_bytes() == b"original"


def test_build_transport_capture_has_no_shell_retry_or_cleanup():
    import inspect
    source = inspect.getsource(runner.run_build) + inspect.getsource(runner.build_capture)
    assert "shell=False" in source and "systemd-run" in source
    for forbidden in ("shell=True", "rmtree", ".unlink(", "reset-failed", "--collect"):
        assert forbidden not in source


@pytest.fixture
def host_results(pytestconfig):
    root = pytestconfig.getoption("linux_cpu_results", default=None)
    if root is None:
        pytest.fail("native_linux_controls_NOT_RUN: exact retained host matrix required")
    root = Path(root)
    results = {}
    for name in CASES:
        directory = root / name
        raw = (directory / "result.json").read_bytes()
        assert len(raw) <= 65536
        record = json.loads(raw)
        assert record["schema"] == "linux-cpu-control-1" and record["case"] == name
        assert record["scientific_admission"] is False and record["runtime_admission"] is False
        assert record["failure"] is None
        manifest = json.loads((directory / "manifest.json").read_bytes())
        assert record["manifest_sha256"] == hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest()
        t = Transcript(manifest["attempt"], manifest["object"])
        digest = hashlib.sha256()
        with (directory / "native.frames").open("rb") as stream:
            while chunk := stream.read(4096):
                digest.update(chunk)
                t.feed(chunk)
        assert record["raw_sha256"] == digest.hexdigest()
        assert record["final"] == (list(t.final) if t.final else None)
        assert record["samples"] == t.samples
        assert record["digest"] == (t.native_digest.hex() if t.native_digest else None)
        assert record["release"] == t.release
        assert record["controller_sha256"] == manifest["controller_sha256"]
        assert record["fixture_sha256"] == manifest["fixture_sha256"]
        results[name] = record
    return results


def complete(r, error=0):
    f = r["final"]
    assert f is not None and f[11] == error and f[15] == 1
    assert f[6] == 0 and f[7] == 1 and f[12] > 0
    assert r["max_gap_ns"] <= 20_000_000 and r["max_query_ns"] <= 20_000_000
    assert r["release"] == error
    return f


@pytest.mark.parametrize("suffix", ["cdtor.c", "cdtor.o"])
def test_build_linker_scratch_is_phase_specific(tmp_path, suffix):
    from scripts.run_linux_cpu_controls import observe_inventory
    output, scratch = tmp_path / "output", tmp_path / "scratch"
    output.mkdir(); scratch.mkdir()
    (scratch / ("ccA012bZ." + suffix)).write_bytes(b"authored tool output")
    assert observe_inventory(output, scratch)["invalid"] is True
    observed = observe_inventory(output, scratch, linker=True)
    assert observed["invalid"] is False and observed["leaves"] == 1
    (scratch / "ccC456dY.cdtor.c").write_bytes(b"second")
    (scratch / "ccE789fX.cdtor.o").write_bytes(b"third")
    assert observe_inventory(output, scratch, linker=True)["invalid"] is True


@pytest.mark.parametrize("name", ["ccA012bZ.resp", "ccA012bZ.x", "ccA012bZ.cdtor.cpp", "ccBAD.cdtor.c"])
def test_build_linker_scratch_unknown_stays_failed(tmp_path, name):
    from scripts.run_linux_cpu_controls import observe_inventory
    output, scratch = tmp_path / "output", tmp_path / "scratch"
    output.mkdir(); scratch.mkdir()
    (scratch / name).write_bytes(b"unknown contents not adopted")
    assert observe_inventory(output, scratch, linker=True)["invalid"] is True
    with pytest.raises(ControlError):
        observe_inventory(output, scratch, linker=1)


@pytest.mark.parametrize("size", [0, 65536])
def test_build_resolution_scratch_exact_phase_count_bytes(tmp_path, size):
    from scripts.run_linux_cpu_controls import observe_inventory
    output, scratch = tmp_path / "output", tmp_path / "scratch"
    output.mkdir(); scratch.mkdir()
    f = scratch / "ccA012bZ.res"
    f.write_bytes(b"x" * size)
    assert observe_inventory(output, scratch)["invalid"] is True
    assert observe_inventory(output, scratch, linker=True)["invalid"] is False
    (scratch / "ccB345cY.res").write_bytes(b"")
    assert observe_inventory(output, scratch, linker=True)["invalid"] is True


def test_build_resolution_scratch_plus_one_rejected(tmp_path):
    from scripts.run_linux_cpu_controls import observe_inventory
    output, scratch = tmp_path / "output", tmp_path / "scratch"
    output.mkdir(); scratch.mkdir()
    (scratch / "ccA012bZ.res").write_bytes(b"x" * 65537)
    assert observe_inventory(output, scratch, linker=True)["invalid"] is True


def test_build_first_invalid_sample_is_retained(tmp_path, monkeypatch):
    import scripts.run_linux_cpu_controls as runner
    output, scratch = tmp_path / "output", tmp_path / "scratch"
    output.mkdir(); scratch.mkdir()
    (scratch / "unknown.linker").write_bytes(b"untrusted private bytes")
    class Pipe:
        def fileno(self): return 123
        def close(self): pass
    class Child:
        stdout = Pipe(); stderr = Pipe()
        def poll(self): return 0
    class Selector:
        def register(self, *unused): pass
        def get_map(self): return {123: True}
        def close(self): pass
    # Authored transport doubles only; no actual compiler/controller/OS fixture.
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *a, **k: Child())
    monkeypatch.setattr(runner.selectors, "DefaultSelector", Selector)
    monkeypatch.setattr(runner.os, "set_blocking", lambda *a: None)
    stage, out, err = runner.build_capture(["authored"], output, scratch,
                                          runner.time.monotonic_ns()+10**9, linker=True)
    assert stage["held"] is not None and stage["returncode"] is None
    assert stage["first_invalid_inventory"]["invalid"] is True
    assert stage["first_invalid_inventory"]["entries"][0]["name"] == "unknown.linker"
    assert "untrusted private bytes" not in str(stage) and out == err == b""
    assert (scratch / "unknown.linker").read_bytes() == b"untrusted private bytes"


def test_build_held_cli_returns_failure_not_transport_success(monkeypatch, capsys):
    import scripts.run_linux_cpu_controls as runner
    import sys
    monkeypatch.setattr(sys, "argv", ["authored", "build", "manifest", "hash"])
    monkeypatch.setattr(runner, "run_build", lambda *unused:
                        dict(artifact_success=False, held="build_stage_failed"))
    with pytest.raises(SystemExit) as raised:
        runner.main()
    assert raised.value.code == 1
    assert '"artifact_success": false' in capsys.readouterr().out


def test_birth_and_credential_barrier(host_results):
    for name in ("nominal", "threads", "exited", "escape"):
        assert host_results[name]["birth_marker"] is True
        complete(host_results[name])
    for name in ("wrong_attempt", "wrong_object", "malformed_frame", "clone_denied", "early_ack"):
        r = host_results[name]
        assert r["birth_marker"] is False and r["release"] is None and r["returncode"] != 0
    setup = host_results["setup_denied"]
    assert setup["birth_marker"] is False and setup["returncode"] != 0


def test_exited_descendants_accounted(host_results):
    for name, minimum, entities in (("nominal", 50_000_000, 1), ("threads", 80_000_000, 5),
                                    ("exited", 180_000_000, 17)):
        f = complete(host_results[name])
        assert f[5] >= minimum
        # Independent complete wait4 family oracle. Candidate bound: two native
        # microsecond component floors per authored entity plus two cgroup floors.
        # A mismatch FAILS; do not enlarge this after observing a failed host run.
        oracle_ns = (f[16] + f[17]) * 1000
        assert oracle_ns >= minimum
        assert abs(f[2] * 1000 - oracle_ns) <= (2 * entities + 2) * 1000
    system = complete(host_results["system_cpu"])
    assert system[5] >= 200_000_000 and system[17] > 0 and system[4] > 0
    assert abs(system[2] * 1000 - (system[16] + system[17]) * 1000) <= 4000


def test_cancel_and_root_exit_descendants(host_results):
    for name, error in (("cancel", 12), ("heartbeat_loss", 14), ("grandchild", 16)):
        f = complete(host_results[name], error)
        assert f[14] >= f[13] > 0 and f[12] - f[13] <= 250_000_000
    assert host_results["grandchild"]["final"][8] >= 1
    # EOF closes the only ACK endpoint. An available failed CPU final can be
    # retained, but release is forbidden without ACK, not synthesized cleanup.
    eof = host_results["eof"]
    f = eof["final"]
    assert f is not None and f[11] == 13 and f[15] == 1 and f[6] == 0 and f[7] == 1
    assert f[14] >= f[13] > 0 and f[12] - f[13] <= 250_000_000
    assert eof["returncode"] == 13 and eof["release"] is None and eof["group_extinct"] is True
    assert all(packet[1] not in (4, 5) for packet in eof["sent"])


def test_actual_budget_and_gap(host_results):
    for name, budget, stop in (("upper60", 60_000_000_000, 57_000_000_000),
                               ("upper240", 240_000_000_000, 237_000_000_000)):
        f = complete(host_results[name], 10)
        assert stop <= f[5] <= budget
    backpressure = host_results["backpressure"]
    assert backpressure["returncode"] != 0 and backpressure["release"] is None
    for name in ("delayed_observer", "over_budget"):
        f = host_results[name]["final"]
        assert f is not None and f[11] == 9 and host_results[name]["returncode"] != 0
        assert host_results[name]["max_gap_ns"] > 20_000_000
    assert host_results["over_budget"]["final"][5] > 60_000_000_000


def test_manager_three_death_orders(host_results):
    for name in ("parent_crash", "controller_crash", "simultaneous_crash"):
        r = host_results[name]
        assert r["returncode"] != 0 and r["final"] is None and r["digest"] is None
        assert r["unit"]["MainPID"] == "0"
        assert r["unit"]["ActiveState"] in ("inactive", "failed")
        assert r["group_extinct"] is True


def test_escape_and_cross_attempt(host_results):
    assert host_results["escape"]["escape_denied"] is True
    complete(host_results["escape"])
    for name in ("wrong_attempt", "wrong_object"):
        assert host_results[name]["birth_marker"] is False


def test_final_custody_and_resource_failures(host_results):
    for name in ("bad_ack", "no_ack"):
        r = host_results[name]
        assert r["final"] is not None and r["digest"] is not None
        assert r["returncode"] != 0 and r["release"] is None
    output = host_results["output"]
    assert output["returncode"] != 0 and output["final"][11] == 15
    oom = host_results["oom"]
    assert oom["returncode"] != 0 and oom["final"][11] == 22 and oom["final"][20] > 0
