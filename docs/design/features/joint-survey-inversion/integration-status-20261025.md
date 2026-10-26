# M11 supplied-survey integration status: 2026-10-25

## Implemented and validated locally

The current product branch contains the closed native input contract, geometry
and mask planner, public gravity and magnetic forward operators, weighted
joint objective, exact cross-gradient and Hessian paths, separately optimized
uncoupled references, conditioned public baselines, sealed selection and
evaluation, private serialization/replay, bounded CLI workflows, and the
frozen 24-case control matrix. Reproduction entry points are
`scripts/run_joint_survey.py`, `scripts/validate_joint_matrix.py`,
`scripts/validate_joint_precision.py`, and
`scripts/validate_joint_resources.py`.

The executable receipt is
[`m11-final-precision-20261025.json`](evidence/m11-final-precision-20261025.json).
Its numerical artifacts were generated outside the repository at
`E:\_worktrees\_runs\CAOS_Geophysics-M11-integrated-20261025`.

| Gate | Observed result |
| --- | --- |
| Focused numerical regression | 451 tests; 446 passed, 5 skipped, 0 failed, 0 errors |
| Actual workflow matrix | 24 of 24 complete; all 24 sealed replays validated |
| Candidate status | 524 converged, 100 nonconverged, 0 engine failures; nonconvergence retained |
| Independent exact-face comparison | 343 converged candidates passed all four predicates; 41 nonconverged retained; 0 reference-stationarity failures |
| Maximum-count resource gate | 4,096 full cells, 1,932 active, 2,048 receivers per modality and full covariance; active-count plus one rejected |
| Maximum-count replay | Validated; peak sampled RSS 464,322,560 bytes during replay; no scratch growth observed |
| Linux CPU regression | 488 passed, 3 skipped across the M11 numerical suite and M04 magnetic forward controls on CPython 3.12.10 x86_64; platform-specific SimPEG, discretize and SciPy source pins recorded in [`runtime-linux-cp312.json`](runtime-linux-cp312.json) |

The matrix tests co-structural, disjoint, flat/null and wrong-field regimes at
dense, sparse-blocked and shifted geometries, including diagonal and full
covariance. A positive coupling was selected in each case, but this is not a
claim that joint inversion improves every regime: the held-out selection,
nonconverged candidates and truth diagnostics remain separately available.
All outputs remain synthetic controls. `field_eligible`,
`scientific_precision_accepted` for the overall matrix, and `public_activation`
remain false by design.

The Linux run verifies the named regression suite against the Linux CPU source
epoch. It does not yet rerun the full 24-case sealed workflow matrix, the
maximum-count resource workflow, or the independent precision receipt on Linux.
The RTX 4070 exists on the Windows development host; M11 remains a measured CPU
lane and makes no GPU performance or VPS-capability claim.

The browser importer is now pinned to the exact current
`physical_nonlinear_optimizer.py` source bytes. `frontend/scripts/verify-joint-pins.mjs`
checks the browser pin against both the optimizer source and the M11 adapter
before every production build. The real-artifact browser import, input, and
result views pass 46 focused tests; eight are conditional on optional component
fixtures. Two additional hash-admission tests still require the retained
maximum-size external output fixture.

## Product integration still open

The local solver and CLI do not yet complete the online workflow. The current
FastAPI assembly does not register the M11 joint-member, dataset, job,
cancellation, custody-history, or result-export routes expected by the
frontend's `JointProjectWorkbench` and `JointCustodyApi`. The frontend's
actual-Python custody tests therefore correctly fail closed when no real API
receipt is supplied. Do not call uploaded-survey M11 available online until
those routes are integrated with the current account/project ownership,
bounded worker, migration, storage and result-custody paths and pass the real
Python API/browser contract tests.

This work does not change the whole-product SDD convergence ledger. It does not
close field-data rights/validity, broader M01–M13 submitted-data coverage,
complete browser visual acceptance, current VPS resource admission, or the
single-origin replacement cutover. No deployment was performed.

## Online lifecycle audit: 2026-10-25

The integration boundary was rechecked against the current branch's app
assembly, authenticated project routes, processing API/worker, physical
classifier, private-byte accounting, project deletion, and the frontend API
client. The result is a hard integration gap, not a route-only task.

| Seam | Current evidence | Required before online M11 admission |
| --- | --- | --- |
| Authenticated intake and dataset index | `app/joint_routes.py` now contains owner/project-bound member upload and immutable dataset indexing. The router mounts only inside the explicit physical assembly and each handler requires the exact M11 0006 schema identity, current custody classification, quota and writer lease. A Linux candidate-runtime integration test uses the exact 0006 migration capsule and production `PrivateFiles`: all authored members upload byte-exactly, dataset creation and receipt readback pass, and every receipt remains `scientific_accepted=false`. | The 0006 migration is still an unmounted candidate, so the ordinary serving chain cannot admit this route. The isolated test does not prove production startup/restart, assembled project deletion, crash recovery, owner crossover negatives, or VPS admission. Complete those release gates before enabling the route. |
| Solver job, cancel, history and result API | `app/processing.py` only admits its explicit current method set; `app/worker.py` dispatches the existing profile, waveform, MT and gravity-L2 children. M11 has no admitted job schema, child supervisor, cancellation drain, or result API in this branch. | Add M11-specific typed admission and dispatch under current queue/resource limits; bind input digest, code/runtime digest, worker identity and terminal states; persist all output copies and provide owner-scoped cancellation/history/export. |
| Physical startup/classifier custody | `classify_startup_snapshot` delegates to `classify_snapshot`, and `audit_startup_participating` invokes that wrapper while holding the startup participant lease. The populated-state registration fixture passes for a failed M11 job and exact stored copies. Request-time publication and committed-restart M11 receipts remain unqualified. | Exercise the exact M11 reader through committed restart and unknown-file refusal under the live lease; qualify startup receipts on the supported Linux runtime. |
| Quota and admission accounting | `app/physical_accounting.py` adds M11 retained members, terminal indices and active reservations only when passed the classifier's same-transaction audit token. The focused populated-state fixture verifies additive charges. Request-time admission and generic processing storage still do not use this M11 accounting path. | Bind request-time M11 reservations and completion writes to the same quota model; verify race, cancellation and retained failed-output accounting at quota boundaries. |
| Project deletion and retained debt | The versioned M11 tombstone/custody projection now binds source originals, dependencies, terminal indexes (including failed/cancelled indexes), and every result member. Structural API tests exercise prepare, transfer to the retained receipt, restart classification, and rejection of changed originals/indexes/members. The project DELETE route's real native filesystem move, cleanup acknowledgements, and crash cuts are not yet qualified with M11 data. | Exercise the same projection through the assembled authenticated DELETE route and actual `PrivateFiles` storage on the supported Linux runtime; test each cleanup ordinal, missing/changed member, and process restart before releasing M11 online. |
| Database/migration lifecycle | The recognized M11 tables remain an explicit `0006_joint_artifacts` candidate in `app/physical_schema.py`; the new route test builds that candidate only in an isolated database. | Mount the reviewed migration into the serving chain only with forward/rollback policy and prove old database migration, startup receipts, active jobs, quota and the actual deletion route. |
| Runtime portability | The old PR154 `joint_execution.py` binds Windows paths, interpreter/site-packages and source hashes. It is a reference only; its child worker is not a current-branch Linux VPS runtime. | Implement and qualify a separately pinned supported worker runtime, or keep the API lane closed. Recheck executable, dependency, source digest, scratch, RSS, deadline and cancellation behavior on the actual target before admission. |

The PR154 implementation is not directly promotable: its APIs and ORM schema
are absent from this branch's current assembly; its generic derived-usage and
worker assumptions do not satisfy the current physical union; its deletion
and startup paths predate the current registered-reader refusal; and its
execution context is Windows-bound. Copying its route modules alone would
create an API that accepts/uploads data which current startup, quota accounting,
classification, or deletion cannot safely retain.

The online M11 worker remains fail-closed and no scientific or public-activation
verdict changed. Before the candidate route implementation, a route guard
recorded that the frontend's expected endpoint was not served. The remaining
worker, startup/restart, deletion and VPS seams must be closed before M11 online
compute can be advertised.

## Candidate intake and indexing implementation: 2026-10-25

The branch now has an isolated intake/index router and a successful authenticated
API test against the exact allocated 0006 candidate migration. The test runs on
Linux with the production descriptor-relative `PrivateFiles` implementation,
uploads each member in the external authored `joint-control-00` input fixture,
checks exact hashes and private storage, creates the structural dataset, and
reads its receipt back. A separate `write_new_stream` primitive publishes a
bounded upload spool without copying a potentially 256 MiB member into Python
memory; its Linux test checks digest, byte cap, permissions and retained partial
file behavior. The focused custody/source suite and these new tests pass 62
checks together.

## Candidate job lifecycle and deletion implementation: 2026-10-26

The isolated candidate now mounts owner-scoped M11 job, cancel, result and
export routes in the explicit physical API assembly. They share native intake's
exact 0006 schema, custody, quota and lease checks. A dedicated worker claims
only M11 jobs, invokes the pinned Linux workflow CLI, replays its output, exports
the post-freeze state instrument, validates that instrument, and publishes
terminal index and member copies in one transaction. Browser and API contracts
now agree on the history schema, stored ZIP index name, byte-preserving archive,
and the explicit infrastructure-failure record. The candidate API tests cover
queue saturation, cancellation publication, failed terminal export, project
deletion with a retained result, and cross-project denial. They use a controlled
publisher for terminal states and do not substitute for the separate real
solver and instrument workflow run.

The authenticated project-delete route was exercised against POSIX private
storage for a source-only M11 dataset. The test verifies raw and index hashes,
both project-tree moves before cleanup, committed receipt ordering, cleanup,
restart reconciliation, and tampered-source refusal. A separate failed-result
case verifies deletion of the terminal index and native failure member and
their digests in the committed deletion receipt. Result-bearing restart and
the cleanup crash-cut matrix remain unqualified.

A fresh current-source Linux CPU run was generated from the external development
and sealed inputs, then independently validated. The post-freeze state
instrument was exported and replay-validated from that exact fresh output. Its
workflow/index data remain outside Git under
`E:\_worktrees\_runs\CAOS_Geophysics-M11-integrated-20261025\data`; the
reproducible receipt, hashes, resource samples and nonclaims are recorded in
[`m11-fresh-workflow-20261026.json`](evidence/m11-fresh-workflow-20261026.json).
The real artifact browser-import test passes on the instrument bundle, and the
actual Python API archive test passes on the terminal failure receipt. This
does not exercise the deployed VPS worker process.

These are isolated candidate-schema results. Revision 0006 remains an unmounted
migration candidate, so the normal deployed database cannot pass the job route's
exact schema gate. The M11 worker has no installed service unit and is not
running. Request-time active-job quota accounting, memory and scratch
enforcement, committed result restart/deletion receipts, the full API/browser
contract, actual-host capacity and the single-VPS cutover remain open. Nothing
here changes M11 scientific acceptance, R-008, whole-product acceptance or
deployment status.
