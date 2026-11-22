# Locked ordinary-L2 24-condition replay, 2026-10-31

## Scope

This is the full configured current-source 6-family by 4-condition local gravity L2 calibration, refit, and held-out evaluation test. It is the source-bound run of `test_complete_locked_l2_control_matrix`; it is not field validation, independent review, VPS acceptance, or complete M02/product acceptance.

## Exact run

- Repository commit at run start: `64372916d2853db13b8b7595570bce4f31eba2f2`.
- Runtime: CPython 3.12.10, Windows, `.venv-pipeline`.
- Native thread policy: `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.
- Command: `python -m pytest tests/numerics/test_gravity_l2_selection.py::test_complete_locked_l2_control_matrix -q` with JUnit and temporary files outside the checkout.
- Result: 24 passed, 0 failed, 0 errors, 0 skipped; pytest test time 8,223.663 seconds.
- JUnit SHA-256: `002370bbfda0ec05b7125b4f10b25706d28da87b4b22d12236dd3f62395ea184`.
- Every case recorded its seed, result hashes, selected candidate, per-fold status, per-fold score, outer WRMS, model error ratio where truth is defined, and wall time in the JUnit `locked_l2_outcome` property.
- The installed pytest configuration emitted 24 warnings that `record_property` is incompatible with its `xunit2` family. All 24 properties are present in the saved JUnit and were parsed for this report; the warnings did not become failures.

## Per-condition outcomes

`Eligible` is the number of beta candidates with all three folds eligible. `Failed folds` counts retained nonconverged fold outcomes across all candidates. `Outer WRMS` is normalized by the declared observation uncertainty. Model RMSE is a ratio to the known synthetic truth and is not computed where that case does not declare a truth model. Full precision values and all fold outcomes remain in the external JUnit receipt.

| Family | Condition | Selection | Beta | Eligible | Failed folds | Outer WRMS | Model RMSE ratio | Wall seconds |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| F0 | 0 | selected | 10 | 6/8 | 6 | 1.233 | 0.898 | 192.75 |
| F1 | 0 | selected | 100 | 6/8 | 6 | 0.942 | 0.831 | 160.69 |
| F2 | 0 | selected | 1000 | 6/8 | 6 | 1.132 | 0.610 | 409.01 |
| F3 | 0 | selected | 10 | 6/8 | 6 | 1.003 | 0.435 | 280.34 |
| F4 | 0 | selected | 1000 | 5/8 | 7 | 1.143 | not computed | 179.12 |
| F5 | 0 | selected | 100 | 6/8 | 6 | 1.108 | 0.844 | 174.66 |
| F0 | 1 | selected | 100 | 6/8 | 6 | 1.218 | 0.607 | 386.88 |
| F1 | 1 | selected | 100 | 5/8 | 7 | 1.220 | 0.833 | 387.80 |
| F2 | 1 | selected | 1000 | 5/8 | 7 | 1.116 | 0.607 | 435.26 |
| F3 | 1 | selected | 10 | 6/8 | 6 | 1.087 | 0.483 | 291.11 |
| F4 | 1 | selected | 1000 | 6/8 | 6 | 1.172 | not computed | 306.47 |
| F5 | 1 | selected | 100 | 5/8 | 8 | 0.901 | 0.874 | 328.02 |
| F0 | 2 | selected | 100 | 5/8 | 8 | 1.274 | 0.532 | 300.39 |
| F1 | 2 | selected | 1000 | 5/8 | 7 | 1.054 | 0.872 | 231.03 |
| F2 | 2 | selected | 1000 | 6/8 | 6 | 0.839 | 0.605 | 444.89 |
| F3 | 2 | selected | 100 | 5/8 | 7 | 1.066 | 0.505 | 525.88 |
| F4 | 2 | selected | 1000 | 5/8 | 7 | 0.966 | not computed | 415.78 |
| F5 | 2 | selected | 10 | 5/8 | 8 | 0.818 | 0.911 | 232.97 |
| F0 | 3 | selected | 100 | 4/8 | 10 | 2.851 | 1.035 | 341.24 |
| F1 | 3 | selected | 1000 | 5/8 | 9 | 2.730 | 0.882 | 456.45 |
| F2 | 3 | selected | 100 | 5/8 | 9 | 2.898 | 0.937 | 442.38 |
| F3 | 3 | selected | 100 | 5/8 | 9 | 2.639 | 0.620 | 334.41 |
| F4 | 3 | selected | 1000 | 5/8 | 9 | 2.957 | not computed | 304.59 |
| F5 | 3 | selected | 1000 | 5/8 | 9 | 2.613 | 0.954 | 658.45 |

## Interpretation and limits

All 24 cases selected a candidate and completed the separate final refit/evaluation path. The four cases with explicit scientific efficacy assertions (families 0 and 1, conditions 0 and 1) passed their declared outer-WRMS `<= 2` and model-RMSE-ratio `< 1` checks. The other 20 cases are diagnostic controls: the test requires complete workflow/result structure and forward-prediction identity, but does not impose those same geological error thresholds on them. Their metrics above must not be promoted into a universal accuracy claim. Candidate fold failures were retained rather than replaced; each case still had four to six eligible candidates.

This closes the local execution portion of the locked ordinary-L2 matrix for these exact source bytes. The independent pinned review remains required. Non-null sparse IRLS still fails its frozen final-transition criterion, and a distinct low-beta Armijo case remains unresolved. Field-source eligibility, actual API/user-data integration, host admission, and full product acceptance remain open.
