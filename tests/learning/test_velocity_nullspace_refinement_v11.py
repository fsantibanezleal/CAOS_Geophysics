from __future__ import annotations

import numpy as np

import velocity_nullspace_refinement_v11 as study
import velocity_physics_refinement as refinement
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
                  (247001, 247080), (257001, 257080), (267001, 267160),
                  (317001, 317160), (327001, 327160), (337001, 337080),
                  (347001, 347080), (357001, 357160)]
    assert all(not any(start <= seed <= end for start, end in old_ranges) for seed in new_seeds)
    assert {record["family"] for record in cohorts["joint_ood"]["records"]} == set(physics.TEST_FAMILIES)
    assert set(cohorts["joint_ood"]["acquisition"]) == {"C"}


def test_fresh_features_match_the_checkpoint_training_contract():
    ops = physics.operators()
    cohort = study.make_cohort("calibration", ops, fixture=True)
    for index, record in enumerate(cohort["records"]):
        rng = np.random.default_rng(record["seed"])
        velocity = physics.velocity_family(record["family"], rng)
        observed = ops[record["acquisition"]]["oracle"] @ (1.0 / velocity.ravel())
        observed += rng.normal(0.0, physics.NOISE_S, len(observed))
        expected = refinement.input_features(observed, ops[record["acquisition"]]["cell"])
        np.testing.assert_array_equal(cohort["features"][index], expected)


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


def test_retained_v11_receipt_accepts_only_the_verified_historical_code_epoch(monkeypatch):
    historical = study.source_hashes()
    historical["method"] = study.LEGACY_METHOD_MODULE_SHA256
    historical["feature_contract"] = study.LEGACY_FEATURE_MODULE_SHA256
    assert study.source_receipt_matches(historical)
    historical["forward_inverse"] = "0" * 64
    assert not study.source_receipt_matches(historical)

    historical = study.source_hashes()
    historical["method"] = study.LEGACY_METHOD_MODULE_SHA256
    historical["feature_contract"] = study.LEGACY_FEATURE_MODULE_SHA256
    monkeypatch.setattr(study, "project_correction", lambda *args, **kwargs: None)
    assert not study.source_receipt_matches(historical)


def test_legacy_feature_module_hash_requires_exact_input_function(monkeypatch):
    assert study.feature_contract_hash_compatible(study.LEGACY_FEATURE_MODULE_SHA256)
    assert not study.feature_contract_hash_compatible("0" * 64)
    monkeypatch.setattr(refinement, "input_features", lambda observed, matrix: None)
    assert not study.feature_contract_hash_compatible(study.LEGACY_FEATURE_MODULE_SHA256)
