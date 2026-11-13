"""Process the pinned USGS Amargosa aeromagnetic lines through the M03 contract.

The released levelled-anomaly channel already includes provider correction and
flight/tie crossover levelling. This adapter never reapplies those operations,
does not infer a magnetic source, and does not produce a subsurface inversion.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from pyproj import Transformer

from magnetic_processing import MagneticProcessingError, process, _write_new_file
from sources import SourceError, acquire_source, local_data_root


SOURCE_ID = "usgs-amargosa-aeromagnetic"
SOURCE_CRS = "EPSG:4267"
PROJECTED_CRS = "EPSG:26711"
MAX_EXPANDED_BYTES = 100_000_000
MAX_RECORDS = 500_000
FIXED_WIDTH = 71
DEFAULT_BOUNDS = (538_462.0, 543_462.0, 4_067_437.0, 4_072_437.0)
DEFAULT_FLIGHT_CLUSTER_M = 200.0
DEFAULT_TIE_CLUSTER_M = 500.0
DEFAULT_ORIENTATION_LIMIT_DEG = 30.0


class AmargosaError(ValueError):
    """Pinned source or selected survey cannot satisfy this adapter contract."""


def _digest(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(128 * 1024):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _number(raw: bytes, field: str, row_number: int) -> float:
    try:
        value = float(raw.decode("ascii").strip())
    except (UnicodeDecodeError, ValueError) as error:
        raise AmargosaError(f"row {row_number}: {field} is not an ASCII number") from error
    if not math.isfinite(value):
        raise AmargosaError(f"row {row_number}: {field} must be finite")
    return value


def _read_archive(path: Path, record: dict) -> dict[str, np.ndarray | list[str] | str]:
    if path.is_symlink() or not path.is_file():
        raise AmargosaError("input must be the regular pinned gzip source object")
    size, digest = _digest(path)
    if size != record["expected_bytes"] or digest != record["sha256"]:
        raise AmargosaError("compressed source byte count or SHA-256 differs from the reviewed ledger pin")

    line_ids: list[str] = []
    longitude: list[float] = []
    latitude: list[float] = []
    radar_height: list[float] = []
    barometric_height: list[float] = []
    uncorrected: list[float] = []
    total_anomaly: list[float] = []
    levelled_anomaly: list[float] = []
    expanded_bytes = 0
    try:
        with gzip.open(path, "rb") as stream:
            for row_number, raw in enumerate(stream, start=1):
                expanded_bytes += len(raw)
                if expanded_bytes > MAX_EXPANDED_BYTES:
                    raise AmargosaError(f"expanded data exceeds {MAX_EXPANDED_BYTES} bytes")
                if row_number > MAX_RECORDS:
                    raise AmargosaError(f"record count exceeds {MAX_RECORDS}")
                line = raw.rstrip(b"\r\n")
                if len(line) != FIXED_WIDTH:
                    raise AmargosaError(f"row {row_number}: expected {FIXED_WIDTH} fixed-width bytes, got {len(line)}")
                try:
                    line_id = line[0:8].decode("ascii").strip()
                except UnicodeDecodeError as error:
                    raise AmargosaError(f"row {row_number}: line identifier is not ASCII") from error
                if not line_id:
                    raise AmargosaError(f"row {row_number}: source line identifier is empty")
                line_ids.append(line_id)
                longitude.append(_number(line[8:20], "longitude_deg", row_number))
                latitude.append(_number(line[20:30], "latitude_deg", row_number))
                radar_height.append(_number(line[30:37], "radar_height_m", row_number))
                barometric_height.append(_number(line[37:44], "barometric_height_m", row_number))
                uncorrected.append(_number(line[44:53], "uncorrected_field_nT", row_number))
                total_anomaly.append(_number(line[53:62], "total_field_anomaly_nT", row_number))
                levelled_anomaly.append(_number(line[62:71], "levelled_anomaly_nT", row_number))
    except (OSError, EOFError) as error:
        raise AmargosaError(f"source gzip stream is invalid: {error}") from error
    if (len(line_ids) != record["record_count"] or expanded_bytes != record["expanded_bytes"]
            or not line_ids):
        raise AmargosaError("expanded byte count or fixed-width record count differs from the reviewed ledger pin")
    lon = np.asarray(longitude, dtype=np.float64)
    lat = np.asarray(latitude, dtype=np.float64)
    if np.any((lon < -180) | (lon > 180)) or np.any((lat < -90) | (lat > 90)):
        raise AmargosaError("geographic coordinates fall outside longitude/latitude bounds")
    transformer = Transformer.from_crs(SOURCE_CRS, PROJECTED_CRS, always_xy=True)
    easting, northing = transformer.transform(lon, lat, errcheck=True)
    easting = np.asarray(easting, dtype=np.float64)
    northing = np.asarray(northing, dtype=np.float64)
    if not np.isfinite(easting).all() or not np.isfinite(northing).all():
        raise AmargosaError("NAD27 transformation returned nonfinite projected coordinates")
    return {
        "sha256": digest,
        "line_ids": line_ids,
        "easting_m": easting,
        "northing_m": northing,
        "radar_height_m": np.asarray(radar_height, dtype=np.float64),
        "barometric_height_m": np.asarray(barometric_height, dtype=np.float64),
        "uncorrected_field_nT": np.asarray(uncorrected, dtype=np.float64),
        "total_field_anomaly_nT": np.asarray(total_anomaly, dtype=np.float64),
        "levelled_anomaly_nT": np.asarray(levelled_anomaly, dtype=np.float64),
        "source_record_count": len(line_ids),
        "expanded_bytes": expanded_bytes,
    }


def read_source(path: Path | str, record: dict) -> dict[str, np.ndarray | list[str] | str]:
    """Read and verify the pinned fixed-width Amargosa archive without altering channels."""
    return _read_archive(Path(path), record)


def _segment_direction(xy: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    if len(xy) < 2:
        raise AmargosaError("a source segment with fewer than two in-window measurements cannot define a track")
    center = xy.mean(axis=0)
    centered = xy - center
    covariance = centered.T @ centered
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    axis = eigenvectors[:, int(np.argmax(eigenvalues))]
    if np.linalg.norm(centered @ axis) <= 1e-6:
        raise AmargosaError("source segment has no resolvable along-track extent")
    # Canonical sign makes sample order stable across LAPACK eigenvector signs.
    if (abs(axis[0]) >= abs(axis[1]) and axis[0] < 0) or (abs(axis[1]) > abs(axis[0]) and axis[1] < 0):
        axis = -axis
    angle = math.degrees(math.atan2(abs(float(axis[1])), abs(float(axis[0]))))
    return angle, center, axis


def _cluster_tracks(segments: list[dict], *, tolerance_m: float, role: str) -> list[list[dict]]:
    if not math.isfinite(tolerance_m) or tolerance_m <= 0:
        raise AmargosaError(f"{role} cross-track cluster tolerance must be positive and finite")
    coordinate = "northing_m" if role == "flight" else "easting_m"
    ordered = sorted(segments, key=lambda item: (item["center"][1 if role == "flight" else 0], item["line_id"]))
    groups: list[list[dict]] = []
    for segment in ordered:
        position = float(segment["center"][1 if role == "flight" else 0])
        if not groups:
            groups.append([segment])
            continue
        first = float(groups[-1][0]["center"][1 if role == "flight" else 0])
        if position - first <= tolerance_m:
            groups[-1].append(segment)
        else:
            groups.append([segment])
    for group in groups:
        center = float(np.median([float(item["center"][1 if role == "flight" else 0]) for item in group]))
        for item in group:
            item["track_coordinate_m"] = center
            item["cross_track_axis"] = coordinate
    return groups


def select_tracks(data: dict, *, bounds: tuple[float, float, float, float] = DEFAULT_BOUNDS,
                  flight_cluster_m: float = DEFAULT_FLIGHT_CLUSTER_M,
                  tie_cluster_m: float = DEFAULT_TIE_CLUSTER_M,
                  orientation_limit_deg: float = DEFAULT_ORIENTATION_LIMIT_DEG) -> tuple[list[dict], dict]:
    if len(bounds) != 4 or not all(math.isfinite(float(value)) for value in bounds):
        raise AmargosaError("bounds must be four finite projected coordinates")
    xmin, xmax, ymin, ymax = map(float, bounds)
    if not xmin < xmax or not ymin < ymax:
        raise AmargosaError("projected bounds must have positive width and height")
    if not 0 < orientation_limit_deg < 45:
        raise AmargosaError("orientation limit must be strictly between 0 and 45 degrees")
    x, y = data["easting_m"], data["northing_m"]
    inside = (x >= xmin) & (x < xmax) & (y >= ymin) & (y < ymax)
    selected_indices = np.flatnonzero(inside)
    if len(selected_indices) > 250_000:
        raise AmargosaError("selected ROI exceeds the M03 row bound")
    source_lines = data["line_ids"]
    segments = []
    for line_id in sorted({source_lines[int(index)] for index in selected_indices}):
        indices = np.asarray([index for index in selected_indices if source_lines[int(index)] == line_id], dtype=np.int64)
        xy = np.column_stack((x[indices], y[indices]))
        angle, center, axis = _segment_direction(xy)
        if angle <= orientation_limit_deg:
            role = "flight"
        elif angle >= 90.0 - orientation_limit_deg:
            role = "tie"
        else:
            continue
        segments.append({"line_id": line_id, "indices": indices, "xy": xy, "center": center,
                         "axis": axis, "angle_deg": angle, "role": role})
    flight = _cluster_tracks([item for item in segments if item["role"] == "flight"],
                             tolerance_m=flight_cluster_m, role="flight")
    ties = _cluster_tracks([item for item in segments if item["role"] == "tie"],
                           tolerance_m=tie_cluster_m, role="tie")
    if len(flight) < 4:
        raise AmargosaError(f"ROI yields {len(flight)} distinct flight tracks; M03 needs at least four")

    chosen: list[dict] = []
    track_manifest = []
    for role, groups in (("flight", flight), ("tie", ties)):
        groups = sorted(groups, key=lambda group: (group[0]["track_coordinate_m"], group[0]["line_id"]))
        prefix = "F" if role == "flight" else "T"
        for track_number, group in enumerate(groups, start=1):
            representative = sorted(group, key=lambda item: (-len(item["indices"]), item["line_id"]))[0]
            indices = representative["indices"]
            xy = representative["xy"]
            along = (xy - representative["center"]) @ representative["axis"]
            order = np.lexsort((indices, along))
            track_id = f"{prefix}{track_number:03d}"
            chosen.extend({
                "E": float(data["easting_m"][int(indices[pos])]),
                "N": float(data["northing_m"][int(indices[pos])]),
                "anomaly_nT": float(data["levelled_anomaly_nT"][int(indices[pos])]),
                "track_id": track_id,
                "role": role,
                "radar_height_m": float(data["radar_height_m"][int(indices[pos])]),
                "sample_order": float(position),
            } for position, pos in enumerate(order))
            track_manifest.append({
                "track_id": track_id,
                "role": role,
                "cross_track_coordinate_m": representative["track_coordinate_m"],
                "cross_track_axis": representative["cross_track_axis"],
                "representative_source_line_id": representative["line_id"],
                "representative_sample_count": int(len(indices)),
                "source_segment_ids_in_cluster": sorted(item["line_id"] for item in group),
                "discarded_segment_ids": sorted(item["line_id"] for item in group if item is not representative),
                "representative_orientation_deg": representative["angle_deg"],
            })
    chosen.sort(key=lambda row: (row["role"], row["track_id"], row["sample_order"]))
    manifest = {
        "bounds_projected_m_half_open": [xmin, xmax, ymin, ymax],
        "roi_source_record_count": int(len(selected_indices)),
        "orientation_limit_deg": float(orientation_limit_deg),
        "flight_cluster_tolerance_m": float(flight_cluster_m),
        "tie_cluster_tolerance_m": float(tie_cluster_m),
        "ambiguous_or_oblique_segment_count": int(len({source_lines[int(index)] for index in selected_indices}) - len(segments)),
        "track_count": {"flight": len(flight), "tie": len(ties)},
        "tracks": track_manifest,
        "selected_row_count": len(chosen),
        "selected_channel": "levelled anomaly, fixed-width columns 63-71; nT",
        "sensor_height": "radar height, metres above terrain per source report",
        "limitations": [
            "USGS provider processing already removed diurnal and IGRF fields and applied navigation and crossover levelling.",
            "The provider-levelled channel is used as published; no provider corrections are repeated.",
            "One longest source segment represents each cross-track cluster; omitted segment IDs remain listed.",
            "The ROI interpolation and blocked-line score are local processing diagnostics, not subsurface recovery or independent-site validation.",
        ],
    }
    return chosen, manifest


def run(data_root: Path | str, *, bounds: tuple[float, float, float, float] = DEFAULT_BOUNDS,
        flight_cluster_m: float = DEFAULT_FLIGHT_CLUSTER_M,
        tie_cluster_m: float = DEFAULT_TIE_CLUSTER_M,
        orientation_limit_deg: float = DEFAULT_ORIENTATION_LIMIT_DEG,
        grid_spacing_m: float = 100.0, holdout_fraction: float = 0.2,
        seed: str = "amargosa-m03-v1") -> dict:
    root = local_data_root(Path(data_root))
    record, source_path, receipt = acquire_source(SOURCE_ID, root=root)
    archive = read_source(source_path, record)
    rows, selection = select_tracks(archive, bounds=bounds, flight_cluster_m=flight_cluster_m,
                                    tie_cluster_m=tie_cluster_m,
                                    orientation_limit_deg=orientation_limit_deg)
    request = {
        "schema": "magnetic-flightline-process-request-1",
        "source": {
            "source_id": SOURCE_ID,
            "sha256": archive["sha256"],
            "citation": record["citation"],
            "rights_decision": record["rights_decision"],
            "processing_state": "USGS provider-processed levelled total-field anomaly; original corrections retained, none reapplied here",
            "value_unit": "nT",
            "value_quantity": "levelled total-field anomaly",
            "sensor_height_reference": "radar height above terrain as reported by USGS",
        },
        "frame": {"crs": f"{PROJECTED_CRS} (NAD27 / UTM zone 11N)",
                  "coordinates_are_projected": True, "linear_unit": "m"},
        "mapping": {"easting": "E", "northing": "N", "value": "anomaly_nT", "line_id": "track_id",
                    "line_role": "role", "sensor_height_m": "radar_height_m", "sample_order": "sample_order"},
        "settings": {"grid_spacing_m": grid_spacing_m, "holdout_fraction": holdout_fraction, "seed": seed},
        "rows": rows,
    }
    result = process(request, source_hash_verified=True)
    result["source_selection"] = selection
    result["source_acquisition_receipt"] = {key: receipt[key] for key in (
        "source_id", "asset_id", "bytes", "sha256", "storage_key", "rights_decision", "citation",
        "acquisition_method", "validation_status")}
    return result


def sensitivity_matrix(data_root: Path | str) -> list[dict]:
    """Run predeclared grid, holdout and orientation perturbations without selecting a winner."""
    experiments = []
    for spacing in (50.0, 100.0, 200.0):
        result = run(data_root, grid_spacing_m=spacing, holdout_fraction=0.2,
                     orientation_limit_deg=30.0)
        experiments.append({
            "factor": "grid_spacing_m", "value": spacing,
            "grid_shape_yx": result["grid"]["shape_yx"],
            "supported_cells": sum(map(sum, result["grid"]["support_mask"])),
            "heldout_rows": result["heldout_interpolation"]["heldout_row_count"],
            "heldout_rmse_nT": result["heldout_interpolation"]["rmse"],
        })
    for fraction in (0.1, 0.2, 0.3):
        result = run(data_root, grid_spacing_m=100.0, holdout_fraction=fraction,
                     orientation_limit_deg=30.0)
        experiments.append({
            "factor": "holdout_fraction", "value": fraction,
            "grid_shape_yx": result["grid"]["shape_yx"],
            "supported_cells": sum(map(sum, result["grid"]["support_mask"])),
            "heldout_rows": result["heldout_interpolation"]["heldout_row_count"],
            "heldout_rmse_nT": result["heldout_interpolation"]["rmse"],
        })
    for angle in (20.0, 30.0, 40.0):
        result = run(data_root, grid_spacing_m=100.0, holdout_fraction=0.2,
                     orientation_limit_deg=angle)
        experiments.append({
            "factor": "orientation_limit_deg", "value": angle,
            "track_count": result["source_selection"]["track_count"],
            "selected_rows": result["source_selection"]["selected_row_count"],
            "heldout_rows": result["heldout_interpolation"]["heldout_row_count"],
            "heldout_rmse_nT": result["heldout_interpolation"]["rmse"],
        })
    return experiments


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, help="external absolute data root; defaults to GEOPHYSICS_LOCAL_DATA_ROOT")
    parser.add_argument("--output", type=Path, required=True, help="new result receipt path; existing files are never overwritten")
    parser.add_argument("--bounds", type=float, nargs=4, metavar=("XMIN", "XMAX", "YMIN", "YMAX"), default=DEFAULT_BOUNDS)
    parser.add_argument("--flight-cluster-m", type=float, default=DEFAULT_FLIGHT_CLUSTER_M)
    parser.add_argument("--tie-cluster-m", type=float, default=DEFAULT_TIE_CLUSTER_M)
    parser.add_argument("--orientation-limit-deg", type=float, default=DEFAULT_ORIENTATION_LIMIT_DEG)
    parser.add_argument("--grid-spacing-m", type=float, default=100.0)
    parser.add_argument("--holdout-fraction", type=float, default=0.2)
    parser.add_argument("--seed", default="amargosa-m03-v1")
    args = parser.parse_args(argv)
    try:
        root = local_data_root(args.data_root)
        output = args.output.resolve()
        if output.is_relative_to(root) is False:
            raise AmargosaError("result must be written under the external data root")
        if output.exists() or output.is_symlink():
            raise AmargosaError("refusing to overwrite an existing result")
        result = run(root, bounds=tuple(args.bounds), flight_cluster_m=args.flight_cluster_m,
                     tie_cluster_m=args.tie_cluster_m, orientation_limit_deg=args.orientation_limit_deg,
                     grid_spacing_m=args.grid_spacing_m, holdout_fraction=args.holdout_fraction, seed=args.seed)
        encoded = json.dumps(result, allow_nan=False, separators=(",", ":")).encode("utf-8")
        _write_new_file(output, encoded)
    except (OSError, SourceError, MagneticProcessingError, AmargosaError, ValueError) as error:
        print(f"Amargosa M03 processing failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"output": str(output), "selected_rows": result["source_selection"]["selected_row_count"],
                      "tracks": result["source_selection"]["track_count"],
                      "sha256": hashlib.sha256(encoded).hexdigest()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
