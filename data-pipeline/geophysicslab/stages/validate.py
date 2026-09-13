from __future__ import annotations

import json
from pathlib import Path


def run(derived_dir: Path, manifests_dir: Path, case_ids: list[str]) -> dict:
    failures: list[str] = []
    for case_id in case_ids:
        manifest_path = manifests_dir / f"{case_id}.json"
        if not manifest_path.exists():
            failures.append(f"missing manifest {case_id}")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact = derived_dir / manifest["artifact"]["path"]
        if not artifact.exists() or artifact.stat().st_size != manifest["artifact"]["bytes"]:
            failures.append(f"artifact contract drift {case_id}")
    return {"ok": not failures, "failures": failures, "n_cases": len(case_ids)}
