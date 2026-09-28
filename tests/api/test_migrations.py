"""Schema and job-boundary checks."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.server import create_app


def test_upgrade_and_schema_guard(harness):
    config = Config("app/alembic.ini")
    command.check(config)
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0001_api_foundation"
        db.execute("UPDATE alembic_version SET version_num='stale'")
    async def capture(_a, _b, _c):
        return None
    with pytest.raises(RuntimeError, match="not 0001_api_foundation"):
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
