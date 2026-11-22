"""The protected M04 API boundary exposes only its explicit local candidate recipe."""

from tests.api.test_magnetic_upload import magnetic_original, metadata, options


def test_owner_job_boundary_and_online_closed(make_harness):
    harness = make_harness(magnetic_online_enabled=False)
    harness.account()
    project = harness.project()
    raw = magnetic_original()
    uploaded = harness.upload(project["id"], raw, metadata(raw))
    assert uploaded.status_code == 201, uploaded.text
    created = harness.request(
        "POST",
        f"/api/projects/{project['id']}/datasets",
        json={"asset_id": uploaded.json()["asset_id"], "magnetic_request": options()},
    )
    assert created.status_code == 201, created.text
    dataset_id = created.json()["dataset_id"]
    base = f"/api/projects/{project['id']}/datasets/{dataset_id}"

    response = harness.client.get(f"{base}/methods")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["methods"] == []
    m03, m04 = result["unavailable"]
    assert m03["method_id"] == "magnetic.flightline-qc-grid/v1"
    assert m04["method_id"] == "M04"
    assert m04["eligible"] is False and m04["lane"] == "offline_only"
    assert m04["source_eligible"] is True
    assert m04["local_recipe"]["schema"] == "m04-local-recipe/v1"
    assert m04["local_recipe"]["status"] == "candidate_only"
    assert m04["local_recipe"]["acceptance"] == {
        "method_accepted": False,
        "field_validated": False,
        "online_admitted": False,
    }
    assert "<closed-request-template.json>" in m04["local_recipe"]["commands"][0]
    assert "calibrate" in m04["local_recipe"]["commands"][2]

    denied = harness.request(
        "POST",
        f"/api/projects/{project['id']}/jobs",
        json={"dataset_id": dataset_id, "method_id": "M04", "parameters": {"threshold": 6}},
    )
    assert denied.status_code == 422
    assert denied.json()["code"] == "method_ineligible"
    assert harness.client.get(f"/api/projects/{project['id']}/jobs").json()["jobs"] == []

    harness.account(email="other@example.org")
    other_project = harness.project()
    assert harness.client.get(f"{base}/methods").status_code == 404
    foreign_submit = harness.request(
        "POST",
        f"/api/projects/{other_project['id']}/jobs",
        json={"dataset_id": dataset_id, "method_id": "M04", "parameters": {"threshold": 6}},
    )
    assert foreign_submit.status_code == 404
