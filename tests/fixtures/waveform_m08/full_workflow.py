"""Fixed authored nominal/upper inputs; no IO/native/controller on import/call."""

from datetime import datetime, timedelta
import hashlib
import json
import math
import struct

CASES = {"nominal1": (1, 100, 180), "nominal3": (3, 100, 180), "upper3": (3, 200, 300)}
CHANNELS = (("BHZ", 0, -90), ("BHN", 0, 0), ("BHE", 90, 0))


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def record(channel, sequence, rate, start_index, values):
    # Private generator-only fixed trusted values; not an untrusted format API.
    stamp = datetime(2020, 1, 1) + timedelta(microseconds=start_index * (1000000 // rate))
    out = bytearray(4096)
    out[:20] = f"{sequence:06d}D TEST   {channel}XX".encode("ascii")
    struct.pack_into(
        ">HHBBBBHHhhBBBBiHH",
        out,
        20,
        stamp.year,
        stamp.timetuple().tm_yday,
        stamp.hour,
        stamp.minute,
        stamp.second,
        0,
        stamp.microsecond // 100,
        len(values),
        rate,
        1,
        0,
        0,
        0,
        1,
        0,
        64,
        48,
    )
    struct.pack_into(">HHBBBB", out, 48, 1000, 0, 3, 1, 12, 0)
    struct.pack_into(">" + str(len(values)) + "i", out, 64, *values)
    return out


def xml_bytes(selected, rate):
    channels = []
    for name, azimuth, dip in selected:
        channels.append(f'''<Channel code="{name}" locationCode="" startDate="2019-01-01T00:00:00Z" endDate="2021-01-01T00:00:00Z">
<Latitude>0</Latitude><Longitude>0</Longitude><Elevation>0</Elevation><Depth>0</Depth>
<Azimuth>{azimuth}</Azimuth><Dip>{dip}</Dip><SampleRate>{rate}</SampleRate><Response>
<InstrumentSensitivity><Value>1000</Value><Frequency>3</Frequency><InputUnits><Name>M/S</Name></InputUnits><OutputUnits><Name>COUNTS</Name></OutputUnits></InstrumentSensitivity>
<Stage number="1"><PolesZeros><InputUnits><Name>M/S</Name></InputUnits><OutputUnits><Name>COUNTS</Name></OutputUnits><PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType><NormalizationFactor>1</NormalizationFactor><NormalizationFrequency>3</NormalizationFrequency></PolesZeros><StageGain><Value>1000</Value><Frequency>3</Frequency></StageGain></Stage>
</Response></Channel>''')
    return (
        """<?xml version="1.0" encoding="UTF-8"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1" schemaVersion="1.2"><Source>authored ordinary M08 workflow control</Source><Created>2020-01-01T00:00:00Z</Created>
<Network code="XX" startDate="2019-01-01T00:00:00Z"><Station code="TEST" startDate="2019-01-01T00:00:00Z"><Latitude>0</Latitude><Longitude>0</Longitude><Elevation>0</Elevation><Site><Name>authored, not field</Name></Site>
"""
        + "".join(channels)
        + """</Station></Network></FDSNStationXML>"""
    ).encode("ascii")


def make_case(case):
    if type(case) is not str or case not in CASES:
        raise ValueError("workflow_fixture_contract")
    count, rate, seconds = CASES[case]
    npts = rate * seconds
    # Bounds before selection/retained allocation; no configurable resource cap.
    if not (count in (1, 3) and rate in (100, 200) and npts <= 60000 and count * npts <= 180000):
        raise ValueError("workflow_fixture_contract")
    selected = CHANNELS[:count]
    identities = [{"network": "XX", "station": "TEST", "location": "", "channel": row[0]} for row in selected]
    raw = bytearray()
    sequence = 0
    for channel_index, (channel, _, _) in enumerate(selected):
        for start in range(0, npts, 1000):
            values = [
                round(
                    10000 * math.sin(2 * math.pi * 3 * i / rate + channel_index / 10)
                    + 500 * math.sin(2 * math.pi * 17 * i / rate)
                )
                for i in range(start, min(start + 1000, npts))
            ]
            sequence += 1
            raw.extend(record(channel, sequence, rate, start, values))
    mseed = bytes(raw)
    stamp = datetime(2020, 1, 1) + timedelta(seconds=seconds)
    submitted = {
        "schema": "caos.local-waveform-request.v1",
        "channels": identities,
        "conditioning_start_utc": "2020-01-01T00:00:00Z",
        "conditioning_end_utc": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "analysis_start_utc": "2020-01-01T00:01:00Z",
        "analysis_end_utc": "2020-01-01T00:04:00Z" if case == "upper3" else "2020-01-01T00:02:00Z",
        "representation": "unrestituted_integer_counts",
        "source": {
            "kind": "user",
            "citation": "Author-created ordinary M08 workflow control; not field data",
            "provider_url": None,
            "declared_sha256": hashlib.sha256(mseed).hexdigest(),
            "rights": "private-use-attested",
            "processing_statement": "Literal authored integer counts; no previous correction",
        },
        "adc_rails": [None] * count,
        "processing": {
            "output": "native",
            "prefilter_hz": [0.5, 1.0, 20.0, 25.0],
            "water_level_db": 60.0,
            "taper_fraction": 0.05,
            "bandpass_hz": [2.0, 10.0],
            "filter_order": 4,
            "filter_mode": "offline-zero-phase",
            "edge_guard_s": 5.0,
            "sta_s": 0.2,
            "lta_s": 2.0,
            "threshold_on": 3.5,
            "threshold_off": 1.5,
            "refractory_s": 1.0,
            "welch_segment_samples": 256,
        },
    }
    reference = {
        "schema": "caos.waveform-analyst-references.v1",
        "event_id": "1",
        "source": {
            "raw_sha256": hashlib.sha256(b"Author-created empty reference control, not catalogue bytes").hexdigest(),
            "citation": "Authored no-reference control; no field/catalogue truth",
            "rights": "private-use-attested",
        },
        "selection_sealed_before_scoring": True,
        "references": [],
    }
    inputs = {
        "mseed": mseed,
        "stationxml": xml_bytes(selected, rate),
        "request": encode(submitted),
        "reference": encode(reference),
    }
    return {
        "schema": "caos.authored-m08-workflow.v1",
        "case": case,
        "origin": "authored_not_field",
        **inputs,
        "manifest": {
            "schema": "caos.authored-m08-workflow-input.v1",
            "case": case,
            "origin": "authored_not_field",
            "sample_rate_hz": rate,
            "samples_per_channel": npts,
            "samples_total": count * npts,
            "channels": identities,
            "inputs": {
                name: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for name, body in inputs.items()
            },
        },
    }
