# M02 sealed L2 selection workflow test replay, 2026-10-31

## Scope

This current-source replay executes every test in `tests/numerics/test_gravity_l2_selection.py` except the separately receipt-backed `test_complete_locked_l2_control_matrix` parameter matrix. It verifies candidate-fold execution, refit/evaluation separation, tamper rejection, partition controls, unavailable outcomes, and injected failure barriers. It is software/workflow evidence on authored test controls; it does not establish predictive efficacy, the locked 24-condition calibration matrix, independent acceptance, field eligibility, or full M02 acceptance.

## Exact run

- Repository commit: `11cef85ea302d3b256145a4489ae0841ca80c8b9`.
- Runtime: CPython 3.12.10, Windows, `.venv-pipeline`.
- Native thread policy: `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.
- Command: `python -m pytest tests/numerics/test_gravity_l2_selection.py -k 'not complete_locked_l2_control_matrix' -q` with JUnit output and pytest temporary files outside the checkout.
- Result: 27 passed, 0 failed, 0 errors, 0 skipped; 181.449 seconds.
- JUnit SHA-256: `0b7b34efcb70bf6d94abd430431fe5381e8fd2d2af53cb9b0a422e804d9bae41`.
- Test source SHA-256: `f6557c33df18599ec8d511b9656a67456d1434ff84430ea4cf87b86e1bc82028`.
- Solver source SHA-256: `3b6e20f6cf0280a3db0f0bf14beec2dec0851445cf9ec157a6ec66d4176f823e`.
- External result root: `E:\_Datos\CAOS_Geophysics\validation\m02-selection-20261031-current`.

## Interpretation

The replay includes the real 25-fit authored calibration workflow test and sealed outer evaluation test, plus deterministic fault-injection tests. Test fixture scores are not benchmark evidence: passing means the tested workflow obeyed its declared mechanics. The 24-condition scientific control matrix, resource envelope, nonnull IRLS acceptance, independent exact-source review, field-data acceptance and product integration remain open.
