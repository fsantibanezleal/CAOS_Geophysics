import numpy as np

import magnetic_fold_score as scoring
from magnetic_survey_json import parse_request
from magnetic_survey_support import encode, request


def test_scores_only_validation_rows_and_returns_aggregate_metrics(monkeypatch):
    handle = parse_request(encode(request()))
    model = np.zeros(528, dtype=np.float64)
    model[0] = 1.
    validation = [2, 4, 6]
    plan = {
        "partition": {"outer_rows": {"data": [8]}, "folds": [
            {"validation_rows": {"data": validation}},
            {"validation_rows": {"data": [10]}},
            {"validation_rows": {"data": [12]}},
        ]},
        "identity": {"seal_sha256": "c" * 64},
    }
    seen = {}

    def forward(request):
        seen["receivers"] = request["receivers_m"].copy()
        kernel = np.zeros((3 * len(request["receivers_m"]), len(model)), dtype=np.float64)
        kernel[0::3, 0] = 1.
        return {"component_jacobian_nT_per_si": kernel}

    monkeypatch.setattr(scoring, "plan_geometry", lambda passed: plan)
    monkeypatch.setattr(scoring, "forward_magnetic_with_kernel", forward)
    result = scoring.score_magnetic_validation_fold(
        handle, 0, model, scoring.model_q_sha256(model)
    )
    expected_rms = 0.01 / np.sqrt(3.)
    assert result["role"] == "development-validation-only"
    assert result["observation_count"] == 9
    assert result["geometry_seal_sha256"] == "c" * 64
    assert np.isclose(result["residual_rms_nT"], expected_rms)
    assert result["phi_d"] > 0.
    assert result["contains_observation_vectors"] is False
    assert not any("residual" in key and key != "residual_rms_nT" for key in result)
    assert np.array_equal(seen["receivers"],
                          np.asarray(request()["geometry"]["receivers_m"]["data"])
                          .reshape(-1, 3)[validation])


def test_model_hash_mismatch_refuses_before_reading_geometry(monkeypatch):
    handle = parse_request(encode(request()))
    model = np.zeros(528, dtype=np.float64)
    monkeypatch.setattr(scoring, "plan_geometry", lambda _: (_ for _ in ()).throw(
        AssertionError("geometry must not run for an unfrozen model")))
    try:
        scoring.score_magnetic_validation_fold(handle, 0, model, "0" * 64)
    except ValueError as exc:
        assert "changed after freeze" in str(exc)
    else:
        raise AssertionError("modified candidate hash was accepted")


def test_actual_validation_score_uses_nonzero_physical_model():
    model = np.full(528, 0.002 / 0.01, dtype=np.float64)
    result = scoring.score_magnetic_validation_fold(
        parse_request(encode(request())), 0, model, scoring.model_q_sha256(model)
    )
    assert result["role"] == "development-validation-only"
    assert result["receiver_count"] > 0
    assert result["phi_d"] > 0.
    assert result["residual_rms_nT"] > 0.
    assert result["candidate_selection_performed"] is False
    assert result["outer_evaluation_performed"] is False
