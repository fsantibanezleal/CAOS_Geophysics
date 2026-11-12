"""Receipt-level checks for the M12 paired bootstrap used in the research lesson."""
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from m12_nullspace_analysis import paired_bootstrap_intervals  # noqa: E402


def test_joint_ood_bootstrap_reproduces_manuscript_intervals() -> None:
    receipt_path = ROOT / "data/derived/v2/models/m12-nullspace-v1_1/receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    result = paired_bootstrap_intervals(receipt, "joint_ood")

    assert result["count"] == 160
    assert result["draws"] == 20_000
    assert result["seed"] == 6_122_026
    assert result["metrics"]["velocity"]["ci95"] == pytest.approx([0.9661, 0.9737], abs=0.00006)
    assert result["metrics"]["oracle_time"]["ci95"] == pytest.approx([0.9950, 0.9983], abs=0.00006)


@pytest.mark.parametrize(
    ("cohort", "kwargs", "message"),
    [
        ("not-a-cohort", {}, "unknown held-out cohort"),
        ("joint_ood", {"draws": 1}, "at least two"),
        ("joint_ood", {"draws": True}, "integer"),
        ("joint_ood", {"seed": -1}, "nonnegative"),
        ("joint_ood", {"seed": True}, "nonnegative"),
    ],
)
def test_bootstrap_rejects_invalid_protocol_parameters(cohort, kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        paired_bootstrap_intervals({"cohorts": {}}, cohort, **kwargs)
