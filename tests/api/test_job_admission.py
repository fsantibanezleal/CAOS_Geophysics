"""Transactional job admission and immutable request identity."""

from __future__ import annotations

import json
import sqlite3

from app.processing_contract import METHOD_ID, canonical_bytes, sha256


def _submit(harness, project_id: str, dataset_id: str, threshold: float = 6):
    return harness.request("POST", f"/api/projects/{project_id}/jobs", json={
        "dataset_id": dataset_id, "method_id": METHOD_ID, "parameters": {"threshold": threshold},
    })


def test_immutable_request_and_transactional_admission(harness):
    harness.account()
    project = harness.project()
    _asset, dataset = harness.processed_dataset(project["id"])
    first = _submit(harness, project["id"], dataset["dataset_id"])
    assert first.status_code == 202, first.text
    item = first.json()
    assert item["state"] == "queued"
    assert item["dataset_sha256"] == dataset["sha256"]
    assert item["request"]["parameters"] == {"threshold": 6.0}
    assert sha256(canonical_bytes(item["request"])) == item["request_sha256"]
    assert item["preflight"]["memory_limit_bytes"] <= 256 * 1024 * 1024
    assert item["preflight"]["wall_limit_seconds"] <= 30
    second = _submit(harness, project["id"], dataset["dataset_id"], threshold=3)
    assert second.status_code == 409 and second.json()["code"] == "active_job_limit"
    with sqlite3.connect(harness.settings.database_path) as db:
        request, digest = db.execute("SELECT request_json,request_sha256 FROM processing_jobs").fetchone()
        assert sha256(canonical_bytes(json.loads(request))) == digest
        assert db.execute("SELECT COUNT(*) FROM processing_jobs").fetchone()[0] == 1


def test_queue_and_resource_admission_are_bounded(make_harness):
    harness = make_harness(max_queued_jobs=1)
    harness.account()
    project = harness.project()
    _asset, dataset = harness.processed_dataset(project["id"])
    assert _submit(harness, project["id"], dataset["dataset_id"]).status_code == 202
    harness.account(email="queue-second@example.org")
    second_project = harness.project()
    _asset2, second_dataset = harness.processed_dataset(second_project["id"])
    full = _submit(harness, second_project["id"], second_dataset["dataset_id"])
    assert full.status_code == 429 and full.json()["code"] == "job_queue_full"

    small = make_harness(worker_memory_bytes=32 * 1024 * 1024)
    small.account(email="small@example.org")
    small_project = small.project()
    _asset3, small_dataset = small.processed_dataset(small_project["id"])
    rejected = _submit(small, small_project["id"], small_dataset["dataset_id"])
    assert rejected.status_code == 413 and rejected.json()["code"] == "job_resource_ineligible"

    quota = make_harness(max_upload_bytes=1024 * 1024, account_quota_bytes=4 * 1024 * 1024)
    quota.account(email="quota@example.org")
    quota_project = quota.project()
    _asset4, quota_dataset = quota.processed_dataset(quota_project["id"])
    full = _submit(quota, quota_project["id"], quota_dataset["dataset_id"])
    assert full.status_code == 507 and full.json()["code"] == "account_quota_exceeded"
