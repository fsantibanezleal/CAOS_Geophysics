"""Strict real EDI ingestion, independent oracle and actual inverse execution."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from edi import EDIError, MT_TO_OHM, build_fixture_bundle, invert_edi, read_edi, screen_edi
from electromagnetics import MU

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT/"data/fixtures/edi"
NATIVE = FIXTURES/"halfspace-100-native.edi"
NEGATIVE = FIXTURES/"halfspace-500-ohm-negative.edi"


def test_screen_only_preserves_observations_without_inventing_an_inverse(tmp_path):
    output=tmp_path/'screen.json'
    result=screen_edi(NATIVE,output=output)
    assert result['schema']=='inverse-earth/edi-screen/v1'
    assert result['source_kind']=='original synthetic EDI transfer functions'
    assert result['truth'] is None and result['methods']=={}
    assert result['inversion_performed'] is False
    assert result['one_d_inversion_eligible'] is True
    assert len(result['frequencies_hz'])==24
    assert result['provenance']['source_sha256']==hashlib.sha256(NATIVE.read_bytes()).hexdigest()
    assert json.loads(output.read_text(encoding='utf-8'))==result


def altered(tmp_path, replacement):
    source = tmp_path/"changed.edi"
    source.write_text(replacement(NATIVE.read_text(encoding="utf-8")), encoding="utf-8")
    return source


def with_field_style_tipper(text):
    """Exercise the field EDI structure without adding a downloaded file to Git."""
    text = text.replace(" UNITS=millivolts_per_kilometer_per_nanotesla\n", "")
    text = text.replace(" SIGN_CONVENTION=+", r" SIGNCONVENTION=exp(+ i\omega t)")
    text = text.replace(" VARIANCE_CONVENTION=complex\n", "")
    text = text.replace("MAXCHAN=4", "MAXCHAN=5").replace("MAXMEAS=4", "MAXMEAS=5")
    text = text.replace("NCHAN=4", "NCHAN=5")
    text = text.replace(">EMEAS ID=3", ">HMEAS ID=5 CHTYPE=HZ X=0 Y=0 AZM=0\n>EMEAS ID=3", 1)
    text = text.replace(" HY=2\n", " HY=2\n HZ=5\n", 1)
    valid = " ".join(["1e32" if i == 23 else "0.01" for i in range(24)])
    variance = " ".join(["1e32" if i == 23 else "0.001" for i in range(24)])
    tipper = ">TROT // 24\n" + " ".join(["0"]*24) + "\n"
    for axis in ("X", "Y"):
        for suffix, values in (("R.EXP", valid), ("I.EXP", valid), ("VAR.EXP", variance)):
            tipper += f">T{axis}{suffix} ROT=TROT // 24\n{values}\n"
    return text.replace(">END", tipper+">END")


def test_original_fixture_manifest_hashes():
    manifest = json.loads((FIXTURES/"manifest.json").read_text())
    assert manifest["license"] == "CC0-1.0"
    assert manifest["generator_sha256"] == hashlib.sha256((FIXTURES/"generate_fixtures.py").read_bytes()).hexdigest()
    for fixture in manifest["fixtures"]:
        path = FIXTURES/fixture["path"]
        assert fixture["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert fixture["bytes"] == path.stat().st_size
        assert fixture["target"]["provenance"] == "independent analytic synthetic oracle"


def test_native_units_complex_variance_and_independent_halfspace():
    run = read_edi(NATIVE)
    z, sigma = run.select("xy")
    expected = (1+1j)*np.sqrt(np.pi*run.frequencies*MU*100)
    np.testing.assert_allclose(z, expected, rtol=1e-12)
    np.testing.assert_allclose(abs(z)**2/(2*np.pi*run.frequencies*MU), 100, rtol=1e-12)
    np.testing.assert_allclose(sigma, abs(expected)*.025, rtol=1e-12)
    np.testing.assert_allclose(run.select("yx")[0], expected, rtol=1e-12)
    assert run.provenance["units_multiplier_to_ohm"] == pytest.approx(MT_TO_OHM)
    assert run.provenance["variance_convention"] == "complex"
    assert run.provenance["source_sha256"] == hashlib.sha256(NATIVE.read_bytes()).hexdigest()
    assert run.compatibility["passes_screen"]
    assert np.all(np.diff(run.frequencies) > 0)


def test_negative_time_sign_si_units_and_exact_rotation():
    original = read_edi(NEGATIVE)
    geographic = read_edi(NEGATIVE, rotation="geographic", rotation_reference="geographic-north")
    z, _ = original.select("xy")
    expected = (1+1j)*np.sqrt(np.pi*original.frequencies*MU*500)
    np.testing.assert_allclose(z, expected, rtol=1e-12)
    np.testing.assert_allclose(geographic.tensor, original.tensor, rtol=1e-12, atol=1e-15)
    np.testing.assert_allclose(geographic.sigma, original.sigma, rtol=1e-12)
    assert (original.rotation_deg == 90).all()
    assert (geographic.rotation_deg == 0).all()
    assert original.provenance["original_sign_convention"] == "-"
    assert geographic.provenance["rotation_reference"] == "geographic-north"


def test_nonzero_rotation_preserves_errors_but_arbitrary_rerotation_rejected():
    source = FIXTURES/"two-layer-noisy-rotated.edi"
    sounding = read_edi(source)
    assert sounding.compatibility["passes_screen"]
    assert np.all(sounding.rotation_deg == 27)
    assert "none" in sounding.provenance["rotation_action"]
    with pytest.raises(EDIError, match="full error covariance"):
        read_edi(source, rotation="geographic", rotation_reference="geographic-north")
    with pytest.raises(EDIError, match="geographic-north reference"):
        read_edi(NEGATIVE, rotation="geographic")


@pytest.mark.parametrize("mutation, message", [
    (lambda s: s.replace(">END", ""), "HEAD first"),
    (lambda s: s.replace("NFREQ=24", "NFREQ=23"), "declare exactly"),
    (lambda s: s.replace(">ZXYR ROT=ZROT // 24", ">ZXYR ROT=ZROT // 23"), "declare exactly"),
    (lambda s: s.replace(">ZXYR", ">SPECTRA"), "Missing required"),
    (lambda s: s.replace("UNITS=millivolts_per_kilometer_per_nanotesla", "UNITS=tesla"), "units"),
    (lambda s: s.replace(" SIGN_CONVENTION=+", ""), "time/sign"),
    (lambda s: s.replace(" VARIANCE_CONVENTION=complex", ""), "variance convention"),
    (lambda s: s.replace("ROT=ZROT", "ROT=MISSING", 1), "rotation reference"),
    (lambda s: s.replace(">ZXYR ROT=ZROT", ">ZXYR ROT=17"), "common frame"),
    (lambda s: s.replace("AZM=90", "AZM=75"), "Nonorthogonal"),
    (lambda s: s.replace("HY=2", "HY=8"), "identifiers"),
    (lambda s: s.replace("FREQUENCY_UNITS=Hz", "FREQUENCY_UNITS=rad/s"), "Hz"),
    (lambda s: s.replace(">FREQ //", ">FREQ UNITS=rad/s //"), "Hz"),
    (lambda s: s.replace(">FREQ // 24", ">FREQ // 24\nnan", 1), "nonfinite"),
    (lambda s: s.replace(">ZXXR ROT=ZROT // 24", ">ZXXR ROT=ZROT // 24\n1e32", 1), "length"),
    (lambda s: s.replace(">END", ">FREQ // 24\n1\n>END"), "Duplicate block"),
])
def test_malformed_or_ambiguous_edi_rejected(tmp_path, mutation, message):
    with pytest.raises(EDIError, match=message):
        read_edi(altered(tmp_path, mutation))


def replace_first_data_value(text, block, value):
    start = text.index("\n", text.index(">"+block))+1
    stop = text.index(" ", start)
    return text[:start]+value+text[stop:]


@pytest.mark.parametrize("block,value,message", [
    ("FREQ", "-1", "positive"),
    ("FREQ", "nan", "nonfinite"),
    ("ZXYR", "1e32", "sentinel"),
    ("ZXYR", "*****", "numeric"),
    ("ZXY.VAR", "0", "strictly positive"),
    ("ZXY.VAR", "-1", "strictly positive"),
])
def test_bad_numeric_values_never_silently_become_zero(tmp_path, block, value, message):
    source = altered(tmp_path, lambda s: replace_first_data_value(s, block, value))
    with pytest.raises(EDIError, match=message):
        read_edi(source)


def test_exact_rotation_permutates_unequal_variances_and_signed_components(tmp_path):
    def edit(text):
        text = text.replace("ROT=ZROT", "ROT=90")
        text = replace_first_data_value(text, "ZXXR", "0.2")
        return replace_first_data_value(text, "ZXX.VAR", "0.125")
    source = altered(tmp_path, edit)
    original = read_edi(source)
    rotated = read_edi(source, rotation="geographic", rotation_reference="geographic-north")
    np.testing.assert_array_equal(rotated.tensor[:, 0, 0], original.tensor[:, 1, 1])
    np.testing.assert_array_equal(rotated.tensor[:, 1, 1], original.tensor[:, 0, 0])
    np.testing.assert_array_equal(rotated.tensor[:, 0, 1], -original.tensor[:, 1, 0])
    np.testing.assert_array_equal(rotated.sigma[:, 1, 1], original.sigma[:, 0, 0])
    assert rotated.sigma[-1, 1, 1] != original.sigma[-1, 1, 1]


def test_explicit_metadata_interpretation_is_recorded_not_silently_guessed(tmp_path):
    source = altered(tmp_path, lambda s: s.replace(" VARIANCE_CONVENTION=complex", ""))
    sounding = read_edi(source, variance_convention="complex")
    assert sounding.provenance["interpretation_arguments"]["variance_convention"] == "complex"
    with pytest.raises(EDIError, match="Conflicting"):
        read_edi(NATIVE, units="ohm")
    with pytest.raises(EDIError, match="diagonal"):
        sounding.select("xx")


def test_field_style_info_and_ancillary_tipper_preserve_missing_mask(tmp_path):
    source = altered(tmp_path, with_field_style_tipper)
    with pytest.raises(EDIError, match="impedance units"):
        read_edi(source)
    with pytest.raises(EDIError, match="variance convention"):
        read_edi(source, units="mt")
    sounding = read_edi(source, units="mt", variance_convention="complex")
    assert sounding.provenance["original_sign_convention"] == "+"
    assert sounding.metadata["info"]["SIGNCONVENTION"] == r"exp(+ i\omega t)"
    assert sounding.provenance["tipper_present"]
    assert not sounding.provenance["tipper_used_in_1d_inversion"]
    tipper = sounding.metadata["tipper"]
    assert tipper["missing_frequency_hz"] == [pytest.approx(sounding.frequencies[0])]
    assert tipper["components"]["X"]["real"][0] is None
    assert tipper["components"]["Y"]["variance"][0] is None
    assert tipper["components"]["X"]["real"][1] == pytest.approx(.01)
    json.dumps(sounding.metadata, allow_nan=False)


@pytest.mark.parametrize("mutation, message", [
    (lambda s: s.replace(">TYI.EXP", ">UNKNOWN", 1), "Incomplete tipper"),
    (lambda s: s.replace(" HZ=5\n", " HZ=6\n", 1), "identifiers"),
    (lambda s: s.replace("NCHAN=5", "NCHAN=4", 1), "NCHAN"),
    (lambda s: s.replace(">TXR.EXP ROT=TROT", ">TXR.EXP ROT=27", 1), "TROT frame"),
    (lambda s: replace_first_data_value(s, "TXVAR.EXP", "0"), "tipper variances"),
    (lambda s: replace_first_data_value(s, "TXR.EXP", "1e32"), "masks disagree"),
])
def test_invalid_field_tipper_fails_closed(tmp_path, mutation, message):
    source = altered(tmp_path, lambda s: mutation(with_field_style_tipper(s)))
    with pytest.raises(EDIError, match=message):
        read_edi(source, units="mt", variance_convention="complex")


def test_converted_variance_underflow_rejected(tmp_path):
    source = altered(tmp_path, lambda s: replace_first_data_value(s, "ZXY.VAR", "5e-324"))
    with pytest.raises(EDIError, match="finite and strictly positive"):
        read_edi(source)


def test_per_real_variance_is_distinct_and_recorded(tmp_path):
    source = altered(tmp_path, lambda s: s.replace("VARIANCE_CONVENTION=complex", "VARIANCE_CONVENTION=per-real-component"))
    per_real, complex_error = read_edi(source), read_edi(NATIVE)
    np.testing.assert_allclose(per_real.sigma, complex_error.sigma*np.sqrt(2), rtol=1e-12)
    assert per_real.provenance["variance_convention"] == "per-real-component"


def test_frequency_duplicates_and_missing_component_are_rejected(tmp_path):
    def duplicate(s):
        start = s.index("\n", s.index(">FREQ"))+1
        first, second = s[start:].split()[:2]
        return s[:start]+s[start:].replace(first, second, 1)
    with pytest.raises(EDIError, match="unique"):
        read_edi(altered(tmp_path, duplicate))
    with pytest.raises(EDIError, match="Missing required"):
        read_edi(altered(tmp_path, lambda s: s.replace(">ZYY.VAR", ">UNSUPPORTED")))


def test_actual_edi_inverse_no_invented_truth_and_flat_uncertainty(tmp_path):
    destination = tmp_path/"recovered.json"
    result = invert_edi(NATIVE, [], output=destination, bootstrap_samples=64, seed=71401)
    assert result["truth"] is None and result["clean"] is None
    method = result["methods"]["mt-lm"]
    assert method["model"][0] == pytest.approx(100, rel=1e-8)
    assert method["metrics"]["other_component_wrms"] < 1e-8
    assert method["uncertainty"]["lower"][0] < 100 < method["uncertainty"]["upper"][0]
    assert method["uncertainty"]["members"] == 64
    assert method["state_identity"]["predictions"] == "final-model"
    assert method["target"]["quantity"] == "electrical resistivity"
    assert "no_independent_geological_truth" in method["evaluation"]["reason_codes"]
    assert json.loads(destination.read_text()) == result


def test_actual_noisy_layered_edi_recovery():
    result = invert_edi(FIXTURES/"two-layer-noisy-rotated.edi", [350.], bootstrap_samples=0)
    method = result["methods"]["mt-lm"]
    np.testing.assert_allclose(method["model"], [120, 12], rtol=.15)
    assert method["metrics"]["active_component_wrms"] < 1.5
    assert method["metrics"]["other_component_wrms"] < 1.5


def test_1d_incompatible_tensor_is_not_inverted(tmp_path):
    source = altered(tmp_path, lambda s: replace_first_data_value(s, "ZXXR", "100000"))
    sounding = read_edi(source)
    assert not sounding.compatibility["passes_screen"]
    with pytest.raises(EDIError, match="1D consistency"):
        invert_edi(source, [], bootstrap_samples=0)


def test_cli_executes_and_rejects_malformed_input(tmp_path):
    destination = tmp_path/"cli.json"
    command = [sys.executable, str(ROOT/"data-pipeline/edi.py"), str(NEGATIVE),
               "--output", str(destination), "--bootstrap-samples", "0"]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=90)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(destination.read_text())["methods"]["mt-lm"]["model"][0] == pytest.approx(500, rel=1e-8)
    bad = altered(tmp_path, lambda s: s.replace(" SIGN_CONVENTION=+", ""))
    command[2] = str(bad)
    completed = subprocess.run(command, capture_output=True, text=True, timeout=90)
    assert completed.returncode == 2 and "EDI rejected" in completed.stderr


def test_frontend_fixture_bundle_relative_urls_and_known_truth_separation(tmp_path):
    output = tmp_path/"bundle"
    bundle = build_fixture_bundle(output, bootstrap_samples=0)
    assert bundle["schema"] == "inverse-earth/edi-bundle/v1"
    assert len(bundle["fixtures"]) == 3
    for row in bundle["fixtures"]:
        assert row["synthetic"]
        artifact = json.loads((output/row["artifact"]).read_text())
        assert artifact["truth"] is None
        assert len(row["truth_ohm_m"]) == len(artifact["thickness"])+1
        assert artifact["provenance"]["synthetic"]
        assert row["artifact_sha256"] == hashlib.sha256((output/row["artifact"]).read_bytes()).hexdigest()
        assert row["source_sha256"] == hashlib.sha256((output/row["source"]).read_bytes()).hexdigest()
        assert artifact["methods"]["mt-lm"]["evaluation"]["status"] in ("recovered", "unresolved", "failed", "negative-control")
