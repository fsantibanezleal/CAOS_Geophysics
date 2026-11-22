#!/usr/bin/env python3
"""Verify the external SPARC receipt and render its report table."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latex_number(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def render(data_root: Path) -> str:
    case = data_root / "data" / "raw" / "magnetic" / "sparc-northern-palmer-m03-v006"
    receipt_path = case / "case-receipt-v001.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "caos-geophysics-measured-case-receipt-1":
        raise ValueError("Unrecognized measured-case receipt schema")

    for label, record in receipt["files"].items():
        path = Path(record["path"])
        if not path.is_file():
            raise FileNotFoundError(f"Missing receipt input {label}: {path}")
        if path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            raise ValueError(f"Receipt integrity mismatch for {label}: {path}")

    magl = json.loads((case / "magl-all-lines-crossover-result-v002.json").read_text(encoding="utf-8"))
    paired_l = json.loads((case / "magl-paired-profile-result-v002.json").read_text(encoding="utf-8"))
    paired_ml = json.loads((case / "magml-paired-profile-result-v002.json").read_text(encoding="utf-8"))
    cross = magl["geometry_qc"]["crossover_interpolation_qc"]
    score_l, score_ml = paired_l["heldout_interpolation"], paired_ml["heldout_interpolation"]
    if cross["intersection_count"] != 648 or cross["segment_pair_tests"] != 1236:
        raise ValueError("SPARC crossover result differs from reviewed case")
    if score_l["heldout_line_ids"] != score_ml["heldout_line_ids"]:
        raise ValueError("MagL and MagML holdout line sets differ")
    if score_l["heldout_row_count"] != score_ml["heldout_row_count"]:
        raise ValueError("MagL and MagML held-out row counts differ")

    return r"""\begin{table}[!t]
\centering
\caption{Measured SPARC magnetic survey diagnostics from the pinned local source and M03 outputs; differences are descriptive and are not corrected for sensor height.}
\label{tab:sparc-m03-measured}
\begin{tabular}{lrrrr}
\toprule
Quantity & $n$ & Coverage & MAE (nT) & RMSE (nT)\\
\midrule
MagL flight/tie crossover difference & """ + str(cross["intersection_count"]) + r""" & -- & """ + latex_number(cross["mae"]) + r""" & """ + latex_number(cross["rmse"]) + r"""\\
MagL held-out profile interpolation & """ + str(score_l["heldout_row_count"]) + r""" & """ + latex_number(score_l["coverage_fraction"] * 100, 2) + r"""\% & """ + latex_number(score_l["mae"]) + r""" & """ + latex_number(score_l["rmse"]) + r"""\\
MagML held-out profile interpolation & """ + str(score_ml["heldout_row_count"]) + r""" & """ + latex_number(score_ml["coverage_fraction"] * 100, 2) + r"""\% & """ + latex_number(score_ml["mae"]) + r""" & """ + latex_number(score_ml["rmse"]) + r"""\\
\bottomrule
\end{tabular}
\end{table}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path(os.environ["GEOPHYSICS_LOCAL_DATA_ROOT"]) if os.environ.get("GEOPHYSICS_LOCAL_DATA_ROOT") else None)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "generated" / "sparc-m03-table.tex")
    parser.add_argument("--check", action="store_true", help="verify the committed table without rewriting it")
    args = parser.parse_args()
    if args.data_root is None:
        parser.error("set GEOPHYSICS_LOCAL_DATA_ROOT or pass --data-root")
    expected = render(args.data_root.resolve())
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != expected:
            raise SystemExit("SPARC report table differs from the hash-verified case receipt")
        print(f"SPARC report table verified: {sha256(args.output)}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(expected, encoding="utf-8", newline="\n")
        print(f"SPARC report table written: {args.output} ({sha256(args.output)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
