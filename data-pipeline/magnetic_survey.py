"""Metadata-only magnetic geometry eligibility and deterministic sealed partition.

No likelihood arrays, magnetic kernel, optimization or file IO. NumPy is loaded
only for the frozen geometry SVD after closed byte/schema/capacity admission.
Returned plain documents are independent snapshots, not tamperproof state.
"""

import hashlib
import math
import struct
from magnetic_survey_json import SurveyHandle, digest, fail

CLAIMS = dict(full_method_accepted=False, field_source_verified=False,
              geology_truth_known=False, online_admitted=False)


def _indices(rows):
    rows = sorted(rows)
    h = hashlib.sha256()
    for i in rows:
        h.update(struct.pack("<q", i))
    return dict(dtype="int64", shape=[len(rows)], data=rows, sha256=h.hexdigest())


def _extent(meta):
    mesh = meta["geometry"]["mesh"]
    lower, upper = mesh["origin_m"]["data"], []
    axes = []
    for origin, key in zip(lower, ("widths_x_m", "widths_y_m", "widths_z_m")):
        edge = origin
        nodes = [origin]
        for width in mesh[key]["data"]:
            next_edge = edge+width
            if (abs(next_edge) > 1e7 or next_edge <= edge
                    or abs((next_edge-edge)-width) > 1e-10*width
                    or not edge < (edge+next_edge)/2 < next_edge):
                fail("geometry", "$/geometry/mesh", "Local binary64 edge/centre fidelity failure")
            nodes.append(next_edge)
            edge = next_edge
        axes.append(nodes)
        upper.append(edge)
    xyz = meta["geometry"]["receivers_m"]["data"]
    flags = meta["geometry"]["usable"]["data"]
    rows = [tuple(xyz[3*i:3*i+3]) for i in range(len(flags))]
    for i, flag in enumerate(flags):
        if flag and all(lo <= x <= hi for x, lo, hi in zip(rows[i], lower, upper)):
            fail("geometry", "$/geometry/receivers_m", "Usable receiver inside closed full source box")
    if len({rows[i] for i, flag in enumerate(flags) if flag}) != sum(flags):
        fail("geometry", "$/geometry/receivers_m", "Exact duplicate usable coordinates")
    return rows


def _units(meta, rows):
    flags = meta["geometry"]["usable"]["data"]
    bw = meta["geometry"]["partition"]["block_width_m"]["data"]
    groups, ids = meta["acquisition"]["group_ids"], meta["acquisition"]["row_ids"]
    parent = list(range(len(rows)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        a, b = root(i), root(j)
        if a != b:
            parent[b] = a

    by_group, by_block = {}, {}
    for i, flag in enumerate(flags):
        if flag:
            block = (math.floor(rows[i][0]/bw[0]), math.floor(rows[i][1]/bw[1]))
            for table, key in ((by_group, groups[i]), (by_block, block)):
                if key in table:
                    union(i, table[key])
                else:
                    table[key] = i
    connected = {}
    for i, flag in enumerate(flags):
        if flag:
            connected.setdefault(root(i), []).append(i)
    units = {}
    unit_ids = [None]*len(rows)
    for component in connected.values():
        uid = hashlib.sha256("\n".join(sorted(ids[i] for i in component)).encode("ascii")).hexdigest()
        units[uid] = component
        for i in component:
            unit_ids[i] = uid
    ordered = sorted(units, key=lambda uid: (
        hashlib.sha256(("magnetic-geometry-seal-1|104729|"+uid).encode("ascii")).hexdigest(), uid))
    return units, ordered, unit_ids


def _buffer(candidates, forbidden, xyz, radius):
    radius2 = radius*radius
    keep, excluded = [], []
    for i in sorted(candidates):
        near = any((xyz[i][0]-xyz[j][0])**2+(xyz[i][1]-xyz[j][1])**2 <= radius2
                   for j in forbidden)
        (excluded if near else keep).append(i)
    return keep, excluded


def _rank(rows, xyz, minimum, name):
    if len(rows) < minimum or any(len({xyz[i][axis] for i in rows}) < 2 for axis in (0, 1)):
        fail("partition", "$/geometry/partition", "Insufficient partition counts/horizontal coverage: "+name)
    import numpy as np
    if np.__version__ != "2.2.6":
        fail("dependency", "$/geometry/partition", "Unreviewed NumPy geometry SVD version")
    coordinates = np.array([[xyz[i][0], xyz[i][1]] for i in rows], dtype=np.float64)
    coordinates -= coordinates.mean(axis=0)
    matrix = np.column_stack((np.ones(len(rows)), coordinates))
    try:
        singular = np.linalg.svd(matrix, compute_uv=False)
    except np.linalg.LinAlgError:
        fail("numerical", "$/geometry/partition", "Geometry SVD did not converge")
    if not np.isfinite(singular).all() or sum(singular > singular[0]*1e-12) != 3:
        fail("partition", "$/geometry/partition", "Insufficient centered geometry rank: "+name)


def _partition(meta, xyz):
    units, ordered, unit_ids = _units(meta, xyz)
    if len(units) < 12:
        fail("partition", "$/geometry/partition", "At least twelve indivisible group/block units required")
    outer_units = ordered[:math.ceil(len(ordered)/5)]
    development_units = ordered[len(outer_units):]
    outer = sorted(i for uid in outer_units for i in units[uid])
    development = sorted(i for uid in development_units for i in units[uid])
    _rank(outer, xyz, 10, "outer")
    radius = meta["geometry"]["partition"]["buffer_m"]
    folds = []
    for fold in range(3):
        validation = sorted(i for pos, uid in enumerate(development_units) if pos % 3 == fold for i in units[uid])
        candidates = sorted(set(development)-set(validation))
        fit, buffered = _buffer(candidates, outer+validation, xyz, radius)
        _rank(validation, xyz, 10, "validation")
        _rank(fit, xyz, 40, "fit")
        folds.append(dict(fit_rows=_indices(fit), validation_rows=_indices(validation),
                          buffered_rows=_indices(buffered)))
    final, _ = _buffer(development, outer, xyz, radius)
    if len(final) < 50:
        fail("partition", "$/geometry/partition", "Insufficient final_refit row count")
    p = dict(unit_ids=unit_ids, outer_rows=_indices(outer),
             development_rows=_indices(development), folds=folds)
    p["sha256"] = digest(p)
    return p, _indices(final)


def _eligibility(meta):
    rights = meta["source"]["rights"]
    reasons = []
    if rights == "unresolved":
        reasons.append("rights_unresolved")
    if rights != "redistribution_permitted":
        reasons.append("raw_mirror_forbidden")
    external = any(node["operation"] != "original" for node in meta["processing"]["nodes"])
    if external:
        reasons.append("unresolved_lineage")
    # Client binding strings alone cannot establish an accepted public M02 seam.
    reasons.extend(("optimizer_unbound", "likelihood_not_validated", "online_not_admitted"))
    return dict(local_processing=rights != "unresolved" and not external,
                redistribution=rights == "redistribution_permitted", lineage_verified=False,
                reasons=reasons)


def plan_geometry(handle):
    """Plan exactly admitted geometry, never read observation/uncertainty values."""
    if type(handle) is not SurveyHandle:
        fail("type", "$", "Closed parsed byte handle required")
    meta = handle.metadata()
    xyz = _extent(meta)
    partition, final = _partition(meta, xyz)
    geometry_identity = dict(source=dict(id=meta["source"]["id"], scope=meta["source"]["scope"]),
                             frame=meta["frame"],
                             acquisition=dict(row_ids=meta["acquisition"]["row_ids"],
                                              group_ids=meta["acquisition"]["group_ids"]),
                             geometry=meta["geometry"])
    seal = digest(geometry_identity)
    identity = dict(seal_sha256=seal,
                    configuration_sha256=digest(dict(seal_sha256=seal, field=meta["inducing_field"],
                                                     prior=meta["prior"], policy=meta["policy"])),
                    source_record_sha256=digest(dict(source=meta["source"], acquisition=meta["acquisition"],
                                                     processing=meta["processing"])),
                    observations_sha256=meta["observations"]["values_sha256"],
                    noise_sha256=meta["noise"]["values"]["sha256"])
    g, a = meta["geometry"], meta["acquisition"]
    inventory = dict(row_ids=a["row_ids"], group_ids=a["group_ids"], usable=g["usable"],
                     qc_reason=g["qc_reason"], receivers_m=g["receivers_m"])
    return dict(schema="magnetic-geometry-plan-1", identity=identity, inventory=inventory,
                partition=partition, final_refit_rows=final, eligibility=_eligibility(meta),
                preflight=dict(handle.preflight), claims=CLAIMS.copy())


def main(argv=None):
    """Explicit bounded local geometry validation/export; never calibration."""
    import argparse
    import json
    import os
    import stat
    from pathlib import Path
    from magnetic_survey_json import InputError, MAX_BYTES, parse_request
    from magnetic_survey_bundle import write_geometry
    parser = argparse.ArgumentParser(description="M04 geometry validation only, no magnetic fit")
    parser.add_argument("operation", choices=["validate"])
    parser.add_argument("--request", required=True)
    parser.add_argument("--export", required=True)
    args = parser.parse_args(argv)
    path = Path(args.request)
    try:
        if path.is_symlink():
            fail("durability", "$", "Symlink input forbidden")
        with path.open("rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                fail("durability", "$", "Regular local input file required")
            if info.st_size > MAX_BYTES:
                fail("bytes", "$", "Input byte limit exceeded")
            raw = stream.read(MAX_BYTES+1)
        handle = parse_request(raw)
        plan = plan_geometry(handle)
        write_geometry(args.export, handle)
        # No user values or full inventory in stdout; output path is caller-owned.
        print(json.dumps(dict(schema=plan["schema"], identity=plan["identity"],
                              eligibility=plan["eligibility"], claims=plan["claims"]), sort_keys=True))
        return 0
    except InputError as error:
        print(json.dumps(error.envelope(), sort_keys=True))
        return 5 if error.code == "durability" else 2
    except OSError:
        print(json.dumps(dict(schema="magnetic-input-error-1", code="durability", path="$",
                              message="Explicit local file operation failed"), sort_keys=True))
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
