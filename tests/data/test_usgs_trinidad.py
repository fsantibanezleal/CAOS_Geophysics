"""Synthetic protocol controls for the source-pinned Trinidad stream processor."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

import usgs_trinidad as trinidad


def _write_source(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=trinidad.CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _row(*, flight: int, line: int, fid: float, east: float, north: float,
         rmi: float, tmi: float, igrf: float) -> dict[str, str]:
    row = {name: "1" for name in trinidad.CSV_FIELDS}
    row.update(date="20240902", flight=str(flight), line=str(line), fid=str(fid),
        time_ssm=str(fid), easting_WGS84=str(east), northing_WGS84=str(north),
        longitude_WGS84="-124.0", latitude_WGS84="41.0", mag_rmi=str(rmi),
        mag_tmi=str(tmi), igrf=str(igrf))
    return row


def test_streams_full_rows_into_noninterpolated_tiles_and_lines(tmp_path):
    raw = tmp_path / "survey.csv"
    _write_source(raw, [
        _row(flight=11, line=10010, fid=10, east=370620, north=4643140,
             rmi=-2, tmi=100, igrf=102),
        _row(flight=11, line=10010, fid=20, east=370650, north=4643170,
             rmi=2, tmi=104, igrf=102),
        _row(flight=12, line=10011, fid=30, east=371000, north=4643600,
             rmi=5, tmi=105, igrf=100),
    ])
    output = tmp_path / "derived"
    result = trinidad.process(raw, output, verify_official_source=False)
    summary = result["summary"]
    assert summary["original"]["rows"] == 3
    assert summary["original"]["sha256"] == hashlib.sha256(raw.read_bytes()).hexdigest()
    assert summary["survey"]["flight_count"] == 2
    assert summary["survey"]["line_count"] == 2
    assert summary["identity_check"]["absolute_difference_max_nT"] == 0
    assert summary["claims"] == {
        "field_data": False, "full_source_verified": False, "geology_truth_known": False,
        "measurement_uncertainty_known": False, "inverse_performed": False,
        "induced_susceptibility_eligible": False, "interpolation_performed": False,
    }
    fine = json.loads((output / "tiles-120m.json").read_text(encoding="utf-8"))
    assert fine["aggregation"] == "observed_point_mean_min_max_count"
    assert fine["interpolation"] is False
    assert sum(cell["count"] for cell in fine["cells"]) == 3
    first = next(line for line in json.loads((output / "lines.json").read_text(encoding="utf-8"))
                 if line["flight"] == 11)
    assert first["count"] == 2
    assert first["fid_start"] == 10 and first["fid_end"] == 20
    assert first["mag_rmi"]["mean"] == 0


@pytest.mark.parametrize("mutation", ["header", "row-width", "nonfinite"])
def test_rejects_malformed_or_nonfinite_rows_before_publishing(tmp_path, mutation):
    raw = tmp_path / "bad.csv"
    row = _row(flight=11, line=10010, fid=10, east=370620, north=4643140,
               rmi=-2, tmi=100, igrf=102)
    if mutation == "header":
        raw.write_text("wrong,header\n1,2\n", encoding="utf-8")
    elif mutation == "row-width":
        _write_source(raw, [row])
        with raw.open("a", encoding="utf-8", newline="") as stream:
            stream.write("extra\n")
    else:
        row["mag_rmi"] = "NaN"
        _write_source(raw, [row])
    output = tmp_path / "derived"
    with pytest.raises(trinidad.SourceError):
        trinidad.process(raw, output, verify_official_source=False)
    assert not output.exists()


def test_official_source_admission_checks_size_before_creating_outputs(tmp_path):
    raw = tmp_path / "not-the-official-survey.csv"
    _write_source(raw, [_row(flight=11, line=10010, fid=10, east=370620,
                             north=4643140, rmi=-2, tmi=100, igrf=102)])
    output = tmp_path / "derived"
    with pytest.raises(trinidad.SourceError, match="size differs"):
        trinidad.process(raw, output)
    assert not output.exists()
