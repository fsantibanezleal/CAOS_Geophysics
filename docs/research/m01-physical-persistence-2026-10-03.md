# M01 physical persistence research, 2026-10-03

Status: researched docs-only milestone A; no product/schema execution. See [feature packet](../design/features/m01-physical-persistence/review-packet.md) and [fresh receipt ledger](m01-physical-persistence-primary-sources.json). Primary pages were actually fetched as bytes on2026-10-03; response SHA/counts are not copied from PR123 and not a vendor signature. No webpage bodies/private data are committed.

## Exact repository baseline and full reading

Application baseline is protected87eb9e9bd65e8a5cd1385d9c58e5ed32460461bb, same application/recovery files as develop at initial1b112bb258520a5679a865335cec30b6a97a1a0d inspection. Develop moved during coordination; no latest-develop merge or new source approval is implied. Attribution-only9d192094e16452e7f43556a69067d95fe633bb0f changes no code. Read-only latest-develop paired-source-bundle operations guide was additionally inspected; it is not silently substituted for the frozen source policy.

Fully inspected0001/0002/0003 migrations; models, database, processing storage, worker, projects, processing, processing contract and config; full ops_recovery and ops_source_pin; runtime dependency pins and backup/restore guide. Existing processing MT identity is retained from its fixed contract, not scientific solver work. Source ledger hashes identify actual local file bytes, including working-tree line endings; they are NOT Git normalized-blob hashes or a measured migrated DDL hash. Selected-source provenance must later use reviewed Git blobs. Read the installed GUID implementation read-only to verify owner IDs are CHAR36 hyphenated UUID strings, not guessed32-hex IDs.

0003 has only thirteen dataset columns, globally unique raw_asset_id/parser_version and no family/edge/producer/intent/custody. Jobs reference input dataset; success stores one result key/hash/count. There are no physical CPU columns. Existing AccountUsage.raw_bytes is raw-only. The old user/token/project/source/raw/rate/receipt definitions must retain their original metadata/JSON/time values. Existing deletion_receipts.project_id is already a non-FK unique historical ID; do not infer custody survival from a proposed FK cascade.

Observed code gaps: worker terminal commit precedes clear_known_stage; project deletion commits before exact raw/derived unlink. Worker byte lock is worker-only; recover_interrupted mutates running state before startup audit. Connection setup enables FK/WAL/busy timeout but does not explicitly pin synchronous=FULL. Ops is exactly revision0003, frozen v1 schemas/16-MiB JSON cap; stopped sidecar-free immutable input is not a live WAL classifier. Ops source pins legacy/MT files only. These are inspected source facts, not a crash execution or a proof that the future proposal works.

## Primary-source interpretation

- [SQLite datatype documentation](https://www.sqlite.org/datatype3.html): affinity and declared length are not strict transport validation. Proposed explicit SQL CHECKs plus source-token validation are independent layers.
- [SQLite foreign keys](https://www.sqlite.org/foreignkeys.html): referenced parent identities must be suitable unique keys; enforcement is connection-scoped. Composite references are specified as pairs/tuples, not independent column FKs.
- [SQLite partial indexes](https://www.sqlite.org/partialindex.html): WHERE scopes index entries. Proposal uses distinct root-only and active/success-only uniqueness; this does not enforce cross-row scientific provenance.
- [SQLite WAL](https://www.sqlite.org/wal.html): committed data may reside in WAL, so preserve sidecars and use fresh WAL-aware reads under exclusion. Immutable clean snapshots and live uncertain state are different inputs.
- [SQLite PRAGMAs](https://www.sqlite.org/pragma.html): connection durability/enforcement readback is a separate prerequisite. Proposal requires FULL; current runtime is not claimed already pinned or power-loss tested.
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html): BEGIN IMMEDIATE establishes the write transaction boundary. It cannot serialize external file writers or replace a durable custody protocol.
- [SQLAlchemy constraints](https://docs.sqlalchemy.org/en/20/core/constraints.html): ForeignKeyConstraint represents composite parent binding. Explicit deterministic names are part of the candidate dictionary, not evidence an ORM relationship enforces immutable history.
- [SQLAlchemy SQLite dialect](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html): FK/driver/transaction details need versioned testing. Current pins SQLAlchemy2.0.54,alembic1.20.0,aiosqlite0.22.1 are inspected, not upgraded.
- [Alembic batch operations](https://alembic.sqlalchemy.org/en/latest/batch.html): SQLite rebuild/reflection of constraints needs review. Candidate migration must preserve SQL native JSON text and all legacy values, not decode/re-encode old rows.
- [Python3.12 JSON](https://docs.python.org/3.12/library/json.html): hooks/default decoding behavior require explicit duplicate/nonfinite and numeric-source checks. Byte-domain hashing preserves original saved bytes separately from canonical application/scientific object digests.

These primary facts motivate authored proposals, not ready-made repository implementations. SQL types/role ceilings/fingerprints/custody shapes are NEW design choices requiring MAIN review. No primary page establishes host capability, per-job lifetime CPU enforcement, backup-provider freshness or safe phone memory admission.

## Retrieval notes and non-claims

First byte-receipt attempt used a newer .NET HashData API unavailable in this PowerShell runtime; it produced no usable receipts. Retried with SHA256.Create().ComputeHash and recorded the actual successful bytes. The unusually large partialindex HTTP body was checked for its Partial Indexes title and expected Unique Partial Indexes/CREATE UNIQUE INDEX text, not assumed from HTTP200 alone. No local source file was edited by retrieval. An attempted fingerprint of a nonexistent ops_source_bundle.py was discarded; actual existing source-policy file is ops_source_pin.py. No failed/missing hash is included as evidence.

Milestone split: A is exact proposed DDL/custody, while B still needs complete typed v2 authority/legacy bridge/migration revision/source policy and measured all-writer/platform classifier. External durable checkpoint provider stays an owner choice. All future feature tests NOT_RUN; no numerical computation, schema migration, runtime admission or operational proof from this research.
