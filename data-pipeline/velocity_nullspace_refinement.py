"""Validation-selected, nullspace-constrained M12 residual refinement.

The method reuses a hash-verified learned residual checkpoint, then projects
its slowness correction into the numerical null space of each acquisition's
straight-ray matrix. A new calibration cohort selects the L2 regularization
and correction scale. All test cohorts use new, disjoint realizations.
"""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import time
from pathlib import Path

import numpy as np

import velocity_residual_learning as learned
import velocity_validation as physics
import velocity_physics_refinement as refinement


PROTOCOL = "m12-nullspace-residual/v1"
COUNTS = {"calibration": 160, "id_test": 160, "family_only": 80,
          "acquisition_only": 80, "joint_ood": 160}
SEED_BASES = {"calibration": 317001, "id_test": 327001, "family_only": 337001,
              "acquisition_only": 347001, "joint_ood": 357001}
ALPHAS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)
TEST_NAMES = ("id_test", "family_only", "acquisition_only", "joint_ood")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_hashes() -> dict[str, str]:
    runner = Path(__file__).resolve().parents[1] / "scripts" / "run_m12_nullspace_v1.py"
    return {"method": sha256_file(Path(__file__)),
            "runner": sha256_file(runner),
            "learned_checkpoint_model": sha256_file(Path(learned.__file__)),
            "forward_inverse": sha256_file(Path(physics.__file__)),
            "feature_contract": sha256_file(Path(refinement.__file__))}


def make_cohort(name: str, ops: dict, *, fixture: bool = False) -> dict:
    if name not in COUNTS:
        raise ValueError("Unknown nullspace-refinement cohort")
    count = min(COUNTS[name], 12) if fixture else COUNTS[name]
    families = physics.TRAIN_FAMILIES if name in ("calibration", "id_test", "acquisition_only") else physics.TEST_FAMILIES
    layouts = ("C",) if name in ("acquisition_only", "joint_ood") else ("A", "B")
    records, features, velocities, observations, acquisitions = [], [], [], [], []
    for index in range(count):
        seed = SEED_BASES[name] + index
        family = families[index % len(families)]
        layout = layouts[(index // len(families)) % len(layouts)]
        rng = np.random.default_rng(seed)
        velocity = physics.velocity_family(family, rng)
        observed = ops[layout]["oracle"] @ (1.0 / velocity.ravel())
        observed = observed + rng.normal(0.0, physics.NOISE_S, len(observed))
        records.append({"id": f"{PROTOCOL}:{name}:{seed}:{family}:{layout}", "seed": seed,
                        "family": family, "acquisition": layout,
                        "velocity_sha256": physics.sha256_bytes(velocity.astype("<f4").tobytes()),
                        "noisy_picks_sha256": physics.sha256_bytes(observed.astype("<f8").tobytes())})
        features.append(physics.input_features(observed, ops[layout]["cell"]))
        velocities.append(velocity)
        observations.append(observed)
        acquisitions.append(layout)
    return {"records": records, "features": np.stack(features),
            "velocity": np.stack(velocities), "observed": np.stack(observations),
            "acquisition": np.asarray(acquisitions),
            "manifest_sha256": physics.canonical_hash(records)}


def nullspace_basis(matrix: np.ndarray) -> tuple[np.ndarray, dict]:
    """Orthonormal basis for null(A), with an explicit numerical residual check."""
    a = np.asarray(matrix, dtype=np.float64)
    if a.ndim != 2 or not np.isfinite(a).all() or min(a.shape) == 0:
        raise ValueError("Invalid ray matrix")
    _u, singular, vh = np.linalg.svd(a, full_matrices=True)
    tolerance = np.finfo(np.float64).eps * max(a.shape) * (singular[0] if len(singular) else 0.0)
    rank = int(np.sum(singular > tolerance))
    basis = vh[rank:].T.copy()
    residual = float(np.max(np.abs(a @ basis))) if basis.size else 0.0
    limit = 1e-10 * max(float(np.linalg.norm(a, ord=2)), 1.0)
    if residual > limit:
        raise ArithmeticError("Ray nullspace basis failed its residual check")
    return basis, {"rank": rank, "nullity": basis.shape[1],
                   "max_abs_A_times_basis": residual, "residual_limit": limit}


def project_correction(cohort: dict, baseline: np.ndarray, learned_prediction: np.ndarray,
                       ops: dict, alpha: float, bases: dict | None = None) -> tuple[np.ndarray, dict]:
    if not np.isfinite(alpha) or alpha < 0 or alpha > 2:
        raise ValueError("Correction scale must be within [0, 2]")
    base = np.asarray(baseline, dtype=np.float64)
    estimate = np.asarray(learned_prediction, dtype=np.float64)
    truth_shape = cohort["velocity"].shape
    if base.shape != truth_shape or estimate.shape != truth_shape or not np.isfinite(base).all() or not np.isfinite(estimate).all():
        raise ValueError("M12 candidate arrays have invalid shape or values")
    output = np.empty_like(base)
    diagnostics = {}
    labels = cohort["acquisition"]
    for layout in np.unique(labels):
        ids = np.flatnonzero(labels == layout)
        matrix = ops[layout]["cell"]
        basis, basis_receipt = (bases or {}).get(layout) or nullspace_basis(matrix)
        correction = (1.0 / estimate[ids].reshape(len(ids), -1)
                      - 1.0 / base[ids].reshape(len(ids), -1))
        projected = (correction @ basis) @ basis.T if basis.shape[1] else np.zeros_like(correction)
        null_residual = float(np.max(np.abs(matrix @ projected.T))) if projected.size else 0.0
        raw_slowness = 1.0 / base[ids].reshape(len(ids), -1) + alpha * projected
        clipped = np.clip(raw_slowness, 1.0 / 4000.0, 1.0 / 1400.0)
        output[ids] = (1.0 / clipped).reshape(-1, physics.GRID, physics.GRID)
        diagnostics[str(layout)] = {**basis_receipt,
            "max_abs_A_projected_correction": null_residual,
            "clipped_fraction": float(np.mean(clipped != raw_slowness))}
    return output, diagnostics


def _attach_model_features(cohort: dict, baseline: np.ndarray) -> None:
    learned.attach_classical_features(cohort, baseline)


def _select_alpha(calibration: dict, baseline: np.ndarray, prediction: np.ndarray,
                  ops: dict, bases: dict) -> tuple[float, dict]:
    rows = {}
    eligible = []
    for alpha in ALPHAS:
        candidate, _ = project_correction(calibration, baseline, prediction, ops, alpha, bases)
        score = physics.score(calibration, candidate, baseline, ops, float("inf"))
        velocity_ratio = score["learned_to_classical_velocity_ratio"]
        oracle_ratio = score["learned_to_classical_oracle_ratio"]
        combined = 0.5 * (velocity_ratio + oracle_ratio)
        rows[str(alpha)] = {"velocity_ratio": velocity_ratio,
                            "oracle_time_ratio": oracle_ratio,
                            "mean_ratio": combined}
        if velocity_ratio < 1.0 and oracle_ratio < 1.0:
            eligible.append((combined, alpha))
    # Alpha zero is the exact classical solution; if validation cannot support
    # a joint improvement, do not force a learned correction.
    selected = min(eligible, key=lambda item: (item[0], item[1]))[1] if eligible else 0.0
    return selected, {"grid": rows, "selected_alpha": selected,
                      "selection": "minimum mean of velocity and oracle-time ratios among candidates below one on both; smallest alpha breaks ties",
                      "no_joint_improvement_fallback": 0.0,
                      "calibration_supported": bool(eligible)}


def _verified_base(source_run: Path) -> tuple[dict, Path]:
    receipt_path = source_run / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (receipt.get("schema") != "caos-geophysics.m12-residual/v3.1"
            or receipt.get("protocol") != "m12-learned-residual/v3.1"):
        raise ValueError("Unsupported source checkpoint protocol")
    expected_sources = {"implementation_sha256": sha256_file(Path(learned.__file__)),
                        "forward_inverse_sha256": sha256_file(Path(physics.__file__)),
                        "corrected_feature_sha256": sha256_file(Path(refinement.__file__))}
    if receipt.get("sources") != expected_sources:
        raise ValueError("Source checkpoint implementation hashes differ")
    checkpoint = source_run / receipt["checkpoint"]
    if sha256_file(checkpoint) != receipt.get("checkpoint_sha256"):
        raise ValueError("Source checkpoint SHA-256 mismatch")
    if receipt.get("status") != "failed-held-out-comparator":
        raise ValueError("Source run is not the explicitly failed v3.1 research checkpoint")
    return receipt, checkpoint


def _check_score_replay(saved: dict, replayed: dict, label: str) -> None:
    exact = ("count", "manifest_sha256", "noisy_input_sha256", "forward_threshold_exceedances")
    for key in exact:
        if saved.get(key) != replayed.get(key):
            raise AssertionError(f"M12 nullspace replay changed: {label}/{key}")
    tolerances = {"learned_velocity_rmse_m_s": (0.15, 1e-5),
                  "classical_velocity_rmse_m_s": (1e-8, 1e-10),
                  "learned_oracle_rmse_ms": (0.01, 1e-5),
                  "classical_oracle_rmse_ms": (1e-8, 1e-10),
                  "learned_to_classical_velocity_ratio": (1e-4, 1e-5),
                  "learned_to_classical_oracle_ratio": (1e-5, 1e-5)}
    for key, (absolute, relative) in tolerances.items():
        if not np.isclose(saved[key], replayed[key], rtol=relative, atol=absolute):
            raise AssertionError(f"M12 nullspace replay changed: {label}/{key}")
    if [row["id"] for row in saved["per_record"]] != [row["id"] for row in replayed["per_record"]]:
        raise AssertionError(f"M12 nullspace per-record IDs changed: {label}")
    for before, after in zip(saved["per_record"], replayed["per_record"], strict=True):
        for key, (absolute, relative) in tolerances.items():
            if key in before and not np.isclose(before[key], after[key], rtol=relative, atol=absolute):
                raise AssertionError(f"M12 nullspace per-record replay changed: {label}/{before['id']}/{key}")


def execute(output: Path, source_run: Path, *, device: str = "cpu", fixture: bool = False) -> dict:
    import scipy
    import torch
    output, source_run = Path(output).resolve(), Path(source_run).resolve()
    if output.exists():
        raise FileExistsError("M12 nullspace output directory already exists")
    if device not in ("cpu", "cuda") or device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Requested M12 inference device is unavailable")
    started = time.perf_counter()
    base_receipt, source_checkpoint = _verified_base(source_run)
    ops = physics.operators()
    bases = {name: nullspace_basis(ops[name]["cell"]) for name in ops}
    calibration = make_cohort("calibration", ops, fixture=fixture)
    selected_lambda, lambda_scores = physics.select_classical(calibration, ops)
    baseline = physics.classical_predict(calibration, ops, selected_lambda)
    _attach_model_features(calibration, baseline)
    model = learned.load_checkpoint(source_checkpoint, base_receipt["checkpoint_sha256"], device)
    prediction, _ = learned.predict(model, calibration, device)
    alpha, alpha_selection = _select_alpha(calibration, baseline, prediction, ops, bases)
    calibration_prediction, calibration_projection = project_correction(
        calibration, baseline, prediction, ops, alpha, bases)
    calibration_score = physics.score(calibration, calibration_prediction, baseline, ops, float("inf"))
    # Hyperparameters are now frozen. Generate and score all fresh test cohorts.
    cohorts, reports, projection_receipts = {}, {}, {}
    if not fixture:
        for name in TEST_NAMES:
            cohort = make_cohort(name, ops)
            test_baseline = physics.classical_predict(cohort, ops, selected_lambda)
            _attach_model_features(cohort, test_baseline)
            test_prediction, _ = learned.predict(model, cohort, device)
            refined, diagnostic = project_correction(cohort, test_baseline, test_prediction, ops, alpha, bases)
            cohorts[name] = cohort
            reports[name] = physics.score(cohort, refined, test_baseline, ops, float("inf"))
            projection_receipts[name] = diagnostic
    status = "fixture-only" if fixture else physics.scientific_verdict(reports["joint_ood"])
    checkpoint_name = "m12-residual-v3.1-source.npz"
    base_receipt_name = "m12-residual-v3.1-training-receipt.json"
    output.mkdir(parents=True)
    shutil.copyfile(source_checkpoint, output / checkpoint_name)
    shutil.copyfile(source_run / "receipt.json", output / base_receipt_name)
    receipt = {
        "schema": "caos-geophysics.m12-nullspace-residual/v1", "protocol": PROTOCOL,
        "status": status, "scientific_acceptance": False, "device": device,
        "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                    "scipy": scipy.__version__, "torch": torch.__version__,
                    "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None},
        "sources": source_hashes(),
        "base_checkpoint": {"protocol": base_receipt["protocol"], "sha256": base_receipt["checkpoint_sha256"],
                            "source_status": base_receipt["status"], "copied_name": checkpoint_name,
                            "training_receipt": base_receipt_name,
                            "training_receipt_sha256": sha256_file(source_run / "receipt.json")},
        "fixture": fixture,
        "seed_bases": dict(SEED_BASES), "counts": ({"calibration": len(calibration["records"])} if fixture
                                                       else {"calibration": len(calibration["records"]),
                                                             **{name: len(value["records"]) for name, value in cohorts.items()}}),
        "split_manifests": {"calibration": calibration["records"],
                            **({name: value["records"] for name, value in cohorts.items()} if not fixture else {})},
        "split_hashes": {"calibration": calibration["manifest_sha256"],
                         **({name: value["manifest_sha256"] for name, value in cohorts.items()} if not fixture else {})},
        "classical": {"selected_lambda": selected_lambda, "validation_candidate_rmse_m_s": lambda_scores,
                      "selection": "minimum velocity RMSE on the fresh calibration cohort"},
        "refinement": {"projection": "orthogonal null(A) projection in slowness coordinates",
                       "alpha_selection": alpha_selection,
                       "calibration_projection": calibration_projection,
                       "calibration_metrics": calibration_score,
                       "alpha_grid": list(ALPHAS)},
        "cohorts": reports, "projection_diagnostics": projection_receipts,
        "wall_seconds": time.perf_counter() - started,
        "limitations": ["synthetic straight-ray study only; no field-data or geological validity",
                        "16x16 fixed grid and three fixed acquisition layouts",
                        "nonlinear velocity conversion and physical bounds can perturb exact nullspace invariance",
                        "the base network was trained under the separately failed residual-v3.1 protocol",
                        "a held-out advantage does not establish general or field superiority"]}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return receipt


def verify(output: Path) -> dict:
    output = Path(output)
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    if receipt.get("schema") != "caos-geophysics.m12-nullspace-residual/v1" or receipt.get("protocol") != PROTOCOL:
        raise ValueError("Unsupported M12 nullspace receipt")
    if receipt.get("sources") != source_hashes():
        raise ValueError("M12 nullspace source hashes changed")
    checkpoint = output / receipt["base_checkpoint"]["copied_name"]
    if sha256_file(checkpoint) != receipt["base_checkpoint"]["sha256"]:
        raise ValueError("M12 nullspace checkpoint SHA-256 mismatch")
    training_receipt_path = output / receipt["base_checkpoint"]["training_receipt"]
    if sha256_file(training_receipt_path) != receipt["base_checkpoint"]["training_receipt_sha256"]:
        raise ValueError("M12 nullspace base training receipt hash mismatch")
    base_receipt = json.loads(training_receipt_path.read_text(encoding="utf-8"))
    expected_base_sources = {"implementation_sha256": sha256_file(Path(learned.__file__)),
                             "forward_inverse_sha256": sha256_file(Path(physics.__file__)),
                             "corrected_feature_sha256": sha256_file(Path(refinement.__file__))}
    if (base_receipt.get("schema") != "caos-geophysics.m12-residual/v3.1"
            or base_receipt.get("status") != "failed-held-out-comparator"
            or base_receipt.get("sources") != expected_base_sources
            or base_receipt.get("checkpoint_sha256") != receipt["base_checkpoint"]["sha256"]):
        raise ValueError("M12 nullspace checkpoint and training receipt differ")
    ops = physics.operators()
    bases = {name: nullspace_basis(ops[name]["cell"]) for name in ops}
    fixture = receipt.get("fixture") is True
    calibration = make_cohort("calibration", ops, fixture=fixture)
    lam, lambda_scores = physics.select_classical(calibration, ops)
    if lam != receipt["classical"]["selected_lambda"] or lambda_scores != receipt["classical"]["validation_candidate_rmse_m_s"]:
        raise AssertionError("M12 nullspace calibration lambda changed")
    baseline = physics.classical_predict(calibration, ops, lam)
    _attach_model_features(calibration, baseline)
    model = learned.load_checkpoint(checkpoint, receipt["base_checkpoint"]["sha256"], "cpu")
    prediction, _ = learned.predict(model, calibration, "cpu")
    alpha, selection = _select_alpha(calibration, baseline, prediction, ops, bases)
    saved_selection = receipt["refinement"]["alpha_selection"]
    if alpha != saved_selection["selected_alpha"] or selection["selection"] != saved_selection["selection"]:
        raise AssertionError("M12 nullspace alpha selection changed")
    for key, values in selection["grid"].items():
        for metric, value in values.items():
            if not np.isclose(value, saved_selection["grid"][key][metric], rtol=1e-6, atol=1e-8):
                raise AssertionError(f"M12 nullspace alpha score changed: {key}/{metric}")
    if calibration["records"] != receipt["split_manifests"]["calibration"]:
        raise AssertionError("M12 calibration manifest changed")
    if calibration["manifest_sha256"] != receipt["split_hashes"]["calibration"]:
        raise AssertionError("M12 calibration split hash changed")
    calibration_refined, _ = project_correction(calibration, baseline, prediction, ops, alpha, bases)
    calibration_score = physics.score(calibration, calibration_refined, baseline, ops, float("inf"))
    _check_score_replay(receipt["refinement"]["calibration_metrics"], calibration_score, "calibration")
    if not receipt["cohorts"]:
        if receipt["status"] != "fixture-only":
            raise AssertionError("M12 test cohorts are missing")
        return {"status": "fixture-verified", "cohorts": 0}
    reproduced = {}
    for name in TEST_NAMES:
        cohort = make_cohort(name, ops)
        if cohort["records"] != receipt["split_manifests"][name]:
            raise AssertionError(f"M12 test manifest changed: {name}")
        if cohort["manifest_sha256"] != receipt["split_hashes"][name]:
            raise AssertionError(f"M12 test split hash changed: {name}")
        baseline = physics.classical_predict(cohort, ops, lam)
        _attach_model_features(cohort, baseline)
        prediction, _ = learned.predict(model, cohort, "cpu")
        refined, _diagnostic = project_correction(cohort, baseline, prediction, ops, alpha)
        report = physics.score(cohort, refined, baseline, ops, float("inf"))
        original = receipt["cohorts"][name]
        _check_score_replay(original, report, name)
        reproduced[name] = report
    verdict = physics.scientific_verdict(reproduced["joint_ood"])
    if verdict != receipt["status"]:
        raise AssertionError("M12 nullspace scientific verdict changed")
    return {"status": "verified", "cohorts": len(reproduced),
            "checkpoint_sha256": receipt["base_checkpoint"]["sha256"],
            "scientific_verdict": verdict}
