"""Verify sealed M04 outer-evaluation receipts without rescoring."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    if args.request.is_symlink() or not args.request.is_absolute() or not args.request.is_file():
        parser.error("--request must name an absolute regular non-symlink file")
    if args.request.stat().st_size > 8_388_608:
        parser.error("--request exceeds the closed 8 MiB M04 input contract")
    if args.matrix_dir.is_symlink() or not args.matrix_dir.is_absolute() or not args.matrix_dir.is_dir():
        parser.error("--matrix-dir must name an absolute regular directory")
    if args.freeze.is_symlink() or not args.freeze.is_absolute() or not args.freeze.is_file():
        parser.error("--freeze must name an absolute regular non-symlink file")
    if args.result.is_symlink() or not args.result.is_absolute() or not args.result.is_file():
        parser.error("--result must name an absolute regular non-symlink file")
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"):
        os.environ[key] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    import magnetic_outer_evaluation

    try:
        result = magnetic_outer_evaluation.verify_outer_evaluation(
            args.request.read_bytes(), args.matrix_dir, args.freeze, args.result,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        parser.exit(2, f"M04 outer-evaluation verification failed: {error}\n")
    print("VERIFIED " + result["selection"]["candidate_id"])
    print("OUTER_PHI_D " + str(result["metrics"]["outer"]["phi_d"]))
    print("RECEIPT_SHA256 " + result["receipt_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
