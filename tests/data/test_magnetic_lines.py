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
    assert len(err.value.error) == 9
