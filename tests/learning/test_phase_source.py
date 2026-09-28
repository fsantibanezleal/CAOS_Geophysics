"""Source and waveform contract tests for the M13/M08 phase-picking lane."""

import csv
import hashlib
import io
from pathlib import Path
import zipfile

import numpy as np
import pytest

from phase_picking import ArchiveError, load_phase_archive, split_by_event_and_station

ROOT = Path(__file__).resolve().parents[2]
LOCAL_SOURCE = ROOT / "data/raw/phasenet/test_data.zip"
SOURCE_SHA256 = "60476821a71697ded05884c225c75ae7e0099bd9a7b79c4e2bdc9e7b3a5706b3"


def make_archive(path, *, p=120, s=180, dt=0.01, unit="m/s", member="test_data/npz/CI.AAA..HH.1.npz", data=None):
    if data is None:
        data = np.zeros((512, 3), dtype=np.float32)
        data[120:124, 2] = 1
        data[180:184, 2] = 2
    raw = io.BytesIO()
    np.savez_compressed(
        raw, data=data, dt=dt, p_idx=p, s_idx=s, unit=unit, channels="HHZ",
        event_index=1, network="CI", station="AAA", location_code="",
    )
    table = io.StringIO()
    writer = csv.DictWriter(
        table,
        fieldnames=["fname", "network", "station", "location_code", "p_idx", "s_idx", "dt", "unit", "event_index", "channels"],
        delimiter="\t",
    )
    writer.writeheader()
    writer.writerow(dict(
        fname="CI.AAA..HH.1.npz", network="CI", station="AAA", location_code="",
        p_idx=p, s_idx=s, dt=dt, unit=unit, event_index=1, channels="HHZ",
    ))
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("test_data/npz.csv", table.getvalue())
        archive.writestr(member, raw.getvalue())
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_archive_receipt_and_rejections(tmp_path):
    path = tmp_path / "source.zip"
    digest = make_archive(path)
    traces = load_phase_archive(path, expected_sha256=digest)
    assert len(traces) == 1
    assert traces[0].p_index == 120
    assert traces[0].s_index == 180
    assert traces[0].component_present == (False, False, True)
    assert traces[0].source_sha256 == digest
    with pytest.raises(ArchiveError, match="SHA-256"):
        load_phase_archive(path, expected_sha256="0" * 64)
    with pytest.raises(ArchiveError, match="entry"):
        load_phase_archive(path, expected_sha256=digest, max_entries=1)
    make_archive(path, member="test_data/npz/../escape.npz")
    with pytest.raises(ArchiveError, match="path"):
        load_phase_archive(path, expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (dict(p=190, s=180), "pick"),
        (dict(dt=0), "sample interval"),
        (dict(unit="counts"), "unit"),
        (dict(data=np.full((512, 3), np.nan, dtype=np.float32)), "finite"),
    ],
)
def test_trace_contract_rejects_ambiguity(tmp_path, change, message):
    path = tmp_path / "invalid.zip"
    digest = make_archive(path, **change)
    with pytest.raises(ArchiveError, match=message):
        load_phase_archive(path, expected_sha256=digest)


@pytest.mark.skipif(not LOCAL_SOURCE.is_file(), reason="24.9 MB provider source is deliberately not committed")
def test_local_real_fixture_receipt_and_disjoint_partitions():
    traces = load_phase_archive(LOCAL_SOURCE, expected_sha256=SOURCE_SHA256, reject_ambiguous=False)
    assert len(traces) == 93
    assert {trace.sample_interval_s for trace in traces} == {0.01}
    assert {trace.unit for trace in traces} == {"m/s", "m/s**2"}
    split = split_by_event_and_station(traces, salt="phasenet-fixture-v1")
    assert {key: len(value) for key, value in split.members.items()} == {
        "train": 61, "dev": 17, "test": 15,
    }
