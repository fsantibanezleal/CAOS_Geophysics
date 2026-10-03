# M01 physical persistence: milestone A design

Status: proposed, not implemented. Read [requirements](requirements.md), [column/constraint contract](sql-contract.md), [custody](custody.md), [recovery boundary](recovery-boundary.md) and [review packet](review-packet.md) as one review unit. The exact baseline and primary references are in the [research dossier](../../../research/m01-physical-persistence-2026-10-03.md).

## 1. Decision and limitation

The initial physical version graph is a one-parent branching forest, not a general multi-input DAG. Existing root IDs, parser versions, version=1 and scientific files stay unchanged. Children use real family ordinals and fixed parser identity, never parser suffixes. Legacy gravity flag-only and EDI/MT rows do not acquire invented physical producers.

The allocator owns the reserved root UUID before a dataset exists. A root intent references that allocator identity, not an absent dataset. Published datasets reference the allocator; child edges reference already committed parents. Producer relations reference existing input jobs and children without adding a reverse job-to-child FK cycle. Ordinal gaps are retained; ordinals are not correction counts.

Publication targets are only the immutable dataset and job result destinations. Custody is separately recorded for stage files, pending installed copies and exact project-deletion files. Success/failure/cancel and abandonment leave durable custody even if the publication intent is deleted. Project deletion leaves durable custody even if all project rows are gone. Cleanup is a later, independently committed verified-removal event, not part of scientific success.

This unit deliberately does not pretend that SQL constraints implement scientific verification, a filesystem transaction or a crash-safe runner. Cross-row audits, cancellation, per-job CPU accounting, directory durability and the v2 recovery/source adapters need review and actual future tests. A schema dictionary is not a migrated SQLite fingerprint.

## 2. Transaction ownership

All physical admission/accounting transactions use `BEGIN IMMEDIATE`, but this database lock alone does not exclude filesystem writers or stale API/worker code. Milestone B must define a cross-process all-writers protocol covering API uploads/deletions/export scratch, physical/legacy workers, schema maintenance and recovery tools, with platform-specific locking proofs. No process may hold a SQLite transaction while waiting for that protocol's exclusive lock. No runtime or host lock is created by these docs.

Queue-time accounting reserves permanent dataset/result ceilings and full stage capacity before a child launches. Root structural parsing reserves its own stage before creation. Final installation uses exclusive ordinary copies; each stage and installed copy is charged separately. Symlinks, junctions, hardlinks, reflinks, shared inode aliases and arbitrary cache paths are unsupported in this lane. Existing legacy bytes are not copied or renamed by schema backfill.

The final transaction checks owner/project/raw/parent/request/config/module/result identities and cancellation, inserts the immutable dataset/edge/production, makes result/success visible, transfers stage reservation into retained custody and deletes the intent in the SAME commit. A failure/cancel transaction analogously retains installed unpublished files and stage debt, publishes no scientific child/result and retires only proven reservations. Unknown inventory blocks this transition instead of becoming a convenient failure with released quota.

## 3. Legacy preservation and migration boundary

Baseline `0003_processing_jobs` is a fixed input, including its unnamed global raw/parser unique constraint. Only `observation_datasets` needs a reviewed candidate-table rebuild to replace that constraint with a named root-only partial index and add family metadata. The exact old 13 column definitions and all old FK/index/storage-key semantics are retained. All other old table columns remain untouched; named composite unique constraints required below are additive. Existing JSON values must be copied as stored SQL text, not decoded/re-encoded. Original file hashes, DB value/type inventory and scientific acceptance declarations must agree before/after. A rewritten DB file hash is naturally different and is not the legacy-value equality check.

Backfill one family per existing dataset; it is published with root UUID=id, next_ordinal=2, published_count=1, reserved_count=0. Add kind=root, root_dataset_id=id, parent=NULL, payload_schema=geophysics.observation-dataset/v1. No production/physical job control/custody/intent is fabricated. Existing raw-only assets have no family. Invalid/unknown legacy rows, active jobs, sidecars or interrupted stage require explicit review, not normalization.

Migration revision is a milestone B assignment after integration-base inspection and main approval, not an implementation-critical column/type left to the schema owner. No `0004` is presumed available. No migration/source code may begin before that registration and full B review. DDL fingerprint must be measured from the actual reviewed candidate. Maintenance must keep all writers stopped throughout candidate validation/replacement; no service action is authorized here. Snapshot fallback is allowed only if writers never reopened and no subsequent committed writes exist. After reopen, use forward repair or separately reviewed reconstruction preserving every later write.

## 4. Capacity and compatibility

Physical admission retains the existing one-active-job/account and configured global queue limit; it does not weaken legacy guards. Family published+reserved capacity is 64; maximum actual ancestry is four edges. Failed/cancelled intents leave ordinal gaps but release the reserved-node count only with custody transfer. Existing roots remain root rows regardless of whether the physical feature is closed.

New record budgets are exact server ceilings, not measured runtime/device permissions. Root stage 32 MiB, correction stage 256 MiB, transform stage 512 MiB; permanent root ceiling 16 MiB, correction 80 MiB (16+64), transform 128 MiB (64+64). These correct the previous ambiguous 64-MiB total-output proposal: a complete wrapped transform dataset and a separate result can each reach 64 MiB. Main must explicitly review this larger dual-artifact reservation; it grants no execution approval. Full job request storage is additionally charged as specified in custody. Phone verification admission remains unset/closed; 512 MiB is NOT a phone budget.

Deletion inventory is bounded to 4,096 ordinary files and 4 MiB of control JSON per batch; each actual custody leaf has a 1-GiB defensive cap. It must cover the COMPLETE project file set and relevant retained stages. If a legitimate legacy project exceeds these bounded limits, refuse before moving/deleting anything and require a separately reviewed large-inventory procedure. Never truncate or discard old bytes to meet a new bound. This limitation blocks claiming universal project-deletion acceptance for the full vertical.

## 5. What remains intentionally outside A

Milestone B owns all-writer lock mechanics and exact uncertain-commit proof; complete v2 deletion tombstone/authority/registration/expiry/0003 bridge; migration revision; new source-policy paths and module pins. External durable checkpoint provider remains an unresolved owner choice, not an invented service. Per-job Linux/Windows lifetime CPU accounting and measured browser memory remain separate unresolved designs/tests. A review must not imply B or full vertical approval.
