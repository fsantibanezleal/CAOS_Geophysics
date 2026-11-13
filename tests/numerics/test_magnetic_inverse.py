"""Independent generated M04 truth controls; no accepted inverse is exposed here."""

import hashlib
import json
from pathlib import Path
from decimal import Decimal, localcontext
from time import monotonic

import choclo
from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as MU0
import numpy as np
import pytest
import scipy.sparse as sp

import magnetic_forward
from magnetic_inverse import MagneticQuantity, build_operator
import magnetic_optimizer_adapter
from magnetic_optimizer_adapter import MagneticObjective, MagneticRegularizer
import magnetic_original_optimizer
import physical_original_quadratic
import physical_original_optimizer
import physical_owned_spd
from magnetic_likelihood import GaussianWhitener
from magnetic_quantity import compose_magnetic_observable
from magnetic_survey import plan_geometry
from magnetic_survey_json import InputError, parse_request


ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "tests" / "fixtures" / "magnetic_survey" / "generated"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _small_forward_request():
    return {
        "schema": "magnetic-prism-forward-request-1", "engine": magnetic_forward.ENGINE,
        "frame": magnetic_forward.FRAME,
        "mesh": {"origin_m": np.array([-50., -40., -120.]),
                 "hx_m": np.array([100.]), "hy_m": np.array([80.]),
                 "hz_m": np.array([120.]), "active": np.array([True])},
        "receivers_m": np.array([[0., 0., 100.], [170., 30., 120.], [-100., 160., 240.]]),
        "susceptibility_si": np.array([.03]),
        "inducing_field": {"amplitude_nt": 50000., "inclination_deg": 60.,
                           "declination_deg": 12.},
    }


def _independent_secondary(chi_si, request):
    field = request["inducing_field"]
    inc, dec = np.deg2rad([field["inclination_deg"], field["declination_deg"]])
    direction = np.array([np.cos(inc)*np.sin(dec), np.cos(inc)*np.cos(dec), -np.sin(inc)])
    magnetization = chi_si * direction * field["amplitude_nt"] * 1e-9 / MU0
    bounds = (-50., 50., -40., 40., -120., 0.)
    return np.asarray([
        choclo.prism.magnetic_field(*receiver, *bounds, *magnetization)
        for receiver in request["receivers_m"]
    ], dtype=np.float64) * 1e9


def _independent_observable(secondary, request, quantity):
    field = request["inducing_field"]
    inc, dec = np.deg2rad([field["inclination_deg"], field["declination_deg"]])
    direction = np.array([np.cos(inc)*np.sin(dec), np.cos(inc)*np.cos(dec), -np.sin(inc)])
    if quantity == "secondary_enu":
        return secondary.reshape(-1)
    if quantity == "linear_tmi_nT":
        return secondary @ direction
    f = Decimal.from_float(field["amplitude_nt"])
    b0 = np.asarray(request["inducing_field"]["amplitude_nt"]*direction, dtype=np.float64)
    result = []
    with localcontext() as context:
        context.prec = 80
        for vector in secondary:
            total = [Decimal.from_float(float(a+b)) for a, b in zip(b0, vector)]
            result.append(float(sum((value*value for value in total), Decimal(0)).sqrt()-f))
    return np.asarray(result, dtype=np.float64)


def test_independent_case_matrix():
    manifest_raw = (GENERATED / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    assert manifest["schema"] == "m04-independent-s2-acquisitions-1"
    cases = manifest["cases"]
    assert len(cases) == 18
    assert {(item["regime"], item["quantity"]) for item in cases} == {
        (regime, quantity) for regime in "ABCDEF" for quantity in
        ("secondary_enu_nT", "linear_tmi_nT", "exact_total_anomaly_nT")}
    assert manifest["claims"] == {"field_observations": False, "geology_truth": False,
                                   "inverse_results": False, "method_acceptance": False}

    for item in cases:
        request_record, truth_record = item["request"], item["truth"]
        request_raw = (GENERATED / request_record["path"]).read_bytes()
        truth_raw = (GENERATED / truth_record["path"]).read_bytes()
        assert len(request_raw) == request_record["bytes"]
        assert len(truth_raw) == truth_record["bytes"]
        assert sha256(request_raw) == request_record["sha256"]
        assert sha256(truth_raw) == truth_record["sha256"]
        request = json.loads(request_raw)
        truth = json.loads(truth_raw)
        # The forward truth, body bounds, and noise-free predictions never enter
        # the input that a future calibration routine receives.
        assert not {"truth", "bodies", "clean_observable_nT",
                    "clean_secondary_components_nT"}.intersection(request)
        assert request["policy"]["optimizer_binding"] == {
            "accepted_source": None, "accepted_export": None, "epoch": None}
        assert truth["claims"]["inversion_accepted"] is False
        assert truth["request_source_sha256"] == request["source"]["original_sha256"]
        handle = parse_request(request_raw)
        if item["regime"] == "F":
            assert len(set(handle.metadata()["acquisition"]["group_ids"])) == 4
            with pytest.raises(InputError, match="twelve indivisible"):
                plan_geometry(handle)
            assert all(value == 0. for value in request["observations"]["values"]["data"])
        else:
            plan = plan_geometry(handle)
            assert truth["geometry_seal_sha256"] == plan["identity"]["seal_sha256"]
            assert len(plan["partition"]["outer_rows"]["data"]) == 72
            assert len(plan["partition"]["development_rows"]["data"]) == 216
        if item["regime"] == "D":
            assert truth["bodies"][0]["remanence_enu_a_per_m"] == [8., -5.5, 2.3]
        if item["regime"] == "E":
            assert request["inducing_field"]["I_deg"] == -35.
            assert truth["truth_field"]["I_deg"] == 37.


def test_quantity_specific_physics_and_jacobian():
    request = _small_forward_request()
    forward = magnetic_forward.forward_magnetic_with_kernel(request)
    kernel = forward["component_jacobian_nT_per_si"]
    background = forward["inducing_field"]["background_enu_nt"]
    q = 3.0
    chi = np.array([.01*q], dtype=np.float64)
    step = 2e-4
    for quantity in ("secondary_enu", "linear_tmi_nT", "exact_total_anomaly_nT"):
        actual = compose_magnetic_observable(kernel, chi, background, quantity)
        secondary = _independent_secondary(chi[0], request)
        expected = _independent_observable(secondary, request, quantity)
        np.testing.assert_allclose(actual["values_nT"].reshape(-1), expected,
                                   rtol=2e-8, atol=2e-7)
        plus = _independent_observable(_independent_secondary(.01*(q+step), request), request, quantity)
        minus = _independent_observable(_independent_secondary(.01*(q-step), request), request, quantity)
        finite_difference = (plus-minus)/(2*step)
        np.testing.assert_allclose(actual["jacobian_q_nT"].reshape(-1), finite_difference,
                                   rtol=3e-5, atol=3e-7)


def test_full_covariance_whitening():
    lower = np.array([
        [.7, 0., 0., 0., 0., 0.],
        [.19, .8, 0., 0., 0., 0.],
        [-.14, .23, .9, 0., 0., 0.],
        [.11, -.09, .2, .75, 0., 0.],
        [.08, .15, -.18, .12, .85, 0.],
        [-.2, .1, .16, -.13, .21, .95],
    ], dtype=np.float64)
    covariance = lower @ lower.T
    selected = np.array([0, 2, 5], dtype=np.int64)
    principal = covariance[np.ix_(selected, selected)]
    residual_full = np.array([.4, -.8, 1.2, .3, -1.1, .7], dtype=np.float64)
    residual = residual_full[selected]
    jacobian_full = np.array([[1., .2], [.1, -.4], [.7, .3],
                              [-.5, .8], [.2, .6], [.9, -.1]], dtype=np.float64)
    jacobian = jacobian_full[selected]
    whitener = GaussianWhitener("full_covariance", covariance, selected)
    factor = np.linalg.cholesky(principal)
    expected_white = np.linalg.solve(factor, residual)
    expected_jacobian = np.linalg.solve(factor, jacobian)
    np.testing.assert_allclose(whitener.whiten(residual), expected_white, rtol=1e-14, atol=1e-14)
    np.testing.assert_allclose(whitener.precision(residual), np.linalg.solve(principal, residual),
                               rtol=1e-14, atol=1e-14)
    np.testing.assert_allclose(whitener.weighted_column_norms(jacobian),
                               np.linalg.norm(expected_jacobian, axis=0), rtol=1e-14, atol=1e-14)
    diagonal_only = residual/np.sqrt(np.diag(principal))
    assert not np.allclose(expected_white, diagonal_only, rtol=1e-3, atol=1e-3)


def test_sealed_survey_operator_preserves_original_receiver_rows():
    manifest = json.loads((GENERATED / "manifest.json").read_bytes())
    item = next(case for case in manifest["cases"]
                if case["regime"] == "A" and case["quantity"] == "secondary_enu_nT")
    raw = (GENERATED / item["request"]["path"]).read_bytes()
    handle = parse_request(raw)
    metadata = handle.metadata()
    usable = metadata["geometry"]["usable"]["data"]
    rows = tuple(index for index, value in enumerate(usable) if value)[:4]
    assert len(rows) == 4

    operator = build_operator(raw, rows, deadline=monotonic() + 120.)
    mesh = metadata["geometry"]["mesh"]
    mesh_values = {
        "origin_m": np.asarray(mesh["origin_m"]["data"], dtype=np.float64),
        "hx_m": np.asarray(mesh["widths_x_m"]["data"], dtype=np.float64),
        "hy_m": np.asarray(mesh["widths_y_m"]["data"], dtype=np.float64),
        "hz_m": np.asarray(mesh["widths_z_m"]["data"], dtype=np.float64),
        "active": np.asarray(mesh["active"]["data"], dtype=np.bool_),
    }
    receivers = np.asarray(metadata["geometry"]["receivers_m"]["data"], dtype=np.float64)
    receivers = receivers.reshape(-1, 3, order="C")[list(rows)]
    field = metadata["inducing_field"]
    direct = magnetic_forward.forward_magnetic_with_kernel({
        "schema": "magnetic-prism-forward-request-1", "engine": magnetic_forward.ENGINE,
        "frame": magnetic_forward.FRAME, "mesh": mesh_values, "receivers_m": receivers,
        "susceptibility_si": np.zeros(int(mesh_values["active"].sum()), dtype=np.float64),
        "inducing_field": {"amplitude_nt": float(field["F_nT"]),
                           "inclination_deg": float(field["I_deg"]),
                           "declination_deg": float(field["D_deg"])},
    })
    q = np.linspace(.1, .8, operator.parameters, dtype=np.float64)
    expected = compose_magnetic_observable(
        direct["component_jacobian_nT_per_si"], .01 * q,
        direct["inducing_field"]["background_enu_nt"], "secondary_enu",
    )
    actual = operator.evaluate(q)
    np.testing.assert_allclose(actual["prediction_nT"], expected["values_nT"].reshape(-1),
                               rtol=1e-13, atol=1e-13)
    np.testing.assert_allclose(actual["jacobian_nT_per_q"], expected["jacobian_q_nT"],
                               rtol=1e-13, atol=1e-13)
    assert operator.rows == 4 and operator.components == 3


def test_nonlinear_lane_refuses_but_sparse_frozen_surrogate_runs_source_bound_solver(monkeypatch):
    request = _small_forward_request()
    forward = magnetic_forward.forward_magnetic_with_kernel(request)
    background = forward["inducing_field"]["background_enu_nt"]
    field_norm = float(np.linalg.norm(background))
    direction = background / field_norm
    nonlinear = MagneticQuantity(
        forward["component_jacobian_nT_per_si"], background, direction,
        field_norm, "exact_total_anomaly_nT",
    )
    prediction = nonlinear.evaluate(np.array([3.], dtype=np.float64))
    assert prediction["prediction_nT"].shape == (3,)
    assert prediction["jacobian_nT_per_q"].shape == (3, 1)

    sparse_request = _small_forward_request()
    sparse_request["mesh"]["hx_m"] = np.array([100., 100.], dtype=np.float64)
    sparse_request["mesh"]["active"] = np.ones(2, dtype=np.bool_)
    sparse_request["susceptibility_si"] = np.array([.03, .04], dtype=np.float64)
    sparse_forward = magnetic_forward.forward_magnetic_with_kernel(sparse_request)
    mesh = {"origin_m": sparse_request["mesh"]["origin_m"],
            "hx_m": sparse_request["mesh"]["hx_m"], "hy_m": sparse_request["mesh"]["hy_m"],
            "hz_m": sparse_request["mesh"]["hz_m"], "active": sparse_request["mesh"]["active"]}
    reference = np.array([.2, .25], dtype=np.float64)
    lengths = np.array([10., 10., 10.], dtype=np.float64)
    weight_model = np.array([.3, .35], dtype=np.float64)
    with pytest.raises(ValueError, match="frozen positive schedule"):
        MagneticRegularizer(mesh, reference, lengths, "sparse", .2, weight_model)
    with pytest.raises(TypeError, match="refresh model"):
        MagneticRegularizer(mesh, reference, lengths, "sparse", .1, None)
    sparse = MagneticRegularizer(mesh, reference, lengths, "sparse", .1, weight_model)
    refreshed = sparse.source.evaluate_sparse(weight_model, .1)
    q = np.array([.7, .65], dtype=np.float64)
    source_evaluations = []
    source_evaluate = sparse.source.evaluate
    def counted_source_evaluate(model):
        source_evaluations.append(None)
        return source_evaluate(model)
    monkeypatch.setattr(sparse.source, "evaluate", counted_source_evaluate)
    evaluated = sparse.evaluate(q)
    assert source_evaluations == []
    assert evaluated["engine_epoch"] == magnetic_optimizer_adapter.magnetic_regularization.ENGINE_EPOCH
    np.testing.assert_allclose(sparse.vendor(q), evaluated["phi"], rtol=2e-15, atol=0.)
    np.testing.assert_allclose(sparse.vendor.deriv(q), evaluated["gradient_q"], rtol=2e-14, atol=1e-15)
    np.testing.assert_array_equal(sparse.smallness_irls_weights, refreshed["smallness_irls_weights"])
    terms = sparse.terms()
    assert len(terms) == 2
    np.testing.assert_allclose(
        terms[0]["weights"],
        np.sqrt(sparse.source.volumes / sparse.source.total_volume
                * sparse.smallness_irls_weights), rtol=2e-15, atol=0.,
    )
    reconstructed_hessian = sp.csr_matrix(sparse.hessian.shape, dtype=np.float64)
    for term in terms:
        reconstructed_hessian += 2. * (
            term["alpha"] * term["derivative"].T
            @ sp.diags(term["weights"] ** 2, format="csr")
            @ term["derivative"]
        )
    np.testing.assert_allclose(reconstructed_hessian.toarray(), sparse.hessian.toarray(), atol=1e-15)
    field = sparse_forward["inducing_field"]["background_enu_nt"]
    field_norm = float(np.linalg.norm(field))
    linear_operator = MagneticQuantity(
        sparse_forward["component_jacobian_nT_per_si"], field, field / field_norm,
        field_norm, "secondary_enu_nT",
    )
    observed = linear_operator.evaluate(np.array([.8, .6], dtype=np.float64))["prediction_nT"]
    objective = MagneticObjective(
        linear_operator, sparse, observed,
        {"kind": "diagonal_sd", "values": np.ones(
            (linear_operator.rows, linear_operator.components), dtype=np.float64)},
        np.zeros(2, dtype=np.float64), np.full(2, 10., dtype=np.float64),
        .1, "a" * 64, "b" * 64,
    )
    phi, gradient, hessian = objective.evaluate(q, return_g=True, return_H=True)
    np.testing.assert_allclose(gradient, objective._state(q)[3], rtol=0., atol=0.)
    direction = np.array([.7, -.4], dtype=np.float64)
    np.testing.assert_allclose(hessian @ direction,
                               2. * objective._state(q)[-1].T
                               @ (objective._state(q)[-1] @ direction)
                               + objective.beta * sparse.hessian @ direction,
                               rtol=2e-14, atol=1e-14)
    assert np.isfinite(phi)
    dto = magnetic_original_optimizer._MagneticDTO(objective, 9)
    operands = dto.quadratic_operands(q)
    assert len(operands.terms) == len(sparse.terms())
    np.testing.assert_allclose(operands.terms[0].weights.diagonal(), terms[0]["weights"])
    physical_original_quadratic.validate(
        operands, dto.identity(), q, deadline=monotonic() + 15.,
        resource_limit_bytes=805_306_368, admitted_bytes=805_306_368,
    )
    metric_model = np.array([.3, .4], dtype=np.float64)
    metric = dto.metric_operands(metric_model)
    metric_allocation = physical_owned_spd.validate_operands(
        metric, dto.identity(), metric_model, 805_306_368,
    )
    assert metric_allocation["maximum"] <= 805_306_368
    allocation_sha = "b" * 64
    budget = physical_original_optimizer.ConditionedBudget(
        monotonic() + 120., 200, 805_306_368, 805_306_368, allocation_sha,
    )
    terminal = physical_owned_spd.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6)
    start = metric_model.copy()
    solved = magnetic_optimizer_adapter.solve_linear(
        objective, start, source_components=9, budget=budget, terminal=terminal,
    )
    assert solved["status"] == "converged", repr(solved)[:4000]
    assert solved["iterations"] > 0

    # A native zero direction is recoverable only when the same exact source
    # state passes the independent original-objective terminal certificate.
    stationary_regularizer = MagneticRegularizer(
        mesh, q, lengths, "sparse", .1, q.copy(),
    )
    stationary_objective = MagneticObjective(
        linear_operator, stationary_regularizer,
        linear_operator.evaluate(q)["prediction_nT"],
        {"kind": "diagonal_sd", "values": np.ones(
            (linear_operator.rows, linear_operator.components), dtype=np.float64)},
        np.zeros(2, dtype=np.float64), np.full(2, 10., dtype=np.float64),
        .1, "a" * 64, "b" * 64,
    )
    native_stopping = physical_original_optimizer.reduced.core.linear._NativeRecorded.stoppingCriteria

    def withhold_stationary_stop(self, inLS=False):
        if inLS:
            self.reason = "zero_free_direction"
            raise physical_original_optimizer.reduced.core.linear._Failure("zero_free_direction")
        answer = native_stopping(self, inLS)
        if not inLS and answer and self.reason == "absolute_stationary":
            return False
        return answer

    monkeypatch.setattr(
        physical_original_optimizer.reduced.core.linear._NativeRecorded,
        "stoppingCriteria", withhold_stationary_stop,
    )
    stationary_budget = physical_original_optimizer.ConditionedBudget(
        monotonic() + 120., 200, 805_306_368, 805_306_368, allocation_sha,
    )
    stationary = magnetic_optimizer_adapter.solve_linear(
        stationary_objective, q.copy(), source_components=9,
        budget=stationary_budget, terminal=terminal,
    )
    assert stationary["status"] == "converged", repr(stationary)[:4000]
    assert stationary["reason"] == "absolute_stationary"
    assert stationary["iterations"] == 0
    np.testing.assert_array_equal(stationary["q"], q)
    assert stationary["terminal_audits"][-1]["check"]["proof_basis"] == (
        "original_physical_residual_strong_convexity"
    )
    assert stationary["terminal_audits"][-1]["check"]["passed"] is True

    monkeypatch.setattr(physical_original_optimizer._Linear, "stronger_terminal", lambda _self: False)
    uncertified = magnetic_optimizer_adapter.solve_linear(
        stationary_objective, q.copy(), source_components=9,
        budget=physical_original_optimizer.ConditionedBudget(
            monotonic() + 120., 200, 805_306_368, 805_306_368, allocation_sha,
        ), terminal=terminal,
    )
    assert uncertified["status"] == "nonconverged"
    assert uncertified["reason"] == "zero_free_direction"

    l2 = MagneticRegularizer(mesh, reference, lengths)
    with pytest.raises(ValueError, match="affine magnetic quantities"):
        MagneticObjective(
            nonlinear, l2, np.zeros(3, dtype=np.float64),
            {"kind": "diagonal_sd", "values": np.ones((3, 1), dtype=np.float64)},
            np.zeros(1, dtype=np.float64), np.full(1, 10., dtype=np.float64),
            .1, "a" * 64, "b" * 64,
        )


def test_magnetic_regularizer_rejects_oversized_mesh_before_tensor_allocation(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("TensorMesh construction preceded physical mesh caps")

    monkeypatch.setattr("discretize.TensorMesh", forbidden)
    mesh = {"origin_m": np.zeros(3, dtype=np.float64),
            "hx_m": np.ones(64, dtype=np.float64),
            "hy_m": np.ones(64, dtype=np.float64),
            "hz_m": np.ones(2, dtype=np.float64),
            "active": np.ones(8192, dtype=np.bool_)}
    reference = np.ones(8192, dtype=np.float64)
    lengths = np.ones(3, dtype=np.float64)
    with pytest.raises(ValueError, match="full-cell cap"):
        MagneticRegularizer(mesh, reference, lengths)
