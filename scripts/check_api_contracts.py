"""Check API route coverage, JSON Schema references and representative payloads."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
METHODS = {"get", "post", "put", "patch", "delete"}
SCHEMA_PATH = ROOT / "docs/contracts/schemas/api-payloads.schema.json"
OPENAPI_PATH = ROOT / "docs/contracts/api.openapi.json"


def _source_routes(path: Path) -> set[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    prefixes: dict[str, str] = {"app": ""}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name) or value.func.id != "APIRouter":
            continue
        prefix = next((keyword.value.value for keyword in value.keywords
                       if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant)
                       and isinstance(keyword.value.value, str)), "")
        for target in targets:
            if isinstance(target, ast.Name):
                prefixes[target.id] = prefix

    routes: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr.lower()
            base = decorator.func.value
            if method not in METHODS or not isinstance(base, ast.Name) or base.id not in prefixes:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                raise AssertionError(f"nonliteral API route in {path}:{node.lineno}")
            route = decorator.args[0].value
            if not isinstance(route, str):
                raise AssertionError(f"non-string API route in {path}:{node.lineno}")
            routes.add((prefixes[base.id] + route, method))
    return routes


def _pointer(document: dict, pointer: str):
    value = document
    for part in pointer.lstrip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def _check_references(value, document: dict, schema_doc: dict) -> list[str]:
    problems: list[str] = []
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            if ref.startswith("#/"):
                try:
                    _pointer(document, ref[1:])
                except (KeyError, IndexError, ValueError, TypeError):
                    problems.append(f"unresolved OpenAPI reference: {ref}")
            elif ref.startswith("schemas/api-payloads.schema.json#/"):
                try:
                    _pointer(schema_doc, ref.split("#", 1)[1])
                except (KeyError, IndexError, ValueError, TypeError):
                    problems.append(f"unresolved JSON Schema reference: {ref}")
            else:
                problems.append(f"unsupported external reference form: {ref}")
        for child in value.values():
            problems.extend(_check_references(child, document, schema_doc))
    elif isinstance(value, list):
        for child in value:
            problems.extend(_check_references(child, document, schema_doc))
    return problems


def check_contracts(root: Path = ROOT) -> list[str]:
    issues: list[str] = []
    try:
        schema_doc = json.loads((root / "docs/contracts/schemas/api-payloads.schema.json").read_text(encoding="utf-8"))
        openapi = json.loads((root / "docs/contracts/api.openapi.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"contract JSON is unreadable: {error}"]

    if openapi.get("openapi") != "3.1.0":
        issues.append("API contract must use OpenAPI 3.1.0")
    issues.extend(_check_references(openapi, openapi, schema_doc))
    try:
        Draft202012Validator.check_schema(schema_doc)
    except Exception as error:  # jsonschema exposes several validation exception subclasses.
        issues.append(f"API JSON Schema is invalid: {error}")

    expected: set[tuple[str, str]] = set()
    for source in ("app/auth.py", "app/security.py", "app/projects.py", "app/processing.py"):
        expected |= _source_routes(root / source)
    # FastAPI-Users contributes these literal routes through include_router().
    expected |= {
        ("/api/auth/cookie/login", "post"), ("/api/auth/cookie/logout", "post"),
        ("/api/auth/register", "post"), ("/api/auth/verify/request", "post"),
        ("/api/auth/verify/verify", "post"), ("/api/auth/reset-password/forgot-password", "post"),
        ("/api/auth/reset-password/reset-password", "post"),
    }
    actual: set[tuple[str, str]] = set()
    conditional: set[tuple[str, str]] = set()
    for route, item in openapi.get("paths", {}).items():
        for method, operation in item.items():
            if method not in METHODS:
                continue
            actual.add((route, method))
            if operation.get("x-registered-when") == "auth_mode=email":
                conditional.add((route, method))
            responses = operation.get("responses", {})
            if not any(code.startswith("2") for code in responses):
                issues.append(f"{route} {method.upper()} has no documented success response")
            if method in {"post", "put", "patch", "delete"}:
                security = operation.get("security", openapi.get("security", []))
                required = {scheme for requirement in security for scheme in requirement}
                if not {"csrfToken", "csrfCookie"} <= required:
                    issues.append(f"{route} {method.upper()} omits the implemented CSRF header/cookie requirement")
            body = operation.get("requestBody")
            if body and any("schema" not in media for media in body.get("content", {}).values()):
                issues.append(f"{route} {method.upper()} request body has a media type without a schema")
            for code, response in responses.items():
                if "$ref" in response:
                    continue
                for media, definition in response.get("content", {}).items():
                    if "schema" not in definition:
                        issues.append(f"{route} {method.upper()} response {code} {media} has no schema")
    if expected != actual:
        issues.extend(f"route inventory mismatch: {path} {method.upper()} {direction} OpenAPI"
                      for path, method in sorted(expected - actual)
                      for direction in ["missing from"])
        issues.extend(f"route inventory mismatch: {path} {method.upper()} is extra in OpenAPI"
                      for path, method in sorted(actual - expected))
    expected_email = {route for route in expected if route[0] in {
        "/api/auth/register", "/api/auth/verify/request", "/api/auth/verify/verify",
        "/api/auth/reset-password/forgot-password", "/api/auth/reset-password/reset-password",
    }}
    if conditional != expected_email:
        issues.append("email-mode conditional route set differs from FastAPI-Users router installation")

    ids = [operation.get("operationId") for path in openapi.get("paths", {}).values()
           for method, operation in path.items() if method in METHODS]
    if len(ids) != len(set(ids)) or any(not item for item in ids):
        issues.append("every API operation must have a unique operationId")

    registry = Registry().with_resource(schema_doc["$id"], Resource.from_contents(schema_doc))
    samples = {
        "ProjectCreate": ({"name": "Field campaign", "description": ""}, {"name": "  "}),
        "ProjectUpdate": ({"description": "Updated"}, {"unknown": True}),
        "SourceInput": ({"provider": "Survey group", "rights_statement": "Private-use permission granted",
                         "rights_decision": "derivative-only", "private_storage_permission": "attested",
                         "attribution": "Survey group", "expected_sha256": "a" * 64},
                        {"provider": "x", "rights_statement": "x", "rights_decision": "unknown",
                         "private_storage_permission": "attested", "attribution": "x"}),
        "DatasetCreate": ({"asset_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41"}, {"asset_id": "bad-id"}),
        "M06Parameters": ({"qc_job_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41", "thickness_m": [350],
                           "initial_ohm_m": [100, 20], "beta": 0.5},
                          {"qc_job_id": "bad-id", "thickness_m": [1], "initial_ohm_m": [], "beta": 2}),
        "WaveformDatasetPayload": ({"schema": "geophysics.waveform-dataset/v1", "dataset_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                                     "version": 1, "owner_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                                     "project_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                                     "raw_asset_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41", "parent_raw_sha256": "a" * 64,
                                     "parser_version": "m08/v1/" + "b" * 64, "modality": "waveform_counts_response",
                                     "dimensions": {"channel": 1, "sample": 100, "record": 1},
                                     "sources": {"miniseed": {}, "stationxml": {}}, "request": {},
                                     "scientific_request_sha256": "b" * 64,
                                     "qc_verdict": "structural_index_not_physical_qc"},
                                    {"schema": "geophysics.observation-dataset/v1"}),
        "PhysicalDatasetPayload": ({"schema": "geophysics.physical-dataset/v2", "dataset_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                                     "version": 1, "owner_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                                     "project_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                                     "raw_asset_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41", "raw_sha256": "a" * 64,
                                     "raw_bytes": 1, "parser_version": "gravity-stations-json/v1",
                                     "root_dataset_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                                     "parent_dataset_id": None, "parent_dataset_sha256": None, "kind": "root",
                                     "modality": "gravity_physical_station", "payload_schema": "gravity-stations-1",
                                     "scientific_payload_sha256": "b" * 64,
                                     "payload": {"schema_version": "gravity-stations-1", "metadata": {
                                         "source_kind": "field", "source_sha256": "c" * 64,
                                         "source_citation": "Survey citation", "rights": "Private-use permission",
                                         "crs": "EPSG:4326", "reference_ellipsoid": "WGS84", "height_datum": "ellipsoidal",
                                         "height_unit": "m", "height_sign": "upward", "gravity_unit": "mGal",
                                         "gravity_sign": "downward", "gravity_quantity": "absolute_gravity",
                                         "gravity_datum": "Local datum", "tide_system": "tide_free",
                                         "instrument_processing": {name: {"status": "applied", "citation": "Instrument record"}
                                                                    for name in ("calibration", "drift", "tide")}},
                                         "state": "observed_absolute", "stations": [{"station_id": "S1", "latitude_deg": -33.0,
                                         "longitude_deg": -70.0, "receiver_height_m": 10.0, "surface_height_m": 9.0,
                                         "original_value": 980000.0, "value_mgal": 980000.0, "gravity_sigma": 0.1,
                                         "receiver_sigma_m": 0.01, "surface_sigma_m": 0.02, "latitude_sigma_deg": 0.0}],
                                         "history": []},
                                     "source": {"provider": "Survey group", "exact_url": None, "doi": None, "citation": None,
                                                "rights_decision": "derivative-only", "rights_statement": "Private-use permission",
                                                "attribution": "Survey group"}, "production": None, "structural_verdict": "structural_only"},
                                    {"schema": "geophysics.observation-dataset/v1"}),
        "DatasetPayload": ({"schema": "geophysics.observation-dataset/v1", "dataset_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                            "version": 1, "owner_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                            "project_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                            "raw_asset_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41", "parent_raw_sha256": "a" * 64,
                            "parser_version": "gravity-station-csv/v1", "modality": "gravity_station",
                            "dimensions": {"station": 4}, "axis_order": ["station"], "station_ids": ["S1", "S2", "S3", "S4"],
                            "xyz_m": [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]],
                            "observed_mgal": [1, 2, 3, 4], "sigma_mgal": [0.1, 0.1, 0.1, 0.1],
                            "uncertainty_kind": "per_station_standard_deviation", "mask": [False] * 4,
                            "missing_reasons": [None] * 4,
                            "physical_metadata": {"coordinate_reference": "epsg", "epsg": 32719, "local_crs": None,
                                "axis_order": "xy", "horizontal_datum": "WGS84", "vertical_datum": "survey", "vertical_positive": "up",
                                "horizontal_unit": "m", "vertical_unit": "m", "measurement_unit": "mGal", "epoch_utc": "2026-01-01T00:00:00Z",
                                "component_frame": "scalar", "geometry": {}}, "correction_history": [], "qc_verdict": "parsed_for_flag_qc_only",
                            "rights_decision": "derivative-only", "rights_statement": "Private-use permission", "attribution": "Survey group"},
                           {"schema": "unknown"}),
        "ProcessingResult": ({"schema": "geophysics.processing-result/v1", "job_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                               "dataset_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41", "dataset_sha256": "a" * 64,
                               "method_id": "gravity.station-outlier-flags/v1", "request_sha256": "b" * 64},
                              {"schema": "wrong", "job_id": "bad", "dataset_id": "bad"}),
        "WaveformProcessingResult": ({"schema": "geophysics.waveform-result/v1", "job_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                                       "project_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41",
                                       "dataset_id": "d2719f2d-9968-4ef0-8a66-8df16ab12f41", "dataset_sha256": "a" * 64,
                                       "method_id": "seismic.waveform-qc-classical/v1", "request_sha256": "b" * 64,
                                       "scientific_request_sha256": "c" * 64, "sources": {}, "scientific_status": "qc_only",
                                       "calculation_sha256": "d" * 64, "calculation": {"status": "qc_only", "array_descriptors": [],
                                       "channels": [{}], "request": {}, "sources": {}, "qc": {}, "acceptance": {},
                                       "field_truth": None, "candidates": None},
                                       "members": [{"name": "calculation.json", "bytes": 1, "sha256": "a" * 64},
                                                   {"name": "receipt.json", "bytes": 1, "sha256": "a" * 64},
                                                   {"name": "manifest.json", "bytes": 1, "sha256": "a" * 64}],
                                       "resources": {}},
                                      {"schema": "geophysics.processing-result/v1"}),
        "UploadMetadata": ({"filename": "survey.csv", "mime": "text/csv", "format": "gravity_csv",
                             "source": {"provider": "Survey group", "rights_statement": "Private use attested",
                                        "rights_decision": "derivative-only", "private_storage_permission": "attested",
                                        "attribution": "Survey group"},
                             "physical": {"coordinate_reference": "local", "local_crs": "local projected CRS", "axis_order": "xy",
                                          "horizontal_datum": "local grid", "vertical_datum": "local datum",
                                          "vertical_positive": "down", "horizontal_unit": "m", "vertical_unit": "m",
                                          "measurement_unit": "mGal", "epoch_utc": "2026-01-01T00:00:00Z",
                                          "component_frame": "scalar", "geometry": {"x": 0}}},
                            {"filename": "../survey.csv", "mime": "text/csv", "format": "gravity_csv",
                             "source": {"provider": "x", "rights_statement": "x", "rights_decision": "bad",
                                        "private_storage_permission": "attested", "attribution": "x"},
                             "physical": {}}),
    }
    for name, (valid, invalid) in samples.items():
        try:
            Draft202012Validator({"$ref": schema_doc["$id"] + f"#/$defs/{name}"}, registry=registry,
                                 format_checker=FormatChecker()).validate(valid)
        except Exception as error:
            issues.append(f"valid {name} sample rejected: {error}")
        else:
            try:
                Draft202012Validator({"$ref": schema_doc["$id"] + f"#/$defs/{name}"}, registry=registry,
                                     format_checker=FormatChecker()).validate(invalid)
            except Exception:
                pass
            else:
                issues.append(f"invalid {name} sample accepted")

    required_defs = {
        "ProjectCreate", "ProjectUpdate", "SourceInput", "PhysicalInput", "AssetMetadata",
        "PhysicalAssetMetadata", "UploadMetadata", "DatasetCreate", "JobCreate", "UserCreate", "User",
        "Project", "RawAsset", "DatasetReceipt", "DatasetPayload", "ObservationDatasetPayload",
        "GravityDatasetPayload", "EdiDatasetPayload", "ProfileDatasetPayload", "RawPhysicalMetadata", "EdiSource", "WaveformDatasetPayload",
        "PhysicalDatasetPayload", "PhysicalSource", "PhysicalMetadata", "PhysicalStation", "PhysicalHistory",
        "Methods", "Job", "ProcessingResult", "WaveformProcessingResult",
    }
    missing_defs = required_defs - schema_doc.get("$defs", {}).keys()
    if missing_defs:
        issues.append("missing API payload schema definitions: " + ", ".join(sorted(missing_defs)))
    return issues


def main() -> int:
    issues = check_contracts()
    if issues:
        print("API CONTRACT CHECK FAILED:")
        print("\n".join(f"  - {issue}" for issue in issues))
        return 1
    schema_doc = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    openapi = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    count = sum(1 for item in openapi["paths"].values() for method in item if method in METHODS)
    print(f"API contract OK: {count} operations, {len(schema_doc['$defs'])} schema definitions, references and payload samples valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
