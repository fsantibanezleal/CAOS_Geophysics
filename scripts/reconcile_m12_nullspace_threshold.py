from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

SCHEMA = "caos-geophysics.m12-nullspace-threshold-reconciliation/v1"
SOURCE_SCHEMA = "caos-geophysics.m12-nullspace-residual/v1.1"
SOURCE_PROTOCOL = "m12-nullspace-residual/v1.1"
TEST_COHORTS = ("id_test", "family_only", "acquisition_only", "joint_ood")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _scores(section: dict, label: str) -> tuple[list[dict], np.ndarray]:
    if type(section) is not dict or type(section.get("per_record")) is not list:
        raise ValueError(f"{label}: missing per-record scores")
    rows = section["per_record"]
    count = section.get("count")
    if type(count) is not int or count <= 0 or len(rows) != count:
        raise ValueError(f"{label}: score count does not match rows")
    ids = [row.get("id") if type(row) is dict else None for row in rows]
    if any(type(value) is not str or not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"{label}: invalid or duplicate record IDs")
    raw_values = [row.get("learned_oracle_rmse_ms") for row in rows]
    if any(type(value) not in (int, float) for value in raw_values):
        raise ValueError(f"{label}: invalid learned oracle RMSE values")
    values = np.asarray(raw_values, dtype=np.float64)
    if values.shape != (len(rows),) or not np.isfinite(values).all() or np.any(values < 0.0):
        raise ValueError(f"{label}: invalid learned oracle RMSE values")
    return rows, values


def reconcile(receipt: dict, source_sha256: str) -> dict:
    if (type(receipt) is not dict or receipt.get("schema") != SOURCE_SCHEMA
            or receipt.get("protocol") != SOURCE_PROTOCOL or receipt.get("fixture") is not False
            or type(source_sha256) is not str or len(source_sha256) != 64
            or any(character not in "0123456789abcdef" for character in source_sha256)):
        raise ValueError("Expected a full immutable M12 null-space v1.1 receipt")
    calibration, calibration_values = _scores(
        receipt.get("refinement", {}).get("calibration_metrics"), "calibration")
    declared_counts = receipt.get("counts")
    if (type(declared_counts) is not dict
            or type(declared_counts.get("calibration")) is not int
            or declared_counts["calibration"] != len(calibration)):
        raise ValueError("Calibration count does not match the top-level receipt")
    threshold = float(np.quantile(calibration_values, 0.95, method="linear"))
    if not np.isfinite(threshold) or threshold <= 0.0:
        raise ValueError("Calibration threshold must be finite and positive")
    cohorts = {
        "calibration": {
            "count": len(calibration),
            "exceedances": int(np.count_nonzero(calibration_values > threshold)),
            "non_exceedances": int(np.count_nonzero(calibration_values <= threshold)),
            "exceedance_fraction": float(np.mean(calibration_values > threshold)),
            "records": [
                {"id": row["id"], "learned_oracle_rmse_ms": float(value),
                 "forward_threshold_exceeded": bool(value > threshold)}
                for row, value in zip(calibration, calibration_values, strict=True)
            ],
        }
    }
    for name in TEST_COHORTS:
        rows, values = _scores(receipt.get("cohorts", {}).get(name), name)
        if type(declared_counts.get(name)) is not int or declared_counts[name] != len(rows):
            raise ValueError(f"{name}: count does not match the top-level receipt")
        flags = values > threshold
        cohorts[name] = {
            "count": len(rows),
            "exceedances": int(np.count_nonzero(flags)),
            "non_exceedances": int(len(rows) - np.count_nonzero(flags)),
            "exceedance_fraction": float(np.mean(flags)),
            "records": [
                {"id": row["id"], "learned_oracle_rmse_ms": float(value),
                 "forward_threshold_exceeded": bool(flag)}
                for row, value, flag in zip(rows, values, flags, strict=True)
            ],
        }
    id_count = cohorts["id_test"]["count"]
    joint_count = cohorts["joint_ood"]["count"]
    return {
        "schema": SCHEMA,
        "source": {"schema": SOURCE_SCHEMA, "protocol": SOURCE_PROTOCOL,
                   "receipt_sha256": source_sha256},
        "method": {"threshold_ms": threshold, "quantile": 0.95,
                   "quantile_method": "numpy-linear", "reference": "calibration learned oracle RMSE only",
                   "comparison": "strict greater-than; no cohort-specific retuning"},
        "cohorts": cohorts,
        "descriptive_rates": {
            "id_test_specificity": 1.0 - cohorts["id_test"]["exceedance_fraction"],
            "joint_ood_sensitivity": cohorts["joint_ood"]["exceedance_fraction"],
            "interpretation": "synthetic cohort diagnostics only; not a calibrated field detector",
        },
        "scope": {
            "original_receipt_modified": False,
            "original_rmse_metrics_changed": False,
            "scientific_acceptance": False,
            "field_validity": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.receipt.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if source == output or output.exists():
        parser.error("output must be a new path distinct from the source receipt")
    parsed = json.loads(source.read_text(encoding="utf-8"))
    analysis = reconcile(parsed, sha256_file(source))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(analysis, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({name: {key: value for key, value in item.items() if key != "records"}
                      for name, item in analysis["cohorts"].items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
