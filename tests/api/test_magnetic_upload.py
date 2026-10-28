"""Owned M03 magnetic CSV admission stays source-bound and execution-closed."""

from __future__ import annotations

import hashlib
import sqlite3

from app.processing_contract import canonical_bytes


MAPPING = {
    "easting": "E", "northing": "N", "value": "TMI_nT", "line_id": "line",
    "line_role": "role", "sensor_height_m": "height_m", "sample_order": "sample",
}


def magnetic_original() -> bytes:
    lines = ["E,N,TMI_nT,line,role,height_m,sample"]
    for line in range(5):
        for sample in range(8):
            lines.append(f"{500000 + sample * 10},{100000 + line * 100},"
                         f"{20 + line + sample / 10},F{line},flight,100,{sample}")
    return ("\n".join(lines) + "\n").encode()


def metadata(raw: bytes) -> dict:
    return {
        "filename": "flight-lines.csv", "mime": "text/csv", "format": "magnetic_csv",
        "source": {
            "provider": "Authored M03 control", "citation": "Authored synthetic control; not field data.",
            "rights_statement": "Private test fixture authored for this test.", "rights_decision": "mirror",
            "private_storage_permission": "attested", "attribution": "M03 test fixture",
            "expected_bytes": len(raw), "expected_sha256": hashlib.sha256(raw).hexdigest(),
        },
        "physical": {
            "coordinate_reference": "epsg", "epsg": 32719, "axis_order": "xy",
            "horizontal_datum": "WGS84", "vertical_datum": "survey reference",
            "vertical_positive": "up", "horizontal_unit": "m", "vertical_unit": "m",
            "measurement_unit": "nT", "epoch_utc": "2026-10-27T12:00:00Z",
            "component_frame": "total field",
            "geometry": {"line_id_column": "line", "x_column": "E", "y_column": "N",
                          "z_column": "height_m", "value_column": "TMI_nT"},
        },
    }


def options(mapping: dict | None = None) -> dict:
    return {"mapping": mapping or MAPPING, "processing_state": "Synthetic total-field anomaly, no prior corrections",
            "value_quantity": "total-field anomaly", "sensor_height_reference": "above local ground"}


def test_magnetic_csv_creates_source_bound_dataset_without_claiming_processing(harness):
    harness.account()
    project = harness.project()
    raw = magnetic_original()
    upload = harness.upload(project["id"], raw, metadata(raw))
    assert upload.status_code == 201, upload.text
    created = harness.request("POST", f"/api/projects/{project['id']}/datasets",
                              json={"asset_id": upload.json()["asset_id"], "magnetic_request": options()})
    assert created.status_code == 201, created.text
    receipt = created.json()
    dataset = harness.client.get(f"/api/projects/{project['id']}/datasets/{receipt['dataset_id']}").json()
    assert dataset["modality"] == "magnetic_flightline"
    assert dataset["dimensions"] == {"measurement": 40}
    assert dataset["mapping"] == MAPPING
    assert dataset["parent_raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert dataset["source"]["citation"] == "Authored synthetic control; not field data."
    assert dataset["qc_verdict"] == "source_bound_not_numerically_processed"
    assert hashlib.sha256(canonical_bytes(dataset)).hexdigest() == receipt["sha256"]
    eligibility = harness.client.get(f"/api/projects/{project['id']}/datasets/{receipt['dataset_id']}/methods").json()
    assert eligibility["methods"] == []
    assert eligibility["unavailable"][0]["method_id"] == "magnetic.flightline-qc-grid/v1"
    assert eligibility["unavailable"][0]["lane"] == "pending_host_admission"
    assert eligibility["unavailable"][0]["source_eligible"] is True
    assert eligibility["unavailable"][0]["reason_fields"] == ["host.magnetic_online_admission"]
    job = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": receipt["dataset_id"], "method_id": "magnetic.flightline-qc-grid/v1",
        "parameters": {"grid_spacing_m": 20, "holdout_fraction": 0.2, "seed": "m03-test"},
    })
    assert job.status_code == 409 and job.json()["code"] == "host_admission_pending"
    with sqlite3.connect(harness.settings.database_path) as db:
        db.execute("UPDATE source_records SET private_storage_permission=NULL WHERE id=?",
                   (upload.json()["source"]["source_id"],))
    changed = harness.client.get(f"/api/projects/{project['id']}/datasets/{receipt['dataset_id']}/methods").json()
    assert changed["unavailable"][0]["source_eligible"] is False
    assert changed["unavailable"][0]["lane"] == "ineligible_source"
    assert changed["unavailable"][0]["reason_fields"] == ["source.private_storage_permission"]


def test_magnetic_csv_requires_explicit_mapping_and_source_declarations(harness):
    harness.account()
    project = harness.project()
    raw = magnetic_original()
    upload = harness.upload(project["id"], raw, metadata(raw))
    assert upload.status_code == 201, upload.text
    rejected = harness.request("POST", f"/api/projects/{project['id']}/datasets",
                               json={"asset_id": upload.json()["asset_id"]})
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "magnetic_metadata_required"
    bad_mapping = {**MAPPING, "sample_order": "missing-column"}
    rejected = harness.request("POST", f"/api/projects/{project['id']}/datasets",
                               json={"asset_id": upload.json()["asset_id"], "magnetic_request": options(bad_mapping)})
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "magnetic_columns_missing"


def test_admitted_local_m03_worker_creates_provenance_bound_result_and_export(make_harness):
    from app.magnetic_contract import METHOD_ID
    from app.worker import _claim, _execute

    harness = make_harness(magnetic_online_enabled=True)
    harness.account()
    project = harness.project()
    raw = magnetic_original()
    upload = harness.upload(project["id"], raw, metadata(raw))
    assert upload.status_code == 201, upload.text
    created = harness.request("POST", f"/api/projects/{project['id']}/datasets",
                              json={"asset_id": upload.json()["asset_id"], "magnetic_request": options()})
    assert created.status_code == 201, created.text
    dataset_id = created.json()["dataset_id"]
    eligibility = harness.client.get(f"/api/projects/{project['id']}/datasets/{dataset_id}/methods").json()
    assert eligibility["methods"][0]["method_id"] == METHOD_ID
    queued = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset_id, "method_id": METHOD_ID,
        "parameters": {"grid_spacing_m": 20, "holdout_fraction": .2, "seed": "worker-integration"},
    })
    assert queued.status_code == 202, queued.text
    app = harness.client.app

    async def execute():
        job = await _claim(app.state.sessions, "m03-integration-test")
        assert job is not None and job.id == queued.json()["job_id"]
        await _execute(harness.settings, app.state.sessions, job, poll_interval=.02)

    harness.client.portal.call(execute)
    terminal = harness.client.get(f"/api/projects/{project['id']}/jobs/{queued.json()['job_id']}")
    assert terminal.status_code == 200, terminal.text
    assert terminal.json()["state"] == "succeeded", terminal.text
    assert terminal.json()["wall_ms"] > 0 and terminal.json()["peak_rss_bytes"] > 0
    result = harness.client.get(f"/api/projects/{project['id']}/jobs/{queued.json()['job_id']}/result")
    assert result.status_code == 200, result.text
    assert result.json()["claims"]["source_hash_recomputed_from_original_bytes"] is True
    assert result.json()["heldout_interpolation"]["supported_heldout_row_count"] > 0
    exported = harness.client.get(f"/api/projects/{project['id']}/jobs/{queued.json()['job_id']}/export")
    assert exported.status_code == 200, exported.text
    from app.magnetic_bundle import verify_magnetic_bundle
    manifest, dataset, bundled_result = verify_magnetic_bundle(exported.content)
    assert manifest["units"] == {"position": "m", "observation": "nT"}
    assert dataset["parent_raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert bundled_result["job_id"] == queued.json()["job_id"]
