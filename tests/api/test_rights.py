"""Private possession and public release rights are different decisions."""

from __future__ import annotations

from tests.api.conftest import gravity_metadata


def test_private_storage_permission_is_not_public_mirror(harness):
    harness.account()
    project = harness.project()
    for decision in ("provider-link-only", "derivative-only"):
        meta = gravity_metadata()
        meta["source"]["rights_decision"] = decision
        response = harness.upload(project["id"], metadata=meta)
        assert response.status_code == 201, response.text
        asset = response.json()
        assert asset["source"]["rights_decision"] == decision
        assert asset["source"]["private_storage_permission"] == "attested"
        assert harness.client.get(asset["download_url"]).status_code == 200

    missing = gravity_metadata()
    del missing["source"]["private_storage_permission"]
    denied = harness.upload(project["id"], metadata=missing)
    assert denied.status_code == 422
    assert "source.private_storage_permission" in denied.json()["fields"]

    forbidden = gravity_metadata()
    forbidden["source"]["rights_decision"] = "forbidden"
    denied = harness.upload(project["id"], metadata=forbidden)
    assert denied.status_code == 422 and denied.json()["code"] == "rights_forbidden"
    assert len(harness.client.get(f"/api/projects/{project['id']}/assets").json()["assets"]) == 2

    assert harness.request("POST", "/api/auth/cookie/logout").status_code == 204
    assert harness.client.get(f"/api/projects/{project['id']}/export").status_code == 401
    harness.account("other-reader@example.org")
    assert harness.client.get(f"/api/projects/{project['id']}/export").status_code == 404
