from decimal import Decimal, ROUND_HALF_EVEN, localcontext

import numpy as np
import pytest

import magnetic_quantity as mq
from magnetic_quantity import CHI_SCALE_SI, compose_magnetic_observable


@pytest.fixture
def physical_case():
    kernel = np.array([
        [1200.0, -300.0], [700.0, 900.0], [-150.0, 500.0],
        [-800.0, 400.0], [500.0, -600.0], [250.0, 1100.0],
    ], dtype=np.float64)
    chi = np.array([0.0012, 0.0021], dtype=np.float64)
    background = np.array([12000.0, 35000.0, -18000.0], dtype=np.float64)
    return kernel, chi, background


def test_secondary_enu_and_linear_tmi_use_the_declared_kernel(physical_case):
    kernel, chi, background = physical_case
    components = (kernel @ chi).reshape(2, 3)
    direction = background / np.hypot(np.hypot(background[0], background[1]), background[2])

    vector = compose_magnetic_observable(kernel, chi, background, "secondary_enu")
    np.testing.assert_allclose(vector["values_nT"], components, rtol=8e-16, atol=1e-16)
    np.testing.assert_allclose(vector["jacobian_q_nT"], CHI_SCALE_SI * kernel, rtol=0, atol=0)

    scalar = compose_magnetic_observable(kernel, chi, background, "linear_tmi_nT")
    np.testing.assert_allclose(scalar["values_nT"], components @ direction, rtol=2e-16, atol=1e-15)
    expected_j = CHI_SCALE_SI * np.einsum("nca,c->na", kernel.reshape(2, 3, 2), direction)
    np.testing.assert_allclose(scalar["jacobian_q_nT"], expected_j, rtol=2e-16, atol=1e-15)
    assert scalar["parameter_unit"] == "q=chi_si/0.01"
    assert not scalar["values_nT"].flags.writeable


def test_exact_total_anomaly_matches_direct_norm_and_directional_derivative(physical_case):
    kernel, chi, background = physical_case
    result = compose_magnetic_observable(kernel, chi, background, "exact_total_anomaly_nT")
    components = (kernel @ chi).reshape(2, 3)
    expected = np.linalg.norm(background + components, axis=1) - np.linalg.norm(background)
    np.testing.assert_allclose(result["values_nT"], expected, rtol=2e-12, atol=2e-12)

    direction_q = np.array([0.3, -0.7], dtype=np.float64)
    step = 1e-5
    shifted_chi = chi + CHI_SCALE_SI * step * direction_q
    shifted = compose_magnetic_observable(kernel, shifted_chi, background,
                                          "exact_total_anomaly_nT")["values_nT"]
    finite_difference = (shifted - result["values_nT"]) / step
    predicted = result["jacobian_q_nT"] @ direction_q
    np.testing.assert_allclose(finite_difference, predicted, rtol=2e-7, atol=1e-8)


def test_null_start_exact_magnitude_jacobian_is_inducing_field_projection(physical_case):
    kernel, _, background = physical_case
    chi = np.zeros(2, dtype=np.float64)
    result = compose_magnetic_observable(kernel, chi, background, "exact_total_anomaly_nT")
    direction = background / np.hypot(np.hypot(background[0], background[1]), background[2])
    np.testing.assert_array_equal(result["values_nT"], np.zeros(2, dtype=np.float64))
    expected = CHI_SCALE_SI * np.einsum("nca,c->na", kernel.reshape(2, 3, 2), direction)
    np.testing.assert_allclose(result["jacobian_q_nT"], expected, rtol=2e-16, atol=1e-15)


def test_exact_total_field_ill_conditioning_is_rejected():
    background = np.array([50000.0, 0.0, 0.0], dtype=np.float64)
    chi = np.array([0.001], dtype=np.float64)
    kernel = np.array([[-background[0] / chi[0]], [0.0], [0.0]], dtype=np.float64)
    with pytest.raises(ValueError, match="ill-conditioned"):
        compose_magnetic_observable(kernel, chi, background, "exact_total_anomaly_nT")


@pytest.mark.parametrize("secondary", [1e-9, -1e-9, 1e-12, -1e-12, 0.0])
def test_exact_magnitude_tiny_longitudinal_anomaly_matches_decimal80(secondary):
    field = 50000.0
    chi = np.array([0.001], dtype=np.float64)
    kernel = np.zeros((3, 1), dtype=np.float64)
    kernel[1, 0] = secondary / chi[0]
    background = np.array([0.0, field, 0.0], dtype=np.float64)
    result = compose_magnetic_observable(kernel, chi, background, "exact_total_anomaly_nT")
    actual_secondary = float(kernel[1, 0] * chi[0])
    with localcontext() as context:
        context.prec = 80
        context.rounding = ROUND_HALF_EVEN
        total = (Decimal.from_float(field) + Decimal.from_float(actual_secondary)) ** 2
        total = total.sqrt()
        expected = total - Decimal.from_float(field)
        observed = Decimal.from_float(float(result["values_nT"][0]))
        if expected == 0:
            assert observed == 0
        else:
            assert observed != 0 and (observed > 0) == (expected > 0)
            assert abs(observed - expected) <= Decimal("2e-8") * abs(expected)


@pytest.mark.parametrize("quantity", ["secondary", "TMI", "magnitude", "exact_total_anomaly"])
def test_unknown_or_noncanonical_quantity_names_fail(physical_case, quantity):
    kernel, chi, background = physical_case
    with pytest.raises(ValueError, match="unsupported"):
        compose_magnetic_observable(kernel, chi, background, quantity)


def test_metadata_caps_precede_finite_value_scan(monkeypatch):
    oversized = np.zeros((3 * 2049, 1), dtype=np.float64)
    chi = np.ones(1, dtype=np.float64)
    background = np.array([1000.0, 0.0, 0.0], dtype=np.float64)
    monkeypatch.setattr(mq, "_finite", lambda *_: (_ for _ in ()).throw(
        AssertionError("finite scan occurred before metadata cap")))
    with pytest.raises(ValueError, match="receiver count"):
        compose_magnetic_observable(oversized, chi, background, "linear_tmi_nT")
