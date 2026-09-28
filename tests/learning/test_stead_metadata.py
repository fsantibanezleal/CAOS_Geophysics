"""STEAD metadata-only split design and input receipt tests."""

import csv
import hashlib
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import profile_stead_metadata as stead  # noqa: E402


def sample_metadata(path):
    fields = [
        "station_network_code", "station_code", "source_id", "trace_category",
        "trace_p_arrival_sample", "trace_s_arrival_sample", "trace_name_original", "split",
    ]
    rows = [
        ("CI", "A", "E1", "earthquake_local", "100", "200", "T1", "train"),
        ("CI", "B", "E1", "earthquake_local", "100", "200", "T2", "test"),
        ("CI", "A", "E2", "earthquake_local", "100", "200", "T3", "dev"),
        ("CI", "C", "E3", "earthquake_local", "100", "200", "T4", "train"),
        ("CI", "C", "", "noise", "", "", "N1", "test"),
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)


def test_metadata_receipt_and_no_joint_hash_leakage(tmp_path, monkeypatch):
    path = tmp_path / "metadata.csv"
    sample_metadata(path)
    monkeypatch.setattr(stead, "SOURCE_BYTES", path.stat().st_size)
    monkeypatch.setattr(stead, "SOURCE_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())
    result = stead.profile(path)
    rows = result["rows"]
    assert rows["total"] == 5
    assert rows["earthquake_eligible_p_before_s"] == 4
    prior = result["published_split_leakage_on_eligible_earthquakes"]
    assert prior["events_in_multiple_partitions"] == 1
    assert prior["stations_in_multiple_partitions"] == 1
    proposed = result["proposed_joint_hash_split"]
    assert sum(proposed["eligible_counts"].values()) + proposed["cross_partition_event_station_traces_quarantined"] == 4
    assert proposed["event_and_station_disjoint_by_construction"] is True
    with path.open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(ValueError, match="byte count"):
        stead.profile(path)
