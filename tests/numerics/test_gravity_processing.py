"""Independent equations, limiting controls and adversarial M01 contracts.

All inputs here are original synthetic numerical controls, never field data.
"""

from copy import deepcopy
import csv
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pytest

from gravity_processing import GravityContractError, digest, normal_gravity, process_survey


ROOT = Path(__file__).resolve().parents[2]
G = 6.67430e-11
COEFFICIENT = 2 * math.pi * G * 1e5


def somigliana(latitude):
    """Independent WGS84 surface formula using published rounded constants."""
    a, f = 6378137.0, 1 / 298.257223563
    b = a * (1 - f)
    ge, gp = 9.7803253359, 9.8321849378
    k = b * gp / (a * ge) - 1
    sin2 = np.sin(np.radians(latitude)) ** 2
    return ge * (1 + k * sin2) / np.sqrt(1 - (2 * f - f**2) * sin2) * 1e5


def survey(count=1):
    return {
        "schema_version": "gravity-stations-1",
        "state": "observed_absolute",
        "history": [],
        "metadata": {
            "source_kind": "synthetic_control",
            "source_sha256": sha256(b"authored controls").hexdigest(),
            "source_citation": "Original deterministic numerical controls, no field observations",
            "rights": "Authored test inputs, Apache-2.0",
            "crs": "EPSG:4326",
            "reference_ellipsoid": "WGS84",
            "height_datum": "ellipsoidal",
            "height_unit": "m",
            "height_sign": "upward",
            "gravity_unit": "mGal",
            "gravity_sign": "downward",
            "gravity_quantity": "absolute_gravity",
            "gravity_datum": "WGS84 normal-field synthetic control",
            "tide_system": "tide_free",
            "instrument_processing": {
                k: {
                    "status": "applied" if k == "calibration" else "not_applicable",
                    "citation": "Analytic synthetic control has no instrument or time effects",
                }
                for k in ("calibration", "drift", "tide")
            },
        },
        "stations": [
            {
                "station_id": f"control-{i}",
                "latitude_deg": 45.0,
                "longitude_deg": float(i),
                "receiver_height_m": 0.0,
                "surface_height_m": 0.0,
                "original_value": float(somigliana(45)) + i,
                "value_mgal": float(somigliana(45)) + i,
                "gravity_sigma": 0.1,
                "receiver_sigma_m": 0.0,
                "surface_sigma_m": 0.0,
                "latitude_sigma_deg": 0.0,
            }
            for i in range(count)
        ],
    }


def config(target="bouguer_disturbance", **kwargs):
    return {
        "target": target,
        "uncertainty_model": "conservative_marginals",
        "density_kg_m3": 2670.0,
        "density_sigma_kg_m3": 0.0,
        **kwargs,
    }


def terrain(rows, **kwargs):
    return {
        "kind": "additive_residual_to_plate",
        "unit": "mGal",
        "height_reference": "WGS84_ellipsoid",
        "density_kg_m3": 2670.0,
        "source_sha256": sha256(b"authored residual terrain control").hexdigest(),
        "method": "Synthetic signed residual control, not a DEM calculation",
        "station_ids": [r["station_id"] for r in rows],
        "additions_mgal": [2.0] * len(rows),
        "sigma_mgal": [0.2] * len(rows),
        **kwargs,
    }


def test_station_correction_lineage():
    data = survey(2)
    data["stations"][0].update(receiver_height_m=1000.0, surface_height_m=900.0)
    original = deepcopy(data)
    result = process_survey(data, config("terrain_adjusted_disturbance", terrain=terrain(data["stations"])))
    assert data == original
    derived = result["dataset"]
    assert [r["name"] for r in derived["history"]] == [
        "normal_reference",
        "elevation_reference",
        "bouguer_plate",
        "terrain_residual",
    ]
    reconstructed = [r["original_value"] for r in data["stations"]]
    for entry in derived["history"]:
        assert entry["input_values_sha256"] == digest(reconstructed)
        reconstructed = (np.asarray(reconstructed) + entry["additions_mgal"]).tolist()
        assert entry["output_values_sha256"] == digest(reconstructed)
    np.testing.assert_array_equal(reconstructed, result["qc"]["derived_mgal"])
    assert result["processing"]["input_sha256"] == digest(original)
    assert result["processing"]["output_sha256"] == digest(derived)
    assert result["processing"]["full_method_accepted"] is False
    assert result == process_survey(data, config("terrain_adjusted_disturbance", terrain=terrain(data["stations"])))
    first = process_survey(data, config("gravity_disturbance"))
    resumed = process_survey(first["dataset"], config("bouguer_disturbance"))
    direct = process_survey(data, config("bouguer_disturbance"))
    assert resumed["dataset"] == direct["dataset"]


def test_normal_gravity_oracles():
    lat = np.array([-90, -60, -45, 0, 45, 60, 90])
    # Published equator/pole constants are truncated to 10 decimals in SI;
    # one last-place unit converts to 1e-5 mGal, the independent precision bound.
    np.testing.assert_allclose(normal_gravity(lat, 0), somigliana(lat), rtol=0, atol=1e-5)
    assert float(normal_gravity(45, 1000)) == pytest.approx(980311.28969268, abs=1e-7)
    np.testing.assert_allclose(normal_gravity(lat, 500), normal_gravity(-lat, 500), rtol=0, atol=1e-8)
    assert np.all(normal_gravity(lat, 1000) < normal_gravity(lat, 0))
    data = survey()
    data["stations"][0].update(receiver_height_m=1000.0, original_value=980311.28969268, value_mgal=980311.28969268)
    result = process_survey(data, config("gravity_disturbance"))
    assert result["qc"]["derived_mgal"][0] == pytest.approx(0, abs=1e-7)
    assert result["dataset"]["history"][1]["additions_mgal"][0] == pytest.approx(308.48724505, abs=1e-7)
    # This explicitly fails if 0.3086*h is also applied after Boule's height term.


def test_plate_formula_and_sign():
    data = survey()
    data["stations"][0].update(receiver_height_m=1000.0, surface_height_m=1000.0)
    result = process_survey(data, config())
    plate = result["dataset"]["history"][2]["additions_mgal"][0]
    assert plate == pytest.approx(-2 * math.pi * G * 2670 * 1000 * 1e5, abs=1e-10)
    zero = process_survey(survey(), config())
    assert zero["dataset"]["history"][2]["additions_mgal"] == [0.0]
    for unit, factor, sign in (("m/s^2", 1e5, 1), ("microGal", 1e-3, 1), ("mGal", 1, -1)):
        converted = deepcopy(data)
        converted["metadata"].update(gravity_unit=unit, gravity_sign="upward" if sign < 0 else "downward")
        for row in converted["stations"]:
            row["original_value"] /= factor * sign
            row["gravity_sigma"] /= factor
        other = process_survey(converted, config())
        np.testing.assert_allclose(other["qc"]["derived_mgal"], result["qc"]["derived_mgal"], atol=1e-8, rtol=0)
        np.testing.assert_allclose(
            other["processing"]["uncertainty_mgal"], result["processing"]["uncertainty_mgal"], atol=1e-12
        )


def test_no_double_correction():
    first = process_survey(survey(), config())
    for target in ("gravity_disturbance", "bouguer_disturbance"):
        with pytest.raises(GravityContractError, match="double correction"):
            process_survey(first["dataset"], config(target))
    damaged = deepcopy(first["dataset"])
    damaged["history"].append(deepcopy(damaged["history"][-1]))
    with pytest.raises(GravityContractError, match="correction count"):
        process_survey(damaged, config("terrain_adjusted_disturbance", terrain=terrain(damaged["stations"])))
    for mutation in ("hash", "order", "value"):
        damaged = deepcopy(first["dataset"])
        if mutation == "hash":
            damaged["history"][0]["output_values_sha256"] = "0" * 64
        elif mutation == "order":
            damaged["history"][0]["name"] = "free_air"
        else:
            damaged["stations"][0]["value_mgal"] += 1
        with pytest.raises(GravityContractError):
            process_survey(damaged, config("terrain_adjusted_disturbance", terrain=terrain(damaged["stations"])))
    with pytest.raises(GravityContractError, match="changed prior parameters"):
        process_survey(
            first["dataset"],
            config(
                "terrain_adjusted_disturbance",
                density_kg_m3=2500,
                terrain=terrain(first["dataset"]["stations"], density_kg_m3=2500),
            ),
        )
    ambiguous = survey()
    ambiguous["history"] = [{"name": "provider_free_air"}]
    with pytest.raises(GravityContractError, match="correction count"):
        process_survey(ambiguous, config())


@pytest.mark.parametrize(
    "field,value",
    [
        ("latitude_deg", 91),
        ("longitude_deg", -181),
        ("gravity_sigma", -1),
        ("original_value", float("nan")),
        ("surface_height_m", -1),
        ("receiver_height_m", -1),
        ("latitude_sigma_deg", True),
        ("value_mgal", float("inf")),
    ],
)
def test_invalid_contract(field, value):
    data = survey()
    data["stations"][0][field] = value
    with pytest.raises(GravityContractError, match=field):
        process_survey(data, config())


@pytest.mark.parametrize(
    "field,value",
    [
        ("gravity_unit", "Gal"),
        ("gravity_sign", "unknown"),
        ("height_datum", "sea_level"),
        ("crs", "local"),
        ("tide_system", "unknown"),
        ("gravity_quantity", "relative_meter_counts"),
        ("source_sha256", "unknown"),
    ],
)
def test_invalid_metadata(field, value):
    data = survey()
    data["metadata"][field] = value
    with pytest.raises(GravityContractError, match=field):
        process_survey(data, config())


def test_duplicate_and_unapplied_instrument():
    data = survey(2)
    data["stations"][1]["longitude_deg"] = 0.0
    with pytest.raises(GravityContractError, match="duplicate"):
        process_survey(data, config())
    for name in ("calibration", "drift", "tide"):
        data = survey()
        data["metadata"]["instrument_processing"][name]["status"] = "unknown"
        with pytest.raises(GravityContractError, match=name):
            process_survey(data, config())
    data = survey()
    data["metadata"]["corrections"] = "already Bouguer"
    with pytest.raises(GravityContractError, match="unknown"):
        process_survey(data, config())


def test_height_datum_and_uncertainty():
    data = survey()
    data["metadata"].update(height_datum="orthometric", geoid_model="Authored constant 30-m control")
    row = data["stations"][0]
    row.update(
        receiver_height_m=970,
        surface_height_m=870,
        geoid_m=30,
        geoid_sigma_m=2,
        receiver_sigma_m=0.5,
        surface_sigma_m=0.7,
        latitude_sigma_deg=0.0002,
    )
    cfg = config(density_sigma_kg_m3=20, uncertainty_model="independent_first_order")
    result = process_survey(data, cfg)
    same = deepcopy(data)
    same["metadata"]["height_datum"] = "ellipsoidal"
    del same["metadata"]["geoid_model"]
    same["stations"][0].update(receiver_height_m=1000, surface_height_m=900)
    del same["stations"][0]["geoid_m"]
    del same["stations"][0]["geoid_sigma_m"]
    np.testing.assert_allclose(
        result["qc"]["derived_mgal"], process_survey(same, cfg)["qc"]["derived_mgal"], atol=1e-10
    )
    components = result["processing"]["uncertainty_components_mgal"]
    assert components["density"][0] == pytest.approx(COEFFICIENT * 900 * 20, abs=1e-12)
    assert components["surface_height"][0] == pytest.approx(COEFFICIENT * 2670 * 0.7, abs=1e-12)
    # Independent backward derivative from the official published 45-degree
    # table at h=777.777..., 888.888..., 1000 m, not production engine calls.
    gradient = -(3 * 980311.28969268 - 4 * 980345.55889093 + 980379.82987947) / (2 * (1000 / 9))
    assert components["receiver_height"][0] == pytest.approx(gradient * 0.5, abs=3e-7)
    assert components["geoid"][0] == pytest.approx((gradient - COEFFICIENT * 2670) * 2, abs=1.2e-6)
    expected = math.sqrt(sum(v[0] ** 2 for v in components.values()))
    assert result["processing"]["uncertainty_mgal"][0] == pytest.approx(expected)
    conservative = process_survey(data, {**cfg, "uncertainty_model": "conservative_marginals"})
    assert conservative["processing"]["uncertainty_mgal"][0] == pytest.approx(sum(v[0] for v in components.values()))
    del data["stations"][0]["geoid_m"]
    with pytest.raises(GravityContractError, match="geoid_m"):
        process_survey(data, cfg)


def test_terrain_semantics():
    data = survey()
    base = process_survey(data, config())
    supplied = terrain(data["stations"], additions_mgal=[-2.0])
    result = process_survey(base["dataset"], config("terrain_adjusted_disturbance", terrain=supplied))
    assert result["qc"]["derived_mgal"][0] == pytest.approx(base["qc"]["derived_mgal"][0] - 2)
    assert result["processing"]["uncertainty_mgal"][0] == pytest.approx(0.3)
    for key, value in (
        ("kind", "total_topographic_effect"),
        ("density_kg_m3", 2500),
        ("height_reference", "sea_level"),
        ("station_ids", ["wrong"]),
        ("sigma_mgal", [-1]),
        ("source_sha256", "missing"),
    ):
        with pytest.raises(GravityContractError, match=key):
            process_survey(data, config("terrain_adjusted_disturbance", terrain={**supplied, key: value}))
    with pytest.raises(GravityContractError, match="conservative_marginals"):
        process_survey(
            data, config("terrain_adjusted_disturbance", terrain=supplied, uncertainty_model="independent_first_order")
        )


def test_uncertainty_reference_cancellation_and_poles():
    data = survey()
    data["stations"][0].update(gravity_sigma=0, latitude_sigma_deg=0.001)
    # Analytical latitude derivative of the independent Somigliana oracle.
    f, ge, gp = 1 / 298.257223563, 9.7803253359, 9.8321849378
    k, e2 = (1 - f) * gp / ge - 1, 2 * f - f**2
    s = math.sin(math.radians(45)) ** 2
    ds = math.sin(2 * math.radians(45)) * math.pi / 180
    derivative = ge * 1e5 * ds * (k / math.sqrt(1 - e2 * s) + (1 + k * s) * e2 / (2 * (1 - e2 * s) ** 1.5))
    result = process_survey(data, config("gravity_disturbance", uncertainty_model="independent_first_order"))
    assert result["processing"]["uncertainty_mgal"][0] == pytest.approx(derivative * 0.001, abs=1e-8)
    for latitude in (-90, 90):
        data["stations"][0]["latitude_deg"] = latitude
        result = process_survey(data, config("gravity_disturbance"))
        assert np.isfinite(result["processing"]["uncertainty_mgal"][0])
        assert result["processing"]["uncertainty_mgal"][0] < 1e-6


def test_config_and_resume_metadata_rejection():
    for changes in (
        {"uncertainty_model": "guessed"},
        {"target": "free_air"},
        {"density_kg_m3": -1},
        {"density_sigma_kg_m3": -1},
        {"outlier_z": 0.5},
    ):
        with pytest.raises(GravityContractError, match="config"):
            process_survey(survey(), config(**changes))
    with pytest.raises(GravityContractError, match="explicit plate density"):
        process_survey(survey(), {"target": "bouguer_disturbance", "uncertainty_model": "conservative_marginals"})
    with pytest.raises(GravityContractError, match="terrain"):
        process_survey(survey(), config("terrain_adjusted_disturbance"))
    first = process_survey(survey(), config("gravity_disturbance"))["dataset"]
    first["stations"][0]["receiver_height_m"] = 10
    with pytest.raises(GravityContractError, match="do not reconstruct"):
        process_survey(first, config())


def test_worked_request_is_synthetic_and_closes_formula():
    example = ROOT / "docs/methods/gravity-processing/examples/station-control.json"
    request = json.loads(example.read_text(encoding="utf-8"))
    assert request["dataset"]["metadata"]["source_kind"] == "synthetic_control"
    definition = b"M01 synthetic: phi=45; h=t=1000 m; rho=2670 kg/m3; residual=12 mGal"
    assert request["dataset"]["metadata"]["source_sha256"] == sha256(definition).hexdigest()
    result = process_survey(**request)
    assert result["qc"]["derived_mgal"] == pytest.approx([12], abs=1e-8)
    assert result["processing"]["full_method_accepted"] is False


@pytest.mark.skipif(
    not os.environ.get("M01_PRINCIPAL_FACT_ARCHIVE"),
    reason="Attributed field archive is a separate source acquisition, not a synthetic substitute",
)
def test_author_principal_fact_bytes_require_physical_metadata():
    """Read one real member in memory, without extraction or a source profile.

    This is a negative admission gate. No height, instrument status or error
    value is invented to make the author's processed principal facts eligible.
    """
    with zipfile.ZipFile(os.environ["M01_PRINCIPAL_FACT_ARCHIVE"]) as archive:
        names = [n for n in archive.namelist() if n == "data/ground_gravity_data.csv"]
        assert len(names) == 1
        assert archive.getinfo(names[0]).file_size == 335377
        raw = archive.read(names[0])
    member_hash = sha256(raw).hexdigest()
    assert member_hash == "7cb3ed0c3cbac60f896a11f213ba40209c3083cb7635ab80ab7c0fd0382a1055"
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    assert reader.fieldnames == [
        "",
        "Station_ID",
        "lonWGS84",
        "latWGS84",
        "xWGS84_UTM10N",
        "yWGS84_UTM10N",
        "zWGS84",
        "OG",
        "FAA",
        "SBA",
        "TTC",
        "CBA",
        "ISO",
    ]
    first = next(reader)
    original = deepcopy(first)
    # Retain known source evidence only; unknown physical metadata stays absent.
    dataset = {
        "schema_version": "gravity-stations-1",
        "state": "observed_absolute",
        "history": [],
        "metadata": {
            "source_kind": "field",
            "source_sha256": member_hash,
            "source_citation": "Attributed author compiled principal facts, Zenodo 16975696 v2",
            "rights": "CC BY 4.0, author attribution required",
        },
        "stations": [first],
    }
    with pytest.raises(GravityContractError) as rejected:
        process_survey(dataset, config())
    for key in ("height_datum", "instrument_processing", "gravity_quantity", "tide_system"):
        assert key in str(rejected.value)
    assert first == original
    assert first["OG"] == "979999.22" and first["CBA"] == "6.67"
    assert "zWGS84" in first and "receiver_height_m" not in first


def test_qc_preserves_outliers():
    data = survey(7)
    data["stations"][-1]["original_value"] += 100
    data["stations"][-1]["value_mgal"] += 100
    result = process_survey(data, config("gravity_disturbance"))
    assert result["qc"]["outlier_flag"] == [False] * 6 + [True]
    assert len(result["dataset"]["stations"]) == 7
    assert result["qc"]["excluded_station_ids"] == []
    assert result["qc"]["longitude_deg"] == list(range(7))
    assert result["dataset"]["stations"][-1]["original_value"] == data["stations"][-1]["original_value"]


def test_cli_roundtrip(tmp_path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"dataset": survey(), "config": config()}), encoding="utf-8")
    original = source.read_bytes()
    receipts = []
    for name in ("first", "second"):
        args = [
            sys.executable,
            str(ROOT / "data-pipeline/gravity_processing.py"),
            "--input",
            str(source),
            "--output-dir",
            str(tmp_path / name),
        ]
        run = subprocess.run(args, capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr
        receipt = json.loads(run.stdout)
        assert receipt["input_file_sha256"] == sha256(original).hexdigest()
        assert (
            receipt["result_file_sha256"] == sha256((tmp_path / name / "gravity-result.json").read_bytes()).hexdigest()
        )
        receipts.append(receipt)
    assert receipts[0]["result_file_sha256"] == receipts[1]["result_file_sha256"]
    repeat = subprocess.run(args, capture_output=True, text=True, timeout=60)
    assert repeat.returncode == 2 and "overwrite forbidden" in repeat.stderr
    assert source.read_bytes() == original
    source.write_text('{"dataset":{},"dataset":{},"config":{}}', encoding="utf-8")
    args[-1] = str(tmp_path / "invalid")
    invalid = subprocess.run(args, capture_output=True, text=True, timeout=60)
    assert invalid.returncode == 2 and "duplicate key" in invalid.stderr
    assert not (tmp_path / "invalid").exists()
    args[-1] = str(ROOT / "data/derived/M01-test-forbidden")
    forbidden = subprocess.run(args, capture_output=True, text=True, timeout=60)
    assert forbidden.returncode == 2 and "ignored" in forbidden.stderr


def test_wiki_contract():
    folder = ROOT / "docs/methods/gravity-processing"
    text = (folder / "01_station-corrections.md").read_text(encoding="utf-8")
    assert all(s in text for s in ("gamma", "uncertainty", "other data", "Full M01", "https://www.fatiando.org"))
    svg = ET.parse(folder / "station-corrections.svg")
    assert svg.getroot().attrib["viewBox"] == "0 0 960 620"
    assert "var(--" in (folder / "station-corrections.svg").read_text(encoding="utf-8")
    assert len(svg.findall(".//{http://www.w3.org/2000/svg}text")) >= 15
