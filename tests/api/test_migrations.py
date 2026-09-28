"""Schema and job-boundary checks."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.server import create_app


def test_upgrade_and_schema_guard(harness):
    config = Config("app/alembic.ini")
    command.check(config)
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0002_private_storage_permission"
        db.execute("UPDATE alembic_version SET version_num='stale'")
    async def capture(_a, _b, _c):
        return None
    with pytest.raises(RuntimeError, match="not 0002_private_storage_permission"):
        with TestClient(create_app(harness.settings, capture)):
            pass


def test_no_job_route(harness):
    harness.account()
    paths = set(harness.app.openapi()["paths"])
    assert not any("/jobs" in path for path in paths)
    assert harness.request("POST", "/api/jobs").status_code == 404


def test_migration_respects_private_data_dir(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GEOPHYSICS_DB_PATH", raising=False)
    data_dir = tmp_path / "private"
    monkeypatch.setenv("GEOPHYSICS_DATA_DIR", str(data_dir))
    command.upgrade(Config("app/alembic.ini"), "head")
    assert (data_dir / "api.sqlite3").is_file()


def test_upgrade_does_not_invent_historical_storage_permission(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "historical.sqlite3"
    monkeypatch.setenv("GEOPHYSICS_DB_PATH", str(db_path))
    config = Config("app/alembic.ini")
    command.upgrade(config, "0001_api_foundation")
    user_id, project_id, source_id = (str(uuid4()) for _ in range(3))
    with sqlite3.connect(db_path) as db:
        db.execute(
            "INSERT INTO user (id,email,hashed_password,is_active,is_superuser,is_verified) VALUES (?,?,?,1,0,1)",
            (user_id, "historical@example.org", "historical-hash"),
        )
        db.execute(
            "INSERT INTO projects (id,owner_id,name,description,created_at,updated_at) VALUES (?,?,?,?,?,?)",
            (project_id, user_id, "Historical", "", "2026-09-27 12:00:00", "2026-09-27 12:00:00"),
        )
        db.execute(
            "INSERT INTO source_records (id,project_id,owner_id,original_filename,version,provider,"
            "retrieved_at,rights_statement,rights_decision,declared_format,sha256,attribution) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (source_id, project_id, user_id, "old.csv", 1, "Historical import", "2026-09-27 12:00:00",
             "Older private source statement", "mirror", "gravity_csv", "a" * 64, "Historical team"),
        )
        db.execute(
            "INSERT INTO deletion_receipts (id,project_id,owner_id,deleted_at,asset_hashes,backup_purge_status) "
            "VALUES (?,?,?,?,?,?)",
            (str(uuid4()), str(uuid4()), user_id, "2026-09-27 12:00:00", "[]", "external_pending"),
        )
    command.upgrade(config, "head")
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT private_storage_permission FROM source_records WHERE id=?", (source_id,)).fetchone() == (None,)
        assert db.execute("SELECT asset_manifest FROM deletion_receipts").fetchone() == (None,)
