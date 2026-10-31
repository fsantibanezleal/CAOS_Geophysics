"""Authored S2 geometry only. No magnetic truth, field acquisition or noise."""

import hashlib
import struct


def descriptor(dtype, shape, data):
    formats = {"float64": "d", "int64": "q", "bool": "?"}
    values = [float(x) for x in data] if dtype == "float64" else list(data)
    payload = b"".join(struct.pack("<"+formats[dtype], x) for x in values)
    return dict(dtype=dtype, shape=list(shape), data=values,
                sha256=hashlib.sha256(payload).hexdigest())


def geometry():
    """Original ordered heterogeneous heights and explicit flight groups."""
    ids, groups, xyz = [], [], []
    for line in range(12):
        for sample in range(24):
            ids.append(f"S2-L{line:02d}-S{sample:02d}")
            groups.append(f"S2-L{line:02d}")
            xyz.extend((-200+80*sample, 600*line, 120+10*(sample % 3)))
    assert descriptor("float64", [288, 3], xyz)["sha256"] == (
        "b784c2e62476cc8926a948fa3c20787df9dcf017a54497d1a696fddb2026538a")
    return dict(row_ids=ids, group_ids=groups,
                timestamp_policy="unavailable_declared", timestamps=None,
                geometry_basis="Authored S2 local ENU geometry, not field"), dict(
        receivers_m=descriptor("float64", [288, 3], xyz),
        usable=descriptor("bool", [288], [True]*288), qc_reason=["accepted"]*288,
        mesh=dict(origin_m=descriptor("float64", [3], [-400, -300, -1800]),
                  widths_x_m=descriptor("float64", [11], [200]*11),
                  widths_y_m=descriptor("float64", [12], [600]*12),
                  widths_z_m=descriptor("float64", [4], [150, 250, 400, 1000]),
                  active=descriptor("bool", [528], [True]*528)),
        partition=dict(name="magnetic-geometry-seal-1",
                       block_width_m=descriptor("float64", [2], [250, 500]),
                       buffer_m=200.0, seed=104729))
