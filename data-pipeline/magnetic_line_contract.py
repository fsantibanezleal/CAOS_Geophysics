"""Strict, bounded M03 intake. No corrections, solver, network or provider authentication."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import re


MAX_CSV_BYTES = 16777216
MAX_METADATA_BYTES = 2097152
MAX_NODES = 200000
MAX_DEPTH = 16
CSV_COLUMNS = (
    "row_id", "line_id", "line_kind", "sensor_id", "ordinal", "utc",
    "easting_m", "northing_m", "upward_m", "terrain_upward_m", "clearance_m",
    "magnetic_nT", "uncertainty_nT", "heading_deg",
)
OPERATIONS = ("lag", "diurnal", "heading", "main_field", "rereference", "leveling", "microlevel")
PERMISSIONS = ("allowed", "denied", "unresolved")
ID_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,64}\Z", re.ASCII)
NUMBER_PATTERN = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", re.ASCII)
CSV_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z", re.ASCII)
UTC_PATTERN = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.([0-9]{1,9}))?Z\Z")


class MagneticContractError(ValueError):
    """Fixed safe failure envelope; never copies an arbitrary exception or user value."""

    def __init__(self, code="schema_invalid", field=None, stage="parse", observed=None, limit=None):
        messages = {
            "schema_invalid": "Input does not satisfy the exact magnetic contract.",
            "metadata_ineligible": "Physical metadata do not authorize this operation.",
            "resource_refused": "The explicit magnetic resource bound was exceeded.",
            "unsupported_operation": "This operation is outside the magnetic scalar contract.",
            "custody_mismatch": "Declared identity does not match the supplied original bytes.",
        }
        self.error = dict(code=code, stage=stage, field=field, observed=observed, limit=limit,
                          reason=messages[code], local_recipe=None, attempt_id=None)
        super().__init__(messages[code])


def fail(field, code="schema_invalid", stage="parse", observed=None, limit=None):
    raise MagneticContractError(code, field, stage, observed, limit)


def canonical_bytes(value):
    """Product encoding, not RFC8785; typed F64 and original bytes remain distinct."""
    def normalize(v):
        if type(v) is float:
            if not math.isfinite(v):
                fail("canonical.number")
            return 0.0 if v == 0 else v
        if type(v) is list:
            return [normalize(x) for x in v]
        if type(v) is dict:
            return {k: normalize(x) for k, x in v.items()}
        return v
    try:
        return json.dumps(normalize(value), sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        fail("canonical")


def digest(value):
    return sha256(canonical_bytes(value)).hexdigest()


def read_bounded(path, limit):
    """MAX+1 actual read, not stat-before-read; two supplied local originals only."""
    try:
        with Path(path).open("rb") as stream:
            data = stream.read(limit + 1)
    except OSError:
        fail("original", "custody_mismatch")
    if len(data) > limit:
        fail("original.bytes", "resource_refused", observed=len(data), limit=limit)
    return data


class _Scanner:
    """Grammar/decoded-string/node/depth scan before full JSON materialization."""

    def __init__(self, text):
        self.text, self.i, self.nodes = text, 0, 0

    def space(self):
        while self.i < len(self.text) and self.text[self.i] in " \t\r\n":
            self.i += 1

    def string(self, key=False):
        start = self.i
        self.i += 1
        escaped = False
        while self.i < len(self.text):
            char = self.text[self.i]
            self.i += 1
            if not escaped and char == '"':
                token = self.text[start:self.i]
                try:
                    value = json.loads(token)
                    count = len(value.encode("utf-8"))
                except (ValueError, UnicodeError):
                    fail("json.string")
                if "\x00" in value or count > (128 if key else 8192):
                    fail("json.string", "resource_refused")
                return value
            if ord(char) < 32:
                fail("json.string")
            if self.i - start > (6 * 128 + 2 if key else 6 * 8192 + 2):
                fail("json.string", "resource_refused")
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
        fail("json.string")

    def value(self, depth=0):
        self.space()
        self.nodes += 1
        if depth > MAX_DEPTH or self.nodes > MAX_NODES:
            fail("json.complexity", "resource_refused")
        if self.i >= len(self.text):
            fail("json")
        char = self.text[self.i]
        if char == '"':
            self.string()
        elif char in "[{":
            self.i += 1
            closing = "]" if char == "[" else "}"
            self.space()
            if self.i < len(self.text) and self.text[self.i] == closing:
                self.i += 1
                return
            keys = set()
            while True:
                if char == "{":
                    self.space()
                    if self.i >= len(self.text) or self.text[self.i] != '"':
                        fail("json.key")
                    key = self.string(key=True)
                    self.nodes += 1
                    if self.nodes > MAX_NODES:
                        fail("json.nodes", "resource_refused")
                    if key in keys:
                        fail("json.key")
                    keys.add(key)
                    self.space()
                    if self.i >= len(self.text) or self.text[self.i] != ":":
                        fail("json")
                    self.i += 1
                self.value(depth + 1)
                self.space()
                if self.i >= len(self.text):
                    fail("json")
                end = self.text[self.i]
                self.i += 1
                if end == closing:
                    return
                if end != ",":
                    fail("json")
        elif char in "-0123456789":
            match = NUMBER_PATTERN.match(self.text, self.i)
            if match is None:
                fail("json.number")
            token = match.group()
            self.i = match.end()
            if len(token) > 128:
                fail("json.number", "resource_refused")
            if not math.isfinite(float(token)):
                fail("json.number")
        else:
            for literal in ("true", "false", "null"):
                if self.text.startswith(literal, self.i):
                    self.i += len(literal)
                    return
            fail("json")


def strict_json(raw):
    if type(raw) is not bytes:
        fail("json.bytes")
    if len(raw) > MAX_METADATA_BYTES:
        fail("json.bytes", "resource_refused")
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        fail("json.utf8")
    scan = _Scanner(text)
    scan.value()
    scan.space()
    if scan.i != len(text):
        fail("json.trailing")
    try:
        return json.loads(text)
    except (ValueError, RecursionError):
        fail("json")


def E(*values):
    return ("enum", values)


def L(item, low, high):
    return ("list", item, low, high)


def I(low, high):
    return ("int", low, high)


def literal(value):
    return ("literal", value)


PARAMETERS = dict(zip(OPERATIONS, (
    "LagParameters", "DiurnalParameters", "HeadingParameters", "MainFieldParameters",
    "RereferenceParameters", "LevelingParameters", "MicrolevelParameters",
)))
P = E(*PERMISSIONS)
OP = E(*OPERATIONS)
KIND = E("flight", "tie", "reflight")
WEIGHT = E("unweighted", "admitted_inverse_variance")
# These are the complete reviewed intake/request tables, never parsed from documentation.
SCHEMAS = {
    "Sidecar": dict(schema=literal("magnetic-lines/1"), dataset_id="ID", revision="ID",
        source_kind=E("field_acquisition", "original_synthetic_acquisition", "provider_grid", "provider_image"),
        original="Original", rights="Rights", quantity="Quantity", coordinates="Coordinates",
        acquisition="Acquisition", channel_state=L("StateRecord", 0, 64), reference="?Reference",
        uncertainty="?Uncertainty", subset="?Subset", authored_control="?AuthoredControl"),
    "Original": dict(csv_sha256="Hash", csv_bytes=I(1, MAX_CSV_BYTES), source_url="?Text",
        provider_identifier="?Text", retrieval_utc="?UTC"),
    "Rights": dict(evidence_uri="?Text", evidence_sha256="?Hash", decision=P,
        private_processing=P, derivative_publication=P, raw_mirroring=P, attribution=L("Text", 0, 32)),
    "Quantity": dict(kind=E("scalar_total_intensity", "scalar_total_field_anomaly"), unit=literal("nT"),
        channel_name="ID", sign_definition=E("measured_total_intensity", "total_minus_reference", "authored_weak_projection")),
    "Coordinates": dict(horizontal_crs="Text", axis_order=literal("easting_northing"), xy_unit=literal("m"),
        vertical_datum="?Text", vertical_axis=literal("upward"), z_unit=literal("m"),
        datum_transform="?DatumTransform", geometry_accuracy_m="?Nonneg"),
    "DatumTransform": dict(source_crs="Text", target_crs="Text", vertical_source="Text",
        vertical_target="Text", method="Text", evidence_sha256="Hash", transformed_coordinates_sha256="Hash"),
    "Acquisition": dict(line_dictionary=L("LineDefinition", 1, 32), sensor_dictionary=L("SensorDefinition", 1, 4),
        timestamp_basis=E("UTC", "absent", "unknown"), declared_precision_s="?Pos", max_segment_gap_m="Pos",
        max_time_gap_s="?Pos", height_consistency_tolerance_m="?Nonneg"),
    "LineDefinition": dict(line_id="ID", kind=KIND, description="Text", provider_code="?Text"),
    "SensorDefinition": dict(sensor_id="ID", description="Text", provider_column="?Text", unit=literal("nT")),
    "Uncertainty": dict(meaning=E("independent_one_sigma", "correlated_one_sigma", "other_documented"),
        source_evidence="Text", independence_assumption=E("row_independent", "correlated", "unknown"), unit=literal("nT")),
    "Subset": dict(parent_raw_sha256="Hash", parent_row_count=I(1, 2147483647), selected_ids=L("ID", 1, 400),
        reason="Text", selection_policy_sha256="Hash", coverage_limitations="Text"),
    "AuthoredControl": dict(generator_revision="ID", seed=I(0, 2147483647), truth_definition="Text",
        authored_clock_and_datum="Text", regime=E("S1", "S2", "S3", "S4", "S5", "S6", "plane", "null", "periodic", "geometry"),
        notice=literal("synthetic, not field")),
    "StateRecord": dict(operation=OP, status=E("not_applied", "applied", "unknown"),
        parent_channel_sha256="?Hash", output_channel_sha256="?Hash", evidence_sha256="?Hash",
        parameters=("parameters", True), units=("nullable", E("m", "nT")),
        sign=E("position_time_plus_tau", "subtract_base_perturbation", "subtract_heading_model", "subtract_reference_F",
               "add_old_subtract_new_F", "subtract_line_offset", "diagnostic_removed_plus_retained", "unknown"),
        applied_by=E("provider", "user", "processor", "unknown")),
    "OperationRequest": dict(operation=OP, input_channel_sha256="Hash", parameters=("parameters", False)),
    "LagParameters": dict(tau_s="F64", definition=literal("position_time = measurement_time + tau_s"),
        navigation="NavigationSeries", max_bracket_gap_s="Pos", interpolation=literal("linear_no_extrapolation")),
    "DiurnalParameters": dict(base="BaseSeries", base_reference_nT="F64", valid_intervals=L("TimeInterval", 1, 32),
        max_bracket_gap_s="Pos", interpolation=literal("linear_no_extrapolation"), sign=literal("subtract_base_minus_reference")),
    "HeadingParameters": dict(a0_nT="F64", ac_nT="F64", as_nT="F64", convention=literal("clockwise_from_north_degrees"),
        calibration="CalibrationIdentity", sign=literal("subtract_model")),
    "MainFieldParameters": dict(evaluated_reference="Reference", sign=literal("subtract_F")),
    "RereferenceParameters": dict(old_reference="Reference", new_reference="Reference",
        old_applied_state_evidence_sha256="Hash", input_reference_receipt_sha256="Hash",
        sign=literal("add_old_F_subtract_new_F")),
    "LevelingParameters": dict(crossover_policy="CrossoverPolicy", weights_policy=WEIGHT,
        gauge_policy=literal("lexicographic_first_tie_per_component"), scope=literal("training_only"),
        heldout_calibration="?IndependentOffsets"),
    "MicrolevelParameters": dict(flight_azimuth_deg="F64", max_azimuth_spread_deg="Pos", kc_rad_per_m="Pos",
        ka_rad_per_m="Pos", amplitude_cap_nT="?Pos", promotion=literal("diagnostic_only"), spectrum_policy="SpectrumConfig"),
    "NavigationSeries": dict(schema=literal("magnetic-navigation/1"), identity="AuxIdentity", clock="Clock",
        coordinates="Coordinates", records=L("NavigationRecord", 2, 4096)),
    "NavigationRecord": dict(utc="UTC", line_id="ID", easting_m="F64", northing_m="F64", upward_m="F64"),
    "BaseSeries": dict(schema=literal("magnetic-base/1"), identity="AuxIdentity", clock="Clock",
        station_id="ID", quantity=literal("scalar_total_intensity"), unit=literal("nT"), records=L("BaseRecord", 2, 4096)),
    "BaseRecord": dict(utc="UTC", intensity_nT="F64"),
    "AuxIdentity": dict(source_sha256="?Hash", source_verification=E("reviewed_original", "user_claimed", "authored"),
        source_receipt_sha256="?Hash", canonical_records_sha256="Hash", rights="Rights"),
    "Clock": dict(basis=literal("UTC"), precision_s="Pos", synchronization_evidence_sha256="Hash",
        synchronization_error_s="?Nonneg"),
    "TimeInterval": dict(start="UTC", end="UTC"),
    "CalibrationIdentity": dict(identity="AuxIdentity", partition=literal("independent_calibration"),
        calibration_row_ids=L("ID", 0, 400), coefficient_receipt_sha256="Hash"),
    "IndependentOffsets": dict(calibration="CalibrationIdentity", values=L("OffsetValue", 1, 32), reference_gauge_id="ID"),
    "OffsetValue": dict(line_id="ID", offset_nT="F64", uncertainty_nT="?Pos"),
    "Reference": dict(kind=E("igrf_evaluated", "authored_constant"), model_generation="Text", coefficients_sha256="?Hash",
        evaluator="Evaluator", epoch="ReferenceEpoch", coordinates_sha256="Hash", input_height_definition="Text",
        input_height_unit=E("m", "km"), datum_transform_evidence_sha256="?Hash", original_basis=E("NED", "ENU"),
        output_basis=literal("ENU"), vector_east_nT=("rows", "F64"), vector_north_nT=("rows", "F64"),
        vector_up_nT=("rows", "F64"), scalar_F_nT=("rows", "Pos"), direction_tolerance_deg="Pos", receipt_sha256="Hash"),
    "Evaluator": dict(name="Text", revision="Text", source_sha256="Hash", calculation=literal("main_field"),
        valid_start_decimal_year="F64", valid_end_decimal_year="F64", rounding_tolerance_nT="Nonneg",
        input_coordinates_sha256="Hash", source_rights_evidence_sha256="Hash"),
    "ReferenceEpoch": dict(date_mode=E("survey_reference", "row_utc"), date_decimal_year="?F64",
        row_date_decimal_year=("nullable", ("rows", "F64")), survey_epoch_evidence_sha256="?Hash", row_utc_sha256="?Hash"),
    "Request": dict(schema=literal("magnetic-request/1"), dataset_version_sha256="Hash", channel_sha256="Hash",
        sensor_id="ID", operations=L("OperationRequest", 0, 6), geometry_policy="GeometryPolicy", grid="GridConfig",
        equivalent_sources="EquivalentSourcesConfig", split="SplitConfig", spectrum="?SpectrumConfig", export_policy="ExportPolicy"),
    "GeometryPolicy": dict(version=literal("lines-geometry/1"), max_segment_gap_m="Pos", max_time_gap_s="?Pos",
        crossover="CrossoverPolicy", same_plane_height_tolerance_m="?Nonneg", minimum_resolved_wavelength_m="?Pos",
        gap_policy=literal("break_and_mask"), support_policy=literal("closed_hull_and_nearest_training"),
        direction_tolerance_deg="Pos", numerical_tolerances="NumericalTolerancePolicy"),
    "CrossoverPolicy": dict(max_height_separation_m="Nonneg", max_time_separation_s="?Nonneg",
        sensor_policy=literal("same_sensor"), channel_policy=literal("same_channel_state"), min_crossing_sine="Pos",
        shared_endpoint_policy=literal("retain_pairs_one_physical_constraint"), collinear_policy=literal("reject_overlap"),
        uncertainty_policy=E("unweighted", "documented_independent_rows")),
    "NumericalTolerancePolicy": dict(version=literal("float64-scaled-intersection/1"),
        epsilon=literal(2.220446049250313e-16), multiplier=literal(64), max_parameter_tolerance=literal(.000001)),
    "GridConfig": dict(origin_e_m="F64", origin_n_m="F64", spacing_e_m="Pos", spacing_n_m="Pos",
        nx=I(2, 16384), ny=I(2, 16384), plane_upward_m="F64", datum="Text", support_radius_m="Pos",
        continuation_delta_m="?Pos", boundary_policy="BoundaryPolicy"),
    "BoundaryPolicy": dict(mode=E("periodic", "zero_pad", "reflect_pad"), pad_e_cells=I(0, 16384),
        pad_n_cells=I(0, 16384), detrend=E("none", "remove_mean"), taper=E("none", "hann"), crop=literal("original_extent")),
    "EquivalentSourcesConfig": dict(source_geometry="SourceGeometry", depth_candidates_m=L("Pos", 2, 2),
        damping_candidates=L("Pos", 4, 4), damping_unit=E("dimensionless", "nT^-2"), weights_policy=WEIGHT,
        weight_multiplier="Pos", dtype=literal("float64"), parallel=literal(False), fit_intercept=literal(False),
        column_scaling=literal("unweighted_population_std_no_mean"), candidate_order=literal("depth_then_damping_ascending"),
        tie_break=literal("larger_damping_then_depth")),
    "SourceGeometry": dict(version=literal("half_open_training_blocks/1"), origin_e_m="F64", origin_n_m="F64",
        block_e_m="Pos", block_n_m="Pos", representative=literal("unweighted_xy_mean_fsum_sorted_row_ids"),
        edge_policy=literal("floor_half_open_positive_side"), vertical_policy=literal("minimum_training_upward_minus_depth"),
        max_sources=I(1, 256)),
    "SplitConfig": dict(version=literal("full_lines_buffered_ties/1"), outer_line_ids=L("ID", 1, 32),
        heldout_blocks=L("SpatialBlock", 1, 32), buffer_m="Nonneg", anchor_line_ids=L("ID", 0, 32),
        inner_folds=L("InnerFold", 3, 3), geometry_manifest_sha256="Hash", sealed_values_sha256="Hash",
        tuning_candidate_order=literal("depth_then_damping_ascending"), maximum_outer_evaluations=literal(1),
        minimum_supported_fraction="Pos"),
    "SpatialBlock": dict(block_id="ID", e_min_m="F64", e_max_m="F64", n_min_m="F64", n_max_m="F64", boundary=literal("closed")),
    "InnerFold": dict(fold_id="ID", validation_line_ids=L("ID", 1, 32), validation_blocks=L("SpatialBlock", 1, 32)),
    "SpectrumConfig": dict(rectangle="GridRectangle", window=E("rectangular", "hann"),
        mean_policy=literal("subtract_arithmetic_mean"), normalization=literal("full_two_sided_bin_power"),
        axis_unit=E("cycles_per_m", "rad_per_m"), direction_sectors=L("DirectionSector", 0, 16)),
    "GridRectangle": dict(e_start=I(0, 16383), n_start=I(0, 16383), nx=I(2, 16384), ny=I(2, 16384)),
    "DirectionSector": dict(sector_id="ID", azimuth_start_deg="F64", azimuth_end_deg="F64"),
    "ExportPolicy": dict(destination_policy=literal("new_directory_only"), raw_requested=E("include", "exclude"),
        derivative_requested=E("private", "public"), include_replay_inputs=literal(True),
        redaction_policy=literal("deny_members_keep_reason"), network_during_replay=literal(False)),
}


def utc_key(value):
    """Nanosecond-exact order key; datetime alone would truncate 7..9 digit fractions."""
    match = UTC_PATTERN.fullmatch(value) if type(value) is str else None
    if match is None:
        fail("utc")
    try:
        date = datetime.strptime(match[1], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        fail("utc")
    return (date, int((match[2] or "").ljust(9, "0")))


def _type(value, spec, field, rows, parent=None):
    if isinstance(spec, str) and spec.startswith("?"):
        return None if value is None else _type(value, spec[1:], field, rows)
    if type(spec) is tuple:
        tag = spec[0]
        if tag == "nullable":
            return None if value is None else _type(value, spec[1], field, rows)
        if tag == "literal":
            if type(value) is not type(spec[1]) or value != spec[1]:
                fail(field)
            return value
        if tag == "enum":
            if type(value) is not str or value not in spec[1]:
                fail(field)
            return value
        if tag == "int":
            if type(value) is not int or not spec[1] <= value <= spec[2]:
                fail(field)
            return value
        if tag in ("list", "rows"):
            low, high = (rows, rows) if tag == "rows" else spec[2:]
            if type(value) is not list or not low <= len(value) <= high:
                fail(field)
            return [_type(v, spec[1], f"{field}[{i}]", rows) for i, v in enumerate(value)]
        if tag == "parameters":
            if value is None and spec[1]:
                return None
            return validate_named(PARAMETERS[parent["operation"]], value, rows, field)
        fail(field)
    if spec in SCHEMAS:
        return validate_named(spec, value, rows, field)
    if spec in ("F64", "Pos", "Nonneg"):
        if type(value) not in (int, float):
            fail(field)
        try:
            number = float(value)
        except (ValueError, OverflowError):
            fail(field)
        if not math.isfinite(number) or (spec == "Pos" and number <= 0) or (spec == "Nonneg" and number < 0):
            fail(field)
        return number
    if spec not in ("ID", "Hash", "Text", "UTC"):
        fail(field)
    if type(value) is not str:
        fail(field)
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError:
        fail(field)
    if spec == "ID" and ID_PATTERN.fullmatch(value) is None:
        fail(field)
    if spec == "Hash" and re.fullmatch("[0-9a-f]{64}", value, re.ASCII) is None:
        fail(field)
    if spec == "Text" and (not 1 <= size <= 8192 or "\0" in value):
        fail(field)
    if spec == "UTC":
        utc_key(value)
    return value


def unique(values, field, ordered=False):
    if len(set(values)) != len(values) or (ordered and values != sorted(values)):
        fail(field)


def validate_named(name, obj, row_count=1, field=None):
    field = field or name
    if name not in SCHEMAS or type(obj) is not dict or set(obj) != set(SCHEMAS[name]):
        fail(field)
    decoded = {k: _type(obj[k], spec, f"{field}.{k}", row_count, obj) for k, spec in SCHEMAS[name].items()}
    _conditional(name, decoded, field)
    return decoded


def _conditional(name, v, f):
    if name == "Quantity":
        if (v["kind"] == "scalar_total_intensity") != (v["sign_definition"] == "measured_total_intensity"):
            fail(f + ".sign_definition")
    elif name == "StateRecord":
        units = "m" if v["operation"] == "lag" else "nT"
        signs = ("position_time_plus_tau", "subtract_base_perturbation", "subtract_heading_model",
                 "subtract_reference_F", "add_old_subtract_new_F", "subtract_line_offset", "diagnostic_removed_plus_retained")
        if v["sign"] != "unknown" and (v["units"] != units or v["sign"] != signs[OPERATIONS.index(v["operation"])]):
            fail(f + ".sign")
        if v["status"] == "applied" and v["applied_by"] == "processor" and any(v[k] is None for k in (
            "parent_channel_sha256", "output_channel_sha256", "evidence_sha256", "parameters")):
            fail(f + ".processor_identity")
    elif name == "AuxIdentity":
        mode = v["source_verification"]
        if v["source_sha256"] is None or ((mode == "user_claimed") != (v["source_receipt_sha256"] is None)):
            fail(f + ".source_verification")
    elif name in ("NavigationSeries", "BaseSeries"):
        seen = {}
        for r in v["records"]:
            group = r.get("line_id", "base")
            key = utc_key(r["utc"])
            if group in seen and key <= seen[group]:
                fail(f + ".records.utc")
            seen[group] = key
        if digest(v["records"]) != v["identity"]["canonical_records_sha256"]:
            fail(f + ".records", "custody_mismatch")
    elif name == "TimeInterval":
        if utc_key(v["start"]) > utc_key(v["end"]):
            fail(f + ".end")
    elif name == "DiurnalParameters":
        last = None
        for interval in v["valid_intervals"]:
            if last is not None and utc_key(interval["start"]) <= last:
                fail(f + ".valid_intervals")
            last = utc_key(interval["end"])
    elif name == "CalibrationIdentity":
        unique(v["calibration_row_ids"], f + ".calibration_row_ids")
    elif name == "IndependentOffsets":
        ids = [x["line_id"] for x in v["values"]]
        unique(ids, f + ".values", True)
        if v["reference_gauge_id"] not in ids:
            fail(f + ".reference_gauge_id")
    elif name == "Evaluator":
        if v["valid_start_decimal_year"] > v["valid_end_decimal_year"]:
            fail(f + ".valid_interval")
    elif name == "ReferenceEpoch":
        survey = v["date_mode"] == "survey_reference"
        if survey:
            valid = v["date_decimal_year"] is not None and v["survey_epoch_evidence_sha256"] is not None
            valid &= v["row_date_decimal_year"] is None and v["row_utc_sha256"] is None
        else:
            valid = v["row_date_decimal_year"] is not None and v["row_utc_sha256"] is not None
            valid &= v["date_decimal_year"] is None and v["survey_epoch_evidence_sha256"] is None
        if not valid:
            fail(f + ".date_mode")
    elif name == "Reference":
        if not 0 < v["direction_tolerance_deg"] <= .5:
            fail(f + ".direction_tolerance_deg")
        igrf = v["kind"] == "igrf_evaluated"
        if igrf:
            if v["model_generation"] != "IGRF14" or v["coefficients_sha256"] is None:
                fail(f + ".model_generation")
        elif v["model_generation"] != "authored_constant" or v["coefficients_sha256"] is not None:
            fail(f + ".model_generation")
        epoch = v["epoch"]
        dates = [epoch["date_decimal_year"]] if epoch["date_mode"] == "survey_reference" else epoch["row_date_decimal_year"]
        ev = v["evaluator"]
        if any(not ev["valid_start_decimal_year"] <= d <= ev["valid_end_decimal_year"] or
               (igrf and not 1900 <= d <= 2030) for d in dates):
            fail(f + ".epoch")
    elif name == "CrossoverPolicy":
        if not 1e-6 <= v["min_crossing_sine"] <= 1:
            fail(f + ".min_crossing_sine")
    elif name == "MicrolevelParameters":
        if not 0 <= v["flight_azimuth_deg"] < 360 or v["max_azimuth_spread_deg"] > 5 or v["spectrum_policy"]["window"] != "rectangular":
            fail(f + ".azimuth_or_window")
    elif name == "GeometryPolicy":
        if v["direction_tolerance_deg"] > .5:
            fail(f + ".direction_tolerance_deg")
    elif name == "SourceGeometry":
        if any(not 1 <= v[k] <= 10000 for k in ("block_e_m", "block_n_m")):
            fail(f + ".block_size")
    elif name == "EquivalentSourcesConfig":
        depths, damping = v["depth_candidates_m"], v["damping_candidates"]
        if depths != sorted(set(depths)) or not all(1 <= x <= 2000 for x in depths):
            fail(f + ".depth_candidates_m")
        if damping != sorted(set(damping)) or max(damping) > 1e6:
            fail(f + ".damping_candidates")
        unit = "dimensionless" if v["weights_policy"] == "unweighted" else "nT^-2"
        if v["damping_unit"] != unit or v["weight_multiplier"] != 1:
            fail(f + ".weights_or_damping_unit")
    elif name == "SpatialBlock":
        if not v["e_min_m"] < v["e_max_m"] or not v["n_min_m"] < v["n_max_m"]:
            fail(f + ".extent")
    elif name in ("SplitConfig", "InnerFold"):
        list_key = "outer_line_ids" if name == "SplitConfig" else "validation_line_ids"
        unique(v[list_key], f + "." + list_key)
        blocks = v["heldout_blocks" if name == "SplitConfig" else "validation_blocks"]
        unique([b["block_id"] for b in blocks], f + ".blocks")
        if name == "SplitConfig":
            unique(v["anchor_line_ids"], f + ".anchor_line_ids")
            unique([x["fold_id"] for x in v["inner_folds"]], f + ".inner_folds")
            if v["minimum_supported_fraction"] > 1:
                fail(f + ".minimum_supported_fraction")
    elif name == "DirectionSector":
        if not 0 <= v["azimuth_start_deg"] < v["azimuth_end_deg"] <= 360:
            fail(f + ".azimuth")
    elif name == "SpectrumConfig":
        sectors = v["direction_sectors"]
        unique([s["sector_id"] for s in sectors], f + ".sectors")
        ordered = sorted(sectors, key=lambda s: s["azimuth_start_deg"])
        if any(a["azimuth_end_deg"] > b["azimuth_start_deg"] for a, b in zip(ordered, ordered[1:])):
            fail(f + ".sectors")


def parse_csv(raw):
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_CSV_BYTES:
        fail("csv.bytes", "resource_refused")
    bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        text = raw.decode("utf-8-sig" if bom else "utf-8")
    except UnicodeError:
        fail("csv.utf8")
    # Each field is bounded BEFORE csv materializes a record. Multiline/quoted
    # fields cannot be valid in this exact ASCII numerical/ID/UTC contract.
    stream = io.StringIO(text, newline=None)
    if stream.readline(2048).rstrip("\r\n") != ",".join(CSV_COLUMNS):
        fail("csv.header")
    rows, flags, ids, ordinals = [], [], set(), {}
    locations, times = {}, {}
    while True:
        line = stream.readline(14 * 129 + 3)
        if line == "":
            break
        index = len(rows)
        if index >= 400:
            fail("csv.rows", "resource_refused", observed=401, limit=400)
        line = line.rstrip("\r\n")
        if len(line) > 14 * 129 or '"' in line or "\0" in line:
            fail("csv.record", "resource_refused")
        values = line.split(",")
        if len(values) != 14:
            fail("csv.columns")
        row = {}
        for k, val in zip(CSV_COLUMNS, values):
            if k in ("row_id", "line_id", "sensor_id"):
                row[k] = _type(val, "ID", "csv." + k, 1)
            elif k == "line_kind":
                row[k] = _type(val, KIND, "csv.line_kind", 1)
            elif k == "ordinal":
                if not re.fullmatch(r"0|[1-9][0-9]{0,9}", val, re.ASCII) or int(val) > 2147483647:
                    fail("csv.ordinal")
                row[k] = int(val)
            elif k == "utc":
                row[k] = _type(val, "UTC", "csv.utc", 1) if val else None
            elif val == "" and k not in ("easting_m", "northing_m"):
                row[k] = None
            else:
                if len(val) > 128 or CSV_NUMBER.fullmatch(val) is None:
                    fail("csv." + k)
                row[k] = _type(float(val), "F64", "csv." + k, 1)
        rid, group = row["row_id"], (row["line_id"], row["sensor_id"])
        if rid in ids or (group in ordinals and row["ordinal"] <= ordinals[group]):
            fail("csv.identity_or_order")
        ids.add(rid)
        ordinals[group] = row["ordinal"]
        rows.append(row)
        reasons = []
        if row["magnetic_nT"] is None:
            reasons.append("missing_value")
        if row["upward_m"] is None or (row["uncertainty_nT"] is not None and row["uncertainty_nT"] <= 0):
            reasons.append("invalid_geometry" if row["upward_m"] is None else "missing_value")
        if row["heading_deg"] is not None and not 0 <= row["heading_deg"] < 360:
            reasons.append("invalid_geometry")
        flags.append(reasons)
        point = (row["easting_m"], row["northing_m"], row["sensor_id"])
        if point in locations:
            for j in (index, locations[point]):
                if "duplicate_location" not in flags[j]:
                    flags[j].append("duplicate_location")
        locations[point] = index
        if row["utc"] is not None:
            timekey = (group, utc_key(row["utc"]))
            if timekey in times:
                for j in (index, times[timekey]):
                    if "unsupported_time" not in flags[j]:
                        flags[j].append("unsupported_time")
            times[timekey] = index
    if len({r["line_id"] for r in rows}) > 32 or len({r["sensor_id"] for r in rows}) > 4:
        fail("csv.groups", "resource_refused")
    if not rows:
        fail("csv.rows")
    return dict(rows=rows, flags=flags, bom=bom)


def dataset_identity(csv_sha256, sidecar_sha256):
    return digest(dict(csv_sha256=csv_sha256, sidecar_sha256=sidecar_sha256))


def channel_identity(rows):
    return digest([[r["row_id"], r["magnetic_nT"]] for r in rows])


def validate_operation(operation):
    if operation not in OPERATIONS:
        fail("operation", "unsupported_operation", "eligibility")
    return operation


def validate_lines(rows, meta, request=None):
    """Structural intake plus explicit unresolved reasons. No evidence authentication."""
    reasons = []
    if meta["source_kind"] in ("provider_grid", "provider_image"):
        reasons.append("source_kind_not_lines")
    synthetic = meta["source_kind"] == "original_synthetic_acquisition"
    if synthetic != (meta["authored_control"] is not None):
        fail("Sidecar.authored_control")
    if meta["rights"]["private_processing"] != "allowed":
        reasons.append("rights_" + ("denied" if meta["rights"]["private_processing"] == "denied" else "unresolved"))
    actual_lines = {r["line_id"]: r["line_kind"] for r in rows}
    if any(actual_lines[r["line_id"]] != r["line_kind"] for r in rows):
        fail("csv.line_kind")
    line_defs = meta["acquisition"]["line_dictionary"]
    sensor_defs = meta["acquisition"]["sensor_dictionary"]
    unique([r["line_id"] for r in line_defs], "Acquisition.line_dictionary", True)
    unique([r["sensor_id"] for r in sensor_defs], "Acquisition.sensor_dictionary", True)
    if {r["line_id"]: r["kind"] for r in line_defs} != actual_lines:
        fail("Acquisition.line_dictionary")
    if {r["sensor_id"] for r in sensor_defs} != {r["sensor_id"] for r in rows}:
        fail("Acquisition.sensor_dictionary")
    if meta["subset"] is not None:
        if meta["subset"]["selected_ids"] != [r["row_id"] for r in rows] or meta["subset"]["parent_row_count"] < len(rows):
            fail("Subset.selected_ids")
    if meta["coordinates"]["vertical_datum"] is None:
        reasons.append("vertical_datum_unresolved")
    if any(r["upward_m"] is None for r in rows):
        reasons.append("upward_missing")
    if any(r["magnetic_nT"] is None for r in rows):
        reasons.append("measurement_missing")
    tolerance = meta["acquisition"]["height_consistency_tolerance_m"]
    if tolerance is None:
        reasons.append("height_consistency_unresolved")
    elif any(r["upward_m"] is not None and r["terrain_upward_m"] is not None and r["clearance_m"] is not None and
             abs(r["upward_m"] - r["terrain_upward_m"] - r["clearance_m"]) > tolerance for r in rows):
        reasons.append("height_consistency_mismatch")
    if meta["uncertainty"] is None:
        reasons.append("uncertainty_unresolved")
    reference = meta["reference"]
    if reference is not None:
        if reference["kind"] == "authored_constant" and not synthetic:
            fail("Reference.kind", "metadata_ineligible", "eligibility")
        reasons.append("reference_independent_review_unverified")
        _reference_rows(reference, rows, synthetic, "Reference")
    if any(state["parameters"] is not None for state in meta["channel_state"]):
        reasons.append("supplied_processing_independent_review_unverified")
    if any(r["utc"] is None for r in rows) and meta["acquisition"]["timestamp_basis"] == "UTC":
        reasons.append("timestamp_missing")
    if request is not None:
        _request_cross_checks(rows, meta, request)
    return reasons


def _request_cross_checks(rows, meta, req):
    acq, geo, grid, eq, split = (meta["acquisition"], req["geometry_policy"], req["grid"],
                               req["equivalent_sources"], req["split"])
    if req["sensor_id"] not in {r["sensor_id"] for r in rows}:
        fail("Request.sensor_id")
    if geo["max_segment_gap_m"] > acq["max_segment_gap_m"] or (
        geo["max_time_gap_s"] is not None and
        (acq["max_time_gap_s"] is None or geo["max_time_gap_s"] > acq["max_time_gap_s"])
    ):
        fail("GeometryPolicy.gap")
    if meta["coordinates"]["vertical_datum"] is None or grid["datum"] != meta["coordinates"]["vertical_datum"]:
        fail("GridConfig.datum", "metadata_ineligible", "eligibility")
    if split["buffer_m"] < grid["support_radius_m"]:
        fail("SplitConfig.buffer_m")
    policy = eq["weights_policy"]
    admitted = meta["uncertainty"] is not None and meta["uncertainty"]["meaning"] == "independent_one_sigma" and \
        meta["uncertainty"]["independence_assumption"] == "row_independent"
    if policy == "admitted_inverse_variance" and (
        not admitted or any(r["uncertainty_nT"] is None or r["uncertainty_nT"] <= 0
                            for r in rows if r["sensor_id"] == req["sensor_id"])
    ):
        fail("EquivalentSourcesConfig.weights_policy", "metadata_ineligible", "eligibility")
    names = [o["operation"] for o in req["operations"]]
    unique(names, "Request.operations")
    order = {op: i for i, op in enumerate(OPERATIONS)}
    if names != sorted(names, key=order.get) or {"main_field", "rereference"} <= set(names):
        fail("Request.operations")
    for operation in req["operations"]:
        if operation["input_channel_sha256"] != req["channel_sha256"]:
            fail("OperationRequest.input_channel_sha256", "custody_mismatch")
        op, params = operation["operation"], operation["parameters"]
        if op == "leveling":
            if params["crossover_policy"] != geo["crossover"]:
                fail("LevelingParameters.crossover_policy")
            if params["weights_policy"] == "admitted_inverse_variance" and (
                not admitted or geo["crossover"]["uncertainty_policy"] != "documented_independent_rows"
            ):
                fail("LevelingParameters.weights_policy")
        if op == "lag" and meta["quantity"]["kind"] != "scalar_total_intensity":
            fail("LagParameters.input_quantity", "metadata_ineligible", "eligibility")
        for field in ("evaluated_reference", "old_reference", "new_reference"):
            if field in params:
                _reference_rows(params[field], rows, meta["source_kind"] == "original_synthetic_acquisition",
                                "OperationRequest." + field)
        calibration = params.get("calibration")
        if op == "leveling" and params["heldout_calibration"] is not None:
            calibration = params["heldout_calibration"]["calibration"]
        if calibration is not None:
            sealed_ids = {r["row_id"] for r in rows if r["line_id"] in split["outer_line_ids"]}
            sealed_ids.update(r["row_id"] for r in rows if any(
                r["line_id"] in fold["validation_line_ids"] for fold in split["inner_folds"]))
            if sealed_ids.intersection(calibration["calibration_row_ids"]):
                fail("CalibrationIdentity.calibration_row_ids", "metadata_ineligible", "eligibility")
        if op == "lag":
            nav = params["navigation"]
            if nav["coordinates"] != meta["coordinates"]:
                fail("NavigationSeries.coordinates", "metadata_ineligible", "eligibility")
            if not {r["line_id"] for r in nav["records"]} <= {r["line_id"] for r in rows}:
                fail("NavigationSeries.records.line_id")
    if meta["reference"] is not None and meta["reference"]["direction_tolerance_deg"] != geo["direction_tolerance_deg"]:
        fail("Reference.direction_tolerance_deg")
    b = grid["boundary_policy"]
    if b["mode"] == "periodic" and (b["pad_e_cells"] or b["pad_n_cells"] or b["detrend"] != "none" or b["taper"] != "none"):
        fail("BoundaryPolicy.periodic")
    if req["spectrum"] is not None:
        rect = req["spectrum"]["rectangle"]
        if rect["e_start"] + rect["nx"] > grid["nx"] or rect["n_start"] + rect["ny"] > grid["ny"]:
            fail("SpectrumConfig.rectangle")


def _reference_rows(reference, rows, synthetic, field):
    if reference["kind"] == "authored_constant" and not synthetic:
        fail(field + ".kind", "metadata_ineligible", "eligibility")
    epoch = reference["epoch"]
    if epoch["date_mode"] == "row_utc":
        if any(row["utc"] is None for row in rows):
            fail(field + ".epoch.row_utc", "metadata_ineligible", "eligibility")
        actual = []
        for row in rows:
            date, nano = utc_key(row["utc"])
            start = datetime(date.year, 1, 1, tzinfo=timezone.utc)
            end = datetime(date.year+1, 1, 1, tzinfo=timezone.utc)
            actual.append(date.year + ((date-start).total_seconds() + nano*1e-9)/(end-start).total_seconds())
        if epoch["row_date_decimal_year"] != actual or epoch["row_utc_sha256"] != digest([r["utc"] for r in rows]):
            fail(field + ".epoch", "custody_mismatch")


def load_lines(csv_original, sidecar_original, request_original=None):
    """Inputs are exact bytes, not user paths. Preserve original bytes and typed derivatives."""
    if type(csv_original) is not bytes or type(sidecar_original) is not bytes:
        fail("original.bytes")
    if len(sidecar_original) + (len(request_original) if type(request_original) is bytes else 0) > MAX_METADATA_BYTES:
        fail("metadata.bytes", "resource_refused")
    parsed = parse_csv(csv_original)
    meta = validate_named("Sidecar", strict_json(sidecar_original), len(parsed["rows"]))
    csv_hash, side_hash = sha256(csv_original).hexdigest(), sha256(sidecar_original).hexdigest()
    if meta["original"]["csv_sha256"] != csv_hash or meta["original"]["csv_bytes"] != len(csv_original):
        fail("Original", "custody_mismatch")
    dataset_hash = dataset_identity(csv_hash, side_hash)
    channel_hash = channel_identity(parsed["rows"])
    req = None if request_original is None else validate_named("Request", strict_json(request_original), len(parsed["rows"]))
    if req is not None and (req["dataset_version_sha256"] != dataset_hash or req["channel_sha256"] != channel_hash):
        fail("Request.input_identity", "custody_mismatch")
    reasons = validate_lines(parsed["rows"], meta, req)
    return dict(**parsed, original_bytes=csv_original, sidecar_bytes=sidecar_original, request_bytes=request_original,
                csv_sha256=csv_hash, sidecar_sha256=side_hash, dataset_sha256=dataset_hash, channel_sha256=channel_hash,
                metadata=meta, request=req, eligibility_reasons=reasons, provider_authenticated=False,
                numerical_success=False)


def preflight(rows, metadata, request):
    # Lazy stdlib-only sibling, not a scientific engine import or computation.
    from magnetic_line_validation import preflight_geometry
    return preflight_geometry(rows, metadata, request)
