"""Typed records exchanged by the geophysics stages."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    id: str
    category: str
    method: str
    anomaly: float
    depth: float
    conductivity: float
    noise: float
    frequency: float
    angle_deg: float
    description: str
    real_or_synthetic: str = "synthetic"


@dataclass(frozen=True)
class ObservationContract:
    station_id: str
    x_m: float
    y_m: float
    frequency_hz: float
    value: float
    unit: str


@dataclass(frozen=True)
class PipelineResult:
    case_id: str
    category: str
    method: str
    seed: int
    artifact: dict
    metrics: dict
    engines: dict
