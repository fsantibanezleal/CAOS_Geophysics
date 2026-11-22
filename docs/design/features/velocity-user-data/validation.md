# First-arrival user-data adversarial validation

| requirement | adversarial check | gate |
| --- | --- | --- |
| VUD-01 | Plant duplicate JSON keys, nonfinite constants, excessive depth and size, invalid units, impossible rays, and shape mismatch; require rejection at the bounded physical parser. | `tests/adversarial/test_velocity_user_data_adversarial.py::test_adversarial_vud_01_rejects_forged_requests` |
| VUD-02 | Compare the accepted result against the exact submitted bytes and ray sequence; refute changed source hashes, reordered identifiers, input mutation, or invented known-truth claims. | `tests/adversarial/test_velocity_user_data_adversarial.py::test_adversarial_vud_02_preserves_supplied_identity` |
| VUD-03 | Perturb times, uncertainties, and lambda, then plant active velocity bounds; compare the result with an independently assembled SciPy bounded least-squares oracle and require the projected KKT gate. | `tests/adversarial/test_velocity_user_data_adversarial.py::test_adversarial_vud_03_refutes_unbounded_or_unweighted_solves` |
| VUD-04 | Plant a checkpoint digest mismatch and a changed acquisition path; require identity rejection, actual learned inference on the supplied survey, and retained failure/domain warnings. | `tests/adversarial/test_velocity_user_data_adversarial.py::test_adversarial_vud_04_rejects_checkpoint_substitution` |
| VUD-05 | Alter result bytes and recompute their outer hash, inject inconsistent residual or KKT values, interrupt producer verification, and reopen a historical v1 record; reject forged v2 success while preserving the legacy status. | `tests/adversarial/test_velocity_user_data_adversarial.py::test_adversarial_vud_05_rejects_forged_generations` |
| VUD-06 | Plant malformed input and an already occupied output directory; require a nonzero CLI exit, no partial success manifest, and byte-identical existing output. | `tests/adversarial/test_velocity_user_data_adversarial.py::test_adversarial_vud_06_cli_fails_closed` |
