"""Loopback QA only: real API, migrated isolated DB and separately controlled worker.

No canonical datasets are read/written; no solver responses are mocked. The worker
starts only when a test requests it, so queued cancellation is deterministic.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import psutil
import uvicorn
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.config import Settings
from app.server import create_app

ROOT = Path(__file__).resolve().parents[2]
DIST = (ROOT / "frontend" / "dist").resolve()
ROUTES = {"", "app", "introduction", "methodology", "implementation", "experiments", "benchmark"}

def main() -> None:
    if not (DIST / "index.html").is_file():
        raise RuntimeError("Build frontend: npm run build:single-origin")
    parent = Path(os.environ.get("GEOPHYSICS_QA_ROOT", Path(tempfile.gettempdir()) / "caos-geophysics-processing-qa")).expanduser().resolve()
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_relative_to(ROOT):
        raise RuntimeError("QA root must be outside the repository checkout")
    port = int(os.environ.get("GEOPHYSICS_QA_PORT", "8876"))
    origin = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="run-", dir=parent) as temporary:
        private = Path(temporary) / "private"
        private.mkdir()
        db = private / "api.sqlite3"
        os.environ["GEOPHYSICS_DB_PATH"] = str(db)
        os.environ["GEOPHYSICS_DATA_DIR"] = str(private)
        command.upgrade(Config(str(ROOT / "app" / "alembic.ini")), "head")
        messages: list[str] = []
        qa_m02 = os.environ.get("GEOPHYSICS_QA_M02") == "1"
        gravity_python = Path(os.environ.get(
            "GEOPHYSICS_GRAVITY_L2_PYTHON",
            ROOT / ".venv-gravity" / "Scripts" / "python.exe" if os.name == "nt" else sys.executable,
        )).resolve()
        if qa_m02 and (not gravity_python.is_absolute() or not gravity_python.is_file()):
            raise RuntimeError("QA M02 requires an explicit installed gravity child interpreter")
        if qa_m02:
            os.environ["GEOPHYSICS_GRAVITY_L2_ONLINE_ENABLED"] = "1"
            os.environ["GEOPHYSICS_GRAVITY_L2_PYTHON"] = str(gravity_python)
        worker: subprocess.Popen | None = None
        def stop_worker() -> None:
            nonlocal worker
            if worker is not None and worker.poll() is None:
                process = psutil.Process(worker.pid)
                children = process.children(recursive=True)
                for child in children:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                worker.terminate()
                psutil.wait_procs(children, timeout=5)
                worker.wait(timeout=10)
            worker = None

        async def capture(_address: str, _subject: str, body: str) -> None:
            messages.append(body)

        server: uvicorn.Server | None = None

        app = create_app(Settings(data_dir=private, db_path=db, auth_mode="email",
            auth_secret="qa-only-processing-not-deployment-secret-123456789",
            public_origin=origin, cookie_secure=False,
            gravity_l2_online_enabled=qa_m02), capture)
        original_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def lifespan(application):
            async with original_lifespan(application):
                try:
                    yield
                finally:
                    stop_worker()
        app.router.lifespan_context = lifespan

        @app.get("/__qa/processing")
        async def identity():
            return {"harness": "real-processing-api-v1", "worker_started": worker is not None,
                    "m02_enabled": qa_m02}

        @app.get("/__qa/m02-prism-survey")
        async def m02_prism_survey():
            if not qa_m02:
                raise HTTPException(404, "M02 QA lane is disabled")
            import hashlib
            import choclo
            rows = ["station,x,y,z,anomaly,sigma,line_id"]
            for j in range(12):
                for i in range(12):
                    x, y, z = (i - 5.5) * 100.0, (j - 5.5) * 100.0, 100.0
                    observed = choclo.prism.gravity_u(x, y, z, -50.0, 50.0, -50.0, 50.0,
                                                        -200.0, -100.0, 500.0) * 1e5
                    rows.append(f"S{j:02d}_{i:02d},{x:.1f},{y:.1f},{z:.1f},{observed:.17g},0.1,L{j:02d}")
            body = ("\n".join(rows) + "\n").encode("utf-8")
            digest = hashlib.sha256(body).hexdigest()
            metadata = {
                "filename": "authored-prism-m02-control.csv", "mime": "text/csv", "format": "gravity_csv",
                "source": {"provider": "Loopback M02 QA", "citation": "Authored Choclo prism control",
                    "rights_statement": "Authored synthetic QA input; private test storage only.",
                    "rights_decision": "mirror", "private_storage_permission": "attested",
                    "attribution": "CAOS local QA", "expected_bytes": len(body), "expected_sha256": digest},
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
            return {"csv": body.decode("utf-8"), "metadata": metadata,
                    "sha256": digest, "bytes": len(body), "oracle": "Choclo prism gravity_u"}

        @app.get("/__qa/mail/latest")
        async def latest_mail():
            if not messages:
                raise HTTPException(404, "No captured mail")
            token = re.search(r"(?:Verification|Password reset) token: ([^\n]+)", messages[-1])
            return {"token": token.group(1) if token else None}

        @app.post("/__qa/worker/start")
        async def start_worker():
            nonlocal worker
            if worker is None:
                worker = subprocess.Popen([sys.executable, "-m", "app.worker"], cwd=ROOT,
                    env=os.environ.copy(), creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            if worker.poll() is not None:
                raise HTTPException(500, "QA worker exited")
            return {"started": True}

        @app.post("/__qa/worker/stop")
        async def stop_qa_worker():
            stop_worker()
            return {"stopped": True}

        @app.post("/__qa/shutdown")
        async def shutdown_qa_server():
            nonlocal server
            stop_worker()
            if server is None:
                raise HTTPException(503, "QA server is not initialized")
            server.should_exit = True
            return {"shutting_down": True}

        @app.get("/{path:path}")
        async def browser_files(path: str):
            candidate = (DIST / path).resolve()
            if candidate.is_relative_to(DIST) and candidate.is_file():
                return FileResponse(candidate)
            if path.rstrip("/") in ROUTES:
                return FileResponse(DIST / "index.html")
            raise HTTPException(404, "Not found")

        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        server.run()

if __name__ == "__main__":
    main()
