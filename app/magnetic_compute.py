"""Isolated child entry point for source-bound M03 flight-line processing."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--raw-sha256", required=True)
    parser.add_argument("--raw-bytes", required=True, type=int)
    parser.add_argument("--raw-asset-id", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--parameters", required=True)
    parser.add_argument("--memory-limit", required=True, type=int)
    parser.add_argument("--scratch-limit", required=True, type=int)
    args = parser.parse_args()

    input_path, raw_path, output_path = Path(args.input), Path(args.raw), Path(args.output)
    if input_path.is_symlink() or raw_path.is_symlink() or output_path.exists() or output_path.is_symlink():
        raise SystemExit("M03 paths must be regular inputs and a new output")
    raw_path = raw_path.resolve(strict=True)
    if raw_path.stat().st_size != args.raw_bytes or _digest(raw_path) != args.raw_sha256:
        raise SystemExit("M03 source bytes differ from the admitted raw receipt")
    dataset_bytes = input_path.read_bytes()
    if hashlib.sha256(dataset_bytes).hexdigest() != args.dataset_sha256:
        raise SystemExit("M03 dataset bytes differ from the admitted dataset receipt")
    dataset = json.loads(dataset_bytes)
    parameters = json.loads(args.parameters)
    source = dataset.get("source")
    if (dataset.get("modality") != "magnetic_flightline"
            or dataset.get("raw_asset_id") != args.raw_asset_id
            or dataset.get("parent_raw_sha256") != args.raw_sha256
            or source is None or source.get("source_id") != args.source_id):
        raise SystemExit("M03 dataset/raw/source identity mismatch")

    repo_root = Path(__file__).resolve().parents[1]
    pipeline_root = repo_root / "data-pipeline"
    sys.path.insert(0, str(pipeline_root))
    import magnetic_processing

    request = magnetic_processing.read_csv(
        raw_path,
        field_map=dataset["mapping"],
        source_metadata={
            "source_id": source["source_id"], "citation": source["citation"],
            "rights_decision": source["rights_decision"],
            "processing_state": source["processing_state"],
            "value_unit": source["value_unit"], "value_quantity": source["value_quantity"],
            "sensor_height_reference": source["sensor_height_reference"],
        },
        frame=dataset["frame"],
        settings=parameters,
    )
    if request["source"]["sha256"] != args.raw_sha256:
        raise SystemExit("M03 parser computed a different source SHA-256")
    result = magnetic_processing.process(request, source_hash_verified=True)
    result.update({
        "job_id": args.job_id, "dataset_id": dataset["dataset_id"],
        "dataset_sha256": args.dataset_sha256, "request_sha256": args.request_sha256,
        "method_id": "magnetic.flightline-qc-grid/v1", "parameters": parameters,
        "raw_asset_id": args.raw_asset_id, "raw_sha256": args.raw_sha256,
        "source_id": args.source_id,
        "engine_sha256": hashlib.sha256(Path(magnetic_processing.__file__).read_bytes()).hexdigest(),
        "resource_contract": {"memory_limit_bytes": args.memory_limit,
                              "scratch_limit_bytes": args.scratch_limit},
    })
    encoded = _canonical(result)
    if len(encoded) > args.scratch_limit:
        raise SystemExit("M03 result exceeds the admitted scratch bound")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())


if __name__ == "__main__":
    main()
