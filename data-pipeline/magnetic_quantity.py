"""Quantity-specific M04 magnetic response composition from an actual kernel.

The caller supplies the native SimPEG component sensitivity matrix. This
module composes measured quantities and their physical q=chi/0.01 Jacobians;
it does not generate a kernel, infer field metadata, or admit an inverse.
"""

import numpy as np


CHI_SCALE_SI = 0.01
MAX_RECEIVERS = 2048
MAX_ACTIVE_CELLS = 2048
MAX_PROJECTED_ENTRIES = 12_582_912
MIN_TOTAL_TO_BACKGROUND = 1e-8


def _owned(value):
    result = np.array(value, dtype=np.float64, copy=True, order="C")
    if not np.isfinite(result).all():
        raise FloatingPointError("magnetic response contains nonfinite values")
    result.flags.writeable = False
    return result


def _metadata(value, name, ndim):
    if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim != ndim:
        raise TypeError(f"{name}: expected native float64 {ndim}-D array")


def _finite(value, name):
    if not np.isfinite(value).all():
        raise ValueError(f"{name}: values must be finite")


def compose_magnetic_observable(component_jacobian_nT_per_si, chi_si,
                                background_enu_nT, quantity):
    """Return a physical anomaly and dH/dq for one declared magnetic quantity.

    Supported quantities are `secondary_enu`, `linear_tmi_nT`, and
    `exact_total_anomaly_nT`. `component_jacobian_nT_per_si` is flattened
    receiver-major with ENU components contiguous, shape `(3*N,A)`.
    """
    _metadata(component_jacobian_nT_per_si, "component_jacobian_nT_per_si", 2)
    _metadata(chi_si, "chi_si", 1)
    _metadata(background_enu_nT, "background_enu_nT", 1)
    if type(quantity) is not str or quantity not in {
        "secondary_enu", "linear_tmi_nT", "exact_total_anomaly_nT"
    }:
        raise ValueError("quantity: unsupported measured magnetic quantity")
    n_parameters = len(chi_si)
    if not 1 <= n_parameters <= MAX_ACTIVE_CELLS:
        raise ValueError("chi_si: active parameter count outside 1..2048")
    if component_jacobian_nT_per_si.shape[1] != n_parameters:
        raise ValueError("component_jacobian_nT_per_si: active-cell count mismatch")
    if component_jacobian_nT_per_si.shape[0] % 3:
        raise ValueError("component_jacobian_nT_per_si: ENU row count must be divisible by 3")
    n_receivers = component_jacobian_nT_per_si.shape[0] // 3
    if not 1 <= n_receivers <= MAX_RECEIVERS:
        raise ValueError("component_jacobian_nT_per_si: receiver count outside 1..2048")
    if 3 * n_receivers * n_parameters > MAX_PROJECTED_ENTRIES:
        raise ValueError("component_jacobian_nT_per_si: projected-entry cap exceeded")
    if background_enu_nT.shape != (3,):
        raise ValueError("background_enu_nT: expected ENU vector")
    _finite(component_jacobian_nT_per_si, "component_jacobian_nT_per_si")
    _finite(chi_si, "chi_si")
    _finite(background_enu_nT, "background_enu_nT")
    if np.any((chi_si < 0.0) | (chi_si > 0.1)):
        raise ValueError("chi_si: outside declared physical susceptibility bounds")
    amplitude = float(np.hypot(np.hypot(background_enu_nT[0], background_enu_nT[1]),
                               background_enu_nT[2]))
    if not np.isfinite(amplitude) or not 1.0 <= amplitude <= 1e6:
        raise ValueError("background_enu_nT: magnitude outside declared field range")

    kernel = component_jacobian_nT_per_si.reshape(n_receivers, 3, n_parameters)
    components = np.einsum("nca,a->nc", kernel, chi_si)
    scale = CHI_SCALE_SI
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        if quantity == "secondary_enu":
            values = components
            jacobian_q = (scale * kernel).reshape(3 * n_receivers, n_parameters)
        elif quantity == "linear_tmi_nT":
            direction = background_enu_nT / amplitude
            values = components @ direction
            jacobian_q = scale * np.einsum("nca,c->na", kernel, direction)
        else:
            total = background_enu_nT[None, :] + components
            total_magnitude = np.hypot(np.hypot(total[:, 0], total[:, 1]), total[:, 2])
            ratio = total_magnitude / amplitude
            if np.any(ratio <= MIN_TOTAL_TO_BACKGROUND):
                raise ValueError("exact_total_anomaly_nT: total-field direction is ill-conditioned")
            numerator = (2.0 * np.einsum("c,nc->n", background_enu_nT, components)
                         + np.einsum("nc,nc->n", components, components))
            values = numerator / (total_magnitude + amplitude)
            direction = total / total_magnitude[:, None]
            jacobian_q = scale * np.einsum("nc,nca->na", direction, kernel)
    return {"quantity": quantity, "values_nT": _owned(values),
            "jacobian_q_nT": _owned(jacobian_q),
            "chi_scale_si": scale, "parameter_unit": "q=chi_si/0.01"}
