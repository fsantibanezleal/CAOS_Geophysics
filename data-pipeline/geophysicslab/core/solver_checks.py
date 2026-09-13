"""Small solver-backed certificates for the research-selected engines."""
from __future__ import annotations

import numpy as np


def simpeg_gravity_certificate() -> dict:
    from discretize import TensorMesh
    from simpeg import maps
    from simpeg.potential_fields import gravity

    mesh = TensorMesh([np.ones(3) * 100, np.ones(3) * 100, np.ones(3) * 100], origin=[-150, -150, -300])
    receiver = gravity.receivers.Point(np.array([[0.0, 0.0, 1.0]]), components="gz")
    source = gravity.sources.SourceField(receiver_list=[receiver])
    survey = gravity.Survey(source)
    simulation = gravity.Simulation3DIntegral(mesh=mesh, survey=survey, rhoMap=maps.IdentityMap(nP=mesh.nC), engine="geoana")
    values = np.asarray(simulation.dpred(np.ones(mesh.nC)), dtype=float)
    return {"passed": bool(values.size == 1 and np.isfinite(values[0])), "value_mgal": float(values[0])}


def choclo_prism_certificate() -> dict:
    from choclo.prism import gravity_u

    value = gravity_u(0.0, 0.0, 500.0, -50.0, 50.0, -50.0, 50.0, 0.0, 100.0, 2670.0)
    return {"passed": bool(np.isfinite(value)), "value": float(value)}


def torch_gpu_certificate() -> dict:
    import torch

    if not torch.cuda.is_available():
        return {"passed": False, "available": False}
    device = torch.device("cuda")
    wave = torch.zeros((64, 64), device=device)
    previous = torch.zeros_like(wave)
    velocity = torch.full_like(wave, 1800.0)
    source = torch.zeros_like(wave)
    source[32, 32] = 1.0
    for _ in range(24):
        laplacian = (torch.roll(wave, 1, 0) + torch.roll(wave, -1, 0) + torch.roll(wave, 1, 1) + torch.roll(wave, -1, 1) - 4 * wave)
        current = 2 * wave - previous + (velocity * 0.0005) ** 2 * laplacian + source
        previous, wave = wave, current
    torch.cuda.synchronize()
    return {"passed": bool(torch.isfinite(wave).all().item()), "available": True, "device": torch.cuda.get_device_name(0), "checksum": float(wave.abs().sum().item())}


def deepwave_acoustic_certificate() -> dict:
    import deepwave
    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    velocity = torch.full((32, 32), 1800.0, device=device)
    source_amplitudes = torch.zeros((1, 1, 16), device=device)
    source_amplitudes[0, 0, 2] = 1.0
    source_locations = torch.tensor([[[16, 4]]], device=device)
    receiver_locations = torch.tensor([[[4, 4], [8, 4], [12, 4], [16, 4], [20, 4], [24, 4], [28, 4], [10, 4]]], device=device)
    outputs = deepwave.scalar(velocity, 10.0, 0.0005, source_amplitudes=source_amplitudes, source_locations=source_locations, receiver_locations=receiver_locations, pml_width=4, nt=16, python_backend="eager")
    receiver_data = outputs[-1]
    if device.type == "cuda":
        torch.cuda.synchronize()
    return {"passed": bool(torch.isfinite(receiver_data).all().item()), "device": str(device), "shape": list(receiver_data.shape)}


def devito_symbolic_certificate() -> dict:
    from devito import Eq, Grid, Operator, TimeFunction

    grid = Grid(shape=(8, 8))
    wave = TimeFunction(name="wave", grid=grid, time_order=2, space_order=2)
    operator = Operator(Eq(wave.forward, wave + 0.1 * (wave.dx2 + wave.dy2)))
    return {"passed": "wave" in str(operator), "mode": "symbolic stencil constructed; JIT execution is platform-dependent"}


def run_solver_certificates() -> dict:
    result: dict[str, dict] = {}
    for name, function in (("simpeg_gravity", simpeg_gravity_certificate), ("choclo_prism", choclo_prism_certificate)):
        try:
            result[name] = function()
        except Exception as exc:  # optional engines must fail explicitly, never silently substitute
            result[name] = {"passed": False, "error": type(exc).__name__}
    try:
        result["torch_gpu"] = torch_gpu_certificate()
    except ImportError:
        result["torch_gpu"] = {"passed": False, "available": False, "error": "torch not installed"}
    try:
        result["deepwave_acoustic"] = deepwave_acoustic_certificate()
    except ImportError:
        result["deepwave_acoustic"] = {"passed": False, "error": "deepwave not installed"}
    try:
        result["devito_symbolic"] = devito_symbolic_certificate()
    except ImportError:
        result["devito_symbolic"] = {"passed": False, "error": "devito not installed"}
    result["all_passed"] = {"passed": all(item.get("passed", False) for item in result.values())}
    return result
