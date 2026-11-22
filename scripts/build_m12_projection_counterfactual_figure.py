#!/usr/bin/env python3
"""Render a paired projected-versus-raw M12 counterfactual figure and manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/derived/v2/models/m12-projection-counterfactual-20261112/counterfactual-analysis.json"
FIGURES = ROOT / "manuscripts/m12-nullspace-refinement-v0.01/figures"
COHORTS = (
    ("id_test", "In distribution"),
    ("family_only", "Family shift"),
    ("acquisition_only", "Acquisition shift"),
    ("joint_ood", "Joint shift"),
)
METRICS = (
    ("projected_to_raw_velocity", "Velocity RMSE"),
    ("projected_to_raw_oracle_time", "Independent travel-time RMSE"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    result = json.loads(DATA.read_text(encoding="utf-8"))
    if result.get("schema") != "caos-geophysics.m12-projection-counterfactual-analysis/v1":
        raise ValueError("Unsupported counterfactual analysis schema")
    if result.get("scientific_acceptance") is not False:
        raise ValueError("Exploratory counterfactual must not claim scientific acceptance")
    if tuple(result["cohorts"]) != tuple(name for name, _ in COHORTS):
        raise ValueError("Counterfactual cohort inventory/order changed")

    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    })
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.7), sharey=True,
                             gridspec_kw={"wspace": 0.12})
    labels = [label for _, label in COHORTS]
    colors = {"projection": "#167B83", "raw": "#C65D32"}
    for ax, (metric, title) in zip(axes, METRICS):
        ax.axvspan(0.65, 1.0, color=colors["projection"], alpha=0.075, zorder=0)
        ax.axvspan(1.0, 2.15, color=colors["raw"], alpha=0.055, zorder=0)
        ax.axvline(1.0, color="#344054", linewidth=1.1, linestyle=(0, (4, 3)), zorder=1)
        for index, (name, _) in enumerate(COHORTS):
            summary = result["cohorts"][name]["paired_projection_effect"][metric]
            estimate = summary["estimate_ratio_of_mean_errors"]
            low, high = summary["paired_case_bootstrap_95_percentile_interval"]
            color = colors["projection"] if estimate < 1.0 else colors["raw"]
            ax.errorbar(estimate, index, xerr=[[estimate - low], [high - estimate]],
                        fmt="o", markersize=6, markerfacecolor=color, markeredgecolor="white",
                        markeredgewidth=0.9, ecolor=color, elinewidth=1.6, capsize=3.2,
                        zorder=3)
        ax.set_title(title, loc="left", fontweight="bold", pad=10)
        ax.set_xlabel("Ratio of mean per-case errors (projected / raw CNN)")
        ax.set_xlim(0.65, 2.15)
        ax.set_xticks([0.75, 1.0, 1.25, 1.5, 1.75, 2.0])
        ax.grid(axis="x", color="#D9DEE5", linewidth=0.7, zorder=0)
        ax.set_axisbelow(True)
    axes[0].set_yticks(np.arange(len(COHORTS)), labels)
    axes[0].invert_yaxis()
    fig.suptitle("Paired same-case effect of null-space projection", x=0.085,
                 y=0.985, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.085, 0.915,
             "Point estimates and 95% paired case-bootstrap intervals; both methods use identical cases and checkpoint.",
             ha="left", va="center", fontsize=8.5, color="#475467")
    fig.text(0.5, 0.035,
             "Below 1: projection lowers error     •     Above 1: raw CNN lowers error     •     Dashed line: equal mean error",
             ha="center", fontsize=8, color="#344054")
    fig.subplots_adjust(left=0.17, right=0.985, top=0.84, bottom=0.18)

    outputs = []
    for name, fmt in (("m12-projection-counterfactual.png", "png"),
                      ("m12-projection-counterfactual.pdf", "pdf")):
        path = FIGURES / name
        metadata = {"Creator": "CAOS Geophysics counterfactual figure builder"}
        if fmt == "png":
            metadata = {"Software": "Matplotlib; CAOS Geophysics"}
        fig.savefig(path, format=fmt, dpi=280 if fmt == "png" else None,
                    bbox_inches="tight", metadata=metadata)
        outputs.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    plt.close(fig)

    table_dir = ROOT / "manuscripts/m12-nullspace-refinement-v0.01/generated"
    table_dir.mkdir(parents=True, exist_ok=True)
    table_rows = []
    for name, label in COHORTS:
        cohort = result["cohorts"][name]
        velocity = cohort["paired_projection_effect"]["projected_to_raw_velocity"]
        oracle = cohort["paired_projection_effect"]["projected_to_raw_oracle_time"]
        vlo, vhi = velocity["paired_case_bootstrap_95_percentile_interval"]
        tlo, thi = oracle["paired_case_bootstrap_95_percentile_interval"]
        table_rows.append(
            f"{label} & {cohort['count']} & {velocity['estimate_ratio_of_mean_errors']:.4f} "
            f"[{vlo:.4f}, {vhi:.4f}] & {velocity['cases_projected_error_lower']}/{cohort['count']} "
            f"& {oracle['estimate_ratio_of_mean_errors']:.4f} [{tlo:.4f}, {thi:.4f}] "
            f"& {oracle['cases_projected_error_lower']}/{cohort['count']} \\\\"
        )
    table = "\n".join([
        r"\begin{table}[htbp]", r"\centering", r"\scriptsize",
        r"\caption{Same-case projected-to-raw CNN error ratios and paired intervals quantify the correction trade-off across four frozen synthetic cohorts.}",
        r"\label{tab:projection-counterfactual}",
        r"\begin{tabular}{lrrrrr}", r"\toprule",
        r"Cohort & $n$ & Velocity ratio [95\% CI] & Lower & Oracle-time ratio [95\% CI] & Lower \\",
        r"\midrule", *table_rows, r"\bottomrule", r"\end{tabular}", r"\end{table}",
    ]) + "\n"
    table_path = table_dir / "projection-counterfactual-table.tex"
    table_path.write_text(table, encoding="utf-8")
    table_record = {"path": table_path.relative_to(ROOT).as_posix(),
                    "bytes": table_path.stat().st_size, "sha256": sha256(table_path)}

    manifest = {
        "schema": "caos-geophysics.m12-projection-counterfactual-figure/v1",
        "analysis_path": DATA.relative_to(ROOT).as_posix(),
        "analysis_sha256": sha256(DATA),
        "builder_path": Path(__file__).relative_to(ROOT).as_posix(),
        "builder_sha256": sha256(Path(__file__).resolve()),
        "cohort_counts": {name: result["cohorts"][name]["count"] for name, _ in COHORTS},
        "scientific_acceptance": False,
        "figures": outputs,
        "tables": [table_record],
        "interpretation": "Ratios are projected/raw CNN mean per-case RMSE on identical held-out cases; intervals resample cases within each fixed synthetic cohort.",
    }
    manifest_path = FIGURES / "m12-projection-counterfactual-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": manifest_path.relative_to(ROOT).as_posix(),
                      "figures": outputs}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
