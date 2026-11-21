# EDI M05/M06 adversarial validation

The tests exercise the private API and singleton worker against owned synthetic EDI controls. The field-specific Clear Lake exclusion is an additional ignored-source test and is not replaced with synthetic bytes. Local tests do not qualify actual VPS admission.

| requirement | adversarial check | gate |
|---|---|---|
| EDI-001 | Replace the original after queue admission; require a hash-bound worker snapshot or refusal before solve. | `tests/api/test_online_mt_adversarial.py::test_adversarial_verified_snapshot_survives_source_drift` |
| EDI-002 | Submit an owned EDI and challenge metadata, units, tensor screening and the recorded source identity. | `tests/api/test_online_mt_adversarial.py::test_adversarial_source_identity_and_m05_screen` |
| EDI-003 | Plant malformed blocks and conflicting physical metadata; require no eligible inverse. | `tests/api/test_online_mt_adversarial.py::test_adversarial_malformed_and_clear_lake_exclusion` and `tests/api/test_online_mt_adversarial.py::test_adversarial_declared_physics_mismatch_fails_m05` |
| EDI-004 | Change beta and thickness on fixed observations; compare the fitted response with an independent halfspace oracle and withheld frequencies. | `tests/api/test_online_mt_adversarial.py::test_adversarial_inverse_parameter_effect_and_independent_oracle` |
| EDI-005 | Inspect truth absence, uncertainty conditioning, units and source metadata through solve and re-import. | `tests/api/test_online_mt_adversarial.py::test_adversarial_inverse_parameter_effect_and_independent_oracle` and `tests/api/test_online_mt_adversarial.py::test_adversarial_bundle_roundtrip_and_wrong_principal` |
| EDI-006 | Request an owner's result and export as a different principal; require denial. | `tests/api/test_online_mt_adversarial.py::test_adversarial_bundle_roundtrip_and_wrong_principal` |
| EDI-007 | Plant insufficient memory, scratch, cancellation, timeout and source-integrity conditions; require bounded non-success and no live child. | `tests/api/test_online_mt_adversarial.py::test_adversarial_preflight_cancel_timeout_and_memory` and `tests/api/test_online_mt_adversarial.py::test_adversarial_raw_receipt_tamper_blocks_m05` |
| EDI-008 | Re-hash a tampered export member and alter units; require bundle verification to reject the numerical and provenance mismatch. | `tests/api/test_online_mt_adversarial.py::test_adversarial_bundle_roundtrip_and_wrong_principal` |
| EDI-009 | Leave VPS admission unset and attempt queued work; require both API and worker to refuse by default. | `tests/api/test_online_mt_adversarial.py::test_adversarial_host_gate_defaults_closed` and `tests/api/test_online_mt_adversarial.py::test_adversarial_worker_gate_refuses_queued_mt` |
| EDI-010 | Change the M01 gravity request while preserving its QC and result export invariants. | `tests/api/test_job_execution.py::test_adversarial_real_flag_qc_and_parameter_effect` and `tests/api/test_job_export.py::test_adversarial_bundle_roundtrip_tamper_and_rights` |
