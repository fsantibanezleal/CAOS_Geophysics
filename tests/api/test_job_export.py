"""Owner-only round-trip bundle, rights and tamper boundaries."""

from __future__ import annotations

import asyncio
import io
import zipfile

import pytest

from app.bundle import verify_bundle
from app.processing_contract import METHOD_ID, canonical_bytes, sha256
from app.worker import run_one
from tests.api.conftest import PROCESSED_GRAVITY_CSV, processed_gravity_metadata


def test_bundle_roundtrip_tamper_and_rights(harness):
    harness.account()
    project = harness.project()
    metadata = processed_gravity_metadata()
    metadata["source"]["rights_decision"] = "provider-link-only"
    metadata["source"]["rights_statement"] = "Private processing permitted; no public raw redistribution"
    _asset, dataset = harness.processed_dataset(project["id"], metadata=metadata)
    created = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID, "parameters": {"threshold": 6},
    })
    assert created.status_code == 202, created.text
    job_id = created.json()["job_id"]
    asyncio.run(run_one(harness.settings))
    response = harness.client.get(f"/api/projects/{project['id']}/jobs/{job_id}/export")
    assert response.status_code == 200
    manifest, dataset_body, result = verify_bundle(response.content)
    assert manifest["rights_decision"] == "provider-link-only"
    assert manifest["raw_bytes_included"] is False
    assert manifest["units"] == {"position": "m", "observation": "mGal", "uncertainty": "mGal"}
    assert dataset_body["observed_mgal"] == result["observed_mgal"]
    assert dataset_body["sigma_mgal"] == result["sigma_mgal"]
    assert PROCESSED_GRAVITY_CSV not in response.content
    assert b"storage_key" not in response.content

    tampered = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(response.content)) as source, zipfile.ZipFile(tampered, "w") as output:
        for name in source.namelist():
            data = source.read(name)
            output.writestr(name, data.replace(b'"flagged_count":1', b'"flagged_count":0') if name == "result.json" else data)
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_bundle(tampered.getvalue())

    # A re-hashed archive is still invalid when result geometry disagrees with its dataset.
    result["station_ids"][0] = "different-station"
    rewritten_result = canonical_bytes(result)
    manifest["members"]["result.json"] = {
        "sha256": sha256(rewritten_result), "bytes": len(rewritten_result),
    }
    mismatched = io.BytesIO()
    with zipfile.ZipFile(mismatched, "w", compression=zipfile.ZIP_STORED) as output:
        output.writestr("manifest.json", canonical_bytes(manifest))
        output.writestr("dataset.json", canonical_bytes(dataset_body))
        output.writestr("result.json", rewritten_result)
    with pytest.raises(ValueError, match="identity, rights or units mismatch"):
        verify_bundle(mismatched.getvalue())

    harness.account(email="foreign-export@example.org")
    assert harness.client.get(f"/api/projects/{project['id']}/jobs/{job_id}/export").status_code == 404


def test_result_read_refuses_tampered_storage(harness):
    harness.account()
    project = harness.project()
    _asset, dataset = harness.processed_dataset(project["id"])
    created = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID, "parameters": {"threshold": 6},
    })
    assert created.status_code == 202
    job_id = created.json()["job_id"]
    asyncio.run(run_one(harness.settings))
    owner = harness.client.get("/api/auth/me").json()["id"]
    path = harness.settings.data_dir / "derived" / owner / project["id"] / "results" / f"{job_id}.json"
    path.write_bytes(path.read_bytes() + b"tampered")
    for suffix in ("result", "export"):
        response = harness.client.get(f"/api/projects/{project['id']}/jobs/{job_id}/{suffix}")
        assert response.status_code == 409 and response.json()["code"] == "derived_integrity_failed"
    assert path.read_bytes().endswith(b"tampered")
