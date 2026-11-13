"""M03 line geometry, height-QC and blocked interpolation products.

This module does not apply diurnal, IGRF, lag, tie-line levelling, terrain or
regional corrections. It consumes an explicit field map and lineage statement,
keeps the measured values untouched, and does not call an interpolated grid an
inverse model or a provider-equivalent product.
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys
import tempfile

import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import QhullError


MAX_SOURCE_BYTES = 256 * 1024 * 1024
MAX_ROWS = 250_000
MAX_GRID_CELLS = 250_000
MAX_CROSSOVER_SEGMENT_TESTS = 2_000_000
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class MagneticProcessingError(ValueError):
    """Input contract cannot support the declared M03 operation."""


def _strict_json(raw: bytes) -> object:
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise MagneticProcessingError(f"JSON contains duplicate key {key!r}")
            result[key] = value
        return result

    def reject_constant(value):
        raise MagneticProcessingError(f"JSON contains non-finite constant {value}")

    return json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=reject_constant)


@dataclass(frozen=True)
class Observation:
    easting_m: float
    northing_m: float
    value: float
    line_id: str
    line_role: str
    sensor_height_m: float
    sample_order: float


def _finite(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise MagneticProcessingError(f"{field}: boolean is not a physical number")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise MagneticProcessingError(f"{field}: expected a finite number") from error
    if not math.isfinite(result):
        raise MagneticProcessingError(f"{field}: expected a finite number")
    return result


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise MagneticProcessingError(f"{field}: expected nonempty text up to 256 characters")
    return value.strip()


def _parse_request(request: object) -> tuple[dict, dict, list[Observation]]:
    if not isinstance(request, dict) or set(request) != {"schema", "source", "frame", "mapping", "settings", "rows"}:
        raise MagneticProcessingError("request: expected the closed M03 request fields")
    if request["schema"] != "magnetic-flightline-process-request-1":
        raise MagneticProcessingError("schema: unsupported M03 request version")
    source = request["source"]
    source_keys = {"source_id", "sha256", "citation", "rights_decision", "processing_state", "value_unit",
                   "value_quantity", "sensor_height_reference"}
    if not isinstance(source, dict) or set(source) != source_keys:
        raise MagneticProcessingError("source: exact source identity, rights, lineage and value unit are required")
    if not isinstance(source["sha256"], str) or not SHA256.fullmatch(source["sha256"]):
        raise MagneticProcessingError("source.sha256: lowercase SHA-256 of the original bytes is required")
    for field in ("source_id", "citation", "rights_decision", "processing_state", "value_unit",
                  "value_quantity", "sensor_height_reference"):
        _required_text(source[field], f"source.{field}")

    frame = request["frame"]
    if (not isinstance(frame, dict) or set(frame) != {"crs", "coordinates_are_projected", "linear_unit"}
            or frame["coordinates_are_projected"] is not True or frame["linear_unit"] != "m"):
        raise MagneticProcessingError("frame: projected coordinates in metres are required for line geometry")
    _required_text(frame["crs"], "frame.crs")

    mapping = request["mapping"]
    expected_mapping = {"easting", "northing", "value", "line_id", "line_role", "sensor_height_m", "sample_order"}
    if not isinstance(mapping, dict) or set(mapping) != expected_mapping:
        raise MagneticProcessingError("mapping: explicitly map easting, northing, value, line ID, role and sensor height")
    if any(not isinstance(value, str) or not value.strip() for value in mapping.values()):
        raise MagneticProcessingError("mapping: field names must be nonempty strings")
    if len(set(mapping.values())) != len(mapping):
        raise MagneticProcessingError("mapping: source columns must map to distinct physical quantities")

    settings = request["settings"]
    if not isinstance(settings, dict) or set(settings) != {"grid_spacing_m", "holdout_fraction", "seed"}:
        raise MagneticProcessingError("settings: require grid spacing, line holdout fraction and a stable seed")
    spacing = _finite(settings["grid_spacing_m"], "settings.grid_spacing_m")
    fraction = _finite(settings["holdout_fraction"], "settings.holdout_fraction")
    if not 0 < spacing <= 100_000:
        raise MagneticProcessingError("settings.grid_spacing_m: expected a positive spacing no greater than 100 km")
    if not 0.05 <= fraction <= 0.5:
        raise MagneticProcessingError("settings.holdout_fraction: expected a fraction in [0.05, 0.5]")
    seed = _required_text(settings["seed"], "settings.seed")
    if len(seed) > 128:
        raise MagneticProcessingError("settings.seed: maximum length is 128 characters")

    rows = request["rows"]
    if not isinstance(rows, list) or not 12 <= len(rows) <= MAX_ROWS:
        raise MagneticProcessingError(f"rows: expected 12 to {MAX_ROWS} observations")
    parsed: list[Observation] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != set(mapping.values()):
            raise MagneticProcessingError(f"rows[{index}]: row columns do not exactly match the explicit mapping")
        role = row[mapping["line_role"]]
        if role not in ("flight", "tie"):
            raise MagneticProcessingError(f"rows[{index}].{mapping['line_role']}: expected flight or tie")
        easting = _finite(row[mapping["easting"]], f"rows[{index}].easting")
        northing = _finite(row[mapping["northing"]], f"rows[{index}].northing")
        value = _finite(row[mapping["value"]], f"rows[{index}].value")
        height = _finite(row[mapping["sensor_height_m"]], f"rows[{index}].sensor_height_m")
        order = _finite(row[mapping["sample_order"]], f"rows[{index}].sample_order")
        if max(abs(easting), abs(northing)) > 1e8:
            raise MagneticProcessingError(f"rows[{index}]: projected coordinates exceed the 100,000 km safety bound")
        if abs(value) > 1e15 or abs(height) > 1e6:
            raise MagneticProcessingError(f"rows[{index}]: field value or sensor height exceeds the numerical safety bound")
        parsed.append(Observation(
            easting_m=easting,
            northing_m=northing,
            value=value,
            line_id=_required_text(row[mapping["line_id"]], f"rows[{index}].line_id"),
            line_role=role,
            sensor_height_m=height,
            sample_order=order,
        ))
    orders: dict[tuple[str, str], set[float]] = {}
    for point in parsed:
        key = (point.line_role, point.line_id)
        if point.sample_order in orders.setdefault(key, set()):
            raise MagneticProcessingError(f"line {point.line_id!r} contains duplicate sample-order values")
        orders[key].add(point.sample_order)
    return source, {**frame, **settings}, parsed


def read_csv(path: Path, *, field_map: dict[str, str], source_metadata: dict,
             frame: dict, settings: dict) -> dict:
    """Read a bounded CSV with exact user-specified columns; infer no schema."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise MagneticProcessingError("CSV input must be a regular non-symlink file")
    size = path.stat().st_size
    if size <= 0 or size > MAX_SOURCE_BYTES:
        raise MagneticProcessingError(f"CSV size must be between 1 byte and {MAX_SOURCE_BYTES} bytes")
    digest = sha256(path.read_bytes()).hexdigest()
    names = set(field_map.values()) if isinstance(field_map, dict) else set()
    if not names or not all(isinstance(name, str) and name for name in names):
        raise MagneticProcessingError("field_map must explicitly name source CSV columns")
    rows = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise MagneticProcessingError("CSV header is missing or contains duplicate column names")
            missing = names - set(reader.fieldnames)
            if missing:
                raise MagneticProcessingError(f"CSV is missing explicitly mapped columns: {sorted(missing)}")
            for row in reader:
                rows.append({name: row[name] for name in names})
                if len(rows) > MAX_ROWS:
                    raise MagneticProcessingError(f"CSV exceeds the {MAX_ROWS}-row online processing bound")
    except (OSError, UnicodeError, csv.Error) as error:
        raise MagneticProcessingError(f"cannot read source CSV: {error}") from error
    request = {"schema": "magnetic-flightline-process-request-1", "source": {**source_metadata, "sha256": digest},
               "frame": frame, "mapping": field_map, "settings": settings, "rows": rows}
    return request


def _line_geometry(points: list[Observation]) -> dict:
    lines: dict[tuple[str, str], list[Observation]] = {}
    for point in points:
        lines.setdefault((point.line_role, point.line_id), []).append(point)
    summaries = []
    centers = []
    for (role, line_id), values in sorted(lines.items()):
        xy = np.asarray([(point.easting_m, point.northing_m) for point in values], dtype=np.float64)
        heights = np.asarray([point.sensor_height_m for point in values], dtype=np.float64)
        median = float(np.median(heights))
        mad = float(np.median(np.abs(heights - median)))
        threshold = max(6.0 * 1.4826 * mad, 1e-9)
        outliers = [i for i, height in enumerate(heights) if abs(float(height) - median) > threshold]
        span = np.ptp(xy, axis=0)
        centers.append((role, line_id, np.mean(xy, axis=0)))
        summaries.append({
            "line_id": line_id, "role": role, "sample_count": len(values),
            "easting_span_m": float(span[0]), "northing_span_m": float(span[1]),
            "sensor_height_m": {"minimum": float(np.min(heights)), "median": median,
                                 "maximum": float(np.max(heights)), "mad": mad,
                                 "qc_outlier_rows": outliers},
            "coordinate_extent_m": {"easting": [float(np.min(xy[:, 0])), float(np.max(xy[:, 0]))],
                                     "northing": [float(np.min(xy[:, 1])), float(np.max(xy[:, 1]))]},
        })
    flight_centers = np.asarray([center for role, _, center in centers if role == "flight"], dtype=np.float64)
    if len(flight_centers) < 4:
        raise MagneticProcessingError("at least four distinct flight lines are required for a blocked-line holdout")
    centered = flight_centers - flight_centers.mean(axis=0)
    covariance = centered.T @ centered
    eig_values, eig_vectors = np.linalg.eigh(covariance)
    if eig_values[-1] <= 0 or eig_values[0] / eig_values[-1] > 0.5:
        raise MagneticProcessingError("flight-line centers do not define a distinguishable survey-line direction")
    normal = eig_vectors[:, -1]
    projections = sorted(float(center @ normal) for center in flight_centers)
    separations = np.diff(projections)
    positive = separations[separations > 1e-6]
    spacing = float(np.median(positive)) if len(positive) else None
    coincident: dict[tuple[float, float], list[Observation]] = {}
    for point in points:
        coincident.setdefault((point.easting_m, point.northing_m), []).append(point)
    crossover_groups = [group for group in coincident.values()
                        if len({point.line_id for point in group}) > 1]
    crossover_deltas = [max(point.value for point in group) - min(point.value for point in group)
                        for group in crossover_groups]
    return {"lines": summaries, "flight_line_count": len(flight_centers),
            "tie_line_count": sum(role == "tie" for role, _, _ in centers),
            "exact_collocation_qc": {"cross_line_groups": len(crossover_groups),
                                     "maximum_value_difference": max(crossover_deltas) if crossover_deltas else None,
                                     "interpretation": "exactly coincident mapped samples only; no near-crossing interpolation"},
            "estimated_flight_line_spacing_m": spacing,
            "flight_line_normal_xy": [float(value) for value in normal]}


def _line_segments(points: list[Observation]) -> dict[tuple[str, str], list[tuple[np.ndarray, np.ndarray, float, float]]]:
    """Build acquisition-order segments for each flight or tie line."""
    grouped: dict[tuple[str, str], list[Observation]] = {}
    for point in points:
        grouped.setdefault((point.line_role, point.line_id), []).append(point)
    result = {}
    for key, observations in grouped.items():
        observations.sort(key=lambda point: point.sample_order)
        segments = []
        for left, right in zip(observations, observations[1:]):
            a = np.asarray([left.easting_m, left.northing_m], dtype=np.float64)
            b = np.asarray([right.easting_m, right.northing_m], dtype=np.float64)
            if not np.array_equal(a, b):
                segments.append((a, b, left.value, right.value))
        result[key] = segments
    return result


def _segment_intersection(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray):
    """Return intersection coordinates and segment fractions; collinear overlap is undefined."""
    r, s = b - a, d - c
    cross = lambda u, v: float(u[0] * v[1] - u[1] * v[0])
    denominator = cross(r, s)
    scale = max(float(np.linalg.norm(r) * np.linalg.norm(s)), 1.0)
    if abs(denominator) <= 1e-12 * scale:
        return None
    delta = c - a
    t, u = cross(delta, s) / denominator, cross(delta, r) / denominator
    tolerance = 1e-10
    if -tolerance <= t <= 1 + tolerance and -tolerance <= u <= 1 + tolerance:
        t, u = min(1.0, max(0.0, t)), min(1.0, max(0.0, u))
        # Snap endpoint hits to the original sample coordinate so adjacent
        # segments deduplicate exactly, without rounding distinct nearby hits.
        xy = a if t == 0.0 else b if t == 1.0 else c if u == 0.0 else d if u == 1.0 else a + t * r
        return xy, t, u
    return None


def _crossover_interpolation(points: list[Observation]) -> dict:
    """Compute line-to-line residual diagnostics at geometrical segment crossings."""
    lines = _line_segments(points)
    ordered = sorted(lines)
    pairs = [(left, right) for i, left in enumerate(ordered) for right in ordered[i + 1:]
             if left[0] != right[0]]
    tests = sum(len(lines[left]) * len(lines[right]) for left, right in pairs)
    if tests > MAX_CROSSOVER_SEGMENT_TESTS:
        raise MagneticProcessingError(
            f"crossover QC requires {tests} segment comparisons; bound is {MAX_CROSSOVER_SEGMENT_TESTS}"
        )
    crossings = {}
    for left_key, right_key in pairs:
        for a, b, va, vb in lines[left_key]:
            for c, d, vc, vd in lines[right_key]:
                if (max(a[0], b[0]) < min(c[0], d[0]) or max(c[0], d[0]) < min(a[0], b[0])
                        or max(a[1], b[1]) < min(c[1], d[1]) or max(c[1], d[1]) < min(a[1], b[1])):
                    continue
                hit = _segment_intersection(a, b, c, d)
                if hit is None:
                    continue
                xy, t, u = hit
                key = (left_key, right_key, float(xy[0]), float(xy[1]))
                crossings.setdefault(key, (xy, va + t * (vb - va), vc + u * (vd - vc)))
    differences = [left - right for _, left, right in crossings.values()]
    return {
        "intersection_count": len(crossings), "segment_pair_tests": tests,
        "mean_signed_difference": float(np.mean(differences)) if differences else None,
        "mae": float(np.mean(np.abs(differences))) if differences else None,
        "rmse": float(np.sqrt(np.mean(np.square(differences)))) if differences else None,
        "crossings": [{"line_a": key[0][1], "role_a": key[0][0], "line_b": key[1][1],
                       "role_b": key[1][0], "easting_m": float(xy[0]), "northing_m": float(xy[1]),
                       "value_a": float(left), "value_b": float(right),
                       "difference_a_minus_b": float(left - right)}
                      for key, (xy, left, right) in sorted(crossings.items())],
        "interpretation": "segment-linear crossover QC only; no leveling or correction applied",
    }


def process(request: dict, *, source_hash_verified: bool = False) -> dict:
    """Create measured-data QC, whole-line holdout, and a supported-only grid."""
    source, config, points = _parse_request(request)
    coordinates = np.asarray([(p.easting_m, p.northing_m) for p in points], dtype=np.float64)
    values = np.asarray([p.value for p in points], dtype=np.float64)
    geometry = _line_geometry(points)
    geometry["crossover_interpolation_qc"] = _crossover_interpolation(points)
    line_sums: dict[str, list[float]] = {}
    for point in points:
        if point.line_role == "flight":
            total = line_sums.setdefault(point.line_id, [0.0, 0.0, 0.0])
            total[0] += point.easting_m
            total[1] += point.northing_m
            total[2] += 1
    line_centers = {line: np.asarray([total[0] / total[2], total[1] / total[2]])
                    for line, total in line_sums.items()}
    normal = np.asarray(geometry["flight_line_normal_xy"], dtype=np.float64)
    ordered_ids = sorted(line_centers, key=lambda line: (float(line_centers[line] @ normal), line))
    holdout_n = min(len(ordered_ids) - 2,
                    max(1, math.ceil(len(ordered_ids) * config["holdout_fraction"])))
    candidates = []
    for start in range(len(ordered_ids) - holdout_n + 1):
        block = ordered_ids[start:start + holdout_n]
        interior_count = max(0, min(start + holdout_n - 1, len(ordered_ids) - 2) - max(start, 1) + 1)
        candidates.append((interior_count, block))
    best_interior = max(count for count, _ in candidates)
    interior_blocks = [block for count, block in candidates if count == best_interior]
    heldout_ids = set(min(interior_blocks,
                          key=lambda block: sha256((config["seed"] + "\0" + "\0".join(block)).encode("utf-8")).hexdigest()))
    train_rows = [i for i, point in enumerate(points) if point.line_role == "flight" and point.line_id not in heldout_ids]
    heldout_rows = [i for i, point in enumerate(points) if point.line_role == "flight" and point.line_id in heldout_ids]
    train_coordinates = coordinates[train_rows]
    train_values = values[train_rows]
    if len(train_rows) < 12 or np.linalg.matrix_rank(train_coordinates - train_coordinates.mean(axis=0)) < 2:
        raise MagneticProcessingError("training flight-line samples are insufficient or collinear")
    if len({tuple(coordinates[i]) for i in train_rows}) != len(train_rows):
        raise MagneticProcessingError("duplicate training coordinates cannot be silently averaged")

    spacing = config["grid_spacing_m"]
    xmin, ymin = np.min(train_coordinates, axis=0)
    xmax, ymax = np.max(train_coordinates, axis=0)
    ratio_x = (xmax - xmin) / spacing
    ratio_y = (ymax - ymin) / spacing
    if not math.isfinite(ratio_x) or not math.isfinite(ratio_y) or max(ratio_x, ratio_y) > MAX_GRID_CELLS:
        raise MagneticProcessingError("grid spacing and survey extent exceed the bounded grid capacity")
    nx = int(math.floor(ratio_x)) + 1
    ny = int(math.floor(ratio_y)) + 1
    if nx < 2 or ny < 2 or nx * ny > MAX_GRID_CELLS:
        raise MagneticProcessingError(f"grid is {nx}x{ny}; require >=2 per axis and <= {MAX_GRID_CELLS} cells")
    x_axis = xmin + np.arange(nx, dtype=np.float64) * spacing
    y_axis = ymin + np.arange(ny, dtype=np.float64) * spacing
    xx, yy = np.meshgrid(x_axis, y_axis, indexing="xy")
    try:
        grid_interp = LinearNDInterpolator(train_coordinates, train_values, fill_value=np.nan)
        grid = np.asarray(grid_interp(xx, yy), dtype=np.float64)
    except QhullError as error:
        raise MagneticProcessingError(f"Delaunay triangulation failed for the admitted flight geometry: {error}") from error
    except MemoryError as error:
        raise MagneticProcessingError("interpolation exceeded available memory; reduce the source subset and grid extent") from error
    support = np.isfinite(grid)

    heldout_xy = coordinates[heldout_rows]
    heldout_observed = values[heldout_rows]
    try:
        predicted = np.asarray(grid_interp(heldout_xy), dtype=np.float64)
    except MemoryError as error:
        raise MagneticProcessingError("held-out interpolation exceeded available memory") from error
    valid = np.isfinite(predicted)
    residual = predicted[valid] - heldout_observed[valid]
    score = {
        "heldout_line_ids": sorted(heldout_ids), "heldout_row_count": len(heldout_rows),
        "supported_heldout_row_count": int(valid.sum()),
        "coverage_fraction": float(valid.mean()) if len(valid) else 0.0,
        "mae": float(np.mean(np.abs(residual))) if len(residual) else None,
        "rmse": float(np.sqrt(np.mean(residual**2))) if len(residual) else None,
        "interpretation": "spatial interpolation on withheld whole flight lines; not a subsurface inverse",
    }
    return {
        "schema": "magnetic-flightline-process-result-1",
        "claims": {"source_hash_recomputed_from_original_bytes": source_hash_verified, "corrections_applied": [],
                   "provider_grid_comparison": False, "inverse_model": False, "scientific_release_accepted": False},
        "source": dict(source),
        "configuration": {"frame": {"crs": config["crs"], "linear_unit": "m"},
                          "value_quantity": source["value_quantity"], "value_unit": source["value_unit"],
                          "sensor_height_reference": source["sensor_height_reference"], "grid_spacing_m": spacing,
                          "holdout_fraction": config["holdout_fraction"], "seed": config["seed"],
                          "interpolation": "piecewise_linear_delaunay"},
        "geometry_qc": geometry,
        "split": {"unit": "contiguous interior block of entire flight lines",
                  "line_order_by": "survey-center projection onto estimated flight-line normal",
                  "fit_line_ids": sorted(set(ordered_ids) - heldout_ids),
                  "holdout_line_ids": sorted(heldout_ids), "tie_lines_used_for_fit": False},
        "heldout_interpolation": score,
        "grid": {"x_easting_m": x_axis.tolist(), "y_northing_m": y_axis.tolist(),
                 "shape_yx": [ny, nx], "values": np.where(support, grid, 0.0).tolist(),
                 "support_mask": support.tolist(), "unsupported_value_encoding": "zero plus false support mask"},
        "limitations": ["No source correction or tie-line levelling was performed.",
                        "Grid values outside the training convex hull are masked as unsupported.",
                        "Tie-line observations are retained for geometry/height QC and are not used to fit the grid.",
                        "A provider grid comparison is unavailable until the matching source product is acquired.",
                        "Held-out interpolation accuracy is not subsurface-model accuracy."],
    }


def _write_new_file(path: Path, data: bytes) -> None:
    """Stage and atomically install a new result without replacing a peer file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, staged_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    staged = Path(staged_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(staged, path)
        except FileExistsError as error:
            raise MagneticProcessingError("refusing to overwrite an existing result") from error
    finally:
        try:
            staged.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", type=Path, help="closed JSON request; its raw-source hash is a declaration")
    source_group.add_argument("--csv", type=Path, help="raw CSV to hash and map using --config")
    parser.add_argument("--config", type=Path, help="JSON with exact source, frame, mapping and settings fields (required with --csv)")
    parser.add_argument("--output", type=Path, required=True, help="new result JSON path")
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise MagneticProcessingError("refusing to overwrite an existing result")
        if args.csv is not None:
            if args.config is None:
                raise MagneticProcessingError("--config is required with --csv")
            config_raw = args.config.read_bytes()
            if len(config_raw) > 1024 * 1024:
                raise MagneticProcessingError("CSV mapping config exceeds the 1 MiB bound")
            config = _strict_json(config_raw)
            if not isinstance(config, dict) or set(config) != {"source", "frame", "mapping", "settings"}:
                raise MagneticProcessingError("CSV config requires exactly source, frame, mapping and settings")
            request = read_csv(args.csv, field_map=config["mapping"], source_metadata=config["source"],
                               frame=config["frame"], settings=config["settings"])
        else:
            if args.config is not None:
                raise MagneticProcessingError("--config is only valid with --csv")
            raw = args.input.read_bytes()
            if len(raw) > MAX_SOURCE_BYTES:
                raise MagneticProcessingError("request exceeds the 256 MiB input bound")
            request = _strict_json(raw)
        result = process(request, source_hash_verified=args.csv is not None)
        encoded = json.dumps(result, allow_nan=False, separators=(",", ":")).encode("utf-8")
        _write_new_file(args.output, encoded)
    except (OSError, UnicodeError, json.JSONDecodeError, MagneticProcessingError, ValueError) as error:
        print(f"M03 processing failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"output": str(args.output), "bytes": len(encoded), "sha256": sha256(encoded).hexdigest()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
