#!/usr/bin/env python3
"""Check or write the compact readiness record for the committed experiment catalogue.

This gate checks structural availability and declared byte sizes. It does not hash every large result,
validate numerical claims, qualify a field dataset, or certify a deployment. Those are separate gates.
Standard library only. Usage: python scripts/check_readiness.py [--write]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = Path("data/derived/v2/catalog.json")
READINESS = Path("data/derived/readiness.json")
VERSION = re.compile(r"^\d+\.\d{2}\.\d{3}$")


def document(root: Path) -> dict:
    catalog_path = root / CATALOG
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(catalog, dict) or catalog.get("schema") != "inverse-earth.catalog/v2":
        raise ValueError(f"{CATALOG.as_posix()}: expected inverse-earth.catalog/v2")
    if not isinstance(catalog.get("cases"), list):
        raise ValueError(f"{CATALOG.as_posix()}: cases must be an array")
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not VERSION.fullmatch(version):
        raise ValueError(f"VERSION: expected X.XX.XXX, found {version!r}")

    present = 0
    missing: list[str] = []
    declared_bytes = 0
    methods = 0
    variants = 0
    seen: set[str] = set()
    base = catalog_path.parent.resolve()
    for case in catalog["cases"]:
        if not isinstance(case, dict) or not isinstance(case.get("variants"), list):
            raise ValueError("catalog: every case must contain a variants array")
        for variant in case["variants"]:
            variants += 1
            if not isinstance(variant, dict) or not isinstance(variant.get("path"), str):
                raise ValueError("catalog: every variant must name an artifact path")
            rel = Path(variant["path"])
            if rel.is_absolute() or ".." in rel.parts or "\\" in variant["path"]:
                raise ValueError(f"catalog: unsafe artifact path {variant['path']!r}")
            key = rel.as_posix()
            if key in seen:
                raise ValueError(f"catalog: duplicate artifact path {key}")
            seen.add(key)
            if not re.fullmatch(r"[0-9a-f]{64}", str(variant.get("sha256", ""))):
                raise ValueError(f"catalog: invalid SHA-256 for {key}")
            size = variant.get("bytes")
            if type(size) is not int or size < 1:
                raise ValueError(f"catalog: invalid declared byte count for {key}")
            declared_bytes += size
            methods += len(variant.get("methods", {})) if isinstance(variant.get("methods"), dict) else 0
            path = (base / rel).resolve()
            if not path.is_relative_to(base):
                raise ValueError(f"catalog: artifact escapes catalogue root: {key}")
            if not path.is_file():
                missing.append(key)
            elif path.stat().st_size != size:
                missing.append(key + " (declared byte count differs)")
            else:
                present += 1

    state = "missing" if present == 0 else "partial" if missing or catalog.get("complete") is not True else "available"
    return {
        "schema": "inverse-earth.readiness/v1",
        "product_version": version,
        "catalog": {
            "schema": catalog["schema"],
            "version": catalog.get("version", ""),
            "sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
            "complete": catalog.get("complete") is True,
        },
        "counts": {"cases": len(catalog["cases"]), "variants": variants, "method_results": methods},
        "artifacts": {"present": present, "missing": missing, "declared_bytes": declared_bytes},
        "state": state,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true", help="write the deterministic readiness record")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    output = root / READINESS
    try:
        fresh = document(root)
        expected = json.dumps(fresh, separators=(",", ":"), ensure_ascii=False) + "\n"
        if args.write:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(expected, encoding="utf-8", newline="\n")
            print(f"readiness: wrote {READINESS.as_posix()} ({fresh['state']})")
            return 0
        if not output.is_file():
            print(f"readiness: {READINESS.as_posix()} is missing; run python scripts/check_readiness.py --write")
            return 1
        actual = output.read_text(encoding="utf-8")
        if actual != expected:
            print(f"readiness: stale; run python scripts/check_readiness.py --write")
            return 1
        print(f"readiness: current ({fresh['state']}; {fresh['counts']['cases']} cases, "
              f"{fresh['counts']['variants']} variants, {fresh['artifacts']['present']} artifacts present)")
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"readiness: invalid ({exc})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
