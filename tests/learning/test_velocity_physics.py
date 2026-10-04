"""Dimensional controls and fresh realization identities for revised M12."""
import hashlib
import os
from pathlib import Path

import numpy as np
import pytest
import torch

import velocity_physics_refinement as refined
import velocity_validation as original


def test_uniform_slowness_feature_oracle():
    a = original.cell_length_matrix(original.acquisition("A"))
    s0 = 1 / original.background().ravel()
    delta = 1e-5
    observed = a @ (s0 + delta)
    feature = refined.input_features(observed, a)
    expected = -delta * original.background() ** 2 / 400
    supported = a.sum(axis=0).reshape(16, 16) > 0
    expected[~supported] = 0
    np.testing.assert_allclose(feature[0], expected, rtol=1e-6, atol=1e-6)
    assert np.all(feature[0][supported] < 0)
    assert np.all(feature[0][~supported] == 0)
    assert np.max(feature[1]) == 1
    null = a.copy()
    null[:, 0] = 0
    result = refined.input_features(null @ s0, null)
    assert result[0, 0, 0] == 0 and result[1, 0, 0] == 0
    with pytest.raises(ValueError):
        refined.input_features(observed, np.zeros_like(a))


def test_fresh_cohorts_and_original_preservation():
    ops = original.operators()
    old = {seed + i for count, seed, _, _ in original.COHORTS.values() for i in range(count)}
    new = set()
    for name in refined.COHORTS:
        cohort = refined.make_cohort(name, ops, fixture=True)
        seeds = {x["seed"] for x in cohort["records"]}
        assert seeds.isdisjoint(old | new)
        new |= seeds
        assert all(x["id"].startswith("m12-physics-v2:") for x in cohort["records"])
        assert refined.make_cohort(name, ops, fixture=True)["manifest_sha256"] == cohort["manifest_sha256"]
    trained = set(refined.COHORTS["train"][2])
    assert trained.isdisjoint(refined.COHORTS["joint_ood"][2])
    assert original.COHORTS["train"][1] == 17001
    assert original.sha256_bytes((Path(original.__file__)).read_bytes()) == "2b9ed95d3ba7b1b0f9f80167fa610640dc75c8a142dafb9f7f09791b96a1fd44"


def test_network_reference_bounds_and_checkpoint(tmp_path):
    model = refined.network()
    torch.set_num_threads(4)
    output = model(torch.zeros(2, 2, 16, 16)).detach().numpy()
    np.testing.assert_allclose(output[0], original.background(), rtol=1e-6, atol=1e-4)
    with torch.no_grad():
        model.net[-1].bias.fill_(100)
    output = model(torch.ones(2, 2, 16, 16)).detach().numpy()
    assert np.all((output >= 1400) & (output <= 4000))
    path = tmp_path / "model.npz"
    sha = original.save_checkpoint(model, path)
    restored = refined.load_checkpoint(path, sha)
    np.testing.assert_array_equal(restored(torch.ones(2, 2, 16, 16)).detach().numpy(), output)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sha


def test_scientific_verdict_preserves_failure():
    assert original.scientific_verdict({"learned_to_classical_velocity_ratio": 2,
                                       "learned_to_classical_oracle_ratio": 0.9}) == "failed-held-out-comparator"


def test_fixture_is_not_full_receipt(tmp_path):
    result = refined.execute(tmp_path / "fixture", device="cpu", fixture=True)
    assert result["status"] == "fixture-only"
    assert result["epochs"] == 1
    assert all(count == 12 for count in result["counts"].values())
    with pytest.raises(ValueError, match="Fixture"):
        refined.verify(tmp_path / "fixture")


def test_frozen_receipt_and_replay():
    root = Path(__file__).resolve().parents[2]
    output = Path(os.environ.get("M12_PHYSICS_RECEIPT", root / "models/experimental/m12-physics-cuda-20261004"))
    receipt = refined.verify(output)
    assert receipt["device"] == "cuda"
    assert receipt["epochs"] == len(receipt["history"]) == 40
    assert receipt["counts"] == {name: value[0] for name, value in refined.COHORTS.items()}
    assert receipt["original_benchmark"].startswith("failed-held-out-comparator")
