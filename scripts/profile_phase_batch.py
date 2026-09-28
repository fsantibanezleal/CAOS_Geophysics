"""Measure local M13 training throughput/memory without opening any field data.

Synthetic random tensors are used only to select a safe hardware batch size;
this command produces no scientific accuracy evidence or release artifact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from phase_model import PhaseUNet, SAMPLES, gaussian_targets, weighted_soft_cross_entropy  # noqa: E402


def profile(batch_size: int, *, warmup: int, measured: int) -> dict:
    if not torch.cuda.is_available() or batch_size < 1 or warmup < 1 or measured < 1:
        raise ValueError("CUDA and positive batch/step counts are required")
    torch.manual_seed(41027)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    model = PhaseUNet().cuda().train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-4)
    scaler = torch.amp.GradScaler("cuda")
    values = torch.randn((batch_size, 3, SAMPLES), device="cuda")
    p = torch.full((batch_size,), 1000, device="cuda", dtype=torch.long)
    s = torch.full((batch_size,), 2000, device="cuda", dtype=torch.long)
    p[::10] = -1
    s[::10] = -1
    target = gaussian_targets(p, s)
    torch.cuda.reset_peak_memory_stats()
    started = None
    for step in range(warmup + measured):
        if step == warmup:
            torch.cuda.synchronize()
            started = time.perf_counter()
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast("cuda", dtype=torch.float16):
            loss = weighted_soft_cross_entropy(model(values), target)
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
        scaler.step(optimizer)
        scaler.update()
    torch.cuda.synchronize()
    seconds = time.perf_counter() - started
    return {
        "schema": "caos.phase-local-throughput-only.v1",
        "batch_size": batch_size,
        "warmup_steps": warmup,
        "measured_steps": measured,
        "seconds_per_step": seconds / measured,
        "traces_per_second": batch_size * measured / seconds,
        "peak_gpu_mib": torch.cuda.max_memory_allocated() / 1048576,
        "gpu": torch.cuda.get_device_name(),
        "synthetic_inputs_only": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batches", type=int, nargs="+", default=[16, 32, 64])
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--measured", type=int, default=10)
    parser.add_argument("--output", type=Path,
                        help="New ignored data/raw JSON receipt for this local hardware profile")
    args = parser.parse_args()
    results = []
    for batch_size in args.batches:
        result = profile(batch_size, warmup=args.warmup, measured=args.measured)
        results.append(result)
        print(json.dumps(result), flush=True)
    if args.output:
        output = args.output.resolve()
        if not output.is_relative_to((ROOT / "data/raw").resolve()) or output.exists():
            raise ValueError("hardware receipt must be a new ignored data/raw path")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({
            "schema": "caos.phase-local-hardware-profile.v1",
            "torch": str(torch.__version__),
            "cuda": torch.version.cuda,
            "synthetic_inputs_only": True,
            "recommended_batch_by_this_microbenchmark": max(
                results, key=lambda item: item["traces_per_second"])["batch_size"],
            "profiles": results,
        }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
