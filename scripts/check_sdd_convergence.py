"""Validate the replacement SDD ledger; release acceptance is a separate mode.

Stdlib only. Never execute a test, solver, training job or download here.
This checks receipt integrity and declared coverage, not scientific correctness.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
VERDICTS = {"pass", "fail", "unresolved", "ineligible"}
REQUIREMENT = re.compile(r"^(R-\d{3})\s+THE\b.*?\s+Gate:\s*(.+?)\s*$", re.M)
ALTERNATE = re.compile(r"^(R-\d{3})\s+(?:WHEN|IF)\b.*?\s+Gate:\s*(.+?)\s*$", re.M)
GATE = re.compile(r"(?P<file>(?:scripts|tests|frontend|docs)/[\w./-]+\.(?:py|ts|json|md))(?:::(?P<symbol>[A-Za-z_]\w*(?:(?:\.|::)[A-Za-z_]\w*)*))?")
SHA = re.compile(r"^[0-9a-f]{64}$")


class LedgerError(ValueError):
    """An evidence claim does not satisfy the contract."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_json(path: Path) -> dict:
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise LedgerError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    def invalid_constant(value):
        raise LedgerError(f"nonfinite JSON constant: {value}")

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=invalid_constant)
    if not isinstance(value, dict):
        raise LedgerError("ledger/receipt must be an object")
    return value


def checked_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise LedgerError("evidence paths must be nonblank repository-relative POSIX paths")
    rel = Path(value)
    if rel.is_absolute() or ".." in rel.parts or re.match(r"^[A-Za-z]:", value):
        raise LedgerError(f"evidence path escapes repository: {value}")
    path = root.joinpath(rel)
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise LedgerError(f"missing or escaping evidence: {value}")
    return path


def checked_hash(path: Path, expected: str) -> None:
    if not isinstance(expected, str) or not SHA.fullmatch(expected) or digest(path) != expected:
        raise LedgerError(f"evidence hash mismatch: {path.name}")


def declarations(sdd: Path) -> dict[str, str]:
    text = sdd.read_text(encoding="utf-8")
    section = text.split("## 9. EARS requirements and named failing gates", 1)
    if len(section) != 2:
        raise LedgerError("product SDD has no EARS gate section")
    section = section[1].split("\n## ", 1)[0]
    items = sorted(REQUIREMENT.findall(section) + ALTERNATE.findall(section))
    result = {}
    for key, gate in items:
        if key in result or not GATE.search(gate):
            raise LedgerError(f"duplicate requirement or missing named gate: {key}")
        result[key] = gate
    declared_ids = re.findall(r"^(R-\d{3})\b", section, re.M)
    if not result or len(result) != len(declared_ids):
        raise LedgerError("unparsed EARS requirement or missing gate")
    return result


def executable_gate(root: Path, name: str) -> Path:
    match = GATE.fullmatch(name)
    if match is None:
        raise LedgerError(f"invalid gate name: {name}")
    path = checked_path(root, match["file"])
    if path.suffix == ".py" and match["symbol"]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        node = tree
        for part in re.split(r"::|\.", match["symbol"]):
            node = next((child for child in getattr(node, "body", [])
                         if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                         and child.name == part), None)
            if node is None:
                raise LedgerError(f"missing executable Python gate: {name}")
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            raise LedgerError(f"gate is not executable: {name}")
    return path


def method_declarations(sdd: Path) -> dict[str, list[str]]:
    """Expand R-008's explicit reference to the M01-M13 acceptance table."""
    text = sdd.read_text(encoding="utf-8")
    rows = re.findall(r"^\| (M\d{2}) \|[^\n]+\| ([^|]+) \|\s*$", text, re.M)
    result = {}
    for key, gate in rows:
        matches = list(GATE.finditer(gate))
        if key in result or not matches:
            raise LedgerError(f"duplicate method or missing method gate: {key}")
        result[key] = [match.group() for match in matches]
    if set(result) != {f"M{i:02d}" for i in range(1, 14)}:
        raise LedgerError("product method acceptance table is not complete M01-M13")
    return result


def validate(root: Path, ledger: dict, *, require_release: bool = False) -> dict[str, int]:
    if ledger.get("schema") != "geophysics.sdd-convergence/v1":
        raise LedgerError("unknown convergence schema")
    sdd = checked_path(root, ledger.get("sdd_path"))
    checked_hash(sdd, ledger.get("sdd_sha256"))
    declared = declarations(sdd)
    revision = ledger.get("assessed_revision", "")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise LedgerError("assessment must name a full source revision")
    try:
        datetime.fromisoformat(ledger["assessed_at"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise LedgerError("assessment must name an ISO timestamp") from exc
    records = ledger.get("requirements")
    if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
        raise LedgerError("requirements must be an object list")
    ids = [record.get("id") for record in records]
    if len(set(ids)) != len(ids) or set(ids) != set(declared):
        raise LedgerError("requirement coverage differs from the current SDD")
    counts = dict.fromkeys(sorted(VERDICTS), 0)
    for record in records:
        key = record["id"]
        verdict = record.get("verdict")
        if verdict not in VERDICTS or record.get("declared_gate") != declared[key]:
            raise LedgerError(f"invalid verdict or gate drift: {key}")
        if not isinstance(record.get("note"), str) or not record["note"].strip():
            raise LedgerError(f"missing scope note: {key}")
        evidence = record.get("evidence")
        if not isinstance(evidence, list):
            raise LedgerError(f"missing evidence list: {key}")
        for item in evidence:
            if not isinstance(item, dict):
                raise LedgerError(f"invalid evidence: {key}")
            checked_hash(checked_path(root, item.get("path")), item.get("sha256"))
        receipts = record.get("receipts")
        if not isinstance(receipts, list):
            raise LedgerError(f"missing receipts list: {key}")
        gate_matches = list(GATE.finditer(declared[key]))
        if key == "R-008":
            gate_matches.extend(GATE.fullmatch(name) for names in method_declarations(sdd).values() for name in names)
        required = {m.group() for m in gate_matches if Path(m["file"]).suffix in {".py", ".ts"}}
        # A document is a required artifact, not an executable invocation. The
        # ledger validates itself structurally; hashing its own receipt inside
        # itself would require an impossible cryptographic fixed point.
        artifacts = {m["file"] for m in gate_matches if Path(m["file"]).suffix in {".json", ".md"}
                     and not (key == "R-018" and m["file"] == "docs/design/convergence.json")}
        executed = set()
        for item in receipts:
            if not isinstance(item, dict):
                raise LedgerError(f"invalid receipt reference: {key}")
            path = checked_path(root, item.get("path"))
            checked_hash(path, item.get("sha256"))
            receipt = strict_json(path)
            name = receipt.get("gate")
            if name not in required or name in executed:
                raise LedgerError(f"unknown or duplicate measured gate: {key}")
            if (receipt.get("schema") != "geophysics.gate-receipt/v1"
                    or receipt.get("requirement") != key or receipt.get("verdict") != "pass"
                    or receipt.get("source_revision") != revision
                    or not isinstance(receipt.get("command"), list) or not receipt["command"]
                    or any(not isinstance(arg, str) for arg in receipt["command"])
                    or not isinstance(receipt.get("measured_at"), str)):
                raise LedgerError(f"invalid measured receipt: {key}")
            checked_hash(executable_gate(root, name), receipt.get("gate_sha256"))
            outputs = receipt.get("outputs")
            if not isinstance(outputs, list) or not outputs:
                raise LedgerError(f"receipt has no measured output: {key}")
            for output in outputs:
                if not isinstance(output, dict):
                    raise LedgerError(f"invalid measured output: {key}")
                checked_hash(checked_path(root, output.get("path")), output.get("sha256"))
            executed.add(name)
        if verdict == "pass" and executed != required:
            raise LedgerError(f"pass lacks every named measured gate: {key}")
        if verdict == "pass" and not artifacts.issubset({item["path"] for item in evidence}):
            raise LedgerError(f"pass lacks every named evidence artifact: {key}")
        counts[verdict] += 1
    state = ledger.get("release")
    if not isinstance(state, dict) or not isinstance(state.get("application_origins"), list):
        raise LedgerError("missing release/origin state")
    if require_release and (
        counts["pass"] != len(declared) or state.get("replacement_accepted") is not True
        or state.get("class") != "vps-service" or len(state["application_origins"]) != 1
        or not re.fullmatch(r"https://[A-Za-z0-9.-]+/?", state["application_origins"][0])
        or state.get("pages_publishes_application") is not False
    ):
        raise LedgerError(f"replacement release is not accepted: {counts}; origin state={state}")
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--ledger", default="docs/design/convergence.json")
    parser.add_argument("--require-release", action="store_true")
    args = parser.parse_args(argv)
    try:
        path = checked_path(args.root, args.ledger)
        ledger = strict_json(path)
        counts = validate(args.root, ledger, require_release=args.require_release)
    except (LedgerError, OSError, ValueError, TypeError, SyntaxError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"Ledger structurally valid: {counts}. This is not scientific or release acceptance.")
    for record in ledger["requirements"]:
        if record["verdict"] != "pass":
            print(f"{record['id']}: {record['verdict']}: {record['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
