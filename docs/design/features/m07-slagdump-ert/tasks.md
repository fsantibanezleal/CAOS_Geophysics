# M07 Slagdump ERT tasks

Dependency order; each task names its requirement gate.

1. [x] Read approved SDD/ADRs, source guide and scientific dossier; verify fixed provider bytes/hash and inspect upstream rights and source geometry. ERT-01, ERT-02, ERT-08.
2. [x] Implement strict `.ohm` parser and source-bound QC, with malformed, unit, index, geometry and reciprocal-availability tests. ERT-01 through ERT-03.
3. [x] Pin pyGIMLi and implement analytical flat plus numerical topographic factor/oracle controls. ERT-04.
4. [x] Implement fixed train/holdout 2D inverse, reproducible ignored receipt, forward residual and sensitivity checks. ERT-05 through ERT-07.
5. [x] Expand source guide with units, rights, reproducibility and limitations; run the local scientific tests and record their limits. ERT-08.
6. [x] Exercise an owned user-uploaded Slagdump original through dataset admission, protected worker execution, the real inverse, result validation and bundle export with the pinned ERT runtime; check physical/ownership admission and a real ineligible negative-resistance result. Gates: `tests/api/test_profile_jobs.py::test_actual_owned_profile_execution[ert_ohm-slagdump.ohm-38-222]`, `tests/api/test_profile_contract.py` and `test_actual_owned_failed_science_execution`.
7. [x] Run the focused ERT result view and local profile-contract browser tests. Gate: `frontend/src/test/ert-result-view.test.ts` and `frontend/src/test/profile-local.test.ts`; this is component/contract evidence, not full browser route acceptance.
8. [x] Run the owned-result browser round-trip against real ERT and traveltime owned results. Gate: `frontend/e2e/protected-profile-results.spec.ts::owned_result_roundtrip`; 16/16 shared-shell G6 drawing gates passed across both cases, EN/ES, light/dark and desktop/phone; cell interaction, exact inspection export, ZIP verification and navigation passed. Evidence is held outside Git under `E:\_Datos\CAOS_Geophysics\browser-profile-qa-20261031\evidence-r7`.
9. [ ] Run the actual ML VPS nominal, upper-bound, malformed and cancellation admission receipts. Gate: `tests/ops/test_profile_host_admission.py::test_actual_host_profile_receipts`; local browser/API success does not substitute for the deployed host gate.
9. [ ] Complete the method and product release matrix before commit/promotion or deployment; the VPS remains the sole deployment target and release acceptance is tracked outside these local M07 scientific gates.
