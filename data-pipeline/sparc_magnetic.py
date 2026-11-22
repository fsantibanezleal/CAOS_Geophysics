"""Pinned, provenance-preserving reader for the BAS SPARC magnetic XYZ archive.

This adapter parses the source's 21-column ASCII export, preserves a row-level
inventory and writes two explicit M03 CSV inputs. It applies no correction and
does not make magnetic-inversion or geological claims.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, time
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile


SOURCE_ID = "sparc-northern-palmer-magnetic"
SOURCE_SHA256 = "db63cf49dada843676429376f1991f2531c37eab8007f1da2feeb22b3b7943f8"
SOURCE_BYTES = 69_305_816
MAX_SOURCE_BYTES = 128 * 1024 * 1024
MAX_SOURCE_ROWS = 500_000
SOURCE_URL = "https://data.bas.ac.uk/full-record.php?id=GB/NERC/BAS/PDC/01358"
SOURCE_DOI = "10.5285/5c87409e-fdfd-4732-ad19-9d319a0e5a2b"
DATASET_CITATION = (
    "Ferraccioli, F., & Jones, P. C. (2020). Processed line aeromagnetic data over Northern Palmer Land, "
    "Antarctic Peninsula (2002/03 season) (Version 1.0) [Data set]. UK Polar Data Centre, NERC, UKRI. "
    f"https://doi.org/{SOURCE_DOI}"
)
COLUMNS = (
    "Line_No", "Flight_No", "Lon", "Lat", "x", "y", "Height_WGS1984", "Date", "Time",
    "MagR", "MagC", "TCorr", "RefField", "MagRTC", "BCorr", "MagBRTC", "ACorr", "SCorr",
    "MagF", "MagL", "MagML",
)
NUMERIC_COLUMNS = COLUMNS[2:7] + COLUMNS[9:]
MISSING = "*"


class SPARCError(ValueError):
    """Source bytes or their declared schema are not admissible."""


def _digest(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            if size > MAX_SOURCE_BYTES:
                raise SPARCError(f"source exceeds {MAX_SOURCE_BYTES} bytes")
            digest.update(chunk)
    return size, digest.hexdigest()


def _float_or_none(value: str, *, field: str, record: int) -> float | None:
    if value == MISSING:
        return None
    try:
        result = float(value)
    except ValueError as error:
        raise SPARCError(f"record {record}: {field} is not numeric") from error
    if not math.isfinite(result):
        raise SPARCError(f"record {record}: {field} is not finite")
    return result


def _read_numeric_rows(path: Path):
    numeric_index = 0
    current_marker = None
    marker_header_pending = False
    with path.open("r", encoding="ascii", errors="strict", newline="") as stream:
        for source_line, line in enumerate(stream, start=1):
            tokens = line.split()
            if not tokens:
                continue
            if tokens[0].startswith("/"):
                continue
            if tokens[0] in {"Line", "Tie", "Random", "Special"}:
                if len(tokens) != 2 or not tokens[1].isdigit():
                    raise SPARCError(f"source line {source_line}: malformed {tokens[0]} line marker")
                current_marker = (tokens[0], int(tokens[1]))
                marker_header_pending = True
                continue
            if not tokens[0].isdigit():
                raise SPARCError(f"source line {source_line}: unexpected non-comment record")
            if len(tokens) != len(COLUMNS):
                raise SPARCError(f"source line {source_line}: expected 21 fields, received {len(tokens)}")
            if not tokens[1].isdigit():
                raise SPARCError(f"source line {source_line}: Flight_No must be an integer")
            if current_marker is None or int(tokens[0]) != current_marker[1]:
                raise SPARCError(f"source line {source_line}: numeric row does not match the active provider line marker")
            numeric_index += 1
            if numeric_index > MAX_SOURCE_ROWS:
                raise SPARCError(f"source exceeds {MAX_SOURCE_ROWS} numeric records")
            row = dict(zip(COLUMNS, tokens, strict=True))
            for field in NUMERIC_COLUMNS:
                _float_or_none(row[field], field=field, record=numeric_index)
            try:
                date.fromisoformat(row["Date"].replace("/", "-"))
                if row["Time"] != MISSING:
                    time.fromisoformat(row["Time"])
            except ValueError as error:
                raise SPARCError(f"record {numeric_index}: invalid date or UTC time") from error
            row["source_record_index"] = numeric_index
            row["source_line_number"] = source_line
            row["raw_record"] = line.rstrip("\r\n")
            row["source_marker_type"] = current_marker[0]
            row["provider_segment_header"] = (
                marker_header_pending
                and row["x"] == MISSING
                and row["y"] == MISSING
                and row["Time"] == MISSING
                and all(row[field] == MISSING for field in COLUMNS[9:])
            )
            marker_header_pending = False
            yield row


def _bearing(row_a: dict, row_b: dict) -> float:
    dx = float(row_b["x"]) - float(row_a["x"])
    dy = float(row_b["y"]) - float(row_a["y"])
    if math.hypot(dx, dy) <= 1e-6:
        raise SPARCError("a survey line has coincident endpoints")
    return math.degrees(math.atan2(dy, dx)) % 180.0


def _angular_distance(left: float, right: float) -> float:
    difference = abs(left - right) % 180.0
    return min(difference, 180.0 - difference)


def _axis_mean(values: list[float]) -> float:
    x = sum(math.cos(math.radians(2.0 * value)) for value in values)
    y = sum(math.sin(math.radians(2.0 * value)) for value in values)
    return (math.degrees(math.atan2(y, x)) / 2.0) % 180.0


def _classify_line_axes(endpoints: dict[tuple[int, int], list[dict]]) -> tuple[dict, dict]:
    bearings = {key: _bearing(rows[0], rows[-1]) for key, rows in endpoints.items() if len(rows) >= 2}
    if len(bearings) < 6:
        raise SPARCError("at least six coordinate-complete lines are required to check the two survey axes")
    keys = sorted(bearings)
    seed_a, seed_b = max(
        ((a, b) for i, a in enumerate(keys) for b in keys[i + 1:]),
        key=lambda pair: _angular_distance(bearings[pair[0]], bearings[pair[1]]),
    )
    centers = [bearings[seed_a], bearings[seed_b]]
    labels = {}
    for _ in range(32):
        labels = {key: int(_angular_distance(bearings[key], centers[1])
                           < _angular_distance(bearings[key], centers[0])) for key in keys}
        updated = [_axis_mean([bearings[key] for key in keys if labels[key] == index]) for index in (0, 1)]
        if max(_angular_distance(updated[i], centers[i]) for i in (0, 1)) < 1e-10:
            centers = updated
            break
        centers = updated
    counts = [sum(label == index for label in labels.values()) for index in (0, 1)]
    separation = _angular_distance(centers[0], centers[1])
    if min(counts) < 3 or not 70.0 <= separation <= 110.0 or max(
        _angular_distance(bearings[key], centers[labels[key]]) for key in keys
    ) > 12.0:
        raise SPARCError("observed line bearings do not support two distinct near-orthogonal survey axes")
    profile_axis = int(counts[1] > counts[0])
    tie_axis = 1 - profile_axis
    if counts[profile_axis] < 1.5 * counts[tie_axis]:
        raise SPARCError("line-axis counts do not distinguish profiles from tie lines")
    role = {key: ("flight" if labels[key] == profile_axis else "tie") for key in keys}
    marker_roles = {"Line": "flight", "Tie": "tie", "Random": "tie"}
    marker_summary = {}
    for key, rows in endpoints.items():
        marker_types = {row["source_marker_type"] for row in rows}
        if len(marker_types) != 1:
            raise SPARCError(f"line {key!r} changes its provider marker within the file")
        marker = marker_types.pop()
        marker_summary.setdefault(marker, {"line_count": 0, "assigned_flight": 0, "assigned_tie": 0})
        marker_summary[marker]["line_count"] += 1
        marker_summary[marker][f"assigned_{role[key]}"] += 1
        expected_role = marker_roles.get(marker)
        if expected_role is not None and role[key] != expected_role:
            raise SPARCError(f"provider {marker} marker conflicts with its measured orientation cluster")
    summary = {
        "method": "two-axis unsupervised orientation clustering; geometry only, no magnetic values",
        "official_design": "profile lines E-W; tie lines N-S; 5 km and 25 km nominal spacing",
        "profile_axis_center_deg_mod_180": centers[profile_axis],
        "tie_axis_center_deg_mod_180": centers[tie_axis],
        "axis_separation_deg": separation,
        "flight_line_count": counts[profile_axis],
        "tie_line_count": counts[tie_axis],
        "maximum_within_axis_deviation_deg": max(
            _angular_distance(bearings[key], centers[labels[key]]) for key in keys
        ),
        "provider_marker_role_crosscheck": marker_summary,
        "line_assignments": [
            {"flight_id": key[0], "line_no": key[1], "line_id": f"F{key[0]}-L{key[1]}",
             "role": role[key], "bearing_deg_mod_180": bearings[key],
             "coordinate_complete_rows": len(endpoints[key])}
            for key in sorted(role)
        ],
    }
    return role, summary


def _write_csv(path: Path, fields: tuple[str, ...], rows) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def _sha256(path: Path) -> str:
    return _digest(path)[1]


def preprocess(source_path: Path, output_path: Path, *, verify_pin: bool = True) -> dict:
    source_path, output_path = Path(source_path), Path(output_path)
    if source_path.is_symlink() or not source_path.is_file():
        raise SPARCError("source must be a regular non-symlink file")
    if output_path.exists() or output_path.is_symlink():
        raise SPARCError("refusing to replace an existing output directory")
    source_bytes, source_hash = _digest(source_path)
    if verify_pin and (source_bytes != SOURCE_BYTES or source_hash != SOURCE_SHA256):
        raise SPARCError("source does not match the pinned BAS SPARC object size and SHA-256")

    endpoint_rows: dict[tuple[int, int], list[dict]] = {}
    counts = {"numeric_records": 0, "line_headers": 0, "coordinate_complete": 0,
              "coordinate_incomplete": 0, "MagML_tie_rows": 0}
    missing = {field: 0 for field in NUMERIC_COLUMNS}
    for row in _read_numeric_rows(source_path):
        counts["numeric_records"] += 1
        for field in NUMERIC_COLUMNS:
            missing[field] += row[field] == MISSING
        xy_ok = row["x"] != MISSING and row["y"] != MISSING
        if row["provider_segment_header"]:
            counts["line_headers"] += 1
            continue
        if xy_ok:
            counts["coordinate_complete"] += 1
            endpoint_rows.setdefault((int(row["Flight_No"]), int(row["Line_No"])), []).append(row)
        else:
            counts["coordinate_incomplete"] += 1
    roles, geometry = _classify_line_axes(endpoint_rows)
    if len(roles) != len(endpoint_rows):
        raise SPARCError("one or more coordinate groups cannot be assigned a stable survey-line role")
    magml_tie_rows = sum(
        row["MagML"] != MISSING and roles.get((int(row["Flight_No"]), int(row["Line_No"]))) == "tie"
        for row in _read_numeric_rows(source_path)
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_path.name}.", dir=output_path.parent))
    try:
        inventory_fields = ("source_record_index", "source_line_number", "record_kind",
                            "source_marker_type", *COLUMNS, "raw_record")
        with (staging / "inventory.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=inventory_fields, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            for row in _read_numeric_rows(source_path):
                xy_ok = row["x"] != MISSING and row["y"] != MISSING
                kind = ("line_header" if row["provider_segment_header"] else
                        "observation" if xy_ok else "incomplete_observation")
                writer.writerow({**row, "record_kind": kind})

        def processing_rows(channel: str, *, profiles_only: bool, require_magml: bool = False):
            for row in _read_numeric_rows(source_path):
                if row["x"] == MISSING or row["y"] == MISSING or row["Height_WGS1984"] == MISSING:
                    continue
                key = (int(row["Flight_No"]), int(row["Line_No"]))
                line_role = roles.get(key)
                if (line_role is None or (profiles_only and line_role != "flight") or row[channel] == MISSING
                        or (require_magml and row["MagML"] == MISSING)):
                    continue
                result = {
                    "Easting_m": row["x"], "Northing_m": row["y"], "field_nT": row[channel],
                    "line_id": f"F{key[0]}-L{key[1]}", "line_role": line_role,
                    "height_WGS1984_m": row["Height_WGS1984"],
                    "sample_order": row["source_record_index"],
                    "source_record_index": row["source_record_index"],
                    "source_marker_type": row["source_marker_type"],
                }
                if require_magml:
                    result["comparison_MagML_nT"] = row["MagML"]
                yield result

        process_fields = ("Easting_m", "Northing_m", "field_nT", "line_id", "line_role",
                          "height_WGS1984_m", "sample_order", "source_record_index", "source_marker_type")
        common_fields = (*process_fields, "comparison_MagML_nT")
        counts["magl_processing_rows"] = _write_csv(
            staging / "magl-flight-and-tie.csv", process_fields,
            processing_rows("MagL", profiles_only=False),
        )
        counts["magml_processing_rows"] = _write_csv(
            staging / "magml-flight-profiles.csv", process_fields,
            processing_rows("MagML", profiles_only=True),
        )
        counts["magl_common_profile_rows"] = _write_csv(
            staging / "magl-common-profile-rows.csv", common_fields,
            processing_rows("MagL", profiles_only=True, require_magml=True),
        )
        for path, field in ((staging / "magl-flight-and-tie.csv", "MagL"),
                            (staging / "magml-flight-profiles.csv", "MagML"),
                            (staging / "magl-common-profile-rows.csv", "MagL_common")):
            counts[f"{field}_sha256"] = _sha256(path)
        counts["inventory_sha256"] = _sha256(staging / "inventory.csv")
        manifest = {
            "schema": "bas-sparc-magnetic-preprocess/v1",
            "source": {"source_id": SOURCE_ID, "url": SOURCE_URL, "doi": SOURCE_DOI,
                       "citation": DATASET_CITATION, "rights": "UK Open Government Licence v3; cite source",
                       "bytes": source_bytes, "sha256": source_hash,
                       "processing_state": "provider-processed channels; no additional corrections applied"},
            "frame": {"name": "BAS metadata Polar stereographic (verbatim parameters retained)",
                      "parameters_as_published": {"latitude_of_natural_origin_deg": -71,
                          "longitude_of_natural_origin_deg": 0,
                          "scale_factor_field_verbatim": "-75.33333333333",
                          "false_easting_m": 0, "false_northing_m": 2082760.109},
                      "unit": "m", "reprojection_applied": False},
            "channel_semantics": {"MagL": "statistically levelled magnetic data, nT",
                "MagML": "provider microlevelled magnetic data, nT; tie-line samples are not included",
                "selected_for_M03": {"MagL": "flight and tie line crossing QC plus blocked-flight-line interpolation",
                                     "MagML": "blocked-flight-line interpolation only; provider excludes ties"}},
            "geometry_classification": geometry,
            "counts": {**counts, "missing_token_counts": missing,
                       "MagML_tie_rows": magml_tie_rows},
            "limitations": [
                "Original source bytes remain the authoritative immutable record; inventory preserves every numeric row and source line index.",
                "The dataset already includes provider compensation, IGRF removal, diurnal correction, levelling and microlevelling products.",
                "No correction, coordinate transformation, tie-line levelling or reduction to the pole is applied here.",
                "The provider states MagML excludes tie lines; MagML is therefore never used for tie-line crossover QC.",
                "M03 held-out interpolation measures spatial interpolation only, not subsurface recovery or field inversion accuracy.",
                "Provider-reported crossover accuracy is not independently reproduced by this preprocessing receipt.",
            ],
            "outputs": {name: {"bytes": (staging / name).stat().st_size,
                               "sha256": _sha256(staging / name)}
                        for name in ("inventory.csv", "magl-flight-and-tie.csv", "magml-flight-profiles.csv",
                                     "magl-common-profile-rows.csv")},
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
        )
        try:
            os.rename(staging, output_path)
        except FileExistsError as error:
            raise SPARCError("refusing to replace an existing output directory") from error
        return manifest
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Original SPARC_Mag.XYZ bytes")
    parser.add_argument("--output", type=Path, required=True, help="New external output directory; never overwritten")
    parser.add_argument("--allow-unpinned-test-source", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        manifest = preprocess(args.source, args.output, verify_pin=not args.allow_unpinned_test_source)
    except (OSError, UnicodeError, SPARCError) as error:
        print(f"SPARC preprocessing failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"output": str(args.output), "source_sha256": manifest["source"]["sha256"],
                      "counts": manifest["counts"], "outputs": manifest["outputs"]}, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
