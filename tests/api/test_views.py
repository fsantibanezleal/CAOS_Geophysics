"""Owner-only response projection and private storage redaction."""

from __future__ import annotations

import asyncio
import io
import json
import sqlite3
import zipfile
from uuid import uuid4

import pytest

from app.database import reconcile_private_files
from tests.api.conftest import GRAVITY_CSV


def test_source_and_asset_view_contract(harness):
    owner = harness.account()
    project = harness.project()
    created = harness.upload(project["id"])
    assert created.status_code == 201, created.text
    asset = created.json()
    assert set(asset) == {
        "schema_version", "asset_id", "owner_id", "project_id", "source_id", "source",
        "original_filename", "mime_type", "detected_format", "byte_count", "sha256",
        "physical_metadata", "validation_status", "created_at", "receipt", "download_url",
    }
    assert asset["schema_version"] == "geophysics.raw-asset-view/v1"
    assert asset["owner_id"] == owner["id"]
    assert asset["project_id"] == project["id"]
    assert asset["source_id"] == asset["source"]["source_id"]
    assert asset["original_filename"] == "stations.csv" and asset["mime_type"] == "text/csv"
    assert asset["validation_status"] == "raw_metadata_checked"
    assert asset["receipt"] == f"/api/projects/{project['id']}/assets/{asset['asset_id']}"
    assert asset["download_url"] == asset["receipt"] + "/download"
    source = asset["source"]
    assert set(source) == {
        "schema_version", "source_id", "version", "provider", "location", "doi", "citation",
        "retrieved_at", "rights_statement", "rights_decision", "private_storage_permission",
        "declared_format", "expected_bytes", "sha256", "attribution",
    }
    assert source["schema_version"] == "geophysics.source-record-view/v1"
    assert source["location"] == {"kind": "upload", "filename": "stations.csv"}
    assert source["citation"] is None  # Never fabricate a bibliographic citation.
    assert source["private_storage_permission"] == "attested"
    assert harness.client.get(asset["receipt"]).json() == asset
    assert harness.client.get(f"/api/projects/{project['id']}/assets").json() == {"assets": [asset]}


def test_private_storage_key_never_serialized(harness):
    harness.account()
    project = harness.project()
    asset = harness.upload(project["id"]).json()
    with sqlite3.connect(harness.settings.database_path) as db:
        private_key = db.execute("SELECT storage_key FROM raw_assets").fetchone()[0]
    responses = [
        asset,
        harness.client.get(asset["receipt"]).json(),
        harness.client.get(f"/api/projects/{project['id']}/assets").json(),
    ]
    exported = harness.client.get(f"/api/projects/{project['id']}/export")
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        responses.append(json.loads(archive.read("manifest.json")))
    for body in responses:
        serialized = json.dumps(body)
        assert "storage_key" not in serialized
        assert private_key not in serialized
        assert str(harness.settings.data_dir) not in serialized
    schema = json.dumps(harness.app.openapi()["components"]["schemas"]["RawAssetView"])
    assert "storage_key" not in schema


def test_private_storage_key_drift_fails_closed(harness):
    harness.account()
    project = harness.project()
    asset = harness.upload(project["id"]).json()
    directory = next((harness.settings.data_dir / "projects").glob("*/*"))
    other = directory / str(uuid4())
    other.write_bytes(GRAVITY_CSV)
    with sqlite3.connect(harness.settings.database_path) as db:
        db.execute("UPDATE raw_assets SET storage_key=? WHERE id=?", (other.relative_to(harness.settings.data_dir).as_posix(), asset["asset_id"]))
    response = harness.client.get(asset["download_url"])
    assert response.status_code == 409 and response.json()["code"] == "raw_integrity_failed"
    with pytest.raises(RuntimeError, match="storage key disagrees"):
        asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))
    assert other.read_bytes() == GRAVITY_CSV
