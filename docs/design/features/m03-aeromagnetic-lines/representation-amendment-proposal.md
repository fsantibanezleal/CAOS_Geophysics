# Proposed independently sealed representation study

This is a supported scientific amendment **proposal**, not an implementation,
replacement of original S1 or authorization to change its candidates/thresholds.
It follows the [calibration-support diagnosis](calibration-support-diagnosis.md)
and the retained original S1 predictive failure.

## What is established

Independent augmented QR reproduces the original selected model predictions.
The numerical final training-column-space projection RMSE is
3.5608746056014646nT; its selected damped fit training RMSE is
3.5608761126551283nT. Thus the selected66-source basis has substantial numerical
training representation error even without a damping penalty. This is not a
proof that every equivalent-source basis is inadequate, nor that arbitrary
outer predictions are mathematically impossible. No outer observation selects
a new depth/damping/source representation here.

The original outer RMSE18.799740861734186nT remains above its unchanged
0.25966396538773057nT target. Hull/distance support is1, and outer nearest
training XY370.91..387.45m is not worse than inner A421.09..447.27m or
B340.82..447.52m. Geometric interpolation coverage therefore does not explain
away the failure as a simple outer extrapolation. Source/QR agreement is not
predictive acceptance; the separate coefficient diagnostic discrepancy is
retained, not asserted to pass.

[Official Harmonica block-averaging guidance](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.EquivalentSources.html)
recommends source blocks no larger than the desired grid resolution. Original
400m blocks are eight times the50m output spacing. Geometry-only occupied-block
counts below were computed from the original magnetic-null geometry/partitions,
before any new magnetic truth, model fit or test opening:

| Block width m | Outer training | Inner A | Inner B | Inner C |
| --- | ---: | ---: | ---: | ---: |
| 400 | 66 | 45 | 48 | 57 |
| 200 | 148 | 91 | 101 | 127 |
| 100 | 240 | 137 | 164 | 203 |
| 50 | 292 | 168 | 193 | 247 |

These are geometry/representation counts, not new scores. Fine50m blocks
cannot fit the existing256-source cap in the final training scope. Quietly
coarsening the requested grid or source blocks is not a scientifically honest
repair. Any changed cap needs complete preallocation/resource proof; the
existing bounded method/native admission remains unchanged and CLOSED.

## Prospective untouched definition, not generated or evaluated

Retain original S1 and all its exact5% assertions permanently. A distinct
authored acquisition revision would use the same11-line/363-row ordinal,
height/clock, outerF04, inner A/B/C, anchor, closed470m support/buffer and
50m grid/120m and220m plane definitions. Change ONLY the bounded geometry
jitter hash prefix to ASCII `m03-refinement/20261004/`, followed by row ID and
axis, with the original modulo/100 and exact-zero endpoints. Before generating
any magnetic values, persist and verify its new magnetic-null geometry manifest,
all partitions, source membership, coverage and prospective resource counts.
Its original bytes/revision are distinct from original S1; no existing
measurement is rewritten.

Use a separately authored direct SI dipole control, not the fitted1/r operator:
positions(-350,180,-350),(510,-420,-450),(-850,-610,-280)m and moments
(1.2e7,-0.9e7,2.1e7),(-1.6e7,1.1e7,0.6e7),(0.8e7,1.4e7,-1.3e7)A*m^2.
Project onto the explicitly authored constant reference F48000nT,
D=-17degrees east, I=42degrees down. This defines synthetic physics, never
field observations, datum or uncertainty.

The prospective representation study has two separately identified requests:
100m and50m half-open blocks, keeping original200/500m depths, all four
dampings0.0001/0.01/1/100 and tie rule unchanged. Neither new request chooses
block width using an outer result; publish both outcomes. The50m request
proposes a320-source ceiling solely for this local study after geometry-only
count verification, not an online/full-survey admission. No other cap changes.
All retained observations remain training data; no thinning or enlarged blocks
to escape the bound. Maximum source count, whole request byte/array/CPU/RSS/
wall/scratch/result measurements and cancellation remain explicit prerequisites;
failure must refuse the study rather than substitute a reduced computation.

Seal each inner-only candidate selection before one outer evaluation. Retain
the same5% signal-RMS/1e-6nT floor and all original oracle/tolerance conditions
on this new control, with no new sigma. A failed new control stays failed.
The two representations' geometric coverage, fit conditions, training residuals
and outer scores are separate evidence, not a new winning-parameter search.
No claim of statistical field generalization follows from known synthetic
physics. No promise either representation will meet the target is made.

This study does not repair the independent empty-crossover problem in fold A.
Training-leveling stays ineligible under that seal; its independent graph/offset
control must remain distinct or acquire its own prospectively reviewed adequate
calibration geometry. No untouched heldout label can be restored to the
already opened original S1/S2 by reprocessing them.

## Scientific boundaries

No existing schema/cap, source-block policy, frozen source/candidate values,
original arrays, physics gate or native dispatch is changed by this document.
New geometry/truth generation and source-cap code changes require review of
this exact definition before execution. Independently evaluated IGRF,
rights/physical metadata and genuine complete offline field evidence remain
required; a successful synthetic study would not close full M03.

## 2026-10-08 claim correction and continuation

The predecessor wording "exact ... lower bound" was too strong for an ordinary
floating-point SVD with a numerical rank cutoff. It is corrected transparently:
this is not an interval-certified lower bound, an outer-error bound or proof of
universal1/r inadequacy. Historical predictive failures and receipts are unchanged.
The [corrective workflow packet](../m03-corrective-workflow/design.md) proposes
independent unit/distance/source/constant diagnosis, legitimate train-only
resolution selection and the still-required real owner scientific workflow.
That packet is a proposal, not a claim of review, implementation or new PASS.
