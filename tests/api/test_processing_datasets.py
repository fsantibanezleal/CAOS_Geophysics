"""Typed gravity station dataset admission and immutable provenance."""

from __future__ import annotations

import hashlib
import sqlite3

import pytest

from app.processing_contract import canonical_bytes
from tests.api.conftest import PROCESSED_GRAVITY_CSV, processed_gravity_metadata


def test_owned_gravity_dataset_is_typed_immutable_and_hashed(harness):
    harness.account()
    project = harness.project()
    asset, dataset = harness.processed_dataset(project["id"])
    path = f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}"
    payload = harness.client.get(path).json()
    assert payload["schema"] == "geophysics.observation-dataset/v1"
    assert payload["dimensions"] == {"station": 5}
    assert payload["axis_order"] == ["station"]
    assert payload["observed_mgal"] == [1, 2, 3, 4, 100]
    assert payload["sigma_mgal"] == [0.1] * 5
    assert payload["mask"] == [False] * 5
    assert payload["correction_history"] == []
    assert payload["parent_raw_sha256"] == hashlib.sha256(PROCESSED_GRAVITY_CSV).hexdigest()
    assert hashlib.sha256(canonical_bytes(payload)).hexdigest() == dataset["sha256"]
    assert harness.client.get(asset["download_url"]).content == PROCESSED_GRAVITY_CSV
    duplicate = harness.request("POST", f"/api/projects/{project['id']}/datasets", json={"asset_id": asset["asset_id"]})
    assert duplicate.status_code == 409 and duplicate.json()["code"] == "dataset_exists"
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM observation_datasets").fetchone()[0] == 1


@pytest.mark.parametrize("body,code", [
    (PROCESSED_GRAVITY_CSV.replace(b"S5,40,0,100,100,0.1", b"S5,40,0,100,nan,0.1"), "dataset_value_invalid"),
    (PROCESSED_GRAVITY_CSV.replace(b"S5,40,0,100,100,0.1", b"S5,40,0,100,100,0"), "dataset_uncertainty_invalid"),
    (PROCESSED_GRAVITY_CSV.replace(b"S5,40,0,100,100,0.1", b"S5,30,0,100,100,0.1"), "dataset_geometry_invalid"),
    (PROCESSED_GRAVITY_CSV.replace(b"S5,40,0,100,100,0.1", b"S4,40,0,100,100,0.1"), "dataset_station_invalid"),
])
def test_dataset_parser_rejects_invalid_rows_and_metadata(harness, body, code):
    harness.account()
    project = harness.project()
    asset = harness.upload(project["id"], body, processed_gravity_metadata(body))
    assert asset.status_code == 201, asset.text
    result = harness.request("POST", f"/api/projects/{project['id']}/datasets", json={"asset_id": asset.json()["asset_id"]})
    assert result.status_code == 422 and result.json()["code"] == code
    assert result.json()["fields"]
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM observation_datasets").fetchone()[0] == 0
    assert not list((harness.settings.data_dir / "derived").rglob("*.json"))


def test_dataset_rejects_missing_sigma_and_non_gravity(harness):
    harness.account()
    project = harness.project()
    asset = harness.upload(project["id"])
    assert asset.status_code == 201
    result = harness.request("POST", f"/api/projects/{project['id']}/datasets", json={"asset_id": asset.json()["asset_id"]})
    assert result.status_code == 422 and result.json()["code"] == "dataset_physics_ineligible"


def test_dataset_requires_storage_attestation(harness):
    harness.account()
    project = harness.project()
    asset = harness.upload(project["id"], PROCESSED_GRAVITY_CSV, processed_gravity_metadata())
    assert asset.status_code == 201
    with sqlite3.connect(harness.settings.database_path) as db:
        db.execute("UPDATE source_records SET private_storage_permission=NULL WHERE id=?", (asset.json()["source"]["source_id"],))
    result = harness.request("POST", f"/api/projects/{project['id']}/datasets", json={"asset_id": asset.json()["asset_id"]})
    assert result.status_code == 422 and result.json()["code"] == "storage_permission_missing"


def test_dataset_limits_precede_parse(harness):
    harness.account()
    project = harness.project()
    rows = b"station,x,y,z,g,sigma\n" + b"".join(
        f"S{index},{index},0,100,{index},0.1\n".encode() for index in range(4097)
    )
    over_rows = harness.upload(project["id"], rows, processed_gravity_metadata(rows))
    assert over_rows.status_code == 201
    result = harness.request("POST", f"/api/projects/{project['id']}/datasets", json={"asset_id": over_rows.json()["asset_id"]})
    assert result.status_code == 413 and result.json()["code"] == "dataset_row_limit"

    oversized = PROCESSED_GRAVITY_CSV + b"x" * (2 * 1024 * 1024)
    over_bytes = harness.upload(project["id"], oversized, processed_gravity_metadata(oversized))
    assert over_bytes.status_code == 201
    result = harness.request("POST", f"/api/projects/{project['id']}/datasets", json={"asset_id": over_bytes.json()["asset_id"]})
    assert result.status_code == 413 and result.json()["code"] == "dataset_too_large"
