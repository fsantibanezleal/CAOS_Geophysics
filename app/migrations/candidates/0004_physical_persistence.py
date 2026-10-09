"""Functional local-only candidate; absent from the default Alembic registry.

Revision ID: 0004_physical_persistence
Revises: 0003_processing_jobs
"""

from datetime import datetime, timezone
import hashlib
import json

from alembic import op

from app.physical_persistence import (
    CORRECTION, TRANSFORM, TABLES, DATASET_INDEXES, JOB,
    candidate_dataset_sql, column, column_sql, index_sql,
)


revision = "0004_physical_persistence"
down_revision = "0003_processing_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    context = op.get_context()
    config = context.config
    if config is None or config.attributes.get("physical_candidate_only") is not True or not config.get_main_option("version_locations"):
        raise ValueError("explicit_isolated_candidate_registry_required")
    bind = op.get_bind()
    if bind.dialect.name != "sqlite" or bind.exec_driver_sql("PRAGMA journal_mode").scalar() not in {"delete", "memory"}:
        raise ValueError("candidate_requires_rollback_journal_or_memory")
    if bind.exec_driver_sql("SELECT version_num FROM alembic_version").scalar() != down_revision:
        raise ValueError("candidate_requires_exact_0003")
    if bind.exec_driver_sql("PRAGMA integrity_check").scalar() != "ok" or bind.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
        raise ValueError("inconsistent_legacy_candidate")
    ddl = bind.exec_driver_sql("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name").fetchall()
    if hashlib.sha256(json.dumps([tuple(row) for row in ddl], separators=(",", ":"), ensure_ascii=False).encode()).hexdigest() != "33a96998cd77c595a0d983461f84e1367a813e460b9c13222d07490fd9b86709":
        raise ValueError("unsupported_legacy_ddl")
    total = 0
    for type_, name, _, _ in ddl:
        if type_ == "table":
            # Table names came only from the exact independently pinned DDL.
            total += bind.exec_driver_sql(f'SELECT count(*) FROM "{name}"').scalar()
    if total > 100000:
        raise ValueError("unsupported_legacy_row_count")
    if bind.exec_driver_sql("SELECT count(*) FROM processing_jobs WHERE state NOT IN ('queued','running','succeeded','failed','cancelled') OR method_id NOT IN ('gravity.station-outlier-flags/v1','mt.edi-full-tensor-qc/v1','mt.edi-fixed-thickness-trf/v1')").scalar():
        raise ValueError("unsupported_legacy_job")
    formats = "'gravity_csv','magnetic_csv','traveltime_csv','ert_csv','geotiff','edi','miniseed','stationxml','segy','mth5'"
    if bind.exec_driver_sql("SELECT count(*) FROM raw_assets WHERE detected_format NOT IN (" + formats + ")").scalar() or bind.exec_driver_sql("SELECT count(*) FROM source_records WHERE declared_format NOT IN (" + formats + ")").scalar():
        raise ValueError("unsupported_legacy_format")
    if bind.exec_driver_sql("SELECT count(*) FROM processing_jobs WHERE state IN ('queued','running')").scalar():
        raise ValueError("active_legacy_job")
    roots = bind.exec_driver_sql("SELECT id,raw_asset_id,project_id,owner_id,parser_version,modality,version,created_at FROM observation_datasets").fetchall()
    if len(roots) > 100000:
        raise ValueError("candidate_row_limit")
    families = []
    for id_, raw, project, owner, parser, modality, version, created in roots:
        if version != 1 or (parser, modality) not in {
            ("gravity-station-csv/v1", "gravity_station"), ("edi-strict-envelope/v1", "edi_transfer_function"),
        }:
            raise ValueError("unsupported_legacy_dataset")
        stamp = datetime.fromisoformat(created)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        delta = stamp.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
        micros = delta.days*86400000000 + delta.seconds*1000000 + delta.microseconds
        if not 0 <= micros <= 9007199254740991:
            raise ValueError("unsupported_legacy_dataset_time")
        families.append((id_, raw, project, owner, parser, "published", 2, 1, 0, micros))
    original = bind.exec_driver_sql("SELECT sql FROM sqlite_master WHERE name='observation_datasets' AND type='table'").scalar_one()
    replacement = candidate_dataset_sql(original)
    old_indexes = bind.exec_driver_sql("SELECT sql FROM sqlite_master WHERE tbl_name='observation_datasets' AND type='index' AND sql IS NOT NULL ORDER BY name").scalars().all()
    # FK disable/restore is isolated maintenance only, outside the explicit SQLite transaction.
    with context.autocommit_block():
        bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
        bind.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            for name, table, keys in (
                ("uq_projects_identity", "projects", ("id", "owner_id")),
                ("uq_raw_assets_identity", "raw_assets", ("id", "owner_id", "project_id")),
                ("uq_jobs_identity", "processing_jobs", JOB),
                ("uq_jobs_input_identity", "processing_jobs", ("id", "owner_id", "project_id", "dataset_id", "dataset_sha256")),
                ("uq_deletion_receipt_identity", "deletion_receipts", ("id", "owner_id", "project_id")),
            ):
                bind.exec_driver_sql(index_sql(name, table, keys, True))
            family = TABLES["physical_dataset_families"]
            bind.exec_driver_sql(family.ddl())
            if families:
                bind.exec_driver_sql("INSERT INTO physical_dataset_families VALUES (?,?,?,?,?,?,?,?,?,?)", families)
            bind.exec_driver_sql(replacement)
            bind.exec_driver_sql("INSERT INTO _physical_candidate_datasets SELECT *, 'root',id,NULL,'geophysics.observation-dataset/v1' FROM observation_datasets")
            bind.exec_driver_sql("DROP TABLE observation_datasets")
            bind.exec_driver_sql("ALTER TABLE _physical_candidate_datasets RENAME TO observation_datasets")
            for sql in old_indexes:
                bind.exec_driver_sql(sql)
            for name, keys, unique, where in DATASET_INDEXES:
                bind.exec_driver_sql(index_sql(name, "observation_datasets", keys, unique, where))
            bind.exec_driver_sql("ALTER TABLE processing_jobs ADD COLUMN " + column_sql("processing_jobs", column("physical_cpu_ms", ("I", 0, 9007199254740991), True)))
            fingerprint = column_sql("processing_jobs", column("physical_fingerprint", "H", True))
            fingerprint += f" CONSTRAINT ck_processing_jobs_physical_lane CHECK ((physical_fingerprint IS NULL AND physical_cpu_ms IS NULL) OR (physical_fingerprint IS NOT NULL AND method_id IN ('{CORRECTION}','{TRANSFORM}')))"
            fingerprint += " CONSTRAINT ck_processing_jobs_physical_json CHECK (physical_fingerprint IS NULL OR (typeof(request_json)='text' AND length(CAST(request_json AS BLOB)) BETWEEN 1 AND 36700160 AND typeof(preflight)='text' AND length(CAST(preflight AS BLOB)) BETWEEN 1 AND 65536))"
            bind.exec_driver_sql("ALTER TABLE processing_jobs ADD COLUMN " + fingerprint)
            bind.exec_driver_sql(index_sql("uq_jobs_physical_reuse", "processing_jobs", ("owner_id", "project_id", "dataset_id", "dataset_sha256", "method_id", "physical_fingerprint"), True, "physical_fingerprint IS NOT NULL AND state IN ('queued','running','succeeded')"))
            for table in TABLES.values():
                if table is not family:
                    bind.exec_driver_sql(table.ddl())
                for sql in table.index_ddl():
                    bind.exec_driver_sql(sql)
            if bind.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                raise ValueError("candidate_foreign_key_check_failed")
            bind.exec_driver_sql("COMMIT")
        except BaseException:
            bind.exec_driver_sql("ROLLBACK")
            raise
        finally:
            bind.exec_driver_sql("PRAGMA foreign_keys=ON")
        if bind.exec_driver_sql("PRAGMA foreign_keys").scalar() != 1:
            raise ValueError("candidate_foreign_keys_not_restored")


def downgrade() -> None:
    raise ValueError("candidate_downgrade_forbidden_preserve_later_writes")
