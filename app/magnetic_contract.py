"""Source-bound M03 flight-line dataset declaration and bounded CSV admission."""

from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pyproj import CRS

from app.errors import ApiError

PARSER_VERSION = "magnetic-flightline-original/v1"
MODALITY = "magnetic_flightline"
METHOD_ID = "magnetic.flightline-qc-grid/v1"
SOURCE_LIMIT = 50 * 1024 * 1024
ROW_LIMIT = 250_000
MEMORY_BYTES = 2 * 1024 * 1024 * 1024
SCRATCH_BYTES = 256 * 1024 * 1024
WALL_SECONDS = 600


class MagneticMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    easting: str = Field(min_length=1, max_length=128)
    northing: str = Field(min_length=1, max_length=128)
    value: str = Field(min_length=1, max_length=128)
    line_id: str = Field(min_length=1, max_length=128)
    line_role: str = Field(min_length=1, max_length=128)
    sensor_height_m: str = Field(min_length=1, max_length=128)
    sample_order: str = Field(min_length=1, max_length=128)

    @field_validator("easting", "northing", "value", "line_id", "line_role", "sensor_height_m", "sample_order")
    @classmethod
    def column_name_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("CSV column names must contain visible characters")
        return value.strip()

    @model_validator(mode="after")
    def distinct_columns(self):
        values = list(self.model_dump().values())
        if len(set(values)) != len(values):
            raise ValueError("each M03 physical quantity must map to a distinct CSV column")
        return self


class MagneticDatasetOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapping: MagneticMapping
    processing_state: str = Field(min_length=3, max_length=256)
    value_quantity: str = Field(min_length=3, max_length=128)
    sensor_height_reference: str = Field(min_length=3, max_length=128)

    @field_validator("processing_state", "value_quantity", "sensor_height_reference")
    @classmethod
    def declaration_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("M03 declarations must contain visible characters")
        return value.strip()


class MagneticParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grid_spacing_m: float = Field(gt=0, le=100_000, allow_inf_nan=False)
    holdout_fraction: float = Field(ge=0.05, le=0.5, allow_inf_nan=False)
    seed: str = Field(min_length=1, max_length=128)


def _fail(code: str, message: str, fields: list[str] | None = None) -> None:
    raise ApiError(422, code, message, fields or [])


def _scan_source(path: Path, mapping: MagneticMapping, expected_bytes: int) -> int:
    """Check the declared columns and row envelope without retaining CSV rows in API memory."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        _fail("magnetic_original_invalid", "M03 requires the owned regular CSV original", ["original"])
    size = path.stat().st_size
    if not 0 < size <= SOURCE_LIMIT or size != expected_bytes:
        _fail("dataset_too_large", "M03 original is empty, oversized or differs from its receipt", ["original"])
    names = set(mapping.model_dump().values())
    count = 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
                _fail("magnetic_columns_invalid", "M03 CSV header is missing or contains duplicate names", ["mapping"])
            missing = sorted(names - set(reader.fieldnames))
            if missing:
                _fail("magnetic_columns_missing", "M03 mapping names columns absent from the original", missing)
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    _fail("magnetic_row_invalid", "M03 CSV rows must have the exact declared header width", ["original"])
                count += 1
                if count > ROW_LIMIT:
                    _fail("dataset_row_limit", "M03 original exceeds its 250,000-row bound", ["original"])
    except (OSError, UnicodeError, csv.Error) as exc:
        _fail("magnetic_csv_invalid", f"M03 CSV cannot be scanned: {exc}", ["original"])
    if count < 12:
        _fail("dataset_row_limit", "M03 requires at least 12 observations", ["original"])
    return count


def create_dataset_envelope(*, raw_path: Path, dataset_id: str, owner_id: str, project_id: str,
                            asset, source, options: MagneticDatasetOptions) -> dict:
    """Bind M03's explicit map and physical declarations to the immutable raw receipt."""
    if asset.detected_format != "magnetic_csv" or source.declared_format != "magnetic_csv":
        _fail("method_ineligible", "M03 accepts only an owned magnetic CSV original", ["format"])
    if (str(asset.owner_id) != owner_id or asset.project_id != project_id
            or str(source.owner_id) != owner_id or source.project_id != project_id
            or source.id != asset.source_id):
        _fail("source_integrity_failed", "M03 source, asset and owner identities differ", ["source"])
    if source.private_storage_permission != "attested" or source.rights_decision == "forbidden":
        _fail("source_rights_ineligible", "M03 requires permitted, attested private storage", ["source.rights"])
    if not source.citation:
        _fail("source_citation_required", "M03 requires a source citation before dataset admission", ["source.citation"])
    physical = asset.physical_metadata
    if (not isinstance(physical, dict) or physical.get("measurement_unit") != "nT"
            or physical.get("horizontal_unit") != "m" or physical.get("vertical_unit") != "m"
            or physical.get("axis_order") != "xy"):
        _fail("dataset_physics_ineligible", "M03 requires projected x/y metres, sensor-height metres and nT", ["physical"])
    try:
        crs = CRS.from_epsg(physical["epsg"]) if physical.get("coordinate_reference") == "epsg" \
            else CRS.from_user_input(physical["local_crs"])
        if not crs.is_projected or not crs.axis_info or any(
                not math.isclose(axis.unit_conversion_factor or 0.0, 1.0, rel_tol=0, abs_tol=1e-12)
                for axis in crs.axis_info[:2]):
            raise ValueError("M03 coordinates must use a projected CRS in metres")
    except (KeyError, TypeError, ValueError):
        _fail("dataset_crs_ineligible", "M03 cannot verify the declared projected metric CRS", ["physical.crs"])
    count = _scan_source(raw_path, options.mapping, asset.byte_count)
    digest = hashlib.sha256()
    with Path(raw_path).open("rb") as original:
        for block in iter(lambda: original.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != asset.sha256:
        _fail("raw_integrity_failed", "M03 source bytes differ from the owned hash", ["original.sha256"])
    source_receipt = {
        "source_id": source.id, "provider": source.provider, "exact_url": source.exact_url,
        "doi": source.doi, "citation": source.citation, "rights_decision": source.rights_decision,
        "rights_statement": source.rights_statement, "attribution": source.attribution,
        "processing_state": options.processing_state.strip(), "value_quantity": options.value_quantity.strip(),
        "value_unit": "nT", "sensor_height_reference": options.sensor_height_reference.strip(),
    }
    frame = {"crs": crs.to_string(), "coordinates_are_projected": True, "linear_unit": "m"}
    return {
        "schema": "geophysics.observation-dataset/v1", "dataset_id": dataset_id, "version": 1,
        "owner_id": owner_id, "project_id": project_id, "raw_asset_id": asset.id,
        "parent_raw_sha256": asset.sha256, "parent_raw_bytes": asset.byte_count,
        "parser_version": PARSER_VERSION, "modality": MODALITY,
        "dimensions": {"measurement": count}, "axis_order": ["measurement"],
        "mapping": options.mapping.model_dump(mode="json"), "source": source_receipt,
        "frame": frame, "physical_metadata": physical,
        "rights_decision": source.rights_decision, "rights_statement": source.rights_statement,
        "attribution": source.attribution, "qc_verdict": "source_bound_not_numerically_processed",
    }


def validate_dataset_identity(payload: dict, dataset) -> None:
    try:
        mapping = MagneticMapping.model_validate(payload.get("mapping"))
        source = payload.get("source")
        frame = payload.get("frame")
        physical = payload.get("physical_metadata")
        crs = CRS.from_user_input(frame["crs"])
        valid_frame = (set(frame) == {"crs", "coordinates_are_projected", "linear_unit"}
                       and frame["coordinates_are_projected"] is True and frame["linear_unit"] == "m"
                       and crs.is_projected and bool(crs.axis_info)
                       and all(math.isclose(axis.unit_conversion_factor or 0.0, 1.0, rel_tol=0, abs_tol=1e-12)
                               for axis in crs.axis_info[:2]))
        valid_source = (isinstance(source, dict) and isinstance(source.get("source_id"), str)
                        and bool(source.get("citation")) and source.get("value_unit") == "nT"
                        and source.get("rights_decision") == payload.get("rights_decision")
                        and source.get("rights_statement") == payload.get("rights_statement")
                        and bool(source.get("processing_state")) and bool(source.get("value_quantity"))
                        and bool(source.get("sensor_height_reference")))
        if (payload.get("schema") != "geophysics.observation-dataset/v1"
                or payload.get("dataset_id") != dataset.id or payload.get("version") != dataset.version
                or payload.get("owner_id") != str(dataset.owner_id)
                or payload.get("project_id") != dataset.project_id
                or payload.get("raw_asset_id") != dataset.raw_asset_id
                or payload.get("parent_raw_sha256") != dataset.raw_sha256
                or payload.get("parser_version") != PARSER_VERSION or payload.get("modality") != MODALITY
                or payload.get("dimensions") != {"measurement": dataset.row_count}
                or type(dataset.row_count) is not int or not 12 <= dataset.row_count <= ROW_LIMIT
                or not valid_frame or not valid_source
                or not isinstance(physical, dict) or physical.get("measurement_unit") != "nT"
                or physical.get("horizontal_unit") != "m" or physical.get("vertical_unit") != "m"
                or physical.get("axis_order") != "xy"
                or payload.get("qc_verdict") != "source_bound_not_numerically_processed"):
            raise ValueError("M03 dataset fields differ from their declared contract")
        if set(mapping.model_dump()) != {"easting", "northing", "value", "line_id", "line_role", "sensor_height_m", "sample_order"}:
            raise ValueError("M03 field map differs from its declared contract")
    except (KeyError, TypeError, ValueError):
        raise ApiError(409, "derived_integrity_failed", "M03 dataset identity or shape differs from its receipt")
