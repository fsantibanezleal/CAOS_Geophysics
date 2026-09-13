"""Measured live versus precompute classification."""
from __future__ import annotations

LIVE_WHEELS = {"numpy"}
RUN_MS_GATE = 1500.0
TRACE_BYTES_GATE = 512 * 1024


def classify_lane(*, pure_python: bool, wheels: set[str], run_ms: float, trace_bytes: int) -> dict:
    reasons: list[str] = []
    live = pure_python
    if not pure_python:
        reasons.append("native or accelerator dependency")
    extra = set(wheels) - LIVE_WHEELS
    if extra:
        live = False
        reasons.append(f"browser lane excludes {sorted(extra)}")
    if run_ms > RUN_MS_GATE:
        live = False
        reasons.append(f"runtime exceeds {RUN_MS_GATE:.0f} ms")
    if trace_bytes > TRACE_BYTES_GATE:
        live = False
        reasons.append(f"artifact exceeds {TRACE_BYTES_GATE} bytes")
    return {
        "lane": "live" if live else "precompute",
        "pure_python": pure_python,
        "wheels": sorted(wheels),
        "trace_bytes": trace_bytes,
        "run_ms_budget": RUN_MS_GATE,
        "trace_bytes_budget": TRACE_BYTES_GATE,
        "reasons": reasons,
    }
