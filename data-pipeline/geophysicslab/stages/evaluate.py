from __future__ import annotations

import numpy as np


def run(result: dict, case) -> dict:
    gravity = np.asarray(result["gravity"]["gravity_mgal"], dtype=float)
    magnetic = np.asarray(result["magnetics"]["magnetic_nT"], dtype=float)
    residual = float(np.sqrt(np.mean((gravity - np.mean(gravity)) ** 2)))
    return {"gravity_rms_mgal": round(residual, 6), "magnetic_peak_nT": round(float(np.max(np.abs(magnetic))), 6), "fwi_misfit": round(float(result["fwi"]["misfit"]), 8), "cross_gradient_mean": round(float(np.mean(result["diagnostics"]["cross_gradient"])), 8), "held_out": True, "case_noise": case.noise}
