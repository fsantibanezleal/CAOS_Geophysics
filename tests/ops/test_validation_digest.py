"""Authored reader controls; these fixtures are not scientific run receipts."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validation_digest.py"
spec = importlib.util.spec_from_file_location("validation_digest", SCRIPT)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
custody = reader.custody


def write(path, value):
    path.write_bytes(custody.canonical(value))


def fixture(root, statuses=("PASS",), log=b"private case data\n"):
    cache, reports = root / "cache", root / "reports"
    cache.mkdir()
    reports.mkdir()
    rows = []
    for index, status in enumerate(statuses):
        name = f"node{index}"
        if status in {"BLOCKED", "REFUSED"}:
            rows.append({"id": name, "fingerprint": "a" * 64, "evidence": None, "status": status,
                         "action": "blocked" if status == "BLOCKED" else "refused", "reason": "prerequisite failed"})
            continue
        needs = [rows[-1]["id"]] if rows and rows[-1]["status"] == "PASS" else []
        predecessors = {row["id"]: {key: row[key] for key in ("fingerprint", "evidence", "status")}
                        for row in rows if row["id"] in needs}
        plan = {"base": {"node": {"id": name, "needs": needs}}, "predecessors": predecessors}
        fingerprint = custody.digest(custody.canonical(plan))
        entry = cache / fingerprint
        entry.mkdir()
        write(entry / "plan.json", plan)
        (entry / "stdout.bin").write_bytes(log)
        (entry / "stderr.bin").write_bytes(b"failed assertion\n" if status == "FAIL" else b"")
        receipt = {"schema": 1, "fingerprint": fingerprint, "status": status, "reason": "exit",
                   "returncode": 0 if status == "PASS" else 1, "elapsed_s": 0.125, "captured_bytes": len(log)}
        write(entry / "receipt.json", receipt)
        seal = {name: custody.file_record(entry / name)
                for name in ("plan.json", "receipt.json", "stdout.bin", "stderr.bin")}
        write(entry / "seal.json", seal)
        rows.append({"id": name, "fingerprint": fingerprint, "evidence": custody.digest(custody.canonical(seal)),
                     "status": status, "reason": "exit", "returncode": receipt["returncode"],
                     "action": "started", "receipt": str(entry / "receipt.json")})
    path = reports / "report.json"
    report = {"schema": 1, "config_sha256": "b" * 64, "nodes": rows, "report": str(path)}
    write(path, report)
    return path, report


def test_read_only_digest(tmp_path, monkeypatch):
    path, _ = fixture(tmp_path, ("PASS", "PASS"))
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    def forbidden(*args, **kwargs):
        raise AssertionError("reader must not execute or inventory current sources")
    monkeypatch.setattr(custody, "execute", forbidden)
    monkeypatch.setattr(custody, "inventory", forbidden)
    monkeypatch.setattr(custody, "snapshot", forbidden)
    result = reader.inspect(str(path), str(tmp_path))
    assert result["counts"] == {"PASS": 2, "FAIL": 0, "BLOCKED": 0, "REFUSED": 0}
    assert result["evidence_verified"] and result["all_commands_passed"]
    assert not result["current_sources_verified"]
    assert not result["scientific_acceptance"] and not result["deployment_acceptance"]
    assert result["first_failure"] is None and "private" not in json.dumps(result)
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert reader.main(["--report", str(path), "--device-root", str(tmp_path)]) == 0


def test_failure_and_blocked_digest(tmp_path):
    path, _ = fixture(tmp_path, ("PASS", "FAIL", "BLOCKED", "REFUSED"))
    result = reader.inspect(str(path), str(tmp_path))
    assert result["counts"] == {"PASS": 1, "FAIL": 1, "BLOCKED": 1, "REFUSED": 1}
    assert result["first_failure"]["id"] == "node1"
    assert not result["all_commands_passed"] and "private_failure_tail" not in result
    assert reader.main(["--report", str(path), "--device-root", str(tmp_path)]) == 1


@pytest.mark.parametrize("target", ["stdout.bin", "stderr.bin", "receipt.json", "plan.json", "seal.json",
                                   "report_status", "report_evidence", "report_fingerprint", "report_schema",
                                   "report_duplicate", "report_unknown", "report_path", "missing_receipt"])
def test_tampered_evidence_refused(tmp_path, target):
    path, report = fixture(tmp_path)
    entry = Path(report["nodes"][0]["receipt"]).parent
    if target.endswith(".bin"):
        (entry / target).write_bytes(b"changed")
    elif target.endswith(".json"):
        (entry / target).write_bytes(b"{}")
    elif target == "report_status":
        report["nodes"][0]["status"] = "FAIL"
    elif target == "report_evidence":
        report["nodes"][0]["evidence"] = "c" * 64
    elif target == "report_fingerprint":
        report["nodes"][0]["fingerprint"] = "c" * 64
    elif target == "report_schema":
        report["schema"] = True
    elif target == "report_duplicate":
        report["nodes"] *= 2
    elif target == "report_unknown":
        report["nodes"][0]["extra"] = 1
    elif target == "report_path":
        report["report"] = str(path.parent / "other.json")
    else:
        (entry / "receipt.json").unlink()
    write(path, report)
    with pytest.raises((custody.Refusal, OSError)):
        reader.inspect(str(path), str(tmp_path))
    assert reader.main(["--report", str(path), "--device-root", str(tmp_path)]) == 2


def test_predecessor_binding_refused(tmp_path):
    path, report = fixture(tmp_path, ("PASS", "PASS"))
    # Alter only the earlier report binding; sealed descendant still binds the original.
    report["nodes"][0] = {"id": "node0", "fingerprint": "c" * 64, "evidence": None,
                          "status": "REFUSED", "action": "refused", "reason": "operator refusal"}
    write(path, report)
    with pytest.raises(custody.Refusal, match="predecessor evidence"):
        reader.inspect(str(path), str(tmp_path))


def test_explicit_bounded_tail(tmp_path):
    path, _ = fixture(tmp_path, ("FAIL",), log=b"x" * 12000 + b"last error")
    result = reader.inspect(str(path), str(tmp_path), tail_bytes=4096)
    tail = result["private_failure_tail"]["stdout.bin"]
    assert tail["bytes"] == 4096 and tail["truncated"] and tail["text"].endswith("last error")
    assert result["private_failure_tail"]["stderr.bin"]["bytes"] == 17
    for invalid in (True, -1, 4097, 1.0):
        with pytest.raises(custody.Refusal):
            reader.inspect(str(path), str(tmp_path), tail_bytes=invalid)


def test_unfinished_report_refused(tmp_path):
    with pytest.raises(custody.Refusal, match="missing path"):
        reader.inspect(str(tmp_path / "missing.json"), str(tmp_path))


def test_output_is_exclusive(tmp_path):
    path, _ = fixture(tmp_path)
    output = tmp_path / "digest.json"
    argv = ["--report", str(path), "--device-root", str(tmp_path), "--output", str(output)]
    assert reader.main(argv) == 0
    original = output.read_bytes()
    assert json.loads(original)["evidence_verified"] is True
    assert reader.main(argv) == 2
    assert output.read_bytes() == original
