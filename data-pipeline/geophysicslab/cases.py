"""Canonical, configurable case registry grouped by category."""
from __future__ import annotations

from .io.schema import Case

BASE = [
    ("GRAVITY_INTRUSION", "potential fields", "Gravity prism inversion", 1.35, 420.0, 2.2, 0.025, 0.0, "Dense body with a shallow gravity signature."),
    ("GRAVITY_DEEP_BODY", "potential fields", "Depth-weighted gravity", 1.10, 1080.0, 1.9, 0.035, 18.0, "Deeper target with non-unique amplitude recovery."),
    ("GRAVITY_NOISY", "potential fields", "Robust gravity residual", 1.65, 680.0, 2.8, 0.090, 42.0, "Noisy acquisition for regularization stress testing."),
    ("GRAVITY_TILTED", "potential fields", "Rotated gravity survey", 0.90, 760.0, 1.5, 0.020, 66.0, "Oblique survey geometry tests coordinate conventions."),
    ("MAGNETIC_DYKE", "potential fields", "Induced magnetics", 1.30, 360.0, 2.8, 0.025, 25.0, "Narrow susceptibility contrast under an inducing field."),
    ("MAGNETIC_REMANENCE", "potential fields", "Field-direction sensitivity", 1.55, 720.0, 3.4, 0.060, 54.0, "Direction mismatch exposes scalar inversion limits."),
    ("MAGNETIC_DEEP", "potential fields", "Sparse magnetic body", 0.78, 1180.0, 1.2, 0.040, 72.0, "Deep compact body with weak surface response."),
    ("MAGNETIC_NOISY", "potential fields", "Magnetic IRLS stress", 1.80, 590.0, 4.2, 0.120, 38.0, "Outlier-prone anomaly for robust misfit comparison."),
    ("MT_RESISTIVE", "electromagnetics", "Layered resistive cap", 1.00, 380.0, 0.45, 0.015, 0.0, "High-resistivity layer over a conductive basement."),
    ("MT_CONDUCTIVE", "electromagnetics", "Layered conductive lens", 1.25, 620.0, 4.8, 0.025, 0.0, "Conductive target with frequency-dependent skin depth."),
    ("MT_MIXED", "electromagnetics", "Physics-guided MT", 1.45, 880.0, 1.8, 0.040, 0.0, "Mixed layers for differentiable impedance inversion."),
    ("MT_NOISY", "electromagnetics", "MT uncertainty bands", 0.92, 1040.0, 2.6, 0.110, 0.0, "Large error bars test uncertainty communication."),
    ("FWI_LAYERED", "seismic", "Acoustic layered FWI", 0.90, 520.0, 1.7, 0.020, 0.0, "Low-contrast model for frequency continuation."),
    ("FWI_FAULT", "seismic", "Acoustic fault FWI", 1.40, 760.0, 2.0, 0.035, 0.0, "Laterally varying target and shot residual."),
    ("FWI_CYCLE_SKIP", "seismic", "Cycle-skipping diagnostic", 1.65, 980.0, 2.5, 0.065, 0.0, "Sparse low-frequency content makes phase errors visible."),
    ("FWI_NOISY", "seismic", "Robust FWI residual", 1.05, 660.0, 1.2, 0.120, 0.0, "Noise and taper sensitivity experiment."),
    ("JOINT_SHARED", "joint inversion", "Cross-gradient agreement", 1.30, 640.0, 2.3, 0.035, 40.0, "Gravity and magnetics share a structural boundary."),
    ("JOINT_CONFLICT", "joint inversion", "Cross-gradient conflict", 1.70, 860.0, 3.2, 0.070, 60.0, "Different physics illuminate different parts of the model."),
    ("LEARNED_CNN", "learned methods", "CNN field prior", 1.15, 540.0, 2.0, 0.050, 30.0, "Convolutional prior evaluated against a held-out synthetic case."),
    ("LEARNED_AUTOENCODER", "learned methods", "Autoencoder novelty", 0.95, 910.0, 1.6, 0.045, 15.0, "Latent reconstruction error highlights out-of-distribution structure."),
]

CASES = [Case(case_id, category, method, anomaly, depth, conductivity, noise, 18.0, angle_deg, description)
         for case_id, category, method, anomaly, depth, conductivity, noise, angle_deg, description in BASE]
BY_ID = {case.id: case for case in CASES}


def list_cases() -> list[Case]:
    return list(CASES)


def get_case(case_id: str) -> Case:
    return BY_ID[case_id]


def list_categories() -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for case in CASES:
        grouped.setdefault(case.category, []).append(case.id)
    return grouped
