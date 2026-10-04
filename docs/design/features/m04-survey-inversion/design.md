# Full induced survey inverse design

This is a proposed continuation to the [product SDD](../../SDD.md), not code
authorization or a report of implemented inversion. It includes L2 and sparse
fitting, user-data tools, persisted results, field evaluation and linked views.
P04 physical source and tests are not modified by this proposal.

## Data flow and separation

Bounded bytes -> closed native-independent document validation -> original
inventory and physical eligibility -> geometry-only seal -> independently
validated uncertainty -> development-only fits/validation -> frozen candidate
-> development refit -> single sealed evaluation -> durable generation ->
linked local/replay/eligible online result. No stage downloads a provider asset.

The planner receives the geometry document without values or uncertainties.
The fitting adapter receives compact rows for only its fold and never a full
survey object containing outer data. A scorer has validation observations but
cannot return their values to the solver. The sealed evaluator is unavailable
until a candidate and final-model hash have been durably frozen. Refit retains
development rows only; outer scores never select an alternate beta, start, mesh,
mask, field or regularizer. Any new choice requires a new labelled study/seal.

Arrays passed between local stages are independently owned, C-contiguous,
write-protected snapshots, not tamperproof memory. Persisted hashes and retained
original bytes establish durable identity. No renderer-modified array may become
trusted calibration state.

## Owned implementation seams

| Proposed module | Responsibility | Forbidden dependency |
| --- | --- | --- |
| magnetic_survey_json.py | stdlib byte/token/depth/duplicate/type/canonical parsing | NumPy, SimPEG, filesystem side effects during parse |
| magnetic_survey.py | geometry, metadata eligibility, IDs/QC, exact seal, preflight | observed amplitudes, uncertainty values, solver |
| magnetic_inverse.py | actual physical G, quantity composition/J, WLS/Sparse, fit/score/refit | alternate prism kernel, IGRF, guessed corrections |
| magnetic_optimizer_adapter.py | verify and compose accepted M02 mathematical core | gravity-private constructors, copied optimizer |
| magnetic_survey_bundle.py | bounded arrays/manifest/hash roundtrip, local atomic generation | auth, hosted secrets, provider acquisition |
| run_magnetic_survey.py | explicit local source/config/output commands and non-success exits | implicit HTTP, install, native controller activation |

The accepted M02 binding is required to supply reviewed objective/gradient/GN
callbacks and convergence certification. Its accepted source pin and public
export are currently unavailable. algorithms defines the needed mathematical
boundary; no placeholder implementation or unreviewed vendor default fills it.
A reviewer must bind that boundary to the accepted M02 core before inverse code.
Other source-definition, byte, geometry and independent-oracle tests can be
designed without pretending that dependency passed.

Actual SimPEG 0.25.2, Geoana 0.8.1, discretize 0.12.0, NumPy 2.2.6,
SciPy 1.15.2 and Choclo 0.3.2 remain the existing reviewed environment.
No install/new dependency. Extended regularization/transitive source/native pin
closure must be checked read-only before execution; a matching version alone
does not certify loaded machine code.

## Physical lanes and fits

Three quantity-specific lanes share actual secondary-vector G. Linear TMI and
secondary vector are linear in chi. Exact total-field anomaly is a nonlinear
scalar composition whose derivative is the total-vector direction, not f.
The exact lane needs a certified nonlinear GN binding; an accepted linear-only
M02 seam cannot authorize it by implication. Both lanes remain required.

Each frozen beta gets L2 and sparse candidates. Inner folds use identical row
memberships/noise definitions. Sparse begins from the converged L2 candidate
for that same fold/beta, never from a held-out or truth-derived model. The
start/reference and lengths are user-explicit and sealed before values.
We retain L2 as a baseline even if sparse is selected. No empirical feature
normalization, depth weighting, learned model or geology prior is smuggled in.

## Lanes and resource proposal

Ordinary local fitting caps: 2048 original rows, 4096 full mesh cells, 2048 active
cells, 3*N*A <= 12582912 kernel entries; full covariance D<=512. The conservative
byte bound in contracts is additional, not interchangeable with these counts.
Fits are sequential. Release upper profiles must measure complete process peaks,
copies, BLAS workspace, covariance and history; raw G bytes are not RSS.

Proposed online sub-profile: N<=512, A<=256, full cells<=4096, D<=1536,
covariance D<=512, same schemas and algorithms. One physical worker, no GPU.
Proposed per-job ceilings are 60 s wall, 30 s whole-child CPU, 768 MiB RSS,
1 GiB private committed memory and 512 MiB scratch. Under current product SDD
section8, owner-tested admission uses measured byte capacity for the candidate
release, current plus two rollback releases, retained project bytes and configured
scratch, together with configured worker-memory admission without exhausting the
shared host. No whole-host percentage threshold, off-host backup/restore or
provider SMTP prerequisite applies to this stage. Historical failed receipts
remain historical; this policy change does not turn them into passes.
These are testable proposed ceilings, not
observed feasibility or authority to activate OS/native controls. Offline full
Charleston processing needs a separate full-file workflow and capacity review;
this bounded local/online design cannot silently satisfy it.

An exhausted candidate is failed, not converged; scores do not average failures
away. A per-job budget may make a survey ineligible even below geometric caps.
Cold and warm, null and upper cases are all required. Online remains CLOSED until
the native-controller/job ownership/recovery/auth seams and these profiles pass.

## Explicit local tool contract

Proposed commands, not currently executable examples:

```text
python data-pipeline/run_magnetic_survey.py validate --request survey.json --original raw.bin --output inventory
python data-pipeline/run_magnetic_survey.py calibrate --request survey.json --original raw.bin --output generation
python data-pipeline/run_magnetic_survey.py evaluate --request survey.json --original raw.bin --frozen generation --output evaluated
python data-pipeline/run_magnetic_survey.py export --generation generation --output exported
python data-pipeline/run_magnetic_survey.py import --bundle exported --output imported
```

Every flag shown is mandatory and exact; unknown flags reject. File paths are
caller-explicit local I/O capabilities, not request JSON values or downloads.
Original source is read-only streamed/hash-checked, capped at128 MiB for this
bounded tool. Bigger originals are ineligible here; the parent full-survey
offline obligation remains open. Input JSON8 MiB and bundle128 MiB caps apply.
Output must be a new directory; no overwrite of source or existing generation.
validate emits original inventory/eligibility and geometry seal without kernel.
calibrate executes all candidate/refit/evaluation stages, not a saved replay.
evaluate requires a frozen bundle with matching seal, model/config and likelihood
hashes; it neither fits nor retunes. export/import verify all bundle members and
rights before copying. Source bytes are never bundled implicitly.
Exit0 only complete requested operation,2 invalid/ineligible input or dependency,
3 numerical/convergence failure,4 resource/cancel failure,5 durability failure.
No partial numeric output receives exit0. A machine-readable closed error/result
is written when safe; parse failure exposes no user observations in stdout.
Internal exception traces remain private, not public result metadata.

Local acceptance means genuinely executing these commands on at least two
nonidentical owner-supplied controls and roundtripping their actual outputs;
merely publishing this recipe or invoking validate does not satisfy R-414.

## Existing product integration, not a second app

MAIN owns API/auth/jobs/persistence/frontend and deployment. The local adapter
returns the closed magnetic bundle and job-state descriptors, not its own web
server. Account-scoped uploads and jobs use existing project ownership; method
rights decisions never imply user authentication. Quota rejection leaves the
old successful generation intact. Replay loads an attributed bundle; a local
tool consumes original user bytes; online execution is separately admitted.

The six established routes remain unchanged. An accepted result selected in App
drives the same original-ID map, line, residual, physical chi 3D/slices, coverage,
history and spectrum selectors. No lifecycle top-level routes, replay animation
masquerading as solver progress or shell primitives invented by this feature.
Shared EN/ES language and light/dark tokens govern inline SVG and course content.
Standalone SVG cannot inherit parent CSS; exact documented published-token
fallbacks must accompany it if used.

## Kill criteria and scope truth

Stop on wrong sign/order/unit/J, hidden outer-data access, zero epsilon,
unwhitened full covariance, false optimizer convergence, insufficient geometry,
undeclared field/correction/rights or any uncontained process. No waiver by
small residual, attractive geology, metadata-only cap or browser screenshot.
A complete method requires every requirements gate; no synthetic control alone
establishes field validity. The original forward component acceptance remains
separate from inverse, field, durability, online or deployment gates.
