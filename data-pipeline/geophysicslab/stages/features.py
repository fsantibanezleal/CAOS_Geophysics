from __future__ import annotations

import numpy as np


def run(model: dict) -> dict:
    density = np.asarray(model["density_gcc"], dtype=float)
    susceptibility = np.asarray(model["susceptibility_si"], dtype=float)
    return {"density_mean": float(density.mean()), "density_std": float(density.std()), "susceptibility_mean": float(susceptibility.mean()), "contrast_ratio": float(density.std() / (susceptibility.std() + 1e-12))}
