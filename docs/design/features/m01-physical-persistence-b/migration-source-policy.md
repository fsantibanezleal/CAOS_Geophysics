# Exact proposed revision, source registry and implementation scope

Status: reviewed-candidate design awaiting MAIN. No migration file/module/source bundle is written here. Revision/path choices below are explicit review proposals, not installed schemas. Registration of measured hashes happens only after separately authorized candidate implementation.

## 1. Revision and fingerprint

Exact proposed revision `0004_physical_persistence`; down_revision `0003_processing_jobs`; branch_labels/depends_on NULL. Exact future file `app/migrations/versions/0004_physical_persistence.py`. Inspected A source has only0001/0002/0003; later read-only origin/develop at452e90bcbb09db40e4fcd51b9b4854778eb79a29 also has only those revisions. If integration introduces a conflict, STOP and obtain an amended pinned review; never auto-increment/suffix the name. Proposed runtime app/database.MIGRATION_HEAD changes to0004 ONLY in later B-RUNTIME integration; source-only B-SCHEMA does not activate the candidate or change the existing application's head.

0003's approved DDL fingerprint is EXACT `33a96998cd77c595a0d983461f84e1367a813e460b9c13222d07490fd9b86709`, as current ops constant. New0004 adds A dictionary plus B's two tables/unique parent. No ORM create_all. The new measured fingerprint uses EXACT original ops algorithm: SHA256 of UTF-8 JSON array of tuples from `SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name`, compact separators,ensure_ascii=False. Compare complete actual DDL text, not an inferred ORM object list. It must be generated from the separately approved disposable Alembic candidate, then independently checked and pinned; NOT_RUN now, no fake digest. Native spelling/reflection differences require review, not whitespace-normalized acceptance.

`geophysics.physical-schema-registration/v1` EXACT keys: schema,revision,down_revision,ddl_sha256,migration_sha256,migration_git_blob. Positive pairs ONLY0003_processing_jobs/down0002_private_storage_permission and0004_physical_persistence/down0003_processing_jobs; hashes H,git blob40-lowerhex; object<=65536,depth4,nodes1000. Legacy migration path/hash/blob must match the actual0003 source; new values come from reviewed candidate. All required. UNREGISTERED is an external admission state (record absent), NOT a nullable accepted hash or runtime fallback. The enclosing policy contains these registrations; registrations do NOT contain that policy's digest, avoiding a self-hash cycle. A runtime matching only revision name but not DDL/source pin refuses.

## 2. Candidate migration procedure

An explicitly approved B-SCHEMA unit works on a NEW disposable copied0003 fixture/candidate only, with all source writers continuously stopped and immutable pre-migration receipts. No live database/path overwrite or service action. Preserve all thirteen old dataset values/native JSON/timestamps and every other legacy value/SQL type/file/hash; old views/discriminators unchanged. Rebuild dataset table to remove only the raw/parser global UNIQUE, backfill family/root metadata exactly A, add composite parents/indexes/jobs additions and empty A/B tables. Do NOT fabricate legacy controls/producers/deletion extensions/runtime-control row or measured CPU. Candidate FK handling is controlled outside transactions under pinned Alembic/SQLAlchemy driver tests, restoredON before integrity/FK/full identity checks. No runtime permission to turn FKs off.

Measure new DDL and verify every A/B named constraint/action/index/partial predicate and full old-value/type/file inventory. Reject unknown old state/source format/deletion receipt rather than normalize. Existing incomplete/oversized legacy receipt evidence stays unchanged; unsupported v2 operations refuse, not destroy it to pass. AccountUsage.raw_bytes remains raw-only. New global byte/row/page/source caps stay separate; do not use the1-GiB account quota as a filesystem headroom substitute.

Downgrade after physical children/intents/debt/extensions is forbidden. Even an empty graph does not authorize destructive rollback after writer reopen. Pre-migration snapshot fallback needs continuously stopped ALL writers and no later committed write; otherwise forward repair or separately reviewed reconstruction preserving every later source/upload/job/version/deletion/account write. Latest tombstones cannot recreate those writes. No restore path swap is part of this docs unit or B-SCHEMA approval.

## 3. Source selection policy v2

Proposed `geophysics.ops-physical-source-policy/v2` EXACT keys: schema,policy_id,runtime_commit,ops_commit,database_schemas,files,module_manifests. policy_id literal m01-physical-persistence-v2; independent40-hex reviewed Git commits; database_schemas exact revision->registration map above (legacy entry contains fixed revision/DDL/migration identity, not a fabricated0004 registration); files EXACT runtime,ops maps; module_manifests EXACT correction,transform. Complete policy<=1 MiB,depth12,nodes20000. No unregistered extra version/method/path. Each file value EXACT bytes,sha256,git_blob with0..8MiB,H,40-hex actual Git blob; exact regular file content MUST match pinned commit/blob AND independently approved SHA/count. No LFS pointer/symlink/native executable binary/private binary/venv/.env/database/credential/generated artifact; plain reviewed Python source is not forbidden merely by an executable permission bit. Policy is generated as separately reviewed provenance outside its own selected commit/archive, avoiding a commit/policy self-hash cycle; no digest of the policy is stored inside itself.

Policy is a new independent validation/selection record, not an altered v1 selected-source schema. Existing selected-source/v1 SHA/count/archive policy remains unchanged. Source-only archive verification still caps8MiB/file,64MiB selected total,80MiB USTAR archive,4096 files; exact expected map, directory set, no aliases/traversal/link/PAX/trailing/duplicate files and complete hashes before extraction/acceptance. New policy permits ONLY the exact47 runtime and8 ops paths below; there is no `app/*`, recursive discovery or "all future migrations". Missing planned files keeps policy unregistered/closed; existing files do not make a future bundle approved automatically.

### Complete runtime47 paths

Frozen legacy34:

```
app/__init__.py
app/alembic.ini
app/auth.py
app/bundle.py
app/compute.py
app/config.py
app/database.py
app/errors.py
app/formats.py
app/main.py
app/migrations/env.py
app/migrations/versions/0001_api_foundation.py
app/migrations/versions/0002_private_storage_permission.py
app/migrations/versions/0003_processing_jobs.py
app/models.py
app/mt_bundle.py
app/mt_compute.py
app/mt_contract.py
app/processing.py
app/processing_contract.py
app/processing_storage.py
app/projects.py
app/schemas.py
app/security.py
app/server.py
app/views.py
app/worker.py
data-pipeline/edi.py
data-pipeline/electromagnetics.py
data-pipeline/geology.py
data/fixtures/edi/halfspace-100-native.edi
data/fixtures/edi/two-layer-noisy-rotated.edi
tests/api/conftest.py
tests/api/test_online_mt.py
```

Exact physical13 additions (not edits authorized here):

```
app/migrations/versions/0004_physical_persistence.py
app/physical_contract.py
app/physical_persistence.py
app/physical_leases.py
app/physical_recovery.py
app/physical_compute.py
data-pipeline/gravity_processing.py
data-pipeline/gravity_station_adapter.py
data-pipeline/gravity_transforms.py
tests/api/test_physical_persistence_schema.py
tests/api/test_physical_leases.py
tests/api/test_physical_processing.py
tests/ops/test_physical_recovery_contracts.py
```

### Complete ops8 paths

```
scripts/ops_recovery.py
scripts/ops_source_pin.py
scripts/ops_host_fixture.py
tests/ops/mt_drill.py
scripts/ops_physical_recovery.py
scripts/ops_physical_source_pin.py
tests/ops/test_physical_native.py
tests/ops/physical_drill.py
```

Current paired-source builder may be consumed as an existing separately approved tool, not silently edited or included as a required runtime dependency. Exact builder provenance/bundle receipt remains separate from runtime/ops policy. This branch does not merge current develop or copy its adapter/tool files. The actual adapter present in read-only origin/develop has SHA b770b16e... unchanged from approved PR119; full hashes/source pins are in research. It is absent from protected e67f7ff checkout, so that checkout cannot claim full physical runtime readiness.

## 4. Scientific module mappings and descriptors

Protected module_manifest is EXACT schema,parser_sha256,wrapper_sha256,adapter_sha256,core_sha256,transform_sha256,runtime_manifest. Parser maps to app/physical_contract.py; wrapper to app/physical_compute.py. Core maps data-pipeline/gravity_processing.py; ordinary adapter gravity_station_adapter.py; transform gravity_transforms.py. correction requires adapter/core actual hashes,transformNULL; transform requires core/transform,adapterNULL. runtime_manifest exact python/python_implementation/packages as protected scientific contract: actual approved CPython3.12.x/core PINS or TRANSFORM_PINS, not latest-vendor defaults. No new transform adapter or numerical algorithm. Keep unchanged four-key adapter result/thirteen-key receipt and false scientific acceptance flags, valid terrain:null versus omission hashing and distinct actual submitted/normalized configs.

Core/adapter/transform expected source identities remain exactly `7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321`, `b770b16ef87e83dd92f65a90472145ef93a525a9cedf7f55ee3e6f20f8a10cf8`, `d11d0f207c89c308c9f8711da2a31b84b8adaeb0c12597a5ecc89ce527fdecf0` at this research pin. If integration changes any scientific source, stop for scientific review, not normalize a mismatched policy. Future parser/wrapper/DDL/runtime/ops hashes are mandatory measured inputs after reviewed code, never invented today. Log/output/input limits are intersections: protected child stdout/stderr65536 are stricter than A custody1-MiB defensive slots; retain65536. Whole wrappers and method-specific scientific/permanent ceilings ALL apply. No enlarged cache/phone admission follows from v2 policy.

Physical control digest descriptor is EXACT the complete A physical_job_controls column names, except BLOB fields request_bytes/module_manifest_bytes/parent_production_bytes become `{bytes,sha256}` descriptors (parentNULL staysNULL). All remaining columns retain exact SQL types/values; descriptor SHA uses application canonical bytes. Stage/control ownership/raw/input/request/module/admission bindings are checked with complete saved BLOBs, not inferred from descriptor hash alone. Complete descriptor<=65536,depth8,nodes2000. Deletion digest is taken from the actual terminal control whose permanent_reservation_bytes=0, not its earlier queue reservation. This provides stable deleted-job evidence without embedding35-MiB request/native-JSON duplicates in a tombstone. It is NOT a seven-key envelope production or30-key parent snapshot. Full startup/source/export verification still binds actual unchanged receipts/configs/results before deletion/capture.

Full fresh-classifier inventory digest uses EXACT object `{schema,database_revision,ddl_sha256,source_policy_sha256,storage_generation,lease_generation,rows,files}`, schema geophysics.physical-inventory/v1. rows is exact named-table->PK-sorted complete row descriptors of every registered table; BLOB/JSON native text represented by exact byte/count SHA descriptors, other fields retain SQL type plus value, nullable explicit. Each scalar descriptor EXACT type,value; type integer/text/real/null and actual SQL typeof; BLOB/text byte descriptors EXACT type,bytes,sha256 with type blob/json_text. Tables ONLY legacy11 including alembic_version plus A8/B2 (21 total). No query-dependent omitted column. One explicit digest projection: runtime_control.last_clean_inventory_sha256 and audited_us are validated in the FULL row audit, but replaced by `{"type":"null","value":null}` in the digest projection, avoiding the cache pointing into its own hash. No other column is omitted/projected. Cache update cannot authorize a changed generation/source/row/file; those remain hashed and separately rechecked. files exact registered key->`{bytes,sha256,role,owner_id,project_id,origin_id}` map covering committed and known pending/custody plus fixed metadata descriptors. Ordinary file bytes I(0,1GiB)/SHA H; role raw/dataset/result or exact A custody role; owner/project U; origin_id actual artifact/batch U. Lock metadata role=writer_lock has owner/project/originNULL,bytes1 and actual one-zero-byte hash. Native metadata logical keys ONLY @database,@wal,@shm,role=native_metadata, all five remaining fieldsNULL: identity/existence/stat proof is separately native, not a false stable file hash/size while SQLite updates bookkeeping. The actual DB path mapping must match independently initialized native proof; a missing actual database is never admitted by a NULL descriptor. Only present WAL/SHM are included, no journal/unknown metadata bypass. Hash projection excludes the three native_metadata entries entirely (their existence/identity still fully audited), so SQLite's own creation/removal of SHM/WAL bookkeeping is not a false logical-inventory change. Scientific files remain byte-hashed. Full saved BLOB/JSON/member bodies are strictly validated before these descriptors are built; caller-supplied digests/"validated" flags cannot substitute for cross-binding. Duplicate/unknown table/column/key/state/schema -> inconsistent. Complete descriptor<=16 MiB,100000 rows/files,depth16,nodes500000; exceed refuses before disposition, no truncation. Stable digest recalculated before action from SAME logical state; native metadata/cache exclusions are explicit, never arbitrary unknown-file exclusions.

## 5. Explicit proposed code-owner scope after review

No code authorized now. MAIN may later approve B-DATA for new physical_contract/physical_recovery plus pure tests and new ops physical parsers only, with no production imports/writes; and B-SCHEMA for new0004 plus scoped models definitions and schema fixtures on NEW local copies. Such approvals must name paths/tests and cannot silently authorize API/worker wiring. B-NATIVE owns physical_leases/native tests; B-RUNTIME later owns narrowly scoped app/database/worker/main middleware/processing/storage/projects/startup changes and physical_compute with actual child/CPU/host proof. Existing auth behavior, legacy physics/bundles, scientific sources, canonical artifacts, frontend/courses and other owner files are NOT implementation scope of B-DATA/B-SCHEMA.

Existing scripts/ops_recovery.py/source_pin.py frozen v1 validators and code remain unmodified in initial B-DATA; new positive dispatcher may invoke them on exactly registered0003 only. Any necessary v1 code change needs separate MAIN review. No public activation/provider/host/deploy service changes belong to these local units. Candidate source-policy hashes and explicit MAIN full-B code-scope approval precede implementation, not follow it.

The source-only47runtime/8ops policy is NOT a SQLite distribution/binary allowlist. Native admission additionally requires the exact geophysics.sqlite-wal-patch-build/v1 record and independently reviewed loaded-binary/source_id tuple in leases-wal.md; its SHA binds the revised native proof. No SQLite binary is copied into the source archive or historical module manifests. Future candidate/schema tests need separate explicit authorization; any physical native/WAL experiment needs PB21-supported build evidence before target open. All registries/native contexts remain CLOSED now; no existing dependency, interpreter, host or source pin is modified to pretend a patch was installed.
