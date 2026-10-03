"""Immutable storage, admission and recovery gates."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import make_engine, reconcile_private_files
from app.models import RawAsset
from tests.api.conftest import GRAVITY_CSV, gravity_metadata


def test_raw_immutable_and_receipt(harness):
    harness.account()
    project = harness.project()
    first = harness.upload(project["id"])
    assert first.status_code == 201, first.text
    asset = first.json()
    assert asset["sha256"] == hashlib.sha256(GRAVITY_CSV).hexdigest()
    assert asset["byte_count"] == len(GRAVITY_CSV)
    assert asset["validation_status"] == "raw_metadata_checked"
    assert asset["source"]["rights_decision"] == "mirror"
    assert asset["source"]["version"] == 1
    second = harness.upload(project["id"])
    assert second.status_code == 201, second.text
    assert second.json()["asset_id"] != asset["asset_id"]
    assert second.json()["source"]["source_id"] != asset["source"]["source_id"]
    assert second.json()["source"]["version"] == 2
    download = harness.client.get(asset["download_url"])
    assert download.status_code == 200 and download.content == GRAVITY_CSV
    assert download.headers["X-Content-SHA256"] == asset["sha256"]
    assert len(list((harness.settings.data_dir / "projects").glob("*/*/*"))) == 2


def test_rejected_bytes_and_mime_leave_no_asset(make_harness):
    harness = make_harness(max_upload_bytes=100, account_quota_bytes=200)
    harness.account()
    project = harness.project()
    too_large = harness.upload(project["id"], b"x" * (harness.settings.max_upload_bytes + 1))
    assert too_large.status_code == 413
    empty = harness.upload(project["id"], b"")
    assert empty.status_code == 422
    archive = harness.upload(project["id"], b"PK\x03\x04" + GRAVITY_CSV)
    assert archive.status_code == 415
    wrong_mime = gravity_metadata()
    wrong_mime["mime"] = "image/tiff"
    assert harness.upload(project["id"], metadata=wrong_mime).status_code == 415
    assert harness.client.get(f"/api/projects/{project['id']}/assets").json()["assets"] == []
    assert not list((harness.settings.data_dir / "projects").glob("*/*/*"))


def test_quota_and_parallel_uploads(make_harness):
    harness = make_harness(max_upload_bytes=100, account_quota_bytes=120)
    harness.account()
    project = harness.project()
    body = GRAVITY_CSV + b"S3,20,0,100,9.79\nS4,30,0,100,9.78\n"
    assert 60 < len(body) < 100
    metadata = gravity_metadata(body)

    def send():
        return harness.upload(project["id"], body, metadata).status_code

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _index: send(), range(2)))
    assert sorted(results) == [201, 507]
    assert len(harness.client.get(f"/api/projects/{project['id']}/assets").json()["assets"]) == 1


def test_stream_limit_without_content_length(make_harness):
    harness = make_harness(max_upload_bytes=100, account_quota_bytes=200)
    harness.account()
    project = harness.project()
    body = GRAVITY_CSV + b"x" * 80
    meta = gravity_metadata(body)
    result = harness.request(
        "POST", f"/api/projects/{project['id']}/assets",
        content=iter([body[:40], body[40:]]),
        headers={"Content-Type": "text/csv", "X-Asset-Metadata": json.dumps(meta)},
    )
    assert result.status_code == 413
    assert not list((harness.settings.data_dir / ".staging").iterdir())


def test_startup_preserves_orphaned_bytes(harness):
    harness.account()
    project = harness.project()
    asset = harness.upload(project["id"]).json()
    project_path = next((harness.settings.data_dir / "projects").glob("*/*"))
    orphan = project_path / str(uuid.uuid4())
    orphan.write_bytes(b"orphan")
    with pytest.raises(RuntimeError, match="unreferenced raw bytes"):
        asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))
    assert orphan.read_bytes() == b"orphan"
    assert harness.client.get(f"/api/projects/{project['id']}/assets/{asset['asset_id']}").status_code == 200


def test_raw_tamper_fails_download_and_export(harness):
    harness.account()
    project = harness.project()
    asset = harness.upload(project["id"]).json()
    path = next((harness.settings.data_dir / "projects").glob("*/*/*"))
    path.write_bytes(b"tampered")
    downloaded = harness.client.get(f"/api/projects/{project['id']}/assets/{asset['asset_id']}/download")
    exported = harness.client.get(f"/api/projects/{project['id']}/export")
    assert downloaded.status_code == 409 and downloaded.json()["code"] == "raw_integrity_failed"
    assert exported.status_code == 409 and exported.json()["code"] == "raw_integrity_failed"


def test_startup_preserves_interrupted_delete(harness):
    harness.account()
    project = harness.project()
    harness.upload(project["id"])
    original = next((harness.settings.data_dir / "projects").glob("*/*"))
    raw = next(original.iterdir())
    original_bytes = raw.read_bytes()
    moved = harness.settings.data_dir / ".deleting" / f"{original.parent.name}--{project['id']}"
    moved.parent.mkdir(exist_ok=True)
    original.rename(moved)
    with pytest.raises(RuntimeError, match="preserved .deleting"):
        asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))
    assert not original.exists() and (moved / raw.name).read_bytes() == original_bytes


def test_startup_detects_older_db_restore(harness, tmp_path):
    harness.account()
    project = harness.project()
    first = harness.upload(project["id"]).json()
    snapshot = tmp_path / "older-api.sqlite3"
    with sqlite3.connect(harness.settings.database_path) as live, sqlite3.connect(snapshot) as copy:
        live.backup(copy)
    second = harness.upload(project["id"]).json()
    second_file = next(path for path in (harness.settings.data_dir / "projects").glob("*/*/*") if path.name == second["asset_id"])
    second_bytes = second_file.read_bytes()
    harness.close()
    with sqlite3.connect(snapshot) as copy, sqlite3.connect(harness.settings.database_path) as restored:
        copy.backup(restored)
        assert restored.execute("SELECT COUNT(*) FROM raw_assets").fetchone()[0] == 1
    engine = make_engine(harness.settings)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def audit() -> None:
        try:
            await reconcile_private_files(harness.settings, sessions)
        finally:
            await engine.dispose()

    with pytest.raises(RuntimeError, match="unreferenced raw bytes"):
        asyncio.run(audit())
    assert second_file.read_bytes() == second_bytes
    assert first["asset_id"] != second["asset_id"]


def test_upload_commit_ack_loss_preserves_bytes(harness, monkeypatch):
    harness.account()
    project = harness.project()
    actual_commit = AsyncSession.commit

    async def commit_with_lost_ack(session):
        uploading = any(isinstance(item, RawAsset) for item in session.identity_map.values())
        await actual_commit(session)
        if uploading:
            raise RuntimeError("simulated lost commit acknowledgement")

    monkeypatch.setattr(AsyncSession, "commit", commit_with_lost_ack)
    with pytest.raises(RuntimeError, match="simulated lost commit acknowledgement"):
        harness.upload(project["id"])
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM raw_assets").fetchone()[0] == 1
    raw = next((harness.settings.data_dir / "projects").glob("*/*/*"))
    assert raw.read_bytes() == GRAVITY_CSV
    asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))


def test_startup_rejects_missing_referenced_asset(harness):
    harness.account()
    project = harness.project()
    harness.upload(project["id"])
    raw = next((harness.settings.data_dir / "projects").glob("*/*/*"))
    raw.unlink()
    with pytest.raises(RuntimeError, match="stored raw asset is missing"):
        asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))


@pytest.mark.parametrize("directory", [".staging", ".exports"])
def test_startup_preserves_abandoned_transfer_bytes(harness, directory):
    path = harness.settings.data_dir / directory / "abandoned.bin"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b"unattributed original")
    with pytest.raises(RuntimeError, match="private_recovery_required"):
        asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))
    assert path.read_bytes() == b"unattributed original"
