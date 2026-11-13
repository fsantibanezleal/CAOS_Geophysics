"""Read-only HTTPS/build/access and supplied capacity verification, not release acceptance."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import ssl
import stat
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener

CHUNK = 65536
FILE_COUNT_CAP = 8192
FILE_BYTE_CAP = 512 * 1024 * 1024
TOTAL_BYTE_CAP = 4 * 1024 * 1024 * 1024
ROUTES = ("", "introduction/", "methodology/", "implementation/", "experiments/", "benchmark/")


class VerificationError(ValueError):
    """Fixed reason code without private path or response data."""


@dataclass(frozen=True)
class Remote:
    status: int
    bytes: int
    sha256: str
    payload: bytes | None = None


def origin_root(value: str) -> str:
    if type(value) is not str or len(value) > 300 or any(ord(c) < 33 for c in value) or "\\" in value:
        raise VerificationError("origin_contract")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        valid_host = bool(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host))
        labels = host.split(".")
        if (parsed.scheme != "https" or not valid_host or len(host) > 253 or len(labels) < 2
                or any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-") for label in labels)
                or parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443)
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
            raise VerificationError("origin_contract")
    except ValueError:
        raise VerificationError("origin_contract") from None
    return "https://" + host.lower() + "/"


def regular_path(path: Path, *, directory: bool = False) -> None:
    if not path.is_absolute() or ".." in path.parts:
        raise VerificationError("local_path_contract")
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise VerificationError("local_path_contract")
    mode = path.stat().st_mode
    if not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)):
        raise VerificationError("local_path_contract")


def local_hash(path: Path) -> tuple[int, str]:
    regular_path(path)
    before = path.stat()
    if before.st_size > FILE_BYTE_CAP:
        raise VerificationError("local_byte_bound")
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK):
            count += len(chunk)
            if count > before.st_size:
                raise VerificationError("local_build_changed")
            digest.update(chunk)
    after = path.stat()
    if count != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise VerificationError("local_build_changed")
    return count, digest.hexdigest()


def build_inventory(root: Path) -> dict:
    regular_path(root, directory=True)
    result = {}
    total = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            regular_path(Path(directory) / name, directory=True)
        for name in files:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if any(part in ("", ".", "..") or len(part) > 255 or any(ord(c) < 32 or c in "\\:#?%" for c in part) for part in relative.split("/")):
                raise VerificationError("build_member_contract")
            if len(result) >= FILE_COUNT_CAP:
                raise VerificationError("local_file_bound")
            size, digest = local_hash(path)
            total += size
            if total > TOTAL_BYTE_CAP:
                raise VerificationError("local_byte_bound")
            result[relative] = {"bytes": size, "sha256": digest}
    if "index.html" not in result or not result["index.html"]["bytes"]:
        raise VerificationError("missing_index")
    return dict(sorted(result.items()))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise VerificationError("redirect")


class HttpsTransport:
    def __init__(self):
        context = ssl.create_default_context()
        context.set_alpn_protocols(["http/1.1"])
        self.opener = build_opener(ProxyHandler({}), HTTPSHandler(context=context), NoRedirect())
        self.deadline = time.monotonic() + 1800

    def get(self, url: str, cap: int) -> Remote:
        if time.monotonic() > self.deadline:
            raise VerificationError("verification_deadline")
        request = Request(url, method="GET", headers={"Accept-Encoding": "identity", "Cache-Control": "no-cache", "User-Agent": "CAOS-SingleSite-Verification/1"})
        try:
            response = self.opener.open(request, timeout=30)
        except HTTPError as error:
            response = error
        digest = hashlib.sha256()
        count = 0
        body = bytearray() if cap == 4096 else None
        with response:
            encoding = response.headers.get("Content-Encoding", "identity")
            if encoding != "identity" or response.geturl() != url:
                raise VerificationError("response_contract")
            length = response.headers.get("Content-Length")
            if length is not None and (not re.fullmatch(r"[0-9]{1,20}", length) or int(length) > cap):
                raise VerificationError("response_bound")
            while True:
                if time.monotonic() > self.deadline:
                    raise VerificationError("verification_deadline")
                chunk = response.read(min(CHUNK, cap - count + 1))
                if not chunk:
                    break
                count += len(chunk)
                if count > cap:
                    raise VerificationError("response_bound")
                digest.update(chunk)
                if body is not None:
                    body.extend(chunk)
            if length is not None and count != int(length):
                raise VerificationError("response_length")
            return Remote(response.status, count, digest.hexdigest(), bytes(body) if body is not None else None)


def strict_object(raw: bytes) -> dict:
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise VerificationError("json_contract")
            value[key] = item
        return value

    def nonfinite(_):
        raise VerificationError("json_contract")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
    except (ValueError, UnicodeError, RecursionError):
        raise VerificationError("json_contract") from None
    if type(value) is not dict:
        raise VerificationError("json_contract")
    return value


def validate_capacity(value: dict, *, now: datetime | None = None) -> dict:
    quantities = {"free_disk_bytes", "additional_release_bytes", "job_scratch_bytes", "available_memory_bytes", "worker_memory_bytes", "api_memory_bytes", "controller_memory_bytes"}
    if type(value) is not dict or set(value) != quantities | {"schema", "observed_at", "releases"} or value["schema"] != "geophysics.release-capacity/v1":
        raise VerificationError("capacity_contract")
    for key in quantities:
        if type(value[key]) is not int or not 0 <= value[key] < 2**63:
            raise VerificationError("capacity_contract")
    try:
        if type(value["observed_at"]) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value["observed_at"]):
            raise ValueError
        observed = datetime.strptime(value["observed_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age = ((now or datetime.now(timezone.utc)) - observed).total_seconds()
    except (TypeError, ValueError):
        raise VerificationError("capacity_contract") from None
    if not 0 <= age <= 300:
        raise VerificationError("capacity_stale")
    releases = value["releases"]
    if type(releases) is not list or len(releases) != 3:
        raise VerificationError("retention_contract")
    ids, roles = set(), []
    for release in releases:
        if (type(release) is not dict or set(release) != {"id", "role", "bytes"}
                or type(release["id"]) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", release["id"])
                or release["id"] in ids or release["role"] not in ("current", "rollback")
                or type(release["bytes"]) is not int or not 0 < release["bytes"] < 2**63):
            raise VerificationError("retention_contract")
        ids.add(release["id"])
        roles.append(release["role"])
    if sorted(roles) != ["current", "rollback", "rollback"]:
        raise VerificationError("retention_contract")
    disk = value["additional_release_bytes"] + value["job_scratch_bytes"]
    memory = value["worker_memory_bytes"] + value["api_memory_bytes"] + value["controller_memory_bytes"]
    if disk >= 2**63 or memory >= 2**63 or value["free_disk_bytes"] < disk or value["available_memory_bytes"] < memory:
        raise VerificationError("capacity_insufficient")
    return {"supplied_inventory_consistent": True, "host_measurement_verified": False, "retained_releases": 3}


def verify(origin: str, build: Path, *, transport=None, host_inventory: dict | None = None) -> dict:
    base = origin_root(origin)
    files = build_inventory(build)
    reader = transport or HttpsTransport()
    for relative, record in files.items():
        response = reader.get(base + quote(relative, safe="/"), record["bytes"])
        if response.status != 200 or (response.bytes, response.sha256) != (record["bytes"], record["sha256"]):
            raise VerificationError("build_mismatch")
        if local_hash(build / relative) != (record["bytes"], record["sha256"]):
            raise VerificationError("local_build_changed")
    index = files["index.html"]
    for route in ROUTES:
        response = reader.get(base + route, index["bytes"])
        if response.status != 200 or (response.bytes, response.sha256) != (index["bytes"], index["sha256"]):
            raise VerificationError("route_mismatch")
    config = reader.get(base + "api/auth/config", 4096)
    expected = {"mode": "local", "registration_enabled": False, "mail_flows_enabled": False}
    actual = strict_object(config.payload or b"")
    if config.status != 200 or actual != expected or any(type(actual.get(k)) is not type(v) for k, v in expected.items()):
        raise VerificationError("auth_profile_mismatch")
    projects = reader.get(base + "api/projects", 4096)
    if projects.status != 401 or not strict_object(projects.payload or b""):
        raise VerificationError("anonymous_projects_not_protected")
    if build_inventory(build) != files:
        raise VerificationError("local_build_changed")
    capacity = validate_capacity(host_inventory) if host_inventory is not None else None
    return {"schema": "geophysics.single-site-verification/v1", "origin": base, "verified_at": datetime.now(timezone.utc).isoformat(), "verified_files": len(files), "verified_routes": len(ROUTES), "files": files, "local_auth_profile": True, "anonymous_projects_protected": True, "capacity": capacity, "scientific_acceptance": False, "browser_acceptance": False, "worker_acceptance": False, "full_release_accepted": False}


def write_receipt(path: Path, value: dict) -> None:
    regular_path(path.parent, directory=True)
    if path.exists():
        raise FileExistsError
    data = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
    if len(data) > 2 * 1024 * 1024:
        raise VerificationError("receipt_bound")
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--host-inventory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if not args.output.is_absolute() or args.output.exists():
            raise VerificationError("output_contract")
        inventory = None
        if args.host_inventory is not None:
            regular_path(args.host_inventory)
            with args.host_inventory.open("rb") as stream:
                raw = stream.read(32769)
            if len(raw) > 32768:
                raise VerificationError("capacity_bound")
            inventory = strict_object(raw)
        result = verify(args.origin, args.build, host_inventory=inventory)
        write_receipt(args.output, result)
    except (OSError, ValueError, TypeError, RecursionError, HTTPException):
        print("Single-site verification failed; no release acceptance", flush=True)
        return 1
    print("Single-site byte/access verification passed; full release acceptance remains separate", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
