"""Named adversarial gates for the bounded pure physical-accounting protocol."""

from tests.adversarial._existing_pytest_gate import run_existing


def test_adversarial_pap_001_authority_boundary():
    run_existing("tests/worker_accounting/test_protocol.py::test_pure_boundary_and_no_authority")


def test_adversarial_pap_002_preallocation_bounds():
    run_existing(
        "tests/worker_accounting/test_protocol.py::test_bounds_precede_decode_and_conversion_serialization",
        "tests/worker_accounting/test_protocol.py::test_bounds_precede_decode_and_conversion_no_subclass_hooks",
    )


def test_adversarial_pap_003_strict_records():
    run_existing(
        "tests/worker_accounting/test_protocol.py::test_strict_shapes_and_canonical_records",
        "tests/worker_accounting/test_protocol.py::test_strict_shapes_and_canonical_records_typed_identity",
    )


def test_adversarial_pap_004_counter_arithmetic():
    run_existing(
        "tests/worker_accounting/test_protocol.py::test_golden_units_and_native_maxima",
        "tests/worker_accounting/test_protocol.py::test_golden_units_and_native_maxima_linux",
    )


def test_adversarial_pap_005_invalid_counters():
    run_existing(
        "tests/worker_accounting/test_protocol.py::test_regression_overflow_underflow_and_bool",
        "tests/worker_accounting/test_protocol.py::test_regression_overflow_underflow_and_bool_active",
    )


def test_adversarial_pap_006_frozen_limits():
    run_existing("tests/worker_accounting/test_protocol.py::test_exact_lane_limits_and_no_override")


def test_adversarial_pap_007_transition_replay():
    run_existing(
        "tests/worker_accounting/test_protocol.py::test_transition_identity_and_replay_entire_phase_table",
        "tests/worker_accounting/test_protocol.py::test_transition_identity_and_replay_sequence_exhaustion",
    )


def test_adversarial_pap_008_trace_and_final():
    run_existing(
        "tests/worker_accounting/test_protocol.py::test_bounded_trace_and_final_consistency_exact_trace_caps",
        "tests/worker_accounting/test_protocol.py::test_bounded_trace_and_final_consistency_last_deadline",
    )


def test_adversarial_pap_009_unavailable_is_sticky():
    run_existing(
        "tests/worker_accounting/test_protocol.py::test_unavailable_is_not_final_zero_held_diagnostic",
        "tests/worker_accounting/test_protocol.py::test_unavailable_is_not_final_zero_known_timing_mutation",
    )


def test_adversarial_pap_010_receipt_and_budget():
    run_existing(
        "tests/worker_accounting/test_protocol.py::test_receipt_release_and_eligibility_b_plus_one",
        "tests/worker_accounting/test_protocol.py::test_receipt_release_and_eligibility_receipt_mutation",
    )


def test_adversarial_pap_011_no_forged_authority():
    run_existing(
        "tests/worker_accounting/test_protocol.py::test_safe_errors_and_forged_authority_constructor_variants",
        "tests/worker_accounting/test_protocol.py::test_safe_errors_and_forged_authority_no_equality_hook",
    )


def test_adversarial_pap_012_public_surface():
    run_existing("tests/worker_accounting/test_protocol.py::test_public_surface_and_exports")
