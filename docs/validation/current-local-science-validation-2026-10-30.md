# Current local science and user-data validation — 2026-10-30

This receipt records focused validation from the direct product checkout at `221d031ca366410ca36066da37d302b9832008b1`. The checkout was dirty; commands and machine-readable counts are in the companion JSON.

## Results

- The documentation map covers 13 methods and 62 bilingual notebooks; the notebook structure gate passes. These checks verify coverage and organization, not correctness of every scientific statement.
- The structural method matrix has gates for all 13 methods. The convergence ledger is structurally valid with 1 pass, 1 failure, and 17 unresolved requirements. This is not release acceptance.
- The complete M02 uploaded-gravity test module passed in the dedicated gravity runtime. The uploaded EDI/MT API test module passed in the API runtime.
- Joint input, output, and result rendering checks passed 46 tests with 5 fixture-gated skips. Separate read-queue and runtime-profile checks passed 3 tests against real outputs from cases 0, 8, 16, and 23.
- GPU validation passed the four retained FWI recovery/replay cases, the Deepwave refined-adjoint check, and the M12 CUDA receipt replay on the NVIDIA GeForce RTX 4070 Laptop GPU. The M12 check replays its retained result; it does not retrain the model.
- M07's pinned Slagdump source was acquired into `${GEOPHYSICS_LOCAL_DATA_ROOT}`, outside the repository, and hash-verified. Its local QC found 38 sensors, 222 readings, 12.75 m relief, no reciprocal pairs or source error column, and one flag-only outlier. All five ERT numerical tests passed. The exact external receipt is named and hashed in the JSON companion.
- The ERT flat-factor oracle agreed to relative error `3.16e-15`; topographic factors differed materially from flat factors (median absolute log ratio `0.114`). The 182/40 interleaved holdout improved log-resistance RMSE from `0.471` to `0.113` (76.0%). The independent central-block split (143/79) improved from `0.432` to `0.1085` (74.9%); the solver stopped after four iterations. Alternate mesh and doubled assumed-error diagnostics are retained.
- The local owner-scoped profile-job test also passed against those exact source bytes. It exercised authenticated upload, immutable dataset admission, the fixed pyGIMLi inversion child, original-byte preservation, and result bundle round-trip. The harness asserts positive child wall time and peak RSS; this is local evidence, not live VPS admission or host-containment acceptance.
- A fresh 24-case synthetic joint solver matrix completed all CLI workflows and independent replays. It contains 524 converged and 100 nonconverged candidates; 22 cases retain at least one nonconverged candidate. Its declared precision acceptance, field eligibility, and public activation all remain false.

## Validation runtime correction

The first broad offline-science rerun used `.venv-pipeline` for M07's direct field fixture and stopped at 18% because that interpreter has no pyGIMLi. The saved field receipt then correctly disagreed with the unavailable-engine rerun. `tests/run_validation.py` now excludes the M07 ERT, M09 travel-time, and native profile-mesh tests from that lane and runs them with `.venv-ert`; the lane and separate-interpreter command are covered by `tests/test_validation_runner.py`.

At the current dirty checkout, `tests/run_validation.py --keyword test_topographic_factor_and_inverse` passed the M07 field inverse in `.venv-ert` (1 selected test, 0 failures, 0 skips; 828.267 seconds). The filtered offline, API, and M08 lanes had no selected tests. Receipt: `${CAOS_TEMP_ROOT}\gph-ert-lane-fix-20261030\20261030T235452089829Z\pygimli-profile.junit.xml`; runner environment record: `${CAOS_TEMP_ROOT}\gph-ert-lane-fix-20261030\20261030T235452089829Z\environment.json`. This focused pass verifies the lane/runtime pairing only; it is not the complete numerical or release gate.

## Acceptance boundary

These results improve local evidence for M02, M06, M07, M10, M11, M12, and the shared browser shell. The M07 result is a predictive check on one provider-linked profile with assumed weights; it is not independent-site validation, calibrated uncertainty, unique geology, redistribution permission, or product acceptance. The results do not accept all methods, close the remaining convergence requirements, qualify the ML VPS, or authorize a replacement deployment. The 24-case matrix is held under the local Temp directory referenced in the JSON; it can be regenerated from its recorded source revisions and is not a canonical app dataset.
