# M04 magnetic physical foundation replay — 2026-11-02

## Scope

This replay covers the current local source for bounded magnetic survey parsing,
geometry partitioning, geometry-only export/import, the physical SimPEG forward
and quantity-specific Jacobians, Gaussian covariance whitening, regularization,
objective derivatives, fit-fold assembly, fold scoring, and upward continuation.
It does not execute a magnetic inverse, select a candidate, evaluate a sealed
partition, or qualify field data, API admission, online jobs, or release readiness.

## Result

The focused command ran 430 tests: 430 passed, zero failed, zero errors, and zero
skipped. The JUnit report is stored outside the repository at
`E:\_Datos\CAOS_Geophysics\validation\m04-foundation-current-20261102.xml`;
SHA-256: `9200fe0809630cc49de7cf8e65705adc283b4aba997d34d2d9ee236b167e98b9`.
BLAS/OpenMP/MKL/NumExpr thread pools were each capped at one.

## Acceptance boundary

The full M04 requirements remain planned. In particular, no independently
accepted generic M02 optimizer binding is declared for this magnetic objective;
there is no full fit/IRLS/nested-selection/sealed-evaluation path. The test pass
establishes only the listed foundation components. The convergence ledger still
reports one failed and seventeen unresolved requirements; this replay does not
change those verdicts or authorize VPS deployment.
