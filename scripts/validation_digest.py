"""Read retained local validation evidence without running or retrying commands."""

from __future__ import annotations

import argparse
import importlib.util
import math
from pathlib import Path
import re
import sys

_spec = importlib.util.spec_from_file_location("validation_custody", Path(__file__).with_name("validate_local.py"))
custody = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(custody)
SHA = re.compile(r"[0-9a-f]{64}\Z")
STATUSES = ("PASS", "FAIL", "BLOCKED", "REFUSED")


def require(condition, message):
    custody.require(condition, message)


def bounded_tail(path, size):
    before = custody.file_record(path)
    with path.open("rb") as stream:
        stream.seek(max(0, before["bytes"] - size))
        data = stream.read(size)
    require(custody.file_record(path) == before, "diagnostic log changed during read")
    return {"bytes": len(data), "truncated": before["bytes"] > size,
            "text": data.decode("utf-8", errors="replace")}


def inspect(report_path, device_root, *, tail_bytes=0):
    require(type(tail_bytes) is int and 0 <= tail_bytes <= 4096, "tail must be 0..4096 bytes")
    root = custody.external(device_root)
    require(root.is_dir(), "device root must exist")
    path = custody.external(report_path, root)
    original = custody.file_record(path)
    report = custody.read_json(path)
    require(type(report) is dict and set(report) == {"schema", "config_sha256", "nodes", "report"}
            and type(report["schema"]) is int and report["schema"] == 1, "closed report schema required")
    require(type(report["config_sha256"]) is str and SHA.fullmatch(report["config_sha256"]), "invalid config hash")
    require(report["report"] == str(path), "report path mismatch")
    rows = report["nodes"]
    require(type(rows) is list and 1 <= len(rows) <= 64, "report requires 1..64 nodes")
    counts = {status: 0 for status in STATUSES}
    seen, compact, first_failure = {}, [], None
    diagnostic = None
    for row in rows:
        require(type(row) is dict and type(row.get("id")) is str and custody.NAME.fullmatch(row["id"])
                and row["id"] not in seen, "invalid or duplicate node id")
        require(type(row.get("status")) is str and row["status"] in STATUSES, "invalid node status")
        status = row["status"]
        fields = {"id", "fingerprint", "evidence", "status", "action", "reason"}
        completed = status in {"PASS", "FAIL"}
        require(set(row) == fields | ({"returncode", "receipt"} if completed else set()), "invalid node fields")
        require(type(row["fingerprint"]) is str and SHA.fullmatch(row["fingerprint"]), "invalid fingerprint")
        require(type(row["reason"]) is str and len(row["reason"]) <= 1000, "invalid reason")
        item = {key: row[key] for key in ("id", "status", "action", "fingerprint", "evidence")}
        item["reason"] = row["reason"][:512]
        if completed:
            require(row["action"] in {"started", "reused"}, "invalid completion action")
            receipt_path = custody.external(row["receipt"], root)
            require(receipt_path.name == "receipt.json" and receipt_path.parent.name == row["fingerprint"],
                    "receipt location mismatch")
            entry = receipt_path.parent
            plan = custody.read_json(entry / "plan.json")
            require(type(plan) is dict and set(plan) == {"base", "predecessors"}, "invalid plan")
            require(custody.digest(custody.canonical(plan)) == row["fingerprint"], "plan fingerprint mismatch")
            require(type(plan["base"]) is dict and type(plan["base"].get("node")) is dict, "invalid base")
            node = plan["base"]["node"]
            require(node.get("id") == row["id"] and type(node.get("needs")) is list, "node identity mismatch")
            require(all(type(dep) is str and dep in seen for dep in node["needs"]), "missing predecessor")
            expected = {dep: {key: seen[dep][key] for key in ("fingerprint", "evidence", "status")}
                        for dep in node["needs"]}
            require(plan["predecessors"] == expected and all(seen[dep]["status"] == "PASS" for dep in node["needs"]),
                    "predecessor evidence mismatch")
            receipt, evidence = custody.reuse(entry, plan, row["fingerprint"])
            require(evidence == row["evidence"] and all(receipt[key] == row[key]
                    for key in ("status", "reason", "returncode")), "report/receipt mismatch")
            require(type(receipt["elapsed_s"]) in {int, float} and math.isfinite(receipt["elapsed_s"])
                    and receipt["elapsed_s"] >= 0, "invalid elapsed time")
            item["elapsed_s"] = receipt["elapsed_s"]
            if status == "FAIL" and first_failure is None and tail_bytes:
                diagnostic = {name: bounded_tail(entry / name, tail_bytes) for name in ("stdout.bin", "stderr.bin")}
                # Detect a changed stream between seal verification and diagnostic reading.
                require(custody.reuse(entry, plan, row["fingerprint"])[1] == evidence, "diagnostic evidence changed")
        else:
            require(row["evidence"] is None and row["action"] == ("blocked" if status == "BLOCKED" else "refused"),
                    "invalid unexecuted node")
        if status in {"FAIL", "REFUSED"} and first_failure is None:
            first_failure = dict(item)
        seen[row["id"]] = row
        compact.append(item)
        counts[status] += 1
    require(custody.file_record(path) == original, "report changed during inspection")
    result = {"schema": "geophysics.validation-digest/v1", "report_sha256": original["sha256"],
              "config_sha256": report["config_sha256"], "counts": counts, "nodes": compact,
              "first_failure": first_failure, "all_commands_passed": counts["PASS"] == len(rows),
              "evidence_verified": True, "current_sources_verified": False,
              "scientific_acceptance": False, "deployment_acceptance": False}
    if diagnostic is not None:
        result["private_failure_tail"] = diagnostic
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    parser.add_argument("--device-root", required=True)
    parser.add_argument("--output", help="Optional new external JSON file; never overwrite existing evidence")
    parser.add_argument("--failure-tail-bytes", type=int, default=0,
                        help="Private diagnostic output only; 0..4096 bytes per stream")
    args = parser.parse_args(argv)
    try:
        result = inspect(args.report, args.device_root, tail_bytes=args.failure_tail_bytes)
        if args.output:
            output = custody.external(args.output, custody.external(args.device_root), exists=False)
            custody.exclusive(output, custody.canonical(result))
    except (custody.Refusal, OSError, ValueError, TypeError, KeyError) as error:
        print(custody.canonical({"status": "REFUSED", "reason": str(error)[:512]}).decode(), file=sys.stderr)
        return 2
    print(custody.canonical(result).decode())
    return 0 if result["all_commands_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
