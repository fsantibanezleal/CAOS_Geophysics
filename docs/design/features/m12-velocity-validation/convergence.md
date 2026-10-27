# M12 local validation convergence

Date: 2026-09-28. Source: the [bounded M12 feature design](design.md). This is a branch-local scientific result. No product release, canonical data bake, PR, merge or deployment is implied.

| Gate | Result | Evidence and boundary |
| --- | --- | --- |
| VEL-01 partition | pass | 800 train, 160 validation, 160 independent ID, 80 family-only, 80 acquisition-only and 160 joint test. Whole realization IDs/seeds and the joint geology families are disjoint; layout C has no source or receiver coordinate in A/B. Every manifest is hashed in the receipt. |
| VEL-02 independent oracle | pass within stated physics | Cell-length and fine-quadrature bilinear-slowness operators each match homogeneous geometric travel time within `1e-10` s; heterogeneous responses differ. Both are straight-ray approximations, not measured or refracted arrivals. |
| VEL-03 actual training/checkpoint | pass as execution, fail as useful inversion | Torch 2.14.0 CPU, 40 epochs, selected epoch 39 by validation model RMSE. Reloaded checkpoint SHA-256 `a06a29fc9b64e1797d9b96db10053097816256fa32b578ceb19c301b19b5a99d`; code SHA-256 `2b9ed95d3ba7b1b0f9f80167fa610640dc75c8a142dafb9f7f09791b96a1fd44`. The retained [checkpoint and full receipt](../../../../models/experimental/m12-velocity-cpu-20260928/README.md) verify independently. |
| VEL-04 matched comparator | pass | Identical noisy picks and ray geometry; validation-only regularization grid 1, 10, 100, 1000 selected 100. No locked test selected the classical parameter. |
| VEL-05 per-group and forward evidence | pass as measurement | Mean per-case map/oracle RMSE on joint 160: learned 536.9893 m/s and 28.6056 ms; classical 95.6235 m/s and 2.3387 ms. Every case remains in per-record tables. Validation's 95th-percentile forward threshold is 34.2220 ms. |
| VEL-06 held-out learned advantage and OOD | fail | Joint learned/classical ratios are 5.61566 for map RMSE and 12.23116 for oracle-data RMSE. Forward residual flags 43/160 joint OOD and misses 117/160; it flags 5/160 independent ID. All 80 fault-family cases are unflagged despite 494.93 versus 50.78 m/s learned/classical model RMSE; salt contributes 43 flags among 80. This is not calibrated field OOD detection. |
| VEL-07 local pipeline and GPU | CPU pass; CUDA pending coordination | Full local command, checkpoint reload, complete recomputation and seven named tests pass. CUDA training was not launched while M13 may use the shared GPU. No canonical/public artifacts were changed. |

The [full method and scientific limitations](../../../problem-types/04_learned-velocity-validation.md) explain why the failure cannot be repaired by relabelling the old gravity CNN or reporting a good synthetic forward fit as field geology. The current branch offers a reproducible negative control and a complete validation protocol. M12 remains **not accepted** as a learned seismic inverse until a new, predeclared training protocol passes new untouched holdouts and the remaining product gates. The existing experimental checkpoint is deliberately marked failed.

## Fresh predeclared residual-v3.1 CUDA run: 2026-10-27

The frozen [residual-v3.1 protocol](residual-v3-protocol.md) was executed
without changing its split, seed, loss, optimizer, or locked test cohorts. The
RTX 4070 Laptop run selected epoch 100, completed in 44.98 s, and passed the
declared CPU/CUDA inference parity envelope. Its six method-specific
regressions pass. The full receipt and checkpoint remain outside the checkout
at `E:\_worktrees\CAOS_Geophysics-data\experiments\m12-residual-v3-20261027`;
the receipt SHA-256 is
`6633a816d55c745abe0c529d73074986b8fbcae383691f95b2df1fd0d0cf5239`, and the
checkpoint SHA-256 is
`0f7a8fc43a078ab4cb16016774d44b356ccb70d9c60e0f197506fd3f7a53ea03`.

The independent `--verify` replay regenerated all five non-training cohorts
from the same frozen manifests and reproduced the saved metrics. On all 160
joint family-plus-acquisition holdouts, learned/classical velocity RMSE is
`100.5909 / 96.3807 m/s` (ratio `1.04368`); independent-oracle travel-time
RMSE is `3.26844 / 2.34113 ms` (ratio `1.39609`). Both ratios must be below
one under the frozen gate. The training/validation improvement therefore
does not pass M12: the saved verdict is `failed-held-out-comparator` and R-008
remains failed. No public or canonical artifact was changed, and no test
cohort was used for tuning after this evaluation.

## Local app evidence inspection: 2026-10-27

The Benchmark page now admits the exact `receipt.json`,
`local-evidence-manifest.json`, and `m12-residual-v3.1.npz` files for this
protocol. Browser-side SHA-256 and byte-length checks bind the selected
receipt/checkpoint to the manifest and check the checkpoint hash recorded in
the receipt. The page displays the training/validation curve and each scored
cohort ratio while retaining `failed-held-out-comparator`. It reads files
locally and does not upload, rerun the solver, or treat checksums as proof of
authorship. Five focused unit tests, the production TypeScript/Vite build, and
one Playwright interaction using the actual external 2026-10-27 receipt and
checkpoint pass. This is a result-inspection feature, not new scientific
acceptance or release acceptance.
