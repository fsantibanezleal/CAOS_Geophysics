"""Independent numerical controls: no mocked successful physics or catalogue tuning."""
import copy
import cmath
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(ROOT / "tests/data"))
from test_waveform_input import source, inventory, request, rejected
from waveform_processing import (process_waveform_record, candidate_intervals,
                                 compute_characteristic, welch_products, filter_products)
from waveform_evaluation import references_from_stp, evaluate_waveform_candidates, seal_result


def direct_dft(values):
    n = len(values)
    return np.array([sum(float(values[j]) * cmath.exp(-2j * math.pi * k * j / n)
                         for j in range(n)) for k in range(n // 2 + 1)])


def test_response_epoch_and_classical_picks():
    result = process_waveform_record(source(), inventory(), request())
    assert result.metadata["status"] == "computed"
    assert result.arrays[(0, "physical_native")].shape == (4000,)
    assert result.arrays[(0, "counts")].dtype == np.dtype("<i4")
    assert result.metadata["channels"][0]["native_unit"] == "m/s"
    assert result.metadata["channels"][0]["absolute_timing_verified"] is False
    for candidate in result.metadata["candidates"]:
        assert candidate["phase"] is None and candidate["timing_sigma_s"] is None


def test_stage_chain_units_gain_orientation_and_polarity():
    result = process_waveform_record(source(), inventory(azimuth=90, dip=0), request())
    np.testing.assert_allclose(result.metadata["channels"][0]["projection_enu"], [1, 0, 0], atol=1e-12)
    for xml, reason in [(inventory(units="CM/S"), "response_units_missing"),
                        (inventory(gain=-1), "response_chain_inconsistent"),
                        (inventory(azimuth=360), "orientation_missing")]:
        out = process_waveform_record(source(), xml, request())
        assert out.metadata["status"] == "qc_only" and reason in out.metadata["qc"]["reasons"]


def test_independent_response_oracles_and_stabilization():
    result = process_waveform_record(source(), inventory(), request())
    np.testing.assert_allclose(result.arrays[(0, "response_real")], 1000, rtol=1e-10, atol=1e-9)
    np.testing.assert_allclose(result.arrays[(0, "response_imag")], 0, atol=1e-9)
    # Independent centred least squares + direct DFT at a small actual-engine N=200.
    req = request()
    req["conditioning_end_utc"] = "2020-01-01T00:00:10Z"
    req["analysis_start_utc"] = "2020-01-01T00:00:02Z"
    req["analysis_end_utc"] = "2020-01-01T00:00:08Z"
    req["processing"].update(edge_guard_s=0., lta_s=.5, sta_s=.05, welch_segment_samples=64)
    # Large-N operator oracle uses exact independent DFT bins, not production FFT.
    counts = result.arrays[(0, "counts")].astype(float)
    tau = np.array([(n - (len(counts) - 1) / 2) / 100 for n in range(len(counts))])
    mean = sum(counts) / len(counts)
    slope = sum(tau[n] * (counts[n] - mean) for n in range(len(counts))) / sum(tau * tau)
    x = (counts - mean - slope * tau) * result.arrays[(0, "time_taper")]
    kfft = result.metadata["processing"]["channels"][0]["fft_samples"]
    for k in (0, 80, 240, 1360):
        d = sum(x[j] * cmath.exp(-2j * math.pi * k * j / kfft) for j in range(len(x)))
        f = k * 100 / kfft
        assert abs(f - result.arrays[(0, "response_frequency_hz")][k]) < 1e-12
        if k == 240:
            assert abs(d) > 1
    # No full DFT-FFT self-comparison establishes the physical inverse gate alone.


def test_sos_filter_oracle_edges_and_acausality():
    impulse = np.zeros(4000)
    impulse[2000] = 1
    out, sos, pad = filter_products(impulse, 100, [2., 10.], 4)
    assert np.any(np.abs(out[1900:2000]) > 1e-8) and pad == 27
    f = 5.
    z = cmath.exp(-2j * math.pi * f / 100)
    transfer = math.prod(abs((b0 + b1*z + b2*z*z) / (a0 + a1*z + a2*z*z)) ** 2
                         for b0,b1,b2,a0,a1,a2 in sos)
    sinusoid = np.sin(2 * math.pi * f * np.arange(4000) / 100)
    filtered, _, _ = filter_products(sinusoid, 100, [2., 10.], 4)
    np.testing.assert_allclose(filtered[1500:2500], transfer * sinusoid[1500:2500], rtol=1e-9, atol=1e-9)


def test_welch_dft_parseval_and_units():
    y = np.array([math.sin(2 * math.pi * 7 * j / 64) + .3 for j in range(128)])
    freq, psd, diag = welch_products(y, 100, 64)
    v = np.array([.5 - .5*math.cos(2*math.pi*j/64) for j in range(64)])
    total = np.zeros(33)
    energies = []
    for start in (0, 32, 64):
        segment = y[start:start+64] - sum(y[start:start+64])/64
        transformed = direct_dft(segment*v)
        total += np.abs(transformed)**2
        energies.append(sum((segment*v)**2)/sum(v*v))
    total *= np.array([1]+[2]*31+[1])/(3*100*sum(v*v))
    np.testing.assert_allclose(psd, total, rtol=1e-10, atol=1e-12)
    assert abs(sum(psd)*(100/64) - sum(energies)/3) < 1e-12
    assert diag["segments"] == 3 and diag["omitted_tail"] == 0
    assert freq[-1] == 50


def test_direct_stalta_onsets_and_no_phase_fabrication():
    y = np.array([math.sin(.73*j) * (1 if j < 150 else 20) for j in range(500)])
    cf, scale = compute_characteristic(y, 5, 50)
    z = y/scale
    expected = np.zeros(500)
    for j in range(49, 500):
        expected[j] = (sum(z[j-4:j+1]**2)/5) / max(sum(z[j-49:j+1]**2)/50, np.finfo(float).tiny)
    np.testing.assert_allclose(cf, expected, rtol=1e-9, atol=1e-9)
    exact = np.array([4., 3., 1., 4., 5., 5., 1., 4.])
    rows = candidate_intervals(exact, 0, 8, 3., 1., 1, 0, 100, 0)
    assert [(r["on_index"], r["off_exclusive_index"], r["peak_index"]) for r in rows] == [(0,2,0),(3,6,4),(7,8,7)]
    assert rows[0]["truncated_at_valid_start"] and rows[-1]["truncated_at_valid_end"]
    assert all(r["phase"] is None and r["timing_sigma_s"] is None for r in rows)


def test_actual_parameter_effects_and_reference_noninterference():
    raw = source()
    one = process_waveform_record(raw, inventory(), request())
    two = process_waveform_record(raw, inventory(gain=2000), request())
    np.testing.assert_allclose(two.arrays[(0,"physical_native")], one.arrays[(0,"physical_native")]/2, rtol=1e-10, atol=1e-11)
    np.testing.assert_allclose(two.arrays[(0,"physical_psd")], one.arrays[(0,"physical_psd")]/4, rtol=1e-10, atol=1e-12)
    assert one.metadata["sources"]["miniseed"] == two.metadata["sources"]["miniseed"]
    assert one.metadata["sources"]["stationxml"] != two.metadata["sources"]["stationxml"]
    modified = request()
    modified["processing"]["bandpass_hz"] = [6., 10.]
    changed = process_waveform_record(raw, inventory(), modified)
    assert np.std(changed.arrays[(0,"filtered_native")][800:3200]) < np.std(one.arrays[(0,"filtered_native")][800:3200])/10


def test_sealed_reference_conversion_matching_and_residuals():
    raw = b"# 38457511 le 2020/01/01,00:00:00.125 0 0 1 2 l 1\nXX TEST BHZ -- 0 0 0 P cu i 0.5 1 8.125\n"
    converted = references_from_stp(raw, "38457511", ("XX", "TEST", "", "BHZ"))
    assert converted["rows"][0]["pick_utc"] == "2020-01-01T00:00:08.250000Z"
    assert converted["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert converted["rows"][0]["uncertainty_s"] is None
    result = process_waveform_record(source(), inventory(), request())
    sealed = seal_result(result)
    refs = {"schema": "caos.waveform-analyst-references.v1", "event_id": "38457511",
            "source": {"raw_sha256": converted["raw_sha256"], "citation": "authored", "rights": "private-use-attested"},
            "selection_sealed_before_scoring": True, "references": converted["rows"]}
    before = seal_result(result)
    evaluation = evaluate_waveform_candidates(sealed, json.dumps(refs).encode())
    assert seal_result(result) == before
    assert evaluation["schema"] == "caos.local-waveform-evaluation.v1"
    assert "phase_f1" not in evaluation and evaluation["field_truth"] is None
