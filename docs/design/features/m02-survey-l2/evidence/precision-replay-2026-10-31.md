# M02 precision and allocation-control replay, 2026-10-31

## Scope

This current-source replay runs the complete `tests/numerics/test_gravity_l2_precision.py` module, including precision contracts and the real certified-delta allocation control. It is local software evidence; its process measurement does not establish a resource upper bound or host acceptance.

## Exact run

- Repository commit at run start: `64372916d2853db13b8b7595570bce4f31eba2f2`.
- Runtime: CPython 3.12.10, Windows, `.venv-pipeline`.
- Native thread policy: `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.
- Command: `python -m pytest tests/numerics/test_gravity_l2_precision.py -q` with JUnit and temporary files outside the checkout.
- Result: 81 passed, 0 failed, 0 errors, 0 skipped; 50.010 seconds.
- JUnit SHA-256: `65954a6c466d3394a1da90d45266b7a57b7bbbd2c5ee4a4bc63a716568b52a2d`.
- The test for the real certified-delta allocation case emitted one `record_property` warning because pytest uses the `xunit2` JUnit family; the saved case property is present and the test passed.

## Source identities

| File | SHA-256 |
| --- | --- |
| `tests/numerics/test_gravity_l2_precision.py` | `21d8fdd6e97552fd6efcb0e8910fd90237f8aceecb828e00487a88aa6e295d27` |
| `data-pipeline/gravity_l2_precision.py` | `57727cac9ab6550eab902d20d6c43e662be8f9fac406896c6797d1e29b3e7c1a` |
| `data-pipeline/gravity_l2.py` | `3b6e20f6cf0280a3db0f0bf14beec2dec0851445cf9ec157a6ec66d4176f823e` |

The independent full-source review, resource upper proof, host admission, field-source eligibility, non-null IRLS convergence and overall product acceptance remain open.

## Narrow-stencil arithmetic-path change, same day

The current dirty source removes the `<=8` stencil-width shortcut that forced
certified sparse row products through Decimal arithmetic. It now attempts the
existing outward-bounded native row reduction at every width and retains the
Decimal fallback whenever the interval preconditions fail. This changes only
the arithmetic route; it does not change the bound, optimizer stopping rules,
or acceptance criteria.

- Current focused checks: `tests/numerics/test_gravity_l2_precision.py` and
  `tests/numerics/test_physical_original_terminal.py` passed; scoped Ruff and
  `git diff --check` passed.
- Positive original48 first-fold regression: converged after 20 IRLS weight
  updates; independent replay accepted. Receipt SHA-256
  `577a5fe81eaa406df3693339dcbad797cbe6adec2093450c8ed88d74f19e5eb7`; JUnit
  SHA-256 `b1e4df2b9b778a313d3e7b145c6c9a5ca6738ae37228f24aeab2916a01c54e04`.
  Measured wall time was `36.906` seconds. The comparable prior profile was
  `61.282` seconds; this is one positive fold, not a matrix-level speed claim.
- The current-source family0/condition0 original24 calibration completed and
  its archive was independently replayed. The prior status note that it had
  been interrupted without an archive was incorrect and is superseded here.
  Archive:
  `E:\_Datos\CAOS_Geophysics\validation\m02-original24-irls-20261031\archives\family0-condition0-42c602cd2ccd226e.gza`,
  SHA-256 `c4b14395699a84a5ca459ae865f955a7f8baea1ec2869051cc8b215b3b6a64bf`.
  Request SHA-256
  `21df6770b31fcc94b67025a202cc589e0df4412f156f41bf4b8db1f4bd9b2cc6`,
  result SHA-256
  `72148cb969aca853f7c3b494ddcb03676c15af9e4a99ed717dde83bc2835dda3`,
  and complete source inventory SHA-256
  `f543f9f1919481f1e2c7b110789fde4872548f0ba00d607691c4fbb6853de0ef`.
- The unchanged strict total calibration limit failed narrowly:
  `1800.313000000002` seconds versus 1800. Selection was
  `insufficient_candidates`; zero of eight beta candidates were eligible, so
  no development refit or outer evaluation ran. Across 24 records, 4 reached
  `irls_fixed_point`, 16 reached `irls_iteration_cap`, 1 reached
  `merit_line_search_failed`, and 3 reached `wall_cap`. Twenty-two fits ran;
  two were explicit unstarted wall-cap records. The maximum actual fit time
  was `117.453` seconds, below the unchanged 120-second per-fit limit.
- Full archive verification passed every fit replay and archive check. The
  sole JUnit failure is the deliberate total-wall assertion. JUnit SHA-256
  `f657d5230bd18700ed4abe7be3d5209dea8d9ff69d6552f5bde211cd9a56bbd5`;
  one test, one failure, zero errors/skips, 2015.452 seconds including replay.
  The original24 test previously invoked the same native replay directly and
  again through `workflow.verify_calibration`; it now performs that exact
  validation once and records per-fit replay times. The removed duplicate
  replay did not change acceptance semantics.
- A cProfile of fit0's independent replay took 74.218 seconds under profiler
  overhead. `_Intervals.matrix` accounted for 58.808 seconds, including
  `_decimal_matrix` at 48.687 seconds; Decimal dot products dominated. This
  points to precision conversion/allocation as a replay cost, but does not
  establish that optimizing it would make the solver scientifically eligible.

This focused result justifies retaining the bounded arithmetic-path change
for further validation. It does not close R-008, establish a family-level
runtime improvement, or authorize deployment. In particular, all candidates
remain ineligible and the 0.313-second total overrun remains a real gate
failure; the other 23 family/condition pairs and complete M02 acceptance are
still open.

## Focused verification after evidence correction

With the current precision path and workflow deadline regression, the focused command
`python -m pytest tests/numerics/test_gravity_l2_precision.py tests/numerics/test_physical_original_terminal.py tests/numerics/test_gravity_irls_original_workflow.py -q`
completed with exit code 0: 122 passed, 0 failed/errors/skipped, 470.196 seconds. The JUnit is retained outside the checkout at
`E:\_Datos\CAOS_Geophysics\validation\focus-precision-irlstime-20261031\junit.xml`, SHA-256 `c3ff8c82b73ade0adac64d45e8d6debbdddf601e47d0f05c61af7b5d56df1fad`.
Scoped Ruff and `git diff --check` also passed. The source hashes at this check are:

| File | SHA-256 |
| --- | --- |
| `data-pipeline/gravity_l2_precision.py` | `9b841bfb11c61ed9663886cd5ab9d3a878f95738ce56b8f103d2be36eeaa4f80` |
| `tests/numerics/test_gravity_irls_original_workflow.py` | `c0e05eb25ab89d1ed3c9bd522a51cdab35eeaf5116cb52b3db0b51fdf6bb1c4a` |
| `tests/numerics/test_gravity_irls_original_matrix.py` | `df00b8ca772023a8b9a1483f6aa318ba5f3f97e20c1f5e807205bcbe535c5fab` |

This focused pass does not change the full original24 failure or qualify deployment.

## Failed-fold root-correction branch diagnosis

A read-only decode of the source-bound original24 archive identifies why the first candidate's later folds receive no safeguarded root corrections. Candidate 0, fold 1 (fit index 1) is a 48-parameter partition. At its first recorded correction opportunity, the maximum deviation from the reference is exactly 1.5 g/cc and has 16 tied coordinates; every tied coordinate is at one of the supplied lower/upper density bounds. Sixteen total model coordinates are active. The tie set and active face remain identical over the first correction opportunities, and all 21 stage attempts are recorded as `disabled_tied_max`; the fit reaches `irls_iteration_cap` after 20 weight updates.

The ordinary differentiable rank-one correction in `gravity_irls_corrected.py` is valid only for a unique interior maximizer. Choosing an arbitrary tied coordinate would not represent a derivative of the max normalization, while averaging tied gradients without restricting to the active box face would ignore the bound-constrained KKT system. A scientifically valid continuation therefore needs a generalized derivative for the max scale combined with the active-set/complementarity equations, plus an independent replay of both the derivative and accepted steps. The current archive supplies a reproducible failing case; it does not establish that such a method converges or fits the unchanged compute cap.

This explains the disabled correction in this fold, not every failure mode: other attempted fits enter the unique-interior branch and still hit iteration caps or a merit-line-search failure. Anderson acceleration references reviewed for IRL1 and FWI do not prove convergence for this scaled, box-constrained SimPEG IRLS recurrence. No acceleration or convergence claim is adopted from those adjacent methods.

## Research references reviewed for the blocked branch

- Qi, L. and Sun, J. (1993), “A nonsmooth version of Newton's method,” *Mathematical Programming* 58, 353–367, DOI: <https://doi.org/10.1007/BF01581275>. Generalized-Jacobian Newton methods need problem-specific semismoothness and regularity conditions; this paper does not establish those conditions for this inversion.
- Li, K. (2024), “Anderson acceleration for iteratively reweighted l1 algorithm,” <https://arxiv.org/abs/2403.07271>. The method analyzes a specified nonconvex IRL1 model; its theorem is not a convergence theorem for SimPEG's scaled, box-constrained IRLS recurrence.
- Yang et al. (2020), “Anderson Acceleration for Seismic Inversion,” <https://arxiv.org/abs/2008.11778>. This accelerates a steepest-descent fixed-point form for FWI/LSRTM; it is not the present gravity sparse-regularization map.
- SimPEG 0.25.2 sparse regularization implementation: <https://github.com/simpeg/simpeg/blob/v0.25.2/simpeg/regularization/sparse.py>. The local source-pinned derivation remains authoritative for this product's exact scaling and weights.

These sources motivate investigation only. The method-specific active-bound generalized equation, global safeguard, independent numerical oracle and original held-out calibration are not yet implemented or validated.


The separate post-cap continuation study is recorded in [floor-continuation research](floor-continuation-research-2026-10-31.md). It preserves the original 20-update policy boundary and aggregate-time failure; its continued folds are research-only and do not alter this calibration result.
