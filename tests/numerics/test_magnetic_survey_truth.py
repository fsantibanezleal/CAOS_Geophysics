"""Independent recorded S2 acquisition controls; never an inverse success gate."""

import ast
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, localcontext
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
    assert control["provenance"]["geometry_metadata_sha256"] == (
        "c1f25af64ed06a896bcddf5990180c82c2021687978b2cbe840f00317ea1014f")
    assert control["provenance"]["truth_source_sha256"] == (
        "4e41feee63a5d7a5997dd35d99fe17d62016db003568fe7f7f6108724163254b")
    assert control["kind"] == "authored_synthetic" and control["acquisition"]["timestamps"] is None
    assert all(value is False for value in after["claims"].values())
    c = 3 if quantity == QUANTITIES[0] else 1
    assert control["observed_nT"].shape == (288, c)
    assert np.isfinite(control["observed_nT"]).all()
    np.testing.assert_array_equal(control["sd_nT"], np.full((288, c), .5))


@pytest.mark.parametrize("quantity", QUANTITIES)
@pytest.mark.parametrize("regime", tuple("ABCDE"))
def test_actual_choclo_components_and_independent_decimal_scalar(quantity, regime):
    control = fixture.generate_control(regime, quantity)
    i, d = math.radians(37.), math.radians(-73.)
    direction = np.array([math.cos(i)*math.sin(d), math.cos(i)*math.cos(d), -math.sin(i)])
    background = 50000.*direction
    bodies = [([310., 770., 1700., 2570., -510., -130.], .012),
              ([960., 1430., 3980., 4830., -980., -420.], .021)]
    if regime == "B": bodies = [(bodies[0][0], .025), (bodies[1][0], .003)]
    if regime == "C": bodies = [([310., 770., 1700., 2570., -1050., -470.], .021), bodies[1]]
    xyz = np.array(control["geometry"]["receivers_m"]["data"]).reshape(288, 3)
    # Separate component callables, not the generator's magnetic_field callable.
    selected = [0, 13, 24, 63, 118, 206, 287]
    independent = []
    for row in selected:
        expected = np.zeros(3)
        for index, (bounds, chi) in enumerate(bodies):
            magnetization = chi * background * 1e-9 / MU0
            if regime == "D" and index == 0: magnetization += np.array([8., -5.5, 2.3])
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


@pytest.mark.parametrize("quantity", QUANTITIES)
def test_remanence_wrong_field_and_depth_controls_are_not_relabelled_passes(quantity):
    a = fixture.generate_control("A", quantity)
    b = fixture.generate_control("B", quantity)
    c = fixture.generate_control("C", quantity)
    d = fixture.generate_control("D", quantity)
    e = fixture.generate_control("E", quantity)
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
    with pytest.raises(reader.InputError, match="twelve indivisible"):
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


@pytest.mark.parametrize("fault", ["coordinates", "width", "active", "qc", "timestamp", "group", "buffer"])
def test_owned_snapshots_and_corrupted_geometry_fail_before_values(fault, monkeypatch):
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
        if fault == "coordinates": geometry["receivers_m"]["data"][0] += 1.
        if fault == "width": geometry["mesh"]["widths_z_m"]["data"][0] += 1.
        if fault == "active": geometry["mesh"]["active"]["data"][0] = False
        if fault == "qc": geometry["qc_reason"][0] = "provider_qc_excluded"
        if fault == "timestamp": acquisition["timestamps"] = ["invented"]*288
        if fault == "group": acquisition["group_ids"][0] = "changed"
        if fault == "buffer": geometry["partition"]["buffer_m"] = 199.
        return acquisition, geometry
    monkeypatch.setattr(fixture, "geometry", wrong)
    monkeypatch.setattr(choclo.prism, "magnetic_field", lambda *args: pytest.fail("truth before geometry seal"))
    with pytest.raises(ValueError, match="frozen geometry"):
        fixture.generate_control("A", QUANTITIES[0])


@pytest.mark.parametrize("secondary", [(0., 0., 0.), (1e-20, -2e-20, 3e-20),
                                        (-100., 20., 30.), (100., -20., -30.)])
def test_native_norm_baseline_rational_and_outward_sqrt_oracle(secondary):
    """Test-only algebra/interval oracle, NOT an implemented nonlinear certificate."""
    i, d = math.radians(37.), math.radians(-73.)
    b0_float = [50000.*math.cos(i)*math.sin(d),
                50000.*math.cos(i)*math.cos(d), -50000.*math.sin(i)]
    b0 = [Decimal.from_float(x) for x in b0_float]
    b = [Decimal.from_float(x) for x in secondary]
    f = Decimal.from_float(50000.)
    with localcontext() as context:
        context.prec = 160
        context.rounding = ROUND_HALF_EVEN
        radicand = sum((x+y)**2 for x, y in zip(b0, b))
        reference_norm = radicand.sqrt()
        direct = reference_norm-f
        delta0 = sum(x*x for x in b0)-f*f
        full = (delta0+2*sum(x*y for x, y in zip(b0, b))+sum(x*x for x in b))/(reference_norm+f)
        assert delta0 != 0
        assert abs(full-direct) <= Decimal("1e-140")
        if secondary == (0., 0., 0.):
            assert direct != 0 and (2*sum(x*y for x, y in zip(b0, b))+sum(x*x for x in b)) == 0
        elif max(abs(x) for x in secondary) < 1e-19:
            omitted = (2*sum(x*y for x, y in zip(b0, b))+sum(x*x for x in b))/(reference_norm+f)
            assert abs(omitted-direct) > Decimal("1e-12")
    with localcontext() as context:
        context.prec = 80
        lows, highs = [], []
        for x, y in zip(b0, b):
            context.rounding = ROUND_FLOOR
            lo = x+y
            context.rounding = ROUND_CEILING
            hi = x+y
            context.rounding = ROUND_FLOOR
            lows.append(Decimal(0) if lo <= 0 <= hi else min(lo*lo, hi*hi))
            context.rounding = ROUND_CEILING
            highs.append(max(lo*lo, hi*hi))
        context.rounding = ROUND_FLOOR
        lower_s = sum(lows)
        context.rounding = ROUND_CEILING
        upper_s = sum(highs)
        assert 0 < lower_s <= upper_s
        # sqrt ignores FLOOR/CEILING; neighbours are needed AFTER sqrt.
        lower_t = lower_s.sqrt().next_minus(context)
        upper_t = upper_s.sqrt().next_plus(context)
        assert lower_t <= reference_norm <= upper_t
        context.rounding = ROUND_FLOOR
        lower_h = lower_t-f
        context.rounding = ROUND_CEILING
        upper_h = upper_t-f
        assert lower_h <= direct <= upper_h


@pytest.mark.parametrize("quantity", ["secondary_amplitude", "total_intensity", None, True, "exact_total_anomaly_nT "])
def test_unpromised_quantities_reject_before_truth(quantity, monkeypatch):
    monkeypatch.setattr(choclo.prism, "magnetic_field", lambda *args: pytest.fail("truth before quantity rejection"))
    with pytest.raises((TypeError, ValueError)):
        fixture.generate_control("A", quantity)


@pytest.mark.parametrize("fault", ["version", "source", "nonfinite"])
def test_truth_dependency_and_nonfinite_failures_remain_failures(fault, monkeypatch):
    if fault == "version": monkeypatch.setattr(choclo, "__version__", "v0.3.3")
    if fault == "source":
        original_read = Path.read_bytes
        def changed(path):
            return b"unreviewed physical source" if path.name == "_magnetic.py" else original_read(path)
        monkeypatch.setattr(Path, "read_bytes", changed)
    if fault == "nonfinite":
        monkeypatch.setattr(choclo.prism, "magnetic_field", lambda *args: (np.inf, 0., 0.))
    else:
        monkeypatch.setattr(choclo.prism, "magnetic_field", lambda *args: pytest.fail("truth before dependency rejection"))
    with pytest.raises(RuntimeError):
        fixture.generate_control("A", QUANTITIES[0])
