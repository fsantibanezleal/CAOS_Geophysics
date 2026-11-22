# Adversarial validation: M06 measured MT screening

Each check plants a source, numeric, geometry, or eligibility failure. These controls exercise the production parser and admission logic; ignored C15 data is not required for the synthetic malformed-input cases.

| requirement | adversarial check | gate |
|---|---|---|
| MT-0601 | Supply bytes that do not match the pinned C15 length and SHA-256; acquisition must reject them before creating raw storage. | `tests/adversarial/test_m06_field_mt.py::test_wrong_c15_bytes_never_enter_the_raw_store` |
| MT-0602 | Replace a declared variance with zero in a valid EDI control; parsing must reject it instead of clipping or replacing the value. | `tests/adversarial/test_m06_field_mt.py::test_zero_variance_is_rejected_before_scoring` |
| MT-0603 | Rotate only the declared EY dipole onto EX; the screen must reject the nonorthogonal frame rather than silently rerotate. | `tests/adversarial/test_m06_field_mt.py::test_misaligned_dipole_frame_is_rejected` |
| MT-0604 | Plant a nonzero diagonal impedance at the final supplied period; the full-period tensor gate must fail and retain that period in its score. | `tests/adversarial/test_m06_field_mt.py::test_last_period_violation_is_not_dropped_from_the_1d_gate` |
| MT-0605 | Force a failed tensor admission result; the field runner must emit an ineligible receipt with no model, prediction, held-out score, or truth. | `tests/adversarial/test_m06_field_mt.py::test_failed_tensor_gate_cannot_publish_an_inverse` |
| MT-0606 | Request an unreviewed station identifier; source admission must reject it, so a different field inverse cannot bypass the pinned source and amendment boundary. | `tests/adversarial/test_m06_field_mt.py::test_unreviewed_station_cannot_enter_the_m06_inverse_lane` |
