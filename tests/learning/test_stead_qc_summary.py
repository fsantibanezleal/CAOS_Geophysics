"""Aggregate STEAD extraction receipts remain separate from model claims."""

import json
from pathlib import Path
import sys

import numpy as np
import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from summarize_stead_phase_qc import summarize  # noqa: E402
from stead_phase import file_sha256  # noqa: E402


def test_aggregate_train_dev_qc_retains_failures_and_checks_bytes(tmp_path: Path):
    source = "a" * 64
    for partition in ("train", "dev"):
        values = np.zeros((2, 3, 6000), dtype=np.float32)
        path = tmp_path / f"stead-{partition}-normalized.npy"
        np.save(path, values)
        (tmp_path / f"stead-{partition}-index.json").write_text(json.dumps({
            "schema": "caos.stead-phase-local-array.v1",
            "partition": partition,
            "array_shape": [2, 3, 6000],
            "array_sha256": file_sha256(path),
            "selection_sha256": ("b" if partition == "train" else "c") * 64,
            "waveform_source_sha256": source,
            "members": [
                {"valid": True, "member": {"trace_id": "private-id", "category": "earthquake_local"}},
                {"valid": False, "reason": "SteadFormatError: flat component",
                 "member": {"trace_id": "other-private-id", "category": "noise"}},
            ],
        }), encoding="utf-8")
    report = summarize(tmp_path)
    assert report["test_waveforms_opened"] is False
    assert report["partitions"]["train"]["selected"] == 2
    assert report["partitions"]["dev"]["quarantined"] == 1
    assert "private-id" not in json.dumps(report)
    array_path = tmp_path / "stead-dev-normalized.npy"
    with array_path.open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(ValueError, match="differs from its pinned index"):
        summarize(tmp_path)
