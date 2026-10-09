"""Lossless transport controls, not native containment or field acceptance."""

import copy
import json
import struct

import pytest

import waveform_input as wi
from tests.data.test_waveform_input import record, request


def api():
    return wi.pack_record_ledger, wi.iter_record_ledger


def with_intervals(rows):
    cursors = {}
    for row in rows:
        start = cursors.get(row["channel_index"], 0)
        row["sample_interval"] = {"start": start, "stop": start + row["npts"]}
        cursors[row["channel_index"]] = start + row["npts"]
    return rows


def steim_record(encoding):
    """Literal two-sample STEIM positive, no native writer as scanner oracle."""
    raw = bytearray(record([1, 2]))
    raw[52] = encoding
    # First two integration constants then one packed difference word.
    words = [0, 1, 2, 0] + [0] * 12
    words[0] = 1 << 24  # word3: four8-bit differences, first discarded by decoder
    words[3] = 0x00010000
    struct.pack_into(">16I", raw, 64, *words)
    return bytes(raw)


@pytest.mark.parametrize("variant", ["integer", "little", "flags", "steim1", "steim2"])
def test_exact_scanner_row_roundtrip(variant):
    pack, rows = api()
    if variant.startswith("steim"):
        raw = steim_record(10 if variant == "steim1" else 11)
    else:
        options = (
            {"order": "<", "sample_order": "<"} if variant == "little"
            else {"flags": (2, 32, 129), "correction": -17, "microsecond": -11}
            if variant == "flags" else {}
        )
        raw = record([1, 2, 3], **options)
    original = with_intervals(wi.scan_miniseed(raw, request()))
    before = copy.deepcopy(original)
    packed = pack(original)
    assert packed["schema"] == "caos.waveform-record-ledger/v1"
    assert list(rows(packed)) == before
    assert original == before
    assert list(rows(json.loads(json.dumps(packed)))) == before
    assert type(list(rows(packed))[0]["correction_already_applied"]) is bool


def upper_rows():
    req = request()
    req["channels"] = [{**req["channels"][0], "channel": name} for name in ("BHZ", "BHN", "BHE")]
    chunks = []
    sequence = 0
    for ci, amount in enumerate((1366, 1365, 1365)):
        cursor = 0
        for index in range(amount):
            count = (index + 1) * 60000 // amount - index * 60000 // amount
            raw = bytearray(record([ci] * count, start_us=cursor * 5000, rate=200))
            sequence += 1
            raw[:6] = f"{sequence:06d}".encode("ascii")
            raw[15:18] = req["channels"][ci]["channel"].encode("ascii")
            chunks.append(bytes(raw))
            cursor += count
        assert cursor == 60000
    raw = b"".join(chunks)
    assert len(raw) == 16777216
    records = with_intervals(wi.scan_miniseed(raw, req))
    assert len(records) == 4096 and sum(r["npts"] for r in records) == 180000
    return [[row for row in records if row["channel_index"] == ci] for ci in range(3)]


def test_full_admitted_ledger_fits_without_raising_cap():
    pack, rows = api()
    original = upper_rows()
    repeated = {"channels": [{"records": group} for group in original]}
    raw = json.dumps(repeated, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
    assert len(raw) == 2187180
    with pytest.raises(wi.WaveformInputError, match="local limit"):
        wi.native_precount(repeated, 2097152, max_nodes=2097152, max_depth=16)
    compact = {"channels": [{"records": pack(group)} for group in original]}
    length = wi.native_precount(compact, 2097152, max_nodes=2097152, max_depth=16)
    assert length < 1048576  # measured stronger bound, not a relaxed metadata ceiling
    assert length == len(json.dumps(compact, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    for channel, expected in zip(compact["channels"], original):
        assert list(rows(channel["records"])) == expected


def test_empty_ledger_is_explicit_and_lossless():
    pack, rows = api()
    assert list(rows(pack([]))) == []


@pytest.mark.parametrize("change", [
    "schema", "extra", "fields", "field_duplicate", "row_short", "row_long", "bool_integer",
    "float_integer", "null_required", "order", "rate", "nslc", "sequence", "quality",
    "flags", "microsecond", "correction_bit", "interval", "interval_extra", "steim_extra",
    "cycle", "nan", "unsafe_integer", "row_count",
])
def test_closed_ledger_rejects_mutation(change):
    pack, rows = api()
    packed = pack(with_intervals(wi.scan_miniseed(record([1, 2, 3]), request())))
    fields, row = packed["fields"], packed["rows"][0]
    def set_cell(name, value):
        row[fields.index(name)] = value
    if change == "schema": packed["schema"] = "unknown"
    elif change == "extra": packed["extra"] = 1
    elif change == "fields": fields.reverse()
    elif change == "field_duplicate": fields[1] = fields[0]
    elif change == "row_short": row.pop()
    elif change == "row_long": row.append(0)
    elif change == "bool_integer": set_cell("npts", True)
    elif change == "float_integer": set_cell("npts", 3.0)
    elif change == "null_required": set_cell("npts", None)
    elif change == "order": set_cell("header_order", "native")
    elif change == "rate": set_cell("sample_rate_hz", 1)
    elif change == "nslc": set_cell("nslc", ["XX", "TEST", "", "BHZ", "extra"])
    elif change == "sequence": set_cell("sequence", "1")
    elif change == "quality": set_cell("quality", "X")
    elif change == "flags": set_cell("io_clock_flags", 64)
    elif change == "microsecond": set_cell("microsecond_offset", 128)
    elif change == "correction_bit": set_cell("correction_already_applied", True)
    elif change == "interval": set_cell("sample_interval", {"start": 0, "stop": 2})
    elif change == "interval_extra": set_cell("sample_interval", {"start": 0, "stop": 3, "extra": 0})
    elif change == "steim_extra": set_cell("steim_x0", 0)
    elif change == "cycle": set_cell("nslc", row)
    elif change == "nan": set_cell("start_us", float("nan"))
    elif change == "unsafe_integer": set_cell("start_us", 9007199254740992)
    elif change == "row_count": packed["rows"] *= 4097
    with pytest.raises(wi.WaveformInputError):
        list(rows(packed))


@pytest.mark.parametrize("change", ["missing", "extra", "steim_missing", "sample_total"])
def test_packer_rejects_unknown_or_unbounded_original(change):
    pack, _ = api()
    original = with_intervals(wi.scan_miniseed(steim_record(11), request()))
    if change == "missing": original[0].pop("sequence")
    elif change == "extra": original[0]["extra"] = 1
    elif change == "steim_missing": original[0].pop("steim_x0")
    elif change == "sample_total": original *= 30001
    with pytest.raises(wi.WaveformInputError):
        pack(original)


@pytest.mark.parametrize("change", ["channel", "nslc", "interval_cursor"])
def test_ledger_preserves_one_channel_and_cumulative_intervals(change):
    pack, rows = api()
    original = with_intervals(wi.scan_miniseed(record([1, 2]) + record([3, 4], start_us=20000), request()))
    if change == "channel": original[1]["channel_index"] = 1
    elif change == "nslc": original[1]["nslc"][3] = "BHN"
    elif change == "interval_cursor": original[1]["sample_interval"] = {"start": 1, "stop": 3}
    with pytest.raises(wi.WaveformInputError):
        list(rows(pack(original)))
