"""Owner export and irreversible project deletion."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import sqlite3
import zipfile

import pytest

from app.database import reconcile_private_files
from tests.api.conftest import GRAVITY_CSV


def test_export_manifest_and_owned_bytes(harness):
    harness.account()
    project = harness.project()
    asset = harness.upload(project["id"]).json()
    response = harness.client.get(f"/api/projects/{project['id']}/export")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["schema_version"] == 1
        assert manifest["project"]["id"] == project["id"]
        entry = manifest["raw_assets"][0]
        assert entry["source"]["source_id"] == asset["source"]["source_id"]
        assert entry["physical_metadata"]["measurement_unit"] == "mGal"
        raw = archive.read(entry["zip_member"])
        assert raw == GRAVITY_CSV
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    assert not list((harness.settings.data_dir / ".exports").glob("*.zip"))


def test_delete_erases_project_and_bytes(harness):
    harness.account()
    project = harness.project()
    asset = harness.upload(project["id"]).json()
    backup = harness.settings.data_dir / ".backups" / harness.client.get("/api/auth/me").json()["id"] / project["id"]
    backup.mkdir(parents=True)
    (backup / "snapshot.bin").write_bytes(b"test backup")
    response = harness.request("DELETE", f"/api/projects/{project['id']}")
    assert response.status_code == 200, response.text
    assert response.json()["external_backup_status"] == "pending_reconciliation"
    assert not backup.exists()
    assert not list((harness.settings.data_dir / "projects").glob("*/*/*"))
    assert harness.client.get(f"/api/projects/{project['id']}").status_code == 404
    assert harness.client.get(f"/api/projects/{project['id']}/assets/{asset['asset_id']}/download").status_code == 404
    assert harness.client.get(f"/api/projects/{project['id']}/export").status_code == 404
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM raw_assets").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM source_records").fetchone()[0] == 0
        assert db.execute("SELECT raw_bytes FROM account_usage").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM deletion_receipts").fetchone()[0] == 1
        manifest = json.loads(db.execute("SELECT asset_manifest FROM deletion_receipts").fetchone()[0])
        assert manifest == [{"asset_id": asset["asset_id"], "sha256": asset["sha256"], "byte_count": len(GRAVITY_CSV)}]


def test_delete_refuses_unknown_project_bytes(harness):
    harness.account()
    project = harness.project()
    asset = harness.upload(project["id"]).json()
    directory = next((harness.settings.data_dir / "projects").glob("*/*"))
    unknown = directory / "unreferenced-original"
    unknown.write_bytes(b"recoverable user bytes")
    result = harness.request("DELETE", f"/api/projects/{project['id']}")
    assert result.status_code == 409 and result.json()["code"] == "raw_state_unresolved"
    assert unknown.read_bytes() == b"recoverable user bytes"
    assert harness.client.get(asset["receipt"]).status_code == 200
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM deletion_receipts").fetchone()[0] == 0


def test_startup_preserves_deleted_project_backup(harness):
    harness.account()
    project = harness.project()
    harness.upload(project["id"])
    assert harness.request("DELETE", f"/api/projects/{project['id']}").status_code == 200
    owner = harness.client.get("/api/auth/me").json()["id"]
    backup = harness.settings.data_dir / ".backups" / owner / project["id"]
    backup.mkdir(parents=True)
    (backup / "snapshot.bin").write_bytes(b"restored backup")
    with pytest.raises(RuntimeError, match="deleted-project backup remains"):
        asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))
    assert (backup / "snapshot.bin").read_bytes() == b"restored backup"


def test_startup_preserves_postcommit_deletion_recovery(harness, monkeypatch):
    harness.account()
    project = harness.project()
    asset = harness.upload(project["id"]).json()
    owner = harness.client.get("/api/auth/me").json()["id"]

    def interrupted(_directory, _assets):
        raise RuntimeError("simulated crash after receipt commit")

    monkeypatch.setattr("app.projects._purge_exact_deletion_directory", interrupted)
    with pytest.raises(RuntimeError, match="simulated crash after receipt commit"):
        harness.request("DELETE", f"/api/projects/{project['id']}")
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM projects WHERE id=?", (project["id"],)).fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM deletion_receipts WHERE project_id=?", (project["id"],)).fetchone()[0] == 1
    preserved = harness.settings.data_dir / ".deleting" / f"{owner}--{project['id']}" / asset["asset_id"]
    assert preserved.read_bytes() == GRAVITY_CSV
    with pytest.raises(RuntimeError, match="preserved .deleting"):
        asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))
    assert preserved.read_bytes() == GRAVITY_CSV
