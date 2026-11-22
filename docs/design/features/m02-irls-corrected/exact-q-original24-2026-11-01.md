# Exact-q corrected IRLS frozen original24 matrix

> This matrix is retained as evidence for runtime
> `m02-survey-irls-cpu-2-terminal-certificate-exact-q-1`. Its pytest gate
> passed, but one cell exposed an initialization-path change. It is diagnostic,
> not the acceptance matrix for the current
> `exact-q-replay-legacy-init-1` runtime; see
> `exact-q-initialization-preservation-amendment-2026-11-01.md`.

## Result and scope

The source-bound CPU2 exact-q run completed all 24 family/condition cases and
the archive-identity control. Pytest reported 25 tests, 0 failures, 0 errors,
and 0 skips. Its JUnit `xunit2` configuration emitted the known
`record_property` compatibility warning; this did not fail a test.

This is a local synthetic-control result. It does not establish full M02,
scientific acceptance, field eligibility, or release readiness. The test gate
passes because every cell's actual status, candidate/fold accounting, archive,
physical forward prediction, and replay were checked. Those checks do not mean
that every cell produced a converged final refit or met a prediction-quality
threshold.

## Exact evidence

- Corrected runtime: `m02-survey-irls-cpu-2-terminal-certificate-exact-q-1`.
- Policy: `safeguarded-irls-interior-threepair-log17-terminal-certificate-exact-q-1`.
- Test: `tests/numerics/test_gravity_irls_corrected_matrix.py`, including
  `test_corrected_archive_identity_and_resume` and all 24 parameter cases of
  `test_original24_corrected_science`.
- JUnit: `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\corrected-exact-q-original24.xml`.
- JUnit SHA-256: `AC268B5CC256401625967C54C418A8AF125AB4B56BECFE62A5A317F4D3D5A123`.
- JUnit-reported duration: 17,262.220 s (4 h 47 min 42.220 s).
- External archive root: `E:\_Datos\CAOS_Geophysics\validation\m02-irls-terminal-cert-20261031\data`.
- Every calibration archive carries the exact runtime/source inventory, frozen request,
  all eight candidates and three folds, solver states, and result identity. The
  23 selected final refits also have independent outer-evaluation archives.
  Previous-epoch diagnostic archives remain in the same root and were not used
  as current-source receipts or deleted.
- The source inventory is embedded in each current-epoch calibration archive;
  family 0 / condition 0 result SHA-256 is
  `992cb4ee13296f2da8934565d1d82fa4bf86bbbaa0b566e9b10ff3b8cbec9647`.

## Scientific outcomes

All four predeclared nominal positive assertions passed:

| Family / condition | Selected beta index | Held-out WRMS | Truth-relative model RMSE |
|---|---:|---:|---:|
| 0 / 0 | 5 | 1.221180 | 0.782906 |
| 0 / 1 | 6 | 1.139376 | 0.516689 |
| 1 / 0 | 6 | 0.969996 | 0.851644 |
| 1 / 1 | 6 | 1.198917 | 0.862148 |

The six condition-3 cases selected a model, but their held-out WRMS values
were 2.60–2.96. These are the seeded unmodelled-nuisance negative controls and
are classified `poor_under_declared_noise`; they are not solver-quality wins.

| Condition | Selected final refits | Other final outcomes | Selected-cell outer WRMS range | Defined truth-RMSE cells |
|---|---:|---:|---:|---:|
| 0 | 6 / 6 | 0 | 0.968–1.221 | 5 / 6 |
| 1 | 6 / 6 | 0 | 0.899–1.199 | 5 / 6 |
| 2 | 5 / 6 | 1 `final_nonconverged` | 0.813–1.279 | 4 / 6 |
| 3 | 6 / 6 | 0 | 2.597–2.962 | 5 / 6 |

One additional cell did not produce a usable final model:

- Family 2 / condition 2 selected candidate index 7 (beta 1000) from three
  converged validation folds (fold WRMS 1.012197, 1.110446, and 1.398256),
  then the final development refit ended `final_nonconverged` with
  `zero_free_direction` after 26 accepted inner steps and four IRLS weight
  updates. The run correctly withheld its outer prediction and evaluation.
- Its exact-q result SHA-256 is
  `7a23ab45491947243f8cf46562fc7651e226ab2a7f1b2dfbfba6d9cfdeac4eaf`.
- The preserved prior `terminal-certificate-1` archive for the corresponding
  family/condition had a converged final refit. Its runtime/policy identity and
  request hash differ, so it is diagnostic evidence rather than an exact
  same-request replay. The outcome change across source epochs needs diagnosis
  before acceptance. Do not relabel this result as converged, certify the
  partial four-update path, or relax the optimizer stopping rule.

Family 4 has no truth prism in the frozen controls, so truth-relative model
RMSE is undefined there (`null`) by construction. It still has forward, held-
out, and solver outcomes.

## Remaining M02 work

1. Diagnose and resolve (or explicitly retain as an accepted negative result
   through an approved scientific decision) family 2 / condition 2's
   `zero_free_direction` final-refit regression. Keep the current archive and
   compare the exact source-bound inputs and final-refit trace to the preserved
   prior-epoch diagnostic archive.
2. Run the prescribed corrected noise/refit gates and the 20-repeat nominal
   and cap-bound resource controls with source-bound receipts.
3. Complete independent numerical review and the separate inspection SDD/API/
   UI/course gates. This matrix alone does not clear M02 or deployment.

