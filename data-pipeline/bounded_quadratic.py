"""Deterministic active-set solver for strictly convex box-constrained QPs."""
from __future__ import annotations

import numpy as np


class BoundedQuadraticError(ValueError):
    """The bounded quadratic could not be solved to its declared KKT gate."""


KKT_RELATIVE_TOLERANCE = 1e-9
MAX_ACTIVE_SET_ITERATIONS = 512


def projected_kkt_inf(hessian: np.ndarray, rhs: np.ndarray, value: np.ndarray,
                      lower: np.ndarray, upper: np.ndarray) -> tuple[float, float]:
    """Return absolute and scale-normalized box-KKT residuals."""
    gradient = hessian @ value - rhs
    residual = gradient.copy()
    at_lower = value <= lower
    at_upper = value >= upper
    residual[at_lower] = np.minimum(gradient[at_lower], 0.0)
    residual[at_upper] = np.maximum(gradient[at_upper], 0.0)
    absolute = float(np.max(np.abs(residual), initial=0.0))
    scale = max(1.0, float(np.max(np.abs(rhs), initial=0.0)),
                float(np.max(np.abs(hessian @ value), initial=0.0)))
    return absolute, absolute / scale


def solve_box_quadratic(hessian: np.ndarray, rhs: np.ndarray,
                        lower: np.ndarray, upper: np.ndarray) -> dict[str, object]:
    """Minimize 0.5*x'Hx - rhs'x over a closed box.

    The caller supplies an SPD Hessian. Each active-set direction exactly
    minimizes the quadratic on the current free face. Blocking bounds are
    approached without leaving the feasible box; violated active KKT
    multipliers release constraints. The returned KKT residual is recomputed
    from the final arrays, independently of the stopping branch.
    """
    hessian = np.asarray(hessian, dtype=np.float64)
    rhs = np.asarray(rhs, dtype=np.float64)
    lower = np.asarray(lower, dtype=np.float64)
    upper = np.asarray(upper, dtype=np.float64)
    n = rhs.size
    if (n == 0 or hessian.shape != (n, n) or lower.shape != (n,) or upper.shape != (n,)
            or not all(np.isfinite(a).all() for a in (hessian, rhs, lower, upper))
            or np.any(lower >= upper)
            or not np.allclose(hessian, hessian.T, rtol=1e-13, atol=1e-13)):
        raise BoundedQuadraticError("Invalid bounded quadratic arrays")
    try:
        np.linalg.cholesky(hessian)
    except np.linalg.LinAlgError as error:
        raise BoundedQuadraticError("Quadratic Hessian is not positive definite") from error

    value = np.clip(np.zeros(n, dtype=np.float64), lower, upper)
    # -1 = lower bound, 0 = free, +1 = upper bound.
    active = np.zeros(n, dtype=np.int8)
    active[value == lower] = -1
    active[value == upper] = 1

    for iteration in range(1, MAX_ACTIVE_SET_ITERATIONS + 1):
        free = np.flatnonzero(active == 0)
        gradient = hessian @ value - rhs
        step = np.zeros(n, dtype=np.float64)
        if free.size:
            face = hessian[np.ix_(free, free)]
            try:
                step[free] = np.linalg.solve(face, -gradient[free])
            except np.linalg.LinAlgError as error:
                raise BoundedQuadraticError("Free-face Hessian solve failed") from error
            if not np.isfinite(step).all():
                raise BoundedQuadraticError("Free-face direction is nonfinite")

            alpha = 1.0
            blockers: list[tuple[int, int]] = []
            for index in free:
                direction = step[index]
                if direction > 0.0:
                    candidate = (upper[index] - value[index]) / direction
                    side = 1
                elif direction < 0.0:
                    candidate = (lower[index] - value[index]) / direction
                    side = -1
                else:
                    continue
                if candidate < alpha:
                    alpha = max(0.0, float(candidate))
                    blockers = [(int(index), side)]
                elif candidate == alpha:
                    blockers.append((int(index), side))

            value += alpha * step
            if alpha < 1.0:
                if not blockers:
                    raise BoundedQuadraticError("Blocking bound was not identified")
                for index, side in blockers:
                    value[index] = lower[index] if side < 0 else upper[index]
                    active[index] = side
                continue

        gradient = hessian @ value - rhs
        violations = np.zeros(n, dtype=np.float64)
        lower_active = active == -1
        upper_active = active == 1
        violations[lower_active] = np.maximum(-gradient[lower_active], 0.0)
        violations[upper_active] = np.maximum(gradient[upper_active], 0.0)
        absolute, relative = projected_kkt_inf(hessian, rhs, value, lower, upper)
        if relative <= KKT_RELATIVE_TOLERANCE:
            return {"value": value, "iterations": iteration,
                    "kkt_inf_norm": absolute, "kkt_relative": relative,
                    "kkt_relative_tolerance": KKT_RELATIVE_TOLERANCE}

        scale = max(1.0, float(np.max(np.abs(rhs), initial=0.0)),
                    float(np.max(np.abs(hessian @ value), initial=0.0)))
        if np.max(violations, initial=0.0) > KKT_RELATIVE_TOLERANCE * scale:
            # Deterministic largest-multiplier pivot; argmax uses the lowest
            # index for exact ties.
            release = int(np.argmax(violations))
            active[release] = 0
            continue

        # No active multiplier can repair an inaccurate free-face solve.
        # Returning a plausible clipped vector would hide that failure.
        raise BoundedQuadraticError(
            f"Free-face KKT residual {relative:.3e} exceeds tolerance"
        )

    raise BoundedQuadraticError("Active-set iteration limit reached before KKT gate")
