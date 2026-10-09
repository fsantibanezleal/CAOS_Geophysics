"""Supplied transport controls, not live TLS or host measurement evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def verifier():
    spec = importlib.util.spec_from_file_location("single_vps_review", ROOT / "scripts/verify_single_vps_release.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build(tmp_path):
    root = tmp_path / "build"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_bytes(b'<script src="/assets/app.js"></script>')
    (root / "assets/app.js").write_bytes(b"actual build fixture")
    (root / "assets/empty.bin").write_bytes(b"")
    return root


class SuppliedTransport:
    def __init__(self, verifier, root):
        self.v = verifier
        self.root = root
        self.calls = []
        self.overrides = {}

    def get(self, url, cap):
        self.calls.append((url, cap))
        path = url.removeprefix("https://example.test/")
        status = 200
        if path in self.v.ROUTES:
            data = (self.root / "index.html").read_bytes()
        elif path == "api/auth/config":
            data = b'{"mode":"local","registration_enabled":false,"mail_flows_enabled":false}'
        elif path == "api/projects":
            status, data = 401, b'{"detail":"Unauthorized"}'
        else:
            data = (self.root / path).read_bytes()
        status, data = self.overrides.get(path, (status, data))
        if len(data) > cap:
            raise self.v.VerificationError("response_bound")
        return self.v.Remote(status, len(data), hashlib.sha256(data).hexdigest(), data if cap == 4096 else None)


@pytest.mark.parametrize("origin", ["http://example.test", "https://user:secret@example.test", "https://example.test/x", "https://example.test/?x=1", "https://example.test/#x", "https://example.test:444", "https://example.test//", "https://example.test\\x", "https://example.test.", "https://example.test\n"])
def test_origin_contract(verifier, origin):
    with pytest.raises(verifier.VerificationError):
        verifier.origin_root(origin)
    assert verifier.origin_root("https://example.test:443/") == "https://example.test/"


def test_exact_build_and_routes(verifier, tmp_path):
    root = build(tmp_path)
    transport = SuppliedTransport(verifier, root)
    result = verifier.verify("https://example.test", root, transport=transport)
    assert result["verified_files"] == 3
    assert result["verified_routes"] == 6
    assert result["full_release_accepted"] is False
    assert len(transport.calls) == 11
    transport.overrides["assets/app.js"] = (200, b"wrong")
    with pytest.raises(verifier.VerificationError, match="build_mismatch"):
        verifier.verify("https://example.test", root, transport=transport)


@pytest.mark.parametrize("path,status,data", [("api/auth/config",200,b'{"mode":"email","registration_enabled":true,"mail_flows_enabled":true}'), ("api/auth/config",200,b'{"mode":"local","registration_enabled":false,"mail_flows_enabled":false,"extra":1}'), ("api/auth/config",200,b'{"mode":"local","mode":"local","registration_enabled":false,"mail_flows_enabled":false}'), ("api/auth/config",200,b'{"mode":"local","registration_enabled":0,"mail_flows_enabled":false}'), ("api/projects",200,b'{}'), ("api/projects",401,b'<html>SPA</html>')])
def test_api_boundary(verifier, tmp_path, path, status, data):
    root = build(tmp_path)
    transport = SuppliedTransport(verifier, root)
    transport.overrides[path] = status, data
    with pytest.raises(verifier.VerificationError):
        verifier.verify("https://example.test", root, transport=transport)


def test_transport_bounds(verifier, tmp_path):
    root = build(tmp_path)
    transport = SuppliedTransport(verifier, root)
    transport.overrides["assets/app.js"] = 200, b"x" * 30
    with pytest.raises(verifier.VerificationError, match="response_bound"):
        verifier.verify("https://example.test", root, transport=transport)
    with pytest.raises(verifier.VerificationError, match="redirect"):
        verifier.NoRedirect().redirect_request(None, None, 302, "", {}, "https://elsewhere.test")
    transport.overrides["assets/app.js"] = 302, b""
    with pytest.raises(verifier.VerificationError):
        verifier.verify("https://example.test", root, transport=transport)


def inventory():
    return {"schema":"geophysics.release-capacity/v1", "observed_at":"2026-10-04T00:00:00Z", "releases":[{"id":"release-c","role":"current","bytes":3}, {"id":"release-b","role":"rollback","bytes":2}, {"id":"release-a","role":"rollback","bytes":1}], "free_disk_bytes":40,"additional_release_bytes":10,"job_scratch_bytes":30,"available_memory_bytes":70,"worker_memory_bytes":50,"api_memory_bytes":10,"controller_memory_bytes":10}


@pytest.mark.parametrize("change", ["valid", "disk", "memory", "bool", "negative", "overflow", "roles", "duplicate", "stale", "future", "extra"])
def test_retention_and_capacity(verifier, change):
    value = inventory()
    now = datetime(2026,10,4,0,0,30,tzinfo=timezone.utc)
    if change == "disk": value["free_disk_bytes"] = 39
    elif change == "memory": value["available_memory_bytes"] = 69
    elif change == "bool": value["job_scratch_bytes"] = True
    elif change == "negative": value["api_memory_bytes"] = -1
    elif change == "overflow": value["free_disk_bytes"] = 2**64
    elif change == "roles": value["releases"][1]["role"] = "current"
    elif change == "duplicate": value["releases"][2]["id"] = "release-b"
    elif change == "stale": value["observed_at"] = "2026-10-03T00:00:00Z"
    elif change == "future": value["observed_at"] = "2026-10-05T00:00:00Z"
    elif change == "extra": value["backup_required"] = True
    if change == "valid":
        assert verifier.validate_capacity(value, now=now)["retained_releases"] == 3
    else:
        with pytest.raises(verifier.VerificationError):
            verifier.validate_capacity(value, now=now)


def test_receipt_and_no_overwrite(verifier, tmp_path):
    root = build(tmp_path)
    result = verifier.verify("https://example.test", root, transport=SuppliedTransport(verifier, root))
    assert all(result[key] is False for key in ("scientific_acceptance", "browser_acceptance", "worker_acceptance", "full_release_accepted"))
    target = tmp_path / "private-receipt.json"
    verifier.write_receipt(target, result)
    assert json.loads(target.read_bytes()) == result
    prior = target.read_bytes()
    with pytest.raises(FileExistsError):
        verifier.write_receipt(target, {"replacement": True})
    assert target.read_bytes() == prior


def test_inventory_bounds_and_local_mutation(verifier, tmp_path, monkeypatch):
    root = build(tmp_path)
    monkeypatch.setattr(verifier, "FILE_COUNT_CAP", 2)
    with pytest.raises(verifier.VerificationError):
        verifier.build_inventory(root)
    monkeypatch.setattr(verifier, "FILE_COUNT_CAP", 8192)
    transport = SuppliedTransport(verifier, root)
    original = transport.get
    def mutate(url, cap):
        response = original(url, cap)
        if url.endswith("assets/app.js"):
            (root / "assets/app.js").write_bytes(b"changed after fetch")
        return response
    transport.get = mutate
    with pytest.raises(verifier.VerificationError, match="local_build_changed"):
        verifier.verify("https://example.test", root, transport=transport)


@pytest.mark.parametrize("kind", ["identity", "encoded", "length-too-large", "length-short", "body-too-large", "different-url", "expired"])
def test_actual_transport_reader_controls(verifier, monkeypatch, kind):
    transport = verifier.HttpsTransport()
    class Response(io.BytesIO):
        status = 200
        headers = {}
        def geturl(self):
            return "https://other.test/x" if kind == "different-url" else "https://example.test/x"
    response = Response(b"abc" if kind != "body-too-large" else b"abcd")
    response.headers = {"Content-Encoding": "gzip"} if kind == "encoded" else {}
    if kind == "length-too-large": response.headers["Content-Length"] = "4"
    if kind == "length-short": response.headers["Content-Length"] = "2"
    class Opener:
        def open(self, request, timeout):
            assert request.get_method() == "GET" and timeout == 30
            assert request.get_header("Accept-encoding") == "identity"
            return response
    transport.opener = Opener()
    if kind == "expired":
        monkeypatch.setattr(verifier.time, "monotonic", lambda: transport.deadline + 1)
    if kind == "identity":
        result = transport.get("https://example.test/x", 3)
        assert result.bytes == 3 and result.sha256 == hashlib.sha256(b"abc").hexdigest()
    else:
        with pytest.raises(verifier.VerificationError):
            transport.get("https://example.test/x", 3)
