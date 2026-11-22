"""Build the checked-in OpenAPI document from the runtime route inventory.

This is documentation generation only. It does not import or alter the API.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_REF = "schemas/api-payloads.schema.json#/$defs/{}"
SESSION = [{"apiSession": []}]
CSRF = [{"csrfToken": [], "csrfCookie": []}]
WRITE = [{"apiSession": [], "csrfToken": [], "csrfCookie": []}]


def schema(name: str) -> dict:
    return {"$ref": SCHEMA_REF.format(name)}


def response(description: str, model: str | None = None, *, media="application/json") -> dict:
    item = {"description": description}
    if model:
        item["content"] = {media: {"schema": schema(model)}}
    elif media != "application/json":
        item["content"] = {media: {"schema": {"type": "string", "contentEncoding": "binary"}}}
    return item


def operation(operation_id: str, tag: str, responses: dict, *, request=None, security=None,
              description=None, parameters=None, conditional=None) -> dict:
    item = {
        "tags": [tag],
        "operationId": operation_id,
        "responses": {str(code): value for code, value in responses.items()},
    }
    if security is not None:
        item["security"] = security
    if request:
        item["requestBody"] = {"required": True, "content": request}
    if parameters:
        item["parameters"] = parameters
    if description:
        item["description"] = description
    if conditional:
        item["x-registered-when"] = conditional
    return item


def json_body(model: str) -> dict:
    return {"application/json": {"schema": schema(model)}}


def binary_content(media_types: tuple[str, ...]) -> dict:
    return {media: {"schema": {"type": "string", "contentEncoding": "binary"}} for media in media_types}


def path_id(name: str) -> dict:
    return {"$ref": f"#/components/parameters/{name}"}


ERROR = {"$ref": "#/components/responses/Error"}
AUTH_ERROR = {"$ref": "#/components/responses/AuthError"}

paths = {
    "/api/auth/config": {"get": operation("getAuthConfig", "auth", {
        200: response("Configured auth mode and enabled email flows.", "AuthConfig")}, security=[])},
    "/api/auth/csrf": {"get": operation("getCsrfToken", "auth", {
        200: {**response("CSRF token; also sets the HttpOnly CSRF cookie.", "CsrfToken"), "headers": {
            "Set-Cookie": {"schema": {"type": "string"}},
            "Cache-Control": {"schema": {"const": "no-store"}},
        }}}, security=[])},
    "/api/auth/me": {"get": operation("getCurrentUser", "auth", {
        200: response("Current active account.", "User"), 401: ERROR})},
    "/api/auth/cookie/login": {"post": operation("loginCookie", "auth", {
        204: {"description": "Authenticated; sets session cookie.", "headers": {
            "Set-Cookie": {"schema": {"type": "string"}}}}, 400: AUTH_ERROR, 403: ERROR}, security=CSRF,
        request={"application/x-www-form-urlencoded": {"schema": {
            "type": "object", "required": ["username", "password"],
            "properties": {"username": {"type": "string", "format": "email"}, "password": {"type": "string"}},
        }}})},
    "/api/auth/cookie/logout": {"post": operation("logoutCookie", "auth", {
        204: {"description": "Session cookie cleared."}, 401: ERROR, 403: ERROR}, security=WRITE)},
    "/api/auth/register": {"post": operation("registerAccount", "auth", {
        201: response("Created account; verification email is requested.", "User"), 400: AUTH_ERROR, 403: ERROR},
        request=json_body("UserCreate"), security=CSRF, conditional="auth_mode=email")},
    "/api/auth/verify/request": {"post": operation("requestVerification", "auth", {
        202: {"description": "Verification request accepted."}, 400: AUTH_ERROR, 403: ERROR},
        request=json_body("EmailRequest"), security=CSRF, conditional="auth_mode=email")},
    "/api/auth/verify/verify": {"post": operation("verifyAccount", "auth", {
        200: response("Verified account.", "User"), 400: AUTH_ERROR, 403: ERROR},
        request=json_body("TokenRequest"), security=CSRF, conditional="auth_mode=email")},
    "/api/auth/reset-password/forgot-password": {"post": operation("requestPasswordReset", "auth", {
        202: {"description": "Reset request accepted."}, 400: AUTH_ERROR, 403: ERROR},
        request=json_body("EmailRequest"), security=CSRF, conditional="auth_mode=email")},
    "/api/auth/reset-password/reset-password": {"post": operation("resetPassword", "auth", {
        200: {"description": "Password reset completed."}, 400: AUTH_ERROR, 403: ERROR},
        request=json_body("PasswordReset"), security=CSRF, conditional="auth_mode=email")},
    "/api/projects": {
        "get": operation("listProjects", "projects", {
            200: response("Projects owned by the authenticated account.", "ProjectList"), 401: ERROR}),
        "post": operation("createProject", "projects", {
            201: response("Created project.", "Project"), 422: ERROR},
            request=json_body("ProjectCreate"), security=WRITE),
    },
    "/api/projects/{project_id}": {
        "parameters": [path_id("project_id")],
        "get": operation("getProject", "projects", {
            200: response("Owner-scoped project.", "Project"), 404: ERROR}),
        "patch": operation("updateProject", "projects", {
            200: response("Updated project.", "Project"), 422: ERROR},
            request=json_body("ProjectUpdate"), security=WRITE),
        "delete": operation("deleteProject", "projects", {
            204: {"description": "Deleted project and its owned private state."}, 404: ERROR, 409: ERROR}, security=WRITE),
    },
    "/api/projects/{project_id}/assets": {
        "parameters": [path_id("project_id")],
        "get": operation("listProjectAssets", "projects", {
            200: response("Raw asset receipts.", "AssetList")}),
        "post": operation("uploadProjectAsset", "projects", {
            201: response("Immutable raw asset receipt.", "RawAsset"),
            400: ERROR, 413: ERROR, 415: ERROR, 422: ERROR}, security=WRITE,
            parameters=[path_id("assetMetadata")], request={mime: {
                "schema": {"type": "string", "contentEncoding": "binary"}}
                for mime in ("text/csv", "image/tiff", "application/geotiff", "text/plain",
                             "application/octet-stream", "application/vnd.fdsn.mseed", "application/xml",
                             "text/xml", "application/x-segy", "application/x-hdf5", "application/json")},
            description="Upload bytes in the request body. X-Asset-Metadata contains the JSON metadata envelope."),
    },
    "/api/projects/{project_id}/assets/{asset_id}": {
        "parameters": [path_id("project_id"), path_id("asset_id")],
        "get": operation("getProjectAsset", "projects", {
            200: response("Raw asset receipt.", "RawAsset"), 404: ERROR}),
    },
    "/api/projects/{project_id}/assets/{asset_id}/download": {
        "parameters": [path_id("project_id"), path_id("asset_id")],
        "get": operation("downloadProjectAsset", "projects", {
            200: {"description": "Verified original file bytes; Content-Type is the uploaded asset MIME.", "content": binary_content((
                "text/csv", "image/tiff", "application/geotiff", "text/plain", "application/octet-stream",
                "application/vnd.fdsn.mseed", "application/xml", "text/xml", "application/x-segy",
                "application/x-hdf5", "application/json")),
                "headers": {"X-Content-SHA256": {"schema": schema("Sha256")}}}, 404: ERROR}),
    },
    "/api/projects/{project_id}/export": {
        "parameters": [path_id("project_id")],
        "get": operation("exportProjectOriginals", "projects", {
        200: response("ZIP of project record, manifest and verified original assets.", media="application/zip"),
            404: ERROR}),
    },
    "/api/projects/{project_id}/datasets": {
        "parameters": [path_id("project_id")],
        "get": operation("listProjectDatasets", "processing", {
            200: response("Immutable processed dataset receipts.", "DatasetReceiptList")}),
        "post": operation("createProjectDataset", "processing", {
            201: response("Immutable observation dataset receipt.", "DatasetReceipt"),
            409: ERROR, 413: ERROR, 422: ERROR}, request=json_body("DatasetCreate"), security=WRITE),
    },
    "/api/projects/{project_id}/datasets/{dataset_id}": {
        "parameters": [path_id("project_id"), path_id("dataset_id")],
        "get": operation("getProjectDataset", "processing", {
            200: response("Verified modality-specific scientific observation envelope.", "DatasetPayload"),
            404: ERROR, 409: ERROR}),
    },
    "/api/projects/{project_id}/datasets/{dataset_id}/methods": {
        "parameters": [path_id("project_id"), path_id("dataset_id")],
        "get": operation("getProjectDatasetMethods", "processing", {
            200: response("Available and unavailable methods for this exact dataset.", "Methods"), 404: ERROR}),
    },
    "/api/projects/{project_id}/jobs": {
        "parameters": [path_id("project_id")],
        "get": operation("listProjectJobs", "processing", {
            200: response("Owner-scoped job records.", "JobList")}),
        "post": operation("createProjectJob", "processing", {
            202: response("Accepted queued job record; execution is asynchronous.", "Job"),
            409: ERROR, 413: ERROR, 422: ERROR}, request=json_body("JobCreate"), security=WRITE),
    },
    "/api/projects/{project_id}/jobs/{job_id}": {
        "parameters": [path_id("project_id"), path_id("job_id")],
        "get": operation("getProjectJob", "processing", {
            200: response("Current job state and result receipt.", "Job"), 404: ERROR}),
    },
    "/api/projects/{project_id}/jobs/{job_id}/cancel": {
        "parameters": [path_id("project_id"), path_id("job_id")],
        "post": operation("cancelProjectJob", "processing", {
            200: response("Updated job cancellation state.", "Job"), 404: ERROR, 409: ERROR}, security=WRITE),
    },
    "/api/projects/{project_id}/jobs/{job_id}/result": {
        "parameters": [path_id("project_id"), path_id("job_id")],
        "get": operation("getProjectJobResult", "processing", {
            200: response("Verified method-specific scientific result payload.", "ProcessingResult"),
            404: ERROR, 409: ERROR}),
    },
    "/api/projects/{project_id}/jobs/{job_id}/export": {
        "parameters": [path_id("project_id"), path_id("job_id")],
        "get": operation("exportProjectJob", "processing", {
            200: response("ZIP containing verified dataset, result and manifest; waveform jobs may carry extra members.", media="application/zip"),
            404: ERROR, 409: ERROR}),
    },
    "/api/projects/{project_id}/jobs/{job_id}/artifacts/{name}": {
        "parameters": [path_id("project_id"), path_id("job_id"), {
            "name": "name", "in": "path", "required": True, "schema": {"type": "string"}}],
        "get": operation("getWaveformJobArtifact", "processing", {
            200: {"description": "Named integrity-checked waveform member; JSON members use application/json and arrays use application/octet-stream.",
                  "content": binary_content(("application/json", "application/octet-stream"))}, 404: ERROR}),
    },
}

# Shared path parameters belong at the path item level in OpenAPI.
for path, item in paths.items():
    if path.startswith("/api/projects/{project_id}") and "parameters" not in item:
        item["parameters"] = [path_id("project_id")]

document = {
    "openapi": "3.1.0",
    "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
    "info": {
        "title": "CAOS Geophysics private-state API",
        "version": "1.0.0",
        "summary": "OpenAPI description of the implemented authenticated API routes.",
        "description": (
            "Static contract for app/server.py. Email account routes are registered only when "
            "auth_mode=email. The physical participant adds no routes; it participates in existing "
            "DELETE/upload/dataset paths. Public pages and browser-local calculations are outside this API. "
            "This contract describes the current implementation; it does not change runtime behavior."
        ),
    },
    "servers": [{"url": "https://geophysics.ml.fasl-work.com", "description": "Configured ML VPS origin; deployment availability is not implied."}],
    "tags": [
        {"name": "auth", "description": "Cookie session, CSRF and configuration."},
        {"name": "projects", "description": "Owner-scoped projects and original source assets."},
        {"name": "processing", "description": "Immutable datasets and bounded jobs/results."},
    ],
    "security": SESSION,
    "paths": paths,
    "components": {
        "securitySchemes": {
            "apiSession": {"type": "apiKey", "in": "cookie", "name": "geophysics_session", "description": "Cookie name is __Host-geophysics_session when cookie_secure=true."},
            "csrfToken": {"type": "apiKey", "in": "header", "name": "X-CSRF-Token", "description": "State-changing calls also require the matching CSRF cookie."},
            "csrfCookie": {"type": "apiKey", "in": "cookie", "name": "geophysics_csrf", "description": "Cookie name is __Host-geophysics_csrf when cookie_secure=true."},
        },
        "parameters": {
            "project_id": {"name": "project_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}},
            "asset_id": {"name": "asset_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}},
            "dataset_id": {"name": "dataset_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}},
            "job_id": {"name": "job_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}},
            "assetMetadata": {"name": "X-Asset-Metadata", "in": "header", "required": True,
                "description": "JSON AssetMetadata envelope capped at 16 KiB. Request body contains raw file bytes, and Content-Type must match metadata.mime.",
                "schema": {"type": "string", "contentMediaType": "application/json", "contentSchema": schema("UploadMetadata")}},
        },
        "responses": {
            "Error": {"description": "Structured project/API error; validation errors may include field paths.",
                "content": {"application/json": {"schema": schema("Error")}}},
            "AuthError": {"description": "FastAPI-Users error response.",
                "content": {"application/json": {"schema": schema("FrameworkError")}}},
        },
    },
}

target = ROOT / "docs/contracts/api.openapi.json"
rendered = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
if "--check" in sys.argv:
    if not target.is_file() or target.read_text(encoding="utf-8") != rendered:
        print("OpenAPI export is stale; run scripts/build_api_contracts.py")
        sys.exit(1)
    print("OpenAPI export is reproducible")
else:
    target.write_text(rendered, encoding="utf-8")
