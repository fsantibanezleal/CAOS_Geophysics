"""Candidate 0006 M11 admission, cancellation, custody publication and export."""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import sqlite3
import sys
import time
import zipfile
from contextlib import closing
from pathlib import Path

import pytest

pytest_plugins = (
    "tests.api.test_m11_candidate_runtime_success",
    "tests.api.test_physical_roots",
    "tests.api.test_physical_successor",
    "tests.api.test_physical_wire",
)

from app.config import Settings
def _upload_dataset(fixture_root, row, client, headers, project):
    member_map = {"development": {}, "sealed": {}}
    for member in row["members"]:
        relative = member["path"]
        _, role, name = relative.split("/")
        body = fixture_root.joinpath(*relative.split("/")).read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        descriptor = None
        if name.endswith(".npy"):
            manifest = "request.json" if role == "development" else "sealed.json"
            document = json.loads((fixture_root / row["case_id"] / role / manifest).read_bytes())
            descriptor = document["arrays"][name[:-4]]
        metadata = {
            "role": role, "name": name, "descriptor": descriptor,
            "source": {"provider": "CAOS authored synthetic control fixture",
                       "rights_statement": "Generated synthetic fixture for private research testing",
                       "rights_decision": "mirror", "private_storage_permission": "attested",
                       "attribution": "CAOS Geophysics synthetic control generator",
                       "citation": "Synthetic fixture; no external source",
                       "expected_bytes": len(body), "expected_sha256": digest},
        }
        response = client.post(f"/api/projects/{project}/joint-members", content=body,
            headers={**headers, "Content-Type": "application/octet-stream",
                     "X-Joint-Member-Metadata": json.dumps(metadata, separators=(",", ":"))})
        assert response.status_code == 201, response.text
        member_map[role][name] = response.json()["asset_id"]
    response = client.post(f"/api/projects/{project}/joint-datasets", json=member_map, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_candidate_m11_queue_cancel_failure_publication_and_export(m11_candidate):
    fixture_root, row, client, headers, project, owner, files = m11_candidate
    dataset = _upload_dataset(fixture_root, row, client, headers, project)
    app = client.app
    physical = app.state.physical_assembly
    settings = Settings(data_dir=Path(files.root_path), db_path=Path(app.state.sessions.kw["bind"].url.database),
        auth_secret="candidate-m11-test-secret-long-enough-for-settings",
        public_origin="http://testserver", cookie_secure=False, account_quota_bytes=1024**3)
    created = client.post(f"/api/projects/{project}/joint-jobs", json={"dataset_id": dataset["dataset_id"]}, headers=headers)
    assert created.status_code == 202, created.text
    queued = created.json()
    assert queued["state"] == "queued" and queued["scientific_acceptance"] is False
    assert queued["method_id"] == "joint.gravity-magnetic-native/v1"

    full = client.post(f"/api/projects/{project}/joint-jobs", json={"dataset_id": dataset["dataset_id"]}, headers=headers)
    assert full.status_code == 429 and full.json()["code"] == "joint_queue_full"
    cancelled = client.post(f"/api/projects/{project}/joint-jobs/{queued['job_id']}/cancel", headers=headers)
    assert cancelled.status_code == 200 and cancelled.json()["state"] == "queued", cancelled.text
    assert cancelled.json()["cancel_requested"] is True

    from app.joint_job_worker import _claim, _failure_member, _publish

    async def publish_cancellation():
        async with physical.leases.acquire():
            async with physical.worker.acquire_processing():
                assert await _claim(settings, app.state.sessions, physical, "m11-test-worker") == queued["job_id"]
                await _publish(settings, app.state.sessions, physical, queued["job_id"], "failed",
                               _failure_member("failed", "ignored_for_cancel"), failure_code="ignored_for_cancel")

    client.portal.call(publish_cancellation)
    cancelled_result = client.get(f"/api/projects/{project}/joint-results/{queued['job_id']}")
    assert cancelled_result.status_code == 200
    assert cancelled_result.json()["state"] == "cancelled"
    assert client.get(f"/api/projects/{project}/joint-results/{queued['job_id']}/export").status_code == 200

    second = client.post(f"/api/projects/{project}/joint-jobs", json={"dataset_id": dataset["dataset_id"]}, headers=headers)
    assert second.status_code == 202, second.text
    job_id = second.json()["job_id"]

    async def publish_measured_failure():
        async with physical.leases.acquire():
            async with physical.worker.acquire_processing():
                claimed = await _claim(settings, app.state.sessions, physical, "m11-test-worker")
                assert claimed == job_id
                failure = _failure_member("failed", "custody_fixture_no_execution")
                await _publish(settings, app.state.sessions, physical, job_id, "failed",
                               failure, failure_code="custody_fixture_no_execution",
                               wall_ms=1, peak_rss=1024, scratch_bytes=1)

    client.portal.call(publish_measured_failure)
    terminal = client.get(f"/api/projects/{project}/joint-jobs/{job_id}")
    assert terminal.status_code == 200 and terminal.json()["state"] == "failed"
    result = client.get(f"/api/projects/{project}/joint-results/{job_id}")
    assert result.status_code == 200, result.text
    assert result.json()["scientific_acceptance"] is False
    assert result.json()["state"] == "failed"
    exported = client.get(f"/api/projects/{project}/joint-results/{job_id}/export")
    assert exported.status_code == 200 and exported.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert set(archive.namelist()) == {"private-custody-index.json", "api-failure.json"}
        assert archive.getinfo("api-failure.json").compress_type == zipfile.ZIP_STORED
        assert json.loads(archive.read("api-failure.json"))["state"] == "failed"
    history = client.get(f"/api/projects/{project}/joint-results")
    assert history.status_code == 200, history.text
    assert history.json()["schema"] == "geophysics.joint-custody-history/v1"
    assert history.json()["jobs"][0]["job_id"] == job_id
    assert history.json()["jobs"][0]["index_available"] is True
    receipt_root = os.environ.get("GEOPHYSICS_JOINT_CUSTODY_API_RECEIPT")
    if receipt_root:
        target = Path(receipt_root).resolve()
        repository = Path(__file__).resolve().parents[2]
        assert not target.is_relative_to(repository) and not any((p / ".git").exists() for p in (target, *target.parents))
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name, body in (("actual-history.json", history.content),
                           ("actual-index.json", result.content),
                           ("actual-export.zip", exported.content)):
            (target / name).write_bytes(body)

    other = client.post("/api/projects", json={"name": "M11 owner boundary"}, headers=headers)
    assert other.status_code == 201
    other_project = other.json()["id"]
    assert client.get(f"/api/projects/{other_project}/joint-jobs/{job_id}").status_code == 404
    assert client.get(f"/api/projects/{other_project}/joint-results/{job_id}").status_code == 404

    index_key = f"derived/{owner}/{project}/results/{job_id}.json"
    member_key = f"derived/{owner}/{project}/joint/{job_id}/api-failure.json"
    index_bytes = files.read(index_key, cap=1024 * 1024)
    member_bytes = files.read(member_key, cap=1024 * 1024)
    deleted = client.delete(f"/api/projects/{project}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert not (files.root_path / index_key).exists()
    assert not (files.root_path / member_key).exists()
    with closing(sqlite3.connect(os.environ["GEOPHYSICS_DB_PATH"])) as db:
        receipt = db.execute("SELECT derived_manifest FROM deletion_receipts WHERE id=?",
                             (deleted.json()["receipt_id"],)).fetchone()
        assert receipt is not None
        manifest = json.loads(receipt[0])
        digests = {item.get("sha256") for item in manifest}
        assert hashlib.sha256(index_bytes).hexdigest() in digests
        assert hashlib.sha256(member_bytes).hexdigest() in digests


def test_candidate_job_request_rejects_unknown_fields():
    from pydantic import ValidationError
    from app.joint_job_routes import JointJobCreate

    with pytest.raises(ValidationError):
        JointJobCreate.model_validate({"dataset_id": "00000000-0000-4000-8000-000000000001",
                                       "operation": "solve", "path": "/tmp/untrusted"})


def test_candidate_worker_does_not_relabel_completed_workflow_as_failed(tmp_path):
    from app.joint_job_worker import _workflow_files

    (tmp_path / "workflow.json").write_text('{"status":"completed"}', encoding="utf-8")
    members = _workflow_files(tmp_path, "failed", None, failure_code="instrument_validation_failed")
    payload = json.loads(members["api-failure.json"])
    assert payload["schema"] == "geophysics.joint-job-failure/v1"
    assert payload["reason"] == "instrument_validation_failed"


@pytest.mark.skipif(sys.platform != "linux", reason="candidate workspace permission contract is Linux-only")
def test_candidate_workspace_reuses_root_without_adopting_interrupted_job(tmp_path, monkeypatch):
    from app.joint_job_worker import _workspace_root

    root = tmp_path / "external"
    root.mkdir(mode=0o700)
    monkeypatch.setenv("GEOPHYSICS_LOCAL_DATA_ROOT", str(root))
    workspace = _workspace_root()
    interrupted = workspace / "interrupted-job"
    interrupted.mkdir(mode=0o700)
    (interrupted / "unreviewed.bin").write_bytes(b"preserve")

    assert _workspace_root() == workspace
    assert (interrupted / "unreviewed.bin").read_bytes() == b"preserve"


def test_candidate_worker_failure_code_keeps_only_stable_tokens():
    from app.joint_job_worker import _failure_code

    assert _failure_code(RuntimeError("m11_pinned_interpreter_invalid")) == "m11_pinned_interpreter_invalid"
    assert _failure_code(RuntimeError("/private/data/input.npy")) == "RuntimeError"


@pytest.mark.skipif(sys.platform != "linux", reason="candidate child process contract is Linux-only")
def test_candidate_worker_terminates_child_at_shared_deadline():
    from app.joint_job_worker import _run_child

    async def scenario():
        with pytest.raises(TimeoutError, match="m11_job_wall_limit"):
            await _run_child(Path(sys.executable), ["-c", "import time; time.sleep(30)"],
                             job_id="deadline-test", sessions=None,
                             deadline=time.monotonic() + 0.2)

    asyncio.run(scenario())


def test_candidate_worker_executes_real_nonrecovering_control_honestly(m11_candidate):
    if os.environ.get("GEOPHYSICS_M11_REAL_WORKER") != "1":
        pytest.skip("set GEOPHYSICS_M11_REAL_WORKER=1 for pinned solver execution")
    if not os.environ.get("GEOPHYSICS_M11_PYTHON") or not os.environ.get("GEOPHYSICS_LOCAL_DATA_ROOT"):
        pytest.fail("real M11 execution requires the pinned interpreter and external data root")

    fixture_root, row, client, headers, project, _, files = m11_candidate
    dataset = _upload_dataset(fixture_root, row, client, headers, project)
    app = client.app
    physical = app.state.physical_assembly
    settings = Settings(data_dir=Path(files.root_path), db_path=Path(app.state.sessions.kw["bind"].url.database),
        auth_secret="candidate-m11-test-secret-long-enough-for-settings",
        public_origin="http://testserver", cookie_secure=False, account_quota_bytes=1024**3)
    queued = client.post(f"/api/projects/{project}/joint-jobs",
                         json={"dataset_id": dataset["dataset_id"]}, headers=headers)
    assert queued.status_code == 202, queued.text

    from app.joint_job_worker import _claim, _execute

    async def execute_real_job():
        async with physical.leases.acquire():
            async with physical.worker.acquire_processing():
                assert await _claim(settings, app.state.sessions, physical, "m11-real-worker-test") == queued.json()["job_id"]
                await _execute(settings, app.state.sessions, physical, queued.json()["job_id"])

    client.portal.call(execute_real_job)
    job_id = queued.json()["job_id"]
    terminal = client.get(f"/api/projects/{project}/joint-jobs/{job_id}")
    assert terminal.status_code == 200, terminal.text
    # Software execution succeeded on this locked synthetic control, while its
    # independent scientific-acceptance verdict remains false.
    assert terminal.json()["state"] == "succeeded", terminal.text
    assert terminal.json()["error_code"] is None
    assert terminal.json()["wall_ms"] > 0
    assert terminal.json()["peak_rss_bytes"] > 0
    assert terminal.json()["scratch_bytes"] >= 0
    result = client.get(f"/api/projects/{project}/joint-results/{job_id}")
    assert result.status_code == 200, result.text
    assert result.json()["state"] == "succeeded"
    assert result.json()["scientific_acceptance"] is False
    exported = client.get(f"/api/projects/{project}/joint-results/{job_id}/export")
    assert exported.status_code == 200, exported.text
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        names = set(archive.namelist())
        assert "private-custody-index.json" in names
        assert "workflow.json" in names
        workflow = json.loads(archive.read("workflow.json"))
        assert workflow["status"] == "completed"
        assert workflow["inverse_completed"] is True
        assert workflow["field_eligible"] is False
        assert workflow["public_activation"] is False
