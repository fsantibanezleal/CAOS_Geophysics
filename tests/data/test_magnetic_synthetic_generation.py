"""Independent synthetic M04 acquisition controls, never field-data evidence."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import choclo
from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as MU0
from decimal import Decimal, localcontext

from magnetic_survey import plan_geometry
from magnetic_survey_json import InputError, parse_request


PATH = Path(__file__).parents[1] / "fixtures" / "magnetic_survey" / "generate.py"
SPEC = importlib.util.spec_from_file_location("magnetic_acquisition_generator", PATH)
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


def canonical_request(document):
    return json.dumps(document, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


@pytest.mark.parametrize("regime", list("ABCDE"))
@pytest.mark.parametrize("quantity", generator._QUANTITIES)
def test_frozen_synthetic_regime_and_quantity_protocol(regime, quantity):
    request, truth = generator.acquisition_case(regime, quantity)
    replay, replay_truth = generator.acquisition_case(regime, quantity)
    assert canonical_request(request) == canonical_request(replay)
    assert truth == replay_truth
    handle = parse_request(canonical_request(request))
    meta = handle.metadata()
    count = 288
    components = 3 if quantity == "secondary_enu_nT" else 1
    assert meta["observations"]["values"]["shape"] == [count, components]
    assert meta["noise"]["values"]["shape"] == [count, components]
    assert request["source"]["scope"] == "complete_acquisition"
    assert truth["claims"] == {"field_observation": False, "geology_truth": False,
                                "optimizer_accepted": False, "inversion_accepted": False}
    actual = request["observations"]["values"]["data"]
    assert not np.array_equal(truth["clean_observable_nT"], actual)
    assert len(set(actual)) > 1
    assert meta["policy"]["optimizer_binding"] == {
        "accepted_source": None, "accepted_export": None, "epoch": None}


def test_geometry_is_planned_before_likelihood_and_has_frozen_memberships():
    request, _ = generator.acquisition_case("A", "secondary_enu_nT")
    handle = parse_request(canonical_request(request))
    plan = plan_geometry(handle)
    _, truth = generator.acquisition_case("A", "secondary_enu_nT")
    assert truth["geometry_seal_sha256"] == plan["identity"]["seal_sha256"]
    assert len(plan["partition"]["unit_ids"]) == 288
    assert len(plan["partition"]["outer_rows"]["data"]) == 72
    assert len(plan["partition"]["development_rows"]["data"]) == 216
    for fold in plan["partition"]["folds"]:
        assert len(fold["fit_rows"]["data"]) == 144
        assert len(fold["validation_rows"]["data"]) == 72
        assert fold["buffered_rows"]["data"] == []
    assert plan["claims"]["geology_truth_known"] is False


def test_remanent_and_wrong_field_negative_truth_are_explicit_and_distinct():
    req_a, truth_a = generator.acquisition_case("A", "secondary_enu_nT")
    req_d, truth_d = generator.acquisition_case("D", "secondary_enu_nT")
    req_e, truth_e = generator.acquisition_case("E", "secondary_enu_nT")
    assert truth_d["bodies"][0]["remanence_enu_a_per_m"] == [8., -5.5, 2.3]
    assert not np.allclose(truth_d["clean_secondary_components_nT"],
                           truth_a["clean_secondary_components_nT"], rtol=1e-10, atol=1e-10)
    assert (req_e["inducing_field"]["I_deg"], req_e["inducing_field"]["D_deg"]) == (-35., -100.)
    assert (truth_e["truth_field"]["I_deg"], truth_e["truth_field"]["D_deg"]) == (37., -73.)
    assert req_a["inducing_field"]["I_deg"] == truth_a["truth_field"]["I_deg"]


def test_off_grid_truth_and_remanence_match_independent_choclo_calls():
    request, truth = generator.acquisition_case("D", "secondary_enu_nT")
    received = np.asarray(request["geometry"]["receivers_m"]["data"], dtype=np.float64).reshape(-1, 3)
    inclination, declination = np.deg2rad([37., -73.])
    inducing = np.array([np.cos(inclination)*np.sin(declination),
                         np.cos(inclination)*np.cos(declination), -np.sin(inclination)])
    field_t = inducing * 50_000e-9
    bodies = [
        ((310., 770., 1700., 2570., -510., -130.), .012, np.array([8., -5.5, 2.3])),
        ((960., 1430., 3980., 4830., -980., -420.), .021, np.zeros(3)),
    ]
    for index in (0, 17, 143, 287):
        e, n, up = received[index]
        expected = np.zeros(3)
        for bounds_enu, chi, remanence_enu in bodies:
            e0, e1, n0, n1, u0, u1 = bounds_enu
            magnetization_edn = chi*field_t/MU0 + remanence_enu*np.array([1., 1., -1.])
            expected += np.asarray(choclo.prism.magnetic_field(
                e, n, -up, e0, e1, n0, n1, -u1, -u0, *magnetization_edn))*1e9
        actual = np.asarray(truth["clean_secondary_components_nT"][index])
        np.testing.assert_allclose(actual, expected, rtol=2e-13, atol=2e-13)


@pytest.mark.parametrize("quantity", generator._QUANTITIES)
def test_null_is_exact_zero_and_four_flight_coverage_fails_without_relaxation(quantity):
    request, truth = generator.acquisition_case("F", quantity)
    assert request["source"]["scope"] == "declared_subset"
    assert request["source"]["original_bytes"] > 0
    assert all(value == 0.0 for value in request["observations"]["values"]["data"])
    assert all(value == 0.0 for value in truth["clean_observable_nT"])
    with pytest.raises(InputError, match="twelve indivisible"):
        plan_geometry(parse_request(canonical_request(request)))


def test_linear_and_exact_scalar_channels_use_distinct_declared_physics():
    _, vector_truth = generator.acquisition_case("A", "secondary_enu_nT")
    _, linear_truth = generator.acquisition_case("A", "linear_tmi_nT")
    _, exact_truth = generator.acquisition_case("A", "exact_total_anomaly_nT")
    inc, dec = np.deg2rad([37., -73.])
    f = 50_000.
    direction = np.array([np.cos(inc)*np.sin(dec), np.cos(inc)*np.cos(dec), -np.sin(inc)])
    vectors = np.asarray(vector_truth["clean_secondary_components_nT"])
    linear = vectors @ direction
    np.testing.assert_allclose(linear_truth["clean_observable_nT"], linear, rtol=1e-14, atol=1e-14)
    with localcontext() as ctx:
        ctx.prec = 80
        exact = []
        for vector in vectors:
            dot = sum((Decimal.from_float(float(a))*Decimal.from_float(float(b))
                       for a, b in zip(vector, direction)), Decimal(0))
            norm2 = sum((Decimal.from_float(float(v))**2 for v in vector), Decimal(0))
            field = Decimal.from_float(f)
            exact.append(float((field*field+2*field*dot+norm2).sqrt()-field))
    np.testing.assert_allclose(exact_truth["clean_observable_nT"], exact, rtol=2e-15, atol=1e-15)
    assert not np.array_equal(linear_truth["clean_observable_nT"], exact_truth["clean_observable_nT"])
