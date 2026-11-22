"""Adversarial gates for the revised learned-tomography experiment."""

from tests.adversarial._existing_pytest_gate import run_existing


def test_adversarial_vpr_01_refutes_dimensional_feature_errors():
    run_existing("tests/learning/test_velocity_physics.py::test_uniform_slowness_feature_oracle")


def test_adversarial_vpr_02_refutes_cohort_overlap():
    run_existing("tests/learning/test_velocity_physics.py::test_fresh_cohorts_and_original_preservation")


def test_adversarial_vpr_03_refutes_unbounded_or_unreopenable_weights():
    run_existing("tests/learning/test_velocity_physics.py::test_network_reference_bounds_and_checkpoint")


def test_adversarial_vpr_04_preserves_negative_comparator():
    run_existing("tests/learning/test_velocity_physics.py::test_scientific_verdict_preserves_failure")


def test_adversarial_vpr_05_rejects_fixture_as_qualification():
    run_existing(
        "tests/learning/test_velocity_physics.py::test_fixture_is_not_full_receipt",
        "tests/learning/test_velocity_physics.py::test_frozen_receipt_and_replay",
    )
