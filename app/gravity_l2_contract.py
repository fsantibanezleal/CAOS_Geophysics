from __future__ import annotations

import math
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


METHOD_ID = "gravity.survey-l2-ordinary/v1"
PARAMETER_SCHEMA = "gravity.survey-l2-parameters/v1"
METHOD_MEMORY_BYTES = 2 * 1024**3
METHOD_SCRATCH_BYTES = 256 * 1024**2
METHOD_WALL_SECONDS = 600
MAX_CELLS = 4096
MAX_STATIONS = 2048


def _numbers(value, field: str, *, maximum: int = MAX_CELLS):
    if (type(value) is not list or not 1 <= len(value) <= maximum
            or any(type(item) not in (int, float) or not math.isfinite(item) for item in value)):
        raise ValueError(f"{field} must be a bounded list of finite JSON numbers")
    return [float(item) for item in value]


class GravityMesh(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    origin_m: list[float]
    hx_m: list[float]
    hy_m: list[float]
    hz_m: list[float]
    active: list[bool]

    @field_validator("origin_m", "hx_m", "hy_m", "hz_m", mode="before")
    @classmethod
    def numeric_vectors(cls, value, info):
        return _numbers(value, info.field_name, maximum=3 if info.field_name == "origin_m" else MAX_CELLS)

    @field_validator("active", mode="before")
    @classmethod
    def exact_bool_vector(cls, value):
        if type(value) is not list or not 1 <= len(value) <= MAX_CELLS or any(type(v) is not bool for v in value):
            raise ValueError("active must be a bounded list of exact booleans")
        return value

    @model_validator(mode="after")
    def bounded_mesh(self):
        if len(self.origin_m) != 3 or any(not v > 0 for v in (*self.hx_m, *self.hy_m, *self.hz_m)):
            raise ValueError("mesh needs a 3-vector origin and positive cell widths")
        count = len(self.hx_m) * len(self.hy_m) * len(self.hz_m)
        if count > MAX_CELLS or len(self.active) != count or not any(self.active):
            raise ValueError("mesh full-cell count, active mask or active population is invalid")
        return self


class GravitySplit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    block_origin_m: list[float]
    block_size_m: list[float]
    buffer_m: float = Field(gt=0, allow_inf_nan=False)
    seed: int

    @field_validator("block_origin_m", "block_size_m", mode="before")
    @classmethod
    def two_numbers(cls, value, info):
        result = _numbers(value, info.field_name, maximum=2)
        if len(result) != 2:
            raise ValueError(f"{info.field_name} must contain two values")
        return result

    @field_validator("buffer_m", mode="before")
    @classmethod
    def finite_buffer(cls, value):
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError("buffer_m must be a positive finite JSON number")
        return float(value)

    @field_validator("seed", mode="before")
    @classmethod
    def frozen_seed(cls, value):
        if type(value) is not int or value != 104729:
            raise ValueError("M02 ordinary-L2 split seed is frozen at 104729")
        return value

    @model_validator(mode="after")
    def positive_blocks(self):
        if any(v <= 0 for v in self.block_size_m):
            raise ValueError("block_size_m must be positive")
        return self


class GravityPrior(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    lower_kg_m3: list[float]
    upper_kg_m3: list[float]
    start_kg_m3: list[float]
    reference_kg_m3: list[float]
    density_scale_kg_m3: float = Field(gt=0, allow_inf_nan=False)
    lengths_m: list[float]
    basis: str = Field(min_length=1, max_length=1024)
    reference_in_smooth: bool
    spatial_weights: str

    @field_validator("lower_kg_m3", "upper_kg_m3", "start_kg_m3", "reference_kg_m3", "lengths_m", mode="before")
    @classmethod
    def finite_vectors(cls, value, info):
        return _numbers(value, info.field_name, maximum=3 if info.field_name == "lengths_m" else MAX_CELLS)

    @field_validator("density_scale_kg_m3", mode="before")
    @classmethod
    def finite_scale(cls, value):
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError("density_scale_kg_m3 must be positive and finite")
        return float(value)

    @field_validator("basis", mode="before")
    @classmethod
    def exact_basis(cls, value):
        if type(value) is not str or not value.strip() or len(value) > 1024:
            raise ValueError("prior basis must be an explicit nonblank declaration")
        return value

    @field_validator("reference_in_smooth", mode="before")
    @classmethod
    def smooth_reference(cls, value):
        if type(value) is not bool or value is not True:
            raise ValueError("ordinary L2 requires reference_in_smooth=true")
        return value

    @field_validator("spatial_weights", mode="before")
    @classmethod
    def fixed_weights(cls, value):
        if type(value) is not str or value != "none":
            raise ValueError("ordinary L2 spatial_weights is frozen at none")
        return value

    @model_validator(mode="after")
    def vectors_and_bounds(self):
        a = len(self.lower_kg_m3)
        if not a or any(len(getattr(self, name)) != a for name in
                        ("upper_kg_m3", "start_kg_m3", "reference_kg_m3")):
            raise ValueError("all prior vectors must have equal active-cell length")
        if len(self.lengths_m) != 3 or any(value <= 0 for value in self.lengths_m):
            raise ValueError("lengths_m must contain three positive lengths")
        for lo, hi, start in zip(self.lower_kg_m3, self.upper_kg_m3, self.start_kg_m3):
            if lo >= hi or start < lo or start > hi:
                raise ValueError("finite signed bounds must be ordered and contain the supplied start")
        return self


class GravityL2Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)
    schema_version: str = Field(alias="schema")
    background_mgal: float
    mesh: GravityMesh
    split: GravitySplit
    prior: GravityPrior

    @field_validator("schema_version", mode="before")
    @classmethod
    def exact_schema(cls, value):
        if type(value) is not str or value != PARAMETER_SCHEMA:
            raise ValueError(f"schema must equal {PARAMETER_SCHEMA}")
        return value

    @field_validator("background_mgal", mode="before")
    @classmethod
    def finite_background(cls, value):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("background_mgal must be a finite JSON number")
        return float(value)

    @model_validator(mode="after")
    def active_prior_shape(self):
        if len(self.prior.lower_kg_m3) != sum(self.mesh.active):
            raise ValueError("prior vectors must match the active-cell count")
        return self


def eligible_upload(payload: dict, asset, source) -> tuple[bool, list[str]]:
    """Return only source-declaration eligibility; this is not host admission."""
    reasons: list[str] = []
    physical = payload.get("physical_metadata", {})
    geometry = physical.get("geometry", {})
    declaration = geometry.get("ordinary_l2")
    if type(declaration) is not dict:
        return False, ["Explicit ordinary_l2 processing, error and group declarations are required"]
    if payload.get("modality") != "gravity_station" or payload.get("parser_version") != "gravity-station-csv/v1":
        reasons.append("Only the source-bound gravity station CSV parser is supported")
    if asset.sha256 != payload.get("parent_raw_sha256") or asset.byte_count <= 0:
        reasons.append("Original asset identity is not bound to the parsed dataset")
    if asset.detected_format != "gravity_csv" or source.sha256 != asset.sha256:
        reasons.append("Original gravity CSV or source-record hash is not verified")
    if source.private_storage_permission != "attested" or source.rights_decision == "forbidden":
        reasons.append("Private processing rights/storage permission are missing")
    if not source.citation or not source.attribution or not source.rights_statement:
        reasons.append("Citation, attribution and rights statement are required")
    if (physical.get("coordinate_reference") != "local" or physical.get("axis_order") != "xy"
            or physical.get("horizontal_unit") != "m" or physical.get("vertical_unit") != "m"
            or physical.get("vertical_positive") != "up" or physical.get("measurement_unit") != "mGal"
            or physical.get("component_frame") != "local vertical up"):
        reasons.append("Ordinary L2 requires declared local east/north/up coordinates in metres and upward mGal")
    required = {
        "quantity": "processed_gravity_anomaly",
        "processing_kind": "provider_declared_derivative",
        "correction_state": "complete_no_additional_corrections",
        "original_acceleration_unit": "mGal",
        "original_vertical_positive": "up",
        "sigma_basis": {"measured_gaussian", "propagated_independent_gaussian", "explicit_conditional_gaussian"},
        "cross_partition_dependence": {"declared_absent", "possible_not_removed"},
    }
    for key, expected in required.items():
        value = declaration.get(key)
        valid = type(value) is str and value in expected if isinstance(expected, set) else value == expected
        if not valid:
            reasons.append(f"Explicit eligible gravity declaration required: {key}")
    for key in ("reference_description", "sigma_citation", "background_reference", "partition_group_column"):
        value = declaration.get(key)
        if type(value) is not str or not value.strip() or value.strip().lower() in {"unknown", "unspecified", "none"}:
            reasons.append(f"Explicit non-unknown {key} is required")
    if not isinstance(declaration.get("partition_group_column"), str) or declaration.get("partition_group_column") not in payload.get("raw_columns", []):
        reasons.append("A declared acquisition group column must exist in the raw table")
    return not reasons, reasons


def implementation_hashes() -> dict[str, str]:
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    pipeline = root / "data-pipeline"
    paths = {
        "adapter": Path(__file__),
        "pipeline_adapter": root / "app" / "gravity_l2_compute.py",
        "dataset_contract": root / "app" / "processing_contract.py",
        "forward": pipeline / "gravity_forward.py",
        "survey_plan": pipeline / "gravity_survey_l2.py",
        "inverse": pipeline / "gravity_l2.py",
        "metric": pipeline / "gravity_l2_metric.py",
        "precision": pipeline / "gravity_l2_precision.py",
    }
    return {key: __import__("hashlib").sha256(path.read_bytes()).hexdigest()
            for key, path in paths.items()}


def validate_typed_arrays(value) -> None:
    import hashlib
    import numpy as np
    if type(value) is dict:
        if value.get("kind") == "ndarray":
            if set(value) != {"kind", "dtype", "shape", "order", "sha256", "data"} or value["order"] != "C":
                raise ValueError("typed result array descriptor has unknown fields")
            dtype = value["dtype"]
            if dtype not in {"<f8", "<i8", "|b1"}:
                raise ValueError("typed result array dtype is outside the M02 contract")
            shape = value["shape"]
            if type(shape) is not list or any(type(dim) is not int or dim < 0 for dim in shape):
                raise ValueError("typed result array shape is invalid")
            array = np.asarray(value["data"], dtype=np.dtype(dtype))
            if array.size != math.prod(shape) or list(array.shape) != shape:
                try:
                    array = array.reshape(shape)
                except ValueError as exc:
                    raise ValueError("typed result array data does not match its shape") from exc
            if array.dtype.kind == "f" and not np.isfinite(array).all():
                raise ValueError("typed result array contains non-finite values")
            if hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest() != value["sha256"]:
                raise ValueError("typed result array SHA-256 mismatch")
            return
        for item in value.values():
            validate_typed_arrays(item)
    elif type(value) is list:
        for item in value:
            validate_typed_arrays(item)


def validate_result(payload: dict, job) -> None:
    from app.processing_contract import canonical_bytes, sha256
    expected = {
        "schema": "geophysics.processing-result/v1",
        "job_id": job.id,
        "dataset_id": job.dataset_id,
        "dataset_sha256": job.dataset_sha256,
        "method_id": METHOD_ID,
        "request_sha256": job.request_sha256,
        "parameters": job.request_json["parameters"],
        "raw_asset_id": job.request_json.get("raw_asset_id"),
        "raw_sha256": job.request_json.get("raw_sha256"),
        "raw_bytes": job.request_json.get("raw_bytes"),
        "source_id": job.request_json.get("source_id"),
        "implementation_sha256": job.request_json.get("implementation_sha256"),
        "parameter_schema": PARAMETER_SCHEMA,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise ValueError("M02 result does not match its immutable owner/job/source receipt")
    block = payload.get("gravity_l2")
    required = {"schema", "plan_native_sha256", "calibration_native_sha256", "evaluation_native_sha256",
                "plan", "calibration", "outer_evaluation", "source", "units", "field_truth", "scope"}
    if type(block) is not dict or set(block) != required or block.get("schema") != "geophysics.gravity-survey-l2-result/v1":
        raise ValueError("M02 result block has an unknown schema or field set")
    if payload.get("gravity_l2_sha256") != sha256(canonical_bytes(block)):
        raise ValueError("M02 typed result block hash mismatch")
    if payload.get("environment_sha256") != sha256(canonical_bytes(payload.get("environment"))):
        raise ValueError("M02 runtime environment hash mismatch")
    for key, result_key, native_key in (("plan_native_sha256", "plan", "plan_sha256"),
                                        ("calibration_native_sha256", "calibration", "result_sha256"),
                                        ("evaluation_native_sha256", "outer_evaluation", "result_sha256")):
        if type(block[key]) is not str or len(block[key]) != 64:
            raise ValueError("M02 native result digest is malformed")
        if block[result_key].get(native_key) != block[key]:
            raise ValueError("M02 serialized native result digest differs from the execution receipt")
    if (block["source"].get("raw_sha256") != expected["raw_sha256"]
            or block["source"].get("raw_bytes") != expected["raw_bytes"]
            or block["field_truth"] is not None
            or block["scope"] != {"field_eligible": False, "full_M02_accepted": False,
                                  "GPU_accepted": False, "host_accepted": False}
            or block["units"] != {"model": "kg/m3", "observed": "mGal", "coordinates": "m"}):
        raise ValueError("M02 result contains an invalid source, units or scientific nonclaim")
    if payload.get("environment", {}).get("native_epoch") is None:
        raise ValueError("M02 result omits its pinned numerical runtime epoch")
    validate_typed_arrays(block)
