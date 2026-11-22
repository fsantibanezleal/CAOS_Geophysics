# Original48 first-fold independent replay, 2026-10-31

## Scope

This replay validates one locked original48 development fold with its exact
source, request, beta, noise, and fixed 21-stage policy. It does not validate
candidate selection, all development folds, refits, the 24-condition matrix,
field eligibility, or full M02 acceptance. The separately retained original24
calibration for family0/condition0 remains ineligible because its candidates
contain nonconverged folds.

## Exact execution

- Product base commit: `f0ec2fc` (`task/geophysics-client-first-completion`).
- Local tree: dirty; the receipt-preflight test change is included in the
  executed source and is not represented by that commit.
- Runtime: CPython 3.12.10, Windows, `.venv-pipeline`.
- Native thread policy: `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`,
  `MKL_NUM_THREADS=1`.
- Command: `pytest tests/numerics/test_gravity_irls_original.py::test_firstfold_receipt_preflight tests/numerics/test_gravity_irls_original.py::test_locked_original48_firstfold`.
- Result: 2 passed, 0 failed/errors/skips; JUnit duration 104.266 seconds.
- Outcome receipt: `E:\_Datos\CAOS_Geophysics\validation\original-irls-firstfold-final-20261031\outcome.json`, SHA-256 `7fc773831093f1d7b1e92ee65bf4f3d964a4f3042aec3180f98697b5629c59df`.
- Native archive: `E:\_Datos\CAOS_Geophysics\_Temp\original-irls-firstfold-final-20261031\test_locked_original48_firstfo0\data\original48.gza`, SHA-256 `289b68015158f2217d5a05bd66d17bb520fcc3e2f246f1ae20280d8934b582fa`.

## Measured outcome

- Terminal: `converged/irls_fixed_point`; all21 inner stages converged and all20
  weight updates were retained.
- Accepted optimizer steps:100; auxiliary calls:0; wall time:53.437 seconds.
- The independent per-stage BVLS replay passed every frozen comparison. Maximum
  model-relative error was `3.4443673003985776e-11`, maximum physical
  prediction absolute error was `7.198685813044829e-14`, and maximum objective
  relative error was `3.533164975682536e-15`.
- This first-fold result does not contradict the original24 matrix failure:
  that matrix requires all three folds for at least one frozen beta candidate
  to converge before selection. Its first case had no eligible candidate.

## Harness correction

The expensive first-fold test now checks that
`GEOPHYSICS_M02_IRLS_FIRSTFOLD_RECEIPT` names a new file beneath an existing
absolute external directory before starting the solver. A fast unit test covers
missing, relative, existing, and nonexistent-parent paths. This prevents a
missing evidence destination from being discovered only after a full solve.

The 24-condition matrix archive names now bind runtime epoch, source inventory,
and exact request digest. A cached archive is replayed and validated only under
that identity; an older `family0-condition0.gza` was rejected by the current
source-bound verifier and remains preserved. A fast unit test checks stable
names and request separation. The cache change does not make the ineligible old
calibration a passing result and does not rerun the remaining 23 cases.
