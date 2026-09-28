"""CSRF/origin checks and persistent request admission."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert

from app.config import Settings
from app.models import RateWindow


def _origin(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def install_security(app: FastAPI, settings: Settings) -> None:
    csrf_cookie = "__Host-geophysics_csrf" if settings.cookie_secure else "geophysics_csrf"

    @app.get("/api/auth/csrf")
    async def csrf():
        token = secrets.token_urlsafe(32)
        response = JSONResponse({"csrf_token": token})
        response.set_cookie(
            csrf_cookie, token, max_age=12 * 60 * 60, path="/", secure=settings.cookie_secure,
            httponly=True, samesite="strict",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.middleware("http")
    async def guard(request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            source = request.headers.get("origin") or request.headers.get("referer", "")
            if _origin(source) != settings.public_origin or request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"code": "origin_forbidden", "message": "Same-origin request required"}, status_code=403)
            cookie = request.cookies.get(csrf_cookie, "")
            header = request.headers.get("x-csrf-token", "")
            if not cookie or not header or not secrets.compare_digest(cookie, header):
                return JSONResponse({"code": "csrf_invalid", "message": "CSRF token is missing or invalid"}, status_code=403)

        scope = None
        window = limit = 0
        if request.method == "POST" and path.startswith("/api/auth/"):
            scope, window, limit = "auth", 600, 10
        elif request.method == "POST" and path.endswith("/assets"):
            scope, window, limit = "upload", 3600, 20
        elif request.method == "POST" and path.endswith("/datasets"):
            scope, window, limit = "dataset", 3600, 20
        elif request.method == "POST" and path.endswith("/jobs"):
            scope, window, limit = "processing_jobs", 3600, 30
        if scope is not None:
            ip = request.client.host if request.client else "unknown"
            key = hmac.new(settings.auth_secret.encode(), ip.encode(), hashlib.sha256).hexdigest()
            now = int(time.time())
            bucket = now - now % window
            async with request.app.state.sessions() as session:
                stmt = insert(RateWindow).values(scope=scope, client_key=key, window_start=bucket, count=1)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["scope", "client_key", "window_start"],
                    set_={"count": RateWindow.count + 1},
                )
                await session.execute(stmt)
                count = (await session.execute(
                    select(RateWindow.count).where(
                        RateWindow.scope == scope,
                        RateWindow.client_key == key,
                        RateWindow.window_start == bucket,
                    )
                )).scalar_one()
                if count == 1:
                    await session.execute(delete(RateWindow).where(RateWindow.window_start < now - 86400))
                await session.commit()
            if count > limit:
                response = JSONResponse({"code": "rate_limited", "message": "Retry after the rate window"}, status_code=429)
                response.headers["Retry-After"] = str(bucket + window - now)
                return response
        return await call_next(request)
