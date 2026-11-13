import numpy as np

import magnetic_fit_assembly as assembly
import magnetic_fold_score as scoring
from magnetic_survey_json import parse_request
from magnetic_survey_support import descriptor, encode, request


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
    reader = scoring.read_selected_likelihood
    field = request()["inducing_field"]
    inc, dec = np.deg2rad([field["I_deg"], field["D_deg"]])
    engine_background = field["F_nT"] * np.array([
        np.cos(inc) * np.sin(dec), np.cos(inc) * np.cos(dec), -np.sin(inc),
    ])
    compose = scoring.compose_magnetic_observable

    def selected_reader(passed, indices, seal):
        document, observed, noise = reader(passed, indices, seal)
        seen["selected_indices"] = indices
        seen["observed_shape"] = observed.shape
        seen["noise_shape"] = noise.shape
        return document, observed, noise

    def forward(request):
        seen["receivers"] = request["receivers_m"].copy()
        kernel = np.zeros((3 * len(request["receivers_m"]), len(model)), dtype=np.float64)
        kernel[0::3, 0] = 1.
        return {"component_jacobian_nT_per_si": kernel,
                "inducing_field": {"background_enu_nt": engine_background}}

    def compose_with_observed_background(kernel, susceptibility, background, quantity):
        seen["background"] = background.copy()
        return compose(kernel, susceptibility, background, quantity)

    monkeypatch.setattr(scoring, "plan_geometry", lambda passed: plan)
    monkeypatch.setattr(assembly, "plan_geometry", lambda passed: plan)
    monkeypatch.setattr(scoring, "read_selected_likelihood", selected_reader)
    monkeypatch.setattr(scoring, "forward_magnetic_with_kernel", forward)
    monkeypatch.setattr(scoring, "compose_magnetic_observable", compose_with_observed_background)
    result = scoring.score_magnetic_validation_fold(
        handle, 0, model, scoring.model_q_sha256(model)
    )
    expected_rms = 0.01 / np.sqrt(3.)
    assert result["role"] == "development-validation-only"
    assert result["observation_count"] == 9
    assert len(seen["selected_indices"]) == 9
    assert seen["observed_shape"] == (9,)
    assert seen["noise_shape"] == (9, 1)
    np.testing.assert_array_equal(seen["background"], engine_background)
    assert seen["background"][2] < 0.
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


def test_linear_tmi_score_uses_engine_enu_vertical_sign(monkeypatch):
    doc = request()
    observations = descriptor("float64", [288, 1], [0.0] * 288)
    doc["processing"]["quantity"] = "linear_tmi_nT"
    doc["processing"]["background_relation"] = "projection_of_secondary_declared"
    doc["processing"]["nodes"][0]["output_sha256"] = observations["sha256"]
    doc["observations"] = {"quantity": "linear_tmi_nT", "unit": "nT",
                           "values": observations, "values_sha256": observations["sha256"]}
    doc["noise"] = {"kind": "diagonal_sd", "unit": "nT",
                    "values": descriptor("float64", [288, 1], [0.5] * 288),
                    "basis": "explicit_conditional_gaussian", "citation": "test SD",
                    "cross_partition_dependence": "declared_absent"}
    handle = parse_request(encode(doc))
    model = np.zeros(528, dtype=np.float64)
    model[0] = 1.0
    validation = [2, 4, 6]
    plan = {
        "partition": {"outer_rows": {"data": [8]}, "folds": [
            {"validation_rows": {"data": validation}},
            {"validation_rows": {"data": [10]}},
            {"validation_rows": {"data": [12]}},
        ]},
        "identity": {"seal_sha256": "c" * 64},
    }
    field = doc["inducing_field"]
    inclination, declination = np.deg2rad([field["I_deg"], field["D_deg"]])
    engine_background = field["F_nT"] * np.array([
        np.cos(inclination) * np.sin(declination),
        np.cos(inclination) * np.cos(declination),
        -np.sin(inclination),
    ])

    def forward(request):
        kernel = np.zeros((3 * len(request["receivers_m"]), len(model)), dtype=np.float64)
        kernel[2::3, 0] = 1.0
        return {"component_jacobian_nT_per_si": kernel,
                "inducing_field": {"background_enu_nt": engine_background}}

    monkeypatch.setattr(scoring, "plan_geometry", lambda _: plan)
    monkeypatch.setattr(assembly, "plan_geometry", lambda _: plan)
    monkeypatch.setattr(scoring, "forward_magnetic_with_kernel", forward)
    result = scoring.score_magnetic_validation_fold(
        handle, 0, model, scoring.model_q_sha256(model)
    )

    expected_prediction = 0.01 * -np.sin(inclination)
    assert result["quantity"] == "linear_tmi_nT"
    assert result["observation_count"] == len(validation)
    assert np.isclose(result["residual_rms_nT"], abs(expected_prediction))
    assert np.isclose(result["phi_d"], len(validation) * (expected_prediction / 0.5) ** 2)


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
