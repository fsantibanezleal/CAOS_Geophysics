"""Bounded EDI envelope, method parameters and result identity for the private worker."""

from __future__ import annotations

import math
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.errors import ApiError


EDI_PARSER_VERSION = "edi-strict-envelope/v1"
M05_ID = "mt.edi-full-tensor-qc/v1"
M06_ID = "mt.edi-fixed-thickness-trf/v1"
EDI_SOURCE_LIMIT = 5 * 1024 * 1024
M05_MEMORY_BYTES = 768 * 1024 * 1024
M06_MEMORY_BYTES = 1024 * 1024 * 1024
M05_SCRATCH_BYTES = 8 * 1024 * 1024
M06_SCRATCH_BYTES = 32 * 1024 * 1024
M05_WALL_SECONDS = 90
M06_WALL_SECONDS = 300


class M05Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid")


class M06Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    qc_job_id: UUID
    thickness_m: list[float] = Field(max_length=1)
    initial_ohm_m: list[float] = Field(min_length=1, max_length=2)
    beta: float = Field(ge=0, le=1, allow_inf_nan=False)
    bootstrap_samples: int = Field(default=20, ge=20, le=40)
    seed: int = Field(default=61001, ge=0, le=2147483647)

    @field_validator("thickness_m", "initial_ohm_m", mode="before")
    @classmethod
    def numeric_vector(cls, value):
        if not isinstance(value, list) or any(type(item) not in (int, float) for item in value):
            raise ValueError("layer values must be JSON numbers, not booleans or strings")
        return value

    @field_validator("beta", mode="before")
    @classmethod
    def numeric_scalar(cls, value):
        if type(value) not in (int, float):
            raise ValueError("solver values must be JSON numbers, not booleans or strings")
        return value

    @field_validator("bootstrap_samples", "seed", mode="before")
    @classmethod
    def integer_scalar(cls, value):
        if type(value) is not int:
            raise ValueError("bootstrap count and seed must be JSON integers")
        return value

    @model_validator(mode="after")
    def physical_bounds(self):
        if len(self.initial_ohm_m) != len(self.thickness_m) + 1:
            raise ValueError("one starting resistivity is required per fixed layer")
        if any(not math.isfinite(value) or not 2 <= value <= 4000 for value in self.thickness_m):
            raise ValueError("finite-layer thickness must be in [2,4000] m so sensitivity stays bounded")
        if any(not math.isfinite(value) or not 1 < value < 6000 for value in self.initial_ohm_m):
            raise ValueError("starting resistivity must be strictly inside (1,6000) ohm m")
        return self


def parse_edi_envelope(raw: bytes, *, dataset_id: str, owner_id: str, project_id: str,
                       asset, source) -> dict:
    """Record supplied physics without asserting that the full EDI has yet passed M05."""
    if asset.detected_format != "edi" or not 128 <= len(raw) <= EDI_SOURCE_LIMIT:
        raise ApiError(422, "dataset_format_ineligible", "A bounded original EDI is required", ["asset_id"])
    if source.private_storage_permission != "attested":
        raise ApiError(422, "storage_permission_missing", "Private processing needs storage attestation")
    physical = asset.physical_metadata
    geometry = physical.get("geometry", {})
    fields = []
    if physical.get("measurement_unit") not in {"ohm", "mV/km/nT"}:
        fields.append("physical.measurement_unit")
    if geometry.get("sign_convention") not in {"+", "-"}:
        fields.append("physical.geometry.sign_convention")
    if geometry.get("variance_convention") not in {"complex", "per-real-component"}:
        fields.append("physical.geometry.variance_convention")
    if physical.get("component_frame") == "geographic ENU":
        if geometry.get("rotation_reference") != "geographic-north":
            fields.append("physical.geometry.rotation_reference")
    elif physical.get("component_frame") == "instrument axes":
        if geometry.get("rotation_reference") != "unspecified":
            fields.append("physical.geometry.rotation_reference")
    else:
        fields.append("physical.component_frame")
    components = geometry.get("tensor_components")
    if (not isinstance(geometry.get("station_id"), str) or not geometry["station_id"].strip()
            or type(geometry.get("frequency_count")) is not int
            or not 2 <= geometry["frequency_count"] <= 512
            or not isinstance(components, list) or len(components) not in (4, 6)
            or len(set(components)) != len(components)
            or set(components) not in ({"Zxx", "Zxy", "Zyx", "Zyy"},
                                       {"Zxx", "Zxy", "Zyx", "Zyy", "Tx", "Ty"})):
        fields.append("physical.geometry")
    if fields:
        raise ApiError(422, "dataset_physics_ineligible", "EDI needs explicit compatible conventions", fields)
    return {
        "schema": "geophysics.observation-dataset/v1", "dataset_id": dataset_id, "version": 1,
        "owner_id": owner_id, "project_id": project_id, "raw_asset_id": asset.id,
        "parent_raw_sha256": asset.sha256, "parent_raw_bytes": asset.byte_count,
        "parser_version": EDI_PARSER_VERSION, "modality": "edi_transfer_function",
        "dimensions": {"frequency": geometry["frequency_count"]}, "axis_order": ["frequency"],
        "physical_metadata": physical, "qc_verdict": "awaiting_full_tensor_qc",
        "source": {"provider": source.provider, "exact_url": source.exact_url,
                   "doi": source.doi, "citation": source.citation,
                   "rights_decision": source.rights_decision, "rights_statement": source.rights_statement,
                   "attribution": source.attribution},
    }


def validate_edi_dataset(payload: dict, dataset) -> None:
    if (payload.get("schema") != "geophysics.observation-dataset/v1"
            or payload.get("modality") != "edi_transfer_function"
            or payload.get("dataset_id") != dataset.id or payload.get("version") != dataset.version
            or payload.get("owner_id") != str(dataset.owner_id)
            or payload.get("project_id") != dataset.project_id
            or payload.get("raw_asset_id") != dataset.raw_asset_id
            or payload.get("parent_raw_sha256") != dataset.raw_sha256
            or payload.get("parser_version") != dataset.parser_version
            or payload.get("dimensions") != {"frequency": dataset.row_count}
            or payload.get("axis_order") != ["frequency"]
            or payload.get("qc_verdict") != "awaiting_full_tensor_qc"
            or not isinstance(payload.get("physical_metadata"), dict)
            or not isinstance(payload.get("source"), dict)):
        raise ApiError(409, "derived_integrity_failed", "EDI dataset identity differs from its receipt")


def validate_mt_result(payload: dict, job) -> None:
    from app.processing_contract import canonical_bytes, sha256

    if (payload.get("schema") != "geophysics.processing-result/v1"
            or payload.get("job_id") != job.id or payload.get("dataset_id") != job.dataset_id
            or payload.get("dataset_sha256") != job.dataset_sha256
            or payload.get("method_id") != job.method_id
            or payload.get("request_sha256") != job.request_sha256
            or payload.get("parameters") != job.request_json["parameters"]
            or payload.get("raw_sha256") != job.request_json["raw_sha256"]
            or payload.get("raw_asset_id") != job.request_json["raw_asset_id"]
            or not isinstance(payload.get("environment"), dict)
            or payload.get("environment_sha256") != sha256(canonical_bytes(payload["environment"]))
            or payload.get("axis_order") != ["frequency"]
            or not isinstance(payload.get("screen"), dict)):
        raise ApiError(409, "derived_integrity_failed", "MT result identity differs from its job receipt")
    if job.method_id == M05_ID and (payload.get("inverse") is not None
                                  or payload.get("screen", {}).get("inversion_performed") is not False):
        raise ApiError(409, "derived_integrity_failed", "M05 result must be QC only")
    if job.method_id == M06_ID and (not isinstance(payload.get("inverse"), dict)
                                  or payload.get("qc_screen_sha256") != job.request_json["qc_screen_sha256"]):
        raise ApiError(409, "derived_integrity_failed", "M06 result lacks its admitted inverse")
