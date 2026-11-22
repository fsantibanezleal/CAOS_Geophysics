"""Validate the retained M02 locked-matrix JUnit receipts without rerunning solvers."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


CASE = re.compile(r"^test_complete_locked_l2_control_matrix\[(\d+)-(\d+)\]$")
HASH = re.compile(r"^[0-9a-f]{64}$")
EXPECTED = {(condition, family) for condition in range(4) for family in range(6)}
REPO_ROOT = Path(__file__).resolve().parents[1]


def source_reference(path: Path) -> str:
    """Keep repository receipts relocatable while preserving external run paths."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def validate_junit(paths: list[Path]) -> dict:
    """Check cell coverage, exact duplicated replays, and predeclared holdout controls."""
    cells: dict[tuple[int, int], dict] = {}
    duplicates = 0
    source_files = []
    for path in paths:
        source_files.append(source_reference(path))
        root = ET.parse(path).getroot()
        for case in root.iter("testcase"):
            match = CASE.fullmatch(case.attrib.get("name", ""))
            if not match:
                continue
            condition, family = map(int, match.groups())
            key = (condition, family)
            if key not in EXPECTED:
                raise ValueError(f"unexpected locked matrix cell {condition}-{family} in {path}")
            if int(case.attrib.get("failures", "0")) or int(case.attrib.get("errors", "0")):
                raise ValueError(f"pytest failure/error in cell {condition}-{family} ({path})")
            if int(case.attrib.get("skipped", "0")):
                raise ValueError(f"locked matrix cell {condition}-{family} was skipped ({path})")
            properties = {
                prop.attrib.get("name"): prop.attrib.get("value", "")
                for prop in case.findall("./properties/property")
            }
            try:
                value = json.loads(properties["locked_l2_outcome"])
            except (KeyError, json.JSONDecodeError) as exc:
                raise ValueError(f"missing or malformed locked_l2_outcome in cell {condition}-{family}") from exc
            if value.get("condition") != condition or value.get("family") != family:
                raise ValueError(f"cell identity differs from its JUnit name: {condition}-{family}")
            if value.get("selection_status") != "selected":
                raise ValueError(f"selection did not complete in cell {condition}-{family}")
            selected = value.get("selected_index")
            if type(selected) is not int or not 0 <= selected < 8:
                raise ValueError(f"invalid selected candidate in cell {condition}-{family}")
            if not HASH.fullmatch(value.get("input_sha256", "")) or not HASH.fullmatch(value.get("calibration_sha256", "")):
                raise ValueError(f"missing input/calibration hash in cell {condition}-{family}")
            candidates = value.get("candidates")
            if not isinstance(candidates, list) or len(candidates) != 8:
                raise ValueError(f"expected eight candidate records in cell {condition}-{family}")
            if [candidate.get("index") for candidate in candidates] != list(range(8)):
                raise ValueError(f"candidate IDs are incomplete in cell {condition}-{family}")
            if any(not isinstance(candidate.get("folds"), list) or len(candidate["folds"]) != 3 for candidate in candidates):
                raise ValueError(f"three-fold evidence is incomplete in cell {condition}-{family}")

            wrms = value.get("outer_wrms")
            if isinstance(wrms, bool) or not isinstance(wrms, (int, float)) or not math.isfinite(wrms) or wrms < 0:
                raise ValueError(f"missing finite held-out WRMS in cell {condition}-{family}")
            if condition in (0, 1, 2) and wrms > 2.0:
                raise ValueError(f"declared in-family control exceeds 2 sigma in cell {condition}-{family}: {wrms}")
            if condition == 3 and wrms <= 2.0:
                raise ValueError(f"unmodelled nuisance control was not flagged poor in cell {condition}-{family}: {wrms}")

            previous = cells.get(key)
            if previous is not None:
                identity = ("input_sha256", "calibration_sha256", "selection_status", "selected_index", "outer_wrms")
                if any(previous[field] != value[field] for field in identity):
                    raise ValueError(f"nonidentical duplicate JUnit evidence in cell {condition}-{family}")
                duplicates += 1
                continue
            cells[key] = value

    missing = sorted(EXPECTED - cells.keys())
    if missing:
        raise ValueError(f"missing locked matrix cells: {missing}")

    by_condition = defaultdict(list)
    for (condition, family), value in sorted(cells.items()):
        by_condition[condition].append((family, value))
    condition_summary = {}
    for condition, rows in sorted(by_condition.items()):
        metrics = [float(value["outer_wrms"]) for _, value in rows]
        ratios = [value["model_rmse_ratio"] for _, value in rows if value["model_rmse_ratio"] is not None]
        condition_summary[str(condition)] = {
            "cells": len(rows),
            "classification": "within_declared_noise" if condition < 3 else "poor_under_declared_noise",
            "outer_wrms_min": min(metrics),
            "outer_wrms_max": max(metrics),
            "model_rmse_ratio_count": len(ratios),
            "model_rmse_ratio_gt_one_count": sum(float(ratio) > 1.0 for ratio in ratios),
        }
    return {
        "schema": "geophysics.m02-locked-matrix-validation/v1",
        "cell_count": len(cells),
        "duplicate_identical_replays": duplicates,
        "selection_status_counts": {"selected": len(cells)},
        "conditions": condition_summary,
        "scientific_acceptance": False,
        "field_eligibility": False,
        "source_files": source_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, action="append", required=True, help="JUnit receipt; repeat for all chunks")
    parser.add_argument("--output", type=Path, help="optional JSON summary path outside the repository")
    args = parser.parse_args()
    try:
        result = validate_junit(args.junit)
    except (OSError, ET.ParseError, ValueError) as exc:
        parser.error(str(exc))
    encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
