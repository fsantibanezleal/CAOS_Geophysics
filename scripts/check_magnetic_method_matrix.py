"""Audit the declared M04 requirements and their executable gate references.

This is a structural inventory only. Gate presence, passing unit tests, and a
complete document do not establish scientific or field acceptance.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "docs/design/features/m04-survey-inversion/requirements.md"
REQUIREMENT_IDS = tuple(f"R-{number}" for number in range(401, 421))
GATE_REF = re.compile(
    r"^(?P<path>(?:scripts|tests|frontend|docs|notebooks)/[A-Za-z0-9_./-]+)"
    r"(?:::(?P<symbol>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*))?$"
)
REQUIREMENT = re.compile(r"^R-(\d{3})\s+")


@dataclass(frozen=True)
class GateRecord:
    requirement_id: str
    gate: str
    gate_exists: bool
    implementation: str | None
    implementation_exists: bool | None
    issue: str | None


def _python_symbols(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as error:
        raise ValueError(f"cannot parse gate source {path}: {error}") from error

    symbols: set[str] = set()

    def visit(body: list[ast.stmt], prefix: str = "") -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.add(prefix + node.name)
            elif isinstance(node, ast.ClassDef):
                visit(node.body, prefix + node.name + ".")

    visit(tree.body)
    return symbols


def _gate_parts(value: str) -> tuple[str, str | None]:
    reference = value.strip().strip("`").rstrip(".").replace("\\", "/")
    match = GATE_REF.fullmatch(reference)
    if match is None:
        raise ValueError(f"invalid M04 gate reference: {value}")
    return match.group("path"), match.group("symbol")


def _repo_path(root: Path, relative: str) -> Path:
    resolved_root = root.resolve()
    resolved = (resolved_root / Path(relative)).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"repository path escapes audit root: {relative}")
    return resolved


def _parse_requirements(text: str) -> list[tuple[str, str | None, str]]:
    """Read each numbered requirement, its optional implementation, and gate."""
    parsed: list[tuple[str, str | None, str]] = []
    current_id: str | None = None
    implementation: str | None = None
    gate: str | None = None

    def finish() -> None:
        if current_id is None:
            return
        if gate is None:
            raise ValueError(f"{current_id}: declared gate is missing")
        parsed.append((current_id, implementation, gate))

    for line in text.splitlines():
        match = REQUIREMENT.match(line)
        if match:
            finish()
            current_id = f"R-{match.group(1)}"
            implementation = None
            gate = None
            continue
        if current_id is None:
            continue
        if line.startswith("Implementation:"):
            implementation = line.partition(":")[2].strip().strip("`")
        elif line.startswith("Gate:"):
            if gate is not None:
                raise ValueError(f"{current_id}: duplicate declared gate")
            gate = line.partition(":")[2].strip().strip("`")

    finish()
    ids = tuple(item[0] for item in parsed)
    if ids != REQUIREMENT_IDS:
        raise ValueError(f"M04 requirements must enumerate R-401..R-420 in order; found {ids}")
    return parsed


def audit(requirements_path: Path = REQUIREMENTS, root: Path = ROOT) -> list[GateRecord]:
    """Check implementation-file and named-gate presence without inferring passes."""
    parsed = _parse_requirements(requirements_path.read_text(encoding="utf-8"))
    records: list[GateRecord] = []
    for requirement_id, implementation, gate in parsed:
        issues: list[str] = []
        gate_exists = True
        references = [part.strip() for part in gate.split(" and ")]
        for reference in references:
            path_text, symbol = _gate_parts(reference)
            gate_path = _repo_path(root, path_text)
            if not gate_path.is_file():
                gate_exists = False
                issues.append(f"gate file missing: {path_text}")
            elif symbol and gate_path.suffix == ".py":
                if symbol not in _python_symbols(gate_path):
                    gate_exists = False
                    issues.append(f"gate symbol missing: {reference}")
            elif symbol:
                try:
                    source = gate_path.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as error:
                    gate_exists = False
                    issues.append(f"cannot read gate source {gate_path}: {error}")
                else:
                    if symbol not in source:
                        gate_exists = False
                        issues.append(f"gate symbol missing: {reference}")

        implementation_exists: bool | None = None
        if implementation is not None:
            normalized = implementation.replace("\\", "/").strip("`")
            if normalized.startswith(("data-pipeline/", "app/", "scripts/", "frontend/", "docs/", "tests/")):
                implementation_exists = _repo_path(root, normalized).is_file()
                if not implementation_exists:
                    issues.append(f"implementation file missing: {normalized}")

        records.append(GateRecord(
            requirement_id=requirement_id,
            gate=gate,
            gate_exists=gate_exists,
            implementation=implementation,
            implementation_exists=implementation_exists,
            issue="; ".join(issues) if issues else None,
        ))
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=REQUIREMENTS)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true", help="emit a machine-readable inventory")
    parser.add_argument("--report-only", action="store_true",
                        help="return success while required gates remain absent")
    args = parser.parse_args(argv)
    try:
        records = audit(args.requirements, args.root)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"M04 method matrix invalid: {error}", file=sys.stderr)
        return 2

    missing_gates = [record for record in records if not record.gate_exists]
    incomplete = [record for record in records if record.issue is not None]
    if args.json:
        print(json.dumps({
            "schema": "geophysics.m04-method-matrix-structure/v1",
            "scientific_acceptance": False,
            "field_acceptance": False,
            "requirements": [asdict(record) for record in records],
            "requirement_count": len(records),
            "missing_gate_count": len(missing_gates),
            "incomplete_requirement_count": len(incomplete),
            "structural_inventory_complete": not incomplete,
        }, indent=2))
    else:
        print("M04 structural inventory; scientific and field acceptance are not assessed.")
        for record in records:
            state = "declared source and gate present" if record.issue is None else f"INCOMPLETE: {record.issue}"
            print(f"{record.requirement_id}: {state} - {record.gate}")
        print(f"Structural result: {len(records) - len(incomplete)}/{len(records)} declared source/gate pairs present; "
              "scientific_acceptance=false; field_acceptance=false")
    return 0 if args.report_only or not incomplete else 1


if __name__ == "__main__":
    raise SystemExit(main())
