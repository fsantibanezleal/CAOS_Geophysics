"""Current-source end-to-end candidate L2 fold on sealed authored S2 bytes."""

import json
from pathlib import Path

import numpy as np
import pytest

import magnetic_calibration as calibration
import magnetic_inverse
import magnetic_optimizer_adapter
import magnetic_original_optimizer
import magnetic_regularization
import magnetic_survey
import magnetic_survey_json
from magnetic_survey_json import digest


ROOT = Path(__file__).parents[1] / "fixtures" / "magnetic_survey" / "generated"


def _request(name):
    return (ROOT / "requests" / name).read_bytes()


def test_linear_objective_reuses_one_frozen_simpeg_hessian_per_regularizer(monkeypatch):
    component_jacobian=np.array([
        [1.,.2], [.1,.7], [.4,.3],
        [.8,.5], [.3,.9], [.2,.6],
        [.5,.1], [.6,.4], [.9,.2],
    ],dtype=np.float64)
    direction=np.array([0.,0.,1.],dtype=np.float64)
    background=np.array([0.,0.,50000.],dtype=np.float64)
    operator=magnetic_inverse.MagneticQuantity(
        component_jacobian,background,direction,50000.,"linear_tmi_nT")
    mesh={
        "origin_m":np.array([0.,0.,0.],dtype=np.float64),
        "hx_m":np.array([2.,3.],dtype=np.float64),
        "hy_m":np.array([4.],dtype=np.float64),
        "hz_m":np.array([5.],dtype=np.float64),
        "active":np.ones(2,dtype=np.bool_),
    }
    reference=np.array([.1,.2],dtype=np.float64)
    calls=[]
    original=magnetic_regularization.WeightedLeastSquares.deriv2
    def counted(vendor,model,*args,**kwargs):
        calls.append(None)
        return original(vendor,model,*args,**kwargs)
    monkeypatch.setattr(magnetic_regularization.WeightedLeastSquares,"deriv2",counted)
    regularizer=magnetic_optimizer_adapter.MagneticRegularizer(
        mesh,reference,np.array([3.,4.,5.],dtype=np.float64))
    assert len(calls)==1
    beta=.03
    objective=magnetic_optimizer_adapter.MagneticObjective(
        operator,regularizer,np.array([.5,-.2,.1],dtype=np.float64),
        {"kind":"diagonal_sd","values":np.array([[.4],[.7],[.9]],dtype=np.float64)},
        np.zeros(2,dtype=np.float64),np.full(2,10.,dtype=np.float64),beta,"a"*64,"b"*64)
    q=np.array([.3,.5],dtype=np.float64)
    vector=np.array([-.7,.4],dtype=np.float64)
    weighted_jacobian=objective._state(q)[-1]
    regularizer_hessian=regularizer.source.hessian
    expected=2.*weighted_jacobian.T@(weighted_jacobian@vector)+beta*(regularizer_hessian@vector)

    _,_,hessian=objective.evaluate(q,return_g=True,return_H=True)
    np.testing.assert_allclose(hessian@vector,expected,rtol=2e-14,atol=1e-14)
    np.testing.assert_allclose(hessian@(-vector),-expected,rtol=2e-14,atol=1e-14)
    dto=magnetic_original_optimizer._MagneticDTO(objective,9)
    metric=dto.metric_operands(q)
    np.testing.assert_allclose(metric.regularizer.toarray(),beta*regularizer.source.hessian.toarray(),
                               rtol=0.,atol=0.)
    assert dto.metric_operands(q) is metric
    q_next=q.copy()
    q_next[0]=.31
    next_metric=dto.metric_operands(q_next)
    assert next_metric is not metric
    assert next_metric.regularizer is metric.regularizer
    assert next_metric.binding.model_sha256 != metric.binding.model_sha256
    np.testing.assert_array_equal(next_metric.whitened_jacobian,metric.whitened_jacobian)
    assert len(calls)==1


def test_source_inventory_binds_calibration_and_objective_decoder():
    raw = _request("S2-A-linear_tmi_nT.json")
    handle = magnetic_survey_json.parse_request(raw)
    plan = magnetic_survey.plan_geometry(handle)
    inventory = calibration._source_inventory(raw, plan["identity"]["seal_sha256"])
    for name in (
        "magnetic_calibration.py",
        "magnetic_fit_assembly.py",
        "magnetic_quantity.py",
        "simpeg.optimization",
        "simpeg.regularization",
    ):
        assert len(inventory[name]) == 64
        assert all(character in "0123456789abcdef" for character in inventory[name])


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
    diagnostics = {
        key: result.get(key) for key in (
            "status", "reason", "iterations", "elapsed_seconds",
            "normalized_projected_kkt_inf", "objective",
        )
    }
    diagnostics["terminal_audits_last"] = result.get("terminal_audits", ())[-3:]
    print("MAGNETIC_FOLD_DIAGNOSTICS " + json.dumps(diagnostics, sort_keys=True))
    assert result["status"] == "converged", diagnostics
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
    assert result["source_inventory"]["magnetic_calibration.py"] == __import__("hashlib").sha256(
        Path(calibration.__file__).read_bytes()
    ).hexdigest()
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
    assert len(result["terminal_audits"]) == 1
    terminal = result["terminal_audits"][0]
    assert terminal["passed"] and terminal["check_reason"] == "original_accuracy_certified"
    assert terminal["phase"] == "prediction_sensitivity" and terminal["active_sign_pass"]
    assert float(terminal["source_normalized_kkt_upper"]) <= calibration.TERMINAL.required_kkt_normalized
    assert float(terminal["kappa_upper"]) < 1.
    assert float(terminal["bounds"]["model_error_upper"]) <= calibration.TERMINAL.model_error_limit
    assert float(terminal["bounds"]["objective_gap_upper"]) <= calibration.TERMINAL.objective_gap_limit
    assert float(terminal["bounds"]["physical_prediction_error_upper"]) <= calibration.TERMINAL.physical_prediction_error_limit
    assert set(result["fit_rows"]).isdisjoint(result["trace"].get("outer_rows", []))


def test_nonlinear_quantity_refuses_before_forward_kernel(monkeypatch):
    raw = _request("S2-A-exact_total_anomaly_nT.json")

    def forbidden(*args, **kwargs):
        raise AssertionError("nonlinear quantity reached linear forward adapter")

    monkeypatch.setattr(calibration.magnetic_inverse, "build_operator", forbidden)
    with pytest.raises(ValueError, match="affine quantities"):
        calibration.fit_l2_fold(raw, 0, 0.0001)
