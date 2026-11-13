from __future__ import annotations

import numpy as np

import velocity_nullspace_refinement as study
import velocity_validation as physics


def test_fresh_cohort_manifests_are_disjoint_from_prior_m12_protocols():
    ops = physics.operators()
    cohorts = {name: study.make_cohort(name, ops, fixture=True)
               for name in study.COUNTS}
    new_seeds = [record["seed"] for cohort in cohorts.values() for record in cohort["records"]]
    assert len(new_seeds) == len(set(new_seeds))
    assert all(len(cohort["manifest_sha256"]) == 64 for cohort in cohorts.values())
    old_ranges = [(17001, 17800), (37001, 37160), (47001, 47080), (57001, 57080), (67001, 67160),
                  (217001, 218200), (227001, 227160), (237001, 237160),
                  (247001, 247080), (257001, 257080), (267001, 267160)]
    assert all(not any(start <= seed <= end for start, end in old_ranges) for seed in new_seeds)
    assert {record["family"] for record in cohorts["joint_ood"]["records"]} == set(physics.TEST_FAMILIES)
    assert set(cohorts["joint_ood"]["acquisition"]) == {"C"}


def test_ray_nullspace_basis_is_orthonormal_and_physics_null():
    matrix = physics.operators()["C"]["cell"]
    basis, evidence = study.nullspace_basis(matrix)
    assert evidence["rank"] == np.linalg.matrix_rank(matrix)
    assert evidence["nullity"] == matrix.shape[1] - evidence["rank"]
    np.testing.assert_allclose(basis.T @ basis, np.eye(basis.shape[1]), rtol=1e-10, atol=1e-10)
    assert np.max(np.abs(matrix @ basis)) < evidence["residual_limit"]


def test_zero_scale_is_exact_classical_identity_and_projection_stays_bounded():
    ops = physics.operators()
    cohort = study.make_cohort("calibration", ops, fixture=True)
    baseline = physics.classical_predict(cohort, ops, 100.0)
    learned = np.clip(baseline * 1.001, 1400.0, 4000.0)
    bases = {name: study.nullspace_basis(ops[name]["cell"]) for name in ops}
    identity, _ = study.project_correction(cohort, baseline, learned, ops, 0.0, bases)
    np.testing.assert_array_equal(identity, baseline)
    refined, evidence = study.project_correction(cohort, baseline, learned, ops, 1.0, bases)
    assert refined.shape == cohort["velocity"].shape
    assert np.isfinite(refined).all()
    assert np.all((refined >= 1400.0) & (refined <= 4000.0))
    assert all(row["max_abs_A_projected_correction"] <= row["residual_limit"]
               for row in evidence.values())
