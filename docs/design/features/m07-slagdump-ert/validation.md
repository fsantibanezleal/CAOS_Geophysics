# Adversarial validation: M07 Slagdump ERT

These checks plant bad source identity, malformed measurement rows, unsupported uncertainty, or a failed numerical oracle. They use small authored controls except where a historical field run is the separately documented evidence.

| requirement | adversarial check | gate |
|---|---|---|
| ERT-01 | Supply bytes with the wrong pinned size and digest; acquisition must reject them before writing raw data or an acquisition receipt. | `tests/adversarial/test_m07_slagdump_ert.py::test_wrong_source_bytes_are_not_imported` |
| ERT-02 | Plant a nonfinite electrode coordinate, invalid index, zero resistance, or undeclared trailing value; strict parsing must reject each malformed input. | `tests/adversarial/test_m07_slagdump_ert.py::test_malformed_ohm_rows_fail_closed` |
| ERT-03 | Remove reciprocals and instrument errors from a valid small survey; QC must say unavailable and must not fabricate error estimates. | `tests/adversarial/test_m07_slagdump_ert.py::test_absent_reciprocals_do_not_create_uncertainty` |
| ERT-04 | Compare the signed four-electrode flat-halfspace factor with its independent equation; a sign or geometry error must be visible in the calculated value. | `tests/adversarial/test_m07_slagdump_ert.py::test_flat_factor_matches_independent_signed_equation` |
| ERT-05 | Plant zero, negative, or nonfinite resistances; the disclosed assumed-weighting helper must refuse rather than create a plausible sigma. | `tests/adversarial/test_m07_slagdump_ert.py::test_assumed_sigma_refuses_invalid_resistance` |
| ERT-06 | Build a spatially ordered synthetic survey; training and both held-out partitions must be disjoint, with the central block withheld by midpoint. | `tests/adversarial/test_m07_slagdump_ert.py::test_holdouts_are_disjoint_and_spatially_frozen` |
| ERT-07 | Force the independent factor oracle to fail before inversion; the workflow must return unverified without a model or geology claim. | `tests/adversarial/test_m07_slagdump_ert.py::test_factor_failure_cannot_claim_field_inverse` |
| ERT-08 | Remove a provenance or rights boundary from the source/convergence documentation; the documented contract test must fail. | `tests/adversarial/test_m07_slagdump_ert.py::test_source_and_convergence_docs_preserve_nonclaims` |
