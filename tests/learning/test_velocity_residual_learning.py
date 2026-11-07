from __future__ import annotations

import numpy as np
import torch

import velocity_validation as physics
import velocity_residual_learning as study


def test_fresh_protocol_partitions_are_seed_and_family_separated():
    ops = physics.operators()
    cohorts = {name: study.make_cohort(name, ops) for name in study.COUNTS}
    seeds = [record["seed"] for cohort in cohorts.values() for record in cohort["records"]]
    assert len(seeds) == len(set(seeds))
    assert len(cohorts["train"]["records"]) == 1200
    assert {r["family"] for r in cohorts["train"]["records"]} == set(physics.TRAIN_FAMILIES)
    assert {r["family"] for r in cohorts["joint_ood"]["records"]} == set(physics.TEST_FAMILIES)
    assert set(cohorts["train"]["acquisition"]) == {"A", "B"}
    assert set(cohorts["joint_ood"]["acquisition"]) == {"C"}
    assert all(len(cohort["manifest_sha256"]) == 64 for cohort in cohorts.values())


def test_neural_residual_starts_at_physics_solution_and_is_bounded():
    ops = physics.operators()
    cohort = study.make_cohort("validation", ops)
    baseline = physics.classical_predict(cohort, ops, 100.0)
    study.attach_classical_features(cohort, baseline)
    model = study.network().eval()
    estimate, correction = model(torch.from_numpy(cohort["features"][:3]))
    np.testing.assert_allclose(estimate.detach().numpy(), baseline[:3], rtol=0, atol=2e-4)
    assert torch.count_nonzero(correction) == 0
    assert estimate.shape == correction.shape == (3, physics.GRID, physics.GRID)

    with torch.no_grad():
        model.encoder[-1].bias.fill_(8.0)
    estimate, correction = model(torch.from_numpy(cohort["features"][:3]))
    assert torch.all(estimate >= 1400.0) and torch.all(estimate <= 4000.0)
    assert torch.all(torch.abs(correction) <= study.RESIDUAL_SCALE_M_S)


def test_feature_contract_uses_only_baseline_and_measured_geometry():
    ops = physics.operators()
    cohort = study.make_cohort("validation", ops)
    baseline = physics.classical_predict(cohort, ops, 100.0)
    alternative_truth = {**cohort, "velocity": np.full_like(cohort["velocity"], 1400.0)}
    study.attach_classical_features(cohort, baseline)
    study.attach_classical_features(alternative_truth, baseline)
    np.testing.assert_array_equal(cohort["features"], alternative_truth["features"])
    assert cohort["features"].shape == (160, 3, physics.GRID, physics.GRID)
