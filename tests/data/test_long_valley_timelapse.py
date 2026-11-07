from __future__ import annotations

import csv
import os
from pathlib import Path

import pytest

from long_valley_timelapse import difference, parse_source


def write_table(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream, delimiter="\t", lineterminator="\n").writerows(rows)


def test_real_archive_parses_and_preserves_epoch_values():
    data_root = os.environ.get("GEOPHYSICS_LOCAL_DATA_ROOT")
    if not data_root:
        pytest.skip("set GEOPHYSICS_LOCAL_DATA_ROOT to run the source-bound USGS archive control")
    source = parse_source(Path(data_root) / "data/downloads/long-valley/GravitySurveys.txt")
    assert source["epochs"] == ["1980-06", "1982-06", "1982-09", "1983-07", "1984-07", "1985-07", "1998-07", "1999-07"]
    assert len(source["stations"]) == 37
    by_id = {row["station_id"]: row for row in source["stations"]}
    station = by_id["12DOR75"]
    assert station["measurements"][0]["epoch"] == "1982-06"
    assert station["measurements"][0]["gravity_mgal"] == pytest.approx(979242.333)
    assert station["measurements"][0]["sigma_mgal"] == pytest.approx(0.005)
    suspect = next(m for m in by_id["1JD1952"]["measurements"] if m["epoch"] == "1982-09")
    assert suspect["gravity_mgal"] == pytest.approx(979255.21)
    assert suspect["qc"]["status"] == "suspect"
    assert len(difference(source, "1982-09", "1999-07")["stations"]) == 23
    assert len(difference(source, "1982-09", "1999-07", include_suspect=True)["stations"]) == 24


def test_difference_uses_common_stations_and_propagates_one_sigma():
    data = {
        "epochs": ["a", "b"],
        "stations": [
            {"station_id": "S1", "easting_m": 10, "northing_m": 20, "measurements": [
                {"epoch": "a", "gravity_mgal": 979000.0, "sigma_mgal": 0.003},
                {"epoch": "b", "gravity_mgal": 978999.9, "sigma_mgal": 0.004},
            ]},
            {"station_id": "S2", "easting_m": 30, "northing_m": 40, "measurements": [
                {"epoch": "a", "gravity_mgal": 1.0, "sigma_mgal": 0.1},
            ]},
        ],
    }
    result = difference(data, "a", "b")
    assert len(result["stations"]) == 1
    row = result["stations"][0]
    assert row["delta_gravity_mgal"] == pytest.approx(-0.1)
    assert row["delta_sigma_independent_mgal"] == pytest.approx(0.005)
    assert row["standardized_delta_independent"] == pytest.approx(-20)
    assert result["difference_convention"] == "later-minus-earlier"


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf", "bad"])
def test_rejects_nonfinite_or_non_numeric_observation(tmp_path: Path, bad: str):
    file = tmp_path / "bad.tsv"
    write_table(file, [
        ["STATION", "X (UTM)", "Y (UTM)", " JUNE 1982", "StDev", " JULY 1999", "StDev"],
        ["S1", "1", "2", bad, "0.1", "3", "0.1"],
    ])
    with pytest.raises(ValueError):
        parse_source(file)


def test_rejects_duplicate_station_id_and_unpaired_sigma(tmp_path: Path):
    file = tmp_path / "bad.tsv"
    header = ["STATION", "X (UTM)", "Y (UTM)", " JUNE 1982", "StDev", " JULY 1999", "StDev"]
    write_table(file, [header, ["S1", "1", "2", "3", "0.1", "", ""], ["S1", "4", "5", "3", "0.1", "4", "0.1"]])
    with pytest.raises(ValueError, match="duplicate station ID"):
        parse_source(file)
    write_table(file, [header, ["S1", "1", "2", "3", "0.1", "4", ""]])
    with pytest.raises(ValueError, match="must both be present"):
        parse_source(file)


def test_rejects_missing_epoch_and_nonpositive_sigma(tmp_path: Path):
    file = tmp_path / "bad.tsv"
    write_table(file, [
        ["STATION", "X (UTM)", "Y (UTM)", " JUNE 1982", "StDev", " JULY 1999", "StDev"],
        ["S1", "1", "2", "3", "0", "4", "0.1"],
    ])
    with pytest.raises(ValueError, match="must be positive"):
        parse_source(file)
    write_table(file, [
        ["STATION", "X (UTM)", "Y (UTM)", " JUNE 1982", "StDev", " JULY 1999", "StDev"],
        ["S1", "1", "2", "3", "0.1", "", ""],
    ])
    parsed = parse_source(file)
    with pytest.raises(ValueError, match="no common stations"):
        difference(parsed, "1982-06", "1999-07")
