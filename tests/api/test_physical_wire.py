"""Physical strict wire structure, never field or numerical acceptance."""

import copy
from uuid import uuid4

import pytest

from app.physical_contract import byte_sha, canonical
from app.physical_wire import make_root_envelope, parse_root, root_envelope, scientific_digest


@pytest.fixture
def survey():
    # Structural control only: the HTTP parent must not convert original_value
    # or reject these intentionally non-reconstructed current values.
    return dict(schema_version="gravity-stations-1", state="observed_absolute", history=[],
                metadata=dict(source_kind="synthetic_control", source_sha256="a"*64,
                              source_citation="Structural controls only", rights="Authored test input",
                              crs="EPSG:4326", reference_ellipsoid="WGS84", height_datum="ellipsoidal",
                              height_unit="m", height_sign="upward", gravity_unit="microGal", gravity_sign="upward",
                              gravity_quantity="absolute_gravity", gravity_datum="Supplied unverified statement",
                              tide_system="tide_free", instrument_processing={
                                  k: dict(status="applied" if k == "calibration" else "not_applicable", citation="Control")
                                  for k in ("calibration", "drift", "tide")}),
                stations=[dict(station_id="station-1", latitude_deg=0, longitude_deg=180,
                               receiver_height_m=-1, surface_height_m=-2, original_value=10,
                               value_mgal=10.0, gravity_sigma=0.1, receiver_sigma_m=0,
                               surface_sigma_m=0, latitude_sigma_deg=0)])


def test_structural_parent_preserves_original_units_numbers_and_unsupported_physics(survey):
    raw = canonical(survey)
    parsed = parse_root([raw[:3], raw[3:]])
    assert canonical(parsed) == raw
    assert type(parsed["stations"][0]["original_value"]) is int
    assert type(parsed["stations"][0]["value_mgal"]) is float


def test_no_request_parent_longitude_wrap_or_height_conversion(survey):
    second = dict(survey["stations"][0], station_id="station-2", longitude_deg=-180)
    survey["stations"].append(second)
    assert len(parse_root([canonical(survey)])["stations"]) == 2


@pytest.mark.parametrize("mutate", [
    lambda v: v.update(extra=True),
    lambda v: v["stations"][0].update(latitude_deg=True),
    lambda v: v["stations"][0].update(gravity_sigma=-1),
    lambda v: v["stations"][0].update(geoid_m=0),
    lambda v: v["metadata"].update(geoid_model="invented"),
    lambda v: v["metadata"].update(crs="local"),
    lambda v: v["metadata"]["instrument_processing"]["calibration"].update(status="not_applicable"),
    lambda v: v["stations"].append(copy.deepcopy(v["stations"][0])),
    lambda v: v.update(state="gravity_disturbance"),
])
def test_missing_physics_unknown_keys_boolean_numeric_and_duplicate_id_refuse(survey, mutate):
    mutate(survey)
    with pytest.raises(ValueError):
        parse_root([canonical(survey)])


@pytest.mark.parametrize("body", [
    b'{"schema_version":"gravity-stations-1","schema_version":"gravity-stations-1"}',
    b'{} trailing', b'\xef\xbb\xbf{}', b'{"n":1e400}', b'{"n":NaN}',
    b'{"n":9007199254740992}', br'{"n":"\ud800"}',
])
def test_full_source_eof_and_token_barrier_precedes_any_root_exposure(body):
    with pytest.raises(ValueError):
        parse_root([body])


def test_orthometric_requires_explicit_geoid_metadata_and_station_errors(survey):
    survey["metadata"]["height_datum"] = "orthometric"
    with pytest.raises(ValueError):
        parse_root([canonical(survey)])
    survey["metadata"]["geoid_model"] = "Supplied explicit model"
    survey["stations"][0].update(geoid_m=-4, geoid_sigma_m=0.2)
    assert parse_root([canonical(survey)]) == survey


def test_envelope_has_no_invented_producer_and_retains_nullable_source_citation(survey):
    ids = [str(uuid4()) for _ in range(4)]
    source = dict(provider="Control author", exact_url=None, doi=None, citation=None,
                  rights_decision="mirror", rights_statement="Authored control", attribution="Control author")
    body = make_root_envelope(survey, dataset_id=ids[0], owner_id=ids[1], project_id=ids[2],
                              raw_asset_id=ids[3], raw_sha256=byte_sha(canonical(survey)),
                              raw_bytes=len(canonical(survey)), source=source)
    value = root_envelope([body])
    assert value["production"] is None and value["parent_dataset_id"] is None
    assert value["structural_verdict"] == "structural_only"
    assert value["payload"] == survey and value["source"] == source
    assert value["scientific_payload_sha256"] == scientific_digest(survey)
    value["payload"]["stations"][0]["original_value"] = 10.0
    with pytest.raises(ValueError, match="payload_hash"):
        root_envelope([canonical(value)])


def test_unicode_application_and_scientific_digest_domains_are_not_substitutable(survey):
    survey["metadata"]["source_citation"] = "Explicit \u00e9 control"
    assert byte_sha(canonical(survey)) != scientific_digest(survey)
