"""Original deterministic M03 geometry only. No magnetic truth or provider-looking data."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import csv
import io
import math

from magnetic_line_contract import CSV_COLUMNS, canonical_bytes, channel_identity, dataset_identity, digest
from magnetic_line_validation import geometry_manifest


def geometry_rows(*, jitter_prefix="m03/20261003/"):
    rows = []
    northings = (-1400, -950, -520, -170, 230, 610, 1050, 1500)
    eastings = (-1100, 0, 1000)
    start = datetime(2001, 1, 1, tzinfo=timezone.utc)
    for line_index in range(11):
        line = f"F{line_index:02d}" if line_index < 8 else f"T{line_index-8:02d}"
        for j in range(33):
            rid = f"{line}.{j:03d}"
            e = (-1600 + 100*j if line_index % 2 == 0 else 1600 - 100*j) if line_index < 8 else eastings[line_index-8]
            n = northings[line_index] if line_index < 8 else -1600 + 100*j
            def jitter(axis):
                if j in (0, 32):
                    return 0.0
                value = sha256(f"{jitter_prefix}{rid}/{axis}".encode("ascii")).digest()
                return (int.from_bytes(value[:2], "big") % 1001 - 500) / 100
            t = start + timedelta(seconds=136*line_index + .5*j)
            up = 80 + 15*math.sin(j/5) + 10*math.cos(line_index)
            rows.append(dict(row_id=rid, line_id=line, line_kind="flight" if line_index < 8 else "tie",
                sensor_id="S0", ordinal=j, utc=t.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                easting_m=float(e)+jitter("e"), northing_m=float(n)+jitter("n"), upward_m=up,
                terrain_upward_m=0.0, clearance_m=up, magnetic_nT=None, uncertainty_nT=None, heading_deg=None))
    return rows


def refinement_geometry_rows():
    """Approved NEW magnetic-null geometry; original default bytes unchanged."""
    return geometry_rows(jitter_prefix="m03-refinement/20261004/")


def refinement_input(width, sealed_geometry_sha256):
    """Approved fresh SI dipoles; refuse without the prior NULL geometry seal.

    Widths are separate requests, never chosen from an outer score. Original
    controls, candidates and their failed thresholds remain byte unchanged.
    """
    rows = refinement_geometry_rows()
    if width not in (100.,50.) or type(width) is bool or digest(geometry_manifest(rows))!=sealed_geometry_sha256:
        raise ValueError("The fresh geometry seal and both fixed widths are required.")
    request=geometry_request(rows)
    request["equivalent_sources"]["source_geometry"].update(block_e_m=float(width),block_n_m=float(width),max_sources=320 if width==50 else 256)
    from magnetic_line_validation import make_partitions
    make_partitions(rows,request,local_profile="m03-local-320/1" if width==50 else None)
    _,meta,_=geometry_input()
    meta["rights"]["raw_mirroring"]="allowed"  # Newly authored controls only.
    recipe=dict(F_nT=48000.,D_deg=-17.,I_deg=42.,
        positions_m=[[-350.,180.,-350.],[510.,-420.,-450.],[-850.,-610.,-280.]],
        moments_Am2=[[1.2e7,-.9e7,2.1e7],[-1.6e7,1.1e7,.6e7],[.8e7,1.4e7,-1.3e7]])
    d,i=math.radians(recipe["D_deg"]),math.radians(recipe["I_deg"])
    direction=(math.cos(i)*math.sin(d),math.cos(i)*math.cos(d),-math.sin(i))
    for row in rows:
        vector=[0.,0.,0.]
        for source,moment in zip(recipe["positions_m"],recipe["moments_Am2"]):
            r=[row[k]-s for k,s in zip(("easting_m","northing_m","upward_m"),source)]
            length=math.sqrt(math.fsum(x*x for x in r))
            dot=math.fsum(a*b for a,b in zip(moment,r))
            for axis in range(3):
                vector[axis]+=100*(3*r[axis]*dot/length**5-moment[axis]/length**3)
        row["magnetic_nT"]=math.fsum(a*b for a,b in zip(vector,direction))
    coordinate_hash=digest(dict(datum=meta["coordinates"]["vertical_datum"],rows=[
        [r["row_id"],r["easting_m"],r["northing_m"],r["upward_m"]] for r in rows]))
    start=datetime(2001,1,1,tzinfo=timezone.utc)
    reference=dict(kind="authored_constant",model_generation="authored_constant",coefficients_sha256=None,
        evaluator=dict(name="authored_constant",revision="refinement-1",source_sha256=digest(recipe),calculation="main_field",
            valid_start_decimal_year=2000.,valid_end_decimal_year=2002.,rounding_tolerance_nT=1e-8,
            input_coordinates_sha256=coordinate_hash,source_rights_evidence_sha256=digest(meta["rights"])),
        epoch=dict(date_mode="row_utc",date_decimal_year=None,row_date_decimal_year=[2001+(
            datetime.fromisoformat(r["utc"].replace("Z","+00:00"))-start).total_seconds()/(365*86400) for r in rows],
            survey_epoch_evidence_sha256=None,row_utc_sha256=digest([r["utc"] for r in rows])),
        coordinates_sha256=coordinate_hash,input_height_definition="authored engineering zero",input_height_unit="m",
        datum_transform_evidence_sha256=None,original_basis="ENU",output_basis="ENU",vector_east_nT=[48000*direction[0]]*len(rows),
        vector_north_nT=[48000*direction[1]]*len(rows),vector_up_nT=[48000*direction[2]]*len(rows),scalar_F_nT=[48000.]*len(rows),
        direction_tolerance_deg=.5,receipt_sha256="")
    reference["receipt_sha256"]=digest({k:value for k,value in reference.items() if k!="receipt_sha256"})
    raw=csv_bytes(rows)
    meta.update(dataset_id="authored-refinement-20261004",revision="refinement-1",reference=reference)
    meta["original"].update(csv_sha256=sha256(raw).hexdigest(),csv_bytes=len(raw))
    meta["quantity"].update(kind="scalar_total_field_anomaly",channel_name="fresh-authored-weak-projection",
        sign_definition="authored_weak_projection")
    meta["authored_control"].update(generator_revision="refinement-1",regime="S1",truth_definition="Fresh independent SI dipoles "+canonical_bytes(recipe).decode())
    request["dataset_version_sha256"]=dataset_identity(sha256(raw).hexdigest(),digest(meta))
    request["channel_sha256"]=request["split"]["sealed_values_sha256"]=channel_identity(rows)
    request["export_policy"]["raw_requested"]="include"
    return raw,meta,request


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerow([row[k] if row[k] is not None else "" for k in CSV_COLUMNS])
    return stream.getvalue().encode("utf-8")


def geometry_input():
    rows = geometry_rows()
    raw = csv_bytes(rows)
    meta = dict(schema="magnetic-lines/1", dataset_id="authored-geometry", revision="geometry-1",
        source_kind="original_synthetic_acquisition",
        original=dict(csv_sha256=sha256(raw).hexdigest(), csv_bytes=len(raw),
                      source_url=None, provider_identifier=None, retrieval_utc=None),
        rights=dict(evidence_uri=None, evidence_sha256=None, decision="allowed", private_processing="allowed",
                    derivative_publication="allowed", raw_mirroring="denied", attribution=["Felipe Santibanez-Leal"]),
        quantity=dict(kind="scalar_total_intensity", unit="nT", channel_name="geometry-only",
                      sign_definition="measured_total_intensity"),
        coordinates=dict(horizontal_crs="Authored local metric engineering ENU, no field transform",
            axis_order="easting_northing", xy_unit="m", vertical_datum="authored engineering zero",
            vertical_axis="upward", z_unit="m", datum_transform=None, geometry_accuracy_m=None),
        acquisition=dict(line_dictionary=[dict(line_id=line, kind="flight" if line.startswith("F") else "tie",
            description="Original authored ordered geometry", provider_code=None) for line in sorted({r["line_id"] for r in rows})],
            sensor_dictionary=[dict(sensor_id="S0", description="Authored geometry channel", provider_column=None, unit="nT")],
            timestamp_basis="UTC", declared_precision_s=.5, max_segment_gap_m=150., max_time_gap_s=1.,
            height_consistency_tolerance_m=0.),
        channel_state=[], reference=None, uncertainty=None, subset=None,
        authored_control=dict(generator_revision="geometry-1", seed=0, truth_definition="No magnetic values or truth generated",
            authored_clock_and_datum="Explicit local engineering datum and synthetic 2001 UTC",
            regime="geometry", notice="synthetic, not field"))
    req = geometry_request(rows)
    req["dataset_version_sha256"] = dataset_identity(sha256(raw).hexdigest(), sha256(canonical_bytes(meta)).hexdigest())
    req["channel_sha256"] = channel_identity(rows)
    return raw, meta, req


def geometry_request(rows):
    def block(name, nlo, nhi):
        return dict(block_id=name, e_min_m=-1610., e_max_m=1610., n_min_m=float(nlo), n_max_m=float(nhi), boundary="closed")
    return dict(schema="magnetic-request/1", dataset_version_sha256="0"*64, channel_sha256=channel_identity(rows),
        sensor_id="S0", operations=[],
        geometry_policy=dict(version="lines-geometry/1", max_segment_gap_m=150., max_time_gap_s=1.,
            crossover=dict(max_height_separation_m=0., max_time_separation_s=None, sensor_policy="same_sensor",
                channel_policy="same_channel_state", min_crossing_sine=1e-6,
                shared_endpoint_policy="retain_pairs_one_physical_constraint", collinear_policy="reject_overlap",
                uncertainty_policy="unweighted"),
            same_plane_height_tolerance_m=None, minimum_resolved_wavelength_m=None,
            gap_policy="break_and_mask", support_policy="closed_hull_and_nearest_training", direction_tolerance_deg=.5,
            numerical_tolerances=dict(version="float64-scaled-intersection/1", epsilon=2.220446049250313e-16,
                multiplier=64, max_parameter_tolerance=.000001)),
        grid=dict(origin_e_m=-1600., origin_n_m=-1200., spacing_e_m=50., spacing_n_m=50., nx=65, ny=49,
            plane_upward_m=120., datum="authored engineering zero", support_radius_m=470., continuation_delta_m=100.,
            boundary_policy=dict(mode="periodic", pad_e_cells=0, pad_n_cells=0, detrend="none", taper="none", crop="original_extent")),
        equivalent_sources=dict(source_geometry=dict(version="half_open_training_blocks/1", origin_e_m=-1600.,
            origin_n_m=-1600., block_e_m=400., block_n_m=400., representative="unweighted_xy_mean_fsum_sorted_row_ids",
            edge_policy="floor_half_open_positive_side", vertical_policy="minimum_training_upward_minus_depth", max_sources=256),
            depth_candidates_m=[200., 500.], damping_candidates=[.0001, .01, 1., 100.], damping_unit="dimensionless",
            weights_policy="unweighted", weight_multiplier=1., dtype="float64", parallel=False, fit_intercept=False,
            column_scaling="unweighted_population_std_no_mean", candidate_order="depth_then_damping_ascending",
            tie_break="larger_damping_then_depth"),
        split=dict(version="full_lines_buffered_ties/1", outer_line_ids=["F04"], heldout_blocks=[block("outer-F04", 215, 245)],
            buffer_m=470., anchor_line_ids=["F00", "F07"],
            inner_folds=[dict(fold_id="A", validation_line_ids=["F01", "F06"],
                             validation_blocks=[block("A-F01", -965, -935), block("A-F06", 1035, 1065)]),
                         dict(fold_id="B", validation_line_ids=["F02", "F05"],
                             validation_blocks=[block("B-F02", -535, -505), block("B-F05", 595, 625)]),
                         dict(fold_id="C", validation_line_ids=["F03"], validation_blocks=[block("C-F03", -185, -155)])],
            geometry_manifest_sha256=digest(geometry_manifest(rows)), sealed_values_sha256=channel_identity(rows),
            tuning_candidate_order="depth_then_damping_ascending", maximum_outer_evaluations=1, minimum_supported_fraction=1.),
        spectrum=None, export_policy=dict(destination_policy="new_directory_only", raw_requested="exclude",
            derivative_requested="private", include_replay_inputs=True, redaction_policy="deny_members_keep_reason",
            network_during_replay=False))


def control_rows(regime):
    """Original controls:truth only after the regime's prescribed geometry seal."""
    if regime not in ("S1", "S2", "S4", "S5", "S6"):
        raise ValueError("This generator revision has not implemented the other regimes.")
    from magnetic_line_validation import make_partitions
    rows = geometry_rows()
    if regime == "S2":
        for row in rows:
            row["upward_m"] = row["clearance_m"] = 80.
    seal = make_partitions(rows, geometry_request(rows))
    assert len(seal["outer_training_ids"]) == 294 and len(seal["outer_validation_ids"]) == 33
    dec, inc = math.radians(12.), math.radians(55.)
    direction = (math.cos(inc)*math.sin(dec), math.cos(inc)*math.cos(dec), -math.sin(inc))
    for row in rows:
        if regime == "S2":
            offset = 2*(int(row["line_id"][1:])-3) if row["line_kind"] == "flight" else 0.
            row["magnetic_nT"] = 10+.002*row["easting_m"]-.003*row["northing_m"]+offset
        else:
            vector = analytic_dipole_vector((row["easting_m"], row["northing_m"], row["upward_m"]))
            row["magnetic_nT"] = math.fsum(a*b for a, b in zip(direction, vector))
            if regime == "S5":
                row["magnetic_nT"] += math.sin(2*math.pi*row["northing_m"]/150)
            elif regime == "S6":
                # Explicit unit-amplitude geology/stripe controls, never tuned
                # to original heldout scores. Both vary north, invariant east.
                row["magnetic_nT"] += math.cos(2*math.pi*row["northing_m"]/1600)+math.cos(2*math.pi*row["northing_m"]/800)
    if regime == "S4":
        # Explicit inspection derivatives; no claim these are a new eligible
        # magnetic forward acquisition at their edited descriptive coordinates.
        rows[16]["magnetic_nT"] = None
        rows[50]["easting_m"],rows[50]["northing_m"] = rows[49]["easting_m"],rows[49]["northing_m"]
        rows[83]["upward_m"] += 50.
        rows[83]["clearance_m"] = rows[83]["upward_m"]
        rows[117]["upward_m"] = rows[117]["clearance_m"] = None
        rows[150]["utc"] = None
    return rows


def analytic_dipole_vector(position):
    """Direct SI control operator, independent of Harmonica and fitted1/r blocks."""
    dipoles = (
        ((0., 0., -300.), (2e7, -1e7, 3e7)),
        ((-700., 500., -500.), (-1e7, 2e7, 1e7)),
        ((800., -600., -250.), (1e7, 1e7, -2e7)),
    )
    vector = [0., 0., 0.]
    for source, moment in dipoles:
        r = tuple(a-b for a, b in zip(position, source))
        length = math.sqrt(math.fsum(x*x for x in r))
        dot = math.fsum(a*b for a, b in zip(moment, r))
        for axis in range(3):
            # Explicit analytic control mu0/(4pi)=1e-7 SI and T->nT=1e9.
            vector[axis] += 100*(3*r[axis]*dot/length**5 - moment[axis]/length**3)
    return vector


def control_input(regime):
    """Actually byte-bound original authored acquisition; no provider data."""
    if regime == "S3":
        return instrument_input()
    rows = control_rows(regime)
    _, metadata, request = geometry_input()
    metadata["dataset_id"] = "authored-dipoles"
    metadata["revision"] = "dipole-1"
    metadata["quantity"].update(kind="scalar_total_field_anomaly", channel_name="authored-weak-anomaly",
                                sign_definition="authored_weak_projection")
    metadata["authored_control"].update(generator_revision="dipole-1", regime=regime,
        truth_definition="Three explicit independent SI dipoles; weak projection on authored F48000nT/D12deg/I55deg")
    if regime == "S2":
        metadata["dataset_id"] = "authored-plane-leveling"
        metadata["revision"] = "plane-leveling-1"
        metadata["authored_control"].update(generator_revision="plane-leveling-1",
            truth_definition="Authored common80m plane:10+0.002e-0.003n nT, flight offsets2*(line_index-3),ties0")
        request = geometry_request(rows)
    elif regime in ("S4","S5","S6"):
        metadata["dataset_id"],metadata["revision"] = "authored-"+regime.lower(),"negative-controls-1"
        definition = {"S4":"Inspection derivative:missing F00.016 value;F01.017 duplicates XY;F02.017 upward+50m;F03.018 missing height;F04.018 missing UTC",
            "S5":"Three independent SI dipoles plus unit1nT*sin(2pi*n/150m), intentionally unresolved cross-line wavelength",
            "S6":"Three independent SI dipoles plus true unit1nT*cos(2pi*n/1600m) and stripe unit1nT*cos(2pi*n/800m),both invariant along east"}
        metadata["authored_control"].update(generator_revision="negative-controls-1",truth_definition=definition[regime])
        request = geometry_request(rows)
    raw = csv_bytes(rows)
    metadata["original"].update(csv_sha256=sha256(raw).hexdigest(), csv_bytes=len(raw))
    request["dataset_version_sha256"] = dataset_identity(sha256(raw).hexdigest(), sha256(canonical_bytes(metadata)).hexdigest())
    request["channel_sha256"] = channel_identity(rows)
    request["split"]["sealed_values_sha256"] = channel_identity(rows)
    return raw, metadata, request


def authored_identity(payload, rights):
    """Actual canonical authored bytes, not an authenticated provider receipt."""
    identity = dict(source_sha256=digest(payload),source_verification="authored",source_receipt_sha256=None,
                    canonical_records_sha256=digest(payload),rights=rights)
    identity["source_receipt_sha256"] = digest({k:v for k,v in identity.items() if k != "source_receipt_sha256"})
    return identity


def instrument_input(*, raw_mirroring="denied"):
    """Prescribed S3 calibration with an independently authored piecewise path.

    Navigation knots are measured UTC+0.25s at the original geometry. The
    original assigned coordinates are navigation at measured UTC. A preceding
    independently authored knot supplies overlap. Truth is evaluated only after
    the aligned geometry seal. No sensor value calibrates lag/base/heading.
    """
    _,meta,_ = geometry_input()
    if raw_mirroring not in ("allowed", "denied"):
        raise ValueError("Authored control permissions must be explicit.")
    meta["rights"]["raw_mirroring"] = raw_mirroring
    aligned = geometry_rows()
    rows = []
    navigation = []
    for start in range(0,len(aligned),33):
        line = aligned[start:start+33]
        p,q = line[:2]
        preceding = {k:2*p[k]-q[k] for k in ("easting_m","northing_m","upward_m")}
        nav_start = datetime.fromisoformat(p["utc"].replace("Z","+00:00"))-timedelta(seconds=.25)
        navigation.append(dict(utc=nav_start.isoformat(timespec="milliseconds").replace("+00:00","Z"),
                               line_id=p["line_id"],**preceding))
        previous = preceding
        for known in line:
            date = datetime.fromisoformat(known["utc"].replace("Z","+00:00"))
            nav = dict(utc=(date+timedelta(seconds=.25)).isoformat(timespec="milliseconds").replace("+00:00","Z"),
                       line_id=known["line_id"],**{k:known[k] for k in ("easting_m","northing_m","upward_m")})
            navigation.append(nav)
            known["heading_deg"] = math.degrees(math.atan2(known["easting_m"]-previous["easting_m"],
                                                          known["northing_m"]-previous["northing_m"])) % 360
            row = dict(known)
            for key in ("easting_m","northing_m","upward_m"):
                row[key] = .5*(known[key]+previous[key])
            row["clearance_m"] = row["upward_m"]
            rows.append(row)
            previous = known
    request = geometry_request(aligned)
    from magnetic_line_validation import make_partitions
    make_partitions(aligned,request)  # Before any magnetic truth.
    start_date = datetime(2001,1,1,tzinfo=timezone.utc)
    dec,inc = math.radians(12),math.radians(55)
    direction = (math.cos(inc)*math.sin(dec),math.cos(inc)*math.cos(dec),-math.sin(inc))
    base = []
    for row,known in zip(rows,aligned):
        t = (datetime.fromisoformat(row["utc"].replace("Z","+00:00"))-start_date).total_seconds()
        perturbation = 3*math.sin(2*math.pi*t/120)
        heading = math.radians(row["heading_deg"])
        vector = analytic_dipole_vector(tuple(known[k] for k in ("easting_m","northing_m","upward_m")))
        truth = math.fsum(a*b for a,b in zip(direction,vector))
        row["magnetic_nT"] = 48000+truth+perturbation+2*math.cos(heading)-math.sin(heading)
        base.append(dict(utc=row["utc"],intensity_nT=48000+perturbation))
    meta["dataset_id"] = "authored-instrument"
    meta["revision"] = "instrument-1"
    meta["quantity"]["channel_name"] = "authored-instrument-total"
    meta["acquisition"]["sensor_dictionary"][0]["description"] = "Authored scalar total-intensity control, not field"
    meta["authored_control"].update(generator_revision="instrument-1",regime="S3",
        truth_definition="Independent aligned dipoles; total48000nT,lag+0.25s,base3sin(2pi*t/120),heading2cos(h)-sin(h)")
    meta["channel_state"] = [dict(operation=op,status="not_applied",parent_channel_sha256=None,output_channel_sha256=None,
        evidence_sha256=None,parameters=None,units=None,sign="unknown",applied_by="user")
        for op in ("lag","diurnal","heading","main_field")]
    clock = dict(basis="UTC",precision_s=.5,synchronization_evidence_sha256=digest(
        dict(measurement_basis="UTC",auxiliary_basis="UTC",offset_s=0.,definition="authored shared synthetic2001 clock")),
        synchronization_error_s=None)
    nav = dict(schema="magnetic-navigation/1",identity=authored_identity(navigation,meta["rights"]),clock=clock,
               coordinates=meta["coordinates"],records=navigation)
    base_series = dict(schema="magnetic-base/1",identity=authored_identity(base,meta["rights"]),clock=clock,
        station_id="authored-base",quantity="scalar_total_intensity",unit="nT",records=base)
    coefficients = dict(a0_nT=0.,ac_nT=2.,as_nT=-1.,convention="clockwise_from_north_degrees")
    calibration = dict(identity=authored_identity(coefficients,meta["rights"]),partition="independent_calibration",
        calibration_row_ids=[],coefficient_receipt_sha256=digest(coefficients))
    coordinate_hash = digest(dict(datum=meta["coordinates"]["vertical_datum"],
        rows=[[r["row_id"],r["easting_m"],r["northing_m"],r["upward_m"]] for r in aligned]))
    dates = [2001+(datetime.fromisoformat(r["utc"].replace("Z","+00:00"))-start_date).total_seconds()/(365*86400)
             for r in aligned]
    reference = dict(kind="authored_constant",model_generation="authored_constant",coefficients_sha256=None,
        evaluator=dict(name="authored_constant",revision="instrument-1",source_sha256=digest(dict(F_nT=48000.,D_deg=12.,I_deg=55.)),
            calculation="main_field",valid_start_decimal_year=2000.,valid_end_decimal_year=2002.,rounding_tolerance_nT=1e-8,
            input_coordinates_sha256=coordinate_hash,source_rights_evidence_sha256=digest(meta["rights"])),
        epoch=dict(date_mode="row_utc",date_decimal_year=None,row_date_decimal_year=dates,
            survey_epoch_evidence_sha256=None,row_utc_sha256=digest([r["utc"] for r in aligned])),
        coordinates_sha256=coordinate_hash,input_height_definition="authored engineering zero",input_height_unit="m",
        datum_transform_evidence_sha256=None,original_basis="ENU",output_basis="ENU",
        vector_east_nT=[48000*direction[0]]*len(rows),vector_north_nT=[48000*direction[1]]*len(rows),
        vector_up_nT=[48000*direction[2]]*len(rows),scalar_F_nT=[48000.]*len(rows),direction_tolerance_deg=.5,receipt_sha256="")
    reference["receipt_sha256"] = digest({k:v for k,v in reference.items() if k != "receipt_sha256"})
    raw = csv_bytes(rows)
    meta["original"].update(csv_sha256=sha256(raw).hexdigest(),csv_bytes=len(raw))
    request["dataset_version_sha256"] = dataset_identity(sha256(raw).hexdigest(),digest(meta))
    request["channel_sha256"] = request["split"]["sealed_values_sha256"] = channel_identity(rows)
    parameters = [dict(tau_s=.25,definition="position_time = measurement_time + tau_s",navigation=nav,
                       max_bracket_gap_s=.5,interpolation="linear_no_extrapolation"),
        dict(base=base_series,base_reference_nT=48000.,valid_intervals=[dict(start=rows[0]["utc"],end=rows[-1]["utc"])],
             max_bracket_gap_s=.5,interpolation="linear_no_extrapolation",sign="subtract_base_minus_reference"),
        dict(**coefficients,calibration=calibration,sign="subtract_model"),
        dict(evaluated_reference=reference,sign="subtract_F")]
    request["operations"] = [dict(operation=op,input_channel_sha256=request["channel_sha256"],parameters=params)
                            for op,params in zip(("lag","diurnal","heading","main_field"),parameters)]
    return raw,meta,request
