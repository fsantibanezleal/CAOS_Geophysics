"""Adversarial acceptance entry point for the local waveform boundary.

The original focused tests construct malformed bytes, incomplete metadata,
unsupported response chains and false-claim cases. Keep their assertions in
the owning test modules and run them as one named adversarial feature gate.
"""

from tests.adversarial._existing_pytest_gate import run_existing


def test_adversarial_waveform_user_data_contract():
    run_existing(
        "tests/data/test_waveform_input.py::test_exact_bytes_hash_domains_and_immutability",
        "tests/data/test_waveform_input.py::test_record_preflight_before_native_decode",
        "tests/data/test_waveform_input.py::test_stationxml_preflight_before_inventory",
        "tests/data/test_waveform_input.py::test_time_corrections_rates_gaps_and_overlaps",
        "tests/data/test_waveform_input.py::test_nested_identity_full_window_epoch_and_qc_only",
        "tests/numerics/test_waveform_picks.py::test_stage_chain_units_gain_orientation_and_polarity",
        "tests/data/test_waveform_input.py::test_clipping_flags_unknown_rails_and_missing_components",
        "tests/numerics/test_waveform_picks.py::test_response_epoch_and_classical_picks",
        "tests/numerics/test_waveform_picks.py::test_independent_response_oracles_and_stabilization",
        "tests/numerics/test_waveform_picks.py::test_sos_filter_oracle_edges_and_acausality",
        "tests/numerics/test_waveform_picks.py::test_welch_dft_parseval_and_units",
        "tests/numerics/test_waveform_picks.py::test_direct_stalta_onsets_and_no_phase_fabrication",
        "tests/numerics/test_waveform_picks.py::test_actual_parameter_effects_and_reference_noninterference",
        "tests/numerics/test_waveform_picks.py::test_sealed_reference_conversion_matching_and_residuals",
        "tests/data/test_waveform_input.py::test_native_request_bounds_types_and_safe_errors",
        "tests/data/test_waveform_input.py::test_bounded_artifact_arrays_and_independent_reopen",
        "tests/data/test_waveform_resources.py::test_control_budget_preflight_no_overwrite_and_profile_bounds",
        "tests/data/test_waveform_resources.py::test_measured_capacity_uses_bytes_no_percentage_or_production_floor",
        "tests/data/test_waveform_input.py::test_frozen_sources_and_local_only_nonclaims",
        "tests/data/test_waveform_input.py::test_missing_engine_is_fixed_and_never_decodes",
    )
