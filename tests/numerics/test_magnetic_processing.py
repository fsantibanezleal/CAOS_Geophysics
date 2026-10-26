"""M03 geometry and local operator controls, including the unwaived S1 failure."""
from copy import deepcopy
import importlib
import math

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
from test_magnetic_lines import modules


def test_local_320_geometry_profile_is_explicit_and_value_free():
    c, g = modules()
    v = validation()
    p = processing()
    rows = g.refinement_geometry_rows()
    assert all(r["magnetic_nT"] is None for r in rows)
    assert rows != g.geometry_rows()
    req = g.geometry_request(rows)
    req["equivalent_sources"]["source_geometry"].update(block_e_m=50., block_n_m=50., max_sources=320)
    with pytest.raises(c.MagneticContractError):
        v.make_partitions(rows, req)
    sealed = v.make_partitions(rows, req, local_profile="m03-local-320/1")
    assert len(sealed["outer_source_positions"]) <= 320
    proof = p.local_source_preallocation(rows, req, local_profile="m03-local-320/1")
    assert proof["source_counts"] == [len(sealed["outer_source_positions"])] + [len(f["source_positions"]) for f in sealed["inner"]]
    assert proof["peak_dense_bytes_bound"] < 512 * 1024**2
    assert proof["values_generated"] is False and proof["vps_admitted"] is False
    changed = deepcopy(rows)
    for r in changed:
        r["magnetic_nT"] = 1e12
    with pytest.raises(c.MagneticContractError):
        p.local_source_preallocation(changed, req, local_profile="m03-local-320/1")
    for name in (None, "vps-320", True):
        with pytest.raises(c.MagneticContractError):
            v.make_partitions(rows, req, local_profile=name)
    req["equivalent_sources"]["source_geometry"]["max_sources"] = 321
    with pytest.raises(c.MagneticContractError):
        v.make_partitions(rows, req, local_profile="m03-local-320/1")


def test_local_source_profile_requires_actual_job_before_native_import(monkeypatch):
    c,g=modules()
    p=processing()
    config=g.geometry_request(g.geometry_rows())["equivalent_sources"]
    config["source_geometry"]["max_sources"]=320
    monkeypatch.setattr(p,"engines",lambda: pytest.fail("Uncontained local profile must refuse before scientific imports"))
    with pytest.raises(c.MagneticContractError) as caught:
        p.fit_equivalent(g.geometry_rows(),config,500.,.0001,local_profile="m03-local-320/1")
    assert caught.value.error["code"]=="resource_refused"


def test_fresh_truth_requires_prior_null_geometry_seal():
    _,g=modules()
    for width,seal in ((100.,"0"*64),(50.,"0"*64),(True,"0"*64),(200.,"0"*64)):
        with pytest.raises(ValueError,match="fresh geometry seal"):
            g.refinement_input(width,seal)


def validation():
    return importlib.import_module("magnetic_line_validation")


def test_blocked_line_holdout():
    c, g = modules()
    v = validation()
    raw, meta, req = g.geometry_input()
    rows = g.geometry_rows()
    sealed = v.make_partitions(rows, req)
    assert len(sealed["outer_training_ids"]) == 294
    assert len(sealed["outer_validation_ids"]) == 33
    for fold, train, val in zip(sealed["inner"], (168, 195, 249), (66, 66, 33)):
        assert len(fold["training_ids"]) == train
        assert len(fold["validation_ids"]) == val
        assert fold["geometry_only_coverage"]["fraction"] == 1
        assert not (set(fold["training_ids"]) & set(fold["validation_ids"]))
        assert any(i.startswith("F00.") for i in fold["training_ids"])
        assert any(i.startswith("F07.") for i in fold["training_ids"])
    changed = deepcopy(rows)
    for row in changed:
        row["magnetic_nT"] = 10000 if row["line_id"] == "F04" else -math.pi
        row["uncertainty_nT"] = 100
    assert v.make_partitions(changed, req) == sealed
    bad = deepcopy(req)
    bad["split"]["buffer_m"] = 469
    with pytest.raises(c.MagneticContractError):
        v.make_partitions(rows, bad)


def test_segment_buffer_is_closed_and_not_endpoint_only():
    v = validation()
    block = (0, 1, 0, 1)
    assert v.segment_rectangle((-1, .5), (2, .5), block)
    assert v.segment_rectangle((-1, 0), (0, 0), block)
    assert not v.segment_rectangle((-2, .5), (-1, .5), block)
    assert not v.segment_rectangle((2, 2), (3, 3), block)


def test_half_open_source_maps_no_values_or_thinning():
    c, g = modules()
    v = validation()
    _, _, req = g.geometry_input()
    rows = g.geometry_rows()[:4]
    for row, e in zip(rows, (-2000, -1600, -1200, 1600)):
        row["easting_m"] = e
        row["northing_m"] = -1600
        row["upward_m"] = 80
    mapped = v.source_blocks(rows, req["equivalent_sources"]["source_geometry"], 200)
    assert [m["block_e"] for m in mapped["map"]] == [-1, 0, 1, 8]
    assert [s["source_id"] for s in mapped["sources"]] == ["B.-1.0", "B.0.0", "B.1.0", "B.8.0"]
    assert all(s["upward_m"] == -120 for s in mapped["sources"])
    assert len(mapped["map"]) == 4
    changed = deepcopy(rows)
    for row in changed:
        row["magnetic_nT"] = 1e30
        row["uncertainty_nT"] = .0001
    assert v.source_blocks(changed, req["equivalent_sources"]["source_geometry"], 200) == mapped


def test_preflight_exact_counts_before_native_imports():
    c, g = modules()
    raw, meta, req = g.geometry_input()
    loaded = c.load_lines(raw, c.canonical_bytes(meta), c.canonical_bytes(req))
    counts = c.preflight(loaded["rows"], meta, req)
    assert counts["rows"] == 363
    assert counts["segments"] == 352
    assert counts["fits"] == 26
    assert counts["exported_cells"] == 6370
    assert counts["sources"] == 66
    assert counts["segment_pairs"] <= 4096
    bad = deepcopy(req)
    bad["grid"]["nx"] = 1000
    with pytest.raises(c.MagneticContractError) as err:
        c.preflight(loaded["rows"], meta, bad)
    assert err.value.error["code"] == "resource_refused"
    assert len(loaded["rows"]) == 363


def test_nearconstant_kernel_guard_before_scaler():
    c, _ = modules()
    v = validation()
    with pytest.raises(c.MagneticContractError):
        v.kernel_column_scales([[1., 2.], [1., 3.]])
    scale = v.kernel_column_scales([[1., 2.], [3., 4.]])
    assert scale == [1., 1.]


def test_geometry_seal_counts_source_receipts_and_no_truth():
    c, g = modules()
    v = validation()
    rows = g.geometry_rows()
    raw, meta, req = g.geometry_input()
    assert all(r["magnetic_nT"] is None for r in rows)
    assert g.geometry_input() == (raw, meta, req)
    manifest = v.make_partitions(rows, req)
    assert [len(manifest["outer_source_positions"])] + [len(f["source_positions"]) for f in manifest["inner"]] == [66, 45, 48, 57]
    assert manifest["max_nearest_m"] == pytest.approx(387.45134262252844, abs=1e-10)
    assert [f["max_nearest_m"] for f in manifest["inner"]] == pytest.approx(
        [447.2709304213723, 447.5201609983622, 357.61083274979245], abs=1e-10)
    for fold in manifest["inner"]:
        assert len(fold["source_block_map"]) == len(fold["training_ids"])
        assert [m["row_id"] for m in fold["source_block_map"]] == fold["training_ids"]
        assert sum(s["count"] for s in fold["source_positions"]) == len(fold["training_ids"])
    assert manifest["evaluation_count"] == 0
    changed = deepcopy(rows)
    changed[0]["easting_m"] += 1
    with pytest.raises(c.MagneticContractError) as err:
        v.make_partitions(changed, req)
    assert err.value.error["code"] == "custody_mismatch"


def test_bounds_source_counts_padding_and_geometry_failures():
    c, g = modules()
    v = validation()
    rows = g.geometry_rows()
    _, meta, req = g.geometry_input()
    for axis, number in (("nx", 1000), ("ny", 1000)):
        bad = deepcopy(req)
        bad["grid"][axis] = number
        with pytest.raises(c.MagneticContractError):
            c.preflight(rows, meta, bad)
    bad = deepcopy(req)
    bad["grid"]["boundary_policy"]["mode"] = "reflect_pad"
    bad["grid"]["boundary_policy"]["pad_e_cells"] = 33
    with pytest.raises(c.MagneticContractError):
        c.preflight(rows, meta, bad)
    config = deepcopy(req["equivalent_sources"]["source_geometry"])
    config["max_sources"] = 1
    with pytest.raises(c.MagneticContractError):
        v.source_blocks(rows, config, 200)
    with pytest.raises(c.MagneticContractError):
        c.preflight(rows + rows[:38], meta, req)
    for value in (True, float("nan"), float("inf"), "0"):
        bad = deepcopy(rows)
        bad[0]["easting_m"] = value
        with pytest.raises(c.MagneticContractError):
            v.make_partitions(bad, req)
    bad = deepcopy(req)
    bad["split"]["inner_folds"][0]["validation_line_ids"] = ["F00"]
    with pytest.raises(c.MagneticContractError):
        v.make_partitions(rows, bad)


def processing():
    return importlib.import_module("magnetic_lines")


def test_native_array_shape_bounds_and_fixed_errors():
    import numpy as np
    c, _ = modules()
    p = processing()
    for value in (np.array(1.), np.array(True), [], [True, 1.], [np.bool_(False)],
                  [float("inf")], [float("nan")], ["1"], [0.] * 401):
        with pytest.raises(c.MagneticContractError) as err:
            p._array(value)
        assert set(err.value.error) == {"code", "stage", "field", "observed", "limit",
                                       "reason", "local_recipe", "attempt_id"}
    for value in ([np.array(1.)], [[1., 2.]], [[1., True, 3.]], np.zeros((1, 3, 1))):
        with pytest.raises(c.MagneticContractError):
            p._array(value, 3)
    original = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32)
    admitted = p._array(original, 3)
    assert admitted.dtype == np.float64
    np.testing.assert_array_equal(original, admitted)


def test_lag_diurnal_heading_and_overlap():
    import numpy as np
    p = processing()
    times = np.array([0., .5, 1., 1.5])
    navigation_times = np.array([0., .5, 1., 1.5, 2.])
    coordinates = np.stack([10*navigation_times, -2*navigation_times, 80+navigation_times], axis=1)
    aligned, valid = p.align_navigation(times, navigation_times, coordinates, .25, .5)
    assert valid.all()
    np.testing.assert_allclose(aligned, np.stack([10*(times+.25), -2*(times+.25), 80+times+.25], axis=1), atol=1e-12)
    aligned_negative, valid_negative = p.align_navigation(times, navigation_times, coordinates, -.25, .5)
    assert valid_negative.tolist() == [False, True, True, True]
    assert np.isnan(aligned_negative[0]).all()
    true = np.array([1., 2., -3., 4.])
    base = 48000 + np.array([0., 1., 2., -1.])
    heading = np.array([0., 90., 180., 270.])
    injected = 2*np.cos(np.deg2rad(heading)) - np.sin(np.deg2rad(heading))
    raw = true + base - 48000 + injected
    corrected = p.remove_base_and_heading(raw, base, 48000., heading, 0., 2., -1.)
    np.testing.assert_allclose(corrected, true, atol=1e-12)
    assert not np.array_equal(raw, corrected)


def test_igrf_epoch_vector_datum_and_rereference():
    c, g = modules()
    p = processing()
    from test_magnetic_lines import specimens
    reference = specimens(c, g)["Reference"]
    with pytest.raises(c.MagneticContractError) as err:
        p.validate_reference(reference, "field_acquisition", 1)
    assert err.value.error["code"] == "metadata_ineligible"
    # This negative proves no IGRF admission, not its still-open evaluated gate.
    import numpy as np
    anomaly = np.array([12., -3.])
    old = np.array([48000., 48001.])
    new = np.array([47990., 48005.])
    np.testing.assert_array_equal(p.rereference_values(anomaly, old, new), [22., -7.])
    with pytest.raises(c.MagneticContractError):
        p.rereference_values(anomaly, old, old)


def test_scalar_vector_remanence_and_rtp_rejection():
    import numpy as np
    p = processing()
    vector = np.array([[15., 8., -20.], [-100., 20., 50.]])
    direction = np.array([.3, .4, -math.sqrt(.75)])
    weak, exact, bound = p.weak_anomaly_diagnostic(vector, direction, 48000.)
    independent = np.linalg.norm(48000*direction + vector, axis=1) - 48000
    np.testing.assert_allclose(exact, independent, atol=1e-10)
    assert np.all(np.abs(exact - weak) <= bound)
    assert np.any(np.abs(exact - weak) > 1e-4)
    c, _ = modules()
    with pytest.raises(c.MagneticContractError):
        p.weak_anomaly_diagnostic(vector, direction, 1.)


def test_crossing_geometry_height_and_gap():
    c, _ = modules()
    p = processing()
    for origin, scale in ((0., 1.), (1e8, 1000.), (0., 1000.)):
        a = (origin-scale, origin)
        b = (origin+scale, origin)
        d = (origin, origin-scale)
        e = (origin, origin+scale)
        result = p.intersect_segments(a, b, d, e, 64*2.220446049250313e-16*max(1., abs(origin), 2*scale), 1e-6)
        assert result["a"] == pytest.approx(.5, abs=1e-12)
        assert result["b"] == pytest.approx(.5, abs=1e-12)
        assert result["tolerance"]["coordinate_m"] > 0
        assert result["tolerance"]["parameter_dimensionless"] <= 1e-6
    with pytest.raises(c.MagneticContractError):
        p.intersect_segments((-1., 0.), (1., 0.), (-1., 1.), (1., 1.), 1e-12, 1e-6)
    with pytest.raises(c.MagneticContractError):
        p.intersect_segments((1e8-1., 1e8), (1e8+1., 1e8), (1e8, 1e8-1.), (1e8, 1e8+1.),
                             64*2.220446049250313e-16*1e8, 1e-6)


def test_level_graph_gauges_and_sealed_lines():
    import numpy as np
    p = processing()
    crossings = [
        dict(flight="F0", tie="T0", difference_nT=2., variance_nT2=None),
        dict(flight="F1", tie="T0", difference_nT=-3., variance_nT2=None),
        dict(flight="F1", tie="T1", difference_nT=-7., variance_nT2=None),
        dict(flight="F0", tie="T1", difference_nT=-2., variance_nT2=None),
    ]
    before = [r["difference_nT"] for r in crossings]
    result = p.solve_offsets(crossings, "unweighted")
    assert result["offsets"] == pytest.approx({"F0": 2., "F1": -3., "T0": 0., "T1": 4.}, abs=1e-12)
    np.testing.assert_allclose(result["residuals"], 0., atol=1e-12)
    assert result["components"][0]["gauge_line_id"] == "T0"
    assert result["components"][0]["absolute_datum"] is False
    assert [r["difference_nT"] for r in crossings] == before


def test_dense_independent_fit_and_height_baseline():
    import numpy as np
    from scipy.linalg import lstsq
    c, g = modules()
    p = processing()
    rows = g.control_rows("S1")
    _, _, req = g.geometry_input()
    training = rows[:33] + rows[66:99]
    config = req["equivalent_sources"]
    fitted = p.fit_equivalent(training, config, 200., .01)
    coordinates = np.array([[r[k] for k in ("easting_m", "northing_m", "upward_m")] for r in training])
    sources = np.array([[r[k] for k in ("easting_m", "northing_m", "upward_m")] for r in fitted["source_positions"]])
    jacobian = 1/np.linalg.norm(coordinates[:, None, :] - sources[None, :, :], axis=2)
    scales = np.std(jacobian, axis=0, ddof=0)
    matrix = jacobian/scales
    values = np.array([r["magnetic_nT"] for r in training])
    augmented = np.vstack([matrix, math.sqrt(.01)*np.eye(len(sources))])
    coefficients = lstsq(augmented, np.concatenate([values, np.zeros(len(sources))]), lapack_driver="gelsy")[0]/scales
    np.testing.assert_allclose(fitted["coefficients"], coefficients, rtol=1e-9, atol=1e-6)
    query = np.array([[-321., -712., 220.], [113., 89., 220.], [877., 901., 220.]])
    independent = (1/np.linalg.norm(query[:, None, :] - sources[None, :, :], axis=2)) @ coefficients
    np.testing.assert_allclose(p.predict_equivalent(fitted, query), independent, rtol=1e-9, atol=1e-6)


def test_s1_frozen_blocked_quality_and_sealed_choice():
    c, g = modules()
    p, v = processing(), validation()
    raw, meta, req = g.control_input("S1")
    intake = c.load_lines(raw, c.canonical_bytes(meta), c.canonical_bytes(req))
    rows = intake["rows"]
    sealed = v.make_partitions(rows, req)
    result = p.blocked_fit(rows, req, sealed)
    assert result["production_fit_count"] == 25  # Geometric comparator is separate, ceiling26.
    assert result["evaluation_count"] == 1
    assert result["coverage"] == 1.
    assert result["rmse_nT"] <= max(.05*result["signal_rms_nT"], 1e-6), result


def test_s1_outer_perturbation_does_not_change_training_selection():
    c, g = modules()
    p, v = processing(), validation()
    raw, meta, req = g.control_input("S1")
    rows = c.load_lines(raw, c.canonical_bytes(meta), c.canonical_bytes(req))["rows"]
    sealed = v.make_partitions(rows, req)
    result = p.blocked_fit(rows, req, sealed)
    altered = deepcopy(rows)
    for row in altered:
        if row["line_id"] == "F04":
            row["magnetic_nT"] += 10000
    other_request = deepcopy(req)
    other_raw = g.csv_bytes(altered)
    other_meta = deepcopy(meta)
    from hashlib import sha256
    other_meta["original"].update(csv_sha256=sha256(other_raw).hexdigest(), csv_bytes=len(other_raw))
    other_request["dataset_version_sha256"] = c.dataset_identity(
        sha256(other_raw).hexdigest(), sha256(c.canonical_bytes(other_meta)).hexdigest())
    other_request["channel_sha256"] = c.channel_identity(altered)
    other_request["split"]["sealed_values_sha256"] = c.channel_identity(altered)
    c.load_lines(other_raw, c.canonical_bytes(other_meta), c.canonical_bytes(other_request))
    other = p.blocked_fit(altered, other_request, v.make_partitions(altered, other_request))
    assert other["selected_candidate"] == result["selected_candidate"]
    assert other["training_sha256"] == result["training_sha256"]
    assert other["candidates"] == result["candidates"]


def test_independent_original_dipoles_against_official_engine():
    import numpy as np
    c, g = modules()
    p = processing()
    _, hm = p.engines()
    query = np.array([[-321., -712., 120.], [113., 89., 220.], [877., 901., 550.], [-1100., 1300., 80.]])
    coordinates = tuple(query[:, i] for i in range(3))
    sources = (np.array([0., -700., 800.]), np.array([0., 500., -600.]), np.array([-300., -500., -250.]))
    moments = (np.array([2e7, -1e7, 1e7]), np.array([-1e7, 2e7, 1e7]), np.array([3e7, 1e7, -2e7]))
    official = np.column_stack(hm.dipole_magnetic(coordinates, sources, moments, field="b", parallel=False))
    independent = np.array([g.analytic_dipole_vector(point) for point in query])
    np.testing.assert_allclose(official, independent, rtol=1e-9, atol=1e-6)


def test_s2_original_plane_crossovers_and_full_relative_offsets():
    c, g = modules()
    p = processing()
    raw, meta, req = g.control_input("S2")
    loaded = c.load_lines(raw, c.canonical_bytes(meta), c.canonical_bytes(req))
    rows = loaded["rows"]
    before = deepcopy(rows)
    crossings = p.crossovers(rows, req["geometry_policy"])
    admitted = [x for x in crossings if x["disposition"] == "admitted" and
                x["constraint_representative"] == x["crossover_id"]]
    assert len(admitted) == 24
    assert all(x["height_difference_m"] == 0. for x in admitted)
    result = p.level_offsets(rows, req["geometry_policy"], [r["row_id"] for r in rows])
    for line in (f"F{i:02d}" for i in range(8)):
        assert result["offsets"][line] == pytest.approx(2*(int(line[1:])-3), abs=1e-6)
    assert result["components"][0]["absolute_datum"] is False
    assert result["components"][0]["gauge_line_id"] == "T00"
    assert result["common_relative_gauge"] is True
    for row in result["rows"]:
        assert row["magnetic_nT"] == pytest.approx(10+.002*row["easting_m"]-.003*row["northing_m"], abs=1e-6)
    assert rows == before


def test_crossovers_retain_height_gap_and_endpoint_constraints():
    c, g = modules()
    p = processing()
    raw, _, req = g.control_input("S1")
    mixed = c.parse_csv(raw)["rows"]
    inventory = p.crossovers(mixed, req["geometry_policy"])
    assert not [x for x in inventory if x["disposition"] == "admitted"]
    assert any("height_mismatch" in x["reasons"] for x in inventory)
    assert all(x["flight_minus_tie_nT"] is None for x in inventory)
    # Two straight lines cross at genuine shared endpoints:four segment pairs,
    # one physical equality. No joined segment may skip a missing middle row.
    rows = []
    for line, kind, positions in (("F", "flight", [(-100., 0.), (0., 0.), (100., 0.)]),
                                  ("T", "tie", [(0., -100.), (0., 0.), (0., 100.)])):
        for j, (e, n) in enumerate(positions):
            row = deepcopy(g.geometry_rows()[j])
            row.update(row_id=f"{line}.{j}", line_id=line, line_kind=kind, easting_m=e, northing_m=n,
                       upward_m=80., terrain_upward_m=0., clearance_m=80., magnetic_nT=10+.002*e-.003*n)
            rows.append(row)
    inventory = p.crossovers(rows, req["geometry_policy"])
    assert len(inventory) == 4
    assert len({x["shared_endpoint_group_id"] for x in inventory}) == 1
    assert sum(x["constraint_representative"] == x["crossover_id"] for x in inventory) == 1
    bad = deepcopy(rows)
    bad[1]["magnetic_nT"] = None
    rejected = p.crossovers(bad, req["geometry_policy"])
    assert len(rejected) == 4
    assert all("missing_value" in x["reasons"] and x["flight_minus_tie_nT"] is None for x in rejected)
    for value in (True, float("nan"), float("inf"), "10"):
        bad = deepcopy(rows)
        bad[0]["magnetic_nT"] = value
        with pytest.raises(c.MagneticContractError):
            p.crossovers(bad, req["geometry_policy"])
    weighted = deepcopy(rows)
    for row in weighted:
        row["uncertainty_nT"] = 2. if row["line_kind"] == "flight" else 3.
    policy = deepcopy(req["geometry_policy"])
    policy["crossover"]["uncertainty_policy"] = "documented_independent_rows"
    uncertainty = dict(meaning="independent_one_sigma",source_evidence="Authored algebraic variance control, not field",
                       independence_assumption="row_independent",unit="nT")
    result = p.crossovers(weighted, policy, uncertainty=uncertainty)
    assert all(x["difference_variance_nT2"] == pytest.approx(13., abs=1e-12) for x in result)
    uncertainty["independence_assumption"] = "correlated"
    with pytest.raises(c.MagneticContractError):
        p.crossovers(weighted, policy, uncertainty=uncertainty)
    uncertainty["independence_assumption"] = "row_independent"
    for sigma in (1e-300, 1e308):
        bad = deepcopy(weighted)
        for row in bad:
            row["uncertainty_nT"] = sigma
        with pytest.raises(c.MagneticContractError):
            p.crossovers(bad, policy, uncertainty=uncertainty)


def test_leveling_does_not_calibrate_sealed_or_disconnected_lines():
    c, g = modules()
    p, v = processing(), validation()
    raw, _, req = g.control_input("S2")
    rows = c.parse_csv(raw)["rows"]
    sealed = v.make_partitions(rows, req)
    result = p.level_offsets(rows, req["geometry_policy"], sealed["outer_training_ids"])
    assert "F04" not in result["offsets"]
    assert "F04" in result["uncalibrated_line_ids"]
    assert all(row["magnetic_nT"] is None for row in result["rows"] if row["line_id"] == "F04")
    assert all("outer_sealed" in x["reasons"] and x["flight_minus_tie_nT"] is None
               for x in result["crossovers"] if x["flight_segment_id"].startswith("S00013"))
    before = deepcopy(result)
    altered = deepcopy(rows)
    for row in altered:
        if row["line_id"] == "F04":
            row["magnetic_nT"] += 10000
    other = p.level_offsets(altered, req["geometry_policy"], sealed["outer_training_ids"])
    assert other["offsets"] == before["offsets"]
    assert other["components"] == before["components"]
    disconnected = deepcopy(rows)
    for row in disconnected:
        if row["line_id"] in ("F07","T02"):
            row["easting_m"] += 10000
            row["northing_m"] += 10000
    result = p.level_offsets(disconnected, req["geometry_policy"], [r["row_id"] for r in disconnected])
    assert len(result["components"]) == 2
    assert result["common_relative_gauge"] is False
    assert all(component["absolute_datum"] is False for component in result["components"])


def test_s3_full_instrument_reference_dag_and_original_identity():
    c, g = modules()
    p = processing()
    raw, meta, req = g.control_input("S3")
    original = c.parse_csv(raw)["rows"]
    run = p.apply_corrections(raw, c.canonical_bytes(meta), c.canonical_bytes(req))
    assert run["original_rows"] == original
    assert [s["operation"] for s in run["state"] if s["applied_by"] == "processor"] == [
        "lag","diurnal","heading","main_field"]
    assert len(run["channels"]) == 5
    assert run["kind"] == "scalar_total_field_anomaly"
    assert all(not flags for flags in run["masks"])
    for before, after, known in zip(original,run["rows"],g.geometry_rows()):
        for key in ("easting_m","northing_m","upward_m"):
            assert after[key] == pytest.approx(known[key], abs=1e-8)
        vector = g.analytic_dipole_vector((known["easting_m"],known["northing_m"],known["upward_m"]))
        dec,inc = math.radians(12),math.radians(55)
        true = sum(a*b for a,b in zip(vector,(math.cos(inc)*math.sin(dec),math.cos(inc)*math.cos(dec),-math.sin(inc))))
        assert after["magnetic_nT"] == pytest.approx(true, abs=1e-6)
        assert before["magnetic_nT"] != after["magnetic_nT"]
    assert run["state"][-1]["output_channel_sha256"] == run["output_sha256"]
    assert run["channels"][-1]["parent_sha256"] == run["state"][-1]["parent_channel_sha256"]
    assert run == p.apply_corrections(raw, c.canonical_bytes(meta), c.canonical_bytes(req))


def test_correction_state_and_no_double_application():
    c, g = modules()
    p = processing()
    raw, meta, req = g.control_input("S3")
    for status in ("applied","unknown"):
        bad = deepcopy(meta)
        bad["channel_state"][2]["status"] = status
        other = deepcopy(req)
        other["dataset_version_sha256"] = c.dataset_identity(bad["original"]["csv_sha256"],
                                                           c.digest(bad))
        with pytest.raises(c.MagneticContractError):
            p.apply_corrections(raw, c.canonical_bytes(bad), c.canonical_bytes(other))
    bad = deepcopy(req)
    bad["operations"][0]["parameters"]["navigation"]["identity"]["source_verification"] = "user_claimed"
    bad["operations"][0]["parameters"]["navigation"]["identity"]["source_receipt_sha256"] = None
    with pytest.raises(c.MagneticContractError):
        p.apply_corrections(raw,c.canonical_bytes(meta),c.canonical_bytes(bad))
    bad = deepcopy(req)
    ref = bad["operations"][-1]["parameters"]["evaluated_reference"]
    ref["coordinates_sha256"] = ref["evaluator"]["input_coordinates_sha256"] = "0"*64
    ref["receipt_sha256"] = c.digest({k:v for k,v in ref.items() if k != "receipt_sha256"})
    with pytest.raises(c.MagneticContractError):
        p.apply_corrections(raw,c.canonical_bytes(meta),c.canonical_bytes(bad))


def test_lag_dag_no_extrapolation_and_clock_or_rights_guess():
    c, g = modules()
    p = processing()
    raw, meta, req = g.control_input("S3")
    req["operations"] = req["operations"][:1]
    req["operations"][0]["parameters"]["tau_s"] = 1.
    run = p.apply_corrections(raw,c.canonical_bytes(meta),c.canonical_bytes(req))
    assert any("unsupported_time" in flags for flags in run["masks"])
    assert all(row["magnetic_nT"] is None for row,flags in zip(run["rows"],run["masks"]) if flags)
    for name in ("private_processing","decision"):
        bad = deepcopy(meta)
        bad["rights"][name] = "unresolved"
        other = deepcopy(req)
        other["dataset_version_sha256"] = c.dataset_identity(bad["original"]["csv_sha256"],c.digest(bad))
        with pytest.raises(c.MagneticContractError):
            p.apply_corrections(raw,c.canonical_bytes(bad),c.canonical_bytes(other))


def leveling_request(g, c, raw, meta, req):
    """Independent authored offsets, not inferred from heldout magnetic rows."""
    meta = deepcopy(meta)
    req = deepcopy(req)
    meta["channel_state"].append(dict(operation="leveling",status="not_applied",parent_channel_sha256=None,
        output_channel_sha256=None,evidence_sha256=None,parameters=None,units=None,sign="unknown",applied_by="user"))
    payload = dict(values=[dict(line_id=f"F{i:02d}",offset_nT=float(2*(i-3)),uncertainty_nT=None) for i in range(8)]+
        [dict(line_id=f"T{i:02d}",offset_nT=0.,uncertainty_nT=None) for i in range(3)],reference_gauge_id="T00")
    calibration = dict(identity=g.authored_identity(payload,meta["rights"]),partition="independent_calibration",
        calibration_row_ids=[],coefficient_receipt_sha256=c.digest(payload))
    params = dict(crossover_policy=req["geometry_policy"]["crossover"],weights_policy="unweighted",
        gauge_policy="lexicographic_first_tie_per_component",scope="training_only",
        heldout_calibration=dict(**payload,calibration=calibration))
    req["operations"].append(dict(operation="leveling",input_channel_sha256=req["channel_sha256"],parameters=params))
    req["dataset_version_sha256"] = c.dataset_identity(meta["original"]["csv_sha256"],c.digest(meta))
    return raw,meta,req


def test_leveling_dag_independent_heldout_calibration_and_preserved_parent():
    c,g = modules()
    p,v = processing(),validation()
    raw,meta,req = leveling_request(g,c,*g.control_input("S2"))
    rows = c.parse_csv(raw)["rows"]
    manifest = v.make_partitions(rows,req)
    run = p.apply_corrections(raw,c.canonical_bytes(meta),c.canonical_bytes(req),manifest["outer_training_ids"])
    assert run["original_rows"] == rows
    for row in run["rows"]:
        assert row["magnetic_nT"] == pytest.approx(10+.002*row["easting_m"]-.003*row["northing_m"],abs=1e-6)
    assert not any(run["masks"])
    # This actual point correction precedes leveling. Independent calibration
    # must apply to the immediate derivative, not silently restore raw values.
    meta["channel_state"].insert(0,dict(operation="heading",status="not_applied",parent_channel_sha256=None,
        output_channel_sha256=None,evidence_sha256=None,parameters=None,units=None,sign="unknown",applied_by="user"))
    for row in rows:
        row["heading_deg"] = 0.
    raw = g.csv_bytes(rows)
    coefficients = dict(a0_nT=3.,ac_nT=0.,as_nT=0.,convention="clockwise_from_north_degrees")
    calibration = dict(identity=g.authored_identity(coefficients,meta["rights"]),partition="independent_calibration",
        calibration_row_ids=[],coefficient_receipt_sha256=c.digest(coefficients))
    req["operations"].insert(0,dict(operation="heading",input_channel_sha256="",parameters=dict(
        **coefficients,calibration=calibration,sign="subtract_model")))
    from hashlib import sha256
    meta["original"].update(csv_sha256=sha256(raw).hexdigest(),csv_bytes=len(raw))
    req["dataset_version_sha256"] = c.dataset_identity(meta["original"]["csv_sha256"],c.digest(meta))
    req["channel_sha256"] = req["split"]["sealed_values_sha256"] = c.channel_identity(rows)
    for op in req["operations"]:
        op["input_channel_sha256"] = req["channel_sha256"]
    from magnetic_line_validation import geometry_manifest
    req["split"]["geometry_manifest_sha256"] = c.digest(geometry_manifest(rows))
    manifest = v.make_partitions(rows,req)
    run = p.apply_corrections(raw,c.canonical_bytes(meta),c.canonical_bytes(req),manifest["outer_training_ids"])
    for row in run["rows"]:
        assert row["magnetic_nT"] == pytest.approx(7+.002*row["easting_m"]-.003*row["northing_m"],abs=1e-6)
    assert run["channels"][-1]["parent_sha256"] == run["state"][-2]["output_channel_sha256"]


def test_leveling_dag_refuses_unverified_or_sealed_calibration():
    c,g = modules()
    p,v = processing(),validation()
    raw,meta,req = leveling_request(g,c,*g.control_input("S2"))
    manifest = v.make_partitions(c.parse_csv(raw)["rows"],req)
    for mutation in ("stale","gauge","sealed"):
        bad = deepcopy(req)
        supplied = bad["operations"][-1]["parameters"]["heldout_calibration"]
        if mutation == "stale":
            supplied["values"][4]["offset_nT"] += 1.
        elif mutation == "gauge":
            supplied["reference_gauge_id"] = "T01"
            payload = {k:supplied[k] for k in ("values","reference_gauge_id")}
            supplied["calibration"]["identity"] = g.authored_identity(payload,meta["rights"])
            supplied["calibration"]["coefficient_receipt_sha256"] = c.digest(payload)
        else:
            supplied["calibration"]["calibration_row_ids"] = ["F04.000"]
        with pytest.raises(c.MagneticContractError):
            p.apply_corrections(raw,c.canonical_bytes(meta),c.canonical_bytes(bad),manifest["outer_training_ids"])
    bad = deepcopy(req)
    bad["operations"][-1]["parameters"]["heldout_calibration"] = None
    run = p.apply_corrections(raw,c.canonical_bytes(meta),c.canonical_bytes(bad),manifest["outer_training_ids"])
    assert all(r["magnetic_nT"] is None and "uncalibrated_line" in flags
               for r,flags in zip(run["rows"],run["masks"]) if r["line_id"]=="F04")


def test_reference_dag_authored_rereference_and_already_target_identity():
    c,g = modules()
    p = processing()
    raw,meta,req = g.control_input("S3")
    run = p.apply_corrections(raw,c.canonical_bytes(meta),c.canonical_bytes(req))
    rows = run["rows"]
    old = run["reference"]
    meta["quantity"]["kind"] = "scalar_total_field_anomaly"
    meta["reference"],meta["channel_state"] = old,run["state"]
    new = deepcopy(old)
    for key in ("vector_east_nT","vector_north_nT","vector_up_nT","scalar_F_nT"):
        new[key] = [v*48010/48000 for v in old[key]]
    new["evaluator"]["revision"] = "instrument-2"
    new["receipt_sha256"] = c.digest({k:v for k,v in new.items() if k!="receipt_sha256"})
    parameters = dict(old_reference=old,new_reference=new,input_reference_receipt_sha256=old["receipt_sha256"],
        old_applied_state_evidence_sha256=run["state"][-1]["evidence_sha256"],sign="add_old_F_subtract_new_F")
    result,reference = p.apply_reference(rows,meta,parameters,"rereference")
    assert reference == new
    assert [r["magnetic_nT"] for r in result] == pytest.approx([r["magnetic_nT"]-10 for r in rows],abs=1e-6)
    same = deepcopy(old)
    same["evaluator"]["revision"] = "same-field-distinct-record"
    same["receipt_sha256"] = c.digest({k:v for k,v in same.items() if k!="receipt_sha256"})
    parameters["new_reference"] = same
    with pytest.raises(c.MagneticContractError):
        p.apply_reference(rows,meta,parameters,"rereference")
    parameters["new_reference"] = new
    parameters["old_applied_state_evidence_sha256"] = "0"*64
    with pytest.raises(c.MagneticContractError):
        p.apply_reference(rows,meta,parameters,"rereference")


def test_utc_bracket_nanoseconds_signed_lag_and_exact_closed_gap():
    p = processing()
    rows = [dict(utc="2001-01-01T00:00:00.000000001Z",x=0.),
            dict(utc="2001-01-01T00:00:00.500000001Z",x=10.)]
    assert p._bracket(rows,"2001-01-01T00:00:00.250000001Z",.5,("x",)) == [5.]
    assert p._bracket(rows,"2001-01-01T00:00:00.500000001Z",.5,("x",),-.25) == [5.]
    assert p._bracket(rows,"2001-01-01T00:00:00.000000001Z",.5,("x",),.25) == [5.]
    assert p._bracket(rows,"2001-01-01T00:00:00Z",.5,("x",)) is None
    rows[-1]["utc"] = "2001-01-01T00:00:00.500000002Z"
    assert p._bracket(rows,"2001-01-01T00:00:00.250000001Z",.5,("x",)) is None


def periodic_control():
    import numpy as np
    _,g = modules()
    _,_,req = g.geometry_input()
    grid = deepcopy(req["grid"])
    grid.update(nx=40,ny=32,origin_e_m=0.,origin_n_m=0.,spacing_e_m=25.,spacing_n_m=30.)
    spectrum = dict(rectangle=dict(e_start=0,n_start=0,nx=40,ny=32),window="rectangular",
        mean_policy="subtract_arithmetic_mean",normalization="full_two_sided_bin_power",axis_unit="cycles_per_m",
        direction_sectors=[dict(sector_id="north",azimuth_start_deg=0.,azimuth_end_deg=90.),
                           dict(sector_id="east",azimuth_start_deg=90.,azimuth_end_deg=180.)])
    e,n = np.meshgrid(np.arange(40)*25.,np.arange(32)*30.)
    phase = 2*np.pi*(3*e/1000+2*n/960)+.31
    values = 7+2.3*np.cos(phase)
    return grid,spectrum,phase,values


def test_dipole_and_fourier_continuation_oracles():
    import numpy as np
    import xarray as xr
    import harmonica as hm
    p = processing()
    grid,_,phase,values = periodic_control()
    delta = grid["continuation_delta_m"]
    attenuation = math.exp(-math.hypot(2*math.pi*3/1000,2*math.pi*2/960)*delta)
    result = p.continue_plane(values,grid,datum=grid["datum"],source_free=True)
    assert result["values"] == pytest.approx(7+2.3*attenuation*np.cos(phase),rel=1e-10,abs=1e-12)
    # Separate official physical implementation; same declared periodic domain.
    control = xr.DataArray(values,coords={"northing":np.arange(32)*30.,"easting":np.arange(40)*25.},
                           dims=("northing","easting"))
    assert result["values"] == pytest.approx(hm.upward_continuation(control,delta).values,rel=1e-10,abs=1e-12)
    assert result["plane_upward_m"] == 220.
    assert result["transfer"][0,0] == 1.
    assert result["boundary_policy"] == grid["boundary_policy"]


def test_spectrum_parseval_axis_and_holes():
    import numpy as np
    p = processing()
    grid,spec,_,values = periodic_control()
    result = p.power_spectrum(values,grid,spec)
    assert result["mean_removed_nT"] == pytest.approx(7.,abs=1e-12)
    assert result["parseval_sum_nT2"] == pytest.approx(2.3**2/2,rel=1e-10,abs=1e-12)
    assert result["power"][2,3] == pytest.approx(2.3**2/4,rel=1e-10)
    assert result["power"][-2,-3] == pytest.approx(2.3**2/4,rel=1e-10)
    assert result["east_axis"][3] == pytest.approx(3/1000)
    assert result["north_axis"][2] == pytest.approx(2/960)
    rad = deepcopy(spec)
    rad["axis_unit"] = "rad_per_m"
    other = p.power_spectrum(values,grid,rad)
    assert other["east_axis"] == pytest.approx(2*np.pi*result["east_axis"])
    assert other["power"] == pytest.approx(result["power"])
    spec["window"] = "hann"
    windowed = p.power_spectrum(values,grid,spec)
    window = np.hanning(32)[:,None]*np.hanning(40)[None,:]
    assert windowed["parseval_sum_nT2"] == pytest.approx(
        np.mean(window**2*(values-7)**2)/np.mean(window**2),rel=1e-10,abs=1e-12)
    spec["rectangle"] = dict(e_start=3,n_start=2,nx=16,ny=12)
    crop = p.power_spectrum(values,grid,spec)
    assert crop["power"].shape == (12,16)
    assert crop["config"] == spec


def test_microlevel_stripes_and_parallel_geology():
    import numpy as np
    p = processing()
    grid,spec,_,_ = periodic_control()
    e,n = np.meshgrid(np.arange(40)*25.,np.arange(32)*30.)
    # E-W flights: both true cross-line geology and stripes vary only north.
    geology = np.cos(2*np.pi*n/960)
    stripe = np.cos(2*np.pi*4*n/960)
    kc,ka = 2*np.pi/960,2*np.pi/1000
    params = dict(flight_azimuth_deg=90.,max_azimuth_spread_deg=5.,kc_rad_per_m=kc,ka_rad_per_m=ka,
        amplitude_cap_nT=None,promotion="diagnostic_only",spectrum_policy=spec)
    result = p.microlevel_diagnostic(geology+stripe,grid,params,acquisition_azimuths_deg=[90.,270.])
    hg,hs = 1/math.sqrt(2),4**4/math.sqrt(4**8+1)
    assert result["removed"] == pytest.approx(hg*geology+hs*stripe,rel=1e-9,abs=1e-6)
    assert result["retained"]+result["removed"] == pytest.approx(geology+stripe,rel=1e-10,abs=1e-12)
    assert result["geological_preservation_claim"] is False
    assert result["transfer"][0,0] == 0.
    assert result["removed_power_nT2"] == pytest.approx((hg*hg+hs*hs)/2,rel=1e-10)
    assert result["retained_power_nT2"] == pytest.approx(((1-hg)**2+(1-hs)**2)/2,rel=1e-10)
    params["amplitude_cap_nT"] = .2
    clipped = p.microlevel_diagnostic(geology+stripe,grid,params,acquisition_azimuths_deg=[90.])
    assert np.max(np.abs(clipped["clipped_removed"])) <= .2
    assert clipped["removed"] == pytest.approx(result["removed"])
    assert clipped["clipped_spectrum"]["parseval_sum_nT2"] > 0


def test_grid_transforms_strict_domain_bounds_and_no_zero_fill():
    import numpy as np
    c,_ = modules()
    p = processing()
    grid,spec,_,values = periodic_control()
    for bad in (np.full(values.shape,np.nan),np.full(values.shape,np.inf),np.ones(values.shape,dtype=bool),
                values.astype(str),values[0],[[1.,None]]):
        with pytest.raises(c.MagneticContractError):
            p.power_spectrum(bad,grid,spec)
    flags = [[] for _ in range(values.size)]
    flags[0] = ["gap"]
    with pytest.raises(c.MagneticContractError):
        p.continue_plane(values,grid,datum=grid["datum"],source_free=True,masks=flags)
    with pytest.raises(c.MagneticContractError):
        p.power_spectrum(values,grid,spec,masks=flags)
    for delta in (-100.,0.,None):
        bad = deepcopy(grid)
        bad["continuation_delta_m"] = delta
        with pytest.raises(c.MagneticContractError):
            p.continue_plane(values,bad,datum=grid["datum"],source_free=True)
    for datum,free in (("unknown",True),(grid["datum"],False),(grid["datum"],1)):
        with pytest.raises(c.MagneticContractError):
            p.continue_plane(values,grid,datum=datum,source_free=free)
    bad = deepcopy(grid)
    bad.update(nx=129,ny=129)
    with pytest.raises(c.MagneticContractError):
        p.power_spectrum(np.zeros((129,129)),bad,spec)
    bad = deepcopy(grid)
    bad["boundary_policy"].update(mode="reflect_pad",pad_e_cells=21,pad_n_cells=0)
    with pytest.raises(c.MagneticContractError):
        p.continue_plane(values,bad,datum=bad["datum"],source_free=True)
    params = dict(flight_azimuth_deg=90.,max_azimuth_spread_deg=5.,kc_rad_per_m=.01,ka_rad_per_m=.01,
        amplitude_cap_nT=None,promotion="diagnostic_only",spectrum_policy=spec)
    with pytest.raises(c.MagneticContractError):
        p.microlevel_diagnostic(values,grid,params,acquisition_azimuths_deg=[90.,110.])
    with pytest.raises(c.MagneticContractError):
        p.microlevel_diagnostic(values,grid,params,acquisition_azimuths_deg=[])
    for change in (dict(origin_e_m=1e16,spacing_e_m=3.),dict(plane_upward_m=1e16,continuation_delta_m=1.)):
        bad = dict(grid,**change)
        with pytest.raises(c.MagneticContractError):
            p.continue_plane(values,bad,datum=bad["datum"],source_free=True)
    bad = deepcopy(grid)
    bad["boundary_policy"].update(pad_e_cells=1)
    with pytest.raises(c.MagneticContractError):
        p.continue_plane(values,bad,datum=bad["datum"],source_free=True)
    for mode in ("zero_pad","reflect_pad"):
        bad = deepcopy(grid)
        bad["boundary_policy"].update(mode=mode,pad_e_cells=10,pad_n_cells=8,detrend="remove_mean",taper="hann")
        result = p.continue_plane(values,bad,datum=bad["datum"],source_free=True)
        assert result["values"].shape == values.shape
        assert result["transfer"].shape == (48,60)
        assert result["boundary_policy"] == bad["boundary_policy"]
    # A hole outside an explicitly selected supported rectangle does not
    # authorize full-plane continuation, but need not block its own spectrum.
    subset = deepcopy(spec)
    subset["rectangle"] = dict(e_start=2,n_start=2,nx=12,ny=12)
    assert p.power_spectrum(values,grid,subset,masks=flags)["power"].shape == (12,12)


def test_corrected_channel_blocked_fit_requires_original_replay():
    c,g = modules()
    p,v = processing(),validation()
    raw,meta,req = g.control_input("S3")
    original = (raw,c.canonical_bytes(meta),c.canonical_bytes(req))
    run = p.apply_corrections(*original)
    manifest = v.make_partitions(run["rows"],req)
    with pytest.raises(c.MagneticContractError):
        p.blocked_fit(run["rows"],req,manifest)
    result = p.blocked_fit(run["rows"],req,manifest,original_inputs=original)
    assert result["selected_candidate"] == dict(depth_m=500.,damping=.0001)
    assert result["production_fit_count"] == 25
    assert result["evaluation_count"] == 1
    assert result["processing_lineage"]["input_channel_sha256"] == req["channel_sha256"]
    assert result["processing_lineage"]["derived_output_sha256"] == run["output_sha256"]
    assert result["processing_lineage"]["fold_local"] is True
    assert result["rmse_nT"] == pytest.approx(18.799740861734186,abs=1e-6)
    changed = deepcopy(run["rows"])
    changed[0]["magnetic_nT"] += 1.
    with pytest.raises(c.MagneticContractError):
        p.blocked_fit(changed,req,manifest,original_inputs=original)
    bad = list(original)
    bad[-1] = bad[-1]+b" "
    # Extra whitespace keeps request meaning but its exact original hash is
    # distinct provenance; no arbitrary claimed input hash is accepted.
    replay = p.blocked_fit(run["rows"],req,manifest,original_inputs=tuple(bad))
    from hashlib import sha256
    assert replay["processing_lineage"]["request_original_sha256"] == sha256(bad[-1]).hexdigest()


def test_fold_local_leveling_replay_never_calibrates_from_test_values():
    c,g = modules()
    p,v = processing(),validation()
    raw,meta,req = leveling_request(g,c,*g.control_input("S2"))
    original = (raw,c.canonical_bytes(meta),c.canonical_bytes(req))
    manifest = v.make_partitions(c.parse_csv(raw)["rows"],req)
    run = p.apply_corrections(*original,training_ids=manifest["outer_training_ids"])
    # Frozen geometry A leaves only three isolated tie rows and no admissible
    # training crossings. A positive whole-DAG leveling expectation failed in
    # the retained first-run XML. Do not recover it by shrinking buffers,
    # leaking validation endpoints or bypassing the requested graph operation.
    inventory = p.crossovers(c.parse_csv(raw)["rows"],req["geometry_policy"],manifest["inner"][0]["training_ids"])
    assert sum(x["disposition"]=="admitted" for x in inventory) == 0
    with pytest.raises(c.MagneticContractError) as err:
        p.blocked_fit(run["rows"],req,manifest,original_inputs=original)
    assert err.value.error["field"] == "leveling.no_training_constraints"
    altered = c.parse_csv(raw)["rows"]
    for row in altered:
        if row["line_id"]=="F04":
            row["magnetic_nT"] += 10000.
    other_raw = g.csv_bytes(altered)
    from hashlib import sha256
    other_meta,other_req = deepcopy(meta),deepcopy(req)
    other_meta["original"].update(csv_sha256=sha256(other_raw).hexdigest(),csv_bytes=len(other_raw))
    other_req["dataset_version_sha256"] = c.dataset_identity(other_meta["original"]["csv_sha256"],c.digest(other_meta))
    other_req["channel_sha256"] = other_req["split"]["sealed_values_sha256"] = c.channel_identity(altered)
    for op in other_req["operations"]:
        op["input_channel_sha256"] = other_req["channel_sha256"]
    other = (other_raw,c.canonical_bytes(other_meta),c.canonical_bytes(other_req))
    other_run = p.apply_corrections(*other,training_ids=manifest["outer_training_ids"])
    other_manifest = v.make_partitions(other_run["rows"],other_req)
    assert other_run["leveling"]["offsets"] == run["leveling"]["offsets"]
    for a,b in zip(run["rows"],other_run["rows"]):
        assert b["magnetic_nT"] == pytest.approx(a["magnetic_nT"]+(10000 if a["line_id"]=="F04" else 0),abs=1e-6)
    with pytest.raises(c.MagneticContractError) as err:
        p.blocked_fit(other_run["rows"],other_req,other_manifest,original_inputs=other)
    assert err.value.error["field"] == "leveling.no_training_constraints"
    bad = deepcopy(req)
    bad["operations"][-1]["parameters"]["heldout_calibration"] = None
    failed_inputs = (raw,c.canonical_bytes(meta),c.canonical_bytes(bad))
    failed = p.apply_corrections(*failed_inputs,training_ids=manifest["outer_training_ids"])
    with pytest.raises(c.MagneticContractError):
        p.blocked_fit(failed["rows"],bad,v.make_partitions(failed["rows"],bad),original_inputs=failed_inputs)


def test_s4_s5_s6_original_controls_are_distinct_and_not_field_completion():
    c,g = modules()
    p,v = processing(),validation()
    baseline = g.control_rows("S1")
    for regime in ("S4","S5","S6"):
        raw,meta,req = g.control_input(regime)
        intake = c.load_lines(raw,c.canonical_bytes(meta),c.canonical_bytes(req))
        assert meta["authored_control"]["notice"] == "synthetic, not field"
        assert meta["authored_control"]["regime"] == regime
        assert intake["provider_authenticated"] is False
        assert len(intake["rows"]) == 363
        assert g.control_input(regime) == (raw,meta,req)
        if regime=="S4":
            assert "measurement_missing" in intake["eligibility_reasons"]
            assert "upward_missing" in intake["eligibility_reasons"]
            assert "timestamp_missing" in intake["eligibility_reasons"]
            with pytest.raises(c.MagneticContractError):
                v.make_partitions(intake["rows"],req)
        else:
            assert v.make_partitions(intake["rows"],req)["geometry_only_coverage"]["fraction"] == 1.
            for row,parent in zip(intake["rows"],baseline):
                n = row["northing_m"]
                term = math.sin(2*math.pi*n/150) if regime=="S5" else math.cos(2*math.pi*n/1600)+math.cos(2*math.pi*n/800)
                assert row["magnetic_nT"]-parent["magnetic_nT"] == pytest.approx(term,abs=1e-12)
    # A periodic supplementary S5 oracle: two distinct wavelengths produce
    # identical observations at exactly uniform400m cross-line positions.
    import numpy as np
    positions = np.arange(-1600,1601,400.)
    fine_frequency = 1/150
    alias_frequency = fine_frequency-3/400
    assert np.cos(2*np.pi*fine_frequency*positions) == pytest.approx(np.cos(2*np.pi*alias_frequency*positions),abs=1e-12)
    assert abs(alias_frequency) != fine_frequency
    assert p.MASK_ORDER[-2] == "sampling_unresolved"


def test_sampling_aliasing_and_support_masks():
    c,g = modules()
    p = processing()
    raw,_,req = g.control_input("S5")
    rows = c.parse_csv(raw)["rows"]
    policy = deepcopy(req["geometry_policy"])
    policy["minimum_resolved_wavelength_m"] = 150.
    grid = deepcopy(req["grid"])
    grid.update(origin_e_m=-2300.,origin_n_m=-1600.,nx=93,ny=65)
    result = p.support_masks(rows,rows,grid,policy,sensor_id="S0")
    assert result["total_count"] == 93*65
    assert len(result["masks"]) == result["total_count"]
    assert all("sampling_unresolved" in flags for flags in result["masks"])
    assert any("outside_hull" in flags for flags in result["masks"])
    assert any("beyond_support_radius" in flags for flags in result["masks"])
    assert result["eligible_count"] < result["total_count"]
    assert len(result["line_statistics"]) == 11
    assert all(s["spacing_max_m"]>0 for s in result["line_statistics"])
    # Authored +/-5m jitter can change centroid separations by up to10m.
    assert all(320<s["local_perpendicular_spacing_m"]<460 for s in result["line_statistics"] if s["line_id"].startswith("F"))
    fine = deepcopy(grid)
    fine.update(spacing_e_m=25.,spacing_n_m=25.,nx=145,ny=121)
    # Cannot silently shrink this requested grid below its explicit cell cap.
    with pytest.raises(c.MagneticContractError):
        p.support_masks(rows,rows,fine,policy,sensor_id="S0")
    gap_rows = deepcopy(rows)
    gap_rows[16]["magnetic_nT"] = None
    hole = p.support_masks(gap_rows,[r for r in gap_rows if r["magnetic_nT"] is not None],grid,policy,sensor_id="S0")
    assert any("gap" in flags for flags in hole["masks"])
    assert hole["eligible_count"] < result["eligible_count"]
    # A deliberate CV exclusion is not a missing acquisition hole.
    training = [r for r in rows if r["line_id"]!="F04"]
    excluded = p.support_masks(rows,training,grid,policy,sensor_id="S0")
    assert not any("gap" in flags for flags in excluded["masks"])
    noheight = deepcopy(rows)
    noheight[0]["upward_m"] = None
    unresolved = p.support_masks(noheight,[r for r in noheight if r["upward_m"] is not None],grid,policy,sensor_id="S0")
    assert any("height_mismatch" in flags for flags in unresolved["masks"])
    with pytest.raises(c.MagneticContractError):
        p.support_masks(rows,rows,grid,policy,sensor_id="missing")


def test_geometric_baseline_and_source_preserving_grid_orchestration():
    import numpy as np
    c,g = modules()
    p = processing()
    plane = [r for r in g.control_rows("S2") if r["line_kind"]=="tie"]
    query = [[-300.,-300.,80.],[400.,700.,80.],[5000.,0.,80.]]
    result = p.geometric_comparator(plane,query,same_plane_height_tolerance_m=0.)
    assert result["values"][:2] == pytest.approx([10+.002*q[0]-.003*q[1] for q in query[:2]],abs=1e-9)
    assert result["values"][-1] is None
    assert result["masks"][-1] == ["outside_hull"]
    assert result["height_transform_claim"] is False
    # Independent barycentric plane oracle at a single triangle.
    triangle = [dict(plane[0],row_id=f"R{i}",easting_m=e,northing_m=n,magnetic_nT=10+.002*e-.003*n,ordinal=i)
        for i,(e,n) in enumerate(((0.,0.),(100.,0.),(0.,100.)))]
    one = p.geometric_comparator(triangle,[[25.,25.,80.]],same_plane_height_tolerance_m=0.)
    assert one["values"] == pytest.approx([.5*10+.25*10.2+.25*9.7],abs=1e-9)
    for tolerance,coords in ((None,query),(0.,[[0.,0.,81.]])):
        with pytest.raises(c.MagneticContractError):
            p.geometric_comparator(plane,coords,same_plane_height_tolerance_m=tolerance)
    bad = deepcopy(triangle)
    for row in bad:
        row["northing_m"] = 0.
    with pytest.raises(c.MagneticContractError):
        p.geometric_comparator(bad,[[0.,0.,80.]],same_plane_height_tolerance_m=0.)
    # Actual source-preserving complete local orchestration for S1. The run
    # reports its failed quality target; this test does not waive that gate.
    raw,meta,req = g.control_input("S1")
    run = p.fit_grid(raw,c.canonical_bytes(meta),c.canonical_bytes(req))
    assert run["fit"]["evaluation_count"] == 1
    assert run["synthetic_quality_verdict"] == "fail"
    assert run["fit"]["rmse_nT"] == pytest.approx(18.799740861734186,abs=1e-9)
    assert run["comparator"]["verdict"] == "ineligible"
    assert run["grid"]["values"].shape == (49,65)
    assert run["continued_grid"]["values"].shape == (49,65)
    assert run["continued_grid"]["plane_upward_m"] == 220.
    assert run["continued_grid"]["method"] == "direct_equivalent_source_prediction"
    assert run["fft_continuation"]["verdict"] == "eligible"
    assert run["fft_continuation"]["result"]["values"].shape == (49,65)
    # Original grid extent lies within the anchors and nearest-flight radius.
    # Geometric support does not make its failed predictive target acceptable.
    assert all(v is not None for v in run["grid"]["masked_values"])
    assert run["processing"]["original_rows"] == c.parse_csv(raw)["rows"]
    assert run["provider_authenticated"] is False
    assert run["field_acceptance"] == "unresolved"
    fit = run["fit"]["final_fit"]
    coords = [[-450.,150.,220.],[650.,-250.,220.]]
    source = np.array([[s[k] for k in ("easting_m","northing_m","upward_m")] for s in fit["source_positions"]])
    independent = sum(coefficient/np.linalg.norm(np.array(coords)-pos,axis=1) for coefficient,pos in zip(fit["coefficients"],source))
    assert p.predict_equivalent(fit,coords) == pytest.approx(independent,rel=1e-9,abs=1e-6)


def test_weighted_augmented_qr_raw_units_and_negative_error_range():
    import numpy as np
    from scipy.linalg import lstsq
    c,g = modules()
    p = processing()
    rows = g.control_rows("S1")[:33]+g.control_rows("S1")[66:99]
    for i,row in enumerate(rows):
        row["uncertainty_nT"] = 1.+.1*(i%7)  # Authored oracle errors, not field.
    _,_,req = g.geometry_input()
    config = deepcopy(req["equivalent_sources"])
    config.update(weights_policy="admitted_inverse_variance",damping_unit="nT^-2")
    run = p.fit_equivalent(rows,config,200.,.01)
    xyz = np.array([[r[k] for k in ("easting_m","northing_m","upward_m")] for r in rows])
    sources = np.array([[r[k] for k in ("easting_m","northing_m","upward_m")] for r in run["source_positions"]])
    kernel = 1/np.linalg.norm(xyz[:,None,:]-sources[None,:,:],axis=2)
    scale = kernel.std(axis=0,ddof=0)
    a = kernel/scale
    d = np.array([r["magnetic_nT"] for r in rows])
    w = 1/np.array([r["uncertainty_nT"] for r in rows])**2
    def solve(data,weights,penalty):
        augmented = np.vstack((np.sqrt(weights)[:,None]*a,math.sqrt(penalty)*np.eye(a.shape[1])))
        rhs = np.concatenate((np.sqrt(weights)*data,np.zeros(a.shape[1])))
        coefficients = lstsq(augmented,rhs,lapack_driver="gelsy")[0]
        objective = np.sum(weights*(a@coefficients-data)**2)+penalty*np.sum(coefficients**2)
        return coefficients,objective
    coefficients,objective = solve(d,w,.01)
    assert run["coefficients"] == pytest.approx(coefficients/scale,rel=1e-9,abs=1e-6)
    assert run["objective"]["total"] == pytest.approx(objective,rel=1e-8)
    assert run["objective"]["unit"] == "dimensionless"
    assert run["objective"]["damping_unit"] == "nT^-2"
    scaled,scaled_objective = solve(d,7*w,7*.01)
    assert scaled == pytest.approx(coefficients,rel=1e-9,abs=1e-6)
    assert scaled_objective == pytest.approx(7*objective,rel=1e-8)
    changed,_ = solve(d,7*w,.01)
    assert np.linalg.norm(changed-coefficients)>1e-3
    converted,converted_objective = solve(1000*d,w/1000**2,.01/1000**2)
    assert converted == pytest.approx(1000*coefficients,rel=1e-9,abs=1e-6)
    assert converted_objective == pytest.approx(objective,rel=1e-8)
    for sigma in (1e-300,1e308,0.):
        bad = deepcopy(rows)
        for row in bad:
            row["uncertainty_nT"] = sigma
        with pytest.raises(c.MagneticContractError):
            p.fit_equivalent(bad,config,200.,.01)
