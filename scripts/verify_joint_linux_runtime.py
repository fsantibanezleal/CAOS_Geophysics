"""Read-only verifier for the pinned local M11 Linux CPU source epoch."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
M11_PATH = ROOT / "docs/design/features/joint-survey-inversion/runtime-linux-cp312.json"
M02_PATH = ROOT / "docs/design/features/m02-prism-operator/runtime-pins-linux-cp312.json"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def verify() -> dict:
    m11 = json.loads(M11_PATH.read_text(encoding="utf-8"))
    m02 = json.loads(M02_PATH.read_text(encoding="utf-8"))
    if m11.get("schema") != "geophysics.m11-linux-runtime-pins/v1":
        raise ValueError("m11_runtime_schema")
    if m02.get("schema") != "geophysics.prism-linux-runtime-pins/v1":
        raise ValueError("m02_runtime_schema")
    inherited = m11["inherited_potential_engine_manifest"]
    if (inherited["path"] != "../m02-prism-operator/runtime-pins-linux-cp312.json"
            or digest(M02_PATH) != inherited["sha256"]):
        raise ValueError("m11_inherited_runtime_manifest_changed")
    if (sys.implementation.name != "cpython" or sys.version_info[:3] != (3, 12, 10)
            or sys.platform != "linux" or platform.machine().lower() != "x86_64"):
        raise ValueError("m11_linux_runtime_tuple_unregistered")

    expected_versions = dict(m11["engine_versions"])
    expected_versions.update(m11["independent_oracle_versions"])
    actual_versions = {name: importlib.metadata.version(name) for name in expected_versions}
    if actual_versions != expected_versions:
        raise ValueError("m11_linux_runtime_package_versions_changed")

    expected_sources = dict(m02["targeted_source_sha256"])
    expected_sources.update(m11["m11_and_magnetic_source_sha256"])
    measured = {}
    for relative, expected in sorted(expected_sources.items()):
        package = relative.split("/", 1)[0]
        path = Path(importlib.metadata.distribution(package).locate_file(relative))
        actual = digest(path)
        if actual != expected:
            raise ValueError(f"m11_linux_installed_source_changed:{relative}")
        measured[relative] = actual

    return {
        "schema": "geophysics.m11-linux-runtime-verification/v1",
        "source_epoch": m11["source_epoch"],
        "python": platform.python_version(),
        "machine": platform.machine().lower(),
        "package_versions": actual_versions,
        "installed_source_files_verified": len(measured),
        "runtime_pin_manifest_sha256": digest(M11_PATH),
        "ml_vps_host_admitted": False,
        "public_activation": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True, separators=(",", ":")))
