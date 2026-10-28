"""Frozen magnetic observation whitening primitives.

This module implements only the declared Gaussian likelihood algebra. It does
not parse user documents, choose a partition, construct a SimPEG kernel, or
admit an inverse. Rows are receiver-major/component-minor indices in the
original observation vector. Full covariance is subset by its principal
submatrix and factorized without forming an inverse.
"""

import numpy as np
from scipy.linalg import solve_triangular


MAX_COVARIANCE_ROWS = 512
MAX_COVARIANCE_CONDITION = 1e8


def _owned(value):
    result = np.array(value, dtype=np.float64, copy=True, order="C")
    result.flags.writeable = False
    return result


def _vector(value, name):
    if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim != 1:
        raise TypeError(f"{name}: expected native float64 vector")
    if not np.isfinite(value).all():
        raise ValueError(f"{name}: values must be finite")


def _matrix(value, name):
    if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim != 2:
        raise TypeError(f"{name}: expected native float64 matrix")
    if not np.isfinite(value).all():
        raise ValueError(f"{name}: values must be finite")


def _indices(value, total):
    if type(value) is not np.ndarray or value.dtype != np.int64 or value.ndim != 1:
        raise TypeError("selected_flat_indices: expected native int64 vector")
    if not 1 <= len(value) <= total:
        raise ValueError("selected_flat_indices: empty or oversized selection")
    if np.any(value < 0) or np.any(value >= total) or np.any(np.diff(value) <= 0):
        raise ValueError("selected_flat_indices: require unique increasing in-range rows")
    return value.copy()


class GaussianWhitener:
    """Apply W, W.T W, and weighted norms for one frozen row subset."""

    def __init__(self, kind, source, selected):
        if type(kind) is not str or kind not in {"diagonal_sd", "full_covariance"}:
            raise ValueError("kind: expected diagonal_sd or full_covariance")
        if kind == "diagonal_sd":
            _matrix(source, "standard_deviation_nT")
            if not source.size or np.any(source <= 0):
                raise ValueError("standard_deviation_nT: all values must be positive")
            indices = _indices(selected, source.size)
            sigma = source.ravel(order="C")[indices].copy()
            self._sigma = sigma
            self._factor = None
            self.dimension = len(indices)
        else:
            _matrix(source, "covariance_nT2")
            if source.shape[0] != source.shape[1] or not 1 <= source.shape[0] <= MAX_COVARIANCE_ROWS:
                raise ValueError("covariance_nT2: expected square matrix with dimension 1..512")
            indices = _indices(selected, source.shape[0])
            # The covariance contract requires exact symmetry; do not repair it.
            if not np.array_equal(source, source.T):
                raise ValueError("covariance_nT2: exact symmetry required")
            principal = source[np.ix_(indices, indices)].copy(order="C")
            try:
                factor = np.linalg.cholesky(principal)
                condition = float(np.linalg.cond(principal, p=2))
            except np.linalg.LinAlgError as exc:
                raise ValueError("covariance_nT2: principal matrix must be positive definite") from exc
            if not np.isfinite(condition) or condition > MAX_COVARIANCE_CONDITION:
                raise ValueError("covariance_nT2: principal condition number exceeds 1e8")
            factor.flags.writeable = False
            self._factor = factor
            self._sigma = None
            self.dimension = len(indices)
        indices.flags.writeable = False
        self.selected_flat_indices = indices

    def _operand(self, value, name):
        if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim not in (1, 2):
            raise TypeError(f"{name}: expected native float64 vector or matrix")
        if value.shape[0] != self.dimension or not np.isfinite(value).all():
            raise ValueError(f"{name}: wrong row count or nonfinite values")

    def whiten(self, value):
        """Return L^-1 value (or value/sigma) in independent owned storage."""
        self._operand(value, "value")
        if self._sigma is not None:
            result = value / (self._sigma if value.ndim == 1 else self._sigma[:, None])
        else:
            result = solve_triangular(self._factor, value, lower=True, check_finite=False)
        if not np.isfinite(result).all():
            raise FloatingPointError("whitening produced nonfinite values")
        return _owned(result)

    def precision(self, value):
        """Return W.T W value without forming an inverse or a dense W."""
        whitened = self.whiten(value)
        if self._sigma is not None:
            scale = self._sigma if value.ndim == 1 else self._sigma[:, None]
            result = whitened / scale
        else:
            result = solve_triangular(self._factor.T, whitened, lower=False, check_finite=False)
        if not np.isfinite(result).all():
            raise FloatingPointError("precision application produced nonfinite values")
        return _owned(result)

    def squared_norm(self, value):
        """Return the Gaussian quadratic norm for a vector or column matrix."""
        whitened = self.whiten(value)
        result = float(np.sum(whitened * whitened, dtype=np.float64))
        if not np.isfinite(result):
            raise FloatingPointError("weighted norm is nonfinite")
        return result

    def weighted_column_norms(self, sensitivity):
        """Return ||W J[:,j]||, retaining every covariance correlation."""
        self._operand(sensitivity, "sensitivity")
        if sensitivity.ndim != 2 or sensitivity.shape[1] < 1:
            raise ValueError("sensitivity: expected at least one parameter column")
        weighted = self.whiten(sensitivity)
        result = np.linalg.norm(weighted, axis=0)
        if not np.isfinite(result).all():
            raise FloatingPointError("weighted sensitivity norms are nonfinite")
        return _owned(result)
