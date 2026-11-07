# Supplied acoustic shot-gather workflow

2026-10-08. This implements the already approved M10 offline CPU/GPU lane.
It does not activate a server FWI job or change the frozen canonical producer.

- FU-01: validate an explicit external directory containing exactly a bounded
  closed request, original little-endian float32 observations and an independent
  float32 initial velocity model. Reject bad hashes, shapes, units, geometry,
  rights, nonfinite values and symlink/repository custody before propagation.
  Gate: `tests/data/test_fwi_user_data.py::test_admission_before_engine`.
- FU-02: run the actual existing matched full-band/multiscale L-BFGS inverses
  on supplied observations and initial velocity, with explicit frequency, beta,
  iteration budget and device. There is no truth input, inferred source wavelet,
  silently changed acquisition, training or downloaded engine.
  Gate: `tests/data/test_fwi_user_data.py::test_actual_gpu_input_and_parameter_effect`.
- FU-03: retain complete observed/predicted/residual samples, evaluated model
  iterations, original receiver order, physical axes, fixed holdout, solver
  failures and actual resources. Withheld receivers cannot select or optimize a
  state. A finite-budget stop is not a convergence or geological-recovery claim.
  Gate: `tests/data/test_fwi_user_data.py::test_lineage_and_no_truth`.
- FU-04: exclusively export a new external generation, reopening every binary
  member with its SHA-256, byte count, exact shape, units and array order before
  publishing a completion manifest. Preserve failed partial generations.
  Gate: `tests/data/test_fwi_user_data.py::test_export_roundtrip_and_tampering`.
- FU-05: CLI malformed input, unavailable requested GPU, output reuse and source
  mismatch return nonzero without a success manifest or leaked supplied values.
  Gate: `tests/data/test_fwi_user_data.py::test_cli_and_no_overwrite`.
- FU-06: public web import is local-only and must verify the complete generation
  before displaying linked full-sample gathers, signed residuals and physical
  velocity/iteration frames. No upload, solve, fallback or known field truth is
  fabricated. Gate: `frontend/src/test/fwi-local-contracts.test.ts` and
  `frontend/e2e/local-fwi-results.spec.ts`.

The parser and serialization tests do not establish acoustic correctness. The
existing independent analytic, refinement and directional-adjoint tests remain
unchanged; an additional opt-in actual CUDA workflow test uses small original
controlled observations and explicitly records its reduced iteration budget.
Full-budget supplied-input execution is a separate measured gate, not inferred
from that small integration test.
