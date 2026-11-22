"""Build case-level manuscript figures from the frozen M12 v1.1 receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "data/derived/v2/models/m12-nullspace-v1_1/receipt.json"
EXPECTED_RECEIPT_SHA256 = "30df0c2ad495bd850dda602b1c96725be8290dd086119fb3e8e75355fe9dea22"
DEFAULT_OUTPUT = ROOT / "manuscripts/m12-nullspace-refinement-v0.01/figures"
BOOTSTRAP = ROOT / "docs/validation/m12-nullspace-v1_1-bootstrap-2026-10-30.json"
COHORTS = (
    ("id_test", "In-distribution", "#176b87"),
    ("family_only", "Family shift", "#c66b22"),
    ("acquisition_only", "Acquisition shift", "#4d7d42"),
    ("joint_ood", "Joint shift", "#8b4f83"),
)
METRICS = (
    ("Velocity RMSE", "learned_velocity_rmse_m_s", "classical_velocity_rmse_m_s"),
    ("Independent travel-time RMSE", "learned_oracle_rmse_ms", "classical_oracle_rmse_ms"),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_paired_receipt(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    digest = sha256(raw)
    if digest != EXPECTED_RECEIPT_SHA256:
        raise ValueError(f"Receipt digest mismatch: {digest}")
    receipt = json.loads(raw)
    if receipt.get("schema") != "caos-geophysics.m12-nullspace-residual/v1.1":
        raise ValueError("Unsupported receipt schema")
    if receipt.get("scientific_acceptance") is not False:
        raise ValueError("The frozen receipt must retain its non-acceptance status")
    for key, _, _ in COHORTS:
        cohort = receipt["cohorts"][key]
        rows = cohort["per_record"]
        ids = [row.get("id") for row in rows]
        if len(rows) != cohort["count"] or len(set(ids)) != len(ids) or any(not x for x in ids):
            raise ValueError(f"{key}: missing, duplicate, or count-mismatched case records")
        for label, learned_key, classical_key in METRICS:
            learned = np.asarray([row[learned_key] for row in rows], dtype=np.float64)
            classical = np.asarray([row[classical_key] for row in rows], dtype=np.float64)
            if (not np.isfinite(learned).all() or not np.isfinite(classical).all()
                    or np.any(learned < 0) or np.any(classical <= 0)):
                raise ValueError(f"{key}/{label}: invalid case-level RMSE values")
            if np.any(learned <= 0):
                raise ValueError(f"{key}/{label}: log-ratio figure requires positive numerator RMSE")
    if sum(receipt["cohorts"][key]["count"] for key, _, _ in COHORTS) != 480:
        raise ValueError("Frozen v1.1 held-out case total changed")
    return receipt, digest


def arrays(receipt: dict, cohort_key: str, learned_key: str, classical_key: str) -> tuple[np.ndarray, np.ndarray]:
    rows = receipt["cohorts"][cohort_key]["per_record"]
    learned = np.asarray([row[learned_key] for row in rows], dtype=np.float64)
    classical = np.asarray([row[classical_key] for row in rows], dtype=np.float64)
    return learned, classical


def plot_ecdf(receipt: dict, output: Path) -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "axes.edgecolor": "#52616b",
        "axes.linewidth": 0.8,
        "xtick.color": "#34444f",
        "ytick.color": "#34444f",
        "text.color": "#17252e",
        "figure.facecolor": "white",
        "axes.facecolor": "#fbfcfd",
        "savefig.facecolor": "white",
    })
    fig, axes = plt.subplots(2, 4, figsize=(14.2, 7.25), constrained_layout=True, sharey="row")
    for row_index, (metric, learned_key, classical_key) in enumerate(METRICS):
        all_log_ratios = []
        for cohort_key, _, _ in COHORTS:
            learned, classical = arrays(receipt, cohort_key, learned_key, classical_key)
            all_log_ratios.extend(np.log(learned / classical).tolist())
        lo = float(np.floor(min(all_log_ratios) * 2) / 2)
        hi = float(np.ceil(max(all_log_ratios) * 2) / 2)
        if lo == hi:
            lo, hi = lo - 0.5, hi + 0.5
        for col_index, (cohort_key, cohort_title, color) in enumerate(COHORTS):
            ax = axes[row_index, col_index]
            learned, classical = arrays(receipt, cohort_key, learned_key, classical_key)
            log_ratio = np.sort(np.log(learned / classical))
            ecdf = np.arange(1, len(log_ratio) + 1) / len(log_ratio)
            ax.step(log_ratio, ecdf, where="post", color=color, linewidth=2.0)
            ax.axvline(0.0, color="#202a30", linewidth=1.0, linestyle=(0, (4, 3)))
            share_improved = float(np.mean(log_ratio < 0.0))
            ax.scatter([0.0], [share_improved], s=20, color="#202a30", zorder=4)
            ax.set_xlim(lo, hi)
            ax.set_ylim(0.0, 1.02)
            ax.grid(axis="both", color="#d9e0e4", linewidth=0.65, alpha=0.8)
            ax.set_title(f"{cohort_title}  ·  n={len(log_ratio)}", loc="left", pad=9, fontweight="semibold")
            if col_index == 0:
                ax.set_ylabel(f"{metric}\nEmpirical cumulative proportion")
            if row_index == 1:
                ax.set_xlabel("log(projected / L2 per-case RMSE)")
            ax.text(0.97, 0.06, f"{share_improved:.1%} below 1", transform=ax.transAxes,
                    ha="right", va="bottom", fontsize=8, color="#263943",
                    bbox={"boxstyle": "round,pad=0.28", "facecolor": "white", "edgecolor": "#cbd5da"})
    fig.suptitle("Paired case errors across the four held-out cohorts", x=0.02, ha="left", fontsize=15, fontweight="bold")
    stem = "m12-nullspace-paired-error-ecdf"
    fig.savefig(output / f"{stem}.png", dpi=240, bbox_inches="tight", metadata={"Software": "Matplotlib"})
    fig.savefig(output / f"{stem}.pdf", bbox_inches="tight", metadata={"Creator": "build_m12_nullspace_figures.py", "CreationDate": None, "ModDate": None})
    plt.close(fig)


def plot_tradeoffs(receipt: dict, output: Path) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(13.8, 4.1), constrained_layout=True)
    bounds: list[float] = []
    cohort_data = []
    for cohort_key, _, _ in COHORTS:
        v_l, v_c = arrays(receipt, cohort_key, METRICS[0][1], METRICS[0][2])
        t_l, t_c = arrays(receipt, cohort_key, METRICS[1][1], METRICS[1][2])
        vx, ty = v_l / v_c, t_l / t_c
        cohort_data.append((vx, ty))
        bounds.extend(vx.tolist())
        bounds.extend(ty.tolist())
    low = max(float(np.min(bounds)) * 0.75, 1e-3)
    high = float(np.max(bounds)) * 1.25
    for ax, (cohort_key, title, color), (vx, ty) in zip(axes, COHORTS, cohort_data):
        improved_both = (vx < 1.0) & (ty < 1.0)
        ax.scatter(vx[~improved_both], ty[~improved_both], s=19, alpha=0.52, color="#91a0a8",
                   edgecolors="none", label="At least one metric not lower")
        ax.scatter(vx[improved_both], ty[improved_both], s=20, alpha=0.76, color=color,
                   edgecolors="white", linewidths=0.35, label="Both lower")
        ax.axvline(1.0, color="#263943", linestyle=(0, (4, 3)), linewidth=0.9)
        ax.axhline(1.0, color="#263943", linestyle=(0, (4, 3)), linewidth=0.9)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(low, high)
        ax.set_ylim(low, high)
        ax.grid(which="both", color="#d9e0e4", linewidth=0.6, alpha=0.75)
        ax.set_title(f"{title} · n={len(vx)}", loc="left", fontsize=10, fontweight="semibold")
        ax.set_xlabel("Velocity RMSE ratio")
        if ax is axes[0]:
            ax.set_ylabel("Independent travel-time RMSE ratio")
        count_both = int(improved_both.sum())
        ax.text(0.04, 0.96, f"both lower: {count_both}/{len(vx)}", transform=ax.transAxes,
                ha="left", va="top", fontsize=8,
                bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#cbd5da"})
    axes[-1].legend(loc="lower right", fontsize=7, frameon=True, framealpha=0.95)
    fig.suptitle("Per-case trade-off: truth-space and independent data-space error", x=0.02, ha="left",
                 fontsize=14, fontweight="bold")
    stem = "m12-nullspace-case-error-tradeoffs"
    fig.savefig(output / f"{stem}.png", dpi=240, bbox_inches="tight", metadata={"Software": "Matplotlib"})
    fig.savefig(output / f"{stem}.pdf", bbox_inches="tight", metadata={"Creator": "build_m12_nullspace_figures.py", "CreationDate": None, "ModDate": None})
    plt.close(fig)


def plot_aggregate_intervals(receipt: dict, output: Path) -> str:
    raw = BOOTSTRAP.read_bytes()
    bootstrap_hash = sha256(raw)
    report = json.loads(raw)
    if report.get("receipt_sha256") != EXPECTED_RECEIPT_SHA256:
        raise ValueError("Bootstrap report is not tied to the frozen receipt")
    if report.get("schema") != "caos-geophysics.m12-nullspace-v1.1-paired-bootstrap/v1":
        raise ValueError("Unsupported bootstrap summary schema")
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 5.2), sharey=True, constrained_layout=True)
    metric_specs = (
        ("velocity_rmse_m_s", "learned_to_classical_velocity_ratio", "Velocity RMSE ratio"),
        ("oracle_time_rmse_ms", "learned_to_classical_oracle_ratio", "Independent travel-time RMSE ratio"),
    )
    y = np.arange(len(COHORTS))
    for ax, (metric_key, receipt_ratio_key, label) in zip(axes, metric_specs):
        for i, (cohort_key, cohort_label, color) in enumerate(COHORTS):
            stats = report["cohorts"][cohort_key][metric_key]
            point = float(receipt["cohorts"][cohort_key][receipt_ratio_key])
            if not np.isclose(point, stats["observed_ratio_of_means"], rtol=1e-12, atol=1e-14):
                raise ValueError(f"Bootstrap point estimate disagrees with receipt: {cohort_key}/{metric_key}")
            low, high = map(float, stats["percentile_95_interval"])
            ax.errorbar(point, y[i], xerr=[[point - low], [high - point]], fmt="o", color=color,
                        ecolor=color, capsize=3.2, markersize=6, linewidth=1.5)
        ax.axvline(1.0, color="#263943", linestyle=(0, (4, 3)), linewidth=0.9)
        ax.set_xscale("log")
        ax.set_xlim(0.74, 1.02)
        ticks = [0.75, 0.80, 0.85, 0.90, 0.95, 1.00]
        ax.set_xticks(ticks, [f"{value:.2f}" for value in ticks])
        ax.set_yticks(y, [title for _, title, _ in COHORTS])
        ax.invert_yaxis()
        ax.grid(axis="x", which="both", color="#d9e0e4", linewidth=0.65)
        ax.set_xlabel("Projected / straight-ray L2 RMSE")
        ax.set_title(label, loc="left", fontweight="semibold")
    fig.suptitle("Aggregate paired-case ratios with within-cohort bootstrap intervals", x=0.02,
                 ha="left", fontsize=13, fontweight="bold")
    stem = "m12-nullspace-aggregate-ratio-intervals"
    fig.savefig(output / f"{stem}.png", dpi=240, bbox_inches="tight", metadata={"Software": "Matplotlib"})
    fig.savefig(output / f"{stem}.pdf", bbox_inches="tight", metadata={"Creator": "build_m12_nullspace_figures.py", "CreationDate": None, "ModDate": None})
    plt.close(fig)
    return bootstrap_hash


def plot_calibration_selection(receipt: dict, output: Path) -> None:
    grid = receipt["refinement"]["alpha_selection"]["grid"]
    alpha = np.asarray(sorted(float(k) for k in grid), dtype=np.float64)
    velocity = np.asarray([grid[str(a)]["velocity_ratio"] for a in alpha], dtype=np.float64)
    travel = np.asarray([grid[str(a)]["oracle_time_ratio"] for a in alpha], dtype=np.float64)
    selected = float(receipt["refinement"]["alpha_selection"]["selected_alpha"])
    if not np.any(np.isclose(alpha, selected)):
        raise ValueError("Selected alpha is absent from the calibration grid")
    fig, ax = plt.subplots(figsize=(8.4, 4.6), constrained_layout=True)
    ax.plot(alpha, velocity, marker="o", markersize=5, linewidth=2.1, color="#176b87", label="Velocity RMSE ratio")
    ax.plot(alpha, travel, marker="s", markersize=4.5, linewidth=2.1, color="#c66b22", label="Independent travel-time RMSE ratio")
    ax.axhline(1.0, color="#263943", linestyle=(0, (4, 3)), linewidth=1.0, label="Straight-ray L2 baseline")
    ax.axvline(selected, color="#4d7d42", linestyle=(0, (2, 2)), linewidth=1.2, label=f"Selected α={selected:g}")
    ax.scatter([selected, selected], [velocity[np.flatnonzero(np.isclose(alpha, selected))[0]],
                                      travel[np.flatnonzero(np.isclose(alpha, selected))[0]]],
               s=62, facecolor="white", edgecolor="#263943", linewidth=1.3, zorder=5)
    ax.set_xlabel("Null-space correction scale α")
    ax.set_ylabel("Calibration RMSE ratio")
    ax.set_xlim(float(alpha.min()) - 0.08, float(alpha.max()) + 0.08)
    ax.set_ylim(0.72, 1.035)
    ax.set_xticks(alpha)
    ax.grid(color="#d9e0e4", linewidth=0.7)
    ax.legend(frameon=True, framealpha=0.96, ncol=2, loc="lower center", fontsize=8)
    ax.set_title("Calibration-only selection; test cohorts do not choose α", loc="left", fontweight="bold")
    stem = "m12-nullspace-calibration-alpha-selection"
    fig.savefig(output / f"{stem}.png", dpi=240, bbox_inches="tight", metadata={"Software": "Matplotlib"})
    fig.savefig(output / f"{stem}.pdf", bbox_inches="tight", metadata={"Creator": "build_m12_nullspace_figures.py", "CreationDate": None, "ModDate": None})
    plt.close(fig)


def plot_projection_diagnostics(receipt: dict, output: Path) -> None:
    configs: dict[str, dict] = {}
    for cohort_key, _, _ in COHORTS:
        for acquisition, diag in receipt["projection_diagnostics"][cohort_key].items():
            current = configs.setdefault(acquisition, {
                "rank": diag["rank"], "nullity": diag["nullity"], "basis_residual": 0.0,
                "limit": 0.0, "projected_residual": 0.0, "clipped_fraction": 0.0,
            })
            if current["rank"] != diag["rank"] or current["nullity"] != diag["nullity"]:
                raise ValueError(f"Inconsistent SVD dimensions for acquisition {acquisition}")
            current["basis_residual"] = max(current["basis_residual"], diag["max_abs_A_times_basis"])
            current["limit"] = max(current["limit"], diag["residual_limit"])
            current["projected_residual"] = max(current["projected_residual"], diag["max_abs_A_projected_correction"])
            current["clipped_fraction"] = max(current["clipped_fraction"], diag["clipped_fraction"])
    keys = sorted(configs)
    x = np.arange(len(keys))
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.4), constrained_layout=True)
    basis = [configs[k]["basis_residual"] for k in keys]
    projected = [configs[k]["projected_residual"] for k in keys]
    limit = [configs[k]["limit"] for k in keys]
    axes[0].scatter(x, basis, s=62, color="#176b87", zorder=3, label="max |A N|")
    axes[0].scatter(x, limit, s=50, marker="_", linewidths=3, color="#bd4b3f", zorder=3, label="Recorded residual limit")
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Absolute matrix residual")
    axes[0].set_title("Orthonormal null-space basis", loc="left", fontweight="semibold")
    axes[0].legend(fontsize=8)
    axes[1].scatter(x, projected, s=62, color="#4d7d42", zorder=3, label="max |A Pₙ δs|")
    axes[1].set_yscale("log")
    axes[1].set_ylabel("Absolute projected-correction residual")
    axes[1].set_title("Pre-clipping correction", loc="left", fontweight="semibold")
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.set_xticks(x, [f"{k}\nrank {configs[k]['rank']}, nullity {configs[k]['nullity']}" for k in keys])
        ax.grid(axis="y", which="major", color="#d9e0e4", linewidth=0.7)
        ax.minorticks_off()
    if any(configs[k]["clipped_fraction"] != 0 for k in keys):
        raise ValueError("Unexpected physical-bound clipping in frozen projection diagnostics")
    fig.suptitle("Numerical projection checks by distinct acquisition geometry", x=0.02, ha="left",
                 fontsize=12.5, fontweight="bold")
    stem = "m12-nullspace-projection-diagnostics"
    fig.savefig(output / f"{stem}.png", dpi=240, bbox_inches="tight", metadata={"Software": "Matplotlib"})
    fig.savefig(output / f"{stem}.pdf", bbox_inches="tight", metadata={"Creator": "build_m12_nullspace_figures.py", "CreationDate": None, "ModDate": None})
    plt.close(fig)


def plot_subgroup_ratios(receipt: dict, output: Path) -> None:
    subgroup_types = (("per_family", "Model family"), ("per_acquisition", "Acquisition"))
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 7.4), constrained_layout=True)
    cohort_offsets = np.linspace(-0.22, 0.22, len(COHORTS))
    cohort_colors = {key: color for key, _, color in COHORTS}
    all_labels: list[str] = []
    group_rows: list[tuple[str, str, dict[str, list[tuple[float, str]]]]] = []
    for nested_key, section_title in subgroup_types:
        names = sorted({name for cohort_key, _, _ in COHORTS
                        for name in receipt["cohorts"][cohort_key].get(nested_key, {})})
        for name in names:
            values: dict[str, list[tuple[float, str]]] = {"velocity": [], "travel": []}
            for cohort_key, _, _ in COHORTS:
                subgroup = receipt["cohorts"][cohort_key].get(nested_key, {}).get(name)
                if subgroup is None:
                    continue
                values["velocity"].append((subgroup["learned_velocity_rmse_m_s"] / subgroup["classical_velocity_rmse_m_s"], cohort_key))
                values["travel"].append((subgroup["learned_oracle_rmse_ms"] / subgroup["classical_oracle_rmse_ms"], cohort_key))
            group_rows.append((section_title, name, values))
            all_labels.append(f"{section_title}: {name}")
    ybase = np.arange(len(group_rows))
    for ax, metric_key, title in zip(
            axes, ("velocity", "travel"), ("Velocity RMSE ratio", "Independent travel-time RMSE ratio")):
        for y, (_, _, values) in zip(ybase, group_rows):
            for offset, (cohort_key, _, _) in zip(cohort_offsets, COHORTS):
                match = [v for v, c in values[metric_key] if c == cohort_key]
                if match:
                    ax.scatter(match[0], y + offset, color=cohort_colors[cohort_key], s=30, alpha=0.88,
                               edgecolors="white", linewidths=0.35, zorder=3)
        ax.axvline(1.0, color="#263943", linestyle=(0, (4, 3)), linewidth=0.95)
        all_ratios = [value for _, _, values in group_rows for value, _ in values[metric_key]]
        ax.set_xlim(min(all_ratios) - (max(all_ratios) - min(all_ratios)) * 0.1,
                    max(all_ratios) + (max(all_ratios) - min(all_ratios)) * 0.1)
        ax.set_yticks(ybase, all_labels)
        ax.invert_yaxis()
        ax.grid(axis="x", which="both", color="#d9e0e4", linewidth=0.65)
        ax.set_title(title, loc="left", fontweight="semibold")
        ax.set_xlabel("Subgroup projected / L2 RMSE")
    handles = [plt.Line2D([0], [0], marker="o", linestyle="", markersize=6, color=color, label=title)
               for key, title, color in COHORTS]
    axes[-1].legend(handles=handles, loc="lower right", fontsize=7.5, frameon=True)
    fig.suptitle("Receipt subgroup summaries across generator families and acquisitions", x=0.02, ha="left",
                 fontsize=13, fontweight="bold")
    stem = "m12-nullspace-subgroup-ratios"
    fig.savefig(output / f"{stem}.png", dpi=240, bbox_inches="tight", metadata={"Software": "Matplotlib"})
    fig.savefig(output / f"{stem}.pdf", bbox_inches="tight", metadata={"Creator": "build_m12_nullspace_figures.py", "CreationDate": None, "ModDate": None})
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt, receipt_hash = load_paired_receipt(RECEIPT)
    out = args.output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    plot_ecdf(receipt, out)
    plot_tradeoffs(receipt, out)
    bootstrap_hash = plot_aggregate_intervals(receipt, out)
    plot_calibration_selection(receipt, out)
    plot_projection_diagnostics(receipt, out)
    plot_subgroup_ratios(receipt, out)
    script_hash = sha256(Path(__file__).read_bytes())
    figure_stems = (
        "m12-nullspace-paired-error-ecdf", "m12-nullspace-case-error-tradeoffs",
        "m12-nullspace-aggregate-ratio-intervals", "m12-nullspace-calibration-alpha-selection",
        "m12-nullspace-projection-diagnostics", "m12-nullspace-subgroup-ratios",
    )
    files = [out / f"{stem}.{extension}" for stem in figure_stems for extension in ("png", "pdf")]
    manifest = {
        "schema": "caos-geophysics.m12-nullspace-figures/v1",
        "receipt_path": RECEIPT.relative_to(ROOT).as_posix(),
        "receipt_sha256": receipt_hash,
        "bootstrap_summary_path": BOOTSTRAP.relative_to(ROOT).as_posix(),
        "bootstrap_summary_sha256": bootstrap_hash,
        "script_path": Path(__file__).relative_to(ROOT).as_posix(),
        "script_sha256": script_hash,
        "cohort_counts": {key: receipt["cohorts"][key]["count"] for key, _, _ in COHORTS},
        "scientific_acceptance": False,
        "figures": [
            {"path": p.name, "bytes": p.stat().st_size, "sha256": sha256(p.read_bytes())}
            for p in files
        ],
        "limitations": [
            "Figures describe case-level metrics in the frozen synthetic receipt.",
            "The receipt does not contain raw generated input arrays or the source checkpoint required for a full solver replay.",
            "These figures do not establish field accuracy or geological recovery.",
        ],
    }
    (out / "figure-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
