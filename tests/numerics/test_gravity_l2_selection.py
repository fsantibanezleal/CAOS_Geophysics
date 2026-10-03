"""Geometry-only partition controls before any sealed value or solver selection."""

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

import gravity_survey_l2 as survey


def request():
    # Test-owned specification helper; production cannot import a caller path.
    path = Path(__file__).resolve().parents[1] / 'data/test_gravity_survey_l2.py'
    spec = importlib.util.spec_from_file_location('_l2_authored_controls', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.planning_request()


def independent_line_roles(req):
    ordered = []
    for j in range(12):
        ids = tuple(sorted(f"station:{i}:{j}" for i in range(12)))
        encoded = json.dumps({"seed": 104729, "station_ids": ids}, sort_keys=True,
                             separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
        ordered.append((hashlib.sha256(encoded).hexdigest(), ids, j))
    order = [x[2] for x in sorted(ordered)]
    return order[:3], [order[3 + fold::3] for fold in range(3)]


def test_frozen_geometry_blocks_groups_buffers():
    req = request()
    plan = survey.plan_gravity_l2(req)
    outer, fold_lines = independent_line_roles(req)
    assert set(plan["outer_rows"] // 12) == set(outer)
    assert len(plan["outer_rows"]) == 36 and len(plan["development_rows"]) == 108
    assert len(plan["embargo_rows"]) == 0
    for fold in plan["folds"]:
        assert set(fold["validation_rows"] // 12) == set(fold_lines[fold["fold"]])
        assert len(fold["fit_rows"]) == 72 and len(fold["validation_rows"]) == 36
        assert not set(fold["fit_rows"]) & set(fold["validation_rows"])
        assert not set(fold["fit_rows"]) & set(plan["outer_rows"])
    perm = np.arange(143, -1, -1)
    reordered = deepcopy(req)
    for key, value in req["stations"].items():
        reordered["stations"][key] = value[perm] if type(value) is np.ndarray else tuple(value[i] for i in perm)
    reordered["background_mgal"] = req["background_mgal"][perm]
    other = survey.plan_gravity_l2(reordered)
    np.testing.assert_array_equal(np.sort(perm[other["outer_rows"]]), plan["outer_rows"])
    for a, b in zip(plan["folds"], other["folds"]):
        np.testing.assert_array_equal(np.sort(perm[b["fit_rows"]]), a["fit_rows"])


@pytest.mark.parametrize("kind", ["single_group", "buffer", "collinear", "huge_block_index", "too_few_rows"])
def test_partition_failures_no_retry_or_fallback(kind):
    req = request()
    if kind == "single_group": req["stations"]["partition_group_ids"] = ("campaign",) * 144
    if kind == "buffer": req["split"]["buffer_m"] = 10000.
    if kind == "collinear": req["stations"]["receivers_m"][:, 1] = 0.
    if kind == "huge_block_index": req["split"]["block_size_m"][:] = 1e-300
    if kind == "too_few_rows":
        req["stations"]["excluded"][::2] = True
        req["stations"]["exclusion_reasons"] = tuple("gap" if i % 2 == 0 else "" for i in range(144))
    with pytest.raises(ValueError): survey.plan_gravity_l2(req)
