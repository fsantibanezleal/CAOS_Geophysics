"""Local M01 land-station corrections with explicit, replayable lineage.

Uses the real pinned Boule and Harmonica engines. All heights are converted to
WGS84 ellipsoidal metres before normal gravity or plate removal. No instrument,
geoid, terrain model, covariance, or field truth is inferred.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import sys

import boule
import harmonica
import numpy as np


STATES = ("observed_absolute", "gravity_disturbance", "bouguer_disturbance", "terrain_adjusted_disturbance")
HISTORY_NAMES = ("normal_reference", "elevation_reference", "bouguer_plate", "terrain_residual")
STATE_LENGTHS = (0, 2, 3, 4)
PINS = {"boule": "0.5.0", "harmonica": "0.7.0", "numpy": "2.2.6", "scipy": "1.15.2"}
UNIT_FACTORS = {"mGal": 1.0, "m/s^2": 1e5, "microGal": 1e-3}
G = 6.67430e-11
PLATE_COEFFICIENT = 2 * math.pi * G * 1e5


class GravityContractError(ValueError):
    """Input or correction state cannot support the requested calculation."""


def digest(value):
    """Hash deterministic JSON, rejecting non-finite output."""
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _keys(obj, required, optional, field):
    if not isinstance(obj, dict):
        raise GravityContractError(f"{field}: expected object")
    missing = set(required) - obj.keys()
    unknown = obj.keys() - set(required) - set(optional)
    if missing or unknown:
        raise GravityContractError(f"{field}: missing={sorted(missing)}, unknown={sorted(unknown)}")


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise GravityContractError(f"{field}: expected nonempty text")
    return value


def _number(value, field, lower=-math.inf, upper=math.inf):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GravityContractError(f"{field}: expected finite number")
    value = float(value)
    if not math.isfinite(value) or not lower <= value <= upper:
        raise GravityContractError(f"{field}: expected finite value in [{lower}, {upper}]")
    return value


def _sha(value, field):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise GravityContractError(f"{field}: expected lowercase SHA-256")


@dataclass(frozen=True)
class CorrectionConfig:
    target: str
    uncertainty_model: str
    density_kg_m3: float = 2670.0
    density_sigma_kg_m3: float = 0.0
    outlier_z: float = 6.0
    terrain: dict | None = None

    @classmethod
    def parse(cls, obj):
        _keys(
            obj,
            ("target", "uncertainty_model"),
            ("density_kg_m3", "density_sigma_kg_m3", "outlier_z", "terrain"),
            "config",
        )
        result = cls(**deepcopy(obj))
        if result.target not in STATES[1:]:
            raise GravityContractError("config.target: expected a supported derived state")
        if result.uncertainty_model not in ("independent_first_order", "conservative_marginals"):
            raise GravityContractError("config.uncertainty_model: must explicitly select an error model")
        _number(result.density_kg_m3, "config.density_kg_m3", 1, 10000)
        _number(result.density_sigma_kg_m3, "config.density_sigma_kg_m3", 0, 10000)
        _number(result.outlier_z, "config.outlier_z", 1)
        if result.target in STATES[2:] and not {"density_kg_m3", "density_sigma_kg_m3"} <= obj.keys():
            raise GravityContractError(
                "config.density_kg_m3/density_sigma_kg_m3: explicit plate density and SD required"
            )
        if result.terrain is not None and result.target != STATES[3]:
            raise GravityContractError("config.terrain: supplied terrain requires terrain target")
        return result


def _validate(dataset):
    _keys(dataset, ("schema_version", "metadata", "state", "stations", "history"), (), "dataset")
    if dataset["schema_version"] != "gravity-stations-1":
        raise GravityContractError("dataset.schema_version: expected gravity-stations-1")
    if dataset["state"] not in STATES:
        raise GravityContractError("dataset.state: unknown correction state")
    meta = dataset["metadata"]
    required = (
        "source_kind",
        "source_sha256",
        "source_citation",
        "rights",
        "crs",
        "reference_ellipsoid",
        "height_datum",
        "height_unit",
        "height_sign",
        "gravity_unit",
        "gravity_sign",
        "gravity_quantity",
        "gravity_datum",
        "tide_system",
        "instrument_processing",
    )
    _keys(meta, required, ("geoid_model",), "metadata")
    for key in set(required) - {"instrument_processing"}:
        _text(meta[key], f"metadata.{key}")
    _sha(meta["source_sha256"], "metadata.source_sha256")
    if meta["source_kind"] not in ("synthetic_control", "field"):
        raise GravityContractError("metadata.source_kind: expected synthetic_control or field")
    for key, expected in (
        ("crs", "EPSG:4326"),
        ("reference_ellipsoid", "WGS84"),
        ("height_unit", "m"),
        ("height_sign", "upward"),
        ("tide_system", "tide_free"),
        ("gravity_quantity", "absolute_gravity"),
    ):
        if meta[key] != expected:
            raise GravityContractError(
                f"metadata.{key}: only {expected} supported; explicit upstream conversion required"
            )
    if meta["height_datum"] not in ("ellipsoidal", "orthometric"):
        raise GravityContractError("metadata.height_datum: ambiguous height datum")
    if meta["height_datum"] == "orthometric":
        _text(meta.get("geoid_model"), "metadata.geoid_model")
    elif "geoid_model" in meta:
        raise GravityContractError("metadata.geoid_model: do not reconvert ellipsoidal heights")
    if meta["gravity_unit"] not in UNIT_FACTORS or meta["gravity_sign"] not in ("downward", "upward"):
        raise GravityContractError("metadata.gravity_unit/gravity_sign: ambiguous units or sign")
    instrument = meta["instrument_processing"]
    _keys(instrument, ("calibration", "drift", "tide"), (), "metadata.instrument_processing")
    for name, entry in instrument.items():
        _keys(entry, ("status", "citation"), (), f"instrument_processing.{name}")
        if entry["status"] not in ("applied", "not_applicable"):
            raise GravityContractError(f"instrument_processing.{name}: unknown/unapplied correction")
        if name == "calibration" and entry["status"] != "applied":
            raise GravityContractError("instrument_processing.calibration: absolute calibrated gravity required")
        _text(entry["citation"], f"instrument_processing.{name}.citation")
    rows = dataset["stations"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
        raise GravityContractError("stations: require 1..10000 stations")
    ids, positions = set(), set()
    required = (
        "station_id",
        "latitude_deg",
        "longitude_deg",
        "receiver_height_m",
        "surface_height_m",
        "original_value",
        "value_mgal",
        "gravity_sigma",
        "receiver_sigma_m",
        "surface_sigma_m",
        "latitude_sigma_deg",
    )
    for i, row in enumerate(rows):
        label = f"stations[{i}]"
        _keys(row, required, ("geoid_m", "geoid_sigma_m"), label)
        sid = _text(row["station_id"], f"{label}.station_id")
        lat = _number(row["latitude_deg"], f"{label}.latitude_deg", -90, 90)
        lon = _number(row["longitude_deg"], f"{label}.longitude_deg", -180, 180)
        # Longitude 180 and -180 denote the same position; poles ignore longitude.
        pos = (lat, 0.0 if abs(lat) == 90 else ((lon + 180) % 360 - 180))
        if sid in ids or pos in positions:
            raise GravityContractError(f"{label}: duplicate station_id or position requires review")
        ids.add(sid)
        positions.add(pos)
        for key in ("receiver_height_m", "surface_height_m", "original_value", "value_mgal"):
            _number(row[key], f"{label}.{key}")
        for key in ("gravity_sigma", "receiver_sigma_m", "surface_sigma_m", "latitude_sigma_deg"):
            _number(row[key], f"{label}.{key}", 0)
        if meta["height_datum"] == "orthometric":
            _number(row.get("geoid_m"), f"{label}.geoid_m")
            _number(row.get("geoid_sigma_m"), f"{label}.geoid_sigma_m", 0)
        elif "geoid_m" in row or "geoid_sigma_m" in row:
            raise GravityContractError(f"{label}.geoid_m: ellipsoidal heights already converted")
    if not isinstance(dataset["history"], list):
        raise GravityContractError("dataset.history: expected list")
    return meta, rows


def normal_gravity(latitude, height):
    """Pinned Boule closed-form gravity, in mGal at ellipsoidal height in m."""
    return np.asarray(boule.WGS84.normal_gravity(latitude=latitude, height=height), dtype=float)


def _derivatives(lat, height):
    step = 1e-4
    low, high = np.maximum(lat - step, -90), np.minimum(lat + step, 90)
    dlat = (normal_gravity(high, height) - normal_gravity(low, height)) / (high - low)
    # Do not evaluate Boule inside the ellipsoid near h=0.
    low_h = np.maximum(height - 0.1, 0)
    dh = (normal_gravity(lat, height + 0.1) - normal_gravity(lat, low_h)) / (height + 0.1 - low_h)
    boundary = height < 0.1
    if np.any(boundary):
        h = height[boundary]
        phi = lat[boundary]
        dh[boundary] = (
            -3 * normal_gravity(phi, h) + 4 * normal_gravity(phi, h + 0.1) - normal_gravity(phi, h + 0.2)
        ) / 0.2
    return dlat, dh


def _terrain(config, rows):
    terrain = config.terrain
    _keys(
        terrain,
        (
            "kind",
            "unit",
            "height_reference",
            "density_kg_m3",
            "source_sha256",
            "method",
            "station_ids",
            "additions_mgal",
            "sigma_mgal",
        ),
        (),
        "terrain",
    )
    if terrain["kind"] != "additive_residual_to_plate" or terrain["unit"] != "mGal":
        raise GravityContractError("terrain.kind/unit: require signed additive residual to plate in mGal")
    if terrain["height_reference"] != "WGS84_ellipsoid" or terrain["density_kg_m3"] != config.density_kg_m3:
        raise GravityContractError("terrain.height_reference/density_kg_m3: mismatch with selected plate")
    _sha(terrain["source_sha256"], "terrain.source_sha256")
    _text(terrain["method"], "terrain.method")
    if terrain["station_ids"] != [r["station_id"] for r in rows]:
        raise GravityContractError("terrain.station_ids: must match input order exactly")
    for key in ("additions_mgal", "sigma_mgal"):
        if not isinstance(terrain[key], list) or len(terrain[key]) != len(rows):
            raise GravityContractError(f"terrain.{key}: station shape mismatch")
        for i, value in enumerate(terrain[key]):
            _number(value, f"terrain.{key}[{i}]", 0 if key == "sigma_mgal" else -math.inf)
    if config.uncertainty_model != "conservative_marginals":
        raise GravityContractError("terrain: dependence on plate requires conservative_marginals")
    return np.asarray(terrain["additions_mgal"]), np.asarray(terrain["sigma_mgal"])


def process_survey(dataset: dict, config: dict) -> dict:
    """Create a derivative; reject ambiguous state and every duplicate correction."""
    config = CorrectionConfig.parse(config)
    meta, rows = _validate(dataset)
    engines = {name: version(name) for name in PINS}
    if engines != PINS:
        raise GravityContractError(f"environment: expected pinned engines {PINS}, found {engines}")
    current_index, target_index = STATES.index(dataset["state"]), STATES.index(config.target)
    if target_index <= current_index:
        raise GravityContractError("config.target: double correction or backwards processing rejected")

    def col(key):
        return np.asarray([r[key] for r in rows], dtype=float)

    lat, height, surface = col("latitude_deg"), col("receiver_height_m"), col("surface_height_m")
    geoid = col("geoid_m") if meta["height_datum"] == "orthometric" else np.zeros(len(rows))
    height, surface = height + geoid, surface + geoid
    if np.any(surface < 0) or np.any(height < surface):
        raise GravityContractError(
            "surface_height_m/receiver_height_m: require land above ellipsoid and receiver on/above surface"
        )
    factor = UNIT_FACTORS[meta["gravity_unit"]]
    sign = 1 if meta["gravity_sign"] == "downward" else -1
    original = col("original_value") * factor * sign
    if np.any(original <= 0):
        raise GravityContractError("original_value/gravity_sign: absolute downward gravity must be positive")
    gamma0, gammah = normal_gravity(lat, 0), normal_gravity(lat, height)
    plate = harmonica.bouguer_correction(surface, density_crust=config.density_kg_m3)
    additions = [-gamma0, gamma0 - gammah, -plate]
    ref = {"ellipsoid": "WGS84", "height_reference": "WGS84_ellipsoid", "boule": engines["boule"]}
    params = [
        ref,
        {**ref, "height_term": "gamma(phi,0)-gamma(phi,h)"},
        {
            "harmonica": engines["harmonica"],
            "density_kg_m3": config.density_kg_m3,
            "density_sigma_kg_m3": config.density_sigma_kg_m3,
            "geometry": "land_infinite_plate",
            "height_reference": "WGS84_ellipsoid",
        },
    ]
    terrain_sigma = np.zeros(len(rows))
    if target_index == 3:
        terrain_add, terrain_sigma = _terrain(config, rows)
        additions.append(terrain_add)
        params.append(deepcopy(config.terrain))
    history = deepcopy(dataset["history"])
    if len(history) != STATE_LENGTHS[current_index]:
        raise GravityContractError("history: state does not match applied correction count")
    values = original.copy()
    for i, record in enumerate(history):
        _keys(
            record,
            ("name", "parameters", "additions_mgal", "input_values_sha256", "output_values_sha256"),
            (),
            f"history[{i}]",
        )
        if record["name"] != HISTORY_NAMES[i] or record["parameters"] != params[i]:
            raise GravityContractError(f"history[{i}]: ambiguous correction order or changed prior parameters")
        if record["additions_mgal"] != additions[i].tolist() or record["input_values_sha256"] != digest(
            values.tolist()
        ):
            raise GravityContractError(f"history[{i}]: correction values/input hash do not reconstruct")
        values += additions[i]
        if record["output_values_sha256"] != digest(values.tolist()):
            raise GravityContractError(f"history[{i}]: output hash mismatch")
    if not np.array_equal(values, col("value_mgal")):
        raise GravityContractError("value_mgal: current values do not match original values and correction history")
    for i in range(len(history), STATE_LENGTHS[target_index]):
        before = digest(values.tolist())
        values += additions[i]
        history.append(
            {
                "name": HISTORY_NAMES[i],
                "parameters": deepcopy(params[i]),
                "additions_mgal": additions[i].tolist(),
                "input_values_sha256": before,
                "output_values_sha256": digest(values.tolist()),
            }
        )
    dlat, dh = _derivatives(lat, height)
    # Differentiate the final expression, including the shared geoid contribution.
    d_surface = -PLATE_COEFFICIENT * config.density_kg_m3 if target_index >= 2 else 0.0
    components = {
        "observed_gravity": col("gravity_sigma") * factor,
        "latitude": np.abs(dlat) * col("latitude_sigma_deg"),
        "receiver_height": np.abs(dh) * col("receiver_sigma_m"),
        "surface_height": abs(d_surface) * col("surface_sigma_m"),
        "density": PLATE_COEFFICIENT * surface * config.density_sigma_kg_m3
        if target_index >= 2
        else np.zeros(len(rows)),
        "geoid": np.abs(-dh + d_surface) * col("geoid_sigma_m")
        if meta["height_datum"] == "orthometric"
        else np.zeros(len(rows)),
        "terrain": terrain_sigma,
    }
    stack = np.stack(list(components.values()))
    uncertainty = (
        np.sqrt(np.sum(stack**2, axis=0))
        if config.uncertainty_model == "independent_first_order"
        else np.sum(stack, axis=0)
    )
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(uncertainty)):
        raise GravityContractError("result: non-finite gravity or propagated uncertainty")
    out = deepcopy(dataset)
    out["state"], out["history"] = config.target, history
    for row, value in zip(out["stations"], values, strict=True):
        row["value_mgal"] = float(value)
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    warnings = [
        "Plate approximation is not a terrain model or geological uncertainty.",
        "Source hash is supplied provenance; this operation does not retrieve field bytes.",
        "Full M01 field, holdout/transform, online and browser acceptance remains unresolved.",
    ]
    if meta["source_kind"] == "synthetic_control":
        warnings.append("Authored synthetic controls, not measured field data.")
    if config.uncertainty_model == "independent_first_order":
        warnings.append("First-order propagation assumes independent primitive input errors.")
    else:
        warnings.append("Sum of marginal first-order contributions; no independence or geological confidence claim.")
    if len(rows) < 5 or mad == 0:
        scores, flags = [None] * len(rows), [False] * len(rows)
        warnings.append("MAD outlier screen unassessable: fewer than five stations or zero MAD.")
    else:
        scores = (np.abs(values - median) / (1.4826 * mad)).tolist()
        flags = [s > config.outlier_z for s in scores]
    return {
        "dataset": out,
        "processing": {
            "method": "M01-local-station-corrections",
            "input_sha256": digest(dataset),
            "output_sha256": digest(out),
            "config": deepcopy(config.__dict__),
            "engines": engines,
            "python": platform.python_version(),
            "module_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "uncertainty_model": config.uncertainty_model,
            "uncertainty_mgal": uncertainty.tolist(),
            "uncertainty_components_mgal": {k: v.tolist() for k, v in components.items()},
            "full_method_accepted": False,
            "warnings": warnings,
        },
        "qc": {
            "station_ids": [r["station_id"] for r in rows],
            "longitude_deg": col("longitude_deg").tolist(),
            "latitude_deg": lat.tolist(),
            "receiver_ellipsoidal_m": height.tolist(),
            "surface_ellipsoidal_m": surface.tolist(),
            "original_mgal": original.tolist(),
            "derived_mgal": values.tolist(),
            "robust_z": scores,
            "outlier_flag": flags,
            "excluded_station_ids": [],
        },
    }


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise GravityContractError(f"JSON: duplicate key {key}")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="JSON object with dataset and config")
    parser.add_argument("--output-dir", required=True, type=Path, help="New directory, never overwritten")
    args = parser.parse_args(argv)
    try:
        root = Path(__file__).resolve().parents[1]
        if not args.output_dir.is_absolute():
            raise GravityContractError("output-dir: require explicit absolute external storage")
        output = args.output_dir.absolute()
        for parent in (output, *output.parents):
            if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
                raise GravityContractError("output-dir: external storage cannot traverse symlink/junction")
            if (parent / ".git").exists() or (parent / ".git").is_symlink():
                raise GravityContractError("output-dir: require external storage outside every repository")
        output = output.resolve()
        if output.is_relative_to(root):
            raise GravityContractError("output-dir: require external storage outside repository")
        if output.exists():
            raise GravityContractError("output-dir: already exists; overwrite forbidden")
        if args.input.stat().st_size > 32 * 1024 * 1024:
            raise GravityContractError("input: maximum local JSON size is 32 MiB")
        input_bytes = args.input.read_bytes()
        if len(input_bytes) > 32 * 1024 * 1024:
            raise GravityContractError("input: maximum local JSON size is 32 MiB")
        request = json.loads(input_bytes.decode("utf-8"), object_pairs_hook=_unique_object)
        _keys(request, ("dataset", "config"), (), "request")
        result = process_survey(request["dataset"], request["config"])
        encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        output.mkdir(parents=True, exist_ok=False)
        result_path = output / "gravity-result.json"
        with result_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
        receipt = {
            "executed_utc": datetime.now(timezone.utc).isoformat(),
            "input_file_sha256": sha256(input_bytes).hexdigest(),
            "result_file_sha256": sha256(result_path.read_bytes()).hexdigest(),
            "input_dataset_sha256": result["processing"]["input_sha256"],
            "output_dataset_sha256": result["processing"]["output_sha256"],
        }
        with (output / "receipt.json").open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except (GravityContractError, OSError, ValueError, TypeError) as exc:
        print(f"M01 rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
