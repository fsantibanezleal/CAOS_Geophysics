"""Project ownership is checked on every route."""

from __future__ import annotations


def test_owner_scoped_crud(harness):
    assert harness.client.get("/api/projects").status_code == 401
    harness.account("first@example.org")
    project = harness.project("First")
    project_id = project["id"]
    asset = harness.upload(project_id).json()
    changed = harness.request("PATCH", f"/api/projects/{project_id}", json={"name": "Renamed"})
    assert changed.status_code == 200 and changed.json()["name"] == "Renamed"
    assert [row["id"] for row in harness.client.get("/api/projects").json()["projects"]] == [project_id]
    assert harness.request("POST", "/api/auth/cookie/logout").status_code == 204
    harness.account("second@example.org")
    for method, path in (
        ("GET", f"/api/projects/{project_id}"),
        ("PATCH", f"/api/projects/{project_id}"),
        ("DELETE", f"/api/projects/{project_id}"),
        ("GET", f"/api/projects/{project_id}/assets"),
        ("GET", f"/api/projects/{project_id}/assets/{asset['asset_id']}"),
        ("GET", f"/api/projects/{project_id}/assets/{asset['asset_id']}/download"),
        ("GET", f"/api/projects/{project_id}/export"),
    ):
        kwargs = {"json": {"name": "No"}} if method == "PATCH" else {}
        assert harness.request(method, path, **kwargs).status_code == 404
    assert harness.client.get("/api/projects").json()["projects"] == []
    assert harness.upload(project_id).status_code == 404
