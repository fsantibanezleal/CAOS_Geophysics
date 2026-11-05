"""Independent generated M04 truth controls; no accepted inverse is exposed here."""

import hashlib
import json
from pathlib import Path
from decimal import Decimal, localcontext

import choclo
from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as MU0
import numpy as np
import pytest

import magnetic_forward
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
