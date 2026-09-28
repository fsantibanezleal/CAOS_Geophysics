"""Synthetic format oracles; real STEAD bytes remain local and separately gated."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import h5py
import numpy as np
import pytest

from stead_phase import (
    SteadFormatError, SteadHdfReader, SteadMember, file_sha256, hash_partition,
    normalize_counts, select_metadata,
)


FIELDS = [
    "station_network_code", "station_code", "source_id", "trace_category",
    "trace_p_arrival_sample", "trace_s_arrival_sample", "trace_p_status",
    "trace_s_status", "trace_name_original", "trace_name", "trace_channel",
]


def _fake_metadata(path: Path) -> tuple[int, str]:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for index in range(500):
            writer.writerow({
                "station_network_code": "XX", "station_code": f"S{index}",
                "source_id": f"event-{index}", "trace_category": "earthquake_local",
                "trace_p_arrival_sample": "700.0", "trace_s_arrival_sample": "1894.0",
                "trace_p_status": "manual", "trace_s_status": "manual",
                "trace_name_original": f"event-{index}-trace", "trace_name": f"bucket17${index},:3,:6000",
                "trace_channel": "BH",
            })
            writer.writerow({
                "station_network_code": "XX", "station_code": f"S{index}",
                "source_id": "", "trace_category": "noise",
                "trace_p_arrival_sample": "", "trace_s_arrival_sample": "",
                "trace_p_status": "", "trace_s_status": "",
                "trace_name_original": f"noise-{index}-trace", "trace_name": f"bucket18${index},:3,:6000",
                "trace_channel": "BH",
            })
    return path.stat().st_size, file_sha256(path)


def test_joint_metadata_selection(tmp_path):
    path = tmp_path / "metadata.csv"
    size, digest = _fake_metadata(path)
    caps = {partition: {"earthquake_local": 4, "noise": 3}
            for partition in ("train", "dev", "test")}
    selected, report = select_metadata(path, caps=caps, expected_bytes=size, expected_sha256=digest)
    again, second = select_metadata(path, caps=caps, expected_bytes=size, expected_sha256=digest)
    assert report == second and selected == again
    assert report["source_split_ignored"] is True
    assert all(len(selected[partition]) == 7 for partition in caps)
    for first, second_partition in (("train", "dev"), ("train", "test"), ("dev", "test")):
        assert not ({row.station_id for row in selected[first]}
                    & {row.station_id for row in selected[second_partition]})
        assert not ({row.event_id for row in selected[first] if row.event_id}
                    & {row.event_id for row in selected[second_partition] if row.event_id})
    assert report["reasons"]["event-station-partition-conflict"] > 0
    assert hash_partition("event", "event-1") in caps
    with pytest.raises(SteadFormatError, match="SHA-256"):
        select_metadata(path, caps=caps, expected_bytes=size, expected_sha256="0" * 64)


def _fake_hdf(path: Path, *, component_order="ZNE") -> SteadMember:
    with h5py.File(path, "w") as handle:
        fmt = handle.create_group("data_format")
        for key, value in {
            "dimension_order": "CW", "component_order": component_order,
            "sampling_rate": 100, "unit": "counts", "instrument_response": "not restituted",
        }.items():
            fmt.create_dataset(key, data=value)
        block = handle.create_dataset("data/bucket17", (1, 3, 6000), dtype="f4")
        time = np.arange(6000, dtype=np.float32)
        block[0, 0] = time + 10  # Z
        block[0, 1] = time + 20  # N
        block[0, 2] = time + 30  # E
    return SteadMember("original", "bucket17$0,:3,:6000", "event", "XX.S1",
                       "test", "earthquake_local", "BH", 700, 1894)


def test_bucket_reader_and_rejections(tmp_path):
    path = tmp_path / "waveforms.hdf5"
    member = _fake_hdf(path)
    digest = file_sha256(path)
    with SteadHdfReader(path, expected_sha256=digest, expected_bytes=path.stat().st_size) as reader:
        trace = reader.read(member)
        assert trace.values_counts_enz.shape == (6000, 3)
        assert trace.sample_interval_s == 0.01
        assert trace.values_counts_enz[0].tolist() == [30, 20, 10]
        normalized, factors = normalize_counts(trace.values_counts_enz)
        assert normalized.shape == (6000, 3)
        assert factors["component_order"] == ["E", "N", "Z"]
        assert np.max(np.abs(normalized), axis=0) == pytest.approx([1, 1, 1])
        with pytest.raises(SteadFormatError, match="reviewed STEAD bucket slice"):
            reader.read(SteadMember(**{**member.__dict__, "trace_name": "../other$0,:3,:6000"}))
        with pytest.raises(SteadFormatError, match="trace index"):
            reader.read(SteadMember(**{**member.__dict__, "trace_name": "bucket17$9,:3,:6000"}))
    with pytest.raises(SteadFormatError, match="SHA-256"):
        SteadHdfReader(path, expected_sha256="f" * 64, expected_bytes=path.stat().st_size)
    member = _fake_hdf(path, component_order="ENZ")
    with pytest.raises(SteadFormatError, match="component_order"):
        SteadHdfReader(path, expected_sha256=file_sha256(path), expected_bytes=path.stat().st_size)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == file_sha256(path)
    assert member.event_id == "event"
