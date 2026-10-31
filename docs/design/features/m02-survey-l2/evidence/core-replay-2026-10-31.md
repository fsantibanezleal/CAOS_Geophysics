# M02 native survey and ordinary L2 core replay, 2026-10-31

## Scope

This is a current-source Windows replay of native survey admission, geometry
partitioning and the ordinary gravity L2 solver. It does not run the
receipt-backed 24-condition calibration matrix or establish independent M02,
field, hosted or product acceptance.

## Exact run

- Repository commit: `11cef85ea302d3b256145a4489ae0841ca80c8b9`.
- Runtime: CPython 3.12.10, Windows, `.venv-pipeline`.
- Native thread policy: `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`,
  `MKL_NUM_THREADS=1`.
- Tests: `tests/data/test_gravity_survey_l2.py` and
  `tests/numerics/test_gravity_l2.py`.
- Result: 186 passed, 0 failed, 0 errors, 0 skipped.
- JUnit SHA-256:
  `36a703c59e9d10a89c49ebbd8c51cd44387c1fded6827cd987ab21c3749f828f`.
- JUnit and pytest scratch remain outside the repository under the configured
  external validation root.

Reproduction command, with `$RunRoot` created outside every Git checkout:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv-pipeline\Scripts\python.exe -m pytest `
  tests/data/test_gravity_survey_l2.py `
  tests/numerics/test_gravity_l2.py `
  -q --junitxml (Join-Path $RunRoot 'm02-core.junit.xml') `
  --basetemp (Join-Path $RunRoot 'pytest-tmp')
```

The exact six-cell case previously recorded as failing,
`upper_lower-1500.0-diagonal_sd`, was rerun separately with the declared
single-thread policy and passed. An initial invocation without that policy was
rejected before solving with `metric: reviewed single-thread native workspace
required`; that result is a runtime-policy rejection, not a numerical solve
failure.

## Source identities

| File | SHA-256 |
| --- | --- |
| `data-pipeline/gravity_survey_l2.py` | `50934e1f56fcd468787b113598d01966b0a0eb1b124cb95363605fea8278da97` |
| `data-pipeline/gravity_l2.py` | `3b6e20f6cf0280a3db0f0bf14beec2dec0851445cf9ec157a6ec66d4176f823e` |
| `data-pipeline/gravity_l2_metric.py` | `d09a2b4630258d2c26a1a82ea92a3cd79b42143695d3e630d5252df5ba8dfe8b` |
| `data-pipeline/physical_optimizer.py` | `4745d41ff8afb908260611601861db8303ce7bd612ff0ea614cceb201a20bc86` |
| `tests/data/test_gravity_survey_l2.py` | `0da369509d4725646473fb611ee69a5c8e4aead81bfa4468b2e1b763c2a7816e` |
| `tests/numerics/test_gravity_l2.py` | `18a8981be46e7d1f5cdc7e2663af90f8e6e5f88c464d2b4e6f14a355cd4060e4` |

The 24-condition matrix, sparse IRLS convergence, owner-authenticated user-data
workflow, field-source eligibility, online admission and release acceptance
remain separate open gates.
