# Degenerate free-set release: additive L2 amendment

Status: proposed for FULL MAIN review BEFORE any changed optimizer code/test.
Date: 2026-10-03. Original specification48245d1 and frozen optimizer milestone
`d7c66704edaeb46bc83dad4917f7cd41d12e09f1` remain historical exact bytes.
[Primary research and own descent derivation](../../../research/m02-l2-degenerate-active-set-2026-10-03.md)
precede this proposal. Existing compact-data admission changes do NOT implement
this direction. No implicit approval comes from the original SDD or metadata fix.

## Reason and exact scientific delta

MAIN's separate bounded report retains four genuinely independent controls:
two wide-bound passes and two75kg/m3 failures at d7. The original implementation
correctly reports nonconverged/zero_free_direction, not an optimum. The installed
official free-set CG produces no step to scale an inward active gradient when
the free residual is exactly zero. Removing the guard alone is not a remedy.
MAIN owns that report/receipt; this amendment references, not duplicates, it.

Proposed ONLY algorithm exception: a fixed-diagonal projected-gradient release
BEFORE attempting native CG when its initial free residual is elementwise
exactly zero and at least one exactly active coordinate is not binding. All
other search directions use the unchanged official findSearchDirection. This
is an explicitly modified local hybrid, NOT unchanged native ProjectedGNCG,
a full GPCG implementation, another selectable solver or a fallback after failure.
No source/runtime/package/forward46d205/geometry/unit/objective change is proposed.

## Exact trigger, operation and finite failure policy

1. Reevaluate and record the genuine accepted q, objective and gradient through
   the existing official inverse problem. Keep existing state/finite/bound/cap,
   wall and convergence tests FIRST, with their original precedence. A stationary
   null or a converged bound state stops without CG or release.
2. Let A=official activeSet(q), B=official bindingSet(q), F=~A and r=F*(-g).
   The exact release trigger is `not any(r != 0)` AND `any(A & ~B)` AFTER no
   convergence stop. This includes the all-active failure and a mixed face with
   exactly zero free gradient; it is NOT restricted to a fitted fixture/geometry.
   A zero norm caused by underflow with any nonzero r does NOT qualify.
   The KKT tolerance32eps remains diagnostics-only, never used to enlarge A/B.
3. Use the SAME finite strictly positive fixed inverse Hessian diagonal D already
   passed to native approxHinv. No floor, new scale, iteration-dependent tuning,
   dense inverse or positive-bound perturbation. Compute u=q-D*g under strict
   overflow/invalid checks, require finite u, then z=official projection(u),
   d=z-q. Require finite d, an actual nonzero component and finite `g.T@d<0`.
   Nonfinite -> existing nonfinite reason; rounded zero or non-descent -> existing
   zero_free_direction reason. Never nan_to_num, clip infinities or change q/start.
4. Return ONLY this d in the qualifying branch of a private findSearchDirection
   override. Delegate every nonqualifying call to the official method. Existing
   maxStep=infinity, official projection/minimize/line-search/active/binding
   methods stay inherited. Native active_set_grad_scale=.01 remains unchanged
   outside this exceptional branch; the release scale is explicitly D, not .01.
5. Run the SAME official projected Armijo search: LSreduction1e-4, LSshorten.5,
   max20 trials, require_decrease=True, WolfeFalse. On the release branch only,
   reject an actually rounded-zero trial displacement or a nonnegative/nonfinite
   actual slope BEFORE accepting its Armijo test. Classify respectively
   zero_free_direction/nonfinite. This prevents a rounded no-op being misreported
   as progress. No second search/release after an ordinary CG or LS failure.
6. If accepted, record the actual official new state and resume native CG when
   its free residual is nonzero. Another exact degeneracy may qualify again,
   still inside200 total accepted steps and201 total recorded states. No extra
   outer loop or hidden inner projected-gradient iterations are authorized.

Local exact-arithmetic guarantee ONLY: for d=P_box(q-Dg)-q,
`g.T d <= -d.T D^-1 d < 0` if d is nonzero. Feasibility follows from the box's
convexity for0<=t<=1. The proof is in the research file. It does NOT guarantee
finite-precision success under the frozen caps, a global convergence rate,
correct field density, data identifiability or geological recovery.

## Stops, trace, ownership and source epoch

Unchanged stops: normalized projected KKT<=1e-5 AND three accepted relative
objective changes<=1e-6; existing absolute projected-gradient<=1e-12 exception;
CG200/rtol1e-6/atol0, LS20, accepted iteration200, solve120s/calibration1800s
cooperative wall caps. Existing decrease allowance1e-12*max(1,abs(previous Phi)),
prediction/gradient/Choclo/covariance/geometry gates, input/resources/metadata
caps, seeds104729 and locked evaluation seeds, eight betas, all24 conditions,
no warm starts and sealed protocol remain unchanged. No criteria are weakened.

Existing exact solve-record/trace keys and reason enums remain unchanged.
Every accepted release contributes one iteration and its genuine LS count;
`cg_counts` entry is0 because CG was NOT RUN, never a claimed CG success. Before
release set native cg_count0, cg_abs_resid=None, cg_rel_resid=None to prevent stale
diagnostics. Official print_line already renders None blank. Do not fabricate
zero relative/absolute residual. Ordinary CG still executes all existing finite/
cap/residual checks. For release only, those nonexistent CG diagnostics are not
tested as if CG ran; direction/actual-trial finite/descent checks apply instead.

Private external optimizer evidence adds readonly I64 `direction_kinds` of
length max(k-1,0):0=native_CG,1=degenerate_release, aligned with accepted counts.
It adds `last_direction_kind` as exact str native_CG, degenerate_release or
not_run. Last CG residuals are floats for native CG, None for release/not_run.
The last count is0 for release/not_run. Failed trial objectives remain separate,
bounded and retained. No extra public result keys, caller callback or output path.

Proposed deliberate version change, subject to this FULL review:
`runtime_epoch` becomes `m02-survey-l2-cpu-2` and policy.optimizer becomes
`projected-gncg-degenerate-release-1`. The original cpu-1/recorded-1 files and
failed receipts are NEVER rewritten or relabelled. The new entry accepts ONLY
the new exact epoch/optimizer, not an implicit upgrade of an old request. The
geometry-only plan schema, engine pins, beta-grid name and native result schemas
remain unchanged because their types/meaning are unchanged. Source/policy/result
hashes bind the new actual bytes. No claim that an old receipt validates new code.

Changed implementation ownership ONLY existing own gravity_l2.py, the three
approved paired tests as needed, own additive feature/research docs/evidence.
No edits to installed optimizer, accepted forward, legacy kernels, original
seven documents/receipts, source intake, environment, API, canonical or MAIN tree.
Original metadata scalar32768/depth8/256KiB representation/96MiB are unchanged.

## Additive EARS requirements and prospective gates

Status of EVERY new gate below: NOT IMPLEMENTED / NOT RUN, no PASS.
Paths below are all under tests/numerics/test_gravity_l2.py unless stated.

| ID | Requirement | Named gate |
| --- | --- | --- |
| AS-01 | WHEN an unconverged exact zero-free state has an inward active gradient, THE local unit SHALL use only the stated finite feasible diagonal direction. | test_degenerate_release_exact_trigger_and_certificate |
| AS-02 | IF free entries are nonzero but their norm underflows, THEN THE unit SHALL retain zero_free_direction and SHALL NOT use release. | test_nonzero_underflow_free_gradient_is_not_release |
| AS-03 | WHILE the state already meets a frozen convergence test, THE unit SHALL stop without a direction or a CG call. | test_stationary_bound_and_null_do_not_release |
| AS-04 | WHEN release runs, THE unit SHALL retain native projected Armijo and actual LS counts, reject rounded-zero/non-descent trials and retain its real failure. | test_release_official_armijo_counts_and_rounded_trial |
| AS-05 | IF direction construction overflows or has zero/nonnegative slope, THEN THE unit SHALL retain nonfinite/zero_free_direction without floor or retry. | test_release_finite_failure_no_jitter_or_retry |
| AS-06 | WHEN a normal native search or LS fails, THE unit SHALL retain that failure without exceptional release. | test_native_failure_never_invokes_release |
| AS-07 | WHEN a release is accepted, THE unit SHALL record the actual model/objective/KKT and distinguish not-run CG from actual CG. | test_release_trace_identity_and_not_run_cg |
| AS-08 | WHEN the four retained independent controls are rerun at the new source, THE unit SHALL meet both original tiny-oracle and MAIN additional frozen comparison gates or retain failure. | test_independent_six_cell_bvls_tight_and_wide |
| AS-09 | WHEN different signed feasible bound starts are supplied, THE unit SHALL use them unchanged, satisfy the independent optimum/trace gates or retain failure. | test_independent_six_cell_bound_starts |
| AS-10 | IF cpu-1/recorded-1 is supplied to the amended entry, THEN THE unit SHALL reject before scans/hash/engine rather than relabel old provenance. | tests/data/test_gravity_survey_l2.py::test_amended_optimizer_epoch_rejects_old_before_work |

AS-08 includes BOTH noise modes, original signed/nonuniform six-active/five-row
MAIN geometry, bounds75 and1500, unchanged reference/scale/lengths/background,
zero start and candidate.01. Direct Choclo G, independent both-active pairwise
R and separate triangular Cholesky whitening feed tiny BVLS ONLY as an oracle.
Prospective gates: original normalized density/prediction errors<=1e-5 plus
independent feasibility/KKT; MAIN added converged status, normalized model<=1e-3,
relative unhalved objective<=1e-6, prediction abs<=1e-6mGal, ALL still required.
No replacement with the original producer250-bound easier control. AS-09 adds
all-lower/all-upper and mixed signed starts under both noise modes; original
starts/control specimens are not overwritten.

The certificate gate includes independent well-scaled positive diagonals and
mixed exact-zero-free states; strict computed descent and feasibility are
required. Algebraic certificate discrepancy uses existing identity tolerance
rtol1e-10/atol1e-12, NOT a looser runtime convergence gate. Include same-bound
stationary null, outward gradients, underflow nonzero free residual, overflow,
rounded-zero release, LS20, CG200, iteration200, wall, terminal/replay tamper
and persistent prediction errors. Injected diagnostic failures remain labelled
injections, not fabricated natural performance failures.

## Dependency tasks and explicit hold

1. AS-A: persist this full proposal and primary dossier; MAIN reads exact full
   amendment/research/one-direction receipt and approves or revises trigger,
   direction, finite/LS semantics, version strings and evidence. HOLD code.
2. AS-B: only after explicit approval, persist approval BEFORE test-first reds,
   then implement the narrow exception; retain actual red/green chronology.
   Do not delete untracked work to manufacture old red timestamps.
3. AS-C: fresh full focused controls/source28 audit and four-control independent
   BVLS replay; new receipt binds actual new source/epochs and all failures.
4. AS-D: continue original all16 gates, complete sealed beta selection, all24
   cases, estimator and measured local envelope; no skip/exclusion relaxations.
5. AS-E: MAIN detached exact-head full source/test/receipt/negative review and
   independent execution before any whole-unit promotion.

Until AS-A is explicitly accepted, current native policy and zero_free_direction
guard remain unchanged. Compact admission/source-metadata PASS, tiny algebra,
docs guards and a feasible direction certificate do NOT establish complete
inverse/resource/field/API/GPU/host acceptance. No merge/deploy authority.

## Explicit MAIN approval before AS-B tests/code

MAIN confirmed FULL read at1c8b2a1e6cd8dbf3088d3cb5a0c469cf8a0e99c6 of this
complete amendment, the entire primary dossier and detailed one-direction receipt.
MAIN independently checked installed official active/binding/CG/Armijo source
and live Argonne sections2/3. On2026-10-03 MAIN explicitly APPROVED AS-B exactly
as written: elementwise zero free residual AND any active-not-binding AFTER
unchanged stops; existing positive D, finite projected descent, actual-trial
slope/no-op rejection and None not-run CG diagnostics; cpu-2 and
projected-gncg-degenerate-release-1. This approval is persisted BEFORE new red
tests or implementation. Prior proposed/pending statements remain chronology.

Authority covers only own gravity_l2.py, the three already-approved paired tests
and additive own docs/evidence. Planner, accepted forward, installed sources,
runtime environment, original documents/receipts, bounds/tolerances/seeds/caps
remain unchanged. No ordinary-CG failure fallback. MAIN's d7 two failures remain
literal historical failures. New-source controls must include frozen four plus
six bound-start modes and all original16/24-case/selection/resource gates.
Whole-unit acceptance requires later MAIN detached full review/run;195 historical
focused passes are NOT amended-solver proof. No expanded paths, API/field/host,
merge or deployment authority is granted.
