# CPU2 frozen folds for beta candidates 5 and 6

## Scope

Six deterministic family-0 / condition-0 synthetic gravity fits were replayed against the same frozen request (`55f22d00f261b094736708bc0dae40581cdd4b7f34ee9ac699281964c72cb321`) and CPU2 engine inventory (`27220b385b6ab936459a99d48f731a8a5529384981dd12c2a730555f4fca4d93`). Each fit used the existing 20-update cap and its own development fold. The test independently rebuilds the SimPEG sparse regularizer and weights, then checks the final model, objective gradient, box-projected KKT residual, and positive fixed-stage curvature.

All six fits converged and all six independent terminal checks passed. The retained JUnit report records six tests, zero failures, zero errors, and 30.630 seconds total. Its SHA-256 is `6D0C54CF3252E349D52C1E763C31E09A3AA138725A79D23EBA846D6F13D10270`; it is stored outside the repository at `E:\_worktrees\validation\geophysics\junit-cpu2-six-folds-2026-11-13.xml`.

| Beta candidate | Fold | Beta | Iterations | Terminal rule | First of final three weight changes |
| ---: | ---: | ---: | ---: | --- | ---: |
| 5 | 0 | 10 | 70 | `irls_fixed_point` | `3.7742151132273006e-7` |
| 5 | 1 | 10 | 76 | `irls_fixed_point_certificate` | `4.063900546007518e-6` |
| 5 | 2 | 10 | 80 | `irls_fixed_point_certificate` | `9.96392024644985e-6` |
| 6 | 0 | 100 | 72 | `irls_fixed_point` | `6.109920217414679e-8` |
| 6 | 1 | 100 | 78 | `irls_fixed_point` | `7.080344253166294e-7` |
| 6 | 2 | 100 | 77 | `irls_fixed_point_certificate` | `1.0348163696477964e-6` |

For every row, the final two recorded IRLS transitions were exact no-ops. The three certificate cases retained the prescribed 20 updates and passed the independent projected-KKT and strict-convexity checks; the ordinary fixed-point cases satisfied the existing transition criterion and passed the same independent checks. The observed maximum projected KKT residual among the certificate cases was `5.631051180898794e-13`; ordinary cases are asserted at `<=1e-12` in the test.

## Reproduction

From the repository root, with native numerical thread pools constrained before Python imports numerical libraries:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:NUMEXPR_NUM_THREADS = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
& .\.venv-pipeline\Scripts\python.exe -m pytest `
  tests/numerics/test_gravity_irls_corrected_matrix.py::test_cpu2_terminal_certificate_frozen_candidate6_fold2 `
  'tests/numerics/test_gravity_irls_corrected_matrix.py::test_cpu2_frozen_candidate5_and_6_folds' `
  -q -o addopts='' -o junit_family=legacy
```

## Scientific boundary

These six frozen development-fold solves establish solver convergence and independently checked fixed-stage terminal states for two candidate beta values. They do **not** establish the selected beta, full calibration success, sealed outer-test performance, field-data eligibility, or complete M02 acceptance. The remaining six beta candidates and full candidate/fold matrix still require calibration; no product-level or field-accuracy claim follows from these synthetic controls.
