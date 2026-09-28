"""Model-shape, gradient, target and inference-rule oracles (not accuracy claims)."""

import numpy as np
import pytest
import torch

from phase_model import (
    PhaseUNet, SAMPLES, gaussian_targets, pick_probabilities,
    weighted_soft_cross_entropy,
)


def test_phase_unet_tensor_contract_and_gradient():
    torch.manual_seed(8)
    model = PhaseUNet()
    waveform = torch.randn(2, 3, SAMPLES)
    logits = model(waveform)
    assert logits.shape == (2, 3, SAMPLES)
    assert torch.isfinite(logits).all()
    probabilities = logits.softmax(dim=1)
    assert torch.allclose(probabilities.sum(dim=1), torch.ones((2, SAMPLES)), atol=1e-6)
    target = gaussian_targets(torch.tensor([700, -1]), torch.tensor([1894, -1]))
    loss = weighted_soft_cross_entropy(logits, target)
    assert torch.isfinite(loss) and loss > 0
    loss.backward()
    assert model.output.weight.grad is not None
    assert torch.isfinite(model.output.weight.grad).all()
    assert model.output.weight.grad.abs().sum() > 0
    with pytest.raises(ValueError, match="6000"):
        model(torch.zeros((1, 3, 3000)))


def test_arrival_targets_and_noise_are_declared():
    target = gaussian_targets(torch.tensor([700, -1]), torch.tensor([1894, -1]))
    assert target.shape == (2, 3, SAMPLES)
    assert int(target[0, 1].argmax()) == 700
    assert int(target[0, 2].argmax()) == 1894
    assert torch.all(target[1, 0] == 1)
    assert torch.all(target[1, 1:] == 0)
    assert torch.allclose(target.sum(dim=1), torch.ones((2, SAMPLES)), atol=1e-7)
    with pytest.raises(ValueError, match="paired"):
        gaussian_targets(torch.tensor([700]), torch.tensor([-1]))
    with pytest.raises(ValueError, match="ordered"):
        gaussian_targets(torch.tensor([1000]), torch.tensor([700]))


def test_peak_thresholds_are_label_free_and_noise_can_fail():
    probability = np.zeros((3, SAMPLES), dtype=np.float32)
    probability[0] = 1
    probability[:, 700] = [0.05, 0.90, 0.05]
    probability[:, 1894] = [0.02, 0.03, 0.95]
    assert pick_probabilities(probability, p_threshold=0.5, s_threshold=0.5) == {
        "P": 7.0, "S": 18.94,
    }
    assert pick_probabilities(probability, p_threshold=0.95, s_threshold=0.95) == {
        "P": None, "S": 18.94,
    }
    assert pick_probabilities(np.tile([[1], [0], [0]], (1, SAMPLES)),
                              p_threshold=0.5, s_threshold=0.5) == {"P": None, "S": None}
    bad = probability.copy()
    bad[:, 0] = [0.8, 0.8, 0.2]
    with pytest.raises(ValueError, match="sum to one"):
        pick_probabilities(bad, p_threshold=0.5, s_threshold=0.5)
