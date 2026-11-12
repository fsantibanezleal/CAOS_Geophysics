"""Descriptive analysis of the immutable M12 null-space v1.1 research receipt.

This module does not run an inverse or promote scientific acceptance. It
reconstructs cohort summaries from the receipt's paired per-realization
errors, so course figures can be checked against the recorded aggregate.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import csv
import hashlib
import io
import math
from pathlib import Path

import numpy as np


COHORTS = ("id_test", "family_only", "acquisition_only", "joint_ood")
ERROR_PAIRS = {
    "velocity": ("learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s"),
    "oracle_time": ("learned_oracle_rmse_ms", "classical_oracle_rmse_ms"),
}
PAIRED_CSV_COLUMNS = (
    "case_id",
    "cohort",
    "learned_velocity_rmse_m_s",
    "classical_velocity_rmse_m_s",
    "learned_oracle_rmse_ms",
    "classical_oracle_rmse_ms",
)


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


def paired_bootstrap_intervals(receipt: Mapping[str, object], cohort_name: str,
                               *, draws: int = 20_000, seed: int = 6_122_026) -> dict[str, object]:
    """Reproduce the manuscript's paired case-bootstrap intervals for both RMSE ratios.

    Each replicate resamples case indices with replacement and takes the ratio of
    the two cohort means. The two metrics use the same seeded index sequence,
    preserving the case pairing. Intervals describe resampling within this fixed
    synthetic cohort, not variation across geological settings.
    """
    if cohort_name not in COHORTS:
        raise ValueError(f"unknown held-out cohort: {cohort_name}")
    if isinstance(draws, bool) or not isinstance(draws, int) or draws < 2:
        raise ValueError("bootstrap draws must be an integer of at least two")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("bootstrap seed must be a nonnegative integer")
    analyze_receipt(receipt)
    cohorts = receipt.get("cohorts")
    cohort = cohorts.get(cohort_name) if isinstance(cohorts, Mapping) else None
    records = cohort.get("per_record") if isinstance(cohort, Mapping) else None
    if not isinstance(records, list) or not records:
        raise ValueError(f"cohort {cohort_name} has no paired records")

    count = len(records)
    indices = np.random.Generator(np.random.PCG64(seed)).integers(0, count, size=(draws, count))
    intervals: dict[str, object] = {}
    for metric, (learned_key, classical_key) in ERROR_PAIRS.items():
        learned, classical = _paired_values(records, learned_key, classical_key)
        ratios = learned[indices].mean(axis=1) / classical[indices].mean(axis=1)
        low, high = np.quantile(ratios, (0.025, 0.975), method="linear")
        intervals[metric] = {
            "point_ratio": float(learned.mean() / classical.mean()),
            "ci95": [float(low), float(high)],
        }
    return {
        "schema": "caos-geophysics.m12-paired-bootstrap/v1",
        "cohort": cohort_name,
        "count": count,
        "draws": draws,
        "seed": seed,
        "generator": "NumPy PCG64",
        "interval": "95% percentile; ratio of means per paired case-resample",
        "metrics": intervals,
    }


def analyze_paired_metrics_csv(path: str | Path, *, draws: int = 20_000,
                              seed: int = 6_122_026) -> dict[str, object]:
    """Analyze an external CSV of matched model- and data-space errors.

    This is a metrics workflow, not a raw-survey inversion. The caller must
    supply errors from the same cases, a declared truth/reference and an
    independently defined forward score. It cannot create those quantities.
    """
    if isinstance(draws, bool) or not isinstance(draws, int) or draws < 2:
        raise ValueError("bootstrap draws must be an integer of at least two")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("bootstrap seed must be a nonnegative integer")
    source = Path(path)
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    grouped: dict[str, list[dict[str, object]]] = {}
    seen: set[tuple[str, str]] = set()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("CSV must have one unique header row")
    missing = sorted(set(PAIRED_CSV_COLUMNS) - set(reader.fieldnames))
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")
    for line, row in enumerate(reader, start=2):
        if None in row or any(row.get(name) is None for name in PAIRED_CSV_COLUMNS):
            raise ValueError(f"CSV row {line} has an invalid column count")
        case_id = str(row["case_id"]).strip()
        cohort_name = str(row["cohort"]).strip()
        if not case_id or not cohort_name:
            raise ValueError(f"CSV row {line} has an empty case_id or cohort")
        identity = (cohort_name, case_id)
        if identity in seen:
            raise ValueError(f"CSV repeats case {case_id!r} in cohort {cohort_name!r}")
        seen.add(identity)
        record: dict[str, object] = {"id": case_id}
        for name in PAIRED_CSV_COLUMNS[2:]:
            try:
                record[name] = float(row[name])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"CSV row {line} has a nonnumeric {name}") from exc
        grouped.setdefault(cohort_name, []).append(record)
    if not grouped:
        raise ValueError("CSV contains no paired cases")

    output: dict[str, object] = {
        "schema": "caos-geophysics.m12-paired-csv-analysis/v1",
        "source_sha256": digest,
        "draws": draws,
        "seed": seed,
        "cohorts": {},
    }
    summaries: dict[str, object] = {}
    for cohort_name, records in sorted(grouped.items()):
        metrics: dict[str, object] = {}
        ratios_by_metric: dict[str, np.ndarray] = {}
        values = {
            metric: _paired_values(records, learned_key, classical_key)
            for metric, (learned_key, classical_key) in ERROR_PAIRS.items()
        }
        if len(records) < 2:
            raise ValueError("each cohort needs at least two paired cases for bootstrap intervals")
        indices = np.random.Generator(np.random.PCG64(seed)).integers(
            0, len(records), size=(draws, len(records))
        )
        for metric, (learned, classical) in values.items():
            case_ratios = learned / classical
            boot_ratios = learned[indices].mean(axis=1) / classical[indices].mean(axis=1)
            low, high = np.quantile(boot_ratios, (0.025, 0.975), method="linear")
            ratios_by_metric[metric] = case_ratios
            metrics[metric] = {
                "aggregate_ratio": float(learned.mean() / classical.mean()),
                "case_ratio_median": float(np.median(case_ratios)),
                "case_ratio_p90": float(np.quantile(case_ratios, 0.90)),
                "fraction_cases_better": float(np.mean(case_ratios < 1.0)),
                "ci95": [float(low), float(high)],
            }
        metrics["both_metrics_better_fraction"] = float(np.mean(
            (ratios_by_metric["velocity"] < 1.0)
            & (ratios_by_metric["oracle_time"] < 1.0)
        ))
        metrics["count"] = len(records)
        summaries[cohort_name] = metrics
    output["cohorts"] = summaries
    return output
