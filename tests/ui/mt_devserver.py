"""Isolated loopback actual MT API/worker QA. Backend checkout is READ ONLY.

Explicit backend + interpreter required. Private DB/staging live only beneath this
checkout's ignored frontend/node_modules/.mt-qa. Flag opt-in is QA-only, never a
production activation. No API or scientific result is mocked.
"""
from __future__ import annotations
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(os.environ["GEOPHYSICS_MT_QA_BACKEND_ROOT"]).resolve(strict=True)
if not (BACKEND / "app/mt_compute.py").is_file():
    raise RuntimeError("Explicit backend lacks reviewed MT runtime")
sys.path.insert(0, str(BACKEND))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONPATH"] = str(BACKEND)
import psutil
import uvicorn
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.responses import FileResponse
from app.config import Settings
from app.server import create_app

def main():
    dist = (ROOT / "frontend/dist").resolve()
    if not (dist / "index.html").is_file():
        raise RuntimeError("Build frontend first")
    parent = ROOT / "frontend/node_modules/.mt-qa"
    parent.mkdir(parents=True, exist_ok=True)
    enabled = os.environ.get("GEOPHYSICS_MT_QA_ENABLE") == "isolated-test-only"
    os.environ["GEOPHYSICS_MT_ONLINE_ENABLED"] = "1" if enabled else "0"
    port = int(os.environ.get("GEOPHYSICS_MT_QA_PORT", "8877"))
    origin = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="run-", dir=parent) as temporary:
        private = Path(temporary)
        db = private / "api.sqlite3"
        os.environ["GEOPHYSICS_DB_PATH"] = str(db)
        os.environ["GEOPHYSICS_DATA_DIR"] = str(private)
        cfg = Config(str(BACKEND / "app/alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND / "app/migrations"))
        command.upgrade(cfg, "head")
        messages = []
        worker = None
        def stop():
            nonlocal worker
            if worker and worker.poll() is None:
                children = psutil.Process(worker.pid).children(recursive=True)
                for child in children:
                    try: child.terminate()
                    except psutil.NoSuchProcess: pass
                worker.terminate()
                psutil.wait_procs(children, timeout=5)
                worker.wait(timeout=10)
            worker = None
        async def capture(_address, _subject, body): messages.append(body)
        app = create_app(Settings(data_dir=private, db_path=db,
            auth_secret="isolated-mt-browser-qa-not-deployment-1234567890",
            public_origin=origin, cookie_secure=False, mt_online_enabled=enabled), capture)
        original_lifespan = app.router.lifespan_context
        @asynccontextmanager
        async def lifespan(application):
            async with original_lifespan(application):
                try: yield
                finally: stop()
        app.router.lifespan_context = lifespan
        @app.get("/__qa/mt")
        async def identity():
            paths = ["app/mt_compute.py", "app/mt_bundle.py", "data-pipeline/edi.py", "data-pipeline/electromagnetics.py"]
            return {"harness": "actual-mt-api-worker/v1", "mt_enabled": enabled,
                    "backend_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=BACKEND, text=True).strip(),
                    "code_sha256": {p: hashlib.sha256((BACKEND/p).read_bytes()).hexdigest() for p in paths}}
        @app.get("/__qa/mail/latest")
        async def latest():
            if not messages: raise HTTPException(404)
            token = re.search(r"(?:Verification|Password reset) token: ([^\n]+)", messages[-1])
            return {"token": token.group(1) if token else None}
        @app.post("/__qa/worker/start")
        async def start():
            nonlocal worker
            if worker is None:
                worker = subprocess.Popen([sys.executable, "-B", "-m", "app.worker"], cwd=BACKEND, env=os.environ.copy(),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            if worker.poll() is not None: raise HTTPException(500, "QA worker exited")
            return {"started": True}
        @app.post("/__qa/worker/stop")
        async def stop_endpoint(): stop(); return {"stopped": True}
        @app.get("/{path:path}")
        async def files(path: str):
            candidate = (dist/path).resolve()
            if candidate.is_relative_to(dist) and candidate.is_file(): return FileResponse(candidate)
            if path.rstrip("/") in {"", "introduction", "methodology", "implementation", "experiments", "benchmark"}: return FileResponse(dist/"index.html")
            raise HTTPException(404)
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
if __name__ == "__main__": main()
