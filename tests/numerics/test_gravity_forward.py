"""Original ordinary forward controls; not uploaded-field or inverse acceptance."""

import ast
import builtins
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess

import choclo
import numpy as np
from numpy.polynomial.legendre import leggauss
import pytest
from scipy.constants import G

import gravity_forward as op


ROOT = Path(__file__).resolve().parents[2]
PINS = ROOT / "docs/design/features/m02-prism-operator/runtime-pins.json"


def request(nonuniform=False):
    origin = [-50., -50., -100.]
    widths = [[100.], [100.], [100.]]
    active = np.array([True])
    density = [1000.]
    receivers = [[0., 0., 100.], [100., 50., 120.], [-170., 30., 220.]]
    if nonuniform:
        origin, widths = [-140., -180., -260.], [[40., 70.], [30., 50., 90.], [60., 110.]]
        active = np.zeros(12, dtype=bool)
        active[[0, 2, 3, 7, 11]] = True
        density = [400., -600., 900., -300., 1200.]
        receivers = [[0., 0., 100.], [230., -50., 40.], [-400., 60., -350.], [70., 260., -150.]]
    return {
        "schema": "gravity-prism-forward-request-1", "frame": dict(op.FRAME), "engine": op.ENGINE,
        "mesh": {"origin_m": np.array(origin), "hx_m": np.array(widths[0]),
                 "hy_m": np.array(widths[1]), "hz_m": np.array(widths[2]), "active": active},
        "receivers_m": np.array(receivers), "density_kg_m3": np.array(density),
    }


def oracle_bounds(req):
    # Explicit nested physical-cell traversal, independent of operator ordering code.
    x, y, z = [o + np.r_[0., np.cumsum(req["mesh"][key])]
               for o, key in zip(req["mesh"]["origin_m"], ("hx_m", "hy_m", "hz_m"))]
    result = []
    index = 0
    for k in range(len(z) - 1):
        for j in range(len(y) - 1):
            for i in range(len(x) - 1):
                if req["mesh"]["active"][index]:
                    result.append([x[i], x[i+1], y[j], y[j+1], z[k], z[k+1]])
                index += 1
    return np.array(result)


def choclo_oracle(req, density=None):
    rho = req["density_kg_m3"] if density is None else density
    bounds = oracle_bounds(req)
    return np.array([sum(choclo.prism.gravity_u(*r, *b, d) for b, d in zip(bounds, rho)) * 1e5
                     for r in req["receivers_m"]])


class Hook:
    def __eq__(self, other):
        raise AssertionError("custom equality hook executed")

    def __array__(self, *args, **kwargs):
        raise AssertionError("custom array hook executed")


@pytest.mark.parametrize("kind", ["top_extra", "missing", "nested_extra", "schema_hook", "engine_hook",
                                 "axis_hook", "axes_list", "frame_hook", "array_hook", "array_subclass",
                                 "float32", "complex", "object", "list", "wrong_shape", "nan", "inf",
                                 "root_subclass", "mesh_subclass", "string_subclass", "unit_hook",
                                 "origin_hook", "width_hook", "mask_hook", "swapped_endian"])
def test_exact_protocol_and_types(kind):
    req = request()
    if kind == "top_extra": req["observed_gravity"] = np.ones(3)
    elif kind == "missing": del req["schema"]
    elif kind == "nested_extra": req["mesh"]["import_path"] = "private/source.py"
    elif kind == "schema_hook": req["schema"] = Hook()
    elif kind == "engine_hook": req["engine"] = Hook()
    elif kind == "axis_hook": req["frame"]["axes"] = (Hook(), "north", "up")
    elif kind == "axes_list": req["frame"]["axes"] = ["east", "north", "up"]
    elif kind == "frame_hook": req["frame"] = Hook()
    elif kind == "array_hook": req["density_kg_m3"] = Hook()
    elif kind == "array_subclass": req["density_kg_m3"] = req["density_kg_m3"].view(type("ArraySub", (np.ndarray,), {}))
    elif kind == "root_subclass": req = type("DictSub", (dict,), {})(req)
    elif kind == "mesh_subclass": req["mesh"] = type("DictSub", (dict,), {})(req["mesh"])
    elif kind == "string_subclass": req["schema"] = type("StrSub", (str,), {"__eq__": Hook.__eq__})(req["schema"])
    elif kind == "unit_hook": req["frame"]["length_unit"] = Hook()
    elif kind == "origin_hook": req["mesh"]["origin_m"] = Hook()
    elif kind == "width_hook": req["mesh"]["hx_m"] = Hook()
    elif kind == "mask_hook": req["mesh"]["active"] = Hook()
    elif kind == "swapped_endian": req["density_kg_m3"] = req["density_kg_m3"].astype(">f8")
    elif kind in ("float32", "complex", "object"): req["density_kg_m3"] = req["density_kg_m3"].astype({"float32": "f4", "complex": "c16", "object": "O"}[kind])
    elif kind == "list": req["density_kg_m3"] = [1000.]
    elif kind == "wrong_shape": req["density_kg_m3"] = np.ones((1, 1))
    elif kind == "nan": req["density_kg_m3"][0] = np.nan
    elif kind == "inf": req["receivers_m"][0, 0] = np.inf
    with pytest.raises((TypeError, ValueError)):
        op.forward_gravity(req)


@pytest.mark.parametrize("kind", ["zero_receivers", "too_many_receivers", "too_many_cells", "all_inactive",
                                 "negative_width", "zero_width", "collapsed_edges", "volume_overflow",
                                 "wrong_frame", "wrong_units", "wrong_axes", "wrong_mask_type"])
def test_geometry_counts_and_frame(kind):
    req = request()
    if kind == "zero_receivers": req["receivers_m"] = np.empty((0, 3))
    elif kind == "too_many_receivers": req["receivers_m"] = np.tile([0., 0., 100.], (2049, 1))
    elif kind == "too_many_cells": req["mesh"]["hx_m"] = np.ones(4097)
    elif kind == "all_inactive": req["mesh"]["active"][:] = False
    elif kind == "negative_width": req["mesh"]["hx_m"][0] = -1
    elif kind == "zero_width": req["mesh"]["hx_m"][0] = 0
    elif kind == "collapsed_edges": req["mesh"]["origin_m"][0] = 1e100
    elif kind == "volume_overflow":
        req["mesh"]["origin_m"][:] = 0
        for key in ("hx_m", "hy_m", "hz_m"): req["mesh"][key][:] = 1e200
        req["receivers_m"][:] = -1
    elif kind == "wrong_frame": req["frame"]["kind"] = "EPSG:4326"
    elif kind == "wrong_units": req["frame"]["length_unit"] = "ft"
    elif kind == "wrong_axes": req["frame"]["axes"] = ("north", "east", "up")
    elif kind == "wrong_mask_type": req["mesh"]["active"] = np.ones(1, dtype=int)
    with pytest.raises((TypeError, ValueError)):
        op.forward_gravity(req)


@pytest.mark.parametrize("field", ["origin", "axis", "cell_product", "active", "density", "receivers", "receiver_columns"])
def test_metadata_caps_precede_all_scans_and_copies(monkeypatch, field):
    req = request()
    if field == "origin": req["mesh"]["origin_m"] = np.zeros(5000)
    elif field == "axis": req["mesh"]["hx_m"] = np.ones(5000)
    elif field == "cell_product":
        req["mesh"]["hx_m"] = np.ones(65); req["mesh"]["hy_m"] = np.ones(65)
    elif field == "active": req["mesh"]["active"] = np.ones(5000, dtype=bool)
    elif field == "density": req["density_kg_m3"] = np.ones(5000)
    elif field == "receivers": req["receivers_m"] = np.ones((2049, 3))
    elif field == "receiver_columns": req["receivers_m"] = np.ones((1, 5000))
    def deny(*args, **kwargs): raise AssertionError("scan/copy/engine before complete metadata admission")
    for name in ("isfinite", "array", "count_nonzero"):
        monkeypatch.setattr(op.np, name, deny)
    monkeypatch.setattr(op.gravity.simulation, "Simulation3DIntegral", deny)
    with pytest.raises(ValueError): op.forward_gravity(req)


@pytest.mark.parametrize("position", [[0., 0., -50.], [0., 0., 0.], [50., 50., 0.], [-50., 0., -50.]])
def test_receiver_outside_volume_policy(position):
    req = request()
    req["density_kg_m3"][:] = 0
    req["receivers_m"] = np.array([position])
    with pytest.raises(ValueError, match="outside closed"):
        op.forward_gravity(req)


def test_receivers_on_each_external_side():
    req = request()
    req["receivers_m"] = np.array([[-60., 0., -50.], [60., 0., -50.], [0., -60., -50.],
                                    [0., 60., -50.], [0., 0., -110.], [0., 0., 10.]])
    out = op.forward_gravity(req)
    np.testing.assert_allclose(out["gz_up_mgal"], choclo_oracle(req), rtol=1e-7, atol=1e-10)
    assert out["gz_up_mgal"][-2] > 0 and out["gz_up_mgal"][-1] < 0
    # Being inside an inactive cell does not waive the full-box restriction.
    req = request(True)
    req["receivers_m"] = np.array([[-100., -130., -200.]])
    with pytest.raises(ValueError, match="outside closed"):
        op.forward_gravity(req)


@pytest.mark.parametrize("origin,widths", [(1e16, [2.]), (1e16, [2., 2.]), (1e12, [.0001220703125])])
@pytest.mark.parametrize("inactive", [False, True])
def test_unrepresentable_centres_reject_before_prism_engine(monkeypatch, origin, widths, inactive):
    req = request()
    req["mesh"]["origin_m"][:] = origin
    for key in ("hx_m", "hy_m", "hz_m"): req["mesh"][key] = np.array(widths)
    n = len(widths)**3
    req["mesh"]["active"] = np.ones(n, dtype=bool)
    req["density_kg_m3"] = np.ones(n)
    if inactive:
        # One representable active cell cannot exempt a collapsed inactive cell.
        req["mesh"]["hx_m"] = np.array([widths[0], 4. * widths[0]])
        req["mesh"]["hy_m"] = req["mesh"]["hz_m"] = np.array([4. * widths[0]])
        req["mesh"]["active"] = np.array([False, True])
        req["density_kg_m3"] = np.ones(1)
    req["receivers_m"] = np.array([[origin, origin, origin+8*sum(widths)]])
    def deny(*args, **kwargs): raise AssertionError("prism evaluated for invalid centre geometry")
    monkeypatch.setattr(op.gravity.simulation, "Simulation3DIntegral", deny)
    with pytest.raises(ValueError, match="centres.*strictly inside"):
        op.forward_gravity(req)


def test_actual_tensor_nodes_bounds_centres_and_large_offset_control():
    req = request()
    req["mesh"]["origin_m"][:] = 1e16
    for key in ("hx_m", "hy_m", "hz_m"): req["mesh"][key] = np.array([4.])
    req["receivers_m"] = np.array([[1e16, 1e16, 1e16+32.]])
    out = op.forward_gravity(req)
    tensor = op.discretize.TensorMesh([req["mesh"][key] for key in ("hx_m", "hy_m", "hz_m")],
                                    origin=req["mesh"]["origin_m"])
    np.testing.assert_array_equal(out["geometry"]["active_cell_bounds_m"], tensor.cell_bounds)
    np.testing.assert_array_equal(out["geometry"]["active_cell_centres_m"], tensor.cell_centers)
    np.testing.assert_array_equal(out["geometry"]["active_cell_volumes_m3"], tensor.cell_volumes)
    assert out["geometry"]["active_cell_volumes_m3"][0] == 64.
    assert np.all(tensor.cell_centers > tensor.cell_bounds[:, ::2])
    assert np.all(tensor.cell_centers < tensor.cell_bounds[:, 1::2])
    np.testing.assert_allclose(out["gz_up_mgal"], choclo_oracle(req), rtol=1e-7, atol=1e-10)
    # Ordinary decimal accumulation roundoff is admitted, not rejected by a
    # nominal-edge bit-equality test. Output follows actual verified engine nodes.
    req = request()
    req["mesh"]["origin_m"][:] = 1000.
    for key in ("hx_m", "hy_m", "hz_m"): req["mesh"][key] = np.array([.1, .1, .1])
    req["mesh"]["active"] = np.ones(27, dtype=bool)
    req["density_kg_m3"] = np.ones(27)
    req["receivers_m"] = np.array([[1000., 1000., 1010.]])
    out = op.forward_gravity(req)
    tensor = op.discretize.TensorMesh([req["mesh"][key] for key in ("hx_m", "hy_m", "hz_m")],
                                    origin=req["mesh"]["origin_m"])
    np.testing.assert_array_equal(out["geometry"]["active_cell_bounds_m"], tensor.cell_bounds)
    actual_oracle = sum(choclo.prism.gravity_u(*req["receivers_m"][0], *b, rho)
                        for b, rho in zip(out["geometry"]["active_cell_bounds_m"], req["density_kg_m3"])) * 1e5
    np.testing.assert_allclose(out["gz_up_mgal"], [actual_oracle], rtol=1e-7, atol=1e-10)


def test_large_origin_rounded_width_and_volume_reject(monkeypatch):
    req = request()
    req["mesh"]["origin_m"][:] = 1e16
    for key in ("hx_m", "hy_m", "hz_m"): req["mesh"][key] = np.array([3.])
    req["receivers_m"] = np.array([[1e16, 1e16, 1e16+32.]])
    tensor = op.discretize.TensorMesh([np.array([3.])]*3, origin=[1e16]*3)
    assert np.prod(tensor.cell_bounds[0, 1::2] - tensor.cell_bounds[0, ::2]) == 64
    assert tensor.cell_volumes[0] == 27
    def deny(*args, **kwargs): raise AssertionError("prism called for distorted geometry")
    monkeypatch.setattr(op.gravity.simulation, "Simulation3DIntegral", deny)
    with pytest.raises(ValueError, match="local geometry fidelity"):
        op.forward_gravity(req)


@pytest.mark.parametrize("fault", ["nodes", "bounds", "centres", "corners", "volumes"])
def test_tensor_geometry_disagreements_fail_closed(monkeypatch, fault):
    tensor_class = op.discretize.TensorMesh
    property_name = {"nodes": "nodes_x", "bounds": "cell_bounds", "centres": "cell_centers", "corners": "cell_nodes", "volumes": "cell_volumes"}[fault]
    original = getattr(tensor_class, property_name)
    def corrupt(tensor):
        value = original.__get__(tensor, tensor_class).copy()
        if fault == "nodes": value[1:] += 1.
        elif fault == "corners": value[:, 0] = value[:, 1]
        elif fault == "centres": value[:, 0] = tensor.cell_bounds[:, 0]
        elif fault == "volumes": value[:] *= 2
        else: value[:, 0] += 1
        return value
    monkeypatch.setattr(tensor_class, property_name, property(corrupt))
    def deny(*args, **kwargs): raise AssertionError("prism evaluated for inconsistent TensorMesh geometry")
    monkeypatch.setattr(op.gravity.simulation, "Simulation3DIntegral", deny)
    with pytest.raises(ValueError, match="TensorMesh"):
        op.forward_gravity(request())


def test_xfast_activity_and_input_immutability():
    req = request(True)
    req["receivers_m"] = np.asfortranarray(req["receivers_m"])
    original = deepcopy(req)
    result = op.forward_gravity(req)
    np.testing.assert_array_equal(result["geometry"]["active_cell_indices"], [0, 2, 3, 7, 11])
    np.testing.assert_array_equal(result["geometry"]["active_cell_bounds_m"], oracle_bounds(req))
    for key, value in req.items():
        if type(value) is np.ndarray:
            np.testing.assert_array_equal(value, original[key])
        elif key == "mesh":
            for k, a in value.items(): np.testing.assert_array_equal(a, original[key][k])
    for a in (result["gz_up_mgal"], result["jacobian_mgal_per_kg_m3"], *result["geometry"].values()):
        if type(a) is np.ndarray:
            assert not a.flags.writeable and a.flags.c_contiguous
            assert not np.shares_memory(a, req["receivers_m"])
            assert not np.shares_memory(a, req["density_kg_m3"])


def test_actual_required_engine_and_precision(monkeypatch):
    official = op.gravity.simulation.Simulation3DIntegral
    seen = []
    def record(*args, **kwargs):
        seen.append(kwargs.copy())
        return official(*args, **kwargs)
    monkeypatch.setattr(op.gravity.simulation, "Simulation3DIntegral", record)
    req = request()
    req["receivers_m"] = np.tile([0., 0., 100.], (2048, 1))
    assert op.forward_gravity(req)["gz_up_mgal"].shape == (2048,)
    req = request()
    req["mesh"]["hx_m"] = np.ones(4096)
    req["mesh"]["active"] = np.ones(4096, dtype=bool)
    req["density_kg_m3"] = np.ones(4096)
    req["receivers_m"] = np.array([[0., 0., 100.]])
    assert op.forward_gravity(req)["jacobian_mgal_per_kg_m3"].shape == (1, 4096)
    for settings in seen:
        assert settings["engine"] == "geoana" and settings["sensitivity_dtype"] is np.float64
        assert settings["store_sensitivities"] == "ram" and settings["n_processes"] == 1


def test_combined_declared_caps_execute_actual_engine():
    req = request()
    for key in ("hx_m", "hy_m", "hz_m"): req["mesh"][key] = np.full(16, 2.)
    req["mesh"]["active"] = np.ones(4096, dtype=bool)
    req["density_kg_m3"] = np.ones(4096)
    req["receivers_m"] = np.tile([0., 0., 100.], (2048, 1))
    result = op.forward_gravity(req)
    assert result["jacobian_mgal_per_kg_m3"].shape == (2048, 4096)
    assert result["jacobian_mgal_per_kg_m3"].nbytes == 64 * 1024**2
    np.testing.assert_allclose(result["gz_up_mgal"],
                               result["jacobian_mgal_per_kg_m3"] @ req["density_kg_m3"], rtol=1e-10, atol=1e-12)


def test_sign_units_linearity_and_jacobian():
    req = request()
    base = op.forward_gravity(req)
    assert np.all(base["gz_up_mgal"] < 0)
    jac = base["jacobian_mgal_per_kg_m3"]
    for multiplier in (-1., 0., 2.):
        q = deepcopy(req); q["density_kg_m3"] *= multiplier
        out = op.forward_gravity(q)
        np.testing.assert_allclose(out["gz_up_mgal"], base["gz_up_mgal"] * multiplier, rtol=1e-10, atol=1e-12)
        np.testing.assert_array_equal(out["jacobian_mgal_per_kg_m3"], jac)
    assert np.any(jac != 0)
    req = request(True); result = op.forward_gravity(req); jac = result["jacobian_mgal_per_kg_m3"]
    direction = np.array([1., -2., 3., -4., 5.])
    for eps in (1., .1, .01):
        plus, minus = deepcopy(req), deepcopy(req)
        plus["density_kg_m3"] += eps * direction; minus["density_kg_m3"] -= eps * direction
        difference = (op.forward_gravity(plus)["gz_up_mgal"] - op.forward_gravity(minus)["gz_up_mgal"]) / (2 * eps)
        np.testing.assert_allclose(difference, jac @ direction, rtol=1e-6, atol=0)
    v = np.array([1., -2., 3., 4.])
    np.testing.assert_allclose(v @ (jac @ direction), direction @ (jac.T @ v), rtol=1e-10, atol=0)


@pytest.mark.parametrize("nonuniform", [False, True])
def test_independent_choclo_prisms(nonuniform):
    req = request(nonuniform); result = op.forward_gravity(req)
    np.testing.assert_allclose(result["gz_up_mgal"], choclo_oracle(req), rtol=1e-7, atol=1e-10)
    for j in range(len(req["density_kg_m3"])):
        rho = np.zeros(len(req["density_kg_m3"])); rho[j] = 1
        np.testing.assert_allclose(result["jacobian_mgal_per_kg_m3"][:, j], choclo_oracle(req, rho), rtol=1e-7, atol=1e-10)


def volume_integral(bounds, receiver, rho, order):
    t, w = leggauss(order)
    lo, hi = bounds[::2], bounds[1::2]
    axes = [l + (t + 1) * (h - l) / 2 for l, h in zip(lo, hi)]
    x, y, z = np.meshgrid(*axes, indexing="ij")
    weights = np.einsum("i,j,k->ijk", w, w, w) * np.prod((hi - lo) / 2)
    dist2 = (x-receiver[0])**2 + (y-receiver[1])**2 + (z-receiver[2])**2
    return 6.67430e-11 * rho * np.sum(weights * (z-receiver[2]) / dist2**1.5) * 1e5


def test_volume_quadrature_and_physical_limits():
    assert G == choclo.constants.GRAVITATIONAL_CONST == 6.67430e-11
    req = request(); result = op.forward_gravity(req); bounds = oracle_bounds(req)[0]
    sequence = np.array([[volume_integral(bounds, r, 1000., level) for r in req["receivers_m"]]
                         for level in (4, 8, 16)])
    errors = np.abs(sequence - result["gz_up_mgal"])
    assert np.all(errors[-1] <= errors[0] + 1e-12)
    np.testing.assert_allclose(sequence[-1], result["gz_up_mgal"], rtol=1e-5, atol=0)
    # Sphere anchors the independent integral, not a claim of sphere support.
    radius, distance, rho = 100., 500., 1000.
    t, w = leggauss(24); radial = (t+1)*radius/2; mu = t
    rr, mm = np.meshgrid(radial, mu, indexing="ij")
    integral = 2*np.pi * np.sum((rr*mm-distance) / (rr**2+distance**2-2*rr*distance*mm)**1.5
                               * rr**2 * w[:, None]*radius/2 * w[None, :])
    sphere = 6.67430e-11 * rho * integral
    exact = -6.67430e-11 * rho * 4*np.pi*radius**3/3 / distance**2
    np.testing.assert_allclose(sphere, exact, rtol=1e-5, atol=0)
    far = deepcopy(req); far["receivers_m"] = np.array([[0., 0., 9950.], [0., 0., 19950.]])
    p = op.forward_gravity(far)["gz_up_mgal"]
    mass = 1000.*100**3
    np.testing.assert_allclose(p, -6.67430e-11*mass / np.array([10000., 20000.])**2 * 1e5, rtol=1e-3, atol=0)
    np.testing.assert_allclose(p[0]/p[1], 4., rtol=1e-3, atol=0)


@pytest.mark.parametrize("failure", [None, "raise", "float32", "shape", "nan", "state", "memory", "prism_nodes"])
def test_output_protocol_and_engine_failures(monkeypatch, failure):
    if failure is None:
        out = op.forward_gravity(request())
        assert set(out) == {"schema", "frame", "gz_up_mgal", "jacobian_mgal_per_kg_m3", "geometry", "provenance"}
        assert set(out["geometry"]) == {"shape_xyz", "flattening", "active_cell_indices", "active_cell_bounds_m", "active_cell_centres_m", "active_cell_volumes_m3", "receivers_m", "density_kg_m3"}
        assert set(out["provenance"]) == {"engine", "required_source_epoch", "runtime_versions", "python_version", "precision", "sensitivity_storage", "n_processes", "source_verification"}
        return
    official = op.gravity.simulation.Simulation3DIntegral
    def broken(*args, **kwargs):
        sim = official(*args, **kwargs)
        if failure == "prism_nodes": sim._nodes[:, 0] += 1
        fields = sim.fields
        def faulty(q):
            if failure == "raise": raise ValueError("PRIVATE engine diagnostic")
            if failure == "memory": raise MemoryError("PRIVATE allocation context")
            p = fields(q)
            if failure == "float32": sim._G = sim.G.astype(np.float32)
            elif failure == "shape": return p[:, None]
            elif failure == "nan": p[0] = np.nan
            elif failure == "state": p[0] += 1
            return p
        sim.fields = faulty
        return sim
    monkeypatch.setattr(op.gravity.simulation, "Simulation3DIntegral", broken)
    with pytest.raises(MemoryError if failure == "memory" else RuntimeError) as caught:
        op.forward_gravity(request())
    if failure == "raise": assert "PRIVATE" in str(caught.value.__cause__)


def audit_trusted_pins(pin):
    # No path argument from caller/request: only checked-in approved manifest and
    # trusted installed distributions, with an explicit package/relative-path set.
    expected = json.loads(PINS.read_text())
    assert set(pin["targeted_source_sha256"]) == set(expected["targeted_source_sha256"])
    for rel, digest in pin["targeted_source_sha256"].items():
        assert rel in expected["targeted_source_sha256"] and ".." not in Path(rel).parts
        pkg = rel.split("/")[0]
        assert pkg in {"simpeg", "geoana", "discretize", "scipy", "choclo"}
        dist = importlib.metadata.distribution(pkg)
        assert rel in {str(p).replace("\\", "/") for p in dist.files}
        assert hashlib.sha256(dist.locate_file(rel).read_bytes()).hexdigest() == digest


def test_runtime_epoch_and_external_source_pins(monkeypatch):
    pin = json.loads(PINS.read_text()); audit_trusted_pins(pin)
    for name, version in (pin["required_engine_runtime_versions"] | pin["oracle_runtime_versions_observed"]).items():
        assert importlib.metadata.version(name) == version
    altered = deepcopy(pin); altered["targeted_source_sha256"][next(iter(altered["targeted_source_sha256"]))] = "0"*64
    with pytest.raises(AssertionError): audit_trusted_pins(altered)
    altered = deepcopy(pin); altered["targeted_source_sha256"]["../private.py"] = "0"*64
    with pytest.raises(AssertionError): audit_trusted_pins(altered)
    monkeypatch.setattr(op.geoana, "__version__", "wrong")
    with pytest.raises(RuntimeError, match="loaded package"): op.forward_gravity(request())
    monkeypatch.setattr(op.geoana, "__version__", Hook())
    with pytest.raises(RuntimeError, match="loaded package"): op.forward_gravity(request())


def test_no_io_hooks_or_inverse_behavior(monkeypatch):
    source = (ROOT/"data-pipeline/gravity_forward.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [n.name for n in node.names] if isinstance(node, ast.Import) else [node.module]
            assert not any(n.startswith(("os", "pathlib", "socket", "subprocess", "importlib", "urllib", "gravity_inverse")) for n in names)
    def deny(*args, **kwargs): raise AssertionError("application I/O attempted")
    for module, name in [(builtins, "open"), (os, "open"), (os, "mkdir"), (os, "makedirs"),
                         (socket, "socket"), (subprocess, "Popen"), (Path, "read_bytes"), (Path, "read_text")]:
        monkeypatch.setattr(module, name, deny)
    out = op.forward_gravity(request())
    assert out["provenance"]["source_verification"] == "external_required_not_performed_by_operator"


def test_negative_controls_and_literal_scope():
    for key in ("sigma", "observations", "crs", "callback", "import_path", "beta", "gpu"):
        req = request(); req[key] = Hook()
        with pytest.raises(ValueError, match="exact declared keys"): op.forward_gravity(req)
    req = request(); req["density_kg_m3"][:] = 0
    out = op.forward_gravity(req)
    np.testing.assert_array_equal(out["gz_up_mgal"], np.zeros(3))
    assert np.any(out["jacobian_mgal_per_kg_m3"] != 0)
    assert not {"residual", "wrms", "eligible", "solver_success"}.intersection(out)
    req = request(); req["frame"]["vertical_positive"] = "down"
    with pytest.raises(ValueError): op.forward_gravity(req)
