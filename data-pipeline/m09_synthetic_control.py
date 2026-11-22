"""Reproduce the authored M09 Dijkstra travel-time control for the course notebook.

This is a synthetic method control, not a field-data loader or a field-validation
receipt. It uses the same bounded product inverse core as the pinned M09 run.
The caller supplies a repository root and an output path under CAOS_TEMP_ROOT.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def run(repository_root: Path, output_path: Path, *, seed: int = 20261027) -> dict:
    """Generate a two-layer refraction survey, fit it, and save auditable arrays."""
    root = repository_root.resolve(strict=True)
    output = output_path.resolve()
    temp_root = Path(os.environ["CAOS_TEMP_ROOT"]).resolve(strict=True)
    if temp_root not in output.parents or output.suffix.lower() != ".json":
        raise ValueError("M09 control output must be a JSON file below CAOS_TEMP_ROOT")
    pipeline = root / "data-pipeline"
    if not (pipeline / "traveltime.py").is_file():
        raise ValueError("repository root does not contain the travel-time pipeline")

    import numpy as np
    import pygimli as pg
    from pygimli.physics import traveltime as tt

    sys.path.insert(0, str(pipeline))
    import traveltime as product

    np.random.seed(seed)
    pg.utils.noCache(True)
    pg.setThreadCount(1)

    x = np.arange(15, dtype=float) * 10.0
    sensors = np.column_stack([x, np.zeros_like(x)])
    pairs = np.asarray(
        [(shot, receiver) for shot in range(15) for receiver in range(15)
         if shot != receiver],
        dtype=int,
    )
    scheme = tt.DataContainerTT()
    for point in sensors:
        scheme.createSensor(point)
    scheme.resize(len(pairs))
    scheme["s"], scheme["g"] = pairs[:, 0], pairs[:, 1]

    truth_mesh = pg.meshtools.createGrid(
        x=np.arange(-20, 181, 5.0), y=np.arange(-50, 1, 2.5)
    )
    truth_centers = np.asarray(
        [[cell.center().x(), cell.center().y()] for cell in truth_mesh.cells()]
    )
    truth_velocity = np.where(truth_centers[:, 1] < -15, 4500.0, 2500.0)
    body = (((truth_centers[:, 0] - 70) / 18) ** 2
            + ((truth_centers[:, 1] + 30) / 7) ** 2 < 1)
    truth_velocity[body] = 5200.0
    arrivals = np.asarray(
        tt.TravelTimeManager().simulate(
            mesh=truth_mesh, scheme=scheme, vel=truth_velocity,
            secNodes=3, returnArray=True,
        ),
        dtype=float,
    )
    scheme["t"] = arrivals

    survey = product.Survey(sensors, pairs, arrivals)
    splits = product.shot_splits(survey, policy="supplied-whole-shot/v1")
    fit = product._invert_once(
        tt, scheme, survey, splits["interleaved"],
        product.INVERSE_OPTIONS, retain_arrays=True,
    )
    centers = np.asarray(fit["model_cell_center_xy_m"], dtype=float)
    known = np.where(centers[:, 1] < -15, 4500.0, 2500.0)
    body = (((centers[:, 0] - 70) / 18) ** 2
            + ((centers[:, 1] + 30) / 7) ** 2 < 1)
    known[body] = 5200.0

    result = {
        "schema": "inverse-earth.notebook-m09-synthetic-control/v1",
        "source_kind": "authored synthetic; no provider bytes",
        "seed": seed,
        "truth_model": {
            "background_cap_m_s": 2500.0,
            "substrate_m_s": 4500.0,
            "body_m_s": 5200.0,
            "interface_y_m": -15.0,
        },
        "shot_count": 15,
        "pick_count": int(len(arrivals)),
        "held_shot_count": int(len(splits["interleaved"]["held_shots"])),
        "held_pick_count": int(len(splits["interleaved"]["held_rows"])),
        "heldout_rmse_ms": round(float(fit["heldout_rmse_ms"]), 2),
        "homogeneous_baseline_heldout_rmse_ms": round(
            float(fit["baseline_heldout_rmse_ms"]), 5
        ),
        "heldout_improvement_fraction": round(float(fit["heldout_improvement"]), 2),
        "chi2_assumed_weights": round(float(fit["chi2_assumed_weights"]), 2),
        "iterations": fit["iterations"],
        "stopping_reason": fit["stopping_reason"],
        "coverage_nonzero_cell_fraction": round(
            float(fit["coverage_nonzero_cell_fraction"]), 5
        ),
        "velocity_truth_rmse_m_s": round(
            float(np.sqrt(np.mean((np.asarray(fit["model_velocity_m_s"]) - known) ** 2))), 0
        ),
        "cell_centers_xy_m": centers.tolist(),
        "true_velocity_m_s": known.tolist(),
        "recovered_velocity_m_s": np.asarray(
            fit["model_velocity_m_s"], dtype=float
        ).tolist(),
        "training_raypath_coverage_m_per_cell": np.asarray(
            fit["raypath_coverage_m_per_cell"], dtype=float
        ).tolist(),
        "limitations": [
            "Synthetic travel times are generated with pyGIMLi; not field evidence.",
            "The assumed pick weights are not instrument-calibrated.",
            "Ray coverage is path-length support, not resolution or uniqueness.",
            "This control does not change the provider-linked M09 field verdict.",
        ],
    }
    arrays = (
        result["cell_centers_xy_m"], result["true_velocity_m_s"],
        result["recovered_velocity_m_s"],
        result["training_raypath_coverage_m_per_cell"],
    )
    if len({len(values) for values in arrays}) != 1:
        raise RuntimeError("M09 control arrays do not share the parameter-mesh shape")
    if result["shot_count"] != 15 or result["held_pick_count"] <= 0:
        raise RuntimeError("M09 control did not produce the declared whole-shot holdout")
    if not np.isfinite(result["heldout_rmse_ms"] + result["velocity_truth_rmse_m_s"]):
        raise RuntimeError("M09 control produced a non-finite scientific metric")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, allow_nan=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return result


def execute(repository_root: Path) -> dict:
    """Run the control in the pinned pyGIMLi environment and clean its temp output."""
    root = repository_root.resolve(strict=True)
    temp_root = Path(os.environ["CAOS_TEMP_ROOT"]).resolve(strict=True)
    engine_root = Path(os.environ.get("CAOS_SOURCE_ROOT", root)).resolve(strict=True)
    candidates = (
        engine_root / ".venv-ert" / "Scripts" / "python.exe",
        engine_root / ".venv-ert" / "bin" / "python",
    )
    engine = next((path for path in candidates if path.is_file()), None)
    if engine is None:
        raise RuntimeError("The isolated pinned M09 pyGIMLi environment is required")

    child_env = os.environ.copy()
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        child_env[name] = "1"
    with tempfile.TemporaryDirectory(prefix="m09-synthetic-", dir=temp_root) as folder:
        output = Path(folder) / "control.json"
        command = [
            str(engine), str(Path(__file__).resolve()), "--repository-root", str(root),
            "--output", str(output),
        ]
        completed = subprocess.run(
            command, cwd=root, env=child_env, capture_output=True,
            text=True, timeout=240,
        )
        if completed.returncode:
            raise RuntimeError("M09 synthetic solve failed: " + completed.stderr[-2500:])
        return json.loads(output.read_text(encoding="utf-8"))


def execute_user_survey(repository_root: Path, raw: bytes, source_record: dict) -> dict:
    """Run bounded, rights-declared SGT bytes through the isolated M09 user pipeline."""
    if type(raw) is not bytes or not 0 < len(raw) <= 1_000_000:
        raise ValueError("M09 user SGT bytes exceed the one-megabyte input boundary")
    root = repository_root.resolve(strict=True)
    temp_root = Path(os.environ["CAOS_TEMP_ROOT"]).resolve(strict=True)
    engine_root = Path(os.environ.get("CAOS_SOURCE_ROOT", root)).resolve(strict=True)
    candidates = (
        engine_root / ".venv-ert" / "Scripts" / "python.exe",
        engine_root / ".venv-ert" / "bin" / "python",
    )
    engine = next((path for path in candidates if path.is_file()), None)
    if engine is None:
        raise RuntimeError("The isolated pinned M09 pyGIMLi environment is required")

    child_env = os.environ.copy()
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        child_env[name] = "1"
    with tempfile.TemporaryDirectory(prefix="m09-user-run-", dir=temp_root) as folder:
        work = Path(folder)
        source = work / "source.sgt"
        metadata = work / "source.json"
        output = work / "result.json"
        source.write_bytes(raw)
        metadata.write_text(
            json.dumps(source_record, ensure_ascii=False, allow_nan=False),
            encoding="utf-8",
        )
        command = [
            str(engine), str(Path(__file__).resolve()), "--repository-root", str(root),
            "--user-input", str(source), "--source-record", str(metadata),
            "--output", str(output),
        ]
        completed = subprocess.run(
            command, cwd=root, env=child_env, capture_output=True,
            text=True, timeout=900,
        )
        if completed.returncode:
            raise RuntimeError("M09 user-data solve failed: " + completed.stderr[-3500:])
        return json.loads(output.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261027)
    parser.add_argument("--user-input", type=Path)
    parser.add_argument("--source-record", type=Path)
    args = parser.parse_args()
    if bool(args.user_input) != bool(args.source_record):
        parser.error("--user-input and --source-record must be provided together")
    if args.user_input:
        sys.path.insert(0, str(args.repository_root.resolve() / "data-pipeline"))
        import traveltime

        source_record = json.loads(args.source_record.read_text(encoding="utf-8"))
        result = traveltime.run_user_survey(args.user_input, source=source_record)
        args.output.write_text(
            json.dumps(result, allow_nan=False, separators=(",", ":")),
            encoding="utf-8",
        )
        print(json.dumps({key: result.get(key) for key in (
            "source_id", "source_sha256", "rights_decision", "inverse_status",
            "inverse_reason", "qc",
        )}, allow_nan=False, sort_keys=True))
        return
    result = run(args.repository_root, args.output, seed=args.seed)
    summary = {
        key: result[key]
        for key in (
            "source_kind", "seed", "shot_count", "pick_count", "held_shot_count",
            "held_pick_count", "heldout_rmse_ms",
            "homogeneous_baseline_heldout_rmse_ms", "heldout_improvement_fraction",
            "chi2_assumed_weights", "iterations", "stopping_reason",
            "coverage_nonzero_cell_fraction", "velocity_truth_rmse_m_s",
        )
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
