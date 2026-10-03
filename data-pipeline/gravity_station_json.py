"""Strict bounded LOCAL physical root JSON; structural acceptance only.

No scientific calculation or provider, field, method or host eligibility is
conferred. The caller retains original bytes and owns the returned native dict.
"""

from __future__ import annotations

import json
import math


MAX_RAW_BYTES = 16777216
MAX_CANONICAL_BYTES = 8388608
MAX_DEPTH = 16
MAX_NODES = 200000
MAX_KEY_BYTES = 128
MAX_STRING_BYTES = 8192
MAX_NUMERIC_LEXEME = 128
MAX_INTEGER = 9007199254740991

_MESSAGES = {
    "gravity_json_type": "Input must be exact bytes.",
    "gravity_json_limit": "Input exceeds the local physical JSON bounds.",
    "gravity_json_invalid": "Input is not strict physical JSON.",
    "gravity_json_contract": "Input does not match the physical root contract.",
}
_STATES = ("observed_absolute", "gravity_disturbance", "bouguer_disturbance", "terrain_adjusted_disturbance")
_LENGTHS = (0, 2, 3, 4)
_HISTORY = ("normal_reference", "elevation_reference", "bouguer_plate", "terrain_residual")
_META = frozenset(("source_kind", "source_sha256", "source_citation", "rights", "crs", "reference_ellipsoid",
                   "height_datum", "height_unit", "height_sign", "gravity_unit", "gravity_sign", "gravity_quantity",
                   "gravity_datum", "tide_system", "instrument_processing"))
_STATION = frozenset(("station_id", "latitude_deg", "longitude_deg", "receiver_height_m", "surface_height_m",
                      "original_value", "value_mgal", "gravity_sigma", "receiver_sigma_m", "surface_sigma_m",
                      "latitude_sigma_deg"))


class GravityStationsJsonError(ValueError):
    """Expected input failure; fixed safe code/message and known schema field."""

    def __init__(self, code: str, field: str):
        self.code = code
        self.field = field
        self.message = _MESSAGES[code]
        super().__init__(self.message)


def _fail(code="gravity_json_invalid", field="document"):
    raise GravityStationsJsonError(code, field)


def _need(condition, field):
    if not condition:
        _fail("gravity_json_contract", field)


def _hex4(raw, index):
    if index + 4 > len(raw):
        _fail()
    value = 0
    for i in range(index, index + 4):
        byte = raw[i]
        if 48 <= byte <= 57:
            digit = byte - 48
        elif 65 <= byte <= 70:
            digit = byte - 55
        elif 97 <= byte <= 102:
            digit = byte - 87
        else:
            _fail()
        value = (value << 4) | digit
    return value


def _utf8_point(raw, index):
    first = raw[index]
    if first < 128:
        return first, 1
    if 194 <= first <= 223:
        width, point, minimum = 2, first & 31, 128
    elif 224 <= first <= 239:
        width, point, minimum = 3, first & 15, 2048
    elif 240 <= first <= 244:
        width, point, minimum = 4, first & 7, 65536
    else:
        _fail()
    if index + width > len(raw):
        _fail()
    for i in range(index + 1, index + width):
        byte = raw[i]
        if not 128 <= byte <= 191:
            _fail()
        point = (point << 6) | (byte & 63)
    if point < minimum or point > 1114111 or 55296 <= point <= 57343:
        _fail()
    return point, width


def _string(raw, index, key, remaining):
    """Bound decoded bytes and canonical size scalar-by-scalar, never slice a giant token."""
    index += 1
    decoded, canonical = 0, 2
    limit = MAX_KEY_BYTES if key else MAX_STRING_BYTES
    # Only keys need token-local text for decoded duplicate detection.
    chars = [] if key else None
    if canonical > remaining:
        _fail("gravity_json_limit")
    while index < len(raw):
        byte = raw[index]
        if byte == 34:
            return index + 1, canonical, "".join(chars) if key else None
        if byte == 92:
            index += 1
            if index >= len(raw):
                _fail()
            escape = raw[index]
            index += 1
            if escape in (34, 92, 47):
                point = escape
            elif escape == 98:
                point = 8
            elif escape == 102:
                point = 12
            elif escape == 110:
                point = 10
            elif escape == 114:
                point = 13
            elif escape == 116:
                point = 9
            elif escape == 117:
                point = _hex4(raw, index)
                index += 4
                if 55296 <= point <= 56319:
                    if not raw.startswith(b"\\u", index):
                        _fail()
                    low = _hex4(raw, index + 2)
                    if not 56320 <= low <= 57343:
                        _fail()
                    point = 65536 + ((point - 55296) << 10) + low - 56320
                    index += 6
                elif 56320 <= point <= 57343:
                    _fail()
            else:
                _fail()
        else:
            if byte < 32:
                _fail()
            point, width = _utf8_point(raw, index)
            index += width
        decoded += 1 if point < 128 else 2 if point < 2048 else 3 if point < 65536 else 4
        if decoded > limit:
            _fail("gravity_json_limit")
        if point in (8, 9, 10, 12, 13, 34, 92):
            canonical += 2
        elif point < 32 or 127 <= point <= 65535:
            canonical += 6
        elif point > 65535:
            canonical += 12
        else:
            canonical += 1
        if canonical > remaining:
            _fail("gravity_json_limit")
        if key:
            chars.append(chr(point))
    _fail()


def _number_token(raw, index, encoder):
    start = index
    size = len(raw)
    if raw[index] == 45:
        index += 1
    if index >= size:
        _fail()
    if raw[index] == 48:
        index += 1
        if index < size and 48 <= raw[index] <= 57:
            _fail()
    elif 49 <= raw[index] <= 57:
        while index < size and 48 <= raw[index] <= 57:
            index += 1
            if index - start > MAX_NUMERIC_LEXEME:
                _fail("gravity_json_limit")
    else:
        _fail()
    floating = False
    if index < size and raw[index] == 46:
        floating = True
        index += 1
        if index >= size or not 48 <= raw[index] <= 57:
            _fail()
        while index < size and 48 <= raw[index] <= 57:
            index += 1
            if index - start > MAX_NUMERIC_LEXEME:
                _fail("gravity_json_limit")
    if index < size and raw[index] in (69, 101):
        floating = True
        index += 1
        if index < size and raw[index] in (43, 45):
            index += 1
        if index >= size or not 48 <= raw[index] <= 57:
            _fail()
        while index < size and 48 <= raw[index] <= 57:
            index += 1
            if index - start > MAX_NUMERIC_LEXEME:
                _fail("gravity_json_limit")
    if index - start > MAX_NUMERIC_LEXEME:
        _fail("gravity_json_limit")
    token = raw[start:index]  # At most128 ASCII bytes, checked before slicing/conversion.
    value = float(token) if floating else int(token)
    if not floating and not -MAX_INTEGER <= value <= MAX_INTEGER:
        _fail("gravity_json_limit")
    if floating and not math.isfinite(value):
        _fail()
    return index, len(encoder.encode(value))


class _Frame:
    __slots__ = ("object", "state", "keys")

    def __init__(self, object_kind):
        self.object = object_kind
        self.state = "first"
        self.keys = set() if object_kind else None


def _scan(raw):
    """Full grammar and pre-allocation counters, with only bounded active frames."""
    index, nodes, canonical, deepest = 0, 0, 0, 0
    frames, root_seen = [], False
    encoder = json.JSONEncoder(ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    while True:
        while index < len(raw) and raw[index] in (32, 9, 10, 13):
            index += 1
        if not frames and root_seen:
            if index != len(raw):
                _fail()
            return canonical, nodes, deepest
        if index >= len(raw):
            _fail()
        byte = raw[index]
        frame = frames[-1] if frames else None
        if frame is not None:
            closing = 125 if frame.object else 93
            if frame.state == "first" and byte == closing:
                frames.pop()
                index += 1
                canonical += 1
                if canonical > MAX_CANONICAL_BYTES:
                    _fail("gravity_json_limit")
                continue
            if frame.state == "comma":
                if byte == closing:
                    frames.pop()
                elif byte == 44:
                    frame.state = "key" if frame.object else "value"
                else:
                    _fail()
                index += 1
                canonical += 1
                if canonical > MAX_CANONICAL_BYTES:
                    _fail("gravity_json_limit")
                continue
            if frame.object and frame.state in ("first", "key"):
                if byte != 34:
                    _fail()
                nodes += 1
                if nodes > MAX_NODES:
                    _fail("gravity_json_limit")
                index, count, key = _string(raw, index, True, MAX_CANONICAL_BYTES - canonical)
                if key in frame.keys:
                    _fail()
                frame.keys.add(key)
                canonical += count
                frame.state = "colon"
                continue
            if frame.object and frame.state == "colon":
                if byte != 58:
                    _fail()
                index += 1
                canonical += 1
                if canonical > MAX_CANONICAL_BYTES:
                    _fail("gravity_json_limit")
                frame.state = "value"
                continue
            frame.state = "comma"
        else:
            root_seen = True
        nodes += 1
        if nodes > MAX_NODES:
            _fail("gravity_json_limit")
        if byte in (123, 91):
            depth = len(frames) + 1
            if depth > MAX_DEPTH:
                _fail("gravity_json_limit")
            deepest = max(deepest, depth)
            frames.append(_Frame(byte == 123))
            index += 1
            canonical += 1
        elif byte == 34:
            index, count, _ = _string(raw, index, False, MAX_CANONICAL_BYTES - canonical)
            canonical += count
        elif byte == 45 or 48 <= byte <= 57:
            index, count = _number_token(raw, index, encoder)
            canonical += count
        elif raw.startswith(b"true", index):
            index += 4
            canonical += 4
        elif raw.startswith(b"false", index):
            index += 5
            canonical += 5
        elif raw.startswith(b"null", index):
            index += 4
            canonical += 4
        else:
            _fail()
        if canonical > MAX_CANONICAL_BYTES:
            _fail("gravity_json_limit")


def _materialize(raw):
    value, invalid = None, False
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except (ValueError, UnicodeError, OverflowError, RecursionError):
        invalid = True
    # Outside the catch block: no decoder exception/document in error context.
    if invalid:
        _fail()
    return value


def _keys(value, expected, field):
    _need(type(value) is dict and value.keys() == expected, field)


def _text(value, field):
    _need(type(value) is str and bool(value.strip()), field)


def _hash(value, field):
    _need(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value), field)


def _number(value, field, lower=-math.inf, upper=math.inf):
    _need(type(value) in (int, float) and math.isfinite(value) and lower <= value <= upper, field)


def _array(value, count, field, *, nonnegative=False):
    _need(type(value) is list and len(value) == count, field)
    for i, number in enumerate(value):
        _number(number, f"{field}[{i}]", 0 if nonnegative else -math.inf)


def _validate(root):
    _keys(root, frozenset(("schema_version", "metadata", "state", "stations", "history")), "root")
    _need(root["schema_version"] == "gravity-stations-1", "schema_version")
    _need(type(root["state"]) is str and root["state"] in _STATES, "state")
    meta = root["metadata"]
    _need(type(meta) is dict, "metadata")
    orthometric = meta.get("height_datum") == "orthometric"
    _keys(meta, _META | {"geoid_model"} if orthometric else _META, "metadata")
    for key in sorted(_META - {"instrument_processing"}):
        _text(meta[key], f"metadata.{key}")
    _hash(meta["source_sha256"], "metadata.source_sha256")
    for key, choices in (("source_kind", ("field", "synthetic_control")),
                         ("height_datum", ("ellipsoidal", "orthometric")),
                         ("gravity_unit", ("mGal", "m/s^2", "microGal")),
                         ("gravity_sign", ("upward", "downward"))):
        _need(meta[key] in choices, f"metadata.{key}")
    for key, literal in (("crs", "EPSG:4326"), ("reference_ellipsoid", "WGS84"), ("height_unit", "m"),
                         ("height_sign", "upward"), ("gravity_quantity", "absolute_gravity"), ("tide_system", "tide_free")):
        _need(meta[key] == literal, f"metadata.{key}")
    if orthometric:
        _text(meta["geoid_model"], "metadata.geoid_model")
    instrument = meta["instrument_processing"]
    _keys(instrument, frozenset(("calibration", "drift", "tide")), "metadata.instrument_processing")
    for key in ("calibration", "drift", "tide"):
        field = f"metadata.instrument_processing.{key}"
        entry = instrument[key]
        _keys(entry, frozenset(("status", "citation")), field)
        _need(type(entry["status"]) is str and entry["status"] in ("applied", "not_applicable"), field + ".status")
        if key == "calibration":
            _need(entry["status"] == "applied", field + ".status")
        _text(entry["citation"], field + ".citation")
    rows = root["stations"]
    _need(type(rows) is list and 1 <= len(rows) <= 400, "stations")
    ids = set()
    for i, row in enumerate(rows):
        field = f"stations[{i}]"
        _keys(row, _STATION | {"geoid_m", "geoid_sigma_m"} if orthometric else _STATION, field)
        _text(row["station_id"], field + ".station_id")
        _need(row["station_id"] not in ids, field + ".station_id")
        ids.add(row["station_id"])
        _number(row["latitude_deg"], field + ".latitude_deg", -90, 90)
        _number(row["longitude_deg"], field + ".longitude_deg", -180, 180)
        for key in ("receiver_height_m", "surface_height_m", "original_value", "value_mgal"):
            _number(row[key], field + "." + key)
        for key in ("gravity_sigma", "receiver_sigma_m", "surface_sigma_m", "latitude_sigma_deg"):
            _number(row[key], field + "." + key, 0)
        if orthometric:
            _number(row["geoid_m"], field + ".geoid_m")
            _number(row["geoid_sigma_m"], field + ".geoid_sigma_m", 0)
    history = root["history"]
    count = _LENGTHS[_STATES.index(root["state"])]
    _need(type(history) is list and len(history) == count, "history")
    for i, record in enumerate(history):
        field = f"history[{i}]"
        _keys(record, frozenset(("name", "parameters", "additions_mgal", "input_values_sha256", "output_values_sha256")), field)
        _need(record["name"] == _HISTORY[i], field + ".name")
        _hash(record["input_values_sha256"], field + ".input_values_sha256")
        _hash(record["output_values_sha256"], field + ".output_values_sha256")
        _array(record["additions_mgal"], len(rows), field + ".additions_mgal")
        params, path = record["parameters"], field + ".parameters"
        if i < 2:
            expected = {"ellipsoid", "height_reference", "boule"}
            if i == 1:
                expected.add("height_term")
            _keys(params, expected, path)
            for key, literal in (("ellipsoid", "WGS84"), ("height_reference", "WGS84_ellipsoid"), ("boule", "0.5.0")):
                _need(params[key] == literal, path + "." + key)
            if i == 1:
                _need(params["height_term"] == "gamma(phi,0)-gamma(phi,h)", path + ".height_term")
        elif i == 2:
            _keys(params, frozenset(("harmonica", "density_kg_m3", "density_sigma_kg_m3", "geometry", "height_reference")), path)
            for key, literal in (("harmonica", "0.7.0"), ("geometry", "land_infinite_plate"), ("height_reference", "WGS84_ellipsoid")):
                _need(params[key] == literal, path + "." + key)
            _number(params["density_kg_m3"], path + ".density_kg_m3", 1, 10000)
            _number(params["density_sigma_kg_m3"], path + ".density_sigma_kg_m3", 0, 10000)
        else:
            _keys(params, frozenset(("kind", "unit", "height_reference", "density_kg_m3", "source_sha256",
                                     "method", "station_ids", "additions_mgal", "sigma_mgal")), path)
            for key, literal in (("kind", "additive_residual_to_plate"), ("unit", "mGal"), ("height_reference", "WGS84_ellipsoid")):
                _need(params[key] == literal, path + "." + key)
            _number(params["density_kg_m3"], path + ".density_kg_m3", 1, 10000)
            _hash(params["source_sha256"], path + ".source_sha256")
            _text(params["method"], path + ".method")
            _need(type(params["station_ids"]) is list and params["station_ids"] == [r["station_id"] for r in rows], path + ".station_ids")
            _array(params["additions_mgal"], len(rows), path + ".additions_mgal")
            _array(params["sigma_mgal"], len(rows), path + ".sigma_mgal", nonnegative=True)


def _check_canonical(value, expected):
    count, invalid, exceeded = 0, False, False
    try:
        encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        for fragment in encoder.iterencode(value):
            count += len(fragment.encode("utf-8"))
            if count > MAX_CANONICAL_BYTES:
                exceeded = True
                break
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError):
        invalid = True
    if invalid:
        _fail()
    if exceeded:
        _fail("gravity_json_limit")
    if count != expected:
        _fail()


def load_gravity_stations_json(raw: bytes) -> dict:
    """Decode a bounded structural root, preserving native semantics, not certifying physics."""
    if type(raw) is not bytes:
        _fail("gravity_json_type", "raw")
    if len(raw) > MAX_RAW_BYTES:
        _fail("gravity_json_limit", "raw")
    if not raw or raw.startswith(b"\xef\xbb\xbf"):
        _fail()
    canonical, _, _ = _scan(raw)
    value = _materialize(raw)
    _validate(value)
    _check_canonical(value, canonical)
    return value
