"""Strict physical structures and byte/digest bindings, never numerical solves.

The HTTP/publication parent must not replay gravity history, convert units,
infer geometry or normalize submitted configuration. These checks preserve
the exact native numbers and distinguish structural from scientific admission.
"""

import math

from app.physical_contract import (
    M, canonical, decode_source, digest, fields, integer, require, sha, text, uuid,
)


STATES = ("observed_absolute", "gravity_disturbance", "bouguer_disturbance", "terrain_adjusted_disturbance")
HISTORY = ("normal_reference", "elevation_reference", "bouguer_plate", "terrain_residual")
DATASET_KEYS = "schema dataset_id version owner_id project_id raw_asset_id raw_sha256 raw_bytes parser_version root_dataset_id parent_dataset_id parent_dataset_sha256 kind modality payload_schema scientific_payload_sha256 payload source production structural_verdict"
SOURCE_KEYS = "provider exact_url doi citation rights_decision rights_statement attribution"
STATION_KEYS = "station_id latitude_deg longitude_deg receiver_height_m surface_height_m original_value value_mgal gravity_sigma receiver_sigma_m surface_sigma_m latitude_sigma_deg"
METADATA_KEYS = "source_kind source_sha256 source_citation rights crs reference_ellipsoid height_datum height_unit height_sign gravity_unit gravity_sign gravity_quantity gravity_datum tide_system instrument_processing"


def scientific_digest(value):
    return digest(value, scientific=True)


def number(value, low=-math.inf, high=math.inf):
    require(type(value) in (int, float), "physical_number")
    require(math.isfinite(value) and low <= value <= high, "physical_number")


def nonblank(value):
    text(value)
    require(bool(value.strip()), "physical_text")


def terrain_structure(value, station_ids):
    fields(value, "kind unit height_reference density_kg_m3 source_sha256 method station_ids additions_mgal sigma_mgal")
    require((value["kind"], value["unit"], value["height_reference"]) ==
            ("additive_residual_to_plate", "mGal", "WGS84_ellipsoid"), "physical_terrain_declaration")
    number(value["density_kg_m3"], 1, 10000)
    sha(value["source_sha256"])
    nonblank(value["method"])
    require(value["station_ids"] == station_ids, "physical_terrain_stations")
    for key in ("additions_mgal", "sigma_mgal"):
        require(type(value[key]) is list and len(value[key]) == len(station_ids), "physical_terrain_count")
        for item in value[key]:
            number(item, 0 if key == "sigma_mgal" else -math.inf)


def root_structure(value):
    fields(value, "schema_version metadata state stations history")
    require(value["schema_version"] == "gravity-stations-1" and value["state"] in STATES, "physical_root_schema")
    metadata = value["metadata"]
    require(type(metadata) is dict, "physical_metadata")
    orthometric = metadata.get("height_datum") == "orthometric"
    fields(metadata, METADATA_KEYS + (" geoid_model" if orthometric else ""))
    for key in metadata:
        if key != "instrument_processing":
            nonblank(metadata[key])
    sha(metadata["source_sha256"])
    require(metadata["source_kind"] in ("field", "synthetic_control")
            and metadata["height_datum"] in ("ellipsoidal", "orthometric")
            and metadata["gravity_unit"] in ("mGal", "m/s^2", "microGal")
            and metadata["gravity_sign"] in ("downward", "upward"), "physical_metadata_declaration")
    for key, expected in (("crs", "EPSG:4326"), ("reference_ellipsoid", "WGS84"), ("height_unit", "m"),
                          ("height_sign", "upward"), ("gravity_quantity", "absolute_gravity"), ("tide_system", "tide_free")):
        require(metadata[key] == expected, "physical_metadata_declaration")
    instrument = metadata["instrument_processing"]
    fields(instrument, "calibration drift tide")
    for key, entry in instrument.items():
        fields(entry, "status citation")
        require(entry["status"] in ("applied", "not_applicable") and
                (key != "calibration" or entry["status"] == "applied"), "physical_instrument_declaration")
        nonblank(entry["citation"])
    stations = value["stations"]
    require(type(stations) is list and 1 <= len(stations) <= 400, "physical_station_count")
    seen = set()
    for station in stations:
        fields(station, STATION_KEYS + (" geoid_m geoid_sigma_m" if orthometric else ""))
        nonblank(station["station_id"])
        require(station["station_id"] not in seen, "physical_station_duplicate")
        seen.add(station["station_id"])
        for key in station:
            if key != "station_id":
                number(station[key], 0 if key.endswith("sigma") or "sigma_" in key else -math.inf)
        number(station["latitude_deg"], -90, 90)
        number(station["longitude_deg"], -180, 180)
    history = value["history"]
    require(type(history) is list and len(history) == (0, 2, 3, 4)[STATES.index(value["state"])], "physical_history_count")
    ids = [station["station_id"] for station in stations]
    for index, item in enumerate(history):
        fields(item, "name parameters additions_mgal input_values_sha256 output_values_sha256")
        require(item["name"] == HISTORY[index], "physical_history_order")
        sha(item["input_values_sha256"])
        sha(item["output_values_sha256"])
        require(type(item["additions_mgal"]) is list and len(item["additions_mgal"]) == len(stations), "physical_history_count")
        for addition in item["additions_mgal"]:
            number(addition)
        parameters = item["parameters"]
        if index < 2:
            fields(parameters, "ellipsoid height_reference boule" + (" height_term" if index == 1 else ""))
            require((parameters["ellipsoid"], parameters["height_reference"], parameters["boule"]) ==
                    ("WGS84", "WGS84_ellipsoid", "0.5.0"), "physical_history_parameters")
            if index == 1:
                require(parameters["height_term"] == "gamma(phi,0)-gamma(phi,h)", "physical_history_parameters")
        elif index == 2:
            fields(parameters, "harmonica density_kg_m3 density_sigma_kg_m3 geometry height_reference")
            require((parameters["harmonica"], parameters["geometry"], parameters["height_reference"]) ==
                    ("0.7.0", "land_infinite_plate", "WGS84_ellipsoid"), "physical_history_parameters")
            number(parameters["density_kg_m3"], 1, 10000)
            number(parameters["density_sigma_kg_m3"], 0, 10000)
        else:
            terrain_structure(parameters, ids)
    require(len(canonical(value, scientific=True)) <= 8*M, "physical_scientific_root_limit")
    return value  # Identity/presence/native number representation are unchanged.


def parse_root(chunks):
    value = decode_source(chunks, max_bytes=16*M, depth=16, nodes=200000)
    return root_structure(value)


def source_structure(value):
    fields(value, SOURCE_KEYS)
    for key, item in value.items():
        if item is not None:
            nonblank(item)
        else:
            require(key in ("exact_url", "doi", "citation"), "physical_source_null")


def root_envelope(chunks):
    value = decode_source(chunks, max_bytes=16*M, depth=32, nodes=2250000)
    fields(value, DATASET_KEYS)
    require(value["schema"] == "geophysics.physical-dataset/v2", "physical_dataset_schema")
    for key in ("dataset_id", "owner_id", "project_id", "raw_asset_id", "root_dataset_id"):
        uuid(value[key])
    for key in ("raw_sha256", "scientific_payload_sha256"):
        sha(value[key])
    integer(value["version"], 1, 1)
    integer(value["raw_bytes"], 1, 16*M)
    require(value["root_dataset_id"] == value["dataset_id"] and value["parent_dataset_id"] is None
            and value["parent_dataset_sha256"] is None and value["production"] is None
            and (value["parser_version"], value["kind"], value["modality"], value["payload_schema"], value["structural_verdict"]) ==
            ("gravity-stations-json/v1", "root", "gravity_physical_station", "gravity-stations-1", "structural_only"),
            "physical_root_identity")
    root_structure(value["payload"])
    require(scientific_digest(value["payload"]) == value["scientific_payload_sha256"], "physical_payload_hash")
    source_structure(value["source"])
    return value


def make_root_envelope(payload, *, dataset_id, owner_id, project_id, raw_asset_id, raw_sha256, raw_bytes, source):
    value = dict(schema="geophysics.physical-dataset/v2", dataset_id=dataset_id, version=1,
                 owner_id=owner_id, project_id=project_id, raw_asset_id=raw_asset_id,
                 raw_sha256=raw_sha256, raw_bytes=raw_bytes, parser_version="gravity-stations-json/v1",
                 root_dataset_id=dataset_id, parent_dataset_id=None, parent_dataset_sha256=None,
                 kind="root", modality="gravity_physical_station", payload_schema="gravity-stations-1",
                 scientific_payload_sha256=scientific_digest(payload), payload=payload, source=source,
                 production=None, structural_verdict="structural_only")
    body = canonical(value)
    root_envelope([body])
    return body
