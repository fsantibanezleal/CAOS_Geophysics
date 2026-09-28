"""Real child-process gravity QC on submitted project observations."""

from __future__ import annotations

import asyncio
import subprocess
import sys

from app.processing_contract import METHOD_ID
from app.worker import run_one
from tests.api.conftest import PROCESSED_GRAVITY_CSV


def test_real_flag_qc_and_parameter_effect(harness):
    harness.account()
    project = harness.project()
    asset, dataset = harness.processed_dataset(project["id"])
    path = f"/api/projects/{project['id']}/jobs"
    first = harness.request("POST", path, json={
        "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID, "parameters": {"threshold": 6},
    })
    assert first.status_code == 202, first.text
    assert asyncio.run(run_one(harness.settings)) == first.json()["job_id"]
    first_status = harness.client.get(f"{path}/{first.json()['job_id']}").json()
    assert first_status["state"] == "succeeded", first_status["error"]
    assert first_status["peak_rss_bytes"] > 0
    assert first_status["wall_ms"] >= 0
    first_result = harness.client.get(first_status["result_url"]).json()
    assert first_result["outlier_flag"] == [False, False, False, False, True]
    assert first_result["statistics"]["median_mgal"] == 3
    assert first_result["statistics"]["mad_mgal"] == 1
    assert first_result["observed_mgal"] == [1, 2, 3, 4, 100]
    assert first_result["sigma_mgal"] == [0.1] * 5
    assert "model" not in first_result and "predicted" not in first_result and "residual" not in first_result

    second = harness.request("POST", path, json={
        "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID, "parameters": {"threshold": 1},
    })
    assert second.status_code == 202, second.text
    assert asyncio.run(run_one(harness.settings)) == second.json()["job_id"]
    second_result = harness.client.get(f"{path}/{second.json()['job_id']}/result").json()
    assert second_result["outlier_flag"] == [True, False, False, False, True]
    assert second_result["observed_mgal"] == first_result["observed_mgal"]
    assert first_result["request_sha256"] != second_result["request_sha256"]
    assert harness.client.get(asset["download_url"]).content == PROCESSED_GRAVITY_CSV


def test_child_launch_has_fixed_command_and_no_secrets(harness, monkeypatch):
    harness.account()
    project = harness.project()
    _asset, dataset = harness.processed_dataset(project["id"])
    created = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID, "parameters": {"threshold": 6},
    })
    assert created.status_code == 202
    original = subprocess.Popen
    observed = []

    def checked_popen(command, **kwargs):
        assert command[:3] == [sys.executable, "-m", "app.compute"]
        assert kwargs["shell"] is False
        assert kwargs["cwd"].is_relative_to(harness.settings.data_dir / ".job-staging")
        assert "GEOPHYSICS_AUTH_SECRET" not in kwargs["env"]
        assert not any(key.startswith("GEOPHYSICS_SMTP") for key in kwargs["env"])
        observed.append(command)
        return original(command, **kwargs)

    monkeypatch.setattr("app.worker.subprocess.Popen", checked_popen)
    assert asyncio.run(run_one(harness.settings)) == created.json()["job_id"]
    assert len(observed) == 1
    assert harness.client.get(f"/api/projects/{project['id']}/jobs/{created.json()['job_id']}").json()["state"] == "succeeded"
