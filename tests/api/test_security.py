"""Negative CSRF, origin and request admission controls."""

from __future__ import annotations


def test_csrf_origin_and_rate_limits(harness):
    token = harness.client.get("/api/auth/csrf").json()["csrf_token"]
    payload = {"email": "nobody@example.org"}
    assert harness.client.post("/api/auth/reset-password/forgot-password", json=payload, headers={
        "Origin": "http://testserver",
    }).status_code == 403
    assert harness.client.post("/api/auth/reset-password/forgot-password", json=payload, headers={
        "Origin": "https://attacker.example", "X-CSRF-Token": token,
    }).status_code == 403
    assert harness.client.post("/api/auth/reset-password/forgot-password", json=payload, headers={
        "Origin": "http://testserver", "X-CSRF-Token": token, "Sec-Fetch-Site": "cross-site",
    }).status_code == 403
    for _ in range(10):
        response = harness.request("POST", "/api/auth/reset-password/forgot-password", json=payload)
        assert response.status_code == 202, response.text
    limited = harness.request("POST", "/api/auth/reset-password/forgot-password", json=payload)
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0


def test_upload_rate_limit_is_persistent(harness):
    harness.account()
    project = harness.project()
    for _ in range(20):
        result = harness.upload(project["id"])
        assert result.status_code == 201, result.text
    denied = harness.upload(project["id"])
    assert denied.status_code == 429
    assert len(harness.client.get(f"/api/projects/{project['id']}/assets").json()["assets"]) == 20
