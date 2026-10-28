"""Authenticated upload-to-native ordinary-L2 backend contract controls."""
from __future__ import annotations

import hashlib
import json
import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import choclo

from app.gravity_l2_compute import build_native_requests, compute_gravity_l2
from app.gravity_l2_contract import METHOD_ID, GravityL2Parameters, implementation_hashes, validate_typed_arrays
from app.config import WorkerSettings
from app.bundle import verify_bundle
from app.processing_contract import parse_gravity_dataset
from app.worker import run_one


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
    assert entry["reason_fields"] == ["host.gravity_l2_online_admission"]
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


def test_uploaded_survey_executes_native_calibration_then_sealed_evaluation(tmp_path, monkeypatch):
    # The production isolated child sets these before importing BLAS/SciPy;
    # this direct adapter test must model the same frozen native policy.
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        monkeypatch.setenv(variable, "1")
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


def test_uploaded_user_survey_runs_isolated_inverse_and_parameter_changes_predictions(make_harness):
    """Exercise authenticated upload -> eligibility -> isolated M02 child -> owned result."""
    # Build an authored, non-zero physical survey from the declared one-cell
    # prism so the real solver has an identifiable descent direction.
    body, metadata = survey_upload()
    rows = body.decode("utf-8").splitlines()
    for index in range(1, len(rows)):
        station, x, y, z, _anomaly, sigma, group = rows[index].split(",")
        anomaly = choclo.prism.gravity_u(
            float(x), float(y), float(z), -50.0, 50.0, -50.0, 50.0,
            -200.0, -100.0, 500.0,
        ) * 1e5
        rows[index] = ",".join((station, x, y, z, f"{anomaly:.12g}", sigma, group))
    body = ("\n".join(rows) + "\n").encode("utf-8")
    metadata["source"]["expected_bytes"] = len(body)
    metadata["source"]["expected_sha256"] = hashlib.sha256(body).hexdigest()

    gravity_python = Path(os.environ.get(
        "GEOPHYSICS_TEST_GRAVITY_PYTHON",
        Path(__file__).resolve().parents[2] / ".venv-pipeline" / "Scripts" / "python.exe"
        if os.name == "nt" else sys.executable,
    )).resolve()
    harness = make_harness(gravity_l2_online_enabled=True)
    worker_settings = WorkerSettings(data_dir=harness.settings.data_dir,
        db_path=harness.settings.db_path, gravity_l2_online_enabled=True,
        gravity_l2_python=gravity_python)
    harness.account()
    project = harness.project("Uploaded physical M02 control")
    asset_response = harness.upload(project["id"], body, metadata)
    assert asset_response.status_code == 201, asset_response.text
    asset = asset_response.json()
    dataset_response = harness.request("POST", f"/api/projects/{project['id']}/datasets",
                                       json={"asset_id": asset["asset_id"]})
    assert dataset_response.status_code == 201, dataset_response.text
    dataset = dataset_response.json()
    method_response = harness.client.get(
        f"/api/projects/{project['id']}/datasets/{dataset['dataset_id']}/methods")
    methods = method_response.json()
    assert any(item["method_id"] == METHOD_ID and item["eligible"] for item in methods["methods"])

    def execute(background_mgal):
        params = parameters()
        params["background_mgal"] = background_mgal
        queued = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
            "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID, "parameters": params,
        })
        assert queued.status_code == 202, queued.text
        job_id = queued.json()["job_id"]
        assert asyncio.run(run_one(worker_settings)) == job_id
        status = harness.client.get(f"/api/projects/{project['id']}/jobs/{job_id}").json()
        assert status["state"] == "succeeded", status["error"]
        return harness.client.get(status["result_url"]).json()

    first = execute(0.0)
    second = execute(0.05)
    for result in (first, second):
        assert result["method_id"] == METHOD_ID
        assert result["raw_sha256"] == asset["sha256"]
        assert result["gravity_l2"]["source"]["raw_sha256"] == asset["sha256"]
        assert result["gravity_l2"]["outer_evaluation"]["field_truth"] is None
        calibration = result["gravity_l2"]["calibration"]
        assert calibration["selection_status"] == "selected"
        final_solve = calibration["final_solve"]
        assert final_solve["status"] == "converged"
        model = np.asarray(final_solve["model_kg_m3"]["data"], dtype=np.float64)
        assert model.shape == (1,) and np.isfinite(model).all()
        assert -1500.0 <= model[0] <= 1500.0

        # Independently recompute the exact submitted 3D prism response from
        # Choclo, including the declared fixed background. This checks the
        # exported model/prediction relationship, not recovery of synthetic
        # truth or field geology.
        mesh = result["parameters"]["mesh"]
        x0, y0, z0 = mesh["origin_m"]
        hx, hy, hz = mesh["hx_m"][0], mesh["hy_m"][0], mesh["hz_m"][0]
        receivers = np.asarray(
            calibration["plan"]["request"]["stations"]["receivers_m"]["data"], dtype=np.float64)
        independent = np.asarray([
            choclo.prism.gravity_u(x, y, z, x0, x0 + hx, y0, y0 + hy,
                                   z0, z0 + hz, float(model[0])) * 1e5
            + result["parameters"]["background_mgal"]
            for x, y, z in receivers
        ])
        predictions = calibration["predictions"]["gz_up_mgal"]
        predicted = np.asarray(predictions["data"], dtype=np.float64)
        assert predicted.shape == (len(receivers),) and predictions["sha256"]
        np.testing.assert_allclose(predicted, independent, rtol=1e-7, atol=1e-10)

        # Recompute the withheld prediction, residual and standardized metrics
        # from the values actually exported by the job.
        heldout = result["gravity_l2"]["outer_evaluation"]
        heldout_rows = np.asarray(heldout["rows"]["data"], dtype=np.int64)
        observed = np.asarray(heldout["observations"]["gz_up_mgal"]["data"], dtype=np.float64)
        heldout_predicted = np.asarray(heldout["predicted_mgal"]["data"], dtype=np.float64)
        residual = np.asarray(
            heldout["residual_observed_minus_predicted_mgal"]["data"], dtype=np.float64)
        whitened = np.asarray(heldout["whitened_residual"]["data"], dtype=np.float64)
        np.testing.assert_array_equal(heldout_predicted, predicted[heldout_rows])
        np.testing.assert_array_equal(residual, observed - heldout_predicted)
        np.testing.assert_allclose(whitened, residual / 0.1, rtol=1e-12, atol=1e-12)
        assert heldout["phi_d"] == pytest.approx(float(whitened @ whitened), rel=1e-12)
        assert heldout["wrms"] == pytest.approx(float(np.sqrt(np.mean(whitened**2))), rel=1e-12)
        assert heldout["rmse_mgal"] == pytest.approx(float(np.sqrt(np.mean(residual**2))), rel=1e-12)
    assert first["request_sha256"] != second["request_sha256"]
    assert (first["gravity_l2"]["calibration"]["predictions"]["gz_up_mgal"]["sha256"]
            != second["gravity_l2"]["calibration"]["predictions"]["gz_up_mgal"]["sha256"])
    assert harness.client.get(asset["download_url"]).content == body
    exported = harness.client.get(
        f"/api/projects/{project['id']}/jobs/{second['job_id']}/export")
    assert exported.status_code == 200
    manifest, exported_dataset, exported_result = verify_bundle(exported.content)
    assert manifest["units"] == {"model": "kg/m3", "observation": "mGal", "coordinates": "m"}
    assert exported_dataset["parent_raw_sha256"] == asset["sha256"]
    assert exported_result == second


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
