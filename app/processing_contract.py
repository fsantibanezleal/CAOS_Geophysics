"""Private, versioned gravity observation and processing-result contracts."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path
from uuid import UUID

from app.config import Settings
from app.errors import ApiError
from app.models import ObservationDataset, ProcessingJob, RawAsset, SourceRecord


PARSER_VERSION = "gravity-station-csv/v1"
METHOD_ID = "gravity.station-outlier-flags/v1"
METHOD_MEMORY_BYTES = 256 * 1024 * 1024
METHOD_SCRATCH_BYTES = 8 * 1024 * 1024
METHOD_WALL_SECONDS = 30


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dataset_key(owner_id: str, project_id: str, dataset_id: str) -> str:
    return f"derived/{owner_id}/{project_id}/datasets/{dataset_id}.json"


def result_key(owner_id: str, project_id: str, job_id: str) -> str:
    return f"derived/{owner_id}/{project_id}/results/{job_id}.json"


def checked_derived_path(settings: Settings, key: str) -> Path:
    parts = Path(key).parts
    if len(parts) != 5 or parts[0] != "derived" or parts[3] not in {"datasets", "results"}:
        raise RuntimeError("invalid derived storage key")
    try:
        UUID(parts[1]); UUID(parts[2]); UUID(parts[4].removesuffix(".json"))
    except ValueError as exc:
        raise RuntimeError("invalid derived storage identity") from exc
    if not parts[4].endswith(".json"):
        raise RuntimeError("invalid derived storage suffix")
    path = settings.data_dir.joinpath(*parts)
    if not path.resolve(strict=False).is_relative_to(settings.data_dir.resolve()):
        raise RuntimeError("derived storage escapes private root")
    for parent in (path, *path.parents):
        if parent == settings.data_dir:
            break
        if parent.is_symlink():
            raise RuntimeError("derived storage symlink requires recovery")
    return path


def verified_json(settings: Settings, key: str, expected_sha: str, expected_bytes: int) -> dict:
    path = checked_derived_path(settings, key)
    if not path.is_file() or path.stat().st_size != expected_bytes:
        raise ApiError(409, "derived_integrity_failed", "Processed derivative is missing or changed")
    raw = path.read_bytes()
    if sha256(raw) != expected_sha:
        raise ApiError(409, "derived_integrity_failed", "Processed derivative differs from its receipt")
    try:
        parsed = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ApiError(409, "derived_integrity_failed", "Processed derivative is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ApiError(409, "derived_integrity_failed", "Processed derivative is not a JSON object")
    try:
        canonical = canonical_bytes(parsed)
    except (TypeError, ValueError) as exc:
        raise ApiError(409, "derived_integrity_failed", "Processed derivative contains invalid values") from exc
    if canonical != raw:
        raise ApiError(409, "derived_integrity_failed", "Processed derivative is not canonical JSON")
    return parsed


def _number(value: str, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(422, "dataset_value_invalid", "Station table has a nonnumeric value", [field]) from exc
    if not math.isfinite(number):
        raise ApiError(422, "dataset_value_invalid", "Station table has a nonfinite value", [field])
    return number


def parse_gravity_dataset(
    raw: bytes, *, dataset_id: str, owner_id: str, project_id: str,
    asset: RawAsset, source: SourceRecord, settings: Settings,
) -> dict:
    if len(raw) > settings.max_dataset_bytes:
        raise ApiError(413, "dataset_too_large", "Gravity dataset exceeds the processing byte cap")
    if asset.detected_format != "gravity_csv":
        raise ApiError(422, "dataset_format_ineligible", "Only gravity station CSV has a processing adapter", ["asset_id"])
    if source.private_storage_permission != "attested":
        raise ApiError(422, "storage_permission_missing", "Private processing requires an explicit storage attestation", ["source.private_storage_permission"])
    physical = asset.physical_metadata
    geometry = physical.get("geometry", {})
    if (physical.get("coordinate_reference") != "epsg" or physical.get("axis_order") != "xy"
            or physical.get("horizontal_unit") != "m" or physical.get("vertical_unit") != "m"
            or physical.get("measurement_unit") != "mGal" or not isinstance(geometry.get("sigma_column"), str)
            or not geometry["sigma_column"].strip()):
        raise ApiError(422, "dataset_physics_ineligible", "Gravity processing needs projected xy metres, vertical metres, mGal and a declared sigma column", ["physical"])
    names = [geometry.get(key) for key in (
        "station_id_column", "x_column", "y_column", "z_column", "value_column", "sigma_column",
    )]
    if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != 6:
        raise ApiError(422, "dataset_geometry_invalid", "Six distinct station columns are required", ["physical.geometry"])
    try:
        content = raw.decode("utf-8-sig", errors="strict")
        reader = csv.DictReader(io.StringIO(content, newline=""), strict=True)
        if reader.fieldnames is None or len(reader.fieldnames) != 6 or set(reader.fieldnames) != set(names):
            raise ApiError(422, "dataset_columns_invalid", "CSV must contain exactly the six declared columns", ["physical.geometry"])
        stations: list[str] = []
        coordinates: list[list[float]] = []
        values: list[float] = []
        sigma: list[float] = []
        seen_coordinates: set[tuple[float, float, float]] = set()
        for index, row in enumerate(reader, start=1):
            if index > settings.max_dataset_rows:
                raise ApiError(413, "dataset_row_limit", "Gravity dataset exceeds the station cap")
            if None in row or any(value is None for value in row.values()):
                raise ApiError(422, "dataset_columns_invalid", "CSV row has missing or extra columns", [f"rows.{index}"])
            station = row[names[0]].strip()
            if not station or station in stations:
                raise ApiError(422, "dataset_station_invalid", "Station IDs must be nonblank and unique", [f"rows.{index}.station"])
            xyz = tuple(_number(row[name], f"rows.{index}.{name}") for name in names[1:4])
            if xyz in seen_coordinates:
                raise ApiError(422, "dataset_geometry_invalid", "Duplicate XYZ station coordinates", [f"rows.{index}.xyz"])
            observed = _number(row[names[4]], f"rows.{index}.{names[4]}")
            uncertainty = _number(row[names[5]], f"rows.{index}.{names[5]}")
            if uncertainty <= 0:
                raise ApiError(422, "dataset_uncertainty_invalid", "Sigma must be positive in mGal", [f"rows.{index}.{names[5]}"])
            stations.append(station)
            coordinates.append(list(xyz))
            values.append(observed)
            sigma.append(uncertainty)
            seen_coordinates.add(xyz)
    except (UnicodeError, csv.Error) as exc:
        raise ApiError(422, "dataset_csv_invalid", "Gravity station CSV cannot be parsed", ["asset_id"]) from exc
    if len(stations) < 4:
        raise ApiError(422, "dataset_row_limit", "At least four stations are required", ["asset_id"])
    return {
        "schema": "geophysics.observation-dataset/v1", "dataset_id": dataset_id, "version": 1,
        "owner_id": owner_id, "project_id": project_id, "raw_asset_id": asset.id,
        "parent_raw_sha256": asset.sha256, "parser_version": PARSER_VERSION,
        "modality": "gravity_station", "dimensions": {"station": len(stations)},
        "axis_order": ["station"], "station_ids": stations, "xyz_m": coordinates,
        "observed_mgal": values, "sigma_mgal": sigma, "uncertainty_kind": "per_station_standard_deviation",
        "mask": [False] * len(stations), "missing_reasons": [None] * len(stations),
        "physical_metadata": physical, "correction_history": [],
        "qc_verdict": "parsed_for_flag_qc_only", "rights_decision": source.rights_decision,
        "rights_statement": source.rights_statement, "attribution": source.attribution,
    }


def validate_dataset_identity(payload: dict, dataset: ObservationDataset) -> None:
    if (payload.get("schema") != "geophysics.observation-dataset/v1"
            or payload.get("dataset_id") != dataset.id or payload.get("version") != dataset.version
            or payload.get("owner_id") != str(dataset.owner_id)
            or payload.get("project_id") != dataset.project_id
            or payload.get("raw_asset_id") != dataset.raw_asset_id
            or payload.get("parent_raw_sha256") != dataset.raw_sha256
            or payload.get("parser_version") != dataset.parser_version
            or payload.get("modality") != dataset.modality
            or payload.get("dimensions") != {"station": dataset.row_count}
            or len(payload.get("observed_mgal", [])) != dataset.row_count
            or len(payload.get("sigma_mgal", [])) != dataset.row_count):
        raise ApiError(409, "derived_integrity_failed", "Dataset identity or shape differs from its receipt")


def validate_result_identity(payload: dict, job: ProcessingJob) -> None:
    if (payload.get("schema") != "geophysics.processing-result/v1"
            or payload.get("job_id") != job.id or payload.get("dataset_id") != job.dataset_id
            or payload.get("dataset_sha256") != job.dataset_sha256
            or payload.get("method_id") != job.method_id
            or payload.get("request_sha256") != job.request_sha256
            or payload.get("parameters") != job.request_json["parameters"]
            or "predicted" in payload or "model" in payload or "residual" in payload):
        raise ApiError(409, "derived_integrity_failed", "Result identity differs from its job receipt")
