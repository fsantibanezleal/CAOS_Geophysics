"""Compact, documented geophysical forward models for reproducible cases.

The functions are intentionally small enough to validate numerically and to mirror in the browser.
They are not presented as replacements for full-scale field inversion. The release pipeline records the
assumptions and keeps solver-backed extensions in the offline lane.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..core.rng import make_rng


def grid(nx: int = 32, nz: int = 24) -> tuple[np.ndarray, np.ndarray]:
    return np.linspace(-1600.0, 1600.0, nx), np.linspace(0.0, 1800.0, nz)


def subsurface_model(case: Any, nx: int = 32, nz: int = 24) -> dict[str, Any]:
    x, z = grid(nx, nz)
    X, Z = np.meshgrid(x, z)
    body = np.exp(-((X - 0.32 * case.depth) ** 2 / (2 * 430.0**2) + (Z - case.depth) ** 2 / (2 * 260.0**2)))
    body += 0.55 * np.exp(-((X + 0.45 * case.depth) ** 2 / (2 * 260.0**2) + (Z - 1.18 * case.depth) ** 2 / (2 * 180.0**2)))
    density = case.anomaly * body
    susceptibility = 0.010 * case.anomaly * body * (1 + 0.15 * np.sin(X / 280.0))
    velocity = 1800.0 + 1700.0 * (Z / max(z[-1], 1.0)) + 850.0 * body
    return {"x_m": x.tolist(), "z_m": z.tolist(), "density_gcc": density.tolist(), "susceptibility_si": susceptibility.tolist(), "velocity_m_s": velocity.tolist()}


def gravity_forward(model: dict[str, Any], angle_deg: float = 0.0) -> dict[str, list[float]]:
    x = np.asarray(model["x_m"], dtype=float)
    z = np.asarray(model["z_m"], dtype=float)
    density = np.asarray(model["density_gcc"], dtype=float)
    obs_x = np.linspace(x.min(), x.max(), 48)
    X, Z = np.meshgrid(x, z)
    theta = math.radians(angle_deg)
    dx = obs_x[:, None, None] - X[None, :, :]
    dz = 1.0 + Z[None, :, :]
    along = dx * math.cos(theta) + dz * math.sin(theta)
    kernel = 6.67430e-3 * dz / np.power(dx * dx + dz * dz, 1.5)
    obs = np.sum(kernel * density[None, :, :] * (1.0 + 0.12 * along / 1800.0), axis=(1, 2)) * 22.0
    return {"x_m": obs_x.tolist(), "gravity_mgal": obs.tolist()}


def magnetic_forward(model: dict[str, Any], angle_deg: float = 35.0) -> dict[str, list[float]]:
    x = np.asarray(model["x_m"], dtype=float)
    z = np.asarray(model["z_m"], dtype=float)
    susceptibility = np.asarray(model["susceptibility_si"], dtype=float)
    obs_x = np.linspace(x.min(), x.max(), 48)
    X, Z = np.meshgrid(x, z)
    dx = obs_x[:, None, None] - X[None, :, :]
    dz = 1.0 + Z[None, :, :]
    total = dx * dx + dz * dz
    inclination = math.radians(angle_deg)
    kernel = (dx * math.cos(inclination) + dz * math.sin(inclination)) / np.power(total, 1.5)
    obs = np.sum(kernel * susceptibility[None, :, :], axis=(1, 2)) * 1.2e5
    return {"x_m": obs_x.tolist(), "magnetic_nT": obs.tolist()}


def layered_mt(case: Any, nfreq: int = 24) -> dict[str, list[float]]:
    frequencies = np.geomspace(0.01, 100.0, nfreq)
    rho = np.array([40.0 + case.conductivity * 15.0, 180.0, 12.0 + case.anomaly * 3.0, 600.0, 1200.0])
    thickness = np.array([case.depth * 0.25, case.depth * 0.18, case.depth * 0.22, case.depth * 0.35])
    mu = 4.0e-7 * math.pi
    apparent: list[float] = []
    phase: list[float] = []
    for frequency in frequencies:
        omega = 2 * math.pi * frequency
        zed = np.sqrt(1j * omega * mu * rho[-1])
        for index in range(len(thickness) - 1, -1, -1):
            k = np.sqrt(1j * omega * mu / rho[index])
            intrinsic = 1j * omega * mu / k
            reflection = (intrinsic - zed) / (intrinsic + zed)
            zed = intrinsic * (1 - reflection * np.exp(-2 * k * thickness[index])) / (1 + reflection * np.exp(-2 * k * thickness[index]))
        apparent.append(float(abs(zed) ** 2 / (mu * omega)))
        phase.append(float(np.degrees(np.angle(zed))))
    return {"frequency_hz": frequencies.tolist(), "apparent_resistivity_ohm_m": apparent, "phase_deg": phase,
            "layer_resistivity_ohm_m": rho.tolist(), "layer_thickness_m": thickness.tolist()}


def acoustic_fwi(case: Any, seed: int, nx: int = 48, nz: int = 38, nt: int = 96) -> dict[str, list[float] | float]:
    """A finite-difference acoustic shot and one gradient-style update.

    The update is a deterministic correlation between the observed and predicted wavefields. Boundary
    tapering prevents wraparound. This is a compact research instrument, not a claim of field-scale FWI.
    """
    rng = make_rng(seed)
    dz = 20.0
    dt = 0.001
    x = np.arange(nx) * dz
    z = np.arange(nz) * dz
    X, Z = np.meshgrid(x, z)
    anomaly = np.exp(-((X - 0.55 * x[-1]) ** 2 / (2 * 110.0**2) + (Z - case.depth * 0.55) ** 2 / (2 * 95.0**2)))
    velocity_true = 1700.0 + 9.0 * Z + 500.0 * anomaly
    velocity_start = 1700.0 + 9.0 * Z
    source_x, source_z = nx // 2, 3
    receiver_z = 3
    source = np.exp(-((np.arange(nt) * dt - 0.045) / 0.012) ** 2) * np.sin(2 * math.pi * 18.0 * (np.arange(nt) * dt - 0.045))

    def shot(vel: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        prev = np.zeros((nz, nx), dtype=float)
        current = np.zeros_like(prev)
        gather = np.zeros((nt, nx), dtype=float)
        taper = np.outer(np.hanning(nz), np.hanning(nx))
        for it in range(nt):
            lap = (np.roll(current, 1, 0) + np.roll(current, -1, 0) + np.roll(current, 1, 1) + np.roll(current, -1, 1) - 4 * current) / dz**2
            nxt = 2 * current - prev + (vel * dt) ** 2 * lap
            nxt[source_z, source_x] += source[it]
            nxt *= (0.96 + 0.04 * taper)
            gather[it] = nxt[receiver_z]
            prev, current = current, nxt
        return gather, current

    observed, _ = shot(velocity_true)
    predicted, wavefield = shot(velocity_start)
    observed += rng.normal(0.0, case.noise * max(float(np.std(observed)), 1e-10), observed.shape)
    residual = observed - predicted
    gradient = np.mean(residual, axis=0)[None, :] * wavefield
    update = np.clip(velocity_start + 120.0 * gradient / (np.max(np.abs(gradient)) + 1e-12), 1500.0, 3100.0)
    time = (np.arange(nt) * dt).tolist()
    return {"time_s": time, "receiver_x_m": x.tolist(), "observed": observed[:, ::4].mean(axis=1).tolist(),
            "predicted": predicted[:, ::4].mean(axis=1).tolist(), "residual": residual[:, ::4].mean(axis=1).tolist(),
            "velocity_start_m_s": velocity_start[::2, ::2].tolist(), "velocity_update_m_s": update[::2, ::2].tolist(),
            "misfit": float(np.mean(residual**2))}


def derived_diagnostics(model: dict[str, Any], case: Any, seed: int) -> dict[str, Any]:
    gravity = gravity_forward(model, case.angle_deg)
    magnetic = magnetic_forward(model, case.angle_deg)
    mt = layered_mt(case)
    fwi = acoustic_fwi(case, seed)
    density = np.asarray(model["density_gcc"], dtype=float)
    susceptibility = np.asarray(model["susceptibility_si"], dtype=float)
    grad_dz, grad_dx = np.gradient(density)
    grad_s_dz, grad_s_dx = np.gradient(susceptibility)
    cross = np.abs(grad_dx * grad_s_dz - grad_dz * grad_s_dx)
    return {"model": model, "gravity": gravity, "magnetics": magnetic, "mt": mt, "fwi": fwi,
            "diagnostics": {"cross_gradient": cross.tolist(), "density_range": [float(density.min()), float(density.max())],
                             "susceptibility_range": [float(susceptibility.min()), float(susceptibility.max())]}}
