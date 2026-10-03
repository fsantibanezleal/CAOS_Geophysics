"""Exact native planner/admission controls; no field or full-M02 acceptance."""

from copy import deepcopy
import hashlib
import json

import numpy as np
import pytest

import gravity_forward as forward
import gravity_survey_l2 as survey


def planning_request():
    x, y = np.meshgrid(np.arange(12) * 100. - 550., np.arange(12) * 100. - 550.)
    points = np.c_[x.ravel(), y.ravel(), np.full(144, 100.)]
    return {
        "schema": "gravity-survey-l2-plan-request-1", "frame": dict(forward.FRAME),
        "mesh": {"origin_m": np.array([-200., -200., -300.]), "hx_m": np.full(4, 100.),
                 "hy_m": np.full(4, 100.), "hz_m": np.full(3, 100.), "active": np.ones(48, dtype=bool)},
        "source": {"source_id": "authored_control", "source_kind": "synthetic_control",
                   "raw_sha256": "a" * 64, "raw_bytes": 100, "citation": "Authored continuous prism control",
                   "rights": "private_only", "processing_sha256": "b" * 64,
                   "processing_kind": "synthetic_anomaly", "quantity": "processed_gravity_anomaly",
                   "reference_description": "Fixed zero background, synthetic anomaly without absolute gravity",
                   "original_acceleration_unit": "mGal", "original_vertical_positive": "up",
                   "normalization_sha256": "c" * 64, "horizontal_reference": "Authored local metric frame",
                   "vertical_reference": "Authored zero plane", "transform_sha256": None,
                   "geometry_uncertainty": "conditional_fixed_geometry"},
        "stations": {"receivers_m": points,
                     "station_ids": tuple(f"station:{i}:{j}" for j in range(12) for i in range(12)),
                     "partition_group_ids": tuple(f"line:{j}" for j in range(12) for i in range(12)),
                     "excluded": np.zeros(144, dtype=bool), "exclusion_reasons": ("",) * 144},
        "background_mgal": np.zeros(144),
        "split": {"policy": "blocked-hash-3fold-sealed-1", "block_origin_m": np.array([-600., -600.]),
                  "block_size_m": np.array([100., 100.]), "buffer_m": 25., "seed": 104729},
        "engine": forward.ENGINE,
    }


class Hook:
    def __eq__(self, other):
        raise AssertionError("untrusted equality executed")

    def __array__(self, *args, **kwargs):
        raise AssertionError("untrusted array executed")


@pytest.mark.parametrize("field", ["origin", "axis", "product", "mask", "receivers", "background", "block"])
def test_metadata_first_exact_contract(monkeypatch, field):
    req = planning_request()
    if field == "origin": req["mesh"]["origin_m"] = np.zeros(5000)
    if field == "axis": req["mesh"]["hx_m"] = np.ones(5000)
    if field == "product": req["mesh"]["hx_m"] = req["mesh"]["hy_m"] = np.ones(65)
    if field == "mask": req["mesh"]["active"] = np.ones(5000, dtype=bool)
    if field == "receivers": req["stations"]["receivers_m"] = np.ones((2049, 3))
    if field == "background": req["background_mgal"] = np.ones(5000)
    if field == "block": req["split"]["block_size_m"] = np.ones(5000)
    def deny(*args, **kwargs):
        raise AssertionError("scan/copy/count/hash/engine before full metadata admission")
    for name in ("isfinite", "array", "count_nonzero"):
        monkeypatch.setattr(survey.np, name, deny)
    monkeypatch.setattr(survey, "_digest", deny)
    monkeypatch.setattr(survey, "forward_gravity", deny)
    with pytest.raises((TypeError, ValueError)):
        survey.plan_gravity_l2(req)


@pytest.mark.parametrize("field", ["schema", "source_kind", "seed", "buffer", "axes", "array", "array_subclass",
                                  "root_subclass", "source_subclass", "string_subclass", "unknown", "endian"])
def test_reject_hooks_before_equality_or_numpy(field):
    req = planning_request()
    if field == "schema": req["schema"] = Hook()
    if field == "source_kind": req["source"]["source_kind"] = Hook()
    if field == "seed": req["split"]["seed"] = Hook()
    if field == "buffer": req["split"]["buffer_m"] = Hook()
    if field == "axes": req["frame"]["axes"] = (Hook(), "north", "up")
    if field == "array": req["background_mgal"] = Hook()
    if field == "array_subclass": req["background_mgal"] = req["background_mgal"].view(type("Sub", (np.ndarray,), {}))
    if field == "root_subclass": req = type("Sub", (dict,), {})(req)
    if field == "source_subclass": req["source"] = type("Sub", (dict,), {})(req["source"])
    if field == "string_subclass": req["source"]["quantity"] = type("Sub", (str,), {})("processed_gravity_anomaly")
    if field == "unknown": req["raw_path"] = "untrusted"
    if field == "endian": req["background_mgal"] = req["background_mgal"].astype(">f8")
    with pytest.raises((TypeError, ValueError)):
        survey.plan_gravity_l2(req)


@pytest.mark.parametrize("field", ["unit", "sign", "quantity", "datum", "rights", "processing", "seed", "zero_buffer"])
def test_source_frame_sign_and_processing(field):
    req = planning_request()
    if field == "unit": req["frame"]["length_unit"] = "ft"
    if field == "sign": req["frame"]["vertical_positive"] = "down"
    if field == "quantity": req["source"]["quantity"] = "raw_absolute_gravity"
    if field == "datum": req["source"]["vertical_reference"] = ""
    if field == "rights": req["source"]["rights"] = "approved_field"
    if field == "processing": req["source"]["source_kind"] = "field"
    if field == "seed": req["split"]["seed"] = True
    if field == "zero_buffer": req["split"]["buffer_m"] = 0.
    with pytest.raises((TypeError, ValueError)):
        survey.plan_gravity_l2(req)


@pytest.mark.parametrize("field", ["duplicate_id", "duplicate_xyz", "missing_geometry", "mask_reason", "all_masked"])
def test_masks_missingness_duplicates_and_order(field):
    req = planning_request()
    if field == "duplicate_id": req["stations"]["station_ids"] = ("same",) * 144
    if field == "duplicate_xyz": req["stations"]["receivers_m"][1] = req["stations"]["receivers_m"][0]
    if field == "missing_geometry": req["stations"]["receivers_m"][1, 2] = np.nan
    if field == "mask_reason": req["stations"]["excluded"][0] = True
    if field == "all_masked":
        req["stations"]["excluded"][:] = True
        req["stations"]["exclusion_reasons"] = ("gap",) * 144
    with pytest.raises(ValueError):
        survey.plan_gravity_l2(req)


def test_native_digest_exact_array_and_scalar_encoding():
    a = np.array([[1., -2.], [3., 4.]])
    expected = {"array": {"dtype": "<f8", "shape": [2, 2],
                          "sha256": hashlib.sha256(a.tobytes(order="C")).hexdigest()},
                "zero": 0.0, "tuple": ["a", 1]}
    canonical = json.dumps(expected, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    assert survey._digest({"array": np.asfortranarray(a), "zero": -0., "tuple": ("a", 1)}) == hashlib.sha256(
        canonical.encode()).hexdigest()


def test_planner_private_readonly_snapshot_and_tamper():
    req = planning_request()
    original = deepcopy(req)
    plan = survey.plan_gravity_l2(req)
    assert set(plan) == {"schema", "request", "plan_sha256", "development_rows", "outer_rows", "embargo_rows",
                         "folds", "geometry", "scope"}
    assert plan["scope"] == "ordinary_local_conditional_not_field"
    np.testing.assert_array_equal(req["stations"]["receivers_m"], original["stations"]["receivers_m"])
    assert not plan["request"]["stations"]["receivers_m"].flags.writeable
    assert not plan["development_rows"].flags.writeable
    req["stations"]["receivers_m"][0, 0] += 1.
    assert plan["request"]["stations"]["receivers_m"][0, 0] != req["stations"]["receivers_m"][0, 0]
    survey._validate_plan(plan)
    corrupt = deepcopy(plan)
    corrupt["scope"] = "accepted_field"
    with pytest.raises(ValueError): survey._validate_plan(corrupt)


@pytest.mark.parametrize('wrapped', [False, True])
def test_empty_container_budget_before_semantics_scans_copy_or_engine(monkeypatch, wrapped):
    # Shared, small physical allocation. No giant recursive/tree fixture.
    value = (((),) * 32768,) * 5
    if wrapped:
        req = planning_request()
        req['source']['citation'] = value
        value = req
    def deny(*args, **kwargs): raise AssertionError('work before bounded metadata rejection')
    for name in ('isfinite', 'array', 'count_nonzero'):
        monkeypatch.setattr(survey.np, name, deny)
    for name in ('_digest', '_snapshot', '_planning_metadata', 'forward_gravity'):
        monkeypatch.setattr(survey, name, deny)
    with pytest.raises(ValueError, match='metadata'):
        survey._native_metadata(value)


def test_primitive_scalar_limit_does_not_count_empty_containers():
    # Under256KiB but >32768 containers: not new scalar-count semantics.
    survey._native_metadata((((),) * 10000,) * 4)


@pytest.mark.parametrize('kind', ['containers', 'escaped_unicode', 'array', 'primitives'])
def test_proposed_exact_metadata_boundary_without_array_work(monkeypatch, kind):
    # Prospective clarification control, not authority to change the SDD.
    if kind == 'containers':
        value, descriptor = (((),), (), {'x': ()}), [[[]], [], {'x': []}]
    elif kind == 'escaped_unicode':
        value, descriptor = {'key\n': ('\"\\\t', 'é', '\U0001f600')}, {'key\n': ['\"\\\t', 'é', '\U0001f600']}
    elif kind == 'array':
        value = np.zeros((3, 2))
        descriptor = {'dtype': '<f8', 'shape': [3, 2], 'sha256': '0' * 64}
    else:
        value, descriptor = (-0., True, None, -(2**63)), [0.0, True, None, -(2**63)]
    size = len(json.dumps(descriptor, sort_keys=True, ensure_ascii=False, allow_nan=False,
                          separators=(',', ':')).encode('utf-8'))
    def deny(*args, **kwargs): raise AssertionError('values/digest/copy before metadata budget')
    for name in ('isfinite', 'array', 'count_nonzero'):
        monkeypatch.setattr(survey.np, name, deny)
    for name in ('_digest', '_snapshot', '_planning_metadata', 'forward_gravity'):
        monkeypatch.setattr(survey, name, deny)
    monkeypatch.setattr(survey, 'MAX_METADATA_BYTES', size)
    survey._native_metadata(value)
    monkeypatch.setattr(survey, 'MAX_METADATA_BYTES', size - 1)
    with pytest.raises(ValueError, match='metadata'):
        survey._native_metadata(value)


def test_proposed_scalar_accounting_excludes_descriptor_and_containers(monkeypatch):
    # Test-only small budgets; production caps remain frozen.
    monkeypatch.setattr(survey, 'MAX_SCALARS', 4)
    survey._native_metadata({'x': ((), ('a', False, None))})
    with pytest.raises(ValueError, match='scalar-count'):
        survey._native_metadata({'x': ((), ('a', False, None, 1))})
    monkeypatch.setattr(survey, 'MAX_SCALARS', 1)
    survey._native_metadata(np.zeros(3))
