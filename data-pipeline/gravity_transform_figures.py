"""Publication-scale local diagnostic maps; no protected field-data publication."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np


def render_diagnostics(result, directory):
    """Export light/dark SVG and PNG with physical units and explicit masking."""
    directory = Path(directory)
    geometry = result["geometry"]
    source_kind = result["original_correction_result"]["dataset"]["metadata"]["source_kind"]
    source_label = (
        "Authored synthetic control - not measured field data"
        if source_kind == "synthetic_control"
        else "User-declared eligible input - private local diagnostic"
    )
    xy = np.array([geometry["easting_m"], geometry["northing_m"]]) / 1000
    observed = np.array(result["stations"]["observed_mgal"])
    residual = np.array(result["stations"]["signed_predicted_minus_observed_mgal"], dtype=float)
    partition = np.array(result["split"]["partition"])
    grids = result["grids"]
    selected = result["selection"]["height_m"]
    grid = next((g for g in grids if g["height_m"] == selected), grids[0])
    extent = [
        result["axes"]["easting_m"][0] / 1000,
        result["axes"]["easting_m"][-1] / 1000,
        result["axes"]["northing_m"][0] / 1000,
        result["axes"]["northing_m"][-1] / 1000,
    ]
    covered = np.array(grid["covered"]).reshape(grid["shape"])
    prediction = np.array(grid["predicted_mgal"], dtype=float).reshape(grid["shape"])
    sigma = np.array(grid["conditional_sigma_mgal"], dtype=float).reshape(grid["shape"])
    amplitude = max(float(np.nanmax(np.abs(observed))), float(np.nanmax(np.abs(prediction))), 1e-9)
    norm = TwoSlopeNorm(vmin=-amplitude, vcenter=0, vmax=amplitude)
    label = "Selected" if selected is not None else "Diagnostic only: precision ceiling unmet"
    for theme, background, foreground, muted in (
        ("light", "#f8fafc", "#132239", "#d7e1ec"),
        ("dark", "#101b2c", "#e7edf7", "#314258"),
    ):
        style = {
            "figure.facecolor": background,
            "axes.facecolor": muted,
            "text.color": foreground,
            "axes.labelcolor": foreground,
            "axes.edgecolor": foreground,
            "xtick.color": foreground,
            "ytick.color": foreground,
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "svg.fonttype": "none",
            "svg.hashsalt": "m01-transform",
            "savefig.facecolor": background,
        }
        with plt.rc_context(style):
            fig, axes = plt.subplots(2, 2, figsize=(15, 11), layout="constrained")
            fig.suptitle(
                "M01 local harmonic transform - original stations and derived layers\n" + source_label, fontsize=15
            )
            ax = axes[0, 0]
            artist = ax.scatter(*xy, c=observed, s=24, cmap="RdBu_r", norm=norm)
            for name, marker in (("holdout", "s"), ("masked", "x")):
                keep = partition == name
                ax.scatter(
                    *xy[:, keep],
                    facecolors="none" if marker == "s" else foreground,
                    edgecolors=foreground if marker == "s" else None,
                    marker=marker,
                    s=54,
                    linewidths=1,
                    label=name,
                )
            ax.legend(loc="lower right", framealpha=0.8, facecolor=background, labelcolor=foreground)
            ax.set_title("Original disturbance; independent blocked holdout")
            fig.colorbar(artist, ax=ax, label="Down-positive disturbance (mGal)")
            ax = axes[0, 1]
            artist = ax.imshow(
                prediction, origin="lower", extent=extent, cmap="RdBu_r", norm=norm, interpolation="nearest"
            )
            ax.set_title(f"{label}: ellipsoidal height {grid['height_m']:g} m")
            fig.colorbar(artist, ax=ax, label="Continued disturbance (mGal)")
            ax = axes[1, 0]
            artist = ax.imshow(sigma, origin="lower", extent=extent, cmap="viridis", interpolation="nearest")
            ax.set_title("Conditional noise propagation; blank = unsupported")
            fig.colorbar(artist, ax=ax, label="Conditional standard deviation (mGal)")
            ax = axes[1, 1]
            limit = max(float(np.nanmax(np.abs(residual))), 0.001)
            artist = ax.scatter(*xy, c=residual, s=30, cmap="RdBu_r", vmin=-limit, vmax=limit)
            unsupported = ~np.array(result["stations"]["prediction_covered"])
            ax.scatter(*xy[:, unsupported], marker="x", color=foreground, s=35, label="unsupported / masked")
            ax.legend(loc="lower right", facecolor=background, labelcolor=foreground)
            ax.set_title("Prediction − observation, at original receiver heights")
            fig.colorbar(artist, ax=ax, label="Signed station residual (mGal)")
            for ax in axes.flat:
                ax.set(xlabel="Easting (km, declared metric frame)", ylabel="Northing (km)")
                ax.set_aspect("equal")
                ax.grid(alpha=0.16)
            fig.supxlabel(
                "Harmonic coefficients are not density. Coverage is not resolution. Original observations are unchanged.",
                fontsize=10,
            )
            _save(fig, directory, f"maps-{theme}")
            plt.close(fig)

            fig, axes = plt.subplots(2, 2, figsize=(15, 10), layout="constrained")
            fig.suptitle("M01 training-only selection and independent evaluation\n" + source_label, fontsize=15)
            good = [c for c in result["selection"]["candidates"] if c["status"] == "passed"]
            for depth in sorted(set(c["depth_m"] for c in good)):
                rows = sorted((c for c in good if c["depth_m"] == depth), key=lambda c: c["damping"])
                axes[0, 0].semilogx(
                    [c["damping"] for c in rows],
                    [c["cv_normalized_rmse"] for c in rows],
                    "o-",
                    label=f"depth {depth:g} m",
                )
            axes[0, 0].set(
                xlabel="Damping (scaled ridge system)",
                ylabel="Inner blocked normalized RMSE",
                title="No outer holdout observations used in tuning",
            )
            axes[0, 0].legend(facecolor=background, labelcolor=foreground)
            singular = result["condition"]["weighted_singular_values"]
            axes[0, 1].semilogy(np.arange(1, len(singular) + 1), singular, color="#369bc6")
            axes[0, 1].set(
                xlabel="Singular-value index",
                ylabel="Weighted scaled-design singular value",
                title=f"Damped condition = {result['condition']['damped_condition']:.3g}",
            )
            heights = [g["height_m"] for g in grids]
            axes[1, 0].plot(heights, [g["max_conditional_sigma_mgal"] for g in grids], "o-", color="#369bc6")
            axes[1, 0].axhline(
                result["config"]["max_transfer_sigma_mgal"], color="#c77d37", linestyle="--", label="declared ceiling"
            )
            axes[1, 0].set(
                xlabel="Target ellipsoidal height (m)",
                ylabel="Maximum covered conditional σ (mGal)",
                title="Height selected by training-only error transfer",
            )
            axes[1, 0].legend(facecolor=background, labelcolor=foreground)
            ax = axes[1, 1]
            predicted = np.array(result["stations"]["predicted_mgal"], dtype=float)
            for name, marker, colour in (("train", ".", "#369bc6"), ("holdout", "s", "#c77d37")):
                keep = (partition == name) & np.isfinite(predicted)
                ax.scatter(observed[keep], predicted[keep], marker=marker, color=colour, s=28, label=name)
            lo, hi = float(min(observed)), float(max(observed))
            ax.plot([lo, hi], [lo, hi], linestyle="--", color=foreground, linewidth=1)
            holdout = result["evaluation"]["holdout"]
            score = "unavailable" if holdout["rmse_mgal"] is None else f"{holdout['rmse_mgal']:.4f} mGal"
            ax.set(
                xlabel="Observed disturbance (mGal)",
                ylabel="Predicted at station height (mGal)",
                title=f"Holdout RMSE {score}; unsupported {holdout['unsupported_count']}",
            )
            ax.legend(facecolor=background, labelcolor=foreground)
            for ax in axes.flat:
                ax.grid(alpha=0.2)
            fig.supxlabel(
                "Conditional σ excludes geometry error, selection uncertainty, bias and geological ambiguity.",
                fontsize=10,
            )
            _save(fig, directory, f"diagnostics-{theme}")
            plt.close(fig)
    return int(np.sum(covered))


def _save(figure, directory, stem):
    figure.savefig(directory / f"{stem}.svg", metadata={"Date": None})
    figure.savefig(directory / f"{stem}.png", dpi=210, metadata={"Software": "M01 local transform"})
