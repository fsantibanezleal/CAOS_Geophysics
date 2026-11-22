"""Strict USGS Amargosa parsing and deterministic M03 flight-track selection."""
from __future__ import annotations

import gzip
import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from magnetic_amargosa import AmargosaError, _read_archive, select_tracks  # noqa: E402
from sources import load_ledger  # noqa: E402


def _record_line(line_id: str, lon: float, lat: float, height: float, levelled: float) -> bytes:
    row = (f"{line_id:<8}{lon:12.6f}{lat:10.6f}{height:7.1f}{height + 1:7.1f}"
           f"{50_000.0:9.2f}{levelled + 0.1:9.2f}{levelled:9.2f}\n")
    encoded = row.encode("ascii")
    assert len(encoded.rstrip(b"\n")) == 71
    return encoded


def _small_archive(tmp_path: Path, rows: list[bytes]) -> tuple[Path, dict]:
    path = tmp_path / "amargosa.xyz.gz"
    payload = b"".join(rows)
    with gzip.open(path, "wb") as stream:
        stream.write(payload)
    raw = path.read_bytes()
    record = dict(load_ledger()["usgs-amargosa-aeromagnetic"])
    record.update(expected_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                  expanded_bytes=len(payload), record_count=len(rows))
    return path, record


def test_fixed_width_reader_keeps_channel_identity_and_checks_exact_archive(tmp_path):
    path, record = _small_archive(tmp_path, [_record_line("FL001", -116.5, 36.7, 150.0, -12.5)])
    data = _read_archive(path, record)
    assert data["source_record_count"] == 1
    assert data["line_ids"] == ["FL001"]
    assert data["levelled_anomaly_nT"].tolist() == [-12.5]
    assert data["total_field_anomaly_nT"].tolist() == [-12.4]
    assert data["uncorrected_field_nT"].tolist() == [50_000.0]
    assert np.isfinite(data["easting_m"]).all() and np.isfinite(data["northing_m"]).all()


def test_reader_rejects_corrupt_gzip_and_fixed_width_drift(tmp_path):
    path, record = _small_archive(tmp_path, [b"too short\n"])
    with pytest.raises(AmargosaError, match="expected 71 fixed-width bytes"):
        _read_archive(path, record)
    path.write_bytes(b"not gzip")
    record.update(expected_bytes=8, sha256=hashlib.sha256(b"not gzip").hexdigest())
    with pytest.raises(AmargosaError, match="gzip stream is invalid"):
        _read_archive(path, record)


def _selection_fixture():
    x: list[float] = []
    y: list[float] = []
    line_ids: list[str] = []
    height: list[float] = []
    field: list[float] = []
    for line_index, northing in enumerate((0.0, 50.0, 100.0, 150.0)):
        for easting in (0.0, 50.0, 100.0, 150.0, 200.0):
            x.append(easting)
            y.append(northing)
            line_ids.append(f"FL{line_index:03d}")
            height.append(150.0)
            field.append(0.3 * easting - 0.15 * northing)
    # A shorter duplicate segment is grouped with FL000 and must not be a second
    # validation line or enter the selected fit rows.
    for easting in (25.0, 75.0):
        x.append(easting)
        y.append(1.0)
        line_ids.append("FL000S")
        height.append(150.0)
        field.append(0.3 * easting - 0.15)
    for northing in (0.0, 50.0, 100.0, 150.0, 200.0):
        x.append(100.0)
        y.append(northing)
        line_ids.append("TL000")
        height.append(151.0)
        field.append(30.0 - 0.15 * northing)
    return {"line_ids": line_ids, "easting_m": np.asarray(x), "northing_m": np.asarray(y),
            "radar_height_m": np.asarray(height), "levelled_anomaly_nT": np.asarray(field)}


def test_track_clustering_selects_one_longest_segment_per_physical_line():
    rows, manifest = select_tracks(_selection_fixture(), bounds=(-1, 251, -1, 251),
                                   flight_cluster_m=10, tie_cluster_m=10)
    assert manifest["track_count"] == {"flight": 4, "tie": 1}
    assert manifest["roi_source_record_count"] == 27
    assert manifest["selected_row_count"] == 25
    first = next(item for item in manifest["tracks"] if item["track_id"] == "F001")
    assert first["representative_source_line_id"] == "FL000"
    assert first["source_segment_ids_in_cluster"] == ["FL000", "FL000S"]
    assert first["discarded_segment_ids"] == ["FL000S"]
    assert len({row["track_id"] for row in rows if row["role"] == "flight"}) == 4
    assert all(row["track_id"] != "FL000S" for row in rows)


def test_track_selection_is_deterministic_and_rejects_invalid_bounds():
    data = _selection_fixture()
    first = select_tracks(data, bounds=(-1, 251, -1, 251), flight_cluster_m=10, tie_cluster_m=10)
    second = select_tracks(data, bounds=(-1, 251, -1, 251), flight_cluster_m=10, tie_cluster_m=10)
    assert first == second
    with pytest.raises(AmargosaError, match="positive width and height"):
        select_tracks(data, bounds=(0, 0, 0, 1))
