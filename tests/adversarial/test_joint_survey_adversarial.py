"""Named adversarial entry points for the M11 joint-survey requirements."""

from tests.adversarial._existing_pytest_gate import run_existing


def test_adversarial_js_001_exact_contract():
    run_existing("tests/numerics/test_joint_survey_plan.py::test_exact_contract")


def test_adversarial_js_002_preallocation():
    run_existing("tests/numerics/test_joint_survey_plan.py::test_preallocation_rejection")


def test_adversarial_js_003_geometry():
    run_existing("tests/numerics/test_joint_survey_plan.py::test_geometry_and_order")


def test_adversarial_js_004_partition_and_masks():
    run_existing("tests/numerics/test_joint_survey_plan.py::test_global_blocks_and_masks")


def test_adversarial_js_005_source_binding():
    run_existing("tests/numerics/test_joint_survey_plan.py::test_source_and_snapshot")


def test_adversarial_js_006_forward_oracles():
    run_existing("tests/numerics/test_joint_survey_oracles.py::test_prism_oracles")


def test_adversarial_js_007_coupling_derivatives():
    run_existing("tests/numerics/test_joint_survey_oracles.py::test_cross_gradient_derivatives")


def test_adversarial_js_008_objective():
    run_existing("tests/numerics/test_joint_survey_objective.py::test_objective_chain")


def test_adversarial_js_009_baseline_fits():
    run_existing("tests/numerics/test_joint_survey_optimizer.py::test_all_actual_fits_and_stationary_separate_baselines")


def test_adversarial_js_010_optimizer_controls():
    run_existing(
        "tests/numerics/test_joint_survey_inverse.py::test_actual_physical_bound_paths",
        "tests/numerics/test_joint_survey_inverse.py::test_optimizer_controls_reject_forged_trace",
    )


def test_adversarial_js_011_sealed_selection():
    run_existing("tests/numerics/test_joint_survey_inverse.py::test_sealed_selection_and_changed_development_actual_fits")


def test_adversarial_js_012_case_matrix():
    run_existing("tests/numerics/test_joint_survey_cases.py::test_refined_matrix_original_identity_and_no_production_generator")


def test_adversarial_js_013_resources():
    run_existing("tests/numerics/test_joint_survey_resources.py::test_actual_rss_and_scratch_receipt")


def test_adversarial_js_014_serialized_replay():
    run_existing(
        "tests/numerics/test_joint_survey_optimizer.py::test_calibration_exclusive_export_and_frozen_replay",
        "tests/numerics/test_joint_survey_optimizer.py::test_actual_replay_rejects_forged_pass",
    )


def test_adversarial_js_015_cli_pipeline():
    run_existing("tests/numerics/test_joint_survey_optimizer.py::test_full_cli_evaluate_and_validate_real_files")


def test_adversarial_js_016_result_claims():
    run_existing("tests/numerics/test_joint_survey_evaluation.py::test_actual_marginal_metrics_and_result_roundtrip")
