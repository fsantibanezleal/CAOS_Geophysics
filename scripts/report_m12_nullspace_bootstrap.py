"""Compute paired case-bootstrap intervals from the immutable M12 v1.1 receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "data/derived/v2/models/m12-nullspace-v1_1/receipt.json"
EXPECTED_RECEIPT_SHA256 = "30df0c2ad495bd850dda602b1c96725be8290dd086119fb3e8e75355fe9dea22"
COHORTS = ("id_test", "family_only", "acquisition_only", "joint_ood")
METRICS = {
    "velocity_rmse_m_s": (
        "learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s",
        "learned_to_classical_velocity_ratio",
    ),
    "oracle_time_rmse_ms": (
        "learned_oracle_rmse_ms", "classical_oracle_rmse_ms",
        "learned_to_classical_oracle_ratio",
    ),
}
BOOTSTRAP_SEED = 6122026
BOOTSTRAP_DRAWS = 20_000


def _paired_arrays(cohort: dict, learned_key: str, classical_key: str) -> tuple[np.ndarray, np.ndarray]:
    rows = cohort["per_record"]
    ids = [row.get("id") for row in rows]
    if len(ids) != cohort["count"] or len(set(ids)) != len(ids) or any(not item for item in ids):
        raise ValueError("Per-case records are missing, duplicated, or inconsistent with cohort count")
    learned = np.asarray([row[learned_key] for row in rows], dtype=np.float64)
    classical = np.asarray([row[classical_key] for row in rows], dtype=np.float64)
    if (not np.isfinite(learned).all() or not np.isfinite(classical).all()
            or np.any(learned < 0) or np.any(classical <= 0)):
        raise ValueError("Per-case RMSE values must be finite and denominators positive")
    return learned, classical


def paired_bootstrap_ratio(
    learned: np.ndarray,
    classical: np.ndarray,
    *,
    seed: int = BOOTSTRAP_SEED,
    draws: int = BOOTSTRAP_DRAWS,
) -> dict:
    """Percentile interval for ratio of paired-case mean RMSEs."""
    learned = np.asarray(learned, dtype=np.float64)
    classical = np.asarray(classical, dtype=np.float64)
    if (learned.ndim != 1 or classical.shape != learned.shape or learned.size < 2
            or not np.isfinite(learned).all() or not np.isfinite(classical).all()
            or np.any(learned < 0) or np.any(classical <= 0)
            or isinstance(draws, bool) or not isinstance(draws, int) or draws < 1000
            or isinstance(seed, bool) or not isinstance(seed, int) or seed < 0):
        raise ValueError("Invalid paired bootstrap inputs")
    observed = float(learned.mean() / classical.mean())
    generator = np.random.Generator(np.random.PCG64(seed))
    indices = generator.integers(0, learned.size, size=(draws, learned.size))
    ratios = learned[indices].mean(axis=1) / classical[indices].mean(axis=1)
    low, high = np.quantile(ratios, [0.025, 0.975], method="linear")
    return {
        "n": int(learned.size),
        "observed_ratio_of_means": observed,
        "percentile_95_interval": [float(low), float(high)],
        "draws": draws,
        "seed": seed,
        "rng": "numpy.random.PCG64",
        "quantile_method": "linear",
        "paired_resampling_unit": "case_id",
    }


def build_report(receipt: dict, receipt_sha256: str) -> dict:
    if receipt.get("schema") != "caos-geophysics.m12-nullspace-residual/v1.1":
        raise ValueError("Unsupported M12 nullspace receipt")
    if receipt_sha256 != EXPECTED_RECEIPT_SHA256:
        raise ValueError("Receipt identity differs from the frozen v1.1 evidence")
    result = {}
    for cohort_name in COHORTS:
        cohort = receipt["cohorts"][cohort_name]
        result[cohort_name] = {}
        for label, (learned_key, classical_key, ratio_key) in METRICS.items():
            learned, classical = _paired_arrays(cohort, learned_key, classical_key)
            summary_ratio = float(cohort[ratio_key])
            if not np.isclose(summary_ratio, learned.mean() / classical.mean(), rtol=1e-12, atol=1e-14):
                raise ValueError(f"Receipt aggregate differs from per-case values: {cohort_name}/{label}")
            result[cohort_name][label] = paired_bootstrap_ratio(learned, classical)
    return {
        "schema": "caos-geophysics.m12-nullspace-v1.1-paired-bootstrap/v1",
        "receipt_sha256": receipt_sha256,
        "method": "Resample paired case IDs with replacement; for each draw compute mean learned RMSE divided by mean classical RMSE.",
        "limitations": [
            "Intervals quantify resampling variation within these fixed synthetic cohorts only.",
            "They do not quantify variation across natural geology or establish field performance.",
        ],
        "cohorts": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/validation/m12-nullspace-v1_1-bootstrap-2026-10-30.json")
    args = parser.parse_args()
    raw = RECEIPT.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    report = build_report(json.loads(raw), digest)
    report["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    target = args.output.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
