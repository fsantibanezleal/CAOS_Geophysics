"""M03 controls use declared planar fields, never a Charleston-shaped fixture."""

from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from magnetic_processing import MagneticProcessingError, main, process, read_csv  # noqa: E402


MAPPING = {"easting": "E", "northing": "N", "value": "field", "line_id": "line",
           "line_role": "role", "sensor_height_m": "height"}


def request(*, outlier=False, duplicate=False):
    rows = []
    for line in range(5):
        x = float(line * 100)
        for sample in range(9):
            y = float(sample * 12.5)
            height = 120.0 + 0.02 * y
            if outlier and line == 2 and sample == 3:
                height += 15
            rows.append({"E": x, "N": y, "field": 50000 + 0.3 * x - 0.15 * y,
                         "line": f"F{line}", "role": "flight", "height": height})
    if duplicate:
        rows.append(dict(rows[0]))
    return {
        "schema": "magnetic-flightline-process-request-1",
        "source": {"source_id": "controlled-plane", "sha256": sha256(b"controlled bytes").hexdigest(),
                   "citation": "Authored analytic controls", "rights_decision": "local-test-only",
                   "processing_state": "synthetic total-field anomaly", "value_quantity": "total-field anomaly",
                   "value_unit": "nT", "sensor_height_reference": "above-ground"},
        "frame": {"crs": "local projected metric control", "coordinates_are_projected": True, "linear_unit": "m"},
        "mapping": MAPPING,
        "settings": {"grid_spacing_m": 12.5, "holdout_fraction": 0.2, "seed": "M03-control-v1"},
        "rows": rows,
    }


def test_blocked_whole_line_holdout_recovers_plane_without_fit_leakage():
    result = process(request())
    split = result["split"]
    assert set(split["fit_line_ids"]).isdisjoint(split["holdout_line_ids"])
    assert len(split["holdout_line_ids"]) == 1
    assert result["heldout_interpolation"]["supported_heldout_row_count"] > 0
    assert result["heldout_interpolation"]["rmse"] == pytest.approx(0, abs=2e-10)
    assert result["geometry_qc"]["estimated_flight_line_spacing_m"] == pytest.approx(100)
    assert result["claims"]["scientific_release_accepted"] is False
    assert result["claims"]["provider_grid_comparison"] is False
    assert result["claims"]["corrections_applied"] == []
    grid = result["grid"]
    assert grid["shape_yx"] == [len(grid["y_northing_m"]), len(grid["x_easting_m"])]
    assert len(grid["support_mask"]) == grid["shape_yx"][0]
    assert all(len(row) == grid["shape_yx"][1] for row in grid["support_mask"])
    assert grid["unsupported_value_encoding"] == "zero plus false support mask"


def test_height_outlier_is_reported_and_original_observation_is_retained():
    result = process(request(outlier=True))
    line = next(line for line in result["geometry_qc"]["lines"] if line["line_id"] == "F2")
    assert line["sensor_height_m"]["qc_outlier_rows"] == [3]
    assert line["sensor_height_m"]["maximum"] > line["sensor_height_m"]["median"]
    assert "No source correction" in result["limitations"][0]


def test_tie_line_remains_qc_only_and_exact_collocation_is_reported():
    data = request()
    tie = [{"E": float(sample * 50), "N": 50.0,
            "field": 50000 + 0.3 * sample * 50 - 0.15 * 50,
            "line": "T0", "role": "tie", "height": 120.0}
           for sample in range(9)]
    data["rows"].extend(tie)
    result = process(data)
    assert result["geometry_qc"]["tie_line_count"] == 1
    assert result["geometry_qc"]["exact_collocation_qc"]["cross_line_groups"] == 5
    assert result["split"]["tie_lines_used_for_fit"] is False
    assert "Tie-line observations are retained" in result["limitations"][2]


def test_exact_duplicate_training_coordinate_fails_instead_of_averaging():
    with pytest.raises(MagneticProcessingError, match="duplicate training coordinates"):
        process(request(duplicate=True))


def test_geographic_degrees_are_rejected_for_metric_spacing():
    data = request()
    data["frame"]["linear_unit"] = "degree"
    with pytest.raises(MagneticProcessingError, match="projected coordinates in metres"):
        process(data)


def test_value_quantity_and_sensor_height_reference_are_mandatory():
    data = request()
    del data["source"]["value_quantity"]
    with pytest.raises(MagneticProcessingError, match="source: exact source identity"):
        process(data)


def test_csv_adapter_requires_explicit_columns_and_hashes_original_bytes():
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "survey.csv"
        columns = list(MAPPING.values())
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=[*columns, "unmapped"])
            writer.writeheader()
            for row in request()["rows"]:
                writer.writerow({**row, "unmapped": "preserved in raw bytes"})
        prepared = read_csv(
            path, field_map=MAPPING,
            source_metadata={"source_id": "mapped-user-file", "citation": "User supplied",
                             "rights_decision": "user-declared", "processing_state": "unverified prior processing",
                             "value_unit": "nT", "value_quantity": "total-field anomaly",
                             "sensor_height_reference": "above-ground"},
            frame=request()["frame"], settings=request()["settings"],
        )
        assert prepared["source"]["sha256"] == sha256(path.read_bytes()).hexdigest()
        result = process(prepared)
        assert result["source"]["sha256"] == sha256(path.read_bytes()).hexdigest()
        assert result["heldout_interpolation"]["rmse"] == pytest.approx(0, abs=2e-10)


def test_cli_processes_a_user_csv_without_overwriting_results():
    with tempfile.TemporaryDirectory() as folder:
        directory = Path(folder)
        source = directory / "survey.csv"
        with source.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(MAPPING.values()))
            writer.writeheader()
            for row in request()["rows"]:
                writer.writerow(row)
        config = directory / "mapping.json"
        config.write_text(json.dumps({"source": {"source_id": "csv-cli", "citation": "User supplied",
                                                   "rights_decision": "user-declared",
                                                   "processing_state": "unknown prior correction state",
                                                   "value_quantity": "total-field anomaly", "value_unit": "nT",
                                                   "sensor_height_reference": "above-ground"},
                                     "frame": request()["frame"], "mapping": MAPPING,
                                     "settings": request()["settings"]}), encoding="utf-8")
        output = directory / "result.json"
        assert main(["--csv", str(source), "--config", str(config), "--output", str(output)]) == 0
        result = json.loads(output.read_text(encoding="utf-8"))
        assert result["source"]["sha256"] == sha256(source.read_bytes()).hexdigest()
        assert result["claims"]["source_hash_recomputed_from_original_bytes"] is True
        assert main(["--csv", str(source), "--config", str(config), "--output", str(output)]) == 2

