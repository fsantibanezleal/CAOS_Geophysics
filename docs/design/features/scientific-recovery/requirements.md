# Scientific recovery requirements

Authority: user instruction on 2026-09-24 to implement all pending audit and original-plan gaps. Issues #16 and #10. Existing visual shell remains binding.

R-S01 THE potential-field solver SHALL whiten data and apply a documented spatial prior, with tradeoff selection independent of test truth. Gate: `tests/test_recovery.py::test_sigma_changes_inverse_and_final_state_is_exact`, `test_physical_derivatives_and_positive_precision`, and `scripts/validate_recovery.py`.

R-S02 THE evaluation SHALL report active and withheld errors, zero/initial baseline ratios, support and depth errors, and vector-direction errors where applicable. Gate: `tests/test_recovery.py::test_evaluation_rejects_perfect_data_but_failed_model`, `test_independent_magnetic_prism_and_vector_convention`, and `scripts/validate_recovery.py`.

R-S03 WHEN FWI is run, THE solver SHALL use Hz-defined continuation, preserve model/loss state identity and evaluate nominal recovery against the starting model. Gate: `tests/test_seismic_recovery.py::test_frequency_filter_has_physical_cutoff_and_gradient`, `test_withheld_samples_do_not_influence_inverse_and_terminal_is_saved`, `test_reference_recovery_state_and_forward_replay`, CUDA derivative and `scripts/validate_recovery.py`.

R-S04 THE MT comparisons SHALL share objective normalization and physical bounds and pair each recorded model with its evaluated objective. Gate: `tests/test_mt_recovery.py::test_mt_objective_parity_with_mask_and_heteroscedastic_noise` and `test_saved_states_losses_predictions_and_final_identity`.

R-S05 WHEN an EDI file is supplied, THE pipeline SHALL validate frequencies, complex components, units, uncertainties and orientation, preserve provenance and execute an applicable 1D inversion. Gate: `tests/test_edi.py` and `scripts/validate_recovery.py`.

R-S06 THE PGI method SHALL use an independently fitted multi-property mixture prior and provide both a matched uncoupled baseline and a mismatched-prior control. Gate: `tests/test_recovery.py::test_gmm_fit_independent_repeatable_and_gradient`, `test_cross_gradient_uses_metre_spacing`, and `scripts/validate_recovery.py`.

R-S07 THE uncertainty workflow SHALL execute seeded ensembles and report conditioning, coverage and calibration without asserting posterior validity for bootstrap samples. Gate: `tests/test_recovery.py::test_conditional_ensemble_repeats_and_does_not_claim_posterior`, `tests/test_mt_recovery.py::test_independently_seeded_halfspace_coverage_experiment`, and `scripts/validate_recovery.py`.

R-S08 THE learning comparison SHALL use identical noisy observations and identical column targets for classical and neural methods, and publish held-out errors and detection confusion. Gate: `tests/test_learning_evidence.py`, `tests/test_rebuild.py::test_learning_split_hashes_and_checkpoint_inference`, and `scripts/validate_recovery.py`.

R-S09 WHEN comparing target and reconstruction, THE UI SHALL share physical scales and thresholds and expose final versus replay state explicitly. Gate: `frontend/src/test/recovery.test.ts` and recorded rendered comparisons in both languages/themes.

R-S10 THE release SHALL distinguish recovered, unresolved, failed and expected-negative-control outcomes using explicit criteria, without hiding missing methods or substituting data fit for recovery. Gate: `scripts/validate_recovery.py`, `scripts/check_artifacts.py`, six-route rendered QA and exact external artifact verification on both hosts.
