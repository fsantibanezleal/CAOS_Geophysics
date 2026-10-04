"""Local M03 numerical operators. No IGRF admission, network, online dispatch or inversion."""
from __future__ import annotations

from hashlib import sha256
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
import math
from pathlib import Path
import platform

from magnetic_line_contract import _type, digest, fail, validate_named


ENGINE_PINS = {"harmonica": "0.7.0", "verde": "1.9.0", "numpy": "2.2.6",
               "scipy": "1.15.2", "scikit-learn": "1.9.1", "threadpoolctl": "3.7.0", "xarray": "2026.9.0"}
SOURCE_PINS = {
    "harmonica._equivalent_sources.cartesian": "f62f2b5ad5a0ece1b66482a98d700f5093f8f5e18fd05062ca24e72437bea44f",
    "verde.base.least_squares": "a4eb01f891016a50be2451432842e0449ac924ec2fdfef8ecb182cc1f36ec090",
}
EPSILON = 2.220446049250313e-16


def engines():
    """Check existing actual imports and fixed scientific implementation pins."""
    if platform.python_implementation() != "CPython" or platform.python_version_tuple()[:2] != ("3", "12"):
        fail("runtime.python", "custody_mismatch", "fit")
    try:
        matches = all(version(name) == pin for name, pin in ENGINE_PINS.items())
    except PackageNotFoundError:
        matches = False
    if not matches:
        fail("runtime.engines", "custody_mismatch", "fit")
    for name, expected in SOURCE_PINS.items():
        module = import_module(name)
        try:
            path = Path(module.__file__).resolve()
            matches = sha256(path.read_bytes()).hexdigest() == expected
        except (OSError, TypeError, AttributeError):
            matches = False
        if not matches:
            fail("runtime.source", "custody_mismatch", "fit")
    return import_module("numpy"), import_module("harmonica")


def _array(value, columns=None, maximum=400, field="array"):
    # Only in-memory numerical inputs, after ordinary byte/shape preflight.
    np, _ = engines()
    if type(value) not in (list, tuple, np.ndarray) or (type(value) is np.ndarray and value.ndim == 0):
        fail(field + ".shape")
    if not 1 <= len(value) <= maximum:
        fail(field, "resource_refused")
    if columns is not None:
        if any(type(row) not in (list, tuple, np.ndarray) or
               (type(row) is np.ndarray and row.ndim != 1) or len(row) != columns for row in value):
            fail(field + ".shape")
    elif any(isinstance(row, (list, tuple, np.ndarray)) for row in value):
        fail(field + ".shape")
    scalars = [x for row in value for x in row] if columns is not None else value
    if any(isinstance(x, (bool, np.bool_)) for x in scalars):
        fail(field + ".boolean")
    if any(not isinstance(x, (int, float, np.integer, np.floating)) for x in scalars):
        fail(field + ".scalar_type")
    data = np.asarray(value)
    if data.dtype.kind not in "fiu" or not np.isfinite(data).all():
        fail(field + ".finite")
    with np.errstate(over="ignore", invalid="ignore"):
        data = data.astype(np.float64)
    if not np.isfinite(data).all():
        fail(field + ".float64_range")
    if (columns is None and data.ndim != 1) or (columns is not None and data.shape != (len(value), columns)):
        fail(field + ".shape")
    return data


def align_navigation(times, navigation_times, coordinates, tau_s, max_bracket_gap_s):
    """Position time=t+tau; only actual in-line brackets, no extrapolation/fill."""
    np, _ = engines()
    t = _array(times, field="lag.times")
    nav = _array(navigation_times, maximum=4096, field="lag.navigation_times")
    xyz = _array(coordinates, 3, 4096, "lag.navigation_coordinates")
    tau = _type(tau_s, "F64", "LagParameters.tau_s", 1)
    gap = _type(max_bracket_gap_s, "Pos", "LagParameters.max_bracket_gap_s", 1)
    if len(nav) != len(xyz) or len(nav) < 2 or np.any(np.diff(nav) <= 0):
        fail("NavigationSeries.order")
    targets = t + tau
    if not np.isfinite(targets).all():
        fail("lag.targets")
    output = np.full((len(t), 3), np.nan)
    valid = np.zeros(len(t), dtype=bool)
    for i, target in enumerate(targets):
        right = int(np.searchsorted(nav, target, side="left"))
        if right < len(nav) and target == nav[right]:
            output[i], valid[i] = xyz[right], True
        elif 0 < right < len(nav) and nav[right]-nav[right-1] <= gap:
            weight = (target-nav[right-1])/(nav[right]-nav[right-1])
            output[i] = (1-weight)*xyz[right-1] + weight*xyz[right]
            valid[i] = True
    return output, valid


def remove_base_and_heading(values, base, base_reference_nT, headings_deg, a0_nT, ac_nT, as_nT):
    np, _ = engines()
    values, base, headings = (_array(values, field="diurnal.values"), _array(base, field="diurnal.base"),
                              _array(headings_deg, field="heading.degrees"))
    reference, a0, ac, a_s = [_type(v, "F64", "correction.coefficient", 1)
                             for v in (base_reference_nT, a0_nT, ac_nT, as_nT)]
    if not len(values) == len(base) == len(headings) or np.any((headings < 0) | (headings >= 360)):
        fail("heading.shape_or_degrees")
    model = a0 + ac*np.cos(np.deg2rad(headings)) + a_s*np.sin(np.deg2rad(headings))
    result = values - (base-reference) - model
    if not np.isfinite(result).all():
        fail("correction.output", "metadata_ineligible", "correction")
    return result


def validate_reference(reference, source_kind, row_count):
    reference = validate_named("Reference", reference, row_count)
    # No reviewed independently evaluated IGRF receipt/datum exists. Shape,
    # declared hashes and downloaded Fortran are NOT evaluation admission.
    if reference["kind"] == "igrf_evaluated":
        fail("Reference.independent_evaluation", "metadata_ineligible", "correction")
    if source_kind != "original_synthetic_acquisition":
        fail("Reference.authored_constant", "metadata_ineligible", "correction")
    np, _ = engines()
    vector = np.column_stack([reference[k] for k in ("vector_east_nT", "vector_north_nT", "vector_up_nT")])
    field = np.asarray(reference["scalar_F_nT"], dtype=np.float64)
    tolerance = reference["evaluator"]["rounding_tolerance_nT"]
    if not np.all(np.abs(np.linalg.norm(vector, axis=1)-field) <= tolerance):
        fail("Reference.vector_scalar_consistency", "metadata_ineligible", "correction")
    if not np.array_equal(vector, np.broadcast_to(vector[0], vector.shape)) or not np.all(field == field[0]):
        fail("Reference.constant", "metadata_ineligible", "correction")
    return reference


def rereference_values(anomaly, old_reference_F, new_reference_F):
    np, _ = engines()
    anomaly, old, new = (_array(anomaly), _array(old_reference_F), _array(new_reference_F))
    if not len(anomaly) == len(old) == len(new) or np.any(old <= 0) or np.any(new <= 0):
        fail("rereference.shape_or_scalar")
    if np.array_equal(old, new):
        fail("rereference.already_target", "metadata_ineligible", "correction")
    result = anomaly + old - new
    if not np.isfinite(result).all():
        fail("rereference.output", "metadata_ineligible", "correction")
    return result


def weak_anomaly_diagnostic(perturbation_enu_nT, direction_enu, scalar_F_nT):
    """Projection versus actual vector norm; mathematical bound, not field uncertainty."""
    np, _ = engines()
    b, direction = _array(perturbation_enu_nT, 3), _array(direction_enu)
    f = _type(scalar_F_nT, "Pos", "reference.scalar_F_nT", 1)
    if len(direction) != 3 or abs(np.linalg.norm(direction)-1) > 1e-12:
        fail("reference.unit_direction")
    length = np.linalg.norm(b, axis=1)
    if np.any(length >= f):
        fail("reference.weak_bound_domain", "metadata_ineligible", "correction")
    weak = b @ direction
    exact = np.linalg.norm(f*direction+b, axis=1)-f
    bound = length**2/(2*(f-length))
    return weak, exact, bound


def intersect_segments(p0, p1, q0, q1, coordinate_tolerance_m, min_crossing_sine):
    """Translated float64 intersection with metre/m^2/dimensionless tolerances."""
    np, _ = engines()
    points = _array([p0, p1, q0, q1], 2, field="intersection.points")
    tau = _type(coordinate_tolerance_m, "Pos", "intersection.coordinate_tolerance_m", 1)
    sine = _type(min_crossing_sine, "Pos", "intersection.min_crossing_sine", 1)
    if not 1e-6 <= sine <= 1:
        fail("intersection.min_crossing_sine")
    points -= np.min(points, axis=0)
    v, w = points[1]-points[0], points[3]-points[2]
    lp, lq = np.linalg.norm(v), np.linalg.norm(w)
    if lp <= tau or lq <= tau:
        fail("intersection.degenerate", "metadata_ineligible", "crossover")
    det = float(v[0]*w[1]-v[1]*w[0])
    tau_det = 64*EPSILON*lp*lq + 4*tau*(lp+lq) + 4*tau*tau
    cutoff = max(sine, tau_det/(lp*lq))
    if not math.isfinite(det) or abs(det)/(lp*lq) <= cutoff:
        fail("intersection.parallel", "metadata_ineligible", "crossover")
    tau_ab = 64*EPSILON + 8*tau*(lp+lq)/abs(det)
    if tau_ab > 1e-6:
        fail("intersection.ill_conditioned", "metadata_ineligible", "crossover")
    matrix = np.column_stack((v, -w))
    try:
        a, b = np.linalg.solve(matrix, points[2]-points[0])
    except np.linalg.LinAlgError:
        fail("intersection.matrix", "metadata_ineligible", "crossover")
    residual = float(np.linalg.norm(matrix @ np.array([a, b])-(points[2]-points[0]), ord=np.inf))
    if not -tau_ab <= a <= 1+tau_ab or not -tau_ab <= b <= 1+tau_ab or residual > 8*tau:
        fail("intersection.parameters", "metadata_ineligible", "crossover")
    def snap(value):
        return 0. if abs(value) <= tau_ab else 1. if abs(value-1) <= tau_ab else float(value)
    a, b = snap(a), snap(b)
    point = np.asarray(p0, dtype=float) + a*v
    return dict(a=a, b=b, easting_m=float(point[0]), northing_m=float(point[1]),
                tolerance=dict(coordinate_m=tau, determinant_m2=float(tau_det), sine_dimensionless=float(cutoff),
                    parameter_dimensionless=float(tau_ab), matrix_residual_m=float(8*tau)))


def solve_offsets(crossings, weights_policy):
    """Training-graph QR offsets with one relative tie gauge per connected component."""
    if type(crossings) is not list or not 1 <= len(crossings) <= 4096:
        fail("leveling.crossings", "resource_refused")
    if weights_policy not in ("unweighted", "admitted_inverse_variance"):
        fail("leveling.weights_policy")
    for row in crossings:
        if type(row) is not dict or set(row) != {"flight", "tie", "difference_nT", "variance_nT2"}:
            fail("leveling.crossing")
        for key in ("flight", "tie"):
            _type(row[key], "ID", "leveling." + key, 1)
        _type(row["difference_nT"], "F64", "leveling.difference_nT", 1)
        if row["variance_nT2"] is not None:
            _type(row["variance_nT2"], "Pos", "leveling.variance_nT2", 1)
    lines = sorted({r[key] for r in crossings for key in ("flight", "tie")})
    ties = {r["tie"] for r in crossings}
    if len(lines) > 32 or ties.intersection(r["flight"] for r in crossings):
        fail("leveling.line_roles")
    np, _ = engines()
    from scipy.linalg import lstsq
    graph = {line: set() for line in lines}
    for row in crossings:
        graph[row["flight"]].add(row["tie"])
        graph[row["tie"]].add(row["flight"])
    pending, components, offsets = set(lines), [], {}
    while pending:
        group, frontier = set(), [min(pending)]
        while frontier:
            line = frontier.pop()
            if line not in group:
                group.add(line)
                frontier.extend(graph[line]-group)
        pending -= group
        group_ties = sorted(group & ties)
        if not group_ties:
            fail("leveling.gauge", "metadata_ineligible", "crossover")
        gauge = group_ties[0]
        free = sorted(group-{gauge})
        use = [r for r in crossings if r["flight"] in group]
        matrix, data, weights = [], [], []
        for row in use:
            matrix.append([float(line == row["flight"])-float(line == row["tie"]) for line in free])
            data.append(row["difference_nT"])
            if weights_policy == "admitted_inverse_variance" and row["variance_nT2"] is None:
                fail("leveling.variance", "metadata_ineligible", "crossover")
            weights.append(1. if weights_policy == "unweighted" else 1/math.sqrt(row["variance_nT2"]))
        matrix, data, weights = np.asarray(matrix), np.asarray(data), np.asarray(weights)
        scaled = matrix*weights[:, None]
        singular = np.linalg.svd(scaled, compute_uv=False)
        condition = float(singular[0]/singular[-1]) if singular[-1] > 0 else math.inf
        if not math.isfinite(condition) or condition > 1e12:
            fail("leveling.condition", "metadata_ineligible", "crossover")
        values, _, rank, _ = lstsq(scaled, data*weights, lapack_driver="gelsy")
        if rank != len(free):
            fail("leveling.rank", "metadata_ineligible", "crossover")
        offsets.update(zip(free, map(float, values)))
        offsets[gauge] = 0.
        components.append(dict(component_id=f"C{len(components):03d}", line_ids=sorted(group), gauge_line_id=gauge,
                               rank=int(rank), singular_values=singular.tolist(), condition=condition, absolute_datum=False))
    residuals = [r["difference_nT"]-(offsets[r["flight"]]-offsets[r["tie"]]) for r in crossings]
    return dict(offsets=offsets, components=components, residuals=residuals)


def fit_equivalent(rows, config, depth_m, damping):
    """Pinned real harmonic fit; explicit training-only blocks and raw weights."""
    from magnetic_line_validation import kernel_column_scales, source_blocks, validate_geometry_rows
    validate_geometry_rows(rows)
    config = validate_named("EquivalentSourcesConfig", config)
    depth = _type(depth_m, "Pos", "fit.depth_m", 1)
    damping = _type(damping, "Pos", "fit.damping", 1)
    if depth not in config["depth_candidates_m"] or damping not in config["damping_candidates"]:
        fail("fit.frozen_candidate")
    basis = source_blocks(rows, config["source_geometry"], depth)
    np, hm = engines()
    from threadpoolctl import threadpool_limits
    coordinates = _array([[r[k] for k in ("easting_m", "northing_m", "upward_m")] for r in rows], 3)
    sources = _array([[s[k] for k in ("easting_m", "northing_m", "upward_m")] for s in basis["sources"]], 3, 256)
    values = _array([r["magnetic_nT"] for r in rows])
    distance = np.linalg.norm(coordinates[:, None, :]-sources[None, :, :], axis=2)
    if np.any(distance == 0) or not np.isfinite(distance).all():
        fail("fit.distance", "metadata_ineligible", "fit")
    jacobian = 1/distance
    scales = np.asarray(kernel_column_scales(jacobian.tolist()))
    weights = np.ones(len(rows))
    if config["weights_policy"] == "admitted_inverse_variance":
        sigma = _array([r["uncertainty_nT"] for r in rows])
        if np.any(sigma <= 0):
            fail("fit.uncertainty", "metadata_ineligible", "fit")
        weights = 1/sigma**2
        if not np.isfinite(weights).all():
            fail("fit.weights", "metadata_ineligible", "fit")
    scaled = jacobian/scales
    augmented = np.vstack((np.sqrt(weights)[:, None]*scaled, math.sqrt(damping)*np.eye(len(sources))))
    with threadpool_limits(limits=1):
        singular = np.linalg.svd(augmented, compute_uv=False)
        condition = float(singular[0]/singular[-1]) if singular[-1] > 0 else math.inf
        if not math.isfinite(condition) or condition > 1e12:
            fail("fit.condition", "metadata_ineligible", "fit")
        model = hm.EquivalentSources(points=tuple(sources[:, j] for j in range(3)),
                                     damping=damping, dtype="float64", parallel=False)
        model.fit(tuple(coordinates[:, j] for j in range(3)), values,
                  weights=None if config["weights_policy"] == "unweighted" else weights)
        predicted = model.predict(tuple(coordinates[:, j] for j in range(3)))
    coefficients = np.asarray(model.coefs_, dtype=np.float64)
    if not np.isfinite(coefficients).all() or not np.isfinite(predicted).all():
        fail("fit.nonfinite", "metadata_ineligible", "fit")
    scaled_coefficients = coefficients*scales
    data_term = float(np.sum(weights*(values-predicted)**2))
    regularization = float(damping*np.sum(scaled_coefficients**2))
    return dict(source_positions=basis["sources"], source_block_map=basis["map"],
                coefficients=coefficients.tolist(), column_scales=scales.tolist(),
                objective=dict(data_term=data_term, regularization_term=regularization, total=data_term+regularization,
                    unit="nT^2" if config["weights_policy"] == "unweighted" else "dimensionless",
                    weight_multiplier=1., damping=damping, damping_unit=config["damping_unit"],
                    condition=condition, rank=len(sources)), _model=model)


def predict_equivalent(fitted, coordinates):
    np, _ = engines()
    coords = _array(coordinates, 3, 16384, "predict.coordinates")
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=1):
        predicted = fitted["_model"].predict(tuple(coords[:, i] for i in range(3)))
    if not np.isfinite(predicted).all():
        fail("predict.nonfinite", "metadata_ineligible", "predict")
    return predicted


def blocked_fit(rows, request, sealed):
    """Frozen8x3 fits, one final fit, then one outer opening; no outer tuning."""
    from magnetic_line_contract import channel_identity
    from magnetic_line_validation import make_partitions
    np, _ = engines()
    request = validate_named("Request", request, len(rows))
    if sealed != make_partitions(rows, request):
        fail("partition.custody", "custody_mismatch", "fit")
    if request["split"]["sealed_values_sha256"] != channel_identity(rows):
        fail("partition.sealed_values", "custody_mismatch", "fit")
    by_id = {r["row_id"]: r for r in rows}
    config = request["equivalent_sources"]
    candidates = []
    for depth in config["depth_candidates_m"]:
        for damping in config["damping_candidates"]:
            scores = []
            for fold in sealed["inner"]:
                train = [by_id[rid] for rid in fold["training_ids"]]
                unsupported = set(fold["geometry_only_coverage"]["unsupported_ids"])
                validation = [by_id[rid] for rid in fold["validation_ids"] if rid not in unsupported]
                if not validation:
                    fail("fit.fold_support", "metadata_ineligible", "fit")
                fitted = fit_equivalent(train, config, depth, damping)
                query = [[r[k] for k in ("easting_m", "northing_m", "upward_m")] for r in validation]
                # Only this fold's validation values enter its score.
                predicted = predict_equivalent(fitted, query)
                observed = _array([r["magnetic_nT"] for r in validation])
                rmse = float(np.sqrt(np.mean((observed-predicted)**2)))
                scores.append(dict(fold_id=fold["fold_id"], rmse_nT=rmse,
                                   training_sha256=digest(train), source_map_sha256=digest(fitted["source_block_map"]),
                                   coverage=fold["geometry_only_coverage"], scored_count=len(validation)))
            candidates.append(dict(depth_m=depth, damping=damping, mean_rmse_nT=math.fsum(s["rmse_nT"] for s in scores)/3,
                                   folds=scores))
    # Predeclared numerical1e-9 nT tie, never an error model.
    best_score = min(c["mean_rmse_nT"] for c in candidates)
    selected = max((c for c in candidates if abs(c["mean_rmse_nT"]-best_score) <= 1e-9),
                   key=lambda c: (c["damping"], c["depth_m"]))
    train = [by_id[rid] for rid in sealed["outer_training_ids"]]
    final = fit_equivalent(train, config, selected["depth_m"], selected["damping"])
    unsupported = set(sealed["geometry_only_coverage"]["unsupported_ids"])
    validation = [by_id[rid] for rid in sealed["outer_validation_ids"] if rid not in unsupported]
    if not validation:
        fail("fit.outer_support", "metadata_ineligible", "fit")
    predicted = predict_equivalent(final, [[r[k] for k in ("easting_m", "northing_m", "upward_m")] for r in validation])
    observed = _array([r["magnetic_nT"] for r in validation])
    residual = observed-predicted
    return dict(selected_candidate=dict(depth_m=selected["depth_m"], damping=selected["damping"]),
                candidates=candidates, training_sha256=digest(train), production_fit_count=25,
                evaluation_count=1, coverage=sealed["geometry_only_coverage"]["fraction"],
                outer_row_ids=[r["row_id"] for r in validation],
                outer_total_count=len(sealed["outer_validation_ids"]), outer_scored_count=len(validation),
                outer_unsupported_ids=sealed["geometry_only_coverage"]["unsupported_ids"],
                rmse_nT=float(np.sqrt(np.mean(residual**2))), signal_rms_nT=float(np.sqrt(np.mean(observed**2))),
                outer_observed_nT=observed.tolist(), outer_predicted_nT=predicted.tolist(),
                outer_observed_minus_predicted_nT=residual.tolist(), final_fit=final)
