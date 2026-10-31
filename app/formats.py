"""Bounded raw-envelope and declared-physics checks; not scientific ingestion."""

from __future__ import annotations

import csv
import math
import struct
from datetime import datetime
from pathlib import Path

from defusedxml.ElementTree import iterparse
from pyproj import CRS
from pyproj.exceptions import CRSError

from app.errors import ApiError
from app.schemas import RawUploadInput


EXTENSIONS = {
    "gravity_csv": ".csv", "magnetic_csv": ".csv", "traveltime_csv": ".csv", "ert_csv": ".csv",
    "geotiff": (".tif", ".tiff"), "edi": ".edi", "miniseed": (".mseed", ".msd"),
    "stationxml": ".xml", "segy": (".sgy", ".segy"), "mth5": ".h5",
    "ert_ohm": ".ohm", "traveltime_sgt": ".sgt",
}
MIMES = {
    "ert_ohm": {"text/plain", "application/octet-stream"},
    "traveltime_sgt": {"text/plain", "application/octet-stream"},
    "gravity_csv": {"text/csv"}, "magnetic_csv": {"text/csv"},
    "traveltime_csv": {"text/csv"}, "ert_csv": {"text/csv"},
    "geotiff": {"image/tiff", "application/geotiff"},
    "edi": {"text/plain", "application/octet-stream"},
    "miniseed": {"application/vnd.fdsn.mseed", "application/octet-stream"},
    "stationxml": {"application/xml", "text/xml"},
    "segy": {"application/x-segy", "application/octet-stream"},
    "mth5": {"application/x-hdf5", "application/octet-stream"},
}
UNITS = {
    "ert_ohm": {"ohm"}, "traveltime_sgt": {"s"},
    "gravity_csv": {"mGal", "m/s2"}, "magnetic_csv": {"nT"}, "geotiff": {"nT", "mGal"},
    "edi": {"ohm", "mV/km/nT"}, "ert_csv": {"ohm", "V", "ohm.m"},
    "miniseed": {"counts", "m/s", "m/s2"}, "stationxml": {"counts", "m/s", "m/s2"},
    "traveltime_csv": {"s", "ms"}, "segy": {"counts", "Pa", "m/s"}, "mth5": {"counts", "mV/km", "nT"},
}
GEOMETRY_FIELDS = {
    "ert_ohm": ("electrode_count", "measurement_count"),
    "traveltime_sgt": ("sensor_count", "measurement_count"),
    "gravity_csv": ("station_id_column", "x_column", "y_column", "z_column", "value_column"),
    "magnetic_csv": ("line_id_column", "x_column", "y_column", "z_column", "value_column"),
    "traveltime_csv": ("source_x_column", "source_y_column", "receiver_x_column", "receiver_y_column", "time_column"),
    "ert_csv": ("a_column", "b_column", "m_column", "n_column", "electrode_count"),
    "geotiff": ("rows", "columns", "pixel_width", "pixel_height"),
    "edi": ("station_id", "frequency_count", "tensor_components", "rotation_degrees"),
    "miniseed": ("network", "station", "channels", "sample_rate_hz", "start_utc", "end_utc", "stationxml_asset_id"),
    "stationxml": ("network", "station", "channels", "response_epoch_utc"),
    "segy": ("source_count", "receiver_count", "sample_interval_us", "samples_per_trace", "coordinate_scalar"),
    "mth5": ("survey_id", "station_id", "run_id", "channels", "start_utc", "end_utc"),
}
POSITIVE_FIELDS = {
    "sensor_count", "measurement_count",
    "electrode_count", "rows", "columns", "pixel_width", "pixel_height", "frequency_count", "sample_rate_hz",
    "source_count", "receiver_count", "sample_interval_us", "samples_per_trace",
}
INTEGER_FIELDS = {"electrode_count", "sensor_count", "measurement_count", "rows", "columns", "frequency_count", "source_count", "receiver_count", "sample_interval_us", "samples_per_trace"}
LIST_FIELDS = {"tensor_components", "channels"}
CSV_FORMATS = {"gravity_csv", "magnetic_csv", "traveltime_csv", "ert_csv"}
MIB = 1024 * 1024
FORMAT_MAX_BYTES = {
    "ert_ohm": 1_000_000, "traveltime_sgt": 1_000_000,
    "gravity_csv": 50 * MIB, "magnetic_csv": 50 * MIB, "traveltime_csv": 50 * MIB,
    "ert_csv": 50 * MIB, "geotiff": 200 * MIB, "edi": 5 * MIB,
    "miniseed": 200 * MIB, "stationxml": 20 * MIB, "segy": 200 * MIB, "mth5": 200 * MIB,
}
COMPONENT_FRAMES = {
    "ert_ohm": {"ABMN"}, "traveltime_sgt": {"source-receiver"},
    "gravity_csv": {"local vertical down", "local vertical up"},
    "magnetic_csv": {"total field", "ENU", "NED"},
    "geotiff": {"total field", "local vertical down", "local vertical up"},
    "edi": {"geographic ENU", "instrument axes"},
    "ert_csv": {"ABMN"},
    "traveltime_csv": {"source-receiver"},
    "miniseed": {"channel azimuth/dip"},
    "stationxml": {"channel azimuth/dip"},
    "segy": {"source-receiver"},
    "mth5": {"channel azimuth/dip"},
}


def _utc_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None
    except ValueError:
        return None


def _datum_label(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def validate_declared_metadata(meta: RawUploadInput) -> None:
    physical = meta.physical
    fields: list[str] = []
    if physical.coordinate_reference == "epsg" and physical.epsg is None:
        fields.append("physical.epsg")
    if physical.coordinate_reference == "local" and not physical.local_crs:
        fields.append("physical.local_crs")
    if physical.coordinate_reference == "local" and physical.horizontal_unit == "degree":
        fields.append("physical.horizontal_unit")
    if physical.coordinate_reference == "epsg" and physical.epsg is not None:
        try:
            crs = CRS.from_epsg(physical.epsg)
        except CRSError:
            fields.append("physical.epsg")
        else:
            declared_datum = _datum_label(physical.horizontal_datum)
            official_datum = _datum_label(crs.datum.name) if crs.datum is not None else ""
            standard_aliases = {
                "worldgeodeticsystem1984ensemble": {"wgs84", "wgs1984"},
                "northamericandatum1983": {"nad83"},
            }
            if declared_datum not in {official_datum} | standard_aliases.get(official_datum, set()):
                fields.append("physical.horizontal_datum")
            if crs.is_geographic and physical.horizontal_unit != "degree":
                fields.append("physical.horizontal_unit")
            if crs.is_geographic and physical.axis_order not in ("lon_lat", "lat_lon"):
                fields.append("physical.axis_order")
            elif crs.is_projected:
                unit = crs.axis_info[0].unit_conversion_factor if crs.axis_info else None
                expected = "km" if unit == 1000 else "m" if unit == 1 else None
                if expected is None or physical.horizontal_unit != expected:
                    fields.append("physical.horizontal_unit")
                if physical.axis_order not in ("xy", "yx"):
                    fields.append("physical.axis_order")
            elif not crs.is_geographic:
                fields.append("physical.epsg")
    if physical.measurement_unit not in UNITS[meta.format]:
        fields.append("physical.measurement_unit")
    if physical.component_frame not in COMPONENT_FRAMES[meta.format]:
        fields.append("physical.component_frame")
    if meta.format in {"ert_ohm", "traveltime_sgt"}:
        for name, expected in (("coordinate_reference", "local"), ("axis_order", "xy"),
                               ("horizontal_unit", "m"), ("vertical_unit", "m"),
                               ("vertical_positive", "up")):
            if getattr(physical, name) != expected:
                fields.append("physical."+name)
    geometry = physical.geometry
    for key in GEOMETRY_FIELDS[meta.format]:
        value = geometry.get(key)
        if value is None or value == "" or (isinstance(value, str) and not value.strip()):
            fields.append(f"physical.geometry.{key}")
        elif key in POSITIVE_FIELDS and (isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0):
            fields.append(f"physical.geometry.{key}")
        elif key in INTEGER_FIELDS and type(value) is not int:
            fields.append(f"physical.geometry.{key}")
        elif key in LIST_FIELDS and (not isinstance(value, list) or not value or not all(isinstance(x, str) and x for x in value)):
            fields.append(f"physical.geometry.{key}")
        elif key not in POSITIVE_FIELDS | LIST_FIELDS | {"rotation_degrees", "coordinate_scalar"} and not isinstance(value, str):
            fields.append(f"physical.geometry.{key}")
        elif key in POSITIVE_FIELDS and isinstance(value, float) and not math.isfinite(value):
            fields.append(f"physical.geometry.{key}")
    if fields:
        raise ApiError(422, "physical_metadata_invalid", "Physical metadata is incomplete or invalid", sorted(set(fields)))
    if meta.format in CSV_FORMATS:
        columns = [geometry.get(key) for key in GEOMETRY_FIELDS[meta.format] if key.endswith("_column")]
        if all(isinstance(column, str) for column in columns) and len(columns) != len(set(columns)):
            fields.append("physical.geometry")
    if meta.format == "edi" and geometry.get("tensor_components"):
        if not set(geometry["tensor_components"]).issuperset({"Zxx", "Zxy", "Zyx", "Zyy"}) or not set(
            geometry["tensor_components"]
        ).issubset({"Zxx", "Zxy", "Zyx", "Zyy", "Tx", "Ty"}):
            fields.append("physical.geometry.tensor_components")
    if meta.format == "edi" and (isinstance(geometry.get("rotation_degrees"), bool) or not isinstance(geometry.get("rotation_degrees"), (int, float)) or not math.isfinite(
        geometry["rotation_degrees"]
    ) or not -360 <= geometry["rotation_degrees"] <= 360):
        fields.append("physical.geometry.rotation_degrees")
    if meta.format == "segy" and (type(geometry.get("coordinate_scalar")) is not int or geometry["coordinate_scalar"] == 0):
        fields.append("physical.geometry.coordinate_scalar")
    if meta.format in {"miniseed", "stationxml", "mth5"}:
        channels = geometry.get("channels")
        orientations = geometry.get("channel_orientation_deg")
        if not isinstance(orientations, dict) or not isinstance(channels, list) or set(orientations) != set(channels):
            fields.append("physical.geometry.channel_orientation_deg")
        elif any(
            not isinstance(pair, list) or len(pair) != 2
            or any(isinstance(angle, bool) or not isinstance(angle, (int, float)) or not math.isfinite(angle) for angle in pair)
            or not 0 <= pair[0] < 360 or not -90 <= pair[1] <= 90
            for pair in orientations.values()
        ):
            fields.append("physical.geometry.channel_orientation_deg")
    if meta.format in {"miniseed", "mth5"}:
        start = _utc_time(geometry.get("start_utc"))
        end = _utc_time(geometry.get("end_utc"))
        if start is None or end is None or start >= end:
            fields.extend(["physical.geometry.start_utc", "physical.geometry.end_utc"])
    if meta.format == "stationxml" and _utc_time(geometry.get("response_epoch_utc")) is None:
        fields.append("physical.geometry.response_epoch_utc")
    if fields:
        raise ApiError(422, "physical_metadata_invalid", "Physical metadata is incomplete or invalid", sorted(set(fields)))


def _csv_header(path: Path) -> list[str]:
    try:
        with path.open("rb") as binary:
            first = binary.readline(65537)
            second = binary.readline(65537)
        if len(first) > 65536 or not second or b"\x00" in first + second:
            raise ValueError("missing rows or binary content")
        header = next(csv.reader([first.decode("utf-8-sig", errors="strict")]))
        next(csv.reader([second.decode("utf-8", errors="strict")]))
        if not header or len(set(header)) != len(header) or any(not x.strip() for x in header):
            raise ValueError("empty or duplicate CSV header")
        return header
    except (UnicodeError, ValueError, csv.Error) as exc:
        raise ApiError(415, "format_invalid", "CSV envelope is invalid") from exc


def _geotiff_shape(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as stream:
        lead = stream.read(8)
        if len(lead) != 8 or lead[:4] not in (b"II*\x00", b"MM\x00*"):
            return None
        endian = "<" if lead[:2] == b"II" else ">"
        offset = struct.unpack(endian + "I", lead[4:8])[0]
        if offset < 8 or offset > path.stat().st_size - 2:
            return None
        stream.seek(offset)
        count = struct.unpack(endian + "H", stream.read(2))[0]
        if count > 4096 or offset + 2 + 12 * count > path.stat().st_size:
            return None
        tags = {}
        for _ in range(count):
            entry = stream.read(12)
            tag, kind, length = struct.unpack(endian + "HHI", entry[:8])
            if tag in (256, 257) and length == 1 and kind in (3, 4):
                tags[tag] = struct.unpack(endian + ("H" if kind == 3 else "I"), entry[8:10] if kind == 3 else entry[8:12])[0]
            elif tag in (34735, 33550, 33922):
                tags[tag] = True
        if 34735 not in tags and not (33550 in tags and 33922 in tags):
            return None
        if not isinstance(tags.get(256), int) or not isinstance(tags.get(257), int):
            return None
        return tags[257], tags[256]


def validate_file_envelope(path: Path, meta: RawUploadInput) -> None:
    suffix = EXTENSIONS[meta.format]
    allowed_suffixes = (suffix,) if isinstance(suffix, str) else suffix
    if not meta.filename.lower().endswith(allowed_suffixes) or meta.mime not in MIMES[meta.format]:
        raise ApiError(415, "mime_format_mismatch", "Filename, MIME and declared format must agree")
    with path.open("rb") as stream:
        head = stream.read(8192)
    if head.startswith((b"PK\x03\x04", b"\x1f\x8b", b"7z\xbc\xaf\x27\x1c", b"Rar!")) or head[257:262] == b"ustar":
        raise ApiError(415, "archive_forbidden", "Archive uploads are not accepted")
    format_name = meta.format
    if format_name in {"ert_ohm", "traveltime_sgt"}:
        if path.stat().st_size > FORMAT_MAX_BYTES[format_name]:
            raise ApiError(413, "upload_too_large", "Original profile exceeds its parser limit")
        # Only the bounded original grammar is parsed here. Native inversion is
        # never imported during an authenticated upload/admission transaction.
        from app.profile_contract import _workflow
        _workflow()
        try:
            if format_name == "ert_ohm":
                from ert import parse_ohm_bytes
                survey = parse_ohm_bytes(path.read_bytes())
                count, rows = len(survey.sensors_xz_m), len(survey.abmn)
                sensor_key = "electrode_count"
            else:
                from traveltime import parse_sgt_bytes
                survey = parse_sgt_bytes(path.read_bytes())
                count, rows = len(survey.sensor_xy_m), len(survey.shot_geophone)
                sensor_key = "sensor_count"
            geometry = meta.physical.geometry
            if geometry[sensor_key] != count or geometry["measurement_count"] != rows:
                raise ValueError("declared profile counts differ")
        except (ValueError, RuntimeError, KeyError, TypeError):
            raise ApiError(415, "format_invalid", "Original profile grammar or declared counts are invalid")
        return
    if format_name in CSV_FORMATS:
        columns = _csv_header(path)
        missing = []
        for field in GEOMETRY_FIELDS[format_name]:
            if field.endswith("_column") and meta.physical.geometry.get(field) not in columns:
                missing.append(f"physical.geometry.{field}")
        if missing:
            raise ApiError(422, "geometry_column_missing", "Declared geometry columns are absent", missing)
        return
    good = False
    if format_name == "geotiff":
        shape = _geotiff_shape(path)
        good = shape is not None and shape == (
            meta.physical.geometry.get("rows"), meta.physical.geometry.get("columns"),
        )
    elif format_name == "edi":
        good = path.stat().st_size >= 128 and b">HEAD" in head.upper() and b">FREQ" in head.upper()
    elif format_name == "miniseed":
        good = path.stat().st_size >= 256 and (
            head.startswith(b"MS\x03") or (len(head) >= 8 and head[:6].isdigit() and head[6:7] in (b"D", b"R", b"Q", b"M"))
        )
    elif format_name == "stationxml":
        try:
            root_seen = False
            networks: set[str] = set()
            stations: set[str] = set()
            channels: set[str] = set()
            for event, element in iterparse(path, events=("start", "end")):
                if event == "start":
                    name = element.tag.rsplit("}", 1)[-1]
                    if not root_seen:
                        root_seen = True
                        if name != "FDSNStationXML":
                            raise ValueError("wrong XML root")
                    elif name == "Network":
                        networks.add(element.attrib.get("code", ""))
                    elif name == "Station":
                        stations.add(element.attrib.get("code", ""))
                    elif name == "Channel":
                        channels.add(element.attrib.get("code", ""))
                else:
                    element.clear()
            geometry = meta.physical.geometry
            good = (
                root_seen and geometry["network"] in networks and geometry["station"] in stations
                and set(geometry["channels"]).issubset(channels)
            )
        except Exception as exc:
            raise ApiError(415, "format_invalid", "StationXML envelope is invalid") from exc
    elif format_name == "segy":
        if path.stat().st_size > 3600:
            with path.open("rb") as stream:
                stream.seek(3216)
                binary = stream.read(10)
            interval, samples, data_format = struct.unpack(">HHH", binary[:2] + binary[4:6] + binary[8:10])
            good = interval > 0 and samples > 0 and data_format in {1, 2, 3, 5, 8}
            good = good and interval == meta.physical.geometry.get("sample_interval_us")
            good = good and samples == meta.physical.geometry.get("samples_per_trace")
    elif format_name == "mth5":
        good = path.stat().st_size >= 4096 and head.startswith(b"\x89HDF\r\n\x1a\n")
    if not good:
        raise ApiError(415, "format_invalid", "Bytes do not match the declared raw format")
