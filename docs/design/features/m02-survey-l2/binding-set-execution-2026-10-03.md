# Actual cpu-3 execution, 2026-10-03

The approved BS-B binding-set amendment was implemented after the retained test-first red. This is a failed/incomplete candidate checkpoint, not whole L2/M02 acceptance. It does not alter the frozen objective, starts, bounds, noise, runtime, vendor sources, scientific tolerances or the original stopping policy.

## Exact source and tests

- `data-pipeline/gravity_l2.py`: SHA-256 `9f97d30cb9551576dc1664bdb243b2936293db633a93850141a83654a47cc594`.
- `tests/data/test_gravity_survey_l2.py`: SHA-256 `b4747898647e2cf0052f90ffebad68ec5c629be5a4824c31ce738ab3eea3d79b`.
- `tests/numerics/test_gravity_l2.py`: SHA-256 `daa44f3593734919b3ddfeeb0bd419be7adf8de5c664895b61139e50ce4c02df`.

Runtime: existing trusted CPython3.12.10, NumPy2.2.6, SciPy1.15.2, SimPEG0.25.2, Geoana0.8.1, discretize0.12.0, Choclo0.3.2. One OpenBLAS/OMP/MKL thread; no install, package patch or GPU claim. Pytest ran with bytecode/cache disabled and an owned temporary Numba cache. Local JUnit files remain private and untracked because they contain machine paths.

## Executed checks, not prospective passes

All commands used the existing pipeline interpreter; no source exclusion was added to the focused three-file run. Commands append `-q -o addopts= -p no:cacheprovider`, with private JUnit outputs below `.validation/binding-resume-20261003/`.

| Execution | Result | Private original XML SHA-256 |
| --- | --- | --- |
| Before implementation: two paired test files, `-k binding` | 25 failed, 5 passed, 154 deselected; 18.93s | `ef3d80e11d2ff1777d7c96deb0f0a893e9b4eff04e45db1dde15c77ea535dcd0` |
| After implementation: same binding controls | 30 passed, 154 deselected; 2.48s | `9effb23730710aaa3c041fcd37687e914785946605f1c3a9478901d565db2bb3` |
| Complete `test_gravity_survey_l2.py`, `test_gravity_l2.py`, `test_gravity_l2_selection.py` | 189 passed, 1 failed, zero skips; 50.83s | `0071094df543bc358727cd0617520316f27cf70845129f2f30c5198b3dc208e6` |

The complete focused failure is `test_independent_six_cell_bound_starts[upper_lower-1500.0-diagonal_sd]`: status nonconverged, reason zero_free_direction. The new bound-release controls passing do not override this result.

## Diagnosis of the retained failure

A separate fresh execution of the original physical six-cell control compared the actual terminal model with the test-owned Choclo/pairwise regularizer/Cholesky/BVLS reference. BVLS remains an independent test oracle, not a production fallback. Measured terminal differences:

- density relative L2: `2.7047834410359302e-12`;
- objective relative difference: `1.1102230246251565e-16`;
- prediction maximum absolute difference: `1.5804233884050013e-14` mGal;
- independent gradient infinity norm: `2.3321768127804177e-11`;
- normalized projected KKT: `1.3099677235298743e-13`.

The run records four iterations and five states. Its objective sequence is approximately `18.0629391, 13.16565601, 11.1099894, 0.043821538373794246, 0.043821538373794246`. The first two directions release nonbinding constraints; subsequent directions use native face CG. The failed last line-search trial is iteration4, trial17, step `7.62939453125e-06`, computed displacement/slope zero.

This is a stopping/finite-precision issue after near-optimality, not evidence of correct convergence status. The frozen policy requires the absolute projected gradient exception or normalized KKT plus three consecutive small objective changes. It reaches a near-optimal state before enough such changes accumulate, attempts another native step, and retains the rounded-zero failure. No duplicate state, jitter, retrospective convergence, changed absolute tolerance or extra fallback has been introduced to make it pass. A new stopping rule would require a separate explicit mathematical/design review and fresh controls before implementation.

## Still pending

The full broader suite, complete sealed calibration/refit/evaluation implementation, locked 24-family/condition outcomes, resource receipts and detached independent full review are not supplied by this checkpoint. The existing selection test file tests geometry partitions only; it is not full parameter-selection acceptance. Independent review cannot be claimed from MAIN's own author execution. No main promotion, canonical bake/import, field admission, API activation or deployment follows. Historical cpu-2 proposal/source/execution evidence stays unchanged.
