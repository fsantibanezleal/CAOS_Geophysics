"""M03 geometry and local operator controls, including the unwaived S1 failure."""
from copy import deepcopy
import importlib
import math

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
from test_magnetic_lines import modules


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
