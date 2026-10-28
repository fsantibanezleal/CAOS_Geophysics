# Nonlinear candidate KKT refinement — 2026-10-28

## Scope

This execution corrects premature `converged` status in the local nonlinear
candidate optimizer. It does **not** accept the M04 method or bind this
candidate to an accepted M02 optimizer. It uses the existing three-start
authored tiny control and independent bounded SciPy/Choclo comparison; it does
not change observations, geometry, covariance, bounds, resources or comparison
tolerances.

## Failure reproduced

At normalized KKT stop `1e-5`, the `q=0` and `q=1` starts were labelled
converged while missing the frozen normalized KKT limit `1e-7` and the
independent prediction RMS limit `1e-6 nT`:

| Start | Steps | Relative objective gap | Prediction RMS (nT) | Normalized KKT | Result |
|---:|---:|---:|---:|---:|---|
| 0.0 | 5 | `8.693482045352141e-10` | `2.4656978531137448e-6` | `1.7444783433719395e-6` | failed prediction and KKT gates |
| 0.2 | 2 | `1.2467804566540508e-13` | `1.7353085515470412e-9` | `4.2515228681010836e-12` | pass |
| 1.0 | 1 | `4.38470926233947e-10` | `1.6916710825089738e-6` | `4.351743774509328e-6` | failed prediction and KKT gates |

The relative objective limits already passed. The defect was the native
optimizer stopping too early, not a test harness failure.

## Correction and rerun

The candidate now requires normalized projected KKT `<=1e-7` before reporting
convergence. The unchanged three-start independent comparison passes:

| Start | Steps | Relative objective gap | Prediction RMS (nT) | Normalized KKT |
|---:|---:|---:|---:|---:|
| 0.0 | 6 | `1.249000902703301e-13` | `2.0089804087838983e-9` | `6.473906677910262e-13` |
| 0.2 | 2 | `1.2467804566540508e-13` | `1.7353085515470412e-9` | `4.2515228681010836e-12` |
| 1.0 | 2 | `1.2434497875801753e-13` | `3.8286768485776543e-10` | `1.544487777359548e-12` |

The complete focused M04 numerical, data-contract, bundle and CLI selection
collected 306 tests and exited successfully after the solver change. The
three-start test was then rerun with an explicit `1e-7` KKT assertion; all
three starts passed. `ruff check` and `git diff --check` passed for the changed
source.

## Acceptance boundary

These are local authored synthetic controls. They establish neither global
optimality nor field accuracy. The accepted public M02 optimizer source/export,
precision/stopping binding, full 216-row/648-component/528-parameter M04
refit, sparse eight-stage acceptance, full field/source qualification, hosted
resource admission, browser acceptance and release acceptance remain separate
gates. `scientific_acceptance` remains false.
