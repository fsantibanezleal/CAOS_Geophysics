"""Survey-grid shape contracts for learned potential-field models."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data-pipeline"))

import learning


@pytest.mark.parametrize("shape", [(16, 16), (32, 32)])
def test_cnn_and_autoencoder_follow_geology_survey_shape(monkeypatch, shape):
    monkeypatch.setattr(learning.geology, "SURVEY_SHAPE", shape, raising=False)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    cnn = learning.InverseCNN().to(device)
    autoencoder = learning.ObservationAE().to(device)
    sample = torch.zeros((2, 1, *shape), dtype=torch.float32, device=device)

    assert cnn.input_shape == shape
    cnn_output = cnn(sample)
    assert cnn_output.shape == (2, *learning.VOLUME_SHAPE[1:])
    assert cnn_output.device.type == device
    assert autoencoder.input_shape == shape
    reconstruction = autoencoder(sample)
    assert reconstruction.shape == sample.shape
    assert reconstruction.device.type == device
    with pytest.raises(ValueError, match="CNN expects"):
        cnn(torch.zeros((1, 1, 16, 16))) if shape != (16, 16) else cnn(torch.zeros((1, 1, 32, 32)))


def test_training_tensor_builder_checks_count_and_preserves_32_by_32_layout(monkeypatch):
    shape = (32, 32)
    monkeypatch.setattr(learning.geology, "SURVEY_SHAPE", shape, raising=False)
    values = np.arange(3 * np.prod(shape), dtype=np.float32).reshape(3, -1)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tensor = learning._observation_tensor(values, learning.survey_shape(), 2.0, device)

    assert tuple(tensor.shape) == (3, 1, 32, 32)
    assert tensor.device.type == device
    assert tensor[0, 0, 0, 0].item() == pytest.approx(values[0, 0] / 2)
    assert tensor[0, 0, -1, -1].item() == pytest.approx(values[0, -1] / 2)
    with pytest.raises(ValueError, match="Expected observations"):
        learning._observation_tensor(values[:, :-1], shape, 2.0, device)


def test_checkpoint_schema_binds_weights_to_survey_geometry(monkeypatch, tmp_path):
    monkeypatch.setattr(learning.geology, "SURVEY_SHAPE", (32, 32), raising=False)
    model = learning.ObservationAE()
    path = tmp_path / "autoencoder.json"
    digest = learning.checkpoint(model, path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema"] == "inverse-earth.learned-potential-checkpoint/v1"
    assert payload["survey_shape"] == [32, 32]
    assert digest == learning.hashlib.sha256(path.read_bytes()).hexdigest()
    restored = learning.load_checkpoint(learning.ObservationAE(), path)
    assert restored.input_shape == (32, 32)
    with pytest.raises(ValueError, match="Checkpoint survey shape"):
        learning.load_checkpoint(learning.ObservationAE(input_shape=(16, 16)), path)


def test_unversioned_checkpoint_is_only_accepted_for_legacy_geometry(monkeypatch, tmp_path):
    legacy = learning.ObservationAE(input_shape=(16, 16))
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps({
        name: {"shape": list(value.shape), "values": value.detach().cpu().numpy().ravel().tolist()}
        for name, value in legacy.state_dict().items()
    }), encoding="utf-8")

    monkeypatch.setattr(learning.geology, "SURVEY_SHAPE", (16, 16), raising=False)
    assert learning.load_checkpoint(learning.ObservationAE(), path).input_shape == (16, 16)
    monkeypatch.setattr(learning.geology, "SURVEY_SHAPE", (32, 32), raising=False)
    with pytest.raises(ValueError, match="legacy checkpoint is fixed to 16x16"):
        learning.load_checkpoint(learning.ObservationAE(), path)


def test_legacy_training_bundle_is_rejected_for_refined_survey(tmp_path, monkeypatch):
    monkeypatch.setattr(learning.geology, "SURVEY_SHAPE", (32, 32), raising=False)
    (tmp_path / "training.json").write_text(json.dumps({"schema": "inverse-earth.learning/v2"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Legacy learning bundle is fixed to 16x16"):
        learning.load_bundle(tmp_path, device="cpu")


def test_training_and_validation_run_with_refined_survey_shape(tmp_path, monkeypatch):
    shape = (32, 32)
    monkeypatch.setattr(learning.geology, "SURVEY_SHAPE", shape, raising=False)
    monkeypatch.setattr(learning, "VOLUME_SHAPE", (2, 2, 2))
    monkeypatch.setattr(learning, "VOLUME_SPACING", (1.0, 1.0, 70.0))
    mesh = type("Mesh", (), {"cell_centers": np.zeros((8, 3))})()
    rng = np.random.default_rng(73)
    forward = rng.normal(size=(np.prod(shape), 8))
    monkeypatch.setattr(
        learning, "generate",
        lambda _centers, count, seed: np.random.default_rng(seed).normal(size=(count, 8)),
    )
    monkeypatch.setattr(
        learning, "generate_ood",
        lambda _centers: np.random.default_rng(59001).normal(size=(80, 8)),
    )
    monkeypatch.setattr(learning, "invert", lambda _G, _data, _sigma: {"model": np.zeros(8).tolist()})

    prior_determinism = torch.are_deterministic_algorithms_enabled()
    prior_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    torch.use_deterministic_algorithms(True)
    try:
        cnn, autoencoder, metadata = learning.train(mesh, forward, tmp_path, epochs=1)
    finally:
        torch.use_deterministic_algorithms(prior_determinism, warn_only=prior_warn_only)

    expected_device = "cuda" if torch.cuda.is_available() else "cpu"
    assert metadata["schema"] == "inverse-earth.learning/v3"
    assert metadata["survey_shape"] == [32, 32]
    assert metadata["device"] == expected_device
    assert metadata["gpu"] == (torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
    assert cnn.input_shape == autoencoder.input_shape == shape
    assert cnn(torch.zeros((1, 1, *shape), device=expected_device)).shape == (1, 2, 2)
    assert autoencoder(torch.zeros((1, 1, *shape), device=expected_device)).shape == (1, 1, *shape)
    saved = json.loads((tmp_path / "training.json").read_text(encoding="utf-8"))
    assert saved["survey_shape"] == [32, 32]
    assert saved["device"] == expected_device


def test_irregular_pool_matches_adaptive_values_and_has_deterministic_cuda_backward():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    values = torch.randn((2, 3, 17, 19), dtype=torch.float32, device=device, requires_grad=True)
    pool = learning.DeterministicAdaptiveAveragePool2d((17, 19), (4, 4)).to(device)
    expected = torch.nn.functional.adaptive_avg_pool2d(values.detach(), (4, 4))
    prior_determinism = torch.are_deterministic_algorithms_enabled()
    prior_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    torch.use_deterministic_algorithms(True)
    try:
        actual = pool(values)
        actual.square().mean().backward()
    finally:
        torch.use_deterministic_algorithms(prior_determinism, warn_only=prior_warn_only)

    assert actual.shape == (2, 3, 4, 4)
    torch.testing.assert_close(actual, expected, rtol=1e-6, atol=1e-7)
    assert values.grad is not None and torch.isfinite(values.grad).all()


def test_attach_reconstructs_and_infers_on_canonical_32_by_32_grid(monkeypatch):
    shape = (32, 32)
    monkeypatch.setattr(learning.geology, "SURVEY_SHAPE", shape, raising=False)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    cnn = learning.InverseCNN(input_shape=shape).to(device).eval()
    autoencoder = learning.ObservationAE(input_shape=shape).to(device).eval()
    observed = np.linspace(-1, 1, np.prod(shape), dtype=np.float64)
    n_cells = int(np.prod(learning.VOLUME_SHAPE))
    run = {
        "variant": "reference",
        "truth": np.zeros(n_cells).tolist(),
        "survey": {
            "shape": list(shape),
            "observed": observed.tolist(),
            "active": np.ones(observed.size, dtype=bool).tolist(),
            "locations": np.column_stack((np.arange(observed.size), np.zeros((observed.size, 2)))).tolist(),
        },
        "methods": {
            name: {"model": np.zeros(n_cells).tolist(), "metrics": {}}
            for name in ("l2", "irls")
        },
    }
    metadata = {
        "survey_shape": list(shape), "input_scale": 1.0, "target_scale": 400.0,
        "novelty_threshold": 1.0,
        "models": {
            "cnn": {"sha256": "cnn-hash", "history": []},
            "autoencoder": {"sha256": "ae-hash", "history": []},
        },
        "novelty_evaluation": {},
    }

    result = learning.attach(run, (cnn, autoencoder, metadata))

    assert np.asarray(result["methods"]["cnn"]["model"]).shape == learning.VOLUME_SHAPE[1:]
    for key in ("model", "predicted", "residual", "network_input"):
        assert np.asarray(result["methods"]["autoencoder"][key]).size == np.prod(shape)
    assert np.asarray(result["methods"]["autoencoder"]["model"]).shape == shape
    np.testing.assert_allclose(
        result["methods"]["autoencoder"]["residual"],
        np.asarray(result["methods"]["autoencoder"]["network_input"])
        - np.asarray(result["methods"]["autoencoder"]["predicted"]),
        atol=1e-6,
    )
