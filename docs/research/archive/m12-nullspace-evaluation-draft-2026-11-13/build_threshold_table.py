"""Build the manuscript's threshold table from the retained reconciliation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def render(root: Path) -> tuple[bytes, str]:
    artifact = root / "data/derived/v2/models/m12-nullspace-v1_1/threshold-reconciliation.json"
    receipt_path = root / "data/derived/v2/models/m12-nullspace-v1_1/receipt.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    receipt_bytes = receipt_path.read_bytes()
    receipt_sha = hashlib.sha256(receipt_bytes).hexdigest()
    if payload.get("schema") != "caos-geophysics.m12-nullspace-threshold-reconciliation/v1":
        raise SystemExit("unexpected threshold reconciliation schema")
    if payload.get("source", {}).get("receipt_sha256") != receipt_sha:
        raise SystemExit("threshold reconciliation is not bound to the retained source receipt")

    method = payload["method"]
    threshold = float(method["threshold_ms"])
    if method.get("quantile") != 0.95 or method.get("quantile_method") != "numpy-linear":
        raise SystemExit("unexpected calibration threshold rule")
    if method.get("comparison") != "strict greater-than; no cohort-specific retuning":
        raise SystemExit("unexpected exceedance rule")

    labels = {
        "calibration": "Calibration",
        "id_test": "In-distribution test",
        "family_only": "Family-shift test",
        "acquisition_only": "Acquisition-shift test",
        "joint_ood": "Joint-shift test",
    }
    rows: list[str] = []
    for key, label in labels.items():
        cohort = payload["cohorts"][key]
        records = cohort.get("records", [])
        count = int(cohort["count"])
        if len(records) != count:
            raise SystemExit(f"{key}: record count mismatch")
        observed = 0
        for record in records:
            error = float(record["learned_oracle_rmse_ms"])
            flag = error > threshold
            if record.get("forward_threshold_exceeded") is not flag:
                raise SystemExit(f"{key}: stored threshold flag mismatch")
            observed += int(flag)
        if observed != int(cohort["exceedances"]):
            raise SystemExit(f"{key}: summary exceedance count mismatch")
        rate = 100.0 * observed / count
        rows.append(f"{label} & {count} & {observed} & {rate:.3f}\\% " + r"\\")

    table = "\n".join(
        [
            r"\begin{table}[htbp]",
            r"\centering",
            r"\caption{Calibration-derived threshold flags computed from retained synthetic learned-oracle errors; they are diagnostic counts, not field accuracy.}",
            r"\label{tab:threshold-reconciliation}",
            r"\begin{tabular}{lrrr}",
            r"\toprule",
            r"Cohort & $n$ & Exceedances & Rate " + r"\\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    ).encode("utf-8")
    return table, receipt_sha


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    output = Path(__file__).resolve().parent / "generated/threshold-reconciliation-table.tex"
    content, receipt_sha = render(root)
    if args.check:
        if not output.is_file() or output.read_bytes() != content:
            raise SystemExit("generated threshold table is stale; run build.ps1")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
    print(f"threshold table source receipt sha256={receipt_sha}")
    print(f"{'verified' if args.check else 'generated'} {output.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
