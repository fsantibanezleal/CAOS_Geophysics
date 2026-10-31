from __future__ import annotations

import json
from hashlib import sha256

import numpy as np
import pytest

import magnetic_continuation
from magnetic_continuation import ContinuationError, main, process_grid_result, upward_continue


def test_affine_harmonic_field_is_preserved_at_height():
    east = np.arange(32, dtype=np.float64) * 25.0
    north = np.arange(24, dtype=np.float64) * 40.0
    xx, yy = np.meshgrid(east, north, indexing="xy")
    field = 51000.0 + 0.013 * xx - 0.021 * yy

    result = upward_continue(field, spacing_easting_m=25, spacing_northing_m=40, height_m=750)

    np.testing.assert_allclose(result["values"], field, rtol=0, atol=2e-10)
    assert result["regional_plane_coefficients"]["gradient_easting_per_m"] == pytest.approx(0.013)
    assert result["regional_plane_coefficients"]["gradient_northing_per_m"] == pytest.approx(-0.021)
    assert result["claims"]["subsurface_inverse"] is False


def test_single_harmonic_decays_by_analytic_fourier_transfer():
    ny, nx = 40, 48
    dx, dy, height = 20.0, 35.0, 120.0
    east = np.arange(nx) * dx
    north = np.arange(ny) * dy
    xx, yy = np.meshgrid(east, north, indexing="xy")
    mode_x, mode_y = 3, 2
    field = np.cos(2 * np.pi * mode_x * xx / (nx * dx) + 2 * np.pi * mode_y * yy / (ny * dy))
    radial_k = np.hypot(2 * np.pi * mode_x / (nx * dx), 2 * np.pi * mode_y / (ny * dy))
    expected = field * np.exp(-radial_k * height)

    result = upward_continue(field, spacing_easting_m=dx, spacing_northing_m=dy, height_m=height)

    np.testing.assert_allclose(result["values"], expected, rtol=2e-12, atol=2e-12)
    assert result["transfer"] == "exp(-radial_wavenumber_rad_per_m * height_m)"


def test_zero_height_returns_same_grid_and_reports_periodic_seam():
    field = np.arange(64, dtype=np.float64).reshape(8, 8)
    result = upward_continue(field, spacing_easting_m=1, spacing_northing_m=2, height_m=0)
    np.testing.assert_allclose(result["values"], field, rtol=0, atol=2e-13)
    assert result["edge_periodicity_diagnostic"]["maximum_seam_jump_over_grid_std"] > 0


@pytest.mark.parametrize("kwargs", [
    {"spacing_easting_m": 0, "spacing_northing_m": 1, "height_m": 1},
    {"spacing_easting_m": 1, "spacing_northing_m": 1, "height_m": -1},
    {"spacing_easting_m": 1, "spacing_northing_m": 1, "height_m": float("nan")},
    {"spacing_easting_m": 1, "spacing_northing_m": 1, "height_m": 100001},
])
def test_invalid_physical_parameters_are_rejected(kwargs):
    with pytest.raises(ContinuationError):
        upward_continue(np.ones((8, 8)), **kwargs)


def test_grid_cell_budget_and_nonuniform_axes_are_rejected(monkeypatch):
    monkeypatch.setattr(magnetic_continuation, "MAX_GRID_CELLS", 15)
    with pytest.raises(ContinuationError, match="grid contains 16 cells"):
        upward_continue(np.ones((4, 4)), spacing_easting_m=1, spacing_northing_m=1, height_m=10)
    monkeypatch.setattr(magnetic_continuation, "MAX_GRID_CELLS", 250_000)
    artifact = {
        "schema": "magnetic-flightline-process-result-1",
        "source": {"source_id": "nonuniform", "sha256": "c" * 64},
        "configuration": {"value_unit": "nT"},
        "grid": {"x_easting_m": [0, 1, 2, 4], "y_northing_m": [0, 1, 2, 3],
                 "values": np.ones((4, 4)).tolist(), "support_mask": np.ones((4, 4), dtype=bool).tolist()},
    }
    with pytest.raises(ContinuationError, match="uniformly spaced"):
        process_grid_result(artifact, height_m=1)


def test_incomplete_support_and_nonfinite_grids_are_never_filled():
    grid = np.ones((8, 8))
    mask = np.ones((8, 8), dtype=bool)
    mask[3, 3] = False
    with pytest.raises(ContinuationError, match="complete true support mask"):
        upward_continue(grid, spacing_easting_m=1, spacing_northing_m=1, height_m=10,
                        support_mask=mask)
    grid[3, 3] = np.nan
    with pytest.raises(ContinuationError, match="nonfinite"):
        upward_continue(grid, spacing_easting_m=1, spacing_northing_m=1, height_m=10)


def test_m03_result_roi_preserves_coordinates_and_rejects_unsupported_cells():
    ny, nx = 10, 12
    x, y = np.arange(nx) * 25.0, np.arange(ny) * 40.0
    xx, yy = np.meshgrid(x, y, indexing="xy")
    field = 120.0 + 0.01 * xx - 0.02 * yy
    support = np.ones((ny, nx), dtype=bool)
    support[0, 0] = False
    artifact = {
        "schema": "magnetic-flightline-process-result-1",
        "source": {"source_id": "control", "sha256": "a" * 64},
        "configuration": {"value_unit": "nT"},
        "grid": {"x_easting_m": x.tolist(), "y_northing_m": y.tolist(),
                 "values": field.tolist(), "support_mask": support.tolist()},
    }

    window = process_grid_result(artifact, height_m=100, roi=(1, 9, 2, 10))
    assert window["shape_yx"] == [8, 8]
    assert window["x_easting_m"] == x[2:10].tolist()
    assert window["y_northing_m"] == y[1:9].tolist()
    assert window["value_unit"] == "nT"
    with pytest.raises(ContinuationError, match="complete true support mask"):
        process_grid_result(artifact, height_m=100)


def test_cli_hashes_parent_result_and_never_overwrites(tmp_path):
    ny, nx = 8, 9
    x, y = np.arange(nx, dtype=float), np.arange(ny, dtype=float)
    xx, yy = np.meshgrid(x, y, indexing="xy")
    artifact = {
        "schema": "magnetic-flightline-process-result-1",
        "source": {"source_id": "cli-control", "sha256": "b" * 64},
        "configuration": {"value_unit": "nT"},
        "grid": {"x_easting_m": x.tolist(), "y_northing_m": y.tolist(),
                 "values": (10 + xx - 2 * yy).tolist(),
                 "support_mask": np.ones((ny, nx), dtype=bool).tolist()},
    }
    source = tmp_path / "m03-result.json"
    source.write_text(json.dumps(artifact), encoding="utf-8")
    output = tmp_path / "continued.json"

    assert main(["--input", str(source), "--output", str(output), "--height-m", "250"]) == 0
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["parent_result_sha256"] == sha256(source.read_bytes()).hexdigest()
    assert saved["height_m"] == 250
    with pytest.raises(SystemExit) as error:
        main(["--input", str(source), "--output", str(output), "--height-m", "250"])
    assert error.value.code == 2
