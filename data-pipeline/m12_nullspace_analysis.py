"""Descriptive analysis of the immutable M12 null-space v1.1 research receipt.

This module does not run an inverse or promote scientific acceptance. It
reconstructs cohort summaries from the receipt's paired per-realization
errors, so course figures can be checked against the recorded aggregate.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math

import numpy as np


COHORTS = ("id_test", "family_only", "acquisition_only", "joint_ood")
ERROR_PAIRS = {
    "velocity": ("learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s"),
    "oracle_time": ("learned_oracle_rmse_ms", "classical_oracle_rmse_ms"),
}


def _paired_values(records: Sequence[Mapping[str, object]], learned: str,
                   classical: str) -> tuple[np.ndarray, np.ndarray]:
    if not records:
        raise ValueError("cohort must contain per-record outcomes")
    try:
        left = np.asarray([row[learned] for row in records], dtype=np.float64)
        right = np.asarray([row[classical] for row in records], dtype=np.float64)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("per-record outcomes do not satisfy the paired error contract") from exc
    if left.ndim != 1 or right.shape != left.shape or not np.all(np.isfinite(left)) \
            or not np.all(np.isfinite(right)) or np.any(left < 0) or np.any(right <= 0):
        raise ValueError("paired errors must be finite, nonnegative learned values and positive classical values")
    return left, right


def analyze_receipt(receipt: Mapping[str, object]) -> dict[str, object]:
    """Rebuild aggregate metrics and per-case diagnostics without changing verdicts."""
    if receipt.get("schema") != "caos-geophysics.m12-nullspace-residual/v1.1":
        raise ValueError("unsupported M12 receipt schema")
    if receipt.get("protocol") != "m12-nullspace-residual/v1.1":
        raise ValueError("unsupported M12 protocol")
    if receipt.get("fixture") is not False:
        raise ValueError("analysis requires the full held-out receipt, not a fixture")
    cohorts = receipt.get("cohorts")
    if not isinstance(cohorts, Mapping):
        raise ValueError("receipt has no cohort mapping")

    output: dict[str, object] = {
        "schema": "caos-geophysics.m12-nullspace-analysis/v1",
        "receipt_status": receipt.get("status"),
        "scientific_acceptance": receipt.get("scientific_acceptance"),
        "cohorts": {},
    }
    summaries: dict[str, object] = {}
    for name in COHORTS:
        cohort = cohorts.get(name)
        if not isinstance(cohort, Mapping):
            raise ValueError(f"missing held-out cohort: {name}")
        records = cohort.get("per_record")
        if not isinstance(records, list) or len(records) != cohort.get("count"):
            raise ValueError(f"cohort {name} has inconsistent per-record count")
        if len({row.get("id") for row in records if isinstance(row, Mapping)}) != len(records):
            raise ValueError(f"cohort {name} has duplicate or missing case identities")

        metrics: dict[str, object] = {}
        for metric, (learned_key, classical_key) in ERROR_PAIRS.items():
            learned, classical = _paired_values(records, learned_key, classical_key)
            ratio = float(np.mean(learned) / np.mean(classical))
            recorded_key = "learned_to_classical_velocity_ratio" if metric == "velocity" \
                else "learned_to_classical_oracle_ratio"
            recorded = cohort.get(recorded_key)
            if not isinstance(recorded, (int, float)) or not math.isclose(
                    ratio, float(recorded), rel_tol=1e-10, abs_tol=1e-12):
                raise ValueError(f"cohort {name} {metric} aggregate does not match paired records")
            ratios = learned / classical
            metrics[metric] = {
                "aggregate_ratio": ratio,
                "case_ratio_median": float(np.median(ratios)),
                "case_ratio_p90": float(np.quantile(ratios, 0.90)),
                "fraction_cases_better": float(np.mean(ratios < 1.0)),
                "case_ratios": ratios.tolist(),
            }
        velocity = np.asarray(metrics["velocity"]["case_ratios"])
        oracle = np.asarray(metrics["oracle_time"]["case_ratios"])
        metrics["both_metrics_better_fraction"] = float(np.mean((velocity < 1.0) & (oracle < 1.0)))
        metrics["count"] = len(records)
        metrics["forward_threshold_exceedances"] = cohort.get("forward_threshold_exceedances")
        summaries[name] = metrics

    output["cohorts"] = summaries
    alpha = receipt.get("refinement", {}).get("alpha_selection", {})
    output["calibration_selection"] = {
        "selected_alpha": alpha.get("selected_alpha"),
        "selected_lambda": receipt.get("classical", {}).get("selected_lambda"),
        "calibration_supported": alpha.get("calibration_supported"),
        "grid": alpha.get("grid", {}),
    }
    return output
