"""Rights-contained Koenigsee first-arrival QC and conditional 2D tomography.

The source is provider-linked; this script writes only ignored local receipts.
Run with data-pipeline/requirements-traveltime.txt in an isolated environment.
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

SOURCE_ID = "pygimli-koenigsee"
MAX_INPUT_BYTES = 1_000_000
SENSOR_COUNT = re.compile(r"^(\d+) # shot/geophone points$")
PICK_COUNT = re.compile(r"^(\d+) # measurements$")
UNIT_BASIS = "provider pyGIMLi example/manager interpretation: local x/y metres, t seconds; not file-declared"
INVERSE_OPTIONS = {"secNodes": 3, "paraMaxCellSize": 5.0, "zWeight": 0.2,
                   "vTop": 500.0, "vBottom": 5000.0, "lam": 20.0, "maxIter": 20}
ALTERNATE_START_OPTIONS = {**INVERSE_OPTIONS, "vTop": 700.0, "vBottom": 3500.0}
FINER_MESH_OPTIONS = {**INVERSE_OPTIONS, "paraMaxCellSize": 2.5}
CGLS_MAX_ITER = 1000
CGLS_TOLERANCE = 1e-20  # Absolute squared residual of the inner linear solve.
REPEAT_TIME_ATOL_S = 1e-5  # 0.01 ms, below the apparent 0.05 ms pick increment.
REPEAT_VELOCITY_ATOL_M_S = 0.1
REPEAT_VELOCITY_RTOL = 1e-4


class TraveltimeError(ValueError):
    """A physical source contract or numerical gate failed."""


@dataclass(frozen=True)
class Survey:
    sensor_xy_m: np.ndarray
    shot_geophone: np.ndarray  # zero-based sensor IDs; columns s, g
    time_s: np.ndarray


def _finite_float(value: str, where: str) -> float:
    try:
        number = float(value)
    except ValueError as error:
        raise TraveltimeError(f"{where}: expected a finite decimal, got {value!r}") from error
    if not math.isfinite(number):
        raise TraveltimeError(f"{where}: non-finite number {value!r}")
    return number


def _count(line: str, pattern: re.Pattern, where: str, minimum: int, maximum: int) -> int:
    match = pattern.fullmatch(line)
    if match is None:
        raise TraveltimeError(f"{where}: expected {pattern.pattern!r} marker")
    count = int(match.group(1))
    if not minimum <= count <= maximum:
        raise TraveltimeError(f"{where}: count {count} outside [{minimum},{maximum}]")
    return count


def parse_sgt(path: Path) -> Survey:
    """Parse the fixed pyGIMLi survey format without guessed columns or repairs."""
    path = Path(path)
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise TraveltimeError(f"{path}: .sgt exceeds {MAX_INPUT_BYTES} bytes")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise TraveltimeError(f"{path}: cannot read UTF-8 .sgt: {error}") from error
    if len(lines) < 5:
        raise TraveltimeError("source header: truncated .sgt")
    count = _count(lines[0], SENSOR_COUNT, "sensor count", 2, 1024)
    if lines[1].split() != ["#x", "y"]:
        raise TraveltimeError("sensor columns: expected '#x y'; units require the declared provider convention")
    cursor = 2
    sensors = []
    for row in range(count):
        if cursor >= len(lines):
            raise TraveltimeError(f"sensor row {row + 1}: truncated")
        fields = lines[cursor].split()
        if len(fields) != 2:
            raise TraveltimeError(f"sensor row {row + 1}: expected exactly x y")
        sensors.append([_finite_float(fields[0], f"sensor row {row + 1} x"),
                        _finite_float(fields[1], f"sensor row {row + 1} y")])
        cursor += 1
    xy = np.asarray(sensors, dtype=float)
    if not np.all(np.diff(xy[:, 0]) > 0):
        raise TraveltimeError("sensor x: require strictly increasing, unique line positions")
    if cursor >= len(lines):
        raise TraveltimeError("pick count: missing")
    pick_count = _count(lines[cursor], PICK_COUNT, "pick count", 4, 100_000)
    cursor += 1
    if cursor >= len(lines) or lines[cursor].split() != ["#s", "g", "t"]:
        raise TraveltimeError("pick columns: expected '#s g t'; t is seconds by the provider convention")
    cursor += 1
    pairs, times, seen = [], [], set()
    for row in range(pick_count):
        if cursor >= len(lines):
            raise TraveltimeError(f"pick row {row + 1}: truncated")
        fields = lines[cursor].split()
        if len(fields) != 3:
            raise TraveltimeError(f"pick row {row + 1}: expected exactly s g t")
        try:
            shot, receiver = int(fields[0]), int(fields[1])
        except ValueError as error:
            raise TraveltimeError(f"pick row {row + 1}: s/g must be integer sensor IDs") from error
        if min(shot, receiver) < 1 or max(shot, receiver) > count:
            raise TraveltimeError(f"pick row {row + 1}: s/g outside 1..{count}")
        if shot == receiver:
            raise TraveltimeError(f"pick row {row + 1}: zero-offset self-pick")
        if (shot, receiver) in seen:
            raise TraveltimeError(f"pick row {row + 1}: duplicate shot/geophone pair")
        seen.add((shot, receiver))
        pick = _finite_float(fields[2], f"pick row {row + 1} t")
        if pick <= 0:
            raise TraveltimeError(f"pick row {row + 1} t: positive first-arrival seconds required")
        pairs.append([shot - 1, receiver - 1])
        times.append(pick)
        cursor += 1
    if any(line.strip() for line in lines[cursor:]):
        raise TraveltimeError(f"trailing payload: unexpected content after {pick_count} picks")
    return Survey(xy, np.asarray(pairs, dtype=int), np.asarray(times, dtype=float))


def offsets_m(survey: Survey) -> np.ndarray:
    shot, receiver = survey.shot_geophone.T
    return np.linalg.norm(survey.sensor_xy_m[shot] - survey.sensor_xy_m[receiver], axis=1)


def qc(survey: Survey) -> dict:
    """Describe all valid picks; anomaly flags never exclude or change weights."""
    pairs = survey.shot_geophone
    times = survey.time_s
    xy = survey.sensor_xy_m
    offsets = offsets_m(survey)
    if np.any(offsets <= 0):
        raise TraveltimeError("geometry: coincident source and receiver positions")
    apparent = offsets / times
    lookup = {tuple(pair): row for row, pair in enumerate(pairs)}
    reciprocals = [(row, lookup[(receiver, shot)]) for row, (shot, receiver) in enumerate(pairs)
                   if (receiver, shot) in lookup and row < lookup[(receiver, shot)]]
    shots, counts = np.unique(pairs[:, 0], return_counts=True)
    reversal_rows = set()
    for shot in shots:
        shot_rows = np.flatnonzero(pairs[:, 0] == shot)
        signed_x = xy[pairs[shot_rows, 1], 0] - xy[shot, 0]
        for sign in (-1, 1):
            side = shot_rows[signed_x * sign > 0]
            ordered = side[np.argsort(np.abs(xy[pairs[side, 1], 0] - xy[shot, 0]))]
            reversal_rows.update(ordered[1:][np.diff(times[ordered]) < -0.0002].tolist())
    gross_speed_rows = np.flatnonzero((apparent < 100) | (apparent > 10_000)).tolist()
    unique_times = np.unique(times)
    return {
        "sensor_count": len(xy), "shot_count": len(shots),
        "receiver_count": len(np.unique(pairs[:, 1])), "pick_count": len(times),
        "shot_pick_count_range": [int(np.min(counts)), int(np.max(counts))],
        "x_range_m": [float(xy[0, 0]), float(xy[-1, 0])],
        "y_range_m": [float(np.min(xy[:, 1])), float(np.max(xy[:, 1]))],
        "topographic_relief_m": float(np.ptp(xy[:, 1])),
        "offset_range_m": [float(np.min(offsets)), float(np.max(offsets))],
        "time_range_s": [float(np.min(times)), float(np.max(times))],
        "apparent_speed_range_m_s": [float(np.min(apparent)), float(np.max(apparent))],
        "apparent_speed_meaning": "straight source-receiver distance divided by picked time; not a layer speed",
        "smallest_distinct_time_step_s": float(np.min(np.diff(unique_times))) if len(unique_times) > 1 else None,
        "duplicate_pairs": 0, "reciprocal_pairs": [list(pair) for pair in reciprocals],
        "reciprocal_status": "available" if reciprocals else "not_available",
        "source_error_status": "not_supplied",
        "gross_speed_flag_rows": gross_speed_rows,
        "time_reversal_flag_rows": sorted(reversal_rows),
        "flag_rule": "apparent speed outside 100-10000 m/s or same-shot same-side time drop >0.2 ms; flags only",
        "units": {"x": "m", "y": "m, local vertical sign/datum not file-declared", "t": "s"},
        "unit_basis": UNIT_BASIS,
    }


def shot_splits(survey: Survey, *, policy: str = "pinned-15/v1") -> dict[str, dict[str, np.ndarray]]:
    """Freeze two whole-shot tests without looking at picked times."""
    shots = np.unique(survey.shot_geophone[:, 0])
    if policy == "pinned-15/v1":
        if len(shots) != 15:
            raise TraveltimeError(f"whole-shot validation requires the pinned 15 shots; found {len(shots)}")
        held_groups = {"interleaved": shots[4::5], "central_block": shots[6:9]}
        held_count = 3
    elif policy == "supplied-whole-shot/v1":
        n = len(shots)
        if n < 10:
            raise TraveltimeError("supplied whole-shot validation requires at least ten shots")
        held_count = (n + 4) // 5
        interleaved = np.asarray([((j + 1) * n) // held_count - 1 for j in range(held_count)])
        start = (n - held_count) // 2
        held_groups = {"interleaved": shots[interleaved],
                       "central_block": shots[start:start + held_count]}
    else:
        raise TraveltimeError("unsupported whole-shot validation policy")
    result = {}
    for name, held_shots in held_groups.items():
        held = np.flatnonzero(np.isin(survey.shot_geophone[:, 0], held_shots))
        training = np.flatnonzero(~np.isin(survey.shot_geophone[:, 0], held_shots))
        if len(held_shots) != held_count or len(training) < 100 or len(held) < 30:
            raise TraveltimeError(f"{name}: insufficient whole-shot training or held-out picks")
        result[name] = {"held_shots": held_shots, "held_rows": held, "training_rows": training}
    return result


def homogeneous_times(survey: Survey, velocity_m_s: float) -> np.ndarray:
    if not math.isfinite(velocity_m_s) or velocity_m_s <= 0:
        raise TraveltimeError("homogeneous oracle: positive finite velocity required")
    return offsets_m(survey) / velocity_m_s


def homogeneous_oracle() -> dict:
    """Compare an independent Euclidean formula to Dijkstra on a flat mesh."""
    try:
        import pygimli as pg
        from pygimli.physics import traveltime as tt
    except ImportError as error:
        raise TraveltimeError("M09 needs the isolated requirements-traveltime.txt environment") from error
    pg.utils.noCache(True)
    pg.setThreadCount(1)
    positions = np.asarray([[float(x), 0.0] for x in (0, 5, 10, 15, 20)])
    pairs = np.asarray([[0, 2], [0, 4], [1, 4], [4, 0]])
    survey = Survey(positions, pairs, np.ones(len(pairs)))
    scheme = tt.DataContainerTT()
    for x, y in positions:
        scheme.createSensor([x, y])
    scheme.resize(len(pairs))
    scheme["s"], scheme["g"] = pairs[:, 0], pairs[:, 1]
    mesh = pg.meshtools.createGrid(x=np.linspace(0, 20, 41), y=np.linspace(-10, 0, 21))
    manager = tt.TravelTimeManager()
    predicted = np.asarray(manager.simulate(mesh=mesh, scheme=scheme,
                                            vel=np.full(mesh.cellCount(), 1000.0),
                                            secNodes=3, returnArray=True), dtype=float)
    doubled = np.asarray(manager.simulate(mesh=mesh, scheme=scheme,
                                          vel=np.full(mesh.cellCount(), 2000.0),
                                          secNodes=3, returnArray=True), dtype=float)
    expected = homogeneous_times(survey, 1000.0)
    relative = np.abs(predicted - expected) / expected
    scaling = np.abs(2 * doubled - predicted) / predicted
    reciprocal = abs(predicted[1] - predicted[3]) / predicted[1]
    if (not np.all(np.isfinite(predicted)) or np.any(predicted <= 0)
            or np.max(relative) > 1e-3 or np.max(scaling) > 1e-3 or reciprocal > 1e-3):
        raise TraveltimeError("homogeneous Dijkstra/analytic oracle, speed scaling or reciprocity failed")
    return {"max_relative_error": float(np.max(relative)),
            "max_speed_scaling_relative_error": float(np.max(scaling)),
            "reciprocity_relative_error": float(reciprocal),
            "analytic_basis": "straight Euclidean path in a homogeneous isotropic medium, t=distance/v"}


def _mesh_sha256(mesh) -> str:
    """Hash physical geometry, not pyGIMLi node order or floating noise."""
    def position(node) -> tuple[float, float, float]:
        point = node.pos()
        return (round(float(point.x()), 8), round(float(point.y()), 8), round(float(point.z()), 8))

    nodes = sorted(position(node) for node in mesh.nodes())
    if len(nodes) != len(set(nodes)):
        raise TraveltimeError("mesh fingerprint: nodes collide at 1e-8 m precision")
    geometry = {"coordinate_rounding_m": 1e-8, "nodes": nodes,
                "cells": sorted((int(cell.marker()), tuple(sorted(position(node) for node in cell.nodes())))
                                for cell in mesh.cells())}
    return hashlib.sha256(json.dumps(geometry, separators=(",", ":")).encode()).hexdigest()


def _pygimli_data(path: Path, survey: Survey):
    try:
        import pygimli as pg
        from pygimli.physics import traveltime as tt
    except ImportError as error:
        raise TraveltimeError("M09 needs the isolated requirements-traveltime.txt environment") from error
    pg.utils.noCache(True)
    pg.setThreadCount(1)
    data = tt.load(str(path))
    if data.sensorCount() != len(survey.sensor_xy_m) or data.size() != len(survey.time_s):
        raise TraveltimeError("pyGIMLi parser disagrees with strict sensor/pick counts")
    positions = np.asarray([[point.x(), point.y()] for point in data.sensors()], dtype=float)
    if not np.allclose(positions, survey.sensor_xy_m, rtol=0, atol=1e-9):
        raise TraveltimeError("pyGIMLi parser disagrees with strict sensor positions")
    for column, index in (("s", 0), ("g", 1)):
        if not np.array_equal(np.asarray(data[column], dtype=int), survey.shot_geophone[:, index]):
            raise TraveltimeError(f"pyGIMLi parser disagrees with strict {column} indices")
    if not np.allclose(np.asarray(data["t"]), survey.time_s, rtol=0, atol=1e-10):
        raise TraveltimeError("pyGIMLi parser disagrees with strict picked times")
    if not np.all(np.asarray(data["valid"]) == 1):
        raise TraveltimeError("pyGIMLi parser marked a source pick invalid without source provenance")
    return tt, data


def _rmse_s(predicted: np.ndarray, observed: np.ndarray) -> float:
    if (len(predicted) == 0 or predicted.shape != observed.shape
            or not np.all(np.isfinite(predicted)) or np.any(predicted <= 0)):
        return math.inf
    return float(np.sqrt(np.mean((predicted - observed) ** 2)))


def _split_record(name: str, parts: dict[str, np.ndarray]) -> dict:
    record = {"rule": "every fifth shot in x order, starting at index 4" if name == "interleaved"
              else "three central shots by survey x order",
              "held_shots_zero_based": parts["held_shots"].tolist(),
              "training_rows": parts["training_rows"].tolist(),
              "heldout_rows": parts["held_rows"].tolist(),
              "training_count": len(parts["training_rows"]),
              "heldout_count": len(parts["held_rows"])}
    record["sha256"] = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    return record


def _weighted_homogeneous_baseline(offset: np.ndarray, times: np.ndarray,
                                   sigma: np.ndarray, training: np.ndarray) -> tuple[float, np.ndarray]:
    weight = 1 / sigma[training] ** 2
    numerator = np.sum(weight * offset[training] * times[training])
    denominator = np.sum(weight * offset[training] ** 2)
    if not math.isfinite(denominator) or denominator <= 0:
        raise TraveltimeError("training-only homogeneous baseline has invalid geometry/weights")
    slowness = float(numerator / denominator)
    if not math.isfinite(slowness) or slowness <= 0:
        raise TraveltimeError("training-only homogeneous baseline has invalid slowness")
    return slowness, offset * slowness


def _invert_once(tt, full, survey: Survey, parts: dict[str, np.ndarray],
                 options: dict, *, retain_arrays: bool) -> dict:
    """Fit training shots and forward-predict held shots on a fresh frozen mesh."""
    observed = survey.time_s
    shot_ids = survey.shot_geophone[:, 0]
    sigma = np.maximum(0.03 * observed, 0.0001)
    offset = offsets_m(survey)
    training, held, held_shots = parts["training_rows"], parts["held_rows"], parts["held_shots"]
    slowness, baseline = _weighted_homogeneous_baseline(offset, observed, sigma, training)
    train = full.copy()
    valid = np.ones(len(observed), dtype=float)
    valid[held] = 0
    train["valid"] = valid
    train.removeInvalid()
    if (train.size() != len(training) or train.sensorCount() != len(survey.sensor_xy_m)
            or not np.array_equal(np.asarray(train["s"], dtype=int), shot_ids[training])
            or not np.array_equal(np.asarray(train["g"], dtype=int), survey.shot_geophone[training, 1])):
        raise TraveltimeError("pyGIMLi training container changed the fixed whole-shot partition")
    train["err"] = sigma[training]  # pyGIMLi's traveltime manager expects absolute seconds here.
    manager = tt.TravelTimeManager(train)
    inner = manager.inv.inv
    inner.setMaxCGLSIter(CGLS_MAX_ITER)
    inner.setCGLSTolerance(CGLS_TOLERANCE)
    if inner.maxCGLSIter() != CGLS_MAX_ITER or inner.maxCGLSTolerance() != CGLS_TOLERANCE:
        raise TraveltimeError("pyGIMLi did not retain the pinned inner CGLS convergence settings")
    velocity = np.asarray(manager.invert(train, verbose=False, **options), dtype=float)
    if velocity.size < 2 or not np.all(np.isfinite(velocity)) or np.any(velocity <= 0):
        raise TraveltimeError("pyGIMLi inverse returned invalid positive velocity")
    if len(velocity) != manager.mesh.cellCount():
        raise TraveltimeError("inverse velocity vector does not match parameter mesh cells")
    train_response = np.asarray(manager.inv.response, dtype=float)
    if len(train_response) != len(training):
        raise TraveltimeError("inverse training response has wrong length")
    coverage = np.asarray(manager.rayCoverage(), dtype=float)
    if (len(coverage) != len(velocity) or not np.all(np.isfinite(coverage))
            or np.any(coverage < -1e-9)):
        raise TraveltimeError("raypath-length coverage is invalid or mismatched to the velocity model")
    centers = [[float(cell.center().x()), float(cell.center().y())] for cell in manager.mesh.cells()]
    if len(centers) != len(velocity):
        raise TraveltimeError("parameter mesh centers do not match the velocity vector")
    parameter_mesh_sha = _mesh_sha256(manager.mesh)
    forward_mesh_sha = _mesh_sha256(manager.fop.mesh())
    # A fresh forward manager rebuilds the source graph for held shots. Swapping
    # the training container into the original Dijkstra operator is not valid.
    simulator = tt.TravelTimeManager()
    predicted = np.asarray(simulator.simulate(mesh=manager.mesh, scheme=full, vel=velocity,
                                              secNodes=options["secNodes"], returnArray=True), dtype=float)
    if len(predicted) != len(observed) or not np.all(np.isfinite(predicted)) or np.any(predicted <= 0):
        raise TraveltimeError("frozen-mesh forward prediction returned invalid travel times")
    if not np.allclose(predicted[training], train_response, rtol=1e-5, atol=1e-7):
        raise TraveltimeError("fresh forward response disagrees with the fitted training operator")
    held_rmse = _rmse_s(predicted[held], observed[held])
    baseline_rmse = _rmse_s(baseline[held], observed[held])
    improvement = 1 - held_rmse / baseline_rmse
    group_metrics = []
    for shot in held_shots:
        rows = np.flatnonzero(shot_ids == shot)
        model_group = _rmse_s(predicted[rows], observed[rows])
        baseline_group = _rmse_s(baseline[rows], observed[rows])
        group_metrics.append({"shot_sensor_index_zero_based": int(shot), "pick_count": len(rows),
                              "model_rmse_ms": 1000 * model_group,
                              "baseline_rmse_ms": 1000 * baseline_group,
                              "improvement": 1 - model_group / baseline_group})
    iterations = len(manager.inv.chi2History) - 1
    chi2 = float(manager.inv.chi2())
    if not math.isfinite(chi2):
        raise TraveltimeError("inverse ended with nonfinite conditional chi-square")
    if iterations < options["maxIter"] and chi2 <= 1:
        stop = "assumed-chi2-target"
    elif 2 < iterations < options["maxIter"]:
        stop = "objective-stagnation"
    else:
        stop = "iteration-limit"
    result = {
        "mesh_cells": len(velocity), "parameter_mesh_sha256": parameter_mesh_sha,
        "forward_mesh_sha256": forward_mesh_sha,
        "model_velocity_range_m_s": [float(np.min(velocity)), float(np.max(velocity))],
        "coverage_nonzero_cell_fraction": float(np.mean(coverage > 0)),
        "coverage_meaning": "training-ray summed path length per cell in m; not resolution or uniqueness",
        "baseline_homogeneous_velocity_m_s": 1 / slowness,
        "heldout_rmse_s": held_rmse, "heldout_rmse_ms": 1000 * held_rmse,
        "baseline_heldout_rmse_s": baseline_rmse, "baseline_heldout_rmse_ms": 1000 * baseline_rmse,
        "heldout_improvement": improvement,
        "improved_held_shot_count": sum(group["improvement"] > 0 for group in group_metrics),
        "per_held_shot": group_metrics,
        "training_rmse_ms": 1000 * _rmse_s(predicted[training], observed[training]),
        "chi2_assumed_weights": chi2, "chi2_history_assumed_weights": list(map(float, manager.inv.chi2History)),
        "iterations": iterations, "stopping_reason": stop, "engine_stopped_before_limit": stop != "iteration-limit",
    }
    if retain_arrays:
        result.update({"model_velocity_m_s": velocity.tolist(), "model_cell_center_xy_m": centers,
                       "parameter_mesh": parameter_mesh(manager.mesh),
                       "raypath_coverage_m_per_cell": coverage.tolist(),
                       "predicted_t_s": predicted.tolist(),
                       "signed_residual_t_s": (predicted - observed).tolist(),
                       "baseline_predicted_t_s": baseline.tolist()})
    return result


def _field_verdict(results: dict[str, dict], *, minimum_improved_shots: int = 2) -> tuple[str, str | None]:
    for name in ("interleaved", "central_block"):
        result = results[name]
        if not result["engine_stopped_before_limit"]:
            return "not-converged", f"{name} inverse reached its iteration ceiling"
        if (not math.isfinite(result["heldout_improvement"]) or result["heldout_improvement"] < 0.10
                or result["improved_held_shot_count"] < minimum_improved_shots):
            return "not-converged", f"{name} whole-shot prediction failed the frozen improvement gate"
    return "passed", None


def run(path: Path, *, source_sha256: str, allow_inverse: bool = True,
        validation_policy: str = "pinned-15/v1") -> dict:
    """Preserve source QC, then attempt only the predeclared conditional inverse."""
    survey = parse_sgt(path)
    report: dict = {
        "schema": "inverse-earth.local-traveltime-m09/v1", "source_id": SOURCE_ID,
        "source_sha256": source_sha256, "source_bytes": Path(path).stat().st_size,
        "rights_decision": "provider-link-only", "raw_publication": False,
        "qc": qc(survey), "truth": None, "field_geology_claim": None,
        "inverse_status": "not-run", "uncertainty_status": "assumed-not-calibrated",
        "unit_basis": UNIT_BASIS,
    }
    if not allow_inverse:
        return report
    started = time.perf_counter()
    try:
        splits = shot_splits(survey, policy=validation_policy)
    except TraveltimeError as error:
        report.update(inverse_status="ineligible", inverse_reason=str(error))
        report["wall_seconds"] = round(time.perf_counter() - started, 3)
        return report
    try:
        report["homogeneous_oracle"] = homogeneous_oracle()
        tt, full = _pygimli_data(path, survey)
    except (TraveltimeError, RuntimeError, TypeError, AssertionError) as error:
        report.update(inverse_status="unverified", inverse_reason=f"forward/format oracle failed: {error}")
        report["wall_seconds"] = round(time.perf_counter() - started, 3)
        return report
    sigma = np.maximum(0.03 * survey.time_s, 0.0001)
    full["err"] = sigma
    report["weighting"] = {"sigma_t_s": "max(0.03*t,0.0001)",
                           "source_error": "not supplied", "reciprocal_error": "not available",
                           "chi_square_meaning": "conditional on assumed weights, not instrument-calibrated"}
    report["engine"] = {"pygimli_distribution": importlib.metadata.version("pygimli"),
                        "pgcore_distribution": importlib.metadata.version("pgcore"),
                        "numpy": np.__version__, "scipy": importlib.metadata.version("scipy"),
                        "thread_count": 1,
                        "cgls_max_iterations": CGLS_MAX_ITER,
                        "cgls_residual_squared_tolerance": CGLS_TOLERANCE,
                        "options": INVERSE_OPTIONS}
    report["environment_versions_sha256"] = hashlib.sha256(json.dumps(
        {key: value for key, value in report["engine"].items() if key != "options"},
        sort_keys=True).encode()).hexdigest()
    report["split"] = {name: _split_record(name, parts) for name, parts in splits.items()}
    configuration = {"primary_options": INVERSE_OPTIONS, "alternate_start": ALTERNATE_START_OPTIONS,
         "finer_mesh": FINER_MESH_OPTIONS, "cgls_max_iterations": CGLS_MAX_ITER,
         "cgls_residual_squared_tolerance": CGLS_TOLERANCE,
         "weight_rule": report["weighting"]["sigma_t_s"],
         "split_hashes": {name: part["sha256"] for name, part in report["split"].items()}}
    minimum_improved = 2
    if validation_policy != "pinned-15/v1":
        held_count = len(splits["interleaved"]["held_shots"])
        minimum_improved = (2 * held_count + 2) // 3
        report["validation_policy"] = {"name": validation_policy, "held_shot_count": held_count,
                                        "minimum_improved_shots": minimum_improved}
        configuration["validation_policy"] = report["validation_policy"]
    report["configuration_sha256"] = hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()
    report["observations"] = {"sensor_xy_m": survey.sensor_xy_m.tolist(),
                              "shot_geophone_zero_based": survey.shot_geophone.tolist(),
                              "picked_t_s": survey.time_s.tolist(),
                              "sigma_t_assumed_s": sigma.tolist()}
    try:
        report["inverse"] = {}
        for name in ("interleaved", "central_block"):
            report["inverse"][name] = _invert_once(tt, full, survey, splits[name],
                                                    INVERSE_OPTIONS, retain_arrays=True)
        report["sensitivity"] = {
            "alternate_gradient_start": {"options": ALTERNATE_START_OPTIONS,
                                         **_invert_once(tt, full, survey, splits["interleaved"],
                                                        ALTERNATE_START_OPTIONS, retain_arrays=False)},
            "finer_parameter_mesh": {"options": FINER_MESH_OPTIONS,
                                     **_invert_once(tt, full, survey, splits["interleaved"],
                                                    FINER_MESH_OPTIONS, retain_arrays=False)},
            "meaning": "diagnostic perturbations only; never select primary model on held-out picks",
        }
        report["inverse_status"], reason = _field_verdict(report["inverse"], minimum_improved_shots=minimum_improved)
        if reason is not None:
            report["inverse_reason"] = reason
    except (TraveltimeError, RuntimeError, ValueError, TypeError, AssertionError, IndexError) as error:
        report.update(inverse_status="not-converged", inverse_reason=f"pyGIMLi inverse/held-out forward failed: {error}")
    report["wall_seconds"] = round(time.perf_counter() - started, 3)
    return report


def save_local_receipt(report: dict, *, root: Path = ROOT, kind: str = "inverse") -> Path:
    """Install or verify a checksummed, immutable receipt inside ignored data/raw."""
    root = Path(root).resolve()
    folder = root / "data/raw/traveltime"
    if not folder.resolve().is_relative_to((root / "data/raw").resolve()):
        raise TraveltimeError("traveltime result path escapes ignored data/raw")
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / f"koenigsee-m09-{kind}-{report['code_sha256'][:12]}.json"
    checksum_path = folder / f"{output.name}.sha256"
    if output.exists() or checksum_path.exists():
        if not output.is_file() or not checksum_path.is_file() or output.is_symlink() or checksum_path.is_symlink():
            raise TraveltimeError(f"incomplete or symlinked M09 receipt: {output}")
        existing = output.read_bytes()
        if hashlib.sha256(existing).hexdigest() != checksum_path.read_text(encoding="ascii").strip():
            raise TraveltimeError(f"immutable M09 receipt checksum drift: {output}")
        old = json.loads(existing)
        for key in ("schema", "source_sha256", "code_sha256", "qc", "unit_basis",
                    "inverse_status", "inverse_reason", "configuration_sha256", "environment_versions_sha256"):
            if old.get(key) != report.get(key):
                raise TraveltimeError(f"M09 rerun changed {key}: {output}")
        if "inverse" in old and "inverse" in report:
            for name in ("interleaved", "central_block"):
                if old.get("split", {}).get(name, {}).get("sha256") != report.get("split", {}).get(name, {}).get("sha256"):
                    raise TraveltimeError(f"M09 rerun changed {name} whole-shot split: {output}")
                if name in old["inverse"] and name in report["inverse"]:
                    before, now = old["inverse"][name], report["inverse"][name]
                    for key in ("parameter_mesh_sha256", "forward_mesh_sha256"):
                        if before[key] != now[key]:
                            raise TraveltimeError(f"M09 rerun changed {name} {key}: {output}")
                    if before["iterations"] != now["iterations"] or before["stopping_reason"] != now["stopping_reason"]:
                        raise TraveltimeError(f"M09 rerun changed {name} inverse stopping: {output}")
                    if not np.allclose(before["model_cell_center_xy_m"], now["model_cell_center_xy_m"],
                                       rtol=0, atol=1e-8):
                        raise TraveltimeError(f"M09 rerun changed {name} ordered model cells: {output}")
                    if not np.allclose(before["model_velocity_m_s"], now["model_velocity_m_s"],
                                       rtol=REPEAT_VELOCITY_RTOL, atol=REPEAT_VELOCITY_ATOL_M_S):
                        delta = np.max(np.abs(np.asarray(before["model_velocity_m_s"])
                                              - np.asarray(now["model_velocity_m_s"])))
                        raise TraveltimeError(f"M09 rerun changed {name} velocity model "
                                              f"(maximum {delta:.4f} m/s): {output}")
                    if not np.allclose(before["predicted_t_s"], now["predicted_t_s"],
                                       rtol=0, atol=REPEAT_TIME_ATOL_S):
                        delta = np.max(np.abs(np.asarray(before["predicted_t_s"])
                                              - np.asarray(now["predicted_t_s"])))
                        raise TraveltimeError(f"M09 rerun changed {name} forward times beyond tolerance "
                                              f"(maximum {1000 * delta:.4f} ms): {output}")
                    if not math.isclose(before["heldout_rmse_s"], now["heldout_rmse_s"],
                                        rel_tol=0, abs_tol=REPEAT_TIME_ATOL_S):
                        raise TraveltimeError(f"M09 rerun changed {name} held-out RMSE beyond 0.01 ms: {output}")
            old_sensitivity = old.get("sensitivity")
            new_sensitivity = report.get("sensitivity")
            if old_sensitivity is None and new_sensitivity is None and old["inverse_status"] != "passed":
                pass  # An identically failed fit did not reach sensitivity runs.
            elif old_sensitivity is None or new_sensitivity is None:
                raise TraveltimeError(f"M09 rerun lost sensitivity evidence: {output}")
            else:
                for name in ("alternate_gradient_start", "finer_parameter_mesh"):
                    before = old_sensitivity.get(name)
                    now = new_sensitivity.get(name)
                    if before is None or now is None:
                        raise TraveltimeError(f"M09 rerun lost {name} sensitivity evidence: {output}")
                    for key in ("parameter_mesh_sha256", "forward_mesh_sha256", "iterations", "stopping_reason"):
                        if before[key] != now[key]:
                            raise TraveltimeError(f"M09 rerun changed {name} {key}: {output}")
                    if not math.isclose(before["heldout_rmse_s"], now["heldout_rmse_s"],
                                        rel_tol=0, abs_tol=REPEAT_TIME_ATOL_S):
                        raise TraveltimeError(f"M09 rerun changed {name} held-out RMSE beyond 0.01 ms: {output}")
        return output
    payload = (json.dumps(report, indent=2, allow_nan=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    with tempfile.NamedTemporaryFile(prefix=".tt-receipt-", dir=folder, delete=False) as temporary:
        staged = Path(temporary.name)
        temporary.write(payload)
    with tempfile.NamedTemporaryFile(prefix=".tt-hash-", dir=folder, delete=False) as temporary:
        staged_hash = Path(temporary.name)
        temporary.write((digest + "\n").encode("ascii"))
    try:
        os.link(staged, output)
        os.link(staged_hash, checksum_path)
    except FileExistsError as error:
        raise TraveltimeError(f"another M09 run created {output}; rerun to verify") from error
    finally:
        staged.unlink(missing_ok=True)
        staged_hash.unlink(missing_ok=True)
    return output


def run_source(*, root: Path = ROOT, qc_only: bool = False) -> dict:
    """Reverify the ledger source, compute local evidence and retain its receipt."""
    record, raw_path, receipt = acquire_source(SOURCE_ID, root=root)
    if receipt["validation_status"] != "hash-verified":
        raise TraveltimeError("Koenigsee acquisition receipt is not hash-verified")
    report = run(raw_path, source_sha256=record["sha256"], allow_inverse=not qc_only)
    report["source_object_url"] = record["object_url"]
    report["source_acquisition_asset_id"] = receipt["asset_id"]
    report["code_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report["local_receipt_path"] = str(save_local_receipt(report, root=root, kind="qc" if qc_only else "inverse"))
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qc-only", action="store_true", help="Validate source geometry and picks without an inverse")
    args = parser.parse_args(argv)
    try:
        result = run_source(qc_only=args.qc_only)
    except (SourceError, TraveltimeError, OSError) as error:
        print(f"M09 Koenigsee failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({key: result[key] for key in ("source_id", "source_sha256", "inverse_status",
                                                     "local_receipt_path")}, indent=2))
    return 0 if result["inverse_status"] in ("passed", "not-run") else 3


if __name__ == "__main__":
    raise SystemExit(main())
