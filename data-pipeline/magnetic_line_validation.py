"""M03 geometry seals and conservative preflight, without magnetic values or native engines."""
from __future__ import annotations

import math

from magnetic_line_contract import _type, digest, fail, validate_named


EPSILON = 2.220446049250313e-16
GEOMETRY_KEYS = ("row_id", "line_id", "line_kind", "sensor_id", "ordinal", "utc",
                 "easting_m", "northing_m", "upward_m", "terrain_upward_m", "clearance_m", "heading_deg")


def geometry_manifest(rows):
    """No magnetic values, sigma, truth, fitted choice or mutable receipt timestamp."""
    return [{k: row[k] for k in GEOMETRY_KEYS} for row in rows]


def validate_geometry_rows(rows):
    if type(rows) is not list or not 1 <= len(rows) <= 400:
        fail("geometry.rows", "resource_refused")
    ids, groups, lines, sensors = set(), {}, set(), set()
    for row in rows:
        if type(row) is not dict or not set(GEOMETRY_KEYS) <= set(row):
            fail("geometry.row")
        for key in GEOMETRY_KEYS:
            kind = ("ID" if key in ("row_id", "line_id", "sensor_id") else
                    ("nullable", "UTC") if key == "utc" else
                    ("int", 0, 2147483647) if key == "ordinal" else
                    ("enum", ("flight", "tie", "reflight")) if key == "line_kind" else
                    "F64" if key in ("easting_m", "northing_m") else "?F64")
            _type(row[key], kind, "geometry." + key, len(rows))
        group = (row["line_id"], row["sensor_id"])
        if row["row_id"] in ids or (group in groups and row["ordinal"] <= groups[group]):
            fail("geometry.identity")
        groups[group] = row["ordinal"]
        ids.add(row["row_id"])
        lines.add(row["line_id"])
        sensors.add(row["sensor_id"])
    if len(lines) > 32 or len(sensors) > 4:
        fail("geometry.groups", "resource_refused")


def segment_rectangle(p, q, block):
    """Closed finite-segment/rectangle clipping, including touch and degenerate point."""
    lo, hi = 0.0, 1.0
    dx, dy = q[0] - p[0], q[1] - p[1]
    for a, c in ((-dx, p[0] - block[0]), (dx, block[1] - p[0]),
                 (-dy, p[1] - block[2]), (dy, block[3] - p[1])):
        if a == 0:
            if c < 0:
                return False
        else:
            z = c / a
            if a < 0:
                lo = max(lo, z)
            else:
                hi = min(hi, z)
            if lo > hi:
                return False
    return True


def _point(row):
    return (row["easting_m"], row["northing_m"])


def _groups(rows):
    groups = {}
    for index, row in enumerate(rows):
        groups.setdefault((row["line_id"], row["sensor_id"]), []).append((index, row))
    return groups


def _segments(rows, policy):
    """Original consecutive geometry adjacency; never filtered then reconnected."""
    pairs = []
    for group in _groups(rows).values():
        for (index, p), (_, q) in zip(group, group[1:]):
            distance = math.dist(_point(p), _point(q))
            if distance <= 0 or distance > policy["max_segment_gap_m"]:
                continue
            if policy["max_time_gap_s"] is not None:
                from magnetic_line_contract import utc_key
                if p["utc"] is None or q["utc"] is None:
                    continue
                pt, pn = utc_key(p["utc"])
                qt, qn = utc_key(q["utc"])
                elapsed = (qt - pt).total_seconds() + (qn - pn) * 1e-9
                if not 0 < elapsed <= policy["max_time_gap_s"]:
                    continue
            pairs.append(dict(segment_id=f"S{index:06d}", p=p, q=q))
    return pairs


def _rect(block, buffer=0):
    return (block["e_min_m"] - buffer, block["e_max_m"] + buffer,
            block["n_min_m"] - buffer, block["n_max_m"] + buffer)


def _contains(point, rect):
    return rect[0] <= point[0] <= rect[1] and rect[2] <= point[1] <= rect[3]


def _buffered_ties(rows, blocks, buffer):
    excluded = set()
    rectangles = [_rect(b, buffer) for b in blocks]
    for group in _groups(rows).values():
        if group[0][1]["line_kind"] != "tie":
            continue
        # Original adjacencies, even across an acquisition gap, conservatively
        # exclude endpoint identities; no bridge is manufactured for fitting.
        for (_, p), (_, q) in zip(group, group[1:]):
            if any(segment_rectangle(_point(p), _point(q), b) for b in rectangles):
                excluded.update((p["row_id"], q["row_id"]))
        for _, p in group:
            if any(_contains(_point(p), b) for b in rectangles):
                excluded.add(p["row_id"])
    return excluded


def _cross(o, a, b):
    return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])


def _hull(points):
    points = sorted(set(points))
    if len(points) < 3:
        fail("partition.hull", "metadata_ineligible", "partition")
    def half(sequence):
        h = []
        for p in sequence:
            while len(h) >= 2 and _cross(h[-2], h[-1], p) <= 0:
                h.pop()
            h.append(p)
        return h
    hull = half(points)[:-1] + half(reversed(points))[:-1]
    if len(hull) < 3:
        fail("partition.hull", "metadata_ineligible", "partition")
    return hull


def _coverage(training, validation, radius):
    origin = (min(r["easting_m"] for r in training), min(r["northing_m"] for r in training))
    points = [(r["easting_m"]-origin[0], r["northing_m"]-origin[1]) for r in training]
    hull = _hull(points)
    unsupported, distances = [], []
    for row in validation:
        p = (row["easting_m"]-origin[0], row["northing_m"]-origin[1])
        distance = min(math.dist(p, t) for t in points)
        distances.append(distance)
        inside = all(_cross(a, hull[(i+1) % len(hull)], p) >= 0 for i, a in enumerate(hull))
        if not inside or distance > radius:
            unsupported.append(row["row_id"])
    count, total = len(validation) - len(unsupported), len(validation)
    return dict(eligible_count=count, total_count=total, fraction=count/total, unsupported_ids=unsupported), max(distances)


def validate_profile_named(name, value, row_count=1, *, local_profile=None):
    """Explicit local study extension; never mutate the ordinary v1 schema.

    All original validation runs on a copied object with the one extended
    ceiling projected to 256. The original typed ceiling is restored only for
    the named local profile. No request can activate it by adding a key.
    """
    from copy import deepcopy
    if local_profile is None:
        return validate_named(name, value, row_count)
    if type(local_profile) is not str or local_profile != "m03-local-320/1":
        fail("profile.name", "unsupported_operation")
    copied = deepcopy(value)
    try:
        geometry = (copied["equivalent_sources"]["source_geometry"] if name == "Request" else
                    copied["source_geometry"] if name == "EquivalentSourcesConfig" else copied)
        bound = geometry["max_sources"]
    except (KeyError, TypeError):
        fail("profile.source_geometry")
    if type(bound) is not int or not 1 <= bound <= 320:
        fail("profile.sources", "resource_refused")
    geometry["max_sources"] = min(bound, 256)
    decoded = validate_named(name, copied, row_count)
    target = (decoded["equivalent_sources"]["source_geometry"] if name == "Request" else
              decoded["source_geometry"] if name == "EquivalentSourcesConfig" else decoded)
    target["max_sources"] = bound
    return decoded


def source_blocks(rows, config, depth, *, local_profile=None):
    validate_geometry_rows(rows)
    config = validate_profile_named("SourceGeometry", config, local_profile=local_profile)
    if type(depth) not in (float, int) or not math.isfinite(depth) or not 1 <= depth <= 2000:
        fail("sources.depth")
    if not rows or len(rows) > 400:
        fail("sources.rows", "resource_refused")
    blocks = {}
    for row in rows:
        if row["upward_m"] is None:
            fail("sources.upward", "metadata_ineligible", "partition")
        try:
            key = (math.floor((row["easting_m"]-config["origin_e_m"])/config["block_e_m"]),
                   math.floor((row["northing_m"]-config["origin_n_m"])/config["block_n_m"]))
        except (OverflowError, ValueError):
            fail("sources.block_index", "resource_refused")
        if any(not -2147483648 <= x <= 2147483647 for x in key):
            fail("sources.block_index", "resource_refused")
        blocks.setdefault(key, []).append(row)
    if len(blocks) > config["max_sources"]:
        fail("sources.count", "resource_refused", observed=len(blocks), limit=config["max_sources"])
    ids = [r["row_id"] for r in rows]
    if len(set(ids)) != len(ids):
        fail("sources.row_id")
    height = min(r["upward_m"] for r in rows) - float(depth)
    sources, row_map = [], {}
    for (e, n), members in sorted(blocks.items()):
        members = sorted(members, key=lambda r: r["row_id"])
        sid = f"B.{e}.{n}"
        try:
            east = math.fsum(r["easting_m"] for r in members) / len(members)
            north = math.fsum(r["northing_m"] for r in members) / len(members)
        except OverflowError:
            fail("sources.mean", "resource_refused")
        if not all(math.isfinite(x) for x in (east, north, height)):
            fail("sources.geometry", "resource_refused")
        sources.append(dict(source_id=sid, easting_m=east, northing_m=north, upward_m=height, count=len(members)))
        for row in members:
            row_map[row["row_id"]] = dict(row_id=row["row_id"], block_e=e, block_n=n, source_id=sid)
    return dict(sources=sources, map=[row_map[rid] for rid in ids])


def make_partitions(rows, request, *, local_profile=None):
    validate_geometry_rows(rows)
    request = validate_profile_named("Request", request, len(rows), local_profile=local_profile)
    if not 1 <= len(rows) <= 400:
        fail("partition.rows", "resource_refused", "partition")
    split = request["split"]
    if split["buffer_m"] < request["grid"]["support_radius_m"]:
        fail("SplitConfig.buffer_m")
    if digest(geometry_manifest(rows)) != split["geometry_manifest_sha256"]:
        fail("SplitConfig.geometry_manifest_sha256", "custody_mismatch", "partition")
    selected = [r for r in rows if r["sensor_id"] == request["sensor_id"]]
    flights = {r["line_id"] for r in selected if r["line_kind"] in ("flight", "reflight")}
    outer, anchors = set(split["outer_line_ids"]), set(split["anchor_line_ids"])
    if not outer <= flights or not anchors <= flights or outer & anchors:
        fail("SplitConfig.line_sets")
    used = set()
    for fold in split["inner_folds"]:
        val = set(fold["validation_line_ids"])
        if val & (used | outer | anchors) or not val <= flights:
            fail("SplitConfig.inner_folds")
        used |= val
    if used != flights - outer - anchors:
        fail("SplitConfig.inner_coverage")
    def part(ids, blocks, fold_id=None):
        validation = [r for r in selected if r["line_id"] in ids]
        rectangles = [_rect(b) for b in blocks]
        if not validation or any(not any(_contains(_point(r), b) for b in rectangles) for r in validation):
            fail("SplitConfig.validation_blocks", "metadata_ineligible", "partition")
        exclude = _buffered_ties(selected, split["heldout_blocks"] + blocks, split["buffer_m"])
        training = [r for r in selected if r["line_id"] not in ids | outer and r["row_id"] not in exclude]
        if len({r["line_id"] for r in training}) < 4:
            fail("partition.training_groups", "metadata_ineligible", "partition")
        coverage, distance = _coverage(training, validation, request["grid"]["support_radius_m"])
        if coverage["fraction"] < split["minimum_supported_fraction"]:
            fail("partition.support", "metadata_ineligible", "partition",
                 observed=coverage["fraction"], limit=split["minimum_supported_fraction"])
        sources = source_blocks(training, request["equivalent_sources"]["source_geometry"],
                                request["equivalent_sources"]["depth_candidates_m"][0], local_profile=local_profile)
        return dict(fold_id=fold_id, training_ids=[r["row_id"] for r in training],
                    validation_ids=[r["row_id"] for r in validation],
                    tie_buffer_excluded_ids=[r["row_id"] for r in rows if r["row_id"] in exclude],
                    geometry_only_coverage=coverage, max_nearest_m=distance,
                    source_block_map=sources["map"], source_positions=sources["sources"],
                    calibration_receipts=[])
    original = part(outer, split["heldout_blocks"])
    inner = [part(set(f["validation_line_ids"]), f["validation_blocks"], f["fold_id"]) for f in split["inner_folds"]]
    return dict(config=split, original_row_ids=[r["row_id"] for r in rows],
                outer_training_ids=original["training_ids"], outer_validation_ids=original["validation_ids"],
                tie_buffer_excluded_ids=original["tie_buffer_excluded_ids"], inner=inner,
                geometry_only_coverage=original["geometry_only_coverage"],
                max_nearest_m=original["max_nearest_m"], outer_source_map=original["source_block_map"],
                outer_source_positions=original["source_positions"], evaluation_count=0)


def kernel_column_scales(kernel, *, local_profile=None):
    """Unweighted ddof0 std in 1/m, before any StandardScaler numerical fallback."""
    if type(kernel) is not list or not 2 <= len(kernel) <= 400 or any(type(r) is not list for r in kernel):
        fail("kernel.rows")
    width = len(kernel[0])
    if local_profile not in (None, "m03-local-320/1") or type(local_profile) not in (str, type(None)):
        fail("profile.name", "unsupported_operation")
    if not 1 <= width <= (320 if local_profile else 256) or any(len(row) != width for row in kernel):
        fail("kernel.shape")
    scales = []
    for j in range(width):
        col = [r[j] for r in kernel]
        if any(type(x) not in (float, int) or not math.isfinite(x) or x <= 0 for x in col):
            fail("kernel.values")
        try:
            mean = math.fsum(col)/len(col)
            std = math.sqrt(math.fsum((x-mean)**2 for x in col)/len(col))
        except OverflowError:
            fail("kernel.scale", "metadata_ineligible", "fit")
        if not math.isfinite(std) or std <= 1024 * EPSILON * max(col):
            fail("kernel.nearconstant_column", "metadata_ineligible", "fit")
        scales.append(std)
    return scales


def preflight_geometry(rows, metadata, request, *, local_profile=None):
    validate_geometry_rows(rows)
    metadata = validate_named("Sidecar", metadata, len(rows))
    request = validate_profile_named("Request", request, len(rows), local_profile=local_profile)
    if not 1 <= len(rows) <= 400:
        fail("preflight.rows", "resource_refused", observed=len(rows), limit=400)
    grid, boundary = request["grid"], request["grid"]["boundary_policy"]
    exported = grid["nx"] * grid["ny"] * (2 if grid["continuation_delta_m"] is not None else 1)
    fft_e, fft_n = grid["nx"]+2*boundary["pad_e_cells"], grid["ny"]+2*boundary["pad_n_cells"]
    fft = fft_e * fft_n
    if exported > 16384 or fft_e > 2*grid["nx"] or fft_n > 2*grid["ny"] or fft > 65536:
        fail("preflight.cells", "resource_refused", observed=exported, limit=16384)
    for axis in ("e", "n"):
        start, step, count = grid[f"origin_{axis}_m"], grid[f"spacing_{axis}_m"], grid["nx" if axis == "e" else "ny"]
        last = start + step*(count-1)
        if not math.isfinite(last) or start+step == start or last-step == last:
            fail("preflight.grid_float64", "metadata_ineligible", "partition")
    selected = [r for r in rows if r["sensor_id"] == request["sensor_id"]]
    segments = [s for s in _segments(rows, request["geometry_policy"]) if s["p"]["sensor_id"] == request["sensor_id"]]
    if len(segments) > 399:
        fail("preflight.segments", "resource_refused")
    xy = [_point(r) for r in selected]
    magnitude = max(1., *(abs(c) for p in xy for c in p),
                    max(p[0] for p in xy)-min(p[0] for p in xy), max(p[1] for p in xy)-min(p[1] for p in xy))
    tolerance = 64 * EPSILON * magnitude
    flight = [s for s in segments if s["p"]["line_kind"] != "tie"]
    ties = [s for s in segments if s["p"]["line_kind"] == "tie"]
    pairs = 0
    for a in flight:
        for b in ties:
            if all(min(a["p"][key], a["q"][key]) - tolerance <= max(b["p"][key], b["q"][key]) and
                   min(b["p"][key], b["q"][key]) - tolerance <= max(a["p"][key], a["q"][key])
                   for key in ("easting_m", "northing_m")):
                pairs += 1
                if pairs > 4096:
                    fail("preflight.segment_pairs", "resource_refused", observed=pairs, limit=4096)
    sealed = make_partitions(rows, request, local_profile=local_profile)
    source_counts = [len(sealed["outer_source_positions"])] + [len(f["source_positions"]) for f in sealed["inner"]]
    return dict(rows=len(rows), lines=len({r["line_id"] for r in rows}), sensors=len({r["sensor_id"] for r in rows}),
                segments=len(segments), segment_pairs=pairs, sources=max(source_counts), fits=26,
                exported_cells=exported, fft_internal_cells=fft, source_counts=source_counts,
                geometry_manifest_sha256=digest(geometry_manifest(rows)), numerical_success=False)
