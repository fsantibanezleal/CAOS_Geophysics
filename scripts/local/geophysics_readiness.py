"""Strict admission for the geophysics v2 artifact catalog and readiness record."""
from __future__ import annotations

import json
import importlib.util
from pathlib import Path


def validate(root: Path) -> bool:
    """Recompute readiness and require the complete, exact 20-case release inventory."""
    checker = Path(__file__).resolve().parents[1] / "check_readiness.py"
    spec = importlib.util.spec_from_file_location("geophysics_readiness_source", checker)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load the product readiness computation")
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    root = Path(root).resolve()
    fresh = source.document(root)
    if fresh["state"] != "available":
        raise ValueError(f"catalog is not complete: {fresh['state']}")
    counts = fresh["counts"]
    artifacts = fresh["artifacts"]
    if counts.get("cases") != 20 or counts.get("variants") != 120:
        raise ValueError("catalog must contain the complete 20-case, 120-variant inventory")
    if artifacts.get("present") != 120 or artifacts.get("missing"):
        raise ValueError("all 120 catalog artifacts must be present with declared byte sizes")
    path = root / "data/derived/readiness.json"
    expected = json.dumps(fresh, separators=(",", ":"), ensure_ascii=False) + "\n"
    if not path.is_file() or path.read_text(encoding="utf-8") != expected:
        raise ValueError("readiness.json is missing, stale, or not canonically serialized")
    return True
