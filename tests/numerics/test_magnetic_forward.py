"""Independent bounded induced-prism controls, not full magnetic method acceptance."""

import ast
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re

import choclo
from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as MU0
import numpy as np
from numpy.polynomial.legendre import leggauss
import pytest

import magnetic_forward as op


ROOT = Path(__file__).resolve().parents[2]
ENGINE = "simpeg-0.25.2-geoana-0.8.1-f64-induced-ram"
FRAME = {"kind": "local_cartesian", "axes": ("east", "north", "up"),
         "length_unit": "m", "vertical_positive": "up"}


def request(multi=False):
    origin, widths = [-50., -40., -120.], [[100.], [80.], [120.]]
    active, chi = [True], [.03]
    receivers = [[0., 0., 100.], [170., 30., 120.], [-100., 160., 240.]]
    if multi:
        origin, widths = [-140., -180., -260.], [[40., 70.], [30., 50., 90.], [60., 110.]]
        active = np.zeros(12, dtype=bool)
        active[[0, 2, 3, 7, 11]] = True
        chi = [.01, .03, .05, .02, .08]
        receivers = [[0., 0., 100.], [230., -50., 40.], [-400., 60., -350.], [70., 260., -150.]]
    return {"schema": "magnetic-prism-forward-request-1", "engine": ENGINE, "frame": dict(FRAME),
            "mesh": {"origin_m": np.array(origin), "hx_m": np.array(widths[0]),
                     "hy_m": np.array(widths[1]), "hz_m": np.array(widths[2]),
                     "active": np.array(active, dtype=bool)},
            "receivers_m": np.array(receivers), "susceptibility_si": np.array(chi),
            "inducing_field": {"amplitude_nt": 50000., "inclination_deg": 60., "declination_deg": 12.}}


def direction(req):
    field = req["inducing_field"]
    i, d = math.radians(field["inclination_deg"]), math.radians(field["declination_deg"])
    return np.array([math.cos(i)*math.sin(d), math.cos(i)*math.cos(d), -math.sin(i)])


def bounds(req):
    edges = [float(o) + np.r_[0., np.cumsum(req["mesh"][key])]
             for o, key in zip(req["mesh"]["origin_m"], ("hx_m", "hy_m", "hz_m"))]
    result, index = [], 0
    for k in range(len(edges[2])-1):
        for j in range(len(edges[1])-1):
            for i in range(len(edges[0])-1):
                if req["mesh"]["active"][index]:
                    result.append([edges[0][i], edges[0][i+1], edges[1][j],
                                   edges[1][j+1], edges[2][k], edges[2][k+1]])
                index += 1
    return np.array(result)


def physical_oracle(req, unit_columns=False, magnetizations=None):
    # Independent Choclo bounds and physical A/m, never candidate G/helpers.
    prisms = bounds(req)
    unit_m = direction(req)*req["inducing_field"]["amplitude_nt"]*1e-9/MU0
    if unit_columns:
        return np.array([[choclo.prism.magnetic_field(*r, *b, *unit_m)
                          for b in prisms] for r in req["receivers_m"]])*1e9
    ms = [chi*unit_m for chi in req["susceptibility_si"]] if magnetizations is None else magnetizations
    return np.array([sum((np.array(choclo.prism.magnetic_field(*r, *b, *m))
                         for b, m in zip(prisms, ms)), start=np.zeros(3))
                     for r in req["receivers_m"]])*1e9


def arrays(result):
    found = []
    for value in result.values():
        if type(value) is dict:
            found.extend(arrays(value))
        elif type(value) is np.ndarray:
            found.append(value)
    return found


class Hook:
    def __eq__(self, other):
        raise AssertionError("custom equality executed")

    def __array__(self, *args, **kwargs):
        raise AssertionError("custom array conversion executed")


@pytest.mark.parametrize("bad", ["extra", "missing", "root_subclass", "frame_subclass", "mesh_subclass",
                                 "field_subclass", "schema_hook", "engine_hook", "axes_hook", "axes_list",
                                 "unit_hook", "field_extra", "frame_extra", "mesh_extra", "array_hook",
                                 "array_subclass", "float32", "complex", "object", "list", "endian", "shape"])
def test_exact_protocol_preallocation(bad, monkeypatch):
    req = request()
    if bad == "extra": req["observed"] = np.ones(3)
    elif bad == "missing": del req["schema"]
    elif bad == "root_subclass": req = type("DictSub", (dict,), {})(req)
    elif bad.endswith("_subclass") and bad != "array_subclass":
        key = {"frame_subclass": "frame", "mesh_subclass": "mesh", "field_subclass": "inducing_field"}[bad]
        req[key] = type("DictSub", (dict,), {})(req[key])
    elif bad == "schema_hook": req["schema"] = Hook()
    elif bad == "engine_hook": req["engine"] = Hook()
    elif bad == "axes_hook": req["frame"]["axes"] = (Hook(), "north", "up")
    elif bad == "axes_list": req["frame"]["axes"] = ["east", "north", "up"]
    elif bad == "unit_hook": req["frame"]["length_unit"] = Hook()
    elif bad.endswith("_extra"):
        req[{"field_extra": "inducing_field", "frame_extra": "frame", "mesh_extra": "mesh"}[bad]]["extra"] = 1
    elif bad == "array_hook": req["receivers_m"] = Hook()
    elif bad == "array_subclass": req["receivers_m"] = req["receivers_m"].view(type("ArraySub", (np.ndarray,), {}))
    elif bad == "float32": req["receivers_m"] = req["receivers_m"].astype("float32")
    elif bad == "complex": req["receivers_m"] = req["receivers_m"].astype("complex128")
    elif bad == "object": req["receivers_m"] = req["receivers_m"].astype(object)
    elif bad == "list": req["receivers_m"] = req["receivers_m"].tolist()
    elif bad == "endian": req["receivers_m"] = req["receivers_m"].astype(">f8")
    elif bad == "shape": req["receivers_m"] = np.zeros((3, 2))
    monkeypatch.setattr(op, "_snapshot", lambda *args: pytest.fail("snapshot before protocol rejection"))
    with pytest.raises((TypeError, ValueError)):
        op.forward_magnetic(req)


@pytest.mark.parametrize("cap", ["axis_zero", "axis_plus1", "full_plus1", "active_plus1",
                                 "receivers_zero", "receivers_plus1", "matrix_plus1", "mask_shape"])
def test_count_caps_before_scans(cap, monkeypatch):
    req = request()
    if cap == "axis_zero": req["mesh"]["hx_m"] = np.empty(0)
    elif cap == "axis_plus1": req["mesh"]["hx_m"] = np.ones(65)
    elif cap == "full_plus1":
        req["mesh"].update(hx_m=np.ones(64), hy_m=np.ones(64), hz_m=np.ones(17))
    elif cap == "active_plus1":
        req["mesh"].update(hx_m=np.ones(64), hy_m=np.ones(64), hz_m=np.ones(3), active=np.ones(12288, bool))
        req["susceptibility_si"] = np.zeros(8193)
    elif cap == "receivers_zero": req["receivers_m"] = np.zeros((0, 3))
    elif cap == "receivers_plus1": req["receivers_m"] = np.zeros((2049, 3))
    elif cap == "matrix_plus1":
        req["mesh"].update(hx_m=np.ones(64), hy_m=np.ones(64), hz_m=np.ones(2), active=np.ones(8192, bool))
        req["susceptibility_si"], req["receivers_m"] = np.zeros(8192), np.zeros((513, 3))
    elif cap == "mask_shape": req["mesh"]["active"] = np.ones(2, bool)
    monkeypatch.setattr(op.np, "count_nonzero", lambda *args: pytest.fail("scan before metadata rejection"))
    monkeypatch.setattr(op, "_snapshot", lambda *args: pytest.fail("copy before metadata rejection"))
    with pytest.raises(ValueError):
        op.forward_magnetic(req)


def test_exact_cap_metadata_admission_without_upper_kernel(monkeypatch):
    req = request()
    req["mesh"].update(hx_m=np.ones(64), hy_m=np.ones(64), hz_m=np.ones(16))
    req["mesh"]["active"] = np.arange(65536) < 8192
    req["susceptibility_si"] = np.zeros(8192)
    req["receivers_m"] = np.tile([0., 0., 500.], (512, 1))
    monkeypatch.setattr(op, "_runtime", lambda: (_ for _ in ()).throw(RuntimeError("bounded preflight reached")))
    with pytest.raises(RuntimeError, match="bounded preflight reached"):
        op.forward_magnetic(req)


def test_geometry_order_and_immutability():
    req = request(True)
    req["receivers_m"] = req["receivers_m"][::-1]
    req["mesh"]["hx_m"].flags.writeable = False
    original = deepcopy(req)
    result = op.forward_magnetic(req)
    np.testing.assert_array_equal(result["geometry"]["active_indices"], [0, 2, 3, 7, 11])
    np.testing.assert_allclose(result["geometry"]["active_bounds_m"], bounds(req), atol=1e-12)
    np.testing.assert_array_equal(result["geometry"]["receivers_m"], req["receivers_m"])
    np.testing.assert_allclose(result["geometry"]["active_centres_m"],
                               (bounds(req)[:, ::2]+bounds(req)[:, 1::2])/2, rtol=1e-10)
    np.testing.assert_allclose(result["geometry"]["active_volumes_m3"],
                               np.prod(bounds(req)[:, 1::2]-bounds(req)[:, ::2], axis=1), rtol=1e-10)
    inputs = [*req["mesh"].values(), req["receivers_m"], req["susceptibility_si"]]
    outputs = arrays(result)
    for a in outputs:
        assert a.flags.owndata and a.base is None and a.flags.c_contiguous and not a.flags.writeable
        assert np.isfinite(a).all()
        with pytest.raises(ValueError): a.flat[0] = 2
        assert not any(np.shares_memory(a, b) for b in inputs)
    for i, a in enumerate(outputs):
        assert not any(np.shares_memory(a, b) for b in outputs[i+1:])
    before_siblings = [a.copy() for a in outputs[1:]]
    outputs[0].flags.writeable = True
    outputs[0].flat[0] += 1  # Expected reversible owner flag, not tamperproof.
    for a, before in zip(outputs[1:], before_siblings): np.testing.assert_array_equal(a, before)
    for key in req["mesh"]: np.testing.assert_array_equal(req["mesh"][key], original["mesh"][key])
    assert not req["mesh"]["hx_m"].flags.writeable
    np.testing.assert_array_equal(req["receivers_m"], original["receivers_m"])
    permutation = [2, 0, 3, 1]
    other = deepcopy(original)
    other["receivers_m"] = other["receivers_m"][permutation]
    np.testing.assert_allclose(op.forward_magnetic(other)["field_components_nt"],
                               op.forward_magnetic(original)["field_components_nt"][permutation], atol=1e-7)
    other = request(True)
    other["mesh"]["active"][[0, 6]] = [False, True]
    np.testing.assert_allclose(op.forward_magnetic(other)["field_components_nt"], physical_oracle(other),
                               rtol=2e-8, atol=1e-7)


@pytest.mark.parametrize("point", [[0., 0., -60.], [-50., 0., -60.], [50., 40., 0.], [-50., -40., -120.]])
@pytest.mark.parametrize("zero_chi", [False, True])
def test_receiver_volume_rejection(point, zero_chi, monkeypatch):
    req = request()
    req["receivers_m"][0] = point
    if zero_chi: req["susceptibility_si"][:] = 0.
    monkeypatch.setattr(op.magnetics.simulation, "Simulation3DIntegral",
                        lambda *args, **kwargs: pytest.fail("engine before exterior rejection"))
    with pytest.raises(ValueError, match="receivers_m"):
        op.forward_magnetic(req)


def test_inactive_volume_is_not_exterior(monkeypatch):
    req = request(True)
    req["receivers_m"][0] = [-60., -160., -230.]  # Inside inactive cell index1.
    monkeypatch.setattr(op.magnetics.simulation, "Simulation3DIntegral",
                        lambda *args, **kwargs: pytest.fail("engine before full-volume rejection"))
    with pytest.raises(ValueError, match="receivers_m"):
        op.forward_magnetic(req)


@pytest.mark.parametrize("i,d,expected", [(0., 0., [0., 1., 0.]), (0., 90., [1., 0., 0.]),
                                         (0., -90., [-1., 0., 0.]), (0., -180., [0., -1., 0.]),
                                         (90., 0., [0., 0., -1.]), (-90., 0., [0., 0., 1.]),
                                         (37., -73., None)])
def test_field_direction_and_units(i, d, expected):
    req = request(True)
    req["inducing_field"].update(inclination_deg=i, declination_deg=d)
    result = op.forward_magnetic(req)
    f = direction(req)
    np.testing.assert_allclose(result["inducing_field"]["direction_enu"], f, atol=2e-16)
    if expected is not None:
        np.testing.assert_allclose(f, expected, atol=2e-16)
    oracle = physical_oracle(req)
    np.testing.assert_allclose(result["field_components_nt"], oracle, rtol=2e-8, atol=1e-7)
    np.testing.assert_allclose(result["linear_tmi_nt"], oracle@f, rtol=2e-8, atol=1e-7)


@pytest.mark.parametrize("key", ["amplitude_nt", "inclination_deg", "declination_deg"])
@pytest.mark.parametrize("bad", [True, 1, np.float64(1.), float("nan"), float("inf"), Hook()])
def test_field_strict_native_floats(key, bad):
    req = request()
    req["inducing_field"][key] = bad
    with pytest.raises((TypeError, ValueError)):
        op.forward_magnetic(req)


@pytest.mark.parametrize("key,value", [("amplitude_nt", 0.999), ("amplitude_nt", 1000000.1),
                                      ("inclination_deg", -90.001), ("inclination_deg", 90.001),
                                      ("declination_deg", -180.001), ("declination_deg", 180.)])
def test_field_ranges(key, value):
    req = request()
    req["inducing_field"][key] = value
    with pytest.raises(ValueError, match=key): op.forward_magnetic(req)


def test_actual_engine_precision_order(monkeypatch):
    original = op.magnetics.simulation.Simulation3DIntegral
    captured = []

    def actual(*args, **kwargs):
        assert kwargs["engine"] == "geoana" and kwargs["store_sensitivities"] == "ram"
        assert kwargs["sensitivity_dtype"] is np.float64 and kwargs["n_processes"] == 1
        assert kwargs["chiMap"].nP == 5
        simulation = original(*args, **kwargs)
        captured.append(simulation)
        return simulation

    monkeypatch.setattr(op.magnetics.simulation, "Simulation3DIntegral", actual)
    req = request(True)
    result = op.forward_magnetic(req)
    sim = captured[0]
    assert sim.G.dtype == np.float64 and sim.G.shape == (12, 5) and sim.model_type == "scalar"
    native = sim.dpred(req["susceptibility_si"]).reshape(4, 3)
    np.testing.assert_allclose(native, result["field_components_nt"], atol=1e-10, rtol=1e-12)
    np.testing.assert_allclose(sim.G@req["susceptibility_si"], native.ravel(), atol=1e-10, rtol=1e-12)
    columns = physical_oracle(req, unit_columns=True)  # (receiver,cell,component), chi=1 oracle only.
    expected_j = np.einsum("nca,a->nc", columns, direction(req))
    np.testing.assert_allclose(result["linear_jacobian_nt_per_si"], expected_j, atol=1e-7, rtol=2e-8)


def test_components_projection_exact_magnitude():
    req = request(True)
    result = op.forward_magnetic(req)
    b, f, F = result["field_components_nt"], direction(req), req["inducing_field"]["amplitude_nt"]
    np.testing.assert_allclose(result["linear_tmi_nt"], b@f, atol=1e-10, rtol=1e-12)
    np.testing.assert_allclose(result["exact_magnitude_anomaly_nt"], np.linalg.norm(F*f+b, axis=1)-F,
                               atol=1e-7, rtol=2e-8)
    np.testing.assert_allclose(result["linearization"]["secondary_to_background_ratio"],
                               np.linalg.norm(b, axis=1)/F, rtol=1e-12)
    np.testing.assert_allclose(result["linearization"]["exact_minus_linear_nt"],
                               result["exact_magnitude_anomaly_nt"]-result["linear_tmi_nt"], atol=0)
    assert result["linearization"]["maximum_abs_difference_nt"] == float(
        np.max(abs(result["exact_magnitude_anomaly_nt"]-result["linear_tmi_nt"])))
    assert result["linearization"]["maximum_abs_difference_nt"] > 0
    half = deepcopy(req)
    half["susceptibility_si"] *= .5
    np.testing.assert_allclose(op.forward_magnetic(half)["field_components_nt"], b*.5, atol=1e-10, rtol=1e-12)
    twice = deepcopy(req)
    twice["inducing_field"]["amplitude_nt"] *= 2
    np.testing.assert_allclose(op.forward_magnetic(twice)["field_components_nt"], b*2, atol=1e-10, rtol=1e-12)
    null = deepcopy(req)
    null["susceptibility_si"][:] = 0
    zero = op.forward_magnetic(null)
    np.testing.assert_array_equal(zero["field_components_nt"], np.zeros_like(b))
    np.testing.assert_array_equal(zero["exact_magnitude_anomaly_nt"], np.zeros(len(b)))


@pytest.mark.parametrize("b", [(1e-4, 0., 0.), (-1e-4, 0., 0.), (0., 1e-10, 0.),
                              (0., -1e-10, 0.), (0., 0., 0.)])
def test_tiny_decimal_independent_norm(b):
    F, B0 = 50000., np.array([0., 50000., 0.])
    actual = float(op._exact_magnitude(B0, np.array([b]), F)[0])
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 80, ROUND_HALF_EVEN
        reference = sum((Decimal.from_float(float(B0[a]))+Decimal.from_float(b[a]))**2
                        for a in range(3)).sqrt()-Decimal.from_float(F)
        observed = Decimal.from_float(actual)
        if reference == 0:
            assert actual == 0
        else:
            assert actual != 0 and (observed > 0) == (reference > 0)
            assert abs(observed-reference) <= Decimal("2e-8")*abs(reference)
            assert abs(reference) > Decimal("2e-8")*abs(reference)  # Zero would fail.


def volume_quadrature(req, nodes):
    xi, wi = leggauss(nodes)
    r = req["receivers_m"][0]
    answer = np.zeros(3)
    for prism, chi in zip(bounds(req), req["susceptibility_si"]):
        lo, hi = prism[::2], prism[1::2]
        points = np.stack(np.meshgrid(*[(l+h)/2+(h-l)/2*xi for l, h in zip(lo, hi)],
                                     indexing="ij"), axis=-1).reshape(-1, 3)
        w = np.einsum("i,j,k->ijk", wi, wi, wi).ravel()*np.prod((hi-lo)/2)
        R = r-points
        radius = np.linalg.norm(R, axis=1)
        M = chi*direction(req)*req["inducing_field"]["amplitude_nt"]*1e-9/MU0
        kernel = 3*(R@M)[:, None]*R/radius[:, None]**5-M/radius[:, None]**3
        answer += MU0/(4*math.pi)*np.sum(w[:, None]*kernel, axis=0)*1e9
    return answer


@pytest.mark.parametrize("multi", [False, True])
def test_independent_prism_and_quadrature(multi):
    req = request(multi)
    req["mesh"]["origin_m"] += [230., -170., 40.]
    req["receivers_m"] = np.array([[1000., 700., 1400.]])
    q16, q24, q32 = [volume_quadrature(req, n) for n in (16, 24, 32)]
    for prism in bounds(req):
        diagonal = np.linalg.norm(prism[1::2]-prism[::2])
        assert np.linalg.norm(req["receivers_m"][0]-(prism[::2]+prism[1::2])/2) >= 1.5*diagonal
    assert np.isfinite(q16).all()
    np.testing.assert_allclose(q24, q32, atol=1e-8, rtol=2e-8)
    candidate = op.forward_magnetic(req)["field_components_nt"][0]
    np.testing.assert_allclose(candidate, q32, atol=1e-7, rtol=2e-8)
    np.testing.assert_allclose(candidate, physical_oracle(req)[0], atol=1e-7, rtol=2e-8)
    req = request()
    req["receivers_m"] = np.array([[10000., 13000., 17000.]])
    prism = bounds(req)[0]
    R = req["receivers_m"][0]-(prism[::2]+prism[1::2])/2
    assert np.linalg.norm(R) >= 20*np.max(prism[1::2]-prism[::2])
    M = direction(req)*req["inducing_field"]["amplitude_nt"]*1e-9/MU0*req["susceptibility_si"][0]
    dipole = MU0/(4*math.pi)*np.prod(prism[1::2]-prism[::2]) * (
        3*np.dot(M, R)*R/np.linalg.norm(R)**5-M/np.linalg.norm(R)**3)*1e9
    analytic = op.forward_magnetic(req)["field_components_nt"][0]
    assert np.linalg.norm(dipole) > 0
    assert np.linalg.norm(analytic-dipole)/np.linalg.norm(dipole) <= .003


def test_remanence_and_wrong_field_nonclaims():
    req = request()
    actual = op.forward_magnetic(req)
    remanent = physical_oracle(req, magnetizations=[np.array([8., -5.5, 2.3])])
    assert np.linalg.norm(remanent-actual["field_components_nt"])/np.linalg.norm(remanent) > .1
    wrong = deepcopy(req)
    wrong["inducing_field"].update(inclination_deg=-35., declination_deg=-100.)
    changed = op.forward_magnetic(wrong)
    assert np.linalg.norm(changed["field_components_nt"]-actual["field_components_nt"]) > .1
    for result in (actual, changed):
        assert result["linearization"]["interpretation"] == "uniform-induced-no-self-demagnetization"
        assert result["linearization"]["field_source_verified"] is False
        assert result["linearization"]["full_method_accepted"] is False
        assert result["linearization"]["host_approved"] is False


@pytest.mark.parametrize("field", ["origin", "hx", "hy", "hz", "chi", "receivers"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_nonfinite(field, bad):
    req = request()
    a = {"origin": req["mesh"]["origin_m"], "hx": req["mesh"]["hx_m"],
         "hy": req["mesh"]["hy_m"], "hz": req["mesh"]["hz_m"],
         "chi": req["susceptibility_si"], "receivers": req["receivers_m"]}[field]
    a.flat[0] = bad
    with pytest.raises(ValueError): op.forward_magnetic(req)


@pytest.mark.parametrize("bad", ["width_low", "width_high", "span", "origin", "edge", "receiver",
                                 "chi_low", "chi_high", "active_zero", "chi_alignment", "rounded_edges"])
def test_physical_input_rejection(bad):
    req = request()
    if bad == "width_low": req["mesh"]["hx_m"][0] = .000999
    elif bad == "width_high": req["mesh"]["hx_m"][0] = 100000.1
    elif bad == "span":
        req["mesh"].update(hx_m=np.array([60000., 60000.]), active=np.ones(2, bool))
        req["susceptibility_si"] = np.zeros(2)
    elif bad == "origin": req["mesh"]["origin_m"][0] = -10000000.1
    elif bad == "edge": req["mesh"]["origin_m"][0] = 9999990.
    elif bad == "receiver": req["receivers_m"][0, 0] = 10000000.1
    elif bad == "chi_low": req["susceptibility_si"][0] = -.0001
    elif bad == "chi_high": req["susceptibility_si"][0] = .10000001
    elif bad == "active_zero": req["mesh"]["active"][:] = False
    elif bad == "chi_alignment": req["susceptibility_si"] = np.zeros(2)
    elif bad == "rounded_edges":
        req["mesh"]["origin_m"][0], req["mesh"]["hx_m"][0] = 9000000., .001
    with pytest.raises((ValueError, RuntimeError)): op.forward_magnetic(req)


@pytest.mark.parametrize("bad", ["runtime", "kernel_shape", "kernel_dtype", "kernel_nan",
                                 "prediction_shape", "prediction_dtype", "prediction_nan", "state_identity",
                                 "derived_overflow"])
def test_runtime_output_and_scope(bad, monkeypatch):
    req = request()
    if bad == "runtime":
        monkeypatch.setattr(op.geoana, "__version__", "wrong")
    else:
        class Malformed:
            @property
            def G(self):
                if bad == "kernel_shape": return np.zeros((2, 1))
                if bad == "kernel_dtype": return np.zeros((9, 1), dtype=np.float32)
                if bad == "kernel_nan": return np.full((9, 1), np.nan)
                if bad == "derived_overflow": return np.full((9, 1), 1e300)
                return np.ones((9, 1))

            def dpred(self, model):
                if bad == "prediction_shape": return np.zeros(2)
                if bad == "prediction_dtype": return np.zeros(9, dtype=np.float32)
                if bad == "prediction_nan": return np.full(9, np.nan)
                if bad == "derived_overflow": return self.G@model
                return np.zeros(9)
        monkeypatch.setattr(op.magnetics.simulation, "Simulation3DIntegral", lambda *args, **kw: Malformed())
    with pytest.raises(RuntimeError): op.forward_magnetic(req)


def test_external_pins_and_acceptance_boundary():
    assert op.ENGINE == ENGINE and op.SOURCE_EPOCH == "m04-induced-prism-cpu-1"
    versions = {"simpeg": "0.25.2", "geoana": "0.8.1", "discretize": "0.12.0",
                "numpy": "2.2.6", "scipy": "1.15.2", "choclo": "0.3.2",
                "numba": "0.67.0", "llvmlite": "0.49.0"}
    assert {key: importlib.metadata.version(key) for key in versions} == versions
    research = (ROOT/"docs/design/features/m04-induced-prism/research.md").read_text(encoding="utf-8")
    magnetic_pins = dict(re.findall(r"\| ([a-z_/]+\.py) \| ([a-f0-9]{64}) \|", research))
    assert len(magnetic_pins) == 4
    shared = json.loads((ROOT/"docs/design/features/m02-prism-operator/runtime-pins.json").read_text())
    used_pins = {p: h for p, h in shared["targeted_source_sha256"].items()
                 if not p.startswith("simpeg/potential_fields/gravity/") and not p.endswith("_gravity.py")}
    for relative, expected in {**used_pins, **magnetic_pins}.items():
        package = relative.split("/")[0]
        actual = importlib.metadata.distribution(package).locate_file(relative).read_bytes()
        assert hashlib.sha256(actual).hexdigest() == expected, relative
    tree = ast.parse((ROOT/"data-pipeline/magnetic_forward.py").read_text())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.update(n.name.split(".")[0] for n in node.names)
        if isinstance(node, ast.ImportFrom): imports.add(node.module.split(".")[0])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"open", "eval", "exec", "__import__"}
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"save", "savetxt", "load", "write", "write_bytes", "write_text"}
    assert imports <= {"sys", "numpy", "scipy", "simpeg", "geoana", "discretize"}
    assert "gravity_forward" not in imports


def test_all_array_metadata_precedes_float_scans(monkeypatch):
    req = request()
    req["mesh"]["origin_m"][:] = np.nan
    req["receivers_m"] = np.zeros((2049, 3))
    # Native scalar field validation currently precedes metadata; trap only array scans.
    original = np.isfinite

    def finite(value):
        if type(value) is np.ndarray: pytest.fail("array finite scan before late cap")
        return original(value)
    monkeypatch.setattr(op.np, "isfinite", finite)
    with pytest.raises(ValueError, match="receivers_m"): op.forward_magnetic(req)


@pytest.mark.parametrize("path", ["origin_m", "hx_m", "hy_m", "hz_m", "active", "receivers_m", "susceptibility_si"])
@pytest.mark.parametrize("bad", ["hook", "list", "dtype", "subclass", "ndim"])
def test_every_array_native_metadata(path, bad, monkeypatch):
    req = request()
    container = req["mesh"] if path in req["mesh"] else req
    value = container[path]
    if bad == "hook": container[path] = Hook()
    elif bad == "list": container[path] = value.tolist()
    elif bad == "dtype": container[path] = value.astype(float if path == "active" else np.float32)
    elif bad == "subclass": container[path] = value.view(type("ArraySub", (np.ndarray,), {}))
    elif bad == "ndim": container[path] = value.reshape(-1, 1) if value.ndim == 1 else value.ravel()
    monkeypatch.setattr(op, "_snapshot", lambda *args: pytest.fail("snapshot before all metadata validation"))
    with pytest.raises((TypeError, ValueError)): op.forward_magnetic(req)


@pytest.mark.parametrize("container", ["root", "frame", "mesh", "inducing_field"])
def test_every_nested_key_is_native_string(container):
    req = request()
    obj = req if container == "root" else req[container]
    key = next(iter(obj))
    value = obj.pop(key)
    obj[type("StringSub", (str,), {})(key)] = value
    with pytest.raises(ValueError, match="keys"): op.forward_magnetic(req)


@pytest.mark.parametrize("key", ["kind", "length_unit", "vertical_positive"])
def test_exact_frame_enums(key):
    req = request()
    req["frame"][key] = "unknown"
    with pytest.raises(ValueError, match=key): op.forward_magnetic(req)


def test_closed_result_schema_and_types():
    result = op.forward_magnetic(request(True))
    assert set(result) == {"schema", "engine", "source_epoch", "inducing_field", "geometry",
                           "field_components_nt", "linear_tmi_nt", "linear_jacobian_nt_per_si",
                           "exact_magnitude_anomaly_nt", "linearization"}
    assert result["schema"] == "magnetic-prism-forward-result-1"
    assert set(result["inducing_field"]) == {"amplitude_nt", "inclination_deg", "declination_deg",
                                            "direction_enu", "background_enu_nt"}
    assert set(result["geometry"]) == {"receivers_m", "active_indices", "active_bounds_m",
                                      "active_centres_m", "active_volumes_m3", "cell_order"}
    assert set(result["linearization"]) == {"secondary_to_background_ratio", "exact_minus_linear_nt",
                                           "maximum_abs_difference_nt", "interpretation",
                                           "field_source_verified", "full_method_accepted", "host_approved"}
    assert result["geometry"]["cell_order"] == "x-fast"
    assert type(result["linearization"]["maximum_abs_difference_nt"]) is float
    for name in ("amplitude_nt", "inclination_deg", "declination_deg"):
        assert type(result["inducing_field"][name]) is float
    shapes = [(result["inducing_field"]["direction_enu"], (3,)),
              (result["inducing_field"]["background_enu_nt"], (3,)),
              (result["geometry"]["receivers_m"], (4, 3)),
              (result["geometry"]["active_indices"], (5,)),
              (result["geometry"]["active_bounds_m"], (5, 6)),
              (result["geometry"]["active_centres_m"], (5, 3)),
              (result["geometry"]["active_volumes_m3"], (5,)),
              (result["field_components_nt"], (4, 3)),
              (result["linear_tmi_nt"], (4,)),
              (result["linear_jacobian_nt_per_si"], (4, 5)),
              (result["exact_magnitude_anomaly_nt"], (4,)),
              (result["linearization"]["secondary_to_background_ratio"], (4,)),
              (result["linearization"]["exact_minus_linear_nt"], (4,))]
    for a, shape in shapes:
        assert type(a) is np.ndarray and a.shape == shape
        assert a.dtype == (np.int64 if a is result["geometry"]["active_indices"] else np.float64)


def test_signed_lobes_and_zero_jacobian_not_zero_operator():
    req = request()
    req["inducing_field"].update(inclination_deg=90., declination_deg=0.)
    req["receivers_m"] = np.array([[0., 0., 200.], [700., 0., 20.], [0., 700., 20.]])
    result = op.forward_magnetic(req)
    assert result["linear_tmi_nt"][0] > 0
    assert np.all(result["linear_tmi_nt"][1:] < 0)
    np.testing.assert_allclose(result["field_components_nt"], physical_oracle(req), rtol=2e-8, atol=1e-7)
    zero = deepcopy(req)
    zero["susceptibility_si"][:] = 0.
    np.testing.assert_array_equal(op.forward_magnetic(zero)["linear_tmi_nt"], np.zeros(3))
    np.testing.assert_allclose(op.forward_magnetic(zero)["linear_jacobian_nt_per_si"],
                               result["linear_jacobian_nt_per_si"], atol=0, rtol=0)


def test_linear_jacobian_directional_difference():
    req = request(True)
    result = op.forward_magnetic(req)
    step = 1e-6
    changed = deepcopy(req)
    perturbation = np.array([.2, -.1, .3, -.2, .1])
    changed["susceptibility_si"] += step*perturbation
    difference = (op.forward_magnetic(changed)["linear_tmi_nt"]-result["linear_tmi_nt"])/step
    np.testing.assert_allclose(difference, result["linear_jacobian_nt_per_si"]@perturbation,
                               rtol=2e-8, atol=1e-7)


@pytest.mark.parametrize("package", ["simpeg", "geoana", "discretize", "np", "scipy"])
def test_every_loaded_package_epoch(package, monkeypatch):
    monkeypatch.setattr(getattr(op, package), "__version__", "unreviewed")
    with pytest.raises(RuntimeError, match="runtime"): op.forward_magnetic(request())


@pytest.mark.parametrize("kind", ["python", "platform", "bits"])
def test_python_platform_epoch(kind, monkeypatch):
    with monkeypatch.context() as patch:
        if kind == "python": patch.setattr(op.sys, "version_info", (3, 12, 9))
        elif kind == "platform": patch.setattr(op.sys, "platform", "linux")
        else: patch.setattr(op.sys, "maxsize", 2**31-1)
        with pytest.raises(RuntimeError, match="runtime"): op.forward_magnetic(request())


def test_bad_actual_tensor_geometry(monkeypatch):
    original = op.discretize.TensorMesh

    def wrong(widths, **kwargs):
        actual = [w.copy() for w in widths]
        actual[0] *= 1.001
        return original(actual, **kwargs)

    monkeypatch.setattr(op.discretize, "TensorMesh", wrong)
    with pytest.raises(ValueError, match="mesh"): op.forward_magnetic(request())


def test_no_ordinary_function_file_or_network_io(monkeypatch):
    import builtins
    import socket
    # Engines are already loaded; this gate checks ordinary request execution,
    # not a claim that Python/vendor import itself has no file reads.
    def forbidden(*args, **kwargs):
        pytest.fail("ordinary function attempted file/network I/O")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    result = op.forward_magnetic(request())
    assert result["linearization"]["host_approved"] is False


@pytest.mark.parametrize("amplitude", [1., 1000000.])
@pytest.mark.parametrize("width", [.001, 100000.])
def test_numeric_bounds_are_inclusive(amplitude, width):
    req = request()
    req["mesh"].update(origin_m=np.zeros(3), hx_m=np.array([width]), hy_m=np.array([width]), hz_m=np.array([width]))
    req["receivers_m"] = np.array([[width*2+1., width*3+1., width*4+1.]])
    req["inducing_field"]["amplitude_nt"] = amplitude
    req["susceptibility_si"][0] = .1
    result = op.forward_magnetic(req)
    assert np.isfinite(result["field_components_nt"]).all()
    np.testing.assert_allclose(result["field_components_nt"], physical_oracle(req), atol=1e-7, rtol=2e-8)


def test_memory_error_is_not_success_or_backend_fallback(monkeypatch):
    def oom(*args, **kwargs):
        raise MemoryError("isolated deterministic negative")
    monkeypatch.setattr(op.magnetics.simulation, "Simulation3DIntegral", oom)
    with pytest.raises(MemoryError): op.forward_magnetic(request())
