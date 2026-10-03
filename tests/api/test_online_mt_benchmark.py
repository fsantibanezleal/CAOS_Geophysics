"""Opt-in local admission matrix; run explicitly, never from product CI."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from app.mt_contract import EDI_SOURCE_LIMIT, M05_ID, M06_ID
from app.processing_contract import canonical_bytes
from app.worker import run_one
from tests.api.test_online_mt import NATIVE, ROOT, edi_metadata


MU0 = 4 * np.pi * 1e-7


def upper_source(frequency_count=64, *, pad_to_limit=False) -> bytes:
    """Independent reflection formula; comment padding exercises the exact byte cap."""
    f = np.geomspace(100, .01, frequency_count)
    omega = 2 * np.pi * f
    bottom = (1 + 1j) * np.sqrt(omega * MU0 * 12 / 2)
    top = (1 + 1j) * np.sqrt(omega * MU0 * 120 / 2)
    propagation = (1 + 1j) * np.sqrt(omega * MU0 / (2 * 120))
    reflection = (bottom - top) / (bottom + top) * np.exp(-2 * propagation * 350)
    z = top * (1 + reflection) / (1 - reflection)
    native_factor = MU0 * 1000
    sigma = .025 * abs(z)
    tensor = np.zeros((len(f), 2, 2), dtype=complex)
    tensor[:, 0, 1], tensor[:, 1, 0] = z / native_factor, -z / native_factor
    variance = 2 * (sigma / native_factor) ** 2
    template = NATIVE.read_text(encoding="utf-8")
    template = template.replace("HALFSPACE_100_NATIVE", f"UPPER_{frequency_count}")
    template = template.replace("NFREQ=24", f"NFREQ={frequency_count}")

    def block(name, values, *, rotated=True):
        header = f">{name}" + (" ROT=ZROT" if rotated else "") + f" // {len(values)}"
        rows = [" ".join(f"{v:.16e}" for v in values[i:i + 5]) for i in range(0, len(values), 5)]
        return "\n".join((header, *rows)) + "\n"

    blocks = {"FREQ": block("FREQ", f, rotated=False),
              "ZROT": block("ZROT", np.zeros(len(f)), rotated=False)}
    for component, i, j in (("XX", 0, 0), ("XY", 0, 1), ("YX", 1, 0), ("YY", 1, 1)):
        blocks["Z" + component + "R"] = block("Z" + component + "R", tensor[:, i, j].real)
        blocks["Z" + component + "I"] = block("Z" + component + "I", tensor[:, i, j].imag)
        blocks["Z" + component + ".VAR"] = block("Z" + component + ".VAR", variance)
    for name, replacement in blocks.items():
        pattern = rf"(?ms)^>{re.escape(name)}\b.*?(?=^>)"
        template, changed = re.subn(pattern, lambda _match: replacement, template, count=1)
        assert changed == 1, name
    encoded = template.encode("utf-8")
    if pad_to_limit:
        padding_size = EDI_SOURCE_LIMIT - len(encoded)
        assert padding_size >= 2
        padding = b"!" + b"x" * (padding_size - 2) + b"\n"
        encoded = encoded.replace(b">END", padding + b">END", 1)
        assert len(encoded) == EDI_SOURCE_LIMIT
    return encoded


@pytest.mark.skipif(os.environ.get("GEOPHYSICS_RUN_LOCAL_MT_BENCHMARK") != "1",
                    reason="explicit local benchmark only")
def test_local_nominal_upper_malformed_admission(make_harness):
    import asyncio
    import platform

    harness = make_harness(mt_online_enabled=True)
    harness.account()
    rows = []
    artifacts = harness.settings.data_dir.parent / "mt-receipts"
    artifacts.mkdir()

    def upload(body: bytes, station: str, name: str, count=24):
        project = harness.project(name)
        meta = edi_metadata(body, station=station, count=count)
        uploaded = harness.upload(project["id"], body, meta)
        assert uploaded.status_code == 201, uploaded.text
        created = harness.request("POST", f"/api/projects/{project['id']}/datasets",
                                  json={"asset_id": uploaded.json()["asset_id"]})
        assert created.status_code == 201, created.text
        return project, created.json()

    def run(label, project, dataset, method, parameters):
        response = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
            "dataset_id": dataset["dataset_id"], "method_id": method, "parameters": parameters,
        })
        assert response.status_code == 202, response.text
        start = time.perf_counter()
        assert asyncio.run(run_one(harness.settings)) == response.json()["job_id"]
        elapsed = (time.perf_counter() - start) * 1000
        job = harness.client.get(f"/api/projects/{project['id']}/jobs/{response.json()['job_id']}").json()
        artifact = None
        if job["state"] == "succeeded":
            exported = harness.client.get(f"/api/projects/{project['id']}/jobs/{job['job_id']}/export")
            assert exported.status_code == 200
            (artifacts / (label + ".zip")).write_bytes(exported.content)
            artifact = {"path": label + ".zip", "sha256": hashlib.sha256(exported.content).hexdigest(),
                        "bytes": len(exported.content)}
        rows.append({"label": label, "method_id": method, "state": job["state"],
                     "job_id": job["job_id"], "dataset_id": job["dataset_id"],
                     "dataset_sha256": job["dataset_sha256"], "request_sha256": job["request_sha256"],
                     "request": job["request"], "preflight": job["preflight"], "bundle": artifact,
                     "error_code": job["error"]["code"] if job["error"] else None,
                     "worker_wall_ms": job["wall_ms"], "end_to_end_ms": round(elapsed),
                     "peak_rss_bytes": job["peak_rss_bytes"],
                     "peak_scratch_bytes": job["scratch_bytes"],
                     "result_sha256": job["result_sha256"]})
        return job

    nominal_bytes = NATIVE.read_bytes()
    nominal, data = upload(nominal_bytes, "HALFSPACE_100_NATIVE", "nominal-24")
    qc = run("nominal-m05", nominal, data, M05_ID, {})
    assert qc["state"] == "succeeded"
    inverse = run("nominal-m06-20", nominal, data, M06_ID, {
        "qc_job_id": qc["job_id"], "thickness_m": [], "initial_ohm_m": [40],
        "beta": .001, "bootstrap_samples": 20, "seed": 71401,
    })
    assert inverse["state"] == "succeeded"

    upper_bytes = upper_source(pad_to_limit=True)
    upper, upper_data = upload(upper_bytes, "UPPER_64", "upper-64", count=64)
    upper_qc = run("upper-m05", upper, upper_data, M05_ID, {})
    assert upper_qc["state"] == "succeeded"
    upper_inverse = run("upper-m06-40", upper, upper_data, M06_ID, {
        "qc_job_id": upper_qc["job_id"], "thickness_m": [350],
        "initial_ohm_m": [100, 100], "beta": .001, "bootstrap_samples": 40, "seed": 71402,
    })
    assert upper_inverse["state"] == "succeeded"
    upper_result = harness.client.get(upper_inverse["result_url"]).json()
    np.testing.assert_allclose(upper_result["inverse"]["methods"]["mt-lm"]["model"],
                               [120, 12], rtol=.005)

    qc_upper_bytes = upper_source(512, pad_to_limit=True)
    qc_upper, qc_upper_data = upload(qc_upper_bytes, "UPPER_512", "upper-qc-512", count=512)
    qc_max = run("upper-m05-512-5mib", qc_upper, qc_upper_data, M05_ID, {})
    assert qc_max["state"] == "succeeded"
    denied = harness.request("POST", f"/api/projects/{qc_upper['id']}/jobs", json={
        "dataset_id": qc_upper_data["dataset_id"], "method_id": M06_ID,
        "parameters": {"qc_job_id": qc_max["job_id"], "thickness_m": [350],
                       "initial_ohm_m": [100, 100], "beta": .001},
    })
    assert denied.status_code == 422 and denied.json()["code"] == "method_ineligible"
    oversized = upper_bytes + b"\n"
    oversized_meta = edi_metadata(oversized, station="UPPER_64", count=64)
    oversized_upload = harness.upload(upper["id"], oversized, oversized_meta)
    assert oversized_upload.status_code == 413

    malformed_bytes = nominal_bytes.replace(b">ZXYR", b">UNKNOWN", 1)
    malformed, bad_data = upload(malformed_bytes, "HALFSPACE_100_NATIVE", "malformed")
    bad = run("malformed-m05", malformed, bad_data, M05_ID, {})
    assert bad["state"] == "failed" and bad["error"]["code"] == "processing_failed"
    receipt = {
        "schema": "geophysics.mt-admission-benchmark/v1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution": "authenticated TestClient API and actual singleton worker; no public listener",
        "host_activation_asserted": False,
        "isolated_environment": "include-system-site-packages = false" in
                                (Path(sys.prefix) / "pyvenv.cfg").read_text(encoding="utf-8"),
        "dependencies": {package: importlib.metadata.version(package) for package in (
            "fastapi", "fastapi-users", "SQLAlchemy", "numpy", "scipy", "mt-metadata",
            "pandas", "matplotlib", "xarray", "psutil")},
        "code_sha256": {str(path): hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in (
            "app/worker.py", "app/mt_compute.py", "app/mt_contract.py", "app/mt_bundle.py",
            "data-pipeline/edi.py", "data-pipeline/electromagnetics.py")},
        "system": platform.platform(), "python": platform.python_version(),
        "nominal_sha256": hashlib.sha256(nominal_bytes).hexdigest(),
        "upper_sha256": hashlib.sha256(upper_bytes).hexdigest(),
        "qc_upper_sha256": hashlib.sha256(qc_upper_bytes).hexdigest(),
        "nominal_bytes": len(nominal_bytes), "upper_bytes": len(upper_bytes),
        "qc_upper_bytes": len(qc_upper_bytes),
        "malformed_bytes": len(malformed_bytes), "malformed_sha256": hashlib.sha256(malformed_bytes).hexdigest(),
        "admission_rejections": [
            {"label": "m06-over-64-frequencies", "status": denied.status_code, "code": denied.json()["code"]},
            {"label": "source-over-5mib", "status": oversized_upload.status_code,
             "code": oversized_upload.json()["code"]}],
        "rows": rows,
    }
    (artifacts / "benchmark.json").write_bytes(canonical_bytes(receipt))
    print("MT_LOCAL_BENCHMARK=" + json.dumps(receipt, sort_keys=True))
