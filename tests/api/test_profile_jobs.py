"""Actual path-invoked child and durable failed science, never substitute arrays."""
import hashlib
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.errors import ApiError
from app.profile_contract import validate_profile_result
from app.profile_compute import profile_command
from app.worker import run_one, _stage_bytes, _clear_known_stage
from app.bundle import verify_bundle
from app.processing_contract import canonical_bytes, sha256
from test_profile_contract import profile_fixture, admit
from test_profile_uploads import upload_fixture
from tests.api.test_local_auth import provision, login


def owned_dataset(harness, raw=None, method="ert_ohm", sensor_count=None, count=None):
    project = harness.project()
    default, metadata = upload_fixture(method)
    raw = default if raw is None else raw
    metadata["source"].update(expected_bytes=len(raw), expected_sha256=hashlib.sha256(raw).hexdigest())
    if count is not None:
        metadata["physical"]["geometry"]["measurement_count"] = count
        metadata["physical"]["geometry"]["electrode_count" if method == "ert_ohm" else "sensor_count"] = sensor_count
    asset = harness.upload(project["id"], raw, metadata)
    assert asset.status_code == 201, asset.text
    _, _, _, meta = profile_fixture()
    meta["method"] = "ert.topographic-profile/v1" if method == "ert_ohm" else "traveltime.first-arrival-profile/v1"
    meta["source"].update(source_id=asset.json()["source_id"], sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    response = harness.request("POST", f"/api/projects/{project['id']}/datasets",
                               json={"asset_id": asset.json()["asset_id"], "profile_metadata": meta})
    assert response.status_code == 201, response.text
    return project, asset.json(), response.json(), meta


def profile_harness(make_harness, python=None, enabled=True):
    harness = make_harness(auth_mode="local", profile_online_enabled=enabled,
                           profile_python=python or Path(sys.executable))
    provision(harness)
    assert login(harness).status_code == 204
    assert harness.messages == []
    return harness


def test_owned_admission_and_cancellation(make_harness):
    harness = profile_harness(make_harness)
    project, _, dataset, meta = owned_dataset(harness)
    path = f"/api/projects/{project['id']}/jobs"
    request = {"dataset_id": dataset["dataset_id"], "method_id": meta["method"], "parameters": {}}
    first = harness.request("POST", path, json=request)
    assert first.status_code == 202, first.text
    assert harness.request("POST", path, json=request).status_code == 409
    assert harness.request("POST", f"{path}/{first.json()['job_id']}/cancel").json()["state"] == "cancelled"
    assert asyncio.run(run_one(harness.settings)) is None
    provision(harness, username="another-owner@example.org")
    assert login(harness, username="another-owner@example.org").status_code == 204
    assert harness.client.get(f"{path}/{first.json()['job_id']}").status_code == 404
    assert harness.request("POST", path, json=request).status_code == 404


def test_host_flag_closed_preserves_local_route(make_harness):
    harness = profile_harness(make_harness, enabled=False)
    project, _, dataset, meta = owned_dataset(harness)
    base = f"/api/projects/{project['id']}"
    methods = harness.client.get(f"{base}/datasets/{dataset['dataset_id']}/methods").json()
    assert methods["methods"] == []
    assert methods["unavailable"][0]["method_id"] == meta["method"]
    job = harness.request("POST", base+"/jobs", json={"dataset_id": dataset["dataset_id"],
                                "method_id": meta["method"], "parameters": {}})
    assert job.status_code == 409 and job.json()["code"] == "host_admission_pending"


def test_actual_owned_failed_science_execution(make_harness):
    harness = profile_harness(make_harness)
    raw = upload_fixture("ert_ohm")[0].replace(b"1 4 2 3 1\n", b"1 4 2 3 -1\n")
    project, asset, dataset, meta = owned_dataset(harness, raw)
    base = f"/api/projects/{project['id']}/jobs"
    created = harness.request("POST", base, json={"dataset_id": dataset["dataset_id"],
                              "method_id": meta["method"], "parameters": {}})
    assert created.status_code == 202, created.text
    job_id = created.json()["job_id"]
    assert asyncio.run(run_one(harness.settings)) == job_id
    state = harness.client.get(f"{base}/{job_id}").json()
    assert state["state"] == "succeeded", state["error"]
    result = harness.client.get(state["result_url"]).json()
    assert result["numerical_verdict"] == "ineligible"
    assert result["profile"]["engine_report"]["inverse_status"] == "ineligible"
    assert "inverse" not in result["profile"]["engine_report"]
    assert harness.client.get(asset["download_url"]).content == raw
    bundle = harness.client.get(f"{base}/{job_id}/export")
    assert bundle.status_code == 200, bundle.text
    manifest, saved_dataset, saved_result = verify_bundle(bundle.content)
    assert manifest["raw_bytes_included"] is False and saved_result == result
    assert saved_dataset["parent_raw_sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("method,filename,sensors,rows", [
    ("ert_ohm", "slagdump.ohm", 38, 222), ("traveltime_sgt", "koenigsee.sgt", 63, 714)])
def test_actual_owned_profile_execution(make_harness, method, filename, sensors, rows):
    configured = os.environ.get("GEOPHYSICS_PROFILE_TEST_PYTHON")
    root = os.environ.get("GEOPHYSICS_LOCAL_DATA_ROOT")
    if not configured or not root:
        pytest.skip("explicit native interpreter and original-field external data root required")
    original = Path(root)/"data/downloads/pygimli"/filename
    if not original.is_file():
        pytest.skip("rights-controlled original missing")
    raw = original.read_bytes()
    harness = profile_harness(make_harness, python=Path(configured))
    project, asset, dataset, meta = owned_dataset(harness, raw, method, sensors, rows)
    base = f"/api/projects/{project['id']}/jobs"
    created = harness.request("POST", base, json={"dataset_id": dataset["dataset_id"],
                              "method_id": meta["method"], "parameters": {}})
    assert created.status_code == 202, created.text
    job_id = created.json()["job_id"]
    assert asyncio.run(run_one(harness.settings)) == job_id
    state = harness.client.get(f"{base}/{job_id}").json()
    assert state["state"] == "succeeded", state["error"]
    result = harness.client.get(state["result_url"]).json()
    assert result["numerical_verdict"] == "passed", result["profile"]["engine_report"].get("inverse_reason")
    assert state["peak_rss_bytes"] > 0 and state["wall_ms"] > 0
    assert result["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert harness.client.get(asset["download_url"]).content == raw
    exported = harness.client.get(f"{base}/{job_id}/export")
    assert exported.status_code == 200
    assert verify_bundle(exported.content)[2] == result


def test_profile_command_uses_fixed_script_and_operator_runtime(tmp_path):
    job = SimpleNamespace(method_id="ert.topographic-profile/v1", id=str(uuid4()),
                          dataset_sha256="1"*64, request_sha256="2"*64,
                          request_json={"parameters": {}})
    command = profile_command(job, tmp_path/"dataset.json", tmp_path/"original.ohm",
                              tmp_path/"result.json", Path(sys.executable))
    assert command[0] == sys.executable
    assert Path(command[2]).name == "process_profile_job.py"
    assert command[-1] == "{}"
    with pytest.raises(ValueError):
        profile_command(job, tmp_path/"dataset", tmp_path/"raw", tmp_path/"result", Path("python"))
    job.request_json["parameters"] = {"executable": "untrusted"}
    with pytest.raises(ValueError):
        profile_command(job, tmp_path/"dataset", tmp_path/"raw", tmp_path/"result", Path(sys.executable))


def test_native_config_is_private_bounded_and_narrowly_cleaned(tmp_path):
    stage = tmp_path / "job"
    config = stage / ".pygimli-config" / "pygimli"
    (config / "pygimli").mkdir(parents=True)
    (config / "config.json").write_bytes(b"{}")
    (stage / "result.json").write_bytes(b"{}")
    (stage / "stderr.txt").write_bytes(b"log")
    assert _stage_bytes(stage) == 7
    unknown = config / "unrecognized.dat"
    unknown.write_bytes(b"preserve")
    with pytest.raises(RuntimeError):
        _stage_bytes(stage)
    with pytest.raises(RuntimeError):
        _clear_known_stage(stage)
    assert unknown.read_bytes() == b"preserve"
    unknown.unlink()  # Exact test-owned file only; not a generalized cleanup.
    _clear_known_stage(stage)
    assert not stage.exists()


def test_actual_running_profile_cancel_preserves_original(make_harness):
    configured, root = os.environ.get("GEOPHYSICS_PROFILE_TEST_PYTHON"), os.environ.get("GEOPHYSICS_LOCAL_DATA_ROOT")
    if not configured or not root:
        pytest.skip("explicit native runtime and external original root required")
    import psutil
    raw = (Path(root)/"data/downloads/pygimli/slagdump.ohm").read_bytes()
    harness = profile_harness(make_harness, python=Path(configured))
    project, asset, dataset, meta = owned_dataset(harness, raw, "ert_ohm", 38, 222)
    base = f"/api/projects/{project['id']}/jobs"
    response = harness.request("POST", base, json={"dataset_id":dataset["dataset_id"],"method_id":meta["method"],"parameters":{}})
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(lambda: asyncio.run(run_one(harness.settings)))
        deadline = time.monotonic()+30
        child = None
        while time.monotonic() < deadline:
            for process in psutil.Process().children(recursive=True):
                try:
                    command = process.cmdline()
                    if any("process_profile_job.py" in argument for argument in command) and job_id in command:
                        child = process
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            if child is not None:
                break
            time.sleep(.05)
        assert child is not None, "actual native profile child was not observed"
        cancelled = harness.request("POST", f"{base}/{job_id}/cancel")
        assert cancelled.status_code == 200 and cancelled.json()["cancel_requested"]
        assert future.result(timeout=30) == job_id
    state = harness.client.get(f"{base}/{job_id}").json()
    assert state["state"] == "cancelled" and state["error"]["code"] == "user_cancelled"
    assert harness.client.get(asset["download_url"]).content == raw
    assert harness.client.get(f"{base}/{job_id}/result").status_code == 409
    assert not (harness.settings.data_dir/".job-staging"/job_id).exists()


@pytest.mark.parametrize("case", ["ERT", "TRAVELTIME"])
def test_real_passed_report_rejects_forged_numerical_verdict(case):
    root = os.environ.get("GEOPHYSICS_PROFILE_JOB_"+case)
    if not root:
        pytest.skip("explicit original native worker browser receipt required")
    packet = json.loads((Path(root)/"bindings.json").read_bytes())
    result = json.loads((Path(root)/"result.json").read_bytes())
    stored = packet["job"]
    job = SimpleNamespace(id=stored["job_id"], dataset_id=stored["dataset_id"],
                          dataset_sha256=stored["dataset_sha256"], method_id=stored["method_id"],
                          request_sha256=stored["request_sha256"], request_json=stored["request"])
    validate_profile_result(result, job)
    changed = deepcopy(result)
    if case == "ERT":
        changed["profile"]["engine_report"]["blocked_validation"]["improvement_vs_homogeneous"] = -.1
    else:
        changed["profile"]["engine_report"]["inverse"]["central_block"]["improved_held_shot_count"] = 0
    body = {key:value for key,value in changed["profile"].items() if key != "content_sha256"}
    changed["profile"]["content_sha256"] = sha256(canonical_bytes(body))
    with pytest.raises(ApiError):
        validate_profile_result(changed, job)


def test_failed_science_retains_diagnostics(tmp_path):
    raw, asset, source, meta = profile_fixture()
    raw = raw.replace(b"1 4 2 3 1\n", b"1 4 2 3 -1\n")
    asset.sha256 = hashlib.sha256(raw).hexdigest()
    asset.byte_count = len(raw)
    meta["source"].update(sha256=asset.sha256, bytes=len(raw))
    dataset = admit(raw, asset, source, meta)
    original = tmp_path / "original.ohm"
    original.write_bytes(raw)
    original_bytes = original.read_bytes()
    input_file = tmp_path / "dataset.json"
    input_bytes = json.dumps(dataset, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    input_file.write_bytes(input_bytes)
    job_id, request_sha = str(uuid4()), "1"*64
    output = tmp_path / "result.json"
    command = [sys.executable, "-B", str(Path(__file__).resolve().parents[2]/"scripts/process_profile_job.py"),
               "--input", str(input_file), "--raw", str(original), "--output", str(output),
               "--job-id", job_id, "--dataset-sha256", hashlib.sha256(input_bytes).hexdigest(),
               "--request-sha256", request_sha, "--method-id", meta["method"], "--parameters", "{}"]
    completed = subprocess.run(command, capture_output=True, timeout=30)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == b""
    result = json.loads(output.read_bytes())
    assert result["numerical_verdict"] == "ineligible"
    assert result["profile"]["engine_report"]["truth"] is None
    assert "inverse" not in result["profile"]["engine_report"]
    assert original.read_bytes() == original_bytes
    job = SimpleNamespace(id=job_id, dataset_id=dataset["dataset_id"],
                          dataset_sha256=hashlib.sha256(input_bytes).hexdigest(), method_id=meta["method"],
                          request_sha256=request_sha, request_json={"parameters": {},
                              "raw_asset_id": asset.id, "raw_sha256": asset.sha256,
                              "profile_child_sha256": result["child_code_sha256"],
                              "profile_code_hashes": result["profile"]["code_hashes"]})
    validate_profile_result(result, job)
    for key, value in (("environment_sha256", "0"*64), ("child_code_sha256", "0"*64),
                       ("execution_lane", "browser"), ("raw_bytes", len(raw)+1)):
        changed = deepcopy(result)
        changed[key] = value
        with pytest.raises(ApiError):
            validate_profile_result(changed, job)
    result["numerical_verdict"] = "passed"
    with pytest.raises(ApiError):
        validate_profile_result(result, job)
    repeated = subprocess.run(command, capture_output=True, timeout=30)
    assert repeated.returncode != 0
    assert json.loads(output.read_bytes())["numerical_verdict"] == "ineligible"
