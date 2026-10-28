import numpy as np
import pytest

from magnetic_likelihood import GaussianWhitener


def test_diagonal_whitening_precision_and_weighted_sensitivity():
    sd = np.array([[2.0, 4.0], [1.0, 3.0]], dtype=np.float64)
    rows = np.array([0, 2, 3], dtype=np.int64)
    whitener = GaussianWhitener("diagonal_sd", sd, rows)
    residual = np.array([2.0, 2.0, -3.0], dtype=np.float64)
    jacobian = np.array([[2.0, 0.0], [0.0, 2.0], [3.0, 3.0]], dtype=np.float64)

    np.testing.assert_array_equal(whitener.whiten(residual), [1.0, 2.0, -1.0])
    np.testing.assert_array_equal(whitener.precision(residual), [.5, 2.0, -1.0 / 3.0])
    assert whitener.squared_norm(residual) == 6.0
    np.testing.assert_allclose(whitener.weighted_column_norms(jacobian), [np.sqrt(2), np.sqrt(5)])
    assert not whitener.whiten(residual).flags.writeable
    assert not whitener.selected_flat_indices.flags.writeable


def test_full_covariance_uses_principal_submatrix_and_full_correlation():
    covariance = np.array([[4.0, 1.0, 0.5], [1.0, 9.0, 2.0], [0.5, 2.0, 16.0]], dtype=np.float64)
    rows = np.array([0, 2], dtype=np.int64)
    whitener = GaussianWhitener("full_covariance", covariance, rows)
    principal = covariance[np.ix_(rows, rows)]
    residual = np.array([2.0, -4.0], dtype=np.float64)
    expected_phi = float(residual @ np.linalg.solve(principal, residual))
    expected_precision = np.linalg.solve(principal, residual)

    assert whitener.squared_norm(residual) == pytest.approx(expected_phi, rel=2e-15)
    np.testing.assert_allclose(whitener.precision(residual), expected_precision, rtol=2e-15, atol=0)
    assert whitener.squared_norm(residual) != pytest.approx(float(np.sum(residual**2 / np.diag(principal))))


@pytest.mark.parametrize("covariance", [
    np.array([[1.0, 0.1], [0.2, 1.0]], dtype=np.float64),
    np.array([[1.0, 2.0], [2.0, 1.0]], dtype=np.float64),
])
def test_covariance_rejects_asymmetry_and_non_positive_definite(covariance):
    with pytest.raises(ValueError):
        GaussianWhitener("full_covariance", covariance, np.array([0, 1], dtype=np.int64))


@pytest.mark.parametrize("rows", [
    np.array([1, 0], dtype=np.int64),
    np.array([0, 0], dtype=np.int64),
    np.array([0, 2], dtype=np.int64),
])
def test_row_selection_must_be_unique_sorted_and_in_range(rows):
    sd = np.ones((1, 2), dtype=np.float64)
    with pytest.raises(ValueError):
        GaussianWhitener("diagonal_sd", sd, rows)


def test_diagonal_noise_rejects_zero_and_nonfinite_values():
    rows = np.array([0, 1], dtype=np.int64)
    for sd in (np.array([[1.0, 0.0]], dtype=np.float64),
               np.array([[1.0, np.nan]], dtype=np.float64)):
        with pytest.raises(ValueError):
            GaussianWhitener("diagonal_sd", sd, rows)


def test_operands_are_shape_checked_and_input_storage_is_not_retained():
    sd = np.array([[2.0, 3.0]], dtype=np.float64)
    rows = np.array([0, 1], dtype=np.int64)
    whitener = GaussianWhitener("diagonal_sd", sd, rows)
    sd[:] = 1.0
    rows[:] = 0
    np.testing.assert_array_equal(whitener.whiten(np.array([2.0, 3.0], dtype=np.float64)), [1.0, 1.0])
    with pytest.raises(ValueError):
        whitener.whiten(np.ones(3, dtype=np.float64))
