# Protected supplied-profile jobs

Status: planned

This implements the approved M07/M09 service integration, not a new hosting,
account, backup or method policy. Full product acceptance remains separate.

R-P01 WHEN a protected original profile is converted to a dataset, THE service SHALL bind strict supplied metadata and parsed geometry to its exact original hash, owner and project. Gate: tests/api/test_profile_contract.py::test_original_and_physical_bindings.

R-P02 IF supplied units, datum, geometry, rights or original identities disagree with the persisted asset, THEN THE service SHALL reject processing before a native solver runs. Gate: tests/api/test_profile_contract.py::test_reject_metadata_drift_before_native_load.

R-P03 WHEN an eligible profile job executes, THE worker SHALL call the actual existing ERT or Dijkstra inverse on the owned original and export its numerical verdict, native cells, predictions, residuals and provenance without substituted results. Gate: tests/api/test_profile_jobs.py::test_actual_owned_profile_execution.

R-P04 WHILE a profile job is active, THE service SHALL enforce existing ownership, queue, quota, timeout, memory, scratch and cancellation limits. Gate: tests/api/test_profile_jobs.py::test_owned_admission_and_cancellation.

R-P05 IF a scientific inverse is ineligible, unverified or nonconverged, THEN THE service SHALL retain an inspectable diagnostic result and shall not label the numerical verdict passed. Gate: tests/api/test_profile_jobs.py::test_failed_science_retains_diagnostics.

R-P06 WHEN an owned result is opened or exported, THE workbench SHALL inspect the same admitted native arrays and source identities, with physical axes, linked selection and matching exported hashes. Gate: frontend/e2e/protected-profile-results.spec.ts::owned_result_roundtrip.

R-P07 WHERE profile online execution is enabled, THE release SHALL contain actual ML VPS nominal, upper-bound, malformed and cancellation receipts for the unchanged scientific calculation. Gate: tests/ops/test_profile_host_admission.py::test_actual_host_profile_receipts.
