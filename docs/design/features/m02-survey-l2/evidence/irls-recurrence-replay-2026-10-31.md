# Original IRLS recurrence and derivative replay, 2026-10-31

## Scope

This replay checks that the actual 21 native stage solves match an independent
positive-definite weighted-least-squares recurrence and that the analytic
derivative of the scaled-p1 weight map matches finite differences. It validates
stage accuracy, not convergence of the frozen finite schedule or selection on
the original24 matrix.

## Exact run

- Product commit at run start: `b47a3f4a2ea46431c8af823bdb99ebc05bf6d187`.
- Runtime: CPython 3.12.10, Windows, `.venv-pipeline`.
- Native thread policy: `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.
- Command: `python -m pytest tests/numerics/test_gravity_irls_recurrence.py -q`.
- Result: 2 passed, 0 failed, 0 errors, 0 skipped; 12.673 seconds.
- JUnit SHA-256: `c06a5bcadd0435e3b1b161a04ce5ca989066f6827fa11e12a714a75d81e9aa3b`.
- Test source SHA-256: `a29648bcf09ab5741ef8a949c1dacd65b19963ace3eeebc1f68ea887ab441d01`.
- Solver source SHA-256: `466144b89a12d846723b413633b036dcbeda7a67087e8a82f4bbeb7ecec4542c`.
- Maximum infinity-norm discrepancy between native stage models and independent recurrence: `1.0448308884747348e-12`.

The three required final model/weight relative changes independently reproduce
as `(8.2395e-4, 1.17218e-1)`, `(6.7222e-4, 3.48394e-2)`, and
`(5.5561e-4, 8.71846e-3)`. They exceed the unchanged `1e-6` fixed-point test.
This confirms that the native inner stages are accurate while the frozen
outer recurrence remains nonconverged; it does not justify relabeling the
failure or extending its schedule.
