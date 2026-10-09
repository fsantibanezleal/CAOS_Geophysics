"""Bounded ordinary induced-prism forward operator, not magnetic survey admission.

Private caller errors are not safe HTTP payloads. Source-byte verification is
external. Returned arrays are independently owned and write-protected at return,
not tamperproof; no returned storage is retained as trusted future state.
"""

import sys

import discretize
import geoana
import numpy as np
import scipy
import simpeg
from simpeg import maps
from simpeg.potential_fields import magnetics


ENGINE = "simpeg-0.25.2-geoana-0.8.1-f64-induced-ram"
SOURCE_EPOCH = "m04-induced-prism-cpu-1"
VERSIONS = {"simpeg": "0.25.2", "geoana": "0.8.1", "discretize": "0.12.0",
            "numpy": "2.2.6", "scipy": "1.15.2"}
FRAME = {"kind": "local_cartesian", "axes": ("east", "north", "up"),
         "length_unit": "m", "vertical_positive": "up"}
GEOMETRY_RTOL = 1e-10
MAX_FULL_CELLS = 65536
MAX_ACTIVE_CELLS = 8192
MAX_RECEIVERS = 2048
MAX_PROJECTED_ENTRIES = 4194304
CORNER_COLUMNS = np.array([[0, 2, 4], [1, 2, 4], [0, 3, 4], [1, 3, 4],
                           [0, 2, 5], [1, 2, 5], [0, 3, 5], [1, 3, 5]])


def _keys(value, expected, field):
    if type(value) is not dict:
        raise TypeError(f"{field}: expected built-in dict")
    if any(type(key) is not str for key in value) or set(value) != set(expected):
        raise ValueError(f"{field}: exact declared keys required")


def _enum(value, expected, field):
    if type(value) is not str:
        raise TypeError(f"{field}: expected built-in str")
    if value != expected:
        raise ValueError(f"{field}: unsupported value")


def _metadata(value, ndim, field, dtype=np.float64):
    if type(value) is not np.ndarray or value.dtype != np.dtype(dtype):
        raise TypeError(f"{field}: expected native {np.dtype(dtype)} ndarray")
    if value.ndim != ndim:
        raise ValueError(f"{field}: wrong dimensionality")


def _snapshot(value, field):
    if not np.isfinite(value).all():
        raise ValueError(f"{field}: nonfinite values")
    return np.array(value, copy=True, order="C")


def _owned(value, dtype=None):
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if not np.isfinite(array).all():
        raise RuntimeError("result: nonfinite derived values")
    array.flags.writeable = False
    return array


def _runtime():
    loaded = {"simpeg": simpeg, "geoana": geoana, "discretize": discretize, "numpy": np, "scipy": scipy}
    if {key: module.__version__ for key, module in loaded.items()} != VERSIONS:
        raise RuntimeError("runtime: required loaded package versions differ")
    if (sys.version_info[:3] != (3, 12, 10) or sys.platform != "win32"
            or sys.implementation.name != "cpython" or sys.maxsize != 2**63-1):
        raise RuntimeError("runtime: unreviewed Python/platform source epoch")


def _exact_magnitude(background, components, amplitude):
    """Rationalized scalar anomaly; the independent oracle uses direct Decimal sqrt."""
    numerator = components @ (2*background) + np.einsum("ij,ij->i", components, components)
    return numerator / (np.linalg.norm(background+components, axis=1)+amplitude)


def _outside(receivers, lower, upper):
    if not np.all(np.any((receivers < lower) | (receivers > upper), axis=1)):
        raise ValueError("receivers_m: every receiver must be strictly outside closed full source box")


def _tensor_state(tensor, edges, widths, declared):
    """Check public actual TensorMesh geometry against explicitly declared bounds."""
    for actual, expected, w in zip((tensor.nodes_x, tensor.nodes_y, tensor.nodes_z), edges, widths):
        local = np.r_[w[0], np.minimum(w[:-1], w[1:]), w[-1]]
        if (actual.shape != expected.shape or not np.isfinite(actual).all()
                or np.any(np.diff(actual) <= 0)
                or np.any(abs(actual-expected) > GEOMETRY_RTOL*local)
                or np.any(abs(np.diff(actual)-w) > GEOMETRY_RTOL*w)):
            raise ValueError("mesh: actual TensorMesh nodes/widths exceed local fidelity")
    shape = tuple(len(w) for w in widths)
    index = np.unravel_index(np.arange(len(declared)), shape, order="F")
    lengths = np.column_stack([w[i] for w, i in zip(widths, index)])
    actual = tensor.cell_bounds
    if (actual.shape != declared.shape or not np.isfinite(actual).all()
            or np.any(abs(actual-declared) > GEOMETRY_RTOL*np.repeat(lengths, 2, axis=1))):
        raise ValueError("mesh: actual TensorMesh bounds exceed local fidelity")
    corners = tensor.nodes[tensor.cell_nodes]
    if corners.shape != (len(declared), 8, 3) or not np.array_equal(corners, actual[:, CORNER_COLUMNS]):
        raise ValueError("mesh: actual TensorMesh ordered corners disagree")
    centres = tensor.cell_centers
    if (centres.shape != (len(declared), 3) or centres.dtype != np.float64
            or not np.isfinite(centres).all()
            or not np.all((centres > actual[:, ::2]) & (centres < actual[:, 1::2]))
            or np.any(abs(centres-(declared[:, ::2]+declared[:, 1::2])/2) > GEOMETRY_RTOL*lengths)):
        raise ValueError("mesh: actual TensorMesh centres are not faithful interior points")
    volumes = np.prod(actual[:, 1::2]-actual[:, ::2], axis=1)
    declared_volumes = np.prod(lengths, axis=1)
    if (tensor.cell_volumes.shape != volumes.shape or not np.isfinite(volumes).all()
            or np.any(volumes <= 0) or not np.isfinite(tensor.cell_volumes).all()
            or np.any(abs(volumes-declared_volumes) > GEOMETRY_RTOL*declared_volumes)
            or np.any(abs(volumes-tensor.cell_volumes) > GEOMETRY_RTOL*declared_volumes)):
        raise ValueError("mesh: actual TensorMesh physical volumes disagree")
    return actual, centres, volumes


def forward_magnetic(request: dict) -> dict:
    """Evaluate actual scalar induced SimPEG/Geoana components and linear-TMI Jacobian.

    Exact ABI: docs/design/features/m04-induced-prism/contracts.md.
    The caller must keep inputs private during snapshot. No field inference,
    remanence inversion, correction, disk cache or application execution occurs.
    """
    _keys(request, ("schema", "engine", "frame", "mesh", "receivers_m",
                    "susceptibility_si", "inducing_field"), "request")
    _enum(request["schema"], "magnetic-prism-forward-request-1", "schema")
    _enum(request["engine"], ENGINE, "engine")
    frame = request["frame"]
    _keys(frame, FRAME, "frame")
    for key in ("kind", "length_unit", "vertical_positive"):
        _enum(frame[key], FRAME[key], f"frame.{key}")
    if type(frame["axes"]) is not tuple or any(type(axis) is not str for axis in frame["axes"]):
        raise TypeError("frame.axes: expected native tuple of strings")
    if frame["axes"] != FRAME["axes"]:
        raise ValueError("frame.axes: unsupported axis order")
    spec = request["mesh"]
    _keys(spec, ("origin_m", "hx_m", "hy_m", "hz_m", "active"), "mesh")
    field = request["inducing_field"]
    _keys(field, ("amplitude_nt", "inclination_deg", "declination_deg"), "inducing_field")
    for key, lo, hi, closed in (("amplitude_nt", 1., 1e6, True),
                               ("inclination_deg", -90., 90., True),
                               ("declination_deg", -180., 180., False)):
        value = field[key]
        if type(value) is not float:
            raise TypeError(f"inducing_field.{key}: expected built-in finite float")
        if not np.isfinite(value) or value < lo or (value > hi if closed else value >= hi):
            raise ValueError(f"inducing_field.{key}: outside declared range")
    # Phase 1: ALL array metadata/count caps before any array scans or snapshots.
    raw_origin = spec["origin_m"]
    raw_widths = [spec[key] for key in ("hx_m", "hy_m", "hz_m")]
    raw_active = spec["active"]
    raw_chi = request["susceptibility_si"]
    raw_receivers = request["receivers_m"]
    _metadata(raw_origin, 1, "mesh.origin_m")
    if raw_origin.shape != (3,):
        raise ValueError("mesh.origin_m: expected shape (3,)")
    for key, w in zip(("hx_m", "hy_m", "hz_m"), raw_widths):
        _metadata(w, 1, f"mesh.{key}")
        if not 1 <= len(w) <= 64:
            raise ValueError(f"mesh.{key}: axis length outside 1..64")
    shape = tuple(len(w) for w in raw_widths)
    n_full = shape[0]*shape[1]*shape[2]
    if n_full > MAX_FULL_CELLS:
        raise ValueError("mesh: full cell count exceeds 65536")
    _metadata(raw_active, 1, "mesh.active", np.bool_)
    if raw_active.shape != (n_full,):
        raise ValueError("mesh.active: expected full-cell mask")
    _metadata(raw_chi, 1, "susceptibility_si")
    n_active = len(raw_chi)
    if not 1 <= n_active <= min(n_full, MAX_ACTIVE_CELLS):
        raise ValueError("susceptibility_si: active length outside declared cap")
    _metadata(raw_receivers, 2, "receivers_m")
    if raw_receivers.shape[1] != 3 or not 1 <= len(raw_receivers) <= MAX_RECEIVERS:
        raise ValueError("receivers_m: expected shape (1..2048,3)")
    if len(raw_receivers)*n_active > MAX_PROJECTED_ENTRIES:
        raise ValueError("mesh/receivers: 3-component sensitivity matrix exceeds declared cap")
    if int(np.count_nonzero(raw_active)) != n_active:
        raise ValueError("mesh.active/susceptibility_si: nonempty active population mismatch")
    # Phase 2: bounded finite scans and independent snapshots.
    origin = _snapshot(raw_origin, "mesh.origin_m")
    widths = [_snapshot(w, f"mesh.{key}") for w, key in zip(raw_widths, ("hx_m", "hy_m", "hz_m"))]
    active = _snapshot(raw_active, "mesh.active")
    chi = _snapshot(raw_chi, "susceptibility_si")
    receivers = _snapshot(raw_receivers, "receivers_m")
    if np.any(abs(origin) > 1e7):
        raise ValueError("mesh.origin_m: outside coordinate bounds")
    if any(np.any((w < 1e-3) | (w > 1e5)) or float(np.sum(w)) > 1e5 for w in widths):
        raise ValueError("mesh: widths/span outside declared bounds")
    if np.any(abs(receivers) > 1e7):
        raise ValueError("receivers_m: outside coordinate bounds")
    if np.any((chi < 0) | (chi > .1)):
        raise ValueError("susceptibility_si: outside 0..0.1")
    edges = [o+np.r_[0., np.cumsum(w)] for o, w in zip(origin, widths)]
    for edge, w in zip(edges, widths):
        if (not np.isfinite(edge).all() or np.any(abs(edge) > 1e7)
                or np.any(np.diff(edge) <= 0)
                or np.any(abs(np.diff(edge)-w) > GEOMETRY_RTOL*w)):
            raise ValueError("mesh: collapsed, out-of-bounds or unfaithful edges")
        centre = edge[:-1]+np.diff(edge)/2
        if not np.all((centre > edge[:-1]) & (centre < edge[1:])):
            raise ValueError("mesh: no representable interior cell centres")
    _outside(receivers, np.array([e[0] for e in edges]), np.array([e[-1] for e in edges]))
    _runtime()
    full_indices = np.arange(n_full)
    ijk = np.unravel_index(full_indices, shape, order="F")
    declared = np.column_stack([e[i+side] for e, i in zip(edges, ijk) for side in (0, 1)])
    indices = np.flatnonzero(active)
    try:
        tensor = discretize.TensorMesh(widths, origin=origin)
        full_bounds, full_centres, full_volumes = _tensor_state(tensor, edges, widths, declared)
        _outside(receivers, np.array([e[0] for e in (tensor.nodes_x, tensor.nodes_y, tensor.nodes_z)]),
                 np.array([e[-1] for e in (tensor.nodes_x, tensor.nodes_y, tensor.nodes_z)]))
    except (MemoryError, ValueError):
        raise
    except Exception as exc:
        raise RuntimeError("engine: TensorMesh geometry construction failed") from exc
    inc, dec = np.deg2rad([field["inclination_deg"], field["declination_deg"]])
    f = np.array([np.cos(inc)*np.sin(dec), np.cos(inc)*np.cos(dec), -np.sin(inc)])
    amplitude = field["amplitude_nt"]
    background = amplitude*f
    try:
        rx = magnetics.receivers.Point(receivers, components=["bx", "by", "bz"])
        source = magnetics.sources.UniformBackgroundField(
            receiver_list=[rx], amplitude=amplitude,
            inclination=field["inclination_deg"], declination=field["declination_deg"])
        if not np.allclose(source.b0, background, rtol=0, atol=8*np.finfo(np.float64).eps*amplitude):
            raise RuntimeError("engine: actual inducing-field convention differs")
        survey = magnetics.Survey(source)
        simulation = magnetics.simulation.Simulation3DIntegral(
            tensor, survey=survey, active_cells=active, chiMap=maps.IdentityMap(nP=n_active),
            model_type="scalar", engine="geoana", store_sensitivities="ram",
            sensitivity_dtype=np.float64, n_processes=1)
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            kernel = simulation.G
            if (type(kernel) is not np.ndarray or kernel.dtype != np.float64
                    or kernel.shape != (3*len(receivers), n_active) or not np.isfinite(kernel).all()):
                raise RuntimeError("engine: malformed component sensitivity matrix")
            predicted = simulation.dpred(chi)
            if (type(predicted) is not np.ndarray or predicted.dtype != np.float64
                    or predicted.shape != (3*len(receivers),) or not np.isfinite(predicted).all()):
                raise RuntimeError("engine: malformed predicted components")
            if not np.allclose(predicted, kernel@chi, rtol=1e-12, atol=1e-10):
                raise RuntimeError("engine: native dpred/Gchi state identity mismatch")
            components = predicted.reshape(len(receivers), 3)
            jacobian = np.einsum("naj,a->nj", kernel.reshape(len(receivers), 3, n_active), f)
            linear = components@f
            exact = _exact_magnitude(background, components, amplitude)
            ratio = np.linalg.norm(components, axis=1)/amplitude
            difference = exact-linear
            if not all(np.isfinite(a).all() for a in (jacobian, linear, exact, ratio, difference)):
                raise RuntimeError("engine: nonfinite derived result")
    except MemoryError:
        raise
    except Exception as exc:
        raise RuntimeError("engine: ordinary induced magnetic evaluation failed") from exc
    return {
        "schema": "magnetic-prism-forward-result-1", "engine": ENGINE, "source_epoch": SOURCE_EPOCH,
        "inducing_field": {**field, "direction_enu": _owned(f), "background_enu_nt": _owned(background)},
        "geometry": {"receivers_m": _owned(receivers), "active_indices": _owned(indices, np.int64),
                     "active_bounds_m": _owned(full_bounds[indices]),
                     "active_centres_m": _owned(full_centres[indices]),
                     "active_volumes_m3": _owned(full_volumes[indices]), "cell_order": "x-fast"},
        "field_components_nt": _owned(components), "linear_tmi_nt": _owned(linear),
        "linear_jacobian_nt_per_si": _owned(jacobian), "exact_magnitude_anomaly_nt": _owned(exact),
        "linearization": {"secondary_to_background_ratio": _owned(ratio), "exact_minus_linear_nt": _owned(difference),
                          "maximum_abs_difference_nt": float(np.max(abs(difference))),
                          "interpretation": "uniform-induced-no-self-demagnetization",
                          "field_source_verified": False, "full_method_accepted": False, "host_approved": False}}
