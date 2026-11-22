"""Strict original-format additions; no OS containment or source repair."""

import hashlib
import math
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(ROOT / "tests/data"))
from test_waveform_input import inventory, request, source
from waveform_input import WaveformInputError, scan_stationxml, resolve_channel, utc_us
import waveform_evaluation as evaluation
import waveform_processing as processing


def three_stages(gain=1, neighbour="V", decimation=""):
    xml = inventory()
    end = xml.index(b"</Stage>") + len(b"</Stage>")
    prefix, stage = xml[:end].split(b'<Stage number="1">', 1)
    before = (
        prefix
        + b'<Stage number="1">'
        + stage.replace(b"<OutputUnits><Name>COUNTS</Name>", b"<OutputUnits><Name>V</Name>")
    )
    tail = f"""<Stage number="2"><StageGain><Value>{gain}</Value><Frequency>3</Frequency></StageGain>{decimation}</Stage>
<Stage number="3"><Coefficients><InputUnits><Name>{neighbour}</Name></InputUnits><OutputUnits><Name>COUNTS</Name></OutputUnits><CfTransferFunctionType>DIGITAL</CfTransferFunctionType><Numerator number="0">1</Numerator></Coefficients><Decimation><InputSampleRate>100</InputSampleRate><Factor>1</Factor><Offset>0</Offset><Delay>0</Delay><Correction>0</Correction></Decimation><StageGain><Value>1</Value><Frequency>3</Frequency></StageGain></Stage>"""
    return before + tail.encode() + xml[end:]


def resolved(xml):
    r = request()
    return resolve_channel(
        scan_stationxml(xml),
        ("XX", "TEST", "", "BHZ"),
        utc_us(r["conditioning_start_utc"]),
        utc_us(r["conditioning_end_utc"]),
        100,
    )


def test_declared_latin1_same_semantics_unchanged_raw_identity():
    raw = (
        inventory()
        .split(b"?>", 1)[1]
        .replace(b"<Source>authored control</Source>", b"<Source>authored caf\xe9</Source>")
    )
    # Replace only the authored declaration, never a provider source fixture.
    latin = b'<?xml version="1.0" encoding="ISO-8859-1"?>' + raw
    utf = b'<?xml version="1.0" encoding="UTF-8"?>' + raw.replace(b"\xe9", b"\xc3\xa9")
    assert scan_stationxml(latin)["channels"] == scan_stationxml(utf)["channels"]
    assert hashlib.sha256(latin).digest() != hashlib.sha256(utf).digest()


def test_latin1_decoded_utf8_token_expansion_caps_are_not_raw_byte_caps():
    template = b'<?xml version="1.0" encoding="ISO-8859-1"?>' + inventory().split(b"?>", 1)[1]
    at_cap = template.replace(b"authored control", b"\xe9" * 4096)
    assert scan_stationxml(at_cap)["channels"]
    above = template.replace(b"authored control", b"\xe9" * 4097)
    with pytest.raises(WaveformInputError) as caught:
        scan_stationxml(above)
    assert caught.value.code == "waveform_limit"


@pytest.mark.parametrize(
    "declaration",
    [
        b'<?xml version="1.1" encoding="UTF-8"?>',
        b'<?xml version="1.0" encoding="latin1"?>',
        b'<?xml version="1.0" encoding="UTF-16"?>',
        b'<?xml version="1.0" ' + b" " * 512 + b'encoding="UTF-8"?>',
    ],
)
def test_unknown_or_overlong_declaration_rejected(declaration):
    with pytest.raises(WaveformInputError):
        scan_stationxml(declaration + inventory().split(b"?>", 1)[1])


def test_unity_gain_only_requires_visible_bounded_unit_derivation():
    selected, reasons = resolved(three_stages())
    assert reasons == []
    assert selected["response"]["stages"][1]["kind"] == "gain-only"
    assert selected["response"]["stages"][1]["units"] == {}
    ledger = selected["response_unit_ledger"][1]
    assert ledger["original_input_unit"] is ledger["original_output_unit"] is None
    assert ledger["effective_input_unit"] == ledger["effective_output_unit"] == "V"
    assert ledger["derivation"] == "transparent-unity-gain-between-equal-declared-units"
    assert ledger["neighbour_stage_numbers"] == [1, 3]
    result = processing.process_waveform_record(source(), three_stages(), request())
    assert result.metadata["status"] == "computed"
    assert result.metadata["channels"][0]["response_unit_ledger"] == selected["response_unit_ledger"]
    np.testing.assert_allclose(result.arrays[(0, "response_real")], 1000, rtol=1e-10, atol=1e-9)
    np.testing.assert_allclose(result.arrays[(0, "response_imag")], 0, rtol=1e-10, atol=1e-9)


@pytest.mark.parametrize("change", ["unknown", "bool_stage", "neighbour", "original", "derivation"])
def test_seal_rejects_unknown_or_forged_optional_unit_ledger(change):
    from waveform_evaluation import seal_result

    out = processing.process_waveform_record(source(), three_stages(), request())
    item = out.metadata["channels"][0]["response_unit_ledger"][1]
    if change == "unknown":
        item["provider_verified"] = True
    elif change == "bool_stage":
        item["stage_number"] = True
    elif change == "neighbour":
        item["neighbour_stage_numbers"] = [1, 4]
    elif change == "original":
        item["original_input_unit"] = "V"
    else:
        item["derivation"] = "arbitrary-native-inference"
    with pytest.raises(WaveformInputError):
        seal_result(out)


@pytest.mark.parametrize(
    "gain,neighbour,decimation",
    [
        (2, "V", ""),
        (1, "A", ""),
        (
            1,
            "V",
            "<Decimation><InputSampleRate>100</InputSampleRate><Factor>1</Factor><Offset>0</Offset><Delay>0</Delay><Correction>0</Correction></Decimation>",
        ),
    ],
)
def test_gain_only_unknown_or_nontransparent_remains_qc(gain, neighbour, decimation):
    selected, reasons = resolved(three_stages(gain, neighbour, decimation))
    assert "response_stage_unsupported" in reasons or "response_units_missing" in reasons
    assert selected["response"]["stages"][1]["units"] == {}


def fir_dc(coefficients=(0.75, 0.25), symmetry="NONE", delay=0, correction=0):
    xml = inventory()
    start, stop = xml.index(b"<PolesZeros>"), xml.index(b"</PolesZeros>") + len(b"</PolesZeros>")
    taps = "".join(f'<NumeratorCoefficient i="{i}">{v}</NumeratorCoefficient>' for i, v in enumerate(coefficients))
    filt = f"""<FIR><InputUnits><Name>M/S</Name></InputUnits><OutputUnits><Name>COUNTS</Name></OutputUnits><Symmetry>{symmetry}</Symmetry>{taps}</FIR><Decimation><InputSampleRate>100</InputSampleRate><Factor>1</Factor><Offset>0</Offset><Delay>{delay}</Delay><Correction>{correction}</Correction></Decimation>""".encode()
    xml = xml[:start] + filt + xml[stop:]
    xml = xml.replace(
        b"<StageGain><Value>1000</Value><Frequency>3</Frequency>",
        b"<StageGain><Value>1000</Value><Frequency>0</Frequency>",
    )
    z = complex(math.cos(-2 * math.pi * 3 / 100), math.sin(-2 * math.pi * 3 / 100))
    magnitude = abs(sum(c * z**i for i, c in enumerate(coefficients)) / sum(coefficients))
    return xml.replace(
        b"<InstrumentSensitivity><Value>1000</Value>",
        f"<InstrumentSensitivity><Value>{1000 * magnitude}</Value>".encode(),
    )


def test_fir_dc_exact_frequency_and_independent_complex_phase_oracle():
    xml = fir_dc()
    selected, reasons = resolved(xml)
    assert reasons == []
    assert selected["response"]["stages"][0]["gain"]["Frequency"] == 0
    result = processing.process_waveform_record(source(), xml, request())
    assert result.metadata["status"] == "computed"
    f = result.arrays[(0, "response_frequency_hz")]
    actual = result.arrays[(0, "response_real")] + 1j * result.arrays[(0, "response_imag")]
    expected = 1000 * (0.75 + 0.25 * np.exp(-2j * np.pi * f / 100))
    np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-9)
    assert actual[240].imag < 0


def test_fir_dc_uses_explicit_correction_not_estimated_delay():
    # Asymmetric FIR: evalresp's default phase applies Correction, not Delay.
    xml = fir_dc(delay=0.041607, correction=0.041407)
    out = processing.process_waveform_record(source(), xml, request())
    assert out.metadata["status"] == "computed"
    f = out.arrays[(0, "response_frequency_hz")]
    actual = out.arrays[(0, "response_real")] + 1j * out.arrays[(0, "response_imag")]
    oracle = 1000 * (0.75 + 0.25 * np.exp(-2j * np.pi * f / 100)) * np.exp(2j * np.pi * f * 0.041407)
    np.testing.assert_allclose(actual, oracle, rtol=1e-10, atol=1e-9)
    wrong = 1000 * (0.75 + 0.25 * np.exp(-2j * np.pi * f / 100)) * np.exp(2j * np.pi * f * 0.041607)
    assert np.max(np.abs(actual - wrong)) > 1


@pytest.mark.parametrize("mutation", ["first", "last", "consecutive"])
def test_gain_only_cannot_infer_boundary_or_consecutive_units(mutation):
    xml = three_stages()
    a = xml.index(b'<Stage number="1">')
    b = xml.index(b'<Stage number="2">')
    c = xml.index(b'<Stage number="3">')
    d = xml.index(b"</Stage>", c) + len(b"</Stage>")
    if mutation == "first":
        xml = xml[:a] + xml[b:]
    elif mutation == "last":
        xml = xml[:c] + xml[d:]
    else:
        xml = (
            xml[:c] + xml[b:c].replace(b'number="2"', b'number="3"') + xml[c:].replace(b'number="3"', b'number="4"', 1)
        )
    _, reasons = resolved(xml)
    assert reasons
    assert processing.process_waveform_record(source(), xml, request()).metadata["status"] == "qc_only"


def test_zero_fir_dc_is_not_normalizable():
    xml = fir_dc().replace(b">0.25</NumeratorCoefficient>", b">-0.75</NumeratorCoefficient>")
    _, reasons = resolved(xml)
    assert "response_chain_inconsistent" in reasons


def test_native_unit_inference_and_coefficients_must_match_ledger(monkeypatch):
    original = processing._read_inventory

    def changed(raw):
        inv = original(raw)
        inv[0][0][0].response.response_stages[1].output_units = "COUNTS"
        return inv

    monkeypatch.setattr(processing, "_read_inventory", changed)
    result = processing.process_waveform_record(source(), three_stages(), request())
    assert result.metadata["status"] == "qc_only"
    assert "response_chain_inconsistent" in result.metadata["qc"]["reasons"]
    assert set(result.arrays) == {(0, "counts")}


def cloud_bytes(header_extra="", kind="eq", geographic="l"):
    return (
        f"38457511 {kind} {geographic} 2019/07/06,03:19:53.040 35.7695 -117.5993 8.00 7.10 w 0.5{header_extra}\n"
        "CI GSC HHZ -- 35.3018 -116.8057 1000.0 P c. i 1.0 88.43 14.878\n"
    ).encode()


def test_cloud_adapter_is_explicit_and_does_not_reassign_channel():
    converter = getattr(evaluation, "references_from_scedc_cloud_stp")
    raw = cloud_bytes()
    with pytest.raises(WaveformInputError):
        evaluation.references_from_stp(raw, "38457511", ("CI", "GSC", "", "HNZ"))
    selected = converter(raw, "38457511", ("CI", "GSC", "", "HNZ"))
    assert selected["rows"] == []
    assert selected["source_format"] == "scedc-cloud-stp-10/v1"
    assert selected["event_type"] == "eq" and selected["geographic_type"] == "l"
    same = converter(raw, "38457511", ("CI", "GSC", "", "HHZ"))
    assert same["rows"][0]["pick_utc"] == "2019-07-06T03:20:07.918000Z"
    assert same["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert same["rows"][0]["uncertainty_s"] is None


@pytest.mark.parametrize("extra,kind,geo", [(" extra", "eq", "l"), ("", "unknown", "l"), ("", "eq", "unknown")])
def test_unknown_cloud_variants_fail_closed(extra, kind, geo):
    converter = getattr(evaluation, "references_from_scedc_cloud_stp")
    with pytest.raises(WaveformInputError):
        converter(cloud_bytes(extra, kind, geo), "38457511", ("CI", "GSC", "", "HNZ"))
