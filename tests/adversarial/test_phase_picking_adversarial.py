"""Named adversarial gates for the real STEAD phase-picking pipeline."""

from tests.adversarial._existing_pytest_gate import run_existing


def test_adversarial_ph_001_archive():
    run_existing("tests/learning/test_phase_source.py::test_archive_receipt_and_rejections")


def test_adversarial_ph_002_trace_contract():
    run_existing("tests/learning/test_phase_source.py::test_trace_contract_rejects_ambiguity")


def test_adversarial_ph_003_split():
    run_existing("tests/learning/test_phase_split.py::test_disjoint_station_event_and_reproducible_hash")


def test_adversarial_ph_004_matched_evaluation():
    run_existing("tests/learning/test_phase_evaluation.py::test_matched_inputs_and_failed_picks")


def test_adversarial_ph_006_rights_boundary():
    run_existing("tests/learning/test_phase_browser_assets.py::test_finalized_parity_status_preserves_export_identity_and_nonacceptance")


def test_adversarial_ph_007_bucket_reader():
    run_existing("tests/learning/test_stead_waveforms.py::test_bucket_reader_and_rejections")


def test_adversarial_ph_008_joint_selection():
    run_existing("tests/learning/test_stead_waveforms.py::test_joint_metadata_selection")


def test_adversarial_ph_009_model_contract():
    run_existing(
        "tests/learning/test_phase_model.py::test_phase_unet_tensor_contract_and_gradient",
        "tests/learning/test_phase_model.py::test_arrival_targets_and_noise_are_declared",
    )


def test_adversarial_ph_010_extraction_freeze():
    run_existing(
        "tests/learning/test_stead_extraction.py::test_extraction_retains_qc_failures_without_replacement",
        "tests/learning/test_stead_extraction.py::test_test_partition_cannot_be_opened_before_model_freeze",
    )


def test_adversarial_ph_011_exact_overlap():
    run_existing("tests/learning/test_phase_training.py::test_exact_normalized_waveform_overlap_is_a_pretraining_gate")


def test_adversarial_ph_012_amp_overflow():
    run_existing("tests/learning/test_phase_training.py::test_amp_overflow_backs_off_without_applying_a_corrupt_update")


def test_adversarial_ph_013_clock_and_noise_screen():
    run_existing(
        "tests/learning/test_phase_training.py::test_train_only_translation_breaks_narrow_stead_p_clock",
        "tests/learning/test_phase_training.py::test_dev_threshold_avoids_false_noise_picks_and_counts_timing_error",
    )


def test_adversarial_ph_014_display_population():
    run_existing("tests/learning/test_phase_browser_assets.py::test_predeclared_display_population_preserves_qc_failure")
