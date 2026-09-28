"""Diagnostic only: rerun a fixed FWI reference with explicit GPU flags.

Writes small ignored receipts, not canonical release artifacts. This does not
change the solver or its scientific acceptance criteria.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from importlib.metadata import version

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from geology import registry  # noqa: E402
import seismic  # noqa: E402


def digest_array(values) -> str:
    array = np.asarray(values, dtype=np.float32)
    return hashlib.sha256(array.tobytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--deterministic", action="store_true")
    parser.add_argument("--case", choices=("FWI_LAYERED", "FWI_FAULT", "FWI_NOISY", "FWI_CYCLE_SKIP"),
                        default="FWI_FAULT")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "data/raw").resolve()) or output.exists():
        raise ValueError("probe receipt must be a new ignored data/raw path")
    if not torch.cuda.is_available():
        raise RuntimeError("FWI repro probe requires CUDA")
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = args.deterministic
    torch.use_deterministic_algorithms(args.deterministic)
    case = next(case for case in registry() if case["id"] == args.case)
    run = seismic.solve_case(case, "reference")
    receipt = {
        "schema": "caos.fwi-repro-probe.v1",
        "case": args.case,
        "variant": "reference",
        "deterministic_algorithms": args.deterministic,
        "solver_sha256": hashlib.sha256((ROOT / "data-pipeline/seismic.py").read_bytes()).hexdigest(),
        "torch": torch.__version__,
        "deepwave": version("deepwave"),
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(),
        "observation_sha256": digest_array(run["observed"]),
        "initial_sha256": digest_array(run["initial"]),
        "truth_sha256": digest_array(run["truth"]),
        "methods": {name: {
            "status": method["evaluation"]["status"],
            "reason_codes": method["evaluation"]["reason_codes"],
            "model_sha256": digest_array(method["model"]),
            "active_wrms": method["metrics"]["active_wrms"],
            "withheld_wrms": method["metrics"]["withheld_wrms"],
            "model_rmse_ratio": method["metrics"]["model_rmse_ratio"],
            "relative_mse": method["metrics"]["relative_mse"],
        } for name, method in run["methods"].items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == "__main__":
    main()
