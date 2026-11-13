"""Source-bound physical forest successor; explicit isolated registry only."""

from datetime import datetime, timezone

from alembic import op

from app.physical_persistence import (
    CORRECTION, TRANSFORM, TABLES, DATASET_INDEXES, JOB, column, column_sql, index_sql,
)
from app.physical_successor import (
    FORMATS, METHODS, PREDECESSOR_DDL, ddl_sha256, predecessor_payload, successor_dataset_sql,
)

revision = "0005_physical_forest"
down_revision = "0004_waveform_artifacts"
branch_labels = None
depends_on = None


def upgrade():
    context = op.get_context()
    config = context.config
    if (config.attributes.get("m01_successor_candidate_only") is not True
            or not config.get_main_option("version_locations") or not context.impl.transactional_ddl):
        raise ValueError("explicit_transactional_successor_registry_required")
    bind = op.get_bind()
    if bind.dialect.name != "sqlite" or bind.exec_driver_sql("PRAGMA journal_mode").scalar() not in ("delete", "memory"):
        raise ValueError("successor_requires_rollback_journal_or_memory")
    if bind.exec_driver_sql("SELECT version_num FROM alembic_version").scalar() != down_revision:
        raise ValueError("successor_requires_exact_waveform_predecessor")
    if ddl_sha256(bind) != PREDECESSOR_DDL:
        raise ValueError("unsupported_predecessor_ddl")
    if bind.exec_driver_sql("PRAGMA integrity_check").scalar() != "ok" or bind.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
        raise ValueError("inconsistent_predecessor")
    tables = bind.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").scalars().all()
    if sum(bind.exec_driver_sql(f'SELECT count(*) FROM "{name}"').scalar() for name in tables) > 100000:
        raise ValueError("predecessor_row_limit")
    jobs = bind.exec_driver_sql("SELECT method_id,state FROM processing_jobs").fetchall()
    if any(method not in METHODS or state not in ("queued", "running", "succeeded", "failed", "cancelled") for method, state in jobs):
        raise ValueError("unsupported_predecessor_job")
    if any(state in ("queued", "running") for _, state in jobs):
        raise ValueError("active_predecessor_job")
    for table, column_name in (("raw_assets", "detected_format"), ("source_records", "declared_format")):
        if any(value not in FORMATS for value in bind.exec_driver_sql(f'SELECT "{column_name}" FROM "{table}"').scalars()):
            raise ValueError("unsupported_predecessor_format")
    roots = bind.exec_driver_sql("SELECT id,raw_asset_id,project_id,owner_id,parser_version,modality,version,created_at FROM observation_datasets").fetchall()
    families, payloads = [], []
    for id_, raw, project, owner, parser, modality, version, created in roots:
        if type(version) is not int or version != 1:
            raise ValueError("unsupported_predecessor_dataset")
        payload = predecessor_payload(parser, modality)
        stamp = datetime.fromisoformat(created)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        delta = stamp.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
        micros = delta.days*86400000000 + delta.seconds*1000000 + delta.microseconds
        if not 0 <= micros <= 9007199254740991:
            raise ValueError("unsupported_predecessor_time")
        families.append((id_, raw, project, owner, parser, "published", 2, 1, 0, micros))
        payloads.append((payload, id_))
    original = bind.exec_driver_sql("SELECT sql FROM sqlite_master WHERE name='observation_datasets' AND type='table'").scalar_one()
    replacement = successor_dataset_sql(original)
    indexes = bind.exec_driver_sql("SELECT sql FROM sqlite_master WHERE tbl_name='observation_datasets' AND type='index' AND sql IS NOT NULL ORDER BY name").scalars().all()

    def cut(name):
        callback = config.attributes.get("m01_successor_failure_cut")
        if callback is not None:
            callback(name)  # Explicit isolated tests only, never an environment switch.

    for name, table, keys in (
        ("uq_projects_identity", "projects", ("id", "owner_id")),
        ("uq_raw_assets_identity", "raw_assets", ("id", "owner_id", "project_id")),
        ("uq_jobs_identity", "processing_jobs", JOB),
        ("uq_jobs_input_identity", "processing_jobs", ("id", "owner_id", "project_id", "dataset_id", "dataset_sha256")),
        ("uq_deletion_receipt_identity", "deletion_receipts", ("id", "owner_id", "project_id")),
    ):
        bind.exec_driver_sql(index_sql(name, table, keys, True))
    cut("indexes")
    family = TABLES["physical_dataset_families"]
    bind.exec_driver_sql(family.ddl())
    if families:
        bind.exec_driver_sql("INSERT INTO physical_dataset_families VALUES (?,?,?,?,?,?,?,?,?,?)", families)
    cut("families")
    bind.exec_driver_sql(replacement)
    # Choose each registered payload before insert; CHECKs never see a temporary
    # wrong waveform payload. Every original scalar/native text is copied by SQL.
    for payload, id_ in payloads:
        bind.exec_driver_sql("INSERT INTO _physical_candidate_datasets SELECT *, 'root',id,NULL,? FROM observation_datasets WHERE id=?", (payload, id_))
    cut("dataset_copy")
    bind.exec_driver_sql("DROP TABLE observation_datasets")
    bind.exec_driver_sql("ALTER TABLE _physical_candidate_datasets RENAME TO observation_datasets")
    for sql in indexes:
        bind.exec_driver_sql(sql)
    for name, keys, unique, where in DATASET_INDEXES:
        bind.exec_driver_sql(index_sql(name, "observation_datasets", keys, unique, where))
    cut("dataset_rename")
    bind.exec_driver_sql("ALTER TABLE processing_jobs ADD COLUMN " + column_sql("processing_jobs", column("physical_cpu_ms", ("I", 0, 9007199254740991), True)))
    fingerprint = column_sql("processing_jobs", column("physical_fingerprint", "H", True))
    fingerprint += f" CONSTRAINT ck_processing_jobs_physical_lane CHECK ((physical_fingerprint IS NULL AND physical_cpu_ms IS NULL) OR (physical_fingerprint IS NOT NULL AND method_id IN ('{CORRECTION}','{TRANSFORM}')))"
    fingerprint += " CONSTRAINT ck_processing_jobs_physical_json CHECK (physical_fingerprint IS NULL OR (typeof(request_json)='text' AND length(CAST(request_json AS BLOB)) BETWEEN 1 AND 36700160 AND typeof(preflight)='text' AND length(CAST(preflight AS BLOB)) BETWEEN 1 AND 65536))"
    bind.exec_driver_sql("ALTER TABLE processing_jobs ADD COLUMN " + fingerprint)
    bind.exec_driver_sql(index_sql("uq_jobs_physical_reuse", "processing_jobs", ("owner_id", "project_id", "dataset_id", "dataset_sha256", "method_id", "physical_fingerprint"), True, "physical_fingerprint IS NOT NULL AND state IN ('queued','running','succeeded')"))
    cut("job_columns")
    for table in TABLES.values():
        if table is not family:
            bind.exec_driver_sql(table.ddl())
        for sql in table.index_ddl():
            bind.exec_driver_sql(sql)
    cut("tables")
    if bind.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
        raise ValueError("successor_foreign_key_check_failed")
    cut("checked")
    # No COMMIT/autocommit_block: the fixed candidate environment co-commits
    # this DDL/backfill with Alembic's revision update, or rolls all of it back.


def downgrade():
    raise ValueError("successor_downgrade_forbidden_preserve_later_writes")
