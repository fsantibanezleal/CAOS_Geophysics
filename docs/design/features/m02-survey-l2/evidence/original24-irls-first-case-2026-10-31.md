# Original24 IRLS matrix first-case result, 2026-10-31

## Scope

This is the recorded first actual calibration from the prospective source-correct
24-condition IRLS matrix. The complete matrix did not pass or finish. The run was
stopped after this first case failed its frozen candidate/resource requirements;
the other 23 parameter combinations were not run. This receipt preserves the
actual archived calibration, not a passing suite or an independent review.

## Exact execution

- Product commit at run start: `85343b2e936a4b8e94af473645f5fa5e9211357e`.
- Runtime: CPython 3.12.10, Windows, `.venv-pipeline`.
- Native thread policy: `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.
- Command: `python -m pytest tests/numerics/test_gravity_irls_original_matrix.py --junitxml <external-results.xml>`.
- Device data and temporary roots: `E:\_Datos\CAOS_Geophysics\validation\m02-original24-irls-20261031\`.
- Completed case: family 0, condition 0, seed 700001.
- Calibration result: `selection_status=insufficient_candidates`, no selected candidate, `wall_seconds=1800.0469999999987`; the frozen matrix assertion requires at most 1800 seconds.
- All eight beta candidates were ineligible because at least one of their three development folds did not converge. Across the 24 actual folds: 4 converged, 14 reached `irls_iteration_cap`, and 6 reached `wall_cap`.
- The archived calibration is 52,980,452 bytes, SHA-256 `93a05f3bbc0aa47e4f1f63a1866d6e3ec1b585ff844768d8ee86a475bea09bb6`. It was reopened with the native archive reader and its stored outcome fields and fold statuses were inspected.
- Pytest emitted the first case failure; the remaining matrix was interrupted to avoid repeating the same long capped calibration across the other parameter combinations. No complete JUnit file or 24-case matrix result exists for this run.

## Frozen failure

No candidate was selected, so this case produced no development refit or outer
evaluation. No fold cap, beta, seed, model, threshold, or eligibility rule was
changed. The complete ordinary-L2 24-condition results are a separate matrix
and do not imply IRLS acceptance. The original positive non-null IR-C06
fixed-point failure also remains separately recorded in
[its cause analysis](../irls-positive-cause.md).

| Candidate beta | Fold outcomes | Eligible |
| ---: | --- | --- |
| 0.0001 | converged, iteration cap, iteration cap | no |
| 0.001 | iteration cap, iteration cap, iteration cap | no |
| 0.01 | iteration cap, iteration cap, wall cap | no |
| 0.1 | wall cap, iteration cap, iteration cap | no |
| 1 | iteration cap, iteration cap, iteration cap | no |
| 10 | converged, iteration cap, iteration cap | no |
| 100 | converged, converged, wall cap | no |
| 1000 | wall cap, wall cap, wall cap | no |

The source-correct 24-case IRLS matrix, matched L2 comparison, and full M02
scientific and resource acceptance remain open. The fixed 1800-second calibration
cap is an observed failure boundary, not an accepted performance limit.
