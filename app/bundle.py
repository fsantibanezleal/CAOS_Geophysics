"""Hash-verified, private processing bundle for local round-trip inspection."""

from __future__ import annotations

import io
import json
import math
import statistics
import zipfile

from app.processing_contract import METHOD_ID, canonical_bytes, sha256


MAX_MEMBER_BYTES = 8 * 1024 * 1024


def build_bundle(dataset: dict, result: dict, dataset_sha: str, result_sha: str) -> bytes:
    dataset_bytes = canonical_bytes(dataset)
    result_bytes = canonical_bytes(result)
    if sha256(dataset_bytes) != dataset_sha or sha256(result_bytes) != result_sha:
        raise ValueError("bundle inputs disagree with stored receipts")
    manifest = {
        "schema": "geophysics.processing-bundle/v1",
        "dataset_id": dataset["dataset_id"], "job_id": result["job_id"],
        "method_id": result["method_id"], "parameters": result["parameters"],
        "rights_decision": dataset["rights_decision"], "rights_statement": dataset["rights_statement"],
        "axes": dataset["axis_order"], "dimensions": dataset["dimensions"],
        "units": {"position": "m", "observation": "mGal", "uncertainty": "mGal"},
        "provenance": {"raw_sha256": dataset["parent_raw_sha256"],
                       "dataset_sha256": dataset_sha, "request_sha256": result["request_sha256"],
                       "engine_sha256": result["engine_sha256"]},
        "members": {
            "dataset.json": {"sha256": dataset_sha, "bytes": len(dataset_bytes)},
            "result.json": {"sha256": result_sha, "bytes": len(result_bytes)},
        },
        "raw_bytes_included": False,
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("manifest.json", canonical_bytes(manifest))
        archive.writestr("dataset.json", dataset_bytes)
        archive.writestr("result.json", result_bytes)
    encoded = output.getvalue()
    verify_bundle(encoded)
    return encoded


def verify_bundle(encoded: bytes) -> tuple[dict, dict, dict]:
    """Strict local re-import; neither private paths nor raw bytes are accepted."""
    if len(encoded) > 2 * MAX_MEMBER_BYTES + 1024 * 1024:
        raise ValueError("processing bundle exceeds size cap")
    try:
        with zipfile.ZipFile(io.BytesIO(encoded), "r") as archive:
            names = archive.namelist()
            if names != ["manifest.json", "dataset.json", "result.json"]:
                raise ValueError("unexpected or duplicate bundle members")
            if any(item.file_size > MAX_MEMBER_BYTES or item.compress_type != zipfile.ZIP_STORED
                   for item in archive.infolist()):
                raise ValueError("bundle member exceeds bounds or uses compression")
            raw = {name: archive.read(name) for name in names}
        values = {name: json.loads(blob) for name, blob in raw.items()}
    except (zipfile.BadZipFile, UnicodeError, json.JSONDecodeError, KeyError) as exc:
        raise ValueError("invalid processing bundle") from exc
    if any(not isinstance(values[name], dict) or canonical_bytes(values[name]) != raw[name] for name in names):
        raise ValueError("noncanonical processing bundle")
    manifest, dataset, result = (values[name] for name in names)
    if (manifest.get("schema") != "geophysics.processing-bundle/v1"
            or dataset.get("schema") != "geophysics.observation-dataset/v1"
            or result.get("schema") != "geophysics.processing-result/v1"
            or not isinstance(manifest.get("members"), dict)
            or set(manifest.get("members", {})) != {"dataset.json", "result.json"}
            or manifest.get("raw_bytes_included") is not False):
        raise ValueError("processing bundle schema mismatch")
    for name in ("dataset.json", "result.json"):
        member = manifest["members"][name]
        if member != {"sha256": sha256(raw[name]), "bytes": len(raw[name])}:
            raise ValueError("processing bundle member hash mismatch")
    if (not isinstance(dataset.get("dimensions"), dict)
            or not isinstance(result.get("parameters"), dict)
            or not isinstance(dataset.get("physical_metadata"), dict)):
        raise ValueError("processing bundle nested contract mismatch")
    size = dataset["dimensions"].get("station")
    if (not isinstance(size, int) or size < 4
            or dataset.get("axis_order") != ["station"]
            or any(not isinstance(dataset.get(key), list) or len(dataset[key]) != size for key in
                   ("station_ids", "xyz_m", "observed_mgal", "sigma_mgal", "mask", "missing_reasons"))
            or any(not isinstance(result.get(key), list) or len(result[key]) != size for key in
                   ("observed_mgal", "sigma_mgal", "outlier_flag", "robust_score"))):
        raise ValueError("processing bundle array shape mismatch")
    if (manifest.get("dataset_id") != dataset.get("dataset_id")
            or manifest.get("dataset_id") != result.get("dataset_id")
            or manifest.get("job_id") != result.get("job_id")
            or manifest.get("method_id") != result.get("method_id")
            or manifest.get("parameters") != result.get("parameters")
            or manifest.get("rights_decision") != dataset.get("rights_decision")
            or manifest.get("rights_statement") != dataset.get("rights_statement")
            or result.get("observed_mgal") != dataset.get("observed_mgal")
            or result.get("sigma_mgal") != dataset.get("sigma_mgal")
            or result.get("station_ids") != dataset.get("station_ids")
            or result.get("xyz_m") != dataset.get("xyz_m")
            or result.get("rights_decision") != dataset.get("rights_decision")
            or result.get("rights_statement") != dataset.get("rights_statement")
            or result.get("physical_metadata") != dataset.get("physical_metadata")
            or result.get("axis_order") != dataset.get("axis_order")
            or result.get("dimensions") != dataset.get("dimensions")
            or manifest.get("provenance") != {
                "raw_sha256": dataset.get("parent_raw_sha256"),
                "dataset_sha256": sha256(raw["dataset.json"]),
                "request_sha256": result.get("request_sha256"),
                "engine_sha256": result.get("engine_sha256"),
            }
            or manifest.get("units") != {"position": "m", "observation": "mGal", "uncertainty": "mGal"}):
        raise ValueError("processing bundle identity, rights or units mismatch")
    if any(key in result for key in ("predicted", "model", "residual")):
        raise ValueError("flag-only processing result must not claim a solve")
    physical = dataset.get("physical_metadata", {})
    if (manifest.get("method_id") != METHOD_ID or physical.get("measurement_unit") != "mGal"
            or physical.get("horizontal_unit") != "m" or physical.get("vertical_unit") != "m"
            or dataset.get("uncertainty_kind") != "per_station_standard_deviation"
            or result.get("uncertainty_kind") != dataset.get("uncertainty_kind")
            or dataset.get("mask") != [False] * size
            or dataset.get("missing_reasons") != [None] * size
            or dataset.get("correction_history") != []
            or result.get("correction_history") != [{
                "method_id": METHOD_ID, "parameters": result["parameters"],
                "effect": "flag_only; observations and uncertainty unchanged",
            }]):
        raise ValueError("processing bundle physical or lineage contract mismatch")
    ids = dataset["station_ids"]
    xyz = dataset["xyz_m"]
    values = dataset["observed_mgal"]
    sigma = dataset["sigma_mgal"]
    scores = result["robust_score"]
    flags = result["outlier_flag"]
    finite_number = lambda value: type(value) in (int, float) and math.isfinite(value)
    if (any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != size
            or any(not isinstance(point, list) or len(point) != 3 or any(not finite_number(x) for x in point)
                   for point in xyz)
            or len({tuple(point) for point in xyz}) != size
            or any(not finite_number(value) for value in values)
            or any(not finite_number(value) or value <= 0 for value in sigma)
            or any(type(flag) is not bool for flag in flags)
            or any(not finite_number(score) or score < 0 for score in scores)):
        raise ValueError("processing bundle observation or flag type mismatch")
    threshold = result["parameters"].get("threshold")
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values)
    scale = 1.4826 * mad
    if (not finite_number(threshold) or not 1 <= threshold <= 10 or scale <= 0
            or flags != [abs(value - median) / scale > threshold for value in values]
            or any(not math.isclose(score, abs(value - median) / scale, rel_tol=1e-12, abs_tol=1e-12)
                   for score, value in zip(scores, values))
            or result.get("statistics") != {"median_mgal": median, "mad_mgal": mad,
                                            "scaled_mad_mgal": scale, "flagged_count": sum(flags)}):
        raise ValueError("processing bundle numerical result mismatch")
    return manifest, dataset, result
