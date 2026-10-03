"""Diagnostic only: rerun a fixed FWI reference with explicit GPU flags.

Writes small ignored receipts, not canonical release artifacts. This does not
change the solver or its scientific acceptance criteria. solve_case enforces
deterministic algorithms internally even when the caller flag is false.
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
    parser.add_argument("--terminal-full-band", action="store_true",
                        help="Diagnostic: continue at 3/5/8 Hz and fit unfiltered data in the last stage")
    parser.add_argument("--cutoffs", type=str,
                        help="Diagnostic four-stage cutoffs in Hz, comma-separated; use none for full band")
    parser.add_argument("--iterations", type=int, default=seismic.DEFAULT_ITERATIONS,
                        help="Diagnostic optimizer calls per stage")
    parser.add_argument("--trace-optimizer", action="store_true",
                        help="Record accepted parameter steps and gradient magnitudes by stage")
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
    if args.terminal_full_band and args.cutoffs:
        parser.error("choose either --terminal-full-band or --cutoffs")
    if args.terminal_full_band:
        seismic.CUTOFFS_HZ = (*seismic.CUTOFFS_HZ[:-1], None)
    elif args.cutoffs:
        values = tuple(None if part == "none" else float(part) for part in args.cutoffs.split(","))
        if len(values) != len(seismic.CONTROL_GRIDS) or values[0] is None:
            parser.error("provide one positive background cutoff and three spatial cutoffs")
        seismic.CUTOFFS_HZ = values
    case = next(case for case in registry() if case["id"] == args.case)
    optimizer_stages = []
    original_step = torch.optim.LBFGS.step

    def traced_step(optimizer, closure):
        parameter = optimizer.param_groups[0]["params"][0]
        stage = next((entry for entry in optimizer_stages if entry["optimizer"] is optimizer), None)
        if stage is None:
            stage = {"optimizer": optimizer, "calls": []}
            optimizer_stages.append(stage)
        before = parameter.detach().clone()
        result = original_step(optimizer, closure)
        state = optimizer.state[parameter]
        stage["calls"].append({
            "step_linf": float((parameter.detach()-before).abs().max()),
            "last_closure_gradient_linf": float(parameter.grad.detach().abs().max()),
            "total_lbfgs_iterations": state.get("n_iter", 0),
            "total_closure_evaluations": state.get("func_evals", 0),
        })
        return result

    try:
        if args.trace_optimizer:
            torch.optim.LBFGS.step = traced_step
        run = seismic.solve_case(case, "reference", iterations=args.iterations)
    finally:
        torch.optim.LBFGS.step = original_step
    receipt = {
        "schema": "caos.fwi-repro-probe.v1",
        "case": args.case,
        "variant": "reference",
        "deterministic_algorithms": args.deterministic,
        "solver_enforces_deterministic_algorithms": True,
        "diagnostic_terminal_full_band": args.terminal_full_band,
        "continuation_cutoffs_hz": list(seismic.CUTOFFS_HZ),
        "iterations_per_stage": args.iterations,
        "optimizer_stages": [
            {"stage": name, "first_zero_step": next(
                (i+1 for i, call in enumerate(entry["calls"]) if call["step_linf"] == 0), None),
             "last_five_calls": entry["calls"][-5:],
             "calls": len(entry["calls"])}
            for name, entry in zip(
                ("background", "full-spatial-1", "full-spatial-2", "full-spatial-3",
                 "multiscale-spatial-1", "multiscale-spatial-2", "multiscale-spatial-3"),
                optimizer_stages)
        ],
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
            "stage_endpoints": [
                {"phase": phase,
                 "first": next(r for r in method["history_records"] if r["phase"] == phase),
                 "last": next(r for r in reversed(method["history_records"]) if r["phase"] == phase)}
                for phase in ("background", "spatial-1", "spatial-2", "spatial-3")
            ],
        } for name, method in run["methods"].items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == "__main__":
    main()
