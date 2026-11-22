"""Actual API + bounded CPU worker test server, never a deployment entry point.

Trusted immutable backend source and existing interpreter only. A new retained
private DB receives randomized accounts over stdin. No operator secrets, SMTP,
API interception, source edits, package installs or GPU work.
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from alembic import command
from alembic.config import Config
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.exceptions import HTTPException
import psutil
import uvicorn

from app.accounts import provision_account
from app.config import Settings
from app.database import make_engine
from app.server import create_app


def main() -> None:
    declaration = json.loads(sys.stdin.readline())
    checkout = Path.cwd().resolve()
    root = Path(os.environ["GEOPHYSICS_REAL_QA_ROOT"]).resolve()
    # Caller creates a new explicitly reviewed private scratch parent, including
    # C:/E: storage when the source drive is full. No cleanup/deletion here.
    storage_parent = Path(os.environ["GEOPHYSICS_QA_STORAGE_PARENT"]).resolve(strict=True)
    if root.parent != storage_parent or not root.name.startswith("srv-"):
        raise ValueError("Only a new named private QA child is permitted")
    if str(UUID(root.name[4:])) != root.name[4:]:
        raise ValueError("QA child requires a fresh UUID")
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(exist_ok=False)
    os.environ["GEOPHYSICS_DATA_DIR"] = str(root)
    os.environ["GEOPHYSICS_DB_PATH"] = str(root / "api.sqlite3")
    os.environ["GEOPHYSICS_MT_ONLINE_ENABLED"] = "1"
    settings = Settings(data_dir=root, auth_secret=secrets.token_urlsafe(48),
                        public_origin=os.environ["GEOPHYSICS_REAL_QA_ORIGIN"],
                        cookie_secure=False, auth_mode="local", mt_online_enabled=True)
    command.upgrade(Config("app/alembic.ini"), "head")

    async def provision(accounts):
        engine = make_engine(settings)
        try:
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            for account in accounts:
                await provision_account(sessions, account["email"], account["password"])
        finally:
            await engine.dispose()
    asyncio.run(provision(declaration["accounts"]))
    del declaration

    class TestSpa(StaticFiles):
        async def get_response(self, path, scope):
            if scope["path"] == "/api" or scope["path"].startswith("/api/"):
                raise HTTPException(status_code=404)
            try:
                return await super().get_response(path, scope)
            except HTTPException as error:
                if error.status_code != 404 or scope["method"] != "GET":
                    raise
                return await super().get_response("index.html", scope)

    app = create_app(settings)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        async with original(application):
            worker = subprocess.Popen([sys.executable, "-B", "-m", "app.worker"],
                cwd=checkout, env=os.environ.copy(), stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                yield
            finally:
                if worker.poll() is None:
                    children = psutil.Process(worker.pid).children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except psutil.NoSuchProcess:
                            pass
                    psutil.wait_procs(children, timeout=5)
                    worker.terminate()
                    worker.wait(timeout=10)

    app.router.lifespan_context = lifespan
    app.mount("/", TestSpa(directory=os.environ["GEOPHYSICS_REVIEW_BUILD"], html=True))
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["GEOPHYSICS_REAL_QA_PORT"]),
                access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
