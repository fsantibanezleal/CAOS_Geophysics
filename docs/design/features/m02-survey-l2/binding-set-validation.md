# Binding-set hybrid prospective controls and task ledger

Date2026-10-03. Status: DOCS-ONLY PROPOSAL. New implementation/tests:0.
Every BS gate below is NOT IMPLEMENTED / NOT RUN, NOT PASS. MAIN must read ALL
[amendment](binding-set-amendment.md),
[primary research](../../../research/m02-l2-binding-set-2026-10-03.md) and
[source/frozen-path receipt](../../../research/m02-l2-binding-set-evidence-2026-10-03.json)
and explicitly approve BEFORE red tests or code. Frozen incomplete implementation
6331bee9cf289e59647566ac01efc178d51a8e6c, all9 paths and historical failures remain.

## Exact retained baseline, separate from prospective claims

Current own full regression347 PASS/1 FAIL/14 attributed legacy skips; focused
subset240 PASS/1 FAIL/zero skips. Extended six-start/two-bound/two-noise suite
23 PASS/1 FAIL. Wide diagonal lower_reference has inward nonbinding cell0,
tiny nonzero free gradients and a retained wall_cap/KKT/optimum failure. Read
the complete [actual trace](evidence/additional-wide-start-negative-20261003.json)
and [run receipt](evidence/approved-release-execution-20261003.json). The four
producer replays at cpu-2 pass, not MAIN new-source acceptance. All earlier
d7 two-failure records and MAIN-authored16-start4-PASS/12-FAIL baseline remain.
The separate locked24-family/condition matrix has NOT been executed here.

## Prospective additive requirements and exact test ownership

All names below are PROSPECTIVE, not existing PASS claims. Unless stated,
test owner is tests/numerics/test_gravity_l2.py; no new test file is proposed.

| ID | Requirement and named gate | Required positive/negative evidence |
| --- | --- | --- |
| BS-01 | WHEN any exact active coordinate is nonbinding after unchanged stops, THE hybrid SHALL select fixed-D feasible projection before CG. test_binding_release_any_inward_before_native_cg | Same exact A/B, both bounds, mixed/all-active, positive/negative/free gradients zero/1e-300/1e-11/large; deny CG; no norm/epsilon trigger |
| BS-02 | WHEN all exact active coordinates are binding, THE unit SHALL delegate only once to the pinned native face search and retain failure. test_binding_face_delegation_and_no_failure_fallback | A=B/nonempty and empty, fixed D; actual native counts/residual target; injected CG failure denies PG/second solve; no fallback after LS failure |
| BS-03 | WHILE an unchanged convergence test already holds, THE unit SHALL stop before any direction. test_binding_stationary_bound_null_precedence | Both tight all-upper optima, exact null/reference, zero-step counts and None not-run residuals; genuine unstationary active face must not pass |
| BS-04 | WHEN PG constructs a candidate, THE unit SHALL preserve diagonal metric descent/feasibility and retain all finite faults. test_binding_projection_metric_certificate_and_faults | Independent SPD diagonal/box model, signs/scales and native projection; compare g^T d <= -d^T D^-1 d; overflow-before-clip, roundedzero/non-descent, no floor/jitter |
| BS-05 | WHEN either direction searches, THE observer SHALL reject nonnegative actual slope, preserve native20-trial shortening and accept only negative-slope Armijo. test_binding_both_branch_actual_armijo_and_backtracking | Real projected CG whose full trial clips but shorter descent succeeds; PG chord versus projection arc explicitly distinguished; exact actual slopes/counts; injected positive slope cannot accept |
| BS-06 | IF finite/nonfinite/noop/LS/deadline/iteration/terminal conditions fail, THEN THE unit SHALL retain the original failure without invented progress. test_binding_caps_nonfinite_noop_and_terminal |20 actually exhausted trial calls; CG200 negative diagnostic labelled injection when synthetic; accepted200 injection does not claim200 natural steps;120 wall; finite actual terminal/objective replay |
| BS-07 | WHEN an accepted or failed direction is recorded, THE unit SHALL preserve private/public exact epoch-bound trace identities and unavailable diagnostics. test_binding_trace_decision_and_cg_availability |0 CG for PG/not_run and None/status not_run; real CG residual0 allowed only when executed; all10 exact private keys, decision/accepted/trial alignment, <=200/4000/201 caps, readonly, noNaN |
| BS-08 | IF earlier optimizer/epoch is supplied, THEN THE unit SHALL reject before values/hash/copy/engine. tests/data/test_gravity_survey_l2.py::test_binding_epoch_exact_no_upgrade | cpu-1/cpu-2/old policy combinations/hooks; cpu-3/new policy alone accepted metadata; historical source digests never copied |
| BS-09 | WHEN the four original frozen independent controls run, THE new source SHALL meet ALL original tiny and MAIN added gates or retain literal failure. test_binding_original_four_bvls | Same MAIN helper dc4a6... read-only, source-bound four modes; no producer fixture as substitute for independent acceptance |
| BS-10 | WHEN all supplemental starts run, THE new source SHALL meet the independent bounded optimum/trace gates or retain failures. test_binding_all24_signed_start_bvls | Six modes x bounds75/1500 x both noises, unchanged Choclo/pairwise-R/Cholesky/BVLS; specifically retain/retest wide lower_reference; no xfail/skip |
| BS-11 | WHEN MAIN replays its separately authored16-start helper, THE complete16 outcomes SHALL remain separately attributed. MAIN detached test/helper ownership | Same helper de903... and original four, original gates and true augmented-gradient normalized KKT; producer24 does not replace it |
| BS-12 | WHEN candidate selection/sealed evaluation/resource controls execute, THE unit SHALL preserve all original16 requirements and locked24 outcomes. tests/numerics/test_gravity_l2_selection.py original frozen gates | Eight betas x3, same start/no warm starts, complete candidate eligibility/tie/refit failure, no outer values or marginal conditioning, all24 family/condition outcomes and measured resources |

## Frozen control specimens, comparisons and timing

The original four: MAIN's exact six-active nonuniform3x2x2 mesh, five outside
receivers, signed synthetic density/background/reference/lengths, scale750,
beta.01, bounds75/1500 and diagonal/full covariance. Producer supplemental24
uses SAME geometry/observations/noise/prior with start modes all_lower, all_upper,
lower_upper, upper_lower, lower_reference, upper_reference. All prescribed starts
are used verbatim, including already-optimal tight upper states; no perturbation.
The complete frozen specifications/helper SHA and cpu-2 actual traces are in
the immutable run receipt, not reconstructed by changing a seed/source array.

Required comparison conjunction: original normalized physical density/prediction
errors<=1e-5 AND MAIN added normalized model L2<=1e-3, relative unhalved objective
<=1e-6, absolute prediction<=1e-6mGal, converged status, bounds feasibility,
independent projected KKT<=1e-5 normalized by true augmented-gradient at the
actual supplied start. Use original oracle/normalizers; no rescaling error by a
convenient new denominator. All accepted models/objectives/residuals replay.
Native CG residual success, low WRMS or B=A is never a substitute for these gates.

Certificate identities use existing rtol1e-10/atol1e-12 for well-scaled small
algebra. Preserve prediction/J/gradient/covariance/geometry thresholds exactly;
no numeric epsilon is introduced as an active/binding trigger. LS actual slope
is strictly negative for acceptance. Finite positive projected slope only causes
within-direction shortening; all-zero rounded trial still fails immediately.

The full current old test suite and source28 external audit rerun with no excluded
new metadata/optimizer/candidate/resource gates. Explicit legacy skipped/missing
dependency attribution remains, no install. The original acceptance control files
may change expectations only AFTER reviewed cpu-3 authority; cpu-2 commit and
all old JSON/XML receipts retain their original bytes and failure verdicts.

## Sealed matrix, all requirements and resource gates stay mandatory

The approved original [16-requirement matrix](validation.md) remains normative,
except the explicitly proposed direction/LS policy delta. The locked matrix is
SIX families x FOUR conditions, independent off-grid Choclo prism sources, mesh
4x4x3 width100,144 known receivers, seeds700001+100*f+c; source-disjoint development
uses translated(+17,+13,0) sources and seeds900001+100*f+c. This is NOT the24
supplemental start controls. Do not alter priors/grid/noise/masks/model mismatch
to manufacture convergence or nominal-quality passing. Retain all failures,
ineligible beta candidates, selected-refit failure and outer descriptive negatives.

Original blocked seed104729/group/buffer plan, compact dev-only observations,
all eight candidates x three folds, scoring/tie/minimum eligibility and one refit
stay unchanged. Original nominal family0/1 condition0/1 outer WRMS<=2 and model
volume-weighted RMSE ratio<1 remain frozen. No universal geology-quality claim
for null/deep/diffuse/two-depth/model-mismatch. Geometry alternatives, quadrature,
rank/nullspace/sensitivity, source/mask/covariance/Hessian/trace/nonclaim gates
still require actual results. No sealed observation or truth tunes this policy.

Existing96MiB input/256KiB exact metadata32768scalars/depth8/2048rows/4096cells,
64MiB G/32MiB C, projected2GiB,256MiB trace/output, one CPU process/one BLAS thread
and25 serial fits remain unchanged. New private diagnostics must be INCLUDED
inside that same trace/output projection and actual measured RSS; no extra budget.
Twenty nominal repeats, p95 peak<=70%of2GiB, actual peak<=2GiB, per-fit120 and
whole1800s cooperative caps remain; estimator is not a peak guarantee. Every
overrun/collection/environment harness error must be retained separately from
science. No GPU/host/runtime install or production execution claim.

## Tasks, authorization and handoff

- BS-A: persist ONLY new four-file docs/research packet, verify frozen9 SHA and
  historical receipts, documentation/source/artifact guards; send stable complete
  head. FULL MAIN read of all four plus exact changes and explicit approval needed.
- BS-B: after separate approval, append a new authority note and persist/push
  BEFORE test-first reds/code. Do not delete/move files to invent chronology.
- BS-C: implement only approved existing own module/three tests and additive
  evidence; collect all10 private diagnostics and every failure; scoped pin/push.
- BS-D: run all gates above plus original16/24/sealed/resource controls, actual
  source28/forward/canonical safeguards; separate all skips/reused unchanged runs.
- BS-E: MAIN detached full-source/test/packet/receipt review and independent4+16
  replays, candidate/sealed/rank/resources before any promotion. No merge/deploy.

Code/test/runtime/planner/forward/old9/source/canonical changes in BS-A: NONE.
BS-B..E are NOT AUTHORIZED/NOT RUN by this proposal. Broad M02, IRLS, field/API/
GPU/host/release remain unaccepted; no shared-owner changes or issue closure.
