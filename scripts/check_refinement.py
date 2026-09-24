"""Local discretization diagnostic; reports changes, not geological resolving power."""
import json
import sys
from pathlib import Path
import numpy as np
from simpeg import maps
from simpeg.potential_fields import gravity, magnetics

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from geology import properties, registry, volume_grid  # noqa: E402


def compute():
    xx, yy = np.meshgrid(np.linspace(-950, 950, 6), np.linspace(-800, 800, 6))
    receivers = np.c_[xx.ravel(), yy.ravel(), np.full(xx.size, 60.)]
    cases = [c for c in registry() if c["family"] in ("gravity", "magnetics", "joint", "learned")]
    results = {c["id"]: {} for c in cases}
    uniform = []
    for refinement in (1, 2, 4):
        mesh = volume_grid(refinement)
        gs = gravity.Survey(gravity.sources.SourceField([gravity.receivers.Point(receivers, components="gz")]))
        ms = magnetics.Survey(magnetics.sources.UniformBackgroundField([magnetics.receivers.Point(receivers, components="tmi")], amplitude=50000, inclination=60, declination=12))
        g = gravity.simulation.Simulation3DIntegral(mesh, survey=gs, rhoMap=maps.IdentityMap(nP=mesh.nC), engine="geoana").G.astype(float)
        b = magnetics.simulation.Simulation3DIntegral(mesh, survey=ms, chiMap=maps.IdentityMap(nP=mesh.nC), engine="geoana").G.astype(float)
        uniform.append(g @ np.ones(mesh.nC))
        for c in cases:
            rho, chi = properties(c["geometry"], mesh.cell_centers)
            # This diagnostic isolates scalar discretization, including an induced
            # response for the remanent shape. It does not refit inverse models.
            results[c["id"]][refinement] = (b @ chi if c["family"] == "magnetics" else g @ rho)
        print("Computed refinement", refinement, mesh.nC, "cells", flush=True)
    np.testing.assert_allclose(uniform[0], uniform[2], rtol=2e-6)
    np.testing.assert_allclose(uniform[1], uniform[2], rtol=2e-6)
    rows = []
    for c in cases:
        d = results[c["id"]]
        scale = float(np.linalg.norm(d[4]))
        rows.append(dict(case=c["id"], coarse_relative_l2=float(np.linalg.norm(d[1]-d[4])/scale), refined_relative_l2=float(np.linalg.norm(d[2]-d[4])/scale)))
    report = dict(reference="56 x 48 x 32 cell-centre property discretization, not an analytic geological truth", stations=36, uniform_prism_subdivision_max_relative_difference=float(np.max(np.abs((uniform[1]-uniform[2])/uniform[2]))), cases=rows, seismic=dict(previous_spacing_m=25, spacing_m=12.5, dt_seconds=.0005, pml_m=300, points_per_wavelength_at_1550ms_9Hz=1550/9/12.5, caveat="Peak-frequency sampling diagnostic only; no claim of a full seismic convergence study."))
    (ROOT/"docs/validation/refinement.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    compute()
