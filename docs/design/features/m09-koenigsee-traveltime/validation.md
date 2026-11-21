# Adversarial validation: M09 first-arrival travel time

The checks below plant identity, geometry, precision, split, convergence, receipt, and provenance failures. Synthetic fixtures remain distinct from the provider-linked Koenigsee field record.

| requirement | adversarial check | gate |
|---|---|---|
| TT-01 | Change one source byte while retaining the original digest; the field runner must refuse before producing a result receipt. | `tests/adversarial/test_m09_koenigsee_traveltime.py::test_original_source_hash_mismatch_is_refused` |
| TT-02 | Plant a nonfinite coordinate, self-pick, nonpositive time, or trailing payload; the strict parser must reject the malformed record. | `tests/adversarial/test_m09_koenigsee_traveltime.py::test_malformed_sgt_records_fail_closed` |
| TT-03 | Remove reciprocal pairs and instrument errors; QC must retain all picks while reporting that calibrated precision is unavailable. | `tests/adversarial/test_m09_koenigsee_traveltime.py::test_qc_does_not_invent_pick_precision` |
| TT-04 | Plant zero, negative, or nonfinite velocity in the homogeneous oracle; the independent straight-ray calculation must reject it instead of producing nonphysical times. | `tests/adversarial/test_m09_koenigsee_traveltime.py::test_homogeneous_oracle_rejects_invalid_velocity` |
| TT-05 | Plant zero or nonfinite picks; the assumed weighting helper must refuse rather than emit a plausible error floor. | `tests/adversarial/test_m09_koenigsee_traveltime.py::test_assumed_time_sigma_rejects_invalid_picks` |
| TT-06 | Construct ordered shots and assert each frozen partition holds complete shot groups out, disjoint from training, with the central split selected by shot order. | `tests/adversarial/test_m09_koenigsee_traveltime.py::test_whole_shot_splits_remain_disjoint` |
| TT-07 | Force the frozen held-out improvement or stop gate to fail; the result must be `not-converged`. | `tests/adversarial/test_m09_koenigsee_traveltime.py::test_field_verdict_rejects_failed_group` |
| TT-08 | Remove a provenance, rights, leakage, or uncertainty statement; the method-boundary contract test must fail. | `tests/adversarial/test_m09_koenigsee_traveltime.py::test_documentation_retains_provider_and_field_nonclaims` |
| TT-09 | Tamper with the bytes of an existing result receipt; a subsequent save must reject the checksum drift and preserve the tampered bytes for investigation instead of silently overwriting them. | `tests/adversarial/test_m09_koenigsee_traveltime.py::test_immutable_receipt_rejects_byte_drift` |
| TT-10 | Omit rights or declare a coordinate frame inconsistent with the owner source record; the supplied-data workflow must refuse admission. | `tests/adversarial/test_m09_koenigsee_traveltime.py::test_owner_source_requires_closed_rights_and_frame` |
