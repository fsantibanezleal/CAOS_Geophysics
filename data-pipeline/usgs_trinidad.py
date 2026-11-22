"""Stream and verify the USGS Trinidad airborne magnetic point acquisition.

The output is a source-bound field QC/index artifact. It is not an inversion,
an uncertainty model, a field truth model, or a replacement for the original
CSV. Large inputs and outputs belong in the external CAOS data root.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


SOURCE_ID = "usgs-trinidad-aeromag-2025"
SOURCE_URL = (
    "https://cmgds.marine.usgs.gov/data-releases/media/2025/10.5066-P13SZBH7/"
    "6e72781adf5a48a0a9321014128d666d/Trinidad_aeromag.csv"
)
METADATA_URL = (
    "https://cmgds.marine.usgs.gov/data-releases/media/2025/10.5066-P13SZBH7/"
    "6a9a0afabe42480fa3d35ed6c5b3d4dd/Trinidad_aeromag_metadata.xml"
)
EXPECTED_BYTES = 897_706_119
EXPECTED_MD5 = "4ac495b6f0060a19bdc9728bef0ada06"
PUBLISHED_FEATURE_COUNT = 3_337_738
EXPECTED_DATA_ROWS = 3_337_737
CSV_FIELDS = (
    "date", "diurnal", "dtm", "easting_WGS84", "fid", "flight", "Flux_X",
    "Flux_Y", "Flux_Z", "gpsz", "height", "igrf", "latitude_WGS84", "line",
    "longitude_WGS84", "mag_comp", "mag_diu", "mag_raw", "mag_rmi", "mag_tmi",
    "northing_WGS84", "time_ssm",
)
NUMERIC_FIELDS = tuple(name for name in CSV_FIELDS if name not in {"date", "flight", "line"})
MAP_FIELDS = ("mag_rmi", "mag_tmi", "mag_comp", "diurnal", "height")
TILE_SIZES_M = (120, 600)
_SAFE_ID = re.compile(r"[A-Za-z0-9_.-]{1,96}\Z", re.ASCII)


class SourceError(ValueError):
    """The downloaded source or its CSV contract did not verify."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite(row: dict[str, str], key: str, row_number: int) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as error:
        raise SourceError(f"row {row_number}: invalid numeric field {key}") from error
    if not math.isfinite(value):
        raise SourceError(f"row {row_number}: nonfinite numeric field {key}")
    return value


def _atomic_json(path: Path, value: object) -> tuple[int, str]:
    encoded = (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                          separators=(",", ":")) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".partial", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        with temporary.open("rb") as check:
            if check.read() != encoded:
                raise OSError("JSON readback differs from the canonical output")
        digest = hashlib.sha256(encoded).hexdigest()
        os.replace(temporary, path)
        return len(encoded), digest
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _blank_stats() -> dict[str, float | int | None]:
    return {"count": 0, "min": None, "max": None, "sum": 0.0}


def _add_stat(stats: dict[str, float | int | None], value: float) -> None:
    stats["count"] = int(stats["count"]) + 1
    stats["sum"] = float(stats["sum"]) + value
    stats["min"] = value if stats["min"] is None else min(float(stats["min"]), value)
    stats["max"] = value if stats["max"] is None else max(float(stats["max"]), value)


def _finish_stat(stats: dict[str, float | int | None]) -> dict[str, float | int | None]:
    count = int(stats["count"])
    total = float(stats["sum"])
    return {"count": count, "min": stats["min"], "max": stats["max"],
            "mean": total / count if count else None}


def process(source: Path, output_dir: Path, *, metadata: Path | None = None,
            verify_official_source: bool = True) -> dict:
    """Verify the immutable CSV and write deterministic tiled and line summaries."""
    source = Path(source)
    if source.is_symlink():
        raise SourceError("source must be a regular non-symlink file")
    source = source.resolve(strict=True)
    output_dir = Path(output_dir).resolve()
    if not source.is_file():
        raise SourceError("source must be a regular file")
    if output_dir.exists():
        raise SourceError("output directory must not already exist")
    byte_count = source.stat().st_size
    if verify_official_source and byte_count != EXPECTED_BYTES:
        raise SourceError(f"source size differs from USGS record: {byte_count}")
    md5 = _md5(source)
    if verify_official_source and md5 != EXPECTED_MD5:
        raise SourceError(f"source MD5 differs from USGS record: {md5}")
    source_sha256 = _sha256(source)
    metadata_record = None
    if metadata is not None:
        metadata_path = Path(metadata)
        if metadata_path.is_symlink():
            raise SourceError("metadata must be a regular non-symlink file")
        metadata_path = metadata_path.resolve(strict=True)
        if not metadata_path.is_file():
            raise SourceError("metadata must be a regular file")
        metadata_record = {"name": metadata_path.name, "bytes": metadata_path.stat().st_size,
                           "sha256": _sha256(metadata_path), "url": METADATA_URL}

    columns: dict[str, dict[str, float | int | None]] = {
        name: _blank_stats() for name in NUMERIC_FIELDS
    }
    lines: dict[tuple[int, int], dict] = {}
    tiles: dict[int, dict[tuple[int, int], dict]] = {size: {} for size in TILE_SIZES_M}
    date_min: int | None = None
    date_max: int | None = None
    rmi_identity = {"count": 0, "abs_error_max": 0.0, "abs_error_sum": 0.0,
                    "abs_error_gt_0_001_nt": 0}
    row_count = 0
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if tuple(reader.fieldnames or ()) != CSV_FIELDS:
            raise SourceError(f"CSV columns differ from the reviewed USGS schema: {reader.fieldnames!r}")
        for row_count, row in enumerate(reader, start=1):
            row_number = row_count + 1
            if None in row or set(row) != set(CSV_FIELDS) or any(value is None for value in row.values()):
                raise SourceError(f"row {row_number}: CSV width differs from the header")
            try:
                date = int(row["date"])
                flight = int(row["flight"])
                line = int(row["line"])
            except (TypeError, ValueError) as error:
                raise SourceError(f"row {row_number}: date, flight and line must be integers") from error
            date_min = date if date_min is None else min(date_min, date)
            date_max = date if date_max is None else max(date_max, date)
            values = {name: _finite(row, name, row_number) for name in NUMERIC_FIELDS}
            easting = values["easting_WGS84"]
            northing = values["northing_WGS84"]
            fid = values["fid"]
            if not _SAFE_ID.fullmatch(str(flight)) or not _SAFE_ID.fullmatch(str(line)):
                raise SourceError(f"row {row_number}: unsafe flight/line identity")

            record = lines.setdefault((flight, line), {
                "flight": flight, "line": line, "count": 0, "date_min": date,
                "date_max": date, "fid_start": fid, "fid_end": fid,
                "easting_min_m": easting, "easting_max_m": easting,
                "northing_min_m": northing, "northing_max_m": northing,
                "mag_rmi": _blank_stats(), "mag_tmi": _blank_stats(),
            })
            record["count"] += 1
            record["date_min"] = min(record["date_min"], date)
            record["date_max"] = max(record["date_max"], date)
            if record["count"] == 1:
                record["fid_start"] = fid
            record["fid_end"] = fid
            record["easting_min_m"] = min(record["easting_min_m"], easting)
            record["easting_max_m"] = max(record["easting_max_m"], easting)
            record["northing_min_m"] = min(record["northing_min_m"], northing)
            record["northing_max_m"] = max(record["northing_max_m"], northing)
            _add_stat(record["mag_rmi"], values["mag_rmi"])
            _add_stat(record["mag_tmi"], values["mag_tmi"])
            for name in NUMERIC_FIELDS:
                _add_stat(columns[name], values[name])

            delta = abs(values["mag_rmi"] - (values["mag_tmi"] - values["igrf"]))
            rmi_identity["count"] += 1
            rmi_identity["abs_error_max"] = max(rmi_identity["abs_error_max"], delta)
            rmi_identity["abs_error_sum"] += delta
            if delta > 0.001:
                rmi_identity["abs_error_gt_0_001_nt"] += 1

            for size, cells in tiles.items():
                key = (math.floor(easting / size), math.floor(northing / size))
                cell = cells.setdefault(key, {"easting_bin": key[0], "northing_bin": key[1],
                    "count": 0, **{name: _blank_stats() for name in MAP_FIELDS}})
                cell["count"] += 1
                for name in MAP_FIELDS:
                    _add_stat(cell[name], values[name])
        physical_csv_lines = reader.line_num
        if verify_official_source and (row_count != EXPECTED_DATA_ROWS
                                       or physical_csv_lines != PUBLISHED_FEATURE_COUNT):
            raise SourceError(
                "CSV row-count reconciliation failed: "
                f"data_records={row_count}, physical_lines={physical_csv_lines}, "
                f"published_feature_count={PUBLISHED_FEATURE_COUNT}"
            )
    if row_count == 0:
        raise SourceError("CSV contains no point observations")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", suffix=".staging",
                                       dir=output_dir.parent))
    files: dict[str, dict[str, int | str]] = {}
    try:
        lines_value = []
        for key in sorted(lines):
            line = lines[key]
            line["mag_rmi"] = _finish_stat(line["mag_rmi"])
            line["mag_tmi"] = _finish_stat(line["mag_tmi"])
            lines_value.append(line)
        size, digest = _atomic_json(staging_dir / "lines.json", lines_value)
        files["lines.json"] = {"bytes": size, "sha256": digest}

        for cell_size, cells in tiles.items():
            values = []
            for key in sorted(cells, key=lambda item: (item[1], item[0])):
                cell = cells[key]
                for name in MAP_FIELDS:
                    cell[name] = _finish_stat(cell[name])
                values.append(cell)
            name = f"tiles-{cell_size}m.json"
            size, digest = _atomic_json(staging_dir / name, {
                "schema": "usgs-trinidad-observed-bin-aggregate/v1",
                "bin_size_m": cell_size, "aggregation": "observed_point_mean_min_max_count",
                "interpolation": False, "uncertainty": None, "cells": values,
            })
            files[name] = {"bytes": size, "sha256": digest}

        summary = {
        "schema": "caos.geophysics.field-source-summary/v1", "source_id": SOURCE_ID,
        "source": {"name": "Trinidad aeromagnetic point survey", "provider": "USGS",
            "doi": "10.5066/P13SZBH7", "citation": "Watt, J.T., Langenheim, V.E., and Staisch, L.M., 2025, Detailed aeromagnetic survey of the Trinidad Area, California, U.S. Geological Survey data release, DOI 10.5066/P13SZBH7.",
            "url": "https://doi.org/10.5066/P13SZBH7", "license": "USGS public domain; attribution required",
            "metadata": metadata_record},
        "original": {"name": source.name, "bytes": byte_count, "md5_usgs": md5,
            "sha256": source_sha256, "rows": row_count, "columns": list(CSV_FIELDS)},
        "survey": {"date_min_yyyymmdd_utc": date_min, "date_max_yyyymmdd_utc": date_max,
            "flight_count": len({key[0] for key in lines}), "line_count": len(lines),
            "point_count": row_count, "published_feature_count": PUBLISHED_FEATURE_COUNT,
            "physical_csv_lines_including_header": physical_csv_lines,
            "catalog_count_difference_explained_by_header": (
                PUBLISHED_FEATURE_COUNT - row_count == 1 and physical_csv_lines == PUBLISHED_FEATURE_COUNT
            ), "coordinate_reference": "EPSG:32610",
            "horizontal_datum": "WGS 84", "vertical_datum": "mean sea level",
            "horizontal_unit": "m", "elevation_unit": "m", "magnetic_unit": "nT",
            "flight_spacing_m": 600, "tie_spacing_m": 6000,
            "measurement_product": "contractor-provided compensated/levelled total-field and residual channels",
            "published_processing": ["magnetometer compensation", "time-lag correction",
                "diurnal correction from two base stations", "flight/tie-line leveling",
                "full IGRF subtraction"]},
        "field_summary": {name: _finish_stat(value) for name, value in columns.items()},
        "identity_check": {"equation": "mag_rmi = mag_tmi - igrf (metadata-described channel identity)",
            "count": rmi_identity["count"], "absolute_difference_max_nT": rmi_identity["abs_error_max"],
            "absolute_difference_mean_nT": rmi_identity["abs_error_sum"] / rmi_identity["count"],
            "rows_over_0_001_nT": rmi_identity["abs_error_gt_0_001_nt"]},
        "derived_files": files,
        "claims": {"field_data": verify_official_source,
            "full_source_verified": verify_official_source,
            "geology_truth_known": False, "measurement_uncertainty_known": False,
            "inverse_performed": False, "induced_susceptibility_eligible": False,
            "interpolation_performed": False},
        }
        size, digest = _atomic_json(staging_dir / "summary.json", summary)
        os.replace(staging_dir, output_dir)
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
    return {"summary": summary, "summary_file": {"bytes": size, "sha256": digest},
            "output_dir": str(output_dir)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-test-source", action="store_true",
                        help="disable USGS byte, MD5 and row-count checks for a small test fixture")
    args = parser.parse_args(argv)
    try:
        result = process(args.source, args.output_dir, metadata=args.metadata,
                         verify_official_source=not args.allow_test_source)
    except (OSError, UnicodeError, csv.Error, SourceError) as error:
        print(f"USGS Trinidad preprocessing failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "source_verified_field_qc_only", "source_id": SOURCE_ID,
        "rows": result["summary"]["original"]["rows"],
        "source_sha256": result["summary"]["original"]["sha256"],
        "summary_sha256": result["summary_file"]["sha256"],
        "output_dir": result["output_dir"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
