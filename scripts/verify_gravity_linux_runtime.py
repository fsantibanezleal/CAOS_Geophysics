"""Verify the installed Linux CPU gravity runtime against its source epoch."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = ROOT / "docs/design/features/m02-prism-operator/runtime-pins-linux-cp312.json"
REQUIREMENTS_PATH = ROOT / "requirements-gravity-runtime.txt"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def verify() -> dict:
    pin_bytes = PIN_PATH.read_bytes()
    pin = json.loads(pin_bytes)
    if pin.get("schema") != "geophysics.prism-linux-runtime-pins/v1":
        raise ValueError("gravity_runtime_manifest_schema")
    expected_python = tuple(int(part) for part in pin.get("python", "").split("."))
    if (sys.implementation.name != "cpython" or sys.version_info[:3] != expected_python
            or sys.platform != "linux" or platform.machine().lower() != "x86_64"):
        raise ValueError("gravity_runtime_python_platform_unregistered")
    requirements_sha = digest(REQUIREMENTS_PATH)
    if requirements_sha != pin.get("requirements_sha256"):
        raise ValueError("gravity_runtime_requirements_changed")

    versions = pin.get("versions")
    if type(versions) is not dict or not versions:
        raise ValueError("gravity_runtime_versions_missing")
    actual_versions = {name: importlib.metadata.version(name) for name in versions}
    if actual_versions != versions:
        raise ValueError("gravity_runtime_package_versions_changed")

    sources = pin.get("targeted_source_sha256")
    if type(sources) is not dict or not sources:
        raise ValueError("gravity_runtime_source_pins_missing")
    measured = {}
    for relative, expected in sorted(sources.items()):
        if (type(relative) is not str or relative.startswith("/") or "\\" in relative
                or ".." in Path(relative).parts or type(expected) is not str
                or len(expected) != 64):
            raise ValueError("gravity_runtime_source_pin_invalid")
        distribution_name = relative.split("/", 1)[0]
        distribution = importlib.metadata.distribution(distribution_name)
        files = {str(item).replace("\\", "/") for item in distribution.files or ()}
        if relative not in files:
            raise ValueError("gravity_runtime_source_member_missing:" + relative)
        actual = digest(Path(distribution.locate_file(relative)))
        if actual != expected:
            raise ValueError("gravity_runtime_source_hash_changed:" + relative)
        measured[relative] = actual

    wheel_tags = {}
    for name in ("simpeg", "pymatsolver"):
        wheel = importlib.metadata.distribution(name).read_text("WHEEL") or ""
        tags = [line.partition(":")[2].strip() for line in wheel.splitlines()
                if line.startswith("Tag:")]
        if tags != ["py3-none-any"]:
            raise ValueError("gravity_runtime_expected_pure_python_wheel:" + name)
        wheel_tags[name] = tags[0]

    return {
        "schema": "geophysics.gravity-linux-runtime-verification/v1",
        "source_epoch": pin["source_epoch"],
        "python": platform.python_version(),
        "machine": platform.machine().lower(),
        "package_versions": actual_versions,
        "requirements_sha256": requirements_sha,
        "runtime_pin_manifest_sha256": hashlib.sha256(pin_bytes).hexdigest(),
        "installed_source_files_verified": len(measured),
        "pure_python_wheels": wheel_tags,
        "ml_vps_host_admitted": False,
        "public_activation": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True, separators=(",", ":")))
