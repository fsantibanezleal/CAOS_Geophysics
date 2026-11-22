"""Source-bound magnetic quantity operators for sealed user surveys.

This module constructs the actual SimPEG component Jacobian from a sealed
survey and provides quantity-specific predictions. It does not claim that a
forward operator is an accepted inverse or that total-field nonlinearity has
an accepted optimizer binding.
"""

from __future__ import annotations

import hashlib
from time import monotonic

import numpy as np

from magnetic_forward import ENGINE, FRAME, forward_magnetic_with_kernel
from magnetic_quantity import (
    CHI_SCALE_SI, MAX_ACTIVE_CELLS, MAX_PROJECTED_ENTRIES, MAX_RECEIVERS,
    compose_magnetic_observable,
)


QUANTITIES = ("secondary_enu_nT", "linear_tmi_nT", "exact_total_anomaly_nT")


def _array(value, shape, name):
    if type(value) is not np.ndarray or value.dtype != np.float64 or value.shape != shape:
        raise TypeError(f"{name}: expected native float64 array with exact shape")
    if not np.isfinite(value).all():
        raise ValueError(f"{name}: values must be finite")


def _owned(value):
    result = np.array(value, dtype=np.float64, copy=True, order="C")
    if not np.isfinite(result).all():
        raise ValueError("magnetic operator: nonfinite owned state")
    result.flags.writeable = False
    return result


class MagneticQuantity:
    """Owned receiver-major ENU sensitivity with physical output semantics."""

    def __init__(self, component_jacobian_nT_per_si, background_enu_nT,
                 direction_enu, field_norm_nT, quantity):
        kernel = component_jacobian_nT_per_si
        if type(kernel) is not np.ndarray or kernel.dtype != np.float64 or kernel.ndim != 2:
            raise TypeError("kernel: expected native float64 matrix")
        rows3, parameters = kernel.shape
        if (rows3 < 3 or rows3 % 3 or rows3 // 3 > MAX_RECEIVERS
                or not 1 <= parameters <= MAX_ACTIVE_CELLS
                or rows3 * parameters > MAX_PROJECTED_ENTRIES):
            raise ValueError("kernel: receiver, active-cell, or projected-entry cap")
        if quantity not in QUANTITIES or type(quantity) is not str:
            raise ValueError("quantity: unsupported physical magnetic observable")
        _array(background_enu_nT, (3,), "background")
        _array(direction_enu, (3,), "field direction")
        if type(field_norm_nT) is not float or not np.isfinite(field_norm_nT) or field_norm_nT <= 0.:
            raise ValueError("field norm: finite positive nT amplitude required")
        norm = float(np.linalg.norm(direction_enu))
        if (abs(norm - 1.) > 1e-12
                or abs(float(np.linalg.norm(background_enu_nT)) - field_norm_nT) > 1e-8):
            raise ValueError("field: direction and amplitude must match the engine background")
        if not np.isfinite(kernel).all():
            raise ValueError("kernel: nonfinite physical sensitivity")
        self._component_kernel = _owned(kernel)
        self._jacobian_q = _owned(CHI_SCALE_SI * kernel)
        self._background = _owned(background_enu_nT)
        self._direction = _owned(direction_enu)
        self.field_norm_nT = field_norm_nT
        self.quantity = quantity
        self.rows, self.parameters = rows3 // 3, parameters
        self.components = 3 if quantity == "secondary_enu_nT" else 1
        payload = (self._jacobian_q.astype("<f8", copy=False).tobytes()
                   + self._background.astype("<f8", copy=False).tobytes()
                   + self._direction.astype("<f8", copy=False).tobytes()
                   + np.array([field_norm_nT], dtype="<f8").tobytes()
                   + quantity.encode("ascii"))
        self.operand_sha256 = hashlib.sha256(payload).hexdigest()

    def operand_snapshot(self):
        """Return independent copies for the trusted source-bound solver DTO."""
        return (_owned(self._jacobian_q), _owned(self._background),
                _owned(self._direction), self.field_norm_nT, self.quantity)

    def evaluate(self, q):
        _array(q, (self.parameters,), "q")
        if np.any(q < 0.) or np.any(q > 10.):
            raise ValueError("q: expected normalized susceptibility in [0, 10]")
        public_quantity = "secondary_enu" if self.quantity == "secondary_enu_nT" else self.quantity
        result = compose_magnetic_observable(
            self._component_kernel, CHI_SCALE_SI * q, self._background, public_quantity
        )
        return {
            "prediction_nT": _owned(result["values_nT"].reshape(-1, order="C")),
            "jacobian_nT_per_q": _owned(result["jacobian_q_nT"]),
        }


def mesh_from_metadata(metadata):
    """Return owned closed mesh arrays from already validated survey metadata."""
    geometry = metadata["geometry"]["mesh"]
    return {
        "origin_m": np.asarray(geometry["origin_m"]["data"], dtype=np.float64),
        "hx_m": np.asarray(geometry["widths_x_m"]["data"], dtype=np.float64),
        "hy_m": np.asarray(geometry["widths_y_m"]["data"], dtype=np.float64),
        "hz_m": np.asarray(geometry["widths_z_m"]["data"], dtype=np.float64),
        "active": np.asarray(geometry["active"]["data"], dtype=np.bool_),
    }


def build_operator(raw, rows, *, deadline):
    """Build an actual SimPEG kernel for an ordered subset of usable survey rows.

    Parsing and geometry eligibility happen before the numerical engine is
    invoked. Observation and noise arrays are never decoded by this function.
    """
    if type(deadline) is not float or not np.isfinite(deadline):
        raise TypeError("deadline: expected finite monotonic deadline")
    if monotonic() > deadline:
        raise TimeoutError("magnetic operator: wall_cap")
    if type(rows) is not tuple or not 1 <= len(rows) <= MAX_RECEIVERS:
        raise TypeError("rows: expected bounded tuple of original receiver indices")
    if (any(type(index) is not int or index < 0 for index in rows)
            or any(left >= right for left, right in zip(rows, rows[1:]))):
        raise ValueError("rows: require strictly increasing original indices")

    from magnetic_survey import plan_geometry
    from magnetic_survey_json import parse_request

    handle = parse_request(raw)
    plan = plan_geometry(handle)
    metadata = handle.metadata()
    if not plan["eligibility"]["local_processing"]:
        raise ValueError("rights: local magnetic processing is not eligible")
    if any(node["operation"] != "original" for node in metadata["processing"]["nodes"]):
        raise ValueError("lineage: processed values need a bound correction-parameter retrieval")
    usable = metadata["geometry"]["usable"]["data"]
    if any(index >= len(usable) or usable[index] is not True for index in rows):
        raise ValueError("rows: only original usable receiver rows are eligible")
    if monotonic() > deadline:
        raise TimeoutError("magnetic operator: wall_cap")

    mesh = mesh_from_metadata(metadata)
    receivers = np.asarray(metadata["geometry"]["receivers_m"]["data"], dtype=np.float64)
    receivers = receivers.reshape(-1, 3, order="C")[list(rows)]
    field = metadata["inducing_field"]
    request = {
        "schema": "magnetic-prism-forward-request-1",
        "engine": ENGINE,
        "frame": FRAME,
        "mesh": mesh,
        "receivers_m": receivers,
        "susceptibility_si": np.zeros(int(np.count_nonzero(mesh["active"])), dtype=np.float64),
        "inducing_field": {
            "amplitude_nt": float(field["F_nT"]),
            "inclination_deg": float(field["I_deg"]),
            "declination_deg": float(field["D_deg"]),
        },
    }
    forward = forward_magnetic_with_kernel(request)
    if monotonic() > deadline:
        raise TimeoutError("magnetic operator: wall_cap")
    background = np.asarray(forward["inducing_field"]["background_enu_nt"], dtype=np.float64)
    amplitude = float(field["F_nT"])
    direction = background / amplitude
    return MagneticQuantity(
        forward["component_jacobian_nT_per_si"], background, direction,
        amplitude, metadata["processing"]["quantity"],
    )
