"""Authenticated upload-to-native ordinary-L2 backend contract controls."""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pytest
import choclo

from app.gravity_l2_compute import build_native_requests, compute_gravity_l2
from app.gravity_l2_contract import METHOD_ID, GravityL2Parameters, implementation_hashes, validate_typed_arrays
from app.processing_contract import parse_gravity_dataset


def survey_upload():
    lines = ["station,x,y,z,anomaly,sigma,line_id"]
    for j in range(12):
        for i in range(12):
            lines.append(f"S{j:02d}_{i:02d},{(i-5.5)*100},{(j-5.5)*100},100,0,0.1,L{j:02d}")
    body = ("\n".join(lines) + "\n").encode()
    metadata = {
        "filename": "survey.csv", "mime": "text/csv", "format": "gravity_csv",
        "source": {"provider": "Authored test source", "citation": "Authored synthetic integration control",
            "rights_statement": "This authored test survey may be stored privately.",
            "rights_decision": "mirror", "private_storage_permission": "attested",
            "attribution": "CAOS test fixture", "expected_bytes": len(body),
            "expected_sha256": hashlib.sha256(body).hexdigest()},
        "physical": {"coordinate_reference": "local", "local_crs": "local east north metric frame",
            "axis_order": "xy", "horizontal_datum": "authored local origin",
            "vertical_datum": "authored upward survey plane", "vertical_positive": "up",
            "horizontal_unit": "m", "vertical_unit": "m", "measurement_unit": "mGal",
            "epoch_utc": "2026-10-25T00:00:00Z", "component_frame": "local vertical up",
            "geometry": {"station_id_column": "station", "x_column": "x", "y_column": "y",
                "z_column": "z", "value_column": "anomaly", "sigma_column": "sigma",
                "ordinary_l2": {"quantity": "processed_gravity_anomaly",
                    "processing_kind": "provider_declared_derivative",
                    "correction_state": "complete_no_additional_corrections",
                    "original_acceleration_unit": "mGal", "original_vertical_positive": "up",
                    "sigma_basis": "explicit_conditional_gaussian",
                    "sigma_citation": "Authored fixed conditional scale of 0.1 mGal",
                    "cross_partition_dependence": "declared_absent",
                    "reference_description": "Authored zero upward anomaly reference",
                    "background_reference": "Fixed zero background in the authored source",
                    "partition_group_column": "line_id"}}}}
    return body, metadata


def parameters():
    return {"schema": "gravity.survey-l2-parameters/v1", "background_mgal": 0.0,
        "mesh": {"origin_m": [-50, -50, -200], "hx_m": [100], "hy_m": [100],
                 "hz_m": [100], "active": [True]},
        "split": {"block_origin_m": [-600, -600], "block_size_m": [100, 100],
                  "buffer_m": 25.0, "seed": 104729},
        "prior": {"lower_kg_m3": [-1500], "upper_kg_m3": [1500], "start_kg_m3": [0],
                  "reference_kg_m3": [0], "density_scale_kg_m3": 1000,
                  "lengths_m": [100, 100, 100], "basis": "Authored signed density contrast",
                  "reference_in_smooth": True, "spatial_weights": "none"}}


def upload_dataset(harness, project):
    body, metadata = survey_upload()
    asset = harness.upload(project["id"], body, metadata)
    assert asset.status_code == 201, asset.text
    created = harness.request("POST", f"/api/projects/{project['id']}/datasets",
                              json={"asset_id": asset.json()["asset_id"]})
    assert created.status_code == 201, created.text
    payload = harness.client.get(
        f"/api/projects/{project['id']}/datasets/{created.json()['dataset_id']}"
    ).json()
    return asset.json(), created.json(), payload, body


def test_upload_is_source_bound_but_host_lane_stays_closed(make_harness):
    harness = make_harness()
    harness.account()
    project = harness.project()
    asset, dataset, payload, raw = upload_dataset(harness, project)
    methods = harness.client.get(
        f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}/methods"
    ).json()
    entry = next(item for item in methods["unavailable"] if item["method_id"] == METHOD_ID)
    assert entry["source_eligible"] is True and entry["lane"] == "pending_host_admission"
    assert harness.client.get(asset["download_url"]).content == raw
    assert payload["source"]["source_id"] == asset["source"]["source_id"]
    assert payload["partition_group_ids"][:12] == ["L00"] * 12
    queued = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID, "parameters": parameters(),
    })
    assert queued.status_code == 409 and queued.json()["code"] == "host_admission_pending"


def test_missing_error_or_group_provenance_is_not_eligible(make_harness):
    harness = make_harness()
    harness.account()
    project = harness.project()
    body, metadata = survey_upload()
    del metadata["physical"]["geometry"]["ordinary_l2"]["sigma_citation"]
    del metadata["physical"]["geometry"]["ordinary_l2"]["partition_group_column"]
    asset = harness.upload(project["id"], body, metadata)
    assert asset.status_code == 201, asset.text
    created = harness.request("POST", f"/api/projects/{project['id']}/datasets",
                              json={"asset_id": asset.json()["asset_id"]})
    assert created.status_code == 422


@pytest.mark.parametrize("damage", [
    lambda p: p.update(schema="other"),
    lambda p: p["split"].update(seed=104728),
    lambda p: p["split"].update(buffer_m=0),
    lambda p: p["mesh"].update(active=[1]),
    lambda p: p["prior"].update(start_kg_m3=[0, 0]),
    lambda p: p["prior"].update(lower_kg_m3=[2000]),
    lambda p: p["mesh"].update(hx_m=[1] * 65, hy_m=[1] * 65),
])
def test_parameters_reject_frozen_policy_and_resource_violations(damage):
    value = parameters()
    damage(value)
    with pytest.raises(ValueError):
        GravityL2Parameters.model_validate(value)


def _fake_source_dataset(body, metadata):
    asset = SimpleNamespace(id="asset-1", sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body),
                            detected_format="gravity_csv", physical_metadata=metadata["physical"])
    source = SimpleNamespace(id="source-1", sha256=asset.sha256, private_storage_permission="attested",
        provider="Authored", exact_url=None, doi=None, citation=metadata["source"]["citation"],
        retrieved_at=None, rights_decision="mirror", rights_statement=metadata["source"]["rights_statement"],
        attribution=metadata["source"]["attribution"])
    dataset = parse_gravity_dataset(body, dataset_id="dataset-1", owner_id="owner-1", project_id="project-1",
        asset=asset, source=source, settings=SimpleNamespace(max_dataset_bytes=2 * 1024**2, max_dataset_rows=4096))
    return asset, source, dataset


def test_native_plan_uses_the_source_dataset_and_locked_split():
    body, metadata = survey_upload()
    asset, source, dataset = _fake_source_dataset(body, metadata)
    request = {"source_id": source.id, "raw_asset_id": asset.id,
               "raw_sha256": asset.sha256, "raw_bytes": asset.byte_count}
    parsed, plan, calibration, active_count = build_native_requests(dataset, request, parameters())
    assert active_count == 1 and parsed.split.seed == 104729
    assert plan["request"]["source"]["raw_sha256"] == asset.sha256
    assert plan["request"]["stations"]["station_ids"] == tuple(dataset["station_ids"])
    assert plan["request"]["stations"]["partition_group_ids"] == tuple(dataset["partition_group_ids"])
    assert np.array_equal(calibration["observations"]["rows"], plan["development_rows"])
    assert np.array_equal(calibration["observations"]["gz_up_mgal"],
                          np.asarray(dataset["observed_mgal"])[plan["development_rows"]])
    assert np.array_equal(calibration["noise"]["values"],
                          np.asarray(dataset["sigma_mgal"])[plan["development_rows"]])


def test_uploaded_survey_executes_native_calibration_then_sealed_evaluation(tmp_path):
    body, metadata = survey_upload()
    # A genuine synthetic integration input: derive the uploaded observations
    # from the same declared one-cell prism geometry, not a zero-field control
    # that leaves the bounded optimizer with no descent direction.
    rows = body.decode("utf-8").splitlines()
    for index in range(1, len(rows)):
        station, x, y, z, _anomaly, sigma, group = rows[index].split(",")
        observed = choclo.prism.gravity_u(
            float(x), float(y), float(z), -50.0, 50.0, -50.0, 50.0,
            -200.0, -100.0, 500.0,
        ) * 1e5
        rows[index] = ",".join((station, x, y, z, f"{observed:.12g}", sigma, group))
    body = ("\n".join(rows) + "\n").encode("utf-8")
    metadata["source"]["expected_bytes"] = len(body)
    metadata["source"]["expected_sha256"] = hashlib.sha256(body).hexdigest()
    asset, source, dataset = _fake_source_dataset(body, metadata)
    source_path = tmp_path / "source.csv"
    source_path.write_bytes(body)
    result = compute_gravity_l2(dataset, source_path, job_id="job-1",
        dataset_sha=hashlib.sha256(json.dumps(dataset, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False, allow_nan=False).encode()).hexdigest(),
        request_sha="e" * 64, raw_sha=asset.sha256, raw_bytes=asset.byte_count,
        raw_asset_id=asset.id, source_id=source.id, parameters=parameters(),
        memory_limit=2 * 1024**3, scratch_limit=256 * 1024**2,
        expected_implementation_hashes=implementation_hashes())
    assert result["method_id"] == METHOD_ID
    assert result["raw_sha256"] == asset.sha256
    assert result["gravity_l2"]["calibration"]["selection_status"] == "selected"
    assert result["gravity_l2"]["outer_evaluation"]["field_truth"] is None
    assert result["gravity_l2"]["outer_evaluation"]["model_accuracy"] is None
    assert result["gravity_l2"]["scope"]["host_accepted"] is False


def test_changed_original_bytes_fail_before_native_calibration(tmp_path, monkeypatch):
    body, metadata = survey_upload()
    asset, source, dataset = _fake_source_dataset(body, metadata)
    path = tmp_path / "source.csv"
    path.write_bytes(body + b"tampered")
    def should_not_run(*args, **kwargs):
        raise AssertionError("native solver must not receive unverified bytes")
    monkeypatch.setattr("app.gravity_l2_compute._native_modules", lambda: should_not_run())
    with pytest.raises(ValueError, match="file size changed"):
        compute_gravity_l2(dataset, path, job_id="j", dataset_sha="d" * 64,
            request_sha="e" * 64, raw_sha=asset.sha256, raw_bytes=len(body), raw_asset_id=asset.id,
            source_id=source.id, parameters=parameters(), memory_limit=2 * 1024**3,
            scratch_limit=256 * 1024**2, expected_implementation_hashes=implementation_hashes())


def test_typed_array_sha_detects_result_tamper():
    value = {"kind": "ndarray", "dtype": "<f8", "shape": [2], "order": "C",
             "sha256": hashlib.sha256(np.asarray([1., 2.], dtype="<f8").tobytes()).hexdigest(),
             "data": [1., 2.]}
    validate_typed_arrays(value)
    value["data"][1] = 3.
    with pytest.raises(ValueError, match="SHA-256"):
        validate_typed_arrays(value)
