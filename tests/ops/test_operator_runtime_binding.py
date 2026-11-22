"""Read-only operator binding tests; no live service or scientific admission."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.skipif(os.name != "posix", reason="native physical assembly is POSIX only")

from app.operator_runtime import configured_physical_assembly, load_physical_assembly  # noqa: E402


def _write(path: Path, body: bytes, mode: int) -> None:
    path.write_bytes(body)
    path.chmod(mode)


def _fixture(tmp_path: Path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    _write(root / ".physical-writers.lock", b"\0", 0o600)
    _write(root / ".processing-worker.lock", b"0", 0o600)
    _write(root / "api.sqlite3", b"pre-existing database bytes\n", 0o600)

    release_dir = tmp_path / "release"
    release_dir.mkdir(mode=0o700)
    release_dir.chmod(0o700)
    release = {
        "schema": "geophysics.service-release/v1",
        "source_revision": "a" * 40,
        "qualification_only": True,
        "full_release_accepted": False,
        "source": {},
        "web": {},
    }
    release_raw = json.dumps(release, sort_keys=True, separators=(",", ":")).encode()
    release_path = release_dir / "release.json"
    _write(release_path, release_raw, 0o644)

    registry = {
        "schema": "geophysics.physical-operator-binding/v1",
        "release_manifest_sha256": hashlib.sha256(release_raw).hexdigest(),
        "source_policy_sha256": "b" * 64,
        "approved_manifests": {},
        "approved_installations": {},
    }
    registry_raw = json.dumps(registry, sort_keys=True, separators=(",", ":")).encode()
    registry_path = tmp_path / "operator-binding.json"
    _write(registry_path, registry_raw, 0o600)
    settings = SimpleNamespace(data_dir=root, database_path=root / "api.sqlite3",
                               release_manifest_path=release_path)
    return settings, registry_path, hashlib.sha256(registry_raw).hexdigest(), root


def test_loads_preexisting_binding_and_exact_native_metadata(tmp_path):
    settings, path, expected, root = _fixture(tmp_path)
    before = {item.name for item in root.iterdir()}
    assembly = load_physical_assembly(settings, path, expected)
    try:
        assert assembly.leases.files.root_path == root
        assert assembly.leases.identity == (
            os.stat(root / ".physical-writers.lock").st_dev,
            os.stat(root / ".physical-writers.lock").st_ino,
        )
        assert assembly.worker.identity == (
            os.stat(root / ".processing-worker.lock").st_dev,
            os.stat(root / ".processing-worker.lock").st_ino,
        )
        assert assembly.participant.source_policy == "b" * 64
        assert assembly.participant.arguments()["approved_manifests"] == {}
        assert assembly.participant.arguments()["approved_installations"] == {}
        metadata = assembly.participant.arguments()["native_metadata"]
        assert set(metadata) == {
            ".physical-writers.lock", ".processing-worker.lock",
            "api.sqlite3", "api.sqlite3-wal", "api.sqlite3-shm",
        }
        assert metadata[".physical-writers.lock"] == {
            "cap": 1, "bytes": 1, "sha256": hashlib.sha256(b"\0").hexdigest(), "required": True,
        }
        assert metadata[".processing-worker.lock"] == {
            "cap": 1, "bytes": 1, "sha256": hashlib.sha256(b"0").hexdigest(), "required": True,
        }
        assert metadata["api.sqlite3"]["required"] is True
        assert metadata["api.sqlite3"] == {
            "cap": 1024 * 1024 * 1024, "bytes": None, "sha256": None, "required": True,
        }
        assert all(metadata["api.sqlite3" + suffix] == {
            "cap": 1024 * 1024 * 1024, "bytes": None, "sha256": None, "required": False,
        } for suffix in ("-wal", "-shm"))
        assert {item.name for item in root.iterdir()} == before
    finally:
        assembly.leases.close()


def test_database_metadata_remains_valid_after_ordinary_sqlite_content_change(tmp_path):
    settings, path, expected, root = _fixture(tmp_path)
    (root / "api.sqlite3").write_bytes(b"updated database bytes\n")
    assembly = load_physical_assembly(settings, path, expected)
    try:
        metadata = assembly.participant.arguments()["native_metadata"]["api.sqlite3"]
        assert metadata["bytes"] is None and metadata["sha256"] is None
    finally:
        assembly.leases.close()


def test_refuses_tampered_registry_digest_without_creating_files(tmp_path):
    settings, path, expected, root = _fixture(tmp_path)
    path.write_bytes(path.read_bytes() + b" ")
    before = {item.name for item in root.iterdir()}
    with pytest.raises(ValueError, match="operator_registry_digest"):
        load_physical_assembly(settings, path, expected)
    assert {item.name for item in root.iterdir()} == before


@pytest.mark.parametrize("damage", ["missing", "mode", "marker", "symlink"])
def test_refuses_missing_or_unsafe_lock_without_repair(tmp_path, damage):
    settings, path, expected, root = _fixture(tmp_path)
    lock = root / ".physical-writers.lock"
    if damage == "missing":
        lock.unlink()
    elif damage == "mode":
        lock.chmod(0o640)
    elif damage == "marker":
        lock.write_bytes(b"x")
    elif damage == "symlink":
        lock.unlink()
        lock.symlink_to(root / ".processing-worker.lock")
    before = {item.name for item in root.iterdir()}
    with pytest.raises((OSError, ValueError)):
        load_physical_assembly(settings, path, expected)
    assert {item.name for item in root.iterdir()} == before
    if damage == "missing":
        assert not lock.exists()


def test_refuses_release_manifest_digest_mismatch(tmp_path):
    settings, path, expected, _ = _fixture(tmp_path)
    release = settings.release_manifest_path
    release.write_bytes(release.read_bytes() + b" ")
    with pytest.raises(ValueError, match="operator_release_manifest_binding"):
        load_physical_assembly(settings, path, expected)


def test_refuses_registry_with_incorrect_approved_manifest_key(tmp_path):
    settings, path, _, _ = _fixture(tmp_path)
    registry = json.loads(path.read_bytes())
    registry["approved_manifests"] = {"c" * 64: {"schema": "geophysics.physical-modules/v1"}}
    raw = json.dumps(registry, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(raw)
    path.chmod(0o600)
    with pytest.raises(ValueError, match="operator_manifest_digest"):
        load_physical_assembly(settings, path, hashlib.sha256(raw).hexdigest())


def test_refuses_unsafe_registry_permissions(tmp_path):
    settings, path, expected, _ = _fixture(tmp_path)
    path.chmod(stat.S_IMODE(path.stat().st_mode) | 0o020)
    with pytest.raises(ValueError, match="operator_registry_unsafe_file"):
        load_physical_assembly(settings, path, expected)


def test_entrypoint_binding_is_explicit_and_rejects_partial_environment():
    settings = SimpleNamespace()
    assert configured_physical_assembly(settings, {}) is None
    with pytest.raises(ValueError, match="operator_binding_environment_incomplete"):
        configured_physical_assembly(settings, {"GEOPHYSICS_PHYSICAL_BINDING_PATH": "/private/binding.json"})
    with pytest.raises(ValueError, match="operator_binding_environment_incomplete"):
        configured_physical_assembly(settings, {"GEOPHYSICS_PHYSICAL_BINDING_SHA256": "a" * 64})
