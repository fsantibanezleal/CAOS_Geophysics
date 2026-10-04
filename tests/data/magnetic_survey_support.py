"""Protocol-only null payload control, not physical field or inverse evidence."""

import hashlib
import importlib.util
import json
from pathlib import Path

_path = Path(__file__).parents[1]/"fixtures"/"magnetic_survey"/"generate.py"
_spec = importlib.util.spec_from_file_location("magnetic_geometry_fixture", _path)
fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fixture)
descriptor = fixture.descriptor


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def request():
    acquisition, geometry = fixture.geometry()
    values = descriptor("float64", [288, 3], [0]*864)
    params = {"kind": "identity"}
    return dict(
        schema="magnetic-survey-inversion-1", intent="local_calibrate",
        source=dict(id="S2-protocol", kind="authored_synthetic", original_sha256="a"*64,
                    original_bytes=1, provider_url=None, rights="private_user_supplied",
                    scope="complete_acquisition", citation="Authored protocol-only control"),
        frame=dict(axes="ENU", coordinate_unit="m", vertical_positive="up",
                   crs="Authored local Cartesian ENU", vertical_datum="Authored origin",
                   origin=descriptor("float64", [3], [0, 0, 0]), transform_sha256="b"*64),
        inducing_field=dict(kind="uniform_inducing_field", F_nT=50000.0, I_deg=37.0,
                            D_deg=-73.0, reference_epoch="Authored uniform reference",
                            provenance="Authored conditional field, not IGRF",
                            source_sha256="c"*64, spatial_policy="explicit_uniform_approximation"),
        acquisition=acquisition, geometry=geometry,
        processing=dict(nodes=[dict(id="original", parents=[], operation="original",
                                    input_sha256="a"*64, output_sha256=values["sha256"],
                                    parameters_sha256=digest(params), parameters=params,
                                    citation="Declared secondary ENU protocol payload")],
                        final_node="original", quantity="secondary_enu_nT",
                        background_relation="secondary_field_declared",
                        eligibility="explicit_induced_assumption"),
        observations=dict(quantity="secondary_enu_nT", unit="nT", values=values,
                          values_sha256=values["sha256"]),
        noise=dict(kind="diagonal_sd", unit="nT",
                   values=descriptor("float64", [288, 3], [0.5]*864),
                   basis="explicit_conditional_gaussian", citation="Authored protocol SD",
                   cross_partition_dependence="declared_absent"),
        prior=dict(lower_si=descriptor("float64", [528], [0]*528),
                   upper_si=descriptor("float64", [528], [0.1]*528),
                   start_si=descriptor("float64", [528], [0]*528),
                   reference_si=descriptor("float64", [528], [0]*528), chi_scale_si=0.01,
                   lengths_m=descriptor("float64", [3], [400, 1200, 600]),
                   reference_in_smooth=True, spatial_weights="none", basis="Authored protocol prior"),
        policy=dict(name="magnetic-nested-l2-irls-1",
                    betas=[.0001, .001, .01, .1, 1., 10., 100., 1000.],
                    penalties=["l2", "sparse_smallness"], resource_profile="local_bounded",
                    optimizer_binding=dict(accepted_source=None, accepted_export=None, epoch=None)))


def encode(doc):
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def at(doc, path):
    for item in path.split("/"):
        doc = doc[int(item)] if type(doc) is list else doc[item]
    return doc


def rehash(doc, path):
    value = at(doc, path)
    value["sha256"] = descriptor(value["dtype"], value["shape"], value["data"])["sha256"]
    if path == "observations/values":
        doc["observations"]["values_sha256"] = value["sha256"]
        doc["processing"]["nodes"][-1]["output_sha256"] = value["sha256"]
