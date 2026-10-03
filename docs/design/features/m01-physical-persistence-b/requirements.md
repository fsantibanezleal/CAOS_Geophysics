# Physical persistence B requirements

Status: PLANNED, DOCS_ONLY, MAIN_REVIEW_REQUIRED. No implementation approval. MAIN accepted A's complete proposed dictionary at e67f7ff; the acceptance record is8856f5d267f6c9d27764df55f0c06e5b8b39a5b3. Original scientific input87eb9 and PR123 attribution-only9d19209 are separate immutable pins. See [design](design.md) and [review/tasks](review-packet.md).

| ID | Prospective EARS requirement | Named future gate |
| --- | --- | --- |
| MP-B01 | Before any API/worker filesystem or SQLite access, the registered writer SHALL obtain its prescribed lease without holding a DB transaction. | PB05_lease_order |
| MP-B02 | While a handler, export stream or child can write, its supervising writer SHALL retain its lease; no timer SHALL expire a live lease. | PB06_lease_lifetime |
| MP-B03 | If process/native containment, lease identity or file durability proof is absent, the physical runtime SHALL remain closed. | PB07_native_closed |
| MP-B04 | If commit is uncertain, the system SHALL dispose the old session and classify fresh WAL under exclusive all-writer exclusion BEFORE legacy interrupted recovery. | PB08_fresh_wal |
| MP-B05 | When classifying, the system SHALL accept only exact coherent committed or prepared/uncommitted predicates; every other row/file mixture SHALL be inconsistent. | PB09_classification |
| MP-B06 | When a publication is proven uncommitted, the system SHALL abandon it with atomic custody transfer, never automatically adopt/finalize it. | PB10_abandon |
| MP-B07 | When a legacy receipt is wrapped, the system SHALL preserve its actually observed source bytes and canonical v1 identity distinctly, without inventing unobserved native SQL bytes. | PB11_receipt_bytes |
| MP-B08 | When checkpointing v2 authority, the system SHALL preserve cumulative immutable tombstones/registrations and bind predecessor/sequence/source policy explicitly. | PB12_authority_chain |
| MP-B09 | If the external latest-checkpoint provider/ACK is unset, production authority/recovery/deletion admission SHALL remain closed. | PB13_provider_closed |
| MP-B10 | When restoring0003 using latest v2 authority, the system SHALL validate the unchanged v1 snapshot first, reject overlapping contradictions and permit legitimate later IDs absent from that snapshot. | PB14_legacy_bridge |
| MP-B11 | When parsing physical objects, the system SHALL apply only their positive per-schema caps, never raise the legacy v1 JSON guard. | PB15_dispatch_caps |
| MP-B12 | When migrating the reviewed new candidate, the system SHALL use exactly0004_physical_persistence/down_revision0003_processing_jobs and preserve all legacy values/files. | PB16_revision |
| MP-B13 | If a revision, DDL fingerprint, source path/commit/module or future operation is unregistered, the system SHALL refuse rather than use a legacy fallback. | PB17_source_registry |
| MP-B14 | After writers reopen, the system SHALL refuse pre-migration snapshot rollback that loses subsequent committed writes. | PB18_rollback_hold |
| MP-B15 | When producing a restore candidate, the system SHALL expose no validated object until complete archive EOF/member hashes/DB and graph/custody checks pass. | PB19_restore_barrier |
| MP-B16 | If only local pure-data/schema implementation is approved later, the implementation SHALL have no production writer, child, provider, API or host activation path. | PB20_scope_partition |
| MP-B17 | Before opening any physical native WAL target, the system SHALL require the actual SQLite version/source_id/loaded binary tuple and independently reviewed upstream or exact distribution-backport evidence to match an explicitly supported patched-build record; affected unpatched and unknown tuples SHALL remain CLOSED without numeric backport inference. | PB21_sqlite_patch_admission |

All named gates are prospective definitions in [validation](validation-plan.md), NOT_RUN. No SQL candidate or runtime tests are executed by this document task. A's1-GiB quota,32/256/512-MiB stages,16/80/128-MiB permanent ceilings and unknown-cache CLOSED policy are preserved as design choices, not measured resource/device admission.
