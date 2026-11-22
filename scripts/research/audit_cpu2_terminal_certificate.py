"""Independent numerical audit of recorded CPU2 terminal certificates.

This is an audit tool, not a solver or acceptance gate. It rebuilds each fit
problem from the immutable calibration request, recreates the final SimPEG
Sparse stage, and recomputes the fixed-stage KKT and strict-convexity bounds.
It never calls the producer's terminal-certificate decision function.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_key] = "1"

import numpy as np
from simpeg import maps, regularization

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

import gravity_irls_corrected_workflow as workflow
import gravity_irls_pool as pool
import gravity_l2 as l2
import gravity_workflow_io as transport


def _external(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise ValueError(f"{label}: absolute path required")
    if any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
           for p in (path, *path.parents)):
        raise ValueError(f"{label}: reparse-point path refused")
    resolved = path.resolve(strict=False)
    if resolved == ROOT or ROOT in resolved.parents or any((p / ".git").exists() for p in (resolved, *resolved.parents)):
        raise ValueError(f"{label}: path must be external to repositories")
    return resolved


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(archive_path: Path) -> dict:
    archive_path = _external(archive_path, "archive")
    if archive_path.suffix != ".gza" or not archive_path.is_file():
        raise ValueError("archive: one existing .gza file required")
    archive = transport.read_archive(archive_path.parent, archive_path.name)
    result = archive["result"]
    owner = workflow._Workflow("cpu2")
    if (result.get("runtime_epoch") != owner.engine.RUNTIME_EPOCH
            or result.get("source_inventory") != owner.sources):
        raise ValueError("archive/source inventory is not exact for current CPU2 source")
    accepted = owner.admit(archive["request"])
    plan = accepted["plan"]
    policy = accepted["policy"]["irls"]
    observations = accepted["observations"]["gz_up_mgal"]
    noise = {key: accepted["noise"][key] for key in ("kind", "values")}
    fits = result["fits"]
    records = []
    for fit_index, packed in enumerate(fits[:24]):
        fit = pool.decode(packed)
        terminal = fit.get("terminal", {})
        certificate = terminal.get("fixed_point_certificate")
        if certificate is None:
            continue
        candidate, fold = divmod(fit_index, 3)
        if candidate >= len(l2.BETA_CANDIDATES) or not fit.get("stages"):
            raise ValueError(f"fit {fit_index}: invalid frozen candidate/fold mapping")
        stage_record = fit["stages"][-1]
        q = np.array(fit["models_q"][stage_record["stop_row"]], dtype=np.float64, copy=True)
        if (stage_record["index"] != 20 or not np.array_equal(q, fit["models_q"][-1])
                or not np.array_equal(q, stage_record["inner"]["trace"]["models_q"][-1])):
            raise ValueError(f"fit {fit_index}: terminal native state does not replay exactly")
        fold_rows = plan["folds"][fold]["fit_rows"]
        problem = l2._build_problem(plan["request"], observations, noise, accepted["prior"],
            fold_rows, l2.BETA_CANDIDATES[candidate], observation_rows=plan["development_rows"])
        # Recreate the vendor Sparse instance independently of corrected._stage
        # and the producer certificate function.
        simulation = problem["simulation"]
        alpha = problem["alpha"]
        active_count = len(problem["reference_q"])
        regularizer = regularization.Sparse(simulation.mesh,
            active_cells=simulation.active_cells, mapping=maps.IdentityMap(nP=active_count),
            reference_model=problem["reference_q"].copy(), reference_model_in_smooth=True,
            alpha_s=alpha[0], alpha_x=alpha[1], alpha_y=alpha[2], alpha_z=alpha[3],
            norms=[1., 2., 2., 2.], gradient_type="components", irls_scaled=True)
        if len(regularizer.objfcts) != 4:
            raise ValueError(f"fit {fit_index}: vendor sparse component count changed")
        for component, threshold in zip(regularizer.objfcts, policy["epsilon_floor"]):
            component.irls_threshold = threshold
        regularizer.update_weights(q)
        actual_weights = np.array(regularizer.objfcts[0].get_weights("irls"), copy=True)
        recorded_weights = stage_record["adopted_weights"]
        weight_hashes = tuple(l2.survey._digest(np.array(child.get_weights("irls"), copy=True))
                              for child in regularizer.objfcts)
        if (not np.array_equal(actual_weights, recorded_weights)
                or weight_hashes != stage_record["weight_sha256"]):
            raise ValueError(f"fit {fit_index}: exact final sparse-weight replay failed")

        # Independently form the fixed quadratic gradient from its two public
        # operators, rather than reading the certificate's stored KKT value.
        misfit = problem["misfit"]
        gradient = np.asarray(misfit.deriv(q) + problem["beta_engine"] * regularizer.deriv(q))
        lower = accepted["prior"]["lower_kg_m3"] / 1000.0
        upper = accepted["prior"]["upper_kg_m3"] / 1000.0
        projected = gradient.copy()
        projected[(q <= lower) & (gradient > 0.0)] = 0.0
        projected[(q >= upper) & (gradient < 0.0)] = 0.0
        kkt = float(np.linalg.norm(projected, ord=np.inf))
        smallness_hessian = regularizer.objfcts[0].deriv2(q)
        diagonal = np.asarray(smallness_hessian.diagonal(), dtype=np.float64)
        if (not np.isfinite(diagonal).all() or np.any(diagonal <= 0.0)
                or not np.isfinite(kkt) or kkt > 1e-12):
            raise ValueError(f"fit {fit_index}: independent KKT/curvature condition failed")
        curvature = float(np.min(diagonal))
        convexity = float(problem["beta_engine"] * curvature)
        if (certificate.get("weight_sha256") != weight_hashes
                or certificate.get("projected_kkt_inf") != kkt
                or certificate.get("smallness_min_curvature") != curvature
                or certificate.get("strict_convexity_lower_bound") != convexity):
            raise ValueError(f"fit {fit_index}: certificate values differ from recomputation")
        records.append({"fit_index": fit_index, "candidate": candidate, "fold": fold,
            "terminal_reason": terminal.get("reason"), "stage": stage_record["index"],
            "native_q_sha256": l2.survey._digest(q),
            "weights_sha256": l2.survey._digest(actual_weights), "weights_exact": True,
            "projected_kkt_inf": kkt, "smallness_curvature_min": curvature,
            "strict_convexity_lower_bound": convexity,
            "certificate_sha256": l2.survey._digest(certificate)})
    if not records:
        raise ValueError("archive contains no CPU2 fixed-point certificates")
    receipt = {"schema": "gravity-cpu2-terminal-certificate-independent-audit-1",
        "research_only": True, "acceptance": False, "source_inventory": result["source_inventory"],
        "archive_path": str(archive_path), "archive_sha256": _sha_file(archive_path),
        "request_sha256": result["request_sha256"], "result_sha256": result["result_sha256"],
        "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "records": records}
    receipt["receipt_sha256"] = l2.survey._digest(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = _external(args.output, "receipt")
    if output.exists():
        raise FileExistsError(output)
    report = audit(args.archive)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, sort_keys=True, allow_nan=False, indent=2)
        stream.write("\n")
    print(json.dumps({"status": "research_only", "records": len(report["records"]),
        "archive_sha256": report["archive_sha256"], "receipt_sha256": report["receipt_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
