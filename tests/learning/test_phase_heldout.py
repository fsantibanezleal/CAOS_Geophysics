"""Evaluation semantics can be tested without reading the frozen test set."""

import json
import hashlib
from pathlib import Path
import sys

import numpy as np
import pytest
import torch


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import evaluate_stead_phase as heldout  # noqa: E402
from evaluate_stead_phase import _summarize, _variant_batch  # noqa: E402
from phase_model import PhaseUNet  # noqa: E402
from stead_phase import METADATA_SHA256, SteadMember, file_sha256  # noqa: E402


def test_matched_scoring_counts_noise_and_timing_outside_tolerance():
    labels = {
        "good": {"P": 10.0, "S": 20.0},
        "wrong": {"P": 11.0, "S": 21.0},
        "noise": {"P": None, "S": None},
        "qc-failed": {"P": 12.0, "S": 22.0},
    }
    learned = {
        "good": {"P": 10.1, "S": 20.1},
        "wrong": {"P": 21.1, "S": None},
        "noise": {"P": 13.0, "S": None},
        "qc-failed": {"P": None, "S": None},
    }
    result = _summarize(labels, {"M08": learned, "M13": learned}, noise_valid=1)
    p = result["M13"]["P"]
    assert p["reference_count"] == 3
    assert p["correct_within_0p5s"] == 1
    assert p["outside_tolerance"] == 1
    assert p["missed"] == 1
    assert p["false_without_reference"] == 1
    assert p["near_opposite_phase_reference"] == 1
    assert p["precision_at_0p5s"] == pytest.approx(1 / 3)
    assert p["recall_at_0p5s"] == pytest.approx(1 / 3)
    assert p["valid_noise_false_pick_rate"] == 1
    assert result["M13"] == result["M08"]
    with pytest.raises(ValueError, match="identical"):
        _summarize(labels, {"M08": learned, "M13": {"good": learned["good"]}}, noise_valid=1)


def test_stress_inputs_are_trace_bound_and_do_not_mutate_nominal_waveforms():
    values = np.ones((2, 3, 6000), dtype=np.float32)
    dropped = _variant_batch(values, ["a", "b"], "drop_E")
    assert np.all(dropped[:, 0] == 0)
    assert np.all(dropped[:, 1:] == 1)
    noisy = _variant_batch(values, ["a", "b"], "noise_0p1")
    assert np.array_equal(noisy, _variant_batch(values, ["a", "b"], "noise_0p1"))
    assert not np.array_equal(noisy[0], noisy[1])
    assert np.all(values == 1)
    with pytest.raises(ValueError, match="variant"):
        _variant_batch(values, ["a", "b"], "unsupported")


def test_test_waveforms_cannot_open_before_model_freeze(tmp_path: Path, monkeypatch):
    member = SteadMember(
        "heldout", "bucket1$0,:3,:6000", "event", "NW.STA", "test",
        "earthquake_local", "BH", 800, 1800,
    )
    monkeypatch.setattr(heldout, "_members", lambda *_args: ([member], "selection-hash"))
    index = {
        "schema": "caos.stead-phase-local-array.v1", "partition": "test",
        "selection_sha256": "selection-hash", "array_shape": [1, 3, 6000],
        "waveform_source_sha256": "a" * 64,
        "members": [{"member": member.__dict__, "valid": True}],
    }
    (tmp_path / "stead-test-index.json").write_text(json.dumps(index), encoding="utf-8")

    def refuse_unfrozen(*_args, **_kwargs):
        raise ValueError("freeze receipt missing")

    def no_test_array_open(*_args, **_kwargs):
        raise AssertionError("held-out waveform bytes were opened before model freeze")

    monkeypatch.setattr(heldout, "_frozen_model_receipt", refuse_unfrozen)
    monkeypatch.setattr(heldout.np, "load", no_test_array_open)
    with pytest.raises(ValueError, match="freeze receipt missing"):
        heldout._load_locked_test(tmp_path, tmp_path / "selection.json",
                                  tmp_path / "missing-freeze.json", tmp_path)


def test_locked_evaluator_matches_ids_and_writes_aggregate_once(tmp_path: Path, monkeypatch):
    """A two-row contract fixture does not establish any scientific accuracy."""
    monkeypatch.setattr(heldout, "ROOT", tmp_path)
    private = tmp_path / "data/raw/phase"
    extraction = private / "extracted"
    models = private / "models"
    public = tmp_path / "data/derived/phase"
    for directory in (extraction, models, public):
        directory.mkdir(parents=True)
    members = [
        SteadMember("noise", "bucket1$0,:3,:6000", None, "NW.NOISE",
                    "test", "noise", "BH", None, None),
        SteadMember("quake", "bucket1$1,:3,:6000", "event", "NW.QUAKE",
                    "test", "earthquake_local", "BH", 1000, 2000),
    ]
    ids_hash = hashlib.sha256("noise\nquake".encode()).hexdigest()
    selection = private / "selection.json"
    selection.write_text(json.dumps({
        "schema": "caos.stead-phase-members.v1",
        "report": {"metadata_sha256": METADATA_SHA256,
                   "selected": {"test": {"ids_sha256": ids_hash}}},
        "members": {"test": [member.__dict__ for member in members]},
    }), encoding="utf-8")
    values = np.zeros((2, 3, 6000), dtype=np.float32)
    values[1, 2, 1000:1050] = 1
    values[1, 0, 2000:2050] = 1
    array_path = extraction / "stead-test-normalized.npy"
    np.save(array_path, values)
    source_hash = "a" * 64
    checkpoint_path = models / "phase-model.pt"
    torch.save({
        "schema": "caos.phase-picking-checkpoint.v1",
        "model": PhaseUNet().state_dict(),
        "source_sha256": source_hash,
        "chosen_epoch": 1,
        "input": {"shape": [3, 6000]},
    }, checkpoint_path)
    checkpoint_hash = file_sha256(checkpoint_path)
    receipt_path = models / "phase-freeze.json"
    receipt_path.write_text(json.dumps({
        "schema": "caos.phase-freeze.v1", "frozen_before_test": True,
        "checkpoint_filename": checkpoint_path.name,
        "checkpoint_sha256": checkpoint_hash,
        "waveform_source_sha256": source_hash,
        "test_selection_sha256": ids_hash,
        "chosen_epoch": 1, "p_threshold": 0.5, "s_threshold": 0.5,
    }), encoding="utf-8")
    (extraction / "stead-test-index.json").write_text(json.dumps({
        "schema": "caos.stead-phase-local-array.v1", "partition": "test",
        "selection_sha256": ids_hash, "array_shape": [2, 3, 6000],
        "array_sha256": file_sha256(array_path),
        "waveform_source_sha256": source_hash,
        "frozen_checkpoint_sha256": checkpoint_hash,
        "members": [{"member": member.__dict__, "valid": True} for member in members],
    }), encoding="utf-8")
    report_path = public / "fixture-report.json"
    private_predictions = models / "fixture-predictions.json"
    outcome = heldout.evaluate(
        extraction, selection, receipt_path, report_path, private_predictions,
        batch_size=2, device_name="cpu", private_root=tmp_path / "data/raw",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert outcome["selected"] == report["selected"] == 2
    assert report["valid"] == 2 and report["noise_valid"] == 1
    assert report["private_predictions_sha256"] == file_sha256(private_predictions)
    assert set(report["metrics"]) == set(heldout.VARIANTS)
    assert report["metrics"]["nominal"]["M08"]["P"]["reference_count"] == 1
    assert report["metrics"]["nominal"]["M13"]["P"]["reference_count"] == 1
    with pytest.raises(FileExistsError, match="never overwrite"):
        heldout.evaluate(
            extraction, selection, receipt_path, report_path, private_predictions,
            batch_size=2, device_name="cpu", private_root=tmp_path / "data/raw",
        )
