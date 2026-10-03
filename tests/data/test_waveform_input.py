"""Test-first local M08 input gates; native malformed execution is NOT assigned."""
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from waveform_input import (WaveformInputError, validate_request, scan_miniseed,
                            scan_stationxml, utc_us, scientific_identity, bounded_json)
from waveform_processing import process_waveform_record

RECIPE = json.loads((ROOT / "tests/fixtures/waveform_m08/authored-controls.json").read_text())


def request():
    return {
        "schema": "caos.local-waveform-request.v1",
        "channels": [{"network": "XX", "station": "TEST", "location": "", "channel": "BHZ"}],
        "conditioning_start_utc": "2020-01-01T00:00:00Z",
        "conditioning_end_utc": "2020-01-01T00:00:40Z",
        "analysis_start_utc": "2020-01-01T00:00:08Z",
        "analysis_end_utc": "2020-01-01T00:00:32Z",
        "representation": "unrestituted_integer_counts",
        "source": {"kind": "user", "citation": "authored control", "provider_url": None,
                   "declared_sha256": None, "rights": "private-use-attested",
                   "processing_statement": "Original authored integer counts; no previous correction"},
        "adc_rails": [None],
        "processing": {"output": "native", "prefilter_hz": [.5, 1., 20., 25.],
                       "water_level_db": 60.0, "taper_fraction": .05,
                       "bandpass_hz": [2., 10.], "filter_order": 4,
                       "filter_mode": "offline-zero-phase", "edge_guard_s": 5.,
                       "sta_s": .2, "lta_s": 2., "threshold_on": 3.5,
                       "threshold_off": 1.5, "refractory_s": 1.,
                       "welch_segment_samples": 256}}


def record(values, *, start_us=0, order=">", sample_order=">", flags=(0, 0, 0),
           correction=0, microsecond=None, rate=100):
    """Literal SEED2 record, no native writer as an input oracle."""
    from datetime import datetime, timedelta
    stamp = datetime(2020, 1, 1) + timedelta(microseconds=start_us)
    out = bytearray(4096)
    out[:20] = b"000001D TEST   BHZXX"
    assert len(out[:20]) == 20
    struct.pack_into(order + "HHBBBBHHhhBBBBiHH", out, 20,
                     stamp.year, stamp.timetuple().tm_yday, stamp.hour, stamp.minute,
                     stamp.second, 0, stamp.microsecond // 100, len(values), rate, 1,
                     *flags, 1 if microsecond is None else 2, correction, 64, 48)
    struct.pack_into(order + "HHBBBB", out, 48, 1000, 0 if microsecond is None else 56,
                     3, 1 if sample_order == ">" else 0, 12, 0)
    if microsecond is not None:
        struct.pack_into(order + "HHBbBB", out, 56, 1001, 0, 80, microsecond, 0, 0)
    struct.pack_into(sample_order + str(len(values)) + "i", out, 64, *values)
    return bytes(out)


def source(values=None):
    if values is None:
        values = [round(10000 * math.sin(2 * math.pi * 3 * n / 100)
                        + 500 * math.sin(2 * math.pi * 17 * n / 100)) for n in range(4000)]
    return b"".join(record(values[i:i + 1000], start_us=i * 10000)
                    for i in range(0, len(values), 1000))


def inventory(*, gain=1000, start="2019-01-01T00:00:00Z", end="2021-01-01T00:00:00Z",
              units="M/S", azimuth=0, dip=-90, poles="", zeros="", normalization=1,
              sensitivity=None):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1" schemaVersion="1.2">
<Source>authored control</Source><Created>2020-01-01T00:00:00Z</Created>
<Network code="XX" startDate="2019-01-01T00:00:00Z"><Station code="TEST" startDate="2019-01-01T00:00:00Z">
<Latitude>0</Latitude><Longitude>0</Longitude><Elevation>0</Elevation><Site><Name>authored</Name></Site>
<Channel code="BHZ" locationCode="" startDate="{start}" endDate="{end}">
<Latitude>0</Latitude><Longitude>0</Longitude><Elevation>0</Elevation><Depth>0</Depth>
<Azimuth>{azimuth}</Azimuth><Dip>{dip}</Dip><SampleRate>100</SampleRate><Response>
<InstrumentSensitivity><Value>{gain if sensitivity is None else sensitivity}</Value><Frequency>3</Frequency>
<InputUnits><Name>{units}</Name></InputUnits><OutputUnits><Name>COUNTS</Name></OutputUnits></InstrumentSensitivity>
<Stage number="1"><PolesZeros><InputUnits><Name>{units}</Name></InputUnits><OutputUnits><Name>COUNTS</Name></OutputUnits>
<PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType><NormalizationFactor>{normalization}</NormalizationFactor>
<NormalizationFrequency>3</NormalizationFrequency>{zeros}{poles}</PolesZeros>
<StageGain><Value>{gain}</Value><Frequency>3</Frequency></StageGain></Stage>
</Response></Channel></Station></Network></FDSNStationXML>'''.encode()


def rejected(call, code=None):
    with pytest.raises(WaveformInputError) as info:
        call()
    error = info.value
    assert error.__cause__ is None and error.__context__ is None
    assert error.field in {"document", "request", "channels", "processing", "source", "adc_rails"}
    if code:
        assert error.code == code
    assert "SECRET" not in str(error)
    return error


def test_exact_bytes_hash_domains_and_immutability():
    req = request()
    pristine = copy.deepcopy(req)
    raw, xml = source(), inventory()
    result = process_waveform_record(raw, xml, req)
    assert req == pristine
    assert result.metadata["sources"]["miniseed"]["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result.metadata["sources"]["stationxml"]["raw_sha256"] == hashlib.sha256(xml).hexdigest()
    assert result.metadata["request"]["scientific_sha256"] == scientific_identity(req)
    changed = copy.deepcopy(req)
    changed["processing"]["water_level_db"] = 60
    assert scientific_identity(req) != scientific_identity(changed)
    changed["source"]["citation"] = "\U0001d11e -0.0"
    assert scientific_identity(changed) == hashlib.sha256(json.dumps(changed, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()
    for arr in result.arrays.values():
        assert arr.flags.owndata and not arr.flags.writeable and arr.flags.c_contiguous
    for bad in (bytearray(raw), "https://SECRET/", memoryview(raw)):
        rejected(lambda: process_waveform_record(bad, xml, req), "waveform_type")


@pytest.mark.parametrize("offset,value", [(7, 0), (27, 1), (54, 255), (52, 4), (55, 1)])
def test_record_preflight_before_native_decode(offset, value):
    bad = bytearray(record([1, 2, 3]))
    bad[offset] = value
    rejected(lambda: scan_miniseed(bytes(bad), validate_request(request())))
    rejected(lambda: scan_miniseed(b"x" * (16777216 + 1), validate_request(request())), "waveform_limit")


@pytest.mark.parametrize("bad", [b"\xef\xbb\xbf<x/>", b"<x/>", b"<!DOCTYPE x><x/>",
    b'<!DOCTYPE x [<!ENTITY z "SECRET">]><x>&z;</x>', b"\xff<x/>",
    b'<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1" schemaVersion="9"/>'])
def test_stationxml_preflight_before_inventory(bad):
    rejected(lambda: scan_stationxml(bad))


def test_time_corrections_rates_gaps_and_overlaps():
    req = validate_request(request())
    first = scan_miniseed(record([1, 2], correction=10, microsecond=-7), req)[0]
    applied = scan_miniseed(record([1, 2], correction=10, microsecond=-7, flags=(2, 0, 0)), req)[0]
    assert first["start_us"] == utc_us("2020-01-01T00:00:00Z") + 993
    assert applied["start_us"] == utc_us("2020-01-01T00:00:00Z") - 7
    for endian in (">", "<"):
        for payload in (">", "<"):
            assert scan_miniseed(record([1], order=endian, sample_order=payload), req)[0]["sample_rate_hz"] == 100
    for second_start, reason in [(10000001, "gap"), (9999999, "overlap")]:
        raw = record(list(range(1000))) + record(list(range(1000)), start_us=second_start, microsecond=second_start % 100)
        result = process_waveform_record(raw, inventory(), request())
        assert result.metadata["status"] == "qc_only" and reason in result.metadata["qc"]["reasons"]
    rejected(lambda: scan_miniseed(record([1], rate=30), req))


def test_nested_identity_full_window_epoch_and_qc_only():
    for xml, reason in [(inventory(end="2020-01-01T00:00:20Z"), "epoch_partial"),
                        (inventory().replace(b'code="TEST"', b'code="OTHER"'), "epoch_missing")]:
        result = process_waveform_record(source(), xml, request())
        assert result.metadata["status"] == "qc_only"
        assert reason in result.metadata["qc"]["reasons"]
        assert result.metadata["candidates"] is None
        assert all(name[1] == "counts" for name in result.arrays)


def test_clipping_flags_unknown_rails_and_missing_components():
    for raw, reason in [(source([1] * 4000), "flat"),
                        (source([50000] * 4 + list(range(3996))), "clip_suspected"),
                        (record(list(range(1000)), flags=(0, 0, 2)) + source()[4096:], "blocking_flags")]:
        result = process_waveform_record(raw, inventory(), request())
        assert result.metadata["status"] == "qc_only" and reason in result.metadata["qc"]["reasons"]
    req = request()
    req["source"]["rights"] = "unknown"
    result = process_waveform_record(source(), inventory(), req)
    assert result.metadata["qc"]["reasons"] == ["rights_ineligible"] and result.arrays == {}


def test_native_request_bounds_types_and_safe_errors():
    for value in (True, float("inf"), float("nan"), "SECRET"):
        req = request()
        req["processing"]["sta_s"] = value
        rejected(lambda: validate_request(req), "waveform_contract")
    req = request()
    req["source"]["citation"] = "SECRET" * 500
    rejected(lambda: validate_request(req), "waveform_limit")
    req = request()
    req["extra"] = req
    rejected(lambda: validate_request(req))


def test_bounded_artifact_arrays_and_independent_reopen():
    # Library descriptors only; writer/reopen portion remains explicitly held.
    result = process_waveform_record(source(), inventory(), request())
    total = 0
    for desc in result.metadata["array_descriptors"]:
        arr = result.arrays[(desc["channel_index"], desc["name"])]
        assert desc["shape"] == list(arr.shape) and desc["bytes"] == arr.nbytes
        assert desc["sha256"] == hashlib.sha256(arr.tobytes()).hexdigest()
        assert desc["dtype"] in {"<i4", "<f8", "|b1"}
        total += arr.nbytes
    assert total < 33554432


def test_frozen_sources_and_local_only_nonclaims():
    pins = {"data-pipeline/phase_picking.py": "daef04c71c81c6c3b63bdaab72d6ccd74445bb2ee3268ff52004b3bae393938a",
            "data-pipeline/stead_phase.py": "48e29bde71337f949a021b34c8f51cf39746395338f4b46dfa873a42ee810e8e",
            "data-pipeline/phase_model.py": "9a9f8b7db70831cdf1a17051b19250a5c16ac420cf68a0377254a2ccaeb49791"}
    for path, digest in pins.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    result = process_waveform_record(source(), inventory(), request())
    assert result.metadata["field_truth"] is None
    assert not any(result.metadata["acceptance"].values())


@pytest.mark.parametrize("mutate", [
    lambda b: struct.pack_into(">H", b, 30, 65535),
    lambda b: struct.pack_into(">H", b, 50, 48),
    lambda b: struct.pack_into(">H", b, 46, 4094),
    lambda b: struct.pack_into(">H", b, 22, 367),
    lambda b: b.__setitem__(26, 60),
    lambda b: b.__setitem__(36, 128),
    lambda b: b.__setitem__(39, 2),
])
def test_complete_header_admission_negatives(mutate, monkeypatch):
    import waveform_processing as processing
    calls=[]
    monkeypatch.setattr(processing, "_decode_record", lambda *a: calls.append(a))
    bad=bytearray(record([1,2,3]))
    mutate(bad)
    rejected(lambda: process_waveform_record(bytes(bad),inventory(),request()))
    assert calls==[]


def test_xml_bounds_duplicates_and_declared_encoding(monkeypatch):
    import waveform_processing as processing
    calls=[]
    monkeypatch.setattr(processing,"_read_inventory",lambda *a: calls.append(a))
    good=inventory()
    variants=[good.replace(b'encoding="UTF-8"',b'encoding="ISO-8859-1"'),
              good.replace(b"<SampleRate>100</SampleRate>",b"<SampleRate>100</SampleRate>"*2),
              good.replace(b"<Source>authored control</Source>",b"<Source>"+b"x"*8193+b"</Source>"),
              good.replace(b"<Source>authored control</Source>",b'<x:include xmlns:x="http://www.w3.org/2001/XInclude" href="https://SECRET/"/>'),
              good.replace(b"<Source>authored control</Source>",b'<e:a xmlns:e="urn:authored">'*33+b'</e:a>'*33),
              good.replace(b"<NormalizationFactor>1",b"<NormalizationFactor>1e400")]
    for bad in variants:
        rejected(lambda: process_waveform_record(source(),bad,request()))
    assert calls==[]
    good=good.replace(b"authored control", "authored \U0001d11e".encode())
    assert scan_stationxml(good)["schema_version"]=="1.2"


@pytest.mark.parametrize("raw", [b'{"x":1,"\\u0078":2}', b'{"x":1e400}',
    b'{"x":9007199254740992}', b'{"x":"\\ud800"}', b'\xef\xbb\xbf{}',
    b'{"x":NaN}', b'{"x":01}', b'{"x":1.}', b'{"x":true,}', b'[1]SECRET'])
def test_reference_json_preallocation_grammar(raw):
    rejected(lambda: bounded_json(raw,1048576))


def test_native_json_type_semantics_and_precount():
    values=bounded_json(b'{"i":1,"f":1.0,"z":-0.0,"u":"\\ud834\\udd1e","under":1e-400}',1048576)
    assert type(values["i"]) is int and type(values["f"]) is float
    assert math.copysign(1,values["z"])==-1 and values["under"]==0.0
    assert values["u"]=="\U0001d11e"
    for bad in (b'['*9+b'0'+b']'*9, b'{"'+b'x'*65+b'":0}', b'{"x":"'+b'x'*2049+b'"}'):
        rejected(lambda: bounded_json(bad,1048576),"waveform_limit")
