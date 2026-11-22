"""Run the deterministic M07 pyGIMLi synthetic control and emit its full local receipt.

This is a controlled numerical experiment, not Slagdump field data. The forward
survey is simulated on an irregular surface above a finite resistivity body;
the production M07 inversion implementation then fits the generated readings.
Run only in the isolated environment from requirements-ert.txt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np
import pygimli as pg
from pygimli.physics import ert as pg_ert

import ert

# Keep pyGIMLi temporary mesh and solver files on the configured device volume.
_temp_root = os.environ.get("CAOS_TEMP_ROOT")
if _temp_root:
    _temp_path = Path(_temp_root).expanduser().resolve()
    if not _temp_path.is_dir():
        raise RuntimeError(f"CAOS_TEMP_ROOT is not a directory: {_temp_path}")
    tempfile.tempdir = str(_temp_path)

# Fix pyGIMLi's worker count so the controlled receipt is stable across runs.
pg.setThreadCount(1)


def build(*, noise_seed: int = 20261027) -> tuple[bytes, dict]:
    """Create a synthetic topographic Wenner survey and its known forward model."""
    pg.utils.noCache(True)
    count = 28
    x = np.arange(count, dtype=float) * 2.0
    z = 0.65 * np.sin(x / 8.0) + 0.18 * np.sin(x / 3.7) + 0.008 * x
    scheme = pg.DataContainerERT()
    for xx, zz in zip(x, z):
        scheme.createSensor([float(xx), float(zz), 0.0])
    for spacing in (1, 2, 3, 4):
        for a in range(count - 3 * spacing):
            scheme.createFourPointData(scheme.size(), a, a + 3 * spacing,
                                       a + spacing, a + 2 * spacing)

    mesh = pg.meshtools.createParaMesh(scheme.sensors(), paraDX=0.6,
                                       paraMaxCellSize=25.0, paraDepth=36.0, quality=33.6)
    centers = np.asarray([[cell.center().x(), cell.center().y()] for cell in mesh.cells()])
    truth = np.full(mesh.cellCount(), 100.0)
    # Finite, buried, laterally bounded conductive body; coordinates are metres,
    # z is positive upward and follows the actual electrode surface.
    body = ((centers[:, 0] >= 21.0) & (centers[:, 0] <= 35.0)
            & (centers[:, 1] <= -5.0) & (centers[:, 1] >= -20.0))
    truth[body] = 25.0
    simulated = pg_ert.simulate(mesh=mesh, scheme=scheme, res=truth, sr=True,
                                noiseLevel=0.0, verbose=False)
    resistance = np.asarray(simulated["r"], dtype=float)
    rng = np.random.default_rng(noise_seed)
    resistance *= np.exp(rng.normal(0.0, 0.01, size=len(resistance)))
    abmn = np.column_stack([np.asarray(simulated[key], dtype=int) + 1 for key in "abmn"])
    lines = ["# CAOS deterministic synthetic control; not field observations",
             "# A Wenner array with 2m was applied.",
             f"{count}# Number of sensors", "#x z"]
    lines.extend(f"{xx:.9f} {zz:.9f}" for xx, zz in zip(x, z))
    lines.extend([f"{len(resistance)}# Number of data", "#a b m n R"])
    lines.extend(f"{a} {b} {m} {n} {r:.12g}"
                 for (a, b, m, n), r in zip(abmn, resistance))
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    parsed = ert.parse_ohm_bytes(raw)
    if len(parsed.abmn) != scheme.size() or np.any(parsed.resistance_ohm <= 0):
        raise ert.ERTError("synthetic source failed the strict production parser")

    # Truth geometry is expressed independently of the simulation mesh so it
    # can be evaluated at the inversion parameter-cell centers.
    truth_spec = {"background_ohm_m": 100.0, "body_ohm_m": 25.0,
                  "body_x_m": [21.0, 35.0], "body_z_m": [-20.0, -5.0],
                  "forward_mesh_cells": int(mesh.cellCount()),
                  "noise": "seeded multiplicative log-normal, sigma=0.01", "seed": noise_seed}
    return raw, {"electrode_x_m": x.tolist(), "electrode_z_m": z.tolist(),
                 "forward_model": truth_spec, "forward_body_cells": int(body.sum())}


def experiment() -> dict:
    raw, geometry = build()
    with tempfile.TemporaryDirectory(prefix="caos-ert-synthetic-") as folder:
        source = Path(folder) / "synthetic.ohm"
        source.write_bytes(raw)
        report = ert.run(source, source_sha256=hashlib.sha256(raw).hexdigest())
    # Runtime is operational telemetry, not scientific result content; including
    # it in this receipt makes the otherwise seeded result hash change each run.
    report.pop("wall_seconds", None)
    # ert.run is shared with the restricted field workflow; replace its source
    # identity and rights metadata so this synthetic control cannot be mistaken
    # for a Slagdump result.
    report["source_id"] = "original-synthetic-ert-control"
    report["rights_decision"] = "not-applicable-original-synthetic-data"
    report["field_geology_claim"] = False
    report["qc"]["unit_basis"] = "synthetic fixture explicitly declares metres, positive-up z, and Ohm resistance"
    if "inverse" in report:
        centers = np.asarray(report["inverse"]["model_cell_center_xz_m"], dtype=float)
        true_rho = np.full(len(centers), geometry["forward_model"]["background_ohm_m"])
        spec = geometry["forward_model"]
        body = ((centers[:, 0] >= spec["body_x_m"][0]) & (centers[:, 0] <= spec["body_x_m"][1])
                & (centers[:, 1] <= spec["body_z_m"][1]) & (centers[:, 1] >= spec["body_z_m"][0]))
        true_rho[body] = spec["body_ohm_m"]
        recovered = np.asarray(report["inverse"]["model_resistivity_ohm_m"])
        report["synthetic_truth_comparison"] = {
            "truth_resistivity_ohm_m_at_parameter_cell_centers": true_rho.tolist(),
            "body_membership_at_parameter_cell_centers": body.tolist(),
            "log10_rmse_over_parameter_cells": float(np.sqrt(np.mean((np.log10(recovered) - np.log10(true_rho)) ** 2))),
            "interpretation": "synthetic truth error is a controlled experiment score, not field accuracy or uncertainty",
        }
    report["experiment"] = {"kind": "synthetic-2d-ert-control", "is_field_data": False,
                            "is_field_geology_claim": False, "geometry": geometry,
                            "source_sha256": hashlib.sha256(raw).hexdigest(),
                            "source_bytes": len(raw),
                            "pipeline_sha256": hashlib.sha256(Path(ert.__file__).read_bytes()).hexdigest(),
                            "experiment_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="write receipt to a caller-owned temporary path")
    args = parser.parse_args()
    result = experiment()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(result, indent=2, allow_nan=False) + "\n").encode("utf-8")
    args.output.write_bytes(payload)
    args.output.with_suffix(args.output.suffix + ".sha256").write_text(
        hashlib.sha256(payload).hexdigest() + "\n", encoding="ascii")
    print(json.dumps({"inverse_status": result["inverse_status"],
                      "measurements": result["qc"]["measurement_count"],
                      "wall_seconds": result.get("wall_seconds"),
                      "receipt": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
