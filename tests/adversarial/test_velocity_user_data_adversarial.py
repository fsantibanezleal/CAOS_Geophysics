"""Adversarial acceptance gates for local first-arrival user data."""

from tests.adversarial._existing_pytest_gate import run_existing


def test_adversarial_vud_01_rejects_forged_requests():
    run_existing(
        "tests/data/test_velocity_user_data.py::test_bounded_physical_contract",
        "tests/data/test_velocity_user_data.py::test_bounded_bytes_and_encoding",
    )


def test_adversarial_vud_02_preserves_supplied_identity():
    run_existing("tests/data/test_velocity_user_data.py::test_identity_and_original_order")


def test_adversarial_vud_03_refutes_unbounded_or_unweighted_solves():
    run_existing(
        "tests/data/test_velocity_user_data.py::test_weighted_inverse_and_parameter_effect",
        "tests/data/test_velocity_user_data.py::test_active_velocity_bounds_match_independent_qp_oracle",
    )


def test_adversarial_vud_04_rejects_checkpoint_substitution():
    run_existing("tests/data/test_velocity_user_data.py::test_actual_checkpoint_inference")


def test_adversarial_vud_05_rejects_forged_generations():
    run_existing(
        "tests/data/test_velocity_user_data.py::test_bundle_roundtrip_and_corruption",
        "tests/data/test_velocity_user_data.py::test_legacy_v1_result_remains_reopenable_as_historical_data",
        "tests/data/test_velocity_user_data.py::test_failed_verification_has_no_success_manifest",
        "tests/data/test_velocity_user_data.py::test_rehashed_result_does_not_bypass_physical_reopen",
    )


def test_adversarial_vud_06_cli_fails_closed():
    run_existing(
        "tests/data/test_velocity_user_data.py::test_cli_actual_input_and_no_overwrite",
        "tests/data/test_velocity_user_data.py::test_cli_invalid_input_has_no_partial_success",
    )
