"""Independent bounded least-squares oracles for the first-arrival optimizer."""
import numpy as np
import pytest
from scipy.optimize import lsq_linear

from bounded_quadratic import (
    BoundedQuadraticError,
    KKT_RELATIVE_TOLERANCE,
    projected_kkt_inf,
    solve_box_quadratic,
)


def _lsq_oracle(hessian, rhs, lower, upper):
    factor = np.linalg.cholesky(hessian).T
    target = np.linalg.solve(factor.T, rhs)
    return lsq_linear(factor, target, bounds=(lower, upper), method="trf",
                      tol=1e-13, lsq_solver="exact", max_iter=2000)


@pytest.mark.parametrize("seed", range(8))
def test_active_set_matches_independent_bounded_lsq(seed):
    rng = np.random.default_rng(seed + 407)
    design = rng.normal(size=(32, 12))
    hessian = design.T @ design + 0.25 * np.eye(12)
    truth = rng.uniform(-0.6, 0.6, size=12)
    rhs = hessian @ truth + rng.normal(scale=0.3, size=12)
    lower, upper = np.full(12, -0.2), np.full(12, 0.25)

    actual = solve_box_quadratic(hessian, rhs, lower, upper)
    expected = _lsq_oracle(hessian, rhs, lower, upper)

    assert expected.success
    assert actual["kkt_relative"] <= KKT_RELATIVE_TOLERANCE
    np.testing.assert_allclose(actual["value"], expected.x, rtol=2e-7, atol=2e-8)
    absolute, relative = projected_kkt_inf(hessian, rhs, actual["value"], lower, upper)
    assert absolute == pytest.approx(actual["kkt_inf_norm"], rel=1e-12, abs=1e-12)
    assert relative == pytest.approx(actual["kkt_relative"], rel=1e-12, abs=1e-12)


def test_initial_interior_solution_and_active_lower_upper_bounds():
    hessian = np.asarray([[4.0, 1.0, 0.0], [1.0, 3.0, 0.5], [0.0, 0.5, 2.0]])
    rhs = hessian @ np.asarray([1.0, -1.0, 2.0])
    lower = np.asarray([-0.5, -0.25, -0.5])
    upper = np.asarray([0.5, 0.25, 0.75])

    result = solve_box_quadratic(hessian, rhs, lower, upper)
    np.testing.assert_allclose(result["value"], [0.5, -0.25, 0.75], atol=1e-10)
    assert result["kkt_relative"] <= KKT_RELATIVE_TOLERANCE
    assert result["iterations"] > 1


@pytest.mark.parametrize("mutate", [
    lambda h, c, lo, hi: (h + np.asarray([[0.0, 0.1, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]), c, lo, hi),
    lambda h, c, lo, hi: (h, c, hi, lo),
    lambda h, c, lo, hi: (h, c, lo[:-1], hi),
    lambda h, c, lo, hi: (h, c, lo, hi * np.nan),
])
def test_rejects_invalid_quadratic_inputs(mutate):
    h = np.eye(3)
    values = mutate(h, np.ones(3), -np.ones(3), np.ones(3))
    with pytest.raises(BoundedQuadraticError):
        solve_box_quadratic(*values)
