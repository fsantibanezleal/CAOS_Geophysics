"""Closed byte protocol and deferred likelihood preflight."""

import builtins
import json
import pytest
from magnetic_survey_support import at, encode, request, rehash
from magnetic_survey_json import InputError, parse_request

OBJECTS = ["", "source", "frame", "inducing_field", "acquisition", "processing",
           "processing/nodes/0", "processing/nodes/0/parameters", "geometry",
           "geometry/mesh", "geometry/partition", "observations", "noise", "prior",
           "policy", "policy/optimizer_binding", "geometry/receivers_m", "noise/values"]


@pytest.mark.parametrize("path", OBJECTS)
@pytest.mark.parametrize("attack", ["extra", "missing", "null"])
def test_preallocation_closed_protocol(path, attack, monkeypatch):
    doc = request()
    value = at(doc, path) if path else doc
    if attack == "extra":
        value["unknown"] = None
    elif attack == "missing":
        value.pop(next(iter(value)))
    else:
        value[next(iter(value))] = None
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        assert name.split(".")[0] not in {"numpy", "simpeg", "geoana", "scipy", "discretize"}
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    with pytest.raises(InputError):
        parse_request(encode(doc))


@pytest.mark.parametrize("raw,code", [
    (b" "*8388609, "bytes"), (b"\xef\xbb\xbf{}", "encoding"),
    (b'{"x":"\xff"}', "encoding"), (b'{"x":0,"x":1}', "duplicate_key"),
    (b'{"x":0,"\\u0078":1}', "duplicate_key"),
    (b"["*13+b"0"+b"]"*13, "depth"),
    (b'{"x":1e309}', "type"), (b'{"x":1e-999}', "type"),
    (b'{"x":'+b"1"*65+b"}", "tokens"),
    (b'{"x":"'+b"a"*2049+b'"}', "bytes"),
    (b'{"x":"\\ud800"}', "encoding"),
    (b"["+b"0,"*250000+b"0]", "tokens"),
    (b'{"x":NaN}', "type"), (b'{"x":01}', "type"),
    (b'{"x":1.}', "type"), (b'{"x":0}x', "type"),
])
def test_lexical_bounds(raw, code):
    with pytest.raises(InputError) as failure:
        parse_request(raw)
    assert failure.value.code == code
    assert set(failure.value.envelope()) == {"schema", "code", "path", "message"}
    assert len(failure.value.envelope()["message"]) <= 2048


@pytest.mark.parametrize("path,value", [
    ("source/original_bytes", True), ("source/original_bytes", 1.0),
    ("source/original_bytes", 2**63), ("frame/axes", "NEU"),
    ("frame/crs", ""), ("frame/vertical_datum", "x\t"),
    ("inducing_field/D_deg", 180), ("inducing_field/F_nT", 0),
    ("inducing_field/I_deg", 91), ("inducing_field/F_nT", "50000"),
    ("policy/resource_profile", "upper_passed"), ("policy/betas", [1.]),
    ("geometry/partition/seed", 104729.0), ("geometry/partition/buffer_m", -1),
    ("geometry/receivers_m/shape", [2**62, 3]),
    ("geometry/receivers_m/dtype", "float32"),
    ("geometry/receivers_m/data", [0]), ("noise/values/sha256", "d"*64),
    ("policy/optimizer_binding/epoch", "unaccepted"),
    ("observations/unit", "T"), ("noise/unit", "nT^2"),
    ("processing/quantity", "reduced_to_pole"), ("intent", "replay_only"),
])
def test_types_counts_enums_cross_policies(path, value):
    doc = request()
    parent, name = path.rsplit("/", 1) if "/" in path else ("", path)
    (at(doc, parent) if parent else doc)[name] = value
    with pytest.raises(InputError):
        parse_request(encode(doc))


@pytest.mark.parametrize("stamp", ["2026-02-30T00:00:00Z", "2026-01-01T00:00:60Z",
                                   "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00.1234567Z"])
def test_timestamp_negatives(stamp):
    doc = request()
    doc["acquisition"].update(timestamp_policy="recorded_utc", timestamps=[stamp]*288)
    with pytest.raises(InputError):
        parse_request(encode(doc))


def test_deferred_values_and_fresh_metadata():
    handle = parse_request(encode(request()))
    meta = handle.metadata()
    assert "data" not in meta["observations"]["values"]
    assert "data" not in meta["noise"]["values"]
    meta["geometry"]["receivers_m"]["data"][0] = 999
    assert handle.metadata()["geometry"]["receivers_m"]["data"][0] == -200
    assert handle.preflight["conservative_bytes"] == 120112128


@pytest.mark.parametrize("kind", [str, bytearray, memoryview])
def test_native_hooks_not_accepted(kind):
    raw = encode(request())
    with pytest.raises(InputError):
        parse_request(raw.decode() if kind is str else kind(raw))


def test_negative_zero_geometry_and_float_hash():
    doc = request()
    doc["geometry"]["receivers_m"]["data"][0] = -0.0
    rehash(doc, "geometry/receivers_m")
    with pytest.raises(InputError):
        parse_request(encode(doc))
    doc = request()
    doc["observations"]["values"]["data"][0] = -0.0
    rehash(doc, "observations/values")
    assert parse_request(encode(doc)).metadata()["observations"]["values"]["sha256"] == doc["observations"]["values"]["sha256"]
