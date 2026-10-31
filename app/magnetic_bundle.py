"""Typed, bounded export contract for source-bound M03 results."""

from __future__ import annotations

import io
import json
import math
import zipfile

from app.processing_contract import canonical_bytes, sha256

MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_BUNDLE_BYTES = 130 * 1024 * 1024


def _verify_result(dataset: dict, result: dict) -> None:
    grid = result.get("grid")
    if (dataset.get("modality") != "magnetic_flightline"
            or result.get("schema") != "magnetic-flightline-process-result-1"
            or result.get("source", {}).get("sha256") != dataset.get("parent_raw_sha256")
            or result.get("source", {}).get("source_id") != dataset.get("source", {}).get("source_id")
            or result.get("claims") != {
                "source_hash_recomputed_from_original_bytes": True,
                "corrections_applied": [], "provider_grid_comparison": False,
                "inverse_model": False, "scientific_release_accepted": False,
            }
            or not isinstance(grid, dict)):
        raise ValueError("M03 dataset/result provenance or claims mismatch")
    x, y, values, mask, shape = (grid.get("x_easting_m"), grid.get("y_northing_m"),
                                 grid.get("values"), grid.get("support_mask"), grid.get("shape_yx"))
    if (not isinstance(x, list) or not isinstance(y, list) or not isinstance(values, list)
            or not isinstance(mask, list) or shape != [len(y), len(x)]
            or len(values) != len(y) or len(mask) != len(y)
            or not 2 <= len(x) or not 2 <= len(y)
            or len(x) * len(y) > 250_000):
        raise ValueError("M03 grid shape exceeds its declared contract")
    if any(not isinstance(row, list) or len(row) != len(x) for row in values + mask):
        raise ValueError("M03 grid rows have inconsistent shape")
    if any(type(flag) is not bool for row in mask for flag in row):
        raise ValueError("M03 support mask is not boolean")
    if any(not isinstance(number, (int, float)) or not math.isfinite(number)
           for axis in (x, y) for number in axis):
        raise ValueError("M03 grid coordinates are nonfinite")
    if any(not isinstance(value, (int, float)) or not math.isfinite(value)
           for row in values for value in row):
        raise ValueError("M03 grid values are nonfinite")
    if any(values[j][i] != 0.0 for j in range(len(y)) for i in range(len(x)) if not mask[j][i]):
        raise ValueError("M03 unsupported cells must use the declared zero plus false-mask encoding")
    if result.get("method_id") != "magnetic.flightline-qc-grid/v1":
        raise ValueError("M03 method identity mismatch")


def build_magnetic_bundle(dataset: dict, result: dict, dataset_sha: str, result_sha: str) -> bytes:
    dataset_bytes, result_bytes = canonical_bytes(dataset), canonical_bytes(result)
    if (sha256(dataset_bytes) != dataset_sha or sha256(result_bytes) != result_sha
            or max(len(dataset_bytes), len(result_bytes)) > MAX_MEMBER_BYTES):
        raise ValueError("M03 bundle inputs disagree with stored receipts or exceed member bounds")
    _verify_result(dataset, result)
    manifest = {
        "schema": "geophysics.magnetic-processing-bundle/v1",
        "dataset_id": dataset["dataset_id"], "job_id": result["job_id"],
        "method_id": result["method_id"], "parameters": result["parameters"],
        "units": {"position": "m", "observation": "nT"},
        "source": {"source_id": dataset["source"]["source_id"],
                   "citation": dataset["source"]["citation"],
                   "rights_decision": dataset["rights_decision"],
                   "rights_statement": dataset["rights_statement"],
                   "attribution": dataset["attribution"],
                   "processing_state": dataset["source"]["processing_state"]},
        "provenance": {"raw_sha256": dataset["parent_raw_sha256"], "dataset_sha256": dataset_sha,
                       "result_sha256": result_sha, "request_sha256": result["request_sha256"],
                       "engine_sha256": result["engine_sha256"]},
        "members": {"dataset.json": {"sha256": dataset_sha, "bytes": len(dataset_bytes)},
                    "result.json": {"sha256": result_sha, "bytes": len(result_bytes)}},
        "raw_bytes_included": False,
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, value in (("manifest.json", manifest), ("dataset.json", dataset), ("result.json", result)):
            archive.writestr(name, canonical_bytes(value))
    encoded = output.getvalue()
    verify_magnetic_bundle(encoded)
    return encoded


def verify_magnetic_bundle(encoded: bytes) -> tuple[dict, dict, dict]:
    if len(encoded) > MAX_BUNDLE_BYTES:
        raise ValueError("M03 bundle exceeds maximum bytes")
    try:
        with zipfile.ZipFile(io.BytesIO(encoded), "r") as archive:
            infos = archive.infolist()
            if ([item.filename for item in infos] != ["manifest.json", "dataset.json", "result.json"]
                    or any(item.compress_type != zipfile.ZIP_STORED or item.file_size > MAX_MEMBER_BYTES
                           for item in infos)):
                raise ValueError("M03 bundle members are not the exact bounded uncompressed set")
            raw = {item.filename: archive.read(item) for item in infos}
        parsed = {name: json.loads(value) for name, value in raw.items()}
    except (zipfile.BadZipFile, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("M03 bundle is invalid") from exc
    if any(not isinstance(parsed[name], dict) or canonical_bytes(parsed[name]) != raw[name] for name in raw):
        raise ValueError("M03 bundle JSON is not canonical")
    manifest, dataset, result = (parsed[name] for name in ("manifest.json", "dataset.json", "result.json"))
    if (set(manifest) != {"schema", "dataset_id", "job_id", "method_id", "parameters", "units",
                          "source", "provenance", "members", "raw_bytes_included"}
            or manifest.get("schema") != "geophysics.magnetic-processing-bundle/v1"
            or manifest.get("raw_bytes_included") is not False):
        raise ValueError("M03 bundle manifest schema mismatch")
    if manifest.get("members") != {
            name: {"sha256": sha256(raw[name]), "bytes": len(raw[name])}
            for name in ("dataset.json", "result.json")}:
        raise ValueError("M03 bundle member receipts do not verify")
    if manifest.get("dataset_id") != dataset.get("dataset_id") or manifest.get("job_id") != result.get("job_id"):
        raise ValueError("M03 bundle identity mismatch")
    if manifest.get("source") != {
            "source_id": dataset.get("source", {}).get("source_id"),
            "citation": dataset.get("source", {}).get("citation"),
            "rights_decision": dataset.get("rights_decision"),
            "rights_statement": dataset.get("rights_statement"),
            "attribution": dataset.get("attribution"),
            "processing_state": dataset.get("source", {}).get("processing_state")}:
        raise ValueError("M03 bundle source rights and lineage mismatch")
    if (manifest.get("units") != {"position": "m", "observation": "nT"}
            or manifest.get("method_id") != result.get("method_id")
            or manifest.get("parameters") != result.get("parameters")
            or manifest.get("provenance") != {
                "raw_sha256": dataset.get("parent_raw_sha256"),
                "dataset_sha256": sha256(raw["dataset.json"]),
                "result_sha256": sha256(raw["result.json"]),
                "request_sha256": result.get("request_sha256"),
                "engine_sha256": result.get("engine_sha256")}):
        raise ValueError("M03 bundle unit, method, parameters or provenance mismatch")
    _verify_result(dataset, result)
    return manifest, dataset, result
