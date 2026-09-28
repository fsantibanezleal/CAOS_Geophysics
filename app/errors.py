"""Stable errors for project and raw-source operations."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, fields: list[str] | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields or []
        super().__init__(message)


async def api_error_handler(_request: Request, error: ApiError) -> JSONResponse:
    body: dict = {"code": error.code, "message": error.message}
    if error.fields:
        body["fields"] = error.fields
    return JSONResponse(body, status_code=error.status)
