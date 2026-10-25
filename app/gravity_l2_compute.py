"""Bounded adapter from authenticated gravity datasets to the frozen native M02 L2 API."""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sys
import csv
import io
from pathlib import Path
from typing import Any

import numpy as np

from app.gravity_l2_contract import METHOD_ID, GravityL2Parameters, implementation_hashes
from app.processing_contract import canonical_bytes, sha256

PIPELINE = Path(__file__).resolve().parents[1] / "data-pipeline"


def _native_modules():
    if str(PIPELINE) not in sys.path:
        sys.path.insert(0, str(PIPELINE))
    import gravity_forward as forward
    import gravity_l2 as inverse
    import gravity_survey_l2 as survey
    return forward, inverse, survey


def _array(value, dtype=np.float64):
    return np.asarray(value, dtype=dtype).copy(order="C")


def _declaration(dataset: dict) -> dict:
    declaration = dataset["physical_metadata"]["geometry"]["ordinary_l2"]
    if type(declaration) is not dict:
        raise ValueError("ordinary L2 source declaration is missing")
    return declaration


def _source(dataset: dict, request: dict) -> dict:
    physical = dataset["physical_metadata"]
    declaration = _declaration(dataset)
    source_record = dataset["source"]
    processing_receipt = {
        "parser_version": dataset["parser_version"],
        "processing_kind": declaration["processing_kind"],
        "quantity": declaration["quantity"],
        "correction_state": declaration["correction_state"],
        "reference_description": (f"{declaration['reference_description']}; fixed background: "
                                  f"{declaration['background_reference']}"),
        "original_acceleration_unit": declaration["original_acceleration_unit"],
        "original_vertical_positive": declaration["original_vertical_positive"],
    }
    normalization_receipt = {
        "operation": "identity_no_conversion",
        "coordinates": "source_supplied_local_east_north_up_metres",
        "acceleration": "source_supplied_upward_mGal",
        "parser_version": dataset["parser_version"],
    }
    horizontal = physical["local_crs"]
    if type(horizontal) is not str or not horizontal.strip():
        raise ValueError("local metric coordinate reference is required")
    return {
        "source_id": request["source_id"], "source_kind": "user_upload",
        "raw_sha256": request["raw_sha256"], "raw_bytes": request["raw_bytes"],
        "citation": source_record["citation"], "rights": "private_only",
        "processing_sha256": sha256(canonical_bytes(processing_receipt)),
        "processing_kind": declaration["processing_kind"],
        "quantity": declaration["quantity"],
        "reference_description": declaration["reference_description"],
        "original_acceleration_unit": declaration["original_acceleration_unit"],
        "original_vertical_positive": declaration["original_vertical_positive"],
        "normalization_sha256": sha256(canonical_bytes(normalization_receipt)),
        "horizontal_reference": f"{horizontal}; {physical['horizontal_datum']}",
        "vertical_reference": physical["vertical_datum"],
        "transform_sha256": None,
        "geometry_uncertainty": "conditional_fixed_geometry",
    }


def _noise(dataset: dict, rows: np.ndarray, survey) -> dict:
    declaration = _declaration(dataset)
    noise = {
        "kind": "diagonal_sd", "values": _array(dataset["sigma_mgal"], np.float64)[rows],
        "unit": "mGal", "basis": declaration["sigma_basis"],
        "citation": declaration["sigma_citation"],
        "cross_partition_dependence": declaration["cross_partition_dependence"],
    }
    noise["values_sha256"] = survey._digest({
        key: noise[key] for key in ("kind", "unit", "values")
    } | {"rows": rows})
    return noise


def build_native_requests(dataset: dict, request: dict, parameters: dict):
    forward, inverse, survey = _native_modules()
    parsed = GravityL2Parameters.model_validate(parameters)
    if dataset.get("modality") != "gravity_station":
        raise ValueError("M02 ordinary L2 requires gravity_station data")
    n = dataset["dimensions"].get("station")
    if type(n) is not int or not 12 <= n <= 2048:
        raise ValueError("M02 ordinary L2 needs 12..2048 source stations")
    if (len(dataset.get("station_ids", [])) != n or len(dataset.get("partition_group_ids", [])) != n
            or len(dataset.get("xyz_m", [])) != n or len(dataset.get("observed_mgal", [])) != n
            or len(dataset.get("sigma_mgal", [])) != n):
        raise ValueError("source-bound station arrays are incomplete or misaligned")
    if dataset.get("uncertainty_kind") != "per_station_standard_deviation":
        raise ValueError("ordinary L2 requires source-bound per-station standard deviations")
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in dataset["sigma_mgal"]):
        raise ValueError("uncertainties must be finite")
    if any(value <= 0 for value in dataset["sigma_mgal"]):
        raise ValueError("uncertainties must be strictly positive")

    declaration = _declaration(dataset)
    if declaration.get("partition_group_column") not in dataset.get("raw_columns", []):
        raise ValueError("the declared acquisition group column is not bound to the original table")
    source_record = dataset.get("source", {})
    if (dataset.get("parent_raw_sha256") != request.get("raw_sha256")
            or dataset.get("raw_asset_id") != request.get("raw_asset_id")
            or not source_record.get("citation") or not source_record.get("rights_statement")
            or not source_record.get("attribution")):
        raise ValueError("source identity, rights or attribution is incomplete")

    n_active = sum(parsed.mesh.active)
    mesh = {
        "origin_m": _array(parsed.mesh.origin_m),
        "hx_m": _array(parsed.mesh.hx_m), "hy_m": _array(parsed.mesh.hy_m),
        "hz_m": _array(parsed.mesh.hz_m), "active": _array(parsed.mesh.active, np.bool_),
    }
    stations = {
        "station_ids": tuple(dataset["station_ids"]),
        "partition_group_ids": tuple(dataset["partition_group_ids"]),
        "receivers_m": _array(dataset["xyz_m"]),
        "excluded": _array([False] * n, np.bool_),
        "exclusion_reasons": tuple([""] * n),
    }
    split = {
        "policy": "blocked-hash-3fold-sealed-1",
        "block_origin_m": _array(parsed.split.block_origin_m),
        "block_size_m": _array(parsed.split.block_size_m),
        "buffer_m": float(parsed.split.buffer_m), "seed": 104729,
    }
    planning = {
        "schema": "gravity-survey-l2-plan-request-1",
        "source": _source(dataset, request), "frame": dict(forward.FRAME),
        "mesh": mesh, "stations": stations,
        "background_mgal": np.full(n, float(parsed.background_mgal), dtype=np.float64),
        "split": split, "engine": forward.ENGINE,
    }
    plan = survey.plan_gravity_l2(planning)
    dev = plan["development_rows"]
    observed = {
        "rows": dev.copy(), "gz_up_mgal": _array(dataset["observed_mgal"])[dev],
        "acceleration_unit": "mGal", "vertical_positive": "up",
    }
    observed["values_sha256"] = survey._digest(observed)
    noise = _noise(dataset, dev, survey)
    prior = {
        "lower_kg_m3": _array(parsed.prior.lower_kg_m3),
        "upper_kg_m3": _array(parsed.prior.upper_kg_m3),
        "start_kg_m3": _array(parsed.prior.start_kg_m3),
        "reference_kg_m3": _array(parsed.prior.reference_kg_m3),
        "density_scale_kg_m3": float(parsed.prior.density_scale_kg_m3),
        "lengths_m": _array(parsed.prior.lengths_m),
        "basis": parsed.prior.basis, "reference_in_smooth": True,
        "spatial_weights": "none", "geometry_sha256": survey._digest(plan["geometry"]),
    }
    calibration_request = {
        "schema": "gravity-survey-l2-calibration-request-1", "plan": plan,
        "observations": observed, "noise": noise, "prior": prior,
        "policy": {"name": "ordinary-l2-beta-grid-1",
                   "beta_candidates": inverse.BETA_CANDIDATES,
                   "optimizer": inverse.OPTIMIZER_POLICY,
                   "training": "not_applicable_classical"},
        "runtime_epoch": inverse.RUNTIME_EPOCH,
    }
    return parsed, plan, calibration_request, n_active


def verify_original_rows(raw_path: Path, dataset: dict) -> None:
    """Reparse source bytes and require exact equality with every admitted row."""
    physical = dataset["physical_metadata"]
    geometry = physical["geometry"]
    declaration = _declaration(dataset)
    names = [geometry[key] for key in ("station_id_column", "x_column", "y_column", "z_column",
                                        "value_column", "sigma_column")]
    group_column = declaration["partition_group_column"]
    columns = [*names, group_column] if group_column not in names else names
    raw = raw_path.read_bytes()
    try:
        text = raw.decode("utf-8-sig", errors="strict")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if reader.fieldnames != columns:
            raise ValueError("original gravity CSV header differs from its declared column map")
        station_ids, xyz, observed, sigma, groups = [], [], [], [], []
        for index, row in enumerate(reader, start=1):
            if index > 2048 or None in row or any(v is None for v in row.values()):
                raise ValueError("original gravity CSV exceeds row cap or has a malformed row")
            station_ids.append(row[names[0]].strip())
            xyz.append([float(row[key]) for key in names[1:4]])
            observed.append(float(row[names[4]]))
            sigma.append(float(row[names[5]]))
            groups.append(row[group_column].strip())
    except (UnicodeError, csv.Error, TypeError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("original gravity CSV"):
            raise
        raise ValueError("original gravity CSV cannot be reparsed under its admitted column map") from exc
    if (station_ids != dataset.get("station_ids") or xyz != dataset.get("xyz_m")
            or observed != dataset.get("observed_mgal") or sigma != dataset.get("sigma_mgal")
            or groups != dataset.get("partition_group_ids") or columns != dataset.get("raw_columns")):
        raise ValueError("normalized gravity observations differ from the immutable original bytes")


def _typed(value: Any):
    if isinstance(value, np.ndarray):
        array = np.asarray(value)
        if array.dtype.kind not in "fib" or array.dtype.byteorder == ">":
            raise ValueError("native result contains an unsupported array dtype")
        array = np.ascontiguousarray(array)
        return {"kind": "ndarray", "dtype": array.dtype.newbyteorder("<").str,
                "shape": list(array.shape), "order": "C", "sha256": hashlib.sha256(array.tobytes()).hexdigest(),
                "data": array.tolist()}
    if isinstance(value, np.generic):
        return value.item()
    if type(value) is dict:
        return {str(key): _typed(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_typed(item) for item in value]
    if value is None or type(value) in (str, int, float, bool):
        if type(value) is float and not math.isfinite(value):
            raise ValueError("native result contains non-finite scalar")
        return value
    raise ValueError("native result contains an unsupported value")


def compute_gravity_l2(dataset: dict, raw_path: Path, *, job_id: str, dataset_sha: str,
                       request_sha: str, raw_sha: str, raw_bytes: int, raw_asset_id: str,
                       source_id: str, parameters: dict, memory_limit: int, scratch_limit: int,
                       expected_implementation_hashes: dict) -> dict:
    if os.name == "posix":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
        resource.setrlimit(resource.RLIMIT_FSIZE, (scratch_limit, scratch_limit))
    if raw_path.is_symlink() or not raw_path.is_file() or raw_path.stat().st_size != raw_bytes:
        raise ValueError("verified gravity source file size changed")
    raw_digest = hashlib.sha256()
    with raw_path.open("rb") as stream:
        remaining = raw_bytes
        while remaining:
            chunk = stream.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError("gravity source file ended before the admitted byte count")
            raw_digest.update(chunk)
            remaining -= len(chunk)
        if stream.read(1):
            raise ValueError("gravity source has bytes beyond its admitted length")
    if raw_digest.hexdigest() != raw_sha or dataset.get("parent_raw_sha256") != raw_sha:
        raise ValueError("gravity source SHA-256 differs from the admitted asset")
    if implementation_hashes() != expected_implementation_hashes:
        raise ValueError("gravity L2 implementation differs from the immutable job receipt")
    if dataset.get("source", {}).get("source_id") != source_id:
        raise ValueError("gravity source record differs from the job receipt")
    verify_original_rows(raw_path, dataset)

    request = {"raw_sha256": raw_sha, "raw_bytes": raw_bytes,
               "raw_asset_id": raw_asset_id, "source_id": source_id}
    parsed, plan, calibration_request, _active = build_native_requests(dataset, request, parameters)
    _forward, inverse, _survey = _native_modules()
    # The native allocation policy is a refusal threshold, never an estimator of host RSS.
    projected = inverse.metric.allocation(
        len(plan["request"]["stations"]["receivers_m"]),
        len(plan["development_rows"]), len(plan["geometry"]["active_cell_indices"]), False,
    )["maximum"]
    if projected > memory_limit or raw_bytes + 16 * 1024 * 1024 > scratch_limit:
        raise ValueError("gravity L2 projected native memory or scratch exceeds the admitted cap")
    calibration = inverse.calibrate_gravity_l2(calibration_request)
    if calibration["selection_status"] != "selected" or calibration["final_solve"] is None or calibration["final_solve"]["status"] != "converged":
        raise ValueError("gravity L2 calibration did not converge; its exact terminal result is not published as success")
    outer = plan["outer_rows"]
    observed = {"rows": outer.copy(), "gz_up_mgal": _array(dataset["observed_mgal"])[outer],
                "acceleration_unit": "mGal", "vertical_positive": "up"}
    observed["values_sha256"] = _survey_digest(observed)
    outer_noise = _noise(dataset, outer, _native_modules()[2])
    evaluation = inverse.evaluate_gravity_l2({
        "schema": "gravity-survey-l2-evaluation-request-1",
        "frozen_calibration": calibration, "observations": observed, "noise": outer_noise,
    })
    from app.gravity_l2_contract import PARAMETER_SCHEMA
    body = {
        "schema": "geophysics.processing-result/v1", "job_id": job_id,
        "dataset_id": dataset["dataset_id"], "dataset_sha256": dataset_sha,
        "method_id": METHOD_ID, "request_sha256": request_sha,
        "parameters": parameters, "raw_asset_id": raw_asset_id,
        "raw_sha256": raw_sha, "raw_bytes": raw_bytes, "source_id": source_id,
        "implementation_sha256": expected_implementation_hashes,
        "engine_sha256": sha256(Path(__file__).read_bytes()),
        "parameter_schema": PARAMETER_SCHEMA,
        "gravity_l2": {
            "schema": "geophysics.gravity-survey-l2-result/v1",
            "plan_native_sha256": plan["plan_sha256"],
            "calibration_native_sha256": calibration["result_sha256"],
            "evaluation_native_sha256": evaluation["result_sha256"],
            "plan": _typed(plan), "calibration": _typed(calibration),
            "outer_evaluation": _typed(evaluation),
            "source": _typed(plan["request"]["source"]),
            "units": {"model": "kg/m3", "observed": "mGal", "coordinates": "m"},
            "field_truth": None,
            "scope": {"field_eligible": False, "full_M02_accepted": False,
                      "GPU_accepted": False, "host_accepted": False},
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "native_epoch": inverse.RUNTIME_EPOCH,
            "engine": plan["request"]["engine"],
        },
    }
    body["environment_sha256"] = sha256(canonical_bytes(body["environment"]))
    body["gravity_l2_sha256"] = sha256(canonical_bytes(body["gravity_l2"]))
    return body


def _survey_digest(value):
    return _native_modules()[2]._digest(value)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "raw", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ("job-id", "dataset-sha256", "request-sha256", "raw-sha256", "raw-asset-id", "source-id", "parameters", "implementation-sha256"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--method-id", required=True)
    parser.add_argument("--raw-bytes", type=int, required=True)
    parser.add_argument("--memory-limit", type=int, required=True)
    parser.add_argument("--scratch-limit", type=int, required=True)
    args = parser.parse_args()
    try:
        dataset_bytes = args.input.read_bytes()
        if len(dataset_bytes) > 8 * 1024 * 1024 or sha256(dataset_bytes) != args.dataset_sha256:
            raise ValueError("admitted gravity dataset bytes differ from the job receipt")
        dataset = json.loads(dataset_bytes)
        if canonical_bytes(dataset) != dataset_bytes:
            raise ValueError("gravity dataset JSON is not canonical")
        parameters = json.loads(args.parameters)
        if args.method_id != METHOD_ID:
            raise ValueError("unsupported gravity processing method")
        result = compute_gravity_l2(
            dataset, args.raw, job_id=args.job_id, dataset_sha=args.dataset_sha256,
            request_sha=args.request_sha256, raw_sha=args.raw_sha256,
            raw_bytes=args.raw_bytes, raw_asset_id=args.raw_asset_id,
            source_id=args.source_id, parameters=parameters,
            memory_limit=args.memory_limit, scratch_limit=args.scratch_limit,
            expected_implementation_hashes=json.loads(args.implementation_sha256),
        )
        encoded = canonical_bytes(result)
        if len(encoded) > args.scratch_limit:
            raise ValueError("gravity L2 result exceeds scratch cap")
        with args.output.open("xb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
