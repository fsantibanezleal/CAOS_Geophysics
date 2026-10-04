"""Actual quantity kernels/Jacobians; not a completed magnetic inverse fit."""

from decimal import Decimal, localcontext, Rounded
import importlib.util
import math
from pathlib import Path
from time import monotonic

import numpy as np
import pytest

import magnetic_inverse as inverse
from magnetic_survey_support import encode, request


spec = importlib.util.spec_from_file_location(
    "independent_objective", Path(__file__).with_name("test_magnetic_survey_objective.py"))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@pytest.fixture(scope="module")
def physics():
    return control.physical.__wrapped__()


def direct(background, secondary, f=50000.):
    with localcontext() as ctx:
        ctx.prec = 160
        return np.array([float(sum((Decimal.from_float(float(a))+Decimal.from_float(float(b)))**2
                                  for a, b in zip(background, row)).sqrt()-Decimal.from_float(f))
                         for row in secondary])


@pytest.mark.parametrize("quantity", inverse.QUANTITIES)
def test_quantity_specific_physics_and_jacobian(physics, quantity):
    _, g, oracle, direction, _, _, _, _, _ = physics
    op = inverse.MagneticQuantity(g, 50000.*direction, direction, 50000., quantity)
    result = op.evaluate(control.Q)
    independent = oracle @ (.01*control.Q)
    np.testing.assert_allclose(result["secondary_enu_nT"].ravel(), independent, rtol=2e-8, atol=1e-7)
    if quantity == "secondary_enu_nT":
        predicted = independent.reshape(30, 3)
    elif quantity == "linear_tmi_nT":
        predicted = (independent.reshape(30, 3) @ direction)[:, None]
    else:
        predicted = direct(50000.*direction, independent.reshape(30, 3))[:, None]
    np.testing.assert_allclose(result["prediction_nT"], predicted, rtol=2e-8, atol=1e-7)
    # Independent Choclo directional finite differences in physical SI units.
    estimates = []
    for h in (1e-6, 5e-7, 2.5e-7):
        p = (.01*control.Q+h*control.V)
        m = (.01*control.Q-h*control.V)
        if quantity == "exact_total_anomaly_nT":
            difference = (direct(50000.*direction, (oracle @ p).reshape(30, 3))-
                          direct(50000.*direction, (oracle @ m).reshape(30, 3)))/(2*h)
        elif quantity == "linear_tmi_nT":
            difference = ((oracle @ p).reshape(30, 3) @ direction-
                          (oracle @ m).reshape(30, 3) @ direction)/(2*h)
        else:
            difference = (oracle @ p-oracle @ m)/(2*h)
        estimates.append(difference)
    np.testing.assert_allclose(estimates[-1], estimates[-2], rtol=2e-6, atol=1e-6)
    jac = result["jacobian_nT_per_q"]/.01
    np.testing.assert_allclose(jac @ control.V, estimates[-1], rtol=2e-6, atol=1e-6)
    u = np.cos(np.arange(jac.shape[0]))
    np.testing.assert_allclose(u @ (jac @ control.V), control.V @ (jac.T @ u), rtol=1e-12, atol=1e-10)


@pytest.mark.parametrize("background", [np.array([0., 0., 50000.]),
                                        np.array([50000., 0., 0.]),
                                        np.array([0., 50000., 0.])])
def test_cardinal_tiny_scalar_and_zero_direction(background):
    kernel = np.array([[1.], [2.], [-3.]])
    op = inverse.MagneticQuantity(kernel, background, background/50000., 50000., "exact_total_anomaly_nT")
    for q in (np.array([0.]), np.array([1e-20]), np.array([1.])):
        value = op.evaluate(q)
        expected = direct(background, value["secondary_enu_nT"])
        actual = value["prediction_nT"].ravel()
        if q[0] == 0.:
            np.testing.assert_array_equal(actual, expected)
        else:
            assert np.all(expected != 0.)
            assert np.max(np.abs(actual/expected-1.)) <= 2e-8


def test_native_zero_intercept_not_omitted_or_normalized(physics):
    _, g, _, direction, _, _, _, _, _ = physics
    background = 50000.*direction
    op = inverse.MagneticQuantity(g, background, direction, 50000., "exact_total_anomaly_nT")
    value = op.evaluate(np.zeros(7))
    expected = direct(background, np.zeros((30, 3)))
    assert np.all(expected != 0.)
    np.testing.assert_allclose(value["prediction_nT"].ravel()/expected, np.ones(30), rtol=2e-8, atol=0.)
    with localcontext() as ctx:
        ctx.prec = 160
        t0 = float(sum(Decimal.from_float(float(x))**2 for x in background).sqrt())
    np.testing.assert_allclose(value["jacobian_nT_per_q"],
                               np.einsum("c,nca->na", background/t0, (.01*g).reshape(30, 3, 7)),
                               rtol=1e-12, atol=1e-10)


@pytest.mark.parametrize("fault", ["shape", "dtype", "subclass", "count", "quantity", "finite", "field"])
def test_native_closed_kernel_protocol(fault):
    g, background, direction, f, quantity = np.ones((3, 1)), np.array([0., 0., 50000.]), np.array([0., 0., 1.]), 50000., "linear_tmi_nT"
    if fault == "shape": g = np.ones((4, 1))
    if fault == "dtype": g = g.astype("float32")
    if fault == "subclass": g = g.view(type("ForeignArray", (np.ndarray,), {}))
    if fault == "count": g = np.ones((3, 2049))
    if fault == "quantity": quantity = "secondary_amplitude"
    if fault == "finite": g[0, 0] = np.nan
    if fault == "field": f = True
    with pytest.raises((TypeError, ValueError)):
        inverse.MagneticQuantity(g, background, direction, f, quantity)


def test_actual_raw_builder_metadata_only_rights_and_order():
    doc = request()
    with pytest.raises(ValueError):
        inverse.build_operator(encode(doc), (0, 13, 24), deadline=math.inf)
    op = inverse.build_operator(encode(doc), (0, 13, 24), deadline=monotonic()+120.)
    result = op.evaluate(np.zeros(528))
    assert result['prediction_nT'].shape == (3, 3)
    assert result['jacobian_nT_per_q'].shape == (9, 528)
    np.testing.assert_array_equal(result['prediction_nT'], np.zeros((3, 3)))
    doc['source']['rights'] = 'unresolved'
    with pytest.raises(ValueError, match='rights'):
        inverse.build_operator(encode(doc), (0, 13, 24), deadline=monotonic()+120.)


@pytest.mark.parametrize('rows', [[0, 1], (True,), (1, 0), (), (288,)])
def test_builder_rejects_foreign_or_nonoriginal_rows(rows):
    with pytest.raises((ValueError, TypeError)):
        inverse.build_operator(encode(request()), rows, deadline=monotonic()+120.)


@pytest.mark.parametrize("q", [np.array([-1.]), np.array([11.]), np.array([np.nan]),
                               np.array([1.], dtype="float32"), [1.]])
def test_bad_model_and_guard_fail_without_fallback(q):
    op = inverse.MagneticQuantity(np.ones((3, 1)), np.array([0., 0., 50000.]),
                                 np.array([0., 0., 1.]), 50000., "exact_total_anomaly_nT")
    with pytest.raises((ValueError, TypeError)):
        op.evaluate(q)


def test_total_field_guard_and_owned_snapshots():
    background = np.array([0., 0., 50000.])
    g = np.array([[0.], [0.], [-5000000.]])
    op = inverse.MagneticQuantity(g, background, background/50000., 50000., "exact_total_anomaly_nT")
    with pytest.raises(ValueError, match="domain"):
        op.evaluate(np.array([1.]))
    result = op.evaluate(np.array([0.]))
    for value in result.values():
        assert value.flags.owndata and value.flags.c_contiguous and not value.flags.writeable
    before = op.evaluate(np.array([0.]))["prediction_nT"].copy()
    result["prediction_nT"].flags.writeable = True
    result["prediction_nT"][:] = 9.
    np.testing.assert_array_equal(op.evaluate(np.array([0.]))["prediction_nT"], before)
    background[:] = 0.; g[:] = 0.
    np.testing.assert_array_equal(op.evaluate(np.array([0.]))["prediction_nT"], before)


def test_scalar_point_context_isolated_and_zero_one_sided_jacobian(physics):
    _, g, _, direction, _, _, _, _, _ = physics
    op = inverse.MagneticQuantity(g, 50000.*direction, direction, 50000., 'exact_total_anomaly_nT')
    expected = op.evaluate(np.zeros(7))
    with localcontext() as ctx:
        ctx.prec, ctx.Emax = 6, 2
        ctx.traps[Rounded] = True
        actual = op.evaluate(np.zeros(7))
    np.testing.assert_array_equal(actual['prediction_nT'], expected['prediction_nT'])
    # Production zero is a legal boundary. A three-point one-sided SI
    # derivative approaches the total-vector direction, not assumed norm F.
    column = np.eye(7)[2]
    estimates = []
    for h in (1e-6, 5e-7, 2.5e-7):
        y1 = op.evaluate(column*h/.01)['prediction_nT'].ravel()
        y2 = op.evaluate(column*(2*h)/.01)['prediction_nT'].ravel()
        y0 = expected['prediction_nT'].ravel()
        estimates.append((-3*y0+4*y1-y2)/(2*h))
    np.testing.assert_allclose(estimates[-1], estimates[-2], rtol=2e-6, atol=1e-6)
    np.testing.assert_allclose(expected['jacobian_nT_per_q'][:,2]/.01, estimates[-1], rtol=2e-6, atol=1e-6)
