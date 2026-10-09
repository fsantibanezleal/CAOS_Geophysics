# Candidate migration discovery conflict before implementation

Status: STATIC_PREFLIGHT_SCOPE_CONFLICT, CODE_NOT_STARTED, MAIN_DECISION_REQUIRED. Design and bounded local candidate approval are recorded in [candidate-approval](candidate-approval.md). No migration or test is executed to demonstrate a known destructive/incompatible path; this finding comes from exact existing source and independently checked Alembic documentation.

## Read-only current evidence at447f29

- app/alembic.ini:2 sets script_location=app/migrations; no version_locations isolation is configured.
- tests/api/conftest.py:122-123 loads that config and invokes command.upgrade(config,"head") before creating the current API harness.
- app/database.py:18,41-42 pins MIGRATION_HEAD=0003_processing_jobs and refuses any other revision.
- tests/api/test_migrations.py:21 expects exact0003; line19's command.check(config) also expects the legacy metadata/head relationship. Lines42/73 separately upgrade the same default environment to head.
- app/migrations/versions/0003_processing_jobs.py has revision0003/down0002. The accepted proposed candidate has revision0004_physical_persistence/down0003_processing_jobs, branch_labels/depends_on NULL.
- Read-only installed .venv-api Alembic script/base.py:_version_locations/_load_revisions defaults to the versions directory, enumerates its files and constructs the revision map. No interpreter or database was invoked to inspect this source.

[Official Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html#create-a-migration-script) explains file discovery and down_revision chaining; its running-migration examples resolve head to the newest revision. Actual HTTP receipt: URL https://alembic.sqlalchemy.org/en/latest/tutorial.html,status200,bytes111411,SHA2565bf2e468544d08ac61f9cacabc1e5f9a021a98b1aaf74d97f1ebc0fb7bf38545,retrieved2026-10-03T14:06:51Z. This is a documentation retrieval, NOT installed-runtime proof or dependency upgrade.

## Exact incompatibility and stop

Inference from those sources: adding the authorized normal0004 revision at app/migrations/versions/0004_physical_persistence.py makes it discoverable as the default head. The unchanged API fixture then migrates to0004 while current runtime and its assertions require0003. Even pinning a fixture upgrade to0003 alone is insufficient for the unchanged command.check(config) head/autogeneration contract. Silently editing test config/env/models/MIGRATION_HEAD, conditional revision identifiers, no-op upgrades, fake stamping or weakening the guard would violate the approved scope or dictionary.

The constraint "only this new discovered migration path" conflicts with "old runtime tests/head unchanged" before implementation. No candidate file was written, no existing config/test was edited and no synthetic runtime PASS is claimed. Tests-first must not be used to authorize previously excluded paths.

## Narrow proposed resolution, NOT approved or enacted

Request MAIN to authorize the candidate migration at NEW app/migrations/candidates/0004_physical_persistence.py INSTEAD OF the auto-discovered versions path for this local-only unit. Candidate tests can assemble a NEW disposable version registry containing the unchanged0001..0003 source files and this reviewed0004, then invoke only that isolated rollback-journal/memory candidate. Default app/alembic.ini/versions/MIGRATION_HEAD and all existing API tests/metadata remain untouched; no production discovery/wiring. Revision/down_revision stay exact; no parser suffix or invented source identity. Update the candidate source-policy path explicitly only if MAIN approves, not automatically; the accepted historical policy remains pinned.

Alternative isolation/config/source-path choices require MAIN's explicit reviewed scope amendment. No choice is selected by this packet. All B-DATA/B-SCHEMA code remains unstarted pending this exact conflict; all product/native/CPU/provider/host/browser gates NOT_RUN/CLOSED. No SQL,live DB,probe/install/upgrade,merge or deploy.

Actual docs-only checks PASS after explicit staging: content standards,template residue (830 tracked files),CI budget,cached whitespace. Changed paths are ONLY these two NEW feature docs; read-only diff against447f29 confirms app/tests/scripts/frontend/data/data-pipeline unchanged. No original A/B/PR123/PR133 document or receipt is edited. No executable tests or candidate DDL/source hashes exist yet; those remain NOT_RUN/UNMEASURED rather than invented evidence. Final staged guards run again after this note.
