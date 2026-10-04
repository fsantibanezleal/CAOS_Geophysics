#!/usr/bin/env python3
"""Cheap source/build gate for the approved single-ML-VPS deployment.

Historical research and release receipts are deliberately not rewritten. This
checks active publication/build paths, not public availability or acceptance.
No network, dependency installation, scientific execution or credentials.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_FILES = (
    ".github/workflows/deploy-pages.yml",
    ".github/workflows/deploy-pages.yaml",
    "deploy/pages.md",
    "frontend/create-route-entrypoints.mjs",
    "CNAME",
    "frontend/CNAME",
    "frontend/public/CNAME",
    "frontend/public-release/CNAME",
)
PUBLICATION = re.compile(
    r"actions/(?:deploy-pages|upload-pages-artifact|configure-pages)@"
    r"|\bpages\s*:\s*write\b|\bgithub-pages\b", re.I,
)
SECONDARY_ORIGIN = re.compile(r"https?://[^\s)\"']*github\.io\b", re.I)


def check(root: Path, *, built: bool = False) -> list[str]:
    errors: list[str] = []
    for relative in FORBIDDEN_FILES:
        if (root / relative).exists():
            errors.append(f"retired deployment path exists: {relative}")

    def read(relative: str) -> str:
        try:
            return (root / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            errors.append(f"missing or unreadable required source: {relative}")
            return ""

    for workflow in sorted((root / ".github/workflows").glob("*.y*ml")):
        if PUBLICATION.search(workflow.read_text(encoding="utf-8")):
            errors.append(f"secondary publishing action/permission: {workflow.name}")

    config = read("frontend/vite.config.ts")
    # Accept exactly one unconditional root base; conditional/project/relative
    # builds must not pass just because a separate root option also exists.
    bases = re.findall(r"\bbase\s*:\s*([^,\n]+)", config)
    if len(bases) != 1 or bases[0].strip() not in {"'/'", '"/"'}:
        errors.append("Vite requires one unconditional root base")
    deployment = read("frontend/src/lib/deployment.ts")
    if ('export type DeploymentMode = "single-origin";' not in deployment
            or 'export const deploymentMode: DeploymentMode = "single-origin";' not in deployment
            or re.search(r"legacy|import\.meta\.env\.MODE|CAOS_Geophysics", deployment)):
        errors.append("runtime deployment must be unconditional single-origin without project fallback")
    try:
        scripts = json.loads(read("frontend/package.json"))["scripts"]
        if scripts.get("build") != "tsc --noEmit && node copy-data.mjs && vite build":
            errors.append("default build must use the sole root-only build pipeline")
        if scripts.get("build:single-origin") != "npm run build":
            errors.append("single-origin compatibility command must alias the default build")
        for name, command in scripts.items():
            if "build" in name and re.search(r"pages|--base|404\.html|create-route-entrypoints", command, re.I):
                errors.append(f"secondary build or duplicated route entrypoints: {name}")
    except (ValueError, KeyError, TypeError):
        errors.append("invalid frontend package scripts")
    for relative in ("README.md", "deploy/README.md"):
        if SECONDARY_ORIGIN.search(read(relative)):
            errors.append(f"active deployment documentation advertises a secondary origin: {relative}")
    uploader = read("deploy/deploy.ps1")
    release_gate = uploader.find("--require-release")
    key_read = uploader.find("[IO.File]::ReadAllBytes($Key)")
    if release_gate < 0 or key_read < 0 or release_gate >= key_read:
        errors.append("legacy uploader must require product acceptance before credentials or transfer")

    if built:
        index = read("frontend/dist/index.html")
        refs = re.findall(r'(?:src|href)=["\']([^"\']+)["\']', index)
        assets = [ref for ref in refs if "/assets/" in ref or ref.startswith("assets/")]
        if not assets or any(not ref.startswith("/assets/") for ref in assets):
            errors.append("built entry document does not use root-relative hashed assets")
        dist = root / "frontend/dist"
        for path in dist.rglob("assets"):
            if path.is_dir() and path.parent != dist:
                errors.append(f"duplicated route asset tree: {path.relative_to(dist).as_posix()}")
        if (dist / "CNAME").exists():
            errors.append("built secondary-host CNAME exists")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", type=Path, default=ROOT)
    parser.add_argument("--built", action="store_true", help="also inspect a completed frontend build")
    args = parser.parse_args()
    errors = check(args.repo.resolve(), built=args.built)
    for error in errors:
        print(f"::error::{error}")
    if not errors:
        print("single-origin source/build policy: OK (not live release acceptance)")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
