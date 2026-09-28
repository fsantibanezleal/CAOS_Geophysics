"""Private-array training rules, not a substitute for a real STEAD benchmark."""

import json
from pathlib import Path
import sys

import numpy as np
import pytest
import torch


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from train_stead_phase import (  # noqa: E402
    ExtractedPhaseDataset, _augment_shift, _score_rows, select_dev_thresholds,
)
from stead_phase import file_sha256  # noqa: E402


def test_extracted_dataset_masks_qc_rejections_and_checks_bytes(tmp_path: Path):
    values = np.zeros((3, 3, 6000), dtype=np.float32)
    values[0, 0, 800] = 1
    values[2, 0, 1200] = 1
    path = tmp_path / "stead-train-normalized.npy"
    np.save(path, values)
    index_path = tmp_path / "stead-train-index.json"
    index = {
        "schema": "caos.stead-phase-local-array.v1", "partition": "train",
        "array_shape": [3, 3, 6000], "array_sha256": file_sha256(path),
        "members": [
            {"valid": True, "member": {"trace_id": "q1", "p_index": 800, "s_index": 1600}},
            {"valid": False, "member": {"trace_id": "bad", "p_index": 900, "s_index": 1700}},
            {"valid": True, "member": {"trace_id": "n1", "p_index": None, "s_index": None}},
        ],
    }
    index_path.write_text(json.dumps(index), encoding="utf-8")
    dataset = ExtractedPhaseDataset(tmp_path, "train")
    assert len(dataset) == 2
    assert dataset[0][1:] == (800, 1600, "q1")
    assert dataset[1][1:] == (-1, -1, "n1")
    with pytest.raises(ValueError, match="train and dev only"):
        ExtractedPhaseDataset(tmp_path, "test")
    index["array_sha256"] = "0" * 64
    index_path.write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(ValueError, match="QC hash"):
        ExtractedPhaseDataset(tmp_path, "train")


def test_training_shift_preserves_arrival_alignment_without_shifting_noise_labels():
    values = torch.zeros((2, 3, 6000), dtype=torch.float32)
    values[0, 0, 1000] = 1
    values[0, 1, 2000] = 1
    p = torch.tensor([1000, -1])
    s = torch.tensor([2000, -1])
    shifted, new_p, new_s = _augment_shift(values, p, s, torch.Generator().manual_seed(12))
    assert int(shifted[0, 0].argmax()) == int(new_p[0])
    assert int(shifted[0, 1].argmax()) == int(new_s[0])
    assert new_s[0] - new_p[0] == 1000
    assert (int(new_p[1]), int(new_s[1])) == (-1, -1)
    assert p.tolist() == [1000, -1] and s.tolist() == [2000, -1]


def test_dev_threshold_avoids_false_noise_picks_and_counts_timing_error():
    rows = [
        {"p": 1000, "s": 2000, "p_max": 0.9, "p_argmax": 1010,
         "s_max": 0.9, "s_argmax": 2004},
        {"p": -1, "s": -1, "p_max": 0.8, "p_argmax": 1300,
         "s_max": 0.8, "s_argmax": 2100},
    ]
    selection = select_dev_thresholds(rows)
    assert selection["p_threshold"] == pytest.approx(0.9)
    assert selection["s_threshold"] == pytest.approx(0.9)
    assert selection["macro_f1"] == 1.0
    assert _score_rows(rows, 0.5, 0.5)["counts"]["P"]["fp"] == 1
    wrong = [{**rows[0], "p_argmax": 1300}]
    assert _score_rows(wrong, 0.5, 0.5)["counts"]["P"] == {
        "tp": 0, "fp": 1, "fn": 1,
    }
