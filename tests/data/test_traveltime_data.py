"""Pinned Koenigsee identity, strict pick parsing and rights-contained QC."""

import hashlib
from pathlib import Path
import subprocess

import numpy as np
import pytest

from sources import acquire_source, load_ledger
from traveltime import Survey, TraveltimeError, parse_sgt, qc

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/downloads/pygimli/koenigsee.sgt"


def _synthetic_sgt() -> str:
    return "\n".join([
        "5 # shot/geophone points", "#x y",
        "0 0", "1 0", "2 0.1", "3 0", "4 0",
        "4 # measurements", "#s g t",
        "1 2 0.001", "1 3 0.002", "3 1 0.0021", "5 3 0.002",
    ]) + "\n"


def test_pinned_source_and_ignored_receipt():
    record = load_ledger()["pygimli-koenigsee"]
    assert record["acquisition"] == "manual"
    assert record["rights_decision"] == "provider-link-only"
    assert record["expected_bytes"] == 9844
    assert record["sha256"] == "cf8f6c8c79fd0f60984eefc61aff67b567b0c875f8f5c663fe904cdbf0d0414a"
    assert "3bab9c6b96a606e2ca12cbdafc8c7da4f1b73c67" in record["object_url"]
    tracked = subprocess.run(["git", "ls-files", "data/downloads", "data/raw"], cwd=ROOT,
                             capture_output=True, text=True, check=True)
    assert tracked.stdout.strip() == ""
    if RAW.exists():
        assert RAW.stat().st_size == record["expected_bytes"]
        assert hashlib.sha256(RAW.read_bytes()).hexdigest() == record["sha256"]
        _, target, receipt = acquire_source("pygimli-koenigsee")
        assert target == RAW and receipt["validation_status"] == "hash-verified"


def test_strict_sgt_contract(tmp_path):
    path = tmp_path / "survey.sgt"
    valid = _synthetic_sgt()
    path.write_text(valid, encoding="utf-8")
    survey = parse_sgt(path)
    assert survey.sensor_xy_m.shape == (5, 2)
    assert survey.shot_geophone.tolist() == [[0, 1], [0, 2], [2, 0], [4, 2]]
    assert survey.time_s.tolist() == [0.001, 0.002, 0.0021, 0.002]
    invalid = [
        (valid.replace("5 # shot/geophone points", "5# sensors"), "sensor count"),
        (valid.replace("#x y", "#x z"), "sensor columns"),
        (valid.replace("4 # measurements", "4# picks"), "pick count"),
        (valid.replace("#s g t", "#s g milliseconds"), "pick columns"),
        (valid.replace("1 0", "nan 0", 1), "non-finite"),
        (valid.replace("1 0", "0 0", 1), "strictly increasing"),
        (valid.replace("1 2 0.001", "1 6 0.001", 1), "outside 1..5"),
        (valid.replace("1 2 0.001", "1 1 0.001", 1), "self-pick"),
        (valid.replace("1 3 0.002", "1 2 0.002", 1), "duplicate"),
        (valid.replace("1 2 0.001", "1 2 0", 1), "positive"),
        (valid.replace("1 2 0.001", "1 2 inf", 1), "non-finite"),
        (valid.replace("4 # measurements", "5 # measurements"), "truncated"),
        (valid + "unexpected payload\n", "trailing payload"),
    ]
    for text, message in invalid:
        path.write_text(text, encoding="utf-8")
        with pytest.raises(TraveltimeError, match=message):
            parse_sgt(path)


def test_qc_preserves_picks_and_absent_errors(tmp_path):
    path = tmp_path / "survey.sgt"
    path.write_text(_synthetic_sgt(), encoding="utf-8")
    survey = parse_sgt(path)
    result = qc(survey)
    assert result["pick_count"] == len(survey.time_s) == 4
    assert result["reciprocal_pairs"] == [[1, 2]]
    assert result["source_error_status"] == "not_supplied"
    assert result["duplicate_pairs"] == 0
    assert result["topographic_relief_m"] > 0
    assert "not file-declared" in result["unit_basis"]
    flagged = qc(Survey(np.column_stack((np.arange(5, dtype=float), np.zeros(5))),
                        np.array([[0, 1], [0, 2], [0, 3], [4, 0]]),
                        np.array([0.001, 0.002, 0.001, 0.00001])))
    assert flagged["pick_count"] == 4
    assert flagged["time_reversal_flag_rows"] == [2]
    assert flagged["gross_speed_flag_rows"] == [3]
    if RAW.exists():
        field = qc(parse_sgt(RAW))
        assert field["sensor_count"] == 63 and field["pick_count"] == 714
        assert field["shot_count"] == 15 and field["receiver_count"] == 48
        assert field["reciprocal_status"] == "not_available"
        assert field["source_error_status"] == "not_supplied"
        assert field["topographic_relief_m"] > 0


def test_m09_documented_boundaries():
    guide = (ROOT / "docs/guides/05_sources.md").read_text(encoding="utf-8")
    design = (ROOT / "docs/design/features/m09-koenigsee-traveltime/design.md").read_text(encoding="utf-8")
    theory = (ROOT / "docs/problem-types/traveltime-recovery.md").read_text(encoding="utf-8")
    for term in ("Koenigsee", "provider-link-only", "held-out", "reciprocal", "pyGIMLi"):
        assert term in guide and term in design and term in theory
    for term in ("eikonal", "homogeneous", "uncertainty", "coverage"):
        assert term in theory
