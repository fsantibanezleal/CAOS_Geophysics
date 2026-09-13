from __future__ import annotations

import numpy as np


def run(values: list[float], noise: float) -> dict:
    array = np.asarray(values, dtype=float)
    scale = float(np.std(array)) or 1.0
    return {"values": ((array - float(np.mean(array))) / scale).tolist(), "mean": float(np.mean(array)), "scale": scale, "noise": noise}
