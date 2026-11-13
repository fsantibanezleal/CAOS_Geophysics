"""Execute one short M10 inversion replay and export display-ready results."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--iterations", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    sys.path.insert(0, str(root / "data-pipeline"))

    import numpy as np
    import torch
    import seismic
    from fwi_lesson import load_case

    loaded = load_case(args.case_id)
    run = loaded["run"]
    digest = loaded["sha256"]

    torch.use_deterministic_algorithms(True)
    if torch.backends.cudnn.is_available():
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    observed = torch.as_tensor(run["observed"], dtype=torch.float32, device=device)
    # Serialized images are [depth, distance]; the solver mesh is [distance, depth].
    initial_xz = np.asarray(run["initial"], dtype=np.float32).T.copy()
    truth_xz = np.asarray(run["truth"], dtype=np.float32).T.copy()
    initial = torch.as_tensor(initial_xz, device=device)
    active_expected = torch.as_tensor(run["active_receivers"], dtype=torch.bool, device=device)
    start = time.perf_counter()
    methods, active = seismic.invert_observations(
        observed, initial, frequency=float(run["frequency"]),
        iterations=args.iterations, beta=float(run["parameters"]["regularization"]),
    )
    if not torch.equal(active, active_expected):
        raise ValueError("Replay receiver mask does not match the catalogued holdout")
    with torch.no_grad():
        initial_prediction = seismic.simulate(
            initial, float(run["frequency"]), observed.shape[1], observed.shape[-1]
        )

    exported = {}
    for name, item in methods.items():
        model_array = item["model_tensor"].detach().cpu().numpy()
        metrics = seismic.recovery_metrics(
            model_array, truth_xz, initial_xz,
            item["predicted_tensor"], observed, initial_prediction, active,
            float(run["parameters"]["noise_sigma"]),
        )
        exported[name] = {
            "model_depth_distance_m_s": model_array.T.tolist(),
            "history": item["history_records"],
            "solver": item["solver"],
            "metrics": metrics,
        }

    payload = {
        "schema": "caos.m10-interactive-refit.v1",
        "case_id": args.case_id,
        "case_name": run["name"],
        "source_sha256": digest,
        "device": str(device),
        "iterations_per_stage": args.iterations,
        "active_receivers": int(active.sum().item()),
        "withheld_receivers": int((~active).sum().item()),
        "elapsed_seconds": time.perf_counter() - start,
        "methods": exported,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".partial")
    temporary.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({key: payload[key] for key in
                      ("case_id", "device", "iterations_per_stage", "elapsed_seconds")}))


if __name__ == "__main__":
    main()
