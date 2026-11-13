# Supplied acoustic shot-gather workflow

This implements the approved offline CPU/GPU lane. It does not activate a
server FWI job, alter the frozen canonical producer, or establish field validity.

| ID | Requirement | Gate |
| --- | --- | --- |
| FU-01 | WHEN an external input directory contains malformed, oversized, nonfinite, rights-incomplete, hash-mismatched or physically invalid members, admission SHALL reject it before propagation or scientific execution. | `tests/adversarial/test_fwi_user_data_adversarial.py::test_adversarial_fu_01_rejects_invalid_source` |
| FU-02 | WHEN a valid user survey and explicit compute device are supplied, the actual full-band and multiscale inverses SHALL use the supplied observations and starting model, honor frequency, regularization and iteration controls, and SHALL not substitute truth, training or silent CPU fallback. | `tests/adversarial/test_fwi_user_data_adversarial.py::test_adversarial_fu_02_uses_supplied_gpu_inputs` |
| FU-03 | WHEN either inverse reaches its finite budget, the result SHALL retain full observed, predicted and signed residual samples, acquisition order, physical axes, held-out receiver identity, states, solver failures and measured resources without making a convergence or geology claim. | `tests/adversarial/test_fwi_user_data_adversarial.py::test_adversarial_fu_03_retains_full_budget_lineage` |
| FU-04 | WHEN a generation is exported or reopened, the producer SHALL verify every member's digest, bytes, shape, units and array order before publishing completion, and SHALL reject altered or incomplete generations. | `tests/adversarial/test_fwi_user_data_adversarial.py::test_adversarial_fu_04_rejects_tampered_generations` |
| FU-05 | WHEN the CLI receives malformed input, an unavailable requested device, a source mismatch or an occupied output, it SHALL exit nonzero without overwriting data, leaking supplied values or publishing a success manifest. | `tests/adversarial/test_fwi_user_data_adversarial.py::test_adversarial_fu_05_cli_fails_closed` |
| FU-06 | WHEN a local user generation is opened in the public web client, the importer SHALL validate the complete generation before showing linked full-sample gathers, signed residuals and physical model/state views, and SHALL perform no upload, solve or fabricated truth fallback. | `tests/adversarial/test_fwi_user_data_adversarial.py::test_adversarial_fu_06_browser_rejects_unverified_generation` |

The complete physical contract, algorithm and experiment limits are specified in
[`design.md`](design.md). Validation is local and controlled; it does not admit
server FWI computation or claim acoustic field accuracy.
