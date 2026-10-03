"""Fixed child-process engine for reversible gravity station outlier flags."""

from __future__ import annotations

import argparse
import math
import os
import statistics
import sys
import threading
from pathlib import Path

from app.processing_contract import METHOD_ID, canonical_bytes, sha256


def flag_gravity_stations(
    dataset: dict, *, dataset_sha: str, job_id: str, request_sha: str, threshold: float,
) -> dict:
    if dataset.get("schema") != "geophysics.observation-dataset/v1" or dataset.get("modality") != "gravity_station":
        raise ValueError("input is not a validated gravity station dataset")
    values = dataset.get("observed_mgal")
    sigma = dataset.get("sigma_mgal")
    count = dataset.get("dimensions", {}).get("station")
    if (not isinstance(count, int) or not 4 <= count <= 4096
            or not isinstance(values, list) or not isinstance(sigma, list)
            or len(values) != count or len(sigma) != count
            or any(type(value) not in (float, int) or not math.isfinite(value) for value in values)
            or any(type(value) not in (float, int) or not math.isfinite(value) or value <= 0 for value in sigma)
            or not math.isfinite(threshold) or not 1 <= threshold <= 10):
        raise ValueError("gravity observations, uncertainty or threshold are invalid")
    center = statistics.median(values)
    mad = statistics.median(abs(value - center) for value in values)
    scale = 1.4826 * mad
    if scale <= 0 or not math.isfinite(scale):
        raise ValueError("degenerate_mad_scale: flag-only QC requires a positive robust scale")
    scores = [abs(value - center) / scale for value in values]
    flags = [score > threshold for score in scores]
    return {
        "schema": "geophysics.processing-result/v1", "job_id": job_id,
        "dataset_id": dataset["dataset_id"], "dataset_sha256": dataset_sha,
        "method_id": METHOD_ID, "request_sha256": request_sha,
        "engine_sha256": sha256(Path(__file__).read_bytes()),
        "parameters": {"threshold": threshold}, "axis_order": ["station"],
        "dimensions": {"station": count}, "station_ids": dataset["station_ids"],
        "xyz_m": dataset["xyz_m"], "observed_mgal": values, "sigma_mgal": sigma,
        "outlier_flag": flags, "robust_score": scores,
        "statistics": {"median_mgal": center, "mad_mgal": mad, "scaled_mad_mgal": scale,
                       "flagged_count": sum(flags)},
        "uncertainty_kind": dataset["uncertainty_kind"],
        "physical_metadata": dataset["physical_metadata"],
        "rights_decision": dataset["rights_decision"],
        "rights_statement": dataset["rights_statement"],
        "correction_history": dataset["correction_history"] + [
            {"method_id": METHOD_ID, "parameters": {"threshold": threshold},
             "effect": "flag_only; observations and uncertainty unchanged"},
        ],
        "interpretation_limit": "Statistical flags only; no datum correction, anomaly transform, exclusion, model or inversion",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--memory-limit", type=int, required=True)
    parser.add_argument("--scratch-limit", type=int, required=True)
    args = parser.parse_args()
    try:
        if args.memory_limit <= 0 or args.scratch_limit <= 0:
            raise ValueError("invalid child resource ceiling")
        if os.name == "posix":
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (args.memory_limit, args.memory_limit))
            resource.setrlimit(resource.RLIMIT_FSIZE, (args.scratch_limit, args.scratch_limit))

        def parent_watch() -> None:
            if not os.read(0, 1):
                os._exit(99)

        threading.Thread(target=parent_watch, daemon=True).start()
        raw = args.input.read_bytes()
        if len(raw) > 2 * 1024 * 1024 or sha256(raw) != args.dataset_sha256:
            raise ValueError("dataset bytes differ from admitted receipt")
        import json
        dataset = json.loads(raw)
        if canonical_bytes(dataset) != raw:
            raise ValueError("dataset JSON is not canonical")
        result = flag_gravity_stations(
            dataset, dataset_sha=args.dataset_sha256, job_id=args.job_id,
            request_sha=args.request_sha256, threshold=args.threshold,
        )
        encoded = canonical_bytes(result)
        if len(encoded) > 8 * 1024 * 1024:
            raise ValueError("processing result exceeds scratch cap")
        with args.output.open("xb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"processing_failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
