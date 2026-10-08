"""Deterministic local free-face resolution; never posterior covariance."""

from time import monotonic

import numpy as np
from scipy.sparse.linalg import LinearOperator, cg

from magnetic_survey_json import fail


def resolution(objective, q, *, deadline):
    from magnetic_calibration import descriptor
    a = len(q)
    gradient = objective.evaluate(q, True, False)[1]
    tolerance = 32*np.finfo(float).eps*np.maximum.reduce(
        [np.ones(a), abs(q), abs(objective.lower), abs(objective.upper)])
    locked = ((q <= objective.lower+tolerance)&(gradient > 0.))|((q >= objective.upper-tolerance)&(gradient < 0.))
    free = np.flatnonzero(~locked).astype(np.int64)
    selected = np.unique([k*(a-1)//7 for k in range(8)]).astype(np.int64)
    wj = objective.whiten(objective.operator.evaluate(q)['jacobian_nT_per_q'])
    terms = objective.regularizer.terms()
    full_h = objective.evaluate(q, False, True)[1]

    def action(v):
        if monotonic() > deadline:
            fail('resource', '$/diagnostics', 'Resolution deadline; no partial diagnostic')
        embedded = np.zeros(a)
        embedded[free] = v
        return .5*(full_h@embedded)[free]

    point = np.zeros((a, len(selected)))
    matrix = np.zeros((a, a)) if a <= 64 else None
    spectrum = None
    if len(free):
        if a <= 64:
            gram = np.column_stack([action(v) for v in np.eye(len(free))])
            data = wj[:, free].T@wj
            # Positive regularizer smallness guarantees this local SPD system.
            # No inverse, nugget, rank cutoff or zero-mode replacement.
            local = np.linalg.solve(gram, data)
            matrix[free] = local
            point[:] = matrix[:, selected]
            stacked = [wj[:, free]]
            for term in terms:
                stacked.append(np.sqrt(objective.beta*term['alpha'])*
                               term['weights'][:, None]*term['derivative'][:, free].toarray())
            spectrum = descriptor(np.linalg.svd(np.vstack(stacked), compute_uv=False))
        else:
            h = LinearOperator((len(free), len(free)), matvec=action, dtype=np.float64)
            diagonal = .5*objective.binding_diagonal(q)[free]
            preconditioner = LinearOperator(h.shape, matvec=lambda v: v/diagonal, dtype=np.float64)
            for column, index in enumerate(selected):
                rhs = wj[:, free].T@wj[:, index]
                solution, info = cg(h, rhs, M=preconditioner, rtol=1e-10, atol=0., maxiter=1000)
                error = np.linalg.norm(action(solution)-rhs)
                if info != 0 or not np.isfinite(solution).all() or error > 1e-10*np.linalg.norm(rhs):
                    fail('numerical', '$/diagnostics', 'Actual point-spread solve did not converge')
                point[free, column] = solution
    return dict(free_indices=descriptor(free) if len(free) else None,
        selected_indices=descriptor(selected), diagonal=descriptor(np.diag(matrix).copy()) if matrix is not None else None,
        point_spread=descriptor(point), matrix=descriptor(matrix) if matrix is not None else None,
        singular_values=spectrum)


def line_spectrum(coordinates, residual):
    """Separate display helper: signed ENU residuals on horizontal line distance.

    No interpolation and no fitting/selection use; irregular rows are unavailable.
    Caller supplies ONE contiguous original acquisition line, in original order.
    """
    if (type(coordinates) is not np.ndarray or coordinates.dtype != np.float64 or coordinates.ndim != 2
            or coordinates.shape[1] != 3 or type(residual) is not np.ndarray or residual.dtype != np.float64
            or residual.ndim != 2 or len(residual) != len(coordinates) or len(residual) < 3
            or not np.isfinite(coordinates).all() or not np.isfinite(residual).all()):
        raise ValueError('spectrum: native finite contiguous line arrays required')
    horizontal = np.diff(coordinates[:, :2], axis=0)
    steps = np.linalg.norm(horizontal, axis=1)
    if steps[0] <= 0. or not np.allclose(horizontal, horizontal[0], rtol=1e-12, atol=1e-12):
        return dict(status='unavailable', reason='irregular_horizontal_spacing_or_gap')
    fs = 1./steps[0]
    window = np.hanning(len(residual))
    transformed = np.fft.rfft(window[:, None]*(residual-residual.mean(axis=0)), axis=0)
    power = abs(transformed)**2/(fs*np.sum(window**2))
    power[1:-1 if len(residual)%2 == 0 else None] *= 2.
    return dict(status='available', distance_basis='projected_horizontal_m', frequency_unit='cycles/m',
                power_unit='nT^2*m', frequencies=np.fft.rfftfreq(len(residual), d=steps[0]), power=power)
