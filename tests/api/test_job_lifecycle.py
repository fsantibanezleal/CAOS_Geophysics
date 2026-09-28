"""Project deletion and startup recovery with private processed bytes."""

from __future__ import annotations

import asyncio
import json
import sqlite3

import pytest

from app.database import reconcile_private_files
from app.processing_contract import METHOD_ID
from app.worker import run_one


def test_project_deletion_and_orphan_recovery(harness):
    harness.account()
    project = harness.project()
    asset, dataset = harness.processed_dataset(project["id"])
    created = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID, "parameters": {"threshold": 6},
    })
    assert created.status_code == 202
    job_id = created.json()["job_id"]
    blocked = harness.request("DELETE", f"/api/projects/{project['id']}")
    assert blocked.status_code == 409 and blocked.json()["code"] == "project_jobs_active"
    assert harness.client.get(asset["download_url"]).status_code == 200
    asyncio.run(run_one(harness.settings))
    assert harness.client.get(f"/api/projects/{project['id']}/jobs/{job_id}/result").status_code == 200

    deleted = harness.request("DELETE", f"/api/projects/{project['id']}")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["backup_erasure_status"] == "not_attempted"
    assert harness.client.get(f"/api/projects/{project['id']}/jobs/{job_id}").status_code == 404
    assert not list((harness.settings.data_dir / "derived").rglob("*.json"))
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM observation_datasets").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM processing_jobs").fetchone()[0] == 0
        receipt = db.execute("SELECT derived_manifest,backup_purge_status FROM deletion_receipts").fetchone()
        assert {entry["kind"] for entry in json.loads(receipt[0])} == {"dataset", "result"}
        assert receipt[1] == "not_attempted"

    owner = harness.client.get("/api/auth/me").json()["id"]
    orphan = harness.settings.data_dir / "derived" / owner / project["id"] / "results" / "untracked.json"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(b"recoverable older-DB derivative")
    with pytest.raises(RuntimeError, match="unreferenced derivative"):
        asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))
    assert orphan.read_bytes() == b"recoverable older-DB derivative"


def test_delete_refuses_changed_derived_bytes(harness):
    harness.account()
    project = harness.project()
    _asset, dataset = harness.processed_dataset(project["id"])
    owner = harness.client.get("/api/auth/me").json()["id"]
    path = harness.settings.data_dir / "derived" / owner / project["id"] / "datasets" / f"{dataset['dataset_id']}.json"
    path.write_bytes(path.read_bytes() + b"tampered")
    result = harness.request("DELETE", f"/api/projects/{project['id']}")
    assert result.status_code == 409 and result.json()["code"] == "derived_integrity_failed"
    assert path.read_bytes().endswith(b"tampered")
    assert harness.client.get(f"/api/projects/{project['id']}").status_code == 200


def test_delete_refuses_unknown_derived_bytes(harness):
    harness.account()
    project = harness.project()
    _asset, dataset = harness.processed_dataset(project["id"])
    owner = harness.client.get("/api/auth/me").json()["id"]
    unknown = harness.settings.data_dir / "derived" / owner / project["id"] / "datasets" / "untracked.json"
    unknown.write_bytes(b"recoverable processing bytes")
    result = harness.request("DELETE", f"/api/projects/{project['id']}")
    assert result.status_code == 409 and result.json()["code"] == "derived_state_unresolved"
    assert unknown.read_bytes() == b"recoverable processing bytes"
    assert harness.client.get(f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}").status_code == 200
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM deletion_receipts").fetchone()[0] == 0


def test_startup_preserves_interrupted_worker_staging(harness):
    stage = harness.settings.data_dir / ".job-staging" / "interrupted-job"
    stage.mkdir(parents=True)
    partial = stage / "result.json"
    partial.write_bytes(b"unacknowledged worker output")
    with pytest.raises(RuntimeError, match="inspect preserved .job-staging"):
        asyncio.run(reconcile_private_files(harness.settings, harness.app.state.sessions))
    assert partial.read_bytes() == b"unacknowledged worker output"
