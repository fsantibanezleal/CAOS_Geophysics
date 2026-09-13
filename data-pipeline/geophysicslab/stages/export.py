from __future__ import annotations

import time
from pathlib import Path

from ..core.gate import classify_lane
from ..core.manifest import build_manifest
from ..io.formats import write_json


def run(*, case, seed: int, result: dict, metrics: dict, engines: dict, derived_dir: Path, manifests_dir: Path, stages: dict | None = None) -> dict:
    started = time.perf_counter()
    artifact_path = f"{case.id}/result.json"
    payload = {"schema": "inverse-earth.replay/v1", "case_id": case.id, "category": case.category, "method": case.method, "seed": seed, "case_description": case.description, "data": result, "metrics": metrics, "stages": stages or {}}
    size = write_json(derived_dir / artifact_path, payload)
    run_ms = (time.perf_counter() - started) * 1000.0
    gate = classify_lane(pure_python=True, wheels={"numpy"}, run_ms=run_ms, trace_bytes=size)
    manifest = build_manifest(case=case, seed=seed, artifact_path=artifact_path, artifact_bytes=size, gate=gate, metrics=metrics, engines=engines, stages=stages)
    write_json(manifests_dir / f"{case.id}.json", manifest)
    return manifest
