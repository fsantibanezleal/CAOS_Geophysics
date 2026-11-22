"""Authenticated 0006 project deletion against real POSIX private files."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from app.config import Settings
from app.server import create_app
from app.physical_posix import PrivateFiles
from fastapi.testclient import TestClient
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


def _upload_dataset(fixture):
    fixture_root, row, client, headers, project, owner, files = fixture
    member_map = {"development": {}, "sealed": {}}
    source_keys = []
    for member in row["members"]:
        parts = member["path"].split("/")
        assert len(parts) == 3 and parts[0] == row["case_id"]
        role, name = parts[1:]
        body = fixture_root.joinpath(*parts).read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        descriptor = None
        if name.endswith(".npy"):
            manifest_name = "request.json" if role == "development" else "sealed.json"
            manifest = json.loads((fixture_root / row["case_id"] / role / manifest_name).read_bytes())
            descriptor = manifest["arrays"][name[:-4]]
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
        response = client.post(
            f"/api/projects/{project}/joint-members",
            content=body,
            headers={**headers, "Content-Type": "application/octet-stream",
                     "X-Joint-Member-Metadata": json.dumps(metadata, separators=(",", ":"))},
        )
        assert response.status_code == 201, response.text
        asset = response.json()
        assert asset["sha256"] == digest and asset["byte_count"] == len(body)
        source_keys.append(f"projects/{owner}/{project}/{asset['asset_id']}")
        member_map[role][name] = asset["asset_id"]

    created = client.post(f"/api/projects/{project}/joint-datasets", json=member_map, headers=headers)
    assert created.status_code == 201, created.text
    receipt = created.json()
    dataset_key = f"derived/{owner}/{project}/datasets/{receipt['dataset_id']}.json"
    return project, owner, source_keys, dataset_key, receipt


def test_authenticated_m11_source_only_delete_commits_exact_cleanup_and_survives_restart(m11_candidate, monkeypatch):
    _, _, client, headers, project, owner, files = m11_candidate
    project, owner, source_keys, dataset_key, dataset = _upload_dataset(m11_candidate)
    assert isinstance(files, PrivateFiles)
    db_path = os.environ["GEOPHYSICS_DB_PATH"]
    with closing(sqlite3.connect(db_path)) as db:
        raw_keys = [row[0] for row in db.execute("SELECT storage_key FROM raw_assets WHERE project_id=?", (project,))]
    assert set(source_keys) <= set(raw_keys)
    originals = {key: files.read(key, cap=256 * 1024**2) for key in raw_keys}
    index_body = files.read(dataset_key, cap=64 * 1024**2)
    assert json.loads(index_body)["scientific_accepted"] is False

    removed = []
    native_remove = files.remove

    def observe_remove(key, *, cap, expected_bytes, expected_sha256, failure_cut=None):
        raw_path = files.root_path / f".deleting/{owner}--{project}"
        derived_path = files.root_path / f".deleting/{owner}--{project}--derived"
        assert raw_path.is_dir() and derived_path.is_dir(), "cleanup began before both project trees were retired"
        assert not (files.root_path / f"projects/{owner}/{project}").exists()
        assert not (files.root_path / f"derived/{owner}/{project}").exists()
        with closing(sqlite3.connect(db_path)) as db:
            receipt = db.execute("SELECT id FROM deletion_receipts WHERE project_id=?", (project,)).fetchone()
            assert receipt is not None, "filesystem cleanup began before the deletion receipt committed"
        removed.append(key)
        return native_remove(key, cap=cap, expected_bytes=expected_bytes,
                             expected_sha256=expected_sha256, failure_cut=failure_cut)

    monkeypatch.setattr(files, "remove", observe_remove)

    response = client.delete(f"/api/projects/{project}", headers=headers)
    assert response.status_code == 200, response.text
    expected_removed = {
        *(f".deleting/{owner}--{project}/{key.rsplit('/', 1)[1]}" for key in raw_keys),
        f".deleting/{owner}--{project}--derived/datasets/{dataset_key.rsplit('/', 1)[1]}",
    }
    assert expected_removed <= set(removed)
    assert response.json()["deleted"] is True
    assert not list((files.root_path / f".deleting/{owner}--{project}").glob("*"))
    assert not [path for path in (files.root_path / f".deleting/{owner}--{project}--derived").rglob("*") if path.is_file()]
    for key in raw_keys + [dataset_key]:
        assert not (files.root_path / key).exists()
    with closing(sqlite3.connect(db_path)) as db:
        assert db.execute("SELECT COUNT(*) FROM projects WHERE id=?", (project,)).fetchone() == (0,)
        receipt_row = db.execute("SELECT asset_manifest,derived_manifest FROM deletion_receipts WHERE id=?",
                                 (response.json()["receipt_id"],)).fetchone()
        assert receipt_row is not None
        asset_manifest, derived_manifest = map(json.loads, receipt_row)
        assert {item["sha256"] for item in asset_manifest} == {
            hashlib.sha256(body).hexdigest() for body in originals.values()
        }
        assert any(item.get("id") == dataset["dataset_id"] for item in derived_manifest)

    # A fresh server assembly repeats the full startup classifier over the
    # retained deletion receipt and removed custody ledger before serving.
    physical = client.app.state.physical_assembly
    settings = Settings(data_dir=files.root_path, db_path=Path(db_path),
        auth_secret="isolated-fixture-secret-more-than-thirty-two-characters",
        public_origin="http://testserver", cookie_secure=False, auth_mode="local")
    with TestClient(create_app(settings, physical=physical)) as restarted:
        assert restarted.get("/api/auth/csrf").status_code == 200


def test_corrupt_uploaded_m11_original_refuses_delete_without_mutation(m11_candidate):
    _, _, client, headers, project, owner, files = m11_candidate
    project, owner, source_keys, dataset_key, _ = _upload_dataset(m11_candidate)
    victim = source_keys[0]
    path = files.root_path / victim
    original = path.read_bytes()
    path.write_bytes(original + b"tamper")
    response = client.delete(f"/api/projects/{project}", headers=headers)
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "raw_integrity_failed"
    assert path.read_bytes() == original + b"tamper"
    assert (files.root_path / dataset_key).is_file()
    with closing(sqlite3.connect(os.environ["GEOPHYSICS_DB_PATH"])) as db:
        assert db.execute("SELECT COUNT(*) FROM projects WHERE id=?", (project,)).fetchone() == (1,)
        assert db.execute("SELECT COUNT(*) FROM deletion_receipts WHERE project_id=?", (project,)).fetchone() == (0,)


def test_m11_job_routes_are_assembled_but_empty_project_has_no_result_rows(m11_candidate):
    """The API contract is mounted; empty projects retain no invented results."""
    _, _, client, _, _, _, _ = m11_candidate
    # Route assembly is exercised end to end by the queue/cancel/result/export
    # API test. Here verify that assembling routes does not invent SQL rows.
    with closing(sqlite3.connect(os.environ["GEOPHYSICS_DB_PATH"])) as db:
        revision = db.execute("SELECT version_num FROM alembic_version").fetchone()
        assert revision == ("0006_joint_artifacts",)
        assert db.execute("SELECT COUNT(*) FROM processing_jobs WHERE method_id='joint.gravity-magnetic-native/v1'").fetchone() == (0,)
        assert db.execute("SELECT COUNT(*) FROM joint_result_artifacts").fetchone() == (0,)
