# Ordinary local submitted-survey weighted L2 design

Status: planned, 2026-10-03. MAIN full read and explicit implementation approval
are REQUIRED before code/tests. Numerical gates: NOT RUN. Base develop
`1b112bb258520a5679a865335cec30b6a97a1a0d`; branch
`task/geophysics-m02-survey-l2-sdd`. [Research](../../../research/m02-survey-l2-2026-10-03.md)
was persisted first; [typed protocol](contract.md), [gates](validation.md),
[requirements](requirements.md), [ownership/backlog](tasks.md) are one review unit.
PR120's broad 19 requirements and PR122's accepted source remain unchanged.

## Boundary, actual engine and lifecycle

Target: independently inspectable bounded L2 on an explicitly supplied ordinary
metric local survey, immutable geometry/source/uncertainty and leakage-resistant
blocked selection. A conditional regularized density model is the scientific
output, NOT uniquely recovered geology or automatic uploaded-field admission.
IRLS, API/auth/jobs, field/provider/M01 mapping, terrain interpolation, CRS/datum
conversion, public serialization/storage, canonical artifacts, runtime installs,
GPU and host are excluded. Full M02 remains incomplete even if this unit passes.

Prospective new paths ONLY: `data-pipeline/gravity_survey_l2.py` for contract/
geometry-only planning, `data-pipeline/gravity_l2.py` for official L2/calibration/
evaluation; three paired new tests named in validation; this feature's docs.
No public callback, engine/backend/plugin/path option, I/O, inverse fallback or
monkeypatch of installed packages. An internal recorder/stop subclass is explicitly
specified below, not a new optimizer advertised as SimPEG. Ownership is prospective,
not authorization to create those files in this docs-only task.

Flow: normalized source-bound arrays -> geometry-only sealed split plan ->
development-only train/validation candidate fits -> selected development refit
and frozen identity -> separate unopened outer-value evaluation. Owner storage
and independent reviewers own sealing/timing and raw-rights evidence. Array hashes
alone are not cryptographic proof that an author never saw the observations.
Classical learned-training status is `not_applicable_classical`; regularization
selection is CALIBRATION and cannot be erased from the scientific lifecycle.

Use genuine `Simulation3DIntegral` / Geoana RAM/float64/one process, IdentityMap
on active q; `L2DataMisfit`, `WeightedLeastSquares`, `ProjectedGNCG`,
`BaseInvProblem` and `BaseInversion`. All required versions loaded from official
module __version__, no filesystem version scan inside callables. External trusted
read-only source audit binds prior 20 pins plus eight newly inspected source
files from the [research receipt](../../../research/m02-survey-l2-evidence-2026-10-03.json).
The newly proposed implementation/test digests remain null until real code exists.
Windows CPython 3.12.10 only; no Linux/runtime/source-epoch relabelling.

The unchanged accepted forward operator validates geometry and terminal predictions.
The inverse constructs a fresh official fitting simulation from that verified
geometry, checks actual ordered prism corners and G/1000 against the accepted
physical J before fitting. No custom-kernel/private prepared-simulation injection.
Actual bounds/centres/volumes, inactive-cell representability, strict outside and
cell-scaled geometry fidelity 1e-10 are inherited unchanged. No centre-caused G
collapse hypothesis, revised caps or altered prediction tolerances.

## Units, background, mask and uncertainty

Exact input/result types and all bounds are in contract. n includes all known
geometry, masked and sealed rows. Only compact development observations/noise
enter calibration, NEVER outer/truth values. Missing values are absent compact
rows with exclusions/embargo, not NaN/zero fit data. Unknown geometry is unsupported
upstream raw evidence, not a fabricated prediction. Masks true=excluded; reasons
and original order preserved. Duplicate positions/IDs reject; repeat-measurement
policy is not implicit in a full covariance matrix.

Let rho be density contrast in kg/m3, q=rho/1000 in g/cc, G engine mGal/(g/cc),
J_rho=G/1000. Predicted total upward anomaly p=Gq+b with fixed supplied b in mGal.
Positive mass below gives negative gz. Objective residual r=p-d; exported residual
e=d-p. Data, background and SD share mGal; covariance mGal^2. No absolute gravity,
hidden regional removal, refitted intercept, inferred vertical sign or user-value
normalization. Upstream identity/correction/frame fields are explicit declarations
and external receipts, not a provider-physics approval by this local unit.

Diagonal SD is strictly positive traceable Gaussian scale. Full covariance is
finite exactly symmetric SPD in compact row order, condition number <=1e8.
Source-labelled assumptions remain `explicit_conditional_gaussian`, never measured
instrument errors or conservative bounds. No jitter/nugget/floor/eigenvalue clipping.
Independently Cholesky-check each used principal C_ff, C_vv, C_tt. Masking/permutation
acts on both covariance axes. Cross-partition dependence remains literal;
buffering does not assert independent Gaussian test errors.

For full C_ff, use SciPy 1.15.2 eigh(driver='evd', check_finite=True,
overwrite_a=False) and W=U diag(lambda^-1/2) U.T, then set matching upper/lower
entries to their arithmetic mean to make the COMPUTED W exactly symmetric.
This is numerical construction of W, NOT altering supplied covariance C.
Check W C W.T versus I, and W.T W versus independent Cholesky precision action,
under frozen tolerances. Convert W to scipy.sparse.csr_matrix, NOT ndarray or
sparse array: pinned misfit uses matrix `*` operations. Diagonal uses csr diagonal
1/sigma. Do not send a lower-triangular inverse to this pinned Hessian: deriv uses
W.T W but deriv2 uses W W. Symmetric W makes both mathematically compatible;
the correlated-control derivative/Hessian oracle remains mandatory before code
acceptance. This does not authorize rewriting vendor or legacy misfit sources.

No whitening of joint fit/validation/test data, Schur conditioning on heldout
observations or hyperparameter estimation from outer residuals. Score each set
using its own MARGINAL covariance, disclose possible cross-partition dependence.
Geometry/correction/background uncertainty not propagated here is an explicit
fixed-geometry conditioning limitation, not zero uncertainty or field confidence.

## Official finite L2 objective and model regularization

Let V_i be actual admitted cell volumes, Vtot=sum active V_i, s the supplied
density_scale_kg_m3 /1000, and delta=q-q_ref. Let D_j be official active-face
metre derivatives; F_j averages adjacent active cell volumes onto those faces.
The fixed model objective is

`phi_m = (sum_i V_i delta_i^2 + sum_j ell_j^2 ||diag(sqrt(F_j V)) D_j delta||^2) / (Vtot s^2)`.

Positive smallness is mandatory. Official `WeightedLeastSquares` receives
IdentityMap, active mask, explicit q_ref, reference_model_in_smooth=True,
alpha_s=1/(Vtot s^2), alpha_j=ell_j^2/(Vtot s^2),
alpha_xx=alpha_yy=alpha_zz=0. Set direct alpha coefficients, not length_scale_j
(which include base_length). Default volume weights remain; no user/custom depth,
sensitivity weights, spatially variable norms or cross-air smoothness. Export
actual alpha values and official active-face volume/derivative fingerprints.
Independent nonuniform tiny-mesh oracle enumerates adjacent BOTH-active cells;
face volume is arithmetic mean of their volumes, derivative is difference over
centre distance, no boundary/air bridge. If official stencils disagree, retain
failure and seek design review, never quietly substitute a hand-rolled R.

Unhalved `phi_d = ||W_f (G_f q+b_f-d_f)||^2`, WRMS=sqrt(phi_d/n_f).
Beta candidates refer to `phi_d/n_f + beta_candidate phi_m`. Actual official
`beta_engine=n_f*beta_candidate`, fixed per solve, objective
`phi_engine=phi_d+beta_engine*phi_m`. Export both normalizations and beta values.
No discrepancy beta update, BetaEstimate, BetaSchedule, TargetMisfit, IRLS or
early selection based on WRMS~1. Credible errors affect residual interpretation,
not a mandate to hit a target by changing SD/beta/stopping.

Gradient in q: `2G_f.T W_f.T W_f r + 2 beta_engine R.T R delta`.
Hessian action: `2G_f.T W_f.T W_f G_f v + 2 beta_engine R.T R v`.
Density gradient equals q gradient/1000; physical Hessian action has factor
1/1000000 for a perturbation in kg/m3. Model term is dimensionless under stated
numeric q/s convention, with metre derivatives and m3 measures cancelling.
All objectives, derivatives, weight actions, eigenvalues, alpha/beta and predicted
arrays must stay finite; numerical overflow/underflow is a literal failure.
Finite strictly convex regularized grid optimum is prior-conditioned uniqueness,
not data rank, density identifiability or an uncertainty posterior.

## Candidate selection, disjoint values and seeds

Geometry-only partition algorithm, seed **104729**, block/group union/hash ordering,
one-fifth sealed units, three cyclic validation folds and strict buffers are
fully specified in contract. Geometry and block/buffer scales freeze before data;
no automatic correlation-length fit from test or mesh choice by attractive map.
Feasibility minima are ordinary-survey support policy, not sufficient field science.
Native inputs may declare campaign/line groups; transitive unions that leave too
few independent allocation units must fail without random-row fallback.

Frozen eight beta candidates: 1e-4, 1e-3, .01, .1, 1, 10, 100, 1000.
Same supplied bounds/reference/start/lengths/mesh/errors for every candidate/fold.
No warm start from another beta, hidden seed retry or tuning spatial weights.
Per candidate, three actual independent fits from the same supplied start; only
converged finite fits can contribute scores. Fold validation quadratic from that
fold's marginal covariance, score Q=sum phi_validation /sum n_validation.
This is mean squared whitened residual, not model RMSE or a likelihood across
independent blocks. Record fold WRMS, total validation WRMS=sqrt(Q), physical
RMSE, counts and all failures. Missing/nonconverged fold makes candidate ineligible;
NEVER average successful folds only. Require at least two eligible candidates.

Choose minimum Q. Scores within `1e-12*max(1,abs(Q_min))` tie; choose largest beta
among them, then original index if identical (duplicate betas forbidden). Refit
once on all development rows with selected beta_candidate, beta_engine=m*beta,
same start/reference/bounds and no outer values. Retain failure rather than select
a second candidate after an unsuccessful final refit. Freeze result/hash before
separate evaluation; evaluate outer marginal once. An all-data refit is OUT OF
SCOPE and cannot replace this model or its heldout claim.

Noise-generation seeds are ONLY external control-harness seeds (validation);
production classical solver has no RNG. Learned training not-applicable, calibration
explicit, sealed evaluation once. Poisoning outer values/SD/truth must leave plan,
selection, all inner models and final density hashes unchanged. Inner validation
values may affect selection but cannot affect the fit model of their own fold.
Predictions for masked/sealed geometry can be computed without their data and
are NOT test scoring before disclosure. Trusted storage sealing is main-owned.

## Exact optimizer mapping and terminal interpretation

Construct ProjectedGNCG with lower/upper in q, maxIter=200, maxIterLS=20,
cg_maxiter=200, cg_rtol=1e-6, cg_atol=0.0, step_active_set=True,
active_set_grad_scale=.01, LSreduction=1e-4, LSshorten=.5,
use_WolfeCurvature=False, require_decrease=True, maxStep=infinity.
Explicit values prevent version-default/deprecated-tolCG drift. Supply
BaseInvProblem(init_bfgs=False, print_version=False, beta=beta_engine);
BaseInversion calls the official solve, no automatic save/directive writes.
Set positive diagonal preconditioner from diagonal of the actual fixed Hessian;
opt.bfgsH0=csr diagonal reciprocal (no zero/negative/infinite diagonal or floor).
No hidden dense Hessian factorization, checkpoint file or package change.

Proposed PRIVATE `_RecordedProjectedGNCG` subclass in the new inverse module:
override ordinary stoppingCriteria and recording/failure observation ONLY;
delegate inLS=True to official stoppersLS, and leave official search direction,
projection and line-search algorithm unchanged. Internal trusted recorder, not
caller callback; no public hook. Record initial state and each accepted iterate
by reevaluating that EXACT q through fixed official invProblem, not stale
phi_d/phi_m after line-search trial. Preserve all trial objective/count evidence
bounded by declared caps. Stop override captures failed line search and terminal
reason; no optimistic flag inferred from `BaseInversion.run` returning a vector.

For q feasible, define bound-active tolerance `32*eps64*max(1,abs(q_i),abs(l_i),abs(u_i))`
for KKT diagnostics only, never shifting geometry or correcting request bounds.
Projected KKT gradient removes positive gradient at lower bound and negative
gradient at upper bound; otherwise retains gradient. Let
`K=norm_inf(g_KKT)/max(1,norm_inf(initial_gradient))`.
At a state, normalized K<=1e-5 and three successive accepted objective changes
`abs(phi_k-phi_prev)/max(1,abs(phi_prev))<=1e-6` are required for convergence.
Exception: absolute norm_inf(g_KKT)<=1e-12 can converge immediately, including
initial stationary null/reference, without invented three zero steps or jitter.
The exception is a predeclared exact-stationarity criterion, not a WRMS shortcut.
Native tolF/tolX/tolG/eps shortcuts are NOT used to claim this convergence;
private stopping override implements the specified combined policy explicitly.

Terminal precedence: nonfinite/engine/state error; failed line search; monotonic
deadline; convergence; 200 accepted-iteration cap; remaining native stall.
CG failure/nonfinite diagnostics or unmet inner residual target produces a retained
nonconverged solve, not silent early accuracy success. Pinned source may have
zero free-set residual while active-set gradient is nonstationary; do not hide
that with seed/start shifts or nan_to_num. A stationary null is checked BEFORE CG;
otherwise classify zero-free-direction/stall and retain the actual failure.
No asynchronous-cancel callable is supplied: per-solve monotonic wall cap 120 s,
whole calibration 1800 s checked between bounded evaluations. A native call may
overrun until return; no hard preemption/distributed lock/host SLA is promised.

The independent bounded reference uses Choclo-derived tiny G and independent
pairwise R, SciPy dense `lsq_linear(method='bvls', lsq_solver='exact', tol=1e-12,
max_iter=1000)` on `[WG; sqrt(beta_engine)R]` and
`[W(d-b); sqrt(beta_engine)R q_ref]`. Its half-objective is multiplied by two
when compared. No optimizer fallback in production. KKT/bounds/state are checked
independently, including feasible active-bound, signed, null and capped negatives.

## Rank, coverage, geometry outcomes and resources

Coordinate coverage requires centred horizontal SVD rank two: singular values
>max(n_fit,2)*eps64*smax; same rank rule recorded, no handpicked area threshold.
Sensitivity uses ONLY fit rows: diag(J_rho.T W.T W J_rho) with declared physical
units, not density confidence. Report exact-zero column indices (warn), a numeric
rank estimate and nullity using whitened A=W G with threshold
max(n_fit,a)*eps64*smax. SVD values are exported without pretending numeric rank
is effective geological resolution. Rank zero data or nonfinite sensitivities
reject; rank<a is a WARNING/expected underdetermination, not arbitrary rank cutoff.
Never demand full column rank in a regularized gravity inverse.

Resolution response `(A.T A+beta_engine R.T R)^-1 A.T A v` on predeclared cell
impulses and small-control spectrum/nullspace pairs is an external control,
not a returned covariance/posterior. All eigen/pair outcomes, depth tradeoffs and
alternative fixed meshes remain labelled prior/geometry dependent. This first
unit will not auto-build surface/terrain or choose a mesh against observations.
External alternate meshes/prior lengths/bounds are separately frozen before
sealed evaluation and may only be diagnostic, not replace the selected result.

Geometric outcome fields distinguish admitted_fixed_geometry, rank_deficient,
zero_sensitivity_columns, validation_outside_fit_hull, error_assumed_conditional,
geometry_uncertainty_not_propagated and cross_partition_dependence. Prediction
fit good/poor and optimizer converged/nonconverged are distinct. On measured or
uploaded data truth is absent; no model RMSE or geological recovery label.

One local CPU process, one BLAS/OMP thread, serial 8*3+1 solves. Full sensitivity
<=64 MiB, covariance<=32 MiB. Histories bounded <=201 states per solve and at most
20 line-search evaluations/step; exact input/candidate counts before allocation.
Proposed workspace projection includes 8 sensitivity-size arrays, 12 covariance-
size arrays, regularization/SVD workspace, <=256 MiB trace/output and base RSS;
projected workspace >2 GiB rejects before engine. This formula is an unmeasured
design estimator, NOT a guarantee of peak RSS. Resource gate must measure small,
nominal and capped workflows before claiming the full cap operational. No I/O/
scratch publication, GUI, hard-kill cleanup, worker/native-package changes, GPU
fallback or online service is authorized. CI runs docs/artifact guards, no fit.

## Exact result contracts and literal nonclaims

Every result is private readonly arrays plus bounded exact native metadata.
Common `provenance` EXACT keys: `source` (source snapshot), `plan_sha256`,
`normalized_values_sha256`, `noise_sha256`, `prior_sha256`, `policy_sha256`,
`forward_source_sha256` (external verified binding 46d205...), `runtime_epoch`,
`runtime_versions` (actual loaded numpy/scipy/simpeg/geoana/discretize strings),
`source_verification`=`external_required_not_performed_by_solver`.
External receipts additionally bind actual implementation/test/installed-source
SHA; no I/O callable falsely claims to have hashed installed files.

Solve record EXACT keys: `status` enum converged, nonconverged, failed;
`reason` enum kkt_stable, absolute_stationary, iteration_cap, cg_cap,
line_search_failed, wall_cap, zero_free_direction, nonfinite, engine_error,
state_mismatch; `model_kg_m3` F64(a) or None if no finite accepted state;
`beta_candidate` float, `beta_engine` float, `fit_rows` I64, `predicted_mgal`
F64(n_fit) or None, `residual_observed_minus_predicted_mgal` matching or None,
`phi_d`, `phi_m`, `phi_engine`, `wrms`, `kkt_normalized` floats or None;
`trace` exact dict {models_kg_m3:F64(k,a), phi_d:F64(k), phi_m:F64(k),
phi_engine:F64(k), kkt_normalized:F64(k), relative_changes:F64(max(k-1,0)),
line_search_counts:I64(max(k-1,0)), cg_counts:I64(max(k-1,0))};
`iterations` int, `wall_seconds` float; `failed_trial` None or exact dict
{iteration:int, reason:str enum above}. k=0..201, counts remain bounded.
No NaN metrics: unavailable values are literal None, not zero. Arrays must
replay accepted state objectives; failed trial/CG timing remains distinct from
accepted trace. Error causes are private diagnostics, NOT safe HTTP messages.

Candidate record EXACT keys: `index` int0..7, `beta_candidate`, `eligible` bool,
`folds` tuple of three exact dicts {`fold`:int, `solve`:solve record,
`validation_rows`:I64, `validation_phi_d`:float or None,
`validation_wrms`:float or None, `validation_rmse_mgal`:float or None},
`score_q`:float or None, `reason` enum eligible, fold_failure, invalid_score.

Calibration result EXACT keys: `schema`=`gravity-survey-l2-calibration-result-1`,
`plan`, `provenance`, `candidates` tuple8, `selected_index` int or None,
`selection_status` enum selected, insufficient_candidates, final_nonconverged;
`final_solve` solve record or None; `predictions` exact dict {rows:I64(n),
gz_up_mgal:F64(n) or None}; `diagnostics` exact dict {fit_rows:I64,
sensitivity_diagonal:F64(a) or None, sensitivity_unit:str exactly `(kg/m3)^-2`,
singular_values:F64(min(m,a)) or None, numeric_rank:int or None,
numeric_nullity:int or None, rank_threshold:float or None,
warnings:tuple of the seven outcome strings above}; `scope` exact dict
{training:str not_applicable_classical, inverse:str weighted_bounded_l2,
field_eligible:bool False, full_M02_accepted:bool False, API_accepted:bool False,
GPU_accepted:bool False, host_accepted:bool False, geometry_error:str not_propagated};
`result_sha256` SHA of everything except itself. Predictions include fixed b.
Nonconverged results retain outcomes and cannot be evaluated as accepted frozen fits.

Evaluation result EXACT keys: `schema`=`gravity-survey-l2-evaluation-result-1`,
`calibration_sha256`, `observations` (exact outer record), `noise_sha256`,
`rows` I64(h), `predicted_mgal` F64(h),
`residual_observed_minus_predicted_mgal` F64(h), `whitened_residual` F64(h),
`phi_d` float, `wrms` float, `rmse_mgal` float,
`prediction_quality` enum within_declared_noise or poor_under_declared_noise
(WRMS<=2 vs >2 descriptive protocol, NOT scientific acceptance),
`dependence` enum as noise, `geometry_conditioning`=`fixed_not_propagated`,
`field_truth` None, `model_accuracy` None, `field_eligible` bool False,
`full_M02_accepted` bool False, `result_sha256` SHA excluding itself.
Reject nonfinite evaluation rather than return a successful record. Hash and
residual check uses independently validated stored prediction, not subtly different
rounded arithmetic. Portable bundle publication/import is not implemented here.

## Review boundary

All equations, exact types, caps, seeds/candidates/stopping/thresholds and prospective
path ownership must receive MAIN full-read approval BEFORE code. Prospective
numerical/quality controls are not PASS. No changes to PR120/PR122, native sources,
environments, historical failures, canonical data, main or production.
