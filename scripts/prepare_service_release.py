"""Prepare and verify a new immutable service qualification bundle; no publication.

Only stdlib. No build, science, download, account, host write or gate waiver.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys


CHUNK = 65536
MAX_FILES = 16384
MAX_ENTRIES = 32768
MAX_FILE = 512 * 1024**2
MAX_TOTAL = 4 * 1024**3
MAX_MANIFEST = 4 * 1024**2
REVISION = re.compile(r"^[0-9a-f]{40}$")
ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def safe_relative(value: str) -> str:
    if (not isinstance(value, str) or not value or len(value) > 1024
            or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", p) or p in (".", "..")
                   or p.endswith(".") or RESERVED.match(p) for p in value.split("/"))):
        raise ValueError("unsafe relative member name")
    return value


def no_links(path: Path) -> Path:
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("an explicit absolute path is required")
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("link/reparse path is forbidden")
    return path


def file_digest(path: Path) -> dict:
    no_links(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE:
        raise ValueError("regular-file byte bound exceeded")
    sha = hashlib.sha256()
    count = 0
    with path.open("rb") as handle:
        while block := handle.read(min(CHUNK, before.st_size + 1 - count)):
            count += len(block)
            if count > before.st_size:
                raise ValueError("source changed while hashing")
            sha.update(block)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ) or count != before.st_size:
        raise ValueError("source changed while hashing")
    return {"bytes": count, "sha256": sha.hexdigest()}


def inventory(root: Path) -> dict:
    no_links(root)
    if not root.is_dir():
        raise ValueError("inventory root is not a directory")
    result = {}
    total = 0
    folded = set()
    pending = [root]
    entries = 0
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as scan:
            for item in scan:
                entries += 1
                if entries > MAX_ENTRIES:
                    raise ValueError("inventory entry bound exceeded")
                path = Path(item.path)
                no_links(path)
                name = safe_relative(path.relative_to(root).as_posix())
                if name.casefold() in folded:
                    raise ValueError("case-colliding inventory")
                folded.add(name.casefold())
                if item.is_dir(follow_symlinks=False):
                    pending.append(path)
                    continue
                result[name] = file_digest(path)
                total += result[name]["bytes"]
                if len(result) > MAX_FILES or total > MAX_TOTAL:
                    raise ValueError("inventory bound exceeded")
    return dict(sorted(result.items()))


def strict_json(raw: bytes) -> dict:
    if len(raw) > MAX_MANIFEST:
        raise ValueError("manifest byte bound exceeded")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate manifest key")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("nonfinite JSON constant")

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    if not isinstance(value, dict):
        raise ValueError("manifest is not an object")
    return value


def copy_bundle(source: Path, build: Path, output: Path, paths: list[str], revision: str) -> dict:
    for root in (source, build, output):
        no_links(root)
    if not REVISION.fullmatch(revision):
        raise ValueError("source revision is not an exact Git SHA")
    if output.is_relative_to(source) and not output.is_relative_to(source / "data/raw"):
        raise ValueError("output overlaps source")
    if output.is_relative_to(build) or source.is_relative_to(output) or build.is_relative_to(output):
        raise ValueError("output overlaps inputs")
    if output.exists():
        raise FileExistsError("release output already exists; retain it")
    if len(paths) > MAX_FILES:
        raise ValueError("runtime file bound exceeded")
    if len(paths) != len(set(p.casefold() for p in paths)):
        raise ValueError("duplicate runtime member")
    runtime = {safe_relative(name): file_digest(source / name) for name in sorted(paths)}
    web = inventory(build)
    if "index.html" not in web:
        raise ValueError("build has no index.html")
    if len(runtime) + len(web) > MAX_FILES or sum(i["bytes"] for i in [*runtime.values(), *web.values()]) > MAX_TOTAL:
        raise ValueError("combined release bound exceeded")
    required_bytes = sum(i["bytes"] for i in [*runtime.values(), *web.values()]) + MAX_MANIFEST
    if shutil.disk_usage(output.parent).free < required_bytes:
        raise ValueError("qualification destination capacity insufficient")
    output.mkdir()  # Parent must already exist; never overwrite or recursively create input roots.
    for prefix, root, members in (("source", source, runtime), ("web", build, web)):
        for name, receipt in members.items():
            target = output / prefix / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with (root / name).open("rb") as reader, target.open("xb") as writer:
                remaining = receipt["bytes"]
                while remaining:
                    block = reader.read(min(CHUNK, remaining))
                    if not block:
                        raise ValueError("source shortened while copying")
                    writer.write(block)
                    remaining -= len(block)
                if reader.read(1):
                    raise ValueError("source grew while copying")
                writer.flush()
                os.fsync(writer.fileno())
            if file_digest(target) != receipt or file_digest(root / name) != receipt:
                raise ValueError("copied member integrity mismatch")
    if inventory(build) != web:
        raise ValueError("build inventory changed while copying")
    manifest = {"schema": "geophysics.service-release/v1", "source_revision": revision,
                "qualification_only": True, "full_release_accepted": False,
                "source": runtime, "web": web}
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(encoded) > MAX_MANIFEST:
        raise ValueError("manifest byte bound exceeded")
    with (output / "release.json").open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    verify_bundle(output)
    return manifest


def verify_bundle(root: Path) -> dict:
    no_links(root)
    manifest_path = root / "release.json"
    no_links(manifest_path)
    with manifest_path.open("rb") as handle:
        receipt = strict_json(handle.read(MAX_MANIFEST + 1))
    if (set(receipt) != {"schema", "source_revision", "qualification_only", "full_release_accepted", "source", "web"}
            or receipt["schema"] != "geophysics.service-release/v1"
            or not REVISION.fullmatch(receipt.get("source_revision", ""))
            or receipt["qualification_only"] is not True or receipt["full_release_accepted"] is not False):
        raise ValueError("invalid qualification manifest")
    for name in ("source", "web"):
        if not isinstance(receipt[name], dict):
            raise ValueError("invalid member inventory")
        for member, record in receipt[name].items():
            safe_relative(member)
            if (not isinstance(record, dict) or set(record) != {"bytes", "sha256"}
                    or type(record["bytes"]) is not int or not 0 <= record["bytes"] <= MAX_FILE
                    or not isinstance(record["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])):
                raise ValueError("invalid member integrity receipt")
        actual = inventory(root / name)
        if actual != receipt[name]:
            raise ValueError("bundle inventory/integrity mismatch")
    if {p.name for p in root.iterdir()} - {"source", "web", "release.json", ".venv"}:
        raise ValueError("unexpected release root inventory")
    if len(receipt["source"]) + len(receipt["web"]) > MAX_FILES:
        raise ValueError("combined inventory bound exceeded")
    if sum(i["bytes"] for i in [*receipt["source"].values(), *receipt["web"].values()]) > MAX_TOTAL:
        raise ValueError("combined release byte bound exceeded")
    return receipt


def require_pre_cutover(ledger: dict) -> None:
    """Additional sequencing check; caller must first run structural receipt validation."""
    records = ledger.get("requirements", [])
    if len(records) != 19 or {r.get("id") for r in records} != {f"R-{i:03}" for i in range(1, 20)}:
        raise ValueError("complete per-requirement coverage is required")
    pending = [r["id"] for r in records if r["id"] not in {"R-017", "R-018"} and r.get("verdict") != "pass"]
    if pending:
        raise ValueError("pre-cutover scientific/UI acceptance incomplete: " + ", ".join(pending))


def retained_inventory(root: Path, current: str, rollbacks: list[str]) -> list[dict]:
    no_links(root)
    names = [current, *rollbacks]
    if len(names) != 3 or len(set(names)) != 3 or any(not ID.fullmatch(n) for n in names):
        raise ValueError("current plus two distinct explicit rollback IDs required")
    return [{"id": name, "role": "current" if i == 0 else "rollback",
             "bytes": release_bytes(root / name)} for i, name in enumerate(names)]


def release_bytes(root: Path) -> int:
    """Logical regular-file bytes, never follow links; free space is measured separately."""
    no_links(root)
    if not root.is_dir():
        raise ValueError("release directory absent")
    allowed_env_links = {".venv/bin/python", ".venv/bin/python3", ".venv/bin/python3.12", ".venv/lib64"}
    pending, total, entries = [root], 0, 0
    while pending:
        with os.scandir(pending.pop()) as scan:
            for item in scan:
                entries += 1
                if entries > 262144:
                    raise ValueError("release measurement entry bound exceeded")
                path = Path(item.path)
                name = safe_relative(path.relative_to(root).as_posix())
                if item.is_symlink():
                    if name not in allowed_env_links:
                        raise ValueError("unexpected release measurement link")
                    continue  # Not followed or hashed; this is not runtime/dependency acceptance.
                no_links(path)
                if item.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif item.is_file(follow_symlinks=False):
                    total += item.stat(follow_symlinks=False).st_size
                else:
                    raise ValueError("unexpected release measurement entry")
                if total > 32 * 1024**3:
                    raise ValueError("release measurement byte bound exceeded")
    return total


def mem_available(text: str) -> int:
    matches = re.findall(r"^MemAvailable:\s+([0-9]+) kB$", text, re.M)
    if len(matches) != 1:
        raise ValueError("actual MemAvailable is unavailable")
    return int(matches[0]) * 1024


def collect_capacity(root: Path, current: str, rollbacks: list[str], *, additional: int, scratch: int,
                     worker: int, api: int, controller: int) -> dict:
    if os.name != "posix" or not Path("/proc/meminfo").is_file():
        raise ValueError("capacity collection requires the actual Linux host")
    values = [additional, scratch, worker, api, controller]
    if any(type(n) is not int or not 0 <= n <= 2**63 - 1 for n in values):
        raise ValueError("invalid byte reserve")
    releases = retained_inventory(root, current, rollbacks)
    fs = os.statvfs(root)
    return {"schema": "geophysics.release-capacity/v1", "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "releases": releases, "free_disk_bytes": fs.f_bavail * fs.f_frsize,
            "additional_release_bytes": additional, "job_scratch_bytes": scratch,
            "available_memory_bytes": mem_available(Path("/proc/meminfo").read_text(encoding="ascii")),
            "worker_memory_bytes": worker, "api_memory_bytes": api, "controller_memory_bytes": controller}


def prepare(source: Path, output: Path) -> dict:
    source = no_links(source)
    from check_sdd_convergence import validate, strict_json as read_ledger, GATE, method_declarations
    from check_single_origin import check

    def git(*args):
        result = subprocess.run(["git", "-C", str(source), *args], capture_output=True, check=True, timeout=30)
        if len(result.stdout) > MAX_MANIFEST or len(result.stderr) > MAX_MANIFEST:
            raise ValueError("Git inventory bound exceeded")
        return result.stdout

    if git("status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("source is not clean and committed")
    revision = git("rev-parse", "HEAD").decode("ascii").strip()
    ledger = read_ledger(source / "docs/design/convergence.json")
    validate(source, ledger)
    if errors := check(source, built=True):
        raise ValueError("single-origin source/build check failed: " + "; ".join(errors))
    tracked = set(git("ls-files", "-z").decode("utf-8").split("\0")) - {""}
    paths = {p for p in tracked if p.startswith(("app/", "deploy/")) or
             p.startswith(("scripts/", "data-pipeline/")) and p.endswith(".py")}
    paths.update({"requirements-api.txt", "docs/design/SDD.md", "docs/design/convergence.json"})
    for gates in method_declarations(source / "docs/design/SDD.md").values():
        paths.update(GATE.fullmatch(gate)["file"] for gate in gates if GATE.fullmatch(gate)["file"] in tracked)
    for record in ledger["requirements"]:
        paths.update(m["file"] for m in GATE.finditer(record["declared_gate"]) if m["file"] in tracked)
        for item in record["evidence"] + record["receipts"]:
            paths.add(item["path"])
        for item in record["receipts"]:
            paths.update(o["path"] for o in read_ledger(source / item["path"])["outputs"])
    if not paths <= tracked:
        raise ValueError("release evidence/runtime is not committed")
    required = {"deploy/service/geophysics-api.service", "deploy/service/geophysics-api.socket",
                "deploy/service/geophysics-worker.service", "deploy/service/geophysics.nginx"}
    if not required <= paths:
        raise ValueError("service configurations missing")
    receipt = copy_bundle(source, source / "frontend/dist", output, sorted(paths), revision)
    if git("rev-parse", "HEAD").decode("ascii").strip() != revision or git("status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("source revision/status changed during qualification")
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = prepare(args.source, args.output)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"Qualification failed; retain existing outputs: {exc}", file=sys.stderr)
        return 1
    print(f"Qualification bundle prepared for {receipt['source_revision']}; not activated or accepted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
