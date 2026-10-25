"""Candidate-only live M11 upload/index/receipt integration.

This test mounts the exact allocated 0006 migration in an isolated SQLite
fixture. It is not production-schema, filesystem-durability, or scientific
acceptance evidence. The input matrix is supplied outside the repository via
GEOPHYSICS_JOINT_MATRIX_FIXTURE.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from alembic import command
from fastapi.testclient import TestClient
from fastapi_users.password import PasswordHelper
import pytest

from app.physical_contract import byte_sha
from app.server import create_app
from tests.api.test_physical_assembly import bound_fixture
from tests.api.test_physical_deleted_inventory import case
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey
from tests.ops.physical_union_fixture import capsule


class CandidateFiles:
    """Portable test transport for the real classifier, not a host guarantee."""

    def __init__(self, root: Path):
        self.root = root
        self.root_path = root.resolve()

    def _path(self, key: str) -> Path:
        if type(key) is not str or not key or "\\" in key or key.startswith("/"):
            raise ValueError("candidate_path")
        path = self.root.joinpath(*key.split("/"))
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise ValueError("candidate_path_escape")
        return path

    def read(self, key, *, cap, expected_bytes=None, expected_sha256=None):
        path = self._path(key)
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(key)
        body = path.read_bytes()
        if (len(body) > cap or expected_bytes is not None and len(body) != expected_bytes
                or expected_sha256 is not None and byte_sha(body) != expected_sha256):
            raise ValueError("candidate_file_identity")
        return body

    def scan_joint_member(self, key, *, byte_count, sha256, descriptor):
        from app.physical_joint_custody import scan_stream
        import io
        return scan_stream(io.BytesIO(self.read(key, cap=byte_count,
            expected_bytes=byte_count, expected_sha256=sha256)), byte_count=byte_count,
            sha256=sha256, descriptor=descriptor)

    def create_directory(self, key, *, exist_ok=False):
        self._path(key).mkdir(mode=0o700, exist_ok=exist_ok)

    def write_new(self, key, body, *, cap):
        if type(body) is not bytes or not 0 < len(body) <= cap:
            raise ValueError("candidate_write_cap")
        path = self._path(key)
        with path.open("xb") as stream:
            stream.write(body)

    def write_new_stream(self, key, stream, *, cap, expected_bytes, expected_sha256):
        stream.seek(0)
        path = self._path(key)
        digest = hashlib.sha256()
        count = 0
        with path.open("xb") as output:
            while block := stream.read(65536):
                count += len(block)
                if count > cap or count > expected_bytes:
                    raise ValueError("candidate_write_cap")
                digest.update(block)
                output.write(block)
        if count != expected_bytes or digest.hexdigest() != expected_sha256:
            raise ValueError("candidate_write_digest")
        return {"bytes": count, "sha256": digest.hexdigest()}

    def remove(self, key, *, cap, expected_bytes, expected_sha256):
        self.read(key, cap=cap, expected_bytes=expected_bytes, expected_sha256=expected_sha256)
        self._path(key).unlink()

    def names(self, key, *, limit):
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(key)
        if path.is_symlink() or not path.is_dir():
            raise ValueError("candidate_directory_identity")
        names = [item.name for item in path.iterdir()]
        if len(names) > limit:
            raise ValueError("candidate_directory_limit")
        return names

    def census(self, expected, *, empty_directories=()):
        actual = {}
        for path in self.root.rglob("*"):
            if path.is_symlink():
                raise ValueError("candidate_link")
            if path.is_file():
                key = path.relative_to(self.root).as_posix()
                if key not in expected:
                    raise ValueError("candidate_unregistered_file")
                body = path.read_bytes()
                record = expected[key]
                digest = hashlib.sha256(body).hexdigest()
                if (len(body) > record["cap"] or record["bytes"] is not None and len(body) != record["bytes"]
                        or record["sha256"] is not None and digest != record["sha256"]):
                    raise ValueError("candidate_census_identity")
                actual[key] = {"bytes": len(body), "sha256": digest}
        if any(record["required"] and key not in actual for key, record in expected.items()):
            raise ValueError("candidate_required_file_missing")
        allowed_dirs = {""}
        for key in (*expected.keys(), *empty_directories):
            parts = key.split("/")
            allowed_dirs.update("/".join(parts[:i]) for i in range(1, len(parts)))
            if key in empty_directories:
                allowed_dirs.add(key)
        for path in self.root.rglob("*"):
            if path.is_dir() and path.relative_to(self.root).as_posix() not in allowed_dirs:
                raise ValueError("candidate_unregistered_directory")
        return actual


@pytest.fixture
def m11_candidate(root_case, monkeypatch):
    fixture_value = os.environ.get("GEOPHYSICS_JOINT_MATRIX_FIXTURE")
    if not fixture_value:
        pytest.skip("set GEOPHYSICS_JOINT_MATRIX_FIXTURE to the external verified matrix")
    fixture_root = Path(fixture_value).resolve(strict=True)
    if not fixture_root.is_dir() or (fixture_root / ".git").exists():
        pytest.fail("GEOPHYSICS_JOINT_MATRIX_FIXTURE must identify an external fixture directory")
    manifest_path = fixture_root / "fixture-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    assert manifest["schema"] == "geophysics.joint-native-input-matrix-fixture/v1"
    row = next(item for item in manifest["cases"] if item["case_id"] == "joint-control-00")
    assert row["inverse_completed"] is False
    assert row["field_eligible"] is False
    assert row["scientific_precision_accepted"] is False

    case(root_case)
    config, _ = capsule(root_case[0].parent / "literal-union")
    monkeypatch.setenv("GEOPHYSICS_DB_PATH", str(root_case[0]))
    monkeypatch.setenv("GEOPHYSICS_CANDIDATE_ROOT", str(root_case[0].parent))
    command.upgrade(config, "0006_joint_artifacts")
    settings, physical = bound_fixture(root_case, monkeypatch)
    # Exercise the production descriptor-relative writer, scanner and complete
    # filesystem census on Linux. The portable assembly fixture normally swaps
    # in path-based adapters, so bind the actual PrivateFiles implementation.
    for directory in (settings.data_dir, *sorted(settings.data_dir.rglob("*"), reverse=True)):
        if directory.is_dir() and not directory.is_symlink():
            os.chmod(directory, 0o700)
        elif directory.is_file() and not directory.is_symlink():
            os.chmod(directory, 0o600)
    from app.physical_posix import PrivateFiles
    files = PrivateFiles(settings.data_dir)
    physical.leases.files = files

    owner = root_case[2]["owner_id"]
    password = "m11 candidate integration fixture password"
    with closing(sqlite3.connect(settings.database_path)) as db:
        db.execute("UPDATE user SET hashed_password=? WHERE id=?", (PasswordHelper().hash(password), owner))
        db.commit()

    try:
        with TestClient(create_app(settings, physical=physical)) as client:
            csrf = client.get("/api/auth/csrf").json()["csrf_token"]
            headers = {"Origin": "http://testserver", "X-CSRF-Token": csrf}
            login = client.post("/api/auth/cookie/login",
                data={"username": owner + "@example.org", "password": password}, headers=headers)
            assert login.status_code == 204, login.text
            yield fixture_root, row, client, headers, root_case[2]["project_id"], owner, files
    finally:
        files.close()


def test_authenticated_0006_member_upload_dataset_create_and_receipt(m11_candidate):
    fixture_root, row, client, headers, project, owner, files = m11_candidate
    member_map = {"development": {}, "sealed": {}}
    for member in row["members"]:
        relative = member["path"]
        parts = relative.split("/")
        assert len(parts) == 3 and parts[0] == row["case_id"] and parts[1] in member_map
        role, name = parts[1], parts[2]
        body_path = fixture_root.joinpath(*parts)
        body = body_path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        assert len(body) == member["byte_count"] and digest == member["sha256"]
        descriptor = None
        if name.endswith(".npy"):
            manifest_name = "request.json" if role == "development" else "sealed.json"
            document = json.loads((fixture_root / row["case_id"] / role / manifest_name).read_bytes())
            descriptor = document["arrays"][name[:-4]]
        metadata = {
            "role": role,
            "name": name,
            "source": {
                "provider": "CAOS authored synthetic control fixture",
                "rights_statement": "Generated synthetic fixture for private research testing",
                "rights_decision": "mirror",
                "private_storage_permission": "attested",
                "attribution": "CAOS Geophysics synthetic control generator",
                "citation": "Synthetic fixture; no external source",
                "expected_bytes": len(body),
                "expected_sha256": digest,
            },
            "descriptor": descriptor,
        }
        uploaded = client.post(
            f"/api/projects/{project}/joint-members",
            content=body,
            headers={**headers, "Content-Type": "application/octet-stream",
                "X-Joint-Member-Metadata": json.dumps(metadata, separators=(",", ":"))},
        )
        assert uploaded.status_code == 201, f"{relative}: {uploaded.status_code} {uploaded.text}"
        asset = uploaded.json()
        assert asset["sha256"] == digest and asset["byte_count"] == len(body)
        assert asset["physical_metadata"]["scientific_accepted"] is False
        assert asset["physical_metadata"]["scientific_values_decoded"] is False
        assert files.read(f"projects/{owner}/{project}/{asset['asset_id']}", cap=len(body),
            expected_bytes=len(body), expected_sha256=digest) == body
        member_map[role][name] = asset["asset_id"]

    created = client.post(f"/api/projects/{project}/joint-datasets", json=member_map, headers=headers)
    assert created.status_code == 201, created.text
    receipt = created.json()
    assert receipt["scientific_accepted"] is False
    assert receipt["qc_verdict"] == "structural_native_members_only"
    development = json.loads(
        (fixture_root / row["case_id"] / "development" / "request.json").read_bytes()
    )
    expected_rows = sum(development["arrays"][f"{modality}_receivers"]["shape"][0]
                        for modality in ("gravity", "magnetic"))
    assert receipt["row_count"] == expected_rows
    readback = client.get(receipt["receipt_url"])
    assert readback.status_code == 200, readback.text
    assert readback.headers["cache-control"] == "no-store"
    assert readback.json() == receipt
    assert readback.json()["scientific_accepted"] is False
    assert readback.json()["qc_verdict"] == "structural_native_members_only"

    duplicate = client.post(f"/api/projects/{project}/joint-datasets", json=member_map, headers=headers)
    assert duplicate.status_code == 409 and duplicate.json()["code"] == "dataset_exists"
    other_project = client.post("/api/projects", json={"name": "M11 custody boundary"}, headers=headers)
    assert other_project.status_code == 201, other_project.text
    other_id = other_project.json()["id"]
    crossed = client.post(f"/api/projects/{other_id}/joint-datasets", json=member_map, headers=headers)
    assert crossed.status_code == 404
    hidden = client.get(f"/api/projects/{other_id}/joint-datasets/{receipt['dataset_id']}")
    assert hidden.status_code == 404
