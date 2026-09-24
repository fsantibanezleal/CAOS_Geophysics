# Scientific recovery requirements

Authority: user instruction on 2026-09-24 to implement all pending audit and original-plan gaps. Issues #16 and #10. Existing visual shell remains binding.

R-S01 THE potential-field solver SHALL whiten data and apply a documented spatial prior, with tradeoff selection independent of test truth. Gate: `tests/test_recovery.py::test_noise_changes_tradeoff`, `test_spatial_prior`, and `scripts/validate_recovery.py`.

R-S02 THE evaluation SHALL report active and withheld errors, zero/initial baseline ratios, support and depth errors, and vector-direction errors where applicable. Gate: `tests/test_recovery.py::test_metrics_against_direct_arrays` and `scripts/validate_recovery.py`.

R-S03 WHEN FWI is run, THE solver SHALL use Hz-defined continuation, preserve model/loss state identity and evaluate nominal recovery against the starting model. Gate: `tests/test_recovery.py::test_frequency_filter`, `test_saved_states`, CUDA derivative and `scripts/validate_recovery.py`.

R-S04 THE MT comparisons SHALL share objective normalization and physical bounds and pair each recorded model with its evaluated objective. Gate: `tests/test_recovery.py::test_mt_objective_parity` and `test_saved_states`.

R-S05 WHEN an EDI file is supplied, THE pipeline SHALL validate frequencies, complex components, units, uncertainties and orientation, preserve provenance and execute an applicable 1D inversion. Gate: `tests/test_edi.py` and `scripts/validate_recovery.py`.

R-S06 THE PGI method SHALL use an independently fitted multi-property mixture prior and provide both a matched uncoupled baseline and a mismatched-prior control. Gate: `tests/test_pgi.py` and `scripts/validate_recovery.py`.

R-S07 THE uncertainty workflow SHALL execute seeded ensembles and report conditioning, coverage and calibration without asserting posterior validity for bootstrap samples. Gate: `tests/test_uncertainty.py` and `scripts/validate_recovery.py`.

R-S08 THE learning comparison SHALL use identical noisy observations and identical column targets for classical and neural methods, and publish held-out errors and detection confusion. Gate: `tests/test_learning.py` and `scripts/validate_recovery.py`.

R-S09 WHEN comparing target and reconstruction, THE UI SHALL share physical scales and thresholds and expose final versus replay state explicitly. Gate: `frontend/src/test/recovery.test.ts` and recorded rendered comparisons in both languages/themes.

R-S10 THE release SHALL distinguish recovered, unresolved, failed and expected-negative-control outcomes using explicit criteria, without hiding missing methods or substituting data fit for recovery. Gate: `scripts/validate_recovery.py`, `scripts/check_artifacts.py`, six-route rendered QA and exact external artifact verification on both hosts.
