import numpy as np

import magnetic_fit_assembly as assembly
from magnetic_survey_json import parse_request
from magnetic_survey_support import descriptor, encode, rehash, request


def test_assembles_only_sealed_fit_rows_and_subsets_data_noise(monkeypatch):
    doc = request()
    doc["observations"]["values"]["data"] = [float(i) for i in range(864)]
    rehash(doc, "observations/values")
    handle = parse_request(encode(doc))
    seen = {}
    fit_rows = np.array([0, 1, 2, 3], dtype=np.int64)
    fake_plan = {
        "partition": {"outer_rows": {"data": [5]}, "folds": [{
            "fit_rows": {"data": fit_rows.tolist()}, "validation_rows": {"data": [6]},
        }, {"fit_rows": {"data": [7]}, "validation_rows": {"data": [8]}},
            {"fit_rows": {"data": [9]}, "validation_rows": {"data": [10]}}]},
        "identity": {"seal_sha256": "a" * 64},
    }

    class Regularizer:
        def __init__(self, mesh, active, reference_q, lengths):
            self.parameter_count = int(np.count_nonzero(active))
            seen["regularizer_shape"] = (mesh.nC, self.parameter_count)

        def evaluate(self, q):
            return {"phi": float(np.dot(q, q))}

    def forward(request):
        seen["receivers"] = request["receivers_m"].copy()
        seen["start_si"] = request["susceptibility_si"].copy()
        return {"component_jacobian_nT_per_si": np.zeros(
            (3 * len(request["receivers_m"]), len(request["susceptibility_si"])),
            dtype=np.float64,
        )}

    monkeypatch.setattr(assembly, "MagneticRegularizer", Regularizer)
    monkeypatch.setattr(assembly, "forward_magnetic_with_kernel", forward)
    monkeypatch.setattr(assembly, "plan_geometry", lambda passed: fake_plan if passed is handle else None)
    result = assembly.assemble_magnetic_fit_objective(handle, 0)
    fit = result["fit_rows"]
    expected = (fit[:, None] * 3 + np.arange(3, dtype=np.int64)).reshape(-1)
    assert np.array_equal(result["source_flat_indices"], expected)
    assert np.array_equal(seen["receivers"],
                          np.asarray(request()["geometry"]["receivers_m"]["data"]).reshape(-1, 3)[fit])
    assert np.array_equal(result["initial_data"]["residual_observed_minus_predicted_nT"],
                          np.asarray(doc["observations"]["values"]["data"])[expected])
    assert result["initial_data"]["phi_d"] > 0.
    assert "no inversion performed" in result["claim"]


def test_rejects_nonfold_index_before_any_geometry_work(monkeypatch):
    monkeypatch.setattr(assembly, "plan_geometry", lambda handle: (_ for _ in ()).throw(
        AssertionError("geometry should not run for invalid fold")))
    try:
        assembly.assemble_magnetic_fit_objective(parse_request(encode(request())), True)
    except ValueError as exc:
        assert "fold_index" in str(exc)
    else:
        raise AssertionError("invalid fold was accepted")


def test_subsets_full_covariance_by_original_scalar_rows(monkeypatch):
    doc = request()
    obs = descriptor("float64", [288, 1], [float(i) for i in range(288)])
    doc["processing"]["quantity"] = "linear_tmi_nT"
    doc["processing"]["background_relation"] = "projection_of_secondary_declared"
    doc["processing"]["nodes"][0]["output_sha256"] = obs["sha256"]
    doc["observations"] = {"quantity": "linear_tmi_nT", "unit": "nT",
                           "values": obs, "values_sha256": obs["sha256"]}
    covariance = np.eye(288, dtype=np.float64) * 0.25
    doc["noise"] = {"kind": "full_covariance", "unit": "nT^2",
                    "values": descriptor("float64", [288, 288], covariance.reshape(-1).tolist()),
                    "basis": "explicit_conditional_gaussian", "citation": "test covariance",
                    "cross_partition_dependence": "declared_absent"}
    handle = parse_request(encode(doc))
    fit_rows = [2, 4, 6]
    fake_plan = {
        "partition": {"outer_rows": {"data": [8]}, "folds": [
            {"fit_rows": {"data": fit_rows}, "validation_rows": {"data": [10]}},
            {"fit_rows": {"data": [12]}, "validation_rows": {"data": [14]}},
            {"fit_rows": {"data": [16]}, "validation_rows": {"data": [18]}},
        ]},
        "identity": {"seal_sha256": "b" * 64},
    }

    class Regularizer:
        def __init__(self, mesh, active, reference_q, lengths):
            self.parameter_count = int(np.count_nonzero(active))

        def evaluate(self, q):
            return {"phi": 0.0}

    def forward(request):
        return {"component_jacobian_nT_per_si": np.zeros(
            (3 * len(request["receivers_m"]), len(request["susceptibility_si"])),
            dtype=np.float64,
        )}

    monkeypatch.setattr(assembly, "MagneticRegularizer", Regularizer)
    monkeypatch.setattr(assembly, "forward_magnetic_with_kernel", forward)
    monkeypatch.setattr(assembly, "plan_geometry", lambda passed: fake_plan)
    result = assembly.assemble_magnetic_fit_objective(handle, 0)
    assert np.array_equal(result["source_flat_indices"], np.array(fit_rows, dtype=np.int64))
    assert result["initial_data"]["phi_d"] == sum((row / 0.5) ** 2 for row in fit_rows)


def test_actual_nonzero_simpeg_fit_assembly_has_physical_objective_derivative():
    doc = request()
    doc["prior"]["start_si"]["data"] = [0.002] * 528
    rehash(doc, "prior/start_si")
    result = assembly.assemble_magnetic_fit_objective(parse_request(encode(doc)), 0)
    objective = result["objective"]
    q = result["start_q"].copy()
    direction = np.zeros_like(q)
    direction[0] = 1.
    step = 1e-5
    plus = objective.evaluate(q + step * direction)["phi_d"]
    minus = objective.evaluate(q - step * direction)["phi_d"]
    finite_difference = (plus - minus) / (2 * step)
    analytic = float(result["initial_data"]["gradient_q"] @ direction)
    assert len(result["fit_rows"]) > 0
    assert result["initial_data"]["phi_d"] > 0.
    assert np.isfinite(analytic) and abs(analytic) > 0.
    assert np.isclose(finite_difference, analytic, rtol=2e-5, atol=2e-6)
