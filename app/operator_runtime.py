"""Read-only binding of pre-provisioned private physical runtime authority.

This module never provisions storage. The exact registry contract is
``geophysics.physical-operator-binding/v1``; it is bound both to the caller's
registry-byte digest and to the service ``release.json`` selected explicitly
by ``settings.release_manifest_path``. Neither binding implies scientific or
host admission.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

from app.physical_assembly import PhysicalAssembly
from app.physical_contract import byte_sha, digest, require, sha
from app.physical_leases import WriterLeases
from app.physical_participation import WorkerExclusion
from app.physical_posix import PrivateFiles
from app.profile_archive_custody import _installation


REGISTRY_SCHEMA = "geophysics.physical-operator-binding/v1"
REGISTRY_CAP = 4 * 1024 * 1024
RELEASE_CAP = 4 * 1024 * 1024
DATABASE_CAP = 1024 * 1024 * 1024
LOCKS = ((".physical-writers.lock", b"\0"), (".processing-worker.lock", b"0"))
REGISTRY_KEYS = {
    "schema", "release_manifest_sha256", "source_policy_sha256",
    "approved_manifests", "approved_installations",
}


def _strict_json(raw: bytes, *, cap: int, code: str) -> dict:
    require(type(raw) is bytes and 0 < len(raw) <= cap, code + "_size")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, code + "_duplicate_key")
            result[key] = value
        return result

    def constant(_):
        raise ValueError(code + "_constant")

    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=pairs,
                           parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
        raise ValueError(code + "_json") from None
    require(type(value) is dict, code + "_object")
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        require(nodes <= 100_000 and depth <= 24, code + "_complexity")
        if type(item) is dict:
            pending.extend((key, depth + 1) for key in item)
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            require(len(item.encode("utf-8", "strict")) <= 16_384 and "\0" not in item,
                    code + "_string")
        elif type(item) is int:
            require(abs(item) <= 2**64 - 1, code + "_integer")
        elif type(item) is float:
            require(item == item and abs(item) != float("inf"), code + "_number")
        else:
            require(item is None or type(item) is bool, code + "_type")
    return value


def _safe_absolute_file(path: Path, *, label: str, allowed_file_uids: set[int],
                        file_mode: int, directory_uids: set[int]):
    """Open relative to checked directory descriptors; return fd, stat, parent fd, name."""
    require(isinstance(path, Path) and path.is_absolute() and ".." not in path.parts,
            label + "_absolute_path")
    require(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), label + "_posix_required")
    parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    fd = None
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                            dir_fd=parent)
            info = os.fstat(child)
            current = os.stat(component, dir_fd=parent, follow_symlinks=False)
            mode = stat.S_IMODE(info.st_mode)
            require(stat.S_ISDIR(info.st_mode) and info.st_uid in directory_uids
                    and (not mode & 0o022 or mode & stat.S_ISVTX)
                    and (info.st_dev, info.st_ino) == (current.st_dev, current.st_ino),
                    label + "_unsafe_parent")
            os.close(parent)
            parent = child
        name = path.name
        fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=parent)
        info = os.fstat(fd)
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and info.st_uid in allowed_file_uids
                and stat.S_IMODE(info.st_mode) == file_mode
                and (info.st_dev, info.st_ino) == (current.st_dev, current.st_ino),
                label + "_unsafe_file")
        return fd, info, parent, name
    except BaseException:
        if fd is not None:
            os.close(fd)
        os.close(parent)
        raise


def _read_stable(fd: int, before: os.stat_result, *, cap: int, label: str) -> bytes:
    require(0 <= before.st_size <= cap, label + "_size")
    chunks, count = [], 0
    while True:
        block = os.read(fd, min(65_536, cap + 1 - count))
        if not block:
            break
        count += len(block)
        require(count <= cap, label + "_size")
        chunks.append(block)
    after = os.fstat(fd)
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
             before.st_ctime_ns, before.st_nlink) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
             after.st_ctime_ns, after.st_nlink) and count == before.st_size,
            label + "_changed")
    return b"".join(chunks)


def _check_registry(registry: dict, release_raw: bytes) -> tuple[str, dict, dict]:
    require(set(registry) == REGISTRY_KEYS and registry["schema"] == REGISTRY_SCHEMA,
            "operator_registry_schema")
    release_sha = sha(registry["release_manifest_sha256"])
    require(hashlib.sha256(release_raw).hexdigest() == release_sha,
            "operator_release_manifest_binding")
    release = _strict_json(release_raw, cap=RELEASE_CAP, code="operator_release_manifest")
    require(set(release) == {"schema", "source_revision", "qualification_only",
                             "full_release_accepted", "source", "web"}
            and release["schema"] == "geophysics.service-release/v1"
            and type(release["source_revision"]) is str
            and re.fullmatch(r"[0-9a-f]{40}", release["source_revision"]) is not None
            and release["qualification_only"] is True
            and release["full_release_accepted"] is False,
            "operator_release_manifest_schema")
    source_policy = sha(registry["source_policy_sha256"])
    manifests, installations = registry["approved_manifests"], registry["approved_installations"]
    require(type(manifests) is dict and len(manifests) <= 4096,
            "operator_approved_manifests")
    for key, manifest in manifests.items():
        sha(key)
        require(type(manifest) is dict and digest(manifest) == key,
                "operator_manifest_digest")
    require(type(installations) is dict and len(installations) <= 4096,
            "operator_approved_installations")
    from app.physical_contract import uuid
    for identifier, installation in installations.items():
        uuid(identifier)
        _installation(installation)
    return source_policy, manifests, installations


def _lock_records(files: PrivateFiles) -> tuple[dict, dict]:
    uid = os.geteuid()
    records, identities = {}, {}
    for name, marker in LOCKS:
        fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=files.fd)
        try:
            info = os.fstat(fd)
            current = os.stat(name, dir_fd=files.fd, follow_symlinks=False)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                    and info.st_size == 1 and stat.S_IMODE(info.st_mode) == 0o600
                    and info.st_uid == uid and info.st_dev == files.identity[0]
                    and (info.st_dev, info.st_ino) == (current.st_dev, current.st_ino)
                    and os.pread(fd, 2, 0) == marker and not os.get_inheritable(fd),
                    "operator_lock_refused")
            identity = dict(device=info.st_dev, inode=info.st_ino, uid=info.st_uid)
            identities[name] = identity
            records[name] = dict(cap=1, bytes=1, sha256=byte_sha(marker), required=True)
        finally:
            os.close(fd)
    files.check_root()
    return identities, records


def _database_metadata(files: PrivateFiles, settings) -> dict:
    database = Path(settings.database_path)
    require(database.is_absolute() and database.parent == files.root_path
            and database.name in ("api.sqlite3", "geophysics.sqlite3"),
            "operator_database_path")
    name = database.name
    fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
                 dir_fd=files.fd)
    try:
        info = os.fstat(fd)
        current = os.stat(name, dir_fd=files.fd, follow_symlinks=False)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o600
                and info.st_dev == files.identity[0]
                and (info.st_dev, info.st_ino) == (current.st_dev, current.st_ino),
                "operator_database_refused")
        current = os.stat(name, dir_fd=files.fd, follow_symlinks=False)
        require((current.st_dev, current.st_ino) == (info.st_dev, info.st_ino),
                "operator_database_replaced")
        # SQLite is intentionally mutable during ordinary application writes.
        # Pin its path/owner/mode/device and bound its size, but do not bind
        # startup to a content hash that becomes stale after the first commit.
        result = {name: dict(cap=DATABASE_CAP, bytes=None, sha256=None, required=True)}
    finally:
        os.close(fd)
    for suffix in ("-wal", "-shm"):
        result[name + suffix] = dict(cap=DATABASE_CAP, bytes=None, sha256=None, required=False)
    return result


def load_physical_assembly(settings, registry_path, expected_sha256) -> PhysicalAssembly:
    """Bind only verified, pre-existing operator state; perform no provisioning.

    Registry format is exact and versioned. ``settings.release_manifest_path``
    must point to the immutable service bundle's ``release.json``; its bytes
    must hash to the registry's ``release_manifest_sha256``. This identity check
    does not mark that release scientifically accepted or host-admitted.
    """
    require(os.name == "posix", "operator_posix_required")
    sha(expected_sha256)
    registry_path = Path(registry_path)
    require(registry_path.is_absolute(), "operator_registry_absolute_path")
    uid = os.geteuid()
    registry_fd, registry_info, registry_parent, registry_name = _safe_absolute_file(
        registry_path, label="operator_registry", allowed_file_uids={uid}, file_mode=0o600,
        directory_uids={0, uid})
    try:
        registry_raw = _read_stable(registry_fd, registry_info, cap=REGISTRY_CAP,
                                    label="operator_registry")
        current = os.stat(registry_name, dir_fd=registry_parent, follow_symlinks=False)
        require((current.st_dev, current.st_ino) ==
                (registry_info.st_dev, registry_info.st_ino), "operator_registry_replaced")
        require(hashlib.sha256(registry_raw).hexdigest() == expected_sha256,
                "operator_registry_digest")
    finally:
        os.close(registry_fd)
        os.close(registry_parent)
    registry = _strict_json(registry_raw, cap=REGISTRY_CAP, code="operator_registry")

    release_path = getattr(settings, "release_manifest_path", None)
    require(isinstance(release_path, Path) and release_path.is_absolute(),
            "operator_release_manifest_path_required")
    release_fd, release_info, release_parent, release_name = _safe_absolute_file(
        release_path, label="operator_release_manifest", allowed_file_uids={0, uid},
        file_mode=0o644, directory_uids={0, uid})
    try:
        release_raw = _read_stable(release_fd, release_info, cap=RELEASE_CAP,
                                   label="operator_release_manifest")
        current = os.stat(release_name, dir_fd=release_parent, follow_symlinks=False)
        require((current.st_dev, current.st_ino) ==
                (release_info.st_dev, release_info.st_ino), "operator_release_manifest_replaced")
    finally:
        os.close(release_fd)
        os.close(release_parent)
    source_policy, manifests, installations = _check_registry(registry, release_raw)

    root = Path(settings.data_dir)
    files = PrivateFiles(root)
    leases = None
    try:
        identities, lock_metadata = _lock_records(files)
        metadata = {**lock_metadata, **_database_metadata(files, settings)}
        leases = WriterLeases(root, **identities[".physical-writers.lock"])
        worker = WorkerExclusion(leases, **identities[".processing-worker.lock"])
        assembly = PhysicalAssembly(leases, worker, source_policy_sha256=source_policy,
            approved_manifests=manifests, approved_installations=installations,
            native_metadata=metadata)
        files.close()
        return assembly
    except BaseException:
        files.close()
        if leases is not None:
            leases.close()
        raise


def load_physical_assembly_from_env(settings) -> PhysicalAssembly:
    """Explicit environment wrapper; both immutable binding inputs are required."""
    path = os.environ.get("GEOPHYSICS_PHYSICAL_BINDING_PATH")
    expected = os.environ.get("GEOPHYSICS_PHYSICAL_BINDING_SHA256")
    require(bool(path) and bool(expected), "operator_binding_environment_required")
    return load_physical_assembly(settings, Path(path), expected)


def configured_physical_assembly(settings, environ=None) -> PhysicalAssembly | None:
    """Load when explicitly bound; reject partial configuration, never guess."""
    environ = os.environ if environ is None else environ
    path = environ.get("GEOPHYSICS_PHYSICAL_BINDING_PATH")
    expected = environ.get("GEOPHYSICS_PHYSICAL_BINDING_SHA256")
    require(bool(path) == bool(expected), "operator_binding_environment_incomplete")
    if not path:
        return None
    return load_physical_assembly(settings, Path(path), expected)
