"""Geometry-only supplied folds, original provider parity and scaled gates."""
from copy import deepcopy

import numpy as np
import pytest

import traveltime as engine


def survey(n):
    points = np.column_stack((np.arange(2*n, dtype=float), np.zeros(2*n)))
    pairs = np.asarray([(s, g) for s in range(n) for g in range(2*n) if s != g])
    return engine.Survey(points, pairs, np.abs(pairs[:, 1] - pairs[:, 0]) / 1000)


@pytest.mark.parametrize("n", [10, 15, 20, 25])
def test_supplied_folds_geometry_and_complete_rows(n):
    original = survey(n)
    split = engine.shot_splits(original, policy="supplied-whole-shot/v1")
    changed = engine.Survey(original.sensor_xy_m, original.shot_geophone,
                            original.time_s * np.linspace(0.5, 5, len(original.time_s)))
    other = engine.shot_splits(changed, policy="supplied-whole-shot/v1")
    k = (n + 4) // 5
    expected = {"interleaved": [((j + 1) * n) // k - 1 for j in range(k)],
                "central_block": list(range((n-k)//2, (n-k)//2+k))}
    for name, parts in split.items():
        assert parts["held_shots"].tolist() == expected[name]
        assert parts["held_shots"].tolist() == other[name]["held_shots"].tolist()
        training, held = parts["training_rows"], parts["held_rows"]
        assert len(training) >= 100 and len(held) >= 30
        assert set(training).isdisjoint(held)
        assert sorted([*training, *held]) == list(range(len(original.time_s)))
        assert set(original.shot_geophone[training, 0]).isdisjoint(original.shot_geophone[held, 0])


def test_original_provider_policy_parity_and_refusal():
    source = survey(15)
    old = engine.shot_splits(source)
    new = engine.shot_splits(source, policy="supplied-whole-shot/v1")
    for fold in old:
        for key in old[fold]:
            assert np.array_equal(old[fold][key], new[fold][key])
    with pytest.raises(engine.TraveltimeError):
        engine.shot_splits(survey(20))
    for n in (5, 9):
        with pytest.raises(engine.TraveltimeError):
            engine.shot_splits(survey(n), policy="supplied-whole-shot/v1")
    with pytest.raises(engine.TraveltimeError):
        engine.shot_splits(source, policy="unknown")


def test_scaled_held_shot_gate_never_accepts_two_of_five():
    fit = {"engine_stopped_before_limit": True, "heldout_improvement": 0.25,
           "improved_held_shot_count": 2}
    fits = {name: deepcopy(fit) for name in ("interleaved", "central_block")}
    assert engine._field_verdict(fits)[0] == "passed"
    assert engine._field_verdict(fits, minimum_improved_shots=4)[0] == "not-converged"
    for fit in fits.values():
        fit["improved_held_shot_count"] = 4
    assert engine._field_verdict(fits, minimum_improved_shots=4)[0] == "passed"


@pytest.mark.parametrize("n", [10, 15, 20, 25])
def test_exported_supplied_rule_describes_the_actual_variable_fold(n):
    splits = engine.shot_splits(survey(n), policy="supplied-whole-shot/v1")
    for name, parts in splits.items():
        record = engine._split_record(name, parts, policy="supplied-whole-shot/v1")
        assert record["policy"] == "supplied-whole-shot/v1"
        assert "ceil(N/5)" in record["rule"]
        assert record["held_shots_zero_based"] == parts["held_shots"].tolist()
        assert "three central" not in record["rule"]


def test_pinned_split_provenance_stays_byte_compatible():
    parts = engine.shot_splits(survey(15))
    for name, fold in parts.items():
        assert engine._split_record(name, fold) == engine._split_record(name, fold, policy="pinned-15/v1")
        assert "policy" not in engine._split_record(name, fold)
