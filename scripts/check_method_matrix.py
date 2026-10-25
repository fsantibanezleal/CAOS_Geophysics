"""Audit whether every SDD method row has its declared executable gate.

This is a structural completeness check only. It does not run a solver, assess
test quality, validate science, or accept the product release.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
METHOD = re.compile(r"^\|\s*(M\d{2})\s*\|\s*(.*?)\s*\|\s*([^|]+?)\s*\|\s*$")
GATE = re.compile(r"^(?P<path>(?:scripts|tests|frontend|docs)/[\w./-]+)(?:::(?P<symbol>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*))?$")
EXPECTED_METHODS = tuple(f"M{i:02}" for i in range(1, 14))


@dataclass(frozen=True)
class MethodRow:
    method_id: str
    workflow: str
    gate: str
    gate_exists: bool
    issue: str | None


def _python_symbols(path: Path) -> set[str]:
    """Return top-level functions and class-qualified methods from a Python file."""
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


def audit(sdd_path: Path = ROOT / "docs/design/SDD.md", root: Path = ROOT) -> list[MethodRow]:
    """Read section 4's method table and check each named Python gate."""
    text = sdd_path.read_text(encoding="utf-8")
    section_match = re.search(r"(?ms)^##\s+4\.\s+Method ladder and acceptance oracle\s*$\n(.*?)(?=^##\s+\d+\.|\Z)", text)
    if not section_match:
        raise ValueError("SDD section 4 method ladder not found")

    rows: list[MethodRow] = []
    for line in section_match.group(1).splitlines():
        match = METHOD.fullmatch(line)
        if not match:
            continue
        method_id, workflow, gate = match.groups()
        components = [component.strip() for component in gate.split(" and ")]
        issues = []
        for component in components:
            parsed = GATE.fullmatch(component)
            if not parsed:
                issues.append(f"invalid gate: {component}")
                continue
            path = root / Path(parsed.group("path"))
            if not path.is_file():
                issues.append(f"file missing: {parsed.group('path')}")
                continue
            symbol = parsed.group("symbol")
            if symbol:
                if path.suffix != ".py":
                    issues.append(f"symbol gate is not Python: {component}")
                    continue
                try:
                    present = symbol in _python_symbols(path)
                except ValueError as error:
                    issues.append(str(error))
                    continue
                if not present:
                    issues.append(f"symbol missing: {component}")
        issue = "; ".join(issues) if issues else None
        rows.append(MethodRow(method_id, workflow.strip(), gate.strip(), not issues, issue))

    actual = tuple(row.method_id for row in rows)
    if actual != EXPECTED_METHODS:
        raise ValueError(f"SDD method rows must be exactly M01-M13 in order; found {actual}")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdd", type=Path, default=ROOT / "docs/design/SDD.md")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true", help="emit a machine-readable structural report")
    parser.add_argument("--report-only", action="store_true",
                        help="report missing method gates without failing an in-progress development build")
    args = parser.parse_args(argv)
    try:
        rows = audit(args.sdd, args.root)
    except (OSError, ValueError) as error:
        print(f"Method matrix audit invalid: {error}", file=sys.stderr)
        return 2

    missing = [row for row in rows if not row.gate_exists]
    if args.json:
        import json
        print(json.dumps({
            "schema": "geophysics.method-matrix-structure/v1",
            "scientific_acceptance": False,
            "methods": [asdict(row) for row in rows],
            "gate_count": len(rows),
            "missing_gate_count": len(missing),
            "complete": not missing,
        }, indent=2))
    else:
        print("Method matrix structural audit; science and release acceptance are not assessed.")
        for row in rows:
            state = "gate present" if row.gate_exists else f"MISSING: {row.issue}"
            print(f"{row.method_id}: {state} - {row.gate}")
        print(f"Structural result: {len(rows) - len(missing)}/{len(rows)} gates present; "
              f"scientific_acceptance=false")
    return 0 if not missing or args.report_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
