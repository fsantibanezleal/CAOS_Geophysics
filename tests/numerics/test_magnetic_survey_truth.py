"""Independent recorded S2 acquisition controls; never an inverse success gate."""

import ast
from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import choclo
from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as MU0
import numpy as np
import pytest

import magnetic_survey as planner
import magnetic_survey_json as reader
from magnetic_survey_support import descriptor, digest, encode, request


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/magnetic_survey/generate.py"
spec = importlib.util.spec_from_file_location("s2_physical_fixture", FIXTURE)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
QUANTITIES = ("secondary_enu_nT", "linear_tmi_nT", "exact_total_anomaly_nT")


def modelling_request(control):
    """No evaluator truth or signal/noise realization passes to the modelling side."""
    doc = request()
    doc["acquisition"] = deepcopy(control["acquisition"])
    doc["geometry"] = deepcopy(control["geometry"])
    quantity = control["quantity"]
    field = control["declared_field"]
    doc["inducing_field"].update(field)
    doc["inducing_field"]["source_sha256"] = digest(field)
    doc["source"].update(id="S2-"+control["regime"],
                         original_sha256=hashlib.sha256(control["original_bytes"]).hexdigest(),
                         original_bytes=len(control["original_bytes"]),
                         citation="Original authored S2 conditional acquisition, not field")
    values = descriptor("float64", control["observed_nT"].shape,
                        control["observed_nT"].ravel().tolist())
    doc["observations"].update(quantity=quantity, values=values, values_sha256=values["sha256"])
    doc["noise"]["values"] = descriptor("float64", control["sd_nT"].shape,
                                        control["sd_nT"].ravel().tolist())
    doc["noise"]["citation"] = "Authored conditional SD0.5nT, PCG64 recorded realization"
    doc["processing"]["quantity"] = quantity
    doc["processing"]["background_relation"] = (
        "secondary_field_declared", "projection_of_secondary_declared",
        "total_norm_minus_declared_uniform_F")[QUANTITIES.index(quantity)]
    node = doc["processing"]["nodes"][0]
    node["input_sha256"] = doc["source"]["original_sha256"]
    node["output_sha256"] = values["sha256"]
    return doc


@pytest.mark.parametrize("regime", tuple("ABCDEF"))
@pytest.mark.parametrize("quantity", QUANTITIES)
def test_recorded_regimes_preserve_sealed_geometry(regime, quantity):
    # Freeze and check the production planner before generating any magnetic values.
    before = planner.plan_geometry(reader.parse_request(encode(request())))
    control = fixture.generate_control(regime, quantity)
    after = planner.plan_geometry(reader.parse_request(encode(modelling_request(control))))
    assert after["partition"] == before["partition"]
    assert after["inventory"] == before["inventory"]
    assert len(after["partition"]["outer_rows"]["data"]) == 72
    assert all(len(f["fit_rows"]["data"]) == 144 and
               len(f["validation_rows"]["data"]) == 72 for f in after["partition"]["folds"])
    assert control["provenance"]["geometry_sha256"] == (
        "b784c2e62476cc8926a948fa3c20787df9dcf017a54497d1a696fddb2026538a")
    assert control["provenance"]["membership_sha256"] == (
        "2336754f197bcf8470fdcf267df80af962f2483860bad37b5dacefb9691f2d45")
    assert control["kind"] == "authored_synthetic" and control["acquisition"]["timestamps"] is None
    assert all(value is False for value in after["claims"].values())
    c = 3 if quantity == QUANTITIES[0] else 1
    assert control["observed_nT"].shape == (288, c)
    assert np.isfinite(control["observed_nT"]).all()
    np.testing.assert_array_equal(control["sd_nT"], np.full((288, c), .5))


@pytest.mark.parametrize("quantity", QUANTITIES)
def test_actual_choclo_components_and_independent_decimal_scalar(quantity):
    control = fixture.generate_control("A", quantity)
    i, d = math.radians(37.), math.radians(-73.)
    direction = np.array([math.cos(i)*math.sin(d), math.cos(i)*math.cos(d), -math.sin(i)])
    background = 50000.*direction
    bodies = [([310., 770., 1700., 2570., -510., -130.], .012),
              ([960., 1430., 3980., 4830., -980., -420.], .021)]
    xyz = np.array(control["geometry"]["receivers_m"]["data"]).reshape(288, 3)
    # Separate component callables, not the generator's magnetic_field callable.
    selected = [0, 13, 24, 63, 118, 206, 287]
    independent = []
    for row in selected:
        expected = np.zeros(3)
        for bounds, chi in bodies:
            magnetization = chi * background * 1e-9 / MU0
            expected += np.array([function(*xyz[row], *bounds, *magnetization)
                                  for function in (choclo.prism.magnetic_e,
                                                   choclo.prism.magnetic_n,
                                                   choclo.prism.magnetic_u)])*1e9
        independent.append(expected)
    np.testing.assert_allclose(control["secondary_enu_nT"][selected], independent,
                               rtol=2e-8, atol=1e-7)
    expected_signal = np.array(independent)
    if quantity == QUANTITIES[1]:
        expected_signal = (expected_signal @ direction).reshape(-1, 1)
    if quantity == QUANTITIES[2]:
        expected_signal = []
        with localcontext() as context:
            context.prec = 80
            for row in selected:
                # Convert each retained float before addition; no rounded np B0+b.
                s = sum((Decimal.from_float(float(b))+Decimal.from_float(float(v)))**2
                        for b, v in zip(background, control["secondary_enu_nT"][row]))
                expected_signal.append(float(s.sqrt()-Decimal.from_float(50000.)))
        expected_signal = np.array(expected_signal).reshape(-1, 1)
    np.testing.assert_allclose(control["signal_nT"][selected], expected_signal,
                               rtol=2e-8, atol=1e-7)


@pytest.mark.parametrize("regime", tuple("ABCDE"))
@pytest.mark.parametrize("quantity", QUANTITIES)
def test_noise_raw_record_reproducibility_and_truth_separation(regime, quantity):
    control = fixture.generate_control(regime, quantity)
    again = fixture.generate_control(regime, quantity)
    assert control["original_bytes"] == again["original_bytes"]
    assert control["provenance"] == again["provenance"]
    rng = np.random.Generator(np.random.PCG64(20261004))
    noise = rng.normal(0., .5, size=control["signal_nT"].shape)
    np.testing.assert_array_equal(control["observed_nT"], control["signal_nT"]+noise)
    assert control["provenance"]["rng_state_after"] == rng.bit_generator.state
    original = json.loads(control["original_bytes"])
    assert set(original) == {"schema", "regime", "quantity", "acquisition", "frame",
                             "declared_field", "geometry", "observations", "noise"}
    assert original["observations"]["sha256"] == descriptor(
        "float64", control["observed_nT"].shape, control["observed_nT"].ravel())["sha256"]
    assert not any(key in original for key in ("truth", "bodies", "signal", "magnetization"))
    doc = modelling_request(control)
    handle = reader.parse_request(encode(doc))
    assert "data" not in handle.metadata()["observations"]["values"]
    assert handle.metadata()["source"]["original_bytes"] == len(control["original_bytes"])


def test_remanence_wrong_field_and_depth_controls_are_not_relabelled_passes():
    a = fixture.generate_control("A", QUANTITIES[0])
    b = fixture.generate_control("B", QUANTITIES[0])
    c = fixture.generate_control("C", QUANTITIES[0])
    d = fixture.generate_control("D", QUANTITIES[0])
    e = fixture.generate_control("E", QUANTITIES[0])
    assert a["bodies"][0]["bounds_m"] == b["bodies"][0]["bounds_m"]
    assert b["bodies"][0]["chi_si"] == .025 and b["bodies"][1]["chi_si"] == .003
    assert c["bodies"][0]["bounds_m"][-2:] == [-1050., -470.]
    assert c["bodies"][0]["chi_si"] == .021
    assert d["bodies"][0]["remanence_A_m"] == [8., -5.5, 2.3]
    assert np.linalg.norm(d["secondary_enu_nT"]-a["secondary_enu_nT"]) > 0
    np.testing.assert_array_equal(e["observed_nT"], a["observed_nT"])
    assert e["truth_field"] == a["truth_field"]
    assert e["declared_field"] == {"F_nT": 50000., "I_deg": -35., "D_deg": -100.}
    for control in (a, b, c, d, e):
        assert control["verdict"] == "not_evaluated"
        assert control["provenance"]["fit_executed"] is False
        for body in control["bodies"]:
            assert body["bounds_m"][0] not in np.arange(-400., 1801., 200.)


@pytest.mark.parametrize("quantity", QUANTITIES)
def test_null_observations_and_deficient_coverage_are_separate(quantity):
    control = fixture.generate_control("F", quantity)
    np.testing.assert_array_equal(control["secondary_enu_nT"], np.zeros((288, 3)))
    np.testing.assert_array_equal(control["observed_nT"], np.zeros_like(control["observed_nT"]))
    assert control["provenance"]["noise_realization"] == "explicit_zero_observation_control"
    assert control["bodies"] == []
    if quantity == QUANTITIES[2]:
        # Rounded native-vector norm need not equal the separately retained scalar F.
        assert control["signal_nT"][0, 0] != 0.
    doc = modelling_request(control)
    for key in ("row_ids", "group_ids"):
        doc["acquisition"][key] = doc["acquisition"][key][:96]
    doc["geometry"]["receivers_m"] = descriptor(
        "float64", [96, 3], doc["geometry"]["receivers_m"]["data"][:288])
    doc["geometry"]["usable"] = descriptor("bool", [96], [True]*96)
    doc["geometry"]["qc_reason"] = ["accepted"]*96
    c = 3 if quantity == QUANTITIES[0] else 1
    doc["observations"]["values"] = descriptor("float64", [96, c], [0.]*(96*c))
    doc["observations"]["values_sha256"] = doc["observations"]["values"]["sha256"]
    doc["processing"]["nodes"][-1]["output_sha256"] = doc["observations"]["values_sha256"]
    doc["noise"]["values"] = descriptor("float64", [96, c], [.5]*(96*c))
    doc["source"]["scope"] = "declared_subset"
    with pytest.raises(reader.SurveyInputError, match="insufficient_partition_geometry"):
        planner.plan_geometry(reader.parse_request(encode(doc)))


def test_generator_has_no_candidate_kernel_or_inverse_dependency():
    tree = ast.parse(FIXTURE.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.update(n.name.split(".")[0] for n in node.names)
        if isinstance(node, ast.ImportFrom): imports.add(node.module.split(".")[0])
    assert imports <= {"hashlib", "struct", "json", "math", "decimal", "pathlib", "numpy", "choclo"}
    assert not imports & {"simpeg", "geoana", "magnetic_forward", "magnetic_inverse", "physical_optimizer"}


@pytest.mark.parametrize("bad", [None, True, 1, [], {}, "G", "a", "A "])
def test_regime_is_literal_not_coerced(bad):
    with pytest.raises((TypeError, ValueError)):
        fixture.generate_control(bad, QUANTITIES[0])


def test_owned_snapshots_and_corrupted_geometry_fail_before_values(monkeypatch):
    control = fixture.generate_control("A", QUANTITIES[0])
    arrays = [control[key] for key in ("secondary_enu_nT", "signal_nT", "observed_nT", "sd_nT")]
    for i, value in enumerate(arrays):
        assert value.flags.owndata and value.flags.c_contiguous and not value.flags.writeable
        assert not any(np.shares_memory(value, other) for other in arrays[i+1:])
    before = control["observed_nT"].copy()
    control["signal_nT"].flags.writeable = True
    control["signal_nT"][0, 0] += 1
    np.testing.assert_array_equal(control["observed_nT"], before)
    original_geometry = fixture.geometry
    def wrong():
        acquisition, geometry = original_geometry()
        geometry["receivers_m"]["data"][0] += 1.
        return acquisition, geometry
    monkeypatch.setattr(fixture, "geometry", wrong)
    monkeypatch.setattr(choclo.prism, "magnetic_field", lambda *args: pytest.fail("truth before geometry seal"))
    with pytest.raises(ValueError, match="frozen geometry"):
        fixture.generate_control("A", QUANTITIES[0])
