"""Independent authored S2 magnetic acquisitions (never field observations).

The geometry is sealed before values are evaluated. Truth fields use direct
Choclo rectangular-prism calls on off-grid bodies; the production SimPEG
forward/inversion mesh is not used as a truth generator.
"""

from decimal import Decimal, localcontext
import hashlib
import importlib.metadata
import json
import struct

import choclo
from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as MU0
import numpy as np

SOURCE_VERSION = "m04-independent-choclo-s2-1"
BASE_SEED = 20261004
ENGINE_VERSION = "Choclo-0.3.2"
NUMPY_VERSION = "2.2.6"
if importlib.metadata.version("choclo") != "0.3.2":
    raise RuntimeError("M04 truth generator requires the pinned Choclo 0.3.2 runtime")
if np.__version__ != NUMPY_VERSION:
    raise RuntimeError("M04 noise generator requires the pinned NumPy 2.2.6 runtime")


def descriptor(dtype, shape, data):
    formats = {"float64": "d", "int64": "q", "bool": "?"}
    values = [float(x) for x in data] if dtype == "float64" else list(data)
    payload = b"".join(struct.pack("<"+formats[dtype], x) for x in values)
    return dict(dtype=dtype, shape=list(shape), data=values,
                sha256=hashlib.sha256(payload).hexdigest())


def geometry(line_count=12):
    """Original ordered heterogeneous heights and explicit flight groups."""
    if type(line_count) is not int or not 1 <= line_count <= 12:
        raise ValueError("line_count must be an integer from 1 through 12")
    ids, groups, xyz = [], [], []
    for line in range(line_count):
        for sample in range(24):
            ids.append(f"S2-L{line:02d}-S{sample:02d}")
            groups.append(f"S2-L{line:02d}")
            xyz.extend((-200+80*sample, 600*line, 120+10*(sample % 3)))
    if line_count == 12:
        assert descriptor("float64", [288, 3], xyz)["sha256"] == (
            "b784c2e62476cc8926a948fa3c20787df9dcf017a54497d1a696fddb2026538a")
    return dict(row_ids=ids, group_ids=groups,
                timestamp_policy="unavailable_declared", timestamps=None,
                geometry_basis="Authored S2 local ENU geometry, not field"), dict(
        receivers_m=descriptor("float64", [line_count*24, 3], xyz),
        usable=descriptor("bool", [line_count*24], [True]*(line_count*24)), qc_reason=["accepted"]*(line_count*24),
        mesh=dict(origin_m=descriptor("float64", [3], [-400, -300, -1800]),
                  widths_x_m=descriptor("float64", [11], [200]*11),
                  widths_y_m=descriptor("float64", [12], [600]*12),
                  widths_z_m=descriptor("float64", [4], [150, 250, 400, 1000]),
                  active=descriptor("bool", [528], [True]*528)),
        partition=dict(name="magnetic-geometry-seal-1",
                       block_width_m=descriptor("float64", [2], [250, 500]),
                       buffer_m=200.0, seed=104729))


_QUANTITIES = ("secondary_enu_nT", "linear_tmi_nT", "exact_total_anomaly_nT")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _body_bounds(bounds_enu):
    """Convert ENU body limits to Choclo's east/north/down prism convention."""
    e0, e1, n0, n1, u0, u1 = bounds_enu
    return (e0, e1, n0, n1, -u1, -u0)


def _field_vector(amplitude_nt, inclination_deg, declination_deg):
    inc, dec = np.deg2rad([inclination_deg, declination_deg])
    # Choclo uses east/north/down; induction is specified by ENU inclination.
    unit = np.array([np.cos(inc)*np.sin(dec), np.cos(inc)*np.cos(dec), -np.sin(inc)])
    return unit, unit * (amplitude_nt * 1e-9)


def _truth_components(receivers_enu, bodies, field):
    unit, b0_t = _field_vector(*field)
    receiver_edn = np.asarray(receivers_enu, dtype=np.float64).copy()
    receiver_edn[:, 2] *= -1.0
    total = np.zeros((len(receiver_edn), 3), dtype=np.float64)
    truth_records = []
    for body in bodies:
        bounds = _body_bounds(body["bounds_enu_m"])
        induced = body.get("chi_si", 0.0) * b0_t / MU0
        remanent_enu = np.asarray(body.get("remanence_a_per_m", (0., 0., 0.)), dtype=np.float64)
        remanent_edn = remanent_enu * np.array([1., 1., -1.])
        magnetization_edn = induced + remanent_edn
        for index, receiver in enumerate(receiver_edn):
            total[index] += np.asarray(choclo.prism.magnetic_field(
                *receiver, *bounds, *magnetization_edn), dtype=np.float64) * 1e9
        truth_records.append({"bounds_enu_m": list(body["bounds_enu_m"]),
                              "chi_si": float(body.get("chi_si", 0.0)),
                              "remanence_enu_a_per_m": remanent_enu.tolist(),
                              "total_magnetization_edn_a_per_m": magnetization_edn.tolist()})
    return total, truth_records, unit


def _observable(components_nt, field, quantity):
    if quantity == "secondary_enu_nT":
        return components_nt.reshape(-1).tolist()
    unit, _ = _field_vector(*field)
    if quantity == "linear_tmi_nT":
        return (components_nt @ unit).tolist()
    if quantity != "exact_total_anomaly_nT":
        raise ValueError("unsupported magnetic quantity")
    f_nt = float(field[0])
    direction = np.asarray(unit, dtype=np.float64)
    result = []
    # Direct Decimal80 norm subtraction, independent of the production
    # rationalized formula and of float64 cancellation at small anomalies.
    with localcontext() as ctx:
        ctx.prec = 80
        f = Decimal.from_float(f_nt)
        for vector in components_nt:
            projection = sum((Decimal.from_float(float(v))*Decimal.from_float(float(a))
                              for v, a in zip(vector, direction)), Decimal(0))
            squared = sum((Decimal.from_float(float(v))**2 for v in vector), Decimal(0))
            result.append(float((f*f+2*f*projection+squared).sqrt()-f))
    return result


def _case_bodies(regime):
    a = [
        {"bounds_enu_m": [310., 770., 1700., 2570., -510., -130.], "chi_si": .012},
        {"bounds_enu_m": [960., 1430., 3980., 4830., -980., -420.], "chi_si": .021},
    ]
    if regime == "A":
        return a
    if regime == "B":
        return [{**a[0], "chi_si": .025}, {**a[1], "chi_si": .003}]
    if regime == "C":
        return [{**a[0], "bounds_enu_m": [310., 770., 1700., 2570., -1050., -470.], "chi_si": .021}, a[1]]
    if regime == "D":
        return [{**a[0], "remanence_a_per_m": [8., -5.5, 2.3]}, a[1]]
    if regime == "E":
        return a
    if regime == "F":
        return []
    raise ValueError("regime must be A, B, C, D, E, or F")


def _request_document(regime, quantity, acquisition, geometry_spec, observed):
    import hashlib

    receiver_count = len(acquisition["row_ids"])
    components_per_row = 3 if quantity == "secondary_enu_nT" else 1
    observed = np.asarray(observed, dtype=np.float64)
    obs = descriptor("float64", [receiver_count, components_per_row], observed.tolist())
    noise_desc = descriptor("float64", [receiver_count, components_per_row], [.5]*len(observed))
    params = {"generator": SOURCE_VERSION, "regime": regime, "quantity": quantity,
              "truth_engine": ENGINE_VERSION, "noise_engine": f"NumPy-{NUMPY_VERSION}-PCG64",
              "noise_seed_base": BASE_SEED,
              "pcg64_spawn_key": [BASE_SEED, ord(regime)-ord("A"), _QUANTITIES.index(quantity)]}
    payload = {"row_ids": acquisition["row_ids"], "receivers_m": geometry_spec["receivers_m"],
               "quantity": quantity, "values": obs, "noise_sd_nT": .5,
               "generator": params}
    original = _canonical(payload)
    original_hash = hashlib.sha256(original).hexdigest()
    processing_parameters = {"kind": "identity"}
    processing_parameters_sha = hashlib.sha256(_canonical(processing_parameters)).hexdigest()
    field_inc, field_dec = (-35., -100.) if regime == "E" else (37., -73.)
    field_record = dict(kind="uniform_inducing_field", F_nT=50000.0,
                        I_deg=field_inc, D_deg=field_dec,
                        reference_epoch="authored synthetic uniform field",
                        provenance="Authored control; not IGRF or field metadata",
                        source_sha256=hashlib.sha256(_canonical({"field": [field_inc, field_dec],
                                                                  "F_nT": 50000.0})).hexdigest(),
                        spatial_policy="explicit_uniform_approximation")
    processing = dict(nodes=[dict(id="original", parents=[], operation="original",
                                  input_sha256=original_hash, output_sha256=obs["sha256"],
                                  parameters_sha256=processing_parameters_sha,
                                  parameters=processing_parameters,
                                  citation="Authored independent S2 synthetic control")],
                      final_node="original", quantity=quantity,
                      background_relation={"secondary_enu_nT": "secondary_field_declared",
                                          "linear_tmi_nT": "projection_of_secondary_declared",
                                          "exact_total_anomaly_nT": "total_norm_minus_declared_uniform_F"}[quantity],
                      eligibility="explicit_induced_assumption")
    return dict(
        schema="magnetic-survey-inversion-1", intent="local_calibrate",
        source=dict(id=f"S2-{regime}-{quantity}", kind="authored_synthetic",
                    original_sha256=original_hash, original_bytes=len(original), provider_url=None,
                    rights="private_user_supplied", scope="complete_acquisition" if regime != "F" else "declared_subset",
                    citation="Authored independent Choclo synthetic acquisition; not field observations"),
        frame=dict(axes="ENU", coordinate_unit="m", vertical_positive="up",
                   crs="Authored local Cartesian ENU", vertical_datum="Authored origin",
                   origin=descriptor("float64", [3], [0., 0., 0.]),
                   transform_sha256=hashlib.sha256(b"authored-local-ENU-origin").hexdigest()),
        inducing_field=field_record, acquisition=acquisition, geometry=geometry_spec,
        processing=processing, observations=dict(quantity=quantity, unit="nT", values=obs,
                                                 values_sha256=obs["sha256"]),
        noise=dict(kind="diagonal_sd", unit="nT", values=noise_desc,
                   basis="explicit_conditional_gaussian",
                   citation="Authored conditional SD 0.5 nT per scalar component",
                   cross_partition_dependence="declared_absent"),
        prior=dict(lower_si=descriptor("float64", [528], [0.]*528),
                   upper_si=descriptor("float64", [528], [.1]*528),
                   start_si=descriptor("float64", [528], [0.]*528),
                   reference_si=descriptor("float64", [528], [0.]*528),
                   chi_scale_si=.01, lengths_m=descriptor("float64", [3], [400., 1200., 600.]),
                   reference_in_smooth=True, spatial_weights="none", basis="Authored frozen S2 prior"),
        policy=dict(name="magnetic-nested-l2-irls-1",
                    betas=[.0001, .001, .01, .1, 1., 10., 100., 1000.],
                    penalties=["l2", "sparse_smallness"],
                    optimizer_binding=dict(accepted_source=None, accepted_export=None, epoch=None),
                    resource_profile="local_bounded"))


def acquisition_case(regime, quantity):
    """Return (closed request, separate truth record) for a frozen S2 case.

    Request bytes do not contain body bounds, true susceptibility, remanence,
    truth components, or noise-free predictions. Regime E deliberately declares
    the wrong field in the request while its observations use the A field.
    Regime F is an exact zero realization; its four-flight geometry is expected
    to fail the twelve-unit planning minimum without relaxing it.
    """
    if regime not in "ABCDEF" or len(regime) != 1:
        raise ValueError("regime must be one of A-F")
    if quantity not in _QUANTITIES:
        raise ValueError("unsupported magnetic quantity")
    line_count = 4 if regime == "F" else 12
    acquisition, geometry_spec = geometry(line_count)
    receivers = np.asarray(geometry_spec["receivers_m"]["data"], dtype=np.float64).reshape(-1, 3)
    components_per_row = 3 if quantity == "secondary_enu_nT" else 1
    provisional = _request_document(regime, quantity, acquisition, geometry_spec,
                                    np.zeros(len(receivers)*components_per_row))
    # Seal the exact geometry before evaluating Choclo or creating any noise.
    from magnetic_survey import plan_geometry
    from magnetic_survey_json import InputError, parse_request
    parsed_geometry = parse_request(_canonical(provisional))
    if regime == "F":
        try:
            plan_geometry(parsed_geometry)
        except InputError as error:
            if error.code != "partition":
                raise
            geometry_plan = None
        else:
            raise AssertionError("four-flight coverage negative unexpectedly passed geometry planning")
    else:
        geometry_plan = plan_geometry(parsed_geometry)
        partition = geometry_plan["partition"]
        if (len(partition["unit_ids"]) != 288 or len(partition["outer_rows"]["data"]) != 72
                or len(partition["development_rows"]["data"]) != 216
                or len(geometry_plan["final_refit_rows"]["data"]) != 216
                or any(len(fold["fit_rows"]["data"]) != 144
                       or len(fold["validation_rows"]["data"]) != 72
                       or len(fold["buffered_rows"]["data"]) != 0
                       for fold in partition["folds"])):
            raise AssertionError("frozen S2 geometry membership differs from the approved fixture")
    truth_field = (50000.0, 37.0, -73.0)
    declared_field = (-35.0, -100.0) if regime == "E" else truth_field[1:]
    actual_field = (truth_field[0], *truth_field[1:])
    if regime == "F":
        components, truth_bodies = np.zeros((len(receivers), 3)), []
        clean = np.zeros(len(receivers)*components_per_row)
    else:
        components, truth_bodies, _ = _truth_components(receivers, _case_bodies(regime), actual_field)
        clean = _observable(components, actual_field, quantity)
    if regime == "F":
        observed = np.zeros(len(clean), dtype=np.float64)
    else:
        quantity_index = _QUANTITIES.index(quantity)
        regime_index = ord(regime)-ord("A")
        seed_sequence = np.random.SeedSequence([BASE_SEED, regime_index, quantity_index])
        rng = np.random.Generator(np.random.PCG64(seed_sequence))
        observed = np.asarray(clean, dtype=np.float64) + rng.normal(0.0, .5, size=len(clean))

    request_doc = _request_document(regime, quantity, acquisition, geometry_spec, observed)
    truth = dict(schema="magnetic-synthetic-truth-1", source_version=SOURCE_VERSION,
                 regime=regime, quantity=quantity, truth_field={"F_nT": truth_field[0],
                 "I_deg": truth_field[1], "D_deg": truth_field[2]},
                 declared_inversion_field={"I_deg": declared_field[0], "D_deg": declared_field[1]},
                 bodies=truth_bodies, clean_secondary_components_nT=components.tolist(),
                 clean_observable_nT=np.asarray(clean, dtype=np.float64).tolist(), noise_seed=BASE_SEED,
                 noise_spawn_key=[BASE_SEED, ord(regime)-ord("A"), _QUANTITIES.index(quantity)],
                 geometry_seal_sha256=(geometry_plan["identity"]["seal_sha256"]
                                       if geometry_plan is not None else None),
                 request_source_sha256=request_doc["source"]["original_sha256"],
                 claims={"field_observation": False, "geology_truth": False,
                         "optimizer_accepted": False, "inversion_accepted": False})
    return request_doc, truth
