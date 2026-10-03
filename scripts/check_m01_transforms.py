"""Reproduce compact original-control evidence; never acquire or publish field data."""

from hashlib import sha256
import argparse
from importlib.metadata import version
import inspect
import json
from pathlib import Path
import platform
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

import harmonica as hm
import numpy as np
import verde as vd

from gravity_processing import digest
from gravity_transform_controls import control_request, prism_integral
from gravity_transforms import TRANSFORM_PINS, transform_survey


def control_evidence():
    rows = []
    for case in range(3):
        request, truth = control_request(case)
        result = transform_survey(request)
        analytic = hm.prism_gravity(
            truth["coordinates"], truth["prisms"], truth["densities"], field="g_z", parallel=False
        )
        converged = prism_integral(truth["coordinates"], truth["prisms"], truth["densities"], order=22)
        xx, yy = np.meshgrid(result["axes"]["easting_m"], result["axes"]["northing_m"])
        grids = []
        for grid in result["grids"]:
            indices = np.flatnonzero(grid["covered"])[::13]
            query = (xx.ravel()[indices], yy.ravel()[indices], np.full(len(indices), grid["height_m"]))
            independent = prism_integral(query, truth["prisms"], truth["densities"], order=22)
            predictions = np.array(grid["predicted_mgal"], dtype=float)[indices]
            grids.append(
                {
                    "height_m": grid["height_m"],
                    "checked_nodes": len(indices),
                    "covered_nodes": sum(grid["covered"]),
                    "independent_grid_rmse_mgal": float(np.sqrt(np.mean((independent - predictions) ** 2))),
                    "max_conditional_sigma_mgal": grid["max_conditional_sigma_mgal"],
                }
            )
        rows.append(
            {
                "case": case,
                "source_kind": "synthetic_control",
                "source_sha256": result["provenance"]["source_sha256"],
                "request_sha256": digest(request),
                "result_sha256": digest(result),
                "transform_module_sha256": result["provenance"]["module_sha256"],
                "correction_identity": result["provenance"]["correction_identity"],
                "split_sha256": result["split"]["sha256"],
                "stations": len(result["stations"]["station_ids"]),
                "masked": sum(request["geometry"]["mask"]),
                "selection": {k: v for k, v in result["selection"].items() if k != "candidates"},
                "evaluation": result["evaluation"],
                "condition": {k: v for k, v in result["condition"].items() if k != "weighted_singular_values"},
                "quadrature_order16_vs22_max_mgal": float(np.max(np.abs(converged - truth["true_observed_mgal"]))),
                "analytic_vs_volume_max_mgal": float(np.max(np.abs(converged - analytic))),
                "grids": grids,
                "nonuniqueness": result["nonuniqueness"],
            }
        )
    return rows


def primary_receipts():
    urls = [
        "https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.EquivalentSources.html",
        "https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.prism_gravity.html",
        "https://www.fatiando.org/verde/v1.9.0/api/generated/verde.BlockShuffleSplit.html",
        "https://www.fatiando.org/verde/v1.9.0/api/generated/verde.BlockKFold.html",
        "https://www.fatiando.org/verde/v1.9.0/api/generated/verde.base.least_squares.html",
        "https://www.fatiando.org/verde/v1.9.0/api/generated/verde.convexhull_mask.html",
        "https://www.fatiando.org/verde/v1.9.0/api/generated/verde.distance_mask.html",
    ]
    receipts = []
    for url in urls:
        with urlopen(url, timeout=20) as response:
            content = response.read(2 * 1024 * 1024 + 1)
            if response.status != 200 or len(content) > 2 * 1024 * 1024:
                raise ValueError("Official reference receipt failed or exceeded bound")
            receipts.append(
                {"url": url, "status": response.status, "bytes": len(content), "sha256": sha256(content).hexdigest()}
            )
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw/gravity-m01-transforms/verification.json")
    output = parser.parse_args().output.absolute()
    if not output.resolve().is_relative_to(ROOT / "data/raw/gravity-m01-transforms"):
        parser.error("verification output must stay in this worktree's ignored gravity-m01-transforms directory")
    if any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()) for p in output.parents):
        parser.error("symlink/junction output parents rejected")
    output.parent.mkdir(parents=True, exist_ok=True)
    installed_sources = []
    for obj in (hm.EquivalentSources, vd.BlockShuffleSplit, vd.BlockKFold):
        path = Path(inspect.getfile(obj))
        installed_sources.append(
            {
                "object": obj.__name__,
                "distribution_relative_path": "/".join(path.parts[path.parts.index("site-packages") + 1 :]),
                "bytes": path.stat().st_size,
                "sha256": sha256(path.read_bytes()).hexdigest(),
            }
        )
    install = json.loads((ROOT / "data/raw/gravity-m01-transform-install.json").read_text(encoding="utf-8"))
    wheels = [
        {
            "name": entry["metadata"]["name"],
            "version": entry["metadata"]["version"],
            "url": entry["download_info"]["url"],
            "sha256": entry["download_info"]["archive_info"]["hashes"]["sha256"],
        }
        for entry in install["install"]
    ]
    value = {
        "schema_version": "m01-transform-verification-1",
        "python": platform.python_version(),
        "platform": platform.system(),
        "engines": {name: version(name) for name in TRANSFORM_PINS},
        "plotting_extension_wheels": wheels,
        "installed_engine_sources": installed_sources,
        "primary_document_receipts": primary_receipts(),
        "controls": control_evidence(),
        "field_bytes_read": 0,
        "field_eligibility": "closed: unresolved datum/errors/lineage; intake remains main-owned",
        "full_method_accepted": False,
        "protected_source_published": False,
    }
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "receipt": str(output.relative_to(ROOT)),
                "sha256": sha256(output.read_bytes()).hexdigest(),
                "cases": len(value["controls"]),
            }
        )
    )


if __name__ == "__main__":
    main()
