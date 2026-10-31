"""The service cutover migration is exact, additive and forward-only."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config

from scripts import migrate_service_schema as migration


ROOT = Path(__file__).resolve().parents[2]


def legacy_database(path: Path, monkeypatch) -> str:
    monkeypatch.setenv("GEOPHYSICS_DB_PATH", str(path))
    config = Config(str(ROOT / "app/alembic.ini"))
    command.upgrade(config, migration.LEGACY)
    user_id = str(uuid4())
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO user (id,email,hashed_password,is_active,is_superuser,is_verified) "
            "VALUES (?,?,?,1,0,1)",
            (user_id, "migration-owner@example.org", "retained-password-hash"),
        )
    return user_id


def test_exact_legacy_migration_adds_tables_and_preserves_existing_account(tmp_path, monkeypatch):
    database = tmp_path / "api.sqlite3"
    owner = legacy_database(database, monkeypatch)
    before = database.read_bytes()

    receipt = migration.migrate(database, ROOT)

    assert receipt["from"] == migration.LEGACY and receipt["to"] == migration.HEAD
    assert receipt["changed"] is True
    assert receipt["database_sha256_before"] != receipt["database_sha256_after"]
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT id,hashed_password FROM user").fetchall() == [
            (owner, "retained-password-hash")]
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (migration.HEAD,)
        assert {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")} >= {
                "waveform_dataset_sources", "waveform_result_artifacts"}
    assert before != database.read_bytes()

    after = migration.database_state_digest(database)
    repeated = migration.migrate(database, ROOT)
    assert repeated["from"] == repeated["to"] == migration.HEAD
    assert repeated["changed"] is False
    assert repeated["database_sha256_before"] == repeated["database_sha256_after"] == after


def test_unsupported_revision_fails_without_changing_database(tmp_path, monkeypatch):
    database = tmp_path / "api.sqlite3"
    legacy_database(database, monkeypatch)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE alembic_version SET version_num='unknown'")
    before = database.read_bytes()
    with pytest.raises(ValueError, match="revision is unsupported"):
        migration.migrate(database, ROOT)
    assert database.read_bytes() == before


def test_migration_preserves_committed_wal_data(tmp_path, monkeypatch):
    database = tmp_path / "api.sqlite3"
    owner = legacy_database(database, monkeypatch)
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute("UPDATE user SET email=? WHERE id=?", ("wal-owner@example.org", owner))
        connection.commit()
        wal = Path(str(database) + "-wal")
        assert wal.is_file() and wal.stat().st_size > 0

        before = migration.database_state_digest(database)
        receipt = migration.migrate(database, ROOT)
        assert receipt["database_sha256_before"] == before
        assert receipt["database_sha256_after"] != before
        assert connection.execute("SELECT email FROM user WHERE id=?", (owner,)).fetchone() == (
            "wal-owner@example.org",)
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (migration.HEAD,)
    finally:
        connection.close()


def test_downgrade_refuses_before_dropping_lineage_tables(tmp_path, monkeypatch):
    database = tmp_path / "api.sqlite3"
    legacy_database(database, monkeypatch)
    migration.migrate(database, ROOT)
    before = migration.database_state_digest(database)
    with pytest.raises(RuntimeError, match="forward-only"):
        command.downgrade(Config(str(ROOT / "app/alembic.ini")), migration.LEGACY)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (migration.HEAD,)
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN "
            "('waveform_dataset_sources','waveform_result_artifacts')").fetchone() == (2,)
    assert migration.database_state_digest(database) == before


def test_lost_completion_receipt_can_be_recovered_read_only(tmp_path, monkeypatch):
    database = tmp_path / "api.sqlite3"
    legacy_database(database, monkeypatch)
    before = migration.database_state_digest(database)
    with pytest.raises(ValueError, match="verification-only recovery"):
        migration.migrate(database, ROOT, verify_only=True)
    assert migration.database_state_digest(database) == before

    migration.migrate(database, ROOT)
    verified = migration.migrate(database, ROOT, verify_only=True)
    attempt = {"schema": "geophysics.service-schema-migration-attempt/v1", "status": "attempted",
               "preflight_revision": migration.LEGACY, "to": migration.HEAD}
    receipt = migration.recovery_observation(attempt, verified)
    assert receipt["observation"] == "forward_head_verified_after_lost_receipt"
    assert receipt["observed_revision"] == migration.HEAD
    assert verified["database_sha256_after"] == migration.database_state_digest(database)


def test_activation_migrates_only_after_writers_stop_and_before_candidate_switch():
    script = (ROOT / "deploy/activate-service.sh").read_text(encoding="utf-8")
    activation = script[script.index("trap rollback ERR"):]
    worker_stop = activation.index("stop_if_present geophysics-worker.service")
    migration_call = activation.index("migrate_service_schema.py")
    release_switch = activation.index('mv -T -- "$root/activate-$release_id" "$root/current"')
    assert worker_stop < migration_call < release_switch
    assert "0003_processing_jobs" in script and "0004_waveform_artifacts" in script
    assert "schema-migration.json" in script
    assert "schema-migration-recovery.json" in script
    rollback = script[script.index("rollback() {"):script.index("trap rollback ERR")]
    assert "if ! recover_migration_observation; then rollback_schema_verified=false; fi" in rollback
    assert '"$rollback_schema_verified" == true' in rollback
    assert "alembic downgrade" not in script
