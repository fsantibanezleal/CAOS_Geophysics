# Local submitted gravity calibration, evaluation and replay

The ordinary local workflow performs actual pinned Geoana/SimPEG weighted
bounded L2 or Sparse-smallness IRLS fits on supplied survey geometry. It retains
all eight beta candidates and all three buffered spatial folds, excludes failed
candidates, and runs a selected development-only refit once. Outer observations
are a separate immutable evaluation input. Classical learned training is
not-applicable; regularization selection is real calibration, not training.

This is not the legacy five-column CSV API, public upload activation, a field
admission service, or a completed gravity product. The existing non-null IRLS
positive convergence gate remains failed under the fixed log17/floor3 policy.
Null workflow tests check orchestration; they are not a substitute for that gate.

The [integration manifest](../data-contract/03_gravity-survey-native-integration.md)
lists exact native exports and the proposed owner API/isolated UI mounting
contract. Protected profiles, queued M08 and other methods remain in the existing
controller registry. A solver export, handbook or replayable failure is not an
implemented or accepted user-data UI. The graph/course contract needs review,
actual native producer tests, owner isolation and rendered EN/ES/theme gates.

The original positive's [finite outer-recurrence cause](../design/features/m02-survey-l2/irls-positive-cause.md)
is distinct from the low-beta initialization's
[actual projected Armijo search-scale cause](../design/features/m02-survey-l2/armijo-scale-cause.md).
Their controls and literal failures remain unchanged; the feasible-scaling
research proposal also fails at the original200-step cap.

## Other-data preparation

The source/M01 controller must first establish original byte hashes, citation,
rights, processed-anomaly/reference meaning, transformations, metre coordinate
frame, vertical datum and credible declared errors. Neither `source_kind=field`
nor a hash waives these requirements. Uncorrected absolute gravity, ambiguous
FAA/CBA, duplicated correction, geographic degrees as metres, inferred heights,
missing errors, unknown geometry and ambiguous repeats are rejected. Bartlett
remains modelling-ineligible; its existing negative is not replaced.

Build the exact native [planning and calibration contract](../design/features/m02-survey-l2/contract.md)
from the admitted normalized derivative. Call `plan_gravity_l2` on geometry
only. Its `development_rows`, `outer_rows`, buffered folds and original station
order are frozen before supplying values. Only development values enter the
seven-key calibration request. Exact NumPy native float64/int64/bool arrays and
closed dictionaries/tuples are required; no prepared kernel, callback or engine
object is accepted. `archive_bytes`/`publish_archive` transport that native
request losslessly. They do not correct or adjudicate raw measurements.

The adapter archives normalized numerical declarations only, not private raw
provider bytes. Original custody and permission to share even normalized
derivatives remain the source owner's responsibility. Keep raw and derived
materials below separate authorized external device roots. A normalized bundle
is not permission to upload or mirror it publicly.

L2 schema is `gravity-survey-l2-calibration-request-1`, runtime epoch
`m02-survey-l2-cpu-5`. IRLS uses `gravity-survey-irls-calibration-request-1`,
epoch `m02-survey-irls-cpu-1`, and the complete
[fixed IRLS recipe](../design/features/m02-survey-l2/irls-stagebook.md).
The exact beta grid is 0.0001,0.001,0.01,0.1,1,10,100,1000. Do not alter it after
opening outer values, warm-start another candidate or substitute a failed refit.

## External-only commands

Resolve device storage through the management workspace resolver. Set
`GEOPHYSICS_LOCAL_DATA_ROOT` and `GEOPHYSICS_LOCAL_TEMP_ROOT` to approved absolute
external directories, or pass `--data-root` and `--temp-root` on each command.
There is no repository fallback. Repository and symlink/reparse ancestors are
refused. Temporary and destination roots must share a volume for atomic
no-replace publication; an existing destination is never overwritten. Set
`PYTHONDONTWRITEBYTECODE=1` and OPENBLAS_NUM_THREADS/OMP_NUM_THREADS/
MKL_NUM_THREADS to1 before starting the approved pinned Python runtime.

```text
python scripts/run_gravity_survey.py calibrate --input survey.gza --output calibration.gza
python scripts/verify_gravity_survey.py --input calibration.gza
python scripts/run_gravity_survey.py evaluate --input outer.gza --output evaluation.gza
python scripts/verify_gravity_survey.py --input evaluation.gza
python scripts/run_gravity_survey.py refit --input calibration.gza --output noise-refits.gza
python scripts/verify_gravity_survey.py --input noise-refits.gza --calibration calibration.gza
```

Input/output names are flat `.gza` names under the data root. The format is
stored-only ZIP with a closed tagged native manifest and SHA256-bound arrays,
not pickle, a caller-selected code import or an extracted archive. Re-import
checks the entire directory/member/EOF layout, CRCs, byte/type/shape/hash bindings
and unchanged native caps before returning an object. `verify` additionally
rebuilds every objective/stage, KKT/history, weights/operators, physical
predictions/residuals, marginal scores and fixed selection against the original
calibration request. Rehashing a tampered result is insufficient to pass.

Evaluation input schema is `gravity-survey-l2-evaluation-request-2` for the
local L2 adapter or `gravity-survey-irls-evaluation-request-3`. Both contain
frozen_calibration, calibration_request, observations and noise in addition to
schema. The outer arrays must exactly match frozen outer rows and have their
own value/noise digests. Verification never invokes an optimizer. Do not add
outer values to the calibration request or use the evaluation to choose a mesh,
prior, beta, iteration or method.

Unsuccessful calibration is still exported with complete literal failures;
`calibrate` returns exit2. `verify` can pass structural/native replay of that
failure archive; this does not promote it to convergence. `evaluate` and
`refit` reject an unsuccessful frozen selection. Refits return exit2 if any of
the32 actual fits fail, retaining all records. Other transport/science errors
fail without publishing a result. Empty or invalid sources never become a
successful model merely because the CLI ran.

## Physics, limits and interpretation

The upward-positive engine uses q=rho/1000 in g/cc and mGal predictions;
exported density contrast is kg/m3. Positive density below a receiver has
negative upward acceleration. Fixed source-bound background is added once;
residuals are observed-minus-predicted. Official misfit is the unhalved
`phi_d=||W(Gq+b-d)||^2`, WRMS=sqrt(phi_d/n). Each fit independently whitens
its own principal covariance block. Cross-partition dependence is disclosed,
not erased by spatial blocking. Total fixed-stage objective is
`phi_d+n_fit*beta_candidate*phi_m`; the beta normalization is literal.

IRLS is norms[1,2,2,2], sparse smallness and L2 derivatives, not TV. Actual
fixed-stage weights/epsilon/metrics are exported. Different stages are different
quadratics; a weight transition is not an accepted optimizer step. Overall
success requires the unchanged three final model-and-weight fixed-point changes,
not just inner quadratic convergence or a saturated epsilon floor.

The ordinary supported envelope is2048stations,4096activecells,64MiB G,
32MiB covariance, projected2GiB workspace,96MiB request arrays and256MiB result
arrays,256KiB native metadata,32768scalars and depth8. Each fit retains at most
200 accepted steps, original CG/line-search caps and120s; calibration and the
separate optional refit job each have1800s deadlines. Native calls are
cooperatively bounded, not claimed hard-preemptible. Observed RSS/resource
controls do not establish a general allocation upper proof or host admission.

Noise refits use exactly32 development-only perturbed-data fits at frozen
hyperparameters, original starts and fixed seed20261008/NumPy2.2.6 PCG64.
They retain failures and all actual targets. This distribution conditions on
declared Gaussian noise and fixed geometry/background/prior. No posterior,
calibrated confidence interval, field truth or unique geological density is
reported. Mesh/padding/topographic/error alternatives, original48/96 broad
controls, eligible measured field evidence, independent native/platform review,
public job/UI/course and actual-host acceptance remain separate gates.
