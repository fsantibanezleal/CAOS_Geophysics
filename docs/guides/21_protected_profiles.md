# Protected ERT and first-arrival computation

The public browser instrument reads native result files without uploading them.
The protected project workflow instead computes on the owner's stored original
using the same local numerical functions in a separate bounded native child.
These are different execution lanes, not duplicated websites. Both belong to
the single ML VPS origin. No SMTP, external identity provider or off-host
backup is required for internal accounts and small-project testing.

## Original, declaration and immutable dataset

In Projects, upload `.ohm` as `ert_ohm` or `.sgt` as `traveltime_sgt`.
These formats are distinct from generic ERT/traveltime CSV. The strict grammars
are described in [the supplied-profile chapter](20_supplied_profiles.md).
Declare local xy metre coordinates, elevation positive up, a real local
reference and vertical datum, resistance in ohms or first-arrival time in
seconds, and the exact sensor and measurement counts. Originals are limited
to 1,000,000 bytes. Upload admission is not an inversion verdict.

Open the project's App workbench and select **ERT / first-arrival profiles**.
Provide the rights holder and explicit processing and redistribution decisions.
The method declaration binds the existing owned source ID, original hash and
byte count, citation and physical frame. The API rejects metadata drift rather
than converting coordinates or inferring missing declarations.

`POST /api/projects/{project}/datasets` accepts `asset_id` and
`profile_metadata`; it parses all original rows without loading pyGIMLi.
Its immutable receipt identifies the original and canonical dataset hash,
parser version and `parsed_not_numerically_inverted` state. The dataset retains
the original sensor positions, zero-based ABMN or source/geophone indices,
row IDs and observed values. It contains no field truth label.

## Numerical method and actual execution

The method IDs are `ert.topographic-profile/v1` and
`traveltime.first-arrival-profile/v1`. The physical equations, transforms,
conditional errors, native mesh and independent prediction challenges are
documented in [chapter 20](20_supplied_profiles.md),
[inverse-problem fundamentals](../problem-types/problem-types.md) and
[traveltime recovery](../problem-types/traveltime-recovery.md).
This API version admits frozen, tested numerical settings with `parameters: {}`.
Plot colour ranges and measurement playback are display controls, not solver
parameters. A later configurable inverse must independently validate its
parameter contract rather than disguising display controls as computation.

`GET /api/projects/{project}/datasets/{dataset}/methods` reports eligibility
and the host admission decision. When admitted,
`POST /api/projects/{project}/jobs` queues `dataset_id`, `method_id` and
`parameters`. The request binds dataset/raw SHA-256, producer script SHA-256
and every numerical module SHA-256 before execution. The worker refuses a
different producer release instead of silently changing a queued calculation.

The operator enables `GEOPHYSICS_PROFILE_ONLINE_ENABLED` only after actual-host
qualification and sets `GEOPHYSICS_PROFILE_PYTHON` to the absolute pinned native
interpreter. The web API environment remains separate: pyGIMLi requires a
different NumPy line from the API and canonical GPU environment. No caller
controls the executable, imports, paths, network URL or shell command.
Use the repository's pinned ERT/traveltime requirements; do not upgrade the
API environment to make the native child importable.

The separate worker verifies the original again, enforces per-child wall,
RSS and scratch ceilings, limits numerical threads, and routes scientific
config/cache paths into private job staging. On Windows, pyGIMLi's import-time
APPDATA requirement is explicitly contained there. Account quotas and the
single-worker queue also apply; the numerical caps do not imply unlimited
project storage. Cancellation terminates the child tree and retains the owned
original and terminal job record.

## Job state is not scientific validity

`queued` and `running` report execution only. `succeeded` means that the child
returned and its identity, native geometry and typed export were accepted.
The separate `numerical_verdict` can be `passed`, `ineligible`, `not-converged`
or another original scientific refusal. Failed held-out prediction is never
converted into a passed result merely because a finite array exists.
The interface displays QC and refusal evidence without drawing a replacement
model. Process failures, resource exhaustion and cancellation are terminal
job outcomes, not a substituted numerical answer.

Measured wall milliseconds, peak child-tree RSS and peak staging bytes are
returned with the job. A model passing these conditional prediction gates
does not establish unique subsurface geology, independently calibrated
uncertainty or independent-site transfer. Sensitivity coverage is not
posterior uncertainty or resolution.

## Result identity, inspection and export

The result endpoint serves exact canonical producer bytes. The browser checks
their job-bound SHA-256 before parsing; it does not reserialize Python floating
tokens to verify a digest. Source, dataset, request, method, raw identity,
producer modules and the original scientific verdict must agree.
Browser checks are structural and scalar consistency checks, not independent
native solver replay.

The linked instrument draws actual returned triangles and observed acquisition
rows, with equal physical metre scale, no interpolated invented geology and
prediction-minus-observation residuals. Held-out fits remain distinct.
Acquisition playback changes the selected original measurement; it does not
animate invented optimizer states or propagating waves.

The ZIP export contains exactly `manifest.json`, `dataset.json` and
`result.json`. It excludes original bytes, binds member byte/hash counts,
axes, units, rights and producer/request provenance, and is verified before
download. Reopening a ZIP requires the selected successful job and its dataset
receipt. It performs no upload or new computation. A mismatched import is
rejected without replacing the last verified result. Preserve the original
and environment locally to reproduce physics independently.

## Reproduction and acceptance evidence

Put working originals, test scratch, result exports and large intermediates
outside the checkout using absolute external roots. The repository-local
ignored virtual environments are intentional. The same
`scripts/process_supplied_profile.py` path reproduces a supplied original
without API credentials; see chapter 20 for paired shell commands.

The protected integration gates are in `tests/api/test_profile_jobs.py`,
ownership/physical bindings in `test_profile_contract.py`, and original
format checks in `test_profile_uploads.py`. Actual native field-job tests
require explicitly configured `GEOPHYSICS_PROFILE_TEST_PYTHON` and
`GEOPHYSICS_LOCAL_DATA_ROOT`, not silently downloaded replacement data.
The [feature task record](../design/features/protected-profile-jobs/tasks.md)
separates local evidence from rendered and actual-VPS acceptance. A closed
host flag is reported explicitly; it is not represented as deployed compute.

## Linux execution and terminal recovery

The installed Linux profile lane uses a fixed privileged observer, never a root
API or scientific worker. The installation pins runtime, complete source/import
closure, private database and an external `custody_root`; the browser cannot
choose paths or commands. `linux_installation` records the independently checked
pre-launch configuration/runtime/invocation/source digests. `linux_execution`
records actual unit extinction, independent guardian completion and separate
sampled RSS/kernel memory charge. Both accompany the unchanged scientific result
in its normal ZIP. These operational records are not scientific validation or
complete native CPU accounting. The Windows lane contains neither record.

Failed or interrupted stages remain in `.job-staging`, and startup refuses them
until inspected. With the worker stopped, the installation operator can run:

```sh
"$GEOPHYSICS_API_PYTHON" -B scripts/recover_profile_job.py JOB_UUID
```

Use the same explicit `GEOPHYSICS_DATA_DIR`, database, pinned profile interpreter
and supervisor environment as that installation. The command holds the worker
lock and accepts only a terminal owned job. Root recovery proves both exact
groups are already inactive and kernel-empty; it never stops active work, reads
an original upload as root or promotes a failed model. Known copies are removed
only after a durable root intent; originals, original receipts and recovery
records remain. The unprivileged stage is atomically archived under
`.profile-retained/JOB_UUID` with a hash/byte manifest before a verified
uncommitted duplicate is removed. Repeating a completed recovery verifies the
same archive without replacing it. A published successful result is unchanged.

Unknown bytes, changed identities, incomplete input sets or a different
installation epoch refuse recovery unchanged. Archives are bounded to 256 MiB
in total and 64 MiB per stage. This is terminal execution-evidence custody, not a
project backup service; it does not require SMTP or external storage services.
