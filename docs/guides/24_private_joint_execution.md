# Private joint gravity and magnetic workflow

## Scope

This path stores immutable native inputs and outputs for the M11 joint
gravity/magnetic inversion. Dataset indexing is a custody operation; it does
not run a solver or accept a scientific result. A completed result records the
numerical workflow, its frozen and calibration artifacts, and a separate
post-freeze state instrument. The browser verifies the downloaded bytes and
renders the recorded states. It does not repeat the inversion.

All scientific and public-use claims remain explicit false values in the
current synthetic controls. Solver completion is not field eligibility,
source-rights approval, scientific acceptance, or public activation.

## Authenticated project API

The following routes use the signed-in project owner, CSRF protection for
mutations, private storage, the physical writer lease, and a complete custody
and quota check. Dataset members are uploaded as original bytes with the
closed metadata envelope used by `app/joint_routes.py`.

| Route | Operation |
| --- | --- |
| `POST /api/projects/{project_id}/joint-members` | Store one original gravity or magnetic source member. |
| `POST /api/projects/{project_id}/joint-datasets` | Bind exact development and sealed member inventories into an immutable dataset index. |
| `POST /api/projects/{project_id}/joint-jobs` | Queue one `solve` operation for an owned native dataset. The request contains only `dataset_id` and `operation`. |
| `GET /api/projects/{project_id}/joint-jobs/{job_id}` | Read the owner-scoped job state and measured resource fields. |
| `POST /api/projects/{project_id}/joint-jobs/{job_id}/cancel` | Request cancellation. The reservation remains until the worker publishes a terminal record. |
| `GET /api/projects/{project_id}/joint-results` | Read up to 200 owner-scoped terminal and active job summaries. |
| `GET /api/projects/{project_id}/joint-results/{job_id}` | Read the exact result index and its digest-bound member inventory. |
| `GET /api/projects/{project_id}/joint-results/{job_id}/export` | Download original result members and `private-custody-index.json` in a stored ZIP. |

The frontend validates the history schema, every job-to-project binding, the
index digest, the complete archive inventory, member sizes and member hashes
before import. The export uses ZIP stored entries so the transmitted originals
remain byte-identical.

## Worker behavior

The candidate worker claims only `joint.gravity-magnetic-native/v1` jobs. It
copies the immutable dataset dependencies into an exclusive external workspace,
verifies the pinned Linux runtime, runs `scripts/run_joint_survey.py solve`,
replays validation, and runs `scripts/run_joint_instrument.py export` followed
by its validation command. The latter copies the validated workflow artifacts
and records prediction/residual frames for the browser. It does not refit.

Terminal result index and member rows commit together with their private file
copies after custody and quota reclassification. Cancellation and infrastructure
failures use the explicit `geophysics.joint-job-failure/v1` record. Such a record
means no accepted solver output is available; it does not fabricate a workflow
receipt. A scientific workflow's own failure receipt and retained aborted
ledger are preserved as their original files.

The deployment service's systemd memory and CPU ceilings do not qualify this
candidate worker by themselves. Scratch and process resource enforcement,
restart recovery for a running job, and crash-cut publication tests must be
qualified for the assembled service before online admission.

## Candidate and release boundary

The route assembly and worker are implemented for the isolated 0006 candidate
schema. Revision 0006 remains outside the ordinary serving migration chain. The
deployed database therefore fails closed at the exact schema check, and no M11
worker service is installed. The route implementation is not an online service
release. Promote or activate it only after the registered migration lifecycle,
full custody/deletion recovery, browser/API contracts, resource admission, and
the whole-product convergence gates pass for the single ML VPS origin.

## Local reproduction

From the repository root, use the pinned Linux CPU runtime and an external
private data root. Keep solver inputs, outputs, scratch and temporary database
outside Git worktrees. The reproducible solver and instrument commands are
`scripts/run_joint_survey.py solve`, `scripts/run_joint_survey.py validate`,
`scripts/run_joint_instrument.py export`, and
`scripts/run_joint_instrument.py validate`. The full CLI arguments are
validated before reading data; see `--help` for the required absolute paths.

The focused authenticated API tests are
`tests/api/test_m11_candidate_job_routes.py` and
`tests/api/test_m11_project_deletion.py`. The browser custody parser and owner
workbench tests are in `frontend/src/test/joint-custody.test.ts`. These tests
require the external matrix fixture and, for the real browser archive cases,
explicit solver-instrument and Python API receipt directories.
