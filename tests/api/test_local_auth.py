"""Real migrated SQLite, library login, plural ownership and secret-safe operators."""

from __future__ import annotations

import asyncio
from functools import partial
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from fastapi_users.password import PasswordHelper
import pytest
from sqlalchemy import select

from app.accounts import AccountProvisionError, provision_account
from app.config import Settings
from app.models import AccessToken, User


ROOT = Path(__file__).resolve().parents[2]
TEST_PASSWORD = "test-only-password-872"


def provision(harness, username="local-owner@example.org", password=TEST_PASSWORD, *, rotate=False):
    return harness.client.portal.call(partial(
        provision_account, harness.app.state.sessions, username, password, rotate_password=rotate,
    ))


def login(harness, username="local-owner@example.org", password=TEST_PASSWORD):
    return harness.request("POST", "/api/auth/cookie/login", data={"username": username, "password": password})


def test_default_environment_needs_no_smtp(tmp_path, monkeypatch, make_harness):
    for key in list(os.environ):
        if key.startswith("GEOPHYSICS_SMTP") or key == "GEOPHYSICS_AUTH_MODE":
            monkeypatch.delenv(key)
    monkeypatch.setenv("GEOPHYSICS_AUTH_SECRET", "test-only-default-environment-secret-1234567890")
    monkeypatch.setenv("GEOPHYSICS_PUBLIC_ORIGIN", "https://test.example.org")
    monkeypatch.setenv("GEOPHYSICS_DATA_DIR", str(tmp_path))
    settings = Settings.from_env()
    assert settings.auth_mode == "local"
    assert settings.smtp_host == settings.smtp_username == settings.smtp_password == settings.smtp_from == ""
    harness = make_harness(auth_mode="local")
    assert harness.client.get("/api/auth/config").json() == {
        "mode": "local", "registration_enabled": False, "mail_flows_enabled": False,
    }
    assert not harness.messages
    monkeypatch.setenv("GEOPHYSICS_AUTH_MODE", "invalid")
    with pytest.raises(ValueError, match="AUTH_MODE"):
        Settings.from_env()


def test_local_routes_and_session_lifecycle(make_harness):
    harness = make_harness(auth_mode="local")
    for path in ("register", "verify/verify", "reset-password/forgot-password", "reset-password/reset-password"):
        assert harness.request("POST", "/api/auth/" + path, json={}).status_code == 404
    provision(harness)
    assert harness.client.get("/api/auth/me").status_code == 401
    response = login(harness)
    assert response.status_code == 204, response.text
    assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=strict" in response.headers["set-cookie"]
    account = harness.client.get("/api/auth/me")
    assert account.status_code == 200
    assert account.json()["is_verified"] is False  # Provisioning is not mailbox verification.
    assert account.json()["is_superuser"] is False
    assert "password" not in account.text and "hash" not in account.text
    assert harness.request("POST", "/api/auth/cookie/logout").status_code == 204
    assert harness.client.get("/api/auth/me").status_code == 401
    assert not harness.messages


def test_operator_provisioning_and_explicit_rotation(make_harness):
    harness = make_harness(auth_mode="local")
    identifier = "operator@local.worl"  # Preserve a syntactically valid identifier, not a guessed domain.
    result = provision(harness, identifier, "test-9ch!")
    assert result["verdict"] == "created" and set(result) == {"verdict", "account_id"}
    with sqlite3.connect(harness.settings.database_path) as connection:
        row = connection.execute('SELECT email, hashed_password, is_active, is_verified FROM "user"').fetchone()
    assert row[0] == identifier and row[2:] == (1, 0)
    assert row[1].startswith("$argon2")
    assert PasswordHelper().verify_and_update("test-9ch!", row[1])[0]
    with pytest.raises(AccountProvisionError, match="already exists"):
        provision(harness, identifier, "would-replace-password")
    assert login(harness, identifier, "test-9ch!").status_code == 204
    with pytest.raises(AccountProvisionError, match="does not exist"):
        provision(harness, "missing@example.org", rotate=True)
    with pytest.raises(AccountProvisionError, match="8 to 1024"):
        provision(harness, "short@example.org", "short")


def test_rotation_revokes_only_owner_sessions(make_harness):
    harness = make_harness(auth_mode="local")
    first = provision(harness, "first@example.org")
    provision(harness, "second@example.org")
    assert login(harness, "first@example.org").status_code == 204
    first_cookie = harness.client.cookies["geophysics_session"]
    first_project = harness.project("First retained survey")
    assert login(harness, "second@example.org").status_code == 204
    second_cookie = harness.client.cookies["geophysics_session"]
    second_project = harness.project("Second retained survey")
    result = provision(harness, "first@example.org", "test-only-new-password-392", rotate=True)
    assert result == {"verdict": "rotated", "account_id": first["account_id"]}
    assert harness.client.get("/api/auth/me", headers={"Cookie": f"geophysics_session={first_cookie}"}).status_code == 401
    assert harness.client.get("/api/auth/me", headers={"Cookie": f"geophysics_session={second_cookie}"}).status_code == 200
    assert harness.client.get(f"/api/projects/{second_project['id']}").status_code == 200
    assert login(harness, "first@example.org").status_code == 400
    assert login(harness, "first@example.org", "test-only-new-password-392").status_code == 204
    assert harness.client.get(f"/api/projects/{first_project['id']}").status_code == 200


def test_plural_accounts_projects_and_anonymous_boundary(make_harness):
    harness = make_harness(auth_mode="local")
    assert harness.client.get("/api/projects").status_code == 401
    assert harness.request("POST", "/api/projects", json={"name": "No guest server writes"}).status_code == 401
    provision(harness, "first@example.org")
    provision(harness, "second@example.org")
    assert login(harness, "first@example.org").status_code == 204
    first_projects = [harness.project("Survey A"), harness.project("Survey B")]
    uploaded = harness.upload(first_projects[0]["id"])
    assert uploaded.status_code == 201
    assert {item["id"] for item in harness.client.get("/api/projects").json()["projects"]} == {
        item["id"] for item in first_projects
    }
    assert harness.request("POST", "/api/auth/cookie/logout").status_code == 204
    first_id = first_projects[0]["id"]
    assert harness.upload(first_id).status_code == 401
    assert harness.request("POST", f"/api/projects/{first_id}/jobs", json={}).status_code == 401
    assert login(harness, "second@example.org").status_code == 204
    second_projects = [harness.project("Survey C"), harness.project("Survey D")]
    for owned in first_projects:
        assert harness.client.get(f"/api/projects/{owned['id']}").status_code == 404
        assert harness.upload(owned["id"]).status_code == 404
        submitted = {"dataset_id": "00000000-0000-0000-0000-000000000001",
                     "method_id": "gravity.station-outlier-flags/v1", "parameters": {"threshold": 3}}
        assert harness.request("POST", f"/api/projects/{owned['id']}/jobs", json=submitted).status_code == 404
    listed = harness.client.get("/api/projects").json()["projects"]
    assert {item["id"] for item in listed} == {item["id"] for item in second_projects}
    assert len(first_projects) == len(second_projects) == 2


def test_inactive_local_account_and_secure_cookie(make_harness):
    harness = make_harness(auth_mode="local")
    result = provision(harness)
    with sqlite3.connect(harness.settings.database_path) as connection:
        connection.execute('UPDATE "user" SET is_active=0 WHERE email=?', ("local-owner@example.org",))
    assert login(harness).status_code == 400
    with pytest.raises(AccountProvisionError, match="inactive"):
        provision(harness, rotate=True)
    assert result["verdict"] == "created"
    configured = Settings(data_dir=harness.settings.data_dir, auth_secret=harness.settings.auth_secret,
                          public_origin="https://test.example.org")
    from app.server import create_app
    from fastapi.testclient import TestClient
    application = create_app(configured)
    with TestClient(application, base_url="https://test.example.org") as client:
        client.portal.call(partial(provision_account, application.state.sessions, "secure@example.org", TEST_PASSWORD))
        csrf = client.get("/api/auth/csrf").json()["csrf_token"]
        response = client.post("/api/auth/cookie/login", data={"username": "secure@example.org", "password": TEST_PASSWORD},
                               headers={"Origin": "https://test.example.org", "X-CSRF-Token": csrf})
        assert response.status_code == 204
        assert "__Host-geophysics_session" in response.headers["set-cookie"]
        assert "Secure" in response.headers["set-cookie"]
        assert "HttpOnly" in response.headers["set-cookie"]
        assert client.get("/api/auth/me").status_code == 200
        assert client.post("/api/projects", json={"name": "CSRF refused"},
                           headers={"Origin": "https://test.example.org"}).status_code == 403


def test_provisioning_cli_redacts_invalid_secret_input(tmp_path, monkeypatch, capsys):
    from scripts.provision_account import main
    secret = "test-only-sentinel-secret-not-a-real-credential"
    path = tmp_path / "invalid-private.json"
    path.write_text(json.dumps({"username": "invalid-identifier", "password": secret}), encoding="utf-8")
    # No database exists: input validation/failure must not create one or echo secrets.
    monkeypatch.setenv("GEOPHYSICS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("GEOPHYSICS_DB_PATH", raising=False)
    assert main(["--credentials", str(path)]) == 2
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err
    assert "invalid-identifier" not in captured.out + captured.err
    assert not (tmp_path / "api.sqlite3").exists()
    for contents in (secret, json.dumps({"username": "x", "password": secret, "other": secret}),
                     '{"username":"x","username":"y","password":"' + secret + '"}'):
        path.write_text(contents, encoding="utf-8")
        assert main(["--credentials", str(path)]) == 2
        captured = capsys.readouterr()
        assert secret not in captured.out + captured.err


def test_cli_real_migrated_database_without_auth_or_smtp(make_harness, tmp_path, monkeypatch):
    harness = make_harness(auth_mode="local")
    from scripts.provision_account import run
    from app.config import WorkerSettings
    result = asyncio.run(run(WorkerSettings(data_dir=harness.settings.data_dir), "cli@example.org", TEST_PASSWORD, False))
    assert result["verdict"] == "created"
    assert login(harness, "cli@example.org").status_code == 204
    async def count():
        async with harness.app.state.sessions() as session:
            return len((await session.scalars(select(User))).all()), len((await session.scalars(select(AccessToken))).all())
    assert harness.client.portal.call(count) == (1, 1)
    completed = subprocess.run([sys.executable, str(ROOT / "scripts" / "provision_account.py"), "--password", TEST_PASSWORD],
                               capture_output=True, text=True, cwd=ROOT)
    assert completed.returncode == 2
    assert TEST_PASSWORD not in completed.stdout + completed.stderr


def test_parallel_create_serializes_without_overwriting(make_harness):
    harness = make_harness(auth_mode="local")
    async def concurrent():
        return await asyncio.gather(
            provision_account(harness.app.state.sessions, "concurrent@example.org", TEST_PASSWORD),
            provision_account(harness.app.state.sessions, "CONCURRENT@example.org", "different-test-password"),
            return_exceptions=True,
        )
    outcomes = harness.client.portal.call(concurrent)
    assert sum(isinstance(item, dict) and item["verdict"] == "created" for item in outcomes) == 1
    assert sum(isinstance(item, AccountProvisionError) for item in outcomes) == 1
    with sqlite3.connect(harness.settings.database_path) as connection:
        assert connection.execute('SELECT COUNT(*) FROM "user"').fetchone()[0] == 1


def test_local_deletion_profile_and_existing_backup_custody(make_harness):
    harness = make_harness(auth_mode="local")
    provision(harness)
    assert login(harness).status_code == 204
    project = harness.project("Local deletion")
    asset = harness.upload(project["id"]).json()
    response = harness.request("DELETE", f"/api/projects/{project['id']}")
    assert response.status_code == 200
    assert response.json()["external_backup_status"] == "not_configured"
    assert response.json()["backup_erasure_status"] == "not_attempted"
    assert harness.client.get(asset["receipt"]).status_code == 404
    assert harness.client.get(f"/api/projects/{project['id']}").status_code == 404
    with sqlite3.connect(harness.settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM deletion_receipts").fetchone()[0] == 1
        assert connection.execute("SELECT raw_bytes FROM account_usage").fetchone()[0] == 0

    protected = harness.project("Recorded custody")
    stored = harness.upload(protected["id"]).json()
    owner = harness.client.get("/api/auth/me").json()["id"]
    backup = harness.settings.data_dir / ".backups" / owner / protected["id"]
    backup.mkdir(parents=True)
    original = backup / "existing-private-copy.bin"
    original.write_bytes(b"existing owned test backup")
    refusal = harness.request("DELETE", f"/api/projects/{protected['id']}")
    assert refusal.status_code == 409 and refusal.json()["code"] == "backup_reconciliation_required"
    assert original.read_bytes() == b"existing owned test backup"
    assert harness.client.get(stored["receipt"]).status_code == 200
    with sqlite3.connect(harness.settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM deletion_receipts").fetchone()[0] == 1
