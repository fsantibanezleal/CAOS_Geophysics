# Milestone B: exact boundary, not completed recovery approval

Status: REQUIRED_NEXT_REVIEW_UNIT. A specifies DDL/custody; B is NOT delivered as a final typed authority/runner protocol here. This split is intentional and was disclosed before drafting. No schema/worker implementation may start on A alone. External durable checkpoint provider remains an unresolved owner decision. No provider, service, key, headroom or capability is invented.

## 1. Required ordering and uncertain cuts

The existing `.processing-worker.lock` only excludes other workers. The current worker invokes `_recover_interrupted` before startup inventory, which changes running jobs to failed. The physical lane MUST perform the fully reviewed exclusive fresh-WAL classification before that function can mutate jobs/accounting. A fresh `immutable=1` SQLite connection is NOT a live WAL proof; the existing ops use of immutable applies only to stopped, sidecar-free snapshot inputs.

B must enumerate every writer (API upload/update/submit/cancel/deletion/export scratch, legacy/physical worker/child, maintenance/recovery/backup, and operator writers), lock acquisition ordering/reentrancy/fork/Windows semantics and process death, forbid compute descendants from retaining writer leases, and reject any older writer build that does not participate. Shared API/worker leases must cover DB AND filesystem operations. Exclusive owner recovery drains them and proves all child writers reaped before reading. Out-of-band SQL/filesystem writers cannot be made safe by a cooperative lock alone: retain ingress/stopped-writer maintenance proof and deployment-source pin. Missing proof fails closed. No host unit mutation is authorized by this SDD.

Discard uncertain sessions/transactions/connections; preserve DB, WAL and SHM. Under all-writer exclusion open a new normal WAL-aware connection. B must pin runtime driver/Python and verify foreign_keys=1, journal_mode=wal, synchronous=FULL (numeric2), trusted_schema=OFF, busy_timeout=30000, successful integrity/FK checks and coherent source revision/DDL fingerprint. Current app sets WAL/FK/busy_timeout but NOT explicit FULL; this is a proposed requirement, not a current durability claim. Unsupported directory durability/platform/runtime closes. No manual WAL unlink, stale read TX, immutable live connection or preclassification legacy recovery.

| Cut | Public state allowed | Required locked classification/action |
| --- | --- | --- |
| Reservation commit uncertain, before file creation | None | Read fresh batch/control/family uniqueness; if coherent committed, retain reservation; absent proof means do NOT create files |
| Declared stage partial, no prepared intent | None | Exact batch remains charged; child reap; bounded inventory seal or quarantine; nonsuccess transfer only after coherent DB classification |
| Prepared intent commit uncertain | None | Durable intent+complete targets+stage+control or proven absent prepared commit; mixed rows/unknown files inconsistent |
| Only one installed output | None | Prepared_uncommitted only if exact intent-owned destination set/subset and no public dataset/production/success; abandon-only with co-committed debt |
| All installed, final commit not attempted | None | Same prepared_uncommitted; NOT authority to automatically finalize |
| Final success commit uncertain | Exact coherent committed success only | Complete dataset/edge/production/job/result/control/allocator bindings AND no intent AND cleanup debt prove coherent_committed; prepared intent/no visible publication proves prepared_uncommitted; any mix inconsistent |
| Failure/cancel/abandon commit uncertain | Exact coherent terminal disposition only | Terminal state, no outputs and all retained-byte debt with retired intent prove committed; otherwise preserve reservations; never release quota from exception path |
| Success cleanup interrupted | Existing coherent success | Keep success plus exact cleanup debt; verify/removal updates only, no publication rollback |
| Deletion move before DB commit | Original logical project remains | Exact declaration+receipt reservation+move evidence; do NOT treat moved file as absent/deleted or use old inventory sweep |
| Deletion commit uncertain | Coherent original OR coherently deleted project | Receipt+no project+full custody versus original rows/full committed charges; unexpected mixed state inconsistent |
| Cleanup removal commit uncertain | Conservative retained debt | Fresh inventory/removed set and filesystem proof; missing filename alone cannot release charge or erase evidence |
| Post-reopen migration defect | All subsequent committed writes retained | Forward repair or independently reviewed write-preserving reconstruction; never old-snapshot rollback |

Classification is exactly coherent_committed, prepared_uncommitted, inconsistent. Prepared/uncommitted disposition is abandonment only, not adoption/resume/finalization. Inconsistent blocks startup, cleanup, backup and admission with bytes/debt preserved. B must turn this table into an exact bounded record-by-record algorithm/test oracle, including exceptions/death during each classification/cleanup transaction; A does not claim this is already implemented or platform-proven.

## 2. Required v2 authority and legacy bridge

B must enumerate COMPLETE key sets/types/byte/depth/node/string/count bounds for v2 tombstones, latest authority, predecessor hash/sequence, registrations/expiry, source-policy/schema pins and every nested graph/control/custody record. Preserve original v1 receipt bytes/digests; do not replace historical tombstone hashes with hashes of a reconstructed new object. A new v2 record needs an explicit old-receipt domain/payload binding rather than claiming it is byte-identical to v1.

The existing v1 adapter remains EXACT revision0003 and global JSON_CAP16 MiB; do not raise it for physical64-MiB objects. B must add positive per-schema parsing/caps for registered physical request/dataset/result only, with complete EOF/duplicates/token/hash/graph/receipt checks; unknown future operations/revisions fail closed. A does not allocate a new revision name or measured fingerprint without this registration review.

Old0003 snapshot/new-v2-authority bridge MUST first validate the complete old snapshot with its unchanged frozen adapter and preserve survivor bytes. A later legitimate child/job/raw asset named in a deletion tombstone may never have existed in that older snapshot; absence is not automatically corruption. For overlapping IDs, owner/raw/root/hash identity must agree; an absent later node does not excuse a mismatched overlapping node. Remove the complete tombstoned project set only in a NEW candidate, preserve all newer deletion evidence in latest authority, revoke sessions and rebuild logical account charges. No flattening of children into roots/parser aliases, no subset graph and no restoration of a deleted project through a convenient older authority.

Freshness requires independently trusted latest authority ciphertext hash/sequence/watermark and cumulative predecessor/registration chain; an authority bundled in an older snapshot is not proof it is latest. External durable checkpoint ACK/atomic publication/authenticity/failure/lag policy is an owner-selected unresolved dependency. Do not invent its API/service or certify deletion durability before that owner choice and actual tests. A local durable deletion debt or receipt is not proof off-host backups were erased.

## 3. Required exact source policy

The currently reviewed selected-source policy includes legacy0001/0002/0003, strict gravity/EDI/MT parsers/worker/recovery and separate immutable runtime/ops commit pins. A new physical runtime must register the exact migration file and all actual core/ordinary adapter/transform/parser/wrapper/storage/recovery source paths with independently reviewed Git blob hashes. No generic `app/*`, automatic next-revision fallback, parser suffix, optional unknown module or mutable checkout head. Policy selection is reviewed separately from source tar/build receipts; none proves host execution/admission.

The actual core/adapter pins and approval scopes from PR123 stay unchanged. The wrapper/migration path names and integrated commits do not yet exist: B must choose/freeze them through main review BEFORE schema-owner code, not let implementation fill them implicitly. Keep v1 policy usable exactly as before. New selected-source policy is separately versioned and bounded; existing 8-MiB/file,64-MiB selected bytes,80-MiB archive and4096-file guards are NOT weakened. Runtime/ops pair agreement and missing/extra/rehashed source negatives are required. No source archive is produced by this docs-only unit.
