"""Bounded learned residual refinement of a regularized straight-ray inverse.

This is an experimental M12 protocol. The deterministic inverse is evaluated
on the exact same picks and geometry; labels are used only for training and
development selection. No field-data validity is implied.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import time
from pathlib import Path

import numpy as np

import velocity_validation as physics
import velocity_physics_refinement as corrected


PROTOCOL = "m12-learned-residual/v3.1"
SEED = 77214
COUNTS = {"train": 1200, "validation": 160, "id_test": 160,
          "family_only": 80, "acquisition_only": 80, "joint_ood": 160}
SEED_BASES = {"train": 217001, "validation": 227001, "id_test": 237001,
              "family_only": 247001, "acquisition_only": 257001, "joint_ood": 267001}
EPOCHS = 100
PATIENCE = 20
LEARNING_RATE = 5e-4
DATA_WEIGHT = 0.025
RESIDUAL_WEIGHT = 0.025
RESIDUAL_SCALE_M_S = 250.0


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def make_cohort(name: str, ops: dict) -> dict:
    if name not in COUNTS:
        raise ValueError("Unknown M12 residual cohort")
    count = COUNTS[name]
    families = physics.TRAIN_FAMILIES if name in ("train", "validation", "id_test", "acquisition_only") else physics.TEST_FAMILIES
    layouts = ("C",) if name == "acquisition_only" else (("C",) if name == "joint_ood" else ("A", "B"))
    records, features, velocities, observations, acquisitions = [], [], [], [], []
    for index in range(count):
        seed = SEED_BASES[name] + index
        family = families[index % len(families)]
        layout = layouts[(index // len(families)) % len(layouts)]
        rng = np.random.default_rng(seed)
        velocity = physics.velocity_family(family, rng)
        observed = ops[layout]["oracle"] @ (1.0 / velocity.ravel())
        observed = observed + rng.normal(0.0, physics.NOISE_S, len(observed))
        records.append({"id": f"m12-residual-v3:{name}:{seed}:{family}:{layout}",
                        "seed": seed, "family": family, "acquisition": layout,
                        "velocity_sha256": physics.sha256_bytes(velocity.astype("<f4").tobytes()),
                        "noisy_picks_sha256": physics.sha256_bytes(observed.astype("<f8").tobytes())})
        features.append(corrected.input_features(observed, ops[layout]["cell"]))
        velocities.append(velocity)
        observations.append(observed)
        acquisitions.append(layout)
    return {"records": records, "features": np.stack(features),
            "velocity": np.stack(velocities), "observed": np.stack(observations),
            "acquisition": np.asarray(acquisitions),
            "manifest_sha256": physics.canonical_hash(records)}


def attach_classical_features(cohort: dict, baseline: np.ndarray) -> None:
    """Add truth-free classical model and corrected backprojection channels."""
    features = cohort.get("features")
    if (not isinstance(features, np.ndarray) or features.ndim != 4
            or features.shape[1:] != (2, physics.GRID, physics.GRID)):
        raise ValueError("M12 input features must be the exact two measured-geometry channels")
    if baseline.shape != cohort["velocity"].shape or not np.isfinite(baseline).all():
        raise ValueError("M12 baseline does not match the cohort grid")
    reference = physics.background().astype(np.float32)
    normalized = ((baseline.astype(np.float32) - reference[None]) / 400.0)
    cohort["features"] = np.concatenate((normalized[:, None], features), axis=1).astype(np.float32)
    cohort["baseline"] = baseline.astype(np.float32)


def network():
    import torch
    from torch import nn

    class Residual(nn.Module):
        def __init__(self):
            super().__init__()
            self.layers = nn.Sequential(nn.Conv2d(32, 32, 3, padding=1), nn.GELU(),
                                        nn.Conv2d(32, 32, 3, padding=1))

        def forward(self, value):
            return torch.nn.functional.gelu(value + self.layers(value))

    class Refinement(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = nn.Sequential(nn.Conv2d(3, 32, 3, padding=1), nn.GELU(),
                                         Residual(), Residual(), Residual(), Residual(),
                                         nn.Conv2d(32, 1, 1))
            nn.init.zeros_(self.encoder[-1].weight)
            nn.init.zeros_(self.encoder[-1].bias)

        def forward(self, features):
            # Channel zero is the normalized deterministic inverse. Recover it
            # exactly so the network output is a bounded correction to that map.
            reference = self.reference.to(dtype=features.dtype, device=features.device)
            prior = reference + 400.0 * features[:, 0]
            correction = RESIDUAL_SCALE_M_S * torch.tanh(self.encoder(features)[:, 0])
            return torch.clamp(prior + correction, min=1400.0, max=4000.0), correction

    model = Refinement()
    model.register_buffer("reference", torch.from_numpy(physics.background().astype(np.float32))[None])
    return model


def predict(model, cohort: dict, device: str) -> tuple[np.ndarray, np.ndarray]:
    import torch
    model.eval()
    estimates, corrections = [], []
    with torch.no_grad():
        for ids in np.array_split(np.arange(len(cohort["features"])), math.ceil(len(cohort["features"]) / 64)):
            x = torch.from_numpy(cohort["features"][ids]).to(device)
            estimate, correction = model(x)
            estimates.append(estimate.cpu().numpy())
            corrections.append(correction.cpu().numpy())
    return np.concatenate(estimates).astype(np.float64), np.concatenate(corrections).astype(np.float64)


def train(train: dict, validation: dict, ops: dict, *, device: str):
    import torch
    if device not in ("cpu", "cuda") or device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Requested M12 training device is unavailable")
    torch.manual_seed(SEED)
    torch.set_num_threads(4)
    if device == "cuda":
        torch.cuda.manual_seed_all(SEED)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    model = network().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    x = torch.from_numpy(train["features"]).to(device)
    truth = torch.from_numpy(train["velocity"]).to(device)
    picks = torch.from_numpy(train["observed"].astype(np.float32)).to(device)
    matrices = {name: torch.from_numpy(ops[name]["cell"].astype(np.float32)).to(device) for name in ("A", "B")}
    base_rmse = float(np.sqrt(np.mean((validation["baseline"] - validation["velocity"]) ** 2)))
    best_rmse, best_epoch = base_rmse, 0
    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    history = [{"epoch": 0, "validation_velocity_rmse_m_s": base_rmse,
                "train_objective": None, "selection": "unaltered physics inverse"}]
    stale = 0
    for epoch in range(1, EPOCHS + 1):
        model.train()
        losses = []
        for layout in ("A", "B"):
            ids = np.flatnonzero(train["acquisition"] == layout)
            shuffled = ids[torch.randperm(len(ids)).cpu().numpy()]
            for batch in np.array_split(shuffled, math.ceil(len(shuffled) / 64)):
                optimizer.zero_grad(set_to_none=True)
                x_batch = x[batch]
                estimate, delta = model(x_batch)
                model_loss = ((estimate - truth[batch]) / 400.0).square().mean()
                predicted_times = estimate.flatten(1).reciprocal() @ matrices[layout].T
                data_loss = ((predicted_times - picks[batch]) / 0.01).square().mean()
                residual_loss = (delta / RESIDUAL_SCALE_M_S).square().mean()
                objective = model_loss + DATA_WEIGHT * data_loss + RESIDUAL_WEIGHT * residual_loss
                if not torch.isfinite(objective):
                    raise FloatingPointError("Nonfinite M12 residual-refinement objective")
                objective.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()
                losses.append(float(objective.detach().cpu()))
        val_estimate, _ = predict(model, validation, device)
        val_rmse = float(np.sqrt(np.mean((val_estimate - validation["velocity"]) ** 2)))
        history.append({"epoch": epoch, "validation_velocity_rmse_m_s": val_rmse,
                        "train_objective": float(np.mean(losses)), "selection": "validation model RMSE"})
        if val_rmse < best_rmse - 1e-7:
            best_rmse, best_epoch = val_rmse, epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
        if epoch == 1 or epoch % 10 == 0 or stale == PATIENCE:
            print(f"M12 residual epoch {epoch}: validation {val_rmse:.3f} m/s; best {best_rmse:.3f} at {best_epoch}", flush=True)
        if stale >= PATIENCE:
            break
    model.load_state_dict(best_state)
    return model.eval(), history, best_epoch


def _score_all(model, cohorts, ops, lam, threshold, device):
    scored = {}
    for name, cohort in cohorts.items():
        if name == "train":
            continue
        learned, corrections = predict(model, cohort, device)
        scored[name] = physics.score(cohort, learned, cohort["baseline"], ops, threshold)
        scored[name]["mean_abs_learned_correction_m_s"] = float(np.mean(np.abs(corrections)))
        scored[name]["correction_nonzero_fraction"] = float(np.mean(np.abs(corrections) > 1e-5))
    return scored


def execute(output: Path, *, device: str = "cuda") -> dict:
    import scipy
    import torch
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"M12 output already exists: {output}")
    output.mkdir(parents=True)
    started = time.perf_counter()
    ops = physics.operators()
    cohorts = {name: make_cohort(name, ops) for name in COUNTS}
    lam, lambda_scores = physics.select_classical(cohorts["validation"], ops)
    for cohort in cohorts.values():
        baseline = physics.classical_predict(cohort, ops, lam)
        attach_classical_features(cohort, baseline)
    model, history, best_epoch = train(cohorts["train"], cohorts["validation"], ops, device=device)
    validation_prediction, _ = predict(model, cohorts["validation"], device)
    checkpoint = output / "m12-residual-v3.1.npz"
    checkpoint_sha = physics.save_checkpoint(model, checkpoint)
    loaded = load_checkpoint(checkpoint, checkpoint_sha, "cpu")
    cpu_validation, _ = predict(loaded, cohorts["validation"], "cpu")
    parity_difference = np.abs(cpu_validation - validation_prediction)
    parity = {"max_abs_m_s": float(parity_difference.max()),
              "p99_abs_m_s": float(np.quantile(parity_difference, 0.99)),
              "mean_abs_m_s": float(parity_difference.mean()),
              "acceptance": {"max_abs_m_s": 0.15, "p99_abs_m_s": 0.05, "mean_abs_m_s": 0.02},
              "status": "pass" if (parity_difference.max() <= 0.15
                    and np.quantile(parity_difference, 0.99) <= 0.05
                    and parity_difference.mean() <= 0.02) else "fail"}
    if parity["status"] != "pass":
        raise AssertionError(f"CPU/CUDA replay exceeds declared M12 parity envelope: {parity}")
    # All persisted evaluation metrics and the residual-screen threshold are
    # recomputed from the independently reloaded CPU checkpoint.
    threshold = float(np.quantile([item["learned_oracle_rmse_ms"]
        for item in physics.score(cohorts["validation"], cpu_validation,
            cohorts["validation"]["baseline"], ops, float("inf"))["per_record"]], 0.95))
    results = _score_all(loaded, cohorts, ops, lam, threshold, "cpu")
    status = physics.scientific_verdict(results["joint_ood"])
    receipt = {
        "schema": "caos-geophysics.m12-residual/v3.1", "protocol": PROTOCOL,
        "status": status, "device": device,
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "scipy": scipy.__version__, "torch": torch.__version__},
        "sources": {"implementation_sha256": sha256_bytes(Path(__file__).read_bytes()),
                    "forward_inverse_sha256": sha256_bytes(Path(physics.__file__).read_bytes()),
                    "corrected_feature_sha256": sha256_bytes(Path(corrected.__file__).read_bytes())},
        "checkpoint": checkpoint.name, "checkpoint_sha256": checkpoint_sha,
        "seed": SEED, "epochs_max": EPOCHS, "epochs_run": len(history) - 1,
        "selected_epoch": best_epoch, "history": history,
        "counts": {name: len(c["records"]) for name, c in cohorts.items()},
        "split_manifests": {name: c["records"] for name, c in cohorts.items()},
        "split_hashes": {name: c["manifest_sha256"] for name, c in cohorts.items()},
        "classical": {"selected_lambda": lam, "validation_candidate_rmse_m_s": lambda_scores,
                       "selection": "minimum validation velocity RMSE; shared across every cohort"},
        "objective": {"model_scale_m_s": 400.0, "travel_time_scale_s": 0.01,
                      "data_weight": DATA_WEIGHT, "residual_weight": RESIDUAL_WEIGHT,
                      "residual_bound_m_s": RESIDUAL_SCALE_M_S,
                      "optimizer": "Adam", "learning_rate": LEARNING_RATE,
                      "batch_size": 64, "early_stop_patience": PATIENCE},
        "cpu_cuda_parity": parity,
        "forward_threshold_ms": threshold,
        "forward_threshold_policy": "95th percentile of fresh validation learned oracle residuals",
        "cohorts": results, "wall_seconds": time.perf_counter() - started,
        "limitations": ["straight-ray tomography; no ray bending or waveform FWI",
                        "synthetic generator; not field geological validation",
                        "16x16 grid; fixed geometry and conditional noise",
                        "network is a bounded residual corrector over the selected L2 solution",
                        "OOD residual flag is not a calibrated probability"]}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return receipt


def load_checkpoint(path: Path, expected_sha: str, device: str = "cpu"):
    import torch
    if sha256_bytes(Path(path).read_bytes()) != expected_sha:
        raise ValueError("M12 checkpoint SHA-256 mismatch")
    model = network()
    with np.load(path, allow_pickle=False) as archive:
        expected = model.state_dict()
        if set(archive.files) != set(expected):
            raise ValueError("M12 checkpoint keys differ from the model")
        state = {}
        for key, reference in expected.items():
            array = archive[key]
            if array.shape != tuple(reference.shape) or array.dtype != np.float32 or not np.isfinite(array).all():
                raise ValueError(f"M12 checkpoint tensor invalid: {key}")
            state[key] = torch.from_numpy(array.copy())
    model.load_state_dict(state)
    return model.to(device).eval()


def verify(output: Path) -> dict:
    output = Path(output)
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    if receipt.get("schema") != "caos-geophysics.m12-residual/v3.1" or receipt.get("protocol") != PROTOCOL:
        raise ValueError("Unsupported M12 residual receipt")
    if receipt["sources"] != {"implementation_sha256": sha256_bytes(Path(__file__).read_bytes()),
                              "forward_inverse_sha256": sha256_bytes(Path(physics.__file__).read_bytes()),
                              "corrected_feature_sha256": sha256_bytes(Path(corrected.__file__).read_bytes())}:
        raise ValueError("M12 source hashes differ from the trained receipt")
    model = load_checkpoint(output / receipt["checkpoint"], receipt["checkpoint_sha256"], "cpu")
    ops = physics.operators()
    cohorts = {name: make_cohort(name, ops) for name in COUNTS}
    lam, lambda_scores = physics.select_classical(cohorts["validation"], ops)
    if lam != receipt["classical"]["selected_lambda"]:
        raise AssertionError("Validation-only classical selection changed")
    for cohort in cohorts.values():
        attach_classical_features(cohort, physics.classical_predict(cohort, ops, lam))
    threshold = receipt["forward_threshold_ms"]
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("Invalid M12 validation-only residual threshold")
    if receipt["counts"] != {name: len(c["records"]) for name, c in cohorts.items()}:
        raise AssertionError("M12 cohort count changed")
    if receipt["split_hashes"] != {name: c["manifest_sha256"] for name, c in cohorts.items()}:
        raise AssertionError("M12 split manifest changed")
    if receipt["split_manifests"] != {name: c["records"] for name, c in cohorts.items()}:
        raise AssertionError("M12 split records changed")
    reproduced = _score_all(model, cohorts, ops, lam, threshold, "cpu")
    for name, report in reproduced.items():
        original = receipt["cohorts"][name]
        for key in ("learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s",
                    "learned_oracle_rmse_ms", "classical_oracle_rmse_ms",
                    "learned_to_classical_velocity_ratio", "learned_to_classical_oracle_ratio"):
            if not np.isclose(report[key], original[key], rtol=1e-5, atol=1e-5):
                raise AssertionError(f"M12 replay metric changed: {name}/{key}")
        if report["noisy_input_sha256"] != original["noisy_input_sha256"]:
            raise AssertionError(f"M12 input hash changed: {name}")
    if physics.scientific_verdict(reproduced["joint_ood"]) != receipt["status"]:
        raise AssertionError("M12 scientific verdict differs from exact CPU replay")
    return {"status": "verified", "cohorts": len(reproduced), "selected_lambda": lam,
            "checkpoint_sha256": receipt["checkpoint_sha256"]}
