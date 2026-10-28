"""Development-fold scoring for a caller-frozen M04 model; never a fit callback."""

import hashlib
import json
import re

import numpy as np

from magnetic_forward import ENGINE, FRAME, forward_magnetic_with_kernel
from magnetic_likelihood import GaussianDataTerm, GaussianWhitener
from magnetic_quantity import CHI_SCALE_SI, compose_magnetic_observable
from magnetic_survey import plan_geometry
from magnetic_survey_json import SurveyHandle, _Lexer, _Schema


_QUANTITIES = {
    "secondary_enu_nT": ("secondary_enu", 3),
    "linear_tmi_nT": ("linear_tmi_nT", 1),
    "exact_total_anomaly_nT": ("exact_total_anomaly_nT", 1),
}
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def model_q_sha256(model_q):
    """Hash normalized q values in canonical little-endian binary64 order."""
    if type(model_q) is not np.ndarray or model_q.dtype != np.float64 or model_q.ndim != 1:
        raise TypeError("model_q: expected native float64 normalized susceptibility vector")
    if not 1 <= model_q.size <= 2048 or not np.isfinite(model_q).all():
        raise ValueError("model_q: finite vector within the active-cell cap required")
    values = np.asarray(model_q, dtype="<f8", order="C")
    return hashlib.sha256(values.tobytes(order="C")).hexdigest()


def _likelihood(handle):
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
        return result

    return document, values(document["observations"]["values"]), values(document["noise"]["values"])


def score_magnetic_validation_fold(handle, fold_index, model_q, expected_model_sha256):
    """Score one frozen candidate on one development validation fold.

    Returns aggregate diagnostics only. There is no optimizer callback and no
    candidate selection; this score cannot be used as a final outer evaluation.
    """
    if type(handle) is not SurveyHandle:
        raise TypeError("handle: expected closed parsed survey bytes")
    if type(fold_index) is not int or fold_index not in (0, 1, 2):
        raise ValueError("fold_index: expected one of the three sealed development folds")
    if type(expected_model_sha256) is not str or not _HASH.fullmatch(expected_model_sha256):
        raise ValueError("expected_model_sha256: lowercase SHA-256 required")
    if (type(model_q) is not np.ndarray or model_q.dtype != np.float64
            or model_q.ndim != 1 or not 1 <= model_q.size <= 2048):
        raise TypeError("model_q: expected bounded native float64 vector")
    model_snapshot = model_q.copy()
    model_snapshot.flags.writeable = False
    actual_model_sha256 = model_q_sha256(model_snapshot)
    if actual_model_sha256 != expected_model_sha256:
        raise ValueError("model hash: candidate changed after freeze")

    plan = plan_geometry(handle)
    document, observations, noise = _likelihood(handle)
    metadata = handle.metadata()
    active = np.asarray(metadata["geometry"]["mesh"]["active"]["data"], dtype=np.bool_)
    if model_snapshot.shape != (int(np.count_nonzero(active)),):
        raise ValueError("model_q: active-cell count disagrees with sealed geometry")
    if np.any((model_snapshot < 0.) | (model_snapshot > 10.)):
        raise ValueError("model_q: normalized susceptibility must lie in [0,10]")

    validation_rows = np.asarray(
        plan["partition"]["folds"][fold_index]["validation_rows"]["data"], dtype=np.int64
    )
    if (validation_rows.ndim != 1 or not len(validation_rows)
            or np.any(np.diff(validation_rows) <= 0)
            or np.intersect1d(validation_rows, plan["partition"]["outer_rows"]["data"]).size):
        raise ValueError("partition: invalid or outer-overlapping validation rows")
    quantity, components = _QUANTITIES[document["processing"]["quantity"]]
    source_indices = (validation_rows[:, None] * components
                      + np.arange(components, dtype=np.int64)).reshape(-1)
    local_indices = np.arange(len(source_indices), dtype=np.int64)
    observed = observations.reshape(-1, order="C")[source_indices].astype(np.float64, copy=True)
    if document["noise"]["kind"] == "diagonal_sd":
        selected_noise = noise.reshape(-1, order="C")[source_indices].reshape(-1, 1).copy()
        whitener = GaussianWhitener("diagonal_sd", selected_noise, local_indices)
    else:
        selected_noise = noise[np.ix_(source_indices, source_indices)].copy(order="C")
        whitener = GaussianWhitener("full_covariance", selected_noise, local_indices)

    mesh_spec = metadata["geometry"]["mesh"]
    origin = np.asarray(mesh_spec["origin_m"]["data"], dtype=np.float64)
    widths = tuple(np.asarray(mesh_spec[key]["data"], dtype=np.float64)
                   for key in ("widths_x_m", "widths_y_m", "widths_z_m"))
    field = metadata["inducing_field"]
    amplitude = float(field["F_nT"])
    inclination = float(field["I_deg"])
    declination = float(field["D_deg"])
    inc, dec = np.deg2rad(inclination), np.deg2rad(declination)
    background = amplitude * np.array([np.cos(inc)*np.sin(dec),
                                       np.cos(inc)*np.cos(dec), np.sin(inc)], dtype=np.float64)
    receivers = np.asarray(metadata["geometry"]["receivers_m"]["data"], dtype=np.float64)
    receivers = receivers.reshape(-1, 3, order="C")[validation_rows]
    forward_request = {
        "schema": "magnetic-prism-forward-request-1", "engine": ENGINE, "frame": FRAME,
        "mesh": {"origin_m": origin, "hx_m": widths[0], "hy_m": widths[1],
                 "hz_m": widths[2], "active": active},
        "receivers_m": receivers, "susceptibility_si": CHI_SCALE_SI * model_snapshot,
        "inducing_field": {"amplitude_nt": amplitude, "inclination_deg": inclination,
                            "declination_deg": declination},
    }
    forward = forward_magnetic_with_kernel(forward_request)
    response = compose_magnetic_observable(
        forward["component_jacobian_nT_per_si"], CHI_SCALE_SI * model_snapshot,
        background, quantity,
    )
    predicted = response["values_nT"].reshape(-1, order="C")
    jacobian = response["jacobian_q_nT"]
    evaluated = GaussianDataTerm(observed, whitener).evaluate(predicted, jacobian)
    raw_residual = predicted - observed
    return {
        "schema": "magnetic-development-fold-score-1",
        "role": "development-validation-only",
        "fold_index": fold_index,
        "geometry_seal_sha256": plan["identity"]["seal_sha256"],
        "model_q_f64le_sha256": actual_model_sha256,
        "receiver_count": int(len(validation_rows)),
        "observation_count": int(len(source_indices)),
        "quantity": quantity,
        "phi_d": evaluated.phi_d,
        "mean_standardized_quadratic": evaluated.phi_d / len(source_indices),
        "residual_rms_nT": float(np.sqrt(np.mean(raw_residual * raw_residual))),
        "cross_partition_dependence": document["noise"]["cross_partition_dependence"],
        "contains_observation_vectors": False,
        "candidate_selection_performed": False,
        "outer_evaluation_performed": False,
    }
