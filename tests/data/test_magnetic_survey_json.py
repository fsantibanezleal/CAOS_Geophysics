"""Closed byte protocol and deferred likelihood preflight."""

import builtins
import json
import pytest
from magnetic_survey_support import at, descriptor, digest, encode, request, rehash
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
        if path:
            parent, name = path.rsplit("/", 1) if "/" in path else ("", path)
            target = at(doc, parent) if parent else doc
            target[int(name) if type(target) is list else name] = None
        else:
            doc = None
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
], ids=["byte-cap", "bom", "bad-utf8", "duplicate", "escaped-duplicate", "depth",
        "overflow", "underflow", "number-length", "string-length", "surrogate",
        "token-cap", "nan", "leading-zero", "fraction", "trailing"])
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


def test_positive_parser_never_imports_engine_or_decodes_likelihood(monkeypatch):
    import magnetic_survey_json as module
    original_loads, original_import = module.json.loads, builtins.__import__
    doc = request()
    likelihoods = {json.dumps(doc[key]["values"]["data"], separators=(",", ":")) for key in ("observations", "noise")}
    def no_values(raw, *args, **kwargs):
        if type(raw) is str and raw.startswith("["):
            # Equal counts do not identify a value array: geometry also has864
            # scalars. Trap the exact separate likelihood spans instead.
            assert raw not in likelihoods
        if type(raw) is str:
            assert not raw.startswith('{"schema"')
        return original_loads(raw, *args, **kwargs)
    def no_engine(name, *args, **kwargs):
        assert name.split(".")[0] not in {"numpy", "simpeg", "geoana", "scipy", "discretize"}
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(module.json, "loads", no_values)
    monkeypatch.setattr(builtins, "__import__", no_engine)
    assert parse_request(encode(doc)).preflight["rows"] == 288


@pytest.mark.parametrize("quantity,relation,c", [
    ("secondary_enu_nT", "secondary_field_declared", 3),
    ("linear_tmi_nT", "projection_of_secondary_declared", 1),
    ("exact_total_anomaly_nT", "total_norm_minus_declared_uniform_F", 1)])
def test_declared_quantity_and_covariance_metadata(quantity, relation, c):
    doc = request()
    doc["processing"].update(quantity=quantity, background_relation=relation)
    doc["observations"].update(quantity=quantity, values=descriptor("float64", [288, c], [0.]*(288*c)))
    rehash(doc, "observations/values")
    doc["noise"]["values"] = descriptor("float64", [288, c], [.5]*(288*c))
    assert parse_request(encode(doc)).preflight["components"] == c
    if c == 1:
        cov = [0.]*(288*288)
        for i in range(288):
            cov[289*i] = .25
        doc["noise"].update(kind="full_covariance", unit="nT^2", values=descriptor("float64", [288, 288], cov))
        assert parse_request(encode(doc)).metadata()["noise"]["kind"] == "full_covariance"
    else:
        doc["noise"].update(kind="full_covariance", unit="nT^2")
        with pytest.raises(InputError) as failure:
            parse_request(encode(doc))
        assert failure.value.code == "resource"


@pytest.mark.parametrize("operation", ["frame_conversion", "background_subtraction", "linear_projection",
                                      "total_norm_difference", "declared_external_correction", "m03_processed_eligible"])
@pytest.mark.parametrize("attack", ["valid", "extra", "missing", "wrong_tag", "hash"])
def test_every_tagged_lineage_union(operation, attack):
    doc = request()
    variants = {
        "frame_conversion": dict(kind="external_frame_conversion", from_frame=doc["frame"], to_frame=doc["frame"], transform_sha256="b"*64),
        "background_subtraction": dict(kind="subtract_uniform_F", field=doc["inducing_field"]),
        "linear_projection": dict(kind="projection_of_secondary", field=doc["inducing_field"], component_order=["E", "N", "U"]),
        "total_norm_difference": dict(kind="norm_total_minus_F", field=doc["inducing_field"]),
        "declared_external_correction": dict(kind="external_preprocessed", record_sha256="a"*64, bundle_sha256="b"*64),
        "m03_processed_eligible": dict(kind="m03_approved_output", bundle_sha256="a"*64, descriptor_sha256="b"*64,
                                       quantity="secondary_enu_nT", approved_epoch="Unregistered protocol epoch")}
    params = variants[operation]
    if attack == "extra":
        params["unexpected"] = False
    elif attack == "missing":
        params.pop("kind")
    elif attack == "wrong_tag":
        params["kind"] = "identity"
    node = dict(id="derived", parents=["original"], operation=operation,
                input_sha256=doc["observations"]["values_sha256"], output_sha256=doc["observations"]["values_sha256"],
                parameters=params, parameters_sha256="f"*64 if attack == "hash" else digest(params), citation="Protocol-only declared operation")
    doc["processing"]["nodes"].append(node)
    doc["processing"]["final_node"] = "derived"
    if attack == "valid":
        assert parse_request(encode(doc)).preflight["rows"] == 288
    else:
        with pytest.raises(InputError):
            parse_request(encode(doc))


@pytest.mark.parametrize("attack", ["parent_forward", "duplicate_parent", "duplicate_node", "disconnected", "wrong_input", "wrong_final"])
def test_closed_dag_failures(attack):
    doc = request()
    root = doc["processing"]["nodes"][0]
    params = dict(kind="external_preprocessed", record_sha256="a"*64, bundle_sha256="b"*64)
    node = dict(id="derived", parents=["original"], operation="declared_external_correction",
                input_sha256=root["output_sha256"], output_sha256=root["output_sha256"],
                parameters=params, parameters_sha256=digest(params), citation="Protocol DAG")
    doc["processing"]["nodes"].append(node)
    doc["processing"]["final_node"] = "derived"
    if attack == "parent_forward":
        root["parents"] = ["derived"]
    elif attack == "duplicate_parent":
        node["parents"] = ["original", "original"]
    elif attack == "duplicate_node":
        node["id"] = "original"
    elif attack == "disconnected":
        doc["processing"]["final_node"] = "original"
    elif attack == "wrong_input":
        node["input_sha256"] = "e"*64
    else:
        doc["processing"]["final_node"] = "unknown"
    with pytest.raises(InputError):
        parse_request(encode(doc))


def test_scalar_caps_and_typed_snapshot_entry():
    from magnetic_survey_json import SurveyHandle
    with pytest.raises(InputError):
        SurveyHandle(b"{}", {}, {})
    doc = request()
    doc["geometry"]["partition"]["buffer_m"] = -0.0
    with pytest.raises(InputError):
        parse_request(encode(doc))
    # Exact bytes and tokens caps count whitespace, not a claimed source size.
    raw = encode(request())
    assert parse_request(raw+b" "*(8388608-len(raw))).preflight["rows"] == 288
    with pytest.raises(InputError):
        parse_request(raw+b" "*(8388609-len(raw)))


def test_conservative_and_online_capacity_before_numpy(monkeypatch):
    doc = request()
    doc["policy"]["resource_profile"] = "online_proposed"
    with pytest.raises(InputError) as failure:
        parse_request(encode(doc))
    assert failure.value.code == "resource"
    doc = request()
    # Legal row/full/active individual counts, deliberately inadmissible combined
    # memory bound. No solver or allocation measurement is claimed by this test.
    n, a = 2048, 2048
    doc["acquisition"]["row_ids"] = [f"row{i}" for i in range(n)]
    doc["acquisition"]["group_ids"] = [f"group{i//24}" for i in range(n)]
    doc["geometry"]["receivers_m"] = descriptor("float64", [n, 3], [v for i in range(n) for v in [float(i), float(i), 120.]])
    doc["geometry"]["usable"] = descriptor("bool", [n], [True]*n)
    doc["geometry"]["qc_reason"] = ["accepted"]*n
    mesh = doc["geometry"]["mesh"]
    for key, count in (("widths_x_m", 16), ("widths_y_m", 16), ("widths_z_m", 8)):
        mesh[key] = descriptor("float64", [count], [100.]*count)
    mesh["active"] = descriptor("bool", [a], [True]*a)
    for key, value in (("lower_si", 0.), ("upper_si", .1), ("start_si", 0.), ("reference_si", 0.)):
        doc["prior"][key] = descriptor("float64", [a], [value]*a)
    doc["observations"]["values"] = descriptor("float64", [n, 3], [0.]*(n*3))
    rehash(doc, "observations/values")
    doc["noise"]["values"] = descriptor("float64", [n, 3], [.5]*(n*3))
    original = builtins.__import__
    def no_engine(name, *args, **kwargs):
        assert name.split(".")[0] not in {"numpy", "simpeg", "geoana", "scipy", "discretize"}
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_engine)
    with pytest.raises(InputError) as failure:
        parse_request(encode(doc))
    assert failure.value.code == "resource"


def test_total_decoded_string_bound_and_safe_paths():
    raw = json.dumps({f"key{i}": "a"*2048 for i in range(128)}).encode()
    with pytest.raises(InputError) as failure:
        parse_request(raw)
    assert failure.value.code == "bytes"
    with pytest.raises(InputError) as failure:
        parse_request(b'{"\\u0001":{"x":1,"x":2}}')
    assert failure.value.code == "duplicate_key"
    assert all(ord(c) >= 32 for c in failure.value.envelope()["path"])
