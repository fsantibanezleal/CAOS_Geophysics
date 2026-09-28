"""Local M12 first-arrival velocity experiment, separate from waveform FWI and gravity learning.

The data oracle integrates bilinear slowness; inversion uses independent cell-length rays.
Truth is supplied only to supervised training and held-out scoring, never to inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import time
from pathlib import Path

import numpy as np
from scipy.linalg import cho_factor, cho_solve

GRID = 16
DX = 50.0
EXTENT = GRID * DX
NOISE_S = 0.001
LAYOUTS = {
    "A": ((0.08, 0.92), (0.10, 0.90), (0.08, 0.92), (0.10, 0.90)),
    "B": ((0.06, 0.94), (0.13, 0.87), (0.12, 0.88), (0.04, 0.96)),
    "C": ((0.11, 0.89), (0.07, 0.93), (0.05, 0.95), (0.14, 0.86)),
}
TRAIN_FAMILIES = ("layered", "lens", "dipping")
TEST_FAMILIES = ("fault", "salt")
COHORTS = {
    "train": (800, 17001, TRAIN_FAMILIES, ("A", "B")),
    "validation": (160, 27001, TRAIN_FAMILIES, ("A", "B")),
    "id_test": (160, 37001, TRAIN_FAMILIES, ("A", "B")),
    "family_only": (80, 47001, TEST_FAMILIES, ("A", "B")),
    "acquisition_only": (80, 57001, TRAIN_FAMILIES, ("C",)),
    "joint_ood": (160, 67001, TEST_FAMILIES, ("C",)),
}
CLASSICAL_LAMBDAS = (1.0, 10.0, 100.0, 1000.0)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value: object) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def background() -> np.ndarray:
    z = (np.arange(GRID, dtype=np.float64) + 0.5) * DX
    return np.broadcast_to(2000.0 + 0.35 * z[:, None], (GRID, GRID)).copy()


def acquisition(layout: str) -> np.ndarray:
    if layout not in LAYOUTS:
        raise ValueError(f"Unknown acquisition layout: {layout}")
    lr_source, lr_receiver, tb_source, tb_receiver = LAYOUTS[layout]
    left = np.linspace(*lr_source, 8) * EXTENT
    right = np.linspace(*lr_receiver, 8) * EXTENT
    top = np.linspace(*tb_source, 8) * EXTENT
    bottom = np.linspace(*tb_receiver, 8) * EXTENT
    rays = [(0.0, zs, EXTENT, zr) for zs in left for zr in right]
    rays += [(xs, 0.0, xr, EXTENT) for xs in top for xr in bottom]
    return np.asarray(rays, dtype=np.float64)


def cell_length_matrix(rays: np.ndarray) -> np.ndarray:
    """Siddon-style cell crossing, with z-major cell ordering."""
    result = np.zeros((len(rays), GRID * GRID), dtype=np.float64)
    edges = np.arange(1, GRID, dtype=np.float64) * DX
    for row, (x0, z0, x1, z1) in enumerate(rays):
        delta_x, delta_z = x1 - x0, z1 - z0
        crossings = [0.0, 1.0]
        if delta_x:
            crossings.extend(((edges - x0) / delta_x).tolist())
        if delta_z:
            crossings.extend(((edges - z0) / delta_z).tolist())
        ts = np.unique(np.asarray(crossings))
        ts = ts[(ts >= 0.0) & (ts <= 1.0)]
        middles = (ts[:-1] + ts[1:]) / 2.0
        x_cells = np.clip(np.floor((x0 + middles * delta_x) / DX).astype(int), 0, GRID - 1)
        z_cells = np.clip(np.floor((z0 + middles * delta_z) / DX).astype(int), 0, GRID - 1)
        lengths = np.diff(ts) * math.hypot(delta_x, delta_z)
        np.add.at(result[row], z_cells * GRID + x_cells, lengths)
    return result


def quadrature_matrix(rays: np.ndarray, samples_per_cell: int = 8) -> np.ndarray:
    """Independent midpoint integration of bilinear cell-centre slowness."""
    if samples_per_cell < 8:
        raise ValueError("Oracle requires at least eight samples per cell width")
    result = np.zeros((len(rays), GRID * GRID), dtype=np.float64)
    for row, (x0, z0, x1, z1) in enumerate(rays):
        distance = math.hypot(x1 - x0, z1 - z0)
        n = math.ceil(distance / DX * samples_per_cell)
        fractions = (np.arange(n, dtype=np.float64) + 0.5) / n
        gx = np.clip((x0 + fractions * (x1 - x0)) / DX - 0.5, 0, GRID - 1)
        gz = np.clip((z0 + fractions * (z1 - z0)) / DX - 0.5, 0, GRID - 1)
        ix, iz = np.floor(gx).astype(int), np.floor(gz).astype(int)
        jx, jz = np.minimum(ix + 1, GRID - 1), np.minimum(iz + 1, GRID - 1)
        ax, az = gx - ix, gz - iz
        step = distance / n
        for cell, weight in (
            (iz * GRID + ix, (1 - ax) * (1 - az)),
            (iz * GRID + jx, ax * (1 - az)),
            (jz * GRID + ix, (1 - ax) * az),
            (jz * GRID + jx, ax * az),
        ):
            np.add.at(result[row], cell, step * weight)
    return result


def operators() -> dict[str, dict[str, np.ndarray]]:
    return {name: {"rays": rays, "cell": cell_length_matrix(rays), "oracle": quadrature_matrix(rays)}
            for name in LAYOUTS for rays in (acquisition(name),)}


def velocity_family(family: str, rng: np.random.Generator) -> np.ndarray:
    x, z = np.meshgrid((np.arange(GRID) + 0.5) * DX, (np.arange(GRID) + 0.5) * DX)
    base = background()
    if family == "layered":
        interface = rng.uniform(230, 580) + rng.uniform(-55, 55) * np.sin(2 * np.pi * x / EXTENT)
        perturbation = rng.choice((-1.0, 1.0)) * rng.uniform(140, 360) * np.tanh((z - interface) / 85)
    elif family == "lens":
        cx, cz = rng.uniform(230, 570, 2)
        sx, sz = rng.uniform(100, 230), rng.uniform(90, 190)
        perturbation = rng.choice((-1.0, 1.0)) * rng.uniform(200, 450) * np.exp(
            -0.5 * (((x - cx) / sx) ** 2 + ((z - cz) / sz) ** 2))
    elif family == "dipping":
        interface = rng.uniform(250, 540) + rng.uniform(-0.4, 0.4) * (x - EXTENT / 2)
        perturbation = rng.choice((-1.0, 1.0)) * rng.uniform(160, 360) * np.tanh((z - interface) / 65)
    elif family == "fault":
        x_fault = rng.uniform(310, 490)
        interface = rng.uniform(280, 500) + np.where(x < x_fault, -rng.uniform(90, 160), rng.uniform(90, 160))
        perturbation = rng.choice((-1.0, 1.0)) * rng.uniform(250, 450) * np.tanh((z - interface) / 28)
    elif family == "salt":
        cx, cz = rng.uniform(260, 540), rng.uniform(260, 540)
        rx, rz = rng.uniform(100, 190), rng.uniform(140, 240)
        body = ((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2 < 1
        perturbation = rng.uniform(800, 1200) * body.astype(float) - rng.uniform(60, 140)
    else:
        raise ValueError(f"Unknown velocity family: {family}")
    return np.clip(base + perturbation, 1400.0, 4000.0).astype(np.float32)


def input_features(observed: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    reference = background().ravel()
    coverage = matrix.sum(axis=0)
    residual = observed - matrix @ (1.0 / reference)
    backprojected = matrix.T @ residual / np.maximum(coverage, 1.0)
    velocity_scale = -backprojected * reference ** 2 / 400.0
    return np.stack((velocity_scale.reshape(GRID, GRID),
                     (coverage / max(float(coverage.max()), 1.0)).reshape(GRID, GRID))).astype(np.float32)


def make_cohort(name: str, ops: dict, *, fixture: bool = False) -> dict:
    count, seed_base, families, layouts = COHORTS[name]
    if fixture:
        count = min(count, 12)
    records, features, velocities, observations, acquisitions = [], [], [], [], []
    for index in range(count):
        seed = seed_base + index
        family = families[index % len(families)]
        layout = layouts[(index // len(families)) % len(layouts)]
        rng = np.random.default_rng(seed)
        velocity = velocity_family(family, rng)
        true_times = ops[layout]["oracle"] @ (1.0 / velocity.ravel())
        noisy = true_times + rng.normal(0.0, NOISE_S, size=len(true_times))
        identifier = f"m12:{name}:{seed}:{family}:{layout}"
        records.append({"id": identifier, "seed": seed, "family": family, "acquisition": layout,
                        "velocity_sha256": sha256_bytes(velocity.astype("<f4").tobytes()),
                        "noisy_picks_sha256": sha256_bytes(noisy.astype("<f8").tobytes())})
        features.append(input_features(noisy, ops[layout]["cell"]))
        velocities.append(velocity)
        observations.append(noisy)
        acquisitions.append(layout)
    return {"records": records, "features": np.stack(features), "velocity": np.stack(velocities),
            "observed": np.stack(observations), "acquisition": np.asarray(acquisitions),
            "manifest_sha256": canonical_hash(records)}


def _difference_gram() -> np.ndarray:
    gram = np.zeros((GRID * GRID, GRID * GRID), dtype=np.float64)
    for z in range(GRID):
        for x in range(GRID):
            i = z * GRID + x
            for j in ((i + 1,) if x < GRID - 1 else ()) + ((i + GRID,) if z < GRID - 1 else ()):
                gram[i, i] += 1
                gram[j, j] += 1
                gram[i, j] -= 1
                gram[j, i] -= 1
    return gram


def classical_predict(cohort: dict, ops: dict, lam: float, gram: np.ndarray | None = None) -> np.ndarray:
    gram = _difference_gram() if gram is None else gram
    output = np.empty_like(cohort["velocity"], dtype=np.float64)
    s0 = 1.0 / background().ravel()
    for layout in np.unique(cohort["acquisition"]):
        indices = np.flatnonzero(cohort["acquisition"] == layout)
        matrix = ops[layout]["cell"]
        b = matrix / 10.0
        y = (cohort["observed"][indices] - matrix @ s0) / 0.01
        normal = b.T @ b + lam * gram + 0.01 * np.eye(GRID * GRID)
        factor = cho_factor(normal, check_finite=True)
        q = cho_solve(factor, b.T @ y.T).T
        s = np.clip(s0[None, :] + q / 1000.0, 1.0 / 4000.0, 1.0 / 1400.0)
        output[indices] = (1.0 / s).reshape(-1, GRID, GRID)
    return output


def select_classical(validation: dict, ops: dict) -> tuple[float, dict]:
    gram = _difference_gram()
    scores = {}
    for lam in CLASSICAL_LAMBDAS:
        prediction = classical_predict(validation, ops, lam, gram)
        scores[str(lam)] = float(np.sqrt(np.mean((prediction - validation["velocity"]) ** 2)))
    selected = min(CLASSICAL_LAMBDAS, key=lambda lam: (scores[str(lam)], lam))
    return selected, scores


def _network():
    import torch
    from torch import nn

    class Residual(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(nn.Conv2d(24, 24, 3, padding=1), nn.GELU(),
                                     nn.Conv2d(24, 24, 3, padding=1))

        def forward(self, values):
            return torch.nn.functional.gelu(values + self.net(values))

    class VelocityNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(nn.Conv2d(2, 24, 3, padding=1), nn.GELU(),
                                     Residual(), Residual(), Residual(), nn.Conv2d(24, 1, 1))
            self.register_buffer("reference", torch.as_tensor(background(), dtype=torch.float32)[None])

        def forward(self, features):
            return self.reference + 600.0 * torch.tanh(self.net(features)[:, 0])

    return VelocityNet()


def _predict(model, cohort: dict, device: str) -> np.ndarray:
    import torch
    model.eval()
    result = []
    with torch.no_grad():
        for batch in np.array_split(cohort["features"], math.ceil(len(cohort["features"]) / 64)):
            result.append(model(torch.from_numpy(batch).to(device)).cpu().numpy())
    return np.concatenate(result).astype(np.float64)


def train_model(train: dict, validation: dict, ops: dict, *, epochs: int, device: str) -> tuple[object, list, int]:
    import torch
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available")
    if device not in ("cuda", "cpu"):
        raise ValueError("Device must be cpu or cuda")
    torch.manual_seed(77212)
    if device == "cpu":
        torch.set_num_threads(min(4, torch.get_num_threads()))
    model = _network().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    x = torch.from_numpy(train["features"]).to(device)
    y = torch.from_numpy(train["velocity"]).to(device)
    picks = torch.from_numpy(train["observed"].astype(np.float32)).to(device)
    a = {name: torch.from_numpy(ops[name]["cell"].astype(np.float32)).to(device)
         for name in ("A", "B")}
    history, best_rmse, best_epoch, best_state = [], float("inf"), -1, None
    for epoch in range(epochs):
        model.train()
        train_losses = []
        for layout in ("A", "B"):
            ids = np.flatnonzero(train["acquisition"] == layout)
            shuffled = ids[torch.randperm(len(ids)).cpu().numpy()]
            for batch in np.array_split(shuffled, math.ceil(len(shuffled) / 64)):
                optimizer.zero_grad()
                predicted = model(x[batch])
                model_loss = ((predicted - y[batch]) / 400.0).square().mean()
                times = torch.matmul(predicted.flatten(1).reciprocal(), a[layout].T)
                data_loss = ((times - picks[batch]) / 0.01).square().mean()
                loss = model_loss + 0.1 * data_loss
                if not torch.isfinite(loss):
                    raise FloatingPointError("Nonfinite M12 training loss")
                loss.backward()
                optimizer.step()
                train_losses.append(float(loss.detach().cpu()))
        val_prediction = _predict(model, validation, device)
        val_rmse = float(np.sqrt(np.mean((val_prediction - validation["velocity"]) ** 2)))
        history.append({"epoch": epoch + 1, "train_objective": float(np.mean(train_losses)),
                        "validation_velocity_rmse_m_s": val_rmse})
        if val_rmse < best_rmse:
            best_rmse, best_epoch = val_rmse, epoch + 1
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        if epoch == 0 or (epoch + 1) % 5 == 0 or epoch + 1 == epochs:
            print(f"M12 epoch {epoch + 1}/{epochs}: validation RMSE {val_rmse:.3f} m/s", flush=True)
    model.load_state_dict(best_state)
    model.eval()
    return model, history, best_epoch


def save_checkpoint(model, path: Path) -> str:
    if path.exists():
        raise FileExistsError(f"Checkpoint exists: {path}")
    np.savez_compressed(path, **{key: value.detach().cpu().numpy() for key, value in model.state_dict().items()})
    return sha256_bytes(path.read_bytes())


def load_checkpoint(path: Path, expected_sha256: str, device: str = "cpu"):
    import torch
    if sha256_bytes(path.read_bytes()) != expected_sha256:
        raise ValueError("M12 checkpoint SHA-256 mismatch")
    model = _network()
    with np.load(path, allow_pickle=False) as arrays:
        expected = model.state_dict()
        if set(arrays.files) != set(expected):
            raise ValueError("M12 checkpoint state keys differ")
        state = {}
        for key, value in expected.items():
            array = arrays[key]
            if array.shape != tuple(value.shape) or array.dtype != np.float32 or not np.isfinite(array).all():
                raise ValueError(f"Invalid M12 checkpoint tensor: {key}")
            state[key] = torch.from_numpy(array.copy())
    model.load_state_dict(state)
    return model.to(device).eval()


def score(cohort: dict, learned: np.ndarray, classical: np.ndarray, ops: dict, threshold_ms: float) -> dict:
    truth = cohort["velocity"].astype(np.float64)
    model_learned = np.sqrt(np.mean((learned - truth) ** 2, axis=(1, 2)))
    model_classical = np.sqrt(np.mean((classical - truth) ** 2, axis=(1, 2)))
    data_learned = np.empty(len(truth), dtype=np.float64)
    data_classical = np.empty(len(truth), dtype=np.float64)
    for layout in np.unique(cohort["acquisition"]):
        ids = np.flatnonzero(cohort["acquisition"] == layout)
        q = ops[layout]["oracle"]
        observed = cohort["observed"][ids]
        data_learned[ids] = 1000.0 * np.sqrt(np.mean(
            ((1.0 / learned[ids].reshape(len(ids), -1)) @ q.T - observed) ** 2, axis=1))
        data_classical[ids] = 1000.0 * np.sqrt(np.mean(
            ((1.0 / classical[ids].reshape(len(ids), -1)) @ q.T - observed) ** 2, axis=1))
    per_family = {}
    per_acquisition = {}
    families = np.asarray([record["family"] for record in cohort["records"]])
    for labels, target in ((families, per_family), (cohort["acquisition"], per_acquisition)):
        for label in np.unique(labels):
            mask = labels == label
            target[label] = {"count": int(mask.sum()),
                             "learned_velocity_rmse_m_s": float(model_learned[mask].mean()),
                             "classical_velocity_rmse_m_s": float(model_classical[mask].mean()),
                             "learned_oracle_rmse_ms": float(data_learned[mask].mean()),
                             "classical_oracle_rmse_ms": float(data_classical[mask].mean()),
                             "forward_threshold_exceedances": int(np.sum(data_learned[mask] > threshold_ms))}
    return {"count": len(truth), "manifest_sha256": cohort["manifest_sha256"],
            "noisy_input_sha256": sha256_bytes(cohort["observed"].astype("<f8").tobytes()),
            "learned_velocity_rmse_m_s": float(model_learned.mean()),
            "classical_velocity_rmse_m_s": float(model_classical.mean()),
            "learned_oracle_rmse_ms": float(data_learned.mean()),
            "classical_oracle_rmse_ms": float(data_classical.mean()),
            "learned_to_classical_velocity_ratio": float(model_learned.mean() / model_classical.mean()),
            "learned_to_classical_oracle_ratio": float(data_learned.mean() / data_classical.mean()),
            "forward_threshold_exceedances": int(np.sum(data_learned > threshold_ms)),
            "per_family": per_family, "per_acquisition": per_acquisition,
            "per_record": [{"id": record["id"], "learned_velocity_rmse_m_s": float(model_learned[i]),
                            "classical_velocity_rmse_m_s": float(model_classical[i]),
                            "learned_oracle_rmse_ms": float(data_learned[i]),
                            "classical_oracle_rmse_ms": float(data_classical[i]),
                            "forward_threshold_exceeded": bool(data_learned[i] > threshold_ms)}
                           for i, record in enumerate(cohort["records"])]}


def scientific_verdict(joint: dict) -> str:
    if (joint["learned_to_classical_velocity_ratio"] < 1
            and joint["learned_to_classical_oracle_ratio"] < 1):
        return "supported-within-bounded-synthetic-protocol"
    return "failed-held-out-comparator"


def execute(output: Path, *, epochs: int = 40, device: str = "cpu", fixture: bool = False) -> dict:
    import scipy
    import torch
    if epochs < 1:
        raise ValueError("At least one epoch required")
    output.mkdir(parents=True, exist_ok=True)
    checkpoint_path, receipt_path = output / "m12-velocity.npz", output / "receipt.json"
    if checkpoint_path.exists() or receipt_path.exists():
        raise FileExistsError(f"M12 output already exists in {output}")
    start = time.perf_counter()
    ops = operators()
    data = {name: make_cohort(name, ops, fixture=fixture) for name in COHORTS}
    lam, candidate_scores = select_classical(data["validation"], ops)
    model, history, selected_epoch = train_model(data["train"], data["validation"], ops,
                                                   epochs=epochs, device=device)
    validation_prediction = _predict(model, data["validation"], device)
    validation_classical = classical_predict(data["validation"], ops, lam)
    validation_initial = score(data["validation"], validation_prediction, validation_classical, ops, float("inf"))
    threshold = float(np.quantile([r["learned_oracle_rmse_ms"] for r in validation_initial["per_record"]], 0.95))
    checkpoint_sha = save_checkpoint(model, checkpoint_path)
    reloaded = load_checkpoint(checkpoint_path, checkpoint_sha, device)
    if not np.allclose(_predict(model, data["validation"], device),
                       _predict(reloaded, data["validation"], device), atol=1e-5, rtol=0):
        raise AssertionError("Reloaded checkpoint changes M12 predictions")
    scored = {}
    for name in ("validation", "id_test", "family_only", "acquisition_only", "joint_ood"):
        cohort = data[name]
        prediction = _predict(reloaded, cohort, device)
        classic = classical_predict(cohort, ops, lam)
        scored[name] = score(cohort, prediction, classic, ops, threshold)
    verdict = scientific_verdict(scored["joint_ood"])
    receipt = {"schema": "caos-geophysics.m12-velocity/v1", "status": "fixture-only" if fixture else verdict,
               "scope": "straight-ray first-arrival synthetic tomography; no waveforms or field generalization",
               "device": device, "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
               "versions": {"python": platform.python_version(), "numpy": np.__version__,
                            "scipy": scipy.__version__, "torch": torch.__version__},
               "code_sha256": sha256_bytes(Path(__file__).read_bytes()),
               "checkpoint": checkpoint_path.name, "checkpoint_sha256": checkpoint_sha,
               "seed": 77212, "epochs": epochs, "selected_epoch": selected_epoch, "history": history,
               "counts": {name: len(cohort["records"]) for name, cohort in data.items()},
               "split_manifests": {name: cohort["records"] for name, cohort in data.items()},
               "split_hashes": {name: cohort["manifest_sha256"] for name, cohort in data.items()},
               "fixed_scales": {"velocity_m_s": 400.0, "data_s": 0.01, "noise_s": NOISE_S},
               "classical": {"selected_lambda": lam, "validation_candidate_rmse_m_s": candidate_scores,
                             "selection": "minimum validation velocity RMSE; no test tuning"},
               "forward_threshold_ms": threshold, "forward_threshold_policy": "95th percentile of validation learned oracle RMSE",
               "cohorts": scored, "wall_seconds": time.perf_counter() - start,
               "ood_detection": {"id_false_positive": scored["id_test"]["forward_threshold_exceedances"],
                                 "id_true_negative": scored["id_test"]["count"] - scored["id_test"]["forward_threshold_exceedances"],
                                 "joint_true_positive": scored["joint_ood"]["forward_threshold_exceedances"],
                                 "joint_false_negative": scored["joint_ood"]["count"] - scored["joint_ood"]["forward_threshold_exceedances"],
                                 "joint_sensitivity": scored["joint_ood"]["forward_threshold_exceedances"] / scored["joint_ood"]["count"],
                                 "id_specificity": 1 - scored["id_test"]["forward_threshold_exceedances"] / scored["id_test"]["count"],
                                 "interpretation": "synthetic protocol residual flag; not a field-calibrated OOD probability"},
               "limitations": ["straight rays do not refract", "bilinear synthetic oracle is not independent field data",
                               "16 by 16 cells cannot resolve sub-cell structure", "OOD flag is not a calibrated field detector"]}
    receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return receipt


def verify(output: Path) -> dict:
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    if receipt["schema"] != "caos-geophysics.m12-velocity/v1":
        raise ValueError("Unsupported M12 receipt schema")
    if receipt["code_sha256"] != sha256_bytes(Path(__file__).read_bytes()):
        raise ValueError("M12 code hash differs from training source")
    if receipt["status"] == "fixture-only":
        raise ValueError("Fixture-only result cannot verify acceptance evidence")
    model = load_checkpoint(output / receipt["checkpoint"], receipt["checkpoint_sha256"], "cpu")
    ops = operators()
    lam = receipt["classical"]["selected_lambda"]
    threshold = receipt["forward_threshold_ms"]
    validation = make_cohort("validation", ops)
    selected_lam, candidate_scores = select_classical(validation, ops)
    if selected_lam != lam:
        raise AssertionError("M12 classical lambda selection drift")
    for candidate, value in candidate_scores.items():
        if not np.isclose(value, receipt["classical"]["validation_candidate_rmse_m_s"][candidate], rtol=1e-9):
            raise AssertionError(f"M12 classical candidate drift: {candidate}")
    for name in COHORTS:
        cohort = validation if name == "validation" else make_cohort(name, ops)
        if cohort["manifest_sha256"] != receipt["split_hashes"][name]:
            raise AssertionError(f"M12 split hash drift: {name}")
        if name == "train":
            continue
        reproduced = score(cohort, _predict(model, cohort, "cpu"), classical_predict(cohort, ops, lam), ops, threshold)
        original = receipt["cohorts"][name]
        if reproduced["noisy_input_sha256"] != original["noisy_input_sha256"]:
            raise AssertionError(f"M12 noisy input drift: {name}")
        for metric in ("learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s",
                       "learned_oracle_rmse_ms", "classical_oracle_rmse_ms"):
            if not np.isclose(reproduced[metric], original[metric], rtol=1e-5, atol=1e-4):
                raise AssertionError(f"M12 metric drift: {name}/{metric}")
        if reproduced["forward_threshold_exceedances"] != original["forward_threshold_exceedances"]:
            raise AssertionError(f"M12 OOD count drift: {name}")
        if name == "validation":
            reproduced_threshold = float(np.quantile(
                [row["learned_oracle_rmse_ms"] for row in reproduced["per_record"]], 0.95))
            if not np.isclose(reproduced_threshold, threshold, rtol=1e-5, atol=1e-4):
                raise AssertionError("M12 validation threshold drift")
        for new_row, old_row in zip(reproduced["per_record"], original["per_record"], strict=True):
            if new_row["id"] != old_row["id"] or new_row["forward_threshold_exceeded"] != old_row["forward_threshold_exceeded"]:
                raise AssertionError(f"M12 per-record identity or flag drift: {name}")
            for metric in ("learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s",
                           "learned_oracle_rmse_ms", "classical_oracle_rmse_ms"):
                if not np.isclose(new_row[metric], old_row[metric], rtol=1e-5, atol=1e-4):
                    raise AssertionError(f"M12 per-record metric drift: {name}/{new_row['id']}/{metric}")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/experiments/m12-velocity"))
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--fixture", action="store_true", help="small mechanical run; no acceptance evidence")
    parser.add_argument("--verify", action="store_true", help="reload and recompute the full receipt")
    args = parser.parse_args()
    result = verify(args.output) if args.verify else execute(args.output, epochs=args.epochs,
                                                              device=args.device, fixture=args.fixture)
    print(json.dumps({"status": result["status"], "device": result["device"],
                      "checkpoint_sha256": result["checkpoint_sha256"],
                      "joint_ood": {key: value for key, value in result["cohorts"]["joint_ood"].items()
                                    if key in ("learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s",
                                               "learned_oracle_rmse_ms", "classical_oracle_rmse_ms",
                                               "forward_threshold_exceedances")}}, indent=2))


if __name__ == "__main__":
    main()
