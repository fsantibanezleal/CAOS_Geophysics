"""Private waveform extraction never substitutes bad channels or reads test early."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import h5py
import numpy as np
import pytest

from stead_phase import METADATA_SHA256, file_sha256


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from extract_stead_phase import extract_partition  # noqa: E402


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    rows = [
        {"trace_id": f"trace-{i}", "trace_name": f"bucket17${i},:3,:6000",
         "event_id": f"event-{i}", "station_id": f"XX.S{i}", "partition": "train",
         "category": "earthquake_local", "channel": "BH", "p_index": 700, "s_index": 1894}
        for i in range(2)
    ]
    digest = hashlib.sha256("\n".join(row["trace_id"] for row in rows).encode()).hexdigest()
    manifest = tmp_path / "members.json"
    manifest.write_text(json.dumps({"schema": "caos.stead-phase-members.v1",
                                    "report": {"metadata_sha256": METADATA_SHA256,
                                               "selected": {"train": {"ids_sha256": digest}}},
                                    "members": {"train": rows}}), encoding="utf-8")
    hdf = tmp_path / "waveforms.hdf5"
    with h5py.File(hdf, "w") as handle:
        fmt = handle.create_group("data_format")
        for name, value in {"dimension_order": "CW", "component_order": "ZNE",
                            "sampling_rate": 100, "unit": "counts",
                            "instrument_response": "not restituted"}.items():
            fmt.create_dataset(name, data=value)
        block = handle.create_dataset("data/bucket17", (2, 3, 6000), dtype="f4")
        t = np.arange(6000, dtype=np.float32)
        block[0, 0] = np.sin(t / 9)
        block[0, 1] = np.cos(t / 12)
        block[0, 2] = np.sin(t / 17)
        block[1, 0] = np.sin(t / 9)
        block[1, 1] = np.sin(t / 9)  # exact duplicate, must remain quarantined
        block[1, 2] = np.sin(t / 17)
    return manifest, hdf


def test_extraction_retains_qc_failures_without_replacement(tmp_path):
    manifest, hdf = _fixture(tmp_path)
    output = tmp_path / "private" / "extracted"
    result = extract_partition(manifest, hdf, output, partition="train",
                               waveform_sha256=file_sha256(hdf), expected_bytes=hdf.stat().st_size,
                               private_root=tmp_path / "private")
    assert result["selected"] == 2 and result["valid"] == 1
    assert any("duplicated component" in reason for reason in result["quarantined"])
    array = np.load(output / "stead-train-normalized.npy", mmap_mode="r")
    index = json.loads((output / "stead-train-index.json").read_text(encoding="utf-8"))
    assert array.shape == (2, 3, 6000)
    assert index["members"][0]["valid"] is True
    assert index["members"][1]["valid"] is False
    assert np.max(np.abs(array[0])) == pytest.approx(1)
    assert np.all(array[1] == 0)  # masked, never interpreted as a quiet observation
    with pytest.raises(FileExistsError, match="never overwrite"):
        extract_partition(manifest, hdf, output, partition="train",
                          waveform_sha256=file_sha256(hdf), expected_bytes=hdf.stat().st_size,
                          private_root=tmp_path / "private")


def test_test_partition_cannot_be_opened_before_model_freeze(tmp_path):
    manifest, hdf = _fixture(tmp_path)
    document = json.loads(manifest.read_text(encoding="utf-8"))
    test_member = dict(document["members"]["train"][0], trace_id="heldout-trace", partition="test")
    test_hash = hashlib.sha256(test_member["trace_id"].encode()).hexdigest()
    document["members"]["test"] = [test_member]
    document["report"]["selected"]["test"] = {"ids_sha256": test_hash}
    manifest.write_text(json.dumps(document), encoding="utf-8")
    private = tmp_path / "private"
    private.mkdir()
    checkpoint = private / "model.pt"
    checkpoint.write_bytes(b"frozen test fixture, not a real model")
    receipt = private / "freeze.json"
    freeze = {"schema": "caos.phase-freeze.v1", "frozen_before_test": True,
              "test_selection_sha256": test_hash,
              "waveform_source_sha256": file_sha256(hdf),
              "checkpoint_filename": checkpoint.name,
              "checkpoint_sha256": file_sha256(checkpoint),
              "chosen_epoch": 4, "p_threshold": 0.4, "s_threshold": 0.5}
    with pytest.raises(ValueError, match="frozen checkpoint"):
        extract_partition(manifest, hdf, private / "extract", partition="test",
                          waveform_sha256=file_sha256(hdf), expected_bytes=hdf.stat().st_size,
                          private_root=private)
    freeze["checkpoint_sha256"] = "0" * 64
    receipt.write_text(json.dumps(freeze), encoding="utf-8")
    with pytest.raises(ValueError, match="disagrees"):
        extract_partition(manifest, hdf, private / "extract", partition="test",
                          waveform_sha256=file_sha256(hdf), expected_bytes=hdf.stat().st_size,
                          frozen_checkpoint=receipt, private_root=private)
    freeze["checkpoint_sha256"] = file_sha256(checkpoint)
    receipt.write_text(json.dumps(freeze), encoding="utf-8")
    result = extract_partition(manifest, hdf, private / "extract", partition="test",
                               waveform_sha256=file_sha256(hdf), expected_bytes=hdf.stat().st_size,
                               frozen_checkpoint=receipt, private_root=private)
    assert result["frozen_checkpoint_sha256"] == freeze["checkpoint_sha256"]
