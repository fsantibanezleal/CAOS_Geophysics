"""Ordinary, bounded in-memory gravity forward operator; not survey admission.

Errors/cause chains are private caller diagnostics, not safe HTTP responses.
Installed source-byte verification belongs to the trusted external harness.
"""

import sys

import discretize
import geoana
import numpy as np
import scipy
import simpeg
from simpeg import maps
from simpeg.potential_fields import gravity


ENGINE = "simpeg-0.25.2-geoana-0.8.1-f64-ram"
SOURCE_EPOCH = "m02-prism-cpu-1"
VERSIONS = {"simpeg": "0.25.2", "geoana": "0.8.1", "discretize": "0.12.0",
            "numpy": "2.2.6", "scipy": "1.15.2"}
FRAME = {"kind": "local_cartesian", "axes": ("east", "north", "up"),
         "length_unit": "m", "vertical_positive": "up"}
GEOMETRY_RTOL = 1e-10  # Local metadata fidelity, not a prediction tolerance.
CORNER_COLUMNS = np.array([[0, 2, 4], [1, 2, 4], [0, 3, 4], [1, 3, 4],
                           [0, 2, 5], [1, 2, 5], [0, 3, 5], [1, 3, 5]])


def _keys(value, keys, field):
    if type(value) is not dict:
        raise TypeError(f"{field}: expected built-in dict")
    if any(type(k) is not str for k in value) or set(value) != set(keys):
        raise ValueError(f"{field}: exact declared keys required")


def _enum(value, expected, field):
    if type(value) is not str:
        raise TypeError(f"{field}: expected str")
    if value != expected:
        raise ValueError(f"{field}: unsupported value")


def _array_metadata(value, ndim, field, dtype=np.float64):
    if type(value) is not np.ndarray or value.dtype != np.dtype(dtype):
        raise TypeError(f"{field}: expected native {np.dtype(dtype)} ndarray")
    if value.ndim != ndim:
        raise ValueError(f"{field}: wrong dimensionality")


def _snapshot(value, field):
    if not np.isfinite(value).all():
        raise ValueError(f"{field}: nonfinite values")
    return np.array(value, copy=True, order="C")


def _readonly(value, dtype=None):
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.flags.writeable = False
    return result


def _tensor_geometry(tensor, edges, bounds, widths):
    """Verify actual engine geometry, never infer prism corners from centres."""
    actual_edges = (tensor.nodes_x, tensor.nodes_y, tensor.nodes_z)
    for actual, declared, h in zip(actual_edges, edges, widths):
        scale = np.r_[h[0], np.minimum(h[:-1], h[1:]), h[-1]]
        if (actual.shape != declared.shape or not np.isfinite(actual).all()
                or np.any(np.diff(actual) <= 0)
                or np.any(np.abs(actual - declared) > GEOMETRY_RTOL * scale)
                or np.any(np.abs(np.diff(actual) - h) > GEOMETRY_RTOL * h)):
            raise ValueError("mesh: actual TensorMesh nodes/widths exceed local geometry fidelity")
    actual_bounds = tensor.cell_bounds
    shape = tuple(len(h) for h in widths)
    ijk = np.unravel_index(np.arange(len(bounds)), shape, order="F")
    cell_widths = np.column_stack([h[j] for h, j in zip(widths, ijk)])
    if (actual_bounds.shape != bounds.shape or not np.isfinite(actual_bounds).all()
            or np.any(np.abs(actual_bounds - bounds) > GEOMETRY_RTOL * np.repeat(cell_widths, 2, axis=1))):
        raise ValueError("mesh: actual TensorMesh bounds exceed local geometry fidelity")
    corners = tensor.nodes[tensor.cell_nodes]
    if (corners.shape != (len(bounds), 8, 3)
            or not np.array_equal(corners, actual_bounds[:, CORNER_COLUMNS])):
        raise ValueError("mesh: actual TensorMesh ordered corners disagree with actual bounds")
    centres = tensor.cell_centers
    if (centres.shape != (len(bounds), 3) or centres.dtype != np.float64
            or not np.isfinite(centres).all()
            or not np.all((centres > actual_bounds[:, ::2]) & (centres < actual_bounds[:, 1::2]))):
        raise ValueError("mesh: actual TensorMesh centres are not representable strictly inside cells")
    volumes = np.prod(actual_bounds[:, 1::2] - actual_bounds[:, ::2], axis=1)
    declared_volumes = tensor.cell_volumes
    if (declared_volumes.shape != volumes.shape or not np.isfinite(declared_volumes).all()
            or np.any(declared_volumes <= 0) or not np.isfinite(volumes).all() or np.any(volumes <= 0)
            or np.any(np.abs(volumes - declared_volumes) > GEOMETRY_RTOL * declared_volumes)):
        raise ValueError("mesh: node-derived volumes disagree with TensorMesh physical volumes")
    return centres, actual_bounds, volumes


def _runtime():
    modules = {"simpeg": simpeg, "geoana": geoana, "discretize": discretize,
               "numpy": np, "scipy": scipy}
    observed = {name: module.__version__ for name, module in modules.items()}
    if any(type(v) is not str for v in observed.values()) or observed != VERSIONS:
        raise RuntimeError("runtime: required loaded package versions differ")
    if (sys.version_info[:3] != (3, 12, 10) or sys.platform != "win32"
            or sys.implementation.name != "cpython" or sys.maxsize != 2**63 - 1):
        raise RuntimeError("runtime: unreviewed Python/platform source epoch")
    return observed


def forward_gravity(request: dict) -> dict:
    """Return upward mGal and physical-density Jacobian, without application I/O.

    Exact protocol: docs/design/features/m02-prism-operator/design.md.
    Inputs must be private to the caller during the snapshot. Output arrays own
    their memory, are read-only, and retain original receiver/active ordering.
    """
    _keys(request, ("schema", "frame", "mesh", "receivers_m", "density_kg_m3", "engine"), "request")
    _enum(request["schema"], "gravity-prism-forward-request-1", "schema")
    _enum(request["engine"], ENGINE, "engine")
    frame = request["frame"]
    _keys(frame, FRAME, "frame")
    for key in ("kind", "length_unit", "vertical_positive"):
        _enum(frame[key], FRAME[key], f"frame.{key}")
    if type(frame["axes"]) is not tuple or any(type(v) is not str for v in frame["axes"]):
        raise TypeError("frame.axes: expected tuple of strings")
    if frame["axes"] != FRAME["axes"]:
        raise ValueError("frame.axes: unsupported axis order")
    mesh_spec = request["mesh"]
    _keys(mesh_spec, ("origin_m", "hx_m", "hy_m", "hz_m", "active"), "mesh")
    # Phase 1: metadata only for EVERY supplied array before any scan or copy.
    raw_origin = mesh_spec["origin_m"]
    raw_widths = [mesh_spec[key] for key in ("hx_m", "hy_m", "hz_m")]
    raw_active = mesh_spec["active"]
    raw_density = request["density_kg_m3"]
    raw_receivers = request["receivers_m"]
    _array_metadata(raw_origin, 1, "mesh.origin_m")
    if raw_origin.shape != (3,):
        raise ValueError("mesh.origin_m: expected shape (3,)")
    for key, value in zip(("hx_m", "hy_m", "hz_m"), raw_widths):
        _array_metadata(value, 1, f"mesh.{key}")
        if not 1 <= len(value) <= 4096:
            raise ValueError(f"mesh.{key}: axis length outside 1..4096")
    shape = tuple(len(w) for w in raw_widths)
    n_cells = shape[0] * shape[1] * shape[2]
    if not 1 <= n_cells <= 4096:
        raise ValueError("mesh: 1..4096 full cells required")
    _array_metadata(raw_active, 1, "mesh.active", np.bool_)
    if raw_active.shape != (n_cells,):
        raise ValueError("mesh.active: expected full-cell mask")
    _array_metadata(raw_density, 1, "density_kg_m3")
    if not 1 <= len(raw_density) <= n_cells:
        raise ValueError("density_kg_m3: length outside declared cell cap")
    _array_metadata(raw_receivers, 2, "receivers_m")
    if raw_receivers.shape[1] != 3 or not 1 <= len(raw_receivers) <= 2048:
        raise ValueError("receivers_m: expected shape (1..2048,3)")
    # Active population requires a bounded value traversal, only AFTER all
    # metadata/cap checks. Check its density alignment before float scans/copies.
    active_count = int(np.count_nonzero(raw_active))
    if active_count == 0:
        raise ValueError("mesh.active: expected full-cell mask with at least one active cell")
    if raw_density.shape != (active_count,):
        raise ValueError("density_kg_m3: expected active-cell vector")
    # Phase 2: bounded finite-value checks and private snapshots.
    origin = _snapshot(raw_origin, "mesh.origin_m")
    widths = [_snapshot(value, f"mesh.{key}")
              for key, value in zip(("hx_m", "hy_m", "hz_m"), raw_widths)]
    if any(np.any(w <= 0) for w in widths):
        raise ValueError("mesh: positive widths required")
    active = _snapshot(raw_active, "mesh.active")
    indices = np.flatnonzero(active)
    density = _snapshot(raw_density, "density_kg_m3")
    receivers = _snapshot(raw_receivers, "receivers_m")
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        edges = [o + np.r_[0.0, np.cumsum(w)] for o, w in zip(origin, widths)]
    if any(not np.isfinite(e).all() or np.any(np.diff(e) <= 0) for e in edges):
        raise ValueError("mesh: nonfinite or collapsed edges")
    # A finite increasing edge pair can still have no representable interior
    # midpoint (e.g. origin 1e16, width 2). Check ALL cells, including inactive.
    with np.errstate(over="ignore", invalid="ignore"):
        midpoints = [e[:-1] + (e[1:] - e[:-1]) / 2 for e in edges]
    if any(not np.all((m > e[:-1]) & (m < e[1:])) for m, e in zip(midpoints, edges)):
        raise ValueError("mesh: cell centres are not representable strictly inside cells")
    lower = np.array([e[0] for e in edges])
    upper = np.array([e[-1] for e in edges])
    outside = np.any((receivers < lower) | (receivers > upper), axis=1)
    if not np.all(outside):
        raise ValueError("receivers_m: every receiver must be strictly outside closed full source box")
    ijk = np.unravel_index(indices, shape, order="F")
    bounds = np.column_stack([e[j + side] for e, j in zip(edges, ijk) for side in (0, 1)])
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        lengths = bounds[:, 1::2] - bounds[:, ::2]
        centres = bounds[:, ::2] + lengths / 2
        volumes = np.prod(lengths, axis=1)
        # Check inactive volumes too: a mask cannot exempt invalid tensor geometry.
        full_volumes = np.einsum("i,j,k->ijk", *widths)
    if (not np.isfinite(bounds).all() or not np.isfinite(centres).all()
            or not np.isfinite(volumes).all() or np.any(volumes <= 0)
            or not np.isfinite(full_volumes).all() or np.any(full_volumes <= 0)):
        raise ValueError("mesh: nonfinite or nonpositive physical geometry/volume")
    observed = _runtime()
    # Fixed count caps bound G at 64 MiB; this is not a measured total-RSS limit.
    if len(receivers) * len(indices) * 8 > 64 * 1024**2:
        raise ValueError("mesh/receivers: projected G exceeds declared cap")
    try:
        tensor = discretize.TensorMesh(widths, origin=origin)
    except MemoryError:
        raise
    except Exception as exc:
        raise RuntimeError("engine: tensor geometry construction failed") from exc
    full_ijk = np.unravel_index(np.arange(n_cells), shape, order="F")
    full_bounds = np.column_stack([e[j + side] for e, j in zip(edges, full_ijk) for side in (0, 1)])
    # Return the genuine TensorMesh centres after strict interior validation,
    # not a different rounded midpoint pretending to be the engine centre.
    with np.errstate(over="ignore", invalid="ignore"):
        full_centres, actual_bounds, actual_volumes = _tensor_geometry(tensor, edges, full_bounds, widths)
    centres, bounds, volumes = full_centres[indices], actual_bounds[indices], actual_volumes[indices]
    actual_lower = np.array([e[0] for e in (tensor.nodes_x, tensor.nodes_y, tensor.nodes_z)])
    actual_upper = np.array([e[-1] for e in (tensor.nodes_x, tensor.nodes_y, tensor.nodes_z)])
    if not np.all(np.any((receivers < actual_lower) | (receivers > actual_upper), axis=1)):
        raise ValueError("receivers_m: must be strictly outside actual closed TensorMesh source box")
    try:
        rx = gravity.receivers.Point(receivers, components="gz")
        survey = gravity.survey.Survey(gravity.sources.SourceField(receiver_list=[rx]))
        simulation = gravity.simulation.Simulation3DIntegral(
            tensor, survey=survey, active_cells=active, rhoMap=maps.IdentityMap(nP=len(indices)),
            engine="geoana", store_sensitivities="ram", sensitivity_dtype=np.float64, n_processes=1,
        )
        prism_corners = simulation._nodes[simulation._unique_inv.T]
        if (prism_corners.shape != (len(indices), 8, 3)
                or not np.array_equal(prism_corners, bounds[:, CORNER_COLUMNS])):
            raise RuntimeError("engine: actual Geoana prism nodes differ from declared active bounds")
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            prediction = simulation.fields(density / 1000.0)
            kernel = simulation.G
            if (type(prediction) is not np.ndarray or prediction.dtype != np.float64
                    or prediction.shape != (len(receivers),) or not np.isfinite(prediction).all()
                    or type(kernel) is not np.ndarray or kernel.dtype != np.float64
                    or kernel.shape != (len(receivers), len(indices)) or not np.isfinite(kernel).all()):
                raise RuntimeError("engine: nonfinite, wrong shape or non-float64 state")
            jacobian = kernel / 1000.0
            if not np.allclose(prediction, jacobian @ density, rtol=1e-10, atol=1e-12):
                raise RuntimeError("engine: prediction/Jacobian state identity mismatch")
    except MemoryError:
        raise
    except Exception as exc:
        raise RuntimeError("engine: ordinary gravity forward evaluation failed") from exc
    return {
        "schema": "gravity-prism-forward-result-1", "frame": dict(FRAME),
        "gz_up_mgal": _readonly(prediction), "jacobian_mgal_per_kg_m3": _readonly(jacobian),
        "geometry": {
            "shape_xyz": shape, "flattening": "x-fast",
            "active_cell_indices": _readonly(indices, np.int64), "active_cell_bounds_m": _readonly(bounds),
            "active_cell_centres_m": _readonly(centres), "active_cell_volumes_m3": _readonly(volumes),
            "receivers_m": _readonly(receivers), "density_kg_m3": _readonly(density),
        },
        "provenance": {
            "engine": ENGINE, "required_source_epoch": SOURCE_EPOCH, "runtime_versions": observed,
            "python_version": ".".join(map(str, sys.version_info[:3])), "precision": "float64",
            "sensitivity_storage": "ram", "n_processes": 1,
            "source_verification": "external_required_not_performed_by_operator",
        },
    }
