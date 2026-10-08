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
