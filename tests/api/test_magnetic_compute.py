"""Exercise the isolated M03 worker child and source-bound result export."""

from __future__ import annotations

import csv
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from app.bundle import build_bundle, verify_bundle
from app.magnetic_bundle import verify_magnetic_bundle
from app.magnetic_contract import METHOD_ID
from app.processing_contract import canonical_bytes, sha256, validate_result_identity


ROOT = Path(__file__).resolve().parents[2]
MAPPING = {"easting": "E", "northing": "N", "value": "field", "line_id": "line",
           "line_role": "role", "sensor_height_m": "height", "sample_order": "index"}


def test_isolated_child_recomputes_original_hash_and_exports_valid_m03_bundle(tmp_path: Path) -> None:
    raw_path = tmp_path / "survey.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(MAPPING.values()))
        writer.writeheader()
        for line in range(5):
            for sample in range(9):
                x, y = 500_000 + line * 100, 4_500_000 + sample * 12.5
                writer.writerow({"E": x, "N": y, "field": 50_000 + .3 * line * 100 - .15 * sample * 12.5,
                                 "line": f"F{line}", "role": "flight", "height": 120 + .02 * sample * 12.5,
                                 "index": sample})
    raw_sha = sha256(raw_path.read_bytes())
    dataset = {
        "schema": "geophysics.observation-dataset/v1", "dataset_id": "4de5f5db-303b-41cb-81a9-ff879454e5a9",
        "version": 1, "owner_id": "cbeb28ef-c160-4f5a-a37c-3a54b9d091ad",
        "project_id": "a383bd17-0093-46c8-8719-2a2f14c09aed",
        "raw_asset_id": "b51344d8-d752-46bd-a002-dc7408a39baf", "parent_raw_sha256": raw_sha,
        "parent_raw_bytes": raw_path.stat().st_size, "parser_version": "magnetic-flightline-original/v1",
        "modality": "magnetic_flightline", "dimensions": {"measurement": 45},
        "axis_order": ["measurement"], "mapping": MAPPING,
        "source": {"source_id": "8834a0ee-2ad9-46e1-a54a-ceb64c451117", "citation": "Authored analytic control",
                   "rights_decision": "local-test-only", "rights_statement": "Test data",
                   "processing_state": "Synthetic total-field anomaly", "value_quantity": "total-field anomaly",
                   "value_unit": "nT", "sensor_height_reference": "above-ground"},
        "frame": {"crs": "EPSG:32618", "coordinates_are_projected": True, "linear_unit": "m"},
        "physical_metadata": {"measurement_unit": "nT", "horizontal_unit": "m", "vertical_unit": "m",
                              "axis_order": "xy"},
        "rights_decision": "local-test-only", "rights_statement": "Test data", "attribution": "Test",
        "qc_verdict": "source_bound_not_numerically_processed",
    }
    dataset_bytes = canonical_bytes(dataset)
    dataset_sha = sha256(dataset_bytes)
    input_path = tmp_path / "dataset.json"
    input_path.write_bytes(dataset_bytes)
    output_path = tmp_path / "result.json"
    params = {"grid_spacing_m": 12.5, "holdout_fraction": .2, "seed": "m03-isolated-child-test"}
    request = {"schema": "geophysics.processing-request/v1", "job_id": "3d20cb34-a7e3-40ab-b2ec-8c915b572a23",
               "project_id": dataset["project_id"], "dataset_id": dataset["dataset_id"],
               "dataset_sha256": dataset_sha, "method_id": METHOD_ID, "parameters": params,
               "raw_asset_id": dataset["raw_asset_id"], "raw_sha256": raw_sha,
               "raw_bytes": raw_path.stat().st_size, "source_id": dataset["source"]["source_id"]}
    request_sha = sha256(canonical_bytes(request))
    child_env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run([
        sys.executable, "-m", "app.magnetic_compute", "--input", str(input_path), "--raw", str(raw_path),
        "--output", str(output_path), "--job-id", request["job_id"], "--dataset-sha256", dataset_sha,
        "--request-sha256", request_sha, "--raw-sha256", raw_sha, "--raw-bytes", str(raw_path.stat().st_size),
        "--raw-asset-id", dataset["raw_asset_id"], "--source-id", dataset["source"]["source_id"],
        "--parameters", __import__("json").dumps(params, sort_keys=True, separators=(",", ":")),
        "--memory-limit", str(2 * 1024**3), "--scratch-limit", str(1024**3),
    ], cwd=tmp_path, env=child_env, check=True, capture_output=True, text=True)
    import json
    result_bytes = output_path.read_bytes()
    result = json.loads(result_bytes)
    job = SimpleNamespace(id=request["job_id"], dataset_id=dataset["dataset_id"],
                          dataset_sha256=dataset_sha, request_sha256=request_sha, method_id=METHOD_ID,
                          request_json=request)
    validate_result_identity(result, job)
    assert result["claims"]["source_hash_recomputed_from_original_bytes"] is True
    assert result["heldout_interpolation"]["rmse"] < 1e-8
    bundle = build_bundle(dataset, result, dataset_sha, sha256(result_bytes))
    assert verify_bundle(bundle)[0]["units"] == {"position": "m", "observation": "nT"}
    assert verify_magnetic_bundle(bundle)[2]["job_id"] == request["job_id"]
