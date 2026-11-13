"""Train channel ablations for the frozen physics-conditioned velocity study.

The primary test receipt is read-only. Ablations use its training and validation
protocol but fresh held-out seed namespaces. Their result is exploratory and
cannot replace or amend the primary locked comparison.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
import velocity_physics_refinement as physics  # noqa: E402
import velocity_validation as original  # noqa: E402

PRIMARY_RECEIPT_SHA256 = "fe0697531923f24ed0dafc7fba1469eb1ba9b2459615fedce3336934b9370ae0"
FRESH_COHORTS = {
    "id_test": (160, 177001, original.TRAIN_FAMILIES, ("A", "B")),
    "family_only": (80, 187001, original.TEST_FAMILIES, ("A", "B")),
    "acquisition_only": (80, 197001, original.TRAIN_FAMILIES, ("C",)),
    "joint_ood": (160, 207001, original.TEST_FAMILIES, ("C",)),
}
ABLATIONS = {
    "residual_only": np.asarray([1.0, 0.0], dtype=np.float32),
    "coverage_only": np.asarray([0.0, 1.0], dtype=np.float32),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def masked(cohort: dict, mask: np.ndarray) -> dict:
    result = dict(cohort)
    result["features"] = (cohort["features"] * mask[None, :, None, None]).astype(np.float32)
    return result


def make_fresh_cohort(name: str, ops: dict, *, fixture: bool) -> dict:
    count, seed_base, families, layouts = FRESH_COHORTS[name]
    if fixture:
        count = min(count, 12)
    records, features, velocities, observations, acquisitions = [], [], [], [], []
    for index in range(count):
        seed = seed_base + index
        family = families[index % len(families)]
        layout = layouts[(index // len(families)) % len(layouts)]
        rng = np.random.default_rng(seed)
        velocity = original.velocity_family(family, rng)
        observed = ops[layout]["oracle"] @ (1 / velocity.ravel())
        observed += rng.normal(0, original.NOISE_S, size=len(observed))
        records.append({
            "id": f"m12-ablation-v1:{name}:{seed}:{family}:{layout}",
            "seed": seed,
            "family": family,
            "acquisition": layout,
            "velocity_sha256": original.sha256_bytes(velocity.astype("<f4").tobytes()),
            "noisy_picks_sha256": original.sha256_bytes(observed.astype("<f8").tobytes()),
        })
        features.append(physics.input_features(observed, ops[layout]["cell"]))
        velocities.append(velocity)
        observations.append(observed)
        acquisitions.append(layout)
    return {
        "records": records,
        "features": np.stack(features),
        "velocity": np.stack(velocities),
        "observed": np.stack(observations),
        "acquisition": np.asarray(acquisitions),
        "manifest_sha256": original.canonical_hash(records),
    }


def train_channel_model(train: dict, validation: dict, ops: dict, mask: np.ndarray,
                        *, fixture: bool, device: str):
    import torch

    if device not in ("cpu", "cuda") or (device == "cuda" and not torch.cuda.is_available()):
        raise ValueError("Requested compute device unavailable")
    torch.manual_seed(77213)
    torch.set_num_threads(4)
    model = physics.network().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    x = torch.from_numpy(masked(train, mask)["features"]).to(device)
    truth = torch.from_numpy(train["velocity"]).to(device)
    picks = torch.from_numpy(train["observed"].astype(np.float32)).to(device)
    matrices = {name: torch.from_numpy(ops[name]["cell"].astype(np.float32)).to(device)
                for name in ("A", "B")}
    validation_masked = masked(validation, mask)
    validation_x = torch.from_numpy(validation_masked["features"]).to(device)
    validation_truth = validation_masked["velocity"]
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
                    raise FloatingPointError("Nonfinite channel-ablation objective")
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach().cpu()))
        model.eval()
        with torch.inference_mode():
            predicted = model(validation_x).cpu().numpy()
        rmse = float(np.sqrt(np.mean((predicted - validation_truth) ** 2)))
        history.append({"epoch": epoch + 1, "train_objective": float(np.mean(losses)),
                        "validation_velocity_rmse_m_s": rmse})
        if rmse < best:
            best, selected = rmse, epoch + 1
            weights = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        print(f"{int(mask[0])}{int(mask[1])} channel mask epoch {epoch + 1}/{epochs}; "
              f"validation {rmse:.3f} m/s", flush=True)
    model.load_state_dict(weights)
    return model.eval(), history, selected


def predict(model, cohort: dict, mask: np.ndarray, device: str) -> np.ndarray:
    import torch

    values = torch.from_numpy(masked(cohort, mask)["features"]).to(device)
    with torch.inference_mode():
        result = model(values).cpu().numpy()
    if not np.isfinite(result).all():
        raise FloatingPointError("Ablation produced nonfinite velocity")
    return result


def execute(output: Path, primary: Path, *, device: str = "cpu", fixture: bool = False) -> dict:
    import torch

    if output.exists():
        raise FileExistsError("Ablation output directory must be new")
    primary_receipt_path = primary / "receipt.json"
    if sha256_file(primary_receipt_path) != PRIMARY_RECEIPT_SHA256:
        raise ValueError("Primary receipt hash differs from the frozen run")
    primary_receipt = json.loads(primary_receipt_path.read_text(encoding="utf-8"))
    if primary_receipt.get("status") != "failed-held-out-comparator":
        raise ValueError("Primary negative result status changed")
    if sha256_file(primary / primary_receipt["checkpoint"]) != primary_receipt["checkpoint_sha256"]:
        raise ValueError("Primary checkpoint hash mismatch")
    output.mkdir(parents=True)
    start = time.perf_counter()
    ops = original.operators()
    cohorts = {name: physics.make_cohort(name, ops, fixture=fixture)
               for name in ("train", "validation")}
    fresh = {name: make_fresh_cohort(name, ops, fixture=fixture) for name in FRESH_COHORTS}
    selected_lambda, _ = original.select_classical(cohorts["validation"], ops)
    if not fixture and selected_lambda != primary_receipt["classical"]["selected_lambda"]:
        raise AssertionError("Validation-selected classical lambda differs from primary receipt")
    if fixture:
        selected_lambda = primary_receipt["classical"]["selected_lambda"]
    variants = {}
    full_model = physics.load_checkpoint(primary / primary_receipt["checkpoint"],
                                         primary_receipt["checkpoint_sha256"], device)
    models = {"full": (full_model, np.asarray([1.0, 1.0], dtype=np.float32),
                        primary_receipt["checkpoint_sha256"], primary_receipt["selected_epoch"],
                        primary_receipt["history"])}
    for name, mask in ABLATIONS.items():
        model, history, epoch = train_channel_model(cohorts["train"], cohorts["validation"], ops,
                                                    mask, fixture=fixture, device=device)
        checkpoint = output / f"{name}.npz"
        digest = original.save_checkpoint(model, checkpoint)
        models[name] = (model, mask, digest, epoch, history)
    for name, (model, mask, digest, epoch, history) in models.items():
        validation_prediction = predict(model, cohorts["validation"], mask, device)
        validation_score = original.score(
            cohorts["validation"], validation_prediction,
            original.classical_predict(cohorts["validation"], ops, selected_lambda), ops, float("inf"))
        threshold = float(np.quantile([row["learned_oracle_rmse_ms"]
                                       for row in validation_score["per_record"]], 0.95))
        scored = {}
        for cohort_name, cohort in fresh.items():
            scored[cohort_name] = original.score(
                cohort, predict(model, cohort, mask, device),
                original.classical_predict(cohort, ops, selected_lambda), ops, threshold)
        variants[name] = {"mask": mask.astype(int).tolist(), "checkpoint_sha256": digest,
                          "selected_epoch": epoch, "history": history,
                          "validation_threshold_ms": threshold, "cohorts": scored}
    result = {
        "schema": "geophysics.m12-physics-ablation/v1",
        "status": "fixture-only" if fixture else "exploratory-channel-ablation",
        "primary_receipt_sha256": PRIMARY_RECEIPT_SHA256,
        "primary_checkpoint_sha256": primary_receipt["checkpoint_sha256"],
        "device": device,
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "seed": 77213,
        "epochs": 1 if fixture else 40,
        "classical_selected_lambda": selected_lambda,
        "code_sha256": sha256_file(Path(__file__).resolve()),
        "operator_code_sha256": original.sha256_bytes(Path(original.__file__).read_bytes()),
        "feature_code_sha256": original.sha256_bytes(Path(physics.__file__).read_bytes()),
        "fresh_cohorts": {name: {"count": len(cohort["records"]),
                                 "manifest_sha256": cohort["manifest_sha256"],
                                 "records": cohort["records"]}
                          for name, cohort in fresh.items()},
        "variants": variants,
        "interpretation": "Exploratory ablations on fresh synthetic seeds; not a confirmatory rescue of the failed primary hypothesis.",
        "limitations": ["straight-ray 16 by 16 synthetic generator", "family definitions and layouts are known",
                        "no field data", "channel ablations do not establish novelty or generalization"],
        "wall_seconds": time.perf_counter() - start,
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n",
                                          encoding="utf-8")
    return result


def verify(output: Path, primary: Path) -> dict:
    receipt_path = output / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "geophysics.m12-physics-ablation/v1" or receipt.get("status") == "fixture-only":
        raise ValueError("Unsupported or fixture-only ablation receipt")
    if receipt["primary_receipt_sha256"] != PRIMARY_RECEIPT_SHA256:
        raise ValueError("Ablation receipt does not bind to the approved primary run")
    if receipt["code_sha256"] != sha256_file(Path(__file__).resolve()):
        raise ValueError("Ablation source hash mismatch")
    primary_receipt_path = primary / "receipt.json"
    if sha256_file(primary_receipt_path) != PRIMARY_RECEIPT_SHA256:
        raise ValueError("Primary receipt hash mismatch during ablation replay")
    primary_receipt = json.loads(primary_receipt_path.read_text(encoding="utf-8"))
    if sha256_file(primary / primary_receipt["checkpoint"]) != receipt["primary_checkpoint_sha256"]:
        raise ValueError("Primary checkpoint hash mismatch during ablation replay")
    if receipt["operator_code_sha256"] != original.sha256_bytes(Path(original.__file__).read_bytes()):
        raise ValueError("Forward-operator source hash mismatch during ablation replay")
    if receipt["feature_code_sha256"] != original.sha256_bytes(Path(physics.__file__).read_bytes()):
        raise ValueError("Feature-pipeline source hash mismatch during ablation replay")
    ops = original.operators()
    cohorts = {name: make_fresh_cohort(name, ops, fixture=False) for name in FRESH_COHORTS}
    for name, cohort in cohorts.items():
        frozen = receipt["fresh_cohorts"][name]
        if cohort["manifest_sha256"] != frozen["manifest_sha256"]:
            raise AssertionError(f"Fresh cohort changed: {name}")
    lam = receipt["classical_selected_lambda"]
    for name, variant in receipt["variants"].items():
        digest = variant["checkpoint_sha256"]
        checkpoint = (primary / primary_receipt["checkpoint"]
                     if name == "full" else output / f"{name}.npz")
        model = physics.load_checkpoint(checkpoint, digest, "cpu")
        mask = np.asarray(variant["mask"], dtype=np.float32)
        for cohort_name, cohort in cohorts.items():
            score = original.score(cohort, predict(model, cohort, mask, "cpu"),
                                   original.classical_predict(cohort, ops, lam), ops,
                                   float(variant["validation_threshold_ms"]))
            stored = variant["cohorts"][cohort_name]
            for key in ("learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s",
                        "learned_oracle_rmse_ms", "classical_oracle_rmse_ms",
                        "learned_to_classical_velocity_ratio", "learned_to_classical_oracle_ratio"):
                if not np.isclose(score[key], stored[key], rtol=1e-5, atol=1e-4):
                    raise AssertionError(f"Replay drift: {name}/{cohort_name}/{key}")
            if score["forward_threshold_exceedances"] != stored["forward_threshold_exceedances"]:
                raise AssertionError(f"Threshold flag drift: {name}/{cohort_name}")
            for actual, expected in zip(score["per_record"], stored["per_record"], strict=True):
                if (actual["id"] != expected["id"]
                        or actual["forward_threshold_exceeded"] != expected["forward_threshold_exceeded"]):
                    raise AssertionError(f"Per-record identity or flag drift: {name}/{cohort_name}")
                for key in ("learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s",
                            "learned_oracle_rmse_ms", "classical_oracle_rmse_ms"):
                    if not np.isclose(actual[key], expected[key], rtol=1e-5, atol=1e-4):
                        raise AssertionError(f"Per-record metric drift: {name}/{cohort_name}/{actual['id']}/{key}")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    receipt = verify(args.output, args.primary) if args.verify else execute(
        args.output, args.primary, device=args.device, fixture=args.fixture)
    print(json.dumps({"status": receipt["status"], "device": receipt.get("device"),
                      "variants": list(receipt.get("variants", {})),
                      "wall_seconds": receipt.get("wall_seconds")}, indent=2))


if __name__ == "__main__":
    main()
