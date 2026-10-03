"""Actual bounded local M08 science; no acquisition, filesystem, CLI or host lane.

This ordinary function is NOT native isolation. Malformed-native execution and
resource supervision require their separately approved owner and remain held.
"""

from dataclasses import dataclass
import io
import math
import platform
import warnings

from waveform_input import (
    REASONS,
    exact_bytes,
    validate_request,
    scientific_identity,
    sha,
    utc_us,
    format_utc,
    nslc,
    scan_miniseed,
    scan_stationxml,
    resolve_channel,
    response_work,
    clone_native,
    native_precount,
    fail,
)


@dataclass(frozen=True)
class WaveformResult:
    metadata: dict
    arrays: dict


class WaveformCalculationError(RuntimeError):
    """Fixed terminal calculation outcome, never a successfully empty result."""

    def __init__(self, status, reason):
        self.status, self.reason = status, reason
        super().__init__("Waveform calculation did not complete")


def _engine_modules():
    modules = None
    try:
        import numpy
        import scipy
        import obspy

        if (numpy.__version__, scipy.__version__, obspy.__version__) == ("2.2.6", "1.15.2", "1.4.2"):
            modules = numpy, scipy, obspy
    except (ImportError, OSError, AttributeError):
        pass
    if modules is None:
        fail("waveform_engine")
    return modules


def _decode_record(raw, row):
    _, _, obspy = _engine_modules()
    trace = None
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            stream = obspy.read(
                io.BytesIO(raw[row["byte_offset"] : row["byte_offset"] + row["byte_length"]]), format="MSEED"
            )
        if not caught and len(stream) == 1:
            trace = stream[0]
    except (ValueError, TypeError, OSError, RuntimeError):
        pass
    if trace is None:
        fail("waveform_decode")
    identity = tuple(trace.stats[k] for k in ("network", "station", "location", "channel"))
    data = trace.data
    if (
        identity != tuple(row["nslc"])
        or trace.stats.npts != row["npts"]
        or data.ndim != 1
        or data.dtype.kind != "i"
        or data.dtype.itemsize not in (2, 4)
        or trace.stats.sampling_rate != row["sample_rate_hz"]
        or trace.stats.starttime.ns != row["start_us"] * 1000
    ):
        fail("waveform_decode")
    if row["encoding"] in (10, 11) and (int(data[0]) != row["steim_x0"] or int(data[-1]) != row["steim_xn"]):
        fail("waveform_decode")
    return data


def _read_inventory(raw):
    _, _, obspy = _engine_modules()
    inventory = None
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            inventory = obspy.read_inventory(io.BytesIO(raw), format="STATIONXML")
        if caught:
            inventory = None
    except (ValueError, TypeError, OSError, RuntimeError):
        pass
    return inventory


def _fft_size(n):
    # Source-pinned preallocation equivalent; checked against actual _npts2nfft.
    k = 2 * (n + (n & 1))

    def good(v):
        divisor = 2
        largest = 1
        while divisor * divisor <= v:
            while v % divisor == 0:
                largest = divisor
                v //= divisor
            divisor += 1
        return max(largest, v) < 500

    if k > 5000 and not good(k):
        for i in range(1, 11):
            if good(k + 2 * i):
                return k + 2 * i
        return 1 << (k - 1).bit_length()
    return k


def _finite(array):
    np, _, _ = _engine_modules()
    if not np.isfinite(array).all():
        raise WaveformCalculationError("failed", "numerical_failed")


def filter_products(values, fs, band, order):
    from scipy.signal import butter, sosfiltfilt

    sos = butter(order, band, btype="bandpass", fs=fs, output="sos")
    pad = 3 * (2 * len(sos) + 1 - min(int((sos[:, 2] == 0).sum()), int((sos[:, 5] == 0).sum())))
    if len(values) <= pad + 1:
        fail("waveform_contract", "processing")
    filtered = sosfiltfilt(sos, values, padtype="odd", padlen=pad)
    _finite(filtered)
    return filtered, sos, pad


def welch_products(values, fs, m):
    np, _, _ = _engine_modules()
    from scipy.signal import welch

    if type(m) is not int or m < 64 or m > 8192 or m & (m - 1) or len(values) < m:
        fail("waveform_contract", "processing")
    window = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(m) / m)
    frequency, psd = welch(
        values,
        fs=fs,
        window=window,
        nperseg=m,
        noverlap=m // 2,
        nfft=m,
        detrend="constant",
        return_onesided=True,
        scaling="density",
        average="mean",
    )
    _finite(psd)
    if (psd < 0).any():
        raise WaveformCalculationError("failed", "numerical_failed")
    segments = 1 + (len(values) - m) // (m // 2)
    return (
        frequency,
        psd,
        {
            "segments": segments,
            "omitted_tail": len(values) - (m + (segments - 1) * (m // 2)),
            "window_sum_squares": float(sum(window * window)),
            "delta_hz": fs / m,
            "integral": float(sum(psd) * fs / m),
            "rms": math.sqrt(float(sum(psd) * fs / m)),
        },
    )


def compute_characteristic(values, s, l):
    np, _, _ = _engine_modules()
    from obspy.signal.trigger import classic_sta_lta_py

    if type(s) is not int or type(l) is not int or not 2 <= s < l or len(values) < 3 * l:
        fail("waveform_contract", "processing")
    _finite(values)
    scale = float(np.max(np.abs(values)))
    if scale == 0:
        return np.zeros(len(values)), scale
    characteristic = classic_sta_lta_py(values / scale, s, l)
    _finite(characteristic)
    if (characteristic < 0).any():
        raise WaveformCalculationError("failed", "numerical_failed")
    return characteristic, scale


def candidate_intervals(cf, i0, i1, on, off, refractory, channel_index, fs, start_us):
    rows = []
    active = None
    ready = i0

    def emit(last, truncated):
        nonlocal active, ready
        first, peak = active
        rows.append(
            {
                "channel_index": channel_index,
                "on_index": first,
                "off_exclusive_index": last,
                "peak_index": peak,
                "peak_ratio": float(cf[peak]),
                "on_utc": format_utc(start_us + first * (1000000 // fs)),
                "on_relative_s": first / fs,
                "truncated_at_valid_start": first == i0,
                "truncated_at_valid_end": truncated,
                "phase": None,
                "timing_sigma_s": None,
            }
        )
        if len(rows) > 4096:
            raise WaveformCalculationError("resource_exceeded", "candidate_limit")
        active = None
        ready = last + refractory

    for i in range(i0, i1):
        if active is None:
            if i >= ready and cf[i] > on:
                active = (i, i)
        elif cf[i] <= off:
            emit(i, False)
        elif cf[i] > cf[active[1]]:
            active = (active[0], i)
    if active is not None:
        emit(i1, True)
    return rows


def _base(raw, xml, request):
    unknown = {
        "sha256": None,
        "reason": "External execution receipt required; ordinary helper has no filesystem access",
    }
    return {
        "schema": "caos.local-waveform-result.v1",
        "method": "seismic.waveform-qc-classical/v1",
        "status": "qc_only",
        "sources": {
            "miniseed": {"raw_bytes": len(raw), "raw_sha256": sha(raw), "declaration": clone_native(request["source"])},
            "stationxml": {
                "raw_bytes": len(xml),
                "raw_sha256": sha(xml),
                "declaration": "user-supplied-instrument-metadata",
            },
        },
        "request": {
            "submitted": request,
            "scientific_sha256": scientific_identity(request),
            "original_json_bytes": None,
            "original_json_sha256": None,
        },
        "engines": {
            "cpython": platform.python_version(),
            "numpy": None,
            "scipy": None,
            "obspy": None,
            "libmseed": dict(unknown),
            "evalresp": dict(unknown),
            "source_modules": dict(unknown),
        },
        "channels": [],
        "processing": {"submitted": request["processing"], "channels": [], "response_work_units": 0},
        "qc": {"reasons": [], "warnings": [], "channels": []},
        "candidates": None,
        "acceptance": {k: False for k in ("field_eligible", "method_accepted", "host_admitted", "provider_verified")},
        "field_truth": None,
        "array_descriptors": [],
    }


def _descriptors(metadata, arrays, units):
    np, _, _ = _engine_modules()
    total = 0
    for (ci, name), array in sorted(arrays.items()):
        kind = "<i4" if name == "counts" else "|b1" if name == "edge_valid" else "<f8"
        # Reject overflow before constructing the returned owned copy.
        projected = array.size * np.dtype(kind).itemsize
        if total + projected > 33554432:
            raise WaveformCalculationError("resource_exceeded", "output_limit")
        _finite(array)
        owned = np.array(array, dtype=kind, order="C", copy=True)
        owned.setflags(write=False)
        arrays[(ci, name)] = owned
        total += owned.nbytes
        metadata["array_descriptors"].append(
            {
                "channel_index": ci,
                "name": name,
                "dtype": kind,
                "shape": list(owned.shape),
                "unit": units[(ci, name)],
                "bytes": owned.nbytes,
                "sha256": sha(memoryview(owned).cast("B")),
            }
        )
    # Metadata pre-count precedes copying/serialization; stream hashes are separate.
    length = native_precount(metadata, 2097152, max_nodes=2097152, max_depth=16)
    if total + length > 33554432:
        raise WaveformCalculationError("resource_exceeded", "output_limit")
    return WaveformResult(metadata, arrays)


def _qc_finalize(metadata, arrays, units, reasons, warnings_by_channel):
    metadata["qc"]["reasons"] = [r for r in REASONS if r in reasons]
    metadata["qc"]["warnings"] = [
        r
        for r in ("adc_rails_unknown", "clock_accuracy_unknown", "datum_unknown", "zero_filtered_signal")
        if r in warnings_by_channel
    ]
    for channel in metadata["qc"]["channels"]:
        channel["reasons"] = [r for r in REASONS if r in channel["reasons"]]
    metadata["status"] = "qc_only" if reasons else "computed"
    if reasons:
        # Station-level QC: no partially successful station physical products.
        arrays = {k: v for k, v in arrays.items() if k[1] == "counts"}
        units = {k: v for k, v in units.items() if k[1] == "counts"}
        metadata["processing"]["channels"] = []
        metadata["candidates"] = None
    else:
        metadata["candidates"] = metadata["candidates"] or []
    return _descriptors(metadata, arrays, units)


def process_waveform_record(raw_mseed, raw_stationxml, request):
    """Exactly supplied bytes -> actual conditional local science or retained QC.

    Does not establish provider authenticity/native containment/field truth/admission.
    Every global input limit is checked before native allocation, including outside
    the conditioning slice. No input path is opened or mutable source reopened.
    """
    exact_bytes(raw_mseed, 16777216)
    exact_bytes(raw_stationxml, 2097152)
    submitted = validate_request(request)
    records = scan_miniseed(raw_mseed, submitted)
    dto = scan_stationxml(raw_stationxml)
    declared = submitted["source"]["declared_sha256"]
    if declared is not None and declared != sha(raw_mseed):
        fail("waveform_contract", "source")
    metadata = _base(raw_mseed, raw_stationxml, submitted)
    if submitted["source"]["rights"] in ("unknown", "forbidden"):
        metadata["qc"]["reasons"] = ["rights_ineligible"]
        # No scientific import, decode or inventory construction.
        return WaveformResult(metadata, {})
    t0, t1, a0, a1 = [
        utc_us(submitted[k])
        for k in ("conditioning_start_utc", "conditioning_end_utc", "analysis_start_utc", "analysis_end_utc")
    ]
    p = submitted["processing"]
    arrays, units, reasons, warnings_all, plans = {}, {}, [], [], []
    rates = set(r["sample_rate_hz"] for r in records)
    if len(rates) > 1:
        reasons.append("rate_mismatch")
    for ci, identity_row in enumerate(submitted["channels"]):
        identity = nslc(identity_row)
        rows = sorted((r for r in records if r["channel_index"] == ci), key=lambda r: (r["start_us"], r["byte_offset"]))
        channel = {
            "channel_index": ci,
            "nslc": list(identity),
            "records": rows,
            "absolute_timing_verified": False,
            "clock_flags_consistent": bool(rows) and all(bool(r["io_clock_flags"] & 32) for r in rows),
            "datum": "unknown",
            "adc_rails": submitted["adc_rails"][ci],
            "native_unit": None,
            "projection_enu": None,
            "response_epoch": None,
        }
        metadata["channels"].append(channel)
        local = []
        warnings_local = ["clock_accuracy_unknown", "datum_unknown"]
        if submitted["adc_rails"][ci] is None:
            warnings_local.append("adc_rails_unknown")
        if not rows:
            local.append("missing_channel")
            reasons += local
            metadata["qc"]["channels"].append({"channel_index": ci, "reasons": local, "warnings": warnings_local})
            warnings_all += warnings_local
            continue
        fs = rows[0]["sample_rate_hz"]
        step = 1000000 // fs
        if any((x - t0) % step for x in (t1, a0, a1)):
            fail("waveform_contract", "request")
        n = (t1 - t0) // step
        s = math.ceil(p["sta_s"] * fs)
        l = math.ceil(p["lta_s"] * fs)
        if n < 3 * l or not 2 <= s < l or p["prefilter_hz"][-1] >= fs / 2 or p["bandpass_hz"][-1] >= 0.45 * fs:
            fail("waveform_contract", "processing")
        k = _fft_size(n)
        if k > 131072:
            fail("waveform_limit")
        q = math.floor(n * p["taper_fraction"] / 2 + 0.5)
        # Bandpass butter has J=prototype order and no zeros at origin for this lane.
        pad = 3 * (2 * p["filter_order"] + 1)
        guard = max(q, math.ceil(2 * fs / p["prefilter_hz"][1]), l + pad, math.ceil(p["edge_guard_s"] * fs))
        analysis = ((a0 - t0) // step, (a1 - t0) // step)
        if (
            not guard <= analysis[0] < analysis[1] <= n - guard
            or p["welch_segment_samples"] > analysis[1] - analysis[0]
        ):
            fail("waveform_contract", "processing")
        corners = p["prefilter_hz"]
        bins = [
            sum(
                1
                for index in range(k // 2 + 1)
                if (low < index * fs / k < high if j != 1 else low <= index * fs / k <= high)
            )
            for j, (low, high) in enumerate(zip(corners, corners[1:]))
        ]
        if min(bins) < 3:
            fail("waveform_contract", "processing")
        for left, right in zip(rows, rows[1:]):
            if left["sample_rate_hz"] != right["sample_rate_hz"]:
                local.append("rate_mismatch")
            if right["start_us"] > left["end_exclusive_us"]:
                local.append("gap")
            if right["start_us"] < left["end_exclusive_us"]:
                local.append("overlap")
        if (t0 - rows[0]["start_us"]) % step or rows[0]["start_us"] > t0 or rows[-1]["end_exclusive_us"] < t1:
            local.append("gap")
        selected, xml_reasons = resolve_channel(dto, identity, t0, t1, fs)
        local += xml_reasons
        if selected is not None:
            channel.update(
                native_unit=selected.get("native_unit"),
                projection_enu=selected.get("projection_enu"),
                response_epoch={
                    "network": selected["network"],
                    "station": selected["station"],
                    "channel_start": selected["start"],
                    "channel_end": selected["end"],
                },
                source_orientation={
                    k: selected["values"].get(k)
                    for k in ("Azimuth", "Dip", "Latitude", "Longitude", "Elevation", "Depth")
                },
                response_stage_numbers=[s["number"] for s in selected["response"]["stages"]]
                if selected["response"]
                else [],
                original_unit_literals=[dict(s["units"]) for s in selected["response"]["stages"]]
                if selected["response"]
                else [],
            )
        if selected and not xml_reasons:
            metadata["processing"]["response_work_units"] += response_work(selected["response"]["stages"], k)
        if metadata["processing"]["response_work_units"] > 20000000:
            fail("waveform_limit")
        channel.update(sample_rate_hz=fs, start_us=rows[0]["start_us"], npts=sum(r["npts"] for r in rows))
        plans.append((ci, rows, selected, local, n, fs, k, q, pad, guard, s, l, analysis, bins))
        metadata["qc"]["channels"].append(
            {
                "channel_index": ci,
                "reasons": local,
                "warnings": warnings_local,
                "outside_conditioning_blocking_flags": [],
                "clipping_status": "unknown",
            }
        )
        warnings_all += warnings_local
        reasons += local
    np, scipy, obspy = _engine_modules()
    metadata["engines"].update(numpy=np.__version__, scipy=scipy.__version__, obspy=obspy.__version__)
    for ci, rows, selected, local, n, fs, k, q, pad, guard, s, l, analysis, bins in plans:
        counts = np.empty(sum(r["npts"] for r in rows), dtype="<i4")
        cursor = 0
        for row in rows:
            data = _decode_record(raw_mseed, row)
            counts[cursor : cursor + row["npts"]] = data
            row["sample_interval"] = {"start": cursor, "stop": cursor + row["npts"]}
            cursor += row["npts"]
        arrays[(ci, "counts")] = counts
        units[(ci, "counts")] = "counts"
        diag = metadata["qc"]["channels"][ci]
        contributing = [r for r in rows if r["start_us"] < t1 and r["end_exclusive_us"] > t0]

        def blocking(r):
            return bool(r["activity_flags"] & 49 or r["io_clock_flags"] & 7 or r["data_quality_flags"])

        diag["outside_conditioning_blocking_flags"] = [
            r["byte_offset"] for r in rows if r not in contributing and blocking(r)
        ]
        if any(blocking(r) for r in contributing):
            local.append("blocking_flags")
        if any(r["data_quality_flags"] & 3 for r in contributing):
            local.append("clip_detected")
        # Discontinuities remain explicit, so there is no fictitious uniform conditioning slice.
        if any(r in local for r in ("gap", "overlap", "rate_mismatch")):
            reasons += local
            continue
        lo = (t0 - rows[0]["start_us"]) // (1000000 // fs)
        hi = lo + n
        if not 0 <= lo < hi <= len(counts):
            local.append("gap")
            reasons += local
            continue
        x = counts[lo:hi]
        diag["conditioning_slice"] = {"start": lo, "stop": hi}
        minimum, maximum = int(x.min()), int(x.max())
        if minimum == maximum:
            local.append("flat")
        extreme = (x == minimum) | (x == maximum)
        plateau = bool(np.any(extreme[:-2] & extreme[1:-1] & extreme[2:] & (x[:-2] == x[1:-1]) & (x[1:-1] == x[2:])))
        if plateau:
            local.append("clip_suspected")
        rail = submitted["adc_rails"][ci]
        if rail is not None and (minimum <= rail["minimum_count"] or maximum >= rail["maximum_count"]):
            local.append("clip_detected")
        diag.update(
            minimum_count=minimum,
            maximum_count=maximum,
            mean_count=float(np.mean(x, dtype=float)),
            rms_count=float(np.sqrt(np.mean(x.astype(float) ** 2))),
            clipping_status="detected"
            if "clip_detected" in local
            else "suspected"
            if plateau
            else "unknown"
            if rail is None
            else "not_detected",
        )
        reasons += local
    if reasons:
        return _qc_finalize(metadata, arrays, units, reasons, warnings_all)
    inv = _read_inventory(raw_stationxml)
    if inv is None:
        return _qc_finalize(metadata, arrays, units, ["response_warning"], warnings_all)
    responses = []
    for ci, rows, selected, local, n, fs, k, q, pad, guard, s, l, analysis, bins in plans:
        found = [
            c
            for net in inv
            for sta in net
            for c in sta
            if (net.code, sta.code, c.location_code, c.code) == nslc(submitted["channels"][ci])
            and c.start_date is not None
            and c.start_date.ns == _epoch_native_ns(selected["start"])
        ]
        if len(found) != 1 or found[0].response is None:
            fail("waveform_decode")
        responses.append(found[0].response)
    metadata["candidates"] = []
    for plan, response in zip(plans, responses):
        ci, rows, selected, local, n, fs, k, q, pad, guard, s, l, analysis, bins = plan
        from scipy.signal import detrend, sosfreqz
        from obspy.signal.invsim import cosine_taper, cosine_sac_taper
        from obspy.signal.util import _npts2nfft

        if _npts2nfft(n) != k:
            fail("waveform_engine")
        slice_start = (t0 - rows[0]["start_us"]) // (1000000 // fs)
        original = arrays[(ci, "counts")][slice_start : slice_start + n].astype(float)
        tau = (np.arange(n) - (n - 1) / 2) / fs
        mean = float(np.mean(original))
        slope = float(np.sum(tau * (original - mean)) / np.sum(tau * tau))
        conditioned = detrend(original, type="linear")
        taper = cosine_taper(n, p["taper_fraction"], sactaper=True, halfcosine=False)
        code = {"m": "DISP", "m/s": "VEL", "m/s2": "ACC"}[selected["native_unit"]]
        response_values = None
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                h, f = response.get_evalresp_response(1 / fs, k, output=code)
                test_h = response.get_evalresp_response_for_frequencies(
                    [selected["response"]["sensitivity"]["Frequency"]], output=code
                )
            if not caught:
                response_values = h, f, test_h
        except (ValueError, TypeError, OSError, RuntimeError):
            pass
        if response_values is None:
            local.append("response_warning")
            reasons += local
            continue
        h, f, test_h = response_values
        if not np.isfinite(h).all() or not np.isfinite(test_h).all():
            local.append("response_chain_inconsistent")
            reasons += local
            continue
        sensitivity = selected["response"]["sensitivity"]["Value"]
        mismatch = float(abs(abs(test_h[0]) - sensitivity) / sensitivity)
        if mismatch > 0.05:
            local.append("response_sensitivity_inconsistent")
            reasons += local
            continue
        weight = cosine_sac_taper(f, p["prefilter_hz"])
        magnitude = np.abs(h)
        support = weight > 0
        if np.any(magnitude[support] == 0):
            local.append("response_zero_support")
            reasons += local
            continue
        floor = None
        inverse = np.zeros(h.shape, dtype=complex)
        level = p["water_level_db"]
        if level is None:
            if np.any(magnitude[1:] == 0):
                local.append("response_inverse_undefined")
                reasons += local
                continue
            inverse[1:] = 1 / h[1:]
            if not np.isfinite(inverse).all():
                local.append("response_inverse_undefined")
                reasons += local
                continue
        else:
            floor = float(magnitude.max() * 10 ** (-level / 20))
            nonzero = magnitude > 0
            inverse[nonzero] = np.conjugate(h[nonzero]) / magnitude[nonzero] / np.maximum(magnitude[nonzero], floor)
        physical = None
        try:
            private = obspy.Trace(conditioned.copy())
            private.stats.sampling_rate = fs
            private.stats.response = response
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                private.remove_response(
                    output=code,
                    pre_filt=p["prefilter_hz"],
                    water_level=level,
                    zero_mean=False,
                    taper=True,
                    taper_fraction=p["taper_fraction"],
                )
            if not caught:
                physical = private.data
        except (ValueError, TypeError, OSError, RuntimeError):
            pass
        if physical is None:
            local.append("response_warning")
            reasons += local
            continue
        _finite(physical)
        audited = np.fft.irfft(np.fft.rfft(conditioned * taper, n=k) * weight * inverse, n=k)[:n]
        scale = float(np.max(np.abs(physical)))
        if not np.allclose(physical, audited, rtol=1e-10, atol=1e-12 * scale):
            raise WaveformCalculationError("failed", "numerical_failed")
        filtered, sos, actual_pad = filter_products(physical, fs, p["bandpass_hz"], p["filter_order"])
        if actual_pad != pad:
            fail("waveform_engine")
        characteristic, cf_scale = compute_characteristic(filtered, s, l)
        if cf_scale == 0:
            warnings_all.append("zero_filtered_signal")
        refr = math.ceil(p["refractory_s"] * fs)
        candidates = candidate_intervals(
            characteristic, *analysis, p["threshold_on"], p["threshold_off"], refr, ci, fs, t0
        )
        metadata["candidates"] += candidates
        if len(metadata["candidates"]) > 4096:
            raise WaveformCalculationError("resource_exceeded", "candidate_limit")
        products = {"counts": original, "physical": physical, "filtered": filtered}
        psds = {}
        stats = {}
        for name, value in products.items():
            psd_f, psds[name], stats[name] = welch_products(
                value[analysis[0] : analysis[1]], fs, p["welch_segment_samples"]
            )
        mask = np.zeros(n, dtype=bool)
        mask[guard : n - guard] = True
        _, b = sosfreqz(sos, worN=f, fs=fs)
        impulse = np.fft.irfft(weight * inverse * np.abs(b) ** 2, n=k)
        lag = np.minimum(np.arange(k), k - np.arange(k))
        energy = float(sum(impulse * impulse))
        tail = float(sum(impulse[lag > guard] ** 2) / energy) if energy else 0.0
        emitted = {
            "physical_native": physical,
            "filtered_native": filtered,
            "edge_valid": mask,
            "time_taper": taper,
            "response_frequency_hz": f,
            "response_real": h.real,
            "response_imag": h.imag,
            "inverse_real": inverse.real,
            "inverse_imag": inverse.imag,
            "prefilter_weight": weight,
            "characteristic": characteristic,
            "psd_frequency_hz": psd_f,
            "counts_psd": psds["counts"],
            "physical_psd": psds["physical"],
            "filtered_psd": psds["filtered"],
            "filter_sos": sos,
        }
        unit = selected["native_unit"]
        for name, value in emitted.items():
            arrays[(ci, name)] = value
            units[(ci, name)] = (
                unit
                if name in ("physical_native", "filtered_native")
                else "Hz"
                if name.endswith("frequency_hz")
                else "counts/" + unit
                if name in ("response_real", "response_imag")
                else unit + "/counts"
                if name in ("inverse_real", "inverse_imag")
                else "counts2/Hz"
                if name == "counts_psd"
                else "(" + unit + ")2/Hz"
                if name in ("physical_psd", "filtered_psd")
                else "dimensionless"
            )
        metadata["processing"]["channels"].append(
            {
                "channel_index": ci,
                "conditioning_slice": {"start": slice_start, "stop": slice_start + n},
                "analysis_slice": {"start": analysis[0], "stop": analysis[1]},
                "detrend_mean_counts": mean,
                "detrend_slope_counts_per_s": slope,
                "taper_end_samples": q,
                "fft_samples": k,
                "prefilter_bin_counts": bins,
                "water_level_amplitude": floor,
                "response_sensitivity_mismatch": mismatch,
                "water_level_active_bins": int(((magnitude > 0) & (magnitude < floor)).sum())
                if floor is not None
                else 0,
                "filter_pad_samples": pad,
                "effective_guard_samples": guard,
                "operator_tail_energy_fraction": tail,
                "sta_samples": s,
                "lta_samples": l,
                "refractory_samples": refr,
                "cf_scale": cf_scale,
                "welch_segments": stats["counts"]["segments"],
                "welch_omitted_tail": stats["counts"]["omitted_tail"],
                "welch_window_sum_squares": stats["counts"]["window_sum_squares"],
                "psd_delta_hz": fs / p["welch_segment_samples"],
                "psd_integrals": {key: stats[key]["integral"] for key in products},
                "psd_rms": {key: stats[key]["rms"] for key in products},
            }
        )
    return _qc_finalize(metadata, arrays, units, reasons, warnings_all)


def _epoch_native_ns(value):
    from datetime import datetime, timezone

    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    delta = parsed.astimezone(timezone.utc) - epoch
    return ((delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds) * 1000
