# Owned dataset birth and composite custody

The approved first-upload seam is POST
`/api/projects/{project_id}/magnetic-line-surveys/datasets`. Its closed request
has exactly schema (`m03-owner-dataset-request/1`), original_asset_id,
original_sha256, metadata_asset_id, metadata_sha256, request_asset_id,
request_sha256, auxiliary_asset_ids, auxiliary_sha256. Canonical UUIDs,
lowercase hashes, noncoercion, unique paired auxiliary lists (maximum16), and
16384-byte body limits apply. No authority, path, count or solver overrides.
Only actual published inspection permits201; no fixture dataset is produced.

The fifteen-key `m03-owner-dataset/1` descriptor contains schema, dataset_id,
owner_id, project_id, original_asset_id, original_sha256, original_bytes,
metadata_asset_id, metadata_sha256, auxiliary_asset_ids, auxiliary_sha256,
geometry_sha256, rows, ordered_row_ids_sha256, parser_version
(`m03-original-geometry/1`). Its SHA is distinct from the scientific request's
dataset-version domain. The receipt has schema (`m03-owner-dataset-receipt/1`),
dataset_id, sha256, bytes, rows, parser_version, provider_verification
(`not_verified`), field_eligibility (`not_established`). Geometry custody is
neither provider verification nor scientific eligibility.

## Allocation and SQL requirements

R-BIRTH-001 SHALL commit an independently conservative inspection reservation
before namespace allocation. A fixed32GiB ceiling is NOT a reservation:
ordinary configured1GiB owner/scratch limits must support small valid inputs.
Input bytes are independently registered; declared counts are only caps.
Value-free inspection MUST precede a second atomic, independently proved
reservation before extraction/geometry allocation. Raw bytes and all existing
method/job/attempt/export debt remain additional; actual stricter configured
limits win. Failure/uncertainty charges max(reservation, retained bytes).
Default-quota positive and one-byte-deficit negative controls are required.

R-BIRTH-002 SHALL bind actual fixed deployment configuration before native
execution, never a random fixture SHA. Source/native/core/environment/roots/
caps must agree. Missing assembly authority refuses execution, not intake.

R-BIRTH-003 SHALL preserve actual drained lifetime/inventory, rebind every
genuine intake parent, verify full original geometry/closure independently,
commit publication_uncertain before an exclusive fsynced descriptor move,
then atomically publish ObservationDataset/account bytes/terminal attempt.
Moved-but-uncommitted and unknown bytes stay debt; no automatic adoption/retry.

R-SQL-001 SHALL enforce intake(owner,project) and intake(owner,project,raw)
foreign keys to matching unique parent keys, including existing valid but
foreign owners. Nullable unpublished raw IDs do not waive project ownership.
R-SQL-002 SHALL enforce export(attempt,manifest_member) against the actual
member(attempt,id), not separate valid identities. Existing independent FKs
remain. GUID storage uses the same adapter as the shared owner records.

The UNRELEASED allocated revision stays0007 after literal0006. New dataset
attempts are additive in that capsule: id, owner_id, project_id, input_json,
source_receipts, authority_sha256, reservation_bytes, state, retained_bytes,
inventory, lifetime, dataset_id, error_code, created_at, finished_at. Allowed
states reserved/running/drained/publication_uncertain/failed/published;
positive reservation/nonnegative retained. Dataset ownership is composite too.
Every retained custody table refuses downgrade before any change.

## Two-stage finite preparation (prospective equations)

Initial inspection workspace reserve is16MiB (plan, bounded2MiB documents/
receipts, controller logs and roots); peak memory proof512MiB. It streams the
whole original CSV and complete hashed bundle envelopes, with1MiB payload
buffers and4096-byte CSV records, no member list/index/extraction or numerical
measurement decoder. Native actual counts are independently checked against
registered byte envelopes and fixed limits before advancing.

For actual rows N and independently verified physical member count K, index
ceiling I=4096*(16+ceil(2048*K/4096)), I<=2GiB. This reserves2048B per bounded
64-byte-name record for data/two unique indexes/recognition and page slack;
index+journal=2I. Geometry allowance=65536*N+64MiB. Preparation phase scratch
bound=registered auxiliary bytes+2I+geometry+64MiB. Full dataset reservation is
16MiB+that bound+2MiB descriptor allowance, committed before phase2 namespace.
No4GiB empty index charge. All unknown/index/partial/native copies remain
counted. Actual counters/inventory must fit these bounds too. Excess refuses
before allocation without changing original rows/scientific resolution.

The fixed initial plan `m03-owner-inspection-plan/1` uses the same five closed
keys schema/original/metadata/request/bundles as preparation; receipt
`m03-owner-inspection-receipt/1` contains schema, original, rows,
metadata_sha256, request_sha256, bundle_sha256, bundle_members,
auxiliary_bytes, next_phase, value_access. New phase2 plan
`m03-owner-preparation-plan/2` adds exactly inspection (path/bytes/sha256).
It verifies the inspection and rebuilds original count and envelope counts
before index/extraction. Legacy preparation-plan/1 remains explicit and is
not an alias for the staged epoch. Neither phase fits/scores/opens outer values.
Actual controller limits may only tighten the existing hard ceilings and are
included in terminal evidence. Parent's genuine fixed-installation assembly
must supply/verify the expected installation binding; an ERT/TT configuration
cannot grant the M03 method. No new posted host/configuration object is added.

Gates: actual allocated DDL direct cross-owner/project/raw/member negatives;
the original copied-chain M01 cross-owner assertion unchanged; real-cookie
intake and joined source routes; default quota/staged deficit; original native
geometry publication; source drift, first failure, postmove uncertainty and
retained recovery. Parent owns route/migration mounting and shared accounting.

## Espanol

La reserva inicial corresponde a inspeccion acotada, no al techo de32GiB.
Cada fase posterior necesita prueba independiente y reserva atomica previa.
Los originales y toda deuda anterior siguen contados. Las claves compuestas
impiden mezclar propietario/proyecto/original o intento/miembro; no se debilita
la prueba negativa original ni el rechazo de downgrade con evidencia retenida.
Publicar geometria no concede elegibilidad cientifica, campo ni despliegue.
# Native two-phase component qualification (2026-10-08)

`staged1.xml`: 3 tests, no failures/errors/skips, 110.670 seconds. The real
Windows Job inspection retained all 363 original rows and inspected all 69
physical bundle members without measurement decoding or a SQLite index:
CPU 0.203125 s, peak RSS 46,899,200 B, scratch 6,792 B, one child, zero active
after drain. The independently rebound preparation used an actual prospective
158,504,595 B scratch limit (not the 32 GiB global ceiling): CPU 1.0625 s,
peak RSS 46,665,728 B, scratch 188,955 B, one child, zero active after drain.
Both phases enforced 512 MiB committed-memory limits. The prospective retained
dataset reservation is less than 1 GiB for this exact original acquisition.

This qualifies the native inspection/preparation components, not the SQL owner
quota transaction, publication/recovery, authenticated dataset endpoint, full
scientific fit, provider original, host admission or integration. The quota
one-byte-deficit gate still requires the actual owner service transaction.
