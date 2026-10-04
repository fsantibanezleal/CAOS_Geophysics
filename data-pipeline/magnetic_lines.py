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


def reference_coordinates_sha256(rows, datum):
    """Canonical row/metric-coordinate/datum identity, not an evaluator receipt."""
    return digest(dict(datum=datum,rows=[[r["row_id"],r["easting_m"],r["northing_m"],r["upward_m"]] for r in rows]))


def _authored_auxiliary(identity, payload, metadata):
    # A verified embedded authored payload is not provider authentication.
    # Reviewed field-source/evaluator custody needs its separate reviewed seam.
    if metadata["source_kind"] != "original_synthetic_acquisition" or identity["source_verification"] != "authored":
        fail("auxiliary.independent_review", "metadata_ineligible", "correction")
    expected = digest(payload)
    if identity["source_sha256"] != expected or identity["canonical_records_sha256"] != expected or \
       identity["source_receipt_sha256"] != digest({k:v for k,v in identity.items() if k != "source_receipt_sha256"}):
        fail("auxiliary.authored_bytes", "custody_mismatch", "correction")
    if identity["rights"]["decision"] != "allowed" or identity["rights"]["private_processing"] != "allowed":
        fail("auxiliary.rights", "metadata_ineligible", "correction")


def _authored_clock(clock, metadata):
    expected = digest(dict(measurement_basis="UTC",auxiliary_basis="UTC",offset_s=0.,
                           definition="authored shared synthetic2001 clock"))
    if metadata["source_kind"] != "original_synthetic_acquisition" or \
       metadata["acquisition"]["timestamp_basis"] != "UTC" or clock["synchronization_evidence_sha256"] != expected:
        fail("auxiliary.clock_review", "metadata_ineligible", "correction")


def _bracket(records, utc, max_gap_s, keys, tau_s=0.):
    """Relative nanoseconds avoid loss from casting absolute UTC to float64."""
    from bisect import bisect_left
    from fractions import Fraction
    if utc is None:
        return None
    origin = _utc_ns(records[0]["utc"])
    times = [_utc_ns(r["utc"])-origin for r in records]
    target = _utc_ns(utc)-origin+Fraction.from_float(tau_s)*1000000000
    right = bisect_left(times,target)
    if right < len(times) and target == times[right]:
        return [records[right][k] for k in keys]
    if not 0 < right < len(times) or times[right]-times[right-1] > Fraction.from_float(max_gap_s)*1000000000:
        return None
    weight = float((target-times[right-1])/(times[right]-times[right-1]))
    return [math.fsum(((1-weight)*records[right-1][k],weight*records[right][k])) for k in keys]


def apply_instrument_corrections(rows, metadata, operation, masks):
    """One declared lag/base/heading edge with bounded authored custody checks."""
    from copy import deepcopy
    name,parameters = operation["operation"],operation["parameters"]
    output,flags = deepcopy(rows),deepcopy(masks)
    if name == "lag":
        series = parameters["navigation"]
        _authored_auxiliary(series["identity"],series["records"],metadata)
        _authored_clock(series["clock"],metadata)
        grouped = {}
        for record in series["records"]:
            grouped.setdefault(record["line_id"],[]).append(record)
    elif name == "diurnal":
        series = parameters["base"]
        _authored_auxiliary(series["identity"],series["records"],metadata)
        _authored_clock(series["clock"],metadata)
    elif name == "heading":
        coefficients = {k:parameters[k] for k in ("a0_nT","ac_nT","as_nT","convention")}
        calibration = parameters["calibration"]
        _authored_auxiliary(calibration["identity"],coefficients,metadata)
        if calibration["coefficient_receipt_sha256"] != digest(coefficients):
            fail("heading.coefficient_receipt", "custody_mismatch", "correction")
    else:
        fail("instrument.operation", "unsupported_operation", "correction")
    for i,row in enumerate(output):
        if flags[i]:
            continue
        if name == "lag":
            records = grouped.get(row["line_id"],[])
            position = None if len(records)<2 else _bracket(records,row["utc"],parameters["max_bracket_gap_s"],
                ("easting_m","northing_m","upward_m"),parameters["tau_s"])
            if position is None:
                flags[i].append("unsupported_time")
                row["magnetic_nT"] = None
            else:
                for key,value in zip(("easting_m","northing_m","upward_m"),position):
                    row[key] = value
                # Same declared terrain datum; do not manufacture missing terrain.
                row["clearance_m"] = None if row["terrain_upward_m"] is None else row["upward_m"]-row["terrain_upward_m"]
        elif name == "diurnal":
            inside = row["utc"] is not None and any(_utc_ns(t["start"]) <= _utc_ns(row["utc"]) <= _utc_ns(t["end"])
                                                    for t in parameters["valid_intervals"])
            base = _bracket(series["records"],row["utc"],parameters["max_bracket_gap_s"],("intensity_nT",)) if inside else None
            if base is None:
                flags[i].append("unsupported_time")
                row["magnetic_nT"] = None
            else:
                row["magnetic_nT"] -= base[0]-parameters["base_reference_nT"]
        elif row["heading_deg"] is None:
            flags[i].append("invalid_geometry")
            row["magnetic_nT"] = None
        else:
            heading = math.radians(row["heading_deg"])
            row["magnetic_nT"] -= parameters["a0_nT"]+parameters["ac_nT"]*math.cos(heading)+parameters["as_nT"]*math.sin(heading)
        if row["magnetic_nT"] is not None and not math.isfinite(row["magnetic_nT"]):
            fail("instrument.output", "metadata_ineligible", "correction")
    return output,flags


def apply_reference(rows, metadata, parameters, operation="main_field"):
    """Authored constant reference only; independently evaluated IGRF remains closed."""
    from copy import deepcopy
    from magnetic_line_contract import _reference_rows
    coordinate_hash = reference_coordinates_sha256(rows,metadata["coordinates"]["vertical_datum"])
    def check(reference):
        reference = validate_reference(reference,metadata["source_kind"],len(rows))
        _reference_rows(reference,rows,True,"Reference")
        if reference["receipt_sha256"] != digest({k:v for k,v in reference.items() if k != "receipt_sha256"}) or \
           reference["coordinates_sha256"] != coordinate_hash or reference["evaluator"]["input_coordinates_sha256"] != coordinate_hash:
            fail("Reference.corrected_geometry_or_receipt", "custody_mismatch", "correction")
        if reference["input_height_definition"] != metadata["coordinates"]["vertical_datum"] or reference["input_height_unit"] != "m" or \
           reference["evaluator"]["source_rights_evidence_sha256"] != digest(metadata["rights"]):
            fail("Reference.authored_datum_or_rights", "metadata_ineligible", "correction")
        return reference
    if operation == "main_field":
        reference = check(parameters["evaluated_reference"])
        if metadata["quantity"]["kind"] != "scalar_total_intensity":
            fail("Reference.input_quantity", "metadata_ineligible", "correction")
        shift = [-v for v in reference["scalar_F_nT"]]
    elif operation == "rereference":
        old,new = check(parameters["old_reference"]),check(parameters["new_reference"])
        current = metadata["reference"]
        if current is None or metadata["quantity"]["kind"] != "scalar_total_field_anomaly" or \
           current["receipt_sha256"] != old["receipt_sha256"] or parameters["input_reference_receipt_sha256"] != old["receipt_sha256"]:
            fail("rereference.input_reference", "custody_mismatch", "correction")
        if all(old[k] == new[k] for k in ("vector_east_nT","vector_north_nT","vector_up_nT","scalar_F_nT")):
            fail("rereference.already_target", "metadata_ineligible", "correction")
        applied = [s for s in metadata["channel_state"] if s["operation"] in ("main_field","rereference") and s["status"]=="applied"]
        if not applied or applied[-1]["evidence_sha256"] != parameters["old_applied_state_evidence_sha256"]:
            fail("rereference.old_applied_state", "custody_mismatch", "correction")
        shift = [a-b for a,b in zip(old["scalar_F_nT"],new["scalar_F_nT"])]
        reference = new
    else:
        fail("Reference.operation", "unsupported_operation", "correction")
    output = deepcopy(rows)
    for row,value in zip(output,shift):
        if row["magnetic_nT"] is not None:
            row["magnetic_nT"] += value
            if not math.isfinite(row["magnetic_nT"]):
                fail("Reference.output", "metadata_ineligible", "correction")
    return output,reference


def _channel_descriptor(rows, masks):
    values = [r["magnetic_nT"] for r in rows]
    return dict(shape=[len(rows)],dtype="float64",unit="nT",ordered_ids_sha256=digest([r["row_id"] for r in rows]),
                values=values,values_sha256=digest(values),masks=masks,mask_sha256=digest(masks))


def apply_corrections(csv_original, sidecar_original, request_original, training_ids=None, *, defer_microlevel=False):
    """Replay exact originals into immutable DAG channels; not a serialized Result.

    Authored auxiliary byte/clock custody is implemented. Field independent
    auxiliary/evaluator review is explicitly refused, not inferred from hashes.
    Unsupported lag positions retain original descriptive coordinates with a
    mask and null value; they cannot enter physical reference or fitting.
    """
    from copy import deepcopy
    from magnetic_line_contract import channel_identity,load_lines
    intake = load_lines(csv_original,sidecar_original,request_original)
    if type(defer_microlevel) is not bool:
        fail("correction.defer_grid_diagnostic")
    metadata,request = intake["metadata"],intake["request"]
    if request is None or metadata["source_kind"] in ("provider_grid","provider_image"):
        fail("correction.input", "metadata_ineligible", "correction")
    if metadata["rights"]["decision"] != "allowed" or metadata["rights"]["private_processing"] != "allowed":
        fail("correction.rights", "metadata_ineligible", "correction")
    rows = deepcopy(intake["rows"])
    masks = [["unsupported_operation"] if r["sensor_id"] != request["sensor_id"] else
             ["missing_value"] if r["magnetic_nT"] is None else [] for r in rows]
    state = deepcopy(metadata["channel_state"])
    kind = metadata["quantity"]["kind"]
    reference = metadata["reference"]
    leveling_result = None
    pending_grid_operations = []
    parent = channel_identity(rows)
    channels = [dict(channel_id="original",kind=kind,role="original",data=_channel_descriptor(rows,deepcopy(masks)),
                     state=deepcopy(state),parent_sha256=None,
                     reference_receipt_sha256=None if reference is None else reference["receipt_sha256"])]
    for operation in request["operations"]:
        name,parameters = operation["operation"],operation["parameters"]
        known = [s for s in state if s["operation"]==name]
        if name != "rereference" and (not known or any(s["status"] != "not_applied" for s in known)):
            fail("correction.unknown_or_already_applied", "metadata_ineligible", "correction")
        if name == "lag" and (kind != "scalar_total_intensity" or not any(
            s["operation"]=="main_field" and s["status"]=="not_applied" for s in state)):
            fail("lag.reference_subtracted_or_unknown", "metadata_ineligible", "correction")
        if name=="microlevel" and defer_microlevel:
            pending_grid_operations.append(deepcopy(operation))
            continue
        if name in ("lag","diurnal","heading"):
            rows,masks = apply_instrument_corrections(rows,metadata,operation,masks)
        elif name in ("main_field","rereference"):
            if any("unsupported_time" in flags for flags in masks):
                fail("Reference.unknown_aligned_geometry", "metadata_ineligible", "correction")
            actual_metadata = deepcopy(metadata)
            actual_metadata["quantity"]["kind"] = kind
            actual_metadata["reference"],actual_metadata["channel_state"] = reference,state
            rows,reference = apply_reference(rows,actual_metadata,parameters,name)
            kind = "scalar_total_field_anomaly"
        elif name == "leveling":
            if training_ids is None:
                fail("leveling.unsealed_training_scope", "metadata_ineligible", "correction")
            from magnetic_line_validation import make_partitions
            manifest = make_partitions(rows,request)
            allowed = [manifest["outer_training_ids"]]+[fold["training_ids"] for fold in manifest["inner"]]
            if training_ids not in allowed:
                fail("leveling.partition_identity", "custody_mismatch", "correction")
            before_level = deepcopy(rows)
            leveling = level_offsets(rows,request["geometry_policy"],training_ids,parameters["weights_policy"],metadata["uncertainty"])
            leveling_result = deepcopy(leveling)
            if not leveling["common_relative_gauge"]:
                fail("leveling.disconnected_relative_datums", "metadata_ineligible", "correction")
            rows = leveling["rows"]
            mask_order = ("missing_value","duplicate_identity_error","duplicate_location","invalid_geometry","gap",
                          "unsupported_time","height_mismatch","uncalibrated_line","outer_sealed","spatial_buffer",
                          "outside_hull","beyond_support_radius","sampling_unresolved","unsupported_operation")
            masks = [[reason for reason in mask_order if reason in a+b] for a,b in zip(masks,leveling["masks"])]
            supplied = parameters["heldout_calibration"]
            if supplied is not None:
                payload = {k:supplied[k] for k in ("values","reference_gauge_id")}
                calibration = supplied["calibration"]
                _authored_auxiliary(calibration["identity"],payload,metadata)
                if calibration["coefficient_receipt_sha256"] != digest(payload) or \
                   supplied["reference_gauge_id"] != leveling["components"][0]["gauge_line_id"]:
                    fail("leveling.independent_gauge_or_receipt", "custody_mismatch", "correction")
                offsets = {v["line_id"]:v["offset_nT"] for v in supplied["values"]}
                if offsets[supplied["reference_gauge_id"]] != 0.:
                    fail("leveling.independent_gauge_zero", "metadata_ineligible", "correction")
                for i,row in enumerate(rows):
                    if row["line_id"] in leveling["uncalibrated_line_ids"] and row["line_id"] in offsets:
                        original = before_level[i]
                        row["magnetic_nT"] = None if original["magnetic_nT"] is None else original["magnetic_nT"]-offsets[row["line_id"]]
                        masks[i] = [f for f in masks[i] if f != "uncalibrated_line"]
                        if row["magnetic_nT"] is not None and not math.isfinite(row["magnetic_nT"]):
                            fail("leveling.independent_output", "metadata_ineligible", "correction")
        else:
            fail("correction.terminal_grid_diagnostic", "unsupported_operation", "correction")
        output = digest(dict(rows=rows,masks=masks,kind=kind))
        evidence = digest(dict(operation=name,parent=parent,output=output,parameters=parameters))
        signs = dict(lag="position_time_plus_tau",diurnal="subtract_base_perturbation",heading="subtract_heading_model",
                     main_field="subtract_reference_F",rereference="add_old_subtract_new_F",leveling="subtract_line_offset")
        state.append(dict(operation=name,status="applied",parent_channel_sha256=parent,output_channel_sha256=output,
            evidence_sha256=evidence,parameters=parameters,units="m" if name=="lag" else "nT",sign=signs[name],applied_by="processor"))
        channels.append(dict(channel_id=f"derived{len(channels):02d}",kind=kind,role="derived",data=_channel_descriptor(rows,deepcopy(masks)),
            state=deepcopy(state),parent_sha256=parent,reference_receipt_sha256=None if reference is None else reference["receipt_sha256"]))
        parent = output
    return dict(original_rows=intake["rows"],rows=rows,masks=masks,state=state,kind=kind,channels=channels,
                output_sha256=parent,reference=reference,leveling=leveling_result,
                pending_grid_operations=pending_grid_operations,provider_authenticated=False,numerical_success=False)


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
    from threadpoolctl import threadpool_limits
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
        with np.errstate(over="ignore",invalid="ignore"):
            scaled = matrix*weights[:, None]
            rhs = data*weights
        if not np.isfinite(scaled).all() or not np.isfinite(rhs).all():
            fail("leveling.scaled_range", "metadata_ineligible", "crossover")
        try:
            with threadpool_limits(limits=1):
                singular = np.linalg.svd(scaled, compute_uv=False)
                condition = float(singular[0]/singular[-1]) if singular[-1] > 0 else math.inf
                if not math.isfinite(condition) or condition > 1e12:
                    fail("leveling.condition", "metadata_ineligible", "crossover")
                values, _, rank, _ = lstsq(scaled, rhs, lapack_driver="gelsy")
        except np.linalg.LinAlgError:
            fail("leveling.native_solve", "metadata_ineligible", "crossover")
        if rank != len(free) or not np.isfinite(values).all():
            fail("leveling.rank", "metadata_ineligible", "crossover")
        offsets.update(zip(free, map(float, values)))
        offsets[gauge] = 0.
        components.append(dict(component_id=f"C{len(components):03d}", line_ids=sorted(group), gauge_line_id=gauge,
                               rank=int(rank), singular_values=singular.tolist(), condition=condition, absolute_datum=False))
    residuals = [r["difference_nT"]-(offsets[r["flight"]]-offsets[r["tie"]]) for r in crossings]
    if not all(math.isfinite(r) for r in residuals):
        fail("leveling.residual_range", "metadata_ineligible", "crossover")
    return dict(offsets=offsets, components=components, residuals=residuals)


def _utc_ns(value):
    from magnetic_line_contract import utc_key
    date, nano = utc_key(value)
    return ((date.toordinal()*86400 + date.hour*3600 + date.minute*60 + date.second)*1000000000 + nano)


def crossovers(rows, geometry_policy, eligible_ids=None, uncertainty=None):
    """Inventory original-adjacency candidates before physical/partition admission.

    Null/gapped records are never filtered then reconnected. Values outside the
    supplied training IDs are not interpolated. No field error is inferred.
    """
    from magnetic_line_contract import MagneticContractError
    from fractions import Fraction
    from magnetic_line_validation import validate_geometry_rows
    validate_geometry_rows(rows)
    for row in rows:
        _type(row["magnetic_nT"], "?F64", "crossover.magnetic_nT", len(rows))
        _type(row["uncertainty_nT"], "?Pos", "crossover.uncertainty_nT", len(rows))
    policy = validate_named("GeometryPolicy", geometry_policy, len(rows))
    physical = policy["crossover"]
    ids = {r["row_id"] for r in rows}
    if eligible_ids is not None and (type(eligible_ids) is not list or len(set(eligible_ids)) != len(eligible_ids) or
                                     not set(eligible_ids) <= ids):
        fail("crossover.training_ids")
    eligible = ids if eligible_ids is None else set(eligible_ids)
    if physical["uncertainty_policy"] == "documented_independent_rows":
        model = None if uncertainty is None else validate_named("Uncertainty", uncertainty)
        if model is None or model["meaning"] != "independent_one_sigma" or model["independence_assumption"] != "row_independent":
            fail("crossover.uncertainty", "metadata_ineligible", "crossover")
    span = max(max(r[k] for r in rows)-min(r[k] for r in rows) for k in ("easting_m","northing_m"))
    tau = 64*EPSILON*max(1., span, max(abs(r[k]) for r in rows for k in ("easting_m","northing_m")))
    if not math.isfinite(tau) or not math.isfinite(span):
        fail("crossover.geometry_range", "metadata_ineligible", "crossover")
    grouped = {}
    for i, row in enumerate(rows):
        grouped.setdefault((row["line_id"],row["sensor_id"]),[]).append((i,row))
    adjacencies = []
    for group in grouped.values():
        for (i,p),(_,q) in zip(group,group[1:]):
            adjacencies.append(dict(segment_id=f"S{i:06d}",p=p,q=q))
    flights = [s for s in adjacencies if s["p"]["line_kind"] in ("flight","reflight")]
    ties = [s for s in adjacencies if s["p"]["line_kind"] == "tie"]
    def bounds(segment, key):
        return sorted((segment["p"][key],segment["q"][key]))
    pairs = []
    for flight in flights:
        for tie in ties:
            if all(bounds(flight,k)[0] <= bounds(tie,k)[1]+tau and bounds(tie,k)[0] <= bounds(flight,k)[1]+tau
                   for k in ("easting_m","northing_m")):
                if len(pairs) == 4096:
                    fail("crossover.segment_pairs", "resource_refused", "crossover")
                pairs.append((flight,tie))
    pairs.sort(key=lambda pair:(pair[0]["segment_id"],pair[1]["segment_id"]))
    inventory, representatives = [], []
    for index,(flight,tie) in enumerate(pairs):
        endpoints = [s[k] for s in (flight,tie) for k in ("p","q")]
        record = dict(crossover_id=f"X{index:06d}",flight_segment_id=flight["segment_id"],tie_segment_id=tie["segment_id"],
            a=None,b=None,easting_m=None,northing_m=None,flight_minus_tie_nT=None,height_difference_m=None,
            time_separation_s=None,difference_variance_nT2=None,disposition="rejected",reasons=[],
            shared_endpoint_group_id=None,constraint_representative=None,
            tolerance=dict(coordinate_m=tau,determinant_m2=None,sine_dimensionless=None,
                           parameter_dimensionless=None,matrix_residual_m=None))
        reasons = record["reasons"]
        for s in (flight,tie):
            p,q = s["p"],s["q"]
            length = math.hypot(q["easting_m"]-p["easting_m"],q["northing_m"]-p["northing_m"])
            if not math.isfinite(length) or length > policy["max_segment_gap_m"]:
                reasons.append("gap")
            if policy["max_time_gap_s"] is not None:
                if p["utc"] is None or q["utc"] is None:
                    reasons.append("unsupported_time")
                elif not 0 < _utc_ns(q["utc"])-_utc_ns(p["utc"]) <= Fraction.from_float(policy["max_time_gap_s"])*1000000000:
                    reasons.append("gap")
        if any(p["row_id"] not in eligible for p in endpoints):
            if any(p["line_kind"]=="tie" and p["row_id"] not in eligible for p in endpoints):
                reasons.append("spatial_buffer")
            if any(p["line_kind"]!="tie" and p["row_id"] not in eligible for p in endpoints):
                reasons.append("outer_sealed")
        if any(p["sensor_id"] != flight["p"]["sensor_id"] for p in endpoints):
            reasons.append("sensor_mismatch")
        if any(p["magnetic_nT"] is None for p in endpoints):
            reasons.append("missing_value")
        if any(p["upward_m"] is None for p in endpoints):
            reasons.append("missing_height")
        coordinates = [[p["easting_m"],p["northing_m"]] for p in endpoints]
        v = [coordinates[1][i]-coordinates[0][i] for i in range(2)]
        w = [coordinates[3][i]-coordinates[2][i] for i in range(2)]
        lp,lq = math.hypot(*v),math.hypot(*w)
        if lp > tau and lq > tau and math.isfinite(lp*lq):
            det = abs(v[0]*w[1]-v[1]*w[0])
            threshold = 64*EPSILON*lp*lq+4*tau*(lp+lq)+4*tau*tau
            record["tolerance"]["determinant_m2"] = threshold
            record["tolerance"]["sine_dimensionless"] = max(physical["min_crossing_sine"],threshold/(lp*lq))
            if det > 0:
                record["tolerance"]["parameter_dimensionless"] = 64*EPSILON+8*tau*(lp+lq)/det
        try:
            geometry = intersect_segments(*coordinates,tau,physical["min_crossing_sine"])
            for key in ("a","b","easting_m","northing_m","tolerance"):
                record[key] = geometry[key]
        except MagneticContractError as exc:
            field = exc.error["field"]
            reasons.append({"intersection.degenerate":"degenerate_segment","intersection.parallel":"parallel_or_collinear",
                            "intersection.ill_conditioned":"ill_conditioned","intersection.matrix":"ill_conditioned",
                            "intersection.parameters":"parameter_outside_segment"}.get(field,"ill_conditioned"))
        if record["a"] is not None and record["b"] is not None and "missing_height" not in reasons:
            def interpolate(s, key, weight):
                a,b = s["p"][key],s["q"][key]
                return a if a == b else math.fsum(((1-weight)*a,weight*b))
            a,b = record["a"],record["b"]
            height = interpolate(flight,"upward_m",a)-interpolate(tie,"upward_m",b)
            if not math.isfinite(height):
                fail("crossover.height_range", "metadata_ineligible", "crossover")
            record["height_difference_m"] = height
            if abs(height) > physical["max_height_separation_m"]:
                reasons.append("height_mismatch")
            if all(p["utc"] is not None for p in endpoints):
                origin = min(_utc_ns(p["utc"]) for p in endpoints)
                times = [_utc_ns(p["utc"])-origin for p in endpoints]
                delta = abs(math.fsum(((1-a)*times[0],a*times[1],-(1-b)*times[2],-b*times[3])))*1e-9
                record["time_separation_s"] = delta
                if physical["max_time_separation_s"] is not None and delta > physical["max_time_separation_s"]:
                    reasons.append("unsupported_time")
            elif physical["max_time_separation_s"] is not None:
                reasons.append("unsupported_time")
            if not reasons:
                difference = interpolate(flight,"magnetic_nT",a)-interpolate(tie,"magnetic_nT",b)
                if not math.isfinite(difference):
                    fail("crossover.difference", "metadata_ineligible", "crossover")
                record["flight_minus_tie_nT"] = difference
                if physical["uncertainty_policy"] == "documented_independent_rows":
                    sigma = [p["uncertainty_nT"] for p in endpoints]
                    if any(x is None or x <= 0 for x in sigma):
                        fail("crossover.sigma", "metadata_ineligible", "crossover")
                    try:
                        variance = math.fsum((s*w)*(s*w) for s,w in zip(sigma,(1-a,a,1-b,b)))
                    except OverflowError:
                        fail("crossover.variance", "metadata_ineligible", "crossover")
                    if not math.isfinite(variance) or variance <= 0:
                        fail("crossover.variance", "metadata_ineligible", "crossover")
                    record["difference_variance_nT2"] = variance
                record["disposition"] = "admitted"
                role = (flight["p"]["line_id"],tie["p"]["line_id"],flight["p"]["sensor_id"])
                group = next((r for group_role,r in representatives if group_role==role and
                              math.hypot(record["easting_m"]-r["easting_m"],record["northing_m"]-r["northing_m"]) <= tau),None)
                if group is None:
                    representatives.append((role,record))
                    group = record
                else:
                    reasons.append("duplicate_physical_constraint")
                record["constraint_representative"] = group["crossover_id"]
                record["shared_endpoint_group_id"] = group["crossover_id"]
        # Stable diagnostic enum order; rejected pairs never carry an equality.
        order = ("degenerate_segment","parallel_or_collinear","ill_conditioned","parameter_outside_segment",
                 "matrix_residual_exceeded","gap","missing_value","missing_height","height_mismatch","unsupported_time",
                 "sensor_mismatch","channel_state_mismatch","duplicate_physical_constraint","uncalibrated_line",
                 "spatial_buffer","outer_sealed")
        record["reasons"] = [r for r in order if r in reasons]
        inventory.append(record)
    return inventory


def level_offsets(rows, geometry_policy, training_ids, weights_policy="unweighted", uncertainty=None):
    """Infer offsets from training brackets only; retain uncalibrated rows as null."""
    inventory = crossovers(rows,geometry_policy,training_ids,uncertainty)
    by_id = {f"S{i:06d}":r for i,r in enumerate(rows)}
    constraints = [dict(flight=by_id[x["flight_segment_id"]]["line_id"],tie=by_id[x["tie_segment_id"]]["line_id"],
                        difference_nT=x["flight_minus_tie_nT"],variance_nT2=x["difference_variance_nT2"])
                   for x in inventory if x["disposition"]=="admitted" and x["constraint_representative"]==x["crossover_id"]]
    if not constraints:
        fail("leveling.no_training_constraints", "metadata_ineligible", "crossover")
    result = solve_offsets(constraints,weights_policy)
    corrected,masks = [],[]
    for row in rows:
        item = dict(row)
        if row["line_id"] not in result["offsets"]:
            item["magnetic_nT"] = None
            masks.append(["uncalibrated_line"])
        elif row["magnetic_nT"] is None:
            masks.append(["missing_value"])
        else:
            item["magnetic_nT"] = row["magnetic_nT"]-result["offsets"][row["line_id"]]
            if not math.isfinite(item["magnetic_nT"]):
                fail("leveling.output", "metadata_ineligible", "correction")
            masks.append([])
        corrected.append(item)
    return dict(**result,rows=corrected,masks=masks,crossovers=inventory,
                uncalibrated_line_ids=sorted({r["line_id"] for r in rows}-set(result["offsets"])),
                common_relative_gauge=len(result["components"])==1,absolute_datum=False)


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
        with np.errstate(over="ignore",under="ignore",divide="ignore",invalid="ignore"):
            weights = 1/sigma**2
        if not np.isfinite(weights).all() or np.any(weights<=0):
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
        try:
            model.fit(tuple(coordinates[:, j] for j in range(3)), values,
                      weights=None if config["weights_policy"] == "unweighted" else weights)
            predicted = model.predict(tuple(coordinates[:, j] for j in range(3)))
        except (ValueError,FloatingPointError,OverflowError,np.linalg.LinAlgError):
            fail("fit.native_solve","metadata_ineligible","fit")
    coefficients = np.asarray(model.coefs_, dtype=np.float64)
    if not np.isfinite(coefficients).all() or not np.isfinite(predicted).all():
        fail("fit.nonfinite", "metadata_ineligible", "fit")
    scaled_coefficients = coefficients*scales
    with np.errstate(over="ignore",invalid="ignore"):
        data_term = float(np.sum(weights*(values-predicted)**2))
        regularization = float(damping*np.sum(scaled_coefficients**2))
    if not all(math.isfinite(t) for t in (data_term,regularization,data_term+regularization)):
        fail("fit.objective_range","metadata_ineligible","fit")
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


def blocked_fit(rows, request, sealed, *, original_inputs=None):
    """Frozen8x3 fits; corrected channels require exact independent input replay.

    No supplied parent hash can substitute for original bytes. Training-only
    leveling is recomputed per inner/final partition, never once on all rows.
    Existing uncorrected S1 recipe/outputs/candidates remain unchanged.
    """
    from magnetic_line_contract import channel_identity,load_lines
    from magnetic_line_validation import make_partitions
    np, _ = engines()
    request = validate_named("Request", request, len(rows))
    if sealed != make_partitions(rows, request):
        fail("partition.custody", "custody_mismatch", "fit")
    processing_lineage = None
    fold_rows = None
    if original_inputs is not None:
        if type(original_inputs) is not tuple or len(original_inputs)!=3 or any(type(v) is not bytes for v in original_inputs):
            fail("fit.original_input_bytes")
        intake = load_lines(*original_inputs)
        if intake["request"] != request:
            fail("fit.original_request","custody_mismatch","fit")
        final_run = apply_corrections(*original_inputs,training_ids=sealed["outer_training_ids"],defer_microlevel=True)
        if final_run["rows"] != rows or final_run["kind"]!="scalar_total_field_anomaly":
            fail("fit.derived_channel_replay","custody_mismatch","fit")
        scopes = [fold["training_ids"] for fold in sealed["inner"]]+[sealed["outer_training_ids"]]
        runs = [apply_corrections(*original_inputs,training_ids=scope,defer_microlevel=True) for scope in scopes[:3]]+[final_run]
        for run,scope,validation_ids in zip(runs,scopes,
            [fold["validation_ids"] for fold in sealed["inner"]]+[sealed["outer_validation_ids"]]):
            selected = set(scope+validation_ids)
            if any(flags for r,flags in zip(run["rows"],run["masks"]) if r["row_id"] in selected):
                fail("fit.corrected_training_or_holdout_masks","metadata_ineligible","fit")
        fold_rows = [{r["row_id"]:r for r in run["rows"]} for run in runs[:3]]
        processing_lineage = dict(input_channel_sha256=intake["channel_sha256"],derived_output_sha256=final_run["output_sha256"],
            request_original_sha256=sha256(original_inputs[2]).hexdigest(),csv_original_sha256=intake["csv_sha256"],
            sidecar_original_sha256=intake["sidecar_sha256"],fold_local=True,
            correction_output_sha256=[run["output_sha256"] for run in runs],
            leveling_training_sha256=[digest(scope) for scope in scopes] if final_run["leveling"] is not None else [],
            leveling_constraints_sha256=[digest([x for x in run["leveling"]["crossovers"] if x["disposition"]=="admitted"
                and x["constraint_representative"]==x["crossover_id"]]) for run in runs] if final_run["leveling"] is not None else [])
    elif request["operations"] or request["split"]["sealed_values_sha256"] != channel_identity(rows):
        fail("partition.sealed_values", "custody_mismatch", "fit")
    by_id = {r["row_id"]: r for r in rows}
    config = request["equivalent_sources"]
    candidates = []
    for depth in config["depth_candidates_m"]:
        for damping in config["damping_candidates"]:
            scores = []
            for fold_index,fold in enumerate(sealed["inner"]):
                actual = by_id if fold_rows is None else fold_rows[fold_index]
                train = [actual[rid] for rid in fold["training_ids"]]
                unsupported = set(fold["geometry_only_coverage"]["unsupported_ids"])
                validation = [actual[rid] for rid in fold["validation_ids"] if rid not in unsupported]
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
    result = dict(selected_candidate=dict(depth_m=selected["depth_m"], damping=selected["damping"]),
                candidates=candidates, training_sha256=digest(train), production_fit_count=25,
                evaluation_count=1, coverage=sealed["geometry_only_coverage"]["fraction"],
                outer_row_ids=[r["row_id"] for r in validation],
                outer_total_count=len(sealed["outer_validation_ids"]), outer_scored_count=len(validation),
                outer_unsupported_ids=sealed["geometry_only_coverage"]["unsupported_ids"],
                rmse_nT=float(np.sqrt(np.mean(residual**2))), signal_rms_nT=float(np.sqrt(np.mean(observed**2))),
                outer_observed_nT=observed.tolist(), outer_predicted_nT=predicted.tolist(),
                outer_observed_minus_predicted_nT=residual.tolist(), final_fit=final)
    if processing_lineage is not None:
        result["processing_lineage"] = processing_lineage
    return result


def geometric_comparator(rows, coordinates, *, same_plane_height_tolerance_m):
    """Actual LinearND triangle interpolation, no height transfer or extrapolation."""
    from magnetic_line_validation import validate_geometry_rows
    validate_geometry_rows(rows)
    if same_plane_height_tolerance_m is None:
        fail("comparator.height_policy","metadata_ineligible","fit")
    tolerance = _type(same_plane_height_tolerance_m,"Nonneg","comparator.height_tolerance",len(rows))
    np,_ = engines()
    data = _array([[r[k] for k in ("easting_m","northing_m","upward_m")] for r in rows],3)
    query = _array(coordinates,3,16384,"comparator.query")
    values = _array([r["magnetic_nT"] for r in rows])
    if len(rows)<3 or np.max(np.abs(data[:,2]-data[0,2]))>tolerance or np.max(np.abs(query[:,2]-data[0,2]))>tolerance:
        fail("comparator.height_mismatch","metadata_ineligible","fit")
    origin = np.min(data[:,:2],axis=0)
    xy = data[:,:2]-origin
    if not np.isfinite(xy).all() or np.linalg.matrix_rank(xy-xy[0])<2:
        fail("comparator.xy_rank","metadata_ineligible","fit")
    from scipy.interpolate import LinearNDInterpolator
    from scipy.spatial import QhullError
    from threadpoolctl import threadpool_limits
    try:
        with threadpool_limits(limits=1):
            interpolator = LinearNDInterpolator(xy,values,fill_value=np.nan)
            predicted = interpolator(query[:,:2]-origin)
    except QhullError:
        fail("comparator.triangulation","metadata_ineligible","fit")
    if np.isinf(predicted).any():
        fail("comparator.nonfinite","metadata_ineligible","fit")
    return dict(values=[None if math.isnan(v) else float(v) for v in predicted],
        masks=[["outside_hull"] if math.isnan(v) else [] for v in predicted],height_transform_claim=False,
        method="scipy_linear_nd",verdict="eligible")


def _partition_geometry(intake):
    """Independent known navigation precedes the seal; no magnetic fitting."""
    from copy import deepcopy
    rows,flags = deepcopy(intake["rows"]),[[] for _ in intake["rows"]]
    for op in intake["request"]["operations"]:
        if op["operation"]=="lag":
            state = [s for s in intake["metadata"]["channel_state"] if s["operation"]=="lag"]
            if not state or any(s["status"]!="not_applied" for s in state):
                fail("lag.geometry_state","metadata_ineligible","partition")
            rows,flags = apply_instrument_corrections(rows,intake["metadata"],op,flags)
            if any(flags):
                fail("lag.geometry_overlap","metadata_ineligible","partition")
    return rows


def fit_grid(csv_original, sidecar_original, request_original):
    """Local correction/blocked fit/height/support orchestration, NOT Result JSON.

    No field-source approval is inferred. Synthetic quality failure is retained
    alongside actual computed diagnostics. A future complete serializer/export
    has additional exact contracts; this internal mapping is not that result.
    """
    from magnetic_line_contract import load_lines,preflight,MagneticContractError
    from magnetic_line_validation import make_partitions
    original = (csv_original,sidecar_original,request_original)
    intake = load_lines(*original)
    meta,request = intake["metadata"],intake["request"]
    if request is None or meta["rights"]["decision"]!="allowed" or meta["rights"]["private_processing"]!="allowed":
        fail("fit.input_or_rights","metadata_ineligible","fit")
    unresolved = set(intake["eligibility_reasons"])-{"uncertainty_unresolved"}
    if meta["source_kind"]!="original_synthetic_acquisition" or unresolved:
        fail("fit.physical_metadata_or_independent_source_review","metadata_ineligible","fit")
    aligned = _partition_geometry(intake)
    sealed = make_partitions(aligned,request)
    counts = preflight(aligned,meta,request)
    processed = apply_corrections(*original,training_ids=sealed["outer_training_ids"],defer_microlevel=True)
    if processed["kind"]!="scalar_total_field_anomaly":
        fail("fit.reference_subtracted_anomaly_required","metadata_ineligible","fit")
    fitted = blocked_fit(processed["rows"],request,sealed,original_inputs=original)
    by_id = {r["row_id"]:r for r in processed["rows"]}
    training = [by_id[r] for r in sealed["outer_training_ids"]]
    validation = [by_id[r] for r in fitted["outer_row_ids"]]
    config = request["grid"]
    np,_ = engines()
    east = config["origin_e_m"]+np.arange(config["nx"])*config["spacing_e_m"]
    north = config["origin_n_m"]+np.arange(config["ny"])*config["spacing_n_m"]
    ee,nn = np.meshgrid(east,north)
    support = support_masks(processed["rows"],training,config,request["geometry_policy"],sensor_id=request["sensor_id"])
    final = fitted["final_fit"]
    if config["plane_upward_m"]<max(r["upward_m"] for r in training) or any(
        s["upward_m"]>=config["plane_upward_m"] for s in final["source_positions"]):
        fail("grid.source_free_higher_plane","metadata_ineligible","predict")
    coordinates = np.column_stack((ee.ravel(),nn.ravel(),np.full(ee.size,config["plane_upward_m"])))
    predictions = predict_equivalent(final,coordinates).reshape(config["ny"],config["nx"])
    def plane(values,height,method):
        return dict(values=values,east_axis=east,north_axis=north,plane_upward_m=height,method=method,
            masked_values=[None if denied else float(value) for value,denied in zip(values.ravel(),support["excluded"])],
            masks=support["masks"],excluded=support["excluded"])
    grid = plane(predictions,config["plane_upward_m"],"harmonica_equivalent_sources")
    continued = None
    fft = dict(verdict="ineligible",reason="No positive requested height transfer",result=None)
    if config["continuation_delta_m"] is not None:
        height = config["plane_upward_m"]+config["continuation_delta_m"]
        if not math.isfinite(height) or height<=config["plane_upward_m"]:
            fail("grid.continued_height_float64","metadata_ineligible","predict")
        query = coordinates.copy()
        query[:,2] = height
        continued = plane(predict_equivalent(final,query).reshape(predictions.shape),height,"direct_equivalent_source_prediction")
        if not any(support["excluded"]):
            fft = dict(verdict="eligible",reason=None,
                result=continue_plane(predictions,config,datum=meta["coordinates"]["vertical_datum"],source_free=True))
        else:
            fft["reason"] = "Incomplete supported plane; no FFT fill/extrapolation"
    query = [[r[k] for k in ("easting_m","northing_m","upward_m")] for r in validation]
    try:
        comparator = geometric_comparator(training,query,
            same_plane_height_tolerance_m=request["geometry_policy"]["same_plane_height_tolerance_m"])
    except MagneticContractError as exc:
        if exc.error["code"]!="metadata_ineligible":
            raise
        comparator = dict(method="scipy_linear_nd",verdict="ineligible",reason=exc.error["reason"],values=None,masks=None,
                          height_transform_claim=False)
    spectrum = None
    exclusion_masks = [flags if denied else [] for flags,denied in zip(support["masks"],support["excluded"])]
    if request["spectrum"] is not None:
        spectrum = power_spectrum(predictions,config,request["spectrum"],exclusion_masks)
    microlevel = None
    for op in processed["pending_grid_operations"]:
        # IDs do not establish flight kind for user data.
        flight_ids = {r["line_id"] for r in processed["rows"] if r["line_kind"] in ("flight","reflight")}
        azimuths = [s["azimuth_deg"] for s in support["line_statistics"] if s["line_id"] in flight_ids]
        microlevel = microlevel_diagnostic(predictions,config,op["parameters"],
            acquisition_azimuths_deg=azimuths,masks=exclusion_masks)
    baseline_control = meta["authored_control"]["regime"]=="S1"
    quality = ("pass" if fitted["rmse_nT"]<=max(.05*fitted["signal_rms_nT"],1e-6) else "fail") if baseline_control else "unresolved"
    return dict(intake=intake,processing=processed,partitions=sealed,preflight=counts,fit=fitted,grid=grid,
        continued_grid=continued,fft_continuation=fft,comparator=comparator,support=support,spectrum=spectrum,microlevel=microlevel,
        synthetic_quality_verdict=quality,provider_authenticated=False,field_acceptance="unresolved")


MASK_ORDER = ("missing_value","duplicate_identity_error","duplicate_location","invalid_geometry","gap","unsupported_time",
              "height_mismatch","uncalibrated_line","outer_sealed","spatial_buffer","outside_hull","beyond_support_radius",
              "sampling_unresolved","unsupported_operation")


def support_masks(original_rows, training_rows, grid_config, geometry_policy, *, sensor_id):
    """Closed hull/distance support, conservative actual-gap tubes and spacing.

    Broken ORIGINAL adjacencies mask points within the declared support radius.
    CV removal alone never invents an acquisition gap. Sampling flags are
    diagnostic; an output pixel does not establish a recoverable wavelength.
    """
    from magnetic_line_validation import validate_geometry_rows,_hull,_cross
    from statistics import median
    from fractions import Fraction
    validate_geometry_rows(original_rows)
    validate_geometry_rows(training_rows)
    _type(sensor_id,"ID","support.sensor_id",len(original_rows))
    grid = validate_named("GridConfig",grid_config)
    policy = validate_named("GeometryPolicy",geometry_policy)
    nx,ny = grid["nx"],grid["ny"]
    if nx*ny>16384:
        fail("support.cells","resource_refused","predict")
    originals = {r["row_id"]:r for r in original_rows}
    keys = ("line_id","line_kind","sensor_id","ordinal","utc","easting_m","northing_m","upward_m")
    if any(r["row_id"] not in originals or any(r[k]!=originals[r["row_id"]][k] for k in keys) for r in training_rows):
        fail("support.training_geometry_identity","custody_mismatch","predict")
    selected = [r for r in original_rows if r["sensor_id"]==sensor_id]
    training = [r for r in training_rows if r["sensor_id"]==sensor_id and r["magnetic_nT"] is not None and r["upward_m"] is not None]
    if not selected or len(training)<3:
        fail("support.eligible_training","metadata_ineligible","predict")
    np,_ = engines()
    _grid_array(np.zeros((ny,nx)),grid)
    origin = (min(r["easting_m"] for r in training),min(r["northing_m"] for r in training))
    points = [(r["easting_m"]-origin[0],r["northing_m"]-origin[1]) for r in training]
    # Hull/intersection algebra squares coordinate spans. Refuse nonfinite
    # arithmetic rather than admit an apparent hull from +/-inf products.
    spans = [max(p[k] for p in points)-min(p[k] for p in points) for k in (0,1)]
    if not all(math.isfinite(s*s) for s in spans):
        fail("support.hull_float64_range","metadata_ineligible","predict")
    hull = _hull(points)
    groups = {}
    for r in selected:
        groups.setdefault(r["line_id"],[]).append(r)
    stats,gaps,lines = [],[],[]
    for line,rows in groups.items():
        distances,azimuths,reversals,gap_count = [],[],0,0
        for a,b in zip(rows,rows[1:]):
            delta = (b["easting_m"]-a["easting_m"],b["northing_m"]-a["northing_m"])
            length = math.hypot(*delta)
            reasons = []
            if not math.isfinite(length):
                fail("support.distance_range","metadata_ineligible","predict")
            if length==0:
                reasons.append("duplicate_location")
            if length>policy["max_segment_gap_m"] or b["ordinal"]!=a["ordinal"]+1:
                reasons.append("gap")
            if any(r["magnetic_nT"] is None for r in (a,b)):
                reasons += ["missing_value","gap"]
            if any(r["upward_m"] is None for r in (a,b)):
                reasons.append("height_mismatch")
            if policy["max_time_gap_s"] is not None:
                if a["utc"] is None or b["utc"] is None:
                    reasons.append("unsupported_time")
                elif not 0<_utc_ns(b["utc"])-_utc_ns(a["utc"])<=Fraction.from_float(policy["max_time_gap_s"])*1000000000:
                    reasons.append("gap")
            if reasons:
                gap_count += 1
                gaps.append((a,b,reasons))
            else:
                distances.append(length)
                azimuths.append(math.degrees(math.atan2(delta[0],delta[1]))%360)
        start,end = rows[0],rows[-1]
        de,dn = end["easting_m"]-start["easting_m"],end["northing_m"]-start["northing_m"]
        length = math.hypot(de,dn)
        azimuth = None if length==0 else math.degrees(math.atan2(de,dn))%360
        if azimuth is not None:
            reversals = sum(abs((a-azimuth+180)%360-180)>90 for a in azimuths)
            if rows[0]["line_kind"]!="tie":
                lines.append(dict(line_id=line,azimuth_deg=azimuth,
                    center=(math.fsum(r["easting_m"]/len(rows) for r in rows),
                            math.fsum(r["northing_m"]/len(rows) for r in rows))))
        stats.append(dict(line_id=line,sensor_id=sensor_id,spacing_min_m=min(distances) if distances else None,
            spacing_median_m=median(distances) if distances else None,spacing_max_m=max(distances) if distances else None,
            local_perpendicular_spacing_m=None,azimuth_deg=azimuth,reversals=reversals,gap_count=gap_count,row_count=len(rows)))
    sampling_resolved = policy["minimum_resolved_wavelength_m"] is not None
    for line in lines:
        angle = math.radians(line["azimuth_deg"])
        spacing = []
        for other in lines:
            if other["line_id"]==line["line_id"]:
                continue
            if abs((other["azimuth_deg"]-line["azimuth_deg"]+90)%180-90)>5:
                sampling_resolved = False
                continue
            distance = abs((other["center"][0]-line["center"][0])*math.cos(angle)-
                           (other["center"][1]-line["center"][1])*math.sin(angle))
            if distance>0:
                spacing.append(distance)
        record = next(s for s in stats if s["line_id"]==line["line_id"])
        record["local_perpendicular_spacing_m"] = min(spacing) if spacing else None
        if not spacing or record["spacing_max_m"] is None or policy["minimum_resolved_wavelength_m"] is None or \
           policy["minimum_resolved_wavelength_m"]<2*max(min(spacing),record["spacing_max_m"]):
            sampling_resolved = False
    if len(lines)<2:
        sampling_resolved = False
    masks,excluded,nearest = [],[],[]
    radius = grid["support_radius_m"]
    for j in range(ny):
        for i in range(nx):
            point = (grid["origin_e_m"]+i*grid["spacing_e_m"],grid["origin_n_m"]+j*grid["spacing_n_m"])
            translated = (point[0]-origin[0],point[1]-origin[1])
            flags = []
            distance = min(math.dist(translated,p) for p in points)
            nearest.append(distance)
            if not all(_cross(a,hull[(k+1)%len(hull)],translated)>=0 for k,a in enumerate(hull)):
                flags.append("outside_hull")
            if distance>radius:
                flags.append("beyond_support_radius")
            for a,b,reasons in gaps:
                start = (a["easting_m"],a["northing_m"])
                delta = (b["easting_m"]-start[0],b["northing_m"]-start[1])
                length = math.hypot(*delta)
                direction = (0.,0.) if length==0 else tuple(d/length for d in delta)
                fraction = 0. if length==0 else math.fsum((point[k]-start[k])*direction[k] for k in (0,1))/length
                if not math.isfinite(fraction):
                    fail("support.gap_projection_range","metadata_ineligible","predict")
                weight = max(0.,min(1.,fraction))
                distance = math.hypot(*(point[k]-start[k]-weight*delta[k] for k in (0,1)))
                if distance<=radius:
                    flags += reasons
            denied = bool(flags)
            if not sampling_resolved:
                flags.append("sampling_unresolved")
            masks.append([f for f in MASK_ORDER if f in flags])
            excluded.append(denied)
    return dict(masks=masks,excluded=excluded,nearest_training_m=nearest,
        total_count=nx*ny,eligible_count=sum(not f for f in excluded),line_statistics=stats,
        sampling_resolved=sampling_resolved,gap_policy="original_broken_adjacency_closed_support_radius_tubes")


def _grid_array(values, config, masks=None):
    """Exact bounded scalar plane. No holes/strings/booleans become numeric zeros."""
    config = validate_named("GridConfig",config)
    nx,ny = config["nx"],config["ny"]
    if nx*ny > 16384:
        fail("grid.cells","resource_refused","predict",nx*ny,16384)
    boundary = config["boundary_policy"]
    if boundary["mode"]=="periodic" and (boundary["pad_e_cells"] or boundary["pad_n_cells"] or
        boundary["detrend"]!="none" or boundary["taper"]!="none"):
        fail("grid.periodic_boundary_policy")
    data = _array(values,nx,ny,"grid.values")
    if len(data) != ny:
        fail("grid.shape")
    np,_ = engines()
    for origin,spacing,count in ((config["origin_e_m"],config["spacing_e_m"],nx),
                                 (config["origin_n_m"],config["spacing_n_m"],ny)):
        with np.errstate(over="ignore",invalid="ignore"):
            axis = origin+np.arange(count)*spacing
            steps = np.diff(axis)
        if not np.isfinite(axis).all() or np.any(steps<=0) or np.any(np.abs(steps-spacing)>64*EPSILON*spacing):
            fail("grid.float64_geometry","metadata_ineligible","predict")
    if masks is not None:
        if type(masks) is not list or len(masks) != nx*ny or any(
            type(flags) is not list or len(flags)>16 or any(type(f) is not str or f not in MASK_ORDER for f in flags)
            or flags != [f for f in MASK_ORDER if f in flags] for flags in masks):
            fail("grid.masks")
    return data,config


def _real_inverse(coefficients):
    np,_ = engines()
    result = np.fft.ifft2(coefficients)
    if not np.isfinite(result).all() or np.max(np.abs(result.imag)) > 1024*EPSILON*max(1.,float(np.max(np.abs(result.real)))):
        fail("grid.inverse_real_domain","metadata_ineligible","spectrum")
    return result.real


def continue_plane(values, config, *, datum, source_free, masks=None):
    """FFT height transfer on an explicitly complete, source-free declared plane.

    source_free=True is a caller-supplied physical assertion, not independent
    provider review or an inference from successful FFT. Unknown field domains
    cannot be admitted by this operator alone.
    """
    data,config = _grid_array(values,config,masks)
    if type(datum) is not str or datum != config["datum"] or source_free is not True:
        fail("continuation.datum_or_source_free","metadata_ineligible","predict")
    if masks is not None and any(masks):
        fail("continuation.holes","metadata_ineligible","predict")
    delta = config["continuation_delta_m"]
    if delta is None:
        fail("continuation.positive_displacement","metadata_ineligible","predict")
    target_height = config["plane_upward_m"]+delta
    if not math.isfinite(target_height) or target_height <= config["plane_upward_m"]:
        fail("continuation.height_float64","metadata_ineligible","predict")
    boundary = config["boundary_policy"]
    pe,pn = boundary["pad_e_cells"],boundary["pad_n_cells"]
    nx,ny = config["nx"],config["ny"]
    if (nx+2*pe)*(ny+2*pn)>65536 or 2*pe>nx or 2*pn>ny:
        fail("continuation.padding","resource_refused","predict")
    np,_ = engines()
    with np.errstate(over="ignore",invalid="ignore"):
        mean = float(np.mean(data)) if boundary["detrend"]=="remove_mean" else 0.
        work = data-mean
    if not np.isfinite(work).all():
        fail("continuation.detrend_range","metadata_ineligible","predict")
    if boundary["taper"]=="hann":
        work = work*np.hanning(ny)[:,None]*np.hanning(nx)[None,:]
    if pe or pn:
        work = np.pad(work,((pn,pn),(pe,pe)),mode="constant" if boundary["mode"]=="zero_pad" else "reflect")
    ke = 2*np.pi*np.fft.fftfreq(work.shape[1],config["spacing_e_m"])
    kn = 2*np.pi*np.fft.fftfreq(work.shape[0],config["spacing_n_m"])
    transfer = np.exp(-np.hypot(kn[:,None],ke[None,:])*delta)
    transformed = _real_inverse(np.fft.fft2(work)*transfer)
    output = transformed[pn:pn+ny,pe:pe+nx]+mean
    if not np.isfinite(output).all():
        fail("continuation.output_range","metadata_ineligible","predict")
    return dict(values=output,transfer=transfer,east_axis_rad_per_m=ke,north_axis_rad_per_m=kn,
        plane_upward_m=target_height,boundary_policy=dict(boundary),mean_removed_nT=mean,
        domain_interpretation="declared_complete_source_free_plane_not_provider_authentication")


def power_spectrum(values, grid_config, spectrum_config, masks=None):
    """Full two-sided window-normalized nT^2 bin power on the declared rectangle."""
    data,grid = _grid_array(values,grid_config,masks)
    config = validate_named("SpectrumConfig",spectrum_config)
    rectangle = config["rectangle"]
    e,n,nx,ny = (rectangle[k] for k in ("e_start","n_start","nx","ny"))
    if e+nx>grid["nx"] or n+ny>grid["ny"]:
        fail("spectrum.rectangle")
    if masks is not None and any(masks[j*grid["nx"]+i] for j in range(n,n+ny) for i in range(e,e+nx)):
        fail("spectrum.rectangle_holes","metadata_ineligible","spectrum")
    np,_ = engines()
    crop = data[n:n+ny,e:e+nx]
    window = np.ones((ny,nx)) if config["window"]=="rectangular" else np.hanning(ny)[:,None]*np.hanning(nx)[None,:]
    c2 = float(np.mean(window*window))
    if c2<=0:
        fail("spectrum.degenerate_window","metadata_ineligible","spectrum")
    with np.errstate(over="ignore",invalid="ignore"):
        mean = float(np.mean(crop))
        work = window*(crop-mean)
    if not np.isfinite(work).all():
        fail("spectrum.demean_range","metadata_ineligible","spectrum")
    coefficients = np.fft.fft2(work)
    with np.errstate(over="ignore",invalid="ignore"):
        power = np.abs(coefficients)**2/(nx*ny)**2/c2
        parseval = float(np.mean(work*work)/c2)
    with np.errstate(over="ignore",invalid="ignore"):
        power_sum = float(power.sum())
    if not np.isfinite(power).all() or not math.isfinite(parseval) or not math.isfinite(power_sum):
        fail("spectrum.power_range","metadata_ineligible","spectrum")
    fe,fn = np.fft.fftfreq(nx,grid["spacing_e_m"]),np.fft.fftfreq(ny,grid["spacing_n_m"])
    azimuth = np.degrees(np.arctan2(fe[None,:],fn[:,None]))%360
    nonzero = (fe[None,:]!=0)|(fn[:,None]!=0)
    sectors = []
    for sector in config["direction_sectors"]:
        selected = nonzero & (azimuth>=sector["azimuth_start_deg"]) & (azimuth<sector["azimuth_end_deg"])
        sectors.append(dict(sector_id=sector["sector_id"],bin_count=int(selected.sum()),power_nT2=float(power[selected].sum())))
    return dict(config=config,power=power,east_axis=fe*(2*np.pi if config["axis_unit"]=="rad_per_m" else 1),
        north_axis=fn*(2*np.pi if config["axis_unit"]=="rad_per_m" else 1),window_mean_square=c2,
        mean_removed_nT=mean,parseval_sum_nT2=power_sum,windowed_mean_square_nT2=parseval,sectors=sectors)


def microlevel_diagnostic(values, grid_config, parameters, *, acquisition_azimuths_deg, masks=None):
    """Conditional directional filter; retains explicit geological-loss semantics."""
    data,grid = _grid_array(values,grid_config,masks)
    parameters = validate_named("MicrolevelParameters",parameters)
    azimuths = _array(acquisition_azimuths_deg,maximum=32,field="microlevel.acquisition_azimuths")
    np,_ = engines()
    if np.any((azimuths<0)|(azimuths>=360)):
        fail("microlevel.acquisition_degrees")
    # Reversed flight acquisition is the same undirected line orientation.
    difference = np.abs((azimuths-parameters["flight_azimuth_deg"]+90)%180-90)
    if np.any(difference>parameters["max_azimuth_spread_deg"]):
        fail("microlevel.nonparallel_acquisition","metadata_ineligible","spectrum")
    spec = parameters["spectrum_policy"]
    spectrum = power_spectrum(data,grid,spec,masks)
    rect = spec["rectangle"]
    e,n,nx,ny = (rect[k] for k in ("e_start","n_start","nx","ny"))
    crop = data[n:n+ny,e:e+nx]
    ke = 2*np.pi*np.fft.fftfreq(nx,grid["spacing_e_m"])
    kn = 2*np.pi*np.fft.fftfreq(ny,grid["spacing_n_m"])
    angle = math.radians(parameters["flight_azimuth_deg"])
    parallel = ke[None,:]*math.sin(angle)+kn[:,None]*math.cos(angle)
    perpendicular = ke[None,:]*math.cos(angle)-kn[:,None]*math.sin(angle)
    # Ratio form avoids overflow in k^8 and preserves the exact prescribed H.
    kp,kc,ka = np.abs(perpendicular),parameters["kc_rad_per_m"],parameters["ka_rad_per_m"]
    with np.errstate(over="ignore",divide="ignore",invalid="ignore",under="ignore"):
        ratio = kp/kc
        high = np.where(ratio<=1,ratio**4/np.sqrt(1+ratio**8),1/np.sqrt(1+(kc/kp)**8))
        transfer = high*np.exp(-(parallel/ka)**2)
    transfer[0,0] = 0.
    if not np.isfinite(transfer).all():
        fail("microlevel.transfer_range","metadata_ineligible","spectrum")
    removed = _real_inverse(np.fft.fft2(crop)*transfer)
    retained = crop-removed
    local_grid = dict(grid,nx=nx,ny=ny)
    from copy import deepcopy
    local_spec = deepcopy(spec)
    local_spec["rectangle"] = dict(e_start=0,n_start=0,nx=nx,ny=ny)
    removed_power = power_spectrum(removed,local_grid,local_spec)["parseval_sum_nT2"]
    retained_power = power_spectrum(retained,local_grid,local_spec)["parseval_sum_nT2"]
    cap = parameters["amplitude_cap_nT"]
    clipped = None if cap is None else np.clip(removed,-cap,cap)
    clipped_spectrum = None if clipped is None else power_spectrum(clipped,local_grid,local_spec)
    return dict(parameters=parameters,transfer=transfer,removed=removed,retained=retained,
        removed_power_nT2=removed_power,retained_power_nT2=retained_power,
        clipped_removed=clipped,clipped_spectrum=clipped_spectrum,geological_preservation_claim=False,
        source_spectrum=spectrum)
