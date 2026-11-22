"""Test-owned persisted native results served by the actual API, no interception.

Explicit external pytest database only. No provisioning, SMTP, worker execution,
operator credentials, test record substitution or production deployment.
"""
import os
import secrets
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
import uvicorn

from app.config import Settings
from app.server import create_app


def main():
    checkout = Path.cwd().resolve()
    root = Path(os.environ["GEOPHYSICS_PROFILE_QA_CASE"]).resolve(strict=True)
    build = Path(os.environ["GEOPHYSICS_PROFILE_BUILD"]).resolve(strict=True)
    if root.is_relative_to(checkout) or build.is_relative_to(checkout) or not (root / "api.sqlite3").is_file():
        raise ValueError("existing test-owned external native case and build required")
    settings = Settings(data_dir=root, auth_secret=secrets.token_urlsafe(48), cookie_secure=False,
                        public_origin=os.environ["GEOPHYSICS_PROFILE_QA_ORIGIN"], auth_mode="local")

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
    app.mount("/", TestSpa(directory=build, html=True))
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["GEOPHYSICS_PROFILE_QA_PORT"]), log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
