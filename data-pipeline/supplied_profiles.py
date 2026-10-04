"""Explicit local originals to physically computed M07/M09 portable results.

Trusted local directories are required. Hash binding is not a sandbox against
another process owned by the operator; host admission remains a separate layer.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_METADATA_BYTES = 64 * 1024
MAX_RESULT_BYTES = 32 * 1024 * 1024
METADATA_SCHEMA = "geophysics.supplied-profile/v1"
RESULT_SCHEMA = "geophysics.supplied-profile-result/v1"
MANIFEST_SCHEMA = "geophysics.supplied-profile-manifest/v1"
METHODS = {"ert.topographic-profile/v1": "ert",
           "traveltime.first-arrival-profile/v1": "traveltime"}
HEX = re.compile(r"[0-9a-f]{64}\Z")


class ProfileError(ValueError):
    """Closed admission, source binding or portable result failure."""


def _plain(value):
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise ProfileError("non-text object key")
        for item in value.values():
            _plain(item)
    elif type(value) is list:
        for item in value:
            _plain(item)
    elif type(value) not in (str, int, float, bool, type(None)):
        raise ProfileError("non-plain JSON value")


def _encode(value):
    _plain(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ProfileError("invalid finite JSON") from error


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProfileError("duplicate JSON key")
        result[key] = value
    return result


def _decode(raw, ceiling):
    if type(raw) is not bytes or len(raw) > ceiling:
        raise ProfileError("JSON byte bound")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ProfileError("nonfinite JSON")))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ProfileError("invalid closed JSON") from error


def _keys(value, names):
    if type(value) is not dict or set(value) != set(names.split()):
        raise ProfileError("closed object fields")


def _text(value):
    if type(value) is not str or not value.strip() or len(value) > 256:
        raise ProfileError("bounded nonempty text required")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ProfileError("control character in text")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise ProfileError("invalid text encoding") from error


def _digest(value):
    if type(value) is not str or not HEX.fullmatch(value):
        raise ProfileError("invalid SHA256")


def parse_metadata(raw: bytes) -> dict:
    meta = _decode(raw, MAX_METADATA_BYTES)
    _keys(meta, "schema method source frame weights")
    if meta["schema"] != METADATA_SCHEMA or type(meta["method"]) is not str or meta["method"] not in METHODS:
        raise ProfileError("unsupported profile schema or method")
    source = meta["source"]
    _keys(source, "source_id kind citation rights sha256 bytes")
    for key in ("source_id", "citation"):
        _text(source[key])
    if type(source["kind"]) is not str or source["kind"] not in {"user_upload", "field", "synthetic_control"}:
        raise ProfileError("unsupported source kind")
    _digest(source["sha256"])
    if type(source["bytes"]) is not int or not 0 < source["bytes"] <= MAX_INPUT_BYTES:
        raise ProfileError("invalid original byte count")
    rights = source["rights"]
    _keys(rights, "holder processing_allowed redistribution_allowed")
    _text(rights["holder"])
    if rights["processing_allowed"] is not True or type(rights["redistribution_allowed"]) is not bool:
        raise ProfileError("explicit processing permission and publication decision required")
    frame = meta["frame"]
    _keys(frame, "horizontal_reference vertical_datum coordinate_unit vertical_positive profile_axes")
    _text(frame["horizontal_reference"])
    _text(frame["vertical_datum"])
    if (frame["coordinate_unit"] != "m" or frame["vertical_positive"] != "up"
            or frame["profile_axes"] != ["distance", "elevation"]):
        raise ProfileError("unsupported coordinates or axis convention")
    _keys(meta["weights"], "policy")
    if meta["weights"]["policy"] != "provider-example-conditional/v1":
        raise ProfileError("unsupported conditional weighting policy")
    return meta


def _identity(info):
    # CPython 3.12 Windows lstat reports birth-time as deprecated ctime while
    # fstat reports change-time. Birth-time is available consistently on both.
    epoch = info.st_birthtime_ns if os.name == "nt" else info.st_ctime_ns
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, epoch


def _read(path: Path, ceiling: int):
    path = Path(path)
    for component in (path, *path.parents):
        if component.is_symlink() or (hasattr(component, "is_junction") and component.is_junction()):
            raise ProfileError("linked path is not admitted")
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= ceiling:
            raise ProfileError("regular bounded file required")
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if _identity(opened) != _identity(before):
                raise ProfileError("original identity changed before read")
            raw = stream.read(ceiling + 1)
            after = os.fstat(stream.fileno())
        if (len(raw) != before.st_size or len(raw) > ceiling
                or _identity(after) != _identity(before) or _identity(path.lstat()) != _identity(before)):
            raise ProfileError("original changed during read")
    except OSError as error:
        raise ProfileError("file admission failed") from error
    return raw, _identity(before)


def read_metadata(path: Path) -> dict:
    return parse_metadata(_read(path, MAX_METADATA_BYTES)[0])


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def process_profile(path: Path, metadata: dict) -> dict:
    """Run both unchanged scientific challenges on an explicitly bound original."""
    meta = parse_metadata(_encode(metadata))
    raw, identity = _read(path, MAX_INPUT_BYTES)
    binding = {"sha256": _hash(raw), "bytes": len(raw)}
    if any(meta["source"][key] != value for key, value in binding.items()):
        raise ProfileError("original hash or count disagreement")
    # Fixed built-in imports; no caller callbacks or import paths.
    if METHODS[meta["method"]] == "ert":
        import ert as engine
        survey = engine.parse_ohm(Path(path))
        geometry = {"sensor_xz_m": survey.sensors_xz_m.tolist(),
                    "abmn_zero_based": survey.abmn.tolist(),
                    "row_ids_zero_based": list(range(len(survey.resistance_ohm)))}
    else:
        import traveltime as engine
        survey = engine.parse_sgt(Path(path))
        geometry = {"sensor_xy_m": survey.sensor_xy_m.tolist(),
                    "shot_geophone_zero_based": survey.shot_geophone.tolist(),
                    "row_ids_zero_based": list(range(len(survey.time_s)))}
    code = Path(engine.__file__)
    code_raw, code_identity = _read(code, MAX_INPUT_BYTES)
    wrapper_raw, wrapper_identity = _read(Path(__file__), MAX_INPUT_BYTES)
    if METHODS[meta["method"]] == "traveltime":
        report = engine.run(Path(path), source_sha256=binding["sha256"],
                            validation_policy="supplied-whole-shot/v1")
    else:
        report = engine.run(Path(path), source_sha256=binding["sha256"])
    fresh, fresh_identity = _read(path, MAX_INPUT_BYTES)
    if identity != fresh_identity or _hash(fresh) != binding["sha256"]:
        raise ProfileError("original changed during calculation")
    for code_path, prior, prior_identity in ((code, code_raw, code_identity),
                                           (Path(__file__), wrapper_raw, wrapper_identity)):
        observed, observed_identity = _read(code_path, MAX_INPUT_BYTES)
        if observed != prior or observed_identity != prior_identity:
            raise ProfileError("implementation changed during calculation")
    # Retain the legacy report, but never falsely assert provider source identity.
    report["source_id"] = meta["source"]["source_id"]
    report["rights_decision"] = "supplied-declaration-not-verified"
    report["raw_publication"] = False
    report["truth"] = None
    report["field_geology_claim"] = None
    if "unit_basis" in report:
        report["unit_basis"] = "explicit supplied metadata: profile coordinates metres; first arrivals seconds"
    result = {"schema": RESULT_SCHEMA, "method": meta["method"], "metadata": meta,
              "original": binding, "geometry": geometry, "engine_report": report,
              "code_hashes": {code.name: _hash(code_raw), "supplied_profiles.py": _hash(wrapper_raw)},
              "numerical_settings": dict(engine.INVERSE_OPTIONS),
              "scope": {"uploaded": False, "raw_copied": False, "execution": "explicit-local",
                        "rights": "operator-declaration-not-independent-permission-review",
                        "uncertainty": "assumed-not-calibrated", "truth_available": False,
                        "residual_convention": "predicted-minus-observed"}}
    result["content_sha256"] = _hash(_encode(result))
    _validate_result(result)
    return result


def _validate_result(result):
    _keys(result, "schema method metadata original geometry engine_report code_hashes numerical_settings scope content_sha256")
    meta = parse_metadata(_encode(result["metadata"]))
    if result["schema"] != RESULT_SCHEMA or result["method"] != meta["method"]:
        raise ProfileError("result schema or method disagreement")
    _keys(result["original"], "sha256 bytes")
    if result["original"] != {key: meta["source"][key] for key in ("sha256", "bytes")}:
        raise ProfileError("result original disagreement")
    report = result["engine_report"]
    if (type(report) is not dict or report.get("source_id") != meta["source"]["source_id"]
            or report.get("source_sha256") != result["original"]["sha256"]
            or report.get("truth") is not None or report.get("raw_publication") is not False
            or report.get("rights_decision") != "supplied-declaration-not-verified"
            or type(report.get("inverse_status")) is not str
            or report.get("inverse_status") not in {"passed", "ineligible", "unverified", "not-converged"}):
        raise ProfileError("engine report binding or verdict disagreement")
    expected_engine_schema = ("inverse-earth.local-ert-m07/v1" if METHODS[result["method"]] == "ert"
                              else "inverse-earth.local-traveltime-m09/v1")
    if report.get("schema") != expected_engine_schema or report.get("source_bytes") != result["original"]["bytes"]:
        raise ProfileError("engine method or original count disagreement")
    expected_code = "ert.py" if METHODS[result["method"]] == "ert" else "traveltime.py"
    _keys(result["code_hashes"], expected_code + " supplied_profiles.py")
    for value in result["code_hashes"].values():
        _digest(value)
    if type(result["numerical_settings"]) is not dict or not result["numerical_settings"]:
        raise ProfileError("numerical settings required")
    expected_scope = {"uploaded": False, "raw_copied": False, "execution": "explicit-local",
                      "rights": "operator-declaration-not-independent-permission-review",
                      "uncertainty": "assumed-not-calibrated", "truth_available": False,
                      "residual_convention": "predicted-minus-observed"}
    if _encode(result["scope"]) != _encode(expected_scope):
        raise ProfileError("supplied result scope disagreement")
    geometry = result["geometry"]
    sensor_key = "sensor_xz_m" if METHODS[result["method"]] == "ert" else "sensor_xy_m"
    pair_key = "abmn_zero_based" if METHODS[result["method"]] == "ert" else "shot_geophone_zero_based"
    _keys(geometry, f"{sensor_key} {pair_key} row_ids_zero_based")
    points, rows = geometry[sensor_key], geometry[pair_key]
    if (type(points) is not list or not 2 <= len(points) <= 1024
            or type(rows) is not list or not 4 <= len(rows) <= 100000):
        raise ProfileError("bounded original geometry required")
    for point in points:
        if (type(point) is not list or len(point) != 2
                or any(type(v) not in (int, float) for v in point)):
            raise ProfileError("original coordinate geometry")
    width = 4 if METHODS[result["method"]] == "ert" else 2
    for row in rows:
        if (type(row) is not list or len(row) != width
                or any(type(v) is not int or not 0 <= v < len(points) for v in row)
                or len(set(row)) != width):
            raise ProfileError("original measurement row geometry")
    if geometry["row_ids_zero_based"] != list(range(len(rows))):
        raise ProfileError("original measurement row identities")
    _digest(result["content_sha256"])
    if _hash(_encode({key: value for key, value in result.items() if key != "content_sha256"})) != result["content_sha256"]:
        raise ProfileError("result content digest disagreement")


def _exclusive(path, raw):
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise ProfileError("exclusive publication failed; partial files retained") from error


def export_result(result: dict, output: Path) -> dict:
    _validate_result(result)
    raw = _encode(result)
    if len(raw) > MAX_RESULT_BYTES:
        raise ProfileError("result byte bound")
    output = Path(output)
    try:
        output.mkdir(parents=False, exist_ok=False)
    except OSError as error:
        raise ProfileError("new explicit output directory required") from error
    _exclusive(output / "result.json", raw)
    manifest = {"schema": MANIFEST_SCHEMA, "result": {"name": "result.json", "bytes": len(raw),
                                                         "sha256": _hash(raw)},
                "method": result["method"], "source_sha256": result["original"]["sha256"],
                "content_sha256": result["content_sha256"],
                "configuration_sha256": _hash(_encode(result["numerical_settings"]))}
    _exclusive(output / "manifest.json", _encode(manifest))
    return manifest


def import_result(output: Path) -> dict:
    output = Path(output)
    manifest = _decode(_read(output / "manifest.json", MAX_METADATA_BYTES)[0], MAX_METADATA_BYTES)
    _keys(manifest, "schema result method source_sha256 content_sha256 configuration_sha256")
    _keys(manifest["result"], "name bytes sha256")
    member = manifest["result"]
    if (manifest["schema"] != MANIFEST_SCHEMA or member["name"] != "result.json"
            or type(member["bytes"]) is not int or not 0 < member["bytes"] <= MAX_RESULT_BYTES):
        raise ProfileError("invalid result manifest")
    raw = _read(output / "result.json", MAX_RESULT_BYTES)[0]
    if len(raw) != member["bytes"] or _hash(raw) != member["sha256"]:
        raise ProfileError("portable member hash or size disagreement")
    result = _decode(raw, MAX_RESULT_BYTES)
    _validate_result(result)
    if (manifest["method"] != result["method"] or manifest["source_sha256"] != result["original"]["sha256"]
            or manifest["content_sha256"] != result["content_sha256"]
            or manifest["configuration_sha256"] != _hash(_encode(result["numerical_settings"]))):
        raise ProfileError("manifest identity disagreement")
    return result
