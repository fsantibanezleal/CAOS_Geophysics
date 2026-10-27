"""Upward continuation for a complete, uniformly sampled potential-field grid.

The operation is the Fourier-domain harmonic continuation
``F(k, h) = F(k, 0) exp(-|k| h)``. It does not level lines, fill missing cells,
or infer a source model. The periodic-edge assumption is reported explicitly;
users should choose and document a suitable window before calling this tool.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

MAX_GRID_CELLS = 250_000
MAX_INPUT_BYTES = 64 * 1024 * 1024


class ContinuationError(ValueError):
    """The grid cannot support the declared harmonic continuation."""


def upward_continue(
    values: object,
    *,
    spacing_easting_m: float,
    spacing_northing_m: float,
    height_m: float,
    support_mask: object | None = None,
) -> dict:
    """Continue a full regular grid upward by ``height_m``.

    A best-fit affine regional plane is continued unchanged, while its
    residual is filtered by the exact harmonic transfer function. This
    avoids incorrectly attenuating the zero and first spatial frequencies.
    Inputs with holes or nonfinite cells are rejected: this routine never
    silently fills unsupported observations.
    """
    grid = np.asarray(values, dtype=np.float64)
    if grid.ndim != 2 or min(grid.shape, default=0) < 4:
        raise ContinuationError("grid must be a two-dimensional array at least 4 by 4")
    if grid.size > MAX_GRID_CELLS:
        raise ContinuationError(f"grid contains {grid.size} cells; bound is {MAX_GRID_CELLS}")
    if not np.all(np.isfinite(grid)):
        raise ContinuationError("grid contains nonfinite or unsupported values")
    if support_mask is not None:
        mask = np.asarray(support_mask)
        if mask.shape != grid.shape or mask.dtype.kind != "b" or not np.all(mask):
            raise ContinuationError("upward continuation requires a complete true support mask")
    dx, dy, height = map(float, (spacing_easting_m, spacing_northing_m, height_m))
    if not np.isfinite([dx, dy, height]).all() or dx <= 0 or dy <= 0 or height < 0:
        raise ContinuationError("grid spacings must be positive and continuation height nonnegative")
    if height > 100_000:
        raise ContinuationError("continuation height exceeds the 100 km safety bound")

    ny, nx = grid.shape
    east, north = np.meshgrid(np.arange(nx, dtype=np.float64) * dx,
                              np.arange(ny, dtype=np.float64) * dy,
                              indexing="xy")
    design = np.column_stack((np.ones(grid.size), east.ravel(), north.ravel()))
    coefficients, *_ = np.linalg.lstsq(design, grid.ravel(), rcond=None)
    regional = (design @ coefficients).reshape(grid.shape)
    residual = grid - regional

    kx = 2.0 * np.pi * np.fft.fftfreq(nx, d=dx)
    ky = 2.0 * np.pi * np.fft.fftfreq(ny, d=dy)
    radial_wavenumber = np.hypot(ky[:, None], kx[None, :])
    transfer = np.exp(-radial_wavenumber * height)
    continued_residual = np.fft.ifft2(np.fft.fft2(residual) * transfer).real
    result = regional + continued_residual

    # A compact seam diagnostic quantifies the periodic extension assumed by
    # the FFT; it is evidence for inspection, not an automatic acceptance gate.
    east_seam = float(np.sqrt(np.mean((grid[:, 0] - grid[:, -1]) ** 2)))
    north_seam = float(np.sqrt(np.mean((grid[0, :] - grid[-1, :]) ** 2)))
    scale = max(float(np.std(grid)), np.finfo(float).eps)
    return {
        "schema": "magnetic-upward-continuation-result-1",
        "values": result.tolist(),
        "shape_yx": [ny, nx],
        "spacing_easting_m": dx,
        "spacing_northing_m": dy,
        "height_m": height,
        "regional_plane_coefficients": {
            "intercept": float(coefficients[0]),
            "gradient_easting_per_m": float(coefficients[1]),
            "gradient_northing_per_m": float(coefficients[2]),
        },
        "edge_periodicity_diagnostic": {
            "east_rms_seam_jump": east_seam,
            "north_rms_seam_jump": north_seam,
            "grid_standard_deviation": float(np.std(grid)),
            "maximum_seam_jump_over_grid_std": max(east_seam, north_seam) / scale,
        },
        "transfer": "exp(-radial_wavenumber_rad_per_m * height_m)",
        "assumptions": [
            "uniformly sampled rectangular grid",
            "complete measured/interpolated support; missing cells are rejected",
            "periodic extension at grid boundaries for the FFT",
            "affine regional plane is harmonic and is continued unchanged",
        ],
        "claims": {
            "corrections_applied": [],
            "provider_grid_equivalence": False,
            "subsurface_inverse": False,
            "scientific_acceptance": False,
        },
    }


def process_grid_result(result: object, *, height_m: float, roi: tuple[int, int, int, int] | None = None) -> dict:
    """Continue a supported subwindow of an M03 processing result.

    ``roi`` is ``(row_start, row_stop, column_start, column_stop)`` with
    half-open bounds. Requiring the caller to select a completely supported
    rectangle prevents the FFT from manufacturing values across the convex
    hull's unsupported corners.
    """
    if not isinstance(result, dict) or result.get("schema") != "magnetic-flightline-process-result-1":
        raise ContinuationError("input must be a magnetic-flightline-process-result-1 artifact")
    grid_record = result.get("grid")
    if not isinstance(grid_record, dict):
        raise ContinuationError("input M03 result has no gridded field")
    values = np.asarray(grid_record.get("values"), dtype=np.float64)
    support = np.asarray(grid_record.get("support_mask"))
    x = np.asarray(grid_record.get("x_easting_m"), dtype=np.float64)
    y = np.asarray(grid_record.get("y_northing_m"), dtype=np.float64)
    if values.ndim != 2 or support.shape != values.shape or support.dtype.kind != "b":
        raise ContinuationError("input values and boolean support mask must have matching 2D shape")
    if x.ndim != 1 or y.ndim != 1 or values.shape != (len(y), len(x)) or min(len(x), len(y)) < 4:
        raise ContinuationError("grid axes and array dimensions do not agree or are too small")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ContinuationError("grid coordinates must be finite")
    dxs, dys = np.diff(x), np.diff(y)
    if (np.any(dxs <= 0) or np.any(dys <= 0)
            or not np.allclose(dxs, dxs[0], rtol=1e-8, atol=1e-10)
            or not np.allclose(dys, dys[0], rtol=1e-8, atol=1e-10)):
        raise ContinuationError("grid axes must be increasing and uniformly spaced")
    if roi is None:
        r0, r1, c0, c1 = 0, len(y), 0, len(x)
    else:
        if len(roi) != 4 or any(isinstance(v, bool) or not isinstance(v, int) for v in roi):
            raise ContinuationError("ROI must contain four integer half-open bounds")
        r0, r1, c0, c1 = roi
    if not (0 <= r0 < r1 <= len(y) and 0 <= c0 < c1 <= len(x)):
        raise ContinuationError("ROI bounds fall outside the supplied grid")
    window = values[r0:r1, c0:c1]
    window_support = support[r0:r1, c0:c1]
    continued = upward_continue(window, spacing_easting_m=dxs[0], spacing_northing_m=dys[0],
                                height_m=height_m, support_mask=window_support)
    continued.update({
        "source": result.get("source"),
        "parent_result_sha256": None,
        "value_unit": result.get("configuration", {}).get("value_unit"),
        "x_easting_m": x[c0:c1].tolist(),
        "y_northing_m": y[r0:r1].tolist(),
        "roi_row_column_bounds": [r0, r1, c0, c1],
        "limitations": [
            "No levelling, diurnal, IGRF, terrain or regional correction was applied.",
            "FFT assumes periodic extension; inspect the returned seam diagnostic and window the input when appropriate.",
            "Only the explicitly selected fully supported regular-grid rectangle was continued.",
            "This is a potential-field transform, not an inverse model or provider-grid comparison.",
        ],
    })
    return continued


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upward-continue a fully supported M03 regular-grid subset")
    parser.add_argument("--input", required=True, type=Path, help="M03 processing result JSON")
    parser.add_argument("--output", required=True, type=Path, help="new external result JSON; never overwritten")
    parser.add_argument("--height-m", required=True, type=float, help="upward continuation height in metres")
    parser.add_argument("--roi", nargs=4, type=int, metavar=("ROW0", "ROW1", "COL0", "COL1"),
                        help="optional half-open supported-grid window")
    args = parser.parse_args(argv)
    try:
        source_path, output_path = args.input.resolve(), args.output.resolve()
        if source_path == output_path or output_path.exists():
            raise ContinuationError("output must be a new path distinct from input")
        if source_path.is_symlink() or not source_path.is_file():
            raise ContinuationError("input must be a regular non-symlink M03 result file")
        if source_path.stat().st_size <= 0 or source_path.stat().st_size > MAX_INPUT_BYTES:
            raise ContinuationError(f"input JSON must be 1 to {MAX_INPUT_BYTES} bytes")
        raw = source_path.read_bytes()
        result = json.loads(raw)
        continued = process_grid_result(result, height_m=args.height_m,
                                        roi=tuple(args.roi) if args.roi is not None else None)
        continued["parent_result_sha256"] = sha256(raw).hexdigest()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(continued, stream, indent=2, allow_nan=False)
            stream.write("\n")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
