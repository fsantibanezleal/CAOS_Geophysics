"""Runner protocol controls. Fake process here is not numerical acceptance."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location("original_prerequisite_gate", Path(__file__).parents[2] / "scripts/magnetic_original_prerequisite_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def setup(tmp_path, monkeypatch, changed=False):
    monkeypatch.setattr(gate, "inventory", lambda *roots: {"public/" + name + ".py": "b"*64 if changed else "a"*64 for name in gate.PUBLIC})
    raw = gate.canonical(dict(schema="magnetic-original-sparse-firstfit-prerequisite-1", status="failed",
        reason="wall_cap", full_matrix_run=False, sources={name: "a"*64 for name in gate.PUBLIC}))
    predecessor = tmp_path / "original-failed.json"
    predecessor.write_bytes(raw)
    output = tmp_path / "cache"
    output.mkdir()
    return dict(scientific_root=Path(__file__).parents[2], public_root=tmp_path, line_root=tmp_path,
        python=Path("python.exe").resolve(), output=output, failed_receipt=predecessor, failed_sha=gate.sha(raw))


def test_unchanged_public_failure_stops_before_launch(tmp_path, monkeypatch):
    args = setup(tmp_path, monkeypatch)
    def never(*a, **kw): raise AssertionError("Unchanged known failure was rerun")
    result = gate.run_gate(**args, execute=never)
    assert result["status"] == "blocked_unchanged_public_failure" and result["launched"] == []
    assert list(args["output"].iterdir()) == []


@pytest.mark.parametrize("failed", [False, True])
def test_fail_first_sequence_and_exact_cache(tmp_path, monkeypatch, failed):
    args = setup(tmp_path, monkeypatch, changed=True)
    calls = []
    def execute(argv, **kw):
        calls.append(argv[5])
        xml = Path(argv[-1]); xml.write_text('<testsuites><testsuite tests="1" failures="%d" errors="0" skipped="0"/></testsuites>' % failed)
        return SimpleNamespace(returncode=int(failed))
    first = gate.run_gate(**args, execute=execute)
    assert len(calls) == (1 if failed else 2)
    assert first["local_prerequisites_passed"] is not failed
    assert first["full_matrix_unlocked"] is False and first["science_admitted"] is False
    second = gate.run_gate(**args, execute=lambda *a, **kw: pytest.fail("cache reran a job"))
    assert second == first


@pytest.mark.parametrize("attack", ["missing", "bytes", "source"])
def test_changed_source_and_incomplete_cache_refuse(tmp_path, monkeypatch, attack):
    args = setup(tmp_path, monkeypatch, changed=True)
    def execute(argv, **kw):
        Path(argv[-1]).write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"/></testsuites>')
        return SimpleNamespace(returncode=0)
    result = gate.run_gate(**args, execute=execute)
    cache = args["output"] / result["fingerprint"]
    if attack == "missing": (cache / "receipt.json").unlink()
    if attack == "bytes": (cache / "firstfold.xml").write_bytes(b"drift")
    if attack == "source":
        counter = [0]
        def changed(*a):
            counter[0] += 1
            return result["sources"] if counter[0] == 1 else {**result["sources"], "drift": "c"*64}
        monkeypatch.setattr(gate, "inventory", changed)
        # Fresh external cache so this is actual mid-run drift, not reuse.
        args["output"] = tmp_path / "new-cache"; args["output"].mkdir()
        assert gate.run_gate(**args, execute=execute)["status"] == "failed_gate"
    else:
        with pytest.raises(ValueError): gate.run_gate(**args, execute=execute)
