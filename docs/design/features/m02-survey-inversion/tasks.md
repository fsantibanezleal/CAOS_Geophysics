# M02 staged work and main review request

Status: planned. Only this research/SDD sidecar is authorized. All implementation
tasks are unchecked; no independent numerical gate is currently passed.
Handoff base: develop `66952f32b6ce86d5a752cf56d3e4ca8481c8b4da`.

## Review packet

- [Research and unavailable-source record](../../../research/m02-survey-inversion-2026-10-03.md)
  and [source/version receipt](../../../research/m02-survey-inversion-evidence-2026-10-03.json).
- [19 EARS requirements](requirements.md), [design/ownership](design.md), and
  [exact gate/tolerance/control matrix](validation.md).
- Present diff must contain only `docs/research/m02-survey-inversion*` and
  `docs/design/features/m02-survey-inversion/*`. No shared API, environment,
  scientific producer, canonical data, ledger, main or deployment edits.
- Preserve original ignored 137-file FWI backup, candidates and all receipts
  indefinitely. They are not scratch for this feature or part of this PR.

## Decisions required before implementation

Main independently read all six research/design files on 2026-10-03 and checked
the versioned gravity API and pinned misfit/UpdateIRLS sources. This research is
suitable to merge as a **plan only**. CPU Geoana, separate Choclo/volume oracles
and explicit unit principles are approved. Broad local inverse implementation
is **NOT authorized**. Exact survey key/type/enum/asset bindings, locked seeds/
candidates/epsilon/null policy and pinned optimizer stopping mapping remain
unfrozen. The checks below are implementation decisions, not numerical passes.

Next separately reviewable unit is a design amendment for an ordinary pure
forward operator: exact typed request/result, six physical cell bounds, engine
units/frame/receiver restrictions and source/runtime pins, narrowly owned new
operator/test paths, no hooks or I/O. Only a full amendment read and explicit
main approval can authorize that unit; it does not complete M02 or authorize
inverse, survey admission, legacy-kernel, environment or canonical changes.

- [ ] Main reviews real SimPEG/Geoana CPU-first engine choice, separate Choclo
  oracle and physical quadrature/limits, exact float64 tolerances and pinned API
  semantics. No unsupported matrix-free/GPU claim.
- [ ] Main/M01 owner approves input schema and correction/CRS/vertical/frame/
  topography/uncertainty seam, provider-derivative admission and strict rejects.
  Resolve who supplies transformations and height-error propagation.
- [ ] Main reviews calibration/outer partition policy, minimum feasible survey,
  signed bounds, sparse-smallness scope, candidate budget and epsilon/stopping
  policy. Freeze numerical/control seeds and thresholds before test results.
- [ ] Main approves exact new code/test/CLI paths and dependency coordination.
  No edits to legacy producers or shared contracts without another scope review.
- [ ] Main/source owner chooses how to resolve eligible measured field evidence;
  keep current Bartlett failure. Main owns product upload/job/UI/course/host
  acceptance and any later ledger/version/canonical decisions.

## Dependency-ordered implementation milestones, pending authority

- [ ] A. M02 worker: strict new survey admission and immutable manifest/asset
  identity; tests/data/test_gravity_survey.py, M02-01 through M02-05. Obtain M01
  seam review first. Read existing M01 validator, do not rewrite corrections.
- [ ] B. M02 worker: new forward adaptor with actual required engine, float64
  sensitivities, activity/units/order and independent oracles; numerical gates
  M02-06, M02-07 and derivative part of M02-08. Include singular-domain policy.
- [ ] C. M02 worker: actual bounded L2 and official IRLS, source-pinned objective,
  epsilon/order/stop/state diagnostics and reference optimizer; remaining
  M02-08, M02-09 and M02-12. Persist failures before quality runs.
- [ ] D. M02 worker: buffered nested calibration, immutable outer holdout,
  matched methods, synthetic truth exclusion, all-data refit labels and actual
  uncertainty refits; M02-10, M02-11 and M02-13. Separate calibration from learned
  training, which is not-applicable here.
- [ ] E. M02 worker: paired local CLI, exclusive export/bundle replay, corruption
  negatives, other-data method docs and resource preflight/cancellation;
  M02-14, M02-15, M02-16 and M02-19. Main reviews publication/rights seams.
- [ ] F. M02 worker plus independent reviewer: full original 48-control/96-outcome
  matrix, all gates under M02-17, measured resource envelope and independent
  full replay at exact source/config; no canonical bake/import implicit.
- [ ] G. Source owner plus M02 reviewer: admitted measured survey receipt under
  M02-18. Missing required inputs means blocked, not synthetic substitution.
- [ ] H. Main: separately approved shared API/job upload, UI/course wiki and
  actual-host product acceptance. Local solver completion is not full M02.

Each milestone is scoped, self-reviewed and independently reviewed, tested in
proportion to risk, then committed/pushed to a task branch. No merge, main write,
release-version edit or deployment by this sidecar. A milestone failure retains
evidence and does not automatically authorize a changed threshold or source.

## Expected handoff receipts after code approval

For every executed gate: exact command, commit/module/config/environment SHA,
input SHA/rights, seed/partition, engine/version/precision, counts and negative
outcomes. For bundles: raw/normalized/model/prediction/residual/mask identities,
source-bound replay, history/status and private publication policy. For resources:
wall/RSS/scratch/threads/device, estimator-versus-measurement, p95 and explicit
limits/cancel/crash results. For field: admitted unit/datum/processing/error proof
and blocked outer evaluation, never a synthetic geological-truth claim.

Current ready deliverable is the reviewable plan only. Field bytes, numerical
performance, CUDA benefit and public-host/product gates remain unresolved or
NOT RUN as explicitly recorded in research/validation.
