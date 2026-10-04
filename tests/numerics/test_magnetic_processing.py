"""M03 T02 geometry/preflight only; later physics gates are not implemented."""
from copy import deepcopy
import importlib
import math

import pytest

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
    v = validation()
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
