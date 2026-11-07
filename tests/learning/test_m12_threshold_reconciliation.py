import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "reconcile_m12_nullspace_threshold.py"
SPEC = importlib.util.spec_from_file_location("m12_threshold_reconciliation", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def _rows(prefix, values):
    return [{"id": f"{prefix}-{index}", "learned_oracle_rmse_ms": value,
             "forward_threshold_exceeded": False}
            for index, value in enumerate(values)]


def _receipt():
    return {
        "schema": module.SOURCE_SCHEMA,
        "protocol": module.SOURCE_PROTOCOL,
        "fixture": False,
        "counts": {"calibration": 20, "id_test": 4, "family_only": 4,
                   "acquisition_only": 4, "joint_ood": 4},
        "refinement": {"calibration_metrics": {
            "count": 20, "per_record": _rows("cal", list(range(1, 21))) }},
        "cohorts": {
            "id_test": {"count": 4, "per_record": _rows("id", [17.0, 19.0, 20.0, 21.0])},
            "family_only": {"count": 4, "per_record": _rows("family", [1.0, 10.0, 20.0, 30.0])},
            "acquisition_only": {"count": 4, "per_record": _rows("acq", [17.0, 19.0, 20.0, 21.0])},
            "joint_ood": {"count": 4, "per_record": _rows("joint", [17.0, 19.0, 20.0, 21.0])},
        },
    }


def test_uses_calibration_only_quantile_and_recomputes_saved_flags():
    result = module.reconcile(_receipt(), "a" * 64)
    assert result["method"]["threshold_ms"] == pytest.approx(19.05)
    assert result["cohorts"]["id_test"]["exceedances"] == 2
    assert [row["forward_threshold_exceeded"] for row in result["cohorts"]["id_test"]["records"]] == [False, False, True, True]
    assert result["descriptive_rates"]["joint_ood_sensitivity"] == 0.5
    assert result["scope"]["scientific_acceptance"] is False


def test_rejects_fixture_or_inconsistent_record_count():
    receipt = _receipt()
    receipt["fixture"] = True
    with pytest.raises(ValueError, match="full immutable"):
        module.reconcile(receipt, "a" * 64)
    receipt = _receipt()
    receipt["cohorts"]["joint_ood"]["count"] += 1
    with pytest.raises(ValueError, match="count does not match"):
        module.reconcile(receipt, "a" * 64)


def test_rejects_duplicate_ids_and_nonfinite_scores():
    receipt = _receipt()
    receipt["cohorts"]["id_test"]["per_record"][1]["id"] = "id-0"
    with pytest.raises(ValueError, match="duplicate"):
        module.reconcile(receipt, "a" * 64)
    receipt = _receipt()
    receipt["refinement"]["calibration_metrics"]["per_record"][0]["learned_oracle_rmse_ms"] = float("nan")
    with pytest.raises(ValueError, match="invalid learned oracle"):
        module.reconcile(receipt, "a" * 64)


def test_rejects_boolean_error_values():
    receipt = _receipt()
    receipt["cohorts"]["id_test"]["per_record"][0]["learned_oracle_rmse_ms"] = True
    with pytest.raises(ValueError, match="invalid learned oracle"):
        module.reconcile(receipt, "a" * 64)
