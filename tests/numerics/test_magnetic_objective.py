import numpy as np
import pytest

from magnetic_likelihood import GaussianWhitener
from magnetic_objective import MagneticGaussianObjective


def _case(quantity, noise="full_covariance"):
    kernel = np.array([
        [1200., -300.], [700., 900.], [-150., 500.],
        [-800., 400.], [500., -600.], [250., 1100.],
    ], dtype=np.float64)
    background = np.array([12000., 35000., -18000.], dtype=np.float64)
    rows = np.array([0, 1, 2], dtype=np.int64) if quantity == "secondary_enu" else np.array([0, 1], dtype=np.int64)
    if noise == "full_covariance":
        covariance = np.array([[4., .7, .3], [.7, 9., 1.], [.3, 1., 16.]], dtype=np.float64)[:len(rows), :len(rows)]
        whitener = GaussianWhitener(noise, covariance, rows)
    else:
        sigma = np.array([[2., 3.], [4., 5.], [6., 7.]], dtype=np.float64)
        flat = sigma.ravel() if quantity == "secondary_enu" else sigma[:, 0]
        rows = np.arange(len(flat), dtype=np.int64)
        whitener = GaussianWhitener("diagonal_sd", sigma if quantity == "secondary_enu" else flat.reshape(-1, 1), rows)
    observed = np.array([.3, -.2, .1], dtype=np.float64)[:len(rows)]
    objective = MagneticGaussianObjective(kernel, background, observed, whitener, rows, quantity)
    return objective, np.array([.12, .21], dtype=np.float64)


@pytest.mark.parametrize("quantity", ["secondary_enu", "linear_tmi_nT", "exact_total_anomaly_nT"])
def test_objective_gradient_and_gauss_newton_are_consistent(quantity):
    objective, q = _case(quantity)
    result = objective.evaluate(q)
    direction = np.array([.3, -.7], dtype=np.float64)
    step = 1e-6
    plus = objective.evaluate(q + step * direction)["phi_d"]
    minus = objective.evaluate(q - step * direction)["phi_d"]
    centered = (plus - minus) / (2 * step)
    np.testing.assert_allclose(centered, result["gradient_q"] @ direction,
                               rtol=2e-7, atol=1e-9)
    action = result["gauss_newton_action"](direction)
    assert float(direction @ action) >= -1e-12
    assert result["phi_d"] >= 0.
    np.testing.assert_allclose(
        result["residual_observed_minus_predicted_nT"],
        objective.data.observed_selected_nT - result["predicted_selected_nT"],
        rtol=0., atol=0.)


def test_scalar_objective_subsets_original_rows_before_full_covariance_whitening():
    kernel = np.array([[1., 2.], [3., 4.], [5., 6.], [7., 8.], [9., 10.],
                       [11., 12.], [13., 14.], [15., 16.], [17., 18.]], dtype=np.float64)
    rows = np.array([0, 2], dtype=np.int64)
    covariance = np.array([[4., 1., .5], [1., 9., 2.], [.5, 2., 16.]], dtype=np.float64)
    whitener = GaussianWhitener("full_covariance", covariance, rows)
    objective = MagneticGaussianObjective(kernel, np.array([0., 0., 50000.]),
        np.array([1., -2.]), whitener, rows, "linear_tmi_nT")
    result = objective.evaluate(np.array([.1, .2], dtype=np.float64))
    assert result["predicted_selected_nT"].shape == (2,)
    assert result["gradient_q"].shape == (2,)


def test_selection_must_match_the_frozen_whitener_rows():
    kernel = np.ones((6, 1), dtype=np.float64)
    rows = np.array([0, 1], dtype=np.int64)
    whitener = GaussianWhitener("diagonal_sd", np.ones((1, 2)), rows)
    with pytest.raises(ValueError, match="mismatch"):
        MagneticGaussianObjective(kernel, np.array([0., 0., 50000.]), np.zeros(2),
            whitener, np.array([0, 2], dtype=np.int64), "linear_tmi_nT")


def test_malformed_background_shape_is_rejected_before_finite_scan(monkeypatch):
    kernel = np.ones((6, 1), dtype=np.float64)
    rows = np.array([0, 1], dtype=np.int64)
    whitener = GaussianWhitener("diagonal_sd", np.ones((1, 2), dtype=np.float64), rows)
    oversized = np.zeros(1_000_000, dtype=np.float64)
    original_isfinite = np.isfinite

    def guarded_isfinite(value, *args, **kwargs):
        if value is oversized:
            raise AssertionError("malformed background finite scan occurred before shape check")
        return original_isfinite(value, *args, **kwargs)

    monkeypatch.setattr(np, "isfinite", guarded_isfinite)
    with pytest.raises(ValueError, match="three ENU"):
        MagneticGaussianObjective(kernel, oversized, np.zeros(2, dtype=np.float64),
            whitener, rows, "linear_tmi_nT")
