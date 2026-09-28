"""Library account flows and revocable session behavior."""

from __future__ import annotations

import re


def test_register_verify_reset_login_logout(harness):
    create = harness.request("POST", "/api/auth/register", json={
        "email": "owner@example.org", "password": "correct horse battery staple",
        "is_superuser": True, "is_verified": True,
    })
    assert create.status_code == 201, create.text
    assert create.json()["is_superuser"] is False
    assert create.json()["is_verified"] is False
    assert harness.request("POST", "/api/auth/cookie/login", data={
        "username": "owner@example.org", "password": "correct horse battery staple",
    }).status_code == 400
    assert harness.client.get("/api/auth/me").status_code == 401

    verification = re.search(r"Verification token: ([^\n]+)", harness.messages[-1][2]).group(1)
    assert harness.request("POST", "/api/auth/verify/verify", json={"token": verification}).status_code == 200
    login = harness.request("POST", "/api/auth/cookie/login", data={
        "username": "owner@example.org", "password": "correct horse battery staple",
    })
    assert login.status_code == 204, login.text
    assert "HttpOnly" in login.headers["set-cookie"]
    assert "SameSite=strict" in login.headers["set-cookie"]
    assert harness.client.get("/api/auth/me").json()["email"] == "owner@example.org"
    assert harness.request("POST", "/api/auth/cookie/logout").status_code == 204
    assert harness.client.get("/api/auth/me").status_code == 401
    assert harness.request("POST", "/api/auth/cookie/login", data={
        "username": "owner@example.org", "password": "correct horse battery staple",
    }).status_code == 204

    forgotten = harness.request("POST", "/api/auth/reset-password/forgot-password", json={"email": "owner@example.org"})
    assert forgotten.status_code == 202, forgotten.text
    reset_token = re.search(r"Password reset token: ([^\n]+)", harness.messages[-1][2]).group(1)
    reset = harness.request("POST", "/api/auth/reset-password/reset-password", json={
        "token": reset_token, "password": "a different long secure password",
    })
    assert reset.status_code == 200, reset.text
    assert harness.client.get("/api/auth/me").status_code == 401
    old = harness.request("POST", "/api/auth/cookie/login", data={
        "username": "owner@example.org", "password": "correct horse battery staple",
    })
    assert old.status_code == 400
    new = harness.request("POST", "/api/auth/cookie/login", data={
        "username": "owner@example.org", "password": "a different long secure password",
    })
    assert new.status_code == 204
    assert harness.client.get("/api/auth/me").status_code == 200
