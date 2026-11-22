"""Actual owned-worker positives; never substitute resource-contract doubles."""
import asyncio
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile

import pytest

from tests.api.test_waveform_service import metadata, make_case

ROOT = Path(__file__).resolve().parents[2]


def actual_metadata(body, kind, fixture, request, companion=None):
    from app.waveform_contract import INPUT
    value = metadata(body, kind, companion)
    records = INPUT.scan_miniseed(fixture["mseed"], request)
    fs = records[0]["sample_rate_hz"]
    dto = INPUT.scan_stationxml(fixture["stationxml"])
    selected = []
    for channel in request["channels"]:
        row, reasons = INPUT.resolve_channel(dto, tuple(channel[k] for k in ("network","station","location","channel")),
            INPUT.utc_us(request["conditioning_start_utc"]), INPUT.utc_us(request["conditioning_end_utc"]), fs)
        assert not reasons
        selected.append(row)
    first = request["channels"][0]
    geometry = {"network":first["network"], "station":first["station"],
                "channels":[row["channel"] for row in request["channels"]],
                "channel_orientation_deg":{row["code"]:[row["values"]["Azimuth"],row["values"]["Dip"]] for row in selected}}
    if kind=="stationxml":
        # StationXML dates are UTC even when the provider omits the literal Z.
        # Canonicalize the declared envelope only; indexed original bytes stay exact.
        epoch = datetime.fromisoformat(selected[0]["start"].replace("Z", "+00:00"))
        geometry["response_epoch_utc"] = epoch.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    else:
        geometry.update(sample_rate_hz=fs, start_utc=request["conditioning_start_utc"],
                        end_utc=request["conditioning_end_utc"], stationxml_asset_id=companion)
    value["physical"].update(coordinate_reference="epsg", epsg=4326, axis_order="lon_lat", horizontal_unit="degree",
                            horizontal_datum="WGS84", vertical_datum="Provider elevation datum unspecified",
                            epoch_utc=request["conditioning_start_utc"], geometry=geometry)
    value["source"].update(provider="SCEDC original private acquisition" if request["source"]["kind"]=="provider" else "Authored waveform control",
                           citation=request["source"]["citation"], attribution=request["source"]["citation"],
                           rights_statement="User-authorized private processing; no raw redistribution authority inferred.")
    return value


@pytest.mark.skipif(os.environ.get("M08_RUN_NATIVE") != "1", reason="Explicit selected SDK/native context required")
@pytest.mark.parametrize("case", ["nominal1", "upper3", "ridgecrest-original", "ridgecrest-original-aligned"])
def test_actual_owned_worker_full_processing(harness, case):
    from app.worker import run_one
    from app.waveform_contract import INPUT, METHOD_ID

    python = os.environ["M08_TEST_SCIENCE_PYTHON"]
    revision = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    environment = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "SYSTEMDRIVE"}}
    environment.update(TMP=str(harness.settings.data_dir), TEMP=str(harness.settings.data_dir),
                       TMPDIR=str(harness.settings.data_dir), PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    qualified = subprocess.run([
        python, "-B", str(ROOT / "scripts/qualify_waveform_m08.py"),
        "--data-root", str(harness.settings.data_dir),
        "--abi-executable", os.environ["M08_ABI_EXECUTABLE"],
        "--abi-sha256", os.environ["M08_ABI_SHA256"], "--review", os.environ["M08_NATIVE_REVIEW"],
        "--source-revision", revision,
    ], capture_output=True, timeout=120, env=environment)
    assert qualified.returncode == 0, qualified.stderr.decode(errors="replace")
    request = None
    if case.startswith("ridgecrest-original"):
        spec = __import__("importlib.util", fromlist=["util"])
        module_spec = spec.spec_from_file_location("m08_field_selection", ROOT / "tests/data/test_waveform_ridgecrest.py")
        field = spec.module_from_spec(module_spec)
        module_spec.loader.exec_module(field)
        mseed, xml = field.bounded_original("miniseed.raw"), field.bounded_original("stationxml.raw")
        request = field.original_request()
        if case == "ridgecrest-original-aligned":
            # Separate explicit request, not relabelling the frozen off-grid
            # request. Same originals/NSLC/configuration, no interpolation.
            # First sample at/after the old start is exactly +8300 microseconds.
            records = INPUT.scan_miniseed(mseed, request)
            first = records[0]["start_us"]
            step = 1000000 // records[0]["sample_rate_hz"]
            shift = (first - INPUT.utc_us(request["conditioning_start_utc"])) % step
            assert shift == 8300
            for key in ("conditioning_start_utc", "conditioning_end_utc", "analysis_start_utc", "analysis_end_utc"):
                request[key] = INPUT.format_utc(INPUT.utc_us(request[key]) + shift)
            request = INPUT.validate_request(request)
        fixture = {"mseed": mseed, "stationxml": xml, "request": json.dumps(request).encode()}
    else:
        fixture = make_case(case)
        request = json.loads(fixture["request"])
    harness.account()
    project = harness.project("Actual worker " + case)
    response = harness.upload(project["id"], fixture["stationxml"], actual_metadata(fixture["stationxml"], "stationxml", fixture, request))
    assert response.status_code == 201, response.text
    xml_asset = response.json()
    response = harness.upload(project["id"], fixture["mseed"], actual_metadata(fixture["mseed"], "miniseed", fixture, request, xml_asset["asset_id"]))
    assert response.status_code == 201, response.text
    raw = response.json()
    response = harness.request("POST", f"/api/projects/{project['id']}/datasets",
                               json={"asset_id": raw["asset_id"], "waveform_request": request})
    assert response.status_code == 201, response.text
    dataset = response.json()
    response = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
        "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID,
        "parameters": {"scientific_request_sha256": INPUT.scientific_identity(request)},
    })
    assert response.status_code == 202, response.text
    job = response.json()
    assert asyncio.run(run_one(harness.settings)) == job["job_id"]
    base = f"/api/projects/{project['id']}/jobs/{job['job_id']}"
    status = harness.client.get(base).json()
    assert status["state"] == "succeeded", status
    result = harness.client.get(base + "/result")
    assert result.status_code == 200, result.text
    result = result.json()
    if case == "ridgecrest-original":
        assert result["scientific_status"] == "qc_only", result["calculation"]
        assert result["calculation"]["qc"]["reasons"] == ["gap"]
        assert result["calculation"]["candidates"] is None
        assert {d["name"] for d in result["calculation"]["array_descriptors"]} == {"counts"}
    else:
        assert result["scientific_status"] == "computed", result["calculation"]
    assert result["resources"]["memory_kind"] == "windows_job_committed"
    assert result["resources"]["host_admitted"] is False
    assert status["peak_rss_bytes"] is None
    assert not list((harness.settings.data_dir / ".job-staging").iterdir())
    # A second real worker startup audits the committed files before returning idle.
    assert asyncio.run(run_one(harness.settings)) is None
    for original, content in ((raw, fixture["mseed"]), (xml_asset, fixture["stationxml"])):
        assert harness.client.get(original["download_url"]).content == content
    export = harness.client.get(base + "/export")
    assert export.status_code == 200, export.text
    with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
        assert sorted(archive.namelist()) == sorted(row["name"] for row in result["members"])
        for row in result["members"]:
            content = archive.read(row["name"])
            assert len(content) == row["bytes"]
            assert hashlib.sha256(content).hexdigest() == row["sha256"]
            member = harness.client.get(base + "/artifacts/" + row["name"])
            assert member.status_code == 200 and member.content == content
    assert harness.request("DELETE", f"/api/projects/{project['id']}").status_code == 200
