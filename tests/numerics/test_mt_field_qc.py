"""M06 source identity and independent tensor admission, including field negative control."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from mt_field_qc import MTFieldQCError, _provider_screen, inspect_edi, phase_tensor_diagnostic, run, tensor_gate
from sources import load_ledger

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "data/fixtures/edi/halfspace-100-native.edi"
FIELD = ROOT / "data/downloads/auslamp-nsw/C15.edi"
FIELD_RECEIPT = ROOT / "data/raw/mt/auslamp-nsw-c15-m06-admission.json"


def _change_first_value(text: str, block: str, value: str) -> str:
    start = text.index(">" + block)
    first_line_end = text.index("\n", start)
    next_block = text.index("\n>", first_line_end)
    body = text[first_line_end:next_block]
    old = body.split()[0]
    return text[:first_line_end] + body.replace(old, value, 1) + text[next_block:]


def test_raw_blocks_and_parser_agree():
    checked = inspect_edi(FIXTURE)
    assert checked["frequency_count"] == 24
    assert checked["parser_agreement"].startswith("all original FREQ")
    assert checked["rotation"]["zrot_unique_deg"] == [0.0]
    assert checked["rotation"]["channel_layout"]["EX"]["dipole_length_m"] == 100
    assert checked["tensor_1d"]["passes"]
    assert all(value == 0 for value in checked["tensor_1d"]["wrms"].values())


def test_geometry_and_rotation_invariance(tmp_path):
    checked = inspect_edi(FIXTURE)
    assert checked["tensor_1d"]["quarter_turn_invariance_max_abs_error"] < 1e-14
    text = FIXTURE.read_text(encoding="utf-8")
    bad = tmp_path / "wrong-axis.edi"
    bad.write_text(text.replace("CHTYPE=EY X=0 Y=0 X2=0 Y2=100", "CHTYPE=EY X=0 Y=0 X2=100 Y2=0"), encoding="utf-8")
    with pytest.raises(MTFieldQCError, match="orthogonal"):
        inspect_edi(bad)


def test_bad_variance_and_rotation_fail_closed(tmp_path):
    text = FIXTURE.read_text(encoding="utf-8")
    variance = tmp_path / "zero-variance.edi"
    variance.write_text(_change_first_value(text, "ZXX.VAR", "0"), encoding="utf-8")
    with pytest.raises(MTFieldQCError, match="strictly positive"):
        inspect_edi(variance)
    rotation = tmp_path / "unproven-rotation.edi"
    rotation.write_text(_change_first_value(text, "ZROT", "17"), encoding="utf-8")
    with pytest.raises(MTFieldQCError, match="zero ZROT"):
        inspect_edi(rotation)
    extra = tmp_path / "after-end.edi"
    extra.write_text(text + "\n>FREQ // 1\n1\n", encoding="utf-8")
    with pytest.raises(MTFieldQCError, match="terminal END"):
        inspect_edi(extra)


def test_independent_tensor_gate():
    frequency = np.geomspace(0.01, 100, 24)
    amplitude = (1 + 1j) * np.sqrt(frequency)
    tensor = np.zeros((len(frequency), 2, 2), dtype=complex)
    tensor[:, 0, 1], tensor[:, 1, 0] = amplitude, -amplitude
    variance = np.broadcast_to((0.02 * abs(amplitude))[:, None, None] ** 2, tensor.shape).copy()
    accepted = tensor_gate(tensor, variance)
    assert accepted["passes"] and accepted["median_relative_distance_to_1d"] == 0
    assert phase_tensor_diagnostic(tensor)["median_scalar_departure"] < 1e-12
    tensor[:, 0, 0] = 2 * amplitude
    rejected = tensor_gate(tensor, variance)
    assert not rejected["passes"]
    assert rejected["wrms"]["xx"] > 3
    assert rejected["quarter_turn_invariance_max_abs_error"] < 1e-14


def test_pinned_field_receipt():
    if not FIELD.is_file():
        pytest.skip("Acquire the ignored C15 EDI using the documented command")
    station = load_ledger()["auslamp-nsw-c15"]
    assert FIELD.stat().st_size == station["expected_bytes"]
    assert hashlib.sha256(FIELD.read_bytes()).hexdigest() == station["sha256"]
    provider = _provider_screen(station, ROOT, station["sha256"], 35)
    assert provider["classification"] == "1-D"
    for key, filename in (
        ("station_record_sha256", "auslamp-nsw-c15-station.json"),
        ("dimensionality_record_sha256", "auslamp-nsw-c15-dimensionality.json"),
    ):
        assert hashlib.sha256((ROOT / "data/raw/mt" / filename).read_bytes()).hexdigest() == station[key]


def test_ineligible_never_becomes_inverse():
    if not FIELD.is_file():
        pytest.skip("Acquire the ignored C15 EDI using the documented command")
    result = run()
    assert result["status"] == "ineligible"
    assert not result["one_d_inversion_eligible"]
    assert not result["inversion_performed"] and result["methods"] == {}
    assert result["predicted"] is None and result["heldout_metrics"] is None
    assert result["truth"] is None
    assert "complex_tensor_inconsistent_with_isotropic_1d_at_declared_variance" in result["reason_codes"]
    assert result["qc"]["tensor_1d"]["wrms"]["antisymmetry"] > 3
    payload = FIELD_RECEIPT.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    assert FIELD_RECEIPT.with_suffix(".json.sha256").read_text(encoding="ascii").startswith(digest)
    assert json.loads(payload)["source_sha256"] == load_ledger()["auslamp-nsw-c15"]["sha256"]


def test_field_scores_against_independent_component_formula_and_tipper_mask(tmp_path):
    if not FIELD.is_file():
        pytest.skip("Acquire the ignored C15 EDI using the documented command")
    from mt_metadata.transfer_functions.io.edi import EDI

    official = EDI(fn=FIELD)
    z = np.asarray(official.z)
    sigma = np.asarray(official.z_err)

    def direct_wrms(values: np.ndarray, standard_deviation: np.ndarray) -> float:
        two_real_parts = np.concatenate((values.real / standard_deviation, values.imag / standard_deviation))
        return float(np.sqrt(np.mean(np.square(two_real_parts))))

    direct = {
        "xx": direct_wrms(z[:, 0, 0], sigma[:, 0, 0]),
        "yy": direct_wrms(z[:, 1, 1], sigma[:, 1, 1]),
        "antisymmetry": direct_wrms(z[:, 0, 1] + z[:, 1, 0], sigma[:, 0, 1] + sigma[:, 1, 0]),
    }
    checked = inspect_edi(FIELD)
    assert checked["tensor_1d"]["wrms"] == pytest.approx(direct, rel=1e-12)
    assert checked["tensor_1d"]["wrms"] == pytest.approx(
        {"xx": 43.00414898904909, "yy": 14.215855801627093, "antisymmetry": 6.726968632395771}, rel=1e-10
    )
    assert checked["tipper"]["valid_periods"] == 35

    invalid = tmp_path / "missing-one-tipper-component.edi"
    invalid.write_text(_change_first_value(FIELD.read_text(encoding="utf-8"), "TXR.EXP", "1.000E+32"), encoding="utf-8")
    with pytest.raises(MTFieldQCError, match="Tipper missing masks disagree"):
        inspect_edi(invalid)
