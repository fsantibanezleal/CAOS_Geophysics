"""Current-source end-to-end candidate L2 fold on sealed authored S2 bytes."""

import json
from pathlib import Path

import numpy as np
import pytest

import magnetic_calibration as calibration
import magnetic_survey
import magnetic_survey_json
from magnetic_survey_json import digest


ROOT = Path(__file__).parents[1] / "fixtures" / "magnetic_survey" / "generated"


def _request(name):
    return (ROOT / "requests" / name).read_bytes()


def test_full528_linear_l2_fold_is_bound_and_exports_only_fit_predictions():
    raw = _request("S2-A-linear_tmi_nT.json")
    manifest = json.loads((ROOT / "manifest.json").read_bytes())
    request_sha256 = __import__("hashlib").sha256(raw).hexdigest()
    record = next(case for case in manifest["cases"]
                  if case["regime"] == "A" and case["quantity"] == "linear_tmi_nT")
    assert request_sha256 == record["request"]["sha256"]

    handle = magnetic_survey_json.parse_request(raw)
    plan = magnetic_survey.plan_geometry(handle)
    fold = plan["partition"]["folds"][0]
    result = calibration.fit_l2_fold(raw, 0, 0.0001, wall_seconds=120.0)
    assert result["status"] == "converged", {
        key: result.get(key) for key in (
            "status", "reason", "iterations", "elapsed_seconds",
            "normalized_projected_kkt_inf", "objective",
        )
    }
    assert result["claims"] == {
        "field_observations": False,
        "field_geology_validated": False,
        "candidate_selected": False,
        "outer_evaluation_performed": False,
        "method_accepted": False,
        "online_admitted": False,
    }
    assert result["source_inventory_sha256"] == digest(result["source_inventory"])
    assert result["source_inventory"]["survey_request_sha256"] == request_sha256
    assert result["allocation_plan_sha256"] == digest(result["allocation"])
    assert result["allocation"]["parameters"] == 528
    assert result["allocation"]["fit_components"] == len(result["fit_rows"])
    assert result["fit_rows"] == fold["fit_rows"]["data"]
    assert set(result["fit_rows"]).isdisjoint(plan["partition"]["outer_rows"]["data"])
    assert set(result["fit_rows"]).isdisjoint(fold["validation_rows"]["data"])
    assert len(result["model_q"]) == 528
    assert result["prediction_nT"].shape == (len(result["fit_rows"]),)
    assert result["residual_observed_minus_predicted_nT"].shape == result["prediction_nT"].shape
    assert np.isfinite(result["model_q"]).all()
    assert np.isfinite(result["prediction_nT"]).all()
    assert result["normalized_projected_kkt_inf"] <= calibration.TERMINAL.required_kkt_normalized
    assert set(result["fit_rows"]).isdisjoint(result["trace"].get("outer_rows", []))


def test_nonlinear_quantity_refuses_before_forward_kernel(monkeypatch):
    raw = _request("S2-A-exact_total_anomaly_nT.json")

    def forbidden(*args, **kwargs):
        raise AssertionError("nonlinear quantity reached linear forward adapter")

    monkeypatch.setattr(calibration.magnetic_inverse, "build_operator", forbidden)
    with pytest.raises(ValueError, match="affine quantities"):
        calibration.fit_l2_fold(raw, 0, 0.0001)
