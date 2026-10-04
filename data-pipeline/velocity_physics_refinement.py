"""Fresh M12 study correcting ray-length normalization; original evidence untouched."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import platform
import time

import numpy as np
import velocity_validation as original

COHORTS = {
    "train": (800, 117001, original.TRAIN_FAMILIES, ("A", "B")),
    "validation": (160, 127001, original.TRAIN_FAMILIES, ("A", "B")),
    "id_test": (160, 137001, original.TRAIN_FAMILIES, ("A", "B")),
    "family_only": (80, 147001, original.TEST_FAMILIES, ("A", "B")),
    "acquisition_only": (80, 157001, original.TRAIN_FAMILIES, ("C",)),
    "joint_ood": (160, 167001, original.TEST_FAMILIES, ("C",)),
}


def input_features(observed, matrix):
    observed = np.asarray(observed, dtype=np.float64)
    matrix = np.asarray(matrix, dtype=np.float64)
    if (matrix.ndim != 2 or matrix.shape[1] != 256 or observed.shape != (len(matrix),)
            or not np.isfinite(matrix).all() or not np.isfinite(observed).all()
            or np.any(matrix < 0)):
        raise ValueError("Invalid physical ray features")
    length, coverage = matrix.sum(axis=1), matrix.sum(axis=0)
    if np.any(length <= 0):
        raise ValueError("Ray length must be positive")
    reference = original.background().ravel()
    residual_slowness = (observed - matrix @ (1 / reference)) / length
    h = np.divide(matrix.T @ residual_slowness, coverage,
                  out=np.zeros(256), where=coverage > 0)
    velocity_feature = -h * reference ** 2 / 400
    return np.stack((velocity_feature.reshape(16, 16),
                     (coverage / coverage.max()).reshape(16, 16))).astype(np.float32)


def make_cohort(name, ops, *, fixture=False):
    count, seed_base, families, layouts = COHORTS[name]
    count = min(count, 12) if fixture else count
    records, features, velocities, observations, acquisitions = [], [], [], [], []
    for index in range(count):
        seed = seed_base + index
        family = families[index % len(families)]
        layout = layouts[(index // len(families)) % len(layouts)]
        rng = np.random.default_rng(seed)
        velocity = original.velocity_family(family, rng)
        observed = ops[layout]["oracle"] @ (1 / velocity.ravel())
        observed += rng.normal(0, original.NOISE_S, size=len(observed))
        records.append({"id": f"m12-physics-v2:{name}:{seed}:{family}:{layout}",
                        "seed": seed, "family": family, "acquisition": layout,
                        "velocity_sha256": original.sha256_bytes(velocity.astype("<f4").tobytes()),
                        "noisy_picks_sha256": original.sha256_bytes(observed.astype("<f8").tobytes())})
        features.append(input_features(observed, ops[layout]["cell"]))
        velocities.append(velocity)
        observations.append(observed)
        acquisitions.append(layout)
    return {"records": records, "features": np.stack(features), "velocity": np.stack(velocities),
            "observed": np.stack(observations), "acquisition": np.asarray(acquisitions),
            "manifest_sha256": original.canonical_hash(records)}


def network():
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
            nn.init.zeros_(self.net[-1].weight)
            nn.init.zeros_(self.net[-1].bias)
            p = (original.background() - 1400) / 2600
            self.register_buffer("reference_logit", torch.as_tensor(np.log(p / (1 - p)), dtype=torch.float32)[None])

        def forward(self, features):
            return 1400 + 2600 * torch.sigmoid(self.reference_logit + self.net(features)[:, 0])

    return VelocityNet()


def load_checkpoint(path, expected_sha256, device="cpu"):
    import torch
    if original.sha256_bytes(Path(path).read_bytes()) != expected_sha256:
        raise ValueError("M12 refinement checkpoint identity mismatch")
    model = network()
    with np.load(path, allow_pickle=False) as arrays:
        expected = model.state_dict()
        if set(arrays.files) != set(expected):
            raise ValueError("Checkpoint state keys differ")
        state = {}
        for key, value in expected.items():
            array = arrays[key]
            if array.shape != tuple(value.shape) or array.dtype != np.float32 or not np.isfinite(array).all():
                raise ValueError("Invalid checkpoint state")
            state[key] = torch.from_numpy(array.copy())
    model.load_state_dict(state)
    return model.to(device).eval()


def train_model(train, validation, ops, *, fixture, device):
    import torch
    if device not in ("cpu", "cuda") or (device == "cuda" and not torch.cuda.is_available()):
        raise ValueError("Requested compute device unavailable")
    torch.manual_seed(77213)
    torch.set_num_threads(4)
    model = network().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    x = torch.from_numpy(train["features"]).to(device)
    truth = torch.from_numpy(train["velocity"]).to(device)
    picks = torch.from_numpy(train["observed"].astype(np.float32)).to(device)
    matrices = {name: torch.from_numpy(ops[name]["cell"].astype(np.float32)).to(device) for name in ("A", "B")}
    history, best, selected, weights = [], float("inf"), None, None
    epochs = 1 if fixture else 40
    for epoch in range(epochs):
        model.train()
        losses = []
        for layout in ("A", "B"):
            indices = np.flatnonzero(train["acquisition"] == layout)
            indices = indices[torch.randperm(len(indices)).numpy()]
            for batch in np.array_split(indices, math.ceil(len(indices) / 64)):
                optimizer.zero_grad()
                prediction = model(x[batch])
                predicted_times = prediction.flatten(1).reciprocal() @ matrices[layout].T
                loss = ((prediction - truth[batch]) / 400).square().mean()
                loss += 0.1 * ((predicted_times - picks[batch]) / 0.01).square().mean()
                if not torch.isfinite(loss):
                    raise FloatingPointError("Nonfinite revised training objective")
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach().cpu()))
        predicted = original._predict(model, validation, device)
        rmse = float(np.sqrt(np.mean((predicted - validation["velocity"]) ** 2)))
        history.append({"epoch": epoch + 1, "train_objective": float(np.mean(losses)),
                        "validation_velocity_rmse_m_s": rmse})
        if rmse < best:
            best, selected = rmse, epoch + 1
            weights = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        print(f"M12 physics epoch {epoch + 1}/{epochs}, validation {rmse:.3f} m/s", flush=True)
    model.load_state_dict(weights)
    return model.eval(), history, selected


def execute(output, *, device="cpu", fixture=False):
    import scipy
    import torch
    output = Path(output)
    if output.exists():
        raise FileExistsError("Refinement output must be new")
    output.mkdir(parents=True)
    start = time.perf_counter()
    ops = original.operators()
    data = {name: make_cohort(name, ops, fixture=fixture) for name in COHORTS}
    lam, candidates = original.select_classical(data["validation"], ops)
    model, history, epoch = train_model(data["train"], data["validation"], ops, fixture=fixture, device=device)
    checkpoint = output / "m12-physics.npz"
    sha = original.save_checkpoint(model, checkpoint)
    reloaded = load_checkpoint(checkpoint, sha, device)
    prediction = original._predict(reloaded, data["validation"], device)
    preliminary = original.score(data["validation"], prediction,
                                 original.classical_predict(data["validation"], ops, lam), ops, float("inf"))
    threshold = float(np.quantile([x["learned_oracle_rmse_ms"] for x in preliminary["per_record"]], 0.95))
    scores = {name: original.score(cohort, original._predict(reloaded, cohort, device),
                                   original.classical_predict(cohort, ops, lam), ops, threshold)
              for name, cohort in data.items() if name != "train"}
    receipt = {
        "schema": "geophysics.m12-physics/v2", "status": "fixture-only" if fixture else original.scientific_verdict(scores["joint_ood"]),
        "device": device, "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "torch": torch.__version__},
        "code_sha256": original.sha256_bytes(Path(__file__).read_bytes()),
        "operator_code_sha256": original.sha256_bytes(Path(original.__file__).read_bytes()),
        "checkpoint": checkpoint.name, "checkpoint_sha256": sha, "seed": 77213,
        "epochs": len(history), "selected_epoch": epoch, "history": history,
        "counts": {name: len(cohort["records"]) for name, cohort in data.items()},
        "split_manifests": {name: cohort["records"] for name, cohort in data.items()},
        "split_hashes": {name: cohort["manifest_sha256"] for name, cohort in data.items()},
        "classical": {"selected_lambda": lam, "validation_candidate_rmse_m_s": candidates},
        "forward_threshold_ms": threshold, "cohorts": scores,
        "original_benchmark": "failed-held-out-comparator; retained unchanged",
        "limitations": ["straight rays", "16x16 output", "known synthetic family definitions; fresh realizations",
                        "bilinear forward is not field truth", "residual flags are not calibrated probabilities"],
        "wall_seconds": time.perf_counter() - start,
    }
    with (output / "receipt.json").open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, allow_nan=False)
    return receipt


def verify(output):
    output = Path(output)
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    if receipt["schema"] != "geophysics.m12-physics/v2":
        raise ValueError("Unsupported refinement receipt")
    if receipt["status"] == "fixture-only":
        raise ValueError("Fixture does not qualify the full experiment")
    if receipt["epochs"] != 40 or receipt["code_sha256"] != original.sha256_bytes(Path(__file__).read_bytes()):
        raise ValueError("Protocol or source identity mismatch")
    if receipt["operator_code_sha256"] != original.sha256_bytes(Path(original.__file__).read_bytes()):
        raise ValueError("Operator source identity mismatch")
    import torch
    torch.set_num_threads(4)
    model = load_checkpoint(output / receipt["checkpoint"], receipt["checkpoint_sha256"])
    ops = original.operators()
    validation = make_cohort("validation", ops)
    lam, candidates = original.select_classical(validation, ops)
    if receipt["classical"] != {"selected_lambda": lam, "validation_candidate_rmse_m_s": candidates}:
        raise ValueError("Classical selection drift")
    for name in COHORTS:
        cohort = validation if name == "validation" else make_cohort(name, ops)
        if (len(cohort["records"]) != receipt["counts"][name]
                or cohort["records"] != receipt["split_manifests"][name]
                or cohort["manifest_sha256"] != receipt["split_hashes"][name]):
            raise ValueError("Partition identity drift")
        if name == "train":
            continue
        score = original.score(cohort, original._predict(model, cohort, "cpu"),
                               original.classical_predict(cohort, ops, lam), ops, receipt["forward_threshold_ms"])
        previous = receipt["cohorts"][name]
        for metric in ("learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s",
                       "learned_oracle_rmse_ms", "classical_oracle_rmse_ms",
                       "learned_to_classical_velocity_ratio", "learned_to_classical_oracle_ratio"):
            if not np.isclose(score[metric], previous[metric], rtol=1e-5, atol=1e-4):
                raise ValueError("Aggregate metric drift")
        if (score["count"] != previous["count"]
                or score["noisy_input_sha256"] != previous["noisy_input_sha256"]):
            raise ValueError("Metric population drift")
        if score["forward_threshold_exceedances"] != previous["forward_threshold_exceedances"]:
            raise ValueError("Residual flag count drift")
        if name == "validation":
            threshold = float(np.quantile([x["learned_oracle_rmse_ms"] for x in score["per_record"]], 0.95))
            if not np.isclose(threshold, receipt["forward_threshold_ms"], rtol=1e-5, atol=1e-4):
                raise ValueError("Validation threshold drift")
        for new, old in zip(score["per_record"], previous["per_record"], strict=True):
            if new["id"] != old["id"] or new["forward_threshold_exceeded"] != old["forward_threshold_exceeded"]:
                raise ValueError("Per-record identity drift")
            for metric in ("learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s", "learned_oracle_rmse_ms", "classical_oracle_rmse_ms"):
                if not np.isclose(new[metric], old[metric], rtol=1e-5, atol=1e-4):
                    raise ValueError("Per-record metric drift")
    if original.scientific_verdict(receipt["cohorts"]["joint_ood"]) != receipt["status"]:
        raise ValueError("Scientific verdict mismatch")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    receipt = verify(args.output) if args.verify else execute(args.output, device=args.device, fixture=args.fixture)
    print(json.dumps({"status": receipt["status"], "device": receipt["device"],
                      "checkpoint_sha256": receipt["checkpoint_sha256"],
                      "joint_model_ratio": receipt["cohorts"]["joint_ood"]["learned_to_classical_velocity_ratio"],
                      "joint_data_ratio": receipt["cohorts"]["joint_ood"]["learned_to_classical_oracle_ratio"]}, indent=2))


if __name__ == "__main__":
    main()
