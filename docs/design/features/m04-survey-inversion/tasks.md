# Dependency-ordered full M04 continuation tasks

This is an executable design task graph, not a method acceptance ledger.
The ordinary input/geometry foundation has executable verification gates; the
numerical/full-generation/integration gates remain unimplemented, not satisfied
by those foundation tests. No placeholder code is requested.
The product holds scientific definitions and implementation; private execution,
coordination and release records remain in management.

## Current implementation checkpoint : 2026-11-11

The source-bound sparse inner-surrogate path and sealed-fold IRLS driver are
implemented in `magnetic_optimizer_adapter.py` and `magnetic_calibration.py`.
Focused controls show the actual SimPEG frozen weights, objective, gradient,
Hessian and original quadratic operands agree; a two-parameter inner solve
converges through the registered M02 solver. On 2026-11-11, two S2-A
528-cell linear-TMI fold-0 diagnostics used a 600-second fit allowance and a
1024-phase ceiling, exceeding the bound M02 solver's reviewed 120-second and
512-phase policy. The prior-start run completed all eight epsilon stages, but
it is not method evidence. A second run began from a certified same-beta L2
solution and failed at epsilon `0.00625` with `zero_free_direction`; a repeat
under concurrent frontend-build load stopped at `wall_cap`. These over-budget
runs are retained only as diagnostics and do not pass a candidate fold.

A protocol-correct replay then used the certified same-fold, same-beta L2
initialization under the production 120-second fit deadline and 512-phase cap.
The L2 fit converged in 41.828 s. Sparse IRLS used its full 120.328 s allowance:
epsilon values 0.1, 0.05 and 0.025 converged, then epsilon 0.0125 stopped at
`wall_cap`. It used 12 conditioning phases and remained below the recorded
allocation ceiling. This is a valid resource-limit failure receipt, not a
candidate pass; see `validation.md` and the matching evidence summary.

The sparse-fold API now requires a converged, certified L2 result with matching
beta, fold, source inventory, geometry and fitting rows; the profile runner
performs that L2 fit first. T43 remains open: the 16-candidate, three-fold matrix, nested selection,
development refit, immutable freeze and one-time sealed evaluation have not
run. No candidate score, field truth, outer evaluation or method acceptance is
claimed. The full source-bound diagnostic runs are external to Git under the
configured device data root; their exact relative paths and hashes are in
`validation.md`.

Earlier 120-second/512-phase failures and the 120-second phase-sensitivity
failure remain historical diagnostics in `validation.md`. The product fit API
and profile runner now use the bound M02 120-second deadline and 512-phase
limit. The sparse API requires a converged, certified L2 result with matching
beta, fold, source inventory, geometry and fit rows before it can run. The
production-limit replay is now recorded, but a passing candidate fold remains
to be completed before matrix execution.

## T41: source/protocol and geometry foundation

Requirements R-401..404, R-413.
Fully review these seven files, closed schemas and source semantics. Test-first
byte/token/depth/duplicate/descriptor/count attacks and physical eligibility.
Implement magnetic_survey_json.py and magnetic_survey.py only after that review.
Freeze geometry-only S2 fixture before any magnetic values; assert full inventory,
exact twelve units/fold memberships, buffer equality and ID/hash determinism.
Preserve P04 source/tests and all original private data.

Deliver owned source/tests/wiki explanations together, exact tested commit and
private real execution receipts. No engine needed for parsing/planning.
A metadata PASS is not numerical/field/upper-profile acceptance.

## T42: accepted core boundary and physical likelihood

Requirements R-405..408.
Bind the reviewed M02 mathematical core's ACTUAL accepted source pin/export/
epoch/result stops/precision/budgets to algorithms section5. This is a mandatory
dependency amendment, not a request to reimplement its private gravity problem.
Current unbound null fields must reject before the engine.
Resolve both linear and nonlinear GN lanes explicitly; linear acceptance alone
cannot authorize exact-magnitude inversion.

Read-only verify existing runtime/source/native/transitive pins, no install.
Test-first real SimPEG component/J composition, independent Choclo unit-SI,
nonlinear direction/adjoint, Decimal80 tiny norms, full-covariance principal
whitening, regularization topology/units and independent BVLS controls.
Implement magnetic_inverse.py and magnetic_optimizer_adapter.py through the
accepted core; no fallback/copy/ignored failed convergence. Wiki documents actual
runtime/algorithm/limits in same scientific unit.

## T43: actual L2 and sparse calibration

Requirements R-408..412.
Execute all frozen beta/penalty/fold candidates through accepted optimizer.
Add actual SimPEG Sparse unscaled weights, positive epsilon schedule, fixed beta,
true sparse objective and refreshed final certificate. Null/tiny near-zero,
lower/upper release and alternate starts must genuinely converge or fail.
Finish geometric nested selection, final development fit, immutable generation
freeze and one-time sealed evaluation. Persist actual predictions/residuals/
metrics/history, not invented examples. No tuning after outer evaluation.

## T44: independent acquisition, resolution and resource controls

Requirements R-412..413.
Add magnetic generation only after geometry fixture sealed. Use Choclo independent
off-grid heterogeneous bodies and six frozen regimes, both scalar and vector
quantity lanes. Preserve remanent/wrong-field inability-to-discriminate outcomes,
sparse-worse-than-L2 comparisons, null and insufficient geometry.
Measure declared small/nominal/upper native controls only within separately
accepted containment authority. Maintain accepted M02 stop/cap thresholds.
Publish hash-bound scientific artifacts, no field truth/geological certainty.

## T45: real local user-data tools and durability

Requirements R-414..415.
Implement run_magnetic_survey.py local commands and magnetic_survey_bundle.py
through existing raw/provenance contracts. Commands consume user bytes, declare
source+physical metadata, produce actual fits, evaluate/export/reimport and
reproduce hashes. Include negative/cap/non-success exit tests and complete
worked wiki commands. No HTTP/default license/correction guesses.
Run interrupted Windows/local generation tests and honest filesystem-limit
documentation, then owner-scoped hosted persistence integration review. Off-host
restore/mail are not owner-tested-stage prerequisites under product SDD section8.

## T46: full field/user-data/API/view/course vertical

Requirements R-416..419.
Coordinate only through management with existing API/auth/jobs/frontend owners.
Bind sourceID/configHash/result bundle to existing typed contracts and native
admission; no competing server/auth/ownership. Local and replay lanes remain
truthfully labelled until online contained execution passes.
Rights/quantity/time/height/datum/uncertainty/source-fullness must clear the real
field gate; record unresolved acquisitions and parent full-survey obligations.
Complete linked map/line/residual/chi volume/slices/sensitivity/resolution/history/
applicable spectrum, EN/ES course/wiki, theme/native-profile/user-data parameter
reactivity, pointer navigation, original-row display and export flows.

## T47: full convergence and integration

Requirement R-420 and ALL preceding gates.
Enumerate each exact named test/result/hash independently, including failures,
not-run, ineligible and unresolved dependencies. Compare full accepted M04 scope
to source, tests, field matrix, user-data local/API, durability, UI/course and
online/native profile. A bounded forward or synthetic inverse pass does not
close method/product/deployment. Merge/release/host cutover remain the separate
MAIN-owned product workflow; this task creates no deploy authority.

## Required unresolved binding decisions, not implicit defaults

1. Actual accepted M02 generic source/export and precision/stopping mapping,
including nonlinear exact-magnitude GN support.
2. Existing provenance typed correction-parameter retrieval for admitted M03
processed values, not merely a parameter hash.
3. Existing hosted job/result ABI, durability/ownership/native admission and
resource feasibility. Local design does not choose new auth/endpoints.
4. Full provider field rights/acquisition/offline coverage and appropriately
reported predictive comparisons. No field acceptance from authored S2.


## 2026-11-11 preflight reuse follow-up

A validated source-bound metric object and its allocation proof are now reused
within each active-face direction instead of being rebuilt before the native
solve. Focused controls and the M04 current-source suite pass. The production
512-phase cap still refuses the first sparse fold after 87 accepted steps. A
separate process-local 1024-phase diagnostic reaches four complete epsilon
values and times out during the fifth at the unchanged 120-second limit. The
results and exact identities are recorded in
[`validation.md`](validation.md#2026-11-11-active-face-preflight-reuse-performance-diagnostic).
This is not a sparse-method pass; optimize the repeated active-face work under
the existing caps before starting the candidate matrix.

## 2026-11-12 certified no-op line-search stop

The original physical optimizer now catches only the native
`zero_free_direction` failure raised for a zero direction or a rounded
no-displacement line-search trial. It can terminate at the unchanged recorded
state only when the source-bound original-objective terminal proof passes. The
outer solve still checks exact equality with its final recorded state and
re-evaluates the objective. A refused certificate retains the native failure;
it does not become convergence. The previous same-beta production replay
failure is superseded for this one fold by the exact-commit replay in
[`validation.md`](validation.md#2026-11-12-source-exact-same-beta-sparse-fold).

That fold is still only one of the required candidate folds. T43 remains open:
the full candidate/fold matrix, selection, final development refit, frozen
generation, sealed evaluation and independent-acquisition controls have not
run. No method, field, hosted or release claim follows from this single
synthetic development fold.
