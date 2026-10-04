"""Local M03 numerical operators. No IGRF admission, network, online dispatch or inversion."""
from __future__ import annotations

from hashlib import sha256
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
import math
from pathlib import Path
import platform
import magnetic_line_contract as contract

from magnetic_line_contract import _type, digest, fail, validate_named


ENGINE_PINS = {"harmonica": "0.7.0", "verde": "1.9.0", "numpy": "2.2.6",
               "scipy": "1.15.2", "scikit-learn": "1.9.1", "threadpoolctl": "3.7.0", "xarray": "2026.9.0"}
SOURCE_PINS = {
    "harmonica._equivalent_sources.cartesian": "f62f2b5ad5a0ece1b66482a98d700f5093f8f5e18fd05062ca24e72437bea44f",
    "verde.base.least_squares": "a4eb01f891016a50be2451432842e0449ac924ec2fdfef8ecb182cc1f36ec090",
}
EPSILON = 2.220446049250313e-16

# Exhaustive reviewed output tables, independent of the unchanged intake tables.
# This is a literal schema, not a run-time parser of prose or a permissive dict.
E, L, I = contract.E, contract.L, contract.I
V = E("pass", "fail", "unresolved", "ineligible", "nonconverged", "cancelled", "resource_refused")
A = "ArrayDescriptor"
RESULT_TABLES = {
    "Result": dict(schema=contract.literal("magnetic-result/1"), run_id="ID",
        lane=E("local_synthetic", "local_user", "field_provider_product", "future_online_owned"),
        input="InputIdentity", request="RequestIdentity", environment="Environment", inventory="Inventory",
        channels=L("Channel",1,8), geometry="GeometryResult", crossovers=L("Crossover",0,4096),
        leveling="?LevelingResult", partitions="PartitionResult", fit="FitResult", grid=L("GridResult",1,3),
        spectrum="?SpectrumResult", evaluation="EvaluationResult", rights="Rights", artifacts=L("Member",0,64), verdict="Verdict"),
    "InputIdentity": dict(dataset_sha256="Hash",csv_sha256="Hash",csv_bytes=I(1,16777216),sidecar_sha256="Hash",
        sidecar_bytes=I(1,2097152),source_kind=E("field_acquisition","original_synthetic_acquisition","provider_grid","provider_image"),
        row_ids=("rows","ID"),auxiliary_identities=L("AuxIdentity",0,16)),
    "RequestIdentity": dict(bytes_sha256="Hash",bytes=I(1,2097152),canonical_request="Request",geometry_manifest_sha256="Hash"),
    "Environment": dict(python_revision="Text",os_revision="Text",cpu_identity="Text",engine_versions=L("EnginePin",1,64),
        loaded_modules=L("FilePin",1,256),native_modules=L("FilePin",0,256),threads=I(1,1),source_revision="Hash",environment_receipt_sha256="Hash"),
    "EnginePin": dict(name="Text",version="Text",distribution_sha256="Hash",license_evidence_sha256="Hash"),
    "FilePin": dict(module_name="Text",sha256="Hash",bytes=I(1,2147483647)),
    "Inventory": dict(original_rows=I(1,400),retained_ids=L("ID",0,400),invalid_ids=L("ID",0,400),excluded_ids=L("ID",0,400),
        reasons=L("RowMask",0,400),flag_counts=L("MaskCount",0,16)),
    "RowMask": dict(row_id="ID",reasons=L("Mask",1,16),disposition=E("retained","invalid","excluded")),
    "MaskCount": dict(reason="Mask",count=I(0,400)),
    A: dict(shape=L(I(1,65536),1,2),dtype=E("float64","int32","id","mask"),
        unit=E("nT","nT^2","nT*m","nT^-2","m","1_per_m","cycles_per_m","rad_per_m","s","degree","dimensionless","identity"),
        ordered_ids_sha256="Hash",values=L("ArrayScalar",1,65536),values_sha256="Hash",masks=L(L("Mask",0,16),1,65536),mask_sha256="Hash"),
    "Channel": dict(channel_id="ID",kind=E("scalar_total_intensity","scalar_total_field_anomaly"),
        role=E("original","derived","diagnostic_removed","diagnostic_retained"),data=A,state=L("StateRecord",0,64),
        parent_sha256="?Hash",reference_receipt_sha256="?Hash"),
    "GeometryResult": dict(row_ids=("rows","ID"),easting=A,northing=A,upward=A,segments=L("Segment",0,399),
        line_statistics=L("LineStatistics",1,128),coverage_sha256="Hash"),
    "Segment": dict(segment_id="ID",line_id="ID",sensor_id="ID",start_row_id="ID",end_row_id="ID",length_m="Pos",valid=contract.literal(True)),
    "LineStatistics": dict(line_id="ID",sensor_id="ID",spacing_min_m="?Nonneg",spacing_median_m="?Nonneg",spacing_max_m="?Nonneg",
        local_perpendicular_spacing_m="?Nonneg",azimuth_deg="?F64",reversals=I(0,399),gap_count=I(0,399),row_count=I(1,400)),
    "Crossover": dict(crossover_id="ID",flight_segment_id="ID",tie_segment_id="ID",a="?F64",b="?F64",easting_m="?F64",northing_m="?F64",
        flight_minus_tie_nT="?F64",height_difference_m="?F64",time_separation_s="?Nonneg",difference_variance_nT2="?Nonneg",
        disposition=E("admitted","rejected"),reasons=L("CrossoverReason",0,16),shared_endpoint_group_id="?ID",
        constraint_representative="?ID",tolerance="IntersectionTolerance"),
    "IntersectionTolerance": dict(coordinate_m="Pos",determinant_m2="?Pos",sine_dimensionless="?Pos",parameter_dimensionless="?Pos",matrix_residual_m="?Nonneg"),
    "LevelingResult": dict(offsets=L("OffsetValue",1,32),components=L("LevelComponent",1,32),before_residuals=A,after_residuals=A,
        uncalibrated_line_ids=L("ID",0,32),scope=contract.literal("training_only"),gauge_policy=contract.literal("lexicographic_first_tie_per_component")),
    "LevelComponent": dict(component_id="ID",line_ids=L("ID",1,32),gauge_line_id="ID",rank=I(0,32),singular_values=L("Nonneg",1,32),
        condition="?Pos",absolute_datum=contract.literal(False)),
    "PartitionResult": dict(config="SplitConfig",original_row_ids=("rows","ID"),outer_training_ids=L("ID",1,400),outer_validation_ids=L("ID",1,400),
        tie_buffer_excluded_ids=L("ID",0,400),inner=L("FoldInventory",3,3),evaluation_count=I(0,1),geometry_only_coverage="Coverage"),
    "FoldInventory": dict(fold_id="ID",training_ids=L("ID",1,400),validation_ids=L("ID",1,400),tie_buffer_excluded_ids=L("ID",0,400),
        calibration_receipts=L("Hash",0,16),source_block_map=L("BlockMember",1,400),geometry_only_coverage="Coverage"),
    "Coverage": dict(eligible_count=I(0,400),total_count=I(1,400),fraction="Nonneg",unsupported_ids=L("ID",0,400)),
    "FitResult": dict(method=contract.literal("harmonica_equivalent_sources"),candidates=L("CandidateResult",8,8),selected_candidate_id="ID",
        production_fit_count=I(1,26),source_positions=A,source_coefficients=A,source_block_map=L("BlockMember",1,400),column_scales=A,
        objective="Objective",weights_policy=E("unweighted","admitted_inverse_variance"),damping_unit=E("dimensionless","nT^-2"),
        comparator="ComparatorResult",residuals=A,numerical_status=E("converged","nonconverged")),
    "BlockMember": dict(row_id="ID",block_e=I(-2147483648,2147483647),block_n=I(-2147483648,2147483647),source_id="ID"),
    "CandidateResult": dict(candidate_id="ID",depth_m="Pos",damping="Pos",damping_unit=E("dimensionless","nT^-2"),folds=L("FoldScore",3,3),
        mean_rmse_nT="?Nonneg",status=E("eligible","ineligible","nonconverged")),
    "FoldScore": dict(fold_id="ID",coverage="Coverage",rmse_nT="?Nonneg",objective="?Objective",verdict=V,reason="?Text"),
    "Objective": dict(data_term="Nonneg",regularization_term="Nonneg",total="Nonneg",unit=E("nT^2","dimensionless"),
        weight_multiplier="Pos",damping="Pos",damping_unit=E("dimensionless","nT^-2"),condition="?Pos",rank=I(0,256)),
    "ComparatorResult": dict(method=contract.literal("scipy_linear_nd"),verdict=V,reason="?Text",residuals="?ArrayDescriptor",metrics="?Metrics"),
    "GridResult": dict(grid_id="ID",config="GridConfig",quantity=contract.literal("scalar_total_field_anomaly"),easting_axis=A,northing_axis=A,
        values=A,support_flags=L("CellFlags",0,16384),role=E("fitted_plane","continued_plane","microlevel_diagnostic")),
    "CellFlags": dict(cell_index=I(0,16383),reasons=L("Mask",1,16),disposition=E("retained","excluded")),
    "SpectrumResult": dict(config="SpectrumConfig",power=A,east_axis=A,north_axis=A,window_mean_square="Pos",mean_removed_nT="F64",
        parseval_sum_nT2="Nonneg",sectors=L("SectorPower",0,16),microlevel="?MicrolevelResult"),
    "SectorPower": dict(sector_id="ID",bin_count=I(0,16384),power_nT2="Nonneg"),
    "MicrolevelResult": dict(parameters="MicrolevelParameters",transfer=A,removed=A,retained=A,removed_power_nT2="Nonneg",
        retained_power_nT2="Nonneg",clipped_removed="?ArrayDescriptor",geological_preservation_claim=contract.literal(False)),
    "EvaluationResult": dict(interpretation=E("synthetic_truth","conditional_provider_product","independently_sealed_processing","user_prediction_only"),
        outer="Metrics",per_line=L("LineMetrics",1,32),provider_comparison="ProviderComparison",field_acceptance=E("unresolved","ineligible"),
        synthetic_acceptance=V,reference_approximation="Text",maximum_direction_spread_deg="Nonneg"),
    "Metrics": dict(count=I(0,400),coverage="Coverage",bias_nT="?F64",rmse_nT="?Nonneg",mae_nT="?Nonneg",
        median_absolute_nT="?Nonneg",max_absolute_nT="?Nonneg",standardized_rmse="?Nonneg",uncertainty_meaning="?Uncertainty"),
    "LineMetrics": dict(line_id="ID",sensor_id="ID",metrics="Metrics"),
    "ProviderComparison": dict(verdict=E("unresolved","ineligible"),numeric_grid_sha256="?Hash",metadata_receipt_sha256="?Hash",
        matched_cells=I(0,16384),difference_rmse_nT="?Nonneg",reason="Text"),
    "Member": dict(relative_path="Text",kind=E("original","metadata","request","result_array","diagnostic","replay_recipe","receipt"),
        permission=E(*contract.PERMISSIONS),included="Bool",sha256="?Hash",bytes=("nullable",I(0,67108864)),reason="?Text"),
    "Verdict": dict(overall=V,gates=L("GateVerdict",1,26),reasons=L("Text",0,64),error="?Error",numerical_success="Bool"),
    "GateVerdict": dict(requirement_id=E(*(f"M03-{i:03d}" for i in range(1,27))),verdict=V,evidence_sha256="?Hash",reason="?Text"),
    "Error": dict(code=E("schema_invalid","metadata_ineligible","rights_unresolved","rights_denied","resource_refused","unsupported_operation",
        "numerical_failure","method_unadmitted","cancelled","interrupted","custody_mismatch","overwrite_refused"),
        stage=E("parse","eligibility","partition","correction","crossover","fit","predict","spectrum","export","worker","recovery"),
        field="?Text",observed="?EnumOrScalar",limit="?EnumOrScalar",reason="Text",local_recipe="?Text",attempt_id="?ID"),
}


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


def _load_profile_lines(csv_original, sidecar_original, request_original, *, local_profile=None):
    """Explicit local extension; ordinary byte/key/rights checks remain exact."""
    if local_profile is None:
        return contract.load_lines(csv_original,sidecar_original,request_original)
    from magnetic_line_validation import validate_profile_named
    if type(request_original) is not bytes or len(request_original)+len(sidecar_original)>2097152:
        fail("profile.metadata_bytes","resource_refused")
    intake = contract.load_lines(csv_original,sidecar_original)
    request = validate_profile_named("Request",contract.strict_json(request_original),len(intake["rows"]),local_profile=local_profile)
    if request["dataset_version_sha256"]!=intake["dataset_sha256"] or request["channel_sha256"]!=intake["channel_sha256"]:
        fail("Request.input_identity","custody_mismatch")
    intake["request"],intake["request_bytes"] = request,request_original
    intake["eligibility_reasons"] = contract.validate_lines(intake["rows"],intake["metadata"],request)
    return intake


def apply_corrections(csv_original, sidecar_original, request_original, training_ids=None, *, defer_microlevel=False, local_profile=None):
    """Replay exact originals into immutable DAG channels; not a serialized Result.

    Authored auxiliary byte/clock custody is implemented. Field independent
    auxiliary/evaluator review is explicitly refused, not inferred from hashes.
    Unsupported lag positions retain original descriptive coordinates with a
    mask and null value; they cannot enter physical reference or fitting.
    """
    from copy import deepcopy
    from magnetic_line_contract import channel_identity
    intake = _load_profile_lines(csv_original,sidecar_original,request_original,local_profile=local_profile)
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
            manifest = make_partitions(rows,request,local_profile=local_profile)
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


def local_source_preallocation(rows, request, *, local_profile=None):
    """Geometry-only buffer accounting; not an actual RSS or cancellation proof."""
    from magnetic_line_validation import make_partitions, validate_profile_named, geometry_manifest
    if any(r["magnetic_nT"] is not None or r["uncertainty_nT"] is not None for r in rows):
        fail("profile.magnetic_null_required", "custody_mismatch", "partition")
    request = validate_profile_named("Request", request, len(rows), local_profile=local_profile)
    sealed = make_partitions(rows, request, local_profile=local_profile)
    counts = [len(sealed["outer_source_positions"])] + [len(f["source_positions"]) for f in sealed["inner"]]
    n, m = len(rows), max(counts)
    cells = request["grid"]["nx"]*request["grid"]["ny"]
    # Conservative simultaneous dense Python/native buffer allowance, including
    # XYZ pair displacements, distances/J/scaled/weighted, augmented copies,
    # Gram/SVD/ridge work and both grid query/prediction planes. Imports, JIT,
    # allocators and decoder overhead are NOT established by this arithmetic.
    dense = 8*(16*n*m + 12*m*m + 16*cells + 8*(n+m))
    return dict(profile=local_profile or "m03-bounded-256/1", source_counts=counts,
        geometry_manifest_sha256=digest(geometry_manifest(rows)), partitions_sha256=digest(sealed),
        peak_dense_bytes_bound=dense, source_limit=320 if local_profile else 256,
        values_generated=False, vps_admitted=False, measured_resource_verdict="unresolved")


def _local_resource_guard(job_handle=None):
    """Local study only: verify actual current job ceilings before allocation.

    The controller must separately measure cold lifetime/peak and cancellation;
    this check is containment, not completion/admission evidence. POSIX and
    uncontained execution refuse; no host identity is inferred.
    """
    import ctypes
    if platform.system()!="Windows" or type(job_handle) is not int or job_handle<=0:
        fail("profile.windows_job_required","resource_refused","fit")
    class Basic(ctypes.Structure):
        _fields_ = [("process_cpu",ctypes.c_longlong),("job_cpu",ctypes.c_longlong),("flags",ctypes.c_uint32),
            ("min_working",ctypes.c_size_t),("max_working",ctypes.c_size_t),("active",ctypes.c_uint32),
            ("affinity",ctypes.c_size_t),("priority",ctypes.c_uint32),("scheduling",ctypes.c_uint32)]
    class IO(ctypes.Structure):
        _fields_ = [("counter"+str(i),ctypes.c_ulonglong) for i in range(6)]
    class Limits(ctypes.Structure):
        _fields_ = [("basic",Basic),("io",IO),("process_memory",ctypes.c_size_t),("job_memory",ctypes.c_size_t),
            ("peak_process_memory",ctypes.c_size_t),("peak_job_memory",ctypes.c_size_t)]
    api = ctypes.WinDLL("kernel32",use_last_error=True)
    api.QueryInformationJobObject.argtypes = [ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p]
    api.QueryInformationJobObject.restype = ctypes.c_int
    api.GetCurrentProcess.restype = ctypes.c_void_p
    api.IsProcessInJob.argtypes = [ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p]
    api.IsProcessInJob.restype = ctypes.c_int
    member = ctypes.c_int()
    limits = Limits()
    membership = api.IsProcessInJob(api.GetCurrentProcess(),job_handle,ctypes.byref(member))
    query = api.QueryInformationJobObject(job_handle,9,ctypes.byref(limits),ctypes.sizeof(limits),None)
    if not membership or not member.value or not query or limits.basic.flags & (0x2000|0x200|0x8|0x4)!=(0x2000|0x200|0x8|0x4) or \
        limits.basic.active!=1 or limits.job_memory>536870912 or limits.job_memory==0 or limits.basic.job_cpu>600000000 or limits.basic.job_cpu<=0:
        observation = f"member={member.value};query={query};flags={limits.basic.flags};active={limits.basic.active};job_bytes={limits.job_memory};cpu_100ns={limits.basic.job_cpu}"
        fail("profile.actual_resource_and_cancel_receipt_required","resource_refused","fit",observed=observation)


def fit_equivalent(rows, config, depth_m, damping, *, local_profile=None, local_job_handle=None):
    """Pinned real harmonic fit; explicit training-only blocks and raw weights."""
    from magnetic_line_validation import kernel_column_scales, source_blocks, validate_geometry_rows, validate_profile_named
    validate_geometry_rows(rows)
    config = validate_profile_named("EquivalentSourcesConfig", config, local_profile=local_profile)
    if local_profile is not None:
        # Numerical entry requires an ACTUAL bounded Windows Job, not a caller
        # boolean, self-reported trace or a forged JSON provenance flag.
        _local_resource_guard(local_job_handle)
    depth = _type(depth_m, "Pos", "fit.depth_m", 1)
    damping = _type(damping, "Pos", "fit.damping", 1)
    if depth not in config["depth_candidates_m"] or damping not in config["damping_candidates"]:
        fail("fit.frozen_candidate")
    basis = source_blocks(rows, config["source_geometry"], depth, local_profile=local_profile)
    np, hm = engines()
    from threadpoolctl import threadpool_limits
    coordinates = _array([[r[k] for k in ("easting_m", "northing_m", "upward_m")] for r in rows], 3)
    sources = _array([[s[k] for k in ("easting_m", "northing_m", "upward_m")] for s in basis["sources"]], 3, 320 if local_profile else 256)
    values = _array([r["magnetic_nT"] for r in rows])
    distance = np.linalg.norm(coordinates[:, None, :]-sources[None, :, :], axis=2)
    if np.any(distance == 0) or not np.isfinite(distance).all():
        fail("fit.distance", "metadata_ineligible", "fit")
    jacobian = 1/distance
    scales = np.asarray(kernel_column_scales(jacobian.tolist(),local_profile=local_profile))
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


def blocked_fit(rows, request, sealed, *, original_inputs=None, local_profile=None, local_job_handle=None):
    """Frozen8x3 fits; corrected channels require exact independent input replay.

    No supplied parent hash can substitute for original bytes. Training-only
    leveling is recomputed per inner/final partition, never once on all rows.
    Existing uncorrected S1 recipe/outputs/candidates remain unchanged.
    """
    from magnetic_line_contract import channel_identity
    from magnetic_line_validation import make_partitions,validate_profile_named
    np, _ = engines()
    request = validate_profile_named("Request", request, len(rows),local_profile=local_profile)
    if sealed != make_partitions(rows, request,local_profile=local_profile):
        fail("partition.custody", "custody_mismatch", "fit")
    processing_lineage = None
    fold_rows = None
    if original_inputs is not None:
        if type(original_inputs) is not tuple or len(original_inputs)!=3 or any(type(v) is not bytes for v in original_inputs):
            fail("fit.original_input_bytes")
        intake = _load_profile_lines(*original_inputs,local_profile=local_profile)
        if intake["request"] != request:
            fail("fit.original_request","custody_mismatch","fit")
        final_run = apply_corrections(*original_inputs,training_ids=sealed["outer_training_ids"],defer_microlevel=True,local_profile=local_profile)
        if final_run["rows"] != rows or final_run["kind"]!="scalar_total_field_anomaly":
            fail("fit.derived_channel_replay","custody_mismatch","fit")
        scopes = [fold["training_ids"] for fold in sealed["inner"]]+[sealed["outer_training_ids"]]
        runs = [apply_corrections(*original_inputs,training_ids=scope,defer_microlevel=True,local_profile=local_profile) for scope in scopes[:3]]+[final_run]
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
                fitted = fit_equivalent(train, config, depth, damping,local_profile=local_profile,local_job_handle=local_job_handle)
                query = [[r[k] for k in ("easting_m", "northing_m", "upward_m")] for r in validation]
                # Only this fold's validation values enter its score.
                predicted = predict_equivalent(fitted, query)
                observed = _array([r["magnetic_nT"] for r in validation])
                rmse = float(np.sqrt(np.mean((observed-predicted)**2)))
                scores.append(dict(fold_id=fold["fold_id"], rmse_nT=rmse, objective=fitted["objective"],
                                   training_sha256=digest(train), source_map_sha256=digest(fitted["source_block_map"]),
                                   coverage=fold["geometry_only_coverage"], scored_count=len(validation)))
            candidates.append(dict(depth_m=depth, damping=damping, mean_rmse_nT=math.fsum(s["rmse_nT"] for s in scores)/3,
                                   folds=scores))
    # Predeclared numerical1e-9 nT tie, never an error model.
    best_score = min(c["mean_rmse_nT"] for c in candidates)
    selected = max((c for c in candidates if abs(c["mean_rmse_nT"]-best_score) <= 1e-9),
                   key=lambda c: (c["damping"], c["depth_m"]))
    train = [by_id[rid] for rid in sealed["outer_training_ids"]]
    final = fit_equivalent(train, config, selected["depth_m"], selected["damping"],local_profile=local_profile,local_job_handle=local_job_handle)
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


def fit_grid(csv_original, sidecar_original, request_original, *, local_profile=None, local_job_handle=None):
    """Local correction/blocked fit/height/support orchestration, NOT Result JSON.

    No field-source approval is inferred. Synthetic quality failure is retained
    alongside actual computed diagnostics. A future complete serializer/export
    has additional exact contracts; this internal mapping is not that result.
    """
    from magnetic_line_contract import MagneticContractError
    from magnetic_line_validation import make_partitions,preflight_geometry
    original = (csv_original,sidecar_original,request_original)
    intake = _load_profile_lines(*original,local_profile=local_profile)
    meta,request = intake["metadata"],intake["request"]
    if request is None or meta["rights"]["decision"]!="allowed" or meta["rights"]["private_processing"]!="allowed":
        fail("fit.input_or_rights","metadata_ineligible","fit")
    unresolved = set(intake["eligibility_reasons"])-{"uncertainty_unresolved"}
    if meta["source_kind"]=="original_synthetic_acquisition" and meta["reference"] is not None and meta["reference"]["kind"]=="authored_constant":
        authored = meta["reference"]
        validate_reference(authored,meta["source_kind"],len(intake["rows"]))
        if authored["coordinates_sha256"]!=reference_coordinates_sha256(intake["rows"],meta["coordinates"]["vertical_datum"]) or \
            authored["evaluator"]["source_rights_evidence_sha256"]!=digest(meta["rights"]) or \
            authored["receipt_sha256"]!=digest({k:value for k,value in authored.items() if k!="receipt_sha256"}):
            fail("fit.authored_reference_identity","custody_mismatch","fit")
        # This is conditional authored-control physics, NOT independent IGRF or
        # field review. The original intake diagnostic is retained unchanged.
        unresolved.discard("reference_independent_review_unverified")
    if meta["source_kind"]!="original_synthetic_acquisition" or unresolved:
        fail("fit.physical_metadata_or_independent_source_review","metadata_ineligible","fit")
    aligned = _partition_geometry(intake)
    sealed = make_partitions(aligned,request,local_profile=local_profile)
    counts = preflight_geometry(aligned,meta,request,local_profile=local_profile)
    processed = apply_corrections(*original,training_ids=sealed["outer_training_ids"],defer_microlevel=True,local_profile=local_profile)
    if processed["kind"]!="scalar_total_field_anomaly":
        fail("fit.reference_subtracted_anomaly_required","metadata_ineligible","fit")
    fitted = blocked_fit(processed["rows"],request,sealed,original_inputs=original,local_profile=local_profile,local_job_handle=local_job_handle)
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


CROSSOVER_REASONS = ("degenerate_segment","parallel_or_collinear","ill_conditioned","parameter_outside_segment",
    "matrix_residual_exceeded","gap","missing_value","missing_height","height_mismatch","unsupported_time",
    "sensor_mismatch","channel_state_mismatch","duplicate_physical_constraint","uncalibrated_line","spatial_buffer","outer_sealed")


def _result_type(value, spec, field, n, local_profile=None):
    if type(spec) is str and spec.startswith("?"):
        return None if value is None else _result_type(value,spec[1:],field,n,local_profile)
    if type(spec) is tuple and spec[0] in ("list","rows","nullable"):
        if spec[0]=="nullable":
            return None if value is None else _result_type(value,spec[1],field,n,local_profile)
        lo,hi = (n,n) if spec[0]=="rows" else spec[2:]
        if type(value) is not list or not lo<=len(value)<=hi:
            fail(field)
        return [_result_type(v,spec[1],f"{field}[{i}]",n,local_profile) for i,v in enumerate(value)]
    if type(spec) is str and spec in RESULT_TABLES:
        table = RESULT_TABLES[spec]
        if local_profile is not None:
            if type(local_profile) is not str or local_profile!="m03-local-320/1":
                fail("result.profile","unsupported_operation")
            if spec=="Result":
                table=dict(table,schema=contract.literal("magnetic-local-study-result/1"))
            elif spec=="Objective":
                table=dict(table,rank=I(0,320))
        if type(value) is not dict or set(value)!=set(table):
            fail(field)
        return {k:_result_type(value[k],t,field+"."+k,n,local_profile) for k,t in table.items()}
    if spec=="Request" and local_profile is not None:
        from magnetic_line_validation import validate_profile_named
        return validate_profile_named("Request",value,n,local_profile=local_profile)
    if spec=="Bool":
        if type(value) is not bool:
            fail(field)
        return value
    if spec=="Mask":
        return _type(value,E(*MASK_ORDER),field,n)
    if spec=="CrossoverReason":
        return _type(value,E(*CROSSOVER_REASONS),field,n)
    if spec in ("ArrayScalar","EnumOrScalar"):
        if value is None and spec=="ArrayScalar":
            return None
        if type(value) is bool and spec=="EnumOrScalar":
            return value
        if type(value) is int and spec=="EnumOrScalar":
            return _type(value,I(-2147483648,2147483647),field,n)
        if type(value) in (int,float):
            return _type(value,"F64",field,n)
        return _type(value,"Text",field,n)
    return _type(value,spec,field,n)


def _parse_bounded_json(raw, limit):
    import json
    if type(raw) is not bytes or not 1<=len(raw)<=limit:
        fail("result.bytes","resource_refused")
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        fail("result.utf8")
    scan = contract._Scanner(text)
    scan.value()
    scan.space()
    if scan.i!=len(text):
        fail("result.trailing")
    try:
        return json.loads(text)
    except (ValueError,RecursionError):
        fail("result.json")


def array_descriptor(values, ordered_ids, masks, shape, unit, dtype="float64"):
    descriptor = dict(shape=shape,dtype=dtype,unit=unit,ordered_ids_sha256=digest(ordered_ids),
        values=values,values_sha256=digest(values),masks=masks,mask_sha256=digest(masks))
    validate_array_descriptor(descriptor,ordered_ids)
    return descriptor


def validate_array_descriptor(d, ordered_ids=None, *, shape=None, unit=None):
    _result_type(d,A,"result.array",1)
    if len(d["values"])!=math.prod(d["shape"]) or len(d["masks"])!=len(d["values"]):
        fail("result.array.shape")
    if shape is not None and (d["shape"]!=shape or d["dtype"]!="float64"):
        fail("result.array.physical_shape")
    if unit is not None and d["unit"]!=unit:
        fail("result.array.physical_unit")
    if ordered_ids is not None and (len(ordered_ids)!=len(d["values"]) or digest(ordered_ids)!=d["ordered_ids_sha256"]):
        fail("result.array.ordered_identity","custody_mismatch")
    if digest(d["values"])!=d["values_sha256"] or digest(d["masks"])!=d["mask_sha256"]:
        fail("result.array.hash","custody_mismatch")
    for v,flags in zip(d["values"],d["masks"]):
        if flags!=[m for m in MASK_ORDER if m in flags] or (v is None and not flags):
            fail("result.array.mask")
        if v is not None:
            spec = {"float64":"F64","int32":I(-2147483648,2147483647),"id":"ID","mask":E(*MASK_ORDER)}[d["dtype"]]
            _type(v,spec,"result.array.value",1)
    return d


def _coverage_check(v):
    if v["eligible_count"]>v["total_count"] or v["fraction"]!=v["eligible_count"]/v["total_count"] or \
        len(v["unsupported_ids"])!=v["total_count"]-v["eligible_count"] or len(set(v["unsupported_ids"]))!=len(v["unsupported_ids"]):
        fail("result.coverage")


def _metrics(residuals, all_ids, scored_ids, uncertainty=None, sigmas=None):
    from statistics import median
    unsupported = [r for r in all_ids if r not in set(scored_ids)]
    coverage = dict(eligible_count=len(scored_ids),total_count=len(all_ids),fraction=len(scored_ids)/len(all_ids),unsupported_ids=unsupported)
    if len(residuals)!=len(scored_ids):
        fail("result.metrics.count")
    absolute = [abs(v) for v in residuals]
    standardized = None
    if residuals and uncertainty is not None and uncertainty["meaning"]=="independent_one_sigma" and uncertainty["independence_assumption"]=="row_independent":
        if sigmas is None or len(sigmas)!=len(residuals) or any(type(s) not in (int,float) or not math.isfinite(s) or s<=0 for s in sigmas):
            fail("result.metrics.sigma")
        standardized = math.sqrt(math.fsum((r/s)**2 for r,s in zip(residuals,sigmas))/len(residuals))
    return dict(count=len(residuals),coverage=coverage,bias_nT=math.fsum(residuals)/len(residuals) if residuals else None,
        rmse_nT=math.sqrt(math.fsum(v*v for v in residuals)/len(residuals)) if residuals else None,
        mae_nT=math.fsum(absolute)/len(residuals) if residuals else None,median_absolute_nT=median(absolute) if residuals else None,
        max_absolute_nT=max(absolute) if residuals else None,standardized_rmse=standardized,uncertainty_meaning=uncertainty)


def environment_identity(*, local_job_handle=None):
    """Actual installed distribution bytes/licenses and fixed loaded source pins.

    No hostname, user paths, invented wheel digest or CPython-origin assertion.
    Distribution identity excludes interpreter-generated caches, not scientific
    payload. License evidence is actual package metadata plus shipped licenses;
    recording it is not a legal permission inference.
    """
    import sys
    from importlib.metadata import distribution
    np,_=engines()
    root = Path(sys.prefix).resolve()
    if local_job_handle is not None:
        _local_resource_guard(local_job_handle)
        root=Path(np.__file__).resolve().parents[3]
        if not (root/"pyvenv.cfg").is_file():
            fail("environment.explicit_existing_virtualenv_packages","custody_mismatch")
    pins = []
    for name,pin in ENGINE_PINS.items():
        dist = distribution(name)
        inventory,licenses = [],[]
        for entry in sorted(dist.files or [],key=str):
            if str(entry).endswith(".pyc") or "__pycache__" in str(entry):
                continue
            file = Path(dist.locate_file(entry)).resolve()
            if not file.is_relative_to(root) or not file.is_file():
                fail("environment.distribution_path","custody_mismatch")
            body = file.read_bytes()
            record = dict(name=str(entry).replace("\\","/"),sha256=sha256(body).hexdigest(),bytes=len(body))
            inventory.append(record)
            if "license" in str(entry).lower() or file.name=="METADATA":
                licenses.append(record)
        if not inventory or not licenses:
            fail("environment.distribution_evidence","custody_mismatch")
        pins.append(dict(name=name,version=pin,distribution_sha256=digest(inventory),license_evidence_sha256=digest(licenses)))
    files = []
    for name in ("magnetic_line_contract","magnetic_line_validation","magnetic_lines",*SOURCE_PINS):
        module = import_module(name)
        file = Path(module.__file__).resolve()
        if name.startswith("magnetic_") and file!=Path(__file__).resolve().with_name(name+".py"):
            fail("environment.shadow","custody_mismatch")
        body = file.read_bytes()
        files.append(dict(module_name=name,sha256=sha256(body).hexdigest(),bytes=len(body)))
    natives = []
    # Fixed scientific native registry, not whatever a test runner happened to
    # import. Replay can validate this BEFORE computing or importing test code.
    for name in ("numpy._core._multiarray_umath","numpy.linalg._umath_linalg","scipy.linalg._fblas",
                 "scipy.linalg._flapack","scipy.spatial._qhull","sklearn.utils._cython_blas","numba._dispatcher"):
        module = import_module(name)
        file = Path(module.__file__).resolve()
        if not file.is_relative_to(root) or file.suffix.lower() not in (".pyd",".so"):
            fail("environment.native_path","custody_mismatch")
        body = file.read_bytes()
        natives.append(dict(module_name=name,sha256=sha256(body).hexdigest(),bytes=len(body)))
    value = dict(python_revision=platform.python_version(),os_revision=platform.platform(),cpu_identity=platform.processor() or platform.machine(),
        engine_versions=pins,loaded_modules=files,native_modules=natives,threads=1,source_revision=digest(files[:3]))
    value["environment_receipt_sha256"] = digest(value)
    _result_type(value,"Environment","environment",1)
    return value


def parse_result(raw, *, local_profile=None):
    return validate_result(_parse_bounded_json(raw,8388608),local_profile=local_profile)


def validate_result(result, *, local_profile=None):
    if type(result) is not dict or type(result.get("input")) is not dict or type(result["input"].get("row_ids")) is not list:
        fail("Result")
    ids = result["input"]["row_ids"]
    n = len(ids)
    _result_type(result,"Result","Result",n,local_profile)
    if len(set(ids))!=n or result["inventory"]["original_rows"]!=n or result["geometry"]["row_ids"]!=ids:
        fail("result.inventory.identity")
    inv = result["inventory"]
    groups = [inv[k] for k in ("retained_ids","invalid_ids","excluded_ids")]
    combined = sum(groups,[])
    if len(combined)!=n or set(combined)!=set(ids) or len(set(combined))!=n or any(g!=[i for i in ids if i in set(g)] for g in groups):
        fail("result.inventory.dispositions")
    if result["input"]["sidecar_bytes"]+result["request"]["bytes"]>2097152:
        fail("result.metadata.bytes","resource_refused")
    if result["request"]["canonical_request"]["dataset_version_sha256"]!=result["input"]["dataset_sha256"]:
        fail("result.input.request","custody_mismatch")
    if contract.dataset_identity(result["input"]["csv_sha256"],result["input"]["sidecar_sha256"])!=result["input"]["dataset_sha256"] or \
        result["request"]["geometry_manifest_sha256"]!=result["request"]["canonical_request"]["split"]["geometry_manifest_sha256"]:
        fail("result.input.byte_identity","custody_mismatch")
    env = result["environment"]
    if digest({k:v for k,v in env.items() if k!="environment_receipt_sha256"})!=env["environment_receipt_sha256"] or \
        digest(env["loaded_modules"][:3])!=env["source_revision"]:
        fail("result.environment.hash","custody_mismatch")
    for channel in result["channels"]:
        validate_array_descriptor(channel["data"],ids,shape=[n],unit="nT")
    for key in ("easting","northing","upward"):
        validate_array_descriptor(result["geometry"][key],ids,shape=[n],unit="m")
    for reason in inv["reasons"]:
        if reason["row_id"] not in ids or reason["reasons"]!=[m for m in MASK_ORDER if m in reason["reasons"]] or \
            reason["row_id"] not in inv[reason["disposition"]+"_ids"]:
            fail("result.inventory.reasons")
    if len({r["row_id"] for r in inv["reasons"]})!=len(inv["reasons"]) or inv["flag_counts"]!=[
        dict(reason=m,count=sum(m in r["reasons"] for r in inv["reasons"])) for m in MASK_ORDER if any(m in r["reasons"] for r in inv["reasons"])]:
        fail("result.inventory.flag_counts")
    p = result["partitions"]
    if p["original_row_ids"]!=ids or p["config"]!=result["request"]["canonical_request"]["split"] or p["evaluation_count"]!=1:
        fail("result.partition.identity")
    for f in [p]+p["inner"]:
        train = f["outer_training_ids"] if f is p else f["training_ids"]
        val = f["outer_validation_ids"] if f is p else f["validation_ids"]
        if set(train)&set(val) or not set(train+val+f["tie_buffer_excluded_ids"])<=set(ids):
            fail("result.partition.overlap")
        _coverage_check(f["geometry_only_coverage"])
    fit = result["fit"]
    source_ids = list(dict.fromkeys(m["source_id"] for m in sorted(fit["source_block_map"],key=lambda m:(m["block_e"],m["block_n"]))))
    m = len(source_ids)
    if not 1<=m<=(320 if local_profile else 256) or [r["row_id"] for r in fit["source_block_map"]]!=p["outer_training_ids"]:
        fail("result.sources.inventory")
    validate_array_descriptor(fit["source_positions"],[[s,a] for s in source_ids for a in ("e","n","u")],shape=[m,3],unit="m")
    validate_array_descriptor(fit["source_coefficients"],source_ids,shape=[m],unit="nT*m")
    validate_array_descriptor(fit["column_scales"],source_ids,shape=[m],unit="1_per_m")
    validate_array_descriptor(fit["residuals"],ids,shape=[n],unit="nT")
    cfg = result["request"]["canonical_request"]["equivalent_sources"]
    if fit["weights_policy"]!=cfg["weights_policy"] or fit["damping_unit"]!=cfg["damping_unit"]:
        fail("result.fit.weight_identity")
    expected = [(d,l) for d in cfg["depth_candidates_m"] for l in cfg["damping_candidates"]]
    if [(c["depth_m"],c["damping"]) for c in fit["candidates"]]!=expected or fit["production_fit_count"] not in (25,26):
        fail("result.fit.candidates")
    for candidate in fit["candidates"]:
        if candidate["damping_unit"]!=cfg["damping_unit"] or [f["fold_id"] for f in candidate["folds"]]!=[f["fold_id"] for f in p["inner"]]:
            fail("result.fit.fold_identity")
        for f in candidate["folds"]:
            _coverage_check(f["coverage"])
            if f["objective"] is not None:
                _objective_check(f["objective"],cfg,candidate["damping"])
        if candidate["status"]=="eligible" and (any(f["rmse_nT"] is None for f in candidate["folds"]) or
            candidate["mean_rmse_nT"]!=math.fsum(f["rmse_nT"] for f in candidate["folds"])/3):
            fail("result.fit.mean_score")
    selected = [c for c in fit["candidates"] if c["candidate_id"]==fit["selected_candidate_id"]]
    if len(selected)!=1:
        fail("result.fit.selected")
    best = min(c["mean_rmse_nT"] for c in fit["candidates"] if c["status"]=="eligible")
    winner = max((c for c in fit["candidates"] if c["status"]=="eligible" and abs(c["mean_rmse_nT"]-best)<=1e-9),key=lambda c:(c["damping"],c["depth_m"]))
    if winner!=selected[0]:
        fail("result.fit.selection_rule")
    _objective_check(fit["objective"],cfg,selected[0]["damping"])
    if fit["objective"]["rank"]!=m or any(v is None or v<=0 for v in fit["column_scales"]["values"]):
        fail("result.fit.scale_or_rank")
    cells = 0
    for grid in result["grid"]:
        gid,config = grid["grid_id"],grid["config"]
        nx,ny = config["nx"],config["ny"]
        cells+=nx*ny
        validate_array_descriptor(grid["values"],[[gid,j] for j in range(nx*ny)],shape=[ny,nx],unit="nT")
        for key,axis,count in (("easting_axis","e",nx),("northing_axis","n",ny)):
            validate_array_descriptor(grid[key],[[gid,axis,j] for j in range(count)],shape=[count],unit="m")
            expected_axis = [config[f"origin_{axis}_m"]+j*config[f"spacing_{axis}_m"] for j in range(count)]
            if grid[key]["values"]!=expected_axis:
                fail("result.grid.axis")
    if cells>16384 or len(set(g["grid_id"] for g in result["grid"]))!=len(result["grid"]):
        fail("result.grid.cells","resource_refused")
    _validate_optional_result_arrays(result)
    residual_by_id = dict(zip(ids,fit["residuals"]["values"]))
    outer_ids = p["outer_validation_ids"]
    scored = [i for i in outer_ids if residual_by_id[i] is not None]
    metric = result["evaluation"]["outer"]
    expected_metric = _metrics([residual_by_id[i] for i in scored],outer_ids,scored)
    for key in ("count","coverage","bias_nT","rmse_nT","mae_nT","median_absolute_nT","max_absolute_nT"):
        if metric[key]!=expected_metric[key]:
            fail("result.evaluation.residual_binding")
    if any(residual_by_id[i] is not None for i in ids if i not in set(outer_ids)):
        fail("result.residual.scored_identity")
    if len({g["requirement_id"] for g in result["verdict"]["gates"]})!=len(result["verdict"]["gates"]):
        fail("result.verdict.duplicate_gate")
    for member in result["artifacts"]:
        _member_path(member)
    if len({m["relative_path"] for m in result["artifacts"]})!=len(result["artifacts"]) or any(
        m["relative_path"] in ("result.json","custody.json") for m in result["artifacts"]):
        fail("result.circular_member")
    if len(contract.canonical_bytes(result))>8388608:
        fail("result.bytes","resource_refused")
    return result


def _member_path(m):
    from pathlib import PurePosixPath
    name = m["relative_path"]
    if "\\" in name or ":" in name or name.startswith("/") or any(part in ("", ".", "..") for part in name.split("/")) or \
        PurePosixPath(name).suffix.lower() in (".exe",".py",".sh",".ps1",".bat",".cmd",".vbs",".js",".dll",".pyd"):
        fail("result.member.path")
    if m["included"] and (m["permission"]!="allowed" or m["sha256"] is None or m["bytes"] is None):
        fail("result.member.permission")


def _validate_optional_result_arrays(result):
    ids = result["input"]["row_ids"]
    fit = result["fit"]
    comparator = fit["comparator"]
    if comparator["residuals"] is not None:
        validate_array_descriptor(comparator["residuals"],ids,shape=[len(ids)],unit="nT")
    elif comparator["metrics"] is not None:
        fail("result.comparator.nulls")
    leveling = result["leveling"]
    if leveling is not None:
        crossings = [x["crossover_id"] for x in result["crossovers"] if x["disposition"]=="admitted" and x["constraint_representative"]==x["crossover_id"]]
        for key in ("before_residuals","after_residuals"):
            validate_array_descriptor(leveling[key],crossings,shape=[len(crossings)],unit="nT")
    for x in result["crossovers"]:
        if x["reasons"]!=[r for r in CROSSOVER_REASONS if r in x["reasons"]] or \
            (x["disposition"]=="rejected" and (not x["reasons"] or x["flight_minus_tie_nT"] is not None or x["difference_variance_nT2"] is not None)) or \
            (x["disposition"]=="admitted" and any(r!="duplicate_physical_constraint" for r in x["reasons"])):
            fail("result.crossovers.disposition")
    spectrum = result["spectrum"]
    if spectrum is None:
        return
    cfg = spectrum["config"]
    ny,nx = cfg["rectangle"]["ny"],cfg["rectangle"]["nx"]
    bins = [["grid-0","bin",j] for j in range(nx*ny)]
    validate_array_descriptor(spectrum["power"],bins,shape=[ny,nx],unit="nT^2")
    for key,axis,count in (("east_axis","e",nx),("north_axis","n",ny)):
        validate_array_descriptor(spectrum[key],[["grid-0",axis,j] for j in range(count)],shape=[count],unit=cfg["axis_unit"])
    if not math.isclose(math.fsum(spectrum["power"]["values"]),spectrum["parseval_sum_nT2"],rel_tol=1e-10,abs_tol=1e-12):
        fail("result.spectrum.parseval")
    micro = spectrum["microlevel"]
    if micro is not None:
        validate_array_descriptor(micro["transfer"],bins,shape=[ny,nx],unit="dimensionless")
        for key in ("removed","retained","clipped_removed"):
            if micro[key] is not None:
                validate_array_descriptor(micro[key],[["grid-0","cell",j] for j in range(nx*ny)],shape=[ny,nx],unit="nT")


def _objective_check(o, config, damping):
    if o["total"]!=o["data_term"]+o["regularization_term"] or o["damping"]!=damping or o["weight_multiplier"]!=1. or \
        o["damping_unit"]!=config["damping_unit"] or o["unit"]!=("nT^2" if config["weights_policy"]=="unweighted" else "dimensionless") or \
        o["condition"] is None or o["condition"]>1e12:
        fail("result.objective")


def _auxiliary_identities(request):
    records = []
    for op in request["operations"]:
        p = op["parameters"]
        identity = (p["navigation"]["identity"] if op["operation"]=="lag" else p["base"]["identity"] if op["operation"]=="diurnal" else
                    p["calibration"]["identity"] if op["operation"]=="heading" else
                    p["heldout_calibration"]["calibration"]["identity"] if op["operation"]=="leveling" and p["heldout_calibration"] is not None else None)
        if identity is not None and identity not in records:
            records.append(identity)
    return records


def _direction_spread(reference, row_ids, admitted_ids):
    from itertools import combinations
    vectors = []
    for index,rid in enumerate(row_ids):
        if rid in admitted_ids:
            xyz = [reference[k][index] for k in ("vector_east_nT","vector_north_nT","vector_up_nT")]
            norm = math.sqrt(math.fsum(v*v for v in xyz))
            if not math.isfinite(norm) or norm<=0:
                fail("result.reference_direction","metadata_ineligible","predict")
            vectors.append([v/norm for v in xyz])
    if not vectors:
        fail("result.reference_direction","metadata_ineligible","predict")
    return max((math.degrees(math.acos(max(-1.,min(1.,math.fsum(a*b for a,b in zip(u,v)))))) for u,v in combinations(vectors,2)),default=0.)


def run_result(csv_original, sidecar_original, request_original, *, run_id, local_profile=None, local_job_handle=None):
    """Actual 25-fit bounded run -> exact Result, never missing metadata defaults.

    Original S1 without a typed inducing-direction receipt remains an internal
    diagnostic/retained predictive failure, not a fabricated complete Result.
    """
    from copy import deepcopy
    from magnetic_line_validation import _segments
    _type(run_id,"ID","run_id",1)
    if local_profile is not None:
        _local_resource_guard(local_job_handle)
    intake = _load_profile_lines(csv_original,sidecar_original,request_original,local_profile=local_profile)
    request,meta = intake["request"],intake["metadata"]
    if request is None:
        fail("result.request_required")
    reference = meta["reference"]
    for op in request["operations"]:
        if op["operation"]=="main_field":
            reference = op["parameters"]["evaluated_reference"]
        elif op["operation"]=="rereference":
            reference = op["parameters"]["new_reference"]
    if reference is None:
        fail("result.typed_reference_required","metadata_ineligible","eligibility")
    internal = fit_grid(csv_original,sidecar_original,request_original,local_profile=local_profile,local_job_handle=local_job_handle)
    processed,fit,parts = (internal[k] for k in ("processing","fit","partitions"))
    original_rows,rows = intake["rows"],processed["rows"]
    ids = [r["row_id"] for r in rows]
    n = len(ids)
    def row_array(values,masks=None,unit="nT"):
        return array_descriptor(values,ids,masks if masks is not None else [[] for _ in ids],[n],unit)
    channels = deepcopy(processed["channels"])
    for channel in channels:
        d = channel["data"]
        channel["data"] = row_array(d["values"],d["masks"])
    selected_ids = set(parts["outer_training_ids"]+parts["outer_validation_ids"])
    spread = _direction_spread(processed["reference"],ids,selected_ids)
    if spread>min(request["geometry_policy"]["direction_tolerance_deg"],reference["direction_tolerance_deg"],.5):
        fail("result.direction_tolerance","metadata_ineligible","predict")
    invalid,excluded,retained,reasons = [],[],[],[]
    for r,flags,masks in zip(original_rows,intake["flags"],processed["masks"]):
        why = [m for m in MASK_ORDER if m in flags+masks]
        disposition = "invalid" if any(m in why for m in ("missing_value","invalid_geometry")) else "excluded" if masks else "retained"
        {"invalid":invalid,"excluded":excluded,"retained":retained}[disposition].append(r["row_id"])
        if why:
            reasons.append(dict(row_id=r["row_id"],reasons=why,disposition=disposition))
    inventory = dict(original_rows=n,retained_ids=retained,invalid_ids=invalid,excluded_ids=excluded,reasons=reasons,
        flag_counts=[dict(reason=m,count=sum(m in r["reasons"] for r in reasons)) for m in MASK_ORDER if any(m in r["reasons"] for r in reasons)])
    segments = []
    for s in _segments(rows,request["geometry_policy"]):
        a,b = s["p"],s["q"]
        if any(r["magnetic_nT"] is None or r["upward_m"] is None for r in (a,b)) or a["ordinal"]+1!=b["ordinal"]:
            continue
        segments.append(dict(segment_id=s["segment_id"],line_id=a["line_id"],sensor_id=a["sensor_id"],start_row_id=a["row_id"],
            end_row_id=b["row_id"],length_m=math.dist((a["easting_m"],a["northing_m"]),(b["easting_m"],b["northing_m"])),valid=True))
    stats = internal["support"]["line_statistics"]
    if {r["sensor_id"] for r in rows}!={request["sensor_id"]}:
        # A successful one-sensor run must still inventory other sensor geometry
        # correctly; no fabricated statistics for unused channels.
        fail("result.multi_sensor_statistics_extension_required","metadata_ineligible","predict")
    geometry = dict(row_ids=ids,easting=row_array([r["easting_m"] for r in rows],unit="m"),
        northing=row_array([r["northing_m"] for r in rows],unit="m"),upward=row_array([r["upward_m"] for r in rows],
            [["height_mismatch"] if r["upward_m"] is None else [] for r in rows],unit="m"),
        segments=segments,line_statistics=stats,coverage_sha256=digest(internal["support"]))
    crossings = crossovers(rows,request["geometry_policy"],parts["outer_training_ids"],meta["uncertainty"])
    partition = {k:deepcopy(parts[k]) for k in RESULT_TABLES["PartitionResult"]}
    partition["evaluation_count"] = fit["evaluation_count"]
    partition["inner"] = [{k:deepcopy(f[k]) for k in RESULT_TABLES["FoldInventory"]} for f in parts["inner"]]
    candidates = []
    selected = None
    cfg = request["equivalent_sources"]
    for index,c in enumerate(fit["candidates"]):
        candidate_id = f"candidate-{index}"
        if (c["depth_m"],c["damping"])==(fit["selected_candidate"]["depth_m"],fit["selected_candidate"]["damping"]):
            selected = candidate_id
        candidates.append(dict(candidate_id=candidate_id,depth_m=c["depth_m"],damping=c["damping"],damping_unit=cfg["damping_unit"],
            folds=[dict(fold_id=f["fold_id"],coverage=f["coverage"],rmse_nT=f["rmse_nT"],objective=f["objective"],verdict="pass",reason=None) for f in c["folds"]],
            mean_rmse_nT=c["mean_rmse_nT"],status="eligible"))
    final = fit["final_fit"]
    sources = final["source_positions"]
    source_ids = [s["source_id"] for s in sources]
    residual_by_id = dict(zip(fit["outer_row_ids"],fit["outer_observed_minus_predicted_nT"]))
    def residual_array(mapping):
        return row_array([mapping.get(i) for i in ids],[["outer_sealed"] if i in parts["outer_training_ids"] else
            ["spatial_buffer"] if i in parts["tie_buffer_excluded_ids"] else ["outside_hull"] if i not in mapping else [] for i in ids])
    comparator = internal["comparator"]
    comparison = dict(method="scipy_linear_nd",verdict="ineligible",reason=comparator.get("reason"),residuals=None,metrics=None)
    if comparator["verdict"]=="eligible":
        actual = {rid:obs-pred for rid,obs,pred in zip(fit["outer_row_ids"],fit["outer_observed_nT"],comparator["values"]) if pred is not None}
        comparison.update(verdict="pass",reason="Same-height geometric interpolation; no height transfer",residuals=residual_array(actual),
            metrics=_metrics(list(actual.values()),parts["outer_validation_ids"],list(actual)))
    fit_result = dict(method="harmonica_equivalent_sources",candidates=candidates,selected_candidate_id=selected,
        production_fit_count=25+(comparator["verdict"]=="eligible"),source_positions=array_descriptor(
            [s[k] for s in sources for k in ("easting_m","northing_m","upward_m")],[[s,a] for s in source_ids for a in ("e","n","u")],
            [[] for _ in range(3*len(sources))],[len(sources),3],"m"),
        source_coefficients=array_descriptor(final["coefficients"],source_ids,[[] for _ in sources],[len(sources)],"nT*m"),
        source_block_map=final["source_block_map"],column_scales=array_descriptor(final["column_scales"],source_ids,[[] for _ in sources],[len(sources)],"1_per_m"),
        objective=final["objective"],weights_policy=cfg["weights_policy"],damping_unit=cfg["damping_unit"],comparator=comparison,
        residuals=residual_array(residual_by_id),numerical_status="converged")
    grids = []
    for plane,role,gid in ((internal["grid"],"fitted_plane","grid-0"),(internal["continued_grid"],"continued_plane","grid-1")):
        if plane is None:
            continue
        config = deepcopy(request["grid"])
        config["plane_upward_m"] = float(plane["plane_upward_m"])
        if role=="continued_plane":
            config["continuation_delta_m"] = None
        nx,ny = config["nx"],config["ny"]
        grids.append(dict(grid_id=gid,config=config,quantity="scalar_total_field_anomaly",
            easting_axis=array_descriptor(plane["east_axis"].tolist(),[[gid,"e",j] for j in range(nx)],[[] for _ in range(nx)],[nx],"m"),
            northing_axis=array_descriptor(plane["north_axis"].tolist(),[[gid,"n",j] for j in range(ny)],[[] for _ in range(ny)],[ny],"m"),
            values=array_descriptor(plane["masked_values"],[[gid,j] for j in range(nx*ny)],plane["masks"],[ny,nx],"nT"),
            support_flags=[dict(cell_index=j,reasons=flags,disposition="excluded" if denied else "retained")
                for j,(flags,denied) in enumerate(zip(plane["masks"],plane["excluded"])) if flags],role=role))
    spectrum = _serialize_spectrum(internal,request)
    sigmas = {r["row_id"]:r["uncertainty_nT"] for r in rows}
    metrics = _metrics(fit["outer_observed_minus_predicted_nT"],parts["outer_validation_ids"],fit["outer_row_ids"],meta["uncertainty"],
        [sigmas[i] for i in fit["outer_row_ids"]])
    per_line = []
    for line,sensor in dict.fromkeys((r["line_id"],r["sensor_id"]) for r in rows if r["row_id"] in parts["outer_validation_ids"]):
        group = [r["row_id"] for r in rows if (r["line_id"],r["sensor_id"])==(line,sensor) and r["row_id"] in parts["outer_validation_ids"]]
        scored = [i for i in group if i in residual_by_id]
        per_line.append(dict(line_id=line,sensor_id=sensor,metrics=_metrics([residual_by_id[i] for i in scored],group,scored,meta["uncertainty"],[sigmas[i] for i in scored])))
    gates = [dict(requirement_id="M03-013",verdict="pass",evidence_sha256=digest(partition),reason="Geometry-sealed 24 inner fits and one outer evaluation"),
        dict(requirement_id="M03-014",verdict="unresolved",evidence_sha256=None,reason="No independently eligible provider field comparison"),
        dict(requirement_id="M03-018",verdict=internal["synthetic_quality_verdict"],evidence_sha256=digest(metrics),reason="Synthetic quality is separate from numerical convergence"),
        dict(requirement_id="M03-022",verdict="unresolved",evidence_sha256=None,reason="No native online admission or full-survey resource proof")]
    value = dict(schema="magnetic-local-study-result/1" if local_profile else "magnetic-result/1",run_id=run_id,lane="local_synthetic",input=dict(dataset_sha256=intake["dataset_sha256"],
        csv_sha256=intake["csv_sha256"],csv_bytes=len(csv_original),sidecar_sha256=intake["sidecar_sha256"],sidecar_bytes=len(sidecar_original),
        source_kind=meta["source_kind"],row_ids=ids,auxiliary_identities=_auxiliary_identities(request)),
        request=dict(bytes_sha256=sha256(request_original).hexdigest(),bytes=len(request_original),canonical_request=request,
            geometry_manifest_sha256=request["split"]["geometry_manifest_sha256"]),environment=environment_identity(local_job_handle=local_job_handle),inventory=inventory,
        channels=channels,geometry=geometry,crossovers=crossings,leveling=_serialize_leveling(processed["leveling"]),partitions=partition,
        fit=fit_result,grid=grids,spectrum=spectrum,evaluation=dict(interpretation="synthetic_truth",outer=metrics,per_line=per_line,
            provider_comparison=dict(verdict="unresolved",numeric_grid_sha256=None,metadata_receipt_sha256=None,matched_cells=0,
                difference_rmse_nT=None,reason="No eligible numeric provider comparison was supplied"),field_acceptance="unresolved",
            synthetic_acceptance=internal["synthetic_quality_verdict"],reference_approximation="Authored constant-direction weak projection, not exact field norm",
            maximum_direction_spread_deg=spread),rights=meta["rights"],artifacts=[],
        verdict=dict(overall="fail" if internal["synthetic_quality_verdict"]=="fail" else "unresolved",gates=gates,
            reasons=["Numerical convergence does not close field, native, full-survey or parent method gates"],error=None,numerical_success=True))
    validate_result(value,local_profile=local_profile)
    # Scanner verifies global node/depth/string bounds on generated JSON too.
    parse_result(contract.canonical_bytes(value),local_profile=local_profile)
    return value


def _serialize_leveling(leveling):
    if leveling is None:
        return None
    ids = [x["crossover_id"] for x in leveling["crossovers"] if x["disposition"]=="admitted" and x["constraint_representative"]==x["crossover_id"]]
    return dict(offsets=[dict(line_id=k,offset_nT=v,uncertainty_nT=None) for k,v in sorted(leveling["offsets"].items())],
        components=leveling["components"],before_residuals=array_descriptor([x["flight_minus_tie_nT"] for x in leveling["crossovers"]
            if x["crossover_id"] in ids],ids,[[] for _ in ids],[len(ids)],"nT"),
        after_residuals=array_descriptor(leveling["residuals"],ids,[[] for _ in ids],[len(ids)],"nT"),
        uncalibrated_line_ids=leveling["uncalibrated_line_ids"],scope="training_only",gauge_policy="lexicographic_first_tie_per_component")


def _serialize_spectrum(internal,request):
    spectrum = internal["spectrum"]
    if spectrum is None:
        return None
    config = request["spectrum"]
    ny,nx = spectrum["power"].shape
    def descriptor(values,unit,bin_role="bin"):
        return array_descriptor(values.ravel().tolist(),[["grid-0",bin_role,j] for j in range(nx*ny)],[[] for _ in range(nx*ny)],[ny,nx],unit)
    unit = config["axis_unit"]
    out = dict(config=config,power=descriptor(spectrum["power"],"nT^2"),
        east_axis=array_descriptor(spectrum["east_axis"].tolist(),[["grid-0","e",j] for j in range(nx)],[[] for _ in range(nx)],[nx],unit),
        north_axis=array_descriptor(spectrum["north_axis"].tolist(),[["grid-0","n",j] for j in range(ny)],[[] for _ in range(ny)],[ny],unit),
        window_mean_square=spectrum["window_mean_square"],mean_removed_nT=spectrum["mean_removed_nT"],parseval_sum_nT2=spectrum["parseval_sum_nT2"],
        sectors=spectrum["sectors"],microlevel=None)
    micro = internal["microlevel"]
    if micro is not None:
        if micro["transfer"].shape!=(ny,nx):
            fail("result.microlevel.distinct_rectangle_requires_extension","unsupported_operation","spectrum")
        out["microlevel"] = dict(parameters=micro["parameters"],transfer=descriptor(micro["transfer"],"dimensionless"),
            removed=descriptor(micro["removed"],"nT","cell"),retained=descriptor(micro["retained"],"nT","cell"),
            removed_power_nT2=micro["removed_power_nT2"],retained_power_nT2=micro["retained_power_nT2"],
            clipped_removed=None if micro["clipped_removed"] is None else descriptor(micro["clipped_removed"],"nT","cell"),geological_preservation_claim=False)
    return out


class LocalWorkflowError(contract.MagneticContractError):
    """The approved standalone Error union; no arbitrary exception strings."""
    def __init__(self, code, field, stage="export"):
        messages = dict(overwrite_refused="The destination must be a fresh absent directory.",
            rights_denied="The recorded rights deny this export member.",rights_unresolved="The recorded rights do not authorize this export member.",
            numerical_failure="The local numerical workflow did not complete.",interrupted="The local workflow was interrupted.",
            cancelled="The local workflow was cancelled.")
        if code not in messages:
            raise ValueError("Unknown local failure code.")
        self.error = dict(code=code,stage=stage,field=field,observed=None,limit=None,reason=messages[code],local_recipe=None,attempt_id=None)
        ValueError.__init__(self,messages[code])


def _safe_directory(path, *, absent=False):
    import os
    try:
        p = Path(os.path.abspath(path))
        if any(q.is_symlink() or q.is_junction() for q in (p,*p.parents)):
            fail("bundle.symlink_or_junction","custody_mismatch","export")
        if absent and (p.exists() or os.path.lexists(p)):
            raise LocalWorkflowError("overwrite_refused","output_directory")
        if not absent and not p.is_dir():
            fail("bundle.directory","custody_mismatch","export")
    except (OSError,ValueError,TypeError) as exc:
        if isinstance(exc,contract.MagneticContractError):
            raise
        fail("bundle.directory","custody_mismatch","export")
    return p


def _binding_check(result, originals, *, local_profile=None, local_job_handle=None):
    intake = _load_profile_lines(*originals,local_profile=local_profile)
    if result["input"]["dataset_sha256"]!=intake["dataset_sha256"] or result["input"]["csv_sha256"]!=intake["csv_sha256"] or \
        result["input"]["sidecar_sha256"]!=intake["sidecar_sha256"] or result["request"]["bytes_sha256"]!=sha256(originals[2]).hexdigest() or \
        result["request"]["canonical_request"]!=intake["request"] or result["rights"]!=intake["metadata"]["rights"] or \
        result["input"]["auxiliary_identities"]!=_auxiliary_identities(intake["request"]):
        fail("bundle.original_bindings","custody_mismatch","export")
    if result["environment"]!=environment_identity(local_job_handle=local_job_handle):
        fail("bundle.environment","custody_mismatch","export")
    return intake


def export_run(csv_original, sidecar_original, request_original, output_directory, *, result=None, local_profile=None, local_job_handle=None):
    """New local directory, exact original-byte members and closed outer custody.

    A supplied Result is not trusted numerical origin: independently replay it
    before publication. Private exports still honor raw-mirroring exclusions,
    including embedded auxiliary originals. No ZIP, pickle or network loader.
    """
    from copy import deepcopy
    target = _safe_directory(output_directory,absent=True)
    originals = (csv_original,sidecar_original,request_original)
    initial = _load_profile_lines(*originals,local_profile=local_profile)
    initial_policy,initial_rights = initial["request"]["export_policy"],initial["metadata"]["rights"]
    required = initial_rights["derivative_publication"] if initial_policy["derivative_requested"]=="public" else initial_rights["private_processing"]
    embedded = [a["rights"]["raw_mirroring"] for a in _auxiliary_identities(initial["request"])]
    if required!="allowed" or any(p!="allowed" for p in embedded):
        raise LocalWorkflowError("rights_denied" if "denied" in [required]+embedded else "rights_unresolved","result.embedded_original_rights")
    if result is None:
        result = run_result(*originals,run_id="local-run",local_profile=local_profile,local_job_handle=local_job_handle)
    else:
        validate_result(result,local_profile=local_profile)
        _binding_check(result,originals,local_profile=local_profile,local_job_handle=local_job_handle)
        replayed = run_result(*originals,run_id=result["run_id"],local_profile=local_profile,local_job_handle=local_job_handle)
        # Export manifests are not physical producer outputs.
        comparison = deepcopy(result)
        comparison["artifacts"] = []
        compare_replay(comparison,replayed,local_profile=local_profile)
    intake = _binding_check(result,originals,local_profile=local_profile,local_job_handle=local_job_handle)
    policy,rights = intake["request"]["export_policy"],intake["metadata"]["rights"]
    public = policy["derivative_requested"]=="public"
    derivative = rights["derivative_publication"] if public else rights["private_processing"]
    auxiliary_rights = [a["rights"]["raw_mirroring"] for a in result["input"]["auxiliary_identities"]]
    embedded_permission = "denied" if "denied" in auxiliary_rights else "unresolved" if "unresolved" in auxiliary_rights else "allowed"
    if derivative!="allowed" or embedded_permission!="allowed":
        raise LocalWorkflowError("rights_denied" if "denied" in (derivative,embedded_permission) else "rights_unresolved","result.embedded_original_rights")
    raw_allowed = rights["raw_mirroring"]=="allowed" and policy["raw_requested"]=="include" and policy["include_replay_inputs"]
    replay_allowed = raw_allowed and embedded_permission=="allowed"
    bodies,members = {},[]
    def member(name,kind,permission,body,include):
        record = dict(relative_path=name,kind=kind,permission=permission,included=include,
            sha256=sha256(body).hexdigest() if include else None,bytes=len(body) if include else None,
            reason=None if include else "Explicit rights or export policy excludes this original member")
        members.append(record)
        if include:
            bodies[name] = body
    member("original.csv","original",rights["raw_mirroring"],csv_original,raw_allowed)
    member("sidecar.json","metadata",embedded_permission,sidecar_original,policy["include_replay_inputs"])
    member("request.json","request",embedded_permission,request_original,policy["include_replay_inputs"])
    member("environment.json","receipt",derivative,contract.canonical_bytes(result["environment"]),True)
    member("replay.txt","replay_recipe",derivative,b"Use the unchanged local magnetic_lines.py replay --bundle DIRECTORY --output-directory NEW_DIRECTORY. Supply the pinned existing CPython runtime; no network or install.\n",True)
    exported = deepcopy(result)
    exported["artifacts"] = deepcopy(members)
    validate_result(exported,local_profile=local_profile)
    body = contract.canonical_bytes(exported)
    parse_result(body,local_profile=local_profile)
    member("result.json","result_array",derivative,body,True)
    receipt = dict(schema="magnetic-local-custody/1",input_sha256=intake["dataset_sha256"],request_sha256=sha256(request_original).hexdigest(),
        environment_sha256=result["environment"]["environment_receipt_sha256"],result_sha256=sha256(body).hexdigest(),members=members,
        replay_verdict="eligible" if replay_allowed else "ineligible",publication="local_only")
    bodies["custody.json"] = contract.canonical_bytes(receipt)
    if sum(len(v) for v in bodies.values())>67108864:
        fail("export.bytes","resource_refused","export")
    try:
        target.mkdir()  # Exclusive reservation; never overwrite any existing directory.
        for name,content in bodies.items():
            with (target/name).open("xb") as stream:
                stream.write(content)
                stream.flush()
                import os
                os.fsync(stream.fileno())
    except OSError:
        # Owned partial directory remains non-success; no deletion or replacement.
        fail("export.io_or_race","custody_mismatch","export")
    verify_bundle(target,local_profile=local_profile,local_job_handle=local_job_handle)
    return receipt


def verify_bundle(bundle, *, local_profile=None, local_job_handle=None):
    """Verify every original/array/manifest binding before any scientific call."""
    directory = _safe_directory(bundle)
    receipt = _parse_bounded_json(contract.read_bounded(directory/"custody.json",2097152),2097152)
    keys = {"schema","input_sha256","request_sha256","environment_sha256","result_sha256","members","replay_verdict","publication"}
    if type(receipt) is not dict or set(receipt)!=keys or receipt["schema"]!="magnetic-local-custody/1" or receipt["publication"]!="local_only" or \
        receipt["replay_verdict"] not in ("eligible","ineligible"):
        fail("bundle.custody")
    for key in ("input_sha256","request_sha256","environment_sha256","result_sha256"):
        _type(receipt[key],"Hash","bundle."+key,1)
    _result_type(receipt["members"],L("Member",1,64),"bundle.members",1)
    allowed = {"original.csv","sidecar.json","request.json","environment.json","replay.txt","result.json"}
    names,body,total = set(),{},0
    for m in receipt["members"]:
        name = m["relative_path"]
        if name not in allowed or name in names:
            fail("bundle.member.path")
        names.add(name)
        path = directory/name
        if path.is_symlink() or path.is_junction():
            fail("bundle.member.symlink","custody_mismatch","export")
        if m["included"]:
            if m["permission"]!="allowed" or m["sha256"] is None or m["bytes"] is None:
                fail("bundle.member.permission")
            data = contract.read_bounded(path,min(m["bytes"],67108864))
            if len(data)!=m["bytes"] or sha256(data).hexdigest()!=m["sha256"]:
                fail("bundle.member.hash","custody_mismatch","export")
            body[name] = data
            total+=len(data)
        elif path.exists() or m["sha256"] is not None or m["bytes"] is not None:
            fail("bundle.denied_member","custody_mismatch","export")
    if total>67108864 or names!=allowed or {p.name for p in directory.iterdir()}!=set(body)|{"custody.json"}:
        fail("bundle.inventory","custody_mismatch","export")
    result = parse_result(body["result.json"],local_profile=local_profile)
    if sha256(body["result.json"]).hexdigest()!=receipt["result_sha256"] or result["input"]["dataset_sha256"]!=receipt["input_sha256"] or \
        result["request"]["bytes_sha256"]!=receipt["request_sha256"] or result["environment"]["environment_receipt_sha256"]!=receipt["environment_sha256"] or \
        result["artifacts"]!=[m for m in receipt["members"] if m["relative_path"]!="result.json"] or \
        body["environment.json"]!=contract.canonical_bytes(result["environment"]):
        fail("bundle.result_bindings","custody_mismatch","export")
    if "original.csv" in body:
        _binding_check(result,(body["original.csv"],body["sidecar.json"],body["request.json"]),local_profile=local_profile,local_job_handle=local_job_handle)
    if (receipt["replay_verdict"]=="eligible")!=(set(("original.csv","sidecar.json","request.json"))<=set(body)):
        fail("bundle.replay_declaration","custody_mismatch","export")
    return receipt,result,body


def compare_replay(recorded, replayed, *, local_profile=None):
    """Exact structures/identities and frozen 1e-9 relative + 1e-6 nT bound.

    Rehashing altered arrays does not verify physics. Metadata, config, objective
    identity, source/engine/environment and mask hashes are exact; only scalar
    numerical values with float origins use the stated tolerance.
    """
    validate_result(recorded,local_profile=local_profile)
    validate_result(replayed,local_profile=local_profile)
    def compare(a,b,path):
        if type(a) is dict and type(b) is dict and set(a)==set(b):
            for k in a:
                compare(a[k],b[k],path+"."+k)
        elif type(a) is list and type(b) is list and len(a)==len(b):
            for index,(x,y) in enumerate(zip(a,b)):
                compare(x,y,path+f"[{index}]")
        elif type(a) is float and type(b) is float and any(t in path for t in (".values[",".rmse_nT",".data_term",".regularization_term",".total",".condition")):
            if not math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-6):
                fail("replay.numerical_tolerance","custody_mismatch","export")
        elif type(a) is not type(b) or a!=b:
            fail("replay.identity","custody_mismatch","export")
    compare(recorded,replayed,"Result")


def replay_run(bundle, output_directory):
    _safe_directory(output_directory,absent=True)
    receipt,result,body = verify_bundle(bundle)
    if receipt["replay_verdict"]!="eligible":
        raise LocalWorkflowError("rights_denied","replay.original_inputs")
    original = (body["original.csv"],body["sidecar.json"],body["request.json"])
    _binding_check(result,original)
    # export_run independently computes/compares the exact recorded producer
    # once, then publishes it. Do not duplicate the 25-fit replay again here.
    return export_run(*original,output_directory,result=result)


def main(argv=None):
    """Bounded local CLI. No file paths/errors/tracebacks leak to stdout."""
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Local magnetic flight-line contract and computation; no online or field admission")
    sub = parser.add_subparsers(dest="command",required=True)
    for name in ("validate","run"):
        child = sub.add_parser(name)
        for key in ("csv","metadata","request"):
            child.add_argument("--"+key,required=True)
        if name=="run":
            child.add_argument("--output-directory",required=True)
    child = sub.add_parser("replay")
    child.add_argument("--bundle",required=True)
    child.add_argument("--output-directory",required=True)
    args = parser.parse_args(argv)
    try:
        if args.command=="replay":
            value = replay_run(args.bundle,args.output_directory)
        else:
            if args.command=="run":
                _safe_directory(args.output_directory,absent=True)
            original = (contract.read_bounded(args.csv,16777216),contract.read_bounded(args.metadata,2097152),contract.read_bounded(args.request,2097152))
            if args.command=="validate":
                intake = contract.load_lines(*original)
                value = dict(dataset_sha256=intake["dataset_sha256"],eligibility_reasons=intake["eligibility_reasons"],
                    provider_authenticated=False,numerical_success=False)
            else:
                value = export_run(*original,args.output_directory)
        sys.stdout.buffer.write(contract.canonical_bytes(value)+b"\n")
        return 0
    except contract.MagneticContractError as exc:
        sys.stdout.buffer.write(contract.canonical_bytes(exc.error)+b"\n")
        return 2
    except KeyboardInterrupt:
        error = LocalWorkflowError("cancelled","local_workflow",stage="worker")
    except Exception:
        error = LocalWorkflowError("numerical_failure","local_workflow",stage="fit")
    sys.stdout.buffer.write(contract.canonical_bytes(error.error)+b"\n")
    return 2


if __name__=="__main__":
    raise SystemExit(main())
