"""Separate sealed unlabelled onset evaluation. No file/network or picker inputs.

Analyst P/S tags are reference labels only. This is not phase F1, calibration,
field truth, source authentication or a posterior uncertainty estimator.
"""

from collections import Counter
from dataclasses import dataclass
import json
import math
import re
from statistics import median

from waveform_input import (
    exact_bytes,
    bounded_json,
    native_precount,
    clone_native,
    sha,
    fail,
    keys,
    nslc,
    utc_us,
    format_utc,
    DECIMAL,
    finite_number,
    validate_request,
    scientific_identity,
)
from waveform_processing import WaveformResult


REFERENCE_KEYS = (
    "network",
    "station",
    "location",
    "channel",
    "phase",
    "pick_utc",
    "uncertainty_s",
    "analyst_status",
    "source_record_id",
)

ARRAY_NAMES = frozenset(
    (
        "counts",
        "physical_native",
        "filtered_native",
        "edge_valid",
        "time_taper",
        "response_frequency_hz",
        "response_real",
        "response_imag",
        "inverse_real",
        "inverse_imag",
        "prefilter_weight",
        "characteristic",
        "psd_frequency_hz",
        "counts_psd",
        "physical_psd",
        "filtered_psd",
        "filter_sos",
    )
)


@dataclass(frozen=True)
class SealedWaveform:
    metadata_bytes: bytes
    calculation_sha256: str


def _unit_ledger(channel):
    if "response_unit_ledger" not in channel:
        return
    ledger = channel["response_unit_ledger"]
    numbers, originals = channel.get("response_stage_numbers"), channel.get("original_unit_literals")
    if (
        type(ledger) is not list
        or not 1 <= len(ledger) <= 32
        or type(numbers) is not list
        or type(originals) is not list
        or len(ledger) != len(numbers)
        or len(ledger) != len(originals)
        or any(type(o) is not dict or set(o) - {"InputUnits", "OutputUnits"} for o in originals)
        or any(type(n) is not int or not 1 <= n <= 32 for n in numbers)
    ):
        fail("waveform_contract")
    inferred = 0
    for i, item in enumerate(ledger):
        keys(
            item,
            "stage_number original_input_unit original_output_unit effective_input_unit effective_output_unit derivation neighbour_stage_numbers",
        )
        if (
            type(item["stage_number"]) is not int
            or type(numbers[i]) is not int
            or item["stage_number"] != numbers[i]
            or not 1 <= numbers[i] <= 32
            or type(originals[i]) is not dict
            or set(originals[i]) - {"InputUnits", "OutputUnits"}
            or type(item["neighbour_stage_numbers"]) is not list
            or any(type(n) is not int for n in item["neighbour_stage_numbers"])
        ):
            fail("waveform_contract")
        for suffix, literal in (("input_unit", "InputUnits"), ("output_unit", "OutputUnits")):
            if item["original_" + suffix] != originals[i].get(literal):
                fail("waveform_contract")
            for prefix in ("original_", "effective_"):
                value = item[prefix + suffix]
                if value is not None and (type(value) is not str or not 0 < len(value) <= 128):
                    fail("waveform_contract")
        derivation = item["derivation"]
        if derivation in ("provider-declared", "unresolved"):
            if item["neighbour_stage_numbers"] or any(
                item["original_" + s] != item["effective_" + s] for s in ("input_unit", "output_unit")
            ):
                fail("waveform_contract")
        elif derivation == "transparent-unity-gain-between-equal-declared-units":
            inferred += 1
            if (
                not 0 < i < len(ledger) - 1
                or originals[i]
                or item["neighbour_stage_numbers"] != [numbers[i - 1], numbers[i + 1]]
                or item["effective_input_unit"] is None
                or item["effective_output_unit"] is None
                or item["effective_input_unit"] != originals[i - 1].get("OutputUnits")
                or item["effective_output_unit"] != originals[i + 1].get("InputUnits")
                or item["effective_input_unit"].upper() != item["effective_output_unit"].upper()
            ):
                fail("waveform_contract")
        else:
            fail("waveform_contract")
    if inferred > 1:
        fail("waveform_contract")


def _sealed_metadata(m):
    """Bounded typed seal, not evidence that a caller-authored result is field truth."""
    native_precount(m, 2097152, max_nodes=2097152, max_depth=16)
    keys(
        m,
        "schema method status sources request engines channels processing qc candidates acceptance field_truth array_descriptors",
    )
    if (
        m["schema"] != "caos.local-waveform-result.v1"
        or m["method"] != "seismic.waveform-qc-classical/v1"
        or m["status"] not in ("computed", "qc_only")
        or m["field_truth"] is not None
    ):
        fail("waveform_contract")
    keys(m["acceptance"], "field_eligible method_accepted host_admitted provider_verified")
    if any(v is not False for v in m["acceptance"].values()):
        fail("waveform_contract")
    keys(m["request"], "submitted scientific_sha256 original_json_bytes original_json_sha256")
    submitted = validate_request(m["request"]["submitted"])
    if m["request"]["scientific_sha256"] != scientific_identity(submitted):
        fail("waveform_contract")
    if (
        type(m["channels"]) is not list
        or len(m["channels"]) > len(submitted["channels"])
        or type(m["array_descriptors"]) is not list
    ):
        fail("waveform_contract")
    identities = set()
    for i, c in enumerate(m["channels"]):
        if (
            type(c) is not dict
            or type(c.get("channel_index")) is not int
            or c["channel_index"] != i
            or type(c.get("nslc")) is not list
            or len(c["nslc"]) != 4
        ):
            fail("waveform_contract")
        identity = nslc(dict(zip(("network", "station", "location", "channel"), c["nslc"])))
        if identity != nslc(submitted["channels"][i]):
            fail("waveform_contract")
        _unit_ledger(c)
        identities.add(i)
    candidates = m["candidates"]
    if m["status"] == "qc_only":
        if candidates is not None:
            fail("waveform_contract")
    elif type(candidates) is not list or len(candidates) > 4096:
        fail("waveform_contract")
    for c in candidates or []:
        keys(
            c,
            "channel_index on_index off_exclusive_index peak_index peak_ratio on_utc on_relative_s truncated_at_valid_start truncated_at_valid_end phase timing_sigma_s",
        )
        if (
            any(
                type(c[k]) is not int or c[k] < 0
                for k in ("channel_index", "on_index", "off_exclusive_index", "peak_index")
            )
            or c["channel_index"] not in identities
            or not c["on_index"] <= c["peak_index"] < c["off_exclusive_index"]
            or not finite_number(c["peak_ratio"])
            or c["peak_ratio"] < 0
            or not finite_number(c["on_relative_s"])
            or c["on_relative_s"] < 0
            or any(type(c[k]) is not bool for k in ("truncated_at_valid_start", "truncated_at_valid_end"))
            or c["phase"] is not None
            or c["timing_sigma_s"] is not None
        ):
            fail("waveform_contract")
        utc_us(c["on_utc"])
    if len(m["array_descriptors"]) > 3 * len(ARRAY_NAMES):
        fail("waveform_contract")
    total = 0
    seen = set()
    for d in m["array_descriptors"]:
        keys(d, "channel_index name dtype shape unit bytes sha256")
        if (
            type(d["channel_index"]) is not int
            or d["channel_index"] not in identities
            or type(d["name"]) is not str
            or d["name"] not in ARRAY_NAMES
            or d["dtype"] not in ("<i4", "<f8", "|b1")
            or type(d["shape"]) is not list
            or not 1 <= len(d["shape"]) <= 2
            or any(type(n) is not int or n <= 0 for n in d["shape"])
            or type(d["bytes"]) is not int
            or not 0 < d["bytes"] <= 33554432
            or type(d["unit"]) is not str
            or type(d["sha256"]) is not str
            or not re.fullmatch("[a-f0-9]{64}", d["sha256"])
        ):
            fail("waveform_contract")
        key = (d["channel_index"], d["name"])
        if key in seen or (m["status"] == "qc_only" and d["name"] != "counts"):
            fail("waveform_contract")
        seen.add(key)
        expected_dtype = "<i4" if d["name"] == "counts" else "|b1" if d["name"] == "edge_valid" else "<f8"
        if d["dtype"] != expected_dtype:
            fail("waveform_contract")
        size = math.prod(d["shape"]) * (4 if expected_dtype == "<i4" else 1 if expected_dtype == "|b1" else 8)
        if size != d["bytes"]:
            fail("waveform_contract")
        if d["name"] == "filter_sos":
            if d["shape"] != [submitted["processing"]["filter_order"], 6]:
                fail("waveform_contract")
        elif len(d["shape"]) != 1 or d["shape"][0] > (
            65537
            if d["name"].startswith(("response_", "inverse_")) or d["name"] == "prefilter_weight"
            else 4097
            if d["name"].endswith("_psd") or d["name"] == "psd_frequency_hz"
            else 60000
        ):
            fail("waveform_contract")
        total += size
    if total + native_precount(m, 2097152, max_nodes=2097152, max_depth=16) > 33554432:
        fail("waveform_contract")


def seal_result(result):
    if type(result) is not WaveformResult:
        fail("waveform_type")
    m = result.metadata
    _sealed_metadata(m)
    if type(result.arrays) is not dict:
        fail("waveform_type")
    import numpy as np

    if any(
        type(k) is not tuple
        or len(k) != 2
        or type(k[0]) is not int
        or type(k[1]) is not str
        or type(a) is not np.ndarray
        for k, a in result.arrays.items()
    ):
        fail("waveform_type")
    seen = set()
    total = 0
    for d in m["array_descriptors"]:
        keys(d, "channel_index name dtype shape unit bytes sha256")
        key = (d["channel_index"], d["name"])
        if key in seen or key not in result.arrays:
            fail("waveform_contract")
        seen.add(key)
        a = result.arrays[key]
        if (
            a.dtype.str != d["dtype"]
            or list(a.shape) != d["shape"]
            or a.nbytes != d["bytes"]
            or not a.flags.c_contiguous
            or not a.flags.owndata
            or a.flags.writeable
            or not np.isfinite(a).all()
            or sha(memoryview(a).cast("B")) != d["sha256"]
        ):
            fail("waveform_contract")
        total += a.nbytes
    if set(result.arrays) != seen or total > 33554432:
        fail("waveform_contract")
    encoded = json.dumps(m, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    return SealedWaveform(encoded, sha(encoded))


def _stp_number(token):
    if len(token) > 128:
        fail("waveform_limit")
    if not DECIMAL.fullmatch(token):
        fail()
    value = float(token)
    if not math.isfinite(value):
        fail()
    return value


def references_from_stp(raw, event_id, selected_nslc):
    return _references_from_stp(raw, event_id, selected_nslc, cloud=False)


def references_from_scedc_cloud_stp(raw, event_id, selected_nslc):
    """Explicit bounded SCEDC cloud10 variant; never shift legacy9 tokens."""
    return _references_from_stp(raw, event_id, selected_nslc, cloud=True)


def _references_from_stp(raw, event_id, selected_nslc, *, cloud):
    exact_bytes(raw, 1048576)
    if (
        type(event_id) is not str
        or not re.fullmatch(r"[0-9]{1,20}", event_id)
        or type(selected_nslc) is not tuple
        or len(selected_nslc) != 4
    ):
        fail("waveform_contract")
    selected = nslc(dict(zip(("network", "station", "location", "channel"), selected_nslc)))
    if b"\x00" in raw or any(b > 127 for b in raw):
        fail()
    # LF/CRLF only; original line offsets/terminators are retained independently.
    lines = raw.splitlines(keepends=True)
    if len(lines) > 4096:
        fail("waveform_limit")
    rows = []
    origin = None
    cursor = 0
    for index, line in enumerate(lines):
        body = line[:-2] if line.endswith(b"\r\n") else line[:-1] if line.endswith(b"\n") else line
        if len(body) > 2048:
            fail("waveform_limit")
        if b"\r" in body or any(x < 32 and x not in (9,) for x in body):
            fail()
        fields = body.decode("ascii").split()
        offset = cursor
        cursor += len(line)
        if not fields:
            continue
        if origin is None:
            if fields[0] == "#":
                fields = fields[1:]
            elif fields[0].startswith("#"):
                fields[0] = fields[0][1:]
            if len(fields) != (10 if cloud else 9):
                fail()
            if cloud:
                eid, kind, geographic, stamp, lat, lon, depth, mag, magtype, quality = fields
                if (
                    kind != "eq"
                    or geographic not in ("l", "r", "t")
                    or magtype not in ("b", "l", "c", "w", "e", "s", "n", "h")
                ):
                    fail()
            else:
                eid, kind, stamp, lat, lon, depth, mag, magtype, quality = fields
            if (
                eid != event_id
                or not cloud
                and kind not in ("le", "ts")
                or not re.fullmatch(r"[A-Za-z]", magtype)
                or not re.fullmatch(r"[0-9]{4}/[0-9]{2}/[0-9]{2},[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?", stamp)
            ):
                fail()
            if (
                not -90 <= _stp_number(lat) <= 90
                or not -180 <= _stp_number(lon) <= 180
                or not 0 <= _stp_number(quality) <= 1
            ):
                fail()
            _stp_number(depth)
            _stp_number(mag)
            origin = utc_us(stamp.replace("/", "-").replace(",", "T") + "Z")
            continue
        if len(fields) != 13:
            fail()
        net, sta, cha, loc, lat, lon, elev, phase, motion, onset, quality, distance, seconds = fields
        identity = nslc({"network": net, "station": sta, "channel": cha, "location": "" if loc == "--" else loc})
        if (
            not -90 <= _stp_number(lat) <= 90
            or not -180 <= _stp_number(lon) <= 180
            or not 0 <= _stp_number(quality) <= 1
            or _stp_number(distance) < 0
        ):
            fail()
        elevation = _stp_number(elev)
        if phase not in ("P", "S") or not re.fullmatch(r"[cd.][ur.]", motion) or onset not in ("i", "e", "w"):
            fail()
        if len(seconds) > 128 or not re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]{1,6})?", seconds):
            fail()
        sign = -1 if seconds.startswith("-") else 1
        plain = seconds.lstrip("+-")
        whole, _, fraction = plain.partition(".")
        offset_us = sign * (int(whole) * 1000000 + int(fraction.ljust(6, "0")))
        if abs(offset_us) > 86400000000:
            fail()
        if identity != selected:
            continue
        if len(rows) >= 128:
            fail("waveform_limit")
        row_sha = sha(body)
        identifier = f"line:{index};offset:{offset};length:{len(body)};sha256:{row_sha}"
        rows.append(
            {
                "network": net,
                "station": sta,
                "location": identity[2],
                "channel": cha,
                "phase": phase,
                "pick_utc": format_utc(origin + offset_us),
                "uncertainty_s": None,
                "analyst_status": "catalogue-unspecified",
                "source_record_id": identifier,
                "lineage": {
                    "line_index": index,
                    "byte_offset": offset,
                    "byte_length": len(body),
                    "row_sha256": row_sha,
                    "latitude": _stp_number(lat),
                    "longitude": _stp_number(lon),
                    "elevation_m": elevation,
                    "first_motion": motion,
                    "onset": onset,
                    "quality_code": _stp_number(quality),
                    "quality_interpretation": "ordinal, not Gaussian sigma",
                    "distance_km": _stp_number(distance),
                    "origin_offset_us": offset_us,
                },
            }
        )
    if origin is None:
        fail()
    phases = Counter(row["phase"] for row in rows)
    ambiguous = [r["source_record_id"] for r in rows if phases[r["phase"]] > 1]
    converted = {
        "event_id": event_id,
        "origin_utc": format_utc(origin),
        "raw_bytes": len(raw),
        "raw_sha256": sha(raw),
        "rows": rows,
        "unsupported_or_ambiguous_rows": ambiguous,
    }
    if cloud:
        converted.update(source_format="scedc-cloud-stp-10/v1", event_type=kind, geographic_type=geographic)
    return converted


def evaluate_waveform_candidates(sealed_result, reference_bytes):
    if (
        type(sealed_result) is not SealedWaveform
        or type(sealed_result.metadata_bytes) is not bytes
        or type(sealed_result.calculation_sha256) is not str
    ):
        fail("waveform_type")
    exact_bytes(sealed_result.metadata_bytes, 2097152)
    if sha(sealed_result.metadata_bytes) != sealed_result.calculation_sha256:
        fail("waveform_contract")
    metadata = bounded_json(sealed_result.metadata_bytes, 2097152, max_nodes=2097152, max_depth=16)
    _sealed_metadata(metadata)
    refs = bounded_json(reference_bytes, 1048576)
    keys(refs, "schema event_id source selection_sealed_before_scoring references")
    if (
        refs["schema"] != "caos.waveform-analyst-references.v1"
        or type(refs["event_id"]) is not str
        or not re.fullmatch(r"[0-9]{1,20}", refs["event_id"])
        or refs["selection_sealed_before_scoring"] is not True
    ):
        fail("waveform_contract")
    keys(refs["source"], "raw_sha256 citation rights")
    source = refs["source"]
    if (
        type(source["raw_sha256"]) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", source["raw_sha256"])
        or type(source["citation"]) is not str
        or not source["citation"].strip()
        or source["rights"] not in ("private-use-attested", "reviewed-public-scsn", "unknown", "forbidden")
    ):
        fail("waveform_contract")
    reference_rows = refs["references"]
    if type(reference_rows) is not list or len(reference_rows) > 128:
        fail("waveform_contract")
    grouped = Counter()
    normalized = []
    for row in reference_rows:
        keys(row, " ".join(REFERENCE_KEYS))
        identity = nslc({k: row[k] for k in ("network", "station", "location", "channel")})
        uncertainty = row["uncertainty_s"]
        if (
            row["phase"] not in ("P", "S")
            or row["analyst_status"] not in ("manual", "catalogue-unspecified")
            or type(row["source_record_id"]) is not str
            or not row["source_record_id"].strip()
            or (uncertainty is not None and (not finite_number(uncertainty) or uncertainty <= 0))
        ):
            fail("waveform_contract")
        pick = utc_us(row["pick_utc"])
        grouped[(identity, row["phase"])] += 1
        normalized.append((pick, row["source_record_id"], identity, row))
    candidates = metadata["candidates"] or []
    identities = {tuple(c["nslc"]): c["channel_index"] for c in metadata["channels"]}
    t0 = utc_us(metadata["request"]["submitted"]["analysis_start_utc"])
    t1 = utc_us(metadata["request"]["submitted"]["analysis_end_utc"])
    used = set()
    out = []
    denominators = Counter()
    errors = []
    for pick, identifier, identity, row in sorted(normalized, key=lambda x: (x[0], x[1])):
        matching = None
        if source["rights"] in ("unknown", "forbidden"):
            status = "rights_ineligible"
        elif grouped[(identity, row["phase"])] > 1:
            status = "ambiguous"
        elif identity not in identities:
            status = "unknown_channel"
        elif not t0 <= pick < t1:
            status = "out_of_window"
        elif metadata["status"] != "computed":
            status = "calculation_qc_only"
        else:
            eligible = [
                (abs(utc_us(c["on_utc"]) - pick), c["on_index"], i)
                for i, c in enumerate(candidates)
                if i not in used
                and c["channel_index"] == identities[identity]
                and not c["truncated_at_valid_start"]
                and not c["truncated_at_valid_end"]
                and abs(utc_us(c["on_utc"]) - pick) <= 500000
            ]
            if eligible:
                matching = min(eligible)[2]
                used.add(matching)
                status = "matched"
            else:
                status = "unmatched"
        residual = (utc_us(candidates[matching]["on_utc"]) - pick) / 1000000 if matching is not None else None
        denominators[status] += 1
        if residual is not None:
            errors.append(abs(residual))
        out.append(
            {
                "reference": clone_native(row),
                "status": status,
                "candidate_index": matching,
                "signed_residual_s": residual,
            }
        )
    return {
        "schema": "caos.local-waveform-evaluation.v1",
        "status": "evaluated" if denominators["matched"] + denominators["unmatched"] else "not_evaluable",
        "sealed_calculation_sha256": sealed_result.calculation_sha256,
        "reference_json_raw_bytes": len(reference_bytes),
        "reference_json_raw_sha256": sha(reference_bytes),
        "original_reference_parent_sha256": source["raw_sha256"],
        "event_id": refs["event_id"],
        "matching_policy": "UTC then source ID; nearest unused nontruncated onset, tie earliest index; greedy",
        "tolerance_s": 0.5,
        "references": out,
        "reference_count": len(reference_rows),
        "reference_status_counts": dict(denominators),
        "matched_reference_fraction": denominators["matched"] / len(reference_rows) if reference_rows else None,
        "median_absolute_residual_s": median(errors) if errors else None,
        "unmatched_candidate_count": len(candidates) - len(used),
        "reference_rights_declaration": source["rights"],
        "field_truth": None,
        "method_accepted": False,
        "provider_verified": False,
    }
