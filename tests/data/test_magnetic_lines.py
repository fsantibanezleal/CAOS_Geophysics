"""M03 bounded intake gates, not magnetic or provider-field validation."""
from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def modules():
    contract = importlib.import_module("magnetic_line_contract")
    spec = importlib.util.spec_from_file_location(
        "m03_geometry_fixture", ROOT / "tests/fixtures/magnetic_lines/generate.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    return contract, generator


def test_original_identity_and_rights():
    c, g = modules()
    raw, sidecar, request = g.geometry_input()
    loaded = c.load_lines(raw, c.canonical_bytes(sidecar), c.canonical_bytes(request))
    assert loaded["original_bytes"] == raw
    assert loaded["csv_sha256"] == sha256(raw).hexdigest()
    assert loaded["provider_authenticated"] is False
    assert loaded["metadata"]["rights"]["raw_mirroring"] == "denied"
    denied = deepcopy(sidecar)
    denied["rights"]["private_processing"] = "denied"
    inspected = c.load_lines(raw, c.canonical_bytes(denied))
    assert "rights_denied" in inspected["eligibility_reasons"]
    with pytest.raises(c.MagneticContractError):
        c.load_lines(raw + b"\n", c.canonical_bytes(sidecar))


def test_physical_metadata_and_exact_keys():
    c, g = modules()
    raw, meta, req = g.geometry_input()
    for key in meta:
        altered = deepcopy(meta)
        del altered[key]
        with pytest.raises(c.MagneticContractError):
            c.load_lines(raw, c.canonical_bytes(altered))
    for key in ("coordinates", "rights", "quantity", "acquisition", "authored_control", "original"):
        altered = deepcopy(meta)
        altered[key]["extra"] = None
        with pytest.raises(c.MagneticContractError):
            c.load_lines(raw, c.canonical_bytes(altered))
    for key in req:
        altered = deepcopy(req)
        del altered[key]
        with pytest.raises(c.MagneticContractError):
            c.load_lines(raw, c.canonical_bytes(meta), c.canonical_bytes(altered))
    for path, value in (
        (("quantity", "unit"), "mGal"), (("coordinates", "xy_unit"), "degree"),
        (("coordinates", "axis_order"), "northing_easting"),
        (("authored_control", "seed"), True), (("original", "csv_bytes"), 1.0),
    ):
        altered = deepcopy(meta)
        altered[path[0]][path[1]] = value
        with pytest.raises(c.MagneticContractError):
            c.load_lines(raw, c.canonical_bytes(altered))
    unknown = deepcopy(meta)
    unknown["coordinates"]["vertical_datum"] = None
    assert "vertical_datum_unresolved" in c.load_lines(
        raw, c.canonical_bytes(unknown)
    )["eligibility_reasons"]


def test_order_identity_duplicates_and_masks():
    c, g = modules()
    rows = g.geometry_rows()
    assert len(rows) == 363
    raw, meta, _ = g.geometry_input()
    parsed = c.parse_csv(raw)
    assert [r["row_id"] for r in parsed["rows"]] == [r["row_id"] for r in rows]
    assert parsed["rows"][33]["easting_m"] == 1600
    assert parsed["rows"][65]["easting_m"] == -1600
    altered = deepcopy(rows)
    altered[1]["row_id"] = altered[0]["row_id"]
    with pytest.raises(c.MagneticContractError):
        c.parse_csv(g.csv_bytes(altered))
    altered = deepcopy(rows)
    altered[1]["ordinal"] = 0
    with pytest.raises(c.MagneticContractError):
        c.parse_csv(g.csv_bytes(altered))
    altered = deepcopy(rows)
    altered[1]["easting_m"] = altered[0]["easting_m"]
    altered[1]["northing_m"] = altered[0]["northing_m"]
    parsed = c.parse_csv(g.csv_bytes(altered))
    assert len(parsed["rows"]) == 363
    assert "duplicate_location" in parsed["flags"][0]
    assert "missing_value" in parsed["flags"][1]
    bom = c.parse_csv(b"\xef\xbb\xbf" + raw)
    assert bom["bom"] is True


def test_bartlett_grid_and_charleston_rgb_are_not_lines():
    c, g = modules()
    raw, meta, _ = g.geometry_input()
    receipt = json.loads((ROOT / "docs/research/m03-primary-retrieval-2026-10-03.json").read_bytes())
    providers = {r["id"]: r for r in receipt["receipts"]}
    for provider, kind, expected in (
        ("bartlett-metadata", "provider_grid", "84d3d512f9deba53ae0251c74354c389b8723d056375390d2bfebd28c24b8295"),
        ("charleston-metadata", "provider_image", "badd712ff0e169bd62ed70b34ce273ef9bea4b4ec7a206627b09eac55a98a1c2"),
    ):
        record = providers[provider]
        body = ROOT / record["cache_path"]
        assert body.is_file(), "Actual primary metadata is required, not a fabricated provider fixture"
        assert sha256(body.read_bytes()).hexdigest() == expected == record["sha256"]
        text = body.read_text(encoding="utf-8")
        assert ("mag_grid" if kind == "provider_grid" else "255") in text
        altered = deepcopy(meta)
        altered["source_kind"] = kind
        altered["authored_control"] = None
        assert "source_kind_not_lines" in c.load_lines(raw, c.canonical_bytes(altered))["eligibility_reasons"]


@pytest.mark.parametrize("payload", [
    b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'{}{}',
    b'[' * 17 + b'0' + b']' * 17, b'{"a":"\\ud800"}', b'\xff',
    b'{"a":' + b'1' * 129 + b'}',
])
def test_strict_json_pre_materialization(payload):
    c, _ = modules()
    with pytest.raises(c.MagneticContractError):
        c.strict_json(payload)


def test_bounded_reads_and_complexity(tmp_path):
    c, g = modules()
    p = tmp_path / "oversize"
    p.write_bytes(b"x" * (c.MAX_METADATA_BYTES + 1))
    with pytest.raises(c.MagneticContractError) as err:
        c.read_bounded(p, c.MAX_METADATA_BYTES)
    assert err.value.error["code"] == "resource_refused"
    assert c.read_bounded(p, c.MAX_METADATA_BYTES + 1) == p.read_bytes()
    for payload in (b'{"' + b'x' * 129 + b'":0}', b'["' + b'x' * 8193 + b'"]'):
        with pytest.raises(c.MagneticContractError):
            c.strict_json(payload)
    raw, meta, req = g.geometry_input()
    req["equivalent_sources"]["weight_multiplier"] = 2
    with pytest.raises(c.MagneticContractError):
        c.load_lines(raw, c.canonical_bytes(meta), c.canonical_bytes(req))


@pytest.mark.parametrize("operation", [
    "reduction_to_pole", "downward_continuation", "vector_recovery", "susceptibility_inversion",
])
def test_unsupported_operations(operation):
    c, _ = modules()
    with pytest.raises(c.MagneticContractError) as err:
        c.validate_operation(operation)
    assert err.value.error["code"] == "unsupported_operation"
    assert set(err.value.error) == {
        "code", "stage", "field", "observed", "limit", "reason", "local_recipe", "attempt_id",
    }


def specimens(c, g):
    """Typed fixtures have no actual evaluator/calibration authentication."""
    def value(spec, number=0, tag="lag"):
        if type(spec) is str and spec.startswith("?"):
            return None
        if type(spec) is tuple:
            kind = spec[0]
            if kind == "nullable":
                return None
            if kind == "literal":
                return spec[1]
            if kind == "enum":
                return spec[1][0]
            if kind == "int":
                return spec[1]
            if kind == "parameters":
                return None if spec[1] else example(c.PARAMETERS[tag])
            if kind in ("list", "rows"):
                count = 1 if kind == "rows" else spec[2]
                return [value(spec[1], i) for i in range(count)]
        if spec in c.SCHEMAS:
            return example(spec)
        return {"ID": f"id{number}", "Text": "Documented fixture, not independently evaluated",
                "Hash": "a"*64, "UTC": f"2000-01-01T00:00:{number:02d}Z",
                "F64": float(number+1), "Pos": float(number+1), "Nonneg": float(number)}[spec]

    raw, meta, req = g.geometry_input()
    actual = {}
    def collect(name, obj):
        actual[name] = deepcopy(obj)
        for key, spec in c.SCHEMAS[name].items():
            item = obj[key]
            if type(spec) is str and spec in c.SCHEMAS:
                collect(spec, item)
            elif type(spec) is tuple and spec[0] == "list" and spec[1] in c.SCHEMAS and item:
                collect(spec[1], item[0])
    collect("Sidecar", meta)
    collect("Request", req)
    def example(name):
        if name in actual:
            return deepcopy(actual[name])
        obj = {key: value(spec) for key, spec in c.SCHEMAS[name].items()}
        if name == "AuxIdentity":
            obj["source_verification"] = "user_claimed"
            obj["source_sha256"] = "a"*64
        elif name == "StateRecord":
            obj.update(units="m", sign="position_time_plus_tau")
        elif name == "TimeInterval":
            obj.update(start="2000-01-01T00:00:00Z", end="2000-01-01T00:00:01Z")
        elif name in ("BaseSeries", "NavigationSeries"):
            obj["records"][1]["utc"] = "2000-01-01T00:00:01Z"
            typed = [c.validate_named("BaseRecord" if name == "BaseSeries" else "NavigationRecord", r) for r in obj["records"]]
            obj["identity"]["canonical_records_sha256"] = c.digest(typed)
        elif name == "Evaluator":
            obj.update(valid_start_decimal_year=1900., valid_end_decimal_year=2030.)
        elif name == "ReferenceEpoch":
            obj.update(date_decimal_year=2000., survey_epoch_evidence_sha256="b"*64)
        elif name == "Reference":
            obj.update(model_generation="IGRF14", coefficients_sha256="c"*64, direction_tolerance_deg=.5)
        elif name == "IndependentOffsets":
            obj["reference_gauge_id"] = obj["values"][0]["line_id"]
        elif name == "MicrolevelParameters":
            obj.update(flight_azimuth_deg=0., max_azimuth_spread_deg=1.)
        elif name == "DirectionSector":
            obj.update(azimuth_start_deg=0., azimuth_end_deg=90.)
        return obj
    return {name: example(name) for name in c.SCHEMAS}


def test_every_intake_request_table_exact_and_typed():
    c, g = modules()
    examples = specimens(c, g)
    contract = (ROOT / "docs/design/features/m03-aeromagnetic-lines/contracts.md").read_text(encoding="utf-8")
    import re
    table_keys = {}
    for line in contract.splitlines():
        if line.startswith("| ") and "; " in line:
            cells = line.split("|")
            if cells[1].strip() in c.SCHEMAS:
                table_keys[cells[1].strip()] = set(re.findall(r"(?:^|;)\s*([a-z][A-Za-z0-9_]*)\s*:", cells[2]))
    assert set(table_keys) == set(c.SCHEMAS)
    for name, example in examples.items():
        assert table_keys[name] == set(c.SCHEMAS[name])
        c.validate_named(name, example, 363 if name in (
            "Sidecar", "Request", "SplitConfig", "Acquisition", "LineDefinition", "AuthoredControl", "Original"
        ) else 1)
        for key in example:
            bad = deepcopy(example)
            del bad[key]
            with pytest.raises(c.MagneticContractError):
                c.validate_named(name, bad)
        bad = deepcopy(example)
        bad["extra"] = None
        with pytest.raises(c.MagneticContractError):
            c.validate_named(name, bad)


def test_auxiliary_epoch_state_and_union_negative_branches():
    c, g = modules()
    ex = specimens(c, g)
    for name, key, replacement in (
        ("AuxIdentity", "source_verification", "authored"),
        ("CalibrationIdentity", "partition", "outer_training"),
        ("StateRecord", "sign", "subtract_reference_F"),
        ("StateRecord", "units", "nT"),
        ("Reference", "model_generation", "IGRF13"),
        ("ReferenceEpoch", "date_mode", "row_utc"),
        ("ReferenceEpoch", "row_date_decimal_year", [2000.]),
        ("Reference", "direction_tolerance_deg", .5001),
        ("MicrolevelParameters", "max_azimuth_spread_deg", 5.01),
        ("CrossoverPolicy", "min_crossing_sine", 1e-7),
        ("EquivalentSourcesConfig", "damping_unit", "nT^-2"),
        ("EquivalentSourcesConfig", "parallel", 0),
    ):
        bad = deepcopy(ex[name])
        bad[key] = replacement
        with pytest.raises(c.MagneticContractError):
            c.validate_named(name, bad)
    bad = deepcopy(ex["StateRecord"])
    bad.update(status="applied", applied_by="processor")
    with pytest.raises(c.MagneticContractError):
        c.validate_named("StateRecord", bad)
    for name in ("BaseSeries", "NavigationSeries"):
        bad = deepcopy(ex[name])
        bad["records"][1]["utc"] = bad["records"][0]["utc"]
        with pytest.raises(c.MagneticContractError):
            c.validate_named(name, bad)
        bad = deepcopy(ex[name])
        bad["identity"]["canonical_records_sha256"] = "0"*64
        with pytest.raises(c.MagneticContractError):
            c.validate_named(name, bad)
    for op, name in c.PARAMETERS.items():
        operation = dict(operation=op, input_channel_sha256="a"*64, parameters=ex[name])
        c.validate_named("OperationRequest", operation)
        bad = deepcopy(operation)
        bad["parameters"]["code"] = "execute"
        with pytest.raises(c.MagneticContractError):
            c.validate_named("OperationRequest", bad)


def test_csv_native_numeric_time_and_order_boundaries():
    c, g = modules()
    raw, _, _ = g.geometry_input()
    for token in (b"nan", b"inf", b"1e999", b"True", b"1,200", b" "):
        altered = raw.replace(b"-1600.0", token, 1)
        with pytest.raises(c.MagneticContractError):
            c.parse_csv(altered)
    for stamp in ("2000-02-30T00:00:00Z", "2000-01-01T00:00:60Z", "2000-01-01T00:00:00+00:00"):
        with pytest.raises(c.MagneticContractError):
            c.utc_key(stamp)
    assert c.utc_key("2000-01-01T00:00:00.000000001Z") < c.utc_key("2000-01-01T00:00:00.000000002Z")
    rows = g.geometry_rows()
    # Two sensor channels interleave, each preserves its own ordinal.
    sample = [deepcopy(rows[0]), deepcopy(rows[0]), deepcopy(rows[1]), deepcopy(rows[1])]
    for index in (1, 3):
        sample[index]["sensor_id"] = "S1"
        sample[index]["row_id"] += ".S1"
    parsed = c.parse_csv(g.csv_bytes(sample))
    assert [r["sensor_id"] for r in parsed["rows"]] == ["S0", "S1", "S0", "S1"]
    assert len(parsed["rows"]) == 4


def test_actual_byte_token_node_and_record_caps():
    c, g = modules()
    raw, meta, req = g.geometry_input()
    with pytest.raises(c.MagneticContractError):
        c.parse_csv(raw + b"\n"*1000000)
    with pytest.raises(c.MagneticContractError):
        c.strict_json(b"[" + b"0,"*200000 + b"0]")
    # UTF-8 bytes, not characters or raw ASCII escape count.
    c.strict_json(json.dumps(["\U0001f642"*2048], ensure_ascii=False).encode())
    with pytest.raises(c.MagneticContractError):
        c.strict_json(json.dumps(["\U0001f642"*2049], ensure_ascii=False).encode())
    c.strict_json(b'{"a":' + b" "*(c.MAX_METADATA_BYTES-7) + b'0}')
    with pytest.raises(c.MagneticContractError):
        c.strict_json(b" "*(c.MAX_METADATA_BYTES+1))
    with pytest.raises(c.MagneticContractError):
        c.load_lines(raw, c.canonical_bytes(meta), b" "*c.MAX_METADATA_BYTES)


def test_input_module_imports_no_scientific_engines():
    import subprocess
    import sys
    code = "import sys; sys.path.insert(0,'data-pipeline'); import magnetic_line_contract,magnetic_line_validation; assert not {'numpy','scipy','harmonica','verde','sklearn'} & set(sys.modules)"
    completed = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code],
                               cwd=ROOT, capture_output=True, check=False, timeout=10)
    assert completed.returncode == 0, completed.stderr.decode()


def test_primitives_counts_nullability_and_unknown_keys_all_depths():
    c, g = modules()
    ex = specimens(c, g)
    for name, example in ex.items():
        for key, spec in c.SCHEMAS[name].items():
            nullable = (type(spec) is str and spec.startswith("?")) or (
                type(spec) is tuple and (spec[0] == "nullable" or (spec[0] == "parameters" and spec[1])))
            if not nullable:
                bad = deepcopy(example)
                bad[key] = None
                with pytest.raises(c.MagneticContractError):
                    c.validate_named(name, bad, 363 if name in ("Sidecar", "Request", "SplitConfig", "Acquisition", "Original", "AuthoredControl") else 1)
            if type(spec) is tuple and spec[0] == "list":
                bad = deepcopy(example)
                bad[key] = example[key] * (spec[3]+1) if example[key] else [None]*(spec[3]+1)
                with pytest.raises(c.MagneticContractError):
                    c.validate_named(name, bad)
    for spec in ("F64", "Pos", "Nonneg"):
        for wrong in (True, "1", float("nan"), float("inf"), -float("inf"), [], {}):
            with pytest.raises(c.MagneticContractError):
                c._type(wrong, spec, "known", 1)
    for spec in (c.I(0, 4), c.literal(False), c.literal(1)):
        with pytest.raises(c.MagneticContractError):
            c._type(1.0, spec, "known", 1)
    assert c.canonical_bytes({"value": -0.0}) == b'{"value":0.0}'
    assert c.canonical_bytes({"value": 1}) != c.canonical_bytes({"value": 1.0})


def test_actual_reference_epoch_row_binding_not_authentication():
    c, g = modules()
    ex = specimens(c, g)
    rows = g.geometry_rows()[:1]
    reference = deepcopy(ex["Reference"])
    epoch = reference["epoch"]
    date, nano = c.utc_key(rows[0]["utc"])
    from datetime import datetime, timezone
    start, end = datetime(date.year, 1, 1, tzinfo=timezone.utc), datetime(date.year+1, 1, 1, tzinfo=timezone.utc)
    expected = date.year + ((date-start).total_seconds() + nano*1e-9)/(end-start).total_seconds()
    epoch.update(date_mode="row_utc", date_decimal_year=None, row_date_decimal_year=[expected],
                 survey_epoch_evidence_sha256=None, row_utc_sha256=c.digest([rows[0]["utc"]]))
    c._reference_rows(reference, rows, False, "Reference")
    epoch["row_date_decimal_year"][0] += .1
    with pytest.raises(c.MagneticContractError):
        c._reference_rows(reference, rows, False, "Reference")
