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
ROUTES = {"", "introduction", "methodology", "implementation", "experiments", "benchmark"}

def main() -> None:
    if not (DIST / "index.html").is_file():
        raise RuntimeError("Build frontend: npm run build:single-origin")
    parent = ROOT / "frontend" / "node_modules" / ".processing-qa"
    parent.mkdir(parents=True, exist_ok=True)
    if not parent.resolve().is_relative_to((ROOT / "frontend").resolve()):
        raise RuntimeError("QA root escaped scoped frontend directory")
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

        app = create_app(Settings(data_dir=private, db_path=db,
            auth_secret="qa-only-processing-not-deployment-secret-123456789",
            public_origin=origin, cookie_secure=False), capture)
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
            return {"harness": "real-processing-api-v1", "worker_started": worker is not None}

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

        @app.get("/{path:path}")
        async def browser_files(path: str):
            candidate = (DIST / path).resolve()
            if candidate.is_relative_to(DIST) and candidate.is_file():
                return FileResponse(candidate)
            if path.rstrip("/") in ROUTES:
                return FileResponse(DIST / "index.html")
            raise HTTPException(404, "Not found")

        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

if __name__ == "__main__":
    main()
