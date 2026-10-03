"""Submitted EDI bytes through the authenticated singleton worker, including negative gates."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import sqlite3
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import psutil
import pytest

from app import worker
from app.bundle import verify_bundle
from app.config import WorkerSettings
from app.mt_compute import compute_mt, verified_source_snapshot
from app.mt_contract import M05_ID, M06_ID
from app.processing_contract import canonical_bytes, sha256
from app.worker import run_one


ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / "data/fixtures/edi/halfspace-100-native.edi"
LAYERED = ROOT / "data/fixtures/edi/two-layer-noisy-rotated.edi"
CLEAR_LAKE = ROOT / "data/downloads/clear-lake/USGS-GMEG.2022.cl061.edi"


def edi_metadata(body: bytes, *, station: str, count: int, rotation: float = 0,
                 tipper: bool = False, provider: str = "Original synthetic control") -> dict:
    return {
        "filename": "submitted.edi", "mime": "text/plain", "format": "edi",
        "source": {
            "provider": provider, "rights_statement": "I have permission to store this original privately.",
            "rights_decision": "provider-link-only", "private_storage_permission": "attested",
            "attribution": provider, "expected_bytes": len(body),
            "expected_sha256": hashlib.sha256(body).hexdigest(),
        },
        "physical": {
            "coordinate_reference": "local", "local_crs": "source EDI station coordinates",
            "axis_order": "xy", "horizontal_datum": "source EDI frame",
            "vertical_datum": "source EDI elevation", "vertical_positive": "up",
            "horizontal_unit": "m", "vertical_unit": "m",
            "measurement_unit": "mV/km/nT", "epoch_utc": "2026-09-28T00:00:00Z",
            "component_frame": "instrument axes",
            "geometry": {
                "station_id": station, "frequency_count": count,
                "tensor_components": ["Zxx", "Zxy", "Zyx", "Zyy"]
                + (["Tx", "Ty"] if tipper else []),
                "rotation_degrees": rotation, "rotation_reference": "unspecified",
                "sign_convention": "+", "variance_convention": "complex",
            },
        },
    }


def upload_dataset(harness, source: Path, *, station: str, count: int,
                   rotation: float = 0, tipper: bool = False, provider: str = "Original synthetic control"):
    project = harness.project()
    body = source.read_bytes()
    metadata = edi_metadata(body, station=station, count=count, rotation=rotation,
                            tipper=tipper, provider=provider)
    asset = harness.upload(project["id"], body, metadata)
    assert asset.status_code == 201, asset.text
    created = harness.request("POST", f"/api/projects/{project['id']}/datasets",
                              json={"asset_id": asset.json()["asset_id"]})
    assert created.status_code == 201, created.text
    return project, asset.json(), created.json(), body


def submit(harness, project, dataset, method, parameters):
    response = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": method, "parameters": parameters,
    })
    assert response.status_code == 202, response.text
    return response.json()


def complete(harness, job):
    assert asyncio.run(run_one(harness.settings)) == job["job_id"]
    status = harness.client.get(f"/api/projects/{job['project_id']}/jobs/{job['job_id']}").json()
    assert status["state"] == "succeeded", status["error"]
    return harness.client.get(status["result_url"]).json(), status


def test_source_identity_and_m05_screen(make_harness):
    harness = make_harness(mt_online_enabled=True)
    harness.account()
    project, asset, dataset, body = upload_dataset(
        harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    assert harness.client.get(asset["download_url"]).content == body
    assert dataset["qc_verdict"] == "awaiting_full_tensor_qc"
    before = harness.client.get(f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}/methods").json()
    assert before["methods"][0]["method_id"] == M05_ID
    assert before["unavailable"][0]["method_id"] == M06_ID
    result, status = complete(harness, submit(harness, project, dataset, M05_ID, {}))
    assert result["raw_sha256"] == hashlib.sha256(body).hexdigest()
    assert result["raw_bytes"] == len(body)
    assert result["environment"]["packages"]["mt-metadata"] == "1.0.10"
    assert result["environment_sha256"] == sha256(canonical_bytes(result["environment"]))
    assert result["screen"]["one_d_inversion_eligible"] is True
    assert result["screen"]["methods"] == {} and result["inverse"] is None
    assert len(result["screen"]["tensor"]["real"]) == 24
    assert result["screen"]["provenance"]["variance_convention"] == "complex"
    assert result["screen"]["provenance"]["original_sign_convention"] == "+"
    assert result["screen"]["provenance"]["source_file"] == "source.edi"
    assert status["preflight"]["estimated_scratch_bytes"] >= len(body) + 2 * 1024 * 1024
    assert status["peak_rss_bytes"] > 0 and status["scratch_bytes"] > 0
    after = harness.client.get(f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}/methods").json()
    assert after["methods"][1]["method_id"] == M06_ID
    assert after["methods"][1]["qc_job_id"] == status["job_id"]
    invalid = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": M06_ID,
        "parameters": {"qc_job_id": status["job_id"], "thickness_m": [],
                       "initial_ohm_m": [100], "beta": .001, "bootstrap_samples": True},
    })
    assert invalid.status_code == 422


def test_inverse_parameter_effect_and_independent_oracle(make_harness):
    harness = make_harness(mt_online_enabled=True)
    harness.account()
    project, _asset, dataset, _ = upload_dataset(harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    _screen, qc = complete(harness, submit(harness, project, dataset, M05_ID, {}))
    params = {"qc_job_id": qc["job_id"], "thickness_m": [], "initial_ohm_m": [40],
              "beta": 0.001, "bootstrap_samples": 20, "seed": 71401}
    inverse, status = complete(harness, submit(harness, project, dataset, M06_ID, params))
    method = inverse["inverse"]["methods"]["mt-lm"]
    assert method["model"][0] == pytest.approx(100, rel=1e-7)
    frequencies = np.asarray(inverse["frequency_hz"])
    observed = (np.asarray(inverse["screen"]["observed"]["xy"]["real"])
                + 1j * np.asarray(inverse["screen"]["observed"]["xy"]["imag"]))
    analytic = (1 + 1j) * np.sqrt(np.pi * frequencies * (4e-7 * np.pi) * 100)
    np.testing.assert_allclose(observed, analytic, rtol=1e-12)
    assert inverse["inverse"]["truth"] is None and inverse["truth"] is None
    assert inverse["inverse"]["active"].count(False) >= 2
    assert len(inverse["inverse"]["evaluation_protocol"]["starts"]) == 3
    assert method["uncertainty"]["status"] == "computed"
    assert "fixed thickness" in method["uncertainty"]["conditioning"]
    assert status["wall_ms"] >= 0

    layered, _asset, layered_data, _ = upload_dataset(
        harness, LAYERED, station="TWO_LAYER_NOISY_ROTATED", count=24, rotation=27)
    _screen, layered_qc = complete(harness, submit(harness, layered, layered_data, M05_ID, {}))
    base = {"qc_job_id": layered_qc["job_id"], "thickness_m": [350],
            "initial_ohm_m": [100, 100], "bootstrap_samples": 20, "seed": 61001}
    low, _ = complete(harness, submit(harness, layered, layered_data, M06_ID, {**base, "beta": 0.001}))
    high, _ = complete(harness, submit(harness, layered, layered_data, M06_ID, {**base, "beta": 0.5}))
    assert low["request_sha256"] != high["request_sha256"]
    low_model = low["inverse"]["methods"]["mt-lm"]["model"]
    high_model = high["inverse"]["methods"]["mt-lm"]["model"]
    assert not np.allclose(low_model, high_model, rtol=1e-5)
    assert len(low["inverse"]["evaluation_protocol"]["thickness_sensitivity"]) == 2
    assert low["inverse"]["evaluation_protocol"]["halfspace_baseline"]["heldout_component_wrms"] is not None


def test_malformed_and_clear_lake_exclusion(make_harness, tmp_path):
    harness = make_harness(mt_online_enabled=True)
    harness.account()
    malformed = tmp_path / "malformed.edi"
    malformed.write_bytes(NATIVE.read_bytes().replace(b">ZXYR", b">UNKNOWN", 1))
    project, _asset, dataset, _ = upload_dataset(
        harness, malformed, station="HALFSPACE_100_NATIVE", count=24)
    job = submit(harness, project, dataset, M05_ID, {})
    asyncio.run(run_one(harness.settings))
    status = harness.client.get(f"/api/projects/{project['id']}/jobs/{job['job_id']}").json()
    assert status["state"] == "failed" and status["result_url"] is None
    cannot_invert = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": M06_ID,
        "parameters": {"qc_job_id": job["job_id"], "thickness_m": [],
                       "initial_ohm_m": [100], "beta": 0.001},
    })
    assert cannot_invert.status_code == 422

    if not CLEAR_LAKE.is_file():
        pytest.skip("Ignored cl061 original must be acquired locally for the field exclusion gate")
    body = CLEAR_LAKE.read_bytes()
    assert hashlib.sha256(body).hexdigest() == "90c5c96cd69d6d29c866a768097cb3b38bc20e8b9c143e24bf10b2d253261e83"
    field, _asset, field_data, _ = upload_dataset(
        harness, CLEAR_LAKE, station="cl061", count=42, tipper=True, provider="USGS Clear Lake")
    screen, qc = complete(harness, submit(harness, field, field_data, M05_ID, {}))
    assert screen["screen"]["one_d_inversion_eligible"] is False
    assert screen["inverse"] is None and screen["truth"] is None
    denied = harness.request("POST", f"/api/projects/{field['id']}/jobs", json={
        "dataset_id": field_data["dataset_id"], "method_id": M06_ID,
        "parameters": {"qc_job_id": qc["job_id"], "thickness_m": [],
                       "initial_ohm_m": [100], "beta": 0.001},
    })
    assert denied.status_code == 422 and denied.json()["code"] == "method_ineligible"


@pytest.mark.parametrize("field,value", [
    ("measurement_unit", "ohm"), ("sign_convention", "-"),
    ("variance_convention", "per-real-component"), ("rotation_degrees", 90),
])
def test_declared_physics_mismatch_fails_m05(make_harness, field, value):
    harness = make_harness(mt_online_enabled=True)
    harness.account()
    body = NATIVE.read_bytes()
    metadata = edi_metadata(body, station="HALFSPACE_100_NATIVE", count=24)
    destination = (metadata["physical"] if field == "measurement_unit"
                   else metadata["physical"]["geometry"])
    destination[field] = value
    project = harness.project()
    uploaded = harness.upload(project["id"], body, metadata)
    assert uploaded.status_code == 201, uploaded.text
    dataset = harness.request("POST", f"/api/projects/{project['id']}/datasets",
                              json={"asset_id": uploaded.json()["asset_id"]})
    assert dataset.status_code == 201, dataset.text
    job = submit(harness, project, dataset.json(), M05_ID, {})
    assert asyncio.run(run_one(harness.settings)) == job["job_id"]
    status = harness.client.get(f"/api/projects/{project['id']}/jobs/{job['job_id']}").json()
    assert status["state"] == "failed" and status["result_url"] is None


def test_bundle_roundtrip_and_wrong_principal(make_harness):
    harness = make_harness(mt_online_enabled=True)
    harness.account()
    project, asset, dataset, body = upload_dataset(
        harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    _screen, qc = complete(harness, submit(harness, project, dataset, M05_ID, {}))
    result, job = complete(harness, submit(harness, project, dataset, M06_ID, {
        "qc_job_id": qc["job_id"], "thickness_m": [], "initial_ohm_m": [100],
        "beta": 0.001, "bootstrap_samples": 20, "seed": 61001,
    }))
    route = f"/api/projects/{project['id']}/jobs/{job['job_id']}"
    response = harness.client.get(route + "/export")
    assert response.status_code == 200, response.text
    manifest, reimported, imported_result = verify_bundle(response.content)
    assert manifest["units"]["frequency"] == "Hz"
    assert manifest["units"]["impedance"] == "ohm E/H"
    assert manifest["source"]["rights_decision"] == "provider-link-only"
    assert manifest["raw_bytes_included"] is False and body not in response.content
    assert reimported["parent_raw_sha256"] == sha256(body)
    assert imported_result == result
    with zipfile.ZipFile(io.BytesIO(response.content)) as original:
        members = {name: original.read(name) for name in original.namelist()}
    changed = json.loads(members["result.json"])
    changed["inverse"]["methods"]["mt-lm"]["predicted"]["real"][0] += 1
    members["result.json"] = canonical_bytes(changed)
    changed_manifest = json.loads(members["manifest.json"])
    changed_manifest["members"]["result.json"] = {"sha256": sha256(members["result.json"]),
                                                      "bytes": len(members["result.json"])}
    members["manifest.json"] = canonical_bytes(changed_manifest)
    tampered = io.BytesIO()
    with zipfile.ZipFile(tampered, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in ("manifest.json", "dataset.json", "result.json"):
            archive.writestr(name, members[name])
    with pytest.raises(ValueError, match="predicted or residual"):
        verify_bundle(tampered.getvalue())
    with zipfile.ZipFile(io.BytesIO(response.content)) as original:
        members = {name: original.read(name) for name in original.namelist()}
    changed_dataset = json.loads(members["dataset.json"])
    changed_result = json.loads(members["result.json"])
    changed_manifest = json.loads(members["manifest.json"])
    changed_dataset["physical_metadata"]["measurement_unit"] = "ohm"
    changed_result["physical_metadata"]["measurement_unit"] = "ohm"
    members["dataset.json"] = canonical_bytes(changed_dataset)
    changed_result["dataset_sha256"] = sha256(members["dataset.json"])
    members["result.json"] = canonical_bytes(changed_result)
    changed_manifest["provenance"]["dataset_sha256"] = sha256(members["dataset.json"])
    for name in ("dataset.json", "result.json"):
        changed_manifest["members"][name] = {"sha256": sha256(members[name]), "bytes": len(members[name])}
    members["manifest.json"] = canonical_bytes(changed_manifest)
    tampered = io.BytesIO()
    with zipfile.ZipFile(tampered, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in ("manifest.json", "dataset.json", "result.json"):
            archive.writestr(name, members[name])
    with pytest.raises(ValueError, match="declared units"):
        verify_bundle(tampered.getvalue())
    with zipfile.ZipFile(io.BytesIO(response.content)) as original:
        members = {name: original.read(name) for name in original.namelist()}
    changed_result = json.loads(members["result.json"])
    changed_result["inverse"]["methods"]["mt-lm"]["uncertainty"]["lower"][0] += 1
    members["result.json"] = canonical_bytes(changed_result)
    changed_manifest = json.loads(members["manifest.json"])
    changed_manifest["members"]["result.json"] = {
        "sha256": sha256(members["result.json"]), "bytes": len(members["result.json"])}
    members["manifest.json"] = canonical_bytes(changed_manifest)
    tampered = io.BytesIO()
    with zipfile.ZipFile(tampered, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in ("manifest.json", "dataset.json", "result.json"):
            archive.writestr(name, members[name])
    with pytest.raises(ValueError, match="interval summary differs"):
        verify_bundle(tampered.getvalue())
    harness.account(email="other-principal@example.org")
    for path in (f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}",
                 f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}/methods",
                 route, route + "/result", route + "/export", asset["download_url"]):
        assert harness.client.get(path).status_code == 404
    assert harness.request("POST", route + "/cancel").status_code == 404
    assert harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": M05_ID, "parameters": {},
    }).status_code == 404


def test_verified_snapshot_survives_source_drift(make_harness, tmp_path):
    harness = make_harness(mt_online_enabled=True)
    harness.account()
    project, _asset, dataset, body = upload_dataset(
        harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    envelope = harness.client.get(
        f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}").json()
    original = tmp_path / "original.edi"
    original.write_bytes(body)
    stage = tmp_path / "snapshot"
    stage.mkdir()
    snapshot = verified_source_snapshot(original, stage, raw_sha256=sha256(body), raw_bytes=len(body))
    original.write_bytes(body.replace(b">ZXYR", b">UNKNOWN", 1))
    result = compute_mt(envelope, snapshot, dataset_sha=dataset["sha256"], job_id="snapshot-test",
                        request_sha="0" * 64, method_id=M05_ID, parameters={})
    assert snapshot.read_bytes() == body
    assert result["raw_sha256"] == sha256(body) and result["raw_bytes"] == len(body)
    assert result["screen"]["one_d_inversion_eligible"] is True
    with pytest.raises(ValueError, match="differ from receipt"):
        verified_source_snapshot(original, stage, raw_sha256=sha256(body), raw_bytes=len(body))


def test_worker_gate_refuses_queued_mt(make_harness, monkeypatch):
    harness = make_harness(mt_online_enabled=True)
    harness.account()
    project, _asset, dataset, _ = upload_dataset(
        harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    job = submit(harness, project, dataset, M05_ID, {})
    monkeypatch.delenv("GEOPHYSICS_MT_ONLINE_ENABLED", raising=False)
    monkeypatch.setenv("GEOPHYSICS_DATA_DIR", str(harness.settings.data_dir))
    closed_worker = WorkerSettings.from_env()
    assert closed_worker.mt_online_enabled is False
    assert asyncio.run(run_one(closed_worker)) == job["job_id"]
    status = harness.client.get(f"/api/projects/{project['id']}/jobs/{job['job_id']}").json()
    assert status["state"] == "failed" and status["error"]["code"] == "host_admission_pending"
    assert status["result_url"] is None and status["peak_rss_bytes"] == 0
    monkeypatch.setenv("GEOPHYSICS_MT_ONLINE_ENABLED", "1")
    assert WorkerSettings.from_env().mt_online_enabled is True


def test_m06_requires_matching_owned_qc(make_harness):
    harness = make_harness(mt_online_enabled=True)
    harness.account()
    first_project, _asset, first_data, _ = upload_dataset(
        harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    _result, qc = complete(harness, submit(harness, first_project, first_data, M05_ID, {}))
    project, _asset, dataset, _ = upload_dataset(
        harness, LAYERED, station="TWO_LAYER_NOISY_ROTATED", count=24, rotation=27)
    denied = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": M06_ID,
        "parameters": {"qc_job_id": qc["job_id"], "thickness_m": [350],
                       "initial_ohm_m": [100, 100], "beta": .001},
    })
    assert denied.status_code == 422 and denied.json()["code"] == "method_ineligible"


def test_host_gate_defaults_closed(make_harness):
    harness = make_harness()
    harness.account()
    project, _asset, dataset, _ = upload_dataset(
        harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    methods = harness.client.get(f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}/methods").json()
    assert methods["methods"] == []
    assert {item["method_id"] for item in methods["unavailable"]} == {M05_ID, M06_ID}
    denied = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": M05_ID, "parameters": {},
    })
    assert denied.status_code == 409 and denied.json()["code"] == "host_admission_pending"


def test_raw_receipt_tamper_blocks_m05(make_harness):
    harness = make_harness(mt_online_enabled=True)
    owner = harness.account()
    project, asset, dataset, _ = upload_dataset(
        harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    original = harness.settings.data_dir / "projects" / owner["id"] / project["id"] / asset["asset_id"]
    original.write_bytes(original.read_bytes() + b"tampered")
    denied = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": M05_ID, "parameters": {},
    })
    assert denied.status_code == 409 and denied.json()["code"] == "raw_integrity_failed"
    assert harness.client.get(f"/api/projects/{project['id']}/jobs").json()["jobs"] == []


def test_worker_rechecks_queued_raw_receipt(make_harness):
    harness = make_harness(mt_online_enabled=True)
    owner = harness.account()
    project, asset, dataset, _ = upload_dataset(
        harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    job = submit(harness, project, dataset, M05_ID, {})
    original = harness.settings.data_dir / "projects" / owner["id"] / project["id"] / asset["asset_id"]
    original.write_bytes(original.read_bytes().replace(b">ZXYR", b">UNKNOWN", 1))
    assert asyncio.run(run_one(harness.settings)) == job["job_id"]
    status = harness.client.get(f"/api/projects/{project['id']}/jobs/{job['job_id']}").json()
    assert status["state"] == "failed" and status["error"]["code"] == "raw_integrity_failed"
    assert status["result_url"] is None and status["peak_rss_bytes"] == 0


def test_mt_account_quota_reserves_full_m06_scratch(make_harness):
    harness = make_harness(mt_online_enabled=True, max_upload_bytes=1024 * 1024,
                           account_quota_bytes=20 * 1024 * 1024)
    harness.account()
    project, _asset, dataset, _ = upload_dataset(
        harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    _screen, qc = complete(harness, submit(harness, project, dataset, M05_ID, {}))
    denied = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": M06_ID,
        "parameters": {"qc_job_id": qc["job_id"], "thickness_m": [],
                       "initial_ohm_m": [100], "beta": .001},
    })
    assert denied.status_code == 507 and denied.json()["code"] == "account_quota_exceeded"


def test_preflight_cancel_timeout_and_memory(make_harness, monkeypatch, tmp_path):
    too_small = make_harness(mt_online_enabled=True, worker_memory_bytes=80 * 1024 * 1024)
    too_small.account()
    project, _asset, dataset, _ = upload_dataset(
        too_small, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    rejected = too_small.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": M05_ID, "parameters": {},
    })
    assert rejected.status_code == 413 and rejected.json()["code"] == "job_resource_ineligible"
    scratch_small = make_harness(mt_online_enabled=True, worker_scratch_bytes=1024 * 1024)
    scratch_small.account(email="scratch-preflight@example.org")
    small_project, _asset, small_dataset, _ = upload_dataset(
        scratch_small, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    rejected_scratch = scratch_small.request("POST", f"/api/projects/{small_project['id']}/jobs", json={
        "dataset_id": small_dataset["dataset_id"], "method_id": M05_ID, "parameters": {},
    })
    assert rejected_scratch.status_code == 413 and rejected_scratch.json()["code"] == "job_resource_ineligible"

    harness = make_harness(mt_online_enabled=True, worker_wall_seconds=1)
    harness.account(email="limits@example.org")
    project, _asset, dataset, _ = upload_dataset(
        harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    queued = submit(harness, project, dataset, M05_ID, {})
    base = f"/api/projects/{project['id']}/jobs/{queued['job_id']}"
    assert harness.request("POST", base + "/cancel").json()["state"] == "cancelled"
    assert asyncio.run(run_one(harness.settings)) is None
    pid_file = tmp_path / "mt-child.pid"
    script = "import os,sys,time;open(sys.argv[1],'w').write(str(os.getpid()));time.sleep(10)"
    original = worker._mt_command
    monkeypatch.setattr("app.worker._mt_command", lambda *_: [sys.executable, "-c", script, str(pid_file)])
    timed = submit(harness, project, dataset, M05_ID, {})
    assert asyncio.run(run_one(harness.settings)) == timed["job_id"]
    state = harness.client.get(f"/api/projects/{project['id']}/jobs/{timed['job_id']}").json()
    assert state["state"] == "failed" and state["error"]["code"] == "job_timeout"
    assert pid_file.is_file() and not psutil.pid_exists(int(pid_file.read_text()))
    pid_file.unlink()
    cancelling = submit(harness, project, dataset, M05_ID, {})
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(lambda: asyncio.run(run_one(harness.settings)))
        deadline = time.monotonic() + 5
        status_url = f"/api/projects/{project['id']}/jobs/{cancelling['job_id']}"
        while harness.client.get(status_url).json()["state"] != "running":
            assert time.monotonic() < deadline
            time.sleep(.02)
        assert harness.request("POST", status_url + "/cancel").json()["cancel_requested"]
        assert future.result(timeout=8) == cancelling["job_id"]
    state = harness.client.get(status_url).json()
    assert state["state"] == "cancelled" and state["error"]["code"] == "user_cancelled"
    if pid_file.exists():
        assert not psutil.pid_exists(int(pid_file.read_text()))
    monkeypatch.setattr("app.worker._mt_command", original)

    memory = submit(harness, project, dataset, M05_ID, {})
    with sqlite3.connect(harness.settings.database_path) as db:
        db.execute("UPDATE processing_jobs SET preflight=json_set(preflight,'$.memory_limit_bytes',?) WHERE id=?",
                   (80 * 1024 * 1024, memory["job_id"]))
    memory_script = "import time; allocation=bytearray(120000000);time.sleep(5)"
    monkeypatch.setattr("app.worker._mt_command", lambda *_: [sys.executable, "-c", memory_script])
    assert asyncio.run(run_one(harness.settings)) == memory["job_id"]
    state = harness.client.get(f"/api/projects/{project['id']}/jobs/{memory['job_id']}").json()
    assert state["state"] == "failed" and state["error"]["code"] == "job_memory_limit"
