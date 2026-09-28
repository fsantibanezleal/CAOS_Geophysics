"""Owner export and irreversible project deletion."""

from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import zipfile

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
