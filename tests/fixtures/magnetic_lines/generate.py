"""Original deterministic M03 geometry only. No magnetic truth or provider-looking data."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import csv
import io
import math

from magnetic_line_contract import CSV_COLUMNS, canonical_bytes, channel_identity, dataset_identity, digest
from magnetic_line_validation import geometry_manifest


def geometry_rows():
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
                value = sha256(f"m03/20261003/{rid}/{axis}".encode("ascii")).digest()
                return (int.from_bytes(value[:2], "big") % 1001 - 500) / 100
            t = start + timedelta(seconds=136*line_index + .5*j)
            up = 80 + 15*math.sin(j/5) + 10*math.cos(line_index)
            rows.append(dict(row_id=rid, line_id=line, line_kind="flight" if line_index < 8 else "tie",
                sensor_id="S0", ordinal=j, utc=t.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                easting_m=float(e)+jitter("e"), northing_m=float(n)+jitter("n"), upward_m=up,
                terrain_upward_m=0.0, clearance_m=up, magnetic_nT=None, uncertainty_nT=None, heading_deg=None))
    return rows


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
    """Original authored S1 independent dipoles, only after the fixed geometry seal."""
    if regime != "S1":
        raise ValueError("This generator revision has not implemented the other regimes.")
    from magnetic_line_validation import make_partitions
    rows = geometry_rows()
    seal = make_partitions(rows, geometry_request(rows))
    assert len(seal["outer_training_ids"]) == 294 and len(seal["outer_validation_ids"]) == 33
    dec, inc = math.radians(12.), math.radians(55.)
    direction = (math.cos(inc)*math.sin(dec), math.cos(inc)*math.cos(dec), -math.sin(inc))
    for row in rows:
        vector = analytic_dipole_vector((row["easting_m"], row["northing_m"], row["upward_m"]))
        row["magnetic_nT"] = math.fsum(a*b for a, b in zip(direction, vector))
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
    rows = control_rows(regime)
    _, metadata, request = geometry_input()
    metadata["dataset_id"] = "authored-dipoles"
    metadata["revision"] = "dipole-1"
    metadata["quantity"].update(kind="scalar_total_field_anomaly", channel_name="authored-weak-anomaly",
                                sign_definition="authored_weak_projection")
    metadata["authored_control"].update(generator_revision="dipole-1", regime=regime,
        truth_definition="Three explicit independent SI dipoles; weak projection on authored F48000nT/D12deg/I55deg")
    raw = csv_bytes(rows)
    metadata["original"].update(csv_sha256=sha256(raw).hexdigest(), csv_bytes=len(raw))
    request["dataset_version_sha256"] = dataset_identity(sha256(raw).hexdigest(), sha256(canonical_bytes(metadata)).hexdigest())
    request["channel_sha256"] = channel_identity(rows)
    request["split"]["sealed_values_sha256"] = channel_identity(rows)
    return raw, metadata, request
