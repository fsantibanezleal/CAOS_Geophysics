"""Immutable storage, admission and recovery gates."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.database import reconcile_private_files
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


def test_reconcile_orphaned_bytes(harness):
    harness.account()
    project = harness.project()
    asset = harness.upload(project["id"]).json()
    stage = harness.settings.data_dir / ".staging" / "crash.part"
    stage.write_bytes(b"uncommitted")
    os.utime(stage, (time.time() - 7200, time.time() - 7200))
    project_path = next((harness.settings.data_dir / "projects").glob("*/*"))
    orphan = project_path / str(uuid.uuid4())
    orphan.write_bytes(b"orphan")
    asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))
    assert not stage.exists() and not orphan.exists()
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


def test_reconcile_interrupted_delete_and_missing_asset(harness):
    harness.account()
    project = harness.project()
    harness.upload(project["id"])
    original = next((harness.settings.data_dir / "projects").glob("*/*"))
    moved = harness.settings.data_dir / ".deleting" / f"{original.parent.name}--{project['id']}"
    moved.parent.mkdir(exist_ok=True)
    original.rename(moved)
    asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))
    assert original.exists() and not moved.exists()
    raw = next(original.iterdir())
    raw.unlink()
    with pytest.raises(RuntimeError, match="stored raw asset is missing"):
        asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))
