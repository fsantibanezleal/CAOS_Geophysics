"""Lossless magnetic Result history table controls."""

import copy

import numpy as np
import pytest

from magnetic_survey_json import InputError
from magnetic_survey_bundle import decode_history_table, encode_history_table


@pytest.fixture
def candidates():
    betas = (0.0001, 0.001, 0.01, 0.1, 1., 10., 100., 1000.)
    return [{"id": f"b{beta:02d}-{penalty}", "beta": value,
             "penalty": penalty, "folds": [], "status": "failed", "score": None}
            for beta, value in enumerate(betas)
            for penalty in ("l2", "sparse_smallness")]


def record(candidate, *, phase="l2", status="iterating", fold=0, outer=0, inner=0,
           beta=0.0001, epsilon=0.0, hash_value="f"*64):
    return {"candidate": candidate, "fold": fold, "phase": phase,
            "outer_iteration": outer, "inner_iteration": inner,
            "beta": beta, "epsilon_q": epsilon, "phi_d": 1.25,
            "phi_regularizer": 2.5, "objective": 3.75, "kkt_inf": 0.000125,
            "model_sha256": hash_value, "status": status}


def test_roundtrip_history_records_preserves_order_and_signed_hash_words(candidates):
    histories = [
        record(candidates[0]["id"], outer=2, inner=19, hash_value="80"+"01"*31),
        record(candidates[7]["id"], phase="irls_surrogate", status="converged",
               fold=-1, outer=4, inner=20, beta=0.1, epsilon=0.0001,
               hash_value="00"+"fe"*31),
        record(candidates[15]["id"], phase="irls_fixed", status="failed",
               fold=2, outer=5, inner=9, beta=1000., epsilon=0.001,
               hash_value="ab"*32),
    ]
    members, payloads = encode_history_table(histories, candidates)
    assert [member["name"] for member in members] == [
        "history-index.npy", "history-numeric.npy", "history-model-hash-words.npy"]
    assert [member["shape"] for member in members] == [[3, 6], [3, 6], [3, 4]]
    restored = decode_history_table(members, payloads, candidates)
    assert [row["candidate"] for row in restored] == [row["candidate"] for row in histories]
    assert [row["model_sha256"] for row in restored] == [row["model_sha256"] for row in histories]
    for key in ("fold", "phase", "outer_iteration", "inner_iteration", "status"):
        assert [row[key] for row in restored] == [row[key] for row in histories]
    for key in ("beta", "epsilon_q", "phi_d", "phi_regularizer", "objective", "kkt_inf"):
        assert [row[key] for row in restored] == [float(row[key]) for row in histories]


def test_empty_history_uses_only_explicit_zero_sized_history_members(candidates):
    members, payloads = encode_history_table([], candidates)
    assert [member["shape"] for member in members] == [[0, 6], [0, 6], [0, 4]]
    assert decode_history_table(members, payloads, candidates) == []


@pytest.mark.parametrize("change", ["candidate", "fold", "phase", "counter", "epsilon", "hash"])
def test_encoder_rejects_invalid_history_records(candidates, change):
    item = record(candidates[0]["id"])
    if change == "candidate":
        item["candidate"] = "missing"
    elif change == "fold":
        item["fold"] = 3
    elif change == "phase":
        item["phase"] = "unknown"
    elif change == "counter":
        item["inner_iteration"] = -1
    elif change == "epsilon":
        item["epsilon_q"] = 0.01
    else:
        item["model_sha256"] = "F" * 64
    with pytest.raises(InputError):
        encode_history_table([item], candidates)


def test_encoder_requires_contract_candidate_order_and_beta(candidates):
    swapped = copy.deepcopy(candidates)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    with pytest.raises(InputError):
        encode_history_table([], swapped)
    mismatch = copy.deepcopy(candidates)
    mismatch[0]["beta"] = 0.001
    with pytest.raises(InputError):
        encode_history_table([], mismatch)
    wrong_history_beta = record(candidates[0]["id"], beta=0.001)
    with pytest.raises(InputError):
        encode_history_table([wrong_history_beta], candidates)


def test_decoder_rejects_tampered_index_even_when_member_hash_is_recomputed(candidates):
    members, payloads = encode_history_table([record(candidates[0]["id"])], candidates)
    corrupted = np.array([999, 0, 0, 0, 0, 0], dtype=np.int64).reshape(1, 6)
    from magnetic_survey_bundle import encode_array_member
    descriptor, raw = encode_array_member(corrupted, name="history-index.npy", unit="index")
    changed_members = [descriptor if item["name"] == "history-index.npy" else item
                      for item in members]
    changed_payloads = dict(payloads, **{"history-index.npy": raw})
    with pytest.raises(InputError):
        decode_history_table(changed_members, changed_payloads, candidates)


def test_decoder_rejects_missing_or_extra_history_members(candidates):
    members, payloads = encode_history_table([], candidates)
    with pytest.raises(InputError):
        decode_history_table(members[:2], payloads, candidates)
    extra_members = copy.deepcopy(members) + [copy.deepcopy(members[0])]
    with pytest.raises(InputError):
        decode_history_table(extra_members, payloads, candidates)
