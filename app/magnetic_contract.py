"""Closed owned survey input and executable method mapping; online stays closed."""

from __future__ import annotations

import hashlib
import csv
from decimal import Decimal
import io
import json
import math
from pathlib import Path
import sys
import struct
from uuid import UUID

from app.errors import ApiError
from app.magnetic_results import LOCAL_MAGNETIC_METHOD_ID
from app.processing_contract import canonical_bytes

PARSER_VERSION = "mag-survey/v1"
MODALITY = "magnetic_survey"
MAX_REQUEST = 8388608
MAX_DATASET = 8388608  # Complete serialized body, including escaped request and geometry.
MAX_ORIGINAL = 128 * 1024**2
DATASET_KEYS = frozenset("schema dataset_id version owner_id project_id raw_asset_id parent_raw_sha256 parent_raw_bytes parser_version modality dimensions axis_order request_utf8 request_sha256 geometry_plan source_record_id survey_source_id rights_decision private_storage_permission qc_verdict".split())


def science():
    pipeline = str(Path(__file__).resolve().parents[1] / "data-pipeline")
    if pipeline not in sys.path:
        sys.path.insert(0, pipeline)
    import magnetic_survey_json
    import magnetic_survey
    return magnetic_survey_json, magnetic_survey


def _refuse(code="magnetic_input_ineligible", status=422):
    raise ApiError(status, code, "Magnetic survey differs from its owned physical input")


def _uuid(value):
    try:
        valid = type(value) is str and str(UUID(value)) == value
    except ValueError:
        valid = False
    if not valid:
        _refuse()
    return value


def _source(asset, source, owner_id, project_id):
    if (str(asset.owner_id) != owner_id or str(source.owner_id) != owner_id
            or asset.project_id != project_id or source.project_id != project_id
            or asset.source_id != source.id):
        _refuse("not_found", 404)
    if (source.private_storage_permission != "attested" or source.rights_decision == "forbidden"
            or source.sha256 != asset.sha256):
        _refuse()


def validate_physical_record(meta, asset):
    frame = meta["frame"]
    physical = asset.physical_metadata
    expected = {"coordinate_reference": "local", "local_crs": frame["crs"],
                "axis_order": "xy", "horizontal_unit": "m", "vertical_unit": "m",
                "vertical_positive": "up", "vertical_datum": frame["vertical_datum"],
                "measurement_unit": "nT",
                "component_frame": "ENU" if meta["processing"]["quantity"] == "secondary_enu_nT" else "total field"}
    if (type(physical) is not dict or any(physical.get(k) != v for k, v in expected.items())
            or asset.detected_format != "magnetic_csv" or meta["intent"] != "local_calibrate"):
        _refuse()


def verify_original_columns(original, request, asset):
    """Exact declared direct-source codec, not inferred corrections or units."""
    columns = asset.physical_metadata.get("geometry")
    required = {"row_id_column", "line_id_column", "x_column", "y_column", "z_column", "value_column", "quantity"}
    if (type(columns) is not dict or not required <= set(columns)
            or set(columns) - required - {"component_columns", "timestamp_column"}
            or columns["quantity"] != request["processing"]["quantity"]
            or len(request["processing"]["nodes"]) != 1
            or request["processing"]["nodes"][0]["operation"] != "original"):
        _refuse()
    vector = columns["quantity"] == "secondary_enu_nT"
    if vector:
        components = columns.get("component_columns")
        if type(components) is not dict or set(components) != {"E", "N", "U"}:
            _refuse()
        values = [components[k] for k in ("E", "N", "U")]
        if columns["value_column"] != values[0]:
            _refuse()
    else:
        if "component_columns" in columns:
            _refuse()
        values = [columns["value_column"]]
    names = [columns[k] for k in ("row_id_column", "line_id_column", "x_column", "y_column", "z_column")] + values
    acquisition = request["acquisition"]
    recorded = acquisition["timestamp_policy"] == "recorded_utc"
    if recorded:
        names.append(columns.get("timestamp_column"))
    elif "timestamp_column" in columns:
        _refuse()
    if any(type(k) is not str or not 0 < len(k) <= 96 for k in names) or len(set(names)) != len(names):
        _refuse()
    def number(token):
        if type(token) is not str or not 0 < len(token) <= 64:
            _refuse()
        try:
            value = float(token)
            if not math.isfinite(value) or value == 0. and Decimal(token) != 0:
                _refuse()
            return value
        except (ValueError, ArithmeticError):
            _refuse()
    def same(a, b):
        return struct.pack("<d", number(a)) == struct.pack("<d", float(b))
    try:
        reader = csv.DictReader(io.StringIO(original.decode("utf-8-sig"), newline=""), strict=True)
        if reader.fieldnames is None or len(reader.fieldnames) != len(names) or set(reader.fieldnames) != set(names):
            _refuse()
        count = 0
        xyz = request["geometry"]["receivers_m"]["data"]
        observed = request["observations"]["values"]["data"]
        for i, row in enumerate(reader):
            count += 1
            if (count > len(acquisition["row_ids"]) or None in row or any(v is None for v in row.values())
                    or row[names[0]] != acquisition["row_ids"][i] or row[names[1]] != acquisition["group_ids"][i]
                    or any(not same(row[names[2+k]], xyz[3*i+k]) for k in range(3))
                    or any(not same(row[name], observed[len(values)*i+k]) for k,name in enumerate(values))
                    or recorded and row[names[-1]] != acquisition["timestamps"][i]):
                _refuse()
        if count != len(acquisition["row_ids"]):
            _refuse()
    except (UnicodeError, csv.Error):
        _refuse()


def parse_magnetic_dataset(request_raw: bytes, original: bytes, *, dataset_id: str,
                           owner_id: str, project_id: str, asset, source) -> dict:
    """No CSV guessing. Original bytes and full closed physical request are distinct."""
    _source(asset, source, owner_id, project_id)
    for value in (dataset_id, owner_id, project_id, asset.id):
        _uuid(value)
    if (type(original) is not bytes or not 0 < len(original) <= MAX_ORIGINAL
            or len(original) != asset.byte_count or hashlib.sha256(original).hexdigest() != asset.sha256
            or type(request_raw) is not bytes or not 0 < len(request_raw) <= MAX_REQUEST):
        _refuse()
    protocol, planner = science()
    try:
        handle = protocol.parse_request(request_raw)
        meta = handle.metadata()
        plan = planner.plan_geometry(handle)
    except protocol.InputError:
        _refuse()
    declared = meta["source"]
    # Database permission is for owner-private storage, not redistribution.
    if (declared["original_sha256"] != asset.sha256
            or declared["original_bytes"] != asset.byte_count
            or declared["rights"] != "private_user_supplied"
            or declared["scope"] != "complete_acquisition"):
        _refuse()
    validate_physical_record(meta, asset)
    # Geometry is already sealed above. Only now compare all source likelihood
    # values; no fitting callback receives this whole-survey materialization.
    verify_original_columns(original, json.loads(request_raw), asset)
    request_sha = hashlib.sha256(request_raw).hexdigest()
    return dict(schema="geophysics.observation-dataset/v1", dataset_id=dataset_id,
        version=1, owner_id=owner_id, project_id=project_id, raw_asset_id=asset.id,
        parent_raw_sha256=asset.sha256, parent_raw_bytes=asset.byte_count,
        parser_version=PARSER_VERSION + ":" + request_sha, modality=MODALITY,
        dimensions={"row": plan["preflight"]["rows"], "component": plan["preflight"]["components"]},
        axis_order=["row", "component"], request_utf8=request_raw.decode("utf-8"),
        request_sha256=request_sha, geometry_plan=plan,
        source_record_id=source.id, survey_source_id=declared["id"], rights_decision=source.rights_decision,
        private_storage_permission=source.private_storage_permission,
        qc_verdict="geometry_sealed_not_numerically_inverted")


def validate_magnetic_dataset(payload: dict, dataset) -> dict:
    """Recompute geometry from exact lexical request, not view-coordinate rounding."""
    if (type(payload) is not dict or set(payload) != DATASET_KEYS
            or payload["schema"] != "geophysics.observation-dataset/v1"
            or payload["dataset_id"] != dataset.id or payload["version"] != dataset.version
            or payload["owner_id"] != str(dataset.owner_id) or payload["project_id"] != dataset.project_id
            or payload["raw_asset_id"] != dataset.raw_asset_id or payload["parent_raw_sha256"] != dataset.raw_sha256
            or payload["parser_version"] != dataset.parser_version
            or payload["modality"] != dataset.modality or dataset.modality != MODALITY
            or payload["axis_order"] != ["row", "component"] or type(payload["request_utf8"]) is not str):
        _refuse("derived_integrity_failed", 409)
    raw = payload["request_utf8"].encode("utf-8")
    protocol, planner = science()
    try:
        handle = protocol.parse_request(raw)
        plan = planner.plan_geometry(handle)
        meta = handle.metadata()
    except protocol.InputError:
        _refuse("derived_integrity_failed", 409)
    if (hashlib.sha256(raw).hexdigest() != payload["request_sha256"]
            or dataset.parser_version != PARSER_VERSION + ":" + payload["request_sha256"]
            or canonical_bytes(plan) != canonical_bytes(payload["geometry_plan"])
            or payload["dimensions"] != {"row": dataset.row_count, "component": plan["preflight"]["components"]}
            or dataset.row_count != plan["preflight"]["rows"]
            or payload["parent_raw_bytes"] != meta["source"]["original_bytes"]
            or meta["source"]["original_sha256"] != dataset.raw_sha256
            or meta["source"]["id"] != payload["survey_source_id"]
            or meta["source"]["rights"] != "private_user_supplied"
            or meta["source"]["scope"] != "complete_acquisition"
            or payload["private_storage_permission"] != "attested"
            or payload["rights_decision"] == "forbidden"
            or payload["qc_verdict"] != "geometry_sealed_not_numerically_inverted"):
        _refuse("derived_integrity_failed", 409)
    # Full likelihood materialization is reserved for verified replay identity,
    # never supplied to geometry planning or an online optimizer.
    return json.loads(raw)


def method_mapping(payload: dict, dataset) -> dict:
    validate_magnetic_dataset(payload, dataset)
    pipeline = Path(__file__).resolve().parents[1] / "data-pipeline"
    names = {"parse": ("magnetic_survey_json.py", "parse_request"),
             "seal": ("magnetic_survey.py", "plan_geometry"),
             "calibrate": ("magnetic_calibration.py", "calibrate"),
             "local_tools": ("run_magnetic_survey.py", "main"),
             "read": ("magnetic_result_bundle.py", "read_bundle"),
             "export": ("magnetic_result_export.py", "export_zip")}
    import ast
    functions = {}
    for role, (name, function) in names.items():
        raw = (pipeline / name).read_bytes()
        if function not in {n.name for n in ast.parse(raw).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}:
            _refuse("magnetic_source_unavailable", 409)
        functions[role] = {"file": name, "function": function, "sha256": hashlib.sha256(raw).hexdigest()}
    return dict(schema="magnetic-owned-method-1", dataset_id=dataset.id, dataset_sha256=dataset.sha256,
        method_id=LOCAL_MAGNETIC_METHOD_ID, lane="local_replay", online_admitted=False,
        online_reason="magnetic_online_not_admitted", request_sha256=payload["request_sha256"],
        configuration_sha256=payload["geometry_plan"]["identity"]["configuration_sha256"], functions=functions)


def refuse_online_submission():
    raise ApiError(422, "magnetic_online_not_admitted", "Use the explicit local surveyed-input tool; replay is not online inversion")


def magnetic_dataset_receipt(dataset):
    """Existing dataset-list receipt shape with actual magnetic parser semantics."""
    from app.views import stored_utc
    if dataset.modality != MODALITY or not dataset.parser_version.startswith(PARSER_VERSION + ":"):
        _refuse("derived_integrity_failed", 409)
    return dict(dataset_id=dataset.id, project_id=dataset.project_id, raw_asset_id=dataset.raw_asset_id,
        version=dataset.version, schema="geophysics.observation-dataset/v1", modality=MODALITY,
        row_count=dataset.row_count, parser_version=dataset.parser_version, raw_sha256=dataset.raw_sha256,
        sha256=dataset.sha256, created_at=stored_utc(dataset.created_at).isoformat().replace("+00:00", "Z"),
        qc_verdict="geometry_sealed_not_numerically_inverted")
