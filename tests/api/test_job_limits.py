"""Non-success states, bounded child processes and crash recovery."""

from __future__ import annotations

import asyncio
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psutil

from app import worker
from app.processing_contract import METHOD_ID
from app.worker import run_one
from tests.api.conftest import PROCESSED_GRAVITY_CSV, processed_gravity_metadata


def _submit(harness, project_id: str, dataset_id: str):
    response = harness.request("POST", f"/api/projects/{project_id}/jobs", json={
        "dataset_id": dataset_id, "method_id": METHOD_ID, "parameters": {"threshold": 6},
    })
    assert response.status_code == 202, response.text
    return response.json()["job_id"]


def _status(harness, project_id: str, job_id: str):
    return harness.client.get(f"/api/projects/{project_id}/jobs/{job_id}").json()


def test_cancel_timeout_failure_and_recovery(make_harness, monkeypatch, tmp_path: Path):
    harness = make_harness(worker_wall_seconds=1)
    harness.account()
    project = harness.project()
    _asset, dataset = harness.processed_dataset(project["id"])
    base = f"/api/projects/{project['id']}/jobs"

    queued_id = _submit(harness, project["id"], dataset["dataset_id"])
    cancelled = harness.request("POST", f"{base}/{queued_id}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["state"] == "cancelled"
    assert asyncio.run(run_one(harness.settings)) is None
    assert harness.client.get(f"{base}/{queued_id}/result").json()["code"] == "result_not_ready"

    pid_file = tmp_path / "child.pid"
    script = "import os,sys,time;open(sys.argv[1],'w').write(str(os.getpid()));time.sleep(10)"
    original_command = worker._command
    monkeypatch.setattr("app.worker._command", lambda _job, _input, _output: [sys.executable, "-c", script, str(pid_file)])
    timeout_id = _submit(harness, project["id"], dataset["dataset_id"])
    assert asyncio.run(run_one(harness.settings)) == timeout_id
    assert _status(harness, project["id"], timeout_id)["error"]["code"] == "job_timeout"
    assert _status(harness, project["id"], timeout_id)["state"] == "failed"
    assert pid_file.is_file() and not psutil.pid_exists(int(pid_file.read_text()))

    pid_file.unlink()
    running_id = _submit(harness, project["id"], dataset["dataset_id"])
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: asyncio.run(run_one(harness.settings)))
        deadline = time.monotonic() + 5
        while _status(harness, project["id"], running_id)["state"] != "running":
            assert time.monotonic() < deadline
            time.sleep(0.02)
        requested = harness.request("POST", f"{base}/{running_id}/cancel")
        assert requested.status_code == 200 and requested.json()["cancel_requested"]
        assert future.result(timeout=8) == running_id
    assert _status(harness, project["id"], running_id)["state"] == "cancelled"
    assert _status(harness, project["id"], running_id)["error"]["code"] == "user_cancelled"
    if pid_file.exists():
        assert not psutil.pid_exists(int(pid_file.read_text()))

    monkeypatch.setattr("app.worker._command", original_command)
    normal = make_harness()
    normal.account(email="failure@example.org")
    normal_project = normal.project()
    flat = PROCESSED_GRAVITY_CSV.replace(b",2,0.1", b",1,0.1").replace(b",3,0.1", b",1,0.1")
    flat = flat.replace(b",4,0.1", b",1,0.1").replace(b",100,0.1", b",1,0.1")
    _flat_asset, flat_dataset = normal.processed_dataset(normal_project["id"], flat, processed_gravity_metadata(flat))
    failure_id = _submit(normal, normal_project["id"], flat_dataset["dataset_id"])
    assert asyncio.run(run_one(normal.settings)) == failure_id
    assert _status(normal, normal_project["id"], failure_id)["state"] == "failed"
    assert _status(normal, normal_project["id"], failure_id)["error"]["code"] == "degenerate_mad_scale"

    _asset2, normal_dataset = normal.processed_dataset(normal_project["id"])
    interrupted_id = _submit(normal, normal_project["id"], normal_dataset["dataset_id"])
    with sqlite3.connect(normal.settings.database_path) as db:
        db.execute("UPDATE processing_jobs SET state='running' WHERE id=?", (interrupted_id,))
    assert asyncio.run(run_one(normal.settings)) is None
    assert _status(normal, normal_project["id"], interrupted_id)["state"] == "failed"
    assert _status(normal, normal_project["id"], interrupted_id)["error"]["code"] == "worker_interrupted"


def test_scratch_limit_terminates_child(make_harness, monkeypatch):
    harness = make_harness(worker_scratch_bytes=1024 * 1024)
    harness.account()
    project = harness.project()
    _asset, dataset = harness.processed_dataset(project["id"])
    job_id = _submit(harness, project["id"], dataset["dataset_id"])
    script = "import sys,time;open(sys.argv[1],'wb').write(b'x'*2000000);time.sleep(5)"
    monkeypatch.setattr("app.worker._command", lambda _job, _input, output: [sys.executable, "-c", script, str(output)])
    assert asyncio.run(run_one(harness.settings)) == job_id
    status = _status(harness, project["id"], job_id)
    assert status["state"] == "failed" and status["error"]["code"] == "job_scratch_limit"
    assert status["result_url"] is None


def test_rss_limit_terminates_child(make_harness, monkeypatch):
    harness = make_harness(worker_memory_bytes=80 * 1024 * 1024)
    harness.account()
    project = harness.project()
    _asset, dataset = harness.processed_dataset(project["id"])
    job_id = _submit(harness, project["id"], dataset["dataset_id"])
    script = "import time; excess=bytearray(120000000);time.sleep(5)"
    monkeypatch.setattr("app.worker._command", lambda _job, _input, _output: [sys.executable, "-c", script])
    assert asyncio.run(run_one(harness.settings)) == job_id
    status = _status(harness, project["id"], job_id)
    assert status["state"] == "failed" and status["error"]["code"] == "job_memory_limit"
    assert status["peak_rss_bytes"] > 80 * 1024 * 1024
