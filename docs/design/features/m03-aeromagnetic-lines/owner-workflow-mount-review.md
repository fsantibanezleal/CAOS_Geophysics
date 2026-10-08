# M03 owner workflow: wire binding and required host integration

This review applies to the [approved corrective packet](../m03-corrective-workflow/design.md),
especially R-C07. The implemented leaf is `app/magnetic_line_survey_wire.py`.
It defines closed start/export DTOs and reads existing owner-scoped storage.
It installs no router, creates no ProcessingJob, runs no scientific engine and
does not replace the existing CLOSED proposal. Passing its isolated tests is
byte-custody evidence, not lifecycle completion, host admission or M03 acceptance.

## Implemented wire and read boundary

`SurveyStart` requires exactly the eleven approved JSON keys: `schema`,
`dataset_id`, `original_asset_id`, `metadata_asset_id`, `request_asset_id`,
`auxiliary_asset_ids`, `dataset_sha256`, `original_sha256`, `metadata_sha256`,
`request_sha256`, `auxiliary_sha256`. The schema literal is `m03-owner-start/1`.
UUID strings use canonical lowercase hyphenated form; Python UUID objects are
also valid internal inputs. Every dataset/asset UUID is distinct, including
auxiliaries. The two auxiliary lists have identical length 0..16. Hashes are
strict strings of exactly 64 lowercase ASCII hex characters, without whitespace,
newline or case normalization. Equal hashes are permitted for distinct assets
containing equal original bytes; a caller hash is never custody authority.

`SurveyExport` requires only `schema=m03-owner-export/1` and
`scope=private|public`. Scope is an export preference, not a rights grant.
There are no client path, URL, owner, module or callback fields. Unknown keys,
missing keys and coercions refuse. The raw JSON parsers additionally reject
duplicate keys, invalid UTF-8, trailing tokens, nonfinite constants, excessive
nesting and bodies exceeding 16 KiB. Error projections contain fixed text and
known field names only, never values or caller-authored path-like field names.
The HTTP integrator must enforce the 16 KiB limit while streaming the request,
before allocating an unbounded body. The in-memory leaf cap alone cannot do that.
Persist or serialize these DTOs with `model_dump(mode="json", by_alias=True)`;
their internal schema_version attribute maps to the wire key schema. Do not
use Pydantic's ordinary JSON loader in place of the duplicate-key-aware parser.

The existing helper entry points are reused:

```python
parse_survey_start(raw: bytes) -> SurveyStart
parse_survey_export(raw: bytes) -> SurveyExport
await bind_owned_survey_sources(
    session: AsyncSession,
    settings: Settings | WorkerSettings,
    project_id: UUID,
    user: User,
    request: SurveyStart,
) -> OwnedSurveySources
```

The binding first uses `app.projects._owned_project`,
`app.processing._owned_dataset` and `app.projects._owned_asset`. Every asset
and SourceRecord is queried before any file-body read. The shared asset helper
checks SourceRecord.owner_id but does not check SourceRecord.project_id; the
leaf explicitly closes that missing project check. Missing/foreign project,
dataset, asset or source scope yields 404. A frozen model's mutable lists are
revalidated at the binding boundary so mutation or model_construct cannot
bypass list-length/UUID constraints.

The dataset must reference the requested original asset, match its original
SHA and match the requested dataset SHA. Its storage key must be the exact
existing `dataset_key(owner, project, dataset)` result. Each RawAsset must match
the corresponding request SHA, SourceRecord.sha256 and SourceRecord.expected_bytes.
The raw key must be `projects/<owner>/<project>/<asset>`. The existing
`checked_storage_path` and `checked_derived_path` derive locations from DB keys;
no submitted filename is interpreted as a location.

All original, metadata, request and auxiliary files plus the dataset derivative
are streamed and counted against their DB byte receipts. The reader verifies
the actual lowercase SHA, size and file identity before/after reading, and
rejects missing files, nonregular entries, symlinks, Windows junction/reparse
points and additional hardlinks. It reads at most the remaining receipt bytes
plus one and never reads an entire original CSV into memory. Fixed 409 errors
identify raw, derived or storage-integrity failure without exposing paths.

`OwnedSurveySources` is an internal frozen descriptor containing verified
paths, UUIDs, hashes and sizes plus each asset's source UUID and recorded rights
decision/storage attestation. It is not a response DTO. It does not parse JSON
sidecars, prove private/public scientific rights, independently review a provider,
validate magnetic metadata or hold a filesystem lock. A successful read is
not a permanent snapshot: the worker must rebind, safely snapshot originals,
verify copied bytes and reconcile deletion/publication races. No successful
admission follows merely from this descriptor.

## Actual intake and normalization incompatibilities

| Actual source location | Current behavior | Required reviewed integration |
| --- | --- | --- |
| `app/schemas.py:RawUploadInput` | Closed format enum contains gravity_csv, magnetic_csv, traveltime_csv, ert_csv, geotiff, edi, miniseed, stationxml, segy and mth5. Every upload requires PhysicalInput. | Register exact non-executable M03 metadata JSON, request JSON and role-specific original auxiliary attachments with real SourceRecord/RawAsset receipts. JSON cannot be labelled CSV or hidden in geometry to bypass the enum. |
| `app/formats.py` | EXTENSIONS/MIMES/UNITS/GEOMETRY_FIELDS/FORMAT_MAX_BYTES and the envelope validator dispatch on that enum. Magnetic CSV checks five declared line/x/y/z/value column names, a 50 MiB cap and a bounded header/second row. | Add deliberately reviewed attachment format/role admission, closed JSON and bounded original-series checks. Generic magnetic envelope validation does not establish the fourteen-column streamed M03 contract, UTC, ordinals, datum, quantity, correction states or independent reference. |
| `app/projects.py:upload_asset` | Stores measured immutable originals and sources, attestation, SHA/size, exact owner keys and raw-byte quota. Metadata header is capped at 16 KiB. | Preserve this custody model for each attachment. Do not embed multi-MiB scientific sidecars in the header; upload their original bytes separately. The generic 200 MiB request maximum/1 GiB default account quota are not admission for the 4 GiB offline raw profile. |
| `app/processing.py:create_dataset` | Chooses EDI only when detected_format is edi; every other asset enters parse_gravity_dataset and its gravity parser_version. The non-EDI cap is 2 MiB/4096 rows by default. | Define a real magnetic dataset normalization/descriptor path, complete original-row identity and immutable metadata/auxiliary parents, without whole-file read_bytes. Do not reuse gravity or EDI schema/units/parser names. |
| `app/processing_contract.py:validate_dataset_identity` | Dispatches EDI separately, otherwise checks observation-dataset/v1 against station dimensions and observed_mgal/sigma_mgal arrays. | Add an explicit magnetic discriminator and closed source-bound streamed identity validator used by creation, GET, worker, startup and deletion. A new dataset DB row alone will fail those existing consumers. |
| `app/processing.py:methods` and submit_job | Inventory/admission recognize only gravity flag QC and M05/M06 EDI. Generic JobCreate.parameters has those three parameter models. | Register `magnetic_line_survey_v1` separately and use SurveyStart. Bind real schema/profile eligibility and measured host resources before queue admission. |

The binding tests use actual migrated SQLite, verified library accounts and the
existing upload/dataset harness with genuine gravity fixture bytes. This choice
allows an honest positive test of the generic DB/hash boundary without bypassing
the missing magnetic registration. It proves no M03 metadata attachment or
magnetic normalized dataset can currently be registered through the production
routes. Scientific dataset_version_sha256 in SurveyRequest and DB dataset_sha256
identify different specified byte domains until the new normalization contract
defines their relationship; neither may be copied into the other by assumption.

## Mount and lifecycle hooks required from the owning integrator

The prospective module is `app/magnetic_line_survey_workflow.py`, using the
`current_user, get_session` returned by `app.auth.install_auth` and the existing
security middleware. `current_user` already requires an active, verified account.
The route must check authentication and owned project before bounded body parsing;
CSRF/origin refusal remains 403. Existing decorator-based typed body parsing is
not sufficient evidence of ownership-before-parse ordering. Use the same
`ApiError` projection. No raw source path or traceback belongs in job responses.

Proposed integration signatures below are review targets, not implemented
functions, dynamic registries or authorization to change shared files:

```python
install_magnetic_line_survey_workflow(app, settings, current_user, get_session) -> None
await admit_owned_survey(session, settings, user, project_id, request: SurveyStart) -> ProcessingJob
await execute_owned_survey(settings, sessions, job: ProcessingJob, poll_interval: float) -> None
await owned_survey_job(session, user, project_id, job_id) -> ProcessingJob
await verified_survey_result(settings, session, job) -> dict
await verified_survey_member(settings, session, job, member_id: UUID) -> BoundSurveyFile
await export_owned_survey(settings, session, job, request: SurveyExport) -> dict
```

| Hook and integration path | Exact existing behavior and incompatibility | Required acceptance before mounting |
| --- | --- | --- |
| Assembly, `app/server.py:create_app` | Installs auth, security, projects and processing. The CLOSED port remains an isolated unapplied proposal in app/magnetic_survey_port.py. | Install exactly one reviewed `/api/projects/{project_id}/magnetic-line-surveys/jobs` POST. If an integrator has installed CLOSED, replace its registration; do not leave duplicate routes or reinterpret an environment flag as completion. No assembly edit is made here. |
| Admission, `app/processing.py:submit_job` | Rechecks owner under BEGIN IMMEDIATE, enforces one queued/running job per owner, global queue bound and quota; preflight limits are gravity/MT constants and host minima. | Preserve transaction, queue, per-owner concurrency and quota checks. Parse/verify all source and scientific metadata, geometry-only capacity and actual useful host envelope before allocation. The offline ceilings are refusal limits, not a VPS resource permission. |
| Claim, `app/worker.py:_claim` | Transactionally claims the oldest queued ProcessingJob without a method filter, marks running and stores worker_id/started_at. | Do not enqueue magnetic work until the worker has a real fixed method dispatch. _execute currently rejects unknown methods and otherwise its gravity command expects parameters.threshold. Rebind owner/dataset/all original parents at claim, including tombstones and exact request integrity. Never accept a client module or callback. |
| Execution, `app/worker.py:_execute`, _command, _mt_command | Spawns app.compute/app.mt_compute with a dataset JSON and one result.json. Checks request hash, known method list and existing validators/build_bundle. | Add an explicit invocation of the real full-survey controller and its independently verified outputs. Keep original byte SHA distinct from the canonical admitted job request SHA and scientific request identity. No gravity/MT command/result aliases. Scientific failure can accompany completed execution and must remain visible. |
| Containment, _rss_tree, _stage_bytes, _terminate_tree | Measures tree RSS, wall and flat staging bytes; known stage exceptions are .matplotlib and source.edi. No generic committed-memory/CPU receipt or nested M03 artifact inventory exists. | Count originals, channels, chunk pages, indexes, FFT/cache, export and fsync/drain; retain actual tree CPU, RSS, committed memory, scratch, wall and stop reserves. Add exact bounded M03 stage inventory; unknown bytes remain operator-recovery failures. Windows component receipts do not establish Linux/VPS admission. |
| Restart, _recover_interrupted, run_one/run_forever | Marks running rows failed/worker_interrupted, then reconcile_private_files refuses any nonempty .job-staging. Existing recovery does not retain a per-attempt magnetic counter/member receipt. | Drain/contain prior attempts, retain actual partial inventory and terminal counters, preserve unexplained bytes and never mark lost work succeeded. A retry is a new immutable attempt. Recovery must not silently erase forensic evidence or infer zero counters. |
| Accounting, `app/processing_storage.py:account_derived_usage` | Counts dataset bytes, succeeded result_bytes and active reservations; unrecognized methods get the 8 MiB gravity default. | Register the independently calculated magnetic reservation and all retained physical storage, members/exports/failed-attempt evidence. Release reservation only after terminal drain/publication; prevent quota bypass via nested files, export copies or failed jobs. |
| Startup, `app/database.py:reconcile_private_files` | Allows only exact known raw assets, datasets and single JSON result paths, validates those payloads and rejects unreferenced derived files or transfer stages. | Add exact magnetic request/source/result/member/export/attempt inventories and bytes/hashes, not a broad directory allowlist. Preserve restored-DB/orphan/partial-commit/tombstone refusal. Reconcile all references after restart before serving results. |
| Result/member storage, checked_derived_path, result_key, validate_result_identity, app.bundle.build_bundle | Only datasets/results JSON path forms; result identity/build_bundle recognize gravity/MT. ProcessingJob has only one result key/hash/size. | Define immutable owned publication and a durable finite member inventory, UUID member/download identity, actual aggregate storage accounting and transitive rights. Decide persistence using current models and a reviewed schema contract; no migration0004 design/edit is asserted here. |
| Cancellation, `app/processing.py:cancel_job` | Queued becomes cancelled immediately; running sets cancel_requested, worker polls and terminates the child tree. | Owner/method-check every magnetic job. Drain real native work and all children within unchanged 10 CPU/10 wall stop reserves; preserve counters/partial evidence. A flag toggle alone is not cancellation proof. |
| Delete, `app/projects.py:delete_project`, exact_derived_project, purge_exact_derived | Active jobs cause project_jobs_active. Exact derivatives expect one datasets/results JSON per row; unexpected members refuse. Tombstone commits precede exact purge; backups remain pending reconciliation. | Add owner cancellation/drain before deletion where approved, exact magnetic member/export/partial inventories, transactional tombstone/quota handling and stale member/download 404. Preserve unknown bytes and the factual backup-erasure status; do not claim backup purge. |

The reviewed route family also requires GET job, GET result, GET member, POST
cancel with no body and POST export with SurveyExport. The job view has exactly
the approved `m03-owner-job/1` keys and five states queued/running/succeeded/failed/
cancelled. Existing ProcessingJob already uses these spellings, but its generic
view is a different shape and leaks request/preflight/error-message fields the
approved projection does not contain. Map only actual stored timestamps and
counters/receipt state. Do not invent an interrupted SQL alias or mark a
scientific FAIL as an overall scientific PASS. New export returns a persisted
owner artifact UUID, actual hash/size and authorized download route only after
immutable verified export. Current GET generic export is an in-memory bundle,
not that lifecycle. Project_id, job_id and member_id must all be bound together
with owner and method on every access, and deleted members must return 404.

The exact future job projection is `schema:m03-owner-job/1`, `job_id:UUID`,
`project_id:UUID`, `dataset_id:UUID`, `method:magnetic_line_survey_v1`,
`state:queued|running|succeeded|failed|cancelled`, `cancel_requested:Bool`,
`request_sha256:Hash`, `result_sha256:Hash|null`, `result_bytes:Int|null`,
`error_code:ID|null`, `created_at:UTC`, `started_at:UTC|null`,
`finished_at:UTC|null`. Every nullable key is present. Its request SHA must be
explicitly assigned to the approved immutable request domain; the uploaded
request file and canonical DB admission envelope cannot share that field by
accident. The finite member UUID registry and actual export response schema
must be reviewed before their mount; none is fabricated by this leaf.

## Verification and remaining verdict

### Executing leaf contract, before implementation

The fixed native controller additionally observes exactly `cancel.request`
inside its already measured attempt directory. Its bytes are exactly
`m03-owner-cancel/1\n`, written by the internal DB cancellation monitor with
exclusive creation and fsync of `cancel.request.pending`, then atomic rename
to `cancel.request`, never a submitted path or callback. Both names remain
counted. This prevents a controller seeing an incomplete write. Read stability
compares device/inode/size/mtime and each API's ctime, excluding access time
which a legitimate read can change. A malformed,
linked, nonregular or multiply linked marker is a custody refusal, not ignored
cancellation. The existing 100 ms controller poll, actual TerminateJobObject,
one-process/no-descendant containment and 10 CPU/10 wall drain reserve remain.
The marker and partial attempt files stay counted after cancellation; queued
cancellation requires no child. Completed publication rechecks the DB cancel
flag and attempt identity under BEGIN IMMEDIATE, so a completion/cancel race
cannot publish a cancelled job as success.

CLI local plans dispatch only from the literal validated input/request epoch.
Input/1 with Request/1 calls the unchanged fixed-basis DAG; Input/2 with
Request/2 calls the fresh 16-map proof and complete 96-inner/one-final DAG.
Mixed epochs refuse before geometry/value decoding. Original metadata/request
bytes are retained by both paths, without canonicalizing uploaded documents
into new originals. Replay treats candidate_fit_v2 resource clocks in the same
explicit comparison domain as candidate_fit; every candidate identity, score,
numerical diagnostic and geometry remains compared. A nonconverged required
candidate retains actual failure evidence and cannot produce a partial result.

Persistence uses owned additive admission, attempt, member and export rows with
the existing ProcessingJob FK and owner/project joins. MAIN now allocated
0007_magnetic_line_artifacts after0006_joint_artifacts; the isolated capsule and
its custody-preserving downgrade are specified in durable-owner-lifecycle.md.
The actual combined chain remains MAIN's review gate. The canonical admitted
request domain is distinct from the uploaded scientific request SHA; the job
response request_sha256 identifies the canonical admitted envelope. Finite
physical member UUIDs resolve only stored verified receipts, never filenames
from HTTP. Attempt inventory and failed-publication debt remain counted until
exact reconciliation. These are implementation contracts, not a mounted or
host-qualified acceptance assertion.

The leaf gate is `tests/api/test_magnetic_line_survey_wire.py`. Its tests cover
all required fields, strict UUID/hash grammar, unknown path/URL/callback fields,
every pair of duplicate UUID references, auxiliary bounds/length equality,
malformed/duplicate-key bounded JSON and private error sanitization. Real DB
tests cover original/metadata/request/both auxiliary owner and source-project
checks before reads, dataset owner/project/parent checks, client/DB/source hash
and size failures, exact storage keys, actual same-size tampering, truncation,
growth/missing files and hardlink aliases. Successful binding creates no jobs
and changes no source bytes. External validation output records actual results;
the R-C07 real lifecycle gate remains prospective and is not satisfied by this
leaf file. The approved client/browser, restart, cancel, rights export, deletion
and host gates still require the real integrated workflow.

Retained scientific evidence is unchanged: original S1 and the opened 100 m and
50 m refinements remain FAIL at their frozen thresholds. Re-reading/re-fitting
them does not restore an unopened holdout. The requested original 8201-row field
file remains unverified. Reviewed Charleston metadata and release rights do not
constitute acquired flight-line bytes, dictionary/report verification, altitude
datum, IGRF evaluator approval or independent field acceptance. Bartlett cells
remain a compiled grid, never substitute lines. Neither this read binding nor
any future mount can alter those claim boundaries.
