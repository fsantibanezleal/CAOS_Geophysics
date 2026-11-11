"""Notebook-facing runner for a bounded, reproducible M10 FWI refit.

The scientific solver stays in the GPU-capable pipeline environment. This
small adapter lets the CPU notebook environment request a real product solve
without importing a second PyTorch/Deepwave stack into its kernel.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
import hashlib


def _root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parent.parent, *here.parents):
        if (candidate / "data/derived/v2/catalog.json").is_file():
            return candidate
    raise FileNotFoundError("Cannot locate the CAOS Geophysics repository root")


def load_case(case_id: str = "FWI_LAYERED") -> dict:
    """Load one immutable reference run only after checking its catalog hash."""
    if case_id not in {"FWI_LAYERED", "FWI_FAULT", "FWI_CYCLE_SKIP", "FWI_NOISY"}:
        raise ValueError("Unknown M10 case identifier")
    root = _root()
    catalog = json.loads((root / "data/derived/v2/catalog.json").read_text(encoding="utf-8"))
    entry = next(item for item in catalog["cases"] if item["id"] == case_id)
    variant = next(item for item in entry["variants"] if item["id"] == "reference")
    path = root / "data/derived/v2" / variant["path"]
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) != variant["bytes"] or digest != variant["sha256"]:
        raise ValueError("Catalogued M10 input failed its byte-count or SHA-256 check")
    result = json.loads(raw)
    if result.get("id") != case_id or result.get("variant") != "reference":
        raise ValueError("Catalog entry does not identify the requested reference artifact")
    return {"root": root, "run": result, "sha256": digest}


def summarize_case(result: dict) -> list[dict]:
    """Summarize matched FWI schedules without selecting on withheld receivers."""
    rows = []
    for name, method in result["methods"].items():
        metrics = method["metrics"]
        rows.append({
            "method": name,
            "model_rmse_ratio_to_start": metrics["model_rmse_ratio"],
            "fitted_wrms": metrics["active_wrms"],
            "withheld_wrms": metrics["withheld_wrms"],
            "status": method.get("evaluation", {}).get("status", "short interactive replay"),
        })
    return rows


def compare_schedules(result: dict) -> dict:
    """Compare schedule outputs on the same case, retaining the holdout split."""
    methods = result.get("methods", {})
    required = {"fwi-l2", "fwi-multiscale"}
    if set(methods) != required:
        raise ValueError(f"Expected matched schedules {sorted(required)}")
    full = methods["fwi-l2"]["metrics"]
    multi = methods["fwi-multiscale"]["metrics"]
    return {
        "model_rmse_ratio_change": multi["model_rmse_ratio"] - full["model_rmse_ratio"],
        "fitted_wrms_change": multi["active_wrms"] - full["active_wrms"],
        "withheld_wrms_change": multi["withheld_wrms"] - full["withheld_wrms"],
        "withheld_used_for_selection": False,
    }


def run_case(case_id: str = "FWI_LAYERED", *, iterations: int = 1,
             output_directory: str | Path | None = None) -> dict:
    """Run both matched M10 schedules on one catalogued case.

    ``iterations`` is the L-BFGS call budget per spatial stage. The default
    1-call replay is a fast method inspection, not a substitute for the
    committed 28-call reference runs. Output is written outside the checkout.
    """
    allowed = {"FWI_LAYERED", "FWI_FAULT", "FWI_CYCLE_SKIP", "FWI_NOISY"}
    if case_id not in allowed:
        raise ValueError(f"case_id must be one of {sorted(allowed)}")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or not 1 <= iterations <= 4:
        raise ValueError("iterations must be an integer from 1 through 4 for the interactive lesson")

    root = _root()
    configured_python = os.environ.get("CAOS_PIPELINE_PYTHON")
    pipeline_python = Path(configured_python).expanduser() if configured_python else root / ".venv-pipeline/Scripts/python.exe"
    if not configured_python and not pipeline_python.is_file() and os.name != "nt":
        pipeline_python = root / ".venv-pipeline/bin/python"
    if not pipeline_python.is_file():
        raise FileNotFoundError(
            "The FWI lesson needs the repository pipeline environment; run scripts/setup.ps1 -Gpu"
        )

    if output_directory is None:
        base = Path(os.environ.get("CAOS_TEMP_ROOT", tempfile.gettempdir())) / "m10-fwi-lesson"
    else:
        base = Path(output_directory)
    base.mkdir(parents=True, exist_ok=True)
    output = base / f"{case_id.lower()}-{iterations}-{uuid.uuid4().hex}.json"
    worker = root / "scripts/run_m10_lesson_worker.py"
    completed = subprocess.run(
        [str(pipeline_python), str(worker), "--repo-root", str(root),
         "--case-id", case_id, "--iterations", str(iterations), "--output", str(output)],
        cwd=root, check=False, capture_output=True, text=True, timeout=900,
    )
    if completed.returncode:
        raise RuntimeError(
            "M10 refit failed in the pipeline environment:\n"
            f"{completed.stdout[-4000:]}\n{completed.stderr[-4000:]}"
        )
    result = json.loads(output.read_text(encoding="utf-8"))
    result["worker_output"] = str(output)
    return result
