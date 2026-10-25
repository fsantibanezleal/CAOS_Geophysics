# M11 supplied-survey integration status — 2026-10-25

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

## Online lifecycle audit — 2026-10-25

The integration boundary was rechecked against the current branch's app
assembly, authenticated project routes, processing API/worker, physical
classifier, private-byte accounting, project deletion, and the frontend API
client. The result is a hard integration gap, not a route-only task.

| Seam | Current evidence | Required before online M11 admission |
| --- | --- | --- |
| Authenticated intake and dataset index | `app/server.py` registers `projects` and `processing` only. The frontend expects `/joint-members` and `/joint-datasets`; no current router implements these. | Register an owner/project-bound intake and exact dataset-index transaction; enforce native metadata, rights, bounded streaming, request-rate limits, immutable source links, and rollback-safe file publication. |
| Solver job, cancel, history and result API | `app/processing.py` only admits its explicit current method set; `app/worker.py` dispatches the existing profile, waveform, MT and gravity-L2 children. M11 has no admitted job schema, child supervisor, cancellation drain, or result API in this branch. | Add M11-specific typed admission and dispatch under current queue/resource limits; bind input digest, code/runtime digest, worker identity and terminal states; persist all output copies and provide owner-scoped cancellation/history/export. |
| Physical startup/classifier custody | The current candidate calls `original_inventory` and `audit_snapshot` inside the classifier snapshot, declares raw/dataset/result/index bytes, and closes the final namespace census. A new registration fixture passes for a populated failed M11 job and exact stored copies. Startup reconciliation outside this classifier path still does not supply the same M11 reader proof. | Carry the exact reader through every startup/current-custody call site; test committed restart and unknown-file refusal under the live lease. |
| Quota and admission accounting | `app/physical_accounting.py` adds M11 retained members, terminal indices and active reservations only when passed the classifier's same-transaction audit token. The focused populated-state fixture verifies additive charges. Request-time admission and generic processing storage still do not use this M11 accounting path. | Bind request-time M11 reservations and completion writes to the same quota model; verify race, cancellation and retained failed-output accounting at quota boundaries. |
| Project deletion and retained debt | `app/physical_deleted_inventory.py` now detects M11 raw assets, datasets, jobs and child rows and refuses project deletion with `current_deletion_joint_custody_unrepresentable`; it no longer silently omits them. | Extend deletion receipts, custody slots, cleanup acknowledgements, retained-byte charges and restart recovery to M11 rows and every copy. Prove changed/unknown members block deletion without losing rows or files. |
| Database/migration lifecycle | The recognized current M11 tables are an explicit `0006_joint_artifacts` extension in `app/physical_schema.py`, but their nonempty state is intentionally unavailable to the serving lifecycle. | Mount the exact reviewed migration into the current chain only with forward/rollback policy and prove old database migration, startup, active jobs, quota and deletion behavior. |
| Runtime portability | The old PR154 `joint_execution.py` binds Windows paths, interpreter/site-packages and source hashes. It is a reference only; its child worker is not a current-branch Linux VPS runtime. | Implement and qualify a separately pinned supported worker runtime, or keep the API lane closed. Recheck executable, dependency, source digest, scratch, RSS, deadline and cancellation behavior on the actual target before admission. |

The PR154 implementation is not directly promotable: its APIs and ORM schema
are absent from this branch's current assembly; its generic derived-usage and
worker assumptions do not satisfy the current physical union; its deletion
and startup paths predate the current registered-reader refusal; and its
execution context is Windows-bound. Copying its route modules alone would
create an API that accepts/uploads data which current startup, quota accounting,
classification, or deletion cannot safely retain.

The online M11 API and worker remain fail-closed: no route was registered and
no scientific or public-activation verdict changed. The classifier now accepts
only M11 bytes closed by the dedicated same-snapshot inventory and complete
filesystem census; project deletion still refuses M11 state until its receipt
protocol can represent it. The populated-state regression is a custody and
accounting check, not solver or scientific acceptance. A separate route guard
records that the frontend's expected endpoint is not served. The remaining
seams must be closed before M11 online upload or compute can be advertised.
