"""Executable Gaussian objective for the declared M04 magnetic quantities.

This composes the verified physical quantity Jacobian with the frozen
Gaussian data term. It is an objective, not an optimizer or an inverse runner.
The parameter vector is q=chi_si/0.01 and predictions remain in nT.
"""

import numpy as np

from magnetic_likelihood import GaussianDataTerm, GaussianWhitener
from magnetic_quantity import (
    CHI_SCALE_SI, MAX_ACTIVE_CELLS, MAX_PROJECTED_ENTRIES, MAX_RECEIVERS,
    compose_magnetic_observable,
)


class MagneticGaussianObjective:
    """Evaluate phi_d, its exact gradient and positive GN action for M04."""

    def __init__(self, component_jacobian_nT_per_si, background_enu_nT,
                 observed_selected_nT, whitener, selected_flat_indices, quantity):
        if type(whitener) is not GaussianWhitener:
            raise TypeError("whitener: expected a frozen GaussianWhitener")
        indices = np.asarray(selected_flat_indices)
        if type(selected_flat_indices) is not np.ndarray or indices.dtype != np.int64 or indices.ndim != 1:
            raise TypeError("selected_flat_indices: expected native int64 vector")
        if not np.array_equal(indices, whitener.selected_flat_indices):
            raise ValueError("selected_flat_indices: mismatch with frozen whitener rows")
        self._matrix_metadata(component_jacobian_nT_per_si, "kernel")
        rows, columns = component_jacobian_nT_per_si.shape
        if (rows % 3 or not 3 <= rows <= 3 * MAX_RECEIVERS
                or not 1 <= columns <= MAX_ACTIVE_CELLS
                or rows * columns > MAX_PROJECTED_ENTRIES):
            raise ValueError("kernel: receiver, active-cell or projected-entry cap exceeded")
        self._kernel = self._owned_matrix(component_jacobian_nT_per_si, "kernel")
        self._background = self._owned_vector(background_enu_nT, "background")
        if self._background.shape != (3,):
            raise ValueError("background: expected three ENU components")
        total = self._kernel.shape[0] if quantity == "secondary_enu" else self._kernel.shape[0] // 3
        if np.any(indices < 0) or np.any(indices >= total) or np.any(np.diff(indices) <= 0):
            raise ValueError("selected_flat_indices: require increasing in-range original rows")
        if whitener.dimension != len(indices):
            raise ValueError("whitener: selected row count mismatch")
        self._indices = indices.copy()
        self._indices.flags.writeable = False
        self.quantity = quantity
        if type(quantity) is not str or quantity not in {
            "secondary_enu", "linear_tmi_nT", "exact_total_anomaly_nT"
        }:
            raise ValueError("quantity: unsupported measured magnetic quantity")
        if (type(observed_selected_nT) is not np.ndarray or observed_selected_nT.dtype != np.float64
                or observed_selected_nT.ndim != 1 or observed_selected_nT.size != len(indices)):
            raise TypeError("observations: expected selected native float64 vector")
        self.data = GaussianDataTerm(self._owned_vector(observed_selected_nT, "observations"), whitener)
        if self._kernel.shape[1] < 1:
            raise ValueError("kernel: at least one active susceptibility column required")

    @staticmethod
    def _owned_vector(value, name):
        if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim != 1:
            raise TypeError(f"{name}: expected native float64 vector")
        if not np.isfinite(value).all():
            raise ValueError(f"{name}: values must be finite")
        result = value.copy()
        result.flags.writeable = False
        return result

    @staticmethod
    def _owned_matrix(value, name):
        if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim != 2:
            raise TypeError(f"{name}: expected native float64 matrix")
        if not np.isfinite(value).all():
            raise ValueError(f"{name}: values must be finite")
        result = value.copy(order="C")
        result.flags.writeable = False
        return result

    @staticmethod
    def _matrix_metadata(value, name):
        if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim != 2:
            raise TypeError(f"{name}: expected native float64 matrix")

    @property
    def parameter_count(self):
        return self._kernel.shape[1]

    def evaluate(self, q):
        """Return objective derivatives at a feasible normalized model q."""
        if type(q) is not np.ndarray or q.dtype != np.float64 or q.shape != (self.parameter_count,):
            raise TypeError("q: expected native float64 normalized-susceptibility vector")
        if not np.isfinite(q).all() or np.any(q < 0.) or np.any(q > 10.):
            raise ValueError("q: finite model required within 0..10 (chi SI 0..0.1)")
        response = compose_magnetic_observable(
            self._kernel, CHI_SCALE_SI * q, self._background, self.quantity
        )
        selected = response["values_nT"].ravel(order="C")[self._indices]
        jacobian = response["jacobian_q_nT"]
        if jacobian.shape[0] != len(response["values_nT"].ravel(order="C")):
            raise ValueError("quantity Jacobian: row order/shape mismatch")
        selected_jacobian = jacobian[self._indices]
        result = self.data.evaluate(selected, selected_jacobian)
        return {"phi_d": result.phi_d, "gradient_q": result.gradient_q,
                "gauss_newton_action": result.gauss_newton_action,
                "hessian_diagonal_q": result.hessian_diagonal_q,
                "residual_observed_minus_predicted_nT": self.data.observed_selected_nT - selected,
                "predicted_selected_nT": selected.copy(),
                "quantity": self.quantity, "parameter_unit": "q=chi_si/0.01"}
