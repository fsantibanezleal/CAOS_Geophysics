# M12 local validation convergence

Date: 2026-09-28. Source: the [bounded M12 feature design](design.md). This is a branch-local scientific result. No product release, canonical data bake, PR, merge or deployment is implied.

| Gate | Result | Evidence and boundary |
| --- | --- | --- |
| VEL-01 partition | pass | 800 train, 160 validation, 160 independent ID, 80 family-only, 80 acquisition-only and 160 joint test. Whole realization IDs/seeds and the joint geology families are disjoint; layout C has no source or receiver coordinate in A/B. Every manifest is hashed in the receipt. |
| VEL-02 independent oracle | pass within stated physics | Cell-length and fine-quadrature bilinear-slowness operators each match homogeneous geometric travel time within `1e-10` s; heterogeneous responses differ. Both are straight-ray approximations, not measured or refracted arrivals. |
| VEL-03 actual training/checkpoint | pass as execution, fail as useful inversion | Torch 2.14.0 CPU, 40 epochs, selected epoch 39 by validation model RMSE. Reloaded checkpoint SHA-256 `a06a29fc9b64e1797d9b96db10053097816256fa32b578ceb19c301b19b5a99d`; code SHA-256 `2b9ed95d3ba7b1b0f9f80167fa610640dc75c8a142dafb9f7f09791b96a1fd44`. The retained [checkpoint and full receipt](../../../../models/experimental/m12-velocity-cpu-20260928/README.md) verify independently. |
| VEL-04 matched comparator | pass | Identical noisy picks and ray geometry; validation-only regularization grid 1, 10, 100, 1000 selected 100. No locked test selected the classical parameter. |
| VEL-05 per-group and forward evidence | pass as measurement | Mean per-case map/oracle RMSE on joint 160: learned 536.9893 m/s and 28.6056 ms; classical 95.6235 m/s and 2.3387 ms. Every case remains in per-record tables. Validation's 95th-percentile forward threshold is 34.2220 ms. |
| VEL-06 held-out learned advantage and OOD | fail | Joint learned/classical ratios are about 5.616 for map RMSE and 12.231 for oracle-data RMSE. Forward residual flags 43/160 joint OOD and misses 117/160; it flags 5/160 independent ID. This is not calibrated field OOD detection. |
| VEL-07 local pipeline and GPU | CPU pass; CUDA pending coordination | Full local command, checkpoint reload, complete recomputation and seven named tests pass. CUDA training was not launched while M13 may use the shared GPU. No canonical/public artifacts were changed. |

The [full method and scientific limitations](../../../problem-types/04_learned-velocity-validation.md) explain why the failure cannot be repaired by relabelling the old gravity CNN or reporting a good synthetic forward fit as field geology. The current branch offers a reproducible negative control and a complete validation protocol. M12 remains **not accepted** as a learned seismic inverse until a new, predeclared training protocol passes new untouched holdouts and the remaining product gates. The existing experimental checkpoint is deliberately marked failed.
