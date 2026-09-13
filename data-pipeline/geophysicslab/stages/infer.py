from __future__ import annotations

from ..model.physics import derived_diagnostics, subsurface_model


def run(case, seed: int) -> dict:
    model = subsurface_model(case)
    return derived_diagnostics(model, case, seed)
