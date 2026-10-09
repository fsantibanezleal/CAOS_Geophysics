"""Real migrated SQLite and private file roots for API tests."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.config import Settings
from app.server import create_app


GRAVITY_CSV = b"station,x,y,z,g\nS1,0,0,100,9.81\nS2,10,0,100,9.80\n"
PROCESSED_GRAVITY_CSV = (
    b"station,x,y,z,g,sigma\n"
    b"S1,0,0,100,1,0.1\nS2,10,0,100,2,0.1\nS3,20,0,100,3,0.1\n"
    b"S4,30,0,100,4,0.1\nS5,40,0,100,100,0.1\n"
)


def gravity_metadata(body: bytes = GRAVITY_CSV) -> dict:
    return {
        "filename": "stations.csv", "mime": "text/csv", "format": "gravity_csv",
        "source": {
            "provider": "User upload", "rights_statement": "I have permission to store this original privately.",
            "rights_decision": "mirror", "private_storage_permission": "attested",
            "attribution": "Test survey", "expected_bytes": len(body),
            "expected_sha256": hashlib.sha256(body).hexdigest(),
        },
        "physical": {
            "coordinate_reference": "epsg", "epsg": 32719, "axis_order": "xy",
            "horizontal_datum": "WGS84", "vertical_datum": "survey benchmark",
            "vertical_positive": "up", "horizontal_unit": "m", "vertical_unit": "m",
            "measurement_unit": "mGal", "epoch_utc": "2026-09-27T12:00:00Z", "component_frame": "local vertical down",
            "geometry": {
                "station_id_column": "station", "x_column": "x", "y_column": "y",
                "z_column": "z", "value_column": "g",
            },
        },
    }


def processed_gravity_metadata(body: bytes = PROCESSED_GRAVITY_CSV) -> dict:
    metadata = gravity_metadata(body)
    metadata["physical"]["geometry"]["sigma_column"] = "sigma"
    return metadata


class ApiHarness:
    def __init__(self, client: TestClient, app, settings: Settings, messages: list):
        self.client = client
        self.app = app
        self.settings = settings
        self.messages = messages
        self.csrf = ""
        self.closed = False

    def close(self) -> None:
        if not self.closed:
            self.client.__exit__(None, None, None)
            self.closed = True

    def request(self, method: str, path: str, *, headers: dict | None = None, **kwargs):
        if method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            if not self.csrf:
                self.csrf = self.client.get("/api/auth/csrf").json()["csrf_token"]
            headers = {"Origin": "http://testserver", "X-CSRF-Token": self.csrf, **(headers or {})}
        return self.client.request(method, path, headers=headers, **kwargs)

    def account(self, email: str = "reader@example.org", password: str = "correct horse battery staple") -> dict:
        register = self.request("POST", "/api/auth/register", json={"email": email, "password": password})
        assert register.status_code == 201, register.text
        assert not register.json()["is_verified"]
        token = re.search(r"Verification token: ([^\n]+)", self.messages[-1][2]).group(1)
        verified = self.request("POST", "/api/auth/verify/verify", json={"token": token})
        assert verified.status_code == 200, verified.text
        login = self.request("POST", "/api/auth/cookie/login", data={"username": email, "password": password})
        assert login.status_code == 204, login.text
        return verified.json()

    def project(self, name: str = "My survey") -> dict:
        response = self.request("POST", "/api/projects", json={"name": name, "description": "Raw acquisition"})
        assert response.status_code == 201, response.text
        return response.json()

    def upload(self, project_id: str, body: bytes = GRAVITY_CSV, metadata: dict | None = None):
        meta = metadata if metadata is not None else gravity_metadata(body)
        return self.request(
            "POST", f"/api/projects/{project_id}/assets", content=body,
            headers={"Content-Type": meta["mime"], "X-Asset-Metadata": json.dumps(meta)},
        )

    def processed_dataset(self, project_id: str, body: bytes = PROCESSED_GRAVITY_CSV, metadata: dict | None = None):
        asset = self.upload(project_id, body, metadata or processed_gravity_metadata(body))
        assert asset.status_code == 201, asset.text
        dataset = self.request(
            "POST", f"/api/projects/{project_id}/datasets", json={"asset_id": asset.json()["asset_id"]},
        )
        assert dataset.status_code == 201, dataset.text
        return asset.json(), dataset.json()


@pytest.fixture
def make_harness(tmp_path: Path, monkeypatch):
    clients: list[ApiHarness] = []

    def create(*, max_upload_bytes: int = 200 * 1024 * 1024, account_quota_bytes: int = 1024 * 1024 * 1024,
               worker_memory_bytes: int = 2 * 1024 * 1024 * 1024, worker_scratch_bytes: int = 1024 * 1024 * 1024,
               worker_wall_seconds: int = 600, max_queued_jobs: int = 32,
               mt_online_enabled: bool = False, auth_mode: str = "email",
               profile_online_enabled: bool = False, profile_python: Path | None = None):
        root = tmp_path / f"case-{len(clients)}"
        private = root / "private"
        private.mkdir(parents=True)
        db = private / "api.sqlite3"
        monkeypatch.setenv("GEOPHYSICS_DB_PATH", str(db))
        config = Config(str(Path(__file__).resolve().parents[2] / "app" / "alembic.ini"))
        command.upgrade(config, "head")
        settings = Settings(
            data_dir=private, db_path=db, auth_secret="test-secret-with-at-least-32-characters-123456",
            public_origin="http://testserver", cookie_secure=False,
            max_upload_bytes=max_upload_bytes, account_quota_bytes=account_quota_bytes,
            worker_memory_bytes=worker_memory_bytes, worker_scratch_bytes=worker_scratch_bytes,
            worker_wall_seconds=worker_wall_seconds, max_queued_jobs=max_queued_jobs,
            mt_online_enabled=mt_online_enabled,
            profile_online_enabled=profile_online_enabled, profile_python=profile_python,
            auth_mode=auth_mode,
        )
        messages = []

        async def capture(address: str, subject: str, body: str) -> None:
            messages.append((address, subject, body))

        app = create_app(settings, capture)
        client = TestClient(app)
        client.__enter__()
        harness = ApiHarness(client, app, settings, messages)
        clients.append(harness)
        return harness

    yield create

    for client in reversed(clients):
        client.close()


@pytest.fixture
def harness(make_harness) -> ApiHarness:
    return make_harness()
