# FWI deterministic replay and L-BFGS line-search audit

Started: 2026-09-28; export replay verified: 2026-10-03.
Status: isolated solver candidate. The committed 0.04.001
artifacts still have the previous solver fingerprint. No release or deployment
is implied by a passing local inverse.

## Reproduced failure and mechanism

The fixed FWI_FAULT synthetic observations and truth were byte-identical across
fresh local runs, but default CUDA L-BFGS optimization gave materially different
final models. Two independent runs with deterministic PyTorch algorithms and
cuDNN settings produced identical model hashes. Under that policy the original
FWI_LAYERED multiscale result was unresolved: active/withheld WRMS
2.607551/2.656599 versus 1.203248/1.235152 in the committed 0.04.001
reference artifact. The old artifact and a fresh solve are different numerical
evidence, even though they use the same seed and synthetic observations.
The old deterministic FWI_FAULT full-band and multiscale WRMS were
2.271/2.361 (unresolved) and 1.746/1.832 (recovered), respectively.

The underlying optimizer configured PyTorch `LBFGS(max_iter=1,
line_search_fn="strong_wolfe")` without an explicit `max_eval`. In the installed
PyTorch 2.14.0 implementation, the default `max_eval=max_iter*5//4` is one.
One closure evaluates the entry state, leaving `max_ls=max_eval-current_evals=0`
for the Wolfe search. Its first trial is still evaluated, but the bracketing and
zoom loops cannot search further. The previous metadata therefore overstated
the effective line search. See the [versioned PyTorch L-BFGS source](https://github.com/pytorch/pytorch/blob/v2.14.0/torch/optim/lbfgs.py)
and its [optimizer API](https://docs.pytorch.org/docs/stable/optim.html).

An instrumented old-solver layered run made 56 closures for each 28-call
spatial stage. In the multiscale final stage, the first zero parameter step
occurred at call 5; the last trial-closure gradient infinity norm was
0.00082985. That gradient may belong to a rejected trial, so it is not a
stationarity certificate for the accepted state. Doubling all stage-call budgets from
28 to 56 under a 3/8/14 Hz then full-band diagnostic schedule yielded the
exact same final model hash and WRMS as its 28-call counterpart. This was not
evidence that the old solver had converged.

## Controlled comparisons

These are fresh deterministic local CUDA probes on the RTX 4070 Laptop GPU,
Torch 2.14.0+cu126 and Deepwave 0.0.27. Every layered probe used the same
observation SHA-256
`557eb556c372b515a595e614a0a16fc2b1115c78cc5a16b46c8f4a6c568666bb`,
independent start, truth, receiver mask, regularization and spatial grids.
The schedule diagnostics changed only the stated cutoff or call budget; their
failure statuses remain part of the evidence.

| Solver and continuation cutoffs, Hz | Calls/stage | Layered active/withheld WRMS | Whole-model RMSE ratio | Verdict |
| --- | ---: | ---: | ---: | --- |
| Old line search, 3/5/8/14 | 28 | 2.607551 / 2.656599 | 0.538562 | unresolved |
| Old line search, 3/5/8/full band | 28 | 2.547264 / 2.595769 | 0.537624 | unresolved |
| Old line search, 3/8/14/full band | 28 | 2.072258 / 2.128845 | 0.564217 | unresolved |
| Old line search, 3/8/14/full band | 56 | 2.072258 / 2.128845 | 0.564217 | unresolved; same model hash as 28 |
| Corrected line search, original 3/5/8/14 | 28 | 1.207786 / 1.233036 | 0.526925 | recovered |

The correction explicitly sets `max_eval=25` while retaining at most one
L-BFGS update per call, 28 calls per stage, the original frequency schedule,
survey, wavelet, seed, bounds, beta, masks and WRMS <= 2 criterion. The corrected
multiscale final stage made 61 closures over 28 calls and still accepted a
parameter step at the final call. Two independent fresh corrected runs yielded
the same layered full-band and multiscale model hashes and metrics. The
multiscale hash was
`914f1b4035af31f869e3d351009aac88d0e363dec682063dfcde3168cf63cd9e`.

The corrected FWI_FAULT reference also improved without changing its source
geometry or noise: full-band WRMS 1.370423/1.418753 with whole-model RMSE
ratio 0.700736, multiscale WRMS 1.340011/1.387508 with ratio 0.653272.
Both meet the existing recovered criterion. The test expectation for full-band
fault changes from unresolved to recovered; the criterion itself does not.

## Candidate export failure and correction

The first isolated 24-condition bake completed in 2434.97 s with peak monitored
GPU memory 4,578,082,816 bytes. Its CUDA export replay failed immediately on
FWI_LAYERED/reference/fwi-l2: 13,744 of 48,000 decimated prediction samples
exceeded the existing `rtol=2e-5, atol=2e-5` comparison, with maximum absolute
violation 0.00023426. Repeating replay with deterministic CUDA flags did not
change the mismatch. The batch writer called `rebuild.save` at its seven-digit
default despite the FWI result declaring ten significant digits. This rounded
float32 velocities and changed the propagated waveform. No tolerance or model
value was adjusted to make the failed candidate pass.
Comparing the two serialized layered reference models after both were generated
shows that seven-digit rounding changes 9,524 of 12,288 full-band float32
velocity cells and 9,692 of 12,288 multiscale cells, with a maximum cell
difference of 0.00048828125 m/s. The small velocity perturbation is enough to
cross the existing waveform replay tolerance in this finite-difference solve.

The batch writer now passes the result's declared ten-digit precision to the
serializer. A float32 round-trip test covers that call path. The candidate
writer's own SHA-256 is recorded in the plan and each result, so resume cannot
accept files written by the earlier seven-digit version. The failed candidate
is retained locally under the ignored `data/experiments/fwi-candidate`; a fresh
candidate uses `data/experiments/fwi-candidate-precision10`.

The second bake completed all 24 conditions in 2489.061 s with peak monitored
GPU memory 4,870,635,520 bytes and no memory-guard events. On 2026-10-03 all
48 final-model CUDA replays passed: observed and predicted gathers at the
unchanged `rtol=2e-5, atol=2e-5`, residuals at `rtol=2e-4, atol=2e-5`,
recomputed metrics, final history and independently recomputed verdicts.
The candidate source and writer hashes match the frozen plan. The compact
[comparison receipt](../../../validation/fwi-lbfgs-regression-2026-09-28.json)
records the failed first bake, rejected schedule trials, repeat hashes, and
second plan/ledger/replay hashes. The full local receipts and candidates remain
ignored, rather than replacing the committed catalogue.

| Synthetic geometry, both methods across six variants | Recovered | Unresolved | Failed | Negative control |
| --- | ---: | ---: | ---: | ---: |
| Layered | 10 | 0 | 2 | 0 |
| Fault | 10 | 0 | 2 | 0 |
| Gas channel (`FWI_NOISY`) | 4 | 6 | 2 | 0 |
| Salt (`FWI_CYCLE_SKIP`) | 0 | 0 | 0 | 12 |

Strong regularization fails in all three non-salt geometries; its whole-model
RMSE worsens the independent start. The gas-channel reference remains unresolved
at full-band WRMS 2.765/2.904 and multiscale 2.071/2.213. Salt reference
multiscale WRMS is 1.751/1.966, yet deep-model RMSE worsens from 702.62 to
765.06 m/s. Salt's coverage variant also violates the withheld WRMS criterion.
These are retained negatives, not exceptions to a success threshold. In the
layered reference, multiscale deep-model RMSE improves from 295.50 to 163.16 m/s
but remains materially nonzero despite a noise-compatible waveform fit.

## Audited physical and inverse contract

The scalar forward solves constant-density acoustic propagation on a
`[distance,depth]` mesh; exported models transpose to `[depth,distance]`.
Velocity is m/s and spacing is m, whereas pressure/source amplitude retains
Deepwave's arbitrary point-source convention (not calibrated physical Pa).
Sources are at x = 300, 800, 1275 m and z = 75 m. Receivers span 75 to 1500 m
at the same depth, with grid-snapped integer coordinates; the coverage variant
uses 20 rather than 40 receivers. The 300 m PML, fourth-order spatial stencil,
fixed 4600 m/s stability bound, 0.5 ms internal sampling and 3200-sample record
are unchanged. Deepwave handles its internal stability substepping. Exported
traces are every eighth sample (4 ms), never the rate used for inversion.

The known Ricker source has peak time `1.5/frequency`, ordinarily 8 Hz,
5 Hz for the acquisition variant and 9 Hz for salt. This is a prescribed
synthetic wavelet, not a field-wavelet estimate. Predicted and observed traces
use the same zero-padded FFT order-six Butterworth amplitude filter per stage.
The fitted objective is the mean squared filtered residual over active
receivers divided by their filtered observed mean energy, plus beta times
mean squared physical velocity gradients scaled by 1000 m/s and 100 m.
It is not WRMS, and changing stages changes this filtered objective; histories
also retain the unfiltered relative MSE for comparison. WRMS divides the
unfiltered residual RMS by the prescribed synthetic Gaussian noise sigma.

Receiver index modulo five equal to two is withheld from every closure and
state selection; changing withheld traces leaves inverse models unchanged in
the leakage regression. The independent start is `1800 + 0.88*z` m/s.
The shared 3 Hz one-dimensional background is followed by equal two-dimensional
logit grids `(9,12)`, `(17,24)`, `(33,48)` with bilinear interpolation and
1400 to 4400 m/s sigmoid bounds. No truth enters the inverse. Beta is 0.001,
or 0.03 for the declared regularization variant. The terminal evaluated state
is selected after 28 calls per stage; no withheld score selects a cutoff,
iteration or regularization. An explicit nominal function-evaluation budget
permits Wolfe searching, but does not certify successful Wolfe conditions on
every call, stationary convergence, unique reconstruction or a fixed total
closure cost. The solver still declares `finite_budget` stopping.

Resolution is limited by the source spectrum, aperture, finite record and
coarse control grids. At 8 Hz, wavelengths at 1800 m/s are about 225 m;
the 12.5 m mesh resolves wave propagation more finely than the inverse can
identify arbitrary geological detail. The available evidence is a directional
derivative and alternate spatial-stencil comparison, not a separate-engine
adjoint proof or a full mesh/time convergence study. No such stronger claim
is inferred from a low waveform residual.

## Reproduction commands

Run locally in the pinned CUDA pipeline environment, with the GPU released
from other scientific workers. These commands write only isolated candidates:

```powershell
python scripts/probe_fwi_fault_determinism.py --case FWI_LAYERED --deterministic --trace-optimizer --output data/raw/fwi-probes/layered-repeat.json
python data-pipeline/seismic_batch.py prepare --output data/experiments/fwi-candidate-precision10 --receipts data/experiments/fwi-batch-receipts-precision10
python data-pipeline/seismic_batch.py run --output data/experiments/fwi-candidate-precision10 --receipts data/experiments/fwi-batch-receipts-precision10 --workers 2 --gpu-released
python scripts/validate_fwi_exports.py --data data/experiments/fwi-candidate-precision10 --report data/experiments/fwi-batch-receipts-precision10/cuda-replay.json
$env:FWI_RECOVERY_ARTIFACTS = (Resolve-Path data/experiments/fwi-candidate-precision10).Path
python -m pytest tests/test_seismic_recovery.py -q
$fwiSolverSuite = git ls-tree -r --name-only f2bb280 tests | Where-Object { $_ -match '/test_[^/]+\.py$' }
python -m pytest @fwiSolverSuite -q -o addopts='' --junitxml=data/experiments/fwi-batch-receipts-precision10/post-develop-solvers-tests.xml
```

Recovery-artifact reuse validates the current generator fingerprint before
replaying the models. Without that environment variable the recovery tests
solve the four references afresh. The earlier full 148-test run did so;
the resumed run additionally tests the actual ten-digit batch writer and
rejects stale writer or declared seven-digit resume files. No test re-bakes
canonical release data, and numerical suites do not run in CI.

## Interpretation and release boundary

The forward and adjoint remain Deepwave constant-density acoustics with the
original physical coordinates, Ricker wavelet, 0.5 ms internal step, 12.5 m
mesh, 1.6 s record, active/withheld receiver split, and final-model replay.
The current directional derivative and alternate-stencil checks remain distinct
from inverse recovery. Limited source/receiver aperture, low-dimensional
controls, fixed known wavelet, same-operator synthetic data and remaining deep
velocity bias limit identifiability. A recovered label means improvement from
the independent start and consistency with declared synthetic noise. It does
not establish exact geology or field performance.

The full 148-test Python suite passed locally after the numerical change.
On 2026-10-03 the expanded suite passed all 149 tests, including the ten-digit
writer regression, using fingerprint-checked candidate references for recovery
replay. The CPU inverse-bookkeeping test checks the explicit optimizer budget
on every stage independently of those candidate files. Separate CUDA tests
check the filtered acoustic directional derivative and fourth/eighth-order
stencil agreement.

The reviewed milestone was persisted as `6f7b718` before merging current
`origin/develop` (`dce92a1`) into this task branch at `cfeddb7`. The merge was
conflict-free and preserved byte-identical solver, geology and candidate writer
hashes, so it did not invalidate the frozen candidate. After integration the
full original solver/data test-file set passed 150 tests (an upstream source
test adds one), and the deterministic-policy assertion additionally checks
warn-only restoration. Repository-wide Ruff, content and CI-budget guards
pass. The expanded `python -m pytest tests` cannot collect API tests in the
pipeline environment: `ModuleNotFoundError: No module named 'alembic'`.
The failed collection XML is retained alongside the passing scoped XML under
`data/experiments/fwi-batch-receipts-precision10`. It is not a passing whole-product
validation or a reason to modify the API or phase environments in this task.

`scripts/check_artifacts.py` fails with `Stale scientific source/settings` against
the unchanged committed 0.04.001 artifacts, as expected from the new solver
fingerprint. The isolated 24-condition FWI candidate bake and CUDA export
replay are separate release gates; old artifacts must not be relabeled or
silently reused. The candidate is not a release and must not be merged into
the published catalogue without a deliberate complete re-bake and review.
