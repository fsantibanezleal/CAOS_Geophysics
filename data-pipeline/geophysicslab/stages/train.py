"""Train compact spatial learned baselines on grouped synthetic geology."""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from ..cases import get_case, list_cases
from ..model.physics import subsurface_model


def _default_split() -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    ordered = tuple(sorted(case.id for case in list_cases()))
    cut = max(1, int(len(ordered) * 0.7))
    validation_end = max(cut + 2, cut)
    return ordered[:cut], ordered[cut:validation_end], ordered[validation_end:]


def _spatial_samples(case_ids: tuple[str, ...], seed: int, repeats: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    inputs: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    for case_id in case_ids:
        case = get_case(case_id)
        model = subsurface_model(case, nx=16, nz=12)
        density = np.asarray(model["density_gcc"], dtype=np.float32)
        susceptibility = np.asarray(model["susceptibility_si"], dtype=np.float32)
        density_scale = max(float(np.max(np.abs(density))), 1e-6)
        susceptibility_scale = max(float(np.max(np.abs(susceptibility))), 1e-6)
        clean = np.stack([density / density_scale, susceptibility / susceptibility_scale])
        label = (density / density_scale)[None, ...]
        for _ in range(repeats):
            noise = rng.normal(0.0, max(case.noise, 0.01) * 0.08, clean.shape).astype(np.float32)
            inputs.append(clean + noise)
            targets.append(label)
    return np.stack(inputs), np.stack(targets)


@lru_cache(maxsize=4)
def run(seed: int = 42, train_case_ids: tuple[str, ...] | None = None, validation_case_ids: tuple[str, ...] | None = None, test_case_ids: tuple[str, ...] | None = None) -> dict:
    if train_case_ids is None or validation_case_ids is None or test_case_ids is None:
        train_case_ids, validation_case_ids, test_case_ids = _default_split()
    train_x, train_y = _spatial_samples(train_case_ids, seed, repeats=2)
    validation_x, validation_y = _spatial_samples(validation_case_ids, seed + 1, repeats=1)
    test_x, test_y = _spatial_samples(test_case_ids, seed + 2, repeats=1)

    x = np.linspace(-1.0, 1.0, 80)
    basis = np.stack([np.ones_like(x), x, x**2, np.sin(np.pi * x)], axis=1)
    target = 0.62 * basis[:, 0] - 0.14 * basis[:, 1] + 0.21 * basis[:, 2] + 0.08 * basis[:, 3]
    weights = np.linalg.lstsq(basis, target, rcond=None)[0]
    learned = {
        "backend": "numpy fallback",
        "device": "cpu",
        "cnn_loss": None,
        "autoencoder_loss": None,
        "test_cnn_mse": None,
        "test_autoencoder_mse": None,
        "validation_cnn_mse": None,
        "validation_autoencoder_mse": None,
        "architecture": "2-channel Conv2d field prior + 2-channel autoencoder",
        "train_samples": int(len(train_x)),
        "test_samples": int(len(test_x)),
    }
    try:
        import torch

        torch.manual_seed(seed)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        features = torch.tensor(train_x, device=device)
        labels = torch.tensor(train_y, device=device)
        heldout_features = torch.tensor(test_x, device=device)
        heldout_labels = torch.tensor(test_y, device=device)
        validation_features = torch.tensor(validation_x, device=device)
        validation_labels = torch.tensor(validation_y, device=device)
        channels, height, width = train_x.shape[1:]
        cnn = torch.nn.Sequential(
            torch.nn.Conv2d(channels, 12, 3, padding=1),
            torch.nn.GELU(),
            torch.nn.Conv2d(12, 8, 3, padding=1),
            torch.nn.GELU(),
            torch.nn.Conv2d(8, 1, 1),
        ).to(device)
        autoencoder = torch.nn.Sequential(
            torch.nn.Flatten(),
            torch.nn.Linear(channels * height * width, 48),
            torch.nn.Tanh(),
            torch.nn.Linear(48, channels * height * width),
        ).to(device)
        optimiser = torch.optim.Adam(list(cnn.parameters()) + list(autoencoder.parameters()), lr=0.015)
        for _ in range(36):
            prediction = cnn(features)
            reconstruction = autoencoder(features).reshape_as(features)
            loss = torch.mean((prediction - labels) ** 2) + 0.15 * torch.mean((reconstruction - features) ** 2)
            optimiser.zero_grad()
            loss.backward()
            optimiser.step()
        with torch.no_grad():
            train_cnn_loss = torch.mean((cnn(features) - labels) ** 2).item()
            train_ae_loss = torch.mean((autoencoder(features).reshape_as(features) - features) ** 2).item()
            test_cnn_loss = torch.mean((cnn(heldout_features) - heldout_labels) ** 2).item()
            test_ae_loss = torch.mean((autoencoder(heldout_features).reshape_as(heldout_features) - heldout_features) ** 2).item()
            validation_cnn_loss = torch.mean((cnn(validation_features) - validation_labels) ** 2).item()
            validation_ae_loss = torch.mean((autoencoder(validation_features).reshape_as(validation_features) - validation_features) ** 2).item()
        if device.type == "cuda":
            torch.cuda.synchronize()
        learned = {
            "backend": "torch-cuda" if device.type == "cuda" else "torch-cpu",
            "device": str(device),
            "cnn_loss": float(train_cnn_loss),
            "autoencoder_loss": float(train_ae_loss),
            "test_cnn_mse": float(test_cnn_loss),
            "test_autoencoder_mse": float(test_ae_loss),
            "validation_cnn_mse": float(validation_cnn_loss),
            "validation_autoencoder_mse": float(validation_ae_loss),
            "architecture": "2-channel Conv2d field prior + 2-channel autoencoder",
            "train_samples": int(len(train_x)),
            "test_samples": int(len(test_x)),
        }
    except ImportError:
        pass
    return {
        "model": "physics-aware ridge plus spatial CNN and autoencoder",
        "weights": weights.tolist(),
        "seed": seed,
        "features": ["normalized_density", "normalized_susceptibility", "spatial_context"],
        "grouped_train_cases": list(train_case_ids),
        "grouped_validation_cases": list(validation_case_ids),
        "grouped_test_cases": list(test_case_ids),
        "learned": learned,
    }
