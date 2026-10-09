# Binding-set feasible-descent hybrid: full proposed amendment

Status: DOCS-ONLY, NOT APPROVED FOR TESTS/CODE. Date2026-10-03.
MAIN requested a complete evidence-backed amendment after reviewing the new
ordinary near-zero negative. Frozen implementation6331bee9cf289e59647566ac01efc178d51a8e6c
and its nine source/test/evidence/doc paths remain exact original bytes, pinned
in the [new receipt](../../../research/m02-l2-binding-set-evidence-2026-10-03.json).
[Primary research and own proof](../../../research/m02-l2-binding-set-2026-10-03.md)
were written first. [All prospective gates/tasks](binding-set-validation.md)
belong to this same FULL review packet. Proposed implementation executions:0.

## 1. Why a genuine algorithm amendment, not a tolerance workaround

Frozen cpu-2 AS-B passes the original four replay controls and its original12
tight-start controls, but the extended24-start gate is23 PASS/1 FAIL. Full current
regression347 PASS/1 FAIL/14 attributed legacy skips, focused subset240 PASS/1
FAIL/zero skips, remains incomplete. The
[full actual negative](evidence/additional-wide-start-negative-20261003.json)
records tiny NONZERO free gradients beside an inward bound gradient. Its exact-zero
trigger correctly does not fire. No old failure/fixture/result is rewritten.

Proposed decision: use the published scaled feasible-gradient-projection
ingredient to release ANY exactly active nonbinding coordinate, independently
of whether the free gradient is zero, tiny, underflowing in norm or large. Use
current native reduced-face CG only when every active coordinate is binding.
This is a new binding-set hybrid, NOT a full GPCG implementation or an unchanged
native ProjectedGNCG solver. The native method itself remains unmodified on
the eligible face; the set of states delegated to it deliberately changes.

No new near-zero epsilon, rounded-step trigger, gradient ratio, parameterized
branch, norm-dependent tuning, jitter, random retry, dense production BVLS,
alternate vendor/runtime or caller solver selector. Bound KKT tolerance remains
diagnostic only. No other part of the scientific pipeline is changed.

## 2. Exact objective, candidate and state machine

Phi, genuine official gradient/Hessian, physical q=rho/1000, all volume/face
regularization, fixed b, W and beta_engine=n_fit*beta_candidate stay exactly as
the approved original design. Compute h=actual fixed positive Hessian diagonal
and D=diag(1/h) ONCE per partition, as currently. Every reciprocal must be finite
and strictly positive; no floors/updates/bounds changes. Set both official
bfgsH0 and approxHinv to that SAME csr diagonal as currently.

At EACH accepted state, including start:

1. Reevaluate the genuine fixed inverse problem and record exact q/Phi/gradient.
   Preserve current finite/bounds/state/deadline/convergence/iteration checks
   and their precedence BEFORE any direction selection. An already stationary
   null, reference or bound optimum stops with zero new steps, not a release.
2. Compute A=official activeSet(q), B=official bindingSet(q), I=A AND NOT B.
   Feasibility makes <=lower/>=upper the exact bound conditions. B uses official
   gradient signs including equality; zero gradient at a bound is binding.
   Never use the32eps diagnostic KKT bound tolerance for A/B/I. Do not declare
   all-active optimal unless the unchanged convergence check actually passes.
3. If ANY I, choose kind binding_release. DO NOT run native CG first, inspect
   its step, wait for LS failure, or compare free/active magnitudes. Compute
   u=q-Dg with strict overflow/invalid checks and require finite u BEFORE clipping.
   Set z=official projection(u), d=z-q. Require finite/nonzero d, finite STRICT
   g^T d<0 and finite positive d^T D^-1 d. D is the already fixed actual diagonal,
   not a fresh preconditioner or a new scaling parameter. Nonfinite fails as
   nonfinite; zero or non-descent fails as zero_free_direction, NEVER converges.
4. Otherwise A=B. If the original free residual norm is zero, retain the
   original zero_free_direction failure after convergence checks, including
   nonzero entries whose norm underflows. Otherwise call the exact installed
   native findSearchDirection ONCE. Keep its existing200/rtol1e-6/atol0 checks;
   nonfinite residuals, unmet target or cap retain their original failure. No
   projected-gradient fallback after CG failure. Require returned finite/nonzero
   direction and finite STRICT g^T d<0 before search; failure is respectively
   nonfinite/zero_free_direction. These explicit guards now cover native directions.
5. Use the exact line-search state machine in section3. Accept at most ONE
   next state per outer iteration. Recompute A/B after it; never keep a stale
   binding set. A subsequent native-CG state with new inward active coordinates
   selects projection BEFORE the next CG, not a retry within the previous step.

This completely supersedes AS-B's elementwise-zero-free trigger and its AS-02
underflow negative when I is nonempty: with inward active entries, norm underflow
is irrelevant to the new selection. If I is empty, the original norm-underflow
failure remains. The original cpu-2 tests/receipts stay historical byte evidence;
later cpu-3 tests must assert BOTH new branches explicitly rather than relabel old
behaviour. All-positive and all-negative supplied contrasts remain valid.

## 3. Exact projected Armijo and actual-displacement safeguard

Keep official minimize, projection, scaleSearchDirection and modifySearchDirection
loop inherited. Parameters stay maxStep=infinity, LSreduction1e-4, LSshorten.5,
maxIterLS20, require_decrease=True, WolfeFalse. Its actual trial indices are0..19,
t=2^-j, q_trial=P_box(q+t*d). PG d is a FEASIBLE ENDPOINT CHORD; this is not
the generally different projection arc P_box(q-t*Dg). For PG the chord is feasible
in exact arithmetic; official projection still checks each computed trial.

The PRIVATE inLS observer changes admissibility for BOTH kinds, explicitly:

- Nonfinite trial q/Phi/displacement/slope or arithmetic overflow fails immediately
  as nonfinite; do not clip infinity. Deadline overrun fails wall_cap as currently.
- Compute actual Delta=q_trial-q and s_actual=g^T Delta using this SAME accepted
  g. A rounded all-zero Delta fails zero_free_direction immediately. No fabricated
  accepted duplicate step, jitter or convergence from a no-op.
- A finite nonzero Delta with s_actual>=0 is NOT accepted even if projected
  Armijo arithmetic would pass. Return not-stopped to the inherited loop so it
  shortens the SAME direction within its existing20 trials. This is a legitimate
  projected-search rejection, not CG failure fallback or a second solve. On
  exhaustion retain line_search_failed. It is an explicit change from AS-B's
  immediate nonnegative-slope failure, which applied only to its release branch.
- For finite strictly negative s_actual, delegate to the unchanged official
  Armijo stopper: Phi_trial <= Phi_current+1e-4*s_actual. In addition retain the
  existing accepted-objective decrease/state consistency check. No Wolfe test,
  looser decrease, alternate trial or retrospective model correction.

Rounded equality of objective/RHS alone is NOT convergence. It can satisfy the
existing finite Armijo inequality when Delta is real and slope strictly negative;
the unchanged independent KKT/three-change or absolute-stationary terminal policy
is still required. Trial/CG diagnostics are not convergence flags. If a native
LS exhausts or fails, retain that failure; never retry with binding_release.

## 4. Own proof and deliberately limited guarantees

For the PG candidate, D is positive diagonal and the box is Cartesian, so z
minimizes g^T(z-q)+0.5(z-q)^T D^-1(z-q) over the box. Its variational inequality
with test point q gives g^T d <= -d^T D^-1 d <0 whenever d is nonzero. The finite
box is convex; q+t*d is feasible for0<=t<=1. The research file supplies the full
derivation and distinguishes arbitrary dense two-metric scaling, which is NOT used.

On A=B, inward active contributions in the installed method are absent. Exact
fixed-diagonal PCG on the SPD face from zero step has Galerkin orthogonality and
g_F^T p_F=-p_F^T H_FF p_F<0 for nonzero approximate CG steps. A sufficiently
small positive step remains inside all free-coordinate bounds. These two local
facts justify descent plus Armijo; they do NOT bypass computed finite/slope checks.

The binding rule removes the scientific need to solve an already nearly stationary
free subproblem before releasing an inward constraint. No free-gradient epsilon
or relative heuristic occurs. This is a GPCG-style hybrid using standard published
projection/face ingredients; it does NOT reproduce GPCG's extra phase/accuracy
rules or inherit its global/finite-termination claims. In ideal arithmetic unlimited
shortening finds a local Armijo step; LS20, accepted200 and cooperative120s can
still fail. We do NOT promise this amendment passes all tests,24 cases or resources.
Only future independent actual execution can establish the frozen acceptance gates.

## 5. Stops, identities and private trace contract

UNCHANGED: normalized projected KKT<=1e-5 plus three relative changes<=1e-6;
absolute projected gradient<=1e-12 exception;32eps bound diagnostic; CG200 with
rtol1e-6/atol0; accepted200/recorded201;20 LS trials; per-solve120s/calibration1800s
cooperative deadlines. Preserve state/model/objective/terminal replay, units,
all eight betas,25 serial fits, starts/references/bounds/seeds and every numerical
tolerance. No convergence from small native residual, small step, good data fit
or B=A alone. Geometry/source/array/metadata/memory caps are unchanged.

Public solve/result/trace EXACT keys and reason enums remain unchanged. Each
accepted PG or CG direction consumes one original iteration. Direction checks
never create unrecorded accepted models or a hidden PG subloop. Existing cg_counts
are0 for PG because CG NOT RUN; actual native counts for CG. Actual LS counts
retain every evaluated projected trial. Before each attempt reset CG count0 and
residuals None; not_run and binding_release never fabricate zero residual success.

Proposed private optimizer_evidence EXACT keys (not public result additions):

1. trial_objectives: readonly F64(t_finite,3), columns accepted-state index,
   zero-based trial index, finite actual Phi_trial; at most4000 rows. A failed
   nonfinite trial is represented by last_trial_check, not a NaN/Inf array row.
2. direction_kinds: readonly I64(max(k-1,0)),0=native_CG,1=binding_release,
   aligned ONLY accepted directions. The new meaning is epoch-bound, not applied
   retroactively to cpu-2's1=degenerate_release.
3. last_direction_kind: exact str native_CG, binding_release or not_run.
4. last_cg_count: exact int0..200;0 for not-run/release, actual count for native.
5. last_cg_absolute_residual: finite float or None.
6. last_cg_relative_residual: finite float or None.
7. last_cg_residual_status: not_run, finite, nonfinite or unavailable; the latter
   two are retained failed native attempts, NEVER convergence. No NaN/Inf output.
8. direction_decisions: tuple<=200 of exact dicts {state_index:int0..199,
   kind:str as above except not_run, active_count:int0..a, inward_active_count:int0..a,
   free_residual_inf:finite float, candidate_slope:finite float or None,
   pg_metric_norm_squared:finite positive float or None, cg_executed:bool}.
   One record per attempted direction, including a failed last attempt. Native
   metric term is None, not an invented0 PG certificate; preconstruction failure
   slope/metric are None. The norm is diagnostic, NEVER a trigger or stop.
9. trial_checks: readonly F64(t_checked,5), columns accepted-state index,
   trial index, t, actual finite slope, decision0=shorten/1=accept. At most4000
   rows, finite computed trials only. This does not label an unperformed trial.
10. last_trial_check: None if no LS ran, otherwise exact dict {iteration:int0..199,
    trial:int0..19, t:finite float, phi_trial:finite float or None,
    slope:finite float or None, decision:str accepted/shorten/failure,
    cause:None or existing reason enum}. It retains the last actual failed/
    unavailable scalar and cap outcome without fabricating trial values.

Private diagnostics must be readonly/snapshotted, align with attempted/accepted
counts, stay within the existing256MiB trace/output projection and measured2GiB
envelope, and enter external source-bound receipts. They are not caller hooks,
I/O/export paths, a posterior or safe HTTP diagnostics. Genuine failed native
CG/LS/nonfinite/state/engine outcomes keep original public failed_trial meanings.

## 6. Deliberate source/policy epoch and unchanged ownership

PROPOSED ONLY: runtime_epoch=m02-survey-l2-cpu-3;
policy.optimizer=projected-gncg-binding-release-1. Reject cpu-1/cpu-2 and prior
recorded-1/degenerate-release-1 combinations BEFORE finite/hash/copy/engine work.
No implicit request upgrade or provenance relabelling. Geometry-only plan and
public result schemas retain their types/keys; policy/epoch/source/result hashes
bind genuine new bytes. Old9 frozen paths/receipts remain historical and unchanged
during this docs proposal. They are not numerical evidence for a future solver.

If explicitly approved later, algorithm ownership ONLY existing own gravity_l2.py,
the three paired approved test files and NEW additive own feature/research evidence.
No gravity_survey_l2.py/planner, accepted forward, installed source/package/runtime,
legacy physics, raw/canonical, original seven SDD files, historical receipt,
shared API/UI/ledger/product version/host/main/merge/deploy changes. New code paths
outside that authority must STOP for separate review. No tests/code yet.

## 7. Full review and bounded milestones

BS-A: MAIN fully reads this entire amendment, entire research/source receipt and
entire validation/task file; explicitly approves or revises candidate/trigger,
both-branch LS policy, proof limitations, private diagnostics and cpu-3. HOLD code.
BS-B: persist approval BEFORE new tests; actual test-first reds then approved
source implementation, preserve all negatives and truthful timestamps/pins.
BS-C: fresh full focused/broader/source28 gates, original four, producer24 starts
and separate MAIN16 starts with all frozen independent optimum/KKT criteria.
BS-D: unchanged all16 requirements, sealed candidates/refit/evaluation, locked24
family/condition outcomes, rank/resolution and projected/actual resource profile.
BS-E: stable exact-head/source/receipt full MAIN detached read and independent
execution BEFORE whole-unit promotion. No source-only/proposal/local partial PASS
closes these tasks. All prospective BS gates in validation are NOT RUN.
