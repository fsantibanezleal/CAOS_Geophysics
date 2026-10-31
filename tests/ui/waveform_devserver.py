"""External-root loopback QA: real migrated API and actual native waveform worker.

Not a deployment entry point. No source/solver response is mocked; fixtures are
generated authored MiniSEED/StationXML controls, never raw provider mirrors.
"""
from __future__ import annotations

import base64
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import uvicorn
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.config import Settings, external_storage_path
from app.server import create_app
from tests.api.test_waveform_native_workflow import actual_metadata
from tests.api.test_waveform_service import make_case


def main():
    if os.environ.get("GEOPHYSICS_WAVEFORM_QA") != "isolated-loopback-only":
        raise RuntimeError("Explicit isolated waveform QA opt-in required")
    private = external_storage_path(Path(os.environ["GEOPHYSICS_QA_DATA"]), "QA data")
    dist = external_storage_path(Path(os.environ["GEOPHYSICS_QA_DIST"]), "QA build")
    if not (dist / "qa-waveform.html").is_file() or private.exists():
        raise RuntimeError("QA requires built isolated frontend and a NEW external private root")
    private.mkdir(parents=True)
    db = private / "api.sqlite3"
    port = int(os.environ.get("GEOPHYSICS_QA_PORT", "8898"))
    origin = f"http://127.0.0.1:{port}"
    os.environ.update(GEOPHYSICS_DATA_DIR=str(private), GEOPHYSICS_DB_PATH=str(db),
                     PYTHONDONTWRITEBYTECODE="1", TMP=str(private), TEMP=str(private), TMPDIR=str(private))
    command.upgrade(Config(str(ROOT / "app/alembic.ini")), "head")
    revision = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    qualified = subprocess.run([os.environ["M08_TEST_SCIENCE_PYTHON"], "-B", str(ROOT / "scripts/qualify_waveform_m08.py"),
        "--data-root", str(private), "--abi-executable", os.environ["M08_ABI_EXECUTABLE"],
        "--abi-sha256", os.environ["M08_ABI_SHA256"], "--review", os.environ["M08_NATIVE_REVIEW"],
        "--source-revision", revision], cwd=ROOT, capture_output=True, timeout=120)
    if qualified.returncode:
        raise RuntimeError("Selected native context qualification failed")
    messages = []
    worker = None

    async def capture(_address, _subject, body):
        messages.append(body)

    app = create_app(Settings(data_dir=private, db_path=db, auth_mode="email", cookie_secure=False,
        public_origin=origin, auth_secret="isolated-waveform-loopback-test-not-deployment-123456789"), capture)
    original_lifespan = app.router.lifespan_context

    def stop_worker():
        nonlocal worker
        if worker is not None and worker.poll() is None:
            # Only this harness's worker. Closing the observer's sole Job handle
            # provides contained-process kill-on-close; no fleet process scan.
            worker.terminate()
            worker.wait(timeout=15)
        worker = None

    @asynccontextmanager
    async def lifespan(application):
        async with original_lifespan(application):
            try:
                yield
            finally:
                stop_worker()
    app.router.lifespan_context = lifespan

    @app.get("/__qa/waveform")
    async def fixture():
        selected = make_case("nominal1")
        request = json.loads(selected["request"])
        return {"harness": "actual-waveform-native-v1", "request": request,
                "inputs": {role: {"base64": base64.b64encode(selected[key]).decode("ascii"),
                    "metadata": actual_metadata(selected[key], role, selected, request)}
                    for role, key in (("stationxml", "stationxml"), ("miniseed", "mseed"))}}

    @app.get("/__qa/mail/latest")
    async def latest_mail():
        if not messages:
            raise HTTPException(404, "No captured test mail")
        token = re.search(r"Verification token: ([^\n]+)", messages[-1])
        return {"token": token.group(1) if token else None}

    @app.post("/__qa/worker/start")
    async def start_worker():
        nonlocal worker
        if worker is None:
            worker = subprocess.Popen([sys.executable, "-B", "-m", "app.worker"], cwd=ROOT,
                env=os.environ.copy(), creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if worker.poll() is not None:
            raise HTTPException(500, "Actual QA worker exited")
        return {"started": True}

    @app.post("/__qa/worker/stop")
    async def stopped_worker():
        stop_worker()
        return {"stopped": True}

    @app.get("/{path:path}")
    async def static_files(path: str):
        candidate = (dist / path).resolve()
        if candidate.is_relative_to(dist) and candidate.is_file():
            return FileResponse(candidate)
        if path == "":
            return FileResponse(dist / "qa-waveform.html")
        raise HTTPException(404, "Not found")

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
