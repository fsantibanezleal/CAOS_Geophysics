# Normative proposed SQL dictionary: milestone A

Status: documentation contract for review, NOT executable migration/source, NOT measured DDL. No field/type in this milestone is delegated to an implementation owner. Names below are exact proposed SQL names. Approval of them is still required. Recovery authority and migration revision are deliberately a separate milestone, not inferred from this dictionary.

## 1. Domains and convention

Every new column is NOT NULL unless marked `?`; no implicit/default value is allowed. All new TEXT uses BINARY collation. New PK columns explicitly include NOT NULL (do not rely on SQLite's historical nullable TEXT PK behavior). Each domain expands into its SQL declared type and a named column CHECK `ck_<table>_<column>`; nullable domains use `column IS NULL OR (<check>)`. Application validation also enforces canonical semantics before insertion. Declared VARCHAR lengths alone do not bound SQLite values.

| Domain | Declared SQL type | Exact column CHECK / additional source validation |
| --- | --- | --- |
| U | VARCHAR(36) | typeof(c)='text' AND length(c)=36 AND c=lower(c) AND substr(c,9,1)='-' AND substr(c,14,1)='-' AND substr(c,19,1)='-' AND substr(c,24,1)='-' AND length(replace(c,'-',''))=32 AND replace(c,'-','') NOT GLOB '*[^0-9a-f]*'; application canonical UUID parse/re-encode equality |
| O | CHAR(36) | U check; unchanged SQLAlchemy GUID storage, NOT a guessed 32-hex owner ID |
| H | VARCHAR(64) | typeof(c)='text' AND length(c)=64 AND c NOT GLOB '*[^0-9a-f]*' |
| I(a,b) | INTEGER | typeof(c)='integer' AND c BETWEEN a AND b; source JSON integer lexeme before coercion, reject bool/float/exponent/string |
| T(n) | VARCHAR(n) | typeof(c)='text' AND length(c) BETWEEN 1 AND n AND instr(c,char(0))=0; registry-specific literal sets below |
| B(n) | BLOB | typeof(c)='blob' AND length(c) BETWEEN 1 AND n; complete bounded strict UTF-8 JSON source scan before typed parse |
| E(values) | VARCHAR(80) | typeof(c)='text' AND c IN the exact listed literals |

For I, SQLite affinity may coerce a bound value before CHECK. The CHECK is not evidence that `1.0`, `true` or `1e0` was rejected in transport. This needs token-aware source tests. Time fields below are integer UTC microseconds since Unix epoch, I(0,9007199254740991), not rewritten legacy timestamps. `M=1048576`, `J=9007199254740991`. Every FK below uses ON UPDATE RESTRICT, ON DELETE RESTRICT, immediate NOT DEFERRABLE. NO CASCADE/SET NULL; explicit deletion order is specified below. Every CHECK/index/constraint name is deterministic as specified, not automatically invented ORM names.

Immutable published metadata rejects UPDATE except maintenance's reviewed whole-candidate copy. Runtime transaction and full audit enforce this; no trigger is asserted implemented. Allocator, job control, intent, custody and reservation state are mutable only under their defined transitions. Constraint checks alone do not establish exact JSON hashes or safe filesystem identity.

## 2. Frozen legacy tables and additive unique parents

All 0001/0002/0003 definitions are frozen by the [source ledger](../../../research/m01-physical-persistence-primary-sources.json). Preserve user/access_tokens/projects/source_records/raw_assets/processing_jobs/account_usage/rate_windows/deletion_receipts columns and their old PK/unique/FK/index/actions verbatim. Only the changes enumerated here are proposed. AccountUsage.raw_bytes remains raw-only.

Add named suitable composite UNIQUE constraints: `uq_projects_identity(id,owner_id)`; `uq_raw_assets_identity(id,owner_id,project_id)`; `uq_jobs_identity(id,owner_id,project_id,dataset_id,dataset_sha256,method_id,request_sha256)`. These are parent identities, not separate one-column FKs pretending to bind pairs. They preserve all old rows because existing id is a PK. Required legacy parent collation is BINARY; migration preflight verifies it, never silently re-collates bytes.

Add to processing_jobs ONLY `physical_fingerprint H?`, `physical_cpu_ms I(0,J)?`. New named CHECK `ck_processing_jobs_physical_lane`: fingerprint IS NULL implies cpu IS NULL; fingerprint non-null requires method_id IN ('gravity.station-corrections/v1','gravity.equivalent-source-transform/v1'); cpu may be NULL until measured. New `ck_processing_jobs_physical_json`: physical_fingerprint IS NULL OR (typeof(request_json)='text' AND length(CAST(request_json AS BLOB)) BETWEEN 1 AND 35*M AND typeof(preflight)='text' AND length(CAST(preflight AS BLOB)) BETWEEN 1 AND 65536). These bound ACTUAL stored serialization including escaping/whitespace, independently of the stricter34-MiB request wrapper; reject before write if serializer expansion exceeds the native cap. No global serializer change or legacy JSON rewrite. Full audit requires a physical control row iff fingerprint is non-null; successful physical jobs require measured cpu and complete production/result, all non-success output metadata stays null. No existing job gains a fingerprint or CPU measurement.

Exact partial unique index `uq_jobs_physical_reuse(owner_id,project_id,dataset_id,dataset_sha256,method_id,physical_fingerprint) WHERE physical_fingerprint IS NOT NULL AND state IN ('queued','running','succeeded')`. Failed/cancelled rows are outside the index, so retry uses a new UUID. Successful transform non_pass is still succeeded and reuseable. Fingerprint is application-domain SHA-256 of EXACT object `{schema,owner_id,project_id,dataset_id,dataset_sha256,method_id,submitted_parameters_sha256,module_manifest_sha256}`, schema literal `geophysics.physical-job-fingerprint/v1`; it excludes new job UUID/timestamp and includes actual submitted NULL/omission-sensitive parameters and reviewed modules. Compare full fingerprint inputs on hash hit; collision/mismatch closes, never overwrites a row. No scientific normalized-config substitution.

## 3. observation_datasets and physical_dataset_families

Retain the old observation_datasets 13 columns exactly: id VARCHAR(36) PK; project_id VARCHAR(36); owner_id CHAR(36); raw_asset_id VARCHAR(36); version INTEGER; parser_version VARCHAR(80); modality VARCHAR(40); row_count INTEGER; raw_sha256 VARCHAR(64); sha256 VARCHAR(64); byte_count INTEGER; storage_key VARCHAR(180) UNIQUE; created_at DATETIME. All NOT NULL; old project/user/raw FKs and ix_observation_datasets_{project_id,owner_id,raw_asset_id} retained. Old values receive no new lexical/length coercion. Rebuild removes ONLY old UNIQUE(raw_asset_id,parser_version).

Add `kind E(root,derived)`, `root_dataset_id U`, `parent_dataset_id U?`, `payload_schema T(80)`. Backfill is specified in design. New named checks: `ck_dataset_kind` root implies version=1 AND root_dataset_id=id AND parent IS NULL; derived implies typeof(version)='integer' AND version BETWEEN 2 AND J AND parent IS NOT NULL AND parent<>id AND root<>id. `ck_dataset_payload` allows EXACTLY these tuples (kind,parser_version,modality,payload_schema): (root,gravity-station-csv/v1,gravity_station,geophysics.observation-dataset/v1); (root,edi-strict-envelope/v1,edi_transfer_function,geophysics.observation-dataset/v1); (root,gravity-stations-json/v1,gravity_physical_station,gravity-stations-1); (derived,gravity-stations-json/v1,gravity_physical_station,gravity-station-adapter-result-1); (derived,gravity-stations-json/v1,gravity_equivalent_source_transform,gravity-transform-result-1). No prefix/unknown fallback. The complete physical envelope is geophysics.physical-dataset/v2; payload_schema identifies its scientific inner object, not the wrapper. Correction retains the full four-key adapter result; transform the full transform result.

Named UNIQUE `uq_dataset_identity(id,owner_id,project_id,raw_asset_id,root_dataset_id,sha256)`; `uq_dataset_kind_identity(id,owner_id,project_id,raw_asset_id,root_dataset_id,kind)`; `uq_dataset_ordinal(root_dataset_id,version)`. Named partial UNIQUE `uq_dataset_root_parser(raw_asset_id,parser_version) WHERE kind='root'`. Composite FK `fk_dataset_family(root_dataset_id,owner_id,project_id,raw_asset_id,parser_version)` -> families same five columns. Composite FK `fk_dataset_parent(parent_dataset_id,owner_id,project_id,raw_asset_id,root_dataset_id)` -> named `uq_dataset_parent_identity(id,owner_id,project_id,raw_asset_id,root_dataset_id)`. Parent null bypass is permitted ONLY for root. Index `ix_dataset_root(root_dataset_id,version)`.

`physical_dataset_families` complete columns:

| Columns | Domain |
| --- | --- |
| root_dataset_id (PK), raw_asset_id, project_id | U |
| owner_id | O |
| parser_version | T(80) |
| state | E(pending,published) |
| next_ordinal | I(2,J) |
| published_count | I(0,64) |
| reserved_count | I(0,64) |
| created_us | I(0,J) |

Named UNIQUE `uq_family_raw_parser(raw_asset_id,parser_version)` covers pending AND published. Named UNIQUE `uq_family_identity(root_dataset_id,owner_id,project_id,raw_asset_id,parser_version)`. FK `fk_family_raw(raw_asset_id,owner_id,project_id)` -> uq_raw_assets_identity. CHECK `ck_family_capacity` published_count+reserved_count<=64; `ck_family_state` pending requires published_count=0,reserved_count=1,next_ordinal=2; published requires published_count>=1. Index `ix_family_owner(owner_id,project_id)`. Reserved root ID deliberately has NO FK to observation_datasets. Audit pending means exactly one root intent and no root row; published means its committed root row. Allocate under BEGIN IMMEDIATE. Only a proven abandoned pending root with all custody transferred may release the family slot; child abandon never decrements next_ordinal. Ordinal exhaustion J refuses instead of wrapping.

## 4. physical_dataset_edges

Complete columns: `child_dataset_id U` PK; `parent_dataset_id U`; `owner_id O`; `project_id U`; `raw_asset_id U`; `root_dataset_id U`; `role E(scientific_input)`; `parent_dataset_sha256 H`; `child_kind E(derived)`. Named UNIQUE `uq_edge_binding(child_dataset_id,parent_dataset_id,parent_dataset_sha256,owner_id,project_id,raw_asset_id,root_dataset_id)`.

FK `fk_edge_child(child_dataset_id,owner_id,project_id,raw_asset_id,root_dataset_id,child_kind)` -> uq_dataset_kind_identity. FK `fk_edge_parent(parent_dataset_id,owner_id,project_id,raw_asset_id,root_dataset_id,parent_dataset_sha256)` -> uq_dataset_identity. CHECK `ck_edge_distinct` child<>parent. Index `ix_edge_parent(parent_dataset_id)`. Transaction/audit also prove parent ordinal<child ordinal, equality to dataset.parent, published root, permitted ancestry/method and exact parent bytes. The PK permits exactly one input edge, not multiple roles. Root has no edge; each derived row must have one, enforced by final transaction/full audit rather than a false cyclic FK guarantee.

## 5. physical_job_controls

Complete columns:

| Columns | Domain |
| --- | --- |
| job_id (PK), project_id, dataset_id, root_dataset_id, raw_asset_id, stage_id | U |
| owner_id | O |
| dataset_sha256, request_sha256, raw_sha256, submitted_parameters_sha256, scientific_request_sha256, module_manifest_sha256, admission_receipt_sha256 | H |
| method_id | E(gravity.station-corrections/v1,gravity.equivalent-source-transform/v1) |
| raw_bytes | I(1,16*M) |
| request_bytes | B(34*M) |
| module_manifest_bytes | B(65536) |
| parent_production_bytes | B(1*M)? |
| permanent_reservation_bytes | I(0,128*M) |
| created_us | I(0,J) |

Named UNIQUE `uq_control_binding(job_id,owner_id,project_id,dataset_id,dataset_sha256,method_id,request_sha256)` and `uq_control_stage(stage_id)`. FK `fk_control_job` all seven binding columns -> uq_jobs_identity. FK `fk_control_input(dataset_id,owner_id,project_id,raw_asset_id,root_dataset_id,dataset_sha256)` -> uq_dataset_identity. Index `ix_control_owner(owner_id)`. Request BLOB is exact originally saved complete canonical wrapper, not a reconstructed scientific payload; bytes<=34 MiB include all wrappers (35 MiB is the different full job-view cap). Native request_json on ProcessingJob is retained and must semantically/canonically agree; do not mutate historical job JSON. Full producer snapshots follow EXACT 30-key registry; root NULL, correction-parent non-null, no DB-row serialization substitution. Module object follows protected registry. Digest domains/binding checks remain protected contract sections 1/5.1/6. Limits are decoded and compared to exact registered preflight, not numerically inferred here.

Permanent reservation is 80*M correction or 128*M transform while queued/running/prepared, zero ONLY in terminal transfer commit. Control plus request_json logical stored byte charge survives success/failure while the job exists; stages are separately charged. No new JSON self-hash is added. Full source-token/duplicate/NaN/nesting/bytes validation is mandatory; a SQLite BLOB length check alone is insufficient.

## 6. physical_dataset_productions

Complete columns:

| Columns | Domain |
| --- | --- |
| child_dataset_id (PK), job_id, root_dataset_id, project_id, raw_asset_id, parent_dataset_id | U |
| owner_id | O |
| parent_dataset_sha256, request_sha256, submitted_parameters_sha256, scientific_request_sha256, scientific_result_sha256, module_manifest_sha256, result_sha256 | H |
| method_id | E(gravity.station-corrections/v1,gravity.equivalent-source-transform/v1) |
| result_bytes | I(1,64*M) |
| scientific_verdict | E(passed,non_pass) |
| adapter_result_sha256, adapter_receipt_sha256, core_result_sha256, submitted_config_sha256, normalized_config_sha256 | H? |
| adapter_receipt_bytes | B(65536)? |

Named UNIQUE `uq_production_job(job_id)`. FK `fk_production_edge(child_dataset_id,parent_dataset_id,parent_dataset_sha256,owner_id,project_id,raw_asset_id,root_dataset_id)` -> uq_edge_binding. FK `fk_production_control(job_id,owner_id,project_id,parent_dataset_id,parent_dataset_sha256,method_id,request_sha256)` -> uq_control_binding (parent columns map to control dataset columns). Index `ix_production_root(root_dataset_id)`.

CHECK `ck_production_method`: correction requires verdict=passed and ALL six nullable columns non-null; adapter_result_sha256=scientific_result_sha256. Transform permits passed/non_pass and ALL six columns NULL; the full saved original correction remains inside transform scientific_result and its input snapshot, not a fabricated transform adapter receipt. Saved receipt is unchanged exact 13 keys with false acceptance flags. Audit verifies every relation against complete actual job/result/dataset bytes, all 30 parent-snapshot bindings and original NULL/omitted submission hashes. Seven-key envelope production, 14-key bundle index and this SQL relation are distinct identities, not interchangeable objects.

## 7. physical_publication_intents and physical_publication_targets

Intents complete columns: `intent_id U` PK; `kind E(root,job)`; `owner_id O`; `project_id U`; `raw_asset_id U`; `root_dataset_id U`; `parser_version T(80)`; `child_dataset_id U`; `ordinal I(1,J)`; `job_id U?`; `parent_dataset_id U?`; `parent_dataset_sha256 H?`; `request_sha256 H?`; `stage_id U`; `permanent_reservation_bytes I(0,16*M)`; `phase E(prepared)`; `created_us I(0,J)`.

Named UNIQUE `uq_intent_child(child_dataset_id)`, `uq_intent_ordinal(root_dataset_id,ordinal)`, `uq_intent_stage(stage_id)`, partial UNIQUE `uq_intent_job(job_id) WHERE job_id IS NOT NULL`. FK `fk_intent_family` five family identity columns -> uq_family_identity; nullable composite `fk_intent_job(job_id,owner_id,project_id,parent_dataset_id,parent_dataset_sha256)` -> added `uq_jobs_input_identity(id,owner_id,project_id,dataset_id,dataset_sha256)`; composite `fk_intent_parent` parent identity/hash -> uq_dataset_identity. CHECK `ck_intent_kind`: root requires child=root,ordinal=1,permanent_reservation_bytes=16*M and all four job/parent/request fields NULL; job requires child<>root,ordinal>=2,permanent_reservation_bytes=0 and all four non-null (its permanent reservation is already in physical_job_controls). Both root and child reserved IDs have NO FK to missing output rows. Index `ix_intent_owner(owner_id)`.

Targets complete columns: `intent_id U`; `kind E(dataset,result)`; `artifact_id U`; `storage_key T(180)`; `bytes I(1,64*M)`; `sha256 H`. Composite PK `(intent_id,kind)`; UNIQUE `uq_target_key(storage_key)`; FK `fk_target_intent(intent_id)` -> intents PK. Root exactly one dataset target<=16*M; correction one dataset<=16*M plus result<=64*M; transform one dataset<=64*M plus result<=64*M. Artifact ID equals child ID or job ID respectively. Fixed keys are `derived/{owner}/{project}/datasets/{dataset}.json` and `derived/{owner}/{project}/results/{job}.json`, identical existing layout. Full audits check cardinality/keys/ceilings and intent control identities. No caller key, raw/log/cache target or arbitrary path is permitted.

## 8. physical_custody_batches and physical_custody_files

Custody is NOT a publication-target array. Complete batches columns: `batch_id U` PK; `owner_id O`; `project_id U`; `origin_kind E(root_stage,job_stage,publication_abandon,project_deletion)`; `origin_id U`; `stage_id U?`; `deletion_receipt_id U?`; `raw_asset_id U?`; `raw_sha256 H?`; `raw_bytes I(1,16*M)?`; `parser_version T(80)?`; `method_id E(gravity.station-corrections/v1,gravity.equivalent-source-transform/v1)?`; `state E(reserved,active,sealed,cleanup_pending,quarantined,removed)`; `capacity_bytes I(1,1073741824*4096)`; `charged_bytes I(0,J)`; `inventory_bytes B(4*M)?`; `inventory_sha256 H?`; `created_us I(0,J)`; `sealed_us I(0,J)?`; `removed_us I(0,J)?`.

FK `fk_custody_owner(owner_id)` -> user.id, RESTRICT. There is deliberately NO project/intent/job/origin/root/raw FK: these are immutable evidence IDs, not live-row dependencies. No cascade can erase cleanup/deletion debt. UNIQUE `uq_custody_origin(origin_kind,origin_id)`; partial UNIQUE `uq_custody_stage(stage_id) WHERE stage_id IS NOT NULL`; index `ix_custody_owner_state(owner_id,state)` and `ix_custody_project(project_id)`. Owner deletion is blocked while custody records exist; no new account-deletion provider is assumed. Root/job stages require stage_id, no deletion_receipt_id; publication_abandon requires stage_id and receipt both NULL (origin_id is retired intent UUID; the separate stage batch retains its own UUID); project_deletion has receipt UUID, stage_id NULL. Root/job/abandon require all four raw/parser fields non-null, parser_version='gravity-stations-json/v1'; project_deletion requires all four NULL because it can contain many raw families. These origin conditions are named `ck_custody_origin`. CHECK `ck_custody_capacity`: root_stage has method NULL,capacity=32*M; job_stage correction has256*M,transform512*M and method non-null; publication_abandon root method NULL has16*M,correction80*M,transform128*M; project_deletion has method NULL and capacity equal to bounded complete original file sum (minimum1), equality checked transactionally/audit. Other combinations forbidden. Receipt UUID may be reserved before insertion and thus is deliberately NOT an FK; final deletion audit binds it to actual durable receipt. A removed batch retains evidence/zero charge, not automatic destruction.

CHECK `ck_custody_state`: reserved/active have inventory/hash/sealed/removed NULL; their charge=capacity for root_stage/job_stage/publication_abandon, but charge=0 for project_deletion whose original rows remain charged until the deletion commit. sealed/cleanup_pending have inventory/hash/sealed non-null and removed NULL; quarantined permits either incomplete or sealed evidence, removed NULL (incomplete inventory/hash/sealed all NULL; sealed all non-null); removed has inventory/hash/sealed/removed non-null and charge=0. Named `ck_custody_charge`: (state NOT IN ('sealed','cleanup_pending') OR charged_bytes<=capacity_bytes) AND (state<>'quarantined' OR charged_bytes>=capacity_bytes OR inventory_bytes IS NOT NULL). Domain I already supplies nonnegativity. The smaller sealed/quarantined charge must equal the verified retained sum in transaction/audit; this is NOT a SQL aggregate CHECK. All changes need full transaction/audit consistency; SQL CHECK is not evidence that removal occurred. Unknown actual excess must raise charged_bytes to at least measured excess, even above capacity/quota, and block admission. Do not claim a hard ceiling hides an excess file.

Files complete columns: `batch_id U`; `ordinal I(1,4096)`; `role E(raw_delete,dataset_copy,result_copy,request_spool,input_spool,scientific_output,stdout_log,stderr_log,completion,cache)`; `location E(stage,pending_target,deleting_raw,deleting_derived)`; `artifact_id U?`; `leaf T(180)`; `max_bytes I(1,1073741824)`; `actual_bytes I(0,1073741824)?`; `actual_sha256 H?`; `state E(reserved,present,removed)`.

Composite PK `(batch_id,ordinal)`; UNIQUE `uq_custody_leaf(batch_id,location,leaf)`; FK `fk_custody_batch(batch_id)` -> batches PK RESTRICT. CHECK `ck_custody_file_measurement` reserved has both measurements NULL, present/removed both non-null; zero byte ordinary log hashes are allowed (actual SHA of empty bytes), not null-to-zero substitution. `ck_custody_file_role` raw_delete/dataset_copy/result_copy require artifact_id; other roles require artifact_id NULL. CHECK `ck_custody_file_capacity` actual_bytes IS NULL OR actual_bytes<=max_bytes. Role/location/leaf grammar, per-role caps/cardinality and removal evidence are in custody.md. Excess/unknown cannot be forced into this bounded normal table; keep batch quarantine/full charge, close admission and preserve private bounded operator evidence for a separately reviewed exceptional inventory, never drop evidence or fake a normal row.

inventory_bytes is the exact registered custody inventory in custody.md, not a path list or database dump. Its SHA is exact bytes. Immutable sealed measurements may transition present->removed but cannot silently change hash/size. Partial cleanup updates retained charge and inventory in one transaction; original sealed inventory remains preserved inside the JSON as specified. Retirement of an intent/project has no effect on this table.

## 9. Explicit logical deletion order and audit

Under the fully reviewed B exclusion protocol, allocate a project_deletion batch and complete exact inventory BEFORE moving files. Final project deletion transaction inserts the real deletion receipt, sets batch cleanup_pending with charge for every remaining moved/copy/stage byte, deletes publication targets then intents, productions then edges, physical controls then processing jobs, datasets then families, raw assets then source records then project, and decrements AccountUsage.raw_bytes by exact committed raw sum. Reject active physical/legacy jobs or unresolved inconsistent intents rather than racing them. Physical custody rows are NEVER in this deletion list. Remove files only afterwards under the verified removal protocol.

Any FK needed by legacy job input means jobs precede datasets; descendants precede parents if self-parent FKs exist. Explicit topological dataset deletion (highest version first within a family) is required. Families precede raw rows. No dataset producer/edge is reconstructed after deletion. New owner/project/raw hash agreement and exact control request/JSON byte charges are audited before commit. Existing receipt bytes are retained unchanged; physical v2 tombstone extension belongs to B. Therefore project deletion implementation is NOT approved by this A dictionary alone.
