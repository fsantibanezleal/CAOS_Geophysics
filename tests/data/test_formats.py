"""Every declared raw format fails closed on missing physical metadata."""

from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.errors import ApiError
from app.formats import validate_declared_metadata
from app.schemas import RawUploadInput


COMMON_GEOMETRY = {
    "gravity_csv": {
        "station_id_column": "station",
        "x_column": "x",
        "y_column": "y",
        "z_column": "z",
        "value_column": "g",
    },
    "magnetic_csv": {
        "line_id_column": "line",
        "x_column": "x",
        "y_column": "y",
        "z_column": "z",
        "value_column": "field",
    },
    "traveltime_csv": {
        "source_x_column": "sx",
        "source_y_column": "sy",
        "receiver_x_column": "rx",
        "receiver_y_column": "ry",
        "time_column": "time",
    },
    "ert_csv": {"a_column": "a", "b_column": "b", "m_column": "m", "n_column": "n", "electrode_count": 4},
    "geotiff": {"rows": 10, "columns": 12, "pixel_width": 10.0, "pixel_height": 10.0},
    "edi": {
        "station_id": "S1",
        "frequency_count": 3,
        "tensor_components": ["Zxx", "Zxy", "Zyx", "Zyy"],
        "rotation_degrees": 0.0,
    },
    "miniseed": {
        "network": "XX",
        "station": "S1",
        "channels": ["BHZ"],
        "sample_rate_hz": 100.0,
        "start_utc": "2026-09-27T12:00:00Z",
        "end_utc": "2026-09-27T12:01:00Z",
        "stationxml_asset_id": "00000000-0000-0000-0000-000000000001",
        "channel_orientation_deg": {"BHZ": [0.0, -90.0]},
    },
    "stationxml": {
        "network": "XX",
        "station": "S1",
        "channels": ["BHZ"],
        "response_epoch_utc": "2026-09-27T12:00:00Z",
        "channel_orientation_deg": {"BHZ": [0.0, -90.0]},
    },
    "segy": {
        "source_count": 2,
        "receiver_count": 12,
        "sample_interval_us": 1000,
        "samples_per_trace": 500,
        "coordinate_scalar": -100,
    },
    "mth5": {
        "survey_id": "survey-1",
        "station_id": "S1",
        "run_id": "run-1",
        "channels": ["hx", "hy", "hz"],
        "start_utc": "2026-09-27T12:00:00Z",
        "end_utc": "2026-09-27T12:01:00Z",
        "channel_orientation_deg": {"hx": [0.0, 0.0], "hy": [90.0, 0.0], "hz": [0.0, -90.0]},
    },
    "ert_ohm": {"electrode_count": 4, "measurement_count": 6},
    "traveltime_sgt": {"sensor_count": 4, "measurement_count": 6},
}

FORMAT_META = {
    "gravity_csv": ("stations.csv", "text/csv", "mGal", "local vertical down"),
    "magnetic_csv": ("lines.csv", "text/csv", "nT", "total field"),
    "traveltime_csv": ("picks.csv", "text/csv", "s", "source-receiver"),
    "ert_csv": ("ert.csv", "text/csv", "ohm", "ABMN"),
    "geotiff": ("grid.tif", "image/tiff", "mGal", "local vertical down"),
    "edi": ("station.edi", "text/plain", "ohm", "geographic ENU"),
    "miniseed": ("trace.mseed", "application/vnd.fdsn.mseed", "counts", "channel azimuth/dip"),
    "stationxml": ("station.xml", "application/xml", "counts", "channel azimuth/dip"),
    "segy": ("survey.sgy", "application/x-segy", "counts", "source-receiver"),
    "mth5": ("survey.h5", "application/x-hdf5", "nT", "channel azimuth/dip"),
    "ert_ohm": ("survey.ohm", "text/plain", "ohm", "ABMN"),
    "traveltime_sgt": ("survey.sgt", "text/plain", "s", "source-receiver"),
}


def valid_metadata(format_name: str) -> dict:
    filename, mime, unit, frame = FORMAT_META[format_name]
    local = format_name in {"ert_ohm", "traveltime_sgt"}
    return {
        "filename": filename,
        "mime": mime,
        "format": format_name,
        "source": {
            "provider": "Authored metadata control",
            "rights_statement": "Authored control data for metadata validation only.",
            "rights_decision": "mirror",
            "private_storage_permission": "attested",
            "attribution": "CAOS authored control",
        },
        "physical": {
            "coordinate_reference": "local" if local else "epsg",
            "epsg": None if local else 32719,
            "local_crs": "local survey grid, metres" if local else None,
            "axis_order": "xy",
            "horizontal_datum": "local survey grid" if local else "WGS84",
            "vertical_datum": "survey benchmark",
            "vertical_positive": "up",
            "horizontal_unit": "m",
            "vertical_unit": "m",
            "measurement_unit": unit,
            "epoch_utc": "2026-09-27T12:00:00Z",
            "component_frame": frame,
            "geometry": deepcopy(COMMON_GEOMETRY[format_name]),
        },
    }


@pytest.mark.parametrize("format_name", sorted(FORMAT_META))
def test_declared_contract_is_valid_for_each_supported_raw_format(format_name):
    validate_declared_metadata(RawUploadInput.model_validate(valid_metadata(format_name)))


@pytest.mark.parametrize("format_name", sorted(FORMAT_META))
@pytest.mark.parametrize(
    ("field", "bad_value", "expected"),
    [
        ("measurement_unit", "unknown-unit", "physical.measurement_unit"),
        ("component_frame", "unknown-frame", "physical.component_frame"),
    ],
)
def test_required_unit_and_component_frame_fail_with_field_reason(format_name, field, bad_value, expected):
    metadata = valid_metadata(format_name)
    metadata["physical"][field] = bad_value
    with pytest.raises(ApiError) as caught:
        validate_declared_metadata(RawUploadInput.model_validate(metadata))
    assert caught.value.status == 422
    assert expected in caught.value.fields


@pytest.mark.parametrize("format_name", sorted(FORMAT_META))
def test_missing_physical_metadata_rejection(format_name):
    metadata = valid_metadata(format_name)
    field = next(iter(COMMON_GEOMETRY[format_name]))
    del metadata["physical"]["geometry"][field]
    with pytest.raises(ApiError) as caught:
        validate_declared_metadata(RawUploadInput.model_validate(metadata))
    assert caught.value.status == 422
    assert f"physical.geometry.{field}" in caught.value.fields


@pytest.mark.parametrize("format_name", sorted(FORMAT_META))
def test_coordinate_reference_or_datum_cannot_be_omitted(format_name):
    metadata = valid_metadata(format_name)
    if metadata["physical"]["coordinate_reference"] == "epsg":
        metadata["physical"]["epsg"] = None
        expected = "physical.epsg"
        parsed = RawUploadInput.model_validate(metadata)
        with pytest.raises(ApiError) as caught:
            validate_declared_metadata(parsed)
        assert caught.value.status == 422
        assert expected in caught.value.fields
    else:
        metadata["physical"]["local_crs"] = None
        parsed = RawUploadInput.model_validate(metadata)
        with pytest.raises(ApiError) as caught:
            validate_declared_metadata(parsed)
        assert caught.value.status == 422
        assert "physical.local_crs" in caught.value.fields


@pytest.mark.parametrize("format_name", sorted(FORMAT_META))
def test_epoch_is_required_and_timezone_aware(format_name):
    metadata = valid_metadata(format_name)
    del metadata["physical"]["epoch_utc"]
    with pytest.raises(ValidationError) as missing:
        RawUploadInput.model_validate(metadata)
    assert any(error["loc"][-1] == "epoch_utc" for error in missing.value.errors())

    metadata = valid_metadata(format_name)
    metadata["physical"]["epoch_utc"] = "2026-09-27T12:00:00"
    with pytest.raises(ValidationError) as naive:
        RawUploadInput.model_validate(metadata)
    assert any(error["loc"][-1] == "epoch_utc" for error in naive.value.errors())
