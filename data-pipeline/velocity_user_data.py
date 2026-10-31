"""Local error-weighted straight-ray tools; no training, provider or server I/O."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import zipfile

SCHEMA = "geophysics.velocity-user-data/v1"
ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
MAX_INPUT = 512 * 1024
MAX_RESULT = 4 * 1024 * 1024


class VelocityInputError(ValueError):
    """Only fixed error text is exposed by the local command."""


def _fail():
    raise VelocityInputError("Invalid or unsupported first-arrival input")


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _decode(raw, cap):
    if type(raw) is not bytes or not 0 < len(raw) <= cap:
        _fail()
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        _fail()
    depth = nodes = 0
    quoted = escaped = atom = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
            atom = False
            nodes += 1
        elif char in "[{":
            depth += 1
            nodes += 1
            atom = False
        elif char in "]}":
            depth -= 1
            atom = False
        elif char in ",: \t\r\n":
            atom = False
        elif not atom:
            nodes += 1
            atom = True
        if not 0 <= depth <= 12 or nodes > (40000 if cap <= MAX_INPUT else 160000):
            _fail()
    if quoted or depth:
        _fail()
    try:
        return json.loads(text, object_pairs_hook=_pairs,
                          parse_constant=lambda _: _fail())
    except (ValueError, RecursionError, OverflowError):
        _fail()


def _keys(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        _fail()


def _number(value, lower, upper, *, closed=True):
    if (type(value) not in (int, float)
            or not (lower <= value <= upper if closed else lower < value <= upper)
            or not math.isfinite(value)):
        _fail()


def validate_request(raw):
    """No NumPy/SciPy/Torch import occurs until the complete contract passes."""
    doc = _decode(raw, MAX_INPUT)
    _keys(doc, ("schema", "id", "source", "frame", "units", "ray_ids",
                "rays_m", "times_s", "sigma_s", "lambda"))
    if doc["schema"] != SCHEMA or type(doc["id"]) is not str or not ID.fullmatch(doc["id"]):
        _fail()
    _keys(doc["source"], ("citation", "rights", "scope"))
    source = doc["source"]
    if (type(source["citation"]) is not str or not source["citation"].strip()
            or len(source["citation"]) > 2048
            or source["rights"] not in ("owner-permitted", "CC0", "CC-BY")
            or source["scope"] not in ("owner-provided", "synthetic-control")):
        _fail()
    if (doc["frame"] != "local-x-z-down"
            or doc["units"] != {"distance": "m", "time": "s", "velocity": "m/s"}):
        _fail()
    for name in ("ray_ids", "rays_m", "times_s", "sigma_s"):
        if type(doc[name]) is not list:
            _fail()
    n = len(doc["ray_ids"])
    if not 8 <= n <= 2048 or any(len(doc[name]) != n for name in ("rays_m", "times_s", "sigma_s")):
        _fail()
    identifiers = doc["ray_ids"]
    if any(type(x) is not str or not ID.fullmatch(x) for x in identifiers) or len(set(identifiers)) != n:
        _fail()
    for ray, time_s, sigma_s in zip(doc["rays_m"], doc["times_s"], doc["sigma_s"]):
        if type(ray) is not list or len(ray) != 4:
            _fail()
        for coordinate in ray:
            _number(coordinate, 0, 800)
        if math.hypot(ray[2] - ray[0], ray[3] - ray[1]) < 0.001:
            _fail()
        _number(time_s, 0, 100, closed=False)
        _number(sigma_s, 0, 10, closed=False)
    _number(doc["lambda"], 1e-6, 1e6)
    return doc


def _checkpoint(path, expected_sha256, protocol):
    if protocol == "physics-v2":
        from velocity_physics_refinement import load_checkpoint
    else:
        from velocity_validation import load_checkpoint

    if type(expected_sha256) is not str or not SHA.fullmatch(expected_sha256):
        _fail()
    raw = read_regular(path, 1024 * 1024)
    if _hash(raw) != expected_sha256:
        raise VelocityInputError("Checkpoint identity mismatch")
    # A caller's matching hash alone must not permit unbounded NPZ expansion.
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if (not 0 < len(members) <= 64 or sum(x.file_size for x in members) > 1024 * 1024
                or any(x.flag_bits & 1 or x.is_dir() or "/" in x.filename
                       or "\\" in x.filename or not x.filename.endswith(".npy") for x in members)
                or len({x.filename for x in members}) != len(members)):
            _fail()
    return load_checkpoint(Path(path), expected_sha256, "cpu")


def calculate(raw, *, checkpoint=None, checkpoint_sha256=None, checkpoint_protocol="original"):
    doc = validate_request(raw)
    if ((checkpoint is None) != (checkpoint_sha256 is None)
            or checkpoint_protocol not in ("original", "physics-v2")):
        _fail()
    import numpy as np
    import scipy
    from scipy.linalg import cho_factor, cho_solve
    from velocity_validation import (
        GRID, DX, _difference_gram, acquisition, background, cell_length_matrix,
        input_features, quadrature_matrix,
    )

    rays = np.asarray(doc["rays_m"], dtype=np.float64)
    observed = np.asarray(doc["times_s"], dtype=np.float64)
    sigma = np.asarray(doc["sigma_s"], dtype=np.float64)
    a = cell_length_matrix(rays)
    q_operator = quadrature_matrix(rays)
    reference = background().ravel()
    s0 = reference ** -1
    b = a / (1000 * sigma[:, None])
    y = (observed - a @ s0) / sigma
    gram = _difference_gram()
    normal = b.T @ b + doc["lambda"] * gram + 0.01 * np.eye(GRID * GRID)
    q = cho_solve(cho_factor(normal), b.T @ y)
    slowness = s0 + q / 1000
    clipped = np.clip(slowness, 1 / 4000, 1 / 1400)
    models = {"classical": 1 / clipped}
    warnings = ["Straight-ray approximation; no bent-ray or field accuracy established"]
    learned_domain = None
    if checkpoint is not None:
        import torch
        model = _checkpoint(checkpoint, checkpoint_sha256, checkpoint_protocol)
        if checkpoint_protocol == "physics-v2":
            from velocity_physics_refinement import input_features
        with torch.no_grad():
            models["learned"] = model(torch.from_numpy(input_features(observed, a))[None])[0].numpy().ravel().astype(np.float64)
        same_geometry = any(rays.shape == acquisition(layout).shape
                            and np.array_equal(rays, acquisition(layout)) for layout in ("A", "B"))
        same_noise = bool(np.all(sigma == 0.001))
        learned_domain = {"training_geometry": same_geometry, "training_noise": same_noise,
                          "field_validated": False, "heldout_advantage": False}
        warnings.append("Frozen CNN failed the matched family/acquisition-disjoint comparator")
        if checkpoint_protocol == "original":
            warnings.append("CNN perturbations are restricted to +/-600 m/s around the fixed reference")
        else:
            warnings.append("Geometry-normalized CNN predicts only within 1400..4000 m/s; no field calibration")
        if not same_geometry or not same_noise:
            warnings.append("Supplied geometry or uncertainty lies outside the trained acquisition/noise domain")
    outputs = {}
    for name, velocity in models.items():
        predictions = a @ (1 / velocity)
        residual = observed - predictions
        alternate = q_operator @ (1 / velocity)
        outputs[name] = {
            "velocity_m_s": velocity.reshape(GRID, GRID).tolist(),
            "predicted_s": predictions.tolist(), "residual_s": residual.tolist(),
            "normalized_residual": (residual / sigma).tolist(),
            "bilinear_predicted_s": alternate.tolist(),
            "cell_vs_bilinear_rmse_s": float(np.sqrt(np.mean((predictions - alternate) ** 2))),
            "data_chi_square": float(np.sum((residual / sigma) ** 2)),
            "data_wrms": float(np.sqrt(np.mean((residual / sigma) ** 2))),
        }
    bounded_q = 1000 * (clipped - s0)
    outputs["classical"].update({
        "clipped_cells": int(np.count_nonzero(slowness != clipped)),
        "regularizer": float(doc["lambda"] * bounded_q @ gram @ bounded_q + 0.01 * bounded_q @ bounded_q),
        "solver": "Cholesky unconstrained normal equation followed by explicit slowness clipping",
        "bound_constrained_optimum_certified": False,
    })
    return {
        "schema": "geophysics.velocity-result/v1", "status": "computed", "request": doc,
        "source": {"sha256": _hash(raw), "bytes": len(raw)},
        "axes": {"x_m": ((np.arange(GRID) + 0.5) * DX).tolist(),
                 "depth_m": ((np.arange(GRID) + 0.5) * DX).tolist(), "order": ["depth", "distance"]},
        "coverage_m": a.sum(axis=0).reshape(GRID, GRID).tolist(),
        "results": outputs, "learned_domain": learned_domain, "warnings": warnings,
        "engine": {"numpy": np.__version__, "scipy": scipy.__version__,
                   "user_tool_sha256": _hash(Path(__file__).read_bytes()),
                   "velocity_operator_sha256": _hash((Path(__file__).parent / "velocity_validation.py").read_bytes()),
                   "checkpoint_sha256": checkpoint_sha256,
                   "checkpoint_protocol": checkpoint_protocol if checkpoint is not None else None,
                   "refinement_code_sha256": _hash((Path(__file__).parent / "velocity_physics_refinement.py").read_bytes())
                   if checkpoint is not None and checkpoint_protocol == "physics-v2" else None},
        "claims": {"field_truth_known": False, "field_validated": False,
                   "heldout_advantage": False, "online_admitted": False},
    }


def read_regular(path, cap):
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts or any(x.is_symlink() for x in (path, *path.parents)):
        _fail()
    if not path.is_file() or not 0 < path.stat().st_size <= cap:
        _fail()
    with path.open("rb") as handle:
        raw = handle.read(cap + 1)
    if not 0 < len(raw) <= cap:
        _fail()
    return raw


def verify_generation(output):
    output = Path(output)
    if set(x.name for x in output.iterdir()) != {"result.json", "manifest.json"}:
        _fail()
    manifest = _decode(read_regular(output / "manifest.json", 4096), 4096)
    raw = read_regular(output / "result.json", MAX_RESULT)
    return _verify_result(raw, manifest)


def _verify_result(raw, manifest):
    _keys(manifest, ("schema", "result_sha256", "result_bytes", "source", "engine"))
    if (manifest["schema"] != "geophysics.velocity-bundle/v1"
            or type(manifest["result_bytes"]) is not int or len(raw) != manifest["result_bytes"]
            or _hash(raw) != manifest["result_sha256"]):
        _fail()
    result = _decode(raw, MAX_RESULT)
    _keys(result, ("schema", "status", "request", "source", "axes", "coverage_m",
                   "results", "learned_domain", "warnings", "engine", "claims"))
    if (result["schema"] != "geophysics.velocity-result/v1" or result["status"] != "computed"
            or result["source"] != manifest["source"] or result["engine"] != manifest["engine"]
            or result["claims"] != {"field_truth_known": False, "field_validated": False,
                                   "heldout_advantage": False, "online_admitted": False}):
        _fail()
    request = validate_request(_canonical(result["request"]))
    import numpy as np
    from velocity_validation import GRID, DX, background, _difference_gram, cell_length_matrix, quadrature_matrix

    n = len(request["ray_ids"])
    if result["axes"] != {"x_m": ((np.arange(GRID) + 0.5) * DX).tolist(),
                           "depth_m": ((np.arange(GRID) + 0.5) * DX).tolist(), "order": ["depth", "distance"]}:
        _fail()
    a = cell_length_matrix(np.asarray(request["rays_m"]))
    alt = quadrature_matrix(np.asarray(request["rays_m"]))
    if not np.array_equal(np.asarray(result["coverage_m"]), a.sum(axis=0).reshape(GRID, GRID)):
        _fail()
    if set(result["results"]) not in ({"classical"}, {"classical", "learned"}):
        _fail()
    for name, record in result["results"].items():
        keys = ("velocity_m_s", "predicted_s", "residual_s", "normalized_residual",
                "bilinear_predicted_s", "cell_vs_bilinear_rmse_s", "data_chi_square", "data_wrms")
        if name == "classical":
            keys += ("clipped_cells", "regularizer", "solver", "bound_constrained_optimum_certified")
        _keys(record, keys)
        velocity = np.asarray(record["velocity_m_s"], dtype=np.float64)
        if velocity.shape != (GRID, GRID) or not np.isfinite(velocity).all() or np.any(velocity <= 0):
            _fail()
        for key in ("predicted_s", "residual_s", "normalized_residual", "bilinear_predicted_s"):
            arr = np.asarray(record[key], dtype=np.float64)
            if arr.shape != (n,) or not np.isfinite(arr).all():
                _fail()
        predicted = a @ (1 / velocity.ravel())
        residual = np.asarray(request["times_s"]) - predicted
        for key, value in (("predicted_s", predicted), ("residual_s", residual),
                           ("normalized_residual", residual / request["sigma_s"]),
                           ("bilinear_predicted_s", alt @ (1 / velocity.ravel()))):
            if not np.allclose(record[key], value, rtol=1e-12, atol=1e-12):
                _fail()
        wrms = float(np.sqrt(np.mean((residual / request["sigma_s"]) ** 2)))
        if not math.isclose(record["data_wrms"], wrms, rel_tol=1e-12, abs_tol=1e-12):
            _fail()
        chi_square = float(np.sum((residual / request["sigma_s"]) ** 2))
        discretization = float(np.sqrt(np.mean((predicted - alt @ (1 / velocity.ravel())) ** 2)))
        for key, expected in (("data_chi_square", chi_square), ("cell_vs_bilinear_rmse_s", discretization)):
            if type(record[key]) not in (int, float) or not math.isclose(record[key], expected, rel_tol=1e-12, abs_tol=1e-12):
                _fail()
        if name == "classical" and np.any((velocity < 1400) | (velocity > 4000)):
            _fail()
        if name == "classical":
            bounded_q = 1000 * (1 / velocity.ravel() - 1 / background().ravel())
            reg = float(request["lambda"] * bounded_q @ _difference_gram() @ bounded_q + 0.01 * bounded_q @ bounded_q)
            if (not math.isclose(record["regularizer"], reg, rel_tol=1e-9, abs_tol=1e-12)
                    or type(record["clipped_cells"]) is not int or not 0 <= record["clipped_cells"] <= GRID * GRID
                    or record["bound_constrained_optimum_certified"] is not False):
                _fail()
    return result


def export_generation(result, output):
    raw = _canonical(result)
    if len(raw) > MAX_RESULT:
        _fail()
    output = Path(output)
    if not output.is_absolute() or ".." in output.parts or any(x.is_symlink() for x in (output, *output.parents)):
        _fail()
    output.mkdir(exist_ok=False)
    manifest = {"schema": "geophysics.velocity-bundle/v1", "result_sha256": _hash(raw),
                "result_bytes": len(raw), "source": result["source"], "engine": result["engine"]}
    with (output / "result.json").open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    verified = _verify_result(read_regular(output / "result.json", MAX_RESULT), manifest)
    with (output / "manifest.json").open("xb") as handle:
        handle.write(_canonical(manifest))
        handle.flush()
        os.fsync(handle.fileno())
    return verified
