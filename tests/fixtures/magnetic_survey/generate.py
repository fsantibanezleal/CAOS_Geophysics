"""Frozen authored S2 geometry and independent evaluator acquisitions, never field.

geometry() remains stdlib-only and value-free. generate_control() first checks
the frozen geometry then lazily calls actual Choclo, not the inverse kernel.
Evaluator bodies and clean signals are never part of modelling requests.
"""

import hashlib
import json
import math
import struct
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path


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


QUANTITIES = ("secondary_enu_nT", "linear_tmi_nT", "exact_total_anomaly_nT")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _geometry_receipt(acquisition, spec):
    """Independent exact membership for the already frozen S2, before values."""
    frozen_hash = hashlib.sha256(_canonical(dict(acquisition=acquisition, geometry=spec))).hexdigest()
    if frozen_hash != "c1f25af64ed06a896bcddf5990180c82c2021687978b2cbe840f00317ea1014f":
        raise ValueError("S2: frozen geometry metadata changed before truth generation")
    ids = [f"S2-L{line:02d}-S{sample:02d}" for line in range(12) for sample in range(24)]
    groups = [f"S2-L{line:02d}" for line in range(12) for _ in range(24)]
    xyz = spec["receivers_m"]["data"]
    coordinate_hash = descriptor("float64", [288, 3], xyz)["sha256"]
    expected = "b784c2e62476cc8926a948fa3c20787df9dcf017a54497d1a696fddb2026538a"
    if (acquisition["row_ids"] != ids or acquisition["group_ids"] != groups
            or coordinate_hash != expected or spec["receivers_m"]["sha256"] != expected
            or spec["partition"] != dict(name="magnetic-geometry-seal-1",
                block_width_m=descriptor("float64", [2], [250, 500]), buffer_m=200., seed=104729)):
        raise ValueError("S2: frozen geometry changed before truth generation")
    units = []
    for line in range(12):
        rows = list(range(line*24, (line+1)*24))
        uid = hashlib.sha256("\n".join(ids[i] for i in rows).encode("ascii")).hexdigest()
        units.append(dict(id=uid, rows=rows))
    units.sort(key=lambda unit: (hashlib.sha256(
        ("magnetic-geometry-seal-1|104729|"+unit["id"]).encode("ascii")).hexdigest(), unit["id"]))
    outer = sorted(i for unit in units[:3] for i in unit["rows"])
    development = sorted(i for unit in units[3:] for i in unit["rows"])
    folds = []
    for fold in range(3):
        validation = sorted(i for position, unit in enumerate(units[3:])
                            if position % 3 == fold for i in unit["rows"])
        fit = [i for i in development if i not in validation]
        # Known S2: separate flights >=600m; buffer200m cannot remove fit rows.
        folds.append(dict(fit=fit, validation=validation, buffered=[]))
    membership = dict(units=units, outer=outer, development=development,
                      folds=folds, final=development)
    membership_hash = hashlib.sha256(_canonical(membership)).hexdigest()
    if membership_hash != "2336754f197bcf8470fdcf267df80af962f2483860bad37b5dacefb9691f2d45":
        raise ValueError("S2: frozen geometry membership changed")
    return coordinate_hash, membership_hash


def _bodies(regime):
    if regime == "F":
        return []
    bodies = [dict(bounds_m=[310., 770., 1700., 2570., -510., -130.],
                   chi_si=.012, remanence_A_m=[0., 0., 0.]),
              dict(bounds_m=[960., 1430., 3980., 4830., -980., -420.],
                   chi_si=.021, remanence_A_m=[0., 0., 0.])]
    if regime == "B":
        bodies[0]["chi_si"], bodies[1]["chi_si"] = .025, .003
    if regime == "C":
        bodies[0]["bounds_m"][-2:] = [-1050., -470.]
        bodies[0]["chi_si"] = .021
    if regime == "D":
        bodies[0]["remanence_A_m"] = [8., -5.5, 2.3]
    return bodies


def generate_control(regime, quantity):
    """Generate one exact declared evaluator control; no fitting or verdict upgrade.

Each quantity uses a recorded PCG64 seed20261004 stream of its own shape.
Scalar lanes share a paired realization; no independence across controls is
claimed. F supplies explicitly zero observations, not an assertion that the
rounded background vector has exactly scalar norm F. Its algebraic clean
scalar baseline is retained separately. SD remains the declared0.5nT control.
"""
    if type(regime) is not str or type(quantity) is not str:
        raise TypeError("S2: literal regime and quantity strings required")
    if regime not in tuple("ABCDEF") or quantity not in QUANTITIES:
        raise ValueError("S2: undeclared regime or quantity")
    acquisition, spec = geometry()
    coordinate_hash, membership_hash = _geometry_receipt(acquisition, spec)
    import numpy as np
    import choclo
    from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as mu0
    if np.__version__ != "2.2.6" or choclo.__version__ != "v0.3.2":
        raise RuntimeError("S2: unreviewed truth/noise runtime")
    source = Path(choclo.__file__).parent/"prism"/"_magnetic.py"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash != "4e41feee63a5d7a5997dd35d99fe17d62016db003568fe7f7f6108724163254b":
        raise RuntimeError("S2: unreviewed Choclo physical source")
    truth_field = dict(F_nT=50000., I_deg=37., D_deg=-73.)
    declared_field = dict(truth_field)
    if regime == "E":
        declared_field.update(I_deg=-35., D_deg=-100.)
    inclination, declination = math.radians(37.), math.radians(-73.)
    direction = np.array([math.cos(inclination)*math.sin(declination),
                          math.cos(inclination)*math.cos(declination), -math.sin(inclination)])
    background = 50000.*direction
    xyz = np.array(spec["receivers_m"]["data"], dtype=np.float64).reshape(288, 3)
    bodies = _bodies(regime)
    components = np.zeros((288, 3), dtype=np.float64)
    for body in bodies:
        magnetization = body["chi_si"]*background*1e-9/mu0 + np.array(body["remanence_A_m"])
        body["magnetization_A_m"] = magnetization.tolist()
        components += np.array([choclo.prism.magnetic_field(*r, *body["bounds_m"], *magnetization)
                                for r in xyz], dtype=np.float64)*1e9
    if not np.isfinite(components).all():
        raise RuntimeError("S2: nonfinite independent physical truth")
    if quantity == QUANTITIES[0]:
        signal = components.copy()
    elif quantity == QUANTITIES[1]:
        signal = (components @ direction).reshape(288, 1)
    else:
        # Portable independent direct norm, never production rational expression.
        with localcontext() as context:
            context.prec = 80
            context.rounding = ROUND_HALF_EVEN
            b0 = [Decimal.from_float(float(x)) for x in background]
            amplitude = Decimal.from_float(50000.)
            scalar = []
            for row in components:
                radicand = sum((b+Decimal.from_float(float(x)))**2 for b, x in zip(b0, row))
                if not radicand.is_finite() or radicand <= 0:
                    raise RuntimeError("S2: invalid direct norm radicand")
                scalar.append(float(radicand.sqrt()-amplitude))
        signal = np.array(scalar, dtype=np.float64).reshape(288, 1)
    rng = np.random.Generator(np.random.PCG64(20261004))
    before = rng.bit_generator.state
    if regime == "F":
        observed = np.zeros_like(signal)
        realization = "explicit_zero_observation_control"
    else:
        observed = signal + rng.normal(0., .5, size=signal.shape)
        realization = "recorded_conditional_gaussian"
    sd = np.full(signal.shape, .5, dtype=np.float64)
    record = dict(schema="authored-magnetic-acquisition-1", regime=regime, quantity=quantity,
                  acquisition=acquisition, frame=dict(axes="ENU", unit="m", vertical_positive="up",
                    crs="Authored local Cartesian ENU", vertical_datum="Authored origin"),
                  declared_field=declared_field, geometry=spec,
                  observations=descriptor("float64", observed.shape, observed.ravel()),
                  noise=dict(kind="diagonal_sd", unit="nT", basis="explicit_conditional_gaussian",
                             values=descriptor("float64", sd.shape, sd.ravel())))
    raw = _canonical(record)
    provenance = dict(generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      geometry_sha256=coordinate_hash, membership_sha256=membership_hash,
                      geometry_metadata_sha256=hashlib.sha256(
                          _canonical(dict(acquisition=acquisition, geometry=spec))).hexdigest(),
                      truth_engine="choclo-0.3.2", truth_source_sha256=source_hash,
                      noise_engine="numpy-2.2.6-PCG64", noise_seed=20261004,
                      noise_realization=realization, rng_state_before=before, rng_state_after=rng.bit_generator.state,
                      scalar_oracle="Decimal80.from_float.direct.sqrt.minus.F",
                      original_sha256=hashlib.sha256(raw).hexdigest(), fit_executed=False)
    def snapshot(value):
        owned = np.array(value, dtype=np.float64, order="C", copy=True)
        owned.flags.writeable = False
        return owned
    return dict(schema="magnetic-s2-control-1", kind="authored_synthetic", regime=regime,
                quantity=quantity, acquisition=acquisition, geometry=spec,
                truth_field=truth_field, declared_field=declared_field, bodies=bodies,
                secondary_enu_nT=snapshot(components), signal_nT=snapshot(signal),
                observed_nT=snapshot(observed), sd_nT=snapshot(sd), original_bytes=raw,
                provenance=provenance, verdict="not_evaluated")
