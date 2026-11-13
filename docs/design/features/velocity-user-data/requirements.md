# First-arrival user-data tools

This extends the approved local M09/M12 data-tools scope. It does not change the
frozen learned benchmark, train a new checkpoint or assert field accuracy.

| ID | Requirement | Gate |
| --- | --- | --- |
| VUD-01 | WHEN request bytes exceed a parser bound, contain duplicate or nonfinite values, or violate the physical contract, the local parser SHALL reject them before importing scientific packages. | `tests/adversarial/test_velocity_user_data_adversarial.py::test_adversarial_vud_01_rejects_forged_requests` |
| VUD-02 | WHEN a valid survey is processed, the result SHALL preserve its input-byte hash, ray order and identifiers without adding truth claims or modifying the input. | `tests/adversarial/test_velocity_user_data_adversarial.py::test_adversarial_vud_02_preserves_supplied_identity` |
| VUD-03 | WHEN supplied travel times, uncertainties or regularization change, the classical result SHALL solve the declared weighted, box-constrained slowness objective and pass an independent bounded-QP control. | `tests/adversarial/test_velocity_user_data_adversarial.py::test_adversarial_vud_03_refutes_unbounded_or_unweighted_solves` |
| VUD-04 | WHEN a learned checkpoint is requested, inference SHALL verify its pinned digest, use the supplied observations and geometry, and retain the failed-comparator and out-of-domain evidence. | `tests/adversarial/test_velocity_user_data_adversarial.py::test_adversarial_vud_04_rejects_checkpoint_substitution` |
| VUD-05 | WHEN an exported generation is altered or its physical diagnostics are inconsistent, verification SHALL reject it; historical v1 generations SHALL retain their explicit solve-then-clip status when reopened. | `tests/adversarial/test_velocity_user_data_adversarial.py::test_adversarial_vud_05_rejects_forged_generations` |
| VUD-06 | WHEN the CLI receives malformed input or an existing output path, it SHALL exit nonzero and SHALL NOT report success or overwrite a generation. | `tests/adversarial/test_velocity_user_data_adversarial.py::test_adversarial_vud_06_cli_fails_closed` |

Numerical controls: homogeneous cell-ray time agrees with distance/velocity to
1e-10 s. An independent SciPy bounded least-squares oracle matches interior and
active-limit solutions; the v2 projected KKT relative residual is at most
1e-9 after reconstructing the model from its serialized velocities. The browser
and Python active-limit control agree on 127 active cells, 134 active-set
iterations and selected velocity cells. Changed times/uncertainties/lambda
must change the corresponding actual result. This establishes the declared
quadratic solve on controls, not field accuracy. No known-truth error or
held-out score is invented for an unlabelled user survey.
