# Service schema migration: `0003` to `0004`

Status: reviewed implementation; host qualification and release activation remain separate gates.

## Scope

The existing private service database is at Alembic revision `0003_processing_jobs`. The replacement API requires `0004_waveform_artifacts` for explicit raw-source lineage and immutable result artifact registrations. Migration `app/migrations/versions/0004_waveform_artifacts.py` creates exactly:

- `waveform_dataset_sources`, keyed by dataset and source role, with foreign keys to the existing dataset, raw asset and source records.
- `waveform_result_artifacts`, keyed by job and artifact name, with unique storage keys and byte count/SHA-256 metadata.

The migration does not rewrite or delete existing tables, rows or private files. Its source SHA-256 is pinned in `scripts/migrate_service_schema.py`. DDL fingerprints distinguish the exact accepted `0003` and `0004` schemas; unknown revisions or same-revision schema drift refuse before migration.

## Execution and rollback

The activation preflight is read-only. It checks database integrity, foreign keys and exact DDL before stopping production writers. Once the API socket/API and worker are stopped and the queue is empty, activation runs the fixed migration helper as the unprivileged `geophysics` account against `/var/lib/geophysics/api.sqlite3`. The helper rechecks the source migration hash, applies only the `0003` to `0004` upgrade, and verifies the resulting schema and database integrity. It emits a bounded JSON receipt with revision, migration hash, before/after schema fingerprints and quiescent SQLite main/WAL/SHM digests. The root activation controller stores that receipt under its exact release state directory before switching `current`.

The migration is forward-only. A failed later service startup restores the previous release, environment and Nginx configuration while retaining the migration receipt. If the receipt was not persisted, rollback attempts a strictly read-only schema check and records a recovery observation bound to the durable attempt marker. The previous services restart only after the database schema is verified; otherwise they remain stopped while the static rollback stays selected. No downgrade, database replacement or user-data deletion is attempted. The existing current-plus-two-rollback retention policy remains unchanged. A receipt does not itself establish successful activation, actual-host admission, external HTTPS/browser acceptance or full product release acceptance.

## Verification

`tests/ops/test_service_schema_migration.py` applies the actual Alembic chain to a temporary database at revision `0003`, migrates it through the production helper, verifies the account hash is preserved and the two tables exist, then checks idempotent verification at `0004`. WAL-backed committed data are exercised, downgrade refusal is checked before either table can be dropped, lost-receipt recovery is read-only, and unknown revisions are refused without changing bytes. The activation test checks writer-stop, migration, receipt, schema-verification and rollback-service ordering; the shell activation script remains a host-only operation and is never invoked locally.
