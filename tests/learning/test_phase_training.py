"""Private-array training rules, not a substitute for a real STEAD benchmark."""

import json
from pathlib import Path
import sys

import numpy as np
import pytest
import torch


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import train_stead_phase as trainer  # noqa: E402
from train_stead_phase import (  # noqa: E402
    ExtractedPhaseDataset, _augment_shift, _score_rows,
    audit_exact_waveform_overlap, select_dev_thresholds,
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
    assert int(torch.count_nonzero(shifted[0, 0])) == 1
    assert int(torch.count_nonzero(shifted[0, 1])) == 1
    assert new_s[0] - new_p[0] == 1000
    assert (int(new_p[1]), int(new_s[1])) == (-1, -1)
    assert p.tolist() == [1000, -1] and s.tolist() == [2000, -1]


def test_exact_normalized_waveform_overlap_is_a_pretraining_gate(tmp_path: Path):
    def write_partition(partition: str, values: np.ndarray, root: Path = tmp_path) -> ExtractedPhaseDataset:
        root.mkdir(parents=True, exist_ok=True)
        array_path = root / f"stead-{partition}-normalized.npy"
        np.save(array_path, values)
        (root / f"stead-{partition}-index.json").write_text(json.dumps({
            "schema": "caos.stead-phase-local-array.v1",
            "partition": partition,
            "array_shape": list(values.shape),
            "array_sha256": file_sha256(array_path),
            "members": [
                {"valid": True, "member": {"trace_id": f"{partition}-{index}"}}
                for index in range(len(values))
            ],
        }), encoding="utf-8")
        return ExtractedPhaseDataset(root, partition)

    train_values = np.zeros((2, 3, 6000), dtype=np.float32)
    train_values[:, 0, 500] = 1
    train = write_partition("train", train_values)
    dev_values = np.zeros((1, 3, 6000), dtype=np.float32)
    dev_values[0, 1, 800] = 1
    dev = write_partition("dev", dev_values, tmp_path / "replacement")
    report = audit_exact_waveform_overlap(train, dev)
    assert report["within_partition_duplicates"] == {"train": 1, "dev": 0}
    assert report["cross_partition_duplicates"] == 0
    dev_values[0] = train_values[0]
    dev = write_partition("dev", dev_values)
    with pytest.raises(ValueError, match="crosses train/dev"):
        audit_exact_waveform_overlap(train, dev)


def test_train_only_translation_breaks_narrow_stead_p_clock():
    values = torch.zeros((32, 3, 6000), dtype=torch.float32)
    p = torch.full((32,), 700)
    s = torch.full((32,), 1200)
    shifted, new_p, new_s = _augment_shift(values, p, s, torch.Generator().manual_seed(41027))
    assert int(new_p.max() - new_p.min()) > 3500
    assert torch.all(new_p >= 100)
    assert torch.all(new_s <= 5899)
    assert torch.all(new_s - new_p == 500)
    assert shifted.shape == values.shape


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


@pytest.mark.skipif(not torch.cuda.is_available(), reason="local CUDA training gate")
def test_private_epoch_state_resumes_without_opening_test(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(trainer, "ROOT", tmp_path)
    extraction = tmp_path / "data/raw/phase/extracted"
    output = tmp_path / "data/raw/phase/models"
    extraction.mkdir(parents=True)
    source_hash = "a" * 64
    split_hashes = {"train": "b" * 64, "dev": "c" * 64, "test": "d" * 64}
    for partition in ("train", "dev"):
        values = np.random.default_rng(8 if partition == "train" else 9).normal(
            size=(2, 3, 6000)).astype(np.float32)
        array_path = extraction / f"stead-{partition}-normalized.npy"
        np.save(array_path, values)
        (extraction / f"stead-{partition}-index.json").write_text(json.dumps({
            "schema": "caos.stead-phase-local-array.v1", "partition": partition,
            "array_shape": [2, 3, 6000], "array_sha256": file_sha256(array_path),
            "selection_sha256": split_hashes[partition],
            "waveform_source_sha256": source_hash,
            "members": [
                {"valid": True, "member": {"trace_id": f"{partition}-quake",
                                            "p_index": 1000, "s_index": 2000}},
                {"valid": True, "member": {"trace_id": f"{partition}-noise",
                                            "p_index": None, "s_index": None}},
            ],
        }), encoding="utf-8")
    manifest = tmp_path / "data/raw/phase/selection.json"
    manifest.write_text(json.dumps({
        "schema": "caos.stead-phase-members.v1",
        "report": {"selected": {
            partition: {"ids_sha256": digest} for partition, digest in split_hashes.items()
        }},
    }), encoding="utf-8")
    original_save = trainer._save_resume_state
    state_calls = 0

    def stop_after_first(path, state):
        nonlocal state_calls
        original_save(path, state)
        state_calls += 1
        if state_calls == 1:
            raise RuntimeError("simulated interruption after durable epoch")

    prior = torch.are_deterministic_algorithms_enabled()
    monkeypatch.setattr(trainer, "_save_resume_state", stop_after_first)
    try:
        with pytest.raises(RuntimeError, match="simulated interruption"):
            trainer.train(extraction, manifest, output, epochs=2, batch_size=2)
        assert (output / "phase-resume-state.pt").is_file()
        assert not (output / "phase-model.pt").exists()
        monkeypatch.setattr(trainer, "_save_resume_state", original_save)
        result = trainer.train(extraction, manifest, output, epochs=2, batch_size=2, resume=True)
        receipt = json.loads((output / "phase-freeze.json").read_text(encoding="utf-8"))
        assert result["checkpoint_sha256"] == file_sha256(output / "phase-model.pt")
        assert receipt["frozen_before_test"] is True
        assert receipt["test_waveforms_opened"] is False
        assert len(receipt["history"]) == 2
        direct_output = tmp_path / "data/raw/phase/models-direct"
        direct = trainer.train(extraction, manifest, direct_output, epochs=2, batch_size=2)
        resumed_weights = torch.load(output / "phase-model.pt", map_location="cpu",
                                     weights_only=True)["model"]
        direct_weights = torch.load(direct_output / "phase-model.pt", map_location="cpu",
                                    weights_only=True)["model"]
        assert result["chosen_epoch"] == direct["chosen_epoch"]
        assert result["p_threshold"] == direct["p_threshold"]
        assert result["s_threshold"] == direct["s_threshold"]
        assert all(torch.equal(resumed_weights[key], direct_weights[key])
                   for key in resumed_weights)
        with pytest.raises(FileExistsError, match="never overwrite"):
            trainer.train(extraction, manifest, output, epochs=2, batch_size=2, resume=True)
    finally:
        torch.use_deterministic_algorithms(prior)
