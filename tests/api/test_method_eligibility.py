"""Explicit, owner-only method verdicts and no solver claims."""

from __future__ import annotations

from app.processing_contract import METHOD_ID


def test_contract_filtered_methods_and_owner_isolation(harness):
    harness.account()
    project = harness.project()
    asset, dataset = harness.processed_dataset(project["id"])
    assert harness.client.get(f"/api/projects/{project['id']}/datasets/{asset['asset_id']}/methods").status_code == 404
    methods_path = f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}/methods"
    verdict = harness.client.get(methods_path)
    assert verdict.status_code == 200
    assert verdict.json()["methods"] == [{
        "method_id": METHOD_ID, "eligible": True, "lane": "online_processing",
        "scope": "flag-only QC; no correction or inversion",
    }]
    assert len(verdict.json()["unavailable"]) == 13
    assert all(not item["eligible"] and item["reason"] for item in verdict.json()["unavailable"])
    rejected = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": "M02", "parameters": {"threshold": 6},
    })
    assert rejected.status_code == 422 and rejected.json()["code"] == "method_ineligible"
    job = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID, "parameters": {"threshold": 6},
    })
    assert job.status_code == 202, job.text
    harness.account(email="second@example.org")
    own_project = harness.project()
    foreign_submit = harness.request("POST", f"/api/projects/{own_project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID, "parameters": {"threshold": 6},
    })
    assert foreign_submit.status_code == 404
    for path in (methods_path, f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}",
                 f"/api/projects/{project['id']}/jobs/{job.json()['job_id']}",
                 f"/api/projects/{project['id']}/jobs/{job.json()['job_id']}/result"):
        assert harness.client.get(path).status_code == 404


def test_no_solver_or_fake_result_claim(harness):
    harness.account()
    project = harness.project()
    _asset, dataset = harness.processed_dataset(project["id"])
    paths = set(harness.app.openapi()["paths"])
    assert "/api/jobs" not in paths
    assert not any("solver" in path for path in paths)
    verdict = harness.client.get(f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}/methods").json()
    assert all(item["lane"] == "not_activated" for item in verdict["unavailable"])
    assert not any(item["method_id"] == "M01" for item in verdict["methods"])
