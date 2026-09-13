"""Contract 2: immutable processing artifact metadata consumed by the web."""
from __future__ import annotations

from .. import __version__

MANIFEST_SCHEMA = "inverse-earth.manifest/v1"
INDEX_SCHEMA = "inverse-earth.index/v1"


def build_manifest(*, case, seed: int, artifact_path: str, artifact_bytes: int, gate: dict, metrics: dict, engines: dict, stages: dict | None = None) -> dict:
    return {
        "schema": MANIFEST_SCHEMA,
        "case_id": case.id,
        "category": case.category,
        "method": case.method,
        "real_or_synthetic": case.real_or_synthetic,
        "engine": {"package": "geophysicslab", "version": __version__, "model": "multi-physics evidence cartography"},
        "params": {
            "anomaly": case.anomaly, "depth": case.depth, "conductivity": case.conductivity,
            "noise": case.noise, "frequency": case.frequency, "angle_deg": case.angle_deg,
        },
        "seed": seed,
        "artifact": {"path": artifact_path, "format": "json", "schema": "inverse-earth.replay/v1", "bytes": artifact_bytes},
        "lane": gate["lane"],
        "gate": gate,
        "metrics": metrics,
        "engines": engines,
        "stages": stages or {},
        "provenance": {"source": "original seeded synthetic generator", "license": "CC-BY-4.0 content; Apache-2.0 code"},
    }


def build_index(entries: list[dict]) -> dict:
    return {"schema": INDEX_SCHEMA, "engine_version": __version__, "n_cases": len(entries), "cases": sorted(entries, key=lambda x: x["case_id"])}
