"""Read-only diagnostics for saved full-waveform-inversion artifacts.

These functions inspect existing residuals and recorded case metrics. They do
not run a forward model, alter a saved verdict, or estimate geological truth.
"""

from collections.abc import Mapping, Sequence
from numbers import Real
import json

import numpy as np
from scipy import signal


class FWIDiagnosticError(ValueError):
    """Raised when saved FWI inputs do not satisfy the diagnostic contract."""


def _finite_array(value, name: str, ndim: int) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise FWIDiagnosticError(f"{name} must be a finite numeric array") from error
    if array.ndim != ndim or any(size == 0 for size in array.shape):
        raise FWIDiagnosticError(f"{name} must be a non-empty {ndim}-D array")
    if not np.isfinite(array).all():
        raise FWIDiagnosticError(f"{name} must contain only finite values")
    return array


def _positive_real(value, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise FWIDiagnosticError(f"{name} must be a finite positive number")
    result = float(value)
    if not np.isfinite(result) or result <= 0:
        raise FWIDiagnosticError(f"{name} must be a finite positive number")
    return result


def residual_spectrum(
    gather,
    *,
    dt: float,
    low_band_hz: float = 10.0,
    nperseg: int = 256,
    noverlap: int = 128,
    peak_prominence_fraction: float = 0.03,
) -> dict[str, object]:
    """Compute fixed Welch and periodogram summaries from one saved shot gather.

    ``gather`` has shape ``(receiver, time)``. Constant trace means are
    removed. Welch applies one periodic Hann window to each segment; the
    full-record taper is returned separately for display. The periodogram
    applies one periodic Hann window to the full record. Receiver spectra are
    averaged using SciPy's density scaling. Returned values describe only the
    supplied residual; they do not score or select an inversion method.
    """
    values = _finite_array(gather, "gather", 2)
    sample_interval = _positive_real(dt, "dt")
    low_band = _positive_real(low_band_hz, "low_band_hz")
    sampling_rate = 1.0 / sample_interval
    if not np.isfinite(sampling_rate):
        raise FWIDiagnosticError("dt is too small to produce a finite sampling rate")
    if low_band > sampling_rate / 2.0:
        raise FWIDiagnosticError("low_band_hz must not exceed the Nyquist frequency")
    if isinstance(nperseg, (bool, np.bool_)) or not isinstance(nperseg, (int, np.integer)):
        raise FWIDiagnosticError("nperseg must be an integer of at least 2")
    if isinstance(noverlap, (bool, np.bool_)) or not isinstance(noverlap, (int, np.integer)):
        raise FWIDiagnosticError("noverlap must be an integer in [0, nperseg)")
    nperseg, noverlap = int(nperseg), int(noverlap)
    if nperseg < 2 or nperseg > values.shape[1]:
        raise FWIDiagnosticError("nperseg must be between 2 and the number of samples")
    if noverlap < 0 or noverlap >= nperseg:
        raise FWIDiagnosticError("noverlap must be in [0, nperseg)")
    if isinstance(peak_prominence_fraction, (bool, np.bool_)) or not isinstance(
        peak_prominence_fraction, Real
    ):
        raise FWIDiagnosticError("peak_prominence_fraction must be finite and in [0, 1]")
    prominence_fraction = float(peak_prominence_fraction)
    if not np.isfinite(prominence_fraction) or not 0 <= prominence_fraction <= 1:
        raise FWIDiagnosticError("peak_prominence_fraction must be finite and in [0, 1]")

    detrended = signal.detrend(values, axis=-1, type="constant")
    window = signal.windows.hann(values.shape[-1], sym=False)
    tapered = detrended * window[None, :]
    frequencies, density_by_receiver = signal.welch(
        detrended,
        fs=sampling_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        axis=-1,
        detrend=False,
        scaling="density",
    )
    mean_density = density_by_receiver.mean(axis=0)
    total_power = float(mean_density.sum())
    low_fraction = (
        float(mean_density[frequencies < low_band].sum() / total_power)
        if total_power > 0
        else 0.0
    )
    periodogram_frequency, periodogram_by_receiver = signal.periodogram(
        detrended, fs=sampling_rate, window="hann", axis=-1, detrend=False
    )
    computed = (frequencies, density_by_receiver, mean_density,
                periodogram_frequency, periodogram_by_receiver)
    if any(not np.isfinite(array).all() for array in computed):
        raise FWIDiagnosticError("residual spectrum overflowed; input amplitudes are out of range")
    peaks, _ = signal.find_peaks(
        mean_density, prominence=float(mean_density.max()) * prominence_fraction
    )
    return {
        "frequencies_hz": frequencies,
        "density_by_receiver": density_by_receiver,
        "mean_density": mean_density,
        "low_band_fraction": low_fraction,
        "periodogram_frequencies_hz": periodogram_frequency,
        "mean_periodogram": periodogram_by_receiver.mean(axis=0),
        "peak_frequencies_hz": frequencies[peaks],
        "detrended": detrended,
        "tapered": tapered,
    }


def receiver_resolved_spectra(
    gather,
    *,
    dt: float,
    low_band_hz: float = 10.0,
    nperseg: int = 256,
    noverlap: int = 128,
) -> dict[str, object]:
    """Return per-receiver spectral energy summaries for a saved shot gather.

    Each receiver is demeaned independently. Welch applies one periodic Hann
    window to each segment, and density is retained by receiver so spatially
    localized residual energy is visible;
    low-band fraction and centroid are descriptive only and do not rank FWI
    methods. Input shape is ``(receiver, time)``.
    """
    values = _finite_array(gather, "gather", 2)
    sample_interval = _positive_real(dt, "dt")
    sampling_rate = 1.0 / sample_interval
    if not np.isfinite(sampling_rate):
        raise FWIDiagnosticError("dt is too small to produce a finite sampling rate")
    low_band = _positive_real(low_band_hz, "low_band_hz")
    if low_band > sampling_rate / 2.0:
        raise FWIDiagnosticError("low_band_hz must not exceed the Nyquist frequency")
    if isinstance(nperseg, (bool, np.bool_)) or not isinstance(nperseg, (int, np.integer)):
        raise FWIDiagnosticError("nperseg must be an integer between 2 and trace length")
    if isinstance(noverlap, (bool, np.bool_)) or not isinstance(noverlap, (int, np.integer)):
        raise FWIDiagnosticError("noverlap must be an integer in [0, nperseg)")
    nperseg, noverlap = int(nperseg), int(noverlap)
    if nperseg < 2 or nperseg > values.shape[1]:
        raise FWIDiagnosticError("nperseg must be between 2 and the number of samples")
    if noverlap < 0 or noverlap >= nperseg:
        raise FWIDiagnosticError("noverlap must be in [0, nperseg)")

    centered = signal.detrend(values, axis=-1, type="constant")
    frequencies, density = signal.welch(
        centered, fs=sampling_rate, window="hann", nperseg=nperseg,
        noverlap=noverlap, axis=-1, detrend=False, scaling="density",
    )
    totals = density.sum(axis=1)
    low_energy = density[:, frequencies < low_band].sum(axis=1)
    low_fraction = np.divide(low_energy, totals, out=np.zeros_like(totals), where=totals > 0)
    centroid = np.divide(
        density @ frequencies, totals, out=np.zeros_like(totals), where=totals > 0
    )
    dominant = frequencies[np.argmax(density, axis=1)]
    trace_rms = np.sqrt(np.mean(np.square(values), axis=1))
    outputs = (frequencies, density, low_fraction, centroid, dominant, trace_rms)
    if any(not np.isfinite(array).all() for array in outputs):
        raise FWIDiagnosticError("receiver spectrum overflowed; input amplitudes are out of range")
    return {
        "frequencies_hz": frequencies,
        "density_by_receiver": density,
        "low_band_fraction_by_receiver": low_fraction,
        "spectral_centroid_hz_by_receiver": centroid,
        "dominant_frequency_hz_by_receiver": dominant,
        "residual_rms_by_receiver": trace_rms,
    }


def split_residual_by_receiver_mask(residual, active_receivers) -> dict[str, object]:
    """Separate saved shot residuals by the artifact's fitting/holdout mask.

    ``residual`` is ``(shot, receiver, time)`` and the Boolean mask has one
    value per receiver. RMS summaries are raw amplitude diagnostics, not
    noise-normalized WRMS and not a replacement for the recorded verdict.
    Both populations must be present.
    """
    values = _finite_array(residual, "residual", 3)
    try:
        mask = np.asarray(active_receivers)
    except (TypeError, ValueError) as error:
        raise FWIDiagnosticError("active_receivers must be a one-dimensional Boolean mask") from error
    if mask.ndim != 1 or mask.dtype.kind != "b" or mask.size != values.shape[1]:
        raise FWIDiagnosticError("active_receivers must be Boolean with one value per receiver")
    if not mask.any() or mask.all():
        raise FWIDiagnosticError("active and withheld receiver populations must both be non-empty")
    active = values[:, mask, :]
    withheld = values[:, ~mask, :]
    active_rms = np.sqrt(np.mean(np.square(active), axis=(1, 2)))
    withheld_rms = np.sqrt(np.mean(np.square(withheld), axis=(1, 2)))
    if not np.isfinite(active_rms).all() or not np.isfinite(withheld_rms).all():
        raise FWIDiagnosticError("residual RMS overflowed; input amplitudes are out of range")
    return {
        "active_residual": active,
        "withheld_residual": withheld,
        "active_receiver_count": int(mask.sum()),
        "withheld_receiver_count": int((~mask).sum()),
        "active_rms_by_shot": active_rms,
        "withheld_rms_by_shot": withheld_rms,
    }


_PROTOCOL_PATHS = (
    "schema", "variant", "engine", "lane", "units", "data_units", "dt",
    "wavefield_dt", "sources", "receivers", "active_receivers",
    "parameters.internal_dt", "parameters.iterations",
    "parameters.iterations_semantics", "parameters.regularization",
    "parameters.spatial_accuracy", "parameters.pml_thickness_m",
    "parameters.calibration_id", "parameters.data_origin",
    "parameters.withheld_policy", "parameters.initial_policy",
    "parameters.deterministic_algorithms", "parameters.cudnn_deterministic",
    "parameters.cudnn_benchmark", "parameters.noise_fraction",
    "parameters.record_samples", "parameters.record_duration_s",
    "parameters.receivers",
)
_CONTROLLED_VARIATION_PATHS = (
    "geometry", "seed", "parameters.frequency_hz", "parameters.noise_sigma",
)


def _path_value(record: Mapping, dotted_path: str, case_id: str):
    current = record
    try:
        for part in dotted_path.split("."):
            current = current[part]
    except (KeyError, TypeError) as error:
        raise FWIDiagnosticError(f"{case_id} is missing protocol field {dotted_path}") from error
    return current


def _json_fingerprint(value, case_id: str, path: str) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError) as error:
        raise FWIDiagnosticError(f"{case_id} protocol field {path} is not finite JSON data") from error


def audit_fwi_protocol(records: Mapping, case_ids: Sequence[str]) -> dict[str, object]:
    """Audit common acquisition/solver protocol across saved FWI cases.

    Protocol invariants must match exactly. Geometry, random seed, source
    frequency, and realized noise sigma are reported as controlled variations
    because the case matrix intentionally changes geology and realization.
    The audit only identifies mismatches; it does not rewrite metrics or
    decide whether a method recovered a model.
    """
    if not isinstance(records, Mapping):
        raise FWIDiagnosticError("records must be a mapping of case IDs to saved runs")
    if isinstance(case_ids, (str, bytes)) or not isinstance(case_ids, Sequence):
        raise FWIDiagnosticError("case_ids must be a non-empty sequence of unique strings")
    ids = list(case_ids)
    if not ids or any(not isinstance(case_id, str) or not case_id for case_id in ids):
        raise FWIDiagnosticError("case_ids must be a non-empty sequence of unique strings")
    if len(set(ids)) != len(ids):
        raise FWIDiagnosticError("case_ids must not contain duplicates")
    if len(ids) < 2:
        raise FWIDiagnosticError("protocol audit requires at least two saved cases")

    selected = {}
    for case_id in ids:
        try:
            record = records[case_id]
        except KeyError as error:
            raise FWIDiagnosticError(f"missing saved case {case_id}") from error
        if not isinstance(record, Mapping):
            raise FWIDiagnosticError(f"{case_id} must be a saved run mapping")
        selected[case_id] = record

    mismatches = {}
    for path in _PROTOCOL_PATHS:
        observed = {
            case_id: _path_value(record, path, case_id)
            for case_id, record in selected.items()
        }
        fingerprints = {
            case_id: _json_fingerprint(value, case_id, path)
            for case_id, value in observed.items()
        }
        if len(set(fingerprints.values())) != 1:
            mismatches[path] = observed

    controlled_variations = {
        path: {
            case_id: _path_value(record, path, case_id)
            for case_id, record in selected.items()
        }
        for path in _CONTROLLED_VARIATION_PATHS
    }
    for path, by_case in controlled_variations.items():
        for case_id, value in by_case.items():
            _json_fingerprint(value, case_id, path)
    return {
        "consistent": not mismatches,
        "case_ids": tuple(ids),
        "checked_protocol_fields": _PROTOCOL_PATHS,
        "controlled_variations": controlled_variations,
        "mismatches": mismatches,
    }


def _metric(method: Mapping, metric_name: str, case_id: str) -> float:
    try:
        value = method["metrics"][metric_name]
    except (KeyError, TypeError) as error:
        raise FWIDiagnosticError(f"{case_id} is missing metric {metric_name}") from error
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise FWIDiagnosticError(f"{case_id} metric {metric_name} must be numeric")
    result = float(value)
    if not np.isfinite(result) or result < 0:
        raise FWIDiagnosticError(f"{case_id} metric {metric_name} must be finite and non-negative")
    return result


def compare_fwi_cases(records: Mapping, case_ids: Sequence[str]) -> dict[str, object]:
    """Assemble paired comparison rows and plot vectors from saved case metrics.

    The input cases must already be artifact-verified by the caller. Values
    are copied verbatim as floats from their recorded metrics; no new score,
    fit, threshold, or verdict is inferred here.
    """
    if not isinstance(records, Mapping):
        raise FWIDiagnosticError("records must be a mapping of case IDs to saved runs")
    if isinstance(case_ids, (str, bytes)) or not isinstance(case_ids, Sequence):
        raise FWIDiagnosticError("case_ids must be a non-empty sequence of unique strings")
    ids = list(case_ids)
    if not ids or any(not isinstance(case_id, str) or not case_id for case_id in ids):
        raise FWIDiagnosticError("case_ids must be a non-empty sequence of unique strings")
    if len(set(ids)) != len(ids):
        raise FWIDiagnosticError("case_ids must not contain duplicates")

    rows = []
    full_band, continuation, active, withheld, names = [], [], [], [], []
    for case_id in ids:
        try:
            run = records[case_id]
            full = run["methods"]["fwi-l2"]
            multi = run["methods"]["fwi-multiscale"]
            name, geometry = run["name"], run["geometry"]
            verdict = multi["evaluation"]["status"]
        except (KeyError, TypeError) as error:
            raise FWIDiagnosticError(f"{case_id} is missing saved comparison fields") from error
        if not isinstance(name, str) or not name or not isinstance(geometry, str) or not geometry:
            raise FWIDiagnosticError(f"{case_id} must have non-empty name and geometry strings")
        if not isinstance(verdict, str) or not verdict:
            raise FWIDiagnosticError(f"{case_id} must have a recorded evaluation status")
        initial = _metric(multi, "initial_velocity_rmse", case_id)
        full_ratio = _metric(full, "model_rmse_ratio", case_id)
        multi_ratio = _metric(multi, "model_rmse_ratio", case_id)
        fit_wrms = _metric(multi, "active_wrms", case_id)
        held_wrms = _metric(multi, "withheld_wrms", case_id)
        rows.append({
            "Case": name,
            "Geometry": geometry,
            "Verdict": verdict,
            "Start RMSE m/s": initial,
            "Full band / start": full_ratio,
            "Continuation / start": multi_ratio,
            "Fit WRMS": fit_wrms,
            "Held-out WRMS": held_wrms,
        })
        names.append(name)
        full_band.append(full_ratio)
        continuation.append(multi_ratio)
        active.append(fit_wrms)
        withheld.append(held_wrms)

    return {
        "case_ids": tuple(ids),
        "names": tuple(names),
        "rows": rows,
        "full_band_model_rmse_ratio": np.asarray(full_band),
        "continuation_model_rmse_ratio": np.asarray(continuation),
        "active_wrms": np.asarray(active),
        "withheld_wrms": np.asarray(withheld),
    }
