"""Noise-aware integral inversion with a physical, sparse spatial precision.

The linear solve uses Q^-1 G^T and a data-space eigensystem. No target-model
values enter the prior, discrepancy selection, or IRLS weights.
"""
from functools import lru_cache
import hashlib
import numpy as np
from scipy import sparse
from scipy.linalg import eigh
from scipy.optimize import brentq
from scipy.sparse.linalg import splu

DEPTH_POWER = .375  # frozen by independent seed-67081 calibration, not display cases


def differences(shape, spacing):
    """Forward physical derivatives, flattened [up,north,east] / x-fast."""
    index = np.arange(np.prod(shape)).reshape(shape)
    result = []
    for axis, step in enumerate(spacing[::-1]):
        left = [slice(None)] * 3
        right = left.copy()
        left[axis] = slice(None, -1)
        right[axis] = slice(1, None)
        a, b = index[tuple(left)].ravel(), index[tuple(right)].ravel()
        row = np.repeat(np.arange(len(a)), 2)
        matrix = sparse.coo_matrix((np.tile([-1 / step, 1 / step], len(a)),
                                   (row, np.column_stack([a, b]).ravel())),
                                  shape=(len(a), index.size)).tocsr()
        result.append((matrix, a, b))
    return result


@lru_cache(maxsize=8)
def geometry(shape, spacing):
    # Cell depths are positive down from the top face. This is a weak
    # depth correction, not the inverse of each sensitivity-column norm.
    depth = (np.arange(shape[0], 0, -1) - .5) * spacing[2]
    weight = ((depth + spacing[2]) / spacing[2]) ** -DEPTH_POWER
    weight = np.broadcast_to(weight[:, None, None], shape).ravel().copy()
    weight /= np.sqrt(np.mean(weight ** 2))
    return weight, differences(shape, spacing)


def precision(shape, spacing, model=None):
    weight, deriv = geometry(tuple(shape), tuple(spacing))
    cell = np.ones(len(weight))
    if model is not None:
        # Smoothed L1 smallness, with a fixed spatial L2 term. The epsilon is
        # based on this estimate only; it never uses the synthetic reference.
        epsilon = max(float(np.quantile(abs(model), .95)) * .15, 1e-12)
        cell = 1 / np.sqrt(model ** 2 + epsilon ** 2)
        cell /= np.median(cell)
    Q = sparse.diags(weight ** 2 * cell)
    for (D, a, b), length in zip(deriv, (140., 240., 240.)):
        face = .5 * (weight[a] ** 2 + weight[b] ** 2)
        Q = Q + length ** 2 * (D.T @ sparse.diags(face) @ D)
    return Q.tocsc()


_systems = {}


def system(G, sigma, shape, spacing, model=None):
    sigma = np.broadcast_to(np.asarray(sigma, dtype=float), (G.shape[0],))
    if np.any(sigma <= 0) or not np.isfinite(sigma).all():
        raise ValueError('Every data uncertainty must be finite and positive')
    n = int(np.prod(shape))
    if G.shape[1] % n:
        raise ValueError('Operator columns must match the declared spatial grid')
    key = hashlib.sha256(G.tobytes() + sigma.tobytes() + str((shape, spacing)).encode()).hexdigest()
    if model is None and key in _systems:
        return _systems[key]
    A = G / sigma[:, None]
    factor = splu(precision(shape, spacing, model))
    B = np.concatenate([factor.solve(A[:, i:i+n].T) for i in range(0, G.shape[1], n)])
    K = A @ B
    eigenvalues, U = eigh((K + K.T) * .5, check_finite=False)
    result = A, B, np.maximum(eigenvalues, 0), U
    if model is None:
        if len(_systems) >= 4:
            _systems.pop(next(iter(_systems)))
        _systems[key] = result
    return result


def solve(G, d, sigma, shape, spacing, strength=1., sparse_model=False):
    G, d = np.asarray(G, float), np.asarray(d, float)
    sigma = np.broadcast_to(np.asarray(sigma, float), d.shape)
    if np.any(sigma <= 0) or not np.isfinite(sigma).all():
        raise ValueError('Every data uncertainty must be finite and positive')
    if not np.isfinite(G).all() or not np.isfinite(d).all():
        raise ValueError('Non-finite inverse input')
    b = d / sigma
    model = None
    history, frames, objectives, betas = [], [], [], []
    for iteration in range(4 if sparse_model else 1):
        A, B, values, U = system(G, sigma, shape, spacing, model)
        rhs = U.T @ b
        def discrepancy(log_beta):
            beta = np.exp(log_beta)
            return np.mean((rhs * beta / (values + beta)) ** 2) - 1.
        top = max(float(values[-1]), 1e-30)
        low, high = np.log(top) - 28, np.log(top) + 20
        if discrepancy(high) <= 0:
            beta = np.exp(high)
        elif discrepancy(low) >= 0:
            beta = np.exp(low)
        else:
            beta = np.exp(brentq(discrepancy, low, high))
        beta *= strength
        m = B @ (U @ (rhs / (values + beta)))
        residual = A @ m - b
        history.append(float(np.mean(residual ** 2)))
        frames.append(m.tolist())
        # Normal equation beta Q m = A^T(b-Am) avoids another sparse product.
        objectives.append(float(np.sum(residual ** 2) + m @ (A.T @ (b - A @ m))))
        betas.append(float(beta))
        model = m if sparse_model else None
    return m, dict(history=history, frames=frames, objective_history=objectives,
                   solver=dict(noise_weighting='1/sigma', beta=betas[-1], beta_history=betas,
                               selection='Morozov mean squared whitened residual = 1 before strength multiplier',
                               strength=strength, spatial_lengths_m=[240., 240., 140.],
                               depth_weight_power=DEPTH_POWER, sparse_iterations=4 if sparse_model else 0))


def conditional_ensemble(G, d, sigma, shape, spacing, beta, seed, members=32):
    """Parametric noise bootstrap at FIXED prior, beta, mesh and survey.

    This quantifies estimator repeatability, not geological posterior spread.
    """
    sigma = np.broadcast_to(np.asarray(sigma, float), np.shape(d))
    A, B, values, U = system(np.asarray(G, float), sigma, shape, spacing)
    rng = np.random.default_rng(seed)
    data = (np.asarray(d)[:, None] + sigma[:, None] * rng.normal(size=(len(d), members))) / sigma[:, None]
    estimates = B @ (U @ ((U.T @ data) / (values[:, None] + beta)))
    lo, hi = np.quantile(estimates, [.025, .975], axis=1)
    return dict(kind='conditional-parametric-bootstrap',
                conditioning='Fixed mesh, spatial prior, selected beta and acquisition; Gaussian observation perturbations. Not a posterior interval.',
                members=members, seed=seed, quantiles=[.025, .975], lower=lo.tolist(), upper=hi.tolist(),
                mean=estimates.mean(axis=1).tolist(), std=estimates.std(axis=1, ddof=1).tolist())
