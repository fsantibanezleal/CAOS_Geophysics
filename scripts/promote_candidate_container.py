"""Promote a complete, independently fingerprinted candidate into the release container.

The catalog and release container are rebuilt from the verified candidate runs.
Scientific runs, learned weights, and every other candidate byte are hash-bound
in promotion.json.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(ROOT / "scripts"))
from artifact_versions import CONTAINER_VERSION, RUN_VERSIONS  # noqa: E402
from verify_candidate_release import verify_candidate_release  # noqa: E402
from catalog import assemble as assemble_catalog  # noqa: E402


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inventory(root: Path) -> dict[str, dict[str, int | str]]:
    inventory = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"candidate contains a symbolic link: {path.relative_to(root)}")
        if path.is_file():
            inventory[path.relative_to(root).as_posix()] = {"bytes": path.stat().st_size, "sha256": _hash(path)}
    return inventory


def promote(source: Path, destination: Path) -> dict[str, int | str]:
    source = source.resolve()
    destination = destination.resolve()
    experiments = (ROOT / "data" / "experiments").resolve()
    if not source.is_dir() or source == destination:
        raise ValueError("source must be a distinct candidate directory")
    if not destination.is_relative_to(experiments) or destination.exists():
        raise ValueError("destination must be a new ignored child of data/experiments")
    source_catalog = json.loads((source / "catalog.json").read_text(encoding="utf-8"))
    source_release = json.loads((source / "release.json").read_text(encoding="utf-8"))
    source_version = source_catalog.get("version")
    if source_version == CONTAINER_VERSION or source_version not in RUN_VERSIONS:
        raise ValueError("source must use a known earlier container version")
    if source_release.get("version") != source_version:
        raise ValueError("source catalog and release container versions disagree")
    validated = verify_candidate_release(source, container_version=source_version)
    if validated["cases"] != 20 or validated["runs"] != 120:
        raise ValueError("only a complete 20-case/120-run candidate may be promoted")

    before = _inventory(source)
    edi_source = ROOT / "data" / "derived" / "v2" / "edi"
    if not (edi_source / "manifest.json").is_file():
        raise ValueError("current validated EDI evidence bundle is missing")
    for name, receipt in _inventory(edi_source).items():
        before[f"edi/{name}"] = receipt
    shutil.copytree(source, destination)
    shutil.copytree(edi_source, destination / "edi")
    catalog_path = destination / "catalog.json"
    release_path = destination / "release.json"
    # Summary fields evolved with the release contract (for example survey
    # display bounds). Reassemble both containers from these exact validated
    # arrays instead of relabelling a stale catalog header.
    assemble_catalog(destination)
    promoted_catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    promoted_release = json.loads(release_path.read_text(encoding="utf-8"))
    if promoted_catalog.get("version") != CONTAINER_VERSION or promoted_release.get("version") != CONTAINER_VERSION:
        raise ValueError("catalog assembly did not produce the current release container")
    preserved = {name: receipt for name, receipt in before.items() if name not in {"catalog.json", "release.json"}}
    after_preserved = {name: receipt for name, receipt in _inventory(destination).items()
                       if name not in {"catalog.json", "release.json"}}
    if after_preserved != preserved:
        raise ValueError("a scientific or supporting candidate byte changed during container promotion")

    manifest = {
        "schema": "inverse-earth/container-promotion/v1",
        "source_container": source_version,
        "target_container": CONTAINER_VERSION,
        "source_candidate": source.name,
        "source_catalog_sha256": before["catalog.json"]["sha256"],
        "source_release_sha256": before["release.json"]["sha256"],
        "target_catalog_sha256": _hash(catalog_path),
        "target_release_sha256": _hash(release_path),
        "preserved_files": preserved,
        "validated_before_copy": validated,
        "promoted_at": datetime.now(timezone.utc).isoformat(),
    }
    (destination / "promotion.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    result = verify_candidate_release(destination)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        result = promote(args.source, args.destination)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print("Container promotion verified: " + ", ".join(f"{key}={value}" for key, value in result.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
