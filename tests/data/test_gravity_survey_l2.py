"""Exact native planner/admission controls; no field or full-M02 acceptance."""

from copy import deepcopy
import hashlib
import json

import numpy as np
import pytest

import gravity_forward as forward
import gravity_l2 as l2
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


def calibration_request():
    """Test-owned compact development contract, not field/upload admission."""
    plan = survey.plan_gravity_l2(planning_request())
    rows = plan['development_rows']
    observed = {'rows': rows.copy(), 'gz_up_mgal': np.zeros(len(rows)),
                'acceleration_unit': 'mGal', 'vertical_positive': 'up'}
    observed['values_sha256'] = survey._digest(observed)
    noise = {'kind': 'diagonal_sd', 'values': np.full(len(rows), .01), 'unit': 'mGal',
             'basis': 'explicit_conditional_gaussian', 'citation': 'Authored fixed conditional Gaussian scale',
             'cross_partition_dependence': 'declared_absent'}
    noise['values_sha256'] = survey._digest({key: noise[key] for key in ('kind', 'unit', 'values')}
                                           | {'rows': rows})
    a = len(plan['geometry']['active_cell_indices'])
    prior = {'lower_kg_m3': np.full(a, -1500.), 'upper_kg_m3': np.full(a, 1500.),
             'start_kg_m3': np.zeros(a), 'reference_kg_m3': np.zeros(a), 'density_scale_kg_m3': 1000.,
             'lengths_m': np.array([80., 90., 70.]), 'basis': 'Authored frozen zero reference, signed bounds',
             'reference_in_smooth': True, 'spatial_weights': 'none',
             'geometry_sha256': survey._digest(plan['geometry'])}
    return {'schema': 'gravity-survey-l2-calibration-request-1', 'plan': plan,
            'observations': observed, 'noise': noise, 'prior': prior,
            'policy': {'name': 'ordinary-l2-beta-grid-1', 'beta_candidates': l2.BETA_CANDIDATES,
                       'optimizer': 'projected-gncg-recorded-1', 'training': 'not_applicable_classical'},
            'runtime_epoch': l2.RUNTIME_EPOCH}


@pytest.mark.parametrize('field', ['full_observations', 'oversize_covariance', 'noise_unit', 'noise_basis',
                                  'prior_shape', 'prior_scale', 'prior_lengths', 'prior_reference_flag',
                                  'seed_override', 'beta_type', 'outer_payload', 'runtime'])
def test_calibration_metadata_before_any_scan_copy_hash_or_engine(monkeypatch, field):
    req = calibration_request()
    if field == 'full_observations': req['observations']['gz_up_mgal'] = np.zeros(144)
    if field == 'oversize_covariance':
        req['noise'].update(kind='full_covariance', values=np.eye(2049), unit='mGal^2')
    if field == 'noise_unit': req['noise']['unit'] = 'microGal'
    if field == 'noise_basis': req['noise']['basis'] = 'conservative_bounds'
    if field == 'prior_shape': req['prior']['start_kg_m3'] = np.zeros(5000)
    if field == 'prior_scale': req['prior']['density_scale_kg_m3'] = np.float64(1000.)
    if field == 'prior_lengths': req['prior']['lengths_m'] = np.ones(4)
    if field == 'prior_reference_flag': req['prior']['reference_in_smooth'] = 1
    if field == 'seed_override': req['policy']['seed'] = 3
    if field == 'beta_type': req['policy']['beta_candidates'] = (True,) + l2.BETA_CANDIDATES[1:]
    if field == 'outer_payload': req['observations']['outer_values'] = np.zeros(36)
    if field == 'runtime': req['runtime_epoch'] = 'unreviewed'
    def deny(*args, **kwargs): raise AssertionError('numerical work before calibration metadata admission')
    for name in ('isfinite', 'array', 'count_nonzero', 'array_equal'):
        monkeypatch.setattr(survey.np, name, deny)
    for name in ('_digest', '_snapshot', '_validate_plan', 'forward_gravity'):
        monkeypatch.setattr(survey, name, deny)
    monkeypatch.setattr(l2, '_build_problem', deny)
    with pytest.raises((TypeError, ValueError)):
        l2._admit_calibration(req)


def test_compact_calibration_admission_owns_no_outer_observation_values():
    req = calibration_request()
    admitted = l2._admit_calibration(req)
    np.testing.assert_array_equal(admitted['observations']['rows'], req['plan']['development_rows'])
    assert admitted['observations']['gz_up_mgal'].shape == (108,)
    assert admitted['noise']['values'].shape == (108,)
    assert not admitted['observations']['gz_up_mgal'].flags.writeable
    req['observations']['gz_up_mgal'][0] = 1.
    assert admitted['observations']['gz_up_mgal'][0] == 0.


@pytest.mark.parametrize('field', ['observation_hash', 'noise_hash', 'geometry_hash', 'rows',
                                  'bounds_swap', 'infeasible_start', 'infeasible_reference', 'zero_sd', 'nonfinite'])
def test_calibration_finite_identity_bounds_and_noise_fail_closed(field):
    req = calibration_request()
    if field == 'observation_hash': req['observations']['values_sha256'] = '0' * 64
    if field == 'noise_hash': req['noise']['values_sha256'] = '0' * 64
    if field == 'geometry_hash': req['prior']['geometry_sha256'] = '0' * 64
    if field == 'rows': req['observations']['rows'][1] = req['observations']['rows'][0]
    if field == 'bounds_swap': req['prior']['lower_kg_m3'][0] = 1500.
    if field == 'infeasible_start': req['prior']['start_kg_m3'][0] = 1501.
    if field == 'infeasible_reference': req['prior']['reference_kg_m3'][0] = -1501.
    if field == 'zero_sd': req['noise']['values'][0] = 0.
    if field == 'nonfinite': req['observations']['gz_up_mgal'][0] = np.nan
    with pytest.raises(ValueError): l2._admit_calibration(req)
