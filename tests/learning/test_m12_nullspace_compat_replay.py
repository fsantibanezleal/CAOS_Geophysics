from __future__ import annotations

from scripts.verify_m12_nullspace_v1_1_compat import _ReplayScores


def test_replay_score_mapping_accepts_only_float_roundoff():
    expected = {"1": 33.7008983045821, "100": 17.61679311450284}
    recomputed = _ReplayScores({"1": 33.70089830458232, "100": 17.61679311450284})
    assert recomputed == expected


def test_replay_score_mapping_rejects_changed_candidates_or_values():
    expected = {"1": 33.7008983045821, "100": 17.61679311450284}
    assert _ReplayScores({"1": expected["1"], "10": expected["100"]}) != expected
    assert _ReplayScores({"1": 33.7009, "100": 17.61679311450284}) != expected
