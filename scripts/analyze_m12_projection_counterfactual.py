#!/usr/bin/env python3
"""Paired post-hoc analysis of raw versus projected M12 predictions.

This does not change the frozen v1.1 protocol, its calibration, or its verdict.
It regenerates the exact held-out cohorts, applies the already selected alpha,
and compares the raw checkpoint prediction with its projected counterpart on
the same cases. Output must be outside every repository checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

import velocity_nullspace_refinement_v11 as study  # noqa: E402
import velocity_residual_learning as learned  # noqa: E402
import velocity_validation as physics  # noqa: E402

PACKAGE = ROOT / "data/derived/v2/models/m12-current-reproduction-20261106"
TEST_NAMES = study.TEST_NAMES
DRAWS = 20_000
BOOTSTRAP_NAMESPACE = "m12-projection-counterfactual-v1:"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inside_checkout(path: Path) -> bool:
    return any((parent / ".git").exists() for parent in (path, *path.parents))


def bootstrap_mean_ratio(numerator: np.ndarray, denominator: np.ndarray,
                         *, cohort: str, metric: str) -> dict:
    numerator = np.asarray(numerator, dtype=np.float64)
    denominator = np.asarray(denominator, dtype=np.float64)
    if (numerator.ndim != 1 or denominator.shape != numerator.shape or numerator.size < 2
            or not np.isfinite(numerator).all() or not np.isfinite(denominator).all()
            or np.any(numerator < 0) or np.any(denominator <= 0)):
        raise ValueError("Paired bootstrap inputs must be finite, nonnegative, same-case errors")
    seed_material = f"{BOOTSTRAP_NAMESPACE}{cohort}:{metric}".encode("utf-8")
    seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "little") % (2**32)
    rng = np.random.Generator(np.random.PCG64(seed))
    n = numerator.size
    ratios = np.empty(DRAWS, dtype=np.float64)
    offset = 0
    while offset < DRAWS:
        size = min(1024, DRAWS - offset)
        indices = rng.integers(0, n, size=(size, n))
        ratios[offset:offset + size] = (
            numerator[indices].mean(axis=1) / denominator[indices].mean(axis=1)
        )
        offset += size
    return {
        "estimate_ratio_of_mean_errors": float(numerator.mean() / denominator.mean()),
        "paired_case_bootstrap_95_percentile_interval": [
            float(np.quantile(ratios, 0.025, method="linear")),
            float(np.quantile(ratios, 0.975, method="linear")),
        ],
        "draws": DRAWS,
        "seed": seed,
        "generator": "NumPy PCG64",
        "quantile_method": "linear",
        "cases_projected_error_lower": int(np.sum(numerator < denominator)),
        "cases_equal": int(np.sum(numerator == denominator)),
        "cases_projected_error_higher": int(np.sum(numerator > denominator)),
    }


def main() -> int:
    import torch

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="new external directory for the analysis receipt")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if inside_checkout(output):
        parser.error("--output must be outside every repository checkout")
    if output.exists():
        parser.error("--output must be a new directory")

    run = PACKAGE / "nullspace-v1.1"
    receipt_path = run / "receipt.json"
    checkpoint_path = run / "m12-residual-v3.1-source.npz"
    training_receipt_path = run / "m12-residual-v3.1-training-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    training_receipt = json.loads(training_receipt_path.read_text(encoding="utf-8"))
    expected_checkpoint = receipt["base_checkpoint"]["sha256"]
    if file_sha256(checkpoint_path) != expected_checkpoint:
        raise ValueError("Packaged M12 checkpoint hash differs from the frozen receipt")
    if file_sha256(training_receipt_path) != receipt["base_checkpoint"]["training_receipt_sha256"]:
        raise ValueError("Packaged M12 training receipt hash differs from the frozen receipt")
    if file_sha256(receipt_path) != "0d4cd8c14e290b9cd17da387800dbe6cf7314729379d03221df8585b1243d880":
        raise ValueError("Packaged M12 null-space receipt differs from the reviewed source receipt")
    if not study.source_receipt_matches(receipt.get("sources")):
        raise ValueError("M12 null-space receipt source hashes differ from the checked source modules")
    if training_receipt.get("status") != "failed-held-out-comparator":
        raise ValueError("Counterfactual analysis requires the frozen failed v3.1 checkpoint")
    if training_receipt.get("checkpoint_sha256") != expected_checkpoint:
        raise ValueError("Packaged training receipt does not identify the supplied checkpoint")

    alpha = float(receipt["refinement"]["alpha_selection"]["selected_alpha"])
    selected_lambda = float(receipt["classical"]["selected_lambda"])
    if alpha != 1.0:
        raise ValueError(f"Frozen v1.1 alpha changed unexpectedly: {alpha}")
    if receipt.get("scientific_acceptance") is not False:
        raise ValueError("The source receipt must continue to deny scientific acceptance")

    ops = physics.operators()
    bases = {name: study.nullspace_basis(ops[name]["cell"]) for name in ops}
    model = learned.load_checkpoint(checkpoint_path, expected_checkpoint, "cpu")
    cohorts: dict[str, dict] = {}
    for name in TEST_NAMES:
        cohort = study.make_cohort(name, ops)
        if cohort["manifest_sha256"] != receipt["split_hashes"][name]:
            raise AssertionError(f"Regenerated {name} manifest differs from frozen receipt")
        if cohort["records"] != receipt["split_manifests"][name]:
            raise AssertionError(f"Regenerated {name} case identities differ from frozen receipt")
        baseline = physics.classical_predict(cohort, ops, selected_lambda)
        study._attach_model_features(cohort, baseline)
        raw_prediction, _ = learned.predict(model, cohort, "cpu")
        projected_prediction, _ = study.project_correction(
            cohort, baseline, raw_prediction, ops, alpha, bases
        )
        raw_score = physics.score(cohort, raw_prediction, baseline, ops, float("inf"))
        projected_score = physics.score(cohort, projected_prediction, baseline, ops, float("inf"))
        study._check_score_replay(receipt["cohorts"][name], projected_score, name)

        raw_records = {row["id"]: row for row in raw_score["per_record"]}
        projected_records = {row["id"]: row for row in projected_score["per_record"]}
        if raw_records.keys() != projected_records.keys():
            raise AssertionError(f"Raw and projected {name} scores do not have identical cases")
        pairs = []
        for case in cohort["records"]:
            case_id = case["id"]
            raw = raw_records[case_id]
            projected = projected_records[case_id]
            pairs.append({
                "case_id": case_id,
                "family": case["family"],
                "acquisition": case["acquisition"],
                "raw_cnn_velocity_rmse_m_s": raw["learned_velocity_rmse_m_s"],
                "projected_cnn_velocity_rmse_m_s": projected["learned_velocity_rmse_m_s"],
                "l2_velocity_rmse_m_s": raw["classical_velocity_rmse_m_s"],
                "raw_cnn_oracle_time_rmse_ms": raw["learned_oracle_rmse_ms"],
                "projected_cnn_oracle_time_rmse_ms": projected["learned_oracle_rmse_ms"],
                "l2_oracle_time_rmse_ms": raw["classical_oracle_rmse_ms"],
            })

        raw_velocity = np.asarray([p["raw_cnn_velocity_rmse_m_s"] for p in pairs])
        projected_velocity = np.asarray([p["projected_cnn_velocity_rmse_m_s"] for p in pairs])
        l2_velocity = np.asarray([p["l2_velocity_rmse_m_s"] for p in pairs])
        raw_time = np.asarray([p["raw_cnn_oracle_time_rmse_ms"] for p in pairs])
        projected_time = np.asarray([p["projected_cnn_oracle_time_rmse_ms"] for p in pairs])
        l2_time = np.asarray([p["l2_oracle_time_rmse_ms"] for p in pairs])
        cohorts[name] = {
            "count": len(pairs),
            "manifest_sha256": cohort["manifest_sha256"],
            "means": {
                "raw_cnn_velocity_rmse_m_s": float(raw_velocity.mean()),
                "projected_cnn_velocity_rmse_m_s": float(projected_velocity.mean()),
                "l2_velocity_rmse_m_s": float(l2_velocity.mean()),
                "raw_cnn_oracle_time_rmse_ms": float(raw_time.mean()),
                "projected_cnn_oracle_time_rmse_ms": float(projected_time.mean()),
                "l2_oracle_time_rmse_ms": float(l2_time.mean()),
            },
            "ratios_to_l2": {
                "raw_cnn_velocity": float(raw_velocity.mean() / l2_velocity.mean()),
                "projected_cnn_velocity": float(projected_velocity.mean() / l2_velocity.mean()),
                "raw_cnn_oracle_time": float(raw_time.mean() / l2_time.mean()),
                "projected_cnn_oracle_time": float(projected_time.mean() / l2_time.mean()),
            },
            "paired_projection_effect": {
                "projected_to_raw_velocity": bootstrap_mean_ratio(
                    projected_velocity, raw_velocity, cohort=name, metric="velocity"
                ),
                "projected_to_raw_oracle_time": bootstrap_mean_ratio(
                    projected_time, raw_time, cohort=name, metric="oracle-time"
                ),
            },
            "cases": pairs,
        }

    result = {
        "schema": "caos-geophysics.m12-projection-counterfactual-analysis/v1",
        "status": "exploratory-paired-counterfactual",
        "scientific_acceptance": False,
        "question": "On the frozen v1.1 test cases, how do raw and null-space-projected CNN predictions compare when both are evaluated against the same L2 baseline and independent oracle?",
        "protocol_boundary": "Post-hoc paired analysis only. No model, cohort, checkpoint, seed, lambda, alpha, or original v1.1 verdict is changed; alpha and lambda are loaded from the locked calibration receipt.",
        "method": "Same checkpoint and regenerated case are scored as raw CNN, projected CNN at the frozen calibration-selected alpha, and matched straight-ray L2 baseline.",
        "interpretation_limit": "Intervals quantify paired-case resampling within each fixed synthetic cohort. They do not represent uncertainty over natural geology, field noise, generators, or acquisition populations and do not establish field accuracy or product acceptance.",
        "inputs": {
            "protocol": receipt["protocol"],
            "nullspace_receipt_sha256": file_sha256(receipt_path),
            "training_receipt_sha256": file_sha256(training_receipt_path),
            "checkpoint_sha256": file_sha256(checkpoint_path),
            "analysis_source_sha256": file_sha256(Path(__file__).resolve()),
            "method_source_sha256": study.sha256_file(Path(study.__file__)),
            "learned_source_sha256": study.sha256_file(Path(learned.__file__)),
            "forward_inverse_source_sha256": study.sha256_file(Path(physics.__file__)),
            "alpha_from_locked_calibration": alpha,
            "classical_lambda_from_locked_calibration": selected_lambda,
            "cohort_seed_bases": receipt["seed_bases"],
            "case_manifest_sha256": receipt["split_hashes"],
        },
        "bootstrap": {"draws": DRAWS, "generator": "NumPy PCG64", "quantiles": [0.025, 0.975],
                      "quantile_method": "linear", "pairing": "identical case IDs within cohort"},
        "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                    "torch": torch.__version__, "device": "cpu"},
        "cohorts": cohorts,
    }
    output.mkdir(parents=True)
    target = output / "counterfactual-analysis.json"
    target.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "alpha": alpha,
                      "cohorts": {name: {
                          "count": value["count"],
                          "velocity_projected_to_raw": value["paired_projection_effect"]["projected_to_raw_velocity"]["estimate_ratio_of_mean_errors"],
                          "oracle_time_projected_to_raw": value["paired_projection_effect"]["projected_to_raw_oracle_time"]["estimate_ratio_of_mean_errors"],
                      } for name, value in cohorts.items()},
                      "output": str(target)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
