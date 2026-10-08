# M02 result inspection and user-data mounting design

Status: proposed; no new route, worker method or UI is activated by this document.

Prospective owned implementation is authorized by the full M02 continuation;
source/host/online mounting remains separately reviewed. Corrected cpu2 uses
the same inspection wire, explicit fit runtime_epoch/policy and auxiliary/native
phase labels. A safeguarded anchor has an auxiliary merit observation, NOT a
fixed-inner physical objective row; its phi/KKT/LS/CG fixed-stage fields are null.
Actual initialization/native frames carry their ORIGINAL trace metrics.
Frame metrics and terminal metrics are separate, each with explicit stage.
Stage book retains zero-step scheduled observations, epsilon, weight/operator
identities, actual inner reason and canonical audit availability. Actual
auxiliary CG scalar count/residual/timing rows are separate from native counts.
No new score/objective/tolerance or field/native claim is introduced by JSON.

Implementation order starts with whole native replay and isolated owned JSON
producer. Legacy L2/cpu1 and corrected cpu2 readers remain distinct. Unstarted
fits have zero actual states, null frame/density/metrics/predictions. All eight
candidate/24fold verdicts remain visible; failed final refit is never substituted.
The UI consumes published shared-shell0.8.1 (verified available), not local
copies of base components. Owner/source/host mounting is still closed until
its dedicated leaf/auth/worker/rendered gates pass; no MAIN edits or activation.

## Boundary

The admitted native workflow is authoritative. The display projector consumes a
`gravity-calibration-archive-1` through `gravity_workflow_io.verify_calibration`.
It never accepts a prepared simulation, objective callback or web-provided path.
The stored archive remains the lossless export; display JSON is an explicitly
bounded projection, not a substitute for replay or a portable scientific input.

The current original nonnull IRLS gate fails despite all 21 converged inner
solves. Its failed terminal state is inspectable, never accepted. L2 acceptance
does not authorize IRLS, field, API or host acceptance. Neither a successful
archive replay nor a clean wire parser removes these literal distinctions.

## Proposed display wire: `geophysics.gravity-survey-view/v1`

This version is M02 gravity-only. It is not a common M02/M11 result DTO: M11
uses two physical properties, 26 fits, up to 251 states and a different residual
convention. Its exact-Hv and PSD search-Hv identities remain in its own contract.

Exact top-level fields:

- `schema`, `method` (`l2` or `irls`), `calibration_sha256`, `plan_sha256`.
- `selection`: `status`, nullable `selected_index`, exactly eight `candidates`.
  Each candidate retains index, beta, eligibility, nullable score, reason and
  exactly three fold verdicts (fit index, status, reason, nullable validation
  score). Failed scores are never averaged away.
- `fit`: index 0..23 for candidate/fold order or 24 for the selected development
  refit; status, reason, accepted-state count, nullable frame index, actual
  terminal metrics, fit rows, validation rows and exact beta_candidate/beta_engine.
  `fit_sha256`, `frame_model_sha256` and `recipe_sha256` bind the immutable
  original fit, displayed native model and fixed objective/stage recipe. Each
  displayed metric names its original stage and frame; changing-stage terminal
  metrics are not attached to an earlier accepted frame.
  A nonexistent final refit rejects fit 24; it does not return candidate zero.
- `cells`: physical active indices, bounds `(a,6)` metres in the native declared
  order, nullable density `(a,)` kg/m3. Empty history has null density and frame.
- `stations`: development rows only, stable IDs, partition-group IDs, receiver
  `(m,3)` metres, observed `(m,)` upward mGal, nullable predicted `(m,)` upward
  mGal and observed-minus-predicted `(m,)` mGal at the selected actual frame.
  `residual_convention` is exactly `observed_minus_predicted`; acceleration unit
  is exactly `mGal`, vertical sign exactly `upward`. These are parser-checked
  values, not inferred from chart labels or another method's convention.
  Predictions use the pinned physical forward engine after whole-archive replay.
  A previewed unsuccessful model remains unsuccessful even if its prediction is
  finite. Outer coordinates may be shown in a separate geometry-only overlay;
  outer observations/residuals are never included in this calibration wire.
- `history`: actual accepted indices and native phi_d, phi_m, phi_engine, KKT,
  LS/CG counts. IRLS includes actual stage indices and independently replayed
  stage-book records, terminal stage metrics and actual changes. Stage transitions
  with no accepted step remain in the stage book. No claim of monotone objective
  across different IRLS weight/epsilon stages; terminal metrics need not equal
  the last accepted row's changing-stage metric.
- `warnings`, `scope`: exact source-verification requirement, no geometry-error
  propagation, `field_eligible=false`, `full_M02_accepted=false`,
  `API_accepted=false`, `host_accepted=false`, `GPU_accepted=false`.

One packet contains one fit and one recorded frame, at most 4096 cells, 2048
stations and 201 accepted states. Maximum encoded UTF-8 is 4 MiB. Whole native
256 MiB result/96 MiB request guards run before projection; the JSON cap is a
separate transport guard and does not loosen scientific/native guards. Strict
TypeScript parsing checks complete nested keys and lengths, not a type cast.
Unknown units, versions, forged successful scope or partial score tuples reject.

An independently verified evaluation has a separate view and identity; outer
metrics are never joined into a calibration packet or used to alter its model.
Actual 32-refit output also has a separately replayed packet with all 32 literal
verdicts and model samples; any derived spread must name its conditioning recipe,
successful sample count and failures. No synthetic truth is a practitioner API
field or inferred from density samples.

## Practitioner API / worker integration proposal

Reuse the existing project raw upload, source record, normalized dataset and
`POST /api/projects/{project_id}/jobs` lifecycle. Add method admission to that
registry, not a second queue. The exact method identifiers and normalized
dataset schema require main/controller review together; existing MAD station
flagging is not gravity anomaly correction or M02 inversion eligibility.

Admission must bind owner/project/raw hash+byte count, rights, correction state,
processing/normalization/transform hashes, coordinate and height datums, physical
mesh and receiver geometry, masks and stable groups, explicit SD/SPD covariance,
prior/bounds/reference and frozen policy. Unknown error scale, CRS or applied
correction rejects. Outer measurements stay in an inaccessible sealed object
until model/selection identity is frozen. No default percentage error, presumed
flat topography or web-generated field eligibility is introduced.

The worker executes the native CLI in a child with external private per-job
storage, one-thread policy, original wall/step/line-search limits and actual
RSS/scratch/tree termination. A failed scientific run still stores a complete
failed result where available; it does not become `succeeded` because an archive
exists. Successful execution, scientific success and host admission are separate
fields. Existing cancellation/owner recovery is reused, not reimplemented.

`GET /api/projects/{project_id}/jobs/{job_id}/result` selects this view by the
admitted method and stored result identity. Bounded fit/frame query parameters
are inspection controls only. Storage keys remain internal and derive from
owner/project/job UUIDs. Full export downloads the verified lossless bundle
through the existing owner route. Read authorization precedes archive access;
CSRF, cookies, no-store and relative-URL checks remain ApiClient responsibilities.

Full numerical replay belongs in a separately bounded worker operation, not
the FastAPI event loop or an unbounded GET. Any verified projection cache must
bind the complete original archive/member inventory, original request/result,
current defining product/vendor source inventory and runtime, complete replay
verdict and fit/frame/recipe identity. Authorization precedes cache lookup as
well as archive access. Cache invalidation and replay limits require actual
measurements and negative tests before online mounting. No stored digest alone
proves execution authenticity, source permission or scientific success. Replaying
an existing trace does not restart its original solve budget or create new steps.

No public endpoint is added until actual Linux host qualification and the source
admission contract are accepted. Windows measurements are evidence for the local
CPU lane, not a Linux RSS upper bound or permission to open online submission.

## Isolated UI and mount proposal

Owned leaf modules: `gravity-survey-contracts.ts`, `gravity-survey-client.ts`,
`GravitySurveyWorkbench.tsx`, `GravitySurveyCourse.tsx` and physics-only
`GravityDensityView.tsx`. The controller mounts them beside the existing mode
dispatch using one reviewed import/branch change; no shared Workbench replacement.

Consume the governed shared base (currently exact 0.8.1), including CaseWorkbench,
PlotCard, Stage, Readout, UPlotChart, shell controls, formatting and citations.
The owned checkout currently pins 0.6.8; upgrading the shared base is a reviewed
integration prerequisite, never a reason to copy or restyle its new components.

Question groups: stations (observed/predicted/residual and linked station map),
density (physical slices and optional true 3D cell view), selection (all failed
and successful candidates/folds), solve (fixed-stage history and stage book),
refits (conditional actual evidence); the sixth shell group is Context/course.
Zoom/pan/reset, brush, readouts, keyboard selection, full underlying data tables,
physical units, EN/ES and both themes are measured on actual native-produced
packets. Stage/frame selection is labelled replay inspection, not a new solve.
Run parameter changes require a fresh admitted owner job, never front-end model
arithmetic. Course sections cover quantity/correction state, geometry/sign/units,
objective and whitening, buffered selection/embargo, IRLS changing weights and
fixed-point failure, frozen evaluation and nonuniqueness/conditional refits.

The mounting patch is supplied only after leaf gates and rendered actual-data
tests pass. An unmounted component, fake API fixture, decoded archive or green
typecheck alone is not full practitioner-workflow acceptance.

## ADR fit and failure conditions

ADR-0069: all numerical work remains in real native engines; the web is a
consumer. ADR-0075: review this unit before code. ADR-0078/0071: consume the shared
base, viewport layout and measured charts, no local substitutes. ADR-0011/0012:
EN/ES and light/dark. ADR-0044: existing owner authentication only. Original
negative controls, precision failures, scientific budgets and weights remain
unchanged. A failed original IRLS positive blocks IRLS scientific acceptance;
it does not block honest inspection of that failed archive or independent L2.
