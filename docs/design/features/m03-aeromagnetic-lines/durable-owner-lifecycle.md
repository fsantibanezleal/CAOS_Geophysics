# Durable M03 owner lifecycle contract

This additive leaf uses the existing account/project/dataset/ProcessingJob model.
It does not replace the queue, schema head, fixed runtime configuration or Linux
supervisor. MAIN mounts it only after reviewing source/intake, execution, exact
storage accounting, reconciliation and the following persistence contract.
MAIN allocated revision0007_magnetic_line_artifacts with exact predecessor
0006_joint_artifacts (M11), after0005_physical_forest (M01) and
0004_waveform_artifacts. The isolated migration capsule lives in
app/magnetic_line_survey_migrations/0007_magnetic_line_artifacts.py. It is not
inserted into this older checkout's shared Alembic search path: its actual
predecessors must be combined and reviewed by MAIN, never replaced by empty
aliases. Capsule tests apply its real DDL to a private historical-schema
fixture; they do not claim the joint one-head gate. Downgrade refuses any
retained M03 row before changing tables, rather than silently losing custody.

## Persistence and identity domains

`magnetic_survey_admissions`: job_id PK/FK; start_json (closed SurveyStart/1);
source_receipts JSON; authority_sha256; reservation_bytes. Source receipts are
immutable actual dataset/original/metadata/request/auxiliary DB UUID/hash/size
receipts plus source UUID, rights decision and private-storage attestation.
The source physical paths are never stored in the admission or returned to HTTP.
ProcessingJob.result_key stores the actual179-character relative M03 result
path under m03/owner/project/job/attempts/attempt/result/result.json, not the
member UUID or the incompatible generic derived/results path. Its SHA/bytes
describe that one Result JSON, while attempt/member inventory accounts for all
physical storage. Result serving resolves its durable member UUID separately.
Parent startup/delete/accounting must explicitly dispatch this method domain.
ProcessingJob.request_sha256 hashes the canonical `m03-admitted-request/1`
envelope (job, owner, project, dataset, start, source receipts, authority SHA and
reservation), NOT original uploaded request JSON or SurveyRequest.dataset SHA.
Configuration authority is a trusted fixed parent-owned receipt, not a body,
header, client environment flag, callback or user-edited runtime path.

`magnetic_survey_attempts`: id PK; job_id FK; ordinal; state; worker_id;
started_at; finished_at; lifetime JSON nullable; retained_bytes; inventory JSON.
Unique(job_id,ordinal). States claimed/running/drained/publication_uncertain/
published. An attempt is committed BEFORE its directory is allocated. Failed
allocation, file write, cancelled/nonconverged computation or uncertain SQL
publication retains the attempt/reservation rather than deleting evidence.
Only actual drained counters can release active reservation. Missing counters
are unknown, never zeros. Recovery must observe actual controller/OS drain;
an absent heartbeat alone cannot prove it. Another immutable attempt is needed
for any retry. No automatic retry opens the original outer again.

`magnetic_survey_members`: id UUID PK; attempt_id FK; relative_name; byte_count;
sha256; kind. Unique(attempt_id,relative_name). Kinds result/manifest/chunk/page/
receipt. Member names are finite actual receipt entries, not URI path parameters.
Every lookup joins member -> published attempt -> ProcessingJob -> owned project
and checks method and state before byte access. All physical members, including
JSON manifests, are served as octet-stream with a digest and no-store. Closed
UUIDs prevent arbitrary path selection. A result member is not an original/raw
download grant; originals remain governed by transitive export rights.

`magnetic_survey_exports`: id UUID PK; attempt_id FK; scope private/public;
manifest_member_id FK; byte_count; sha256; created_at. Download identity joins
the same owner/project/job/attempt chain. Export bytes must already exist and
pass rights-transitive native export verification before the row is committed.
A scope preference cannot create permission. An export manifest download is not
a ZIP bundle or replay; complete bundle members must have their own verified
registry entries. The client must not imply replay from a manifest alone.

Saved-route integration uses the actual existing current_user/get_session
dependencies and security middleware: GET job, GET result, finite paged GET
members (offset,512 entries maximum) and GET member UUID, POST cancel with empty
body only. Authentication/project scope precedes byte access or cancel-body
streaming. Member bodies are bounded8MiB immutable byte snapshots, rehashed
before response, octet-stream/no-store; no FileResponse reopen race. Result JSON
is bounded2MiB and joins its published result member, actual path/SHA/bytes and
job identity. Registry response: schema m03-owner-members/1, job_id,
result_sha256, offset, total, next_offset nullable, entries each member_id,name,
bytes,sha256,kind. Parent full installer must additionally implement admission,
fixed dispatcher and real export; saved routes alone are NOT online completion.

## Transactional state machine

Claim uses BEGIN IMMEDIATE; immutable admission hashes and method must match.
Queued cancellation writes terminal cancelled without allocating a child.
Running cancellation records cancel_requested only; a DB monitor writes the
fixed counted cancel.request, the native controller terminates and drains, and
only its factual terminal receipt completes cancellation. Publication rechecks
cancel/state/worker/attempt fence under BEGIN IMMEDIATE. A scientific FAIL may
have execution state succeeded, but its Result.verdict and original thresholds
remain FAIL. Nonconverged required candidates never create a successful Result.

Published members must have actual regular single-link bytes, exact SHA/size,
no symlink/junction ancestors and an exhaustive measured attempt inventory.
Fixed member paths resolve under external device storage only. Unknown files,
changed files, stale foreign member IDs, unverified result roots and restored
DB/file inconsistencies refuse; no broad directory allowlist is introduced.
Cancel and publication use the same attempt fence; stale workers cannot publish.
Commit exceptions preserve bytes and reserved debt for exact recovery.

Windows disk-root custody uses the standard extended-length filesystem spelling
internally, preserving the same relative owner/project/job/attempt identity in
SQL and HTTP. It does not shorten UUIDs, relocate data into the repository or
ignore inaccessible entries. Root/link/repository/system-temp checks remain
mandatory. This is filesystem compatibility, not a native/Linux qualification.
The Windows process current directory uses the ordinary spelling when short
enough, otherwise GetShortPathNameW of that SAME measured attempt directory,
verified by filesystem identity before spawn. No junction, alternate scratch,
source copy or repository working directory is introduced. Missing short-name
support or an overlong result refuses before native allocation. Original paths
in all plans/member receipts remain unchanged; stop/CPU/RSS/scratch caps do not.

The existing one-active-job/account and queue/quota checks remain mandatory.
Parent accounting must use max(reservation, retained physical bytes) for each
unreleased attempt and count successful members/exports once, never add only
the small Result JSON or silently use the gravity default reservation. Parent
startup/deletion must consume the exact registry/inventory and preserve unknown
bytes. Stale member/export access after project tombstone/deletion is404.

The additive storage service returns the M03 subtotal only: the parent MUST
exclude M03 jobs from generic result/default-reservation accounting before
adding it. Queued no-attempt jobs reserve the admitted bytes; cancelled queued
jobs with no attempt charge no native bytes. Claimed/running/uncertain attempts
retain max(reservation,recorded retained bytes); drained terminal or published
attempts charge exact retained bytes after actual drain validation. Every old
attempt remains charged once, including failed evidence. Missing admission or
counter integrity refuses, never returns a permissive zero. Export copies must
be incorporated before that export service is mounted.

Read-only project reconciliation rebinds admission/source receipts, requires
factual complete drain, verifies every retained file/size/hash and all published
member/job/result references, then exhausts the exact project namespace. Unknown
jobs, attempts, empty directories, changed/missing members and unverified old
attempts refuse. It does not kill processes, erase bytes, reset jobs or infer
zero counters from missing heartbeats. Its deletion-preparation hook additionally
refuses queued/running jobs and returns the exact verified relative manifest
for the parent's transactional tombstone protocol. Preparation itself never
deletes anything and is not the final deletion/purge or backup-erasure gate.

## Acceptance and claim boundary

Real SQLite transitions and actual-byte negative gates establish this leaf,
not native execution, source registration, host qualification, migration-chain
review or mounted HTTP/browser acceptance. Full acceptance additionally drives
the fixed original-row worker from genuine uploaded magnetic parents, actual
cancel/restart/export/delete, both language/themes and actual ML VPS receipts.
Current missing8201 original cannot be replaced by authored regression bytes.
Original S1 and opened100/50 FAILs remain adverse historical evidence; no97-fit
completion follows from defining the persistence contract.

## Español: identidad y publicación

La admisión conserva UUID/hash/bytes y permisos reales de cada padre. El hash
de la solicitud admitida es distinto del archivo científico original. Cada
intento se registra antes de crear archivos; fallos y publicación incierta
conservan evidencia y deuda de almacenamiento. Sólo contadores reales después
del drenaje permiten finalizar cancelación. El monitor escribe un marcador
interno fijo y medido, nunca una ruta o callback del cliente.

Miembros y exportaciones usan UUID con unión al propietario/proyecto/trabajo e
intento publicado. Se verifica cada byte y cada archivo desconocido impide
reconciliación. El estado de ejecución no cambia FAIL científico. MAIN debe
revisar y montar migración, admisión, contabilidad, recuperación y supervisor;
el archivo original8201, QA del navegador y validación integrada siguen abiertos.
