"""Dataset method eligibility, source fields, ownership, and no solver claims."""

from __future__ import annotations

from app.gravity_l2_contract import METHOD_ID as GRAVITY_L2_ID
from app.processing_contract import METHOD_ID as FLAG_METHOD


def test_contract_filtered_methods(harness):
    harness.account()
    project = harness.project()
    _, dataset = harness.processed_dataset(project["id"])

    response = harness.client.get(
        f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}/methods"
    )
    assert response.status_code == 200, response.text
    verdict = response.json()
    assert verdict["dataset_id"] == dataset["dataset_id"]

    eligible = verdict["methods"]
    unavailable = verdict["unavailable"]
    ids = [row["method_id"] for row in (*eligible, *unavailable)]
    assert len(ids) == len(set(ids))
    assert [row["method_id"] for row in eligible] == [FLAG_METHOD]
    assert all(row["eligible"] is True and row["scope"] for row in eligible)

    by_id = {row["method_id"]: row for row in unavailable}
    assert by_id["M05"]["lane"] == "incompatible_input"
    assert by_id["M05"]["reason_fields"] == ["dataset.modality"]
    assert by_id["M01"]["lane"] == "offline_only"
    assert set(by_id["M01"]["reason_fields"]) == {"method.input_contract", "method.online_lane"}

    l2 = by_id[GRAVITY_L2_ID]
    assert l2["eligible"] is False and l2["lane"] == "ineligible"
    assert l2["source_eligible"] is False
    assert l2["reasons"]
    assert "physical_metadata.geometry.ordinary_l2" in l2["reason_fields"]
    assert all(isinstance(field, str) and field for row in unavailable for field in row["reason_fields"])

    refused = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": "M05", "parameters": {"threshold": 6},
    })
    assert refused.status_code == 422 and refused.json()["code"] == "method_ineligible"
    assert harness.client.get(f"/api/projects/{project['id']}/jobs").json()["jobs"] == []


def test_contract_filtered_methods_and_owner_isolation(harness):
    harness.account()
    project = harness.project()
    asset, dataset = harness.processed_dataset(project["id"])
    assert harness.client.get(f"/api/projects/{project['id']}/datasets/{asset['asset_id']}/methods").status_code == 404
    methods_path = f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}/methods"
    verdict = harness.client.get(methods_path)
    assert verdict.status_code == 200
    assert verdict.json()["methods"] == [{
        "method_id": FLAG_METHOD, "eligible": True, "lane": "online_processing",
        "scope": "flag-only QC; no correction or inversion",
    }]
    assert len(verdict.json()["unavailable"]) == 13
    assert all(not item["eligible"] and item["reason"] and item["reason_fields"]
               for item in verdict.json()["unavailable"])
    rejected = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": "M02", "parameters": {"threshold": 6},
    })
    assert rejected.status_code == 422 and rejected.json()["code"] == "method_ineligible"
    job = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": FLAG_METHOD, "parameters": {"threshold": 6},
    })
    assert job.status_code == 202, job.text
    harness.account(email="second@example.org")
    own_project = harness.project()
    foreign_submit = harness.request("POST", f"/api/projects/{own_project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": FLAG_METHOD, "parameters": {"threshold": 6},
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
    assert all(not item["eligible"] and item["reason"] and item["reason_fields"]
               for item in verdict["unavailable"])
    assert not any(item["method_id"] == "M01" for item in verdict["methods"])
