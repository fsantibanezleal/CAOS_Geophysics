"""Real local API/static test server, not a production entry point.

Uses a trusted existing checkout/runtime and a new private test DB. Randomized
test credentials arrive over stdin only; no supplied operator secret is read.
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
import uvicorn

from app.accounts import provision_account
from app.config import Settings
from app.database import make_engine
from app.server import create_app
from sqlalchemy.ext.asyncio import async_sessionmaker


def main() -> None:
    declaration = json.loads(sys.stdin.readline())
    root = Path(os.environ["GEOPHYSICS_REAL_QA_ROOT"]).resolve()
    checkout = Path.cwd().resolve()
    if root.parent != (checkout / "data" / "raw").resolve() or not root.name.startswith("frontend-local-account-review-"):
        raise ValueError("QA storage must be a new named child of the trusted checkout's ignored raw root")
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(exist_ok=False)
    os.environ["GEOPHYSICS_DATA_DIR"] = str(root)
    os.environ["GEOPHYSICS_DB_PATH"] = str(root / "api.sqlite3")
    settings = Settings(data_dir=root, auth_secret=secrets.token_urlsafe(48),
                        public_origin=os.environ["GEOPHYSICS_REAL_QA_ORIGIN"],
                        cookie_secure=False, auth_mode="local")
    command.upgrade(Config("app/alembic.ini"), "head")

    async def provision(accounts) -> None:
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
            # The static SPA mount must not turn absent API routes into HTML or
            # StaticFiles' method-not-allowed response. Real API routes run first.
            if scope["path"] == "/api" or scope["path"].startswith("/api/"):
                raise HTTPException(status_code=404)
            try:
                return await super().get_response(path, scope)
            except HTTPException as error:
                if error.status_code != 404 or scope["method"] != "GET":
                    raise
                return await super().get_response("index.html", scope)

    app = create_app(settings)
    app.mount("/", TestSpa(directory=os.environ["GEOPHYSICS_REVIEW_BUILD"], html=True))
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["GEOPHYSICS_REAL_QA_PORT"]),
                access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
