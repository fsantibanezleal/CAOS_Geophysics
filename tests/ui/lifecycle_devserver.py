"""Loopback-only real API + built frontend for browser QA; never a deployment entry point."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

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
        raise RuntimeError("Build the single-origin frontend before browser QA")
    parent = ROOT / "data" / "raw" / "qa-browser"
    parent.mkdir(parents=True, exist_ok=True)
    if not parent.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("QA private root must remain inside this worktree")
    port = int(os.environ.get("GEOPHYSICS_QA_PORT", "8765"))
    origin = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="run-", dir=parent) as temporary:
        private = Path(temporary) / "private"
        private.mkdir()
        db = private / "api.sqlite3"
        os.environ["GEOPHYSICS_DB_PATH"] = str(db)
        command.upgrade(Config(str(ROOT / "app" / "alembic.ini")), "head")
        messages: list[str] = []

        async def capture(_address: str, _subject: str, body: str) -> None:
            messages.append(body)

        app = create_app(Settings(
            data_dir=private, db_path=db, auth_secret="qa-only-not-for-deployment-secret-123456789",
            public_origin=origin, cookie_secure=False,
        ), capture)

        @app.get("/__qa/mail/latest")
        async def latest_mail():
            if not messages:
                raise HTTPException(404, "No captured mail")
            verification = re.search(r"Verification token: ([^\n]+)", messages[-1])
            reset = re.search(r"Password reset token: ([^\n]+)", messages[-1])
            return {"token": (verification or reset).group(1) if verification or reset else None}

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
