"""M12 physical and evidence gates for local first-arrival velocity validation."""
import os
from pathlib import Path

import numpy as np
import pytest

from velocity_validation import (
    COHORTS, DX, GRID, acquisition, cell_length_matrix, execute, load_checkpoint, make_cohort,
    operators, quadrature_matrix, scientific_verdict, sha256_bytes, verify,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RECEIPT = ROOT / "models" / "experimental" / "m12-velocity-cpu-20260928"


def receipt_directory() -> Path:
    return Path(os.environ.get("M12_VELOCITY_RECEIPT", DEFAULT_RECEIPT))


def test_family_acquisition_partition_and_hashes():
    ops = operators()
    cohorts = {name: make_cohort(name, ops, fixture=True) for name in COHORTS}
    identifiers = [record["id"] for cohort in cohorts.values() for record in cohort["records"]]
    assert len(identifiers) == len(set(identifiers))
    seeds = [record["seed"] for cohort in cohorts.values() for record in cohort["records"]]
    assert len(seeds) == len(set(seeds))
    trained = {record["family"] for record in cohorts["train"]["records"]}
    joint = {record["family"] for record in cohorts["joint_ood"]["records"]}
    assert trained == {"layered", "lens", "dipping"}
    assert joint == {"fault", "salt"}
    assert {record["acquisition"] for record in cohorts["joint_ood"]["records"]} == {"C"}
    training_pairs = {tuple(ray) for layout in ("A", "B") for ray in acquisition(layout)}
    test_pairs = {tuple(ray) for ray in acquisition("C")}
    assert training_pairs.isdisjoint(test_pairs)
    for name, cohort in cohorts.items():
        assert make_cohort(name, ops, fixture=True)["manifest_sha256"] == cohort["manifest_sha256"]
        assert all(record["velocity_sha256"] and record["noisy_picks_sha256"] for record in cohort["records"])


def test_independent_oracle_and_ray_geometry():
    rays = acquisition("A")
    cell = cell_length_matrix(rays)
    oracle = quadrature_matrix(rays)
    distances = np.linalg.norm(rays[:, 2:] - rays[:, :2], axis=1)
    np.testing.assert_allclose(cell.sum(axis=1), distances, atol=1e-9)
    np.testing.assert_allclose(oracle.sum(axis=1), distances, atol=1e-9)
    homogeneous = np.full(GRID * GRID, 1 / 2500)
    np.testing.assert_allclose(cell @ homogeneous, distances / 2500, atol=1e-10)
    np.testing.assert_allclose(oracle @ homogeneous, distances / 2500, atol=1e-10)
    hetero = 1 / (2000 + np.arange(GRID * GRID).reshape(GRID, GRID) * 2)
    assert float(np.max(np.abs(cell @ hetero.ravel() - oracle @ hetero.ravel()))) > 1e-5
    assert DX == 50.0


def test_family_disjoint_checkpoint_and_forward_consistency(tmp_path):
    output = receipt_directory()
    receipt = verify(output)
    assert receipt["status"] != "fixture-only"
    assert receipt["counts"] == {name: item[0] for name, item in COHORTS.items()}
    assert receipt["checkpoint_sha256"] == sha256_bytes((output / receipt["checkpoint"]).read_bytes())
    model = load_checkpoint(output / receipt["checkpoint"], receipt["checkpoint_sha256"])
    assert model.training is False
    altered = tmp_path / "tampered.npz"
    altered.write_bytes((output / receipt["checkpoint"]).read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="SHA-256"):
        load_checkpoint(altered, receipt["checkpoint_sha256"])
    joint = receipt["cohorts"]["joint_ood"]
    assert joint["count"] == 160
    assert len(joint["per_record"]) == 160
    assert all(np.isfinite(item["learned_oracle_rmse_ms"]) for item in joint["per_record"])


def test_receipt_metrics_recompute():
    receipt = verify(receipt_directory())
    threshold = receipt["forward_threshold_ms"]
    validation_errors = [row["learned_oracle_rmse_ms"] for row in receipt["cohorts"]["validation"]["per_record"]]
    assert threshold == pytest.approx(np.quantile(validation_errors, 0.95))
    for cohort in receipt["cohorts"].values():
        assert cohort["forward_threshold_exceedances"] == sum(
            row["forward_threshold_exceeded"] for row in cohort["per_record"])
        assert cohort["learned_velocity_rmse_m_s"] == pytest.approx(np.mean(
            [row["learned_velocity_rmse_m_s"] for row in cohort["per_record"]]))
        assert sum(group["count"] for group in cohort["per_family"].values()) == cohort["count"]
        assert sum(group["count"] for group in cohort["per_acquisition"].values()) == cohort["count"]
    detection = receipt["ood_detection"]
    assert detection["joint_true_positive"] + detection["joint_false_negative"] == receipt["counts"]["joint_ood"]
    assert detection["id_false_positive"] + detection["id_true_negative"] == receipt["counts"]["id_test"]


def test_failure_verdict_is_not_suppressed():
    assert scientific_verdict({"learned_to_classical_velocity_ratio": 1.02,
                               "learned_to_classical_oracle_ratio": 0.6}) == "failed-held-out-comparator"
    assert scientific_verdict({"learned_to_classical_velocity_ratio": 0.6,
                               "learned_to_classical_oracle_ratio": 1.02}) == "failed-held-out-comparator"
    assert scientific_verdict({"learned_to_classical_velocity_ratio": 0.9,
                               "learned_to_classical_oracle_ratio": 0.9}) == "supported-within-bounded-synthetic-protocol"


def test_local_pipeline_scope(tmp_path):
    result = execute(tmp_path, epochs=1, device="cpu", fixture=True)
    assert result["status"] == "fixture-only"
    assert (tmp_path / result["checkpoint"]).is_file()
    assert (tmp_path / "receipt.json").is_file()
    with pytest.raises(ValueError, match="Fixture-only"):
        verify(tmp_path)
    with pytest.raises(FileExistsError, match="already exists"):
        execute(tmp_path, epochs=1, device="cpu", fixture=True)
