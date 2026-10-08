"""Bounded ordinary local waveform input. Stdlib only; no file/network/env hooks.

Preflight is not native crash containment, field eligibility or a clock calibration.
Raw hashes and CPython scientific JSON identity are deliberately different domains.
"""

from collections import Counter
import codecs
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import hashlib
import json
import math
import re
import struct
from xml.parsers import expat


MESSAGES = {
    "waveform_type": "Waveform input type is unsupported",
    "waveform_limit": "Waveform input exceeds the local limit",
    "waveform_format": "Waveform encoding is unsupported or malformed",
    "waveform_contract": "Waveform scientific request is invalid",
    "waveform_decode": "Waveform samples could not be decoded",
    "waveform_engine": "Waveform scientific engine is unavailable or incompatible",
}
NS = "http://www.fdsn.org/xml/station/1"
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
UTC = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,6}))?Z\Z")
REASONS = (
    "rights_ineligible",
    "unsupported_clock",
    "gap",
    "overlap",
    "rate_mismatch",
    "missing_channel",
    "epoch_missing",
    "epoch_ambiguous",
    "epoch_partial",
    "orientation_missing",
    "response_units_missing",
    "response_stage_unsupported",
    "response_chain_inconsistent",
    "response_sensitivity_inconsistent",
    "response_warning",
    "response_zero_support",
    "response_inverse_undefined",
    "flat",
    "clip_detected",
    "clip_suspected",
    "blocking_flags",
)


class WaveformInputError(ValueError):
    """Only fixed application fields are public; traceback locals are not safe output."""

    def __init__(self, code, field="document"):
        self.code = code
        self.field = field
        self.message = MESSAGES[code]
        super().__init__(self.message)


def fail(code="waveform_format", field="document"):
    raise WaveformInputError(code, field)


def exact_bytes(raw, cap):
    if type(raw) is not bytes:
        fail("waveform_type")
    if not 1 <= len(raw) <= cap:
        fail("waveform_limit")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc_us(text):
    valid = type(text) is str and UTC.fullmatch(text)
    result = None
    if valid:
        parts = valid.groups()
        try:
            stamp = datetime(*map(int, parts[:6]), microsecond=int((parts[6] or "").ljust(6, "0")), tzinfo=timezone.utc)
            if 1970 <= stamp.year <= 2100:
                delta = stamp - EPOCH
                result = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
        except ValueError:
            pass
    if result is None:
        fail("waveform_contract", "request")
    return result


def format_utc(value):
    return (EPOCH + timedelta(microseconds=value)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _string_count(text, cap):
    if type(text) is not str:
        fail("waveform_type", "request")
    encoded = 0
    canonical = 2
    for char in text:
        n = ord(char)
        if 0xD800 <= n <= 0xDFFF:
            fail()
        encoded += 1 if n < 128 else 2 if n < 2048 else 3 if n < 65536 else 4
        canonical += 2 if char in '"\\\b\f\n\r\t' else 6 if n < 32 or 127 <= n < 65536 else 12 if n >= 65536 else 1
        if encoded > cap:
            fail("waveform_limit")
    return canonical


def native_precount(value, cap=65536, *, max_nodes=4096, max_depth=8):
    """Validate native graph BEFORE cloning/encoder; only bounded primitive locals."""
    nodes = 0
    active = set()

    def visit(item, depth, key=False):
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes:
            fail("waveform_limit")
        kind = type(item)
        if kind is str:
            count = _string_count(item, 64 if key else 2048)
        elif kind in (dict, list):
            if depth >= max_depth or id(item) in active:
                fail("waveform_limit")
            active.add(id(item))
            count = 2
            for i, part in enumerate(item.items() if kind is dict else item):
                count += int(i > 0)
                if kind is dict:
                    k, v = part
                    if type(k) is not str:
                        fail("waveform_type", "request")
                    count += visit(k, depth + 1, True) + 1 + visit(v, depth + 1)
                else:
                    count += visit(part, depth + 1)
                if count > cap:
                    fail("waveform_limit")
            active.remove(id(item))
        elif kind in (int, float):
            if (kind is int and abs(item) > 9007199254740991) or not math.isfinite(item):
                fail("waveform_contract", "processing")
            text = str(item) if kind is int else repr(item)
            if len(text) > 128:
                fail("waveform_limit")
            count = len(text)
        elif item is None:
            count = 4
        elif kind is bool:
            count = 4 if item else 5
        else:
            fail("waveform_type", "request")
        if count > cap:
            fail("waveform_limit")
        return count

    return visit(value, 0)


def clone_native(value):
    # Called only after exact-type finite/cycle/count validation.
    if type(value) is dict:
        return {k: clone_native(v) for k, v in value.items()}
    if type(value) is list:
        return [clone_native(v) for v in value]
    return value


def scientific_identity(value):
    native_precount(value)
    digest = hashlib.sha256()
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    for piece in encoder.iterencode(value):
        digest.update(piece.encode("ascii"))
    return digest.hexdigest()


class _JSONScan:
    """Full grammar/token/decoded-duplicate preflight, no final object tree."""

    def __init__(self, text, cap, max_nodes=4096, max_depth=8):
        self.text, self.cap, self.pos, self.nodes = text, cap, 0, 0
        self.max_nodes, self.max_depth = max_nodes, max_depth

    def ws(self):
        while self.pos < len(self.text) and self.text[self.pos] in " \t\r\n":
            self.pos += 1

    def string(self, key=False):
        start = self.pos
        self.pos += 1
        escaped = False
        while self.pos < len(self.text):
            c = self.text[self.pos]
            self.pos += 1
            if not escaped and c == '"':
                token = self.text[start : self.pos]
                parsed = None
                try:
                    parsed = json.loads(token)
                except (ValueError, UnicodeError):
                    pass
                if type(parsed) is not str:
                    fail()
                return parsed, _string_count(parsed, 64 if key else 2048)
            if not escaped and ord(c) < 32:
                fail()
            escaped = not escaped if c == "\\" else False
            # Even fully escaped strings cannot exceed six bytes per allowed UTF-8 byte.
            if self.pos - start > (64 if key else 2048) * 6 + 2:
                fail("waveform_limit")
        fail()

    def value(self, depth=0, key=False):
        self.nodes += 1
        if self.nodes > self.max_nodes:
            fail("waveform_limit")
        self.ws()
        if self.pos >= len(self.text):
            fail()
        c = self.text[self.pos]
        if c == '"':
            return self.string(key)[1]
        if c in "[{":
            if depth >= self.max_depth:
                fail("waveform_limit")
            self.pos += 1
            closing = "]" if c == "[" else "}"
            seen = set()
            count, entries = 2, 0
            self.ws()
            if self.pos < len(self.text) and self.text[self.pos] == closing:
                self.pos += 1
                return count
            while True:
                self.ws()
                if c == "{":
                    self.nodes += 1
                    if self.nodes > self.max_nodes:
                        fail("waveform_limit")
                    if self.pos >= len(self.text) or self.text[self.pos] != '"':
                        fail()
                    k, length = self.string(True)
                    if k in seen:
                        fail()
                    seen.add(k)
                    self.ws()
                    if self.pos >= len(self.text) or self.text[self.pos] != ":":
                        fail()
                    self.pos += 1
                    count += length + 1
                count += int(entries > 0) + self.value(depth + 1)
                entries += 1
                if count > self.cap:
                    fail("waveform_limit")
                self.ws()
                if self.pos >= len(self.text):
                    fail()
                separator = self.text[self.pos]
                self.pos += 1
                if separator == closing:
                    return count
                if separator != ",":
                    fail()
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] not in " \t\r\n,]}:":
            self.pos += 1
            if self.pos - start > 128:
                fail("waveform_limit")
        token = self.text[start : self.pos]
        if token in ("true", "false", "null"):
            return len(token)
        if not NUMBER.fullmatch(token):
            fail()
        if "." in token or "e" in token.lower():
            value = float(token)
            if not math.isfinite(value):
                fail()
            return len(repr(value))
        value = int(token)
        if abs(value) > 9007199254740991:
            fail()
        return len(str(value))


def bounded_json(raw, cap, *, max_nodes=4096, max_depth=8):
    exact_bytes(raw, cap)
    if raw.startswith(b"\xef\xbb\xbf"):
        fail()
    text = None
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        pass
    if text is None:
        fail()
    scanner = _JSONScan(text, cap, max_nodes, max_depth)
    scanner.value()
    scanner.ws()
    if scanner.pos != len(text):
        fail()
    # No tree construction until complete grammar/counters/canonical pre-count pass.
    return json.loads(text)


def keys(value, expected, field="request"):
    if type(value) is not dict or set(value) != set(expected.split()):
        fail("waveform_contract", field)


def nslc(row):
    keys(row, "network station location channel", "channels")
    for key, low, high in (("network", 1, 2), ("station", 1, 5), ("location", 0, 2), ("channel", 3, 3)):
        s = row[key]
        if type(s) is not str or not low <= len(s) <= high or not re.fullmatch(r"[A-Z0-9]*", s):
            fail("waveform_contract", "channels")
    return tuple(row[k] for k in ("network", "station", "location", "channel"))


def validate_request(value):
    if type(value) is not dict:
        fail("waveform_type", "request")
    native_precount(value)
    keys(
        value,
        "schema channels conditioning_start_utc conditioning_end_utc analysis_start_utc "
        "analysis_end_utc representation source adc_rails processing",
    )
    if value["schema"] != "caos.local-waveform-request.v1" or value["representation"] != "unrestituted_integer_counts":
        fail("waveform_contract", "request")
    channels = value["channels"]
    if type(channels) is not list or not 1 <= len(channels) <= 3:
        fail("waveform_contract", "channels")
    names = [nslc(c) for c in channels]
    if len(set(names)) != len(names) or len({c[:2] for c in names}) != 1:
        fail("waveform_contract", "channels")
    t = [
        utc_us(value[k])
        for k in ("conditioning_start_utc", "conditioning_end_utc", "analysis_start_utc", "analysis_end_utc")
    ]
    if not 10000000 <= t[1] - t[0] <= 300000000 or not t[0] <= t[2] < t[3] <= t[1] or t[3] - t[2] < 5000000:
        fail("waveform_contract", "request")
    source = value["source"]
    keys(source, "kind citation provider_url declared_sha256 rights processing_statement", "source")
    if source["kind"] not in ("user", "provider") or source["rights"] not in (
        "private-use-attested",
        "reviewed-public-scsn",
        "unknown",
        "forbidden",
    ):
        fail("waveform_contract", "source")
    for k in ("citation", "processing_statement"):
        if type(source[k]) is not str or not source[k].strip():
            fail("waveform_contract", "source")
    url, declared = source["provider_url"], source["declared_sha256"]
    if url is not None and (type(url) is not str or not re.fullmatch(r"https://[^\s/]+(?:/[^\s]*)?", url)):
        fail("waveform_contract", "source")
    if declared is not None and (type(declared) is not str or not re.fullmatch("[a-f0-9]{64}", declared)):
        fail("waveform_contract", "source")
    rails = value["adc_rails"]
    if type(rails) is not list or len(rails) != len(channels):
        fail("waveform_contract", "adc_rails")
    for rail in rails:
        if rail is None:
            continue
        keys(rail, "minimum_count maximum_count evidence", "adc_rails")
        lo, hi = rail["minimum_count"], rail["maximum_count"]
        if (
            type(lo) is not int
            or type(hi) is not int
            or not -2147483648 <= lo < hi <= 2147483647
            or type(rail["evidence"]) is not str
            or not rail["evidence"].strip()
        ):
            fail("waveform_contract", "adc_rails")
    p = value["processing"]
    keys(
        p,
        "output prefilter_hz water_level_db taper_fraction bandpass_hz filter_order filter_mode "
        "edge_guard_s sta_s lta_s threshold_on threshold_off refractory_s welch_segment_samples",
        "processing",
    )
    if p["output"] != "native" or p["filter_mode"] != "offline-zero-phase":
        fail("waveform_contract", "processing")
    for k, low, high in (
        ("taper_fraction", 0.01, 0.10),
        ("edge_guard_s", 0, 150),
        ("sta_s", 0.05, 2),
        ("lta_s", 0.5, 20),
        ("refractory_s", 0, 10),
    ):
        if not finite_number(p[k]) or not low <= p[k] <= high:
            fail("waveform_contract", "processing")
    if p["water_level_db"] is not None and (
        not finite_number(p["water_level_db"]) or not 20 <= p["water_level_db"] <= 120
    ):
        fail("waveform_contract", "processing")
    if (
        not all(finite_number(p[k]) for k in ("threshold_on", "threshold_off"))
        or not 1 < p["threshold_off"] < p["threshold_on"] <= 100
        or p["sta_s"] >= p["lta_s"]
    ):
        fail("waveform_contract", "processing")
    for k, length in (("prefilter_hz", 4), ("bandpass_hz", 2)):
        v = p[k]
        if (
            type(v) is not list
            or len(v) != length
            or not all(finite_number(x) for x in v)
            or any(a >= b for a, b in zip(v, v[1:]))
        ):
            fail("waveform_contract", "processing")
    if (
        p["prefilter_hz"][0] < 0.05
        or not p["prefilter_hz"][1] <= p["bandpass_hz"][0] < p["bandpass_hz"][1] <= p["prefilter_hz"][2]
    ):
        fail("waveform_contract", "processing")
    m = p["welch_segment_samples"]
    if (
        type(p["filter_order"]) is not int
        or not 2 <= p["filter_order"] <= 6
        or type(m) is not int
        or not 64 <= m <= 8192
        or m & (m - 1)
    ):
        fail("waveform_contract", "processing")
    return clone_native(value)


def _header(raw, off, order):
    """Candidate fixed-header interpretation; exceptions converted outside handlers."""
    (
        year,
        day,
        hour,
        minute,
        second,
        reserved,
        fraction,
        count,
        factor,
        mult,
        activity,
        io,
        quality,
        blocks,
        correction,
        data,
        first,
    ) = struct.unpack_from(order + "HHBBBBHHhhBBBBiHH", raw, off + 20)
    if (
        not 1970 <= year <= 2100
        or not 1 <= day <= (366 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 365)
        or hour > 23
        or minute > 59
        or second > 59
        or reserved
        or fraction > 9999
        or not count
        or not factor
        or not mult
        or blocks not in (1, 2)
        or activity & 128
        or io & 192
    ):
        return None
    rate = (Fraction(factor) if factor > 0 else Fraction(-1, factor)) * (
        Fraction(mult) if mult > 0 else Fraction(-1, mult)
    )
    if rate not in (20, 40, 50, 100, 200) or not 48 <= first < data or data > 4096:
        return None
    visited, offset, block1000, block1001 = [], first, None, None
    for i in range(blocks):
        if offset < 48 or offset + 8 > data or off + offset + 8 > len(raw) or any(abs(offset - v) < 8 for v in visited):
            return None
        visited.append(offset)
        typ, nxt = struct.unpack_from(order + "HH", raw, off + offset)
        body = raw[off + offset + 4 : off + offset + 8]
        if typ == 1000 and block1000 is None:
            enc, word, exponent, res = body
            if enc not in (1, 3, 10, 11) or word not in (0, 1) or not 8 <= exponent <= 12 or res:
                return None
            block1000 = (enc, word, 1 << exponent)
        elif typ == 1001 and block1001 is None:
            timing, micro, res, frames = struct.unpack("BbBB", body)
            if timing > 100 or res:
                return None
            block1001 = (timing, micro, frames)
        else:
            return None
        if (i == blocks - 1 and nxt != 0) or (i != blocks - 1 and nxt == 0):
            return None
        offset = nxt
    if block1000 is None:
        return None
    enc, word, length = block1000
    if not data < length or off + length > len(raw):
        return None
    if enc in (1, 3):
        if count * (2 if enc == 1 else 4) > length - data or (block1001 and block1001[2]):
            return None
    elif data % 64 or (length - data) % 64 or (block1001 and block1001[2] > (length - data) // 64):
        return None
    stamp = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(
        days=day - 1, hours=hour, minutes=minute, seconds=second, microseconds=fraction * 100
    )
    start = (stamp - EPOCH).days * 86400000000 + (stamp - EPOCH).seconds * 1000000 + stamp.microsecond
    start += (0 if activity & 2 else correction * 100) + (block1001[1] if block1001 else 0)
    row = {
        "byte_offset": off,
        "byte_length": length,
        "header_order": order,
        "sample_word_order": ">" if word else "<",
        "encoding": enc,
        "data_offset": data,
        "npts": count,
        "sample_rate_hz": int(rate),
        "start_us": start,
        "end_exclusive_us": start + count * (1000000 // int(rate)),
        "activity_flags": activity,
        "io_clock_flags": io,
        "data_quality_flags": quality,
        "header_correction_100us": correction,
        "correction_already_applied": bool(activity & 2),
        "microsecond_offset": block1001[1] if block1001 else 0,
        "timing_quality": block1001[0] if block1001 else None,
        "steim_frame_count": block1001[2] if block1001 else None,
    }
    if enc in (10, 11):
        capacity, first_sample, last_sample = 0, None, None
        for frame in range((length - data) // 64):
            words = struct.unpack_from(row["sample_word_order"] + "16I", raw, off + data + frame * 64)
            if words[0] >> 30:
                return None
            for w in range(1, 16):
                code = (words[0] >> (30 - 2 * w)) & 3
                if frame == 0 and w in (1, 2):
                    if code:
                        return None
                    signed = struct.unpack(
                        row["sample_word_order"] + "i", struct.pack(row["sample_word_order"] + "I", words[w])
                    )[0]
                    if w == 1:
                        first_sample = signed
                    else:
                        last_sample = signed
                    continue
                if enc == 10:
                    capacity += (0, 4, 2, 1)[code]
                elif code == 1:
                    capacity += 4
                elif code in (2, 3):
                    dnib = words[w] >> 30
                    sizes = {1: 1, 2: 2, 3: 3} if code == 2 else {0: 5, 1: 6, 2: 7}
                    if dnib not in sizes:
                        return None
                    capacity += sizes[dnib]
        if capacity < count or first_sample is None or last_sample is None:
            return None
        row.update(steim_x0=first_sample, steim_xn=last_sample, packed_difference_capacity=capacity)
    return row


def scan_miniseed(raw, request):
    exact_bytes(raw, 16777216)
    requested = [nslc(c) for c in request["channels"]]
    rows, counts, offset = [], Counter(), 0
    while offset < len(raw):
        if len(rows) >= 4096:
            fail("waveform_limit")
        if len(raw) - offset < 48:
            fail()
        fixed = raw[offset : offset + 20]
        if not re.fullmatch(rb"[0-9]{6}", fixed[:6]) or fixed[6] not in b"DRQM" or fixed[7] != 32:
            fail()
        parts = [fixed[18:20], fixed[8:13], fixed[13:15], fixed[15:18]]
        names = []
        for part in parts:
            short = part.rstrip(b" ")
            if not re.fullmatch(rb"[A-Z0-9]*", short):
                fail()
            names.append(short.decode("ascii"))
        identity = tuple(names)
        if identity not in requested:
            fail("waveform_contract", "channels")
        candidates = [r for o in (">", "<") if (r := _header(raw, offset, o)) is not None]
        if len(candidates) != 1:
            fail()
        row = candidates[0]
        ci = requested.index(identity)
        counts[ci] += row["npts"]
        if counts[ci] > 60000 or sum(counts.values()) > 180000:
            fail("waveform_limit")
        row.update(channel_index=ci, nslc=list(identity), sequence=fixed[:6].decode("ascii"), quality=chr(fixed[6]))
        rows.append(row)
        offset += row["byte_length"]
    return rows


def _xml_num(text, integer=False):
    text = text.strip()
    if len(text) > 128:
        fail("waveform_limit")
    if not DECIMAL.fullmatch(text):
        fail()
    value = float(text)
    if not math.isfinite(value):
        fail()
    if integer:
        if not re.fullmatch(r"[+-]?[0-9]+", text) or abs(int(text)) > 9007199254740991:
            fail()
        return int(text)
    return value


_RESPONSE_TAGS = set(
    "Response InstrumentSensitivity InstrumentPolynomial Stage PolesZeros Coefficients FIR "
    "Polynomial ResponseList ResponseListElement InputUnits OutputUnits Name Description Value Frequency "
    "PzTransferFunctionType NormalizationFactor NormalizationFrequency Zero Pole Real Imaginary "
    "CfTransferFunctionType Numerator Denominator NumeratorCoefficient Symmetry Decimation InputSampleRate "
    "Factor Offset Delay Correction StageGain ApproximationType FrequencyLowerBound FrequencyUpperBound "
    "ApproximationLowerBound ApproximationUpperBound MaximumError Coefficient Amplitude Phase".split()
)

# Only these scientific parent/child placements are interpreted. This is an
# explicit local subset, not remote schema validation or arbitrary XML flattening.
_RESPONSE_CHILDREN = {
    "Response": set("InstrumentSensitivity InstrumentPolynomial Stage".split()),
    "InstrumentSensitivity": set("Value Frequency InputUnits OutputUnits".split()),
    "Stage": set("PolesZeros Coefficients FIR Polynomial ResponseList Decimation StageGain".split()),
    "PolesZeros": set(
        "Description InputUnits OutputUnits PzTransferFunctionType NormalizationFactor NormalizationFrequency Pole Zero".split()
    ),
    "Coefficients": set("Description InputUnits OutputUnits CfTransferFunctionType Numerator Denominator".split()),
    "FIR": set("Description InputUnits OutputUnits Symmetry NumeratorCoefficient".split()),
    "Polynomial": set(
        "Description InputUnits OutputUnits ApproximationType FrequencyLowerBound FrequencyUpperBound ApproximationLowerBound ApproximationUpperBound MaximumError Coefficient".split()
    ),
    "InstrumentPolynomial": set(
        "Description InputUnits OutputUnits ApproximationType FrequencyLowerBound FrequencyUpperBound ApproximationLowerBound ApproximationUpperBound MaximumError Coefficient".split()
    ),
    "ResponseList": set("Description InputUnits OutputUnits ResponseListElement".split()),
    "ResponseListElement": set("Frequency Amplitude Phase".split()),
    "Decimation": set("InputSampleRate Factor Offset Delay Correction".split()),
    "StageGain": set("Value Frequency".split()),
    "InputUnits": {"Name", "Description"},
    "OutputUnits": {"Name", "Description"},
    "Pole": {"Real", "Imaginary"},
    "Zero": {"Real", "Imaginary"},
}
_LIST_TAGS = {
    "Stage",
    "Pole",
    "Zero",
    "Numerator",
    "Denominator",
    "NumeratorCoefficient",
    "Coefficient",
    "ResponseListElement",
}


def _epoch_date(v):
    # FDSN unzoned metadata dateTime denotes UTC, never verified sample timing.
    parsed = None
    if type(v) is str and re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})?", v
    ):
        try:
            parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            delta = parsed.astimezone(timezone.utc) - EPOCH
            return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
        except (ValueError, OverflowError):
            pass
    fail()


def scan_stationxml(raw):
    """Expat events into bounded scientific DTOs, not a generic XML tree."""
    exact_bytes(raw, 2097152)
    if raw.startswith(b"\xef\xbb\xbf"):
        fail()
    failure = None
    output = None
    try:
        output = _scan_xml(raw)
    except WaveformInputError as error:
        failure = error.code
    except (expat.ExpatError, UnicodeError, ValueError, OverflowError):
        failure = "waveform_format"
    if failure:
        fail(failure)
    return output


def _scan_xml(raw):
    encoding = "utf-8"
    if raw.startswith(b"<?xml") and raw[5:6] in (b" ", b"\t", b"\r", b"\n"):
        end = raw.find(b"?>", 0, 512)
        if end < 0:
            fail()
        declaration_bytes = raw[: end + 2]
        declaration_bytes.decode("ascii", "strict")
        found = re.search(rb"""\bencoding\s*=\s*(["'])([^"']+)\1""", declaration_bytes)
        if found:
            literal = found[2]
            if literal not in (b"UTF-8", b"ISO-8859-1"):
                fail()
            encoding = "iso-8859-1" if literal == b"ISO-8859-1" else "utf-8"
    parser = expat.ParserCreate(namespace_separator="}")
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    frames = []
    result = {"schema_version": None, "channels": [], "counters": {}}
    counts = Counter()
    network = station = channel = stage = response = None
    numeric_tags = set(
        "Latitude Longitude Elevation Depth Azimuth Dip SampleRate Value Frequency "
        "NormalizationFactor NormalizationFrequency InputSampleRate Factor Offset Delay Correction "
        "Real Imaginary Numerator Denominator NumeratorCoefficient Coefficient Amplitude Phase "
        "FrequencyLowerBound FrequencyUpperBound ApproximationLowerBound ApproximationUpperBound MaximumError".split()
    )
    unit_fields = {"InputUnits", "OutputUnits"}

    def forbidden(*args):
        fail()

    def declaration(version, encoding, standalone):
        if version != "1.0" or encoding not in (None, "UTF-8", "ISO-8859-1"):
            fail()

    def start(name, attrs):
        nonlocal network, station, channel, stage, response
        counts["elements"] += 1
        counts["attributes"] += len(attrs)
        if len(frames) >= 32 or counts["elements"] > 50000 or len(attrs) > 16 or counts["attributes"] > 100000:
            fail("waveform_limit")
        if len(name.encode("utf-8")) > 128:
            fail("waveform_limit")
        for k, v in attrs.items():
            if len(k.encode("utf-8")) > 128 or len(v.encode("utf-8")) > 8192:
                fail("waveform_limit")
        ns, sep, tag = name.rpartition("}")
        if not sep or ns == "http://www.w3.org/2001/XInclude":
            fail()
        core = ns == NS
        parent = frames[-1]["tag"] if frames else None
        if core and frames and not frames[-1]["core"]:
            fail()
        if not frames:
            if not core or tag != "FDSNStationXML" or attrs.get("schemaVersion") not in ("1.1", "1.2"):
                fail()
            result["schema_version"] = attrs["schemaVersion"]
        if not core and any(
            f["tag"]
            in (
                "Response",
                "Stage",
                "InputUnits",
                "OutputUnits",
                "SampleRate",
                "Azimuth",
                "Dip",
                "Latitude",
                "Longitude",
                "Elevation",
                "Depth",
            )
            for f in frames
        ):
            fail()
        if core and any(f["tag"] == "Response" for f in frames) and tag not in _RESPONSE_TAGS:
            fail()
        in_response = any(f["tag"] == "Response" for f in frames)
        if core and not in_response and tag in _RESPONSE_TAGS - {"Response", "Name", "Description"}:
            fail()
        if core and in_response and tag not in _RESPONSE_CHILDREN.get(parent, set()):
            fail()
        if core and frames and parent in numeric_tags:
            fail()
        if (
            core
            and (in_response or tag in ("Network", "Station", "Channel", "Response") or tag in numeric_tags)
            and any("}" in k for k in attrs)
        ):
            fail()
        if core and tag in ("Network", "Station", "Channel"):
            for k in ("startDate", "endDate"):
                if k in attrs:
                    _epoch_date(attrs[k])
        if core and parent in ("Network", "Station", "Channel"):
            scientific = {"Latitude", "Longitude", "Elevation", "Depth", "Azimuth", "Dip", "SampleRate", "Response"}
            if tag in scientific:
                marker = ("scalar", tag)
                if marker in frames[-1]["seen"]:
                    fail()
                frames[-1]["seen"].add(marker)
        if frames:
            frames[-1]["text"] = ""
        frame = {
            "tag": tag,
            "core": core,
            "attrs": attrs if core and tag in ("Network", "Station", "Channel", "Stage", "Pole", "Zero") else {},
            "text": "",
            "seen": set(),
        }
        frames.append(frame)
        if not core:
            return
        if tag == "Network":
            if parent != "FDSNStationXML":
                fail()
            counts["networks"] += 1
            if counts["networks"] > 8:
                fail("waveform_limit")
            network = {"code": attrs.get("code"), "start": attrs.get("startDate"), "end": attrs.get("endDate")}
        elif tag == "Station":
            if parent != "Network":
                fail()
            counts["stations"] += 1
            if counts["stations"] > 32:
                fail("waveform_limit")
            station = {"code": attrs.get("code"), "start": attrs.get("startDate"), "end": attrs.get("endDate")}
        elif tag == "Channel":
            if parent != "Station":
                fail()
            counts["channels"] += 1
            if counts["channels"] > 64:
                fail("waveform_limit")
            channel = {
                "network": dict(network),
                "station": dict(station),
                "code": attrs.get("code"),
                "location": attrs.get("locationCode"),
                "start": attrs.get("startDate"),
                "end": attrs.get("endDate"),
                "values": {},
                "response": None,
            }
        elif tag == "Response":
            if parent != "Channel":
                fail()
            response = {"sensitivity": {}, "stages": [], "unsupported": False}
            channel["response"] = response
        elif tag == "Stage":
            if parent != "Response":
                fail()
            if len(response["stages"]) >= 32:
                fail("waveform_limit")
            stage = {
                "number": _xml_num(attrs.get("number", ""), True),
                "kind": None,
                "values": {},
                "units": {},
                "poles": [],
                "zeros": [],
                "numerator": [],
                "denominator": [],
                "fir": [],
                "gain": {},
                "decimation": {},
            }
            response["stages"].append(stage)
        elif tag in ("PolesZeros", "Coefficients", "FIR", "Polynomial", "ResponseList"):
            if stage is None or parent != "Stage" or stage["kind"] is not None:
                fail()
            stage["kind"] = tag
        elif tag == "InstrumentPolynomial":
            response["unsupported"] = True
        elif tag in ("Pole", "Zero"):
            if parent != "PolesZeros":
                fail()
            frame["complex"] = {}
        if core and tag in ("Pole", "Zero", "Numerator", "Denominator", "NumeratorCoefficient", "Coefficient"):
            attribute = "i" if tag == "NumeratorCoefficient" else "number"
            if attribute in attrs:
                number = _xml_num(attrs[attribute], True)
                marker = (tag, number)
                if number < 0 or marker in frames[-2]["seen"]:
                    fail()
                frames[-2]["seen"].add(marker)
        # Only scalar scientific fields require uniqueness; repeated list items are bounded separately.
        if core and parent in _RESPONSE_CHILDREN and tag not in _LIST_TAGS:
            marker = ("scalar", tag)
            if marker in frames[-2]["seen"]:
                fail()
            frames[-2]["seen"].add(marker)

    def text(value):
        if not frames:
            return
        encoded = len(value.encode("utf-8"))
        counts["text_bytes"] += encoded
        if counts["text_bytes"] > 1048576:
            fail("waveform_limit")
        frame = frames[-1]
        if len(frame["text"].encode("utf-8")) + encoded > 8192:
            fail("waveform_limit")
        frame["text"] += value

    def end(name):
        nonlocal network, station, channel, stage, response
        frame = frames.pop()
        tag, content = frame["tag"], frame["text"].strip()
        parent = frames[-1]["tag"] if frames else None
        ancestors = [f["tag"] for f in frames]
        if not frame["core"]:
            return
        value = _xml_num(content, tag in ("Factor", "Offset")) if tag in numeric_tags else content
        if parent == "Channel" and tag in (
            "Latitude",
            "Longitude",
            "Elevation",
            "Depth",
            "Azimuth",
            "Dip",
            "SampleRate",
        ):
            channel["values"][tag] = value
        elif parent in unit_fields and tag == "Name":
            if "Stage" in ancestors:
                stage["units"][parent] = content
            elif "InstrumentSensitivity" in ancestors:
                response["sensitivity"][parent] = content
        elif parent == "InstrumentSensitivity" and tag in ("Value", "Frequency"):
            response["sensitivity"][tag] = value
        elif parent == "StageGain" and tag in ("Value", "Frequency"):
            stage["gain"][tag] = value
        elif parent == "Decimation" and tag in ("InputSampleRate", "Factor", "Offset", "Delay", "Correction"):
            stage["decimation"][tag] = value
        elif parent in ("Pole", "Zero") and tag in ("Real", "Imaginary"):
            frames[-1]["complex"][tag] = value
        elif tag in ("Pole", "Zero"):
            c = frame["complex"]
            if set(c) != {"Real", "Imaginary"}:
                fail()
            target = stage["poles" if tag == "Pole" else "zeros"]
            if len(target) >= 128:
                fail("waveform_limit")
            target.append((c["Real"], c["Imaginary"]))
            counts["coefficients"] += 2
        elif tag in ("Coefficient", "Amplitude", "Phase") and "Response" in ancestors:
            counts["coefficients"] += 1
            marker = ("list_count", tag)
            counts_local = frames[-1].get(marker, 0) + 1
            frames[-1][marker] = counts_local
            if counts_local > 4096:
                fail("waveform_limit")
        elif parent in ("PolesZeros", "Coefficients", "FIR"):
            if tag in ("Numerator", "Denominator", "NumeratorCoefficient"):
                target = stage[
                    {"Numerator": "numerator", "Denominator": "denominator", "NumeratorCoefficient": "fir"}[tag]
                ]
                if len(target) >= 4096:
                    fail("waveform_limit")
                target.append(value)
                counts["coefficients"] += 1
            elif tag not in ("InputUnits", "OutputUnits", "Pole", "Zero"):
                stage["values"][tag] = value
        elif tag == "Stage":
            if stage["kind"] is None and set(stage["gain"]) == {"Value", "Frequency"}:
                stage["kind"] = "gain-only"
            stage = None
        elif tag == "Channel":
            result["channels"].append(channel)
            channel = response = None
        elif tag == "Station":
            station = None
        elif tag == "Network":
            network = None
        if counts["coefficients"] > 20000:
            fail("waveform_limit")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = text
    parser.XmlDeclHandler = declaration
    parser.StartDoctypeDeclHandler = forbidden
    parser.EntityDeclHandler = forbidden
    parser.ExternalEntityRefHandler = forbidden
    parser.UnparsedEntityDeclHandler = forbidden
    decoder = codecs.getincrementaldecoder(encoding)("strict")
    for i in range(0, len(raw), 4096):
        chunk = raw[i : i + 4096]
        decoder.decode(chunk, final=False)
        parser.Parse(chunk, False)
    decoder.decode(b"", final=True)
    parser.Parse(b"", True)
    result["counters"] = dict(counts)
    return result


def response_work(stages, fft_samples):
    if type(fft_samples) is not int or fft_samples % 2 or not 2 <= fft_samples <= 131072:
        fail("waveform_limit")
    return (fft_samples // 2 + 1) * (
        1 + sum(1 + sum(len(s[k]) for k in ("poles", "zeros", "numerator", "denominator", "fir")) for s in stages)
    )


def _stable_denominator(coefficients):
    """Real Schur recursion for roots of a0*z**n+...+an inside unit circle.

    Scaling is polynomial-invariant; strict equality is unsupported, not nudged.
    Work stays bounded by the already admitted coefficient counts.
    """
    a = list(coefficients)
    while len(a) > 1:
        scale = max(abs(x) for x in a)
        if not scale or not a[0]:
            return False
        a = [x / scale for x in a]
        if abs(a[-1]) >= abs(a[0]):
            return False
        reflection = a[-1] / a[0]
        a = [a[j] - reflection * a[-1 - j] for j in range(len(a) - 1)]
        if not all(math.isfinite(x) for x in a):
            return False
    return bool(a) and a[0] != 0


def resolve_channel(dto, identity, t0, t1, fs):
    """Nested epoch join and science admission BEFORE native inventory/response."""
    matches = [
        c for c in dto["channels"] if (c["network"]["code"], c["station"]["code"], c["location"], c["code"]) == identity
    ]
    if not matches:
        return None, ["epoch_missing"]
    covering, partial = [], False
    for c in matches:
        intervals = []
        for owner in (c["network"], c["station"], c):
            start, end = owner["start"], owner["end"]
            # StationXML dateTime without a zone denotes UTC in FDSN metadata; no sample-clock accuracy follows.
            if start is None:
                intervals = []
                break
            intervals.append((_epoch_date(start), _epoch_date(end) if end else None))
        if not intervals:
            continue
        low = max(a for a, b in intervals)
        ends = [b for a, b in intervals if b is not None]
        high = min(ends) if ends else None
        if high is not None and low >= high:
            continue
        if low <= t0 and (high is None or t1 <= high):
            covering.append(c)
        elif low < t1 and (high is None or high > t0):
            partial = True
    if len(covering) > 1 or (covering and partial):
        return None, ["epoch_ambiguous"]
    if not covering:
        return None, ["epoch_partial" if partial else "epoch_missing"]
    c = covering[0]
    v = c["values"]
    reasons = []
    if (
        not all(k in v for k in ("Latitude", "Longitude", "Elevation", "Depth", "Azimuth", "Dip"))
        or not -90 <= v.get("Latitude", 100) <= 90
        or not -180 <= v.get("Longitude", 200) <= 180
        or not 0 <= v.get("Azimuth", 400) < 360
        or not -90 <= v.get("Dip", 100) <= 90
    ):
        reasons.append("orientation_missing")
    if v.get("SampleRate") != fs:
        reasons.append("rate_mismatch")
    r = c["response"]
    if not r or not r["stages"] or r["unsupported"]:
        return c, reasons + ["response_stage_unsupported"]
    stages = r["stages"]
    sensitivity = r["sensitivity"]
    aliases = {
        "M": "m",
        "m": "m",
        "M/S": "m/s",
        "m/s": "m/s",
        "M/SEC": "m/s",
        "M/S**2": "m/s2",
        "m/s2": "m/s2",
        "M/SEC**2": "m/s2",
        "M/(S**2)": "m/s2",
        "M/S/S": "m/s2",
    }
    counts_units = ("COUNTS", "counts", "COUNT")

    def intermediate_unit(unit):
        return aliases.get(unit) or ("counts" if unit in counts_units else "V" if unit == "V" else None)

    effective = [dict(stage["units"]) for stage in stages]
    ledger = []
    gain_only = [i for i, stage in enumerate(stages) if stage["kind"] == "gain-only"]
    for i, stage in enumerate(stages):
        entry = {
            "stage_number": stage["number"],
            "original_input_unit": stage["units"].get("InputUnits"),
            "original_output_unit": stage["units"].get("OutputUnits"),
            "effective_input_unit": stage["units"].get("InputUnits"),
            "effective_output_unit": stage["units"].get("OutputUnits"),
            "derivation": "provider-declared",
            "neighbour_stage_numbers": [],
        }
        if stage["kind"] == "gain-only":
            entry["derivation"] = "unresolved"
            if (
                len(gain_only) == 1
                and 0 < i < len(stages) - 1
                and stage["gain"].get("Value") == 1
                and 0 < stage["gain"].get("Frequency", 0) < fs / 2
                and not stage["decimation"]
                and not stage["units"]
            ):
                left = stages[i - 1]["units"].get("OutputUnits")
                right = stages[i + 1]["units"].get("InputUnits")
                if intermediate_unit(left) is not None and intermediate_unit(left) == intermediate_unit(right):
                    effective[i] = {"InputUnits": left, "OutputUnits": right}
                    entry.update(
                        effective_input_unit=left,
                        effective_output_unit=right,
                        derivation="transparent-unity-gain-between-equal-declared-units",
                        neighbour_stage_numbers=[stages[i - 1]["number"], stages[i + 1]["number"]],
                    )
        ledger.append(entry)
    c["response_unit_ledger"] = ledger
    first = stages[0]["units"].get("InputUnits")
    c["native_unit"] = aliases.get(first)
    if first not in aliases or stages[-1]["units"].get("OutputUnits") not in counts_units:
        reasons.append("response_units_missing")
    if sensitivity.get("InputUnits") != first or sensitivity.get("OutputUnits") not in counts_units:
        reasons.append("response_chain_inconsistent")
    if not sensitivity.get("Value", 0) > 0 or not 0 < sensitivity.get("Frequency", 0) < fs / 2:
        reasons.append("response_sensitivity_inconsistent")
    previous = None
    next_rate = None
    for i, s in enumerate(stages):
        if s["number"] != i + 1:
            reasons.append("response_chain_inconsistent")
        units = effective[i]
        inp, out = units.get("InputUnits"), units.get("OutputUnits")
        if not inp or not out:
            reasons.append("response_units_missing")
        if previous is not None and (inp is None or inp.upper() != previous.upper()):
            reasons.append("response_chain_inconsistent")
        previous = out
        kind = s["kind"]
        if kind not in ("PolesZeros", "Coefficients", "FIR") and not (
            kind == "gain-only" and ledger[i]["derivation"] == "transparent-unity-gain-between-equal-declared-units"
        ):
            reasons.append("response_stage_unsupported")
        d = s["decimation"]
        val = s["values"]
        stage_fs = d.get("InputSampleRate", fs)
        if d:
            if (
                set(d) != {"InputSampleRate", "Factor", "Offset", "Delay", "Correction"}
                or not stage_fs > 0
                or type(d.get("Factor")) is not int
                or d["Factor"] <= 0
                or not 0 <= d.get("Offset", -1) < d["Factor"]
            ):
                reasons.append("response_chain_inconsistent")
            else:
                if next_rate is not None and next_rate != stage_fs:
                    reasons.append("response_chain_inconsistent")
                next_rate = stage_fs / d["Factor"]
        gain = s["gain"]
        frequency = gain.get("Frequency")
        dc_allowed = False
        if kind == "FIR" and frequency == 0 and s["fir"]:
            try:
                taps = s["fir"]
                symmetry = val.get("Symmetry")
                dc = (
                    math.fsum(taps)
                    if symmetry == "NONE"
                    else (
                        2 * math.fsum(taps[:-1]) + taps[-1]
                        if symmetry == "ODD"
                        else 2 * math.fsum(taps)
                        if symmetry == "EVEN"
                        else float("nan")
                    )
                )
                dc_allowed = bool(d and inp and out and math.isfinite(dc) and dc != 0)
            except OverflowError:
                pass
        if not gain.get("Value", 0) > 0 or not (dc_allowed or frequency is not None and 0 < frequency < stage_fs / 2):
            reasons.append("response_chain_inconsistent")
        if kind == "PolesZeros":
            transfer = val.get("PzTransferFunctionType")
            if transfer not in ("LAPLACE (RADIANS/SECOND)", "LAPLACE (HERTZ)", "DIGITAL (Z-TRANSFORM)"):
                reasons.append("response_stage_unsupported")
            if not val.get("NormalizationFactor", 0) > 0 or not 0 < val.get("NormalizationFrequency", 0) < stage_fs / 2:
                reasons.append("response_chain_inconsistent")
            if transfer == "DIGITAL (Z-TRANSFORM)" and not d:
                reasons.append("response_chain_inconsistent")
            for k in ("poles", "zeros"):
                paired = Counter(s[k])
                if any(imag and paired[(real, -imag)] != n for (real, imag), n in paired.items()):
                    reasons.append("response_chain_inconsistent")
            if any(
                (math.hypot(real, imag) >= 1 if transfer == "DIGITAL (Z-TRANSFORM)" else real > 0)
                for real, imag in s["poles"]
            ):
                reasons.append("response_stage_unsupported")
        elif kind == "Coefficients":
            if val.get("CfTransferFunctionType") != "DIGITAL":
                reasons.append("response_stage_unsupported")
            if not d or (s["denominator"] and s["denominator"][0] == 0):
                reasons.append("response_chain_inconsistent")
            elif s["denominator"] and not _stable_denominator(s["denominator"]):
                reasons.append("response_stage_unsupported")
        elif kind == "FIR":
            if val.get("Symmetry") not in ("NONE", "ODD", "EVEN") or not s["fir"] or not d:
                reasons.append("response_chain_inconsistent")
    if next_rate is not None and next_rate != fs:
        reasons.append("response_chain_inconsistent")
    if not reasons:
        az, dip = math.radians(v["Azimuth"]), math.radians(v["Dip"])
        c["projection_enu"] = [math.cos(dip) * math.sin(az), math.cos(dip) * math.cos(az), -math.sin(dip)]
    return c, [code for code in REASONS if code in reasons]
