"""Pinned author observation intake and principal-fact inspection, not inversion."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import zipfile
import zlib

from sources import (ROOT, SourceError, _digest_file, _inside, acquire_source,
                     archive_member_key, validate_archive_contract)


AUTHOR_SOURCE = "clear-lake-author-potentials-v2"
HEADER = ["", "Station_ID", "lonWGS84", "latWGS84", "xWGS84_UTM10N", "yWGS84_UTM10N",
          "zWGS84", "OG", "FAA", "SBA", "TTC", "CBA", "ISO"]
CHANNELS = ["OG", "FAA", "SBA", "TTC", "CBA", "ISO"]
MAX_PROFILE_BYTES = 2_000_000
MAX_PROFILE_ROWS = 10_000


def safe_target(root: Path, key: PurePosixPath, parent: str) -> Path:
    target = _inside(root, key, parent)
    for item in (target, *target.parents):
        if item == root:
            break
        attributes = item.lstat().st_file_attributes if os.name == "nt" and item.exists() else 0
        if item.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise SourceError("Symlink or reparse point in selected-source storage path")
    return target


def canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")


def publish_bytes(target: Path, value: bytes) -> None:
    """Exclusive atomic publication of complete bytes, with identical reuse only."""
    if target.is_symlink():
        raise SourceError("Immutable output or receipt is a symlink")
    if target.exists():
        if not target.is_file() or target.stat().st_size != len(value) or target.read_bytes() != value:
            raise SourceError("Immutable output or receipt drift; preserve existing bytes")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".receipt-", dir=target.parent) as temporary:
        staged = Path(temporary) / "complete.json"
        staged.write_bytes(value)
        try:
            os.link(staged, target)
        except FileExistsError:
            if (target.is_symlink() or not target.is_file() or target.stat().st_size != len(value)
                    or target.read_bytes() != value):
                raise SourceError("Concurrent output or receipt drift; preserve existing bytes") from None


def inventory(archive: zipfile.ZipFile, contract: dict) -> dict[str, zipfile.ZipInfo]:
    validate_archive_contract(contract)
    entries = archive.infolist()
    if not entries or len(entries) > contract["max_entries"]:
        raise SourceError("ZIP entry-count limit")
    indexed = {}
    aliases = {}
    components = {}
    expanded = 0
    for info in entries:
        name = info.filename[:-1] if info.is_dir() else info.filename
        path = archive_member_key(name)
        if info.filename != info.orig_filename or name.casefold() in aliases:
            raise SourceError("Unsafe or duplicate ZIP path")
        aliases[name.casefold()] = name
        # Reject even component-only case aliases (Data/a versus data/b).
        for length in range(1, len(path.parts) + 1):
            component = PurePosixPath(*path.parts[:length]).as_posix()
            old = components.setdefault(component.casefold(), component)
            if old != component:
                raise SourceError("Unsafe ZIP case alias")
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}):
            raise SourceError("ZIP special file or symlink")
        if ((stat.S_ISDIR(mode) and not info.is_dir()) or (stat.S_ISREG(mode) and info.is_dir())
                or (info.is_dir() and (info.file_size or info.compress_size))):
            raise SourceError("Unsafe ZIP directory/type metadata")
        if info.flag_bits & 1 or info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
            raise SourceError("Encrypted or unsupported ZIP member")
        if (info.file_size > contract["max_member_bytes"]
                or info.file_size > max(info.compress_size, 1) * contract["max_expansion_ratio"]):
            raise SourceError("ZIP member size or expansion-ratio limit")
        expanded += info.file_size
        if expanded > contract["max_expanded_bytes"]:
            raise SourceError("ZIP total expansion limit")
        indexed[name] = info
    for name in indexed:
        if any(parent.as_posix() in indexed and not indexed[parent.as_posix()].is_dir()
               for parent in PurePosixPath(name).parents if parent.as_posix() != "."):
            raise SourceError("Unsafe ZIP file/parent collision")
    for name, expected in contract["selected_members"].items():
        if name not in indexed or indexed[name].is_dir() or indexed[name].file_size != expected["bytes"]:
            raise SourceError(f"Missing or changed selected member: {name}")
    return indexed


def extract_selected(record: dict, archive_path: Path, *, root: Path = ROOT) -> dict:
    """Verify every selected member before exclusive installation; never overwrite."""
    root = root.resolve()
    if record.get("format") != "research-zip" or not isinstance(record.get("archive_contract"), dict):
        raise SourceError("Source needs a reviewed research ZIP contract")
    validate_archive_contract(record["archive_contract"])
    if archive_path.is_symlink() or not archive_path.is_file():
        raise SourceError("Archive must be a regular local file, not a symlink")
    if _digest_file(archive_path) != (record["expected_bytes"], record["sha256"]):
        raise SourceError("Archive byte/hash drift; preserve the disputed original")
    contract = record["archive_contract"]
    source_id = record["source_id"]
    selected = contract["selected_members"]
    # Source IDs are normally validated by load_ledger; retain validation for
    # direct callers and fixtures too.
    if not isinstance(source_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source_id):
        raise SourceError("Unsafe source identity")
    prefix = PurePosixPath("data/downloads/extracted") / source_id
    targets = {name: safe_target(root, prefix / name, "downloads") for name in selected}
    staging_parent = safe_target(root, PurePosixPath("data/downloads/extracted"), "downloads")
    staging_parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive_path) as archive, tempfile.TemporaryDirectory(prefix=".intake-", dir=staging_parent) as temporary:
            indexed = inventory(archive, contract)
            manifest = [{"name": name, "bytes": item.file_size, "compressed_bytes": item.compress_size,
                         "crc32": item.CRC} for name, item in sorted(indexed.items())]
            receipt = {
                "schema": "geophysics.selected-source-members/v1", "source_id": source_id,
                "archive_sha256": record["sha256"], "archive_bytes": record["expected_bytes"],
                "inventory_sha256": hashlib.sha256(canonical({"entries": manifest})).hexdigest(),
                "entry_count": len(manifest), "expanded_bytes": sum(item["bytes"] for item in manifest),
                "rights_decision": record["rights_decision"], "rights_statement": record["rights_statement"],
                "citation": record["citation"], "modified": False,
                "members": [{"name": name, "path": targets[name].relative_to(root).as_posix(), **expected}
                            for name, expected in selected.items()],
            }
            receipt_path = safe_target(root, PurePosixPath("data/raw/acquisition") / (source_id + "-members.json"), "raw")
            value = canonical(receipt)
            if receipt_path.exists() and (not receipt_path.is_file() or receipt_path.stat().st_size != len(value)
                                          or receipt_path.read_bytes() != value):
                raise SourceError("Selected-member receipt drift; preserve old receipt")
            staged = {}
            for index, (name, expected) in enumerate(selected.items()):
                path = Path(temporary) / str(index)
                count, digest = 0, hashlib.sha256()
                with archive.open(indexed[name]) as source, path.open("xb") as output:
                    while chunk := source.read(128 * 1024):
                        count += len(chunk)
                        if count > expected["bytes"]:
                            raise SourceError("Selected member exceeds its byte pin")
                        digest.update(chunk)
                        output.write(chunk)
                if (count, digest.hexdigest()) != (expected["bytes"], expected["sha256"]):
                    raise SourceError(f"Selected member byte/hash mismatch: {name}")
                target = targets[name]
                if target.exists() or target.is_symlink():
                    if (target.is_symlink() or not target.is_file() or target.stat().st_size != count
                            or _digest_file(target) != (count, digest.hexdigest())):
                        raise SourceError(f"Existing selected bytes differ; preserve: {name}")
                staged[name] = path
            if _digest_file(archive_path) != (record["expected_bytes"], record["sha256"]):
                raise SourceError("Archive changed during intake; no selected members published")
            for name, path in staged.items():
                target = targets[name]
                target.parent.mkdir(parents=True, exist_ok=True)
                # Recheck containment after parents exist, including symlinks.
                if safe_target(root, prefix / name, "downloads") != target:
                    raise SourceError("Selected path changed during intake")
                try:
                    os.link(path, target)
                except FileExistsError:
                    if target.is_symlink() or not target.is_file() or _digest_file(target) != _digest_file(path):
                        raise SourceError(f"Concurrent selected bytes differ; preserve: {name}") from None
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError, zlib.error) as exc:
        raise SourceError(f"Invalid ZIP source: {exc}") from exc
    safe_target(root, PurePosixPath(receipt_path.relative_to(root).as_posix()), "raw")
    publish_bytes(receipt_path, value)
    return receipt


def profile_gravity(path: Path, *, source: dict) -> dict:
    if path.is_symlink() or not path.is_file():
        raise SourceError("Principal-fact source must be a regular file")
    if path.stat().st_size > MAX_PROFILE_BYTES:
        raise SourceError("Principal-fact profile byte cap")
    identity = _digest_file(path)
    if source.get("format") == "research-zip":
        validate_archive_contract(source.get("archive_contract"))
        expected = source["archive_contract"]["selected_members"].get("data/ground_gravity_data.csv")
        if not expected or identity != (expected["bytes"], expected["sha256"]):
            raise SourceError("Principal-fact byte/hash mismatch against source member pin")
    stations, xyz, geographic, observed, flags = [], [], [], {name: [] for name in CHANNELS}, []
    original_indices, line_ends = [], []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        if next(reader, None) != HEADER:
            raise SourceError("Unexpected principal-fact columns; do not guess a format")
        for row_number, row in enumerate(reader, 1):
            if row_number > MAX_PROFILE_ROWS or len(row) != len(HEADER) or not row[1].strip():
                raise SourceError(f"Invalid or oversized principal-fact row {row_number}")
            values = []
            for field, raw in zip(HEADER[2:], row[2:]):
                try:
                    number = float(raw)
                except ValueError:
                    if raw.strip() not in {"", "NA", "N/A"}:
                        raise SourceError(f"Nonnumeric {field} in row {row_number}") from None
                    number = None
                if number is not None and not math.isfinite(number):
                    number = None
                if number is None:
                    flags.append({"row": row_number, "field": field, "reason": "missing_or_nonfinite", "raw_token": raw})
                values.append(number)
            stations.append(row[1])
            original_indices.append(row[0])
            line_ends.append(reader.line_num)
            geographic.append(values[:2])
            xyz.append(values[2:5])
            for name, number in zip(CHANNELS, values[5:]):
                observed[name].append(number)
            lon, lat = values[:2]
            if (lon is not None and not -180 <= lon <= 180) or (lat is not None and not -90 <= lat <= 90):
                flags.append({"row": row_number, "field": "longitude_latitude", "reason": "geographic_range"})
            x, y = values[2:4]
            if (x is not None and not 100000 <= x <= 900000) or (y is not None and not 0 <= y <= 10000000):
                flags.append({"row": row_number, "field": "author_xy", "reason": "declared_utm_range"})
            og, ttc = values[5], values[8]
            if og is not None and not 900000 <= og <= 1100000:
                flags.append({"row": row_number, "field": "OG", "reason": "terrestrial_gravity_mgal_range"})
            if ttc is not None and ttc < 0:
                flags.append({"row": row_number, "field": "TTC", "reason": "negative_terrain_correction"})
    if not stations:
        raise SourceError("Empty principal-fact source")
    if _digest_file(path) != identity:
        raise SourceError("Principal-fact bytes changed during inspection")
    duplicates = sorted(name for name, count in Counter(stations).items() if count > 1)
    coordinates = Counter(tuple(row) for row in xyz if None not in row)
    duplicate_xyz = [list(key) for key, count in coordinates.items() if count > 1]
    bounds = {}
    for name, values in observed.items():
        valid = [value for value in values if value is not None]
        bounds[name] = {"min": min(valid) if valid else None, "max": max(valid) if valid else None,
                        "valid_count": len(valid), "missing_count": len(values) - len(valid)}
    correction_difference = [cba - sba - ttc if None not in (cba, sba, ttc) else None
                             for cba, sba, ttc in zip(observed["CBA"], observed["SBA"], observed["TTC"])]
    return {
        "schema": "geophysics.principal-fact-inspection/v1", "source_id": source["source_id"],
        "raw_sha256": identity[1], "raw_bytes": identity[0], "row_count": len(stations),
        "source_archive_sha256": source.get("sha256"), "original_row_indices": original_indices,
        "source_csv_line_ends": line_ends,
        "station_ids": stations, "geographic_lon_lat": geographic, "author_xyz_m": xyz,
        "channels_mgal": observed, "channel_bounds": bounds,
        "cba_minus_sba_minus_ttc_mgal": correction_difference,
        "horizontal_reference": "Author labels WGS84 longitude/latitude and WGS84 UTM10N projected channels",
        "vertical_reference": "unresolved: zWGS84 label alone does not specify its datum/transformation",
        "uncertainty": {"kind": "unavailable", "reason": "Source CSV has no measurement-error column"},
        "flags": flags, "duplicate_station_ids": duplicates, "duplicate_author_xyz": duplicate_xyz, "excluded_rows": [],
        "correction_state": {
            "OG": "observed gravity in author compilation; original provider tide/drift/base ties already applied",
            "FAA": "provider free-air anomaly", "SBA": "provider simple Bouguer anomaly",
            "TTC": "provider total terrain correction", "CBA": "provider complete Bouguer anomaly",
            "ISO": "provider isostatic anomaly",
        },
        "correction_state_evidence": "Original FGDC processing attribution; author station/channel lineage not independently verified",
        "corrections_applied_by_intake": False,
        "modelling_eligible": False,
        "ineligible_reasons": ["Unresolved original/author vertical datum and transform", "Measurement uncertainties absent",
                               "Author compilation needs station-level original-source/processing lineage review"],
        "rights_decision": source["rights_decision"], "rights_statement": source["rights_statement"],
        "citation": source["citation"], "inversion_performed": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", default=AUTHOR_SOURCE, choices=[AUTHOR_SOURCE])
    parser.add_argument("--file", type=Path, help="Already downloaded pinned ZIP; never an arbitrary URL")
    parser.add_argument("--output", type=Path, help="New ignored local inspection JSON; existing files are never replaced")
    args = parser.parse_args(argv)
    try:
        record, raw, _ = acquire_source(args.source_id, local_file=args.file)
        receipt = extract_selected(record, raw)
        member = next(item for item in receipt["members"] if item["name"] == "data/ground_gravity_data.csv")
        result = profile_gravity(ROOT / member["path"], source=record)
        result["member_receipt_sha256"] = hashlib.sha256(canonical(receipt)).hexdigest()
        result["profiled_at_utc"] = datetime.now(timezone.utc).isoformat()
        if args.output:
            target = args.output.absolute()
            if not target.is_relative_to(ROOT / "data/raw"):
                raise SourceError("Inspection output must stay in ignored data/raw, outside public artifacts")
            key = PurePosixPath(target.relative_to(ROOT).as_posix())
            target = safe_target(ROOT, key, "raw")
            if target.exists():
                raise SourceError("Inspection output already exists; choose a new path, do not replace it")
            publish_bytes(target, canonical(result))
        print(json.dumps({key: result[key] for key in ("source_id", "raw_sha256", "row_count", "channel_bounds",
                                                       "duplicate_station_ids", "ineligible_reasons", "inversion_performed")}, indent=2))
    except (SourceError, OSError, UnicodeError, csv.Error, KeyError, ValueError) as error:
        print(f"Source inspection failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
