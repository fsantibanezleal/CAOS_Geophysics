"""Local M01 equivalent-source gridding/continuation, not density inversion."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import re
import sys
import tempfile

import harmonica as hm
import numpy as np
from scipy.linalg import solve
from scipy.spatial import cKDTree
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
import verde as vd

from gravity_processing import (
    GravityContractError,
    PINS,
    STATES,
    STATE_LENGTHS,
    UNIT_FACTORS,
    _keys,
    _number,
    _text,
    _unique_object,
    digest,
    process_survey,
)

TRANSFORM_PINS = {**PINS, "verde": "1.9.0", "scikit-learn": "1.9.1", "matplotlib": "3.10.8"}
ROOT = Path(__file__).resolve().parents[1]
MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_JSON_DEPTH = 16
PROCESSING_FIELDS = (
    "method",
    "input_sha256",
    "output_sha256",
    "config",
    "engines",
    "python",
    "module_sha256",
    "uncertainty_model",
    "uncertainty_mgal",
    "uncertainty_components_mgal",
    "full_method_accepted",
    "warnings",
)


def _array(values, count, label):
    if not isinstance(values, list) or len(values) != count:
        raise GravityContractError(f"{label}: expected {count} values in original station order")
    return np.array([_number(value, f"{label}[{i}]") for i, value in enumerate(values)])


def _integer(value, label, low, high):
    if type(value) is not int or not low <= value <= high:
        raise GravityContractError(f"{label}: require integer in [{low},{high}]")
    return value


def _processing_identity(original, dataset, processing, replay):
    """Verify every deterministic receipt field, bounded parents and runtime declaration."""
    expected = deepcopy(replay["processing"])
    _keys(processing, tuple(expected), (), "correction_result.processing")
    recorded_python = processing["python"]
    if (
        platform.python_implementation() != "CPython"
        or sys.version_info[:2] != (3, 12)
        or not isinstance(recorded_python, str)
        or re.fullmatch(r"3\.12\.(0|[1-9][0-9]{0,2})", recorded_python) is None
    ):
        raise GravityContractError(
            "processing.python: require a declared compatible CPython 3.12.x release, not verified origin"
        )
    candidates = {}
    original_values = np.array([row["value_mgal"] for row in original["stations"]], dtype=float)
    for index, state in enumerate(STATES[: STATES.index(dataset["state"])]):
        candidate = deepcopy(original)
        prefix = deepcopy(dataset["history"][: STATE_LENGTHS[index]])
        candidate.update(state=state, history=prefix)
        values = original_values.copy()
        for record in prefix:
            values += np.asarray(record["additions_mgal"], dtype=float)
        for row, value in zip(candidate["stations"], values, strict=True):
            row["value_mgal"] = float(value)
        candidates[digest(candidate)] = state
    input_sha = processing["input_sha256"]
    if not isinstance(input_sha, str) or re.fullmatch(r"[0-9a-f]{64}", input_sha) is None:
        raise GravityContractError("processing.input_sha256: require canonical SHA-256 string")
    matched_state = candidates.get(input_sha)
    if matched_state is None:
        raise GravityContractError(
            "processing.input_sha256: no independently reconstructable canonical earlier input; exact parent needed"
        )
    expected["input_sha256"] = processing["input_sha256"]
    # Compatibility is not authentication. Preserve the declaration rather than
    # silently rewriting it to the replay machine's patch version.
    expected["python"] = recorded_python
    if digest(processing) != digest(expected):
        raise GravityContractError("correction_result.processing: deterministic receipt identity differs from replay")
    return {
        "input_state": matched_state,
        "input_sha256": processing["input_sha256"],
        "parent_policy": "Canonical converted observations or verified known-stage history prefix only",
        "deterministic_receipt_verified": True,
        "recorded_python": recorded_python,
        "runtime_python": platform.python_version(),
        "python_compatibility": "Reviewed CPython 3.12.x lane",
        "recorded_runtime_origin_verified": False,
        "recorded_runtime_implementation": "Not specified by correction receipt",
    }


def admit(request, *, return_identity=False):
    """Verify existing correction lineage without emitting/reapplying corrections."""
    _keys(request, ("schema_version", "correction_result", "geometry", "config"), (), "request")
    if request["schema_version"] != "gravity-transform-request-1":
        raise GravityContractError("schema_version: expected gravity-transform-request-1")
    result, geom, cfg = request["correction_result"], request["geometry"], request["config"]
    _keys(result, ("dataset", "processing", "qc"), (), "correction_result")
    dataset, processing = result["dataset"], result["processing"]
    _keys(processing, PROCESSING_FIELDS, (), "correction_result.processing")
    _keys(dataset, ("schema_version", "state", "metadata", "stations", "history"), (), "correction_result.dataset")
    if not isinstance(dataset["stations"], list) or not 20 <= len(dataset["stations"]) <= 400:
        raise GravityContractError("stations: local dense transform requires 20..400; no automatic thinning")
    if dataset.get("state") not in ("gravity_disturbance", "bouguer_disturbance", "terrain_adjusted_disturbance"):
        raise GravityContractError("state: require known corrected disturbance, not absolute/provider anomaly")
    # Full replay validates original units/datum/instrument status and the known
    # additions, rather than trusting a state label or an independently editable hash.
    original = deepcopy(dataset)
    original["state"], original["history"] = "observed_absolute", []
    meta = original["metadata"]
    factor = UNIT_FACTORS.get(meta.get("gravity_unit"))
    if factor is None:
        raise GravityContractError("gravity_unit: unknown original units")
    for row in original["stations"]:
        row["value_mgal"] = row["original_value"] * factor * (1 if meta["gravity_sign"] == "downward" else -1)
    replay = process_survey(original, processing["config"])
    if digest(replay["dataset"]) != digest(dataset) or digest(result["qc"]) != digest(replay["qc"]):
        raise GravityContractError("correction_result: replay/hash/geometry/error lineage drift")
    correction_identity = _processing_identity(original, dataset, processing, replay)
    n = len(dataset["stations"])
    required = (
        "station_ids",
        "easting_m",
        "northing_m",
        "upward_m",
        "coordinate_unit",
        "axis_order",
        "vertical_reference",
        "metric_crs",
        "mapping_citation",
        "component",
        "data_unit",
        "source_free_citation",
        "geometry_error_model",
        "geometry_error_citation",
        "mask",
        "mask_reasons",
    )
    _keys(geom, required, (), "geometry")
    for key, expected in (
        ("coordinate_unit", "m"),
        ("axis_order", "easting,northing,upward"),
        ("vertical_reference", "WGS84_ellipsoid"),
        ("component", "g_z_downward"),
        ("data_unit", "mGal"),
        ("geometry_error_model", "fixed_geometry_conditional"),
    ):
        if geom[key] != expected:
            raise GravityContractError(f"geometry.{key}: require {expected}; no inferred conversion")
    for key in ("metric_crs", "mapping_citation", "source_free_citation", "geometry_error_citation"):
        _text(geom[key], f"geometry.{key}")
    if geom["metric_crs"] in ("EPSG:4326", "EPSG:4267", "EPSG:4979"):
        raise GravityContractError("geometry.metric_crs: geographic degrees are not Cartesian metres")
    ids = [row["station_id"] for row in dataset["stations"]]
    if geom["station_ids"] != ids:
        raise GravityContractError("geometry.station_ids: must match original order")
    coords = tuple(_array(geom[key], n, f"geometry.{key}") for key in ("easting_m", "northing_m", "upward_m"))
    if geom["upward_m"] != replay["qc"]["receiver_ellipsoidal_m"]:
        raise GravityContractError("geometry.upward_m: require unchanged ellipsoidal receiver heights")
    if len(set(zip(*coords[:2]))) != n:
        raise GravityContractError("geometry: duplicate metric XY needs review")
    if max(np.ptp(coords[0]), np.ptp(coords[1])) > 20000:
        raise GravityContractError("geometry: local Cartesian extent exceeds 20 km")
    if not isinstance(geom["mask"], list) or len(geom["mask"]) != n or any(type(v) is not bool for v in geom["mask"]):
        raise GravityContractError("geometry.mask: require explicit station-ordered booleans")
    if not isinstance(geom["mask_reasons"], list) or len(geom["mask_reasons"]) != n:
        raise GravityContractError("geometry.mask_reasons: shape mismatch")
    for masked, reason in zip(geom["mask"], geom["mask_reasons"], strict=True):
        if masked:
            _text(reason, "mask_reason")
        elif reason is not None:
            raise GravityContractError("mask_reason: retained stations require null reason")
    active = np.flatnonzero(~np.array(geom["mask"]))
    if (
        len(active) < 20
        or np.linalg.matrix_rank(
            np.column_stack(coords[:2])[active] - np.mean(np.column_stack(coords[:2])[active], axis=0)
        )
        < 2
    ):
        raise GravityContractError("geometry: insufficient noncollinear retained stations")
    required_cfg = (
        "depths_m",
        "dampings",
        "heights_m",
        "region_m",
        "grid_spacing_m",
        "coverage_radius_m",
        "block_shape",
        "holdout_fraction",
        "seed",
        "inner_folds",
        "min_validation_coverage",
        "max_input_sigma_mgal",
        "max_transfer_sigma_mgal",
        "max_condition",
        "error_model",
    )
    _keys(cfg, required_cfg, ("covariance_mgal2", "covariance_citation"), "config")
    for key, low, high in (
        ("depths_m", 10, 10000),
        ("dampings", 1e-8, 1e8),
        ("heights_m", max(coords[2]), max(coords[2]) + 10000),
    ):
        if not isinstance(cfg[key], list) or not 1 <= len(cfg[key]) <= 8:
            raise GravityContractError(f"config.{key}: need 1..8 explicit candidates")
        for value in cfg[key]:
            _number(value, f"config.{key}", low, high)
        if len(set(cfg[key])) != len(cfg[key]):
            raise GravityContractError(f"config.{key}: duplicate candidates")
    if len(cfg["depths_m"]) * len(cfg["dampings"]) > 12:
        raise GravityContractError("config: maximum 12 depth/damping candidates")
    for key, low, high in (
        ("grid_spacing_m", 1, 20000),
        ("coverage_radius_m", 1, 20000),
        ("holdout_fraction", 0.1, 0.4),
        ("min_validation_coverage", 0.1, 1),
        ("max_input_sigma_mgal", 1e-9, 100),
        ("max_transfer_sigma_mgal", 1e-9, 100),
        ("max_condition", 1, 1e12),
    ):
        _number(cfg[key], f"config.{key}", low, high)
    _integer(cfg["seed"], "seed", 0, 2**31 - 1)
    _integer(cfg["inner_folds"], "inner_folds", 2, 5)
    if not isinstance(cfg["block_shape"], list) or len(cfg["block_shape"]) != 2:
        raise GravityContractError("block_shape: require [northing_count,easting_count]")
    for count in cfg["block_shape"]:
        _integer(count, "block_shape", 2, 20)
    region = _array(cfg["region_m"], 4, "region_m")
    if region[0] >= region[1] or region[2] >= region[3] or max(region[1] - region[0], region[3] - region[2]) > 20000:
        raise GravityContractError("region_m: ordered local bounds required")
    nodes = np.floor((region[[1, 3]] - region[[0, 2]]) / cfg["grid_spacing_m"]).astype(int) + 1
    if np.min(nodes) < 3 or np.prod(nodes) > 12000:
        raise GravityContractError("grid: require 3+ nodes per axis and at most 12000 nodes")
    sigma = _array(processing["uncertainty_mgal"], n, "uncertainty_mgal")
    if np.any(sigma <= 0):
        raise GravityContractError("uncertainty_mgal: unknown/zero noise scale")
    if cfg["error_model"] == "independent_stations":
        if "covariance_mgal2" in cfg or "covariance_citation" in cfg:
            raise GravityContractError("covariance_mgal2: conflicts with independent_stations")
        if processing["uncertainty_model"] != "independent_first_order":
            raise GravityContractError(
                "error_model: conservative marginal bounds are not standard deviations; supply cited covariance"
            )
        components = processing["uncertainty_components_mgal"]
        if any(any(v != 0 for v in components[key]) for key in ("density", "geoid")):
            raise GravityContractError("error_model: shared density/geoid error needs supplied covariance")
        covariance = np.diag(sigma**2)
    elif cfg["error_model"] == "supplied_covariance":
        _text(cfg.get("covariance_citation"), "covariance_citation")
        supplied = cfg.get("covariance_mgal2")
        if not isinstance(supplied, list) or len(supplied) != n:
            raise GravityContractError("covariance_mgal2: require numeric station-ordered matrix")
        covariance = np.stack([_array(row, n, "covariance_mgal2") for row in supplied])
        if (
            covariance.shape != (n, n)
            or not np.all(np.isfinite(covariance))
            or not np.allclose(covariance, covariance.T, rtol=1e-10, atol=1e-12)
            or np.any(np.diag(covariance) <= 0)
            or np.min(np.linalg.eigvalsh(covariance)) < -1e-12
        ):
            raise GravityContractError(
                "covariance_mgal2: require PSD symmetric covariance with positive marginal variances"
            )
        declared_sigma = np.sqrt(np.diag(covariance))
        if processing["uncertainty_model"] == "independent_first_order":
            if not np.allclose(declared_sigma, sigma, rtol=1e-8, atol=1e-12):
                raise GravityContractError("covariance_mgal2: diagonal must match propagated standard deviations")
        elif np.any(declared_sigma > sigma + 1e-12):
            raise GravityContractError(
                "covariance_mgal2: declared standard deviation exceeds recorded conservative bound"
            )
        sigma = declared_sigma
    else:
        raise GravityContractError("error_model: explicitly declare station dependence")
    if np.max(sigma[active]) > cfg["max_input_sigma_mgal"]:
        raise GravityContractError("uncertainty_mgal: high noise exceeds declared precision budget")
    admitted = (coords, np.array([r["value_mgal"] for r in dataset["stations"]]), sigma, covariance, active)
    return (*admitted, correction_identity) if return_identity else admitted


def support(train_coords, query, radius):
    """Two independent horizontal coverage gates; no extrapolated public values."""
    hull = vd.convexhull_mask(train_coords[:2], coordinates=query[:2])
    distance = vd.distance_mask(train_coords[:2], radius, coordinates=query[:2])
    nearest = cKDTree(np.column_stack(train_coords[:2])).query(np.column_stack(query[:2]))[0]
    return hull & distance, hull, distance, nearest


def fit_layer(coords, values, sigma, depth, damping, condition_limit):
    points = (coords[0].copy(), coords[1].copy(), np.full(len(values), min(coords[2]) - depth))
    engine = hm.EquivalentSources(points=points, damping=damping, parallel=False)
    engine.fit(coords, values, weights=1 / sigma**2)
    jacobian = engine.jacobian(coords, points)
    scale = StandardScaler(with_mean=False).fit(jacobian).scale_
    design = jacobian / scale
    weights = 1 / sigma**2
    system = design.T @ (weights[:, None] * design) + damping * np.eye(len(values))
    condition = float(np.linalg.cond(system))
    if not np.isfinite(condition) or condition > condition_limit:
        raise GravityContractError("condition: damped system exceeds declared stability limit")
    transfer = solve(system, design.T * weights, assume_a="pos")
    calculated = transfer @ values / scale
    if not np.allclose(calculated, engine.coefs_, rtol=2e-7, atol=1e-8):
        raise GravityContractError("operator: transfer reconstruction disagrees with pinned engine")
    singular = np.linalg.svd(design / sigma[:, None], compute_uv=False)
    raw_condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else None
    return (
        engine,
        scale,
        transfer,
        {
            "damped_condition": condition,
            "weighted_design_condition": raw_condition,
            "weighted_singular_values": singular.tolist(),
        },
    )


def _coords(coords, indices):
    return tuple(value[indices] for value in coords)


def _metrics(values, predicted, sigma, keep):
    residual = predicted[keep] - values[keep]
    return {
        "covered_count": int(sum(keep)),
        "unsupported_count": int(len(keep) - sum(keep)),
        "rmse_mgal": float(np.sqrt(np.mean(residual**2))) if len(residual) else None,
        "normalized_rmse": float(np.sqrt(np.mean((residual / sigma[keep]) ** 2))) if len(residual) else None,
        "signed_mean_mgal": float(np.mean(residual)) if len(residual) else None,
    }


def _nullable(values, keep):
    return [float(v) if accepted else None for v, accepted in zip(np.ravel(values), np.ravel(keep), strict=True)]


def transform_survey(request):
    """Fit on training only; outer observations enter only the final evaluation."""
    engines = {name: version(name) for name in TRANSFORM_PINS}
    if engines != TRANSFORM_PINS:
        raise GravityContractError(f"environment: expected {TRANSFORM_PINS}, found {engines}")
    coords, values, sigma, covariance, active, correction_identity = admit(request, return_identity=True)
    cfg = request["config"]
    matrix = np.column_stack(coords[:2])
    outer = vd.BlockShuffleSplit(
        shape=tuple(cfg["block_shape"]), n_splits=1, test_size=cfg["holdout_fraction"], random_state=cfg["seed"]
    )
    local_train, local_test = next(outer.split(matrix[active]))
    train, test = active[local_train], active[local_test]
    if len(train) < 12 or len(test) < 3:
        raise GravityContractError("split: insufficient train/holdout stations")
    train_coords = _coords(coords, train)
    spacing = float(np.median(cKDTree(matrix[train]).query(matrix[train], k=2)[0][:, 1]))
    if cfg["grid_spacing_m"] < spacing / 3:
        raise GravityContractError("grid_spacing_m: extreme oversampling is not physical resolution")
    _, block_ids = vd.block_split(tuple(coords[:2][i][active] for i in range(2)), shape=tuple(cfg["block_shape"]))
    inner = vd.BlockKFold(
        shape=tuple(cfg["block_shape"]),
        n_splits=cfg["inner_folds"],
        shuffle=True,
        random_state=cfg["seed"],
        balance=False,
    )
    folds = [(train[a], train[b]) for a, b in inner.split(matrix[train])]
    comparisons = []
    with threadpool_limits(limits=1):
        for depth in cfg["depths_m"]:
            for damping in cfg["dampings"]:
                comparison = {"depth_m": depth, "damping": damping, "status": "passed", "folds": []}
                normalized = []
                try:
                    for fold_train, validation in folds:
                        if len(fold_train) < 8:
                            raise GravityContractError("fold: fewer than eight training stations")
                        engine, _, _, condition = fit_layer(
                            _coords(coords, fold_train),
                            values[fold_train],
                            sigma[fold_train],
                            depth,
                            damping,
                            cfg["max_condition"],
                        )
                        query = _coords(coords, validation)
                        keep, _, _, _ = support(_coords(coords, fold_train), query, cfg["coverage_radius_m"])
                        keep &= query[2] > engine.points_[2][0]
                        predicted = engine.predict(query)
                        metrics = _metrics(values[validation], predicted, sigma[validation], keep)
                        if sum(keep) < 3 or np.mean(keep) < cfg["min_validation_coverage"]:
                            raise GravityContractError("fold: insufficient covered blocked validation")
                        normalized.extend(
                            ((predicted[keep] - values[validation][keep]) / sigma[validation][keep]).tolist()
                        )
                        comparison["folds"].append(
                            {
                                "train_indices": fold_train.tolist(),
                                "validation_indices": validation.tolist(),
                                "metrics": metrics,
                                "condition": condition["damped_condition"],
                            }
                        )
                    comparison["cv_normalized_rmse"] = float(np.sqrt(np.mean(np.array(normalized) ** 2)))
                except (ValueError, np.linalg.LinAlgError) as error:
                    comparison.update(status="failed", reason=str(error), cv_normalized_rmse=None)
                comparisons.append(comparison)
        good = [row for row in comparisons if row["status"] == "passed"]
        if not good:
            raise GravityContractError("selection: all blocked candidates failed coverage/condition")
        # This comparison is exclusively training data: different source planes can
        # explain observations without being competing geological interpretations.
        alternatives = []
        fitted = {}
        for candidate in good:
            key = (candidate["depth_m"], candidate["damping"])
            try:
                fitted[key] = fit_layer(train_coords, values[train], sigma[train], *key, cfg["max_condition"])
                alternative, _, _, diagnostic = fitted[key]
                alternatives.append(
                    {
                        "depth_m": key[0],
                        "damping": key[1],
                        "status": "passed",
                        "training_rmse_mgal": float(
                            np.sqrt(np.mean((alternative.predict(train_coords) - values[train]) ** 2))
                        ),
                        "coefficient_l2_mgal_m": float(np.linalg.norm(alternative.coefs_)),
                        "damped_condition": diagnostic["damped_condition"],
                    }
                )
            except (ValueError, np.linalg.LinAlgError) as error:
                candidate.update(status="failed", reason="Full training stability check: " + str(error))
                alternatives.append({"depth_m": key[0], "damping": key[1], "status": "failed", "reason": str(error)})
        good = [row for row in good if row["status"] == "passed"]
        if not good:
            raise GravityContractError("selection: all full-training candidates failed stability checks")
        chosen = min(good, key=lambda row: (row["cv_normalized_rmse"], row["depth_m"], row["damping"]))
        engine, scale, transfer, condition = fitted[(chosen["depth_m"], chosen["damping"])]
        station_keep, _, _, nearest_station = support(train_coords, coords, cfg["coverage_radius_m"])
        station_keep &= coords[2] > engine.points_[2][0]
        station_keep &= ~np.array(request["geometry"]["mask"])
        station_predictions = engine.predict(coords)
        west, east, south, north = cfg["region_m"]
        x = np.arange(west, east + cfg["grid_spacing_m"] * 1e-8, cfg["grid_spacing_m"])
        y = np.arange(south, north + cfg["grid_spacing_m"] * 1e-8, cfg["grid_spacing_m"])
        xx, yy = np.meshgrid(x, y)
        query = (xx.ravel(), yy.ravel())
        keep, hull, distance, nearest = support(train_coords, query, cfg["coverage_radius_m"])
        if not np.any(keep):
            raise GravityContractError("grid: no covered nodes")
        grids = []
        train_covariance = covariance[np.ix_(train, train)]
        for height in sorted(cfg["heights_m"]):
            query3 = (*query, np.full(xx.size, height))
            prediction = engine.predict(query3)
            deviation = np.empty(xx.size)
            for start in range(0, xx.size, 512):
                index = slice(start, start + 512)
                kernel = engine.jacobian(tuple(v[index] for v in query3), engine.points_) / scale
                linear = kernel @ transfer
                propagated = np.einsum("ij,ij->i", linear @ train_covariance, linear)
                deviation[index] = np.sqrt(np.maximum(propagated, 0))
                if not np.allclose(linear @ values[train], prediction[index], rtol=2e-7, atol=1e-8):
                    raise GravityContractError("operator: continued predictions disagree with transfer")
            image = prediction.reshape(xx.shape)
            eligible_edges = keep.reshape(xx.shape)[:, 1:] & keep.reshape(xx.shape)[:, :-1]
            roughness = (
                float(np.sqrt(np.mean(np.diff(image, axis=1)[eligible_edges] ** 2))) if np.any(eligible_edges) else None
            )
            maximum_sd = float(np.max(deviation[keep]))
            grids.append(
                {
                    "height_m": height,
                    "shape": list(xx.shape),
                    "predicted_mgal": _nullable(prediction, keep),
                    "conditional_sigma_mgal": _nullable(deviation, keep),
                    "covered": keep.tolist(),
                    "outside_hull": (~hull).tolist(),
                    "outside_radius": (~distance).tolist(),
                    "nearest_training_m": nearest.tolist(),
                    "max_conditional_sigma_mgal": maximum_sd,
                    "adjacent_easting_difference_rms_mgal": roughness,
                    "height_precision_passed": maximum_sd <= cfg["max_transfer_sigma_mgal"],
                }
            )
    selected_height = next((grid["height_m"] for grid in grids if grid["height_precision_passed"]), None)
    ids = request["geometry"]["station_ids"]
    partition = ["masked"] * len(values)
    for index in train:
        partition[index] = "train"
    for index in test:
        partition[index] = "holdout"
    model = {
        "points_m": [p.tolist() for p in engine.points_],
        "coefficients_mgal_m": engine.coefs_.tolist(),
        "depth_m": chosen["depth_m"],
        "damping": chosen["damping"],
        "training_indices": train.tolist(),
        "interpretation": "Nonunique harmonic coefficients, not density, mass, geology or physical source depth",
    }
    return {
        "schema_version": "gravity-transform-result-1",
        "original_correction_result": deepcopy(request["correction_result"]),
        "geometry": deepcopy(request["geometry"]),
        "config": deepcopy(cfg),
        "model": model,
        "selection": {
            "depth_m": chosen["depth_m"],
            "damping": chosen["damping"],
            "height_m": selected_height,
            "status": "passed" if selected_height is not None else "unmet_height_precision",
            "candidates": comparisons,
            "criterion": "Inner train-block normalized RMSE; height by train-only noise-transfer ceiling",
        },
        "split": {
            "train_indices": train.tolist(),
            "holdout_indices": test.tolist(),
            "partition": partition,
            "block_ids_active": np.asarray(block_ids).tolist(),
            "active_indices": active.tolist(),
            "sha256": digest(
                {
                    "train": train.tolist(),
                    "holdout": test.tolist(),
                    "folds": [(a.tolist(), b.tolist()) for a, b in folds],
                }
            ),
        },
        "stations": {
            "station_ids": ids,
            "observed_mgal": values.tolist(),
            "fit_sigma_mgal": sigma.tolist(),
            "predicted_mgal": _nullable(station_predictions, station_keep),
            "signed_predicted_minus_observed_mgal": _nullable(station_predictions - values, station_keep),
            "normalized_residual": _nullable((station_predictions - values) / sigma, station_keep),
            "prediction_covered": station_keep.tolist(),
            "nearest_training_m": nearest_station.tolist(),
        },
        "evaluation": {
            "train": _metrics(values[train], station_predictions[train], sigma[train], station_keep[train]),
            "holdout": _metrics(values[test], station_predictions[test], sigma[test], station_keep[test]),
        },
        "axes": {
            "easting_m": x.tolist(),
            "northing_m": y.tolist(),
            "grid_axis_order": "northing,easting",
            "unit": "mGal",
        },
        "grids": grids,
        "condition": condition,
        "nonuniqueness": {
            "training_only_alternatives": alternatives,
            "interpretation": "Comparable fits at different mathematical depths do not identify density or source geometry",
        },
        "uncertainty": {
            "kind": "conditional_linear_noise_propagation",
            "error_model": cfg["error_model"],
            "marginal_source": "Explicit cited covariance"
            if cfg["error_model"] == "supplied_covariance"
            else "Independent first-order correction propagation",
            "fit_weights": "Diagonal marginal inverse variances; not full-covariance GLS",
            "excludes": ["Geometry error", "Parameter-selection uncertainty", "Bias", "Geological uncertainty"],
        },
        "resolution": {
            "median_training_nearest_neighbor_m": spacing,
            "grid_sampling_m": cfg["grid_spacing_m"],
            "coverage_radius_m": cfg["coverage_radius_m"],
            "coverage_is_resolution": False,
        },
        "provenance": {
            "request_sha256": digest(request),
            "source_sha256": request["correction_result"]["dataset"]["metadata"]["source_sha256"],
            "engines": engines,
            "python": platform.python_version(),
            "module_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "corrections_reapplied": False,
            "correction_identity": correction_identity,
            "field_gate": "open",
            "full_method_accepted": False,
        },
    }


def replay_grid(result, grid_index):
    """Re-import a numeric checkpoint without pickle or code execution."""
    engine = hm.EquivalentSources(parallel=False)
    engine.points_ = tuple(np.array(v) for v in result["model"]["points_m"])
    engine.coefs_ = np.array(result["model"]["coefficients_mgal_m"])
    xx, yy = np.meshgrid(result["axes"]["easting_m"], result["axes"]["northing_m"])
    grid = result["grids"][grid_index]
    predicted = engine.predict((xx.ravel(), yy.ravel(), np.full(xx.size, grid["height_m"])))
    return _nullable(predicted, grid["covered"])


def export_bundle(request, result, output):
    """Stage a complete immutable local bundle; never canonical or overwriting."""
    output = Path(output).absolute()
    if result["provenance"]["request_sha256"] != digest(request):
        raise GravityContractError("export: result does not belong to this request")
    if output.exists() or output.is_symlink():
        raise GravityContractError("output: already exists; overwrite forbidden")
    for parent in output.parents:
        if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
            raise GravityContractError("output: symlink/junction parent rejected")
    output = output.resolve()
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / "data/raw/gravity-m01-transforms"):
        raise GravityContractError("output: inside repo use ignored data/raw/gravity-m01-transforms only")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".m01-transform-", dir=output.parent) as temporary:
        staging = Path(temporary)
        for filename, value in (("request.json", request), ("result.json", result)):
            (staging / filename).write_text(
                json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n"
            )
        from gravity_transform_figures import render_diagnostics

        render_diagnostics(result, staging)
        files = [
            {"name": p.name, "bytes": p.stat().st_size, "sha256": sha256(p.read_bytes()).hexdigest()}
            for p in sorted(staging.iterdir())
        ]
        receipt = {
            "schema_version": "gravity-transform-export-1",
            "executed_utc": datetime.now(timezone.utc).isoformat(),
            "request_sha256": digest(request),
            "result_sha256": digest(result),
            "files": files,
            "full_method_accepted": False,
        }
        (staging / "receipt.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        # mkdir is exclusive on both Windows and POSIX, unlike POSIX rename of
        # an empty directory. All files are complete before publishing them.
        output.mkdir(exist_ok=False)
        # receipt.json is the completion marker; a interrupted publication is
        # not a completed bundle and is preserved for inspection, never reused.
        for source in sorted(staging.iterdir(), key=lambda p: (p.name == "receipt.json", p.name)):
            source.rename(output / source.name)
    return receipt


def _finite_json_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise GravityContractError("input: nonfinite/overflow JSON number")
    return number


def _reject_json_constant(value):
    raise GravityContractError(f"input: nonfinite JSON constant {value}")


def read_request(path):
    """Bound actual bytes, structural nesting and strict JSON before any engine call."""
    path = Path(path)
    if not path.is_file():
        raise GravityContractError("input: require regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise GravityContractError("input: actual bytes read exceed 32 MiB cap")
    content = raw.decode("utf-8", errors="strict")
    depth, quoted, escaped = 0, False, False
    for character in content:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise GravityContractError("input: JSON nesting exceeds depth 16")
        elif character in "]}":
            depth -= 1
    return json.loads(
        content, object_pairs_hook=_unique_object, parse_constant=_reject_json_constant, parse_float=_finite_json_float
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        request = read_request(args.input)
        result = transform_survey(request)
        receipt = export_bundle(request, result, args.output_dir)
        print(
            json.dumps(
                {
                    "selection": result["selection"]["status"],
                    "holdout": result["evaluation"]["holdout"],
                    "result_sha256": receipt["result_sha256"],
                    "field_gate": "open",
                },
                sort_keys=True,
            )
        )
        return 0 if result["selection"]["status"] == "passed" else 3
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f"M01 transform rejected: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
