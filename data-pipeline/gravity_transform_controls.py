"""Authored, labelled independent volume-integral controls; never field data."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from gravity_processing import digest, normal_gravity, process_survey

G = 6.67430e-11


def prism_integral(coords, prisms, densities, order=16):
    """Downward acceleration by independent Newton volume quadrature, in mGal."""
    nodes, weights = leggauss(order)
    xyz = np.column_stack([np.ravel(value) for value in coords])
    result = np.zeros(len(xyz))
    for prism, density in zip(prisms, densities, strict=True):
        axes, scaled_weights = [], []
        for low, high in zip(prism[::2], prism[1::2], strict=True):
            axes.append((low + high) / 2 + nodes * (high - low) / 2)
            scaled_weights.append(weights * (high - low) / 2)
        source = np.column_stack([v.ravel() for v in np.meshgrid(*axes, indexing="ij")])
        volume_weights = np.prod(np.stack(np.meshgrid(*scaled_weights, indexing="ij")), axis=0).ravel()
        for start in range(0, len(xyz), 32):
            separation = xyz[start : start + 32, None, :] - source[None, :, :]
            radius = np.linalg.norm(separation, axis=2)
            result[start : start + 32] += (
                G * density * 1e5 * np.sum(separation[:, :, 2] / radius**3 * volume_weights, axis=1)
            )
    return result.reshape(np.shape(coords[0]))


def control_request(case=0, noisy=True):
    """Three distinct irregular survey/body arrangements; no fit-kernel generation."""
    if case not in (0, 1, 2):
        raise ValueError("case: require 0, 1 or 2")
    rng = np.random.default_rng(470 + case)
    base_x, base_y = np.meshgrid(np.linspace(-1300, 1700, 14), np.linspace(-1100, 1500, 14))
    base_x = base_x.ravel() + rng.uniform(-50, 50, base_x.size)
    base_y = base_y.ravel() + rng.uniform(-45, 45, base_y.size)
    angle = np.deg2rad([9, -21, 34][case])
    x = base_x * np.cos(angle) - base_y * np.sin(angle) + [400, -800, 1100][case]
    y = base_x * np.sin(angle) + base_y * np.cos(angle) + [-250, 650, -900][case]
    z = 220 + 28 * np.sin(x / 750) + 17 * np.cos(y / 480)
    coords = (x, y, z)
    offset = np.array([x.mean(), x.mean(), y.mean(), y.mean(), 0, 0])
    prisms = (
        np.array(
            [
                [-650, -100, -250, 220, -1200, -420],
                [360, 800, 280, 600, -1900, -680],
                [-250, 110, -720, -420, -1600, -590],
            ],
            dtype=float,
        )
        + offset
    )
    prisms[:, :4] += [
        [0, 0, 0, 0],
        [40 * case, 100 * case, -100 * case, -60 * case],
        [-35 * case, 55 * case, 80 * case, 130 * case],
    ]
    densities = [360 + 70 * case, -280 + 40 * case, 220 - 20 * case]
    true_gravity = prism_integral(coords, prisms, densities)
    sigma = 0.02
    observed = true_gravity + (rng.normal(0, sigma, len(x)) if noisy else 0)
    latitude = 44 + y / 111000
    longitude = -120 + x / (111000 * np.cos(np.deg2rad(44)))
    original = normal_gravity(latitude, z) + observed
    ids = [f"control-{case}-{i:03d}" for i in range(len(x))]
    definition = {
        "case": case,
        "seed": 470 + case,
        "prisms_m": prisms.tolist(),
        "density_kg_m3": densities,
        "operator": "Newton volume integral, tensor Gauss-Legendre order 16",
        "noise_sd_mgal": sigma,
        "noise_added": noisy,
        "survey": "Authored irregular/rotated/translated metric local geometry, nonconstant ellipsoidal heights",
    }
    metadata = {
        "source_kind": "synthetic_control",
        "source_sha256": digest(definition),
        "source_citation": "Original volume-prism numerical control; not measured field data. "
        + json.dumps(definition),
        "rights": "Original controls, Apache-2.0",
        "crs": "EPSG:4326",
        "reference_ellipsoid": "WGS84",
        "height_datum": "ellipsoidal",
        "height_unit": "m",
        "height_sign": "upward",
        "gravity_unit": "mGal",
        "gravity_sign": "downward",
        "gravity_quantity": "absolute_gravity",
        "gravity_datum": "Authored WGS84 normal-field plus independent volumetric anomaly",
        "tide_system": "tide_free",
        "instrument_processing": {
            "calibration": {"status": "applied", "citation": "Authored physical SI definition"},
            "drift": {"status": "not_applicable", "citation": "No synthetic instrument drift"},
            "tide": {"status": "not_applicable", "citation": "No synthetic tidal signals"},
        },
    }
    rows = [
        {
            "station_id": sid,
            "latitude_deg": float(lat),
            "longitude_deg": float(lon),
            "receiver_height_m": float(height),
            "surface_height_m": 0.0,
            "original_value": float(gravity),
            "value_mgal": float(gravity),
            "gravity_sigma": sigma,
            "receiver_sigma_m": 0.0,
            "surface_sigma_m": 0.0,
            "latitude_sigma_deg": 0.0,
        }
        for sid, lat, lon, height, gravity in zip(ids, latitude, longitude, z, original, strict=True)
    ]
    corrected = process_survey(
        {
            "schema_version": "gravity-stations-1",
            "state": "observed_absolute",
            "history": [],
            "metadata": metadata,
            "stations": rows,
        },
        {"target": "gravity_disturbance", "uncertainty_model": "independent_first_order"},
    )
    region = [float(min(x) - 120), float(max(x) + 120), float(min(y) - 120), float(max(y) + 120)]
    geometry = {
        "station_ids": ids,
        "easting_m": x.tolist(),
        "northing_m": y.tolist(),
        "upward_m": z.tolist(),
        "coordinate_unit": "m",
        "axis_order": "easting,northing,upward",
        "vertical_reference": "WGS84_ellipsoid",
        "metric_crs": "LOCAL_CARTESIAN",
        "mapping_citation": "Authored metre local survey; geographic annotations use a declared tangent approximation, not a field CRS transform",
        "component": "g_z_downward",
        "data_unit": "mGal",
        "source_free_citation": "Every receiver/target above independently defined buried prism sources",
        "geometry_error_model": "fixed_geometry_conditional",
        "geometry_error_citation": "Coordinates deterministic by definition; no field accuracy claim",
        "mask": [False] * len(x),
        "mask_reasons": [None] * len(x),
    }
    # A reversible user-declared missing-observation mask, not automatic outlier rejection.
    for index in [83, 84, 97, 98]:
        geometry["mask"][index] = True
        geometry["mask_reasons"][index] = "Authored acquisition-gap control; original retained"
    config = {
        "depths_m": [160.0, 360.0, 700.0],
        "dampings": [0.01, 1.0, 100.0],
        "heights_m": [300.0, 600.0, 1000.0],
        "region_m": region,
        "grid_spacing_m": 100.0,
        "coverage_radius_m": 340.0,
        "block_shape": [6, 6],
        "holdout_fraction": 0.2,
        "seed": 35,
        "inner_folds": 3,
        "min_validation_coverage": 0.3,
        "max_input_sigma_mgal": 0.1,
        "max_transfer_sigma_mgal": 0.03,
        "max_condition": 1e10,
        "error_model": "independent_stations",
    }
    request = {
        "schema_version": "gravity-transform-request-1",
        "correction_result": corrected,
        "geometry": geometry,
        "config": config,
    }
    return request, {
        "definition": definition,
        "coordinates": coords,
        "prisms": prisms,
        "densities": densities,
        "true_observed_mgal": true_gravity,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    request, _ = control_request(args.case)
    output = args.output.absolute()
    root = Path(__file__).resolve().parents[1]
    if any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()) for p in output.parents):
        parser.error("symlink/junction output parents rejected")
    output = output.resolve()
    if output.is_relative_to(root) and not output.is_relative_to(root / "data/raw/gravity-m01-transforms"):
        parser.error("inside repo, output must be ignored data/raw/gravity-m01-transforms")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(deepcopy(request), stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print("Authored independent-volume control only; no field acquisition or eligibility claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
