"""PhaseNet-family 1D encoder-decoder for real STEAD P/S/noise picking.

This is an original PyTorch implementation of the documented U-Net family,
not a claim of bitwise equivalence to the official TensorFlow PhaseNet.
No pretrained weights or training data are bundled with this module.
"""

from __future__ import annotations

import math

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


SAMPLES = 6000
CHANNELS = (16, 32, 64, 128, 192)
PHASES = ("N", "P", "S")
LABEL_SIGMA_SAMPLES = 15.0
SAMPLE_INTERVAL_S = 0.01


class ResidualBlock(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv1d(channels, channels, 7, padding=3)
        self.norm1 = nn.GroupNorm(8, channels)
        self.conv2 = nn.Conv1d(channels, channels, 7, padding=3)
        self.norm2 = nn.GroupNorm(8, channels)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        hidden = F.silu(self.norm1(self.conv1(values)))
        return F.silu(values + self.norm2(self.conv2(hidden)))


class DownBlock(nn.Module):
    def __init__(self, inputs: int, outputs: int):
        super().__init__()
        self.down = nn.Conv1d(inputs, outputs, 5, stride=2, padding=2)
        self.residual = ResidualBlock(outputs)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.residual(self.down(values))


class UpBlock(nn.Module):
    def __init__(self, inputs: int, skip: int, outputs: int):
        super().__init__()
        self.project = nn.Conv1d(inputs + skip, outputs, 1)
        self.residual = ResidualBlock(outputs)

    def forward(self, values: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        values = F.interpolate(values, size=skip.shape[-1], mode="linear", align_corners=False)
        return self.residual(self.project(torch.cat((values, skip), dim=1)))


class PhaseUNet(nn.Module):
    """Fixed 60 s, 100 Hz, three-component input; logits in N/P/S order."""

    def __init__(self):
        super().__init__()
        self.stem = nn.Sequential(nn.Conv1d(3, CHANNELS[0], 7, padding=3),
                                  ResidualBlock(CHANNELS[0]))
        self.down = nn.ModuleList(DownBlock(a, b) for a, b in zip(CHANNELS[:-1], CHANNELS[1:]))
        self.up = nn.ModuleList(
            UpBlock(CHANNELS[index], CHANNELS[index - 1], CHANNELS[index - 1])
            for index in range(len(CHANNELS) - 1, 0, -1)
        )
        self.output = nn.Conv1d(CHANNELS[0], len(PHASES), 1)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        if values.ndim != 3 or values.shape[1:] != (3, SAMPLES):
            raise ValueError("PhaseUNet requires [batch, E/N/Z, 6000] at 100 Hz")
        skips = [self.stem(values)]
        for layer in self.down:
            skips.append(layer(skips[-1]))
        current = skips[-1]
        for layer, skip in zip(self.up, reversed(skips[:-1])):
            current = layer(current, skip)
        return self.output(current)


def gaussian_targets(
    p_indices: torch.Tensor,
    s_indices: torch.Tensor,
    *,
    length: int = SAMPLES,
    sigma_samples: float = LABEL_SIGMA_SAMPLES,
) -> torch.Tensor:
    """Soft analyst-arrival targets; -1 denotes no annotated quake phase."""
    if (p_indices.ndim != 1 or s_indices.shape != p_indices.shape or length < 32
            or sigma_samples <= 0 or not math.isfinite(sigma_samples)):
        raise ValueError("invalid phase-target shape or width")
    if torch.any((p_indices >= length) | (s_indices >= length) | (p_indices < -1) | (s_indices < -1)):
        raise ValueError("pick index is out of the window")
    if torch.any((p_indices < 0) != (s_indices < 0)) or torch.any((p_indices >= 0) & (p_indices >= s_indices)):
        raise ValueError("P/S labels must be paired and ordered")
    time = torch.arange(length, device=p_indices.device)[None, :]
    p = torch.exp(-0.5 * ((time - p_indices[:, None]) / sigma_samples) ** 2)
    s = torch.exp(-0.5 * ((time - s_indices[:, None]) / sigma_samples) ** 2)
    p = p * (p_indices[:, None] >= 0)
    s = s * (s_indices[:, None] >= 0)
    noise = torch.clamp(1 - p - s, min=0)
    target = torch.stack((noise, p, s), dim=1)
    return target / target.sum(dim=1, keepdim=True).clamp_min(1e-12)


def weighted_soft_cross_entropy(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Counter class sparsity without claiming calibrated output probabilities."""
    if logits.shape != target.shape or logits.ndim != 3 or logits.shape[1] != 3:
        raise ValueError("logits and targets require matching [batch,N/P/S,time]")
    weights = logits.new_tensor((1.0, 12.0, 12.0))[None, :, None]
    mass = (target * weights).sum()
    return -((target * weights) * F.log_softmax(logits, dim=1)).sum() / mass.clamp_min(1)


def pick_probabilities(
    probabilities: np.ndarray,
    *,
    p_threshold: float,
    s_threshold: float,
    minimum_ps_s: float = 0.4,
) -> dict[str, float | None]:
    """Dev-selected thresholds; no analyst label is consulted at inference."""
    if (probabilities.shape != (3, SAMPLES) or not np.all(np.isfinite(probabilities))
            or np.any(probabilities < 0) or np.any(probabilities > 1)
            or not 0 < p_threshold <= 1 or not 0 < s_threshold <= 1
            or not math.isfinite(minimum_ps_s) or minimum_ps_s < 0):
        raise ValueError("invalid phase probability input or threshold")
    if not np.allclose(probabilities.sum(axis=0), 1, atol=1e-3):
        raise ValueError("N/P/S probabilities do not sum to one")
    p_index = int(np.argmax(probabilities[1])) if probabilities[1].max() >= p_threshold else None
    s_index = int(np.argmax(probabilities[2])) if probabilities[2].max() >= s_threshold else None
    if p_index is not None and s_index is not None and s_index - p_index < round(minimum_ps_s / SAMPLE_INTERVAL_S):
        s_index = None
    return {"P": p_index * SAMPLE_INTERVAL_S if p_index is not None else None,
            "S": s_index * SAMPLE_INTERVAL_S if s_index is not None else None}
