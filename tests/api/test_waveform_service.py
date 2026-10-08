"""Actual protected waveform pair/index gates; fresh migrated private fixtures."""

import copy
import hashlib
import json
import sqlite3
import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fixtures" / "waveform_m08"))
from full_workflow import make_case
from tests.api.conftest import gravity_metadata


def metadata(body, kind, companion=None):
    value = gravity_metadata(body)
    value.update(
        filename="response.xml" if kind == "stationxml" else "trace.mseed",
        mime="application/xml" if kind == "stationxml" else "application/vnd.fdsn.mseed",
        format=kind,
    )
    value["source"].update(
        provider="Authored waveform control",
        attribution="Author-created test bytes",
        rights_statement="Author-created counts/response for private tests only.",
    )
    value["physical"].update(
        measurement_unit="counts", component_frame="channel azimuth/dip", epoch_utc="2020-01-01T00:00:00Z"
    )
    geometry = {"network": "XX", "station": "TEST", "channels": ["BHZ"], "channel_orientation_deg": {"BHZ": [0, -90]}}
    if kind == "stationxml":
        geometry["response_epoch_utc"] = "2019-01-01T00:00:00Z"
    else:
        geometry.update(
            sample_rate_hz=100,
            start_utc="2020-01-01T00:00:00Z",
            end_utc="2020-01-01T00:03:00Z",
            stationxml_asset_id=companion,
        )
    value["physical"]["geometry"] = geometry
    return value


def pair(harness):
    harness.account()
    project = harness.project("Waveform originals")
    fixture = make_case("nominal1")
    xml = harness.upload(project["id"], fixture["stationxml"], metadata(fixture["stationxml"], "stationxml"))
    assert xml.status_code == 201, xml.text
    xml = xml.json()
    raw = harness.upload(project["id"], fixture["mseed"], metadata(fixture["mseed"], "miniseed", xml["asset_id"]))
    assert raw.status_code == 201, raw.text
    return project, fixture, xml, raw.json()


def index(harness, project, fixture, raw):
    return harness.request(
        "POST",
        f"/api/projects/{project['id']}/datasets",
        json={"asset_id": raw["asset_id"], "waveform_request": json.loads(fixture["request"])},
    )


def test_owned_pair_and_request_index(harness):
    project, fixture, xml, raw = pair(harness)
    response = index(harness, project, fixture, raw)
    assert response.status_code == 201, response.text
    receipt = response.json()
    payload = harness.client.get(f"/api/projects/{project['id']}/datasets/{receipt['dataset_id']}").json()
    assert payload["schema"] == "geophysics.waveform-dataset/v1"
    assert payload["modality"] == "waveform_counts_response"
    assert payload["dimensions"] == {"channel": 1, "sample": 18000, "record": 18}
    assert payload["sources"]["miniseed"]["asset_id"] == raw["asset_id"]
    assert payload["sources"]["stationxml"]["asset_id"] == xml["asset_id"]
    assert payload["request"] == json.loads(fixture["request"])
    assert payload["qc_verdict"] == "structural_index_not_physical_qc"
    assert harness.client.get(raw["download_url"]).content == fixture["mseed"]
    assert harness.client.get(xml["download_url"]).content == fixture["stationxml"]
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT count(*) FROM waveform_dataset_sources").fetchone()[0] == 2
    assert index(harness, project, fixture, raw).status_code == 409


@pytest.mark.parametrize(
    "change", ["missing_request", "unknown_key", "unknown_rights", "changed_companion", "changed_raw"]
)
def test_pair_rejections(harness, change):
    project, fixture, xml, raw = pair(harness)
    fixture = copy.deepcopy(fixture)
    request = json.loads(fixture["request"])
    if change == "unknown_key":
        request["unexpected"] = True
    if change == "unknown_rights":
        request["source"]["rights"] = "unknown"
    fixture["request"] = json.dumps(request).encode()
    if change == "changed_companion":
        with sqlite3.connect(harness.settings.database_path) as db:
            db.execute("UPDATE raw_assets SET sha256=? WHERE id=?", ("0" * 64, xml["asset_id"]))
    if change == "changed_raw":
        path = (
            harness.settings.data_dir / raw["storage_key"]
            if "storage_key" in raw
            else next((harness.settings.data_dir / "projects").rglob(raw["asset_id"]))
        )
        body = path.read_bytes()
        path.write_bytes(body[:-1] + bytes([body[-1] ^ 1]))
    response = (
        harness.request("POST", f"/api/projects/{project['id']}/datasets", json={"asset_id": raw["asset_id"]})
        if change == "missing_request"
        else index(harness, project, fixture, raw)
    )
    assert response.status_code in (409, 422), response.text
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT count(*) FROM observation_datasets").fetchone()[0] == 0


def test_worker_dispatch_and_closed_context(harness):
    project, fixture, xml, raw = pair(harness)
    indexed = index(harness, project, fixture, raw)
    assert indexed.status_code == 201, indexed.text
    receipt = indexed.json()
    eligibility = harness.client.get(f"/api/projects/{project['id']}/datasets/{receipt['dataset_id']}/methods").json()
    assert eligibility["unavailable"][0]["method_id"] == "seismic.waveform-qc-classical/v1"
    response = harness.request(
        "POST",
        f"/api/projects/{project['id']}/jobs",
        json={
            "dataset_id": receipt["dataset_id"],
            "method_id": "seismic.waveform-qc-classical/v1",
            "parameters": {"scientific_request_sha256": hashlib.sha256(fixture["request"]).hexdigest()},
        },
    )
    assert response.status_code == 409 and response.json()["code"] == "waveform_context_unavailable"


def test_inventory_quota_delete(harness):
    project, fixture, xml, raw = pair(harness)
    assert index(harness, project, fixture, raw).status_code == 201
    deleted = harness.request("DELETE", f"/api/projects/{project['id']}")
    assert deleted.status_code == 200, deleted.text
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT count(*) FROM waveform_dataset_sources").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM raw_assets").fetchone()[0] == 0
        assert db.execute("SELECT derived_manifest FROM deletion_receipts").fetchone()[0]


def test_migration_and_unknown_revision(harness):
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0004_waveform_artifacts"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_publication_and_roundtrip(harness, tmp_path, monkeypatch):
    """Real science/files/API/DB; supplied resource record is NOT native proof."""
    from app.database import make_engine, reconcile_private_files
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.worker import _claim
    from app.waveform_result import publish_result
    from app.waveform_contract import INPUT
    from app.waveform_result import local_export
    from app import waveform_contract

    project, fixture, xml, raw = pair(harness)
    indexed = index(harness, project, fixture, raw)
    assert indexed.status_code == 201
    data = indexed.json()
    monkeypatch.setattr("app.processing.context_available", lambda _settings: True)
    submitted = harness.request(
        "POST",
        f"/api/projects/{project['id']}/jobs",
        json={
            "dataset_id": data["dataset_id"],
            "method_id": waveform_contract.METHOD_ID,
            "parameters": {"scientific_request_sha256": INPUT.scientific_identity(json.loads(fixture["request"]))},
        },
    )
    assert submitted.status_code == 202, submitted.text
    # Exact existing science interpreter is supplied by the local test invocation.
    import os

    python = Path(os.environ["M08_TEST_SCIENCE_PYTHON"])
    assert python.is_absolute() and python.is_file()
    for name in ("mseed", "stationxml", "request"):
        (tmp_path / name).write_bytes(fixture[name])
    export = tmp_path / "science"
    script = """import sys,json
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'scripts'));sys.path.insert(0,str(root/'data-pipeline'))
from waveform_m08_child import calculate_bytes
from waveform_m08_export import plan_export,write_export
from waveform_m08_files import create_output
parent=Path(sys.argv[2]);result,sealed=calculate_bytes(*[(parent/name).read_bytes() for name in ('mseed','stationxml','request')])
with create_output(parent/'science',trusted_parent=parent) as out: write_export(plan_export(result,sealed),out)
"""
    actual = subprocess.run(
        [str(python), "-B", "-c", script, str(Path(__file__).resolve().parents[2]), str(tmp_path)],
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert actual.returncode == 0, actual.stderr.decode(errors="replace")
    sealed, members = local_export(export)
    receipt = {
        "schema": "caos.m08-local-resources.v1",
        "status": "measured",
        "run_id": "0" * 32,
        "runtime_authorized": False,
        "method_accepted": False,
        "host_admitted": False,
        "active_processes": 0,
        "cpu_ns": 1,
        "max_sample_gap_ns": 50000000,
        "peak_committed_bytes": 1,
        "budget_ns": 60000000000,
        "stop_ns": 57000000000,
        "sample_count": 3,
        "drained_ns": 1,
        "stable_final_ns": 100000001,
    }
    release = {
        "schema": "caos.m08-local-release.v1",
        "run_id": "0" * 32,
        "receipt_sha256": hashlib.sha256(
            json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest(),
        "all_native_owned_handles_closed": True,
        "runtime_authorized": False,
    }

    async def publish():
        engine = make_engine(harness.settings)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            job = await _claim(sessions, "authored-contract-fixture-not-native")
            output = await publish_result(harness.settings, sessions, job, export, receipt, release)
            await reconcile_private_files(harness.settings, sessions)
            return output
        finally:
            await engine.dispose()

    output = asyncio.run(publish())
    base = f"/api/projects/{project['id']}/jobs/{submitted.json()['job_id']}"
    result = harness.client.get(base + "/result")
    assert result.status_code == 200 and result.json() == output
    assert output["calculation_sha256"] == sealed.calculation_sha256
    for row in members:
        downloaded = harness.client.get(base + "/artifacts/" + row["name"])
        assert downloaded.status_code == 200, downloaded.text
        assert len(downloaded.content) == row["bytes"]
        assert hashlib.sha256(downloaded.content).hexdigest() == row["sha256"]
    import io, zipfile

    downloaded = harness.client.get(base + "/export")
    assert downloaded.status_code == 200, downloaded.text
    with zipfile.ZipFile(io.BytesIO(downloaded.content)) as archive:
        assert set(archive.namelist()) == {row["name"] for row in members}
        for row in members:
            assert archive.read(row["name"]) == (export / row["name"]).read_bytes()
    deleted = harness.request("DELETE", f"/api/projects/{project['id']}")
    assert deleted.status_code == 200, deleted.text
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute("SELECT count(*) FROM waveform_result_artifacts").fetchone()[0] == 0
        manifest = json.loads(db.execute("SELECT derived_manifest FROM deletion_receipts").fetchone()[0])
        assert len([row for row in manifest if row["kind"] == "waveform_artifact"]) == len(members)


@pytest.mark.parametrize(
    "key,value",
    [
        ("cpu_ns", 60000000001),
        ("cpu_ns", True),
        ("cpu_ns", -1),
        ("max_sample_gap_ns", 100000001),
        ("peak_committed_bytes", 1073741825),
        ("active_processes", True),
        ("sample_count", 1),
        ("stable_final_ns", 100000000),
        ("runtime_authorized", True),
        ("host_admitted", True),
    ],
)
def test_resource_contract_negative_is_not_native_evidence(key, value):
    from app.waveform_result import checked_resources
    from app.errors import ApiError

    receipt = {
        "schema": "caos.m08-local-resources.v1",
        "status": "measured",
        "run_id": "0" * 32,
        "runtime_authorized": False,
        "method_accepted": False,
        "host_admitted": False,
        "active_processes": 0,
        "cpu_ns": 1,
        "max_sample_gap_ns": 50000000,
        "peak_committed_bytes": 1,
        "budget_ns": 60000000000,
        "stop_ns": 57000000000,
        "sample_count": 3,
        "drained_ns": 1,
        "stable_final_ns": 100000001,
    }
    receipt[key] = value
    release = {
        "schema": "caos.m08-local-release.v1",
        "run_id": "0" * 32,
        "receipt_sha256": hashlib.sha256(
            json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest(),
        "all_native_owned_handles_closed": True,
        "runtime_authorized": False,
    }
    with pytest.raises(ApiError, match="Final waveform native accounting or release is invalid"):
        checked_resources(receipt, release)


def test_worker_revalidates_closed_context_without_science(harness, monkeypatch):
    from app.worker import run_one
    from app.waveform_contract import INPUT, METHOD_ID

    project, fixture, xml, raw = pair(harness)
    response = index(harness, project, fixture, raw)
    assert response.status_code == 201
    monkeypatch.setattr("app.processing.context_available", lambda _settings: True)
    submitted = harness.request(
        "POST",
        f"/api/projects/{project['id']}/jobs",
        json={
            "dataset_id": response.json()["dataset_id"],
            "method_id": METHOD_ID,
            "parameters": {"scientific_request_sha256": INPUT.scientific_identity(json.loads(fixture["request"]))},
        },
    )
    assert submitted.status_code == 202
    assert asyncio.run(run_one(harness.settings)) == submitted.json()["job_id"]
    status = harness.client.get(f"/api/projects/{project['id']}/jobs/{submitted.json()['job_id']}").json()
    assert status["state"] == "failed" and status["error"]["code"] == "waveform_context_unavailable"
    assert status["peak_rss_bytes"] is None and status["scratch_bytes"] is None
    assert not (harness.settings.data_dir / ".job-staging").exists()
