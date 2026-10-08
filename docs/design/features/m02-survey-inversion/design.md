# M02 local submitted-survey forward and inverse design

Status: planned, 2026-10-03. Review pending; no scientific implementation,
training, bake, environment change, API/UI work or full-field admission performed.
Base `66952f32b6ce86d5a752cf56d3e4ca8481c8b4da` includes the merged FWI/parity
work; immutable scientific snapshot is in the [research receipt](../../../research/m02-survey-inversion-evidence-2026-10-03.json).
Requirements: [requirements.md](requirements.md). Acceptance: [validation.md](validation.md).

## Scope and engine decision

Complete target for the next approved code unit: strict local submitted-survey
admission, genuine 3D forward modelling, weighted bounded L2 and IRLS inversion,
blocked calibration, independent outer evaluation, uncertainty/resolution probes,
safe export and independent replay. A thin wrapper around the existing narrow
CSV inverse does not meet this target. Existing potential fixtures remain valid
historical synthetic fixtures; this plan neither replaces them nor changes their
source fingerprints. Public upload/job/browser integration remains main-owned.

Use actual SimPEG 0.25.2 `Simulation3DIntegral(engine="geoana")`, Geoana 0.8.1,
discretize 0.12.0, official data misfit/regularization/inversion classes and
`ProjectedGNCG`, not a custom solver advertised as SimPEG. Use Choclo 0.3.2
direct prism calls as a separate code oracle; never select the Choclo production
engine and then compare it to itself. Add volume integration and far-field
Newtonian controls to reduce shared-formula dependence. Source licences and data
rights are separate. Primary evidence and unavailable reads are [recorded](../../../research/m02-survey-inversion-2026-10-03.md).

CPU-first local execution is the proposed decision, not a speed measurement.
The inspected Geoana inverse uses stored sensitivities; `forward_only` is not a
complete matrix-free inverse path. This engine has no verified CUDA receipt here.
An RTX 4070 being available, or FWI running on it, does not establish GPU gravity
support. Any later GPU adapter needs its own reviewed source, float64/float32
parity, derivatives, resource and replay gates before selection.

## Immutable upload/admission contract

Proposed schema `gravity-survey-inversion-request-1`, strict JSON manifest plus
bound CSV/array assets, never an untyped five-column file alone. Bind SHA256,
byte sizes, column schema, source_kind (`field`, `user_upload`, `synthetic_control`),
citation/rights/redistribution policy, parent dataset and M01 processing hashes.
Separate raw, normalized, fit and exported derivatives. Reject duplicate JSON
keys, nonfinite JSON numbers, unsafe archive paths, arbitrary remote code/URLs,
pickle, unbounded arrays and overwrite. Original private bytes are not public
bundle contents by default; retain hashes, rights and a local replay recipe.
Declare mode `forward`, `l2`, `irls` or `compare`. Pure forward mode requires a
source-bound physical model/geometry but may omit observations/SD with explicit
null uncertainty; it cannot produce fit scores, inversion acceptance or a field
eligibility badge. Inverse/compare mode needs the complete observation/error
contract and feasible evaluation partitions below.

Manifest must contain:

- Unique station IDs, original row order and acquisition/campaign/line groups;
  exact supplied coordinate/value/SD units, axis order and signed component.
- A projected/ENU or explicitly oriented local Cartesian metric frame, origin,
  horizontal reference and vertical datum common to receivers and surface.
  Degrees are not metres. No inference from column labels or approximate EPSG.
  Named transformation, PROJ/grid versions/hashes and stated accuracy where
  conversion is needed; no ballpark or automatic worker grid downloads.
- Measurement meaning: processed disturbance/anomaly, reference/background and
  signed normal-gravity, tide, drift, elevation, plate and terrain history.
  Either replay a valid M01 derivative or admit a separately reviewed provider
  derivation with source-bound method mapping. Reject absolute gravity without
  corrections, ambiguous CBA/FAA semantics, and any double correction. M01
  equivalent-source coefficients are never used as 3D density parameters.
- Receiver geometry, surface/terrain sampling, surface hull, datum, active-cell
  policy, modelling bounds, independently justified density contrast bounds,
  start/reference model, covariance/SD and error provenance.
- Mask flag (`true` means excluded), mandatory reasons and explicit nulls for
  unavailable observations/coordinates. Reject ambiguous duplicate IDs or exact
  positions unless a reviewed repeated-measurement covariance/group policy is
  supplied. A missing value is not zero. Known-geometry excluded stations may
  receive forward predictions, but never fitting scores; unknown geometry yields
  null prediction. Preserve stable engine-sort and inverse row permutations.

Supported factors must be explicit: mGal to m/s2 is 1e-5; microGal to mGal is
1e-3; international foot is 0.3048 m, US survey foot is 1200/3937 m. Incoming
down-positive gravity converts once to upward-positive engine gz. Export physical
density contrast `rho` in kg/m3; engine parameter `q=rho/1000` in g/cc. Convert
bounds, starts, references and Jacobians consistently: `J_rho=J_q/1000`.
Units are part of the model identity, not display-only metadata.

A flat local vertical is an approximation. Quantify projection/vertical/curvature
error against declared observation SD, with proposed admission bound 0.1 SD per
station; otherwise restrict to a smaller frame or reject pending a reviewed
component-rotation model. Geometry uncertainty must be recorded as conditioning
on fixed geometry or supplied perturbations; never silently turn unknown height
errors into zero. CRS/M01 reference adjudication is coordinated with its owner.

Known positive independent Gaussian SD may form diagonal covariance. Full
covariance must be finite symmetric SPD, source-labelled and in squared data
units; verify Cholesky and transformations/masking/permutations. For fit subset f,
use its principal block `C_ff=L_f L_f^T`, `W_f=L_f^-1`. Never whiten a combined
fit/holdout vector or condition fitting values on observed test values. If noise
correlates across partitions, document marginal test scoring and dependence;
spatial blocking is not proof of statistical independence. Conservative M01
error bounds are not Gaussian SD. Unknown SD has no 3% default; an explicitly
assumed experimental error policy is conditional, not full-field eligibility.

## Physical mesh and objective

Physical independent reference, in SI and upward coordinate u:
`g_u(r)=G_N integral_V rho(r') (u'-u) / |r'-r|^3 dV`.
Thus positive density below a receiver yields negative upward acceleration;
convert SI to mGal only at the declared interface. This integral defines the
quadrature/point-mass/sphere oracle, separate from either prism implementation.

TensorMesh cell widths/origin in metres, x-fast linear index
`i + nx*(j + ny*k)`, external volume `[z,y,x]`, explicit active bitmap/indices,
cell centres/bounds/volumes and density mapping. First supported terrain policy
uses node-based cells entirely below the verified surface; reject uncovered
topography before `active_from_xyz` can extend with nearest neighbours. Declare
stair-step approximation and run refinement/padding alternatives. No silent
fractional terrain cells or smoothness bridging disconnected air. Inactive air
has zero *contrast*, not a claim of zero absolute Earth density.

Fixed background `b` is source-bound or explicitly zero under a documented
anomaly convention; never auto-demean, detrend or fit nuisance offsets invisibly.
Let `G_f` be the physical engine sensitivity for fit stations and active q.
Pinned SimPEG's objective is the unhalved sum
`phi_d = ||W_f (G_f q + b_f - d_f)||^2`; displayed WRMS is
`sqrt(phi_d / n_f)`. Export residual `d_obs-d_pred` with that explicit sign.
Gradients include the factor two. Metric normalization is not an optimizer
normalization or an extra beta scaling.

For `r_f=G_f q+b_f-d_f`, check
`gradient_d=2 G_f^T W_f^T W_f r_f` and
`H_d v=2 G_f^T W_f^T W_f G_f v`. In the diagonal-SD case,
`W_f=diag(1/sigma_f)`; matrix whitening must retain the transpose.
Total objective is `phi=phi_d+beta*phi_m`. A declared L2 model term is
`phi_m=alpha_s ||V_s D_s(q-q_ref)||^2 + sum_j alpha_j ||V_j D_j B_j q||^2`,
where V contains square-root physical volume measures, D the declared normalized
depth/sensitivity weights and B metre derivatives (or derivatives of q-q_ref
when explicitly requested). Pin the official discretization/mapping to this
declaration, export alpha/length scales, and verify weighting on a tiny mesh.
Sensitivity weights derive from fitting receivers only; their normalization and
positive floor are frozen during calibration, not retuned with test residuals.

L2 uses official `WeightedLeastSquares`: active physical volume, smallness and
metre derivatives; disclose reference-in-gradient option, length scales and
any depth/sensitivity weighting. Require a positive smallness contribution for
the independent small-problem uniqueness/KKT oracle, without claiming field
identifiability. Signed contrasts are permitted; positivity needs a stated
geological prior, not an unconditional default.

IRLS uses official `Sparse` with norms `[1,2,2,2]`: smoothed sparse smallness,
L2 directional derivatives, not TV. Same admitted inputs and candidate space as
L2, with its retained L2 initialization. Engine weight scaling, reference model,
epsilon floor/cooling and beta transitions are exported exactly. Adopt a positive
unit-aware epsilon floor frozen during calibration and test the null-model case.
At a fixed IRLS state the smallness quadratic weights are proportional to
`((q-q_ref)^2+epsilon_s^2)^(-1/2)` for p=1, with the actual official scaling
also retained. Epsilon_s is in g/cc, not kg/m3 or mGal; derivative-term norms
remain two. Check the state's weighted quadratic, not a falsely fixed sparse
objective across parameter changes. Candidate beta denotes the frozen initial/
schedule recipe; any fit-driven directive updates are part of that recipe and
must use fitting data alone, with actual final beta/epsilon replayed.
Official `UpdateIRLS` can update beta and epsilon; do not add incompatible
BetaSchedule or place UpdatePreconditioner before it. Each fixed quadratic
subproblem has its own verified objective/gradient; changing weights/beta means
the whole history cannot be advertised as descent of one fixed objective.

Use official BaseInvProblem/BaseInversion and bounded ProjectedGNCG. Proposed
limits: 200 optimizer iterations, 20 line-search evaluations per step, inner
CG relative residual 1e-6, fixed-stage normalized projected-gradient 1e-5 and
relative objective change 1e-6 over three accepted states. Map these policies to
the pinned API explicitly before code review; never presume undocumented defaults
or demand a smooth global optimum of IRLS. Exhausted caps return nonconverged.
Save every accepted model and exact terminal model/weights/history identity.
Fit WRMS near one is interpretable only under credible errors, not forced by beta.

## Blocked calibration, evaluation and resolution

Classical methods have learned-training status `not_applicable`; parameter
selection is explicit calibration, not erased from lifecycle evidence. Freeze
mesh geometry, candidate beta/prior/length/epsilon policies, bounds and seeds
before outer values/truth are opened. Depth weighting power 0.375 from the old
synthetic solver is not a universal user-survey constant.

Define spatial blocks/buffers from coordinates and acquisition groups only.
Keep repeats/campaign groups in the same fold. Proposed full inverse minimum:
9 occupied blocks, 40 fit, 10 inner validation and 10 outer test observations,
non-collinear survey coverage; tiny forward/oracle cases are a separate mode.
Reserve 20% of blocks for locked outer test, then 3 buffered inner folds over the
remaining groups. Choose block size/buffer from acquisition/error correlation
support or separately declared development controls, not test performance.
Admit only feasible disjoint splits; do not quietly fall back to random points.
Verde is not installed in the inspected base runtime; use a reviewed deterministic
geometry-only grouping implementation, or separately coordinate a pinned
dependency. Neither option is decided by an implicit environment modification.

Initial reviewed search cap: at most 12 frozen beta/weight/length combinations
per method, all outcomes retained. Inner validation WRMS selects parameters,
with fixed deterministic tie rule; rerun selected recipe on non-test fit data,
then evaluate the unopened test once. IRLS may finish worse than L2 for diffuse
models. Test values must not select method, iteration, alternative mesh or prior.
Poisoning test values and permuting synthetic truth must leave selection and fit
model hashes unchanged. A later all-data refit is a different unvalidated result,
not the same heldout acceptance model.

Export sensitivity diagonal/coverage in declared units, small-problem spectrum
and resolution/nullspace probes. High sensitivity is not density confidence.
Report alternative mesh, padding, bounds, beta and starts without choosing the
most appealing image against test truth. Compare predictions in noise units;
differences above proposed 0.25 SD are reported mesh/model sensitivity, not
rounded away. Demonstrate different depth/density models fitting within the
noise: gravity nonuniqueness remains even when synthetic truth is available.

Optional uncertainty is 32 actual perturbed-data refits at frozen hyperparameters,
covariance/mesh/bounds with recorded seeds and convergence failures. It is a
conditional noise-refit distribution, not a Bayesian posterior or guaranteed
95% geological interval. Geometry, regional background and prior changes are
separate labelled alternatives. Coverage is measured on independent synthetic
controls, never invented for field data. Field density truth stays null.

## Bundle, replay and local limits

Export normalized observations plus originals/rights policy, physical and
whitened residuals, prediction for all eligible geometry, fit/tune/test/mask maps,
3D model mesh/bounds/active cells, alternatives, uncertainty conditioning,
optimizer state/status, config and source/module/environment/engine fingerprints.
Replay from immutable inputs independently checks forward physics and serialized
residual identity, then source/config/hash seams. Replay-only compatibility is
not rewriting producer provenance. No relabelling old solver SHA or modifying
catalogs/fixtures. Use an exclusive ignored output directory, no overwrite,
bounded scratch with scoped cancellation cleanup, no broad deletion.

Proposed first local envelope: one job; <=2,048 stations, <=16,384 active cells;
float64 G <=256 MiB, dense covariance <=32 MiB. Preflight includes at least four
sensitivity-size working copies, base RSS, regularization/optimizer states and
output, not just G. RSS budget 4 GiB, scratch 2 GiB and wall budget 30 minutes
are *proposed measured gates*, not current capability. Serial candidate/refit
execution, one BLAS thread initially; measure alternative threading separately.
No automatic survey thinning, cell coarsening or relaxed stopping to fit budget.
Oversized requests fail explicitly with an offline recipe and limits.

Nominal measured p95 must remain <=70% of configured resource budgets; record
CPU/device, threads, peak RSS, disk growth, timings, source/env hashes and all
cancel/crash receipts. Test worst-case preflight versus measured use; never claim
station/cell caps alone guarantee a memory ceiling. If the estimator is not
conservative or the envelope fails, reduce advertised supported scale only after
review, keep the failure and rerun at new frozen policy. No hidden threshold
change. Public host admission is separate and currently disk-headroom blocked;
other-method controls and host HTTP success cannot accept this local M02 lane.

## Ownership and acceptance boundary

| Owner | After separate implementation approval | Explicit exclusions |
| --- | --- | --- |
| M02 worker | New `data-pipeline/gravity_survey.py`, `gravity_inverse.py`, `gravity_inverse_bundle.py`, `gravity_inverse_controls.py`; paired local CLI scripts; new tests named in validation; local method docs | Existing potential/spatial/ingest physics, canonical data and gates remain unchanged unless separately authorized |
| M01/reference owner | Review correction/height/CRS and derivative seams, datum-grid availability and provider mappings | No inferred Bartlett heights/errors, no converting equivalent sources into density |
| Main integration | Shared API/job/auth/storage/registry/processing contracts, upload adapter, UI/course/wiki integration, version/ledger/canonical/release, dependency coordination and actual-host admission | Not implemented by this docs sidecar |
| Independent reviewer | Primary evidence, frozen gate review, independent controls/replay and resource/field receipts | Author self-review does not replace independent acceptance |

Main must approve the plan, thresholds, request schema, exact new paths and owner
boundaries before code. Local acceptance requires every local gate and measured
receipt; full M02 also needs eligible measured field data, full product upload/
job/browser/course gates and main admission. Bartlett currently lacks datum,
errors and lineage; author rights/source access alone do not admit it. No field
replacement, full-field badge, deployment or cutover is authorized here.
