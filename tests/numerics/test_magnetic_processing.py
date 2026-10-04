"""M03 T02 geometry/preflight only; later physics gates are not implemented."""
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
