import json
import hashlib
from pathlib import Path

import pytest

from m12_nullspace_analysis import analyze_receipt


ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "data/derived/v2/models/m12-nullspace-v1_1/receipt.json"
RECEIPT_SHA256 = "30df0c2ad495bd850dda602b1c96725be8290dd086119fb3e8e75355fe9dea22"


def test_full_receipt_reconstructs_heldout_cohorts_without_promoting_acceptance():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert hashlib.sha256(RECEIPT.read_bytes()).hexdigest() == RECEIPT_SHA256
    result = analyze_receipt(receipt)

    assert [result["cohorts"][name]["count"] for name in
            ("id_test", "family_only", "acquisition_only", "joint_ood")] == [160, 80, 80, 160]
    joint = result["cohorts"]["joint_ood"]
    assert joint["velocity"]["aggregate_ratio"] == pytest.approx(0.9700567151783237)
    assert joint["oracle_time"]["aggregate_ratio"] == pytest.approx(0.9966524161829474)
    assert result["calibration_selection"]["selected_alpha"] == 1.0
    assert result["scientific_acceptance"] is False


def test_analysis_rejects_receipt_with_stale_aggregate():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    receipt["cohorts"]["joint_ood"]["learned_to_classical_velocity_ratio"] = 0.1
    with pytest.raises(ValueError, match="aggregate does not match"):
        analyze_receipt(receipt)


def test_analysis_rejects_fixture_as_heldout_evidence():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    receipt["fixture"] = True
    with pytest.raises(ValueError, match="full held-out"):
        analyze_receipt(receipt)
