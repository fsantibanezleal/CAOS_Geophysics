"""Physical metadata is explicit and field-specific."""

from __future__ import annotations

import copy
import json
import struct

import pytest

from tests.api.conftest import gravity_metadata


@pytest.mark.parametrize("field", [
    "epsg", "horizontal_datum", "vertical_datum", "vertical_positive", "epoch_utc", "component_frame",
])
def test_missing_physical_metadata_rejection(harness, field):
    harness.account()
    project = harness.project()
    meta = gravity_metadata()
    del meta["physical"][field]
    response = harness.upload(project["id"], metadata=meta)
    assert response.status_code == 422, response.text
    assert any(field in item for item in response.json()["fields"])
    assert harness.client.get(f"/api/projects/{project['id']}/assets").json()["assets"] == []


def test_units_crs_and_geometry_column_are_checked(harness):
    harness.account()
    project = harness.project()
    for key, value, expected in (
        ("measurement_unit", "kg", "physical.measurement_unit"),
        ("coordinate_reference", "local", "physical.local_crs"),
    ):
        meta = gravity_metadata()
        meta["physical"][key] = value
        response = harness.upload(project["id"], metadata=meta)
        assert response.status_code == 422 and expected in response.json()["fields"]
    meta = copy.deepcopy(gravity_metadata())
    meta["physical"]["geometry"]["x_column"] = "wrong_x"
    response = harness.upload(project["id"], metadata=meta)
    assert response.status_code == 422
    assert "physical.geometry.x_column" in response.json()["fields"]


def test_invalid_epsg_orientation_and_nonfinite_rejected(harness):
    harness.account()
    project = harness.project()
    for field, value, expected in (
        ("epsg", 999999, "physical.epsg"),
        ("horizontal_datum", "North American Datum 1927", "physical.horizontal_datum"),
        ("horizontal_unit", "degree", "physical.horizontal_unit"),
        ("axis_order", "lon_lat", "physical.axis_order"),
        ("component_frame", "unknown", "physical.component_frame"),
    ):
        meta = gravity_metadata()
        meta["physical"][field] = value
        result = harness.upload(project["id"], metadata=meta)
        assert result.status_code == 422, result.text
        assert expected in result.json()["fields"]
    meta = gravity_metadata()
    meta["physical"]["geometry"]["station_id_column"] = float("nan")
    result = harness.request(
        "POST", f"/api/projects/{project['id']}/assets", content=b"not stored",
        headers={"Content-Type": "text/csv", "X-Asset-Metadata": json.dumps(meta)},
    )
    assert result.status_code == 422
    assert harness.client.get(f"/api/projects/{project['id']}/assets").json()["assets"] == []


def test_geotiff_needs_geokey_and_declared_grid_shape(harness):
    harness.account()
    project = harness.project()
    # Little-endian TIFF with width/height tags, but no GeoTIFF georeferencing tag.
    tiff = b"II*\x00" + struct.pack("<I", 8) + struct.pack("<H", 2)
    tiff += struct.pack("<HHII", 256, 4, 1, 10)
    tiff += struct.pack("<HHII", 257, 4, 1, 20) + struct.pack("<I", 0)
    meta = gravity_metadata(tiff)
    meta.update({"filename": "grid.tif", "mime": "image/tiff", "format": "geotiff"})
    meta["physical"].update({"measurement_unit": "nT", "component_frame": "total field"})
    meta["physical"]["geometry"] = {"rows": 20, "columns": 10, "pixel_width": 1, "pixel_height": 1}
    assert harness.upload(project["id"], tiff, meta).status_code == 415


def test_format_specific_byte_limit(harness):
    harness.account()
    project = harness.project()
    payload = b">HEAD\n>FREQ\n" + b"x" * (5 * 1024 * 1024)
    meta = gravity_metadata(payload)
    meta.update({"filename": "station.edi", "mime": "text/plain", "format": "edi"})
    meta["physical"].update({"measurement_unit": "ohm", "component_frame": "geographic ENU"})
    meta["physical"]["geometry"] = {
        "station_id": "S1", "frequency_count": 2,
        "tensor_components": ["Zxx", "Zxy", "Zyx", "Zyy"], "rotation_degrees": 0,
    }
    result = harness.upload(project["id"], payload, meta)
    assert result.status_code == 413, result.text


@pytest.mark.parametrize("format_name, geometry, expected", [
    ("edi", {"station_id": "S1", "frequency_count": 2, "tensor_components": [{}], "rotation_degrees": 0},
     "physical.geometry.tensor_components"),
    ("stationxml", {"network": "N", "station": "S", "channels": ["BHZ", {}],
                    "response_epoch_utc": "2026-09-27T12:00:00Z", "channel_orientation_deg": {}},
     "physical.geometry.channels"),
])
def test_malformed_nested_geometry_is_a_client_error(harness, format_name, geometry, expected):
    harness.account()
    project = harness.project()
    meta = gravity_metadata()
    meta["format"] = format_name
    meta["physical"]["geometry"] = geometry
    result = harness.upload(project["id"], metadata=meta)
    assert result.status_code == 422, result.text
    assert expected in result.json()["fields"]


def test_miniseed_companion_must_be_owned(harness):
    harness.account()
    project = harness.project()
    stationxml = b'<FDSNStationXML><Network code="N"><Station code="S"><Channel code="BHZ"/></Station></Network></FDSNStationXML>'
    meta = gravity_metadata(stationxml)
    meta.update({"filename": "station.xml", "mime": "application/xml", "format": "stationxml"})
    meta["physical"].update({"measurement_unit": "counts", "component_frame": "channel azimuth/dip"})
    meta["physical"]["geometry"] = {
        "network": "N", "station": "S", "channels": ["BHZ"], "response_epoch_utc": "2026-09-27T12:00:00Z",
        "channel_orientation_deg": {"BHZ": [0, -90]},
    }
    station = harness.upload(project["id"], stationxml, meta)
    assert station.status_code == 201, station.text
    body = b"000001D " + b"\x00" * 248
    miniseed = gravity_metadata(body)
    miniseed.update({"filename": "trace.mseed", "mime": "application/vnd.fdsn.mseed", "format": "miniseed"})
    miniseed["physical"].update({"measurement_unit": "counts", "component_frame": "channel azimuth/dip"})
    miniseed["physical"]["geometry"] = {
        "network": "N", "station": "S", "channels": ["BHZ"], "sample_rate_hz": 100,
        "start_utc": "2026-09-27T12:00:00Z", "end_utc": "2026-09-27T12:01:00Z",
        "stationxml_asset_id": "00000000-0000-0000-0000-000000000000",
        "channel_orientation_deg": {"BHZ": [0, -90]},
    }
    denied = harness.upload(project["id"], body, miniseed)
    assert denied.status_code == 422 and "stationxml_asset_id" in str(denied.json()["fields"])
    miniseed["physical"]["geometry"]["stationxml_asset_id"] = station.json()["asset_id"]
    accepted = harness.upload(project["id"], body, miniseed)
    assert accepted.status_code == 201, accepted.text
