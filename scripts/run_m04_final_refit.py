"""Freeze the selected M04 model using development rows only."""
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
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="new write-once receipt under GEOPHYSICS_LOCAL_DATA_ROOT")
    parser.add_argument("--wall-seconds", type=float, default=120.,
                        help="per-fit cap; approved maximum is 120 seconds")
    args = parser.parse_args()
    if not args.request.is_absolute() or args.request.is_symlink() or not args.request.is_file():
        parser.error("--request must name an absolute regular non-symlink file")
    if args.request.stat().st_size > 8_388_608:
        parser.error("--request exceeds the closed 8 MiB M04 input contract")
    if not args.matrix_dir.is_absolute() or args.matrix_dir.is_symlink() or not args.matrix_dir.is_dir():
        parser.error("--matrix-dir must name an absolute regular directory")
    if not args.output.is_absolute() or args.output.is_symlink():
        parser.error("--output must be an absolute non-symlink path")

    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"):
        os.environ[key] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    import magnetic_final_refit

    try:
        receipt = magnetic_final_refit.run_final_refit(
            args.request.read_bytes(), args.matrix_dir, args.output,
            wall_seconds=args.wall_seconds,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        parser.exit(2, f"M04 final refit refused: {error}\n")
    print("FINAL_REFIT " + receipt["status"] + " " + receipt["identity"]["selected_candidate"])
    print("MODEL_SHA256 " + str(receipt["frozen_model_sha256"]))
    return 0 if receipt["status"] == "converged" else 2


if __name__ == "__main__":
    raise SystemExit(main())
