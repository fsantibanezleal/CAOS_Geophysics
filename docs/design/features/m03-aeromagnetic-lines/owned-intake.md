# Owned original-byte intake / Custodia de originales

Approved precode: the parent fully read the166-line private intake/dispatch
packet and approved scoped implementation on2026-10-08. These owned leaves
execute actual upload/source custody, not the old CLOSED start port. MAIN owns
mounting and combined migration/accounting/recovery. No shared Workbench,
source/ERT/TT/ingest CLI, lock or host-supervisor file is changed.

`app/magnetic_line_survey_intake_api.py` provides authenticated project-scoped
POSTassets and GETsources. It takes the parent's actual current_user/get_session
dependencies and CSRF/origin middleware. Project ownership, closed header,
role/MIME/Content-Length, rights and configured quota are checked BEFORE body
consumption or staging. The required trusted account ledger is backend assembly,
never a HTTP field, worker command, callback, SHA grant or host activation.

The ledger MUST compute actual account raw+derived+all existing job/attempt/
export debt in the SAME BEGINIMMEDIATE transaction, excluding only this intake
subtotal. `account_intake_usage` adds committed outstanding reservations and
retained failure/uncertainty bytes. No8MiB gravity fallback is permitted. A
missing/malformed ledger refuses before allocation. Parent must review its
combined ledger assembly before mounting. Unit API fixtures use the existing
real generic ledger only with NO existing M03 jobs; they do not validate that
generic fallback for M03. No parent fixed-authority schema is invented here.

Header exactly5keys: schema=m03-owner-asset/1,role,filename,mime,source.
Source exactly9keys: provider,doi,citation,rights_statement,rights_decision,
private_storage_permission,attribution,expected_bytes,expected_sha256.
doi/citation keys are mandatory even when null. Expected bytes are positive
noncoerced integers, hashes lowercase64hex, private-storage permission literal
booleantrue (stored as existing SourceRecord attested). Raw storage requires
mirror; provider-link-only/derivative-only/forbidden refuse. This declaration
does NOT prove provider metadata, redistribution rights or field eligibility.

Roles: original_csv,metadata_json,request_json,typed_auxiliary_bundle,
navigation_original,base_original,calibration_original,reference_original,
offset_original. Metadata/request<=2MiB, other bytes<=4GiB AND configured upload
limit. Header<=16KiB. JSON/octet-stream are not falsely labelled magnetic_csv;
the owned SourceRecord/RawAsset discriminator is m03_<role>. A published row
returns real UUIDs, exact SHA/bytes and explicitly not_verified source status.

`SurveyIntake` is allocated inside owned0007, predecessor0006_joint_artifacts.
Its reservation is committed BEFORE mkdir/open/body read. Streaming is bounded
by the exact reserved count, SHA verified, flushed/fsynced, then independently
rechecked before a no-overwrite move into the existing project UUID namespace.
Publication uncertainty is committed BEFORE the move; raw/source/AccountUsage
and terminal intake transition are committed together afterward. Invalid bytes,
cancel/interruption and uncertain publication preserve physical bytes and
reservation debt; no automatic cleanup, replay or success. Parent recovery must
reconcile both reserved namespace and possible moved UUID target, not assume a
missing published RawAsset implies zero bytes. Existing DB/source records remain
unchanged. Full parent combined0004→0005→0006→0007 one-head gate is separate.

The binary bundle has8-byte M03AUX1-newline magic, little-endian uint32 count,
then sorted unique ASCII basename/uint64 byte count/raw SHA/payload entries.
Every payload SHA/length and count/trailing byte is validated by bounded reads;
the1million count is refused upfront when impossible from declared bytes.
Inventory hashing is streamed, not a1million-object list. No compression,
ZIP/pickle/URI/path/exec is interpreted. This envelope check explicitly reports
semantic_closure=not_verified: schema-derived closure and fresh-attempt
extraction remain part of the downstream dataset/dispatch implementation.

## Requirement gates

R-INTAKE-001 WHEN original bytes are admitted, THE owned service SHALL commit
the actual quota reservation before allocating or consuming the body.
Gate: tests/api/test_magnetic_line_survey_intake.py::test_actual_cookie_owner_stream_upload_uuid_source_and_precustody_reservation

R-INTAKE-002 IF bytes fail custody, THE service SHALL retain actual files and
charge reservation/uncertainty debt, never grant provider/science acceptance.
Gate: tests/api/test_magnetic_line_survey_intake.py::test_failed_sha_retains_actual_partial_debt_and_quota_precedes_allocation

R-INTAKE-003 IF a binary member fails its count/order/hash/envelope, THE service
SHALL refuse it without interpreting extensions as semantic permission.
Gate: tests/api/test_magnetic_line_survey_intake.py::test_streamed_bundle_count_order_sha_trailing_and_no_extension_grant

R-INTAKE-004 IF authentication, ownership, CSRF or trusted ledger is absent,
THE service SHALL refuse before staging.
Gate: tests/api/test_magnetic_line_survey_intake.py::test_csrf_and_invalid_trusted_account_ledger_refuse_before_staging

## Espanol: limites de integracion

La ruta conserva los bytes originales y los padres SourceRecord reales. La
declaracion de derechos no verifica al proveedor ni autoriza campo/publicacion.
Las reservas y los fallos cuentan como deuda hasta una recuperacion exacta; no
se borran automaticamente. MAIN debe montar la hoja con su contabilidad real,
CSRF y migracion combinada. La extraccion semantica, dataset geometrico completo,
admision fija, exportacion durable y cliente de ingreso siguen pendientes;
este componente no demuestra procesamiento online completo ni campo8201.
