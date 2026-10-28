"""Assemble a sealed M04 fit-fold objective; deliberately do not optimize it."""

import json

import numpy as np
from discretize import TensorMesh

from magnetic_forward import ENGINE, FRAME, forward_magnetic_with_kernel
from magnetic_likelihood import GaussianWhitener
from magnetic_objective import MagneticGaussianObjective
from magnetic_regularization import MagneticRegularizer
from magnetic_survey import plan_geometry
from magnetic_survey_json import SurveyHandle, _Lexer, _Schema


_QUANTITIES = {
    "secondary_enu_nT": ("secondary_enu", 3),
    "linear_tmi_nT": ("linear_tmi_nT", 1),
    "exact_total_anomaly_nT": ("exact_total_anomaly_nT", 1),
}


def _likelihood(handle):
    """Revalidate original bounded bytes before materializing only data/noise."""
    lexer = _Lexer(handle._export_bytes())
    document = lexer.document()
    schema = _Schema(lexer)
    schema.validate(document)

    def values(descriptor):
        span = descriptor["data"]
        data = json.loads(lexer.raw[span.start:span.end])
        result = np.asarray(data, dtype=np.float64).reshape(descriptor["shape"], order="C")
        if not np.isfinite(result).all():
            raise ValueError("likelihood payload: nonfinite values")
        result.flags.writeable = False
        return result

    return document, values(document["observations"]["values"]), values(document["noise"]["values"])


def assemble_magnetic_fit_objective(handle, fold_index):
    """Build actual forward, Gaussian data and SimPEG regularization for one fit fold.

    The returned state supports objective/derivative inspection only. No
    optimizer, validation/outer rows, hyperparameter selection, or inverse
    result is produced here.
    """
    if type(handle) is not SurveyHandle:
        raise TypeError("handle: expected closed parsed survey bytes")
    if type(fold_index) is not int or fold_index not in (0, 1, 2):
        raise ValueError("fold_index: expected one of the three sealed development folds")
    plan = plan_geometry(handle)
    document, observations, noise = _likelihood(handle)
    metadata = handle.metadata()
    partition = plan["partition"]
    fit_rows = np.asarray(partition["folds"][fold_index]["fit_rows"]["data"], dtype=np.int64)
    outer_rows = np.asarray(partition["outer_rows"]["data"], dtype=np.int64)
    validation_rows = np.asarray(
        partition["folds"][fold_index]["validation_rows"]["data"], dtype=np.int64
    )
    if (fit_rows.ndim != 1 or not len(fit_rows) or np.any(np.diff(fit_rows) <= 0)
            or np.intersect1d(fit_rows, outer_rows).size
            or np.intersect1d(fit_rows, validation_rows).size):
        raise ValueError("partition: fit rows are empty, unordered, or overlap held-out rows")

    quantity, components = _QUANTITIES[document["processing"]["quantity"]]
    geometry = metadata["geometry"]
    mesh_spec = geometry["mesh"]
    active = np.asarray(mesh_spec["active"]["data"], dtype=np.bool_)
    origin = np.asarray(mesh_spec["origin_m"]["data"], dtype=np.float64)
    widths = tuple(np.asarray(mesh_spec[key]["data"], dtype=np.float64)
                   for key in ("widths_x_m", "widths_y_m", "widths_z_m"))
    mesh = TensorMesh(widths, x0=origin)
    prior = metadata["prior"]
    start_si = np.asarray(prior["start_si"]["data"], dtype=np.float64)
    reference_q = np.asarray(prior["reference_si"]["data"], dtype=np.float64) / 0.01
    lengths = np.asarray(prior["lengths_m"]["data"], dtype=np.float64)
    regularizer = MagneticRegularizer(mesh, active, reference_q, lengths)
    if start_si.shape != (regularizer.parameter_count,):
        raise ValueError("prior: active start model count disagrees with mesh")

    frame = metadata["inducing_field"]
    amplitude = float(frame["F_nT"])
    inclination = float(frame["I_deg"])
    declination = float(frame["D_deg"])
    inc, dec = np.deg2rad(inclination), np.deg2rad(declination)
    background = amplitude * np.array([np.cos(inc)*np.sin(dec),
                                       np.cos(inc)*np.cos(dec), np.sin(inc)], dtype=np.float64)
    original_receivers = np.asarray(
        geometry["receivers_m"]["data"], dtype=np.float64
    ).reshape(-1, 3, order="C")
    receivers = original_receivers[fit_rows]
    forward_request = {
        "schema": "magnetic-prism-forward-request-1", "engine": ENGINE, "frame": FRAME,
        "mesh": {"origin_m": origin, "hx_m": widths[0], "hy_m": widths[1],
                 "hz_m": widths[2], "active": active},
        "receivers_m": receivers, "susceptibility_si": start_si,
        "inducing_field": {"amplitude_nt": amplitude, "inclination_deg": inclination,
                            "declination_deg": declination},
    }
    forward = forward_magnetic_with_kernel(forward_request)

    source_indices = (fit_rows[:, None] * components + np.arange(components, dtype=np.int64)).reshape(-1)
    observed = observations.reshape(-1, order="C")[source_indices].astype(np.float64, copy=True)
    local_indices = np.arange(len(source_indices), dtype=np.int64)
    if document["noise"]["kind"] == "diagonal_sd":
        selected_noise = noise.reshape(-1, order="C")[source_indices].reshape(-1, 1).copy()
        whitener = GaussianWhitener("diagonal_sd", selected_noise, local_indices)
    else:
        selected_noise = noise[np.ix_(source_indices, source_indices)].copy(order="C")
        whitener = GaussianWhitener("full_covariance", selected_noise, local_indices)

    objective = MagneticGaussianObjective(
        forward["component_jacobian_nT_per_si"], background, observed, whitener,
        local_indices, quantity,
    )
    start_q = np.asarray(start_si / 0.01, dtype=np.float64)
    initial_data = objective.evaluate(start_q)
    initial_regularization = regularizer.evaluate(start_q)
    return {
        "objective": objective, "regularizer": regularizer,
        "start_q": start_q, "initial_data": initial_data,
        "initial_regularization": initial_regularization,
        "fold_index": fold_index, "fit_rows": fit_rows.copy(),
        "source_flat_indices": source_indices,
        "quantity": quantity, "geometry_seal_sha256": plan["identity"]["seal_sha256"],
        "claim": "fit-fold objective assembly only; no inversion performed",
    }
