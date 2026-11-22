"""Assemble sealed M04 fit folds without materializing held-out values."""

import numpy as np
from discretize import TensorMesh

from magnetic_forward import ENGINE, FRAME, forward_magnetic_with_kernel
from magnetic_likelihood import GaussianWhitener
from magnetic_objective import MagneticGaussianObjective
from magnetic_regularization import MagneticRegularizer
from magnetic_survey import plan_geometry
from magnetic_survey_json import SurveyHandle, _Lexer, _Schema, _Span


_QUANTITIES = {
    "secondary_enu_nT": ("secondary_enu", 3),
    "linear_tmi_nT": ("linear_tmi_nT", 1),
    "exact_total_anomaly_nT": ("exact_total_anomaly_nT", 1),
}


def _selected_descriptor(lexer, descriptor, selected, *, covariance_dimension=None):
    """Decode only selected scalar values from an already validated descriptor span."""
    span = descriptor["data"]
    indices = tuple(selected)
    if (type(span) is not _Span or not indices
            or any(type(index) is not int or index < 0 or index >= span.count for index in indices)
            or tuple(sorted(set(indices))) != indices):
        raise ValueError("selection: ordered unique in-range scalar indices required")

    if covariance_dimension is None:
        selected_map = {source: output for output, source in enumerate(indices)}
        output = np.empty(len(indices), dtype=np.float64)
    else:
        if type(covariance_dimension) is not int or covariance_dimension < 1:
            raise ValueError("covariance: positive scalar dimension required")
        selected_map = {source: output for output, source in enumerate(indices)}
        output = np.empty((len(indices), len(indices)), dtype=np.float64)
        columns = selected_map

    scanner = _Lexer(lexer.raw.encode("utf-8"))
    scanner.i = span.start
    scanner.punctuation("[")
    for source_index in range(span.count):
        value = scanner.scalar()
        if covariance_dimension is None:
            target = selected_map.get(source_index)
            if target is not None:
                if type(value) not in (int, float):
                    raise ValueError("likelihood: selected value must be numeric")
                output[target] = float(value)
        else:
            row, column = divmod(source_index, covariance_dimension)
            target_row = selected_map.get(row)
            target_column = columns.get(column)
            if target_row is not None and target_column is not None:
                if type(value) not in (int, float):
                    raise ValueError("likelihood: selected covariance value must be numeric")
                output[target_row, target_column] = float(value)
        if source_index + 1 < span.count:
            scanner.punctuation(",")
    scanner.punctuation("]")
    if scanner.i != span.end or not np.isfinite(output).all():
        raise ValueError("likelihood: selected descriptor span or values are invalid")
    return output


def read_selected_likelihood(handle, selected_flat_indices, expected_geometry_seal):
    """Read only authorized scalar observations and their noise principal block.

    The entire bounded request is lexically and semantically revalidated, but
    the numerical observation/covariance arrays remain scalar tokens until the
    geometry plan is recomputed and its expected seal matches. Only selected
    scalar members are copied to NumPy-owned arrays.
    """
    if type(handle) is not SurveyHandle:
        raise TypeError("handle: expected closed parsed survey bytes")
    if type(selected_flat_indices) is not tuple or not selected_flat_indices:
        raise TypeError("selection: nonempty ordered tuple required")
    plan = plan_geometry(handle)
    if plan["identity"]["seal_sha256"] != expected_geometry_seal:
        raise ValueError("geometry_seal: changed before likelihood selection")

    lexer = _Lexer(handle._export_bytes())
    document = lexer.document()
    schema = _Schema(lexer)
    schema.validate(document)
    observations_descriptor = document["observations"]["values"]
    noise_descriptor = document["noise"]["values"]
    components = observations_descriptor["shape"][1]
    scalar_count = observations_descriptor["shape"][0] * components
    selected = selected_flat_indices
    if (any(type(index) is not int or index < 0 or index >= scalar_count for index in selected)
            or tuple(sorted(set(selected))) != selected):
        raise ValueError("selection: original scalar indices must be ordered, unique and in range")
    observations = _selected_descriptor(lexer, observations_descriptor, selected)
    if document["noise"]["kind"] == "diagonal_sd":
        noise_values = _selected_descriptor(lexer, noise_descriptor, selected).reshape(-1, 1)
    else:
        noise_values = _selected_descriptor(
            lexer, noise_descriptor, selected, covariance_dimension=scalar_count
        )
    observations.flags.writeable = False
    noise_values.flags.writeable = False
    return document, observations, noise_values


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

    quantity, components = _QUANTITIES[metadata["processing"]["quantity"]]
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
    # Reuse the engine-validated ENU vector. Re-deriving its convention here
    # had inverted the vertical sign for positive-down inclination.
    background = np.asarray(forward["inducing_field"]["background_enu_nt"], dtype=np.float64)
    if background.shape != (3,) or not np.isfinite(background).all():
        raise ValueError("inducing field: engine returned an invalid ENU background vector")
    background = background.copy()

    source_indices = (fit_rows[:, None] * components + np.arange(components, dtype=np.int64)).reshape(-1)
    document, observed, selected_noise = read_selected_likelihood(
        handle, tuple(int(index) for index in source_indices), plan["identity"]["seal_sha256"]
    )
    local_indices = np.arange(len(source_indices), dtype=np.int64)
    if document["noise"]["kind"] == "diagonal_sd":
        whitener = GaussianWhitener("diagonal_sd", selected_noise, local_indices)
    else:
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
