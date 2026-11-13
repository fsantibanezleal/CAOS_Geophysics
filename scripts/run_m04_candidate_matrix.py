"""Run the resumable 16-candidate / three-fold M04 development matrix."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "data-pipeline"
sys.path.insert(0, str(PIPELINE))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, default=(
        ROOT / "tests/fixtures/magnetic_survey/generated/requests/S2-A-linear_tmi_nT.json"))
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="write-once cell receipts outside the product checkout")
    parser.add_argument("--wall-seconds", type=float, default=120.,
                        help="per-fit cap; the approved maximum is 120 seconds")
    args = parser.parse_args()
    if args.request.is_symlink() or not args.request.is_file():
        parser.error("--request must name a regular, non-symlink source file")
    if args.request.stat().st_size > 8_388_608:
        parser.error("--request exceeds the closed 8 MiB M04 input contract")
    if not args.output_dir.is_absolute():
        parser.error("--output-dir must be an absolute path under the external data root")

    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"):
        os.environ[key] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    import magnetic_candidate_matrix

    raw = args.request.read_bytes()
    matrix = magnetic_candidate_matrix.run_matrix(
        raw, args.output_dir, wall_seconds=args.wall_seconds,
    )
    return 0 if matrix["claims"]["candidate_matrix_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
