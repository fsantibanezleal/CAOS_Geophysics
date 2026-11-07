"""Owned, original-byte M07/M09 envelopes; admission never loads native solvers."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

from pydantic import BaseModel, ConfigDict

from app.errors import ApiError
from app.processing_contract import canonical_bytes, sha256

PIPELINE = Path(__file__).resolve().parents[1] / "data-pipeline"
PARSER_VERSION = "supplied-profile-original/v1"
M07_ID = "ert.topographic-profile/v1"
M09_ID = "traveltime.first-arrival-profile/v1"
PROFILE_METHODS = (M07_ID, M09_ID)
PROFILE_FORMATS = {"ert_ohm": (M07_ID, "ert_profile", "ohm", "ABMN"),
                   "traveltime_sgt": (M09_ID, "traveltime_profile", "s", "source-receiver")}
PROFILE_SOURCE_LIMIT = 1_000_000  # Identical to the strict scientific parsers.
PROFILE_MEMORY_BYTES = 2 * 1024 * 1024 * 1024
PROFILE_SCRATCH_BYTES = 64 * 1024 * 1024
PROFILE_WALL_SECONDS = 600


class ProfileParameters(BaseModel):
    """Frozen, independently tested numerical settings; no disguised display knobs."""
    model_config = ConfigDict(extra="forbid")


def _workflow():
    if str(PIPELINE) not in sys.path:
        sys.path.insert(0, str(PIPELINE))
    import supplied_profiles
    return supplied_profiles


def profile_code_hashes(method: str) -> dict:
    engine = "ert.py" if method == M07_ID else "traveltime.py" if method == M09_ID else None
    if engine is None:
        raise ValueError("unsupported profile method")
    return {name: sha256((PIPELINE/name).read_bytes())
            for name in (engine, "supplied_profiles.py", "profile_mesh.py")}


def profile_child_hash() -> str:
    return sha256((PIPELINE.parent / "scripts/process_profile_job.py").read_bytes())


def _reject(fields: list[str]) -> None:
    raise ApiError(422, "profile_metadata_ineligible",
                   "Profile declarations differ from the original or its owned physical record", fields)


def parse_profile_envelope(raw: bytes, *, metadata: dict, dataset_id: str, owner_id: str,
                           project_id: str, asset, source) -> dict:
    """Parse the strict grammar from bytes; no native load or temporary original copy."""
    if asset.detected_format not in PROFILE_FORMATS:
        _reject(["format"])
    method, modality, unit, component = PROFILE_FORMATS[asset.detected_format]
    if (type(raw) is not bytes or not 0 < len(raw) <= PROFILE_SOURCE_LIMIT
            or len(raw) != asset.byte_count or sha256(raw) != asset.sha256):
        _reject(["original"])
    if (str(asset.owner_id) != owner_id or str(source.owner_id) != owner_id
            or asset.project_id != project_id or source.project_id != project_id
            or source.id != asset.source_id):
        _reject(["owner", "project", "source"])
    if source.private_storage_permission != "attested" or source.rights_decision == "forbidden":
        _reject(["source.rights"])
    workflow = _workflow()
    try:
        meta = workflow.parse_metadata(canonical_bytes(metadata))
    except (workflow.ProfileError, TypeError, ValueError, RecursionError):
        _reject(["profile_metadata"])
    frame, physical = meta["frame"], asset.physical_metadata
    if not isinstance(physical, dict) or not isinstance(physical.get("geometry"), dict):
        _reject(["physical.geometry"])
    fields = []
    if (meta["method"] != method or meta["source"]["source_id"] != source.id
            or meta["source"]["sha256"] != asset.sha256 or meta["source"]["bytes"] != asset.byte_count):
        fields.append("profile_metadata.source")
    expected = {"coordinate_reference": "local", "local_crs": frame["horizontal_reference"],
                "axis_order": "xy", "horizontal_unit": "m", "vertical_unit": "m",
                "vertical_positive": "up", "vertical_datum": frame["vertical_datum"],
                "measurement_unit": unit, "component_frame": component}
    fields.extend("physical."+name for name, value in expected.items() if physical.get(name) != value)
    if fields:
        _reject(fields)
    try:
        if method == M07_ID:
            import ert
            survey = ert.parse_ohm_bytes(raw)
            sensors = survey.sensors_xz_m
            rows = survey.abmn
            observed = survey.resistance_ohm
            geometry = {"sensor_xz_m": sensors.tolist(), "abmn_zero_based": rows.tolist()}
            qc = ert.qc(survey)
            declared_sensor_key = "electrode_count"
        else:
            import traveltime
            survey = traveltime.parse_sgt_bytes(raw)
            sensors, rows, observed = survey.sensor_xy_m, survey.shot_geophone, survey.time_s
            geometry = {"sensor_xy_m": sensors.tolist(), "shot_geophone_zero_based": rows.tolist()}
            qc = traveltime.qc(survey)
            declared_sensor_key = "sensor_count"
    except (ValueError, RuntimeError, TypeError, AssertionError):
        _reject(["original.geometry_or_observations"])
    declaration = physical.get("geometry", {})
    for name, actual in ((declared_sensor_key, len(sensors)), ("measurement_count", len(rows))):
        if type(declaration.get(name)) is not int or declaration[name] != actual:
            _reject(["physical.geometry."+name])
    geometry["row_ids_zero_based"] = list(range(len(rows)))
    return {"schema": "geophysics.observation-dataset/v1", "dataset_id": dataset_id,
            "owner_id": owner_id, "project_id": project_id, "raw_asset_id": asset.id,
            "parent_raw_sha256": asset.sha256, "parent_raw_bytes": asset.byte_count,
            "parser_version": PARSER_VERSION, "modality": modality, "method_id": method,
            "dimensions": {"sensor": len(sensors), "measurement": len(rows)},
            "axis_order": ["measurement"], "geometry": geometry,
            "observed": observed.tolist(), "observation_unit": unit,
            "profile_metadata": meta, "physical_metadata": json.loads(canonical_bytes(physical)),
            "qc": qc, "qc_verdict": "parsed_not_numerically_inverted", "truth": None}


def validate_profile_dataset(payload: dict, dataset) -> None:
    """Match immutable stored receipt before admitting a method or native child."""
    geometry = payload.get("geometry", {})
    dimensions = payload.get("dimensions", {})
    observed = payload.get("observed")
    formats = {item[0]: item[1:] for item in PROFILE_FORMATS.values()}
    method = payload.get("method_id")
    if (not isinstance(geometry, dict) or not isinstance(dimensions, dict)
            or not isinstance(observed, list) or method not in formats
            or payload.get("schema") != "geophysics.observation-dataset/v1"
            or payload.get("dataset_id") != dataset.id or payload.get("owner_id") != str(dataset.owner_id)
            or payload.get("project_id") != dataset.project_id or payload.get("raw_asset_id") != dataset.raw_asset_id
            or payload.get("parent_raw_sha256") != dataset.raw_sha256
            or payload.get("parser_version") != dataset.parser_version or dataset.parser_version != PARSER_VERSION
            or payload.get("modality") != dataset.modality or payload.get("method_id") not in PROFILE_METHODS
            or dimensions.get("measurement") != dataset.row_count
            or geometry.get("row_ids_zero_based") != list(range(dataset.row_count))
            or len(observed) != dataset.row_count or payload.get("truth") is not None):
        raise ApiError(409, "derived_integrity_failed", "Profile dataset differs from its owned receipt")
    workflow = _workflow()
    try:
        meta = workflow.parse_metadata(canonical_bytes(payload["profile_metadata"]))
        modality, unit, _ = formats[method]
        sensor_key, pair_key, width = (("sensor_xz_m", "abmn_zero_based", 4) if method == M07_ID
                                     else ("sensor_xy_m", "shot_geophone_zero_based", 2))
        sensors, pairs = geometry[sensor_key], geometry[pair_key]
        count = dimensions["sensor"]
        if (type(count) is not int or count < 2 or not isinstance(sensors, list) or len(sensors) != count
                or not isinstance(pairs, list) or len(pairs) != dataset.row_count
                or payload["modality"] != modality or payload.get("observation_unit") != unit
                or payload.get("axis_order") != ["measurement"]
                or meta["method"] != method or meta["source"]["sha256"] != dataset.raw_sha256
                or meta["source"]["bytes"] != payload.get("parent_raw_bytes")):
            raise ValueError("profile method/raw drift")
        finite = lambda value: type(value) in (int, float) and math.isfinite(value)
        if (any(not finite(value) for value in observed)
                or any(not isinstance(row, list) or len(row) != 2
                       or any(not finite(value) for value in row) for row in sensors)
                or any(not isinstance(row, list) or len(row) != width
                       or any(type(value) is not int or not 0 <= value < count for value in row)
                       for row in pairs)):
            raise ValueError("invalid physical arrays")
    except (KeyError, ValueError, TypeError, workflow.ProfileError):
        raise ApiError(409, "derived_integrity_failed", "Profile metadata differs from its owned receipt")


def validate_profile_result(payload: dict, job) -> None:
    """Validate worker identity and the portable scientific hash, including failures."""
    expected = {"schema": "geophysics.processing-result/v1", "job_id": job.id,
                "dataset_id": job.dataset_id, "dataset_sha256": job.dataset_sha256,
                "method_id": job.method_id, "request_sha256": job.request_sha256,
                "parameters": job.request_json["parameters"],
                "raw_asset_id": job.request_json["raw_asset_id"],
                "raw_sha256": job.request_json["raw_sha256"]}
    if any(payload.get(key) != value for key, value in expected.items()):
        raise ApiError(409, "derived_integrity_failed", "Profile result differs from its admitted job")
    workflow = _workflow()
    try:
        from app.profile_execution import validate_execution
        validate_execution(payload,job)
        result = payload["profile"]
        workflow._validate_result(result)
        if result["engine_report"]["inverse_status"] == "passed":
            _validate_passed_profile(result)
        if (result["method"] != job.method_id or result["original"]["sha256"] != payload["raw_sha256"]
                or payload.get("numerical_verdict") != result["engine_report"]["inverse_status"]
                or payload.get("raw_bytes") != result["original"]["bytes"]
                or payload.get("execution_lane") != "protected-worker" or payload.get("truth") is not None
                or sha256(canonical_bytes(payload["environment"])) != payload.get("environment_sha256")
                or payload.get("child_code_sha256") != job.request_json["profile_child_sha256"]
                or result["code_hashes"] != job.request_json["profile_code_hashes"]):
            raise ValueError("profile numerical verdict/raw drift")
    except (KeyError, TypeError, ValueError, workflow.ProfileError):
        raise ApiError(409, "derived_integrity_failed", "Profile scientific result integrity failed")


def _validate_passed_profile(result: dict) -> None:
    """Report-level scientific gates, not an independent native solver replay."""
    report = result["engine_report"]
    maximum = result["numerical_settings"]["maxIter"]
    if type(maximum) is not int or not 1 <= maximum <= 100:
        raise ValueError("invalid inverse iteration limit")
    def finite(value):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("nonfinite scientific gate")
        return value
    def stopped(fit):
        iterations = fit["iterations"]
        if (type(iterations) is not int or not 0 <= iterations < maximum
                or fit["stopping_reason"] not in {"objective-stagnation", "assumed-chi2-target"}):
            raise ValueError("passed inverse did not stop before the ceiling")
    if result["method"] == M07_ID:
        primary, blocked = report["inverse"], report["blocked_validation"]
        stopped(primary)
        if (primary["engine_converged"] is not True
                or finite(primary["heldout_improvement_vs_homogeneous"]) < .1
                or blocked["engine_stopped_before_limit"] is not True
                or finite(blocked["improvement_vs_homogeneous"]) < .1
                or type(blocked["iterations"]) is not int or not 0 <= blocked["iterations"] < maximum
                or not 0 <= finite(report["factors"]["flat_formula_max_relative_error"]) <= 1e-5):
            raise ValueError("passed ERT report failed independent prediction/factor gates")
    else:
        for name in ("max_relative_error", "reciprocity_relative_error", "max_speed_scaling_relative_error"):
            if not 0 <= finite(report["homogeneous_oracle"][name]) <= 1e-3:
                raise ValueError("passed traveltime report failed homogeneous oracle")
        rows = result["geometry"]["shot_geophone_zero_based"]
        for name in ("interleaved", "central_block"):
            fit, split = report["inverse"][name], report["split"][name]
            stopped(fit)
            held = split["heldout_rows"]
            if not isinstance(held, list) or any(type(index) is not int or not 0 <= index < len(rows) for index in held):
                raise ValueError("invalid original held-row indices")
            shots = {rows[index][0] for index in held}
            improved = fit["improved_held_shot_count"]
            if (not shots or type(improved) is not int or not math.ceil(2*len(shots)/3) <= improved <= len(shots)
                    or fit["engine_stopped_before_limit"] is not True or finite(fit["heldout_improvement"]) < .1):
                raise ValueError("passed traveltime report failed whole-shot prediction gates")
