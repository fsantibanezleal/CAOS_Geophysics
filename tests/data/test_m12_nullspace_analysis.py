"""Receipt-level checks for the M12 paired bootstrap used in the research lesson."""
import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from m12_nullspace_analysis import (  # noqa: E402
    PAIRED_CSV_COLUMNS,
    analyze_paired_metrics_csv,
    paired_bootstrap_intervals,
)


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


def test_paired_csv_analysis_keeps_case_pairing_and_source_hash(tmp_path: Path) -> None:
    path = tmp_path / "paired-errors.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PAIRED_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows([
            {
                "case_id": "a",
                "cohort": "external-validation",
                "learned_velocity_rmse_m_s": 8,
                "classical_velocity_rmse_m_s": 10,
                "learned_oracle_rmse_ms": 3,
                "classical_oracle_rmse_ms": 4,
            },
            {
                "case_id": "b",
                "cohort": "external-validation",
                "learned_velocity_rmse_m_s": 12,
                "classical_velocity_rmse_m_s": 10,
                "learned_oracle_rmse_ms": 5,
                "classical_oracle_rmse_ms": 4,
            },
        ])

    result = analyze_paired_metrics_csv(path, draws=500, seed=17)
    cohort = result["cohorts"]["external-validation"]

    assert result["source_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert cohort["count"] == 2
    assert cohort["velocity"]["aggregate_ratio"] == pytest.approx(1.0)
    assert cohort["oracle_time"]["aggregate_ratio"] == pytest.approx(1.0)
    assert cohort["both_metrics_better_fraction"] == pytest.approx(0.5)
    assert cohort["velocity"]["ci95"][0] <= 1 <= cohort["velocity"]["ci95"][1]


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([{"case_id": "a", "cohort": "x"}], "missing required columns"),
        (
            [
                {
                    "case_id": "a", "cohort": "x",
                    "learned_velocity_rmse_m_s": "1",
                    "classical_velocity_rmse_m_s": "2",
                    "learned_oracle_rmse_ms": "1",
                    "classical_oracle_rmse_ms": "2",
                },
                {
                    "case_id": "a", "cohort": "x",
                    "learned_velocity_rmse_m_s": "1",
                    "classical_velocity_rmse_m_s": "2",
                    "learned_oracle_rmse_ms": "1",
                    "classical_oracle_rmse_ms": "2",
                },
            ],
            "repeats case",
        ),
        (
            [{
                "case_id": "a", "cohort": "x",
                "learned_velocity_rmse_m_s": "nan",
                "classical_velocity_rmse_m_s": "2",
                "learned_oracle_rmse_ms": "1",
                "classical_oracle_rmse_ms": "2",
            }],
            "finite",
        ),
        (
            [
                {
                    "case_id": "a", "cohort": "x",
                    "learned_velocity_rmse_m_s": "1",
                    "classical_velocity_rmse_m_s": "2",
                    "learned_oracle_rmse_ms": "1",
                    "classical_oracle_rmse_ms": "2",
                },
            ],
            "at least two paired cases",
        ),
        (
            [
                {
                    "case_id": "a", "cohort": "x",
                    "learned_velocity_rmse_m_s": "1",
                    "classical_velocity_rmse_m_s": "0",
                    "learned_oracle_rmse_ms": "1",
                    "classical_oracle_rmse_ms": "2",
                },
                {
                    "case_id": "b", "cohort": "x",
                    "learned_velocity_rmse_m_s": "1",
                    "classical_velocity_rmse_m_s": "2",
                    "learned_oracle_rmse_ms": "1",
                    "classical_oracle_rmse_ms": "2",
                },
            ],
            "positive classical",
        ),
    ],
)
def test_paired_csv_analysis_rejects_malformed_or_unpaired_inputs(tmp_path: Path, rows, message) -> None:
    path = tmp_path / "invalid.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        fields = list(rows[0])
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match=message):
        analyze_paired_metrics_csv(path, draws=20)
