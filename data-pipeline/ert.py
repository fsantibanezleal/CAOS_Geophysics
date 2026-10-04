"""Local, rights-contained Slagdump ERT QC and conditional 2.5D inverse.

The source remains provider-linked; this script writes only ignored local receipts.
Run with an isolated environment from data-pipeline/requirements-ert.txt.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time

import numpy as np
from profile_mesh import parameter_mesh

from sources import ROOT, SourceError, acquire_source

SOURCE_ID = "pygimli-slagdump"
COUNT_SENSOR = re.compile(r"^(\d+)# Number of sensors$")
COUNT_DATA = re.compile(r"^(\d+)# Number of data$")
MAX_INPUT_BYTES = 1_000_000
INVERSE_OPTIONS = {"lam": 10.0, "paraDX": 0.3, "paraMaxCellSize": 10.0,
                   "paraDepth": 20.0, "quality": 33.6, "maxIter": 12}
ALTERNATE_MESH_OPTIONS = {**INVERSE_OPTIONS, "paraDX": 0.45, "paraMaxCellSize": 15.0}


class ERTError(ValueError):
    """Physical source contract or numerical evidence failed."""


@dataclass(frozen=True)
class Survey:
    sensors_xz_m: np.ndarray
    abmn: np.ndarray  # zero-based, A B M N
    resistance_ohm: np.ndarray
    comments: tuple[str, ...]


def _finite_float(value: str, where: str) -> float:
    try:
        number = float(value)
    except ValueError as error:
        raise ERTError(f"{where}: expected a finite decimal, got {value!r}") from error
    if not math.isfinite(number):
        raise ERTError(f"{where}: non-finite number {value!r}")
    return number


def _count(line: str, pattern: re.Pattern, where: str, ceiling: int) -> int:
    match = pattern.fullmatch(line)
    if match is None:
        raise ERTError(f"{where}: expected '{pattern.pattern}' marker")
    count = int(match.group(1))
    if not 4 <= count <= ceiling:
        raise ERTError(f"{where}: count {count} outside [4,{ceiling}]")
    return count


def parse_ohm(path: Path) -> Survey:
    """Strict source-specific parser; no inferred columns, units or missing rows."""
    path = Path(path)
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ERTError(f"{path}: .ohm exceeds {MAX_INPUT_BYTES} bytes")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ERTError(f"{path}: cannot read UTF-8 .ohm: {error}") from error
    index = 0
    comments = []
    while index < len(lines) and lines[index].startswith("#"):
        comments.append(lines[index])
        index += 1
    if not comments or not any("Wenner" in line for line in comments):
        raise ERTError("source header: expected provenance and Wenner survey description")
    if index >= len(lines):
        raise ERTError("sensor count: missing")
    sensor_count = _count(lines[index], COUNT_SENSOR, "sensor count", 512)
    index += 1
    if index >= len(lines) or lines[index].split() != ["#x", "z"]:
        raise ERTError("sensor columns: expected '#x z' with x/z in provider-declared metres")
    index += 1
    sensors = []
    for row in range(sensor_count):
        if index >= len(lines):
            raise ERTError(f"sensor row {row + 1}: truncated")
        fields = lines[index].split()
        if len(fields) != 2:
            raise ERTError(f"sensor row {row + 1}: expected exactly x z")
        sensors.append([_finite_float(fields[0], f"sensor row {row + 1} x"),
                        _finite_float(fields[1], f"sensor row {row + 1} z")])
        index += 1
    xy = np.asarray(sensors, dtype=float)
    if np.any(np.diff(xy[:, 0]) <= 0):
        raise ERTError("sensor x: require strictly increasing, unique surface electrodes")
    if index >= len(lines):
        raise ERTError("data count: missing")
    data_count = _count(lines[index], COUNT_DATA, "data count", 20_000)
    index += 1
    if index >= len(lines) or lines[index].split() != ["#a", "b", "m", "n", "R"]:
        raise ERTError("measurement columns: expected '#a b m n R' in provider-declared Ohm")
    index += 1
    electrodes = []
    resistances = []
    seen = set()
    for row in range(data_count):
        if index >= len(lines):
            raise ERTError(f"measurement row {row + 1}: truncated")
        fields = lines[index].split()
        if len(fields) != 5:
            raise ERTError(f"measurement row {row + 1}: expected exactly a b m n R")
        try:
            a, b, m, n = (int(field) for field in fields[:4])
        except ValueError as error:
            raise ERTError(f"measurement row {row + 1}: ABMN must be integer sensor IDs") from error
        if min(a, b, m, n) < 1 or max(a, b, m, n) > sensor_count:
            raise ERTError(f"measurement row {row + 1}: ABMN outside 1..{sensor_count}")
        normal_wenner = a < m < n < b and m - a == n - m == b - n
        reciprocal_wenner = m < a < b < n and a - m == b - a == n - b
        if len({a, b, m, n}) != 4 or not (normal_wenner or reciprocal_wenner):
            raise ERTError(f"measurement row {row + 1}: invalid distinct, equally spaced Wenner/reciprocal ABMN")
        if (a, b, m, n) in seen:
            raise ERTError(f"measurement row {row + 1}: duplicate ABMN quadrupole")
        seen.add((a, b, m, n))
        resistance = _finite_float(fields[4], f"measurement row {row + 1} R")
        if resistance == 0:
            raise ERTError(f"measurement row {row + 1} R: zero resistance is not model-ready")
        electrodes.append([a - 1, b - 1, m - 1, n - 1])
        resistances.append(resistance)
        index += 1
    if any(line.strip() for line in lines[index:]):
        raise ERTError(f"trailing payload: unexpected content after {data_count} measurements")
    return Survey(xy, np.asarray(electrodes, dtype=int), np.asarray(resistances, dtype=float),
                  tuple(comments))


def qc(survey: Survey) -> dict:
    """Preserve all measurements; flags have no filtering or weight effect."""
    abmn = survey.abmn
    resistances = survey.resistance_ohm
    keys = {tuple(row): i for i, row in enumerate(abmn)}
    reciprocal_pairs = [(i, keys[(m, n, a, b)]) for i, (a, b, m, n) in enumerate(abmn)
                        if (m, n, a, b) in keys and i < keys[(m, n, a, b)]]
    spans = abmn[:, 1] - abmn[:, 0]
    ab_distance = survey.sensors_xz_m[abmn[:, 1], 0] - survey.sensors_xz_m[abmn[:, 0], 0]
    flags = []
    for span in np.unique(spans):
        indices = np.flatnonzero(spans == span)
        log_r = np.log(np.abs(resistances[indices]))
        median = np.median(log_r)
        mad = np.median(np.abs(log_r - median))
        if mad > 0:
            flags.extend(indices[np.abs(log_r - median) > 6 * 1.4826 * mad].tolist())
    return {
        "sensor_count": len(survey.sensors_xz_m),
        "measurement_count": len(abmn),
        "x_range_m": [float(survey.sensors_xz_m[0, 0]), float(survey.sensors_xz_m[-1, 0])],
        "z_range_m": [float(np.min(survey.sensors_xz_m[:, 1])),
                      float(np.max(survey.sensors_xz_m[:, 1]))],
        "topographic_relief_m": float(np.ptp(survey.sensors_xz_m[:, 1])),
        "ab_index_span_counts": {str(int(span)): int(np.sum(spans == span)) for span in np.unique(spans)},
        "ab_distance_m_range": [float(np.min(ab_distance)), float(np.max(ab_distance))],
        "duplicate_quadrupoles": 0,
        "resistance_range_ohm": [float(np.min(resistances)), float(np.max(resistances))],
        "negative_resistance_rows": np.flatnonzero(resistances < 0).tolist(),
        "reciprocal_pairs": [list(pair) for pair in reciprocal_pairs],
        "reciprocal_status": "available" if reciprocal_pairs else "not_available",
        "instrument_error_status": "not_supplied",
        "flagged_rows": sorted(flags),
        "flag_rule": "within-AB-span absolute log(R) > 6 scaled MAD; flag only",
        "units": {"x": "m", "z": "m, positive upward, local datum unknown", "R": "Ohm"},
        "unit_basis": "source Wenner 2 m header and official pyGIMLi example x/z metres and resistance",
    }


def flat_halfspace_factors(survey: Survey) -> np.ndarray:
    """Independent signed 3D halfspace electrode formula in Ohm m/Ohm."""
    x = survey.sensors_xz_m[:, 0]
    a, b, m, n = survey.abmn.T
    denominator = 1 / np.abs(x[a] - x[m]) - 1 / np.abs(x[a] - x[n]) - 1 / np.abs(x[b] - x[m]) + 1 / np.abs(x[b] - x[n])
    if not np.all(np.isfinite(denominator)) or np.any(denominator <= 0):
        raise ERTError("flat geometric factor: invalid signed ABMN denominator")
    return 2 * np.pi / denominator


def holdout_indices(survey: Survey) -> tuple[np.ndarray, np.ndarray]:
    """Predeclared within-spacing fifth-row holdout, independent of R."""
    spans = survey.abmn[:, 1] - survey.abmn[:, 0]
    x = survey.sensors_xz_m[:, 0]
    midpoints = (x[survey.abmn[:, 0]] + x[survey.abmn[:, 1]]) / 2
    held = []
    for span in np.unique(spans):
        indices = np.flatnonzero(spans == span)
        ordered = sorted(indices, key=lambda i: (midpoints[i], i))
        held.extend(ordered[4::5])
    holdout = np.asarray(sorted(held), dtype=int)
    training = np.asarray(sorted(set(range(len(spans))) - set(held)), dtype=int)
    if len(training) < 4 or len(holdout) < 4:
        raise ERTError("holdout: fewer than four train or held-out quadrupoles")
    return training, holdout


def blocked_holdout_indices(survey: Survey) -> tuple[np.ndarray, np.ndarray]:
    """A fixed central survey segment is withheld across every AB span."""
    x = survey.sensors_xz_m[:, 0]
    midpoint = (x[survey.abmn[:, 0]] + x[survey.abmn[:, 1]]) / 2
    start = x[0] + 0.4 * (x[-1] - x[0])
    end = x[0] + 0.6 * (x[-1] - x[0])
    held = np.flatnonzero((midpoint >= start) & (midpoint <= end))
    training = np.flatnonzero((midpoint < start) | (midpoint > end))
    if len(held) < 10 or len(training) < 20:
        raise ERTError("blocked holdout: central 40-60% segment has insufficient train/test rows")
    return training, held


def _pygimli_data(path: Path, survey: Survey):
    try:
        import pygimli as pg
        from pygimli.physics import ert
    except ImportError as error:
        raise ERTError("M07 needs isolated data-pipeline/requirements-ert.txt environment") from error
    pg.utils.noCache(True)  # Never write the user's global pyGIMLi cache.
    data = ert.load(str(path))
    if data.sensorCount() != len(survey.sensors_xz_m) or data.size() != len(survey.abmn):
        raise ERTError("pyGIMLi parser disagrees with strict sensor/measurement counts")
    positions = np.asarray([[p.x(), p.z()] for p in data.sensors()])
    if not np.allclose(positions, survey.sensors_xz_m, rtol=0, atol=1e-8):
        raise ERTError("pyGIMLi parser disagrees with strict electrode positions")
    for column, index in zip("abmn", range(4)):
        if not np.array_equal(np.asarray(data[column], dtype=int), survey.abmn[:, index]):
            raise ERTError(f"pyGIMLi parser disagrees with strict {column} indices")
    if not np.allclose(np.asarray(data["r"]), survey.resistance_ohm, rtol=1e-9, atol=0):
        raise ERTError("pyGIMLi parser disagrees with strict resistance values")
    return pg, ert, data


def factors(path: Path, survey: Survey) -> tuple[object, object, object, np.ndarray, np.ndarray]:
    pg, ert, data = _pygimli_data(path, survey)
    independent_flat = flat_halfspace_factors(survey)
    library_flat = np.asarray(ert.createGeometricFactors(data, numerical=False, forceFlatEarth=True))
    relative = np.abs(independent_flat - library_flat) / independent_flat
    if not np.all(np.isfinite(relative)) or np.max(relative) > 1e-5:
        raise ERTError(f"flat analytical factor oracle failed: max relative error {np.max(relative):.3g}")
    topographic = np.asarray(ert.createGeometricFactors(data, numerical=True))
    if (topographic.shape != independent_flat.shape or not np.all(np.isfinite(topographic))
            or np.any(topographic <= 0)):
        raise ERTError("topographic numerical factor is nonfinite, nonpositive or wrong shape")
    return pg, ert, data, independent_flat, topographic


def _rmse_log(predicted: np.ndarray, observed: np.ndarray) -> float:
    if not np.all(np.isfinite(predicted)) or np.any(predicted <= 0):
        return math.inf
    return float(np.sqrt(np.mean((np.log(predicted) - np.log(observed)) ** 2)))


def _mesh_sha256(mesh) -> str:
    """Fingerprint physical geometry, ignoring node IDs and round-off noise."""
    def position(node) -> tuple[float, float, float]:
        point = node.pos()
        return (round(float(point.x()), 8), round(float(point.y()), 8),
                round(float(point.z()), 8))

    nodes = sorted(position(node) for node in mesh.nodes())
    if len(set(nodes)) != len(nodes):
        raise ERTError("mesh fingerprint: nodes collide at 1e-8 m precision")
    geometry = {
        "coordinate_rounding_m": 1e-8,
        "nodes": nodes,
        "cells": sorted((int(cell.marker()), tuple(sorted(position(node) for node in cell.nodes())))
                        for cell in mesh.cells()),
    }
    return hashlib.sha256(json.dumps(geometry, separators=(",", ":")).encode()).hexdigest()


def inverse_verdict(*, engine_converged: bool, improvement: float) -> tuple[str, str | None]:
    """A predictive result needs both a physical engine stop and independent fit gain."""
    if not engine_converged:
        return "not-converged", "the solver reached its iteration limit or did not stop normally"
    if not math.isfinite(improvement) or improvement < 0.10:
        return "not-converged", "predeclared held-out improvement below 10%"
    return "passed", None


def _sensitivity_variant(ert, train, full, held: np.ndarray, observed: np.ndarray,
                         topographic_k: np.ndarray, options: dict,
                         *, error_scale: float = 1.0) -> dict:
    """Run one declared perturbation; never choose the primary model from it."""
    variant = train.copy()
    variant["err"] = np.asarray(train["err"]) * error_scale
    manager = ert.ERTManager(variant, sr=True)
    mapped_model = np.asarray(manager.invert(variant, verbose=False, **options), dtype=float)
    if not np.all(np.isfinite(mapped_model)) or np.any(mapped_model <= 0):
        raise ERTError("sensitivity inverse returned invalid resistivity")
    manager.fop.setData(full)
    predicted = np.asarray(manager.fop.response(manager.inv.model), dtype=float) / topographic_k
    metric = _rmse_log(predicted[held], observed[held])
    if not math.isfinite(metric):
        raise ERTError("sensitivity forward produced invalid held-out resistance")
    return {"mesh_cells": len(mapped_model), "model_range_ohm_m": [float(np.min(mapped_model)),
                                                                     float(np.max(mapped_model))],
            "heldout_log_r_rmse": metric, "chi2_assumed_weights": float(manager.inv.chi2()),
            "iterations": len(manager.inv.chi2History) - 1}


def run(path: Path, *, source_sha256: str, allow_inverse: bool = True) -> dict:
    """Compute source QC, then a conditional local field inverse with frozen gates."""
    survey = parse_ohm(path)
    report: dict = {
        "schema": "inverse-earth.local-ert-m07/v1", "source_id": SOURCE_ID,
        "source_sha256": source_sha256, "source_bytes": Path(path).stat().st_size,
        "rights_decision": "provider-link-only", "raw_publication": False,
        "qc": qc(survey), "truth": None, "field_geology_claim": None,
        "inverse_status": "not-run", "uncertainty_status": "assumed-not-calibrated",
    }
    if not allow_inverse:
        return report
    if np.any(survey.resistance_ohm <= 0):
        report.update(inverse_status="ineligible", inverse_reason="nonpositive resistance with logarithmic ERT inverse")
        return report
    started = time.perf_counter()
    try:
        pg, ert, full, flat_k, topo_k = factors(path, survey)
    except (ERTError, RuntimeError, TypeError, AssertionError) as error:
        report.update(inverse_status="unverified", inverse_reason=f"geometric-factor oracle failed: {error}")
        report["wall_seconds"] = round(time.perf_counter() - started, 3)
        return report
    resistance = survey.resistance_ohm
    apparent = resistance * topo_k
    if np.any(apparent <= 0):
        raise ERTError("positive resistance produced nonpositive apparent resistivity")
    training, held = holdout_indices(survey)
    blocked_training, blocked_held = blocked_holdout_indices(survey)
    sigma_r = np.maximum(0.03 * np.abs(resistance), 0.001)
    full["k"] = topo_k
    full["rhoa"] = apparent
    full["err"] = sigma_r / resistance
    train = full.copy()
    valid = np.ones(len(resistance), dtype=float)
    valid[held] = 0
    train["valid"] = valid
    train.removeInvalid()
    if train.size() != len(training):
        raise ERTError("pyGIMLi training container did not preserve the predeclared split")
    baseline_rhoa = float(np.exp(np.median(np.log(apparent[training]))))
    baseline_r = baseline_rhoa / topo_k[held]
    baseline_rmse = _rmse_log(baseline_r, resistance[held])
    report["factors"] = {
        "flat_formula_max_relative_error": float(np.max(np.abs(flat_k - np.asarray(
            ert.createGeometricFactors(full, numerical=False, forceFlatEarth=True))) / flat_k)),
        "topography_log_ratio_range": [float(np.min(np.log(topo_k / flat_k))),
                                        float(np.max(np.log(topo_k / flat_k)))],
        "topography_median_abs_log_ratio": float(np.median(np.abs(np.log(topo_k / flat_k)))),
        "flat_k_ohm_m_per_ohm_range": [float(np.min(flat_k)), float(np.max(flat_k))],
        "topographic_k_ohm_m_per_ohm_range": [float(np.min(topo_k)), float(np.max(topo_k))],
    }
    report["split"] = {"rule": "within AB-index-span, spatial midpoint order, every fifth from index 4",
                       "training_rows": training.tolist(), "heldout_rows": held.tolist(),
                       "training_count": len(training), "heldout_count": len(held)}
    report["split"]["sha256"] = hashlib.sha256(json.dumps(report["split"], sort_keys=True).encode()).hexdigest()
    report["blocked_split"] = {
        "rule": "hold out all A/B midpoints in central 40-60% of profile x extent",
        "training_rows": blocked_training.tolist(), "heldout_rows": blocked_held.tolist(),
        "training_count": len(blocked_training), "heldout_count": len(blocked_held),
    }
    report["blocked_split"]["sha256"] = hashlib.sha256(json.dumps(report["blocked_split"], sort_keys=True).encode()).hexdigest()
    report["weighting"] = {"sigma_r_ohm": "max(0.03*abs(R),0.001)",
                           "source_error": "not supplied", "reciprocal_error": "not available",
                           "chi_square_meaning": "conditional on assumed weights, not instrument-calibrated"}
    report["baseline"] = {"training_median_rhoa_ohm_m": baseline_rhoa,
                          "heldout_log_r_rmse": baseline_rmse}
    report["engine"] = {"pygimli_distribution": importlib.metadata.version("pygimli"),
                        "pgcore_distribution": importlib.metadata.version("pgcore"),
                        "numpy": np.__version__, "scipy": importlib.metadata.version("scipy"),
                        "options": INVERSE_OPTIONS}
    report["environment_versions_sha256"] = hashlib.sha256(json.dumps(
        {key: value for key, value in report["engine"].items() if key != "options"},
        sort_keys=True).encode()).hexdigest()
    report["configuration_sha256"] = hashlib.sha256(json.dumps(
        {"primary_options": INVERSE_OPTIONS, "alternate_mesh": ALTERNATE_MESH_OPTIONS,
         "sigma_r_ohm": report["weighting"]["sigma_r_ohm"],
         "interleaved_split_sha256": report["split"]["sha256"],
         "blocked_split_sha256": report["blocked_split"]["sha256"]},
        sort_keys=True).encode()).hexdigest()
    try:
        mgr = ert.ERTManager(train, sr=True)
        model = np.asarray(mgr.invert(train, verbose=False, **INVERSE_OPTIONS), dtype=float)
        if model.size < 2 or not np.all(np.isfinite(model)) or np.any(model <= 0):
            raise ERTError("inverse returned a nonfinite or nonpositive resistivity model")
        train_prediction_rhoa = np.asarray(mgr.inv.response, dtype=float)
        if len(train_prediction_rhoa) != len(training):
            raise ERTError("inverse training response has wrong length")
        coverage = np.asarray(mgr.coverage(), dtype=float)
        if not np.all(np.isfinite(coverage)) or len(coverage) != len(model):
            raise ERTError("inverse Jacobian coverage is nonfinite or wrong shape")
        cell_centers = [[float(cell.center().x()), float(cell.center().y())]
                        for cell in mgr.fop.paraDomain.cells()]
        if len(cell_centers) != len(model):
            raise ERTError("inverse parameter-cell geometry disagrees with model")
        parameter_mesh_sha256 = _mesh_sha256(mgr.fop.paraDomain)
        forward_mesh_sha256 = _mesh_sha256(mgr.fop.mesh())
        # Keep the fitted parameter mesh/model frozen; replace only measurement geometry.
        mgr.fop.setData(full)
        full_prediction_rhoa = np.asarray(mgr.fop.response(mgr.inv.model), dtype=float)
        if len(full_prediction_rhoa) != len(resistance):
            raise ERTError("held-out forward response has wrong length")
        predicted_r = full_prediction_rhoa / topo_k
        model_rmse = _rmse_log(predicted_r[held], resistance[held])
        improvement = 1 - model_rmse / baseline_rmse
        iterations = len(mgr.inv.chi2History) - 1
        chi2 = float(mgr.inv.chi2())
        if chi2 <= 1 and iterations < INVERSE_OPTIONS["maxIter"]:
            stopping_reason = "assumed-chi2-target"
        elif 2 < iterations < INVERSE_OPTIONS["maxIter"]:
            # pyGIMLi also stops when objective improvement is <1% (its dPhi default).
            stopping_reason = "objective-stagnation"
        else:
            stopping_reason = "iteration-limit"
        converged = stopping_reason != "iteration-limit"
        report["inverse"] = {
            "mesh_cells": int(mgr.fop.paraDomain.cellCount()), "model_resistivity_ohm_m": model.tolist(),
            "model_cell_center_xz_m": cell_centers,
            "parameter_mesh": parameter_mesh(mgr.fop.paraDomain),
            "parameter_mesh_sha256": parameter_mesh_sha256,
            "forward_mesh_sha256": forward_mesh_sha256,
            "model_range_ohm_m": [float(np.min(model)), float(np.max(model))],
            "coverage_log10_sensitivity_per_cell": coverage.tolist(),
            "coverage_meaning": "pyGIMLi log-Jacobian coverage divided by cell size; not resolution",
            "observed_r_ohm": resistance.tolist(), "predicted_r_ohm": predicted_r.tolist(),
            "signed_residual_r_ohm": (predicted_r - resistance).tolist(),
            "training_log_r_rmse": _rmse_log(predicted_r[training], resistance[training]),
            "heldout_log_r_rmse": model_rmse,
            "heldout_improvement_vs_homogeneous": improvement,
            "chi2_assumed_weights": chi2, "engine_converged": converged,
            "iterations": iterations, "stopping_reason": stopping_reason,
        }
        report["sensitivity"] = {
            "alternate_mesh": {"options": ALTERNATE_MESH_OPTIONS,
                             **_sensitivity_variant(ert, train, full, held, resistance, topo_k,
                                                    ALTERNATE_MESH_OPTIONS)},
            "doubled_assumed_error": {"scale": 2.0,
                                      **_sensitivity_variant(ert, train, full, held, resistance,
                                                             topo_k, INVERSE_OPTIONS, error_scale=2.0)},
            "meaning": "diagnostic perturbations only; primary model and held-out gate are not retuned",
        }
        block_data = full.copy()
        block_valid = np.ones(len(resistance), dtype=float)
        block_valid[blocked_held] = 0
        block_data["valid"] = block_valid
        block_data.removeInvalid()
        if block_data.size() != len(blocked_training):
            raise ERTError("blocked training container did not preserve the fixed spatial split")
        block_baseline_rhoa = float(np.exp(np.median(np.log(apparent[blocked_training]))))
        block_baseline = _rmse_log(block_baseline_rhoa / topo_k[blocked_held], resistance[blocked_held])
        block_model = _sensitivity_variant(ert, block_data, full, blocked_held, resistance,
                                           topo_k, INVERSE_OPTIONS)
        block_improvement = 1 - block_model["heldout_log_r_rmse"] / block_baseline
        block_converged = block_model["iterations"] < INVERSE_OPTIONS["maxIter"]
        report["blocked_validation"] = {
            **block_model, "baseline_heldout_log_r_rmse": block_baseline,
            "improvement_vs_homogeneous": block_improvement,
            "engine_stopped_before_limit": block_converged,
            "meaning": "within one profile; shared electrodes remain possible at block edges",
        }
        report["inverse_status"], reason = inverse_verdict(
            engine_converged=converged and block_converged,
            improvement=min(improvement, block_improvement))
        if reason is not None:
            report["inverse_reason"] = reason
    except (RuntimeError, ValueError, TypeError, AssertionError) as error:
        report.update(inverse_status="not-converged", inverse_reason=f"pyGIMLi forward/inverse failed: {error}")
    report["wall_seconds"] = round(time.perf_counter() - started, 3)
    return report


def run_source(*, root: Path = ROOT, qc_only: bool = False) -> dict:
    """Reverify the ignored ledger asset and retain only an ignored local result."""
    root = Path(root).resolve()
    record, raw_path, receipt = acquire_source(SOURCE_ID, root=root)
    if receipt["validation_status"] != "hash-verified":
        raise ERTError("Slagdump acquisition receipt is not hash-verified")
    report = run(raw_path, source_sha256=record["sha256"], allow_inverse=not qc_only)
    report["source_object_url"] = record["object_url"]
    report["source_acquisition_asset_id"] = receipt["asset_id"]
    report["code_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    folder = root / "data/raw/ert"
    if not folder.resolve().is_relative_to((root / "data/raw").resolve()):
        raise ERTError("ERT result path escapes ignored data/raw")
    folder.mkdir(parents=True, exist_ok=True)
    kind = "qc" if qc_only else "inverse"
    output = folder / f"slagdump-m07-{kind}-{report['code_sha256'][:12]}.json"
    checksum_path = folder / f"{output.name}.sha256"
    if output.exists() or checksum_path.exists():
        if not output.is_file() or not checksum_path.is_file() or output.is_symlink() or checksum_path.is_symlink():
            raise ERTError(f"incomplete or symlinked local ERT receipt: {output}")
        existing_bytes = output.read_bytes()
        if hashlib.sha256(existing_bytes).hexdigest() != checksum_path.read_text(encoding="ascii").strip():
            raise ERTError(f"immutable local ERT receipt checksum drift: {output}")
        old = json.loads(existing_bytes)
        if old.get("source_sha256") != report["source_sha256"] or old.get("code_sha256") != report["code_sha256"]:
            raise ERTError(f"immutable local ERT receipt drift: {output}")
        if (old.get("qc") != report["qc"] or old.get("inverse_status") != report["inverse_status"]
                or old.get("inverse_reason") != report.get("inverse_reason")):
            raise ERTError(f"M07 rerun changed QC or scientific verdict: {output}")
        for key in ("environment_versions_sha256", "configuration_sha256"):
            if old.get(key) != report.get(key):
                raise ERTError(f"M07 rerun changed {key}: {output}")
        if not qc_only and "inverse" in old and "inverse" in report:
            for key in ("parameter_mesh_sha256", "forward_mesh_sha256"):
                if old["inverse"].get(key) != report["inverse"].get(key):
                    raise ERTError(f"M07 rerun changed {key}: {output}")
            if old.get("split", {}).get("sha256") != report.get("split", {}).get("sha256"):
                raise ERTError(f"M07 rerun changed the predeclared holdout split: {output}")
            for key in ("model_resistivity_ohm_m", "predicted_r_ohm"):
                if not np.allclose(old["inverse"][key], report["inverse"][key], rtol=0.02, atol=1e-6):
                    raise ERTError(f"M07 rerun changed {key} beyond 2%: {output}")
            for key in ("alternate_mesh", "doubled_assumed_error"):
                old_rmse = old["sensitivity"][key]["heldout_log_r_rmse"]
                new_rmse = report["sensitivity"][key]["heldout_log_r_rmse"]
                if not math.isclose(old_rmse, new_rmse, rel_tol=0.02, abs_tol=1e-6):
                    raise ERTError(f"M07 rerun changed {key} holdout RMSE beyond 2%: {output}")
            if old.get("blocked_split", {}).get("sha256") != report.get("blocked_split", {}).get("sha256"):
                raise ERTError(f"M07 rerun changed the spatial blocked holdout: {output}")
            if not math.isclose(old["blocked_validation"]["heldout_log_r_rmse"],
                                report["blocked_validation"]["heldout_log_r_rmse"],
                                rel_tol=0.02, abs_tol=1e-6):
                raise ERTError(f"M07 rerun changed blocked holdout RMSE beyond 2%: {output}")
        return old
    payload = (json.dumps(report, indent=2, allow_nan=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    with tempfile.NamedTemporaryFile(prefix=".ert-receipt-", dir=folder, delete=False) as temporary:
        staged = Path(temporary.name)
        temporary.write(payload)
    with tempfile.NamedTemporaryFile(prefix=".ert-hash-", dir=folder, delete=False) as temporary:
        staged_hash = Path(temporary.name)
        temporary.write((digest + "\n").encode("ascii"))
    try:
        os.link(staged, output)
        os.link(staged_hash, checksum_path)
    except FileExistsError as error:
        raise ERTError(f"another M07 run created {output}; rerun to verify") from error
    finally:
        staged.unlink(missing_ok=True)
        staged_hash.unlink(missing_ok=True)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qc-only", action="store_true", help="Validate source geometry without an inverse")
    args = parser.parse_args(argv)
    try:
        result = run_source(qc_only=args.qc_only)
    except (SourceError, ERTError, OSError) as error:
        print(f"M07 Slagdump failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({key: result[key] for key in ("source_id", "source_sha256", "qc", "inverse_status")},
                     indent=2))
    return 0 if result["inverse_status"] in ("passed", "not-run") else 3


if __name__ == "__main__":
    raise SystemExit(main())
