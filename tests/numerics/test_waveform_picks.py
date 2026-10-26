"""Independent numerical controls: no mocked successful physics or catalogue tuning."""

import cmath
import copy
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
from test_waveform_input import source, inventory, request, record, rejected
from waveform_processing import (
    process_waveform_record,
    candidate_intervals,
    compute_characteristic,
    welch_products,
    filter_products,
)
from waveform_evaluation import references_from_stp, evaluate_waveform_candidates, seal_result, REFERENCE_KEYS


def analog_inventory(pole_hz=0.5, highpass=True):
    omega = 2 * math.pi * 3
    a = 2 * math.pi * pole_hz
    raw_magnitude = omega / math.hypot(omega, a) if highpass else a / math.hypot(omega, a)
    normalization = 1 / raw_magnitude
    return inventory(
        gain=1000 * raw_magnitude,
        normalization=normalization,
        zeros='<Zero number="0"><Real>0</Real><Imaginary>0</Imaginary></Zero>' if highpass else "",
        poles=f'<Pole number="0"><Real>{-a}</Real><Imaginary>0</Imaginary></Pole>',
    ).replace(
        b"<NormalizationFactor>" + str(normalization).encode() + b"</NormalizationFactor>",
        b"<NormalizationFactor>"
        + str(normalization if highpass else a * normalization).encode()
        + b"</NormalizationFactor>",
    )


def digital_inventory(kind="Coefficients", denominator=-0.5):
    xml = inventory()
    begin = xml.index(b"<PolesZeros>")
    end = xml.index(b"</PolesZeros>") + len(b"</PolesZeros>")
    units = "<InputUnits><Name>M/S</Name></InputUnits><OutputUnits><Name>COUNTS</Name></OutputUnits>"
    if kind == "Coefficients":
        filt = f'<Coefficients>{units}<CfTransferFunctionType>DIGITAL</CfTransferFunctionType><Numerator number="0">1</Numerator><Denominator number="0">1</Denominator><Denominator number="1">{denominator}</Denominator></Coefficients>'
    else:
        filt = f'<FIR>{units}<Symmetry>NONE</Symmetry><NumeratorCoefficient i="0">0.75</NumeratorCoefficient><NumeratorCoefficient i="1">0.25</NumeratorCoefficient></FIR>'
    decimation = "<Decimation><InputSampleRate>100</InputSampleRate><Factor>1</Factor><Offset>0</Offset><Delay>0</Delay><Correction>0</Correction></Decimation>"
    return xml[:begin] + filt.encode() + decimation.encode() + xml[end:]


def test_analytic_pz_complex_sign_and_full_inverse():
    for highpass in (True, False):
        out = process_waveform_record(source(), analog_inventory(highpass=highpass), request())
        assert out.metadata["status"] == "computed"
        f = out.arrays[(0, "response_frequency_hz")]
        h = out.arrays[(0, "response_real")] + 1j * out.arrays[(0, "response_imag")]
        s = 2j * np.pi * f
        a = 2 * np.pi * 0.5
        oracle = 1000 * (s if highpass else a) / (s + a)
        np.testing.assert_allclose(h, oracle, rtol=1e-10, atol=1e-9)
        assert h[240].imag > 0 if highpass else h[240].imag < 0


@pytest.mark.parametrize("kind", ["Coefficients", "FIR"])
def test_digital_complex_transfer_product_oracle(kind):
    xml = digital_inventory(kind)
    # Declare actual transfer magnitude at3Hz, not an invented sensitivity.
    z = cmath.exp(-2j * math.pi * 3 / 100)
    mag = abs(1 / (1 - 0.5 * z)) if kind == "Coefficients" else abs(0.75 + 0.25 * z)
    xml = xml.replace(
        b"<InstrumentSensitivity><Value>1000</Value>", f"<InstrumentSensitivity><Value>{1000 * mag}</Value>".encode()
    )
    out = process_waveform_record(source(), xml, request())
    assert out.metadata["status"] == "computed"
    f = out.arrays[(0, "response_frequency_hz")]
    h = out.arrays[(0, "response_real")] + 1j * out.arrays[(0, "response_imag")]
    z = np.array([cmath.exp(-2j * math.pi * float(v) / 100) for v in f])
    expected = (1 / (1 - 0.5 * z)) if kind == "Coefficients" else (0.75 + 0.25 * z)
    np.testing.assert_allclose(h / h[0], expected / expected[0], rtol=1e-10, atol=1e-12)


def test_floor_phase_null_inverse_and_actual_water_level_effect():
    req = request()
    xml = analog_inventory(pole_hz=10)
    req["processing"]["water_level_db"] = 20.0
    low = process_waveform_record(source(), xml, req)
    req["processing"]["water_level_db"] = 120.0
    high = process_waveform_record(source(), xml, req)
    assert low.metadata["status"] == high.metadata["status"] == "computed"
    h = low.arrays[(0, "response_real")] + 1j * low.arrays[(0, "response_imag")]
    g = low.arrays[(0, "inverse_real")] + 1j * low.arrays[(0, "inverse_imag")]
    floor = max(abs(h)) * 0.1
    expected = np.array([0j if v == 0 else cmath.exp(-1j * cmath.phase(v)) / max(abs(v), floor) for v in h])
    np.testing.assert_allclose(g, expected, rtol=1e-10, atol=1e-15)
    assert low.metadata["processing"]["channels"][0]["water_level_active_bins"] > 0
    assert np.max(np.abs(low.arrays[(0, "physical_native")] - high.arrays[(0, "physical_native")])) > 1e-5
    req["processing"]["water_level_db"] = None
    exact = process_waveform_record(source(), xml, req)
    np.testing.assert_allclose(
        exact.arrays[(0, "inverse_real")][1:] + 1j * exact.arrays[(0, "inverse_imag")][1:],
        1 / h[1:],
        rtol=1e-10,
        atol=1e-15,
    )


def scalar_sos(values, sos):
    """Independent DF-II-transposed recurrence and constant-input equilibrium."""
    out = list(map(float, values))
    initial = out[0]
    for b0, b1, b2, a0, a1, a2 in sos:
        gain = (b0 + b1 + b2) / (a0 + a1 + a2)
        state1 = (gain - b0) * initial
        state2 = (b2 - a2 * gain) * initial
        result = []
        for x in out:
            y = b0 * x + state1
            state1 = b1 * x - a1 * y + state2
            state2 = b2 * x - a2 * y
            result.append(y)
        initial *= gain
        out = result
    return out


def test_scalar_biquad_odd_extension_oracle_and_short_rejection():
    y = np.array([math.sin(0.17 * n) + 0.2 * math.cos(0.71 * n) for n in range(200)])
    filtered, sos, pad = filter_products(y, 100, [2.0, 10.0], 4)
    extension = [2 * y[0] - v for v in y[pad:0:-1]] + list(y) + [2 * y[-1] - v for v in y[-2 : -pad - 2 : -1]]
    forward = scalar_sos(extension, sos)
    oracle = scalar_sos(list(reversed(forward)), sos)[::-1][pad:-pad]
    np.testing.assert_allclose(filtered, oracle, rtol=1e-9, atol=1e-9)
    rejected(lambda: filter_products(np.zeros(pad + 1), 100, [2.0, 10.0], 4), "waveform_contract")


def test_all_submitted_processing_knobs_have_array_or_candidate_effects():
    raw = source()
    base = process_waveform_record(raw, inventory(), request())
    for key, value, array in [
        ("taper_fraction", 0.1, "time_taper"),
        ("prefilter_hz", [0.5, 2.0, 20.0, 25.0], "prefilter_weight"),
        ("sta_s", 0.4, "characteristic"),
        ("lta_s", 3.0, "characteristic"),
        ("welch_segment_samples", 512, "filtered_psd"),
        ("filter_order", 2, "filtered_native"),
    ]:
        req = request()
        req["processing"][key] = value
        changed = process_waveform_record(raw, inventory(), req)
        assert changed.metadata["status"] == "computed"
        assert not np.array_equal(changed.arrays[(0, array)], base.arrays[(0, array)])
        assert changed.metadata["sources"]["miniseed"] == base.metadata["sources"]["miniseed"]
    ratio = np.array([0.0, 4.0, 2.0, 1.0, 4.0, 5.0, 2.0, 1.0, 4.0])
    normal = candidate_intervals(ratio, 0, 9, 3.0, 1.0, 0, 0, 100, 0)
    assert normal != candidate_intervals(ratio, 0, 9, 4.0, 1.0, 0, 0, 100, 0)
    assert normal != candidate_intervals(ratio, 0, 9, 3.0, 2.0, 0, 0, 100, 0)
    assert normal != candidate_intervals(ratio, 0, 9, 3.0, 1.0, 3, 0, 100, 0)


def test_eval_ties_ambiguity_residual_sign_no_reference_feedback_and_corruption():
    from waveform_evaluation import SealedWaveform

    out = process_waveform_record(source(), inventory(), request())
    # Authored explicit state-machine candidates; not measured/provider truth.
    local = copy.deepcopy(out.metadata)
    local["candidates"] = candidate_intervals(
        np.array([0.0, 4.0, 1.0]), 0, 3, 3.0, 1.0, 0, 0, 100, 1577836800000000 + 10000000
    )
    from waveform_processing import WaveformResult

    authored = WaveformResult(local, out.arrays)
    sealed = seal_result(authored)
    row = {
        "network": "XX",
        "station": "TEST",
        "location": "",
        "channel": "BHZ",
        "phase": "P",
        "pick_utc": "2020-01-01T00:00:10Z",
        "uncertainty_s": None,
        "analyst_status": "catalogue-unspecified",
        "source_record_id": "authored1",
    }
    refs = {
        "schema": "caos.waveform-analyst-references.v1",
        "event_id": "38457511",
        "source": {"raw_sha256": "1" * 64, "citation": "authored", "rights": "private-use-attested"},
        "selection_sealed_before_scoring": True,
        "references": [row],
    }
    eval_one = evaluate_waveform_candidates(sealed, json.dumps(refs).encode())
    assert eval_one["references"][0]["signed_residual_s"] == 0.01
    second = copy.deepcopy(row)
    second["phase"] = "S"
    second["source_record_id"] = "authored2"
    refs["references"].append(second)
    eval_two = evaluate_waveform_candidates(sealed, json.dumps(refs).encode())
    assert eval_two["reference_status_counts"] == {"matched": 1, "unmatched": 1}
    refs["references"].append(copy.deepcopy(row))
    ambiguous = evaluate_waveform_candidates(sealed, json.dumps(refs).encode())
    assert ambiguous["reference_status_counts"]["ambiguous"] == 2
    refs["references"].reverse()
    assert (
        evaluate_waveform_candidates(sealed, json.dumps(refs).encode())["reference_status_counts"]
        == ambiguous["reference_status_counts"]
    )
    assert seal_result(authored) == sealed
    rejected(
        lambda: evaluate_waveform_candidates(
            SealedWaveform(sealed.metadata_bytes + b" ", sealed.calculation_sha256), json.dumps(refs).encode()
        ),
        "waveform_contract",
    )


def test_response_unsupported_unitless_zero_gain_frequency_and_unstable_coefficients():
    for xml, expected in [
        (inventory().replace(b"<StageGain>", b"<StageGain><Frequency>0</Frequency>"), None),
        (
            inventory().replace(
                b"<StageGain><Value>1000</Value><Frequency>3</Frequency>",
                b"<StageGain><Value>1000</Value><Frequency>0</Frequency>",
            ),
            "response_chain_inconsistent",
        ),
        (
            inventory().replace(
                inventory()[
                    inventory().index(b"<PolesZeros>") : inventory().index(b"</PolesZeros>") + len(b"</PolesZeros>")
                ],
                b"",
            ),
            "response_units_missing",
        ),
        (digital_inventory(denominator=-1), "response_stage_unsupported"),
        (
            inventory(poles='<Pole number="0"><Real>-1</Real><Imaginary>1</Imaginary></Pole>'),
            "response_chain_inconsistent",
        ),
    ]:
        if expected is None:
            rejected(lambda: process_waveform_record(source(), xml, request()))
        else:
            out = process_waveform_record(source(), xml, request())
            assert out.metadata["status"] == "qc_only" and expected in out.metadata["qc"]["reasons"]


def test_sealing_rejects_non_native_array_hooks_and_corrupt_metadata():
    from waveform_processing import WaveformResult
    from waveform_evaluation import SealedWaveform

    out = process_waveform_record(source(), inventory(), request())
    calls = []

    class Hook:
        @property
        def dtype(self):
            calls.append("dtype")
            raise AssertionError("SECRET hook called")

    bad_arrays = dict(out.arrays)
    bad_arrays[(0, "counts")] = Hook()
    rejected(lambda: seal_result(WaveformResult(out.metadata, bad_arrays)), "waveform_type")
    assert calls == []
    for mutation in (
        lambda m: m.update(acceptance={}),
        lambda m: m.update(array_descriptors=None),
        lambda m: m.update(channels=None),
        lambda m: m.update(channels=m["channels"] * 2),
        lambda m: m.update(candidates="SECRET"),
        lambda m: m["request"].update(scientific_sha256="0" * 64),
    ):
        metadata = copy.deepcopy(out.metadata)
        mutation(metadata)
        rejected(lambda: seal_result(WaveformResult(metadata, out.arrays)), "waveform_contract")
        raw = json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        rejected(
            lambda: evaluate_waveform_candidates(SealedWaveform(raw, hashlib.sha256(raw).hexdigest()), b"{}"),
            "waveform_contract",
        )


def test_zero_matches_are_evaluated_not_missing_reference_truth():
    from waveform_processing import WaveformResult

    out = process_waveform_record(source(), inventory(), request())
    metadata = copy.deepcopy(out.metadata)
    metadata["candidates"] = []
    sealed = seal_result(WaveformResult(metadata, out.arrays))
    row = {
        "network": "XX",
        "station": "TEST",
        "location": "",
        "channel": "BHZ",
        "phase": "P",
        "pick_utc": "2020-01-01T00:00:10Z",
        "uncertainty_s": None,
        "analyst_status": "manual",
        "source_record_id": "authored",
    }
    refs = {
        "schema": "caos.waveform-analyst-references.v1",
        "event_id": "38457511",
        "source": {"raw_sha256": "1" * 64, "citation": "authored", "rights": "private-use-attested"},
        "selection_sealed_before_scoring": True,
        "references": [row],
    }
    evaluated = evaluate_waveform_candidates(sealed, json.dumps(refs).encode())
    assert evaluated["status"] == "evaluated"
    assert evaluated["reference_status_counts"] == {"unmatched": 1}
    assert evaluated["matched_reference_fraction"] == 0.0 and evaluated["median_absolute_residual_s"] is None
    refs["references"] = []
    assert evaluate_waveform_candidates(sealed, json.dumps(refs).encode())["status"] == "not_evaluable"


@pytest.mark.parametrize("flag", ["truncated_at_valid_start", "truncated_at_valid_end"])
def test_reference_matching_excludes_both_truncated_interval_variants(flag):
    from waveform_processing import WaveformResult

    out = process_waveform_record(source(), inventory(), request())
    metadata = copy.deepcopy(out.metadata)
    # Authored state-machine candidate, not a provider arrival. This checks the
    # exact approved 'nontruncated' matching policy, not detector performance.
    candidate = candidate_intervals(np.array([0.0, 4.0, 1.0]), 0, 3, 3.0, 1.0, 0, 0, 100, 1577836800000000 + 10000000)[
        0
    ]
    candidate[flag] = True
    metadata["candidates"] = [candidate]
    sealed = seal_result(WaveformResult(metadata, out.arrays))
    refs = {
        "schema": "caos.waveform-analyst-references.v1",
        "event_id": "38457511",
        "source": {"raw_sha256": "1" * 64, "citation": "authored", "rights": "private-use-attested"},
        "selection_sealed_before_scoring": True,
        "references": [
            {
                "network": "XX",
                "station": "TEST",
                "location": "",
                "channel": "BHZ",
                "phase": "P",
                "pick_utc": candidate["on_utc"],
                "uncertainty_s": None,
                "analyst_status": "catalogue-unspecified",
                "source_record_id": "authored",
            }
        ],
    }
    evaluated = evaluate_waveform_candidates(sealed, json.dumps(refs).encode())
    assert evaluated["reference_status_counts"] == {"unmatched": 1}
    assert evaluated["unmatched_candidate_count"] == 1
    assert evaluated["median_absolute_residual_s"] is None


def test_sealing_rejects_nonfinite_arrays_even_with_matching_digest():
    from waveform_processing import WaveformResult

    out = process_waveform_record(source(), inventory(), request())
    for value in (float("nan"), float("inf"), float("-inf")):
        metadata = copy.deepcopy(out.metadata)
        arrays = dict(out.arrays)
        bad = arrays[(0, "physical_native")].copy()
        bad[2000] = value
        bad.setflags(write=False)
        arrays[(0, "physical_native")] = bad
        descriptor = next(d for d in metadata["array_descriptors"] if d["name"] == "physical_native")
        descriptor["sha256"] = hashlib.sha256(memoryview(bad).cast("B")).hexdigest()
        rejected(lambda: seal_result(WaveformResult(metadata, arrays)), "waveform_contract")


def test_sealing_rejects_unregistered_arrays_and_qc_physical_products():
    from waveform_processing import WaveformResult

    out = process_waveform_record(source(), inventory(), request())
    renamed = copy.deepcopy(out.metadata)
    descriptor = next(d for d in renamed["array_descriptors"] if d["name"] == "physical_native")
    descriptor["name"] = "SECRET_unknown"
    arrays = dict(out.arrays)
    arrays[(0, "SECRET_unknown")] = arrays.pop((0, "physical_native"))
    rejected(lambda: seal_result(WaveformResult(renamed, arrays)), "waveform_contract")
    qc = copy.deepcopy(out.metadata)
    qc.update(status="qc_only", candidates=None)
    rejected(lambda: seal_result(WaveformResult(qc, out.arrays)), "waveform_contract")


def test_sealing_includes_metadata_bytes_in_total_output_bound():
    from waveform_processing import WaveformResult

    out = process_waveform_record(source(), inventory(), request())
    # Valid registered counts; owned/read-only finite allocation. Metadata makes
    # the aggregate cap overflow even though the array alone meets it exactly.
    counts = np.zeros(33554432 // 4, dtype="<i4")
    counts.setflags(write=False)
    metadata = copy.deepcopy(out.metadata)
    metadata.update(status="qc_only", candidates=None)
    metadata["array_descriptors"] = [
        {
            "channel_index": 0,
            "name": "counts",
            "dtype": "<i4",
            "shape": list(counts.shape),
            "unit": "counts",
            "bytes": counts.nbytes,
            "sha256": hashlib.sha256(memoryview(counts).cast("B")).hexdigest(),
        }
    ]
    rejected(lambda: seal_result(WaveformResult(metadata, {(0, "counts"): counts})), "waveform_contract")


def direct_dft(values):
    n = len(values)
    return np.array(
        [sum(float(values[j]) * cmath.exp(-2j * math.pi * k * j / n) for j in range(n)) for k in range(n // 2 + 1)]
    )


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
    for xml, reason in [
        (inventory(units="CM/S"), "response_units_missing"),
        (inventory(gain=-1), "response_chain_inconsistent"),
        (inventory(azimuth=360), "orientation_missing"),
    ]:
        out = process_waveform_record(source(), xml, request())
        assert out.metadata["status"] == "qc_only" and reason in out.metadata["qc"]["reasons"]


def test_independent_response_oracles_and_stabilization():
    result = process_waveform_record(source(), inventory(), request())
    np.testing.assert_allclose(result.arrays[(0, "response_real")], 1000, rtol=1e-10, atol=1e-9)
    np.testing.assert_allclose(result.arrays[(0, "response_imag")], 0, atol=1e-9)
    # Independent centred least squares + FULL direct DFT/IDFT at N=200.
    req = request()
    req["conditioning_end_utc"] = "2020-01-01T00:00:10Z"
    req["analysis_start_utc"] = "2020-01-01T00:00:02Z"
    req["analysis_end_utc"] = "2020-01-01T00:00:08Z"
    req["processing"].update(
        prefilter_hz=[0.5, 1.0, 4.0, 6.0],
        bandpass_hz=[1.0, 4.0],
        filter_order=2,
        edge_guard_s=0.0,
        lta_s=0.5,
        sta_s=0.1,
        welch_segment_samples=64,
    )
    values = [round(1000 * math.sin(2 * math.pi * 2 * n / 20) + 3 * n) for n in range(200)]
    small = process_waveform_record(
        record(values, rate=20), inventory().replace(b"<SampleRate>100", b"<SampleRate>20"), req
    )
    counts = np.array(values, dtype=float)
    tau = np.array([(n - (len(counts) - 1) / 2) / 20 for n in range(len(counts))])
    mean = sum(counts) / len(counts)
    slope = sum(tau[n] * (counts[n] - mean) for n in range(len(counts))) / sum(tau * tau)
    q = math.floor(len(counts) * 0.05 / 2 + 0.5)
    taper = np.array(
        [
            math.sin(math.pi * min(n, len(counts) - 1 - n) / (2 * q)) if min(n, len(counts) - 1 - n) <= q else 1
            for n in range(len(counts))
        ]
    )
    np.testing.assert_allclose(small.arrays[(0, "time_taper")], taper, rtol=1e-10, atol=1e-12)
    x = (counts - mean - slope * tau) * taper
    kfft = small.metadata["processing"]["channels"][0]["fft_samples"]
    assert kfft == 400
    transformed = direct_dft(np.concatenate([x, np.zeros(kfft - len(x))]))
    weights = []
    for k in range(kfft // 2 + 1):
        f = k * 20 / kfft
        weights.append(
            0.0
            if f <= 0.5 or f >= 6
            else 0.5 * (1 - math.cos(math.pi * (f - 0.5) / 0.5))
            if f < 1
            else 1.0
            if f <= 4
            else 0.5 * (1 + math.cos(math.pi * (f - 4) / 2))
        )
    positive = transformed * np.array(weights) / 1000
    full = list(positive) + [v.conjugate() for v in positive[-2:0:-1]]
    oracle = np.array(
        [(sum(full[k] * cmath.exp(2j * math.pi * k * n / kfft) for k in range(kfft)) / kfft).real for n in range(200)]
    )
    np.testing.assert_allclose(small.arrays[(0, "physical_native")], oracle, rtol=1e-10, atol=1e-12)


def test_sos_filter_oracle_edges_and_acausality():
    impulse = np.zeros(4000)
    impulse[2000] = 1
    out, sos, pad = filter_products(impulse, 100, [2.0, 10.0], 4)
    assert np.any(np.abs(out[1900:2000]) > 1e-8) and pad == 27
    f = 5.0
    z = cmath.exp(-2j * math.pi * f / 100)
    transfer = math.prod(
        abs((b0 + b1 * z + b2 * z * z) / (a0 + a1 * z + a2 * z * z)) ** 2 for b0, b1, b2, a0, a1, a2 in sos
    )
    sinusoid = np.sin(2 * math.pi * f * np.arange(4000) / 100)
    filtered, _, _ = filter_products(sinusoid, 100, [2.0, 10.0], 4)
    np.testing.assert_allclose(filtered[1500:2500], transfer * sinusoid[1500:2500], rtol=1e-9, atol=1e-9)


def test_welch_dft_parseval_and_units():
    y = np.array([math.sin(2 * math.pi * 7 * j / 64) + 0.3 for j in range(128)])
    freq, psd, diag = welch_products(y, 100, 64)
    v = np.array([0.5 - 0.5 * math.cos(2 * math.pi * j / 64) for j in range(64)])
    total = np.zeros(33)
    energies = []
    for start in (0, 32, 64):
        segment = y[start : start + 64] - sum(y[start : start + 64]) / 64
        transformed = direct_dft(segment * v)
        total += np.abs(transformed) ** 2
        energies.append(sum((segment * v) ** 2) / sum(v * v))
    total *= np.array([1] + [2] * 31 + [1]) / (3 * 100 * sum(v * v))
    np.testing.assert_allclose(psd, total, rtol=1e-10, atol=1e-12)
    assert abs(sum(psd) * (100 / 64) - sum(energies) / 3) < 1e-12
    assert diag["segments"] == 3 and diag["omitted_tail"] == 0
    assert freq[-1] == 50


def test_direct_stalta_onsets_and_no_phase_fabrication():
    y = np.array([math.sin(0.73 * j) * (1 if j < 150 else 20) for j in range(500)])
    cf, scale = compute_characteristic(y, 5, 50)
    z = y / scale
    expected = np.zeros(500)
    for j in range(49, 500):
        expected[j] = (sum(z[j - 4 : j + 1] ** 2) / 5) / max(sum(z[j - 49 : j + 1] ** 2) / 50, np.finfo(float).tiny)
    np.testing.assert_allclose(cf, expected, rtol=1e-9, atol=1e-9)
    exact = np.array([4.0, 3.0, 1.0, 4.0, 5.0, 5.0, 1.0, 4.0])
    rows = candidate_intervals(exact, 0, 8, 3.0, 1.0, 1, 0, 100, 0)
    assert [(r["on_index"], r["off_exclusive_index"], r["peak_index"]) for r in rows] == [
        (0, 2, 0),
        (3, 6, 4),
        (7, 8, 7),
    ]
    assert rows[0]["truncated_at_valid_start"] and rows[-1]["truncated_at_valid_end"]
    assert all(r["phase"] is None and r["timing_sigma_s"] is None for r in rows)


def test_actual_parameter_effects_and_reference_noninterference():
    raw = source()
    one = process_waveform_record(raw, inventory(), request())
    two = process_waveform_record(raw, inventory(gain=2000), request())
    np.testing.assert_allclose(
        two.arrays[(0, "physical_native")], one.arrays[(0, "physical_native")] / 2, rtol=1e-10, atol=1e-11
    )
    np.testing.assert_allclose(
        two.arrays[(0, "physical_psd")], one.arrays[(0, "physical_psd")] / 4, rtol=1e-10, atol=1e-12
    )
    assert one.metadata["sources"]["miniseed"] == two.metadata["sources"]["miniseed"]
    assert one.metadata["sources"]["stationxml"] != two.metadata["sources"]["stationxml"]
    modified = request()
    modified["processing"]["bandpass_hz"] = [6.0, 10.0]
    changed = process_waveform_record(raw, inventory(), modified)
    assert (
        np.std(changed.arrays[(0, "filtered_native")][800:3200])
        < np.std(one.arrays[(0, "filtered_native")][800:3200]) / 10
    )


def test_sealed_reference_conversion_matching_and_residuals():
    raw = b"# 38457511 le 2020/01/01,00:00:00.125 0 0 1 2 l 1\nXX TEST BHZ -- 0 0 0 P cu i 0.5 1 8.125\n"
    converted = references_from_stp(raw, "38457511", ("XX", "TEST", "", "BHZ"))
    assert converted["rows"][0]["pick_utc"] == "2020-01-01T00:00:08.250000Z"
    assert converted["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert converted["rows"][0]["uncertainty_s"] is None
    result = process_waveform_record(source(), inventory(), request())
    sealed = seal_result(result)
    refs = {
        "schema": "caos.waveform-analyst-references.v1",
        "event_id": "38457511",
        "source": {"raw_sha256": converted["raw_sha256"], "citation": "authored", "rights": "private-use-attested"},
        "selection_sealed_before_scoring": True,
        "references": [{k: row[k] for k in REFERENCE_KEYS} for row in converted["rows"]],
    }
    before = seal_result(result)
    evaluation = evaluate_waveform_candidates(sealed, json.dumps(refs).encode())
    assert seal_result(result) == before
    assert evaluation["schema"] == "caos.local-waveform-evaluation.v1"
    assert "phase_f1" not in evaluation and evaluation["field_truth"] is None


def authored_worked_report():
    """Actual same-count controls; no field observation or catalogue calibration."""
    values = [
        round(
            (10000 if 1200 <= n < 1300 or 2000 <= n < 2100 else 250) * math.sin(2 * math.pi * 3 * n / 100)
            + 50 * math.sin(2 * math.pi * 17 * n / 100)
        )
        for n in range(4000)
    ]
    raw = source(values)
    runs = []
    outputs = {}
    for name in ("base", "gain_double", "band_6_10", "threshold_on_5", "guard_9"):
        req = request()
        xml = inventory(gain=2000 if name == "gain_double" else 1000)
        if name == "band_6_10":
            req["processing"]["bandpass_hz"] = [6.0, 10.0]
        elif name == "threshold_on_5":
            req["processing"]["threshold_on"] = 5.0
        elif name == "guard_9":
            req["processing"]["edge_guard_s"] = 9.0
            req["analysis_start_utc"] = "2020-01-01T00:00:09Z"
            req["analysis_end_utc"] = "2020-01-01T00:00:31Z"
        out = process_waveform_record(raw, xml, req)
        assert out.metadata["status"] == "computed"
        outputs[name] = out
        diagnostic = out.metadata["processing"]["channels"][0]
        runs.append(
            {
                "name": name,
                "miniseed_sha256": out.metadata["sources"]["miniseed"]["raw_sha256"],
                "stationxml_sha256": out.metadata["sources"]["stationxml"]["raw_sha256"],
                "scientific_sha256": out.metadata["request"]["scientific_sha256"],
                "calculation_sha256": seal_result(out).calculation_sha256,
                "processing": req["processing"],
                "native_unit": "m/s",
                "analysis_slice": diagnostic["analysis_slice"],
                "guard_samples": diagnostic["effective_guard_samples"],
                "psd_integrals": diagnostic["psd_integrals"],
                "operator_tail_energy_fraction": diagnostic["operator_tail_energy_fraction"],
                "candidates": out.metadata["candidates"],
                "array_sha256": {d["name"]: d["sha256"] for d in out.metadata["array_descriptors"]},
            }
        )
    base, double = outputs["base"], outputs["gain_double"]
    np.testing.assert_allclose(
        double.arrays[(0, "physical_native")], base.arrays[(0, "physical_native")] / 2, rtol=1e-10, atol=1e-12
    )
    np.testing.assert_allclose(
        double.arrays[(0, "physical_psd")], base.arrays[(0, "physical_psd")] / 4, rtol=1e-10, atol=1e-12
    )
    assert base.metadata["candidates"] != outputs["threshold_on_5"].metadata["candidates"]
    assert not np.array_equal(base.arrays[(0, "filtered_native")], outputs["band_6_10"].arrays[(0, "filtered_native")])
    assert not np.array_equal(base.arrays[(0, "edge_valid")], outputs["guard_9"].arrays[(0, "edge_valid")])
    return {
        "schema": "caos.m08-authored-worked.v1",
        "source": "Authored integer-count amplitude bursts, not field data",
        "samples": 4000,
        "fs_hz": 100,
        "authored_burst_indices": [[1200, 1300], [2000, 2100]],
        "burst_indices_are_phase_labels": False,
        "same_count_bytes": True,
        "runs": runs,
        "field_truth": None,
        "method_accepted": False,
        "host_admitted": False,
    }


def test_worked_same_input_response_filter_and_threshold_effects():
    worked = authored_worked_report()
    assert len({r["miniseed_sha256"] for r in worked["runs"]}) == 1
    assert all(c["phase"] is None and c["timing_sigma_s"] is None for row in worked["runs"] for c in row["candidates"])


def test_authored_worked_artifact_matches_actual_local_calculation():
    assert (
        json.loads((ROOT / "data/derived/waveform/m08-authored-worked.json").read_bytes()) == authored_worked_report()
    )
