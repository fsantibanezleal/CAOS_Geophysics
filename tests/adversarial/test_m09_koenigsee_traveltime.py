"""Adversarial source, split, uncertainty, and claim controls for M09."""

from __future__ import annotations

import hashlib
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

import traveltime as pipeline  # noqa: E402
from traveltime import (  # noqa: E402
    Survey,
    TraveltimeError,
    assumed_time_sigma,
    homogeneous_times,
    parse_sgt,
    qc,
    shot_splits,
)


def _synthetic_sgt() -> str:
    return "\n".join([
        "5 # shot/geophone points", "#x y", "0 0", "1 0", "2 0.1", "3 0", "4 0",
        "4 # measurements", "#s g t", "1 2 0.001", "1 3 0.002", "3 1 0.0021", "5 3 0.002",
    ]) + "\n"


def test_original_source_hash_mismatch_is_refused(tmp_path):
    path = tmp_path / "koenigsee.sgt"
    path.write_text(_synthetic_sgt(), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.write_text(_synthetic_sgt().replace("1 2 0.001", "1 2 0.0011"), encoding="utf-8")
    with pytest.raises(TraveltimeError, match="do not match the supplied source SHA-256"):
        pipeline.run(path, source_sha256=digest)
    assert not (tmp_path / "data/raw/traveltime").exists()


def test_malformed_sgt_records_fail_closed(tmp_path):
    path = tmp_path / "survey.sgt"
    valid = _synthetic_sgt()
    for bad, message in (
        (valid.replace("1 0", "nan 0", 1), "non-finite"),
        (valid.replace("1 2 0.001", "1 1 0.001", 1), "self-pick"),
        (valid.replace("1 2 0.001", "1 2 0", 1), "positive"),
        (valid + "undeclared row\n", "trailing payload"),
    ):
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(TraveltimeError, match=message):
            parse_sgt(path)


def test_qc_does_not_invent_pick_precision():
    positions = np.column_stack((np.arange(6, dtype=float), np.zeros(6)))
    pairs = np.asarray([[0, 1], [0, 2], [0, 3], [0, 4]], dtype=int)
    survey = Survey(positions, pairs, np.asarray([0.001, 0.002, 0.003, 0.004]))
    report = qc(survey)
    assert report["pick_count"] == 4
    assert report["reciprocal_status"] == "not_available"
    assert report["source_error_status"] == "not_supplied"


def test_homogeneous_oracle_rejects_invalid_velocity():
    survey = Survey(np.asarray([[0.0, 0.0], [3.0, 4.0]]), np.asarray([[0, 1]]), np.asarray([0.01]))
    assert homogeneous_times(survey, 1000.0).tolist() == pytest.approx([0.005])
    for velocity in (0.0, -1.0, float("nan")):
        with pytest.raises(TraveltimeError, match="positive finite velocity"):
            homogeneous_times(survey, velocity)


def test_assumed_time_sigma_rejects_invalid_picks():
    assert assumed_time_sigma(np.asarray([0.001, 0.01])).tolist() == pytest.approx([0.0001, 0.0003])
    for values in (np.asarray([0.0]), np.asarray([-0.001]), np.asarray([np.inf])):
        with pytest.raises(TraveltimeError, match="finite positive times"):
            assumed_time_sigma(values)


def test_whole_shot_splits_remain_disjoint():
    shots = np.repeat(np.arange(1, 16), 10)
    receivers = np.tile(np.arange(20, 30), 15)
    survey = Survey(np.column_stack((np.arange(30, dtype=float), np.zeros(30))),
                    np.column_stack((shots, receivers)), np.linspace(0.001, 0.010, len(shots)))
    parts = shot_splits(survey)
    for name, split in parts.items():
        train_shots = set(shots[split["training_rows"]])
        held_shots = set(shots[split["held_rows"]])
        assert not train_shots & held_shots
        assert len(held_shots) == 3
        assert len(split["held_rows"]) == 30 and len(split["training_rows"]) == 120
        if name == "central_block":
            assert sorted(held_shots) == [7, 8, 9]


def test_field_verdict_rejects_failed_group():
    passing = {name: {"engine_stopped_before_limit": True, "heldout_improvement": 0.2,
                      "improved_held_shot_count": 2} for name in ("interleaved", "central_block")}
    assert pipeline._field_verdict(passing)[0] == "passed"
    failing = deepcopy(passing)
    failing["central_block"]["heldout_improvement"] = 0.09
    assert pipeline._field_verdict(failing)[0] == "not-converged"


def test_documentation_retains_provider_and_field_nonclaims():
    requirements = (ROOT / "docs/design/features/m09-koenigsee-traveltime/requirements.md").read_text(encoding="utf-8")
    convergence = (ROOT / "docs/design/features/m09-koenigsee-traveltime/convergence.md").read_text(encoding="utf-8")
    theory = (ROOT / "docs/problem-types/traveltime-recovery.md").read_text(encoding="utf-8")
    assert "provider-linked" in requirements and "no licence file or rights statement" in requirements
    assert "within-profile" in convergence and "does not establish" in convergence
    assert "eikonal" in theory and "uncertainty" in theory and "coverage" in theory


def test_immutable_receipt_rejects_byte_drift(tmp_path):
    report = {"schema": "test-m09", "source_sha256": "0" * 64, "code_sha256": "1" * 64,
              "qc": {"pick_count": 1}, "inverse_status": "unverified", "inverse_reason": "oracle failed"}
    target = pipeline.save_local_receipt(report, root=tmp_path, kind="adversarial")
    original = target.read_bytes()
    assert pipeline.save_local_receipt(report, root=tmp_path, kind="adversarial") == target
    target.write_bytes(original + b"tampered")
    with pytest.raises(TraveltimeError, match="checksum drift"):
        pipeline.save_local_receipt(report, root=tmp_path, kind="adversarial")
    assert target.read_bytes() == original + b"tampered"


def test_owner_source_requires_closed_rights_and_frame():
    source = {"id": "owner-line", "citation": "owner supplied for local processing",
              "rights": "owner-permitted", "scope": "owner-provided", "frame": "local-x-y-up",
              "units": {"distance": "m", "time": "s"}}
    assert pipeline._validate_user_source(source) == source
    missing_rights = dict(source)
    del missing_rights["rights"]
    with pytest.raises(TraveltimeError, match="closed M09 provenance schema"):
        pipeline._validate_user_source(missing_rights)
    wrong_scope = dict(source, scope="public-reuse")
    with pytest.raises(TraveltimeError, match="require scope 'owner-provided'"):
        pipeline._validate_user_source(wrong_scope)
