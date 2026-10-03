"""Explicit actual-Linux-host measurements, never enabled by ordinary CI."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import threading
import time

import psutil
import pytest

from app.mt_contract import M05_ID, M06_ID
from app.processing_contract import canonical_bytes
from app.worker import run_one
from tests.api.test_online_mt import NATIVE, ROOT, complete, submit, upload_dataset


HOST = os.environ.get("GEOPHYSICS_RUN_HOST_ADMISSION") == "1"


def rank95(values):
    return sorted(values)[math.ceil(.95 * len(values)) - 1]


def checked_host():
    assert sys.platform == "linux" and os.geteuid() != 0, "Restricted Linux identity required"
    assert os.environ.get("STATE_DIRECTORY"), "Transient private systemd StateDirectory required"
    assert "include-system-site-packages = false" in (Path(sys.prefix) / "pyvenv.cfg").read_text()


def receipt(path, value):
    with path.open("xb") as output:
        output.write(canonical_bytes(value))


@pytest.mark.skipif(not HOST, reason="explicit actual-host gate only")
def test_nominal_distribution_and_concurrent_reads(make_harness, tmp_path):
    checked_host()
    original = NATIVE.read_bytes()
    rows, reads, available, free, tree_rss = [], [], [], [], []
    halt = threading.Event()

    def monitor():
        while not halt.wait(.05):
            available.append(psutil.virtual_memory().available)
            free.append(psutil.disk_usage(tmp_path).free)
            process = psutil.Process()
            total = process.memory_info().rss
            for child in process.children(recursive=True):
                try:
                    total += child.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
            tree_rss.append(total)

    sampler = threading.Thread(target=monitor, daemon=True)
    sampler.start()
    try:
        for method in (M05_ID, M06_ID):
            # Keep the production 30-jobs/IP/hour admission unchanged. Distinct
            # private stores exercise 20 M05, or 1 QC + 20 M06, not 40 in one bucket.
            harness = make_harness(mt_online_enabled=True)
            harness.account()
            project, _asset, dataset, supplied = upload_dataset(
                harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
            assert supplied == original
            qc_id = None
            if method == M06_ID:
                _screen, qc = complete(harness, submit(harness, project, dataset, M05_ID, {}))
                qc_id = qc["job_id"]
            for attempt in range(20):
                parameters = {} if method == M05_ID else {
                    "qc_job_id": qc_id, "thickness_m": [], "initial_ohm_m": [40],
                    "beta": .001, "bootstrap_samples": 20, "seed": 71401,
                }
                job = submit(harness, project, dataset, method, parameters)
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(lambda: asyncio.run(run_one(harness.settings)))
                    while not future.done():
                        started = time.perf_counter()
                        response = harness.client.get(f"/api/projects/{project['id']}/jobs/{job['job_id']}")
                        reads.append((time.perf_counter() - started) * 1000)
                        assert response.status_code == 200
                        time.sleep(.05)
                    assert future.result() == job["job_id"]
                status = harness.client.get(f"/api/projects/{project['id']}/jobs/{job['job_id']}").json()
                assert status["state"] == "succeeded", status["error"]
                if method == M05_ID:
                    qc_id = job["job_id"]
                else:
                    result = harness.client.get(status["result_url"]).json()
                    assert abs(result["inverse"]["methods"]["mt-lm"]["model"][0] - 100) < .5
                    assert result["truth"] is None
                rows.append({key: status[key] for key in (
                    "job_id", "method_id", "dataset_sha256", "request_sha256", "preflight",
                    "wall_ms", "peak_rss_bytes", "scratch_bytes", "result_sha256")})
            harness.close()
    except BaseException as error:
        receipt(tmp_path / "partial-host-receipt.json", {
            "schema": "geophysics.actual-host-incomplete/v1", "failure_type": type(error).__name__,
            "rows": rows, "application_read_samples": len(reads), "admission_passed": False,
            "minimum_available_host_memory_bytes": min(available) if available else None,
            "minimum_free_disk_bytes": min(free) if free else None,
        })
        raise
    finally:
        halt.set()
        sampler.join(timeout=2)
    summary = {}
    for method in (M05_ID, M06_ID):
        selected = [row for row in rows if row["method_id"] == method]
        limits = selected[0]["preflight"]
        summary[method] = {
            "sample_count": len(selected), "p95_wall_ms": rank95([row["wall_ms"] for row in selected]),
            "p95_rss_bytes": rank95([row["peak_rss_bytes"] for row in selected]),
            "p95_scratch_bytes": rank95([row["scratch_bytes"] for row in selected]), "limits": limits,
        }
    memory, disk = psutil.virtual_memory(), psutil.disk_usage(tmp_path)
    value = {
        "schema": "geophysics.actual-host-nominal/v1", "system": platform.platform(),
        "python": platform.python_version(), "effective_uid": os.geteuid(),
        "public_listener": False, "host_activation_asserted": False,
        "source_sha256": hashlib.sha256(original).hexdigest(),
        "code_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
            "app/worker.py", "app/mt_compute.py", "app/mt_contract.py", "data-pipeline/edi.py",
            "data-pipeline/electromagnetics.py", "tests/api/test_host_admission.py")},
        "rows": rows, "methods": summary,
        "sampler_interval_seconds": .05, "observed_parent_plus_child_peak_rss_bytes": max(tree_rss),
        "minimum_available_host_memory_bytes": min(available), "host_memory_bytes": memory.total,
        "minimum_free_disk_bytes": min(free), "host_disk_bytes": disk.total,
        "application_read_samples": len(reads), "application_read_p95_ms": rank95(reads),
        "application_read_max_ms": max(reads),
        "read_scope": "Authenticated TestClient while real worker child runs; not nginx/TLS/network latency",
        "replication_scope": "Twenty attempts per method on one nominal analytic sounding; not diverse-field throughput",
        "rate_limit_policy": "Unchanged 30 jobs/IP/hour; independent private stores per method (20 or 21 submissions)",
    }
    # Retain all measurements even if an acceptance inequality fails.
    receipt(tmp_path / "nominal-host-receipt.json", value)
    for measured in summary.values():
        limits = measured["limits"]
        assert measured["p95_wall_ms"] < .7 * limits["wall_limit_seconds"] * 1000
        assert measured["p95_rss_bytes"] < .7 * limits["memory_limit_bytes"]
        assert measured["p95_scratch_bytes"] < .7 * limits["scratch_limit_bytes"]
    assert min(available) >= .3 * memory.total
    assert min(free) >= .3 * disk.total
    assert max(tree_rss) < .7 * 2 * 1024**3
    assert rank95(reads) < 1000, "Application read p95 exceeds 1 s harness threshold"


@pytest.mark.skipif(not HOST, reason="explicit actual-host gate only")
def test_real_parent_crash_and_recovery(make_harness, tmp_path):
    checked_host()
    harness = make_harness(mt_online_enabled=True)
    harness.account()
    project, _asset, dataset, _original = upload_dataset(harness, NATIVE, station="HALFSPACE_100_NATIVE", count=24)
    job = submit(harness, project, dataset, M05_ID, {})
    env = {**os.environ, "GEOPHYSICS_DATA_DIR": str(harness.settings.data_dir),
           "GEOPHYSICS_DB_PATH": str(harness.settings.database_path), "GEOPHYSICS_MT_ONLINE_ENABLED": "1"}
    log = tmp_path / "crashed-parent.log"
    child_pids = []
    with log.open("xb") as output:
        parent = subprocess.Popen([sys.executable, "-m", "app.worker"], cwd=ROOT, env=env,
                                  stdout=output, stderr=output, start_new_session=True)
        try:
            deadline = time.monotonic() + 15
            while not child_pids:
                assert parent.poll() is None, log.read_text()
                child_pids = [child.pid for child in psutil.Process(parent.pid).children(recursive=True)
                              if "app.mt_compute" in child.cmdline()]
                assert time.monotonic() < deadline, "Actual scientific child did not start"
                time.sleep(.005)
            os.kill(parent.pid, signal.SIGKILL)
            parent.wait(timeout=5)
            deadline = time.monotonic() + 15
            while any(psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE for pid in child_pids):
                assert time.monotonic() < deadline, "Scientific child survived real parent loss"
                time.sleep(.05)
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=5)
    stage = harness.settings.data_dir / ".job-staging" / job["job_id"]
    # Existing production policy correctly refuses unattended recovery of disputed bytes.
    with pytest.raises(RuntimeError, match="private_recovery_required"):
        asyncio.run(run_one(harness.settings))
    state = harness.client.get(f"/api/projects/{project['id']}/jobs/{job['job_id']}").json()
    assert state["state"] == "failed" and state["error"]["code"] == "worker_interrupted"
    assert state["result_url"] is None
    assert stage.is_dir() and not stage.is_symlink()
    files = {str(path.relative_to(stage)): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in stage.rglob("*") if path.is_file()}
    assert all(not path.is_symlink() for path in stage.rglob("*"))
    preserved = tmp_path / "operator-preserved-interrupted-stage"
    stage.rename(preserved)  # Newly created harness files only, recoverable, no deletion.
    assert files == {str(path.relative_to(preserved)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in preserved.rglob("*") if path.is_file()}
    retry_result, retry = complete(harness, submit(harness, project, dataset, M05_ID, {}))
    assert retry_result["inverse"] is None
    receipt(tmp_path / "crash-host-receipt.json", {
        "schema": "geophysics.actual-host-crash/v1", "parent_pid": parent.pid, "child_pids": child_pids,
        "failed_job_id": job["job_id"], "state": state["state"], "error": state["error"],
        "orphan_alive": False, "operator_review_required": True,
        "preserved_staging_hashes": files, "retry_job_id": retry["job_id"],
        "retry_result_sha256": retry["result_sha256"], "public_activation": False,
    })


def test_host_guide_contract():
    guide = (ROOT / "docs/guides/12_actual_host_admission.md").read_text(encoding="utf-8")
    for term in ("DynamicUser", "StateDirectory", "twenty", "TestClient", "SIGKILL",
                 "operator", "Pages", "70%", "30%", "RLIMIT_AS"):
        assert term in guide
