#!/usr/bin/env python3
"""Verify frozen numerical outputs and regenerate the manuscript's figures and tables."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PAPER = Path(__file__).resolve().parent
DATA = PAPER / "data"
FIGURES = PAPER / "figures"
GENERATED = PAPER / "generated"
BOOTSTRAPS = 20_000
BOOTSTRAP_SEED = 6_120_226
EXPECTED = {
    "primary-receipt.json": "fe0697531923f24ed0dafc7fba1469eb1ba9b2459615fedce3336934b9370ae0",
    "primary-checkpoint.npz": "ff6ceb75c8e641c6e17dee911c99a3aa786fcdad4f290b86e93bfc32e809bbb5",
    "ablation-receipt.json": "85838d36b5adb34329866ca25a55a468892e7baf21e63c4076673c79d5dfc5a6",
    "residual-only.npz": "3127d7703ed6d1d9df8f6cbd5e9950ff3ff6d92726c9adf7a25e9d3a57949ec0",
    "coverage-only.npz": "6c022a53ddc3891129e906e6bb60053f0f3aa606ae493727487beaeff1a32ad6",
}
REPLAY_EXPECTED = {
    "independent-replay-receipt.json": "d0b7905b80a184f01a761bb80430e7b6557fcc9dc00a88326f57c9bbdcf5975d",
    "independent-replay-checkpoint.npz": "b7d606a04fe66286490b62b5ddae89e9c4aca882c15afe56524f21f0e511beaf",
}
EXPECTED_TRAINING_CODE = "aa85618783b014df20612e72ca0451f68e658e5dc12ebb4336d1f54259cf4b3e"
EXPECTED_OPERATOR_CODE = "2b9ed95d3ba7b1b0f9f80167fa610640dc75c8a142dafb9f7f09791b96a1fd44"
COHORTS = ("id_test", "family_only", "acquisition_only", "joint_ood")
COHORT_LABELS = {
    "id_test": "In distribution",
    "family_only": "Family shift",
    "acquisition_only": "Acquisition shift",
    "joint_ood": "Joint shift",
}
MODELS = ("full", "residual_only", "coverage_only")
MODEL_LABELS = {"full": "Both channels", "residual_only": "Residual only", "coverage_only": "Coverage only"}
COLORS = {"full": "#315b72", "residual_only": "#b56c38", "coverage_only": "#8a5b7d"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_evidence() -> tuple[dict, dict, dict, dict]:
    for name, expected in EXPECTED.items():
        actual = digest(DATA / name)
        require(actual == expected, f"{name} SHA-256 mismatch: {actual}")
    training_source = digest(ROOT / "data-pipeline/velocity_physics_refinement.py")
    operator_source = digest(ROOT / "data-pipeline/velocity_validation.py")
    require(training_source == EXPECTED_TRAINING_CODE,
            f"Current velocity feature/training source changed: {training_source}")
    require(operator_source == EXPECTED_OPERATOR_CODE,
            f"Current velocity operator source changed: {operator_source}")
    primary = json.loads((DATA / "primary-receipt.json").read_text(encoding="utf-8"))
    ablation = json.loads((DATA / "ablation-receipt.json").read_text(encoding="utf-8"))
    replay = json.loads((DATA / "independent-replay-receipt.json").read_text(encoding="utf-8"))
    require(primary["schema"] == "geophysics.m12-physics/v2", "Unsupported primary receipt schema")
    require(primary["status"] == "failed-held-out-comparator", "Primary result is not the recorded negative result")
    require(primary["code_sha256"] == EXPECTED_TRAINING_CODE, "Primary training code identity mismatch")
    require(primary["operator_code_sha256"] == EXPECTED_OPERATOR_CODE, "Primary operator identity mismatch")
    require(ablation["schema"] == "geophysics.m12-physics-ablation/v1", "Unsupported ablation schema")
    require(ablation["primary_receipt_sha256"] == EXPECTED["primary-receipt.json"], "Ablation is not bound to primary receipt")
    require(ablation["primary_checkpoint_sha256"] == EXPECTED["primary-checkpoint.npz"], "Ablation is not bound to primary checkpoint")
    require(ablation["operator_code_sha256"] == EXPECTED_OPERATOR_CODE, "Ablation operator identity mismatch")
    require(ablation["feature_code_sha256"] == EXPECTED_TRAINING_CODE, "Ablation feature code identity mismatch")
    for name, expected in REPLAY_EXPECTED.items():
        actual = digest(DATA / name)
        require(actual == expected, f"{name} SHA-256 mismatch: {actual}")
    require(replay["schema"] == primary["schema"] == "geophysics.m12-physics/v2",
            "Independent replay schema differs from the primary run")
    require(replay["status"] == primary["status"] == "failed-held-out-comparator",
            "Independent replay status differs from the primary result")
    require(replay["code_sha256"] == primary["code_sha256"] == EXPECTED_TRAINING_CODE,
            "Independent replay training source differs")
    require(replay["operator_code_sha256"] == primary["operator_code_sha256"] == EXPECTED_OPERATOR_CODE,
            "Independent replay operator source differs")
    require(replay["seed"] == primary["seed"] and replay["epochs"] == primary["epochs"],
            "Independent replay seed or epoch budget differs")
    for cohort in ("validation", *COHORTS):
        current = replay["cohorts"][cohort]
        frozen = primary["cohorts"][cohort]
        require(current["manifest_sha256"] == frozen["manifest_sha256"],
                f"Independent replay cohort differs: {cohort}")
        require(current["count"] == frozen["count"], f"Independent replay cohort size differs: {cohort}")
        require([row["id"] for row in current["per_record"]] == [row["id"] for row in frozen["per_record"]],
                f"Independent replay case identifiers differ: {cohort}")
    for model in MODELS:
        filename = {"residual_only": "residual-only.npz", "coverage_only": "coverage-only.npz"}.get(model)
        if filename:
            require(ablation["variants"][model]["checkpoint_sha256"] == EXPECTED[filename], f"{model} checkpoint mismatch")
    return primary, ablation, replay, {
        "receipt_sha256": {name: EXPECTED[name] for name in EXPECTED},
        "replay_sha256": REPLAY_EXPECTED,
        "training_code_sha256": EXPECTED_TRAINING_CODE,
        "operator_code_sha256": EXPECTED_OPERATOR_CODE,
    }


def resolution_diagnostics() -> list[dict]:
    """Measure the exact acquisition support and normalized kernel spectrum."""
    source = ROOT / "data-pipeline/velocity_validation.py"
    spec = importlib.util.spec_from_file_location("velocity_validation_for_paper", source)
    require(spec is not None and spec.loader is not None, "Cannot load the hash-verified ray operator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = []
    for name, item in module.operators().items():
        rays = item["rays"]
        matrix = item["cell"]
        ray_lengths = matrix.sum(axis=1)
        coverage = matrix.sum(axis=0)
        supported = coverage > 0.0
        active = matrix[:, supported]
        gram = (active.T / ray_lengths) @ active
        scale = np.sqrt(coverage[supported])
        normalized = gram / scale[:, None] / scale[None, :]
        spectrum = np.linalg.eigvalsh(normalized)[::-1]
        cutoff = float(spectrum[0]) * 1e-10
        positive = spectrum[spectrum > cutoff]
        directions = np.mod(np.degrees(np.arctan2(rays[:, 3] - rays[:, 1],
                                                  rays[:, 2] - rays[:, 0])), 180.0)
        angles = np.unique(np.round(directions, 10))
        angle_gaps = np.diff(np.r_[angles, angles[0] + 180.0])
        result.append({
            "layout": name,
            "ray_count": int(len(rays)),
            "supported_cells": int(supported.sum()),
            "grid_cells": int(matrix.shape[1]),
            "supported_fraction": float(supported.mean()),
            "numerical_rank": int(len(positive)),
            "positive_eigenvalues": positive.tolist(),
            "minimum_to_maximum_positive_eigenvalue": float(positive[-1] / positive[0]),
            "unique_axial_angles": int(len(angles)),
            "maximum_axial_angle_gap_deg": float(angle_gaps.max()),
            "angle_values_deg": angles.tolist(),
        })
    return result


def bootstrap_ratio(records: list[dict], learned_key: str, reference_key: str, seed: int) -> dict:
    learned = np.asarray([row[learned_key] for row in records], dtype=np.float64)
    reference = np.asarray([row[reference_key] for row in records], dtype=np.float64)
    require(len(learned) > 1 and np.isfinite(learned).all() and np.isfinite(reference).all(), "Invalid per-case metric")
    point = float(np.mean(learned) / np.mean(reference))
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(records), size=(BOOTSTRAPS, len(records)))
    values = np.mean(learned[draws], axis=1) / np.mean(reference[draws], axis=1)
    low, high = np.quantile(values, [0.025, 0.975], method="linear")
    return {"ratio": point, "ci95": [float(low), float(high)], "n": len(records)}


def summaries(primary: dict, ablation: dict, replay: dict) -> dict:
    result = {"schema": "caos-geophysics-paper-analysis/v1", "bootstrap_replicates": BOOTSTRAPS,
              "bootstrap_seed": BOOTSTRAP_SEED, "primary": {}, "ablation": {}, "independent_replay": {}}
    for ci, cohort in enumerate(COHORTS):
        p = primary["cohorts"][cohort]
        result["primary"][cohort] = {
            "velocity": bootstrap_ratio(p["per_record"], "learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s", BOOTSTRAP_SEED + ci),
            "travel_time": bootstrap_ratio(p["per_record"], "learned_oracle_rmse_ms", "classical_oracle_rmse_ms", BOOTSTRAP_SEED + 10 + ci),
            "flags": p["forward_threshold_exceedances"], "threshold_ms": primary["forward_threshold_ms"],
            "receipt_velocity_ratio": p["learned_to_classical_velocity_ratio"],
            "receipt_time_ratio": p["learned_to_classical_oracle_ratio"],
        }
        require(abs(result["primary"][cohort]["velocity"]["ratio"] - p["learned_to_classical_velocity_ratio"]) < 1e-8,
                f"Primary velocity aggregate drift in {cohort}")
        require(abs(result["primary"][cohort]["travel_time"]["ratio"] - p["learned_to_classical_oracle_ratio"]) < 1e-8,
                f"Primary travel-time aggregate drift in {cohort}")
        result["ablation"][cohort] = {}
        replay_cohort = replay["cohorts"][cohort]
        result["independent_replay"][cohort] = {
            "velocity": bootstrap_ratio(replay_cohort["per_record"], "learned_velocity_rmse_m_s",
                                         "classical_velocity_rmse_m_s", BOOTSTRAP_SEED + 300 + ci),
            "travel_time": bootstrap_ratio(replay_cohort["per_record"], "learned_oracle_rmse_ms",
                                            "classical_oracle_rmse_ms", BOOTSTRAP_SEED + 310 + ci),
            "flags": replay_cohort["forward_threshold_exceedances"],
            "threshold_ms": replay["forward_threshold_ms"],
            "checkpoint_sha256": replay["checkpoint_sha256"],
        }
        require(abs(result["independent_replay"][cohort]["velocity"]["ratio"]
                    - replay_cohort["learned_to_classical_velocity_ratio"]) < 1e-8,
                f"Independent replay velocity aggregate drift in {cohort}")
        require(abs(result["independent_replay"][cohort]["travel_time"]["ratio"]
                    - replay_cohort["learned_to_classical_oracle_ratio"]) < 1e-8,
                f"Independent replay travel-time aggregate drift in {cohort}")
        for mi, model in enumerate(MODELS):
            a = ablation["variants"][model]["cohorts"][cohort]
            result["ablation"][cohort][model] = {
                "velocity": bootstrap_ratio(a["per_record"], "learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s", BOOTSTRAP_SEED + 100 + ci * 10 + mi),
                "travel_time": bootstrap_ratio(a["per_record"], "learned_oracle_rmse_ms", "classical_oracle_rmse_ms", BOOTSTRAP_SEED + 200 + ci * 10 + mi),
                "flags": a["forward_threshold_exceedances"],
                "velocity_ratio_receipt": a["learned_to_classical_velocity_ratio"],
                "time_ratio_receipt": a["learned_to_classical_oracle_ratio"],
            }
            require(abs(result["ablation"][cohort][model]["velocity"]["ratio"] - a["learned_to_classical_velocity_ratio"]) < 1e-8,
                    f"Ablation velocity aggregate drift in {cohort}/{model}")
            require(abs(result["ablation"][cohort][model]["travel_time"]["ratio"] - a["learned_to_classical_oracle_ratio"]) < 1e-8,
                    f"Ablation travel-time aggregate drift in {cohort}/{model}")
    return result


def save_figure(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight", metadata={"Creator": "build_analysis.py"})
    fig.savefig(FIGURES / f"{stem}.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def draw_architecture() -> None:
    fig, ax = plt.subplots(figsize=(12, 4.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4.4)
    ax.axis("off")
    blocks = [
        (0.25, 2.15, 1.65, 1.35, "Observed picks\n$\\mathbf{t}$; rays $A$", "#e8edf0"),
        (2.25, 2.15, 1.85, 1.35, "Physics features\nbackprojected $r$\ncoverage $c$", "#d7e7ec"),
        (4.5, 2.15, 2.0, 1.35, "2-channel CNN\n24 filters; 3 residual\nblocks; GELU", "#dce8da"),
        (6.9, 2.15, 1.8, 1.35, "Bounded logit\nupdate about $v_0$\n$1400\u20134000$ m/s", "#f0e4d2"),
        (9.15, 2.15, 2.4, 1.35, "Velocity estimate\nheld against regularized\nray baseline", "#eadde7"),
    ]
    for x, y, w, h, label, color in blocks:
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=color, ec="#243746", lw=1.2, zorder=2))
        ax.text(x+w/2, y+h/2, label, ha="center", va="center", fontsize=10)
    for x1, x2 in ((1.9, 2.25), (4.1, 4.5), (6.5, 6.9), (8.7, 9.15)):
        ax.annotate("", (x2, 2.83), (x1, 2.83), arrowprops={"arrowstyle": "->", "lw": 1.5, "color": "#243746"})
    ax.text(6, 1.18, "Training only: velocity MSE + 0.1 × straight-ray time MSE; Adam, 40 epochs, seed 77213",
            ha="center", va="center", fontsize=10, color="#3b4b55")
    ax.annotate("", (5.5, 2.1), (5.5, 1.55), arrowprops={"arrowstyle": "->", "lw": 1.1, "color": "#586b76"})
    ax.text(6, 0.48, "Inference receives picks and geometry only. Synthetic truth is used for training and evaluation, never as an input.",
            ha="center", va="center", fontsize=9, color="#3b4b55")
    fig.tight_layout()
    save_figure(fig, "fig01-method-pipeline")


def draw_feature_example() -> None:
    sys.path.insert(0, str(ROOT / "data-pipeline"))
    import velocity_physics_refinement as physics  # noqa: PLC0415
    import velocity_validation as oracle  # noqa: PLC0415

    require(digest(ROOT / "data-pipeline" / "velocity_physics_refinement.py") == EXPECTED_TRAINING_CODE,
            "Feature implementation changed since the frozen run")
    require(digest(ROOT / "data-pipeline" / "velocity_validation.py") == EXPECTED_OPERATOR_CODE,
            "Operator implementation changed since the frozen run")
    ops = oracle.operators()
    cohort = physics.make_cohort("joint_ood", ops)
    require(cohort["manifest_sha256"] == json.loads((DATA / "primary-receipt.json").read_text(encoding="utf-8"))["cohorts"]["joint_ood"]["manifest_sha256"],
            "Regenerated illustrative cohort does not match the primary receipt")
    true_velocity = cohort["velocity"][0]
    features = cohort["features"][0]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.7), constrained_layout=True)
    images = [
        axes[0].imshow(true_velocity, origin="upper", extent=[0, 800, 800, 0], cmap="viridis", vmin=1400, vmax=4000),
        axes[1].imshow(features[0], origin="upper", extent=[0, 800, 800, 0], cmap="coolwarm"),
        axes[2].imshow(features[1], origin="upper", extent=[0, 800, 800, 0], cmap="magma", vmin=0, vmax=1),
    ]
    titles = ("Fault-family velocity truth", "Length-normalized residual feature", "Normalized ray coverage")
    cmaps = ("velocity (m/s)", "dimensionless", "dimensionless")
    for ax, image, title, label in zip(axes, images, titles, cmaps, strict=True):
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("x (m)")
        ax.set_ylabel("positive-down z (m)")
        fig.colorbar(image, ax=ax, shrink=0.82, label=label)
        ax.set_aspect("equal")
    save_figure(fig, "fig02-input-feature-example")


def draw_training(primary: dict, ablation: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.0), constrained_layout=True)
    histories = {
        "Both channels": primary["history"],
        "Residual only": ablation["variants"]["residual_only"]["history"],
        "Coverage only": ablation["variants"]["coverage_only"]["history"],
    }
    colors = {"Both channels": COLORS["full"], "Residual only": COLORS["residual_only"], "Coverage only": COLORS["coverage_only"]}
    for label, history in histories.items():
        epochs = [item["epoch"] for item in history]
        axes[0].plot(epochs, [item["train_objective"] for item in history], label=label, color=colors[label], lw=1.5)
        axes[1].plot(epochs, [item["validation_velocity_rmse_m_s"] for item in history], label=label, color=colors[label], lw=1.5)
    axes[0].set_ylabel("Normalized training objective")
    axes[1].set_ylabel("Validation velocity RMSE (m/s)")
    for ax in axes:
        ax.set_xlabel("Epoch")
        ax.grid(alpha=0.25)
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle("One fixed training seed; validation selects each checkpoint", fontsize=10)
    save_figure(fig, "fig03-training-history")


def draw_primary_ratios(analysis: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.5), constrained_layout=True, sharey=True)
    for ax, metric, title in zip(axes, ("velocity", "travel_time"), ("Velocity RMSE ratio", "$Q$-scored observed-pick RMSE ratio"), strict=True):
        for i, cohort in enumerate(COHORTS):
            v = analysis["primary"][cohort][metric]
            ax.errorbar(v["ratio"], i, xerr=[[v["ratio"]-v["ci95"][0]], [v["ci95"][1]-v["ratio"]]],
                        fmt="o", color="#315b72", capsize=3)
        ax.axvline(1, color="#a84135", ls="--", lw=1)
        ax.set_xscale("log")
        ax.set_title(title)
        ax.set_xlabel("Learned / regularized-ray RMSE, 95% case-bootstrap interval")
        ax.grid(axis="x", alpha=0.25, which="both")
    axes[0].set_yticks(range(len(COHORTS)), [COHORT_LABELS[c] for c in COHORTS])
    fig.suptitle("Primary frozen checkpoint; ratios above one favor the matched inverse", fontsize=10)
    save_figure(fig, "fig04-primary-heldout-ratios")


def draw_replay_sensitivity(analysis: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.5), constrained_layout=True, sharey=True)
    runs = (("primary", "Published checkpoint", "#315b72"),
            ("independent_replay", "Independent CUDA replay", "#b56c38"))
    offsets = {"primary": -0.12, "independent_replay": 0.12}
    for ax, metric, title in zip(axes, ("velocity", "travel_time"),
                                 ("Velocity RMSE ratio", "$Q$-scored observed-pick RMSE ratio"), strict=True):
        for key, label, color in runs:
            for i, cohort in enumerate(COHORTS):
                value = analysis[key][cohort][metric]
                ax.errorbar(value["ratio"], i + offsets[key],
                            xerr=[[value["ratio"] - value["ci95"][0]],
                                  [value["ci95"][1] - value["ratio"]]],
                            fmt="o", color=color, capsize=3, label=label if i == 0 else None)
        ax.axvline(1, color="#a84135", ls="--", lw=1)
        ax.set_xscale("log")
        ax.set_title(title)
        ax.set_xlabel("Learned / regularized-ray RMSE, 95% case-bootstrap interval")
        ax.grid(axis="x", alpha=0.25, which="both")
    axes[0].set_yticks(range(len(COHORTS)), [COHORT_LABELS[c] for c in COHORTS])
    axes[1].legend(frameon=False, fontsize=8)
    fig.suptitle("Same seed and cases; separate CUDA checkpoints", fontsize=10)
    save_figure(fig, "fig08-training-replay-sensitivity")


def draw_case_scatter(primary: dict) -> None:
    cohort = primary["cohorts"]["joint_ood"]["per_record"]
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.7), constrained_layout=True)
    series = (("learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s", "Velocity RMSE (m/s)"),
              ("learned_oracle_rmse_ms", "classical_oracle_rmse_ms", "$Q$-scored observed-pick RMSE (ms)"))
    for ax, (learn_key, classic_key, label) in zip(axes, series, strict=True):
        learned = np.asarray([r[learn_key] for r in cohort])
        classical = np.asarray([r[classic_key] for r in cohort])
        colors = ["#516b7b" if "fault" in r["id"] else "#c17b3a" for r in cohort]
        ax.scatter(classical, learned, c=colors, s=13, alpha=0.72, linewidths=0)
        limit = max(float(learned.max()), float(classical.max())) * 1.06
        ax.plot([0, limit], [0, limit], color="#a84135", ls="--", lw=1)
        ax.set_xlim(0, limit)
        ax.set_ylim(0, limit)
        ax.set_xlabel("Regularized ray inverse")
        ax.set_ylabel("Learned estimate")
        ax.set_title(label)
        ax.grid(alpha=0.2)
    axes[0].text(0.04, 0.96, "Fault", color="#516b7b", transform=axes[0].transAxes, va="top")
    axes[0].text(0.04, 0.88, "Salt", color="#c17b3a", transform=axes[0].transAxes, va="top")
    fig.suptitle("Every one of 160 joint-shift cases lies above the equality line", fontsize=10)
    save_figure(fig, "fig05-joint-shift-paired-errors")


def draw_ablation(analysis: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.8), constrained_layout=True, sharey=True)
    x = np.arange(len(COHORTS))
    offsets = {"full": -0.13, "residual_only": 0.0, "coverage_only": 0.13}
    for ax, metric, title in zip(axes, ("velocity", "travel_time"), ("Velocity RMSE ratio", "$Q$-scored observed-pick RMSE ratio"), strict=True):
        for model in MODELS:
            points, low, high = [], [], []
            for cohort in COHORTS:
                item = analysis["ablation"][cohort][model][metric]
                points.append(item["ratio"])
                low.append(item["ratio"] - item["ci95"][0])
                high.append(item["ci95"][1] - item["ratio"])
            ax.errorbar(x + offsets[model], points, yerr=[low, high], label=MODEL_LABELS[model],
                        fmt="o-", color=COLORS[model], capsize=2, lw=1.2, ms=4)
        ax.axhline(1, color="#a84135", ls="--", lw=1)
        ax.set_yscale("log")
        ax.set_xticks(x, [COHORT_LABELS[c] for c in COHORTS], rotation=25, ha="right")
        ax.set_title(title)
        ax.set_ylabel("Learned / regularized-ray RMSE")
        ax.grid(axis="y", alpha=0.25, which="both")
    axes[1].legend(frameon=False, fontsize=8)
    fig.suptitle("Post-hoc channel ablation on new test-cohort seeds; training seed is fixed", fontsize=10)
    save_figure(fig, "fig06-channel-ablation")


def draw_kernel_spectrum(analysis: dict) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.6), constrained_layout=True)
    for item, color in zip(analysis["resolution_kernel"], ("#315b72", "#b56c38", "#8a5b7d"), strict=True):
        values = np.asarray(item["positive_eigenvalues"], dtype=np.float64)
        values = values / values[0]
        ax.semilogy(np.arange(1, len(values) + 1), values, label=f"Layout {item['layout']}",
                    color=color, lw=1.7)
    ax.set_xlabel("Positive eigenvalue rank")
    ax.set_ylabel("Eigenvalue / largest eigenvalue")
    ax.set_title("Coverage-normalized ray kernel spectrum")
    ax.grid(alpha=0.25, which="both")
    ax.legend(frameon=False)
    save_figure(fig, "fig07-resolution-kernel-spectrum")


def fmt(value: float) -> str:
    return f"{value:.3f}"


def render_tables(primary: dict, ablation: dict, analysis: dict) -> None:
    lines = [
        r"\begin{table}[htbp]", r"\centering", r"\small",
        r"\caption{Frozen synthetic cohorts separate interpolation, family shift, acquisition shift, and their joint combination across the declared two-dimensional ray layouts.}",
        r"\label{tab:cohorts}", r"\begin{tabular}{lrrll}", r"\toprule",
        r"Cohort & $n$ & Seed base & Families & Acquisition layouts \\", r"\midrule",
        r"Training & 800 & 117001 & layered, lens, dipping & A, B \\",
        r"Validation & 160 & 127001 & layered, lens, dipping & A, B \\",
        r"In-distribution test & 160 & 137001 & layered, lens, dipping & A, B \\",
        r"Family-shift test & 80 & 147001 & fault, salt & A, B \\",
        r"Acquisition-shift test & 80 & 157001 & layered, lens, dipping & C \\",
        r"Joint-shift test & 160 & 167001 & fault, salt & C \\", r"\bottomrule", r"\end{tabular}", r"\end{table}", "",
        r"\begin{table}[htbp]", r"\centering", r"\small",
        r"\caption{The frozen learned model is compared with a validation-selected regularized ray inverse on identical held-out cases.}",
        r"\label{tab:primary}", r"\begin{tabular}{lrrrrr}", r"\toprule",
        r"Cohort & $n$ & Velocity ratio (95\% CI) & Time ratio (95\% CI) & Flags \\", r"\midrule",
    ]
    for cohort in COHORTS:
        p = primary["cohorts"][cohort]
        s = analysis["primary"][cohort]
        vr, tr = s["velocity"], s["travel_time"]
        lines.append(f"{COHORT_LABELS[cohort]} & {p['count']} & {fmt(vr['ratio'])} ({fmt(vr['ci95'][0])}, {fmt(vr['ci95'][1])}) & {fmt(tr['ratio'])} ({fmt(tr['ci95'][0])}, {fmt(tr['ci95'][1])}) & {p['forward_threshold_exceedances']} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", "",
              r"\begin{table}[htbp]", r"\centering", r"\scriptsize",
        r"\caption{Channel-ablation models evaluated on new test-cohort seeds retain larger errors than the matched inverse across every held-out synthetic cohort; the training seed is unchanged.}",
              r"\label{tab:ablation}", r"\begin{tabular}{llrrr}", r"\toprule",
              r"Model & Cohort & Velocity ratio (95\% CI) & Time ratio (95\% CI) & Flags \\", r"\midrule"]
    for cohort in COHORTS:
        for model in MODELS:
            a = ablation["variants"][model]["cohorts"][cohort]
            s = analysis["ablation"][cohort][model]
            vr, tr = s["velocity"], s["travel_time"]
            lines.append(f"{MODEL_LABELS[model]} & {COHORT_LABELS[cohort]} & {fmt(vr['ratio'])} ({fmt(vr['ci95'][0])}, {fmt(vr['ci95'][1])}) & {fmt(tr['ratio'])} ({fmt(tr['ci95'][0])}, {fmt(tr['ci95'][1])}) & {a['forward_threshold_exceedances']} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", "",
              r"\begin{table}[htbp]", r"\centering", r"\small",
              r"\caption{Model and solver settings define the trained convolutional estimate and validation-selected ray inverse used for every held-out synthetic cohort.}",
              r"\label{tab:parameters}", r"\begin{tabular}{ll}", r"\toprule", r"Quantity & Value \\", r"\midrule",
              r"Grid and domain & $16\times16$, $800\times800$ m, 50 m cells \\",
              r"Velocity bounds & 1400--4000 m/s \\",
              r"Training cases / validation cases & 800 / 160 \\",
              r"Optimizer / learning rate / epochs & Adam / 0.001 / 40 \\",
              r"Mini-batch / initialization seed & 64 / 77213 \\",
              r"Training objective scales & 400 m/s for velocity; 10 ms for travel time \\",
              r"Ray-inverse candidates / selected value & 1, 10, 100, 1000 / 100 \\",
              r"Held-out family / acquisition layouts & fault and salt / C \\",
              r"Primary selected epoch & 40 \\",
              f"Primary GPU training time & {primary['wall_seconds']:.2f} s " + chr(92) * 2,
              f"Ablation GPU training and scoring time & {ablation['wall_seconds']:.2f} s " + chr(92) * 2,
              r"\bottomrule", r"\end{tabular}", r"\end{table}", "",
              r"\clearpage",
              r"\begin{table}[htbp]", r"\centering", r"\small",
              r"\caption{Coverage and eigenvalue summaries quantify rank and angular support of each fixed straight-ray acquisition layout on the 16 by 16 grid.}",
              r"\label{tab:kernel-diagnostics}", r"\begin{tabular}{lrrrrrr}", r"\toprule",
              r"Layout & Rays & Supported cells & Rank & Support (\%) & Axial angles & Max gap ($^\circ$) \\", r"\midrule"]
    for item in analysis["resolution_kernel"]:
        lines.append(f"{item['layout']} & {item['ray_count']} & {item['supported_cells']} & {item['numerical_rank']} & "
                     f"{100*item['supported_fraction']:.1f} & {item['unique_axial_angles']} & "
                     f"{item['maximum_axial_angle_gap_deg']:.2f} " + chr(92) * 2)
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (GENERATED / "tables.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_replay_table(analysis: dict) -> None:
    lines = [
        r"\begin{table}[htbp]", r"\centering", r"\small",
        r"\caption{A second CUDA training uses the same source, seed, and case manifests but a distinct checkpoint; both runs retain the negative comparison.}",
        r"\label{tab:replay-sensitivity}", r"\begin{tabular}{lrrr}", r"\toprule",
        r"Cohort & Velocity ratio, first / replay & Time ratio, first / replay & Flags, first / replay \\", r"\midrule",
    ]
    for cohort in COHORTS:
        first = analysis["primary"][cohort]
        second = analysis["independent_replay"][cohort]
        lines.append(f"{COHORT_LABELS[cohort]} & {fmt(first['velocity']['ratio'])} / {fmt(second['velocity']['ratio'])} & "
                     f"{fmt(first['travel_time']['ratio'])} / {fmt(second['travel_time']['ratio'])} & "
                     f"{first['flags']}/{second['flags']} " + chr(92) * 2)
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (GENERATED / "replay-table.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    GENERATED.mkdir(parents=True, exist_ok=True)
    primary, ablation, replay, identities = load_evidence()
    analysis = summaries(primary, ablation, replay)
    analysis["resolution_kernel"] = resolution_diagnostics()
    analysis.update(identities)
    (GENERATED / "analysis.json").write_text(json.dumps(analysis, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    draw_architecture()
    draw_feature_example()
    draw_training(primary, ablation)
    draw_primary_ratios(analysis)
    draw_replay_sensitivity(analysis)
    draw_case_scatter(primary)
    draw_ablation(analysis)
    draw_kernel_spectrum(analysis)
    render_tables(primary, ablation, analysis)
    render_replay_table(analysis)
    print(json.dumps({"status": "verified", "figures": 8, "tables": 6,
                      "primary_receipt": identities["receipt_sha256"]["primary-receipt.json"],
                      "independent_replay_receipt": identities["replay_sha256"]["independent-replay-receipt.json"],
                      "ablation_receipt": identities["receipt_sha256"]["ablation-receipt.json"],
                      "joint_primary": analysis["primary"]["joint_ood"],
                      "joint_independent_replay": analysis["independent_replay"]["joint_ood"],
                      "outputs": [str(p.relative_to(PAPER)) for p in sorted(FIGURES.glob("*.pdf"))]}, indent=2))


if __name__ == "__main__":
    main()
