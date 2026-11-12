"""Verify an M04 final-refit freeze before sealed outer evaluation."""
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
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.request.is_symlink() or not args.request.is_absolute() or not args.request.is_file():
        parser.error("--request must name an absolute regular non-symlink file")
    if args.request.stat().st_size > 8_388_608:
        parser.error("--request exceeds the closed 8 MiB M04 input contract")
    if (args.matrix_dir.is_symlink() or not args.matrix_dir.is_absolute()
            or not args.matrix_dir.is_dir()):
        parser.error("--matrix-dir must name an absolute regular directory")
    if args.receipt.is_symlink() or not args.receipt.is_absolute() or not args.receipt.is_file():
        parser.error("--receipt must name an absolute regular non-symlink file")
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"):
        os.environ[key] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    import magnetic_final_refit

    try:
        receipt = magnetic_final_refit.verify_final_refit(
            args.request.read_bytes(), args.matrix_dir, args.receipt,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        parser.exit(2, f"M04 final-refit verification failed: {error}\n")
    print("VERIFIED " + receipt["identity"]["selected_candidate"])
    print("MODEL_SHA256 " + receipt["frozen_model_sha256"])
    print("RECEIPT_SHA256 " + receipt["receipt_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
