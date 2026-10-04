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
        "schema": "i01-build-approval-1", "source_commit": "a" * 40,
        "execute_i01_build": True,
        "source_hashes": dict.fromkeys(helper.SOURCE_FILES, "b" * 64),
        "roots": dict.fromkeys(("source", "output", "vc", "sdk", "system"), "reviewed"),
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
    elif change == "unknown-schema": value["schema"] = "i01-build-approval-2"
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
