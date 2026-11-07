from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import signal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from fwi_diagnostics import (  # noqa: E402
    FWIDiagnosticError,
    audit_fwi_protocol,
    compare_fwi_cases,
    receiver_resolved_spectra,
    residual_spectrum,
    split_residual_by_receiver_mask,
)


def _direct_welch_density(traces, *, fs, nperseg, noverlap):
    """Small explicit one-sided Welch oracle; no scipy spectral routine."""
    window = signal.windows.hann(nperseg, sym=False)
    step = nperseg - noverlap
    segments = np.stack(
        [traces[..., start : start + nperseg] for start in range(0, traces.shape[-1] - nperseg + 1, step)],
        axis=-2,
    )
    transforms = np.fft.rfft(segments * window, axis=-1)
    density = np.abs(transforms) ** 2 / (fs * np.sum(window**2))
    if nperseg % 2 == 0:
        density[..., 1:-1] *= 2.0
    else:
        density[..., 1:] *= 2.0
    return np.fft.rfftfreq(nperseg, d=1.0 / fs), density.mean(axis=-2)


def _case(name="Layered"):
    return {
        "name": name,
        "geometry": "layered",
        "methods": {
            "fwi-l2": {"metrics": {"model_rmse_ratio": 0.55}},
            "fwi-multiscale": {
                "evaluation": {"status": "recovered"},
                "metrics": {
                    "initial_velocity_rmse": 700.0,
                    "model_rmse_ratio": 0.52,
                    "active_wrms": 1.1,
                    "withheld_wrms": 1.4,
                },
            },
        },
    }


def test_residual_spectrum_matches_documented_scipy_calculation():
    time = np.arange(512) * 0.004
    gather = np.stack((np.sin(2 * np.pi * 6 * time) + 3, np.cos(2 * np.pi * 14 * time) - 2))
    result = residual_spectrum(gather, dt=0.004)

    detrended = signal.detrend(gather, axis=-1, type="constant")
    frequencies, density = _direct_welch_density(
        detrended, fs=250, nperseg=256, noverlap=128
    )
    full_window = signal.windows.hann(detrended.shape[-1], sym=False)
    full_transform = np.fft.rfft(detrended * full_window, axis=-1)
    periodogram = np.abs(full_transform) ** 2 / (250 * np.sum(full_window**2))
    periodogram[..., 1:-1] *= 2.0
    periodogram_frequencies = np.fft.rfftfreq(detrended.shape[-1], d=1 / 250)

    np.testing.assert_allclose(result["frequencies_hz"], frequencies)
    np.testing.assert_allclose(result["density_by_receiver"], density)
    np.testing.assert_allclose(result["mean_density"], density.mean(axis=0))
    np.testing.assert_allclose(result["periodogram_frequencies_hz"], periodogram_frequencies)
    np.testing.assert_allclose(result["mean_periodogram"], periodogram.mean(axis=0))
    assert result["low_band_fraction"] == pytest.approx(
        density.mean(axis=0)[frequencies < 10].sum() / density.mean(axis=0).sum()
    )
    np.testing.assert_allclose(result["detrended"], detrended)
    np.testing.assert_allclose(
        result["tapered"],
        detrended * signal.windows.hann(gather.shape[-1], sym=False)[None, :],
    )
    # Guard against a full-record Hann being multiplied before Welch applies
    # its own segment window (the previous implementation tapered twice).
    double_window_density = signal.welch(
        result["tapered"], fs=250, window="hann", nperseg=256,
        noverlap=128, axis=-1, detrend=False, scaling="density",
    )[1]
    assert not np.allclose(density, double_window_density)


@pytest.mark.parametrize(
    "gather,kwargs",
    [
        (np.ones(32), {"dt": 0.004}),
        (np.ones((2, 0)), {"dt": 0.004}),
        (np.array([[1.0, np.nan, 2.0]]), {"dt": 0.004}),
        ([["not numeric"]], {"dt": 0.004}),
        (np.ones((2, 32)), {"dt": 0}),
        (np.ones((2, 32)), {"dt": np.inf}),
        (np.ones((2, 32)), {"dt": 0.004, "low_band_hz": -1}),
        (np.ones((2, 32)), {"dt": 0.004, "low_band_hz": 126}),
        (np.ones((2, 32)), {"dt": 1e-320}),
        (np.ones((2, 32)), {"dt": 0.004, "nperseg": 64}),
        (np.ones((2, 32)), {"dt": 0.004, "nperseg": 1}),
        (np.ones((2, 32)), {"dt": 0.004, "noverlap": 256}),
        (np.ones((2, 32)), {"dt": 0.004, "peak_prominence_fraction": 1.1}),
    ],
)
def test_residual_spectrum_rejects_invalid_input(gather, kwargs):
    with pytest.raises(FWIDiagnosticError):
        residual_spectrum(gather, **kwargs)


def test_residual_spectrum_zero_energy_has_finite_zero_fraction():
    result = residual_spectrum(np.ones((2, 256)), dt=0.004)
    assert result["low_band_fraction"] == 0.0
    assert np.isfinite(result["mean_density"]).all()


def test_compare_fwi_cases_preserves_recorded_metrics_and_order():
    runs = {"a": _case("Layered"), "b": _case("Fault")}
    runs["b"]["methods"]["fwi-l2"]["metrics"]["model_rmse_ratio"] = 0.8
    runs["b"]["methods"]["fwi-multiscale"]["metrics"]["model_rmse_ratio"] = 0.7
    result = compare_fwi_cases(runs, ["b", "a"])

    assert result["case_ids"] == ("b", "a")
    assert [row["Case"] for row in result["rows"]] == ["Fault", "Layered"]
    assert result["rows"][0] == {
        "Case": "Fault",
        "Geometry": "layered",
        "Verdict": "recovered",
        "Start RMSE m/s": 700.0,
        "Full band / start": 0.8,
        "Continuation / start": 0.7,
        "Fit WRMS": 1.1,
        "Held-out WRMS": 1.4,
    }
    np.testing.assert_array_equal(result["full_band_model_rmse_ratio"], [0.8, 0.55])
    np.testing.assert_array_equal(result["continuation_model_rmse_ratio"], [0.7, 0.52])
    np.testing.assert_array_equal(result["active_wrms"], [1.1, 1.1])
    np.testing.assert_array_equal(result["withheld_wrms"], [1.4, 1.4])


@pytest.mark.parametrize(
    "records,case_ids",
    [
        ([], ["a"]),
        ({"a": _case()}, []),
        ({"a": _case()}, "a"),
        ({"a": _case()}, ["a", "a"]),
        ({"a": _case()}, [""]),
        ({}, ["missing"]),
    ],
)
def test_compare_fwi_cases_rejects_invalid_mapping_or_ids(records, case_ids):
    with pytest.raises(FWIDiagnosticError):
        compare_fwi_cases(records, case_ids)


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf, -0.1, "1.0", True])
def test_compare_fwi_cases_rejects_invalid_recorded_metric(bad_value):
    run = _case()
    run["methods"]["fwi-multiscale"]["metrics"]["active_wrms"] = bad_value
    with pytest.raises(FWIDiagnosticError):
        compare_fwi_cases({"a": run}, ["a"])


def test_compare_fwi_cases_rejects_incomplete_saved_record():
    with pytest.raises(FWIDiagnosticError, match="missing saved comparison fields"):
        compare_fwi_cases({"a": {"name": "Layered"}}, ["a"])


def test_receiver_resolved_spectra_preserves_receiver_specific_differences():
    time = np.arange(512) * 0.004
    gather = np.stack((np.sin(2 * np.pi * 6 * time), 2 * np.sin(2 * np.pi * 18 * time)))
    result = receiver_resolved_spectra(gather, dt=0.004)
    centered = signal.detrend(gather, axis=-1, type="constant")
    frequencies, density = _direct_welch_density(
        centered, fs=250, nperseg=256, noverlap=128
    )
    np.testing.assert_allclose(result["frequencies_hz"], frequencies)
    np.testing.assert_allclose(result["density_by_receiver"], density)
    expected_fraction = density[:, frequencies < 10].sum(axis=1) / density.sum(axis=1)
    np.testing.assert_allclose(result["low_band_fraction_by_receiver"], expected_fraction)
    np.testing.assert_allclose(
        result["spectral_centroid_hz_by_receiver"], density @ frequencies / density.sum(axis=1)
    )
    np.testing.assert_allclose(result["residual_rms_by_receiver"], np.sqrt(np.mean(gather**2, axis=1)))
    assert result["dominant_frequency_hz_by_receiver"][0] != result["dominant_frequency_hz_by_receiver"][1]


def test_receiver_resolved_spectra_uses_one_sided_scaling_for_odd_segments():
    rng = np.random.default_rng(8041)
    gather = rng.normal(size=(3, 129))
    result = receiver_resolved_spectra(
        gather, dt=0.002, nperseg=63, noverlap=21
    )
    centered = signal.detrend(gather, axis=-1, type="constant")
    expected_frequency, expected_density = _direct_welch_density(
        centered, fs=500, nperseg=63, noverlap=21
    )
    np.testing.assert_allclose(result["frequencies_hz"], expected_frequency)
    np.testing.assert_allclose(result["density_by_receiver"], expected_density)


@pytest.mark.parametrize(
    "gather,kwargs",
    [
        (np.ones(64), {"dt": 0.004}),
        (np.array([[1.0, np.inf]]), {"dt": 0.004}),
        (np.ones((2, 64)), {"dt": 0}),
        (np.ones((2, 64)), {"dt": 0.004, "low_band_hz": 126}),
        (np.ones((2, 64)), {"dt": 0.004, "nperseg": 65}),
        (np.ones((2, 64)), {"dt": 0.004, "noverlap": -1}),
    ],
)
def test_receiver_resolved_spectra_rejects_adversarial_input(gather, kwargs):
    with pytest.raises(FWIDiagnosticError):
        receiver_resolved_spectra(gather, **kwargs)


def test_split_residual_by_receiver_mask_separates_populations_per_shot():
    residual = np.array([
        [[1.0, -1.0], [2.0, 2.0], [3.0, -3.0], [4.0, 4.0]],
        [[2.0, -2.0], [1.0, 1.0], [4.0, -4.0], [2.0, 2.0]],
    ])
    result = split_residual_by_receiver_mask(residual, [True, False, True, False])
    assert result["active_receiver_count"] == 2
    assert result["withheld_receiver_count"] == 2
    np.testing.assert_array_equal(result["active_residual"], residual[:, [0, 2], :])
    np.testing.assert_array_equal(result["withheld_residual"], residual[:, [1, 3], :])
    np.testing.assert_allclose(result["active_rms_by_shot"], [np.sqrt(5), np.sqrt(10)])
    np.testing.assert_allclose(result["withheld_rms_by_shot"], [np.sqrt(10), np.sqrt(2.5)])


@pytest.mark.parametrize(
    "residual,mask",
    [
        (np.ones((2, 4)), [True, False, True, False]),
        (np.ones((2, 4, 8)), [True, False]),
        (np.ones((2, 4, 8)), [1, 0, 1, 0]),
        (np.ones((2, 4, 8)), [True, True, True, True]),
        (np.ones((2, 4, 8)), [False, False, False, False]),
        (np.full((2, 4, 8), np.nan), [True, False, True, False]),
    ],
)
def test_split_residual_by_receiver_mask_rejects_adversarial_input(residual, mask):
    with pytest.raises(FWIDiagnosticError):
        split_residual_by_receiver_mask(residual, mask)


def _protocol_case(case_id="a"):
    return {
        "schema": "inverse-earth/v2",
        "variant": "reference",
        "engine": "Deepwave pinned",
        "lane": "computed replay",
        "units": "m/s",
        "data_units": "amplitude",
        "dt": 0.004,
        "wavefield_dt": 0.024,
        "sources": [[0, 10], [100, 10]],
        "receivers": [[x, 10] for x in range(4)],
        "active_receivers": [True, False, True, False],
        "geometry": "layers" if case_id == "a" else "fault",
        "seed": 100 if case_id == "a" else 101,
        "parameters": {
            "internal_dt": 0.0005,
            "iterations": 28,
            "iterations_semantics": "maximum calls per stage",
            "regularization": 0.001,
            "spatial_accuracy": 4,
            "pml_thickness_m": 300,
            "calibration_id": "calibration-v1",
            "data_origin": "same-operator synthetic",
            "withheld_policy": "fixed modulo-five",
            "initial_policy": "independent trend",
            "deterministic_algorithms": True,
            "cudnn_deterministic": True,
            "cudnn_benchmark": False,
            "noise_fraction": 0.01,
            "record_samples": 3200,
            "record_duration_s": 1.6,
            "receivers": 4,
            "frequency_hz": 8.0 if case_id == "a" else 9.0,
            "noise_sigma": 0.025 if case_id == "a" else 0.024,
        },
    }


def test_audit_fwi_protocol_separates_invariants_from_declared_variations():
    records = {"a": _protocol_case("a"), "b": _protocol_case("b")}
    audit = audit_fwi_protocol(records, ["a", "b"])
    assert audit["consistent"] is True
    assert audit["mismatches"] == {}
    assert audit["controlled_variations"]["parameters.frequency_hz"] == {"a": 8.0, "b": 9.0}
    assert audit["controlled_variations"]["seed"] == {"a": 100, "b": 101}
    assert len(audit["checked_protocol_fields"]) >= 20


@pytest.mark.parametrize(
    "mutation,expected_path",
    [
        (lambda run: run.update(dt=0.008), "dt"),
        (lambda run: run["parameters"].update(pml_thickness_m=500), "parameters.pml_thickness_m"),
        (lambda run: run.update(active_receivers=[True, True, False, False]), "active_receivers"),
    ],
)
def test_audit_fwi_protocol_reports_shared_protocol_mismatch(mutation, expected_path):
    records = {"a": _protocol_case("a"), "b": _protocol_case("b")}
    mutation(records["b"])
    audit = audit_fwi_protocol(records, ["a", "b"])
    assert audit["consistent"] is False
    assert expected_path in audit["mismatches"]


@pytest.mark.parametrize(
    "records,case_ids",
    [
        ({"a": _protocol_case("a")}, ["a"]),
        ({"a": _protocol_case("a"), "b": _protocol_case("b")}, ["a", "a"]),
        ({"a": _protocol_case("a"), "b": _protocol_case("b")}, "ab"),
        ({"a": _protocol_case("a"), "b": {}}, ["a", "b"]),
        ({"a": _protocol_case("a"), "b": _protocol_case("b")}, ["a", "missing"]),
    ],
)
def test_audit_fwi_protocol_rejects_invalid_case_selection(records, case_ids):
    with pytest.raises(FWIDiagnosticError):
        audit_fwi_protocol(records, case_ids)


def test_audit_fwi_protocol_rejects_nonfinite_protocol_values():
    records = {"a": _protocol_case("a"), "b": _protocol_case("b")}
    records["b"]["dt"] = np.nan
    with pytest.raises(FWIDiagnosticError, match="not finite JSON data"):
        audit_fwi_protocol(records, ["a", "b"])
