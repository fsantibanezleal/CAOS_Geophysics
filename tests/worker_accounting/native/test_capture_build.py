"""Build-helper supplied-data/scratch tests; never launch a compiler or DLL.

Fresh pytest-owned scratch only. No real OS containment/CPU/ABI measurement.
"""
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import threading

import pytest

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "scripts/native_physical_cpu/capture_build.py"


@pytest.fixture
def helper():
    spec = importlib.util.spec_from_file_location("_i01_capture_review", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest(helper):
    return {
        "schema": "i01-build-approval-2", "source_commit": "a" * 40,
        "execute_i01_build": True,
        "source_hashes": dict.fromkeys(helper.SOURCE_FILES, "b" * 64),
        "roots": dict.fromkeys(("source", "output", "scratch", "outcome", "vc", "sdk", "system"), "reviewed"),
        "tree_files": [{f"header{i}.h": "c" * 64 for i in range(count)}
                       for count in helper.TREE_COUNTS],
    }


def read_manifest(helper, tmp_path, value):
    raw = json.dumps(value, sort_keys=True).encode("utf-8")
    path = tmp_path / "private-approval.json"
    path.write_bytes(raw)
    return helper.approval(path, hashlib.sha256(raw).hexdigest())


def test_manifest_exact_shape_roundtrip(helper, tmp_path):
    value = manifest(helper)
    assert read_manifest(helper, tmp_path, value) == value


@pytest.mark.parametrize("change", ["extra", "unknown-source", "missing-source", "bad-sha", "bool-pin",
                                    "flag-int", "unknown-schema", "bad-commit", "unknown-root",
                                    "tree-count", "tree-parent", "tree-absolute", "tree-extra", "tree-sha"])
def test_manifest_unknown_or_malformed_closed(helper, tmp_path, change):
    value = manifest(helper)
    if change == "extra": value["extra"] = True
    elif change == "unknown-source": value["source_hashes"]["outside.py"] = "b" * 64
    elif change == "missing-source": value["source_hashes"].pop(helper.SOURCE_FILES[0])
    elif change == "bad-sha": value["source_hashes"][helper.SOURCE_FILES[0]] = "B" * 64
    elif change == "bool-pin": value["source_hashes"][helper.SOURCE_FILES[0]] = True
    elif change == "flag-int": value["execute_i01_build"] = 1
    elif change == "unknown-schema": value["schema"] = "i01-build-approval-1"
    elif change == "bad-commit": value["source_commit"] = "a" * 39
    elif change == "unknown-root": value["roots"]["other"] = "reviewed"
    elif change == "tree-count": value["tree_files"].pop()
    elif change in {"tree-parent", "tree-absolute"}:
        tree = value["tree_files"][0]
        tree.pop("header0.h")
        tree["../header0.h" if change == "tree-parent" else "/header0.h"] = "c" * 64
    elif change == "tree-extra": value["tree_files"][0]["extra.h"] = "c" * 64
    elif change == "tree-sha": value["tree_files"][0]["header0.h"] = False
    with pytest.raises(helper.BuildHeld, match="^build_approval_invalid$"):
        read_manifest(helper, tmp_path, value)


def test_manifest_hash_binds_same_bytes_parsed(helper, tmp_path):
    path = tmp_path / "private-approval.json"
    raw = json.dumps(manifest(helper)).encode("ascii")
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    path.write_bytes(raw.replace(b"a" * 40, b"d" * 40))
    with pytest.raises(helper.BuildHeld, match="^build_approval_invalid$"):
        helper.approval(path, digest)


def test_actual_source_hash_mismatch_before_tool_launch(helper, tmp_path, monkeypatch):
    source, vc, sdk = (tmp_path / name for name in ("source", "vc", "sdk"))
    for path in (source, vc, sdk):
        path.mkdir()
    first = source / helper.SOURCE_FILES[0]
    first.parent.mkdir(parents=True)
    first.write_bytes(b"changed source")
    original_hash = helper.file_hash
    def supplied_hash(path):
        return helper.PYTHON_PIN if path == Path(sys.executable) else original_hash(path)
    monkeypatch.setattr(helper, "file_hash", supplied_hash)
    def forbidden(*args, **kwargs):
        pytest.fail("tool launch during source rejection")
    monkeypatch.setattr(helper.subprocess, "Popen", forbidden)
    with pytest.raises(helper.BuildHeld, match="^build_source_changed$"):
        helper.verify_inputs(source, vc, sdk, manifest(helper))


def test_manifest_raw_limit_before_parser(helper, tmp_path, monkeypatch):
    path = tmp_path / "private-approval.json"
    path.write_bytes(b" " * (helper.STREAM_CAP + 1))
    def forbidden(*args, **kwargs):
        pytest.fail("parser called for an over-limit manifest")
    monkeypatch.setattr(helper.json, "loads", forbidden)
    with pytest.raises(helper.BuildHeld, match="^build_approval_invalid$"):
        helper.approval(path, "a" * 64)


def test_duplicate_decoded_manifest_key_rejected(helper, tmp_path):
    raw = b'{"roots":{},"r\\u006fots":{}}'
    path = tmp_path / "private-approval.json"
    path.write_bytes(raw)
    with pytest.raises(helper.BuildHeld, match="^build_approval_invalid$"):
        helper.approval(path, hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize("extra", [0, 1])
def test_stream_preappend_cap(helper, extra):
    stopped, failed = threading.Event(), threading.Event()
    data = bytearray()
    stream = io.BytesIO(b"x" * (helper.STREAM_CAP + extra))
    helper.drain(stream, data, stopped, failed, threading.Lock())
    assert len(data) == helper.STREAM_CAP
    assert failed.is_set() is bool(extra)
    assert stream.closed


def test_stopped_reader_cannot_mutate_receipt_buffer(helper):
    stopped, failed = threading.Event(), threading.Event()
    stopped.set()
    data = bytearray(b"prior")
    stream = io.BytesIO(b"later")
    helper.drain(stream, data, stopped, failed, threading.Lock())
    assert data == b"prior" and not failed.is_set() and stream.closed


def test_output_never_overwrites_or_deletes(helper, tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    path = output / "stage1.stdout"
    path.write_bytes(b"retained")
    with pytest.raises(FileExistsError):
        helper.write_new(output, path.name, b"replacement")
    assert path.read_bytes() == b"retained"


def test_existing_output_root_rejected_before_launch(helper, tmp_path, monkeypatch):
    paths = {key: tmp_path / key for key in ("source", "output", "vc", "sdk")}
    paths["system"] = tmp_path / "Windows"
    paths["scratch"] = tmp_path / "scratch"
    paths["outcome"] = tmp_path / "outcome"
    for key, path in paths.items():
        if key in {"scratch", "outcome"}: continue
        path.mkdir()
    (paths["system"] / "System32").mkdir()
    prior = paths["output"] / "retained.private"
    prior.write_bytes(b"do not replace")
    binding = manifest(helper)
    binding["roots"] = {key: str(path) for key, path in paths.items()}
    monkeypatch.setattr(helper, "verify_inputs", lambda *args: None)
    def forbidden(*args, **kwargs):
        pytest.fail("tool launch with an existing output root")
    monkeypatch.setattr(helper.subprocess, "Popen", forbidden)
    with pytest.raises(helper.BuildHeld, match="^build_output_invalid$"):
        helper.run(*(paths[key] for key in ("source", "output", "vc", "sdk", "system")), binding,
                   scratch=paths["scratch"], outcome=paths["outcome"])
    assert prior.read_bytes() == b"do not replace"


def test_observed_file_count_exceeded(helper, tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    (output / "core.obj").write_bytes(b"a")
    (output / "abi.obj").write_bytes(b"b")
    monkeypatch.setattr(helper, "FILE_CAP", 1)
    with pytest.raises(helper.BuildHeld, match="^build_output_invalid$"):
        helper.output_size(output)


@pytest.mark.parametrize("name", ["outside.txt", "../stage1.stdout", "core.dll/child"])
def test_unknown_output_name_closed(helper, tmp_path, name):
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(helper.BuildHeld, match="^build_output_exceeded$"):
        helper.write_new(output, name, b"x")
    assert list(output.iterdir()) == []


def test_output_prewrite_remaining_bytes(helper, tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    (output / "core.obj").write_bytes(b"1234567")
    monkeypatch.setattr(helper, "OUTPUT_CAP", 8)  # helper logic control, not production policy change
    with pytest.raises(helper.BuildHeld, match="^build_output_exceeded$"):
        helper.write_new(output, "stage1.stdout", b"xx")
    assert not (output / "stage1.stdout").exists()
    assert (output / "core.obj").read_bytes() == b"1234567"


@pytest.mark.parametrize("kind", ["unknown-file", "directory"])
def test_output_unknown_tree_closed(helper, tmp_path, kind):
    output = tmp_path / "output"
    output.mkdir()
    if kind == "unknown-file": (output / "other").write_bytes(b"x")
    else: (output / "core.obj").mkdir()
    with pytest.raises(helper.BuildHeld, match="^build_output_invalid$"):
        helper.output_size(output)


def test_relative_parent_traversal_never_reaches_file_access(helper):
    for path in (Path("relative"), Path.cwd() / ".." / "elsewhere"):
        with pytest.raises(helper.BuildHeld, match="^build_path_invalid$"):
            helper.safe_path(path)


def test_fixed_recipe_no_execute_or_fallback(helper):
    plans = helper.recipe(Path("source"), Path("output"), Path("vc"), Path("sdk"))
    assert len(plans) == 4
    assert [Path(p[0]).name for p in plans] == ["cl.exe", "link.exe", "cl.exe", "link.exe"]
    for plan in plans[::2]:
        assert {"/MT", "/X", "/std:c17", "/W4", "/WX", "/showIncludes"} <= set(plan)
        assert "/MD" not in plan and not any(p.startswith("@") for p in plan)
    for plan in plans[1::2]:
        assert "/NODEFAULTLIB" in plan and "/FORCE" not in plan
        assert len([p for p in plan if p.endswith(".lib") and not p.startswith("/IMPLIB:")]) == 5
    assert not any(Path(p[0]).name in {"abi.exe", "core.dll"} for p in plans)


def test_source_scope_no_hidden_launch_loader_or_removal():
    text = HELPER.read_text("utf-8")
    tree = ast.parse(text)
    launches = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and
                isinstance(n.func, ast.Attribute) and n.func.attr == "Popen"]
    assert len(launches) == 1
    args = {v.arg: v.value for v in launches[0].keywords}
    assert isinstance(args["shell"], ast.Constant) and args["shell"].value is False
    assert isinstance(args["close_fds"], ast.Constant) and args["close_fds"].value is True
    assert "descendant_drain_proven\": False" in text
    assert "compiled_tests\": \"NOT_RUN\"" in text and "abi_execution\": \"NOT_RUN\"" in text
    assert not re.search(r"\b(?:CDLL|WinDLL|LoadLibrary|exec|eval|rmtree|unlink|remove)\s*\(", text)
    assert [n for n in tree.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)] == []


def workspace(tmp_path):
    output, scratch = tmp_path / "output", tmp_path / "scratch"
    output.mkdir()
    scratch.mkdir()
    return output, scratch


def telemetry(scratch):
    (scratch / "Microsoft/VSApplicationInsights" / ("vstelf" + "a" * 32)).mkdir(parents=True)


def test_observed_empty_telemetry_only_not_arbitrary_allowlist(helper, tmp_path):
    output, scratch = workspace(tmp_path)
    telemetry(scratch)
    (output / "core.obj").write_bytes(b"object")
    report = helper.observe_workspace(output, scratch)
    assert report["held"] is None and report["complete"] is True
    assert (report["files"], report["directories"], report["file_bytes"]) == (1, 3, 6)
    assert len(report["entries"]) == 4
    unknown = scratch / "Microsoft/VSApplicationInsights" / ("vstelf" + "a" * 32) / "unknown.bin"
    unknown.write_bytes(b"private")
    report = helper.observe_workspace(output, scratch)
    assert report["held"] == "build_scratch_invalid"
    assert report["complete"] is True and report["file_bytes"] == 13
    assert unknown.read_bytes() == b"private"


@pytest.mark.parametrize("name", ["other", "Microsoft/other", "Microsoft/VSApplicationInsights/vstelfz",
                                 "Microsoft/VSApplicationInsights/vstelf" + "A" * 32])
def test_unknown_scratch_directory_retained_closed(helper, tmp_path, name):
    output, scratch = workspace(tmp_path)
    (scratch / name).mkdir(parents=True)
    assert helper.observe_workspace(output, scratch)["held"] == "build_scratch_invalid"
    assert (scratch / name).is_dir()


def test_combined_bytes_and_files_include_quarantined_scratch(helper, tmp_path, monkeypatch):
    output, scratch = workspace(tmp_path)
    (output / "core.obj").write_bytes(b"1234")
    (scratch / "unknown").write_bytes(b"56789")
    monkeypatch.setattr(helper, "OUTPUT_CAP", 8)
    report = helper.observe_workspace(output, scratch)
    assert report["held"] and report["file_bytes"] == 9 and report["files"] == 2
    assert report["complete"] is False  # stopped on exceeded bound
    monkeypatch.setattr(helper, "OUTPUT_CAP", 64)
    monkeypatch.setattr(helper, "FILE_CAP", 1)
    assert helper.observe_workspace(output, scratch)["complete"] is False


@pytest.mark.parametrize("limit", ["ENTRY_CAP", "DEPTH_CAP", "NAME_CAP"])
def test_diagnostic_walk_bounded_before_accumulation(helper, tmp_path, monkeypatch, limit):
    output, scratch = workspace(tmp_path)
    telemetry(scratch)
    monkeypatch.setattr(helper, limit, 1)
    report = helper.observe_workspace(output, scratch)
    assert report["held"] and report["complete"] is False
    assert len(report["entries"]) <= helper.ENTRY_CAP


def test_multiple_dynamic_telemetry_leaves_not_accepted(helper, tmp_path):
    output, scratch = workspace(tmp_path)
    telemetry(scratch)
    (scratch / "Microsoft/VSApplicationInsights" / ("vstelf" + "b" * 32)).mkdir()
    assert helper.observe_workspace(output, scratch)["held"] == "build_scratch_invalid"


def test_hardlinked_file_rejected_without_read(helper, tmp_path):
    import os
    output, scratch = workspace(tmp_path)
    original = tmp_path / "original"
    original.write_bytes(b"retained")
    os.link(original, output / "core.obj")
    report = helper.observe_workspace(output, scratch)
    assert report["held"] == "build_path_invalid" and report["complete"] is False
    with pytest.raises(helper.BuildHeld, match="build_path_invalid"):
        helper.file_hash(output / "core.obj")
    assert original.read_bytes() == b"retained"


def run_context(helper, tmp_path, monkeypatch):
    paths = {key: tmp_path / key for key in ("source", "output", "scratch", "outcome", "vc", "sdk")}
    paths["system"] = tmp_path / "Windows"
    for key in ("source", "vc", "sdk", "system"):
        paths[key].mkdir()
    (paths["system"] / "System32").mkdir()
    binding = manifest(helper)
    binding["roots"] = {key: str(path) for key, path in paths.items()}
    monkeypatch.setattr(helper, "verify_inputs", lambda *args: None)
    return paths, binding


def invoke(helper, paths, binding):
    return helper.run(*(paths[k] for k in ("source", "output", "vc", "sdk", "system")), binding,
                      scratch=paths["scratch"], outcome=paths["outcome"])


@pytest.mark.parametrize("root", ["output", "scratch", "outcome"])
def test_all_tool_and_receipt_roots_exclusive(helper, tmp_path, monkeypatch, root):
    paths, binding = run_context(helper, tmp_path, monkeypatch)
    paths[root].mkdir()
    prior = paths[root] / "prior"
    prior.write_bytes(b"retained")
    monkeypatch.setattr(helper.subprocess, "Popen", lambda *a, **kw: pytest.fail("unexpected launch"))
    with pytest.raises(helper.BuildHeld, match="build_output_invalid"):
        invoke(helper, paths, binding)
    assert prior.read_bytes() == b"retained"


@pytest.mark.parametrize("nested", ["equal", "output-in-scratch", "outcome-in-output", "scratch-in-source"])
def test_root_overlap_closed_before_creation(helper, tmp_path, monkeypatch, nested):
    paths, binding = run_context(helper, tmp_path, monkeypatch)
    if nested == "equal": paths["scratch"] = paths["output"]
    elif nested == "output-in-scratch": paths["output"] = paths["scratch"] / "nested"
    elif nested == "outcome-in-output": paths["outcome"] = paths["output"] / "nested"
    else: paths["scratch"] = paths["source"] / "nested"
    binding["roots"] = {key: str(path) for key, path in paths.items()}
    with pytest.raises(helper.BuildHeld):
        invoke(helper, paths, binding)
    assert not paths["outcome"].exists()


@pytest.mark.parametrize("failure", ["unexpected-output", "unexpected-scratch", "launch", "input", "log-write"])
def test_external_receipt_survives_failed_tool_roots(helper, tmp_path, monkeypatch, failure):
    paths, binding = run_context(helper, tmp_path, monkeypatch)
    calls = []
    def supplied_capture(args, output, environment, *, scratch):
        calls.append(args)
        assert environment["TEMP"] == environment["TMP"] == str(paths["scratch"])
        assert set(environment) == {"SystemRoot", "TEMP", "TMP", "PATH"}
        assert (paths["outcome"] / "build.json").exists()  # custody reserved before launch
        assert paths["outcome"] not in (output, scratch)
        if failure == "launch": raise OSError("SECRET PRIVATE PATH")
        if failure == "unexpected-output": (output / "Microsoft").mkdir()
        if failure == "unexpected-scratch": (scratch / "unknown.bin").write_bytes(b"secret")
        return {"returncode": 0, "wall_ms": 0.0, "held": None,
                "streams": (b"private stream", b""), "descendant_drain_proven": False}
    monkeypatch.setattr(helper, "capture", supplied_capture)
    if failure == "input":
        monkeypatch.setattr(helper, "verify_inputs", lambda *a: (_ for _ in ()).throw(helper.BuildHeld("build_source_changed")))
    if failure == "log-write":
        monkeypatch.setattr(helper, "write_new", lambda *a, **kw: (_ for _ in ()).throw(OSError("SECRET PRIVATE PATH")))
    assert invoke(helper, paths, binding) == 1
    raw = (paths["outcome"] / "build.json").read_bytes()
    receipt = json.loads(raw)
    assert len(raw) <= helper.RECEIPT_CAP and b"SECRET PRIVATE PATH" not in raw
    assert b"private stream" not in raw
    assert receipt["held"] and receipt["artifacts"] is None
    assert receipt["recipe_completed"] is False and receipt["artifact_success"] is False
    assert receipt["runtime_authorized"] is False
    assert len(calls) <= 1 and receipt["abi_execution"] == "NOT_RUN"
    if failure in {"unexpected-output", "unexpected-scratch", "log-write"}:
        assert receipt["stages"][0]["stream_bytes"] == [14, 0]
    if failure == "unexpected-scratch":
        assert receipt["workspace"]["file_bytes"] == 6
        assert (paths["scratch"] / "unknown.bin").read_bytes() == b"secret"


def test_same_size_mutation_during_hash_rejected(helper, tmp_path, monkeypatch):
    path = tmp_path / "observed"
    path.write_bytes(b"original")
    real_open = Path.open
    class ChangingReader:
        def __init__(self): self.stream = real_open(path, "rb")
        def __enter__(self): return self
        def __exit__(self, *args): self.stream.close()
        def read(self, count):
            data = self.stream.read(count)
            if data:
                with real_open(path, "wb") as writer: writer.write(b"modified")
            return data
        def fileno(self): return self.stream.fileno()
    monkeypatch.setattr(Path, "open", lambda p, *a, **kw: ChangingReader() if p == path else real_open(p, *a, **kw))
    with pytest.raises(helper.BuildHeld, match="build_file_changed"):
        helper.file_hash(path)
