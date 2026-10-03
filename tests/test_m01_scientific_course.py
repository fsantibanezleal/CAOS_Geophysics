"""M01 course gates and (after test-first approval) an owned record producer.

Existing science is imported, never replaced. All controls are authored, not
field observations. Source assertions do not certify product/browser QA.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import harmonica as hm
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from gravity_processing import GravityContractError, digest, normal_gravity, process_survey
from gravity_station_adapter import run_station_corrections
from gravity_transform_controls import control_request, prism_integral
from gravity_transforms import admit, fit_layer, read_request, replay_grid, transform_survey

COURSE = ROOT / "docs/methods/gravity-processing/scientific-course"
FEATURE = ROOT / "docs/design/features/m01-scientific-course"
WEB = ROOT / "frontend/public/data/m01-scientific-course"
INDEX = ROOT / "frontend/src/data/m01-course-record-index.json"
PINS = {
    "gravity_processing.py": "7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321",
    "gravity_station_adapter.py": "b770b16ef87e83dd92f65a90472145ef93a525a9cedf7f55ee3e6f20f8a10cf8",
    "gravity_transforms.py": "d11d0f207c89c308c9f8711da2a31b84b8adaeb0c12597a5ecc89ce527fdecf0",
    "gravity_transform_controls.py": "5ed27d94f55adbfbfabb7db7371affacd42b1d0bb1887ed2322fc36df077afc9",
    "gravity_transform_figures.py": "4a529f2f19bce53ea80d14c007a43d65f99cbd707ad49e2e9bb3cfbf3c96a273",
}
ENGINES = {"boule": "0.5.0", "harmonica": "0.7.0", "numpy": "2.2.6",
           "scipy": "1.15.2", "verde": "1.9.0", "scikit-learn": "1.9.1",
           "matplotlib": "3.10.8"}
ROLES = {
    "request": "request.json", "result": "result.json", "export_receipt": "receipt.json",
    "map_light": "maps-light.svg", "map_dark": "maps-dark.svg",
    "diagnostics_light": "diagnostics-light.svg", "diagnostics_dark": "diagnostics-dark.svg",
    "map_light_png": "maps-light.png", "map_dark_png": "maps-dark.png",
    "diagnostics_light_png": "diagnostics-light.png", "diagnostics_dark_png": "diagnostics-dark.png",
}
IDS = tuple(f"prism-case-{i}" for i in range(3))
CHAPTERS = ("01_quantity-and-reference", "02_plate-and-terrain",
            "03_uncertainty-and-covariance", "04_equivalent-layer",
            "05_spatial-validation", "06_continuation-and-limits")
G = 6.67430e-11
C = 2 * math.pi * G * 1e5


@pytest.fixture(scope="module")
def controls():
    return [control_request(case=i, noisy=True) for i in range(3)]


@pytest.fixture(scope="module")
def records():
    assert INDEX.is_file(), "Actual course records have not been produced/published."
    catalogue = read_request(INDEX)
    assert type(catalogue) is list and len(catalogue) == 3
    return [(read_request(WEB / item["scenario_id"] / "request.json"),
             read_request(WEB / item["scenario_id"] / "result.json"),
             item) for item in catalogue]


def parent_from_control(request):
    parent = deepcopy(request["correction_result"]["dataset"])
    parent.update(state="observed_absolute", history=[])
    for row in parent["stations"]:
        row["value_mgal"] = row["original_value"]
    return parent


def adapter_request(parent, config):
    return {"schema_version": "gravity-station-adapter-request-1",
            "method": "gravity.station-corrections/v1", "dataset": parent,
            "config": config, "input_dataset_sha256": digest(parent),
            "submitted_config_sha256": digest(config)}


def somigliana(latitude):
    f, ge, gp = 1 / 298.257223563, 9.7803253359, 9.8321849378
    k, e2 = (1 - f) * gp / ge - 1, 2 * f - f**2
    s = np.sin(np.radians(latitude))**2
    return ge * (1 + k * s) / np.sqrt(1 - e2 * s) * 1e5


def test_scope_and_acceptance_boundaries(controls):
    for name, pin in PINS.items():
        assert sha256((ROOT / "data-pipeline" / name).read_bytes()).hexdigest() == pin
    for request, _ in controls:
        corrected = request["correction_result"]
        assert corrected["dataset"]["metadata"]["source_kind"] == "synthetic_control"
        assert corrected["processing"]["full_method_accepted"] is False
        assert corrected["qc"]["excluded_station_ids"] == []
    narrative = (COURSE / "README.md").read_text(encoding="utf-8")
    assert "field" in narrative and "M01" in narrative


def test_reference_height_formula_and_no_double_correction(controls):
    latitude = np.array([-90, -60, -45, 0, 45, 60, 90])
    np.testing.assert_allclose(normal_gravity(latitude, 0), somigliana(latitude),
                               rtol=0, atol=1e-5)
    assert float(normal_gravity(45, 1000)) == pytest.approx(980311.28969268, abs=1e-7)
    parent = parent_from_control(controls[0][0])
    row = parent["stations"][0]
    row.update(latitude_deg=45.0, receiver_height_m=1000.0,
               original_value=980311.28969268, value_mgal=980311.28969268)
    cfg = {"target": "gravity_disturbance", "uncertainty_model": "independent_first_order"}
    result = process_survey(parent, cfg)
    assert result["qc"]["derived_mgal"][0] == pytest.approx(0, abs=1e-7)
    assert result["dataset"]["history"][1]["additions_mgal"][0] == pytest.approx(308.48724505, abs=1e-7)
    with pytest.raises(GravityContractError, match="double correction"):
        process_survey(result["dataset"], cfg)


def test_datum_plate_and_supplied_terrain_contract(controls):
    parent = parent_from_control(controls[0][0])
    parent["metadata"].update(height_datum="orthometric", geoid_model="Authored constant N=30 m")
    for row in parent["stations"]:
        row.update(receiver_height_m=970.0, surface_height_m=870.0, geoid_m=30.0, geoid_sigma_m=0.0)
    cfg = {"target": "bouguer_disturbance", "uncertainty_model": "conservative_marginals",
           "density_kg_m3": 2670.0, "density_sigma_kg_m3": 0.0}
    result = process_survey(parent, cfg)
    assert result["qc"]["surface_ellipsoidal_m"] == [900.0] * 196
    assert result["dataset"]["history"][2]["additions_mgal"][0] == pytest.approx(-C * 2670 * 900, abs=1e-10)
    ids = [r["station_id"] for r in parent["stations"]]
    terrain = {"kind": "additive_residual_to_plate", "unit": "mGal",
               "height_reference": "WGS84_ellipsoid", "density_kg_m3": 2670.0,
               "source_sha256": digest({"authored": "signed residual"}), "method": "Authored T=B-A_topo, no DEM",
               "station_ids": ids, "additions_mgal": [-2.0] * 196, "sigma_mgal": [0.2] * 196}
    resumed = process_survey(result["dataset"], {**cfg, "target": "terrain_adjusted_disturbance", "terrain": terrain})
    np.testing.assert_allclose(resumed["qc"]["derived_mgal"], np.array(result["qc"]["derived_mgal"]) - 2, rtol=0, atol=1e-10)
    process_survey(parent, {**cfg, "terrain": None})  # null is valid for nonterrain
    for key, value in (("kind", "DEM_effect"), ("density_kg_m3", 2500),
                       ("height_reference", "unknown"), ("station_ids", ids[::-1])):
        with pytest.raises(GravityContractError):
            process_survey(parent, {**cfg, "target": "terrain_adjusted_disturbance", "terrain": {**terrain, key: value}})
    with pytest.raises(GravityContractError):
        process_survey(parent, {**cfg, "terrain": terrain})


def test_covariance_and_marginal_bound_definitions(controls):
    parent = parent_from_control(controls[0][0])
    parent["metadata"].update(height_datum="orthometric", geoid_model="Authored N, not a surveyed geoid")
    for row in parent["stations"]:
        row.update(latitude_deg=45.0, receiver_height_m=970.0, surface_height_m=870.0,
                   geoid_m=30.0, geoid_sigma_m=2.0, receiver_sigma_m=0.5, surface_sigma_m=0.7,
                   latitude_sigma_deg=0.0002)
    cfg = {"target": "bouguer_disturbance", "uncertainty_model": "independent_first_order",
           "density_kg_m3": 2670.0, "density_sigma_kg_m3": 20.0}
    result = process_survey(parent, cfg)
    components = result["processing"]["uncertainty_components_mgal"]
    gradient = -(3 * 980311.28969268 - 4 * 980345.55889093 + 980379.82987947) / (2 * (1000 / 9))
    assert components["geoid"][0] == pytest.approx((gradient - C * 2670) * 2, abs=1.2e-6)
    assert components["density"][0] == pytest.approx(C * 900 * 20, abs=1e-12)
    assert result["processing"]["uncertainty_mgal"][0] == pytest.approx(math.sqrt(sum(v[0]**2 for v in components.values())))
    bound = process_survey(parent, {**cfg, "uncertainty_model": "conservative_marginals"})
    assert bound["processing"]["uncertainty_mgal"][0] == pytest.approx(sum(v[0] for v in components.values()))
    # Rank-one shared density covariance: off-diagonal is not zero.
    u = C * np.array([900.0, 800.0]) * 20
    shared = np.outer(u, u)
    assert shared[0, 1] > 0 and np.linalg.eigvalsh(shared).min() > -1e-12
    del parent["stations"][0]["geoid_sigma_m"]
    with pytest.raises(GravityContractError):
        process_survey(parent, cfg)


def test_scalar_kernel_regularization_and_nonuniqueness(controls, records):
    for (request, truth), (_, result, _) in zip(controls, records, strict=True):
        coords = truth["coordinates"]
        independent = prism_integral(coords, truth["prisms"], truth["densities"], order=22)
        analytic = hm.prism_gravity(coords, truth["prisms"], truth["densities"], field="g_z", parallel=False)
        assert np.max(np.abs(independent - truth["true_observed_mgal"])) < 1e-7
        assert np.max(np.abs(independent - analytic)) < 1e-7
        points = tuple(np.asarray(p) for p in result["model"]["points_m"])
        j = hm.EquivalentSources(parallel=False).jacobian(tuple(c[:12] for c in coords), points)
        oracle = 1 / np.sqrt(sum((c[:12, None] - p[None, :])**2 for c, p in zip(coords, points, strict=True)))
        np.testing.assert_allclose(j, oracle, rtol=0, atol=1e-12)
        fits = [a for a in result["nonuniqueness"]["training_only_alternatives"]
                if a["status"] == "passed" and a["training_rmse_mgal"] < 0.02]
        assert len({a["depth_m"] for a in fits}) >= 2
        assert max(a["coefficient_l2_mgal_m"] for a in fits) > 2 * min(a["coefficient_l2_mgal_m"] for a in fits)
        assert "not density" in result["model"]["interpretation"]
    request, _ = controls[0]
    coords, values, sigma, covariance, active = admit(request)
    idx = active[:24]
    xyz = tuple(c[idx] for c in coords)
    engine, scale, transfer, _ = fit_layer(xyz, values[idx], sigma[idx], 360, 100, 1e10)
    j = engine.jacobian(xyz, engine.points_)
    direct = np.linalg.solve(j.T @ (j / sigma[idx, None]**2) + 100 * np.diag(scale**2), j.T / sigma[idx]**2)
    target = (xyz[0][:5], xyz[1][:5], np.full(5, 600.0))
    left = (engine.jacobian(target, engine.points_) / scale) @ transfer
    right = engine.jacobian(target, engine.points_) @ direct
    np.testing.assert_allclose(left, right, rtol=1e-7, atol=1e-9)
    cov = covariance[np.ix_(idx, idx)]
    np.testing.assert_allclose(left @ cov @ left.T, right @ cov @ right.T, rtol=1e-7, atol=1e-12)


def test_blocked_training_only_selection(controls, records):
    for _, result, _ in records:
        split = result["split"]
        blocks = dict(zip(split["active_indices"], split["block_ids_active"], strict=True))
        assert {blocks[i] for i in split["train_indices"]}.isdisjoint(blocks[i] for i in split["holdout_indices"])
        for candidate in result["selection"]["candidates"]:
            for fold in candidate["folds"]:
                assert set(fold["train_indices"]).isdisjoint(fold["validation_indices"])
                assert set(fold["train_indices"] + fold["validation_indices"]) <= set(split["train_indices"])
    request = deepcopy(controls[0][0])
    result = records[0][1]
    parent = parent_from_control(request)
    for i in result["split"]["holdout_indices"]:
        parent["stations"][i]["original_value"] += 7
        parent["stations"][i]["value_mgal"] = parent["stations"][i]["original_value"]
    request["correction_result"] = process_survey(parent, request["correction_result"]["processing"]["config"])
    changed = transform_survey(request)
    for key in ("selection", "model", "grids", "nonuniqueness"):
        assert changed[key] == result[key]
    assert changed["evaluation"]["holdout"]["rmse_mgal"] > 6


def test_continuation_support_height_and_residual_sign(controls, records):
    for (_, truth), (request, result, _) in zip(controls, records, strict=True):
        assert result["evaluation"]["holdout"]["covered_count"] >= 20
        assert result["evaluation"]["holdout"]["rmse_mgal"] < 0.1
        s = result["stations"]
        for i, covered in enumerate(s["prediction_covered"]):
            if covered:
                assert s["signed_predicted_minus_observed_mgal"][i] == pytest.approx(s["predicted_mgal"][i] - s["observed_mgal"][i], abs=1e-12)
            else:
                assert s["predicted_mgal"][i] is None
            if request["geometry"]["mask"][i]:
                assert result["split"]["partition"][i] == "masked" and not covered
        xx, yy = np.meshgrid(result["axes"]["easting_m"], result["axes"]["northing_m"])
        for i, grid in enumerate(result["grids"]):
            assert replay_grid(result, i) == pytest.approx(grid["predicted_mgal"], nan_ok=True)
            for keep, h, r, v, sd in zip(grid["covered"], grid["outside_hull"], grid["outside_radius"],
                                       grid["predicted_mgal"], grid["conditional_sigma_mgal"], strict=True):
                assert keep == (not h and not r)
                assert (v is not None and sd is not None) == keep
            idx = np.flatnonzero(grid["covered"])[::13]
            oracle = prism_integral((xx.ravel()[idx], yy.ravel()[idx], np.full(len(idx), grid["height_m"])),
                                    truth["prisms"], truth["densities"], order=22)
            assert np.sqrt(np.mean((np.array(grid["predicted_mgal"], dtype=float)[idx] - oracle)**2)) < 0.1
        assert result["uncertainty"]["kind"] == "conditional_linear_noise_propagation"
        assert result["selection"]["height_m"] == min(g["height_m"] for g in result["grids"] if g["height_precision_passed"])


def test_explanatory_controls_not_physical_jobs():
    component = (ROOT / "frontend/src/components/M01CourseExercise.tsx").read_text(encoding="utf-8")
    data = (ROOT / "frontend/src/data/m01-scientific-course.ts").read_text(encoding="utf-8")
    assert all(e in data for e in ("E01", "E02", "E03", "E04"))
    assert "Apply" in component and "Reset" in component and "explanatory" in component.lower()
    assert "fetch(" not in component and "submitJob" not in component
    assert "calculateExplanation" in data


def test_recorded_scenario_identity_and_stale_negatives(records, controls):
    catalogue = read_request(INDEX)
    for i, (request, result, item) in enumerate(records):
        validate_record(item, WEB)
        assert digest(request) == digest(controls[i][0])
        assert result == transform_survey(request)
    assert len({i["request_sha256"] for i in catalogue}) == 3
    assert len({i["result_sha256"] for i in catalogue}) == 3
    original = catalogue[0]
    for key, value in (("scenario_id", "unknown"), ("source_pins", {**PINS, "gravity_processing.py": "0"*64}),
                       ("request_sha256", "0"*64), ("result_sha256", "0"*64),
                       ("extra", "forbidden")):
        bad = deepcopy(original)
        bad[key] = value
        with pytest.raises(ValueError):
            validate_record(bad, WEB)
    for key, value in (("bytes", original["artifacts"][0]["bytes"] + 1), ("sha256", "0"*64),
                       ("path", "../request.json"), ("role", "unknown")):
        bad = deepcopy(original)
        bad["artifacts"][0][key] = value
        with pytest.raises(ValueError):
            validate_record(bad, WEB)


def test_user_file_workflow_and_parent_identity(controls, tmp_path):
    request = controls[0][0]
    parent = parent_from_control(request)
    config = {"target": "gravity_disturbance", "uncertainty_model": "independent_first_order"}
    selected = tmp_path / "user-selected-authored.json"
    selected.write_text(json.dumps({"dataset": parent, "config": config}), encoding="utf-8")
    loaded = read_request(selected)
    before = selected.read_bytes()
    result = run_station_corrections(adapter_request(loaded["dataset"], loaded["config"]))
    assert result["correction_result"] == process_survey(parent, config)
    assert result["receipt"]["acceptance"] == {"host_approved": False, "full_method_accepted": False, "field_source_verified": False}
    assert selected.read_bytes() == before
    absent = tmp_path / "absent.json"
    with pytest.raises(OSError):
        read_request(absent)
    assert not absent.exists()
    parent["stations"][0].update(original_value=980000.0, value_mgal=980000)
    native = run_station_corrections(adapter_request(parent, config))["correction_result"]
    assert native["processing"]["input_sha256"] == digest(parent)
    unreconstructable = {**request, "correction_result": native}
    with pytest.raises(GravityContractError, match="exact parent needed"):
        admit(unreconstructable)
    for chapter in COURSE.glob("*.md"):
        for block in chapter.read_text(encoding="utf-8").split("```python\n")[1:]:
            compile(block.split("```")[0], str(chapter), "exec")


def test_bilingual_questions_equations_and_physical_figures():
    for name in CHAPTERS:
        text = (COURSE / f"{name}.md").read_text(encoding="utf-8")
        assert "## English" in text and "## Español" in text
        assert "https://" in text and r"\[" in text
    assets = list((COURSE / "assets").glob("*.svg"))
    assert len(assets) == 6 and len({sha256(p.read_bytes()).hexdigest() for p in assets}) == 6
    for path in assets:
        svg = ET.parse(path).getroot()
        assert svg.get("viewBox") and svg.find("{http://www.w3.org/2000/svg}title") is not None
        assert "var(--" in path.read_text(encoding="utf-8")


def test_shared_shell_and_scoped_mount():
    for name in ("M01ScientificCourse", "M01CourseDiagram", "M01CourseExercise"):
        text = (ROOT / f"frontend/src/components/{name}.tsx").read_text(encoding="utf-8")
        assert "@fasl-work/caos-app-shell" in text
        assert ".css" not in text and "@font-face" not in text
    assert "Research.tsx" in (FEATURE / "tasks.md").read_text(encoding="utf-8")
    # This gate only checks source integration discipline, NOT the MAIN-owned
    # mount or actual rendered product QA, which require separate receipts.


def test_negative_controls_and_field_gate(controls):
    request = controls[0][0]
    for section, key, value in (("geometry", "coordinate_unit", "km"), ("geometry", "data_unit", "microGal"),
                                ("geometry", "component", "g_z_upward"), ("config", "heights_m", [100.0])):
        bad = deepcopy(request)
        bad[section][key] = value
        with pytest.raises(GravityContractError):
            admit(bad)
    for key in ("easting_m", "northing_m", "upward_m"):
        bad = deepcopy(request)
        bad["geometry"][key][83] = None
        with pytest.raises(GravityContractError):
            admit(bad)
    for section, key in (("metadata", "height_datum"), ("stations", "gravity_sigma")):
        parent = parent_from_control(request)
        del (parent[section] if section == "metadata" else parent[section][0])[key]
        with pytest.raises(GravityContractError):
            process_survey(parent, request["correction_result"]["processing"]["config"])
    parent = parent_from_control(request)
    for row in parent["stations"]:
        row["gravity_sigma"] = 1.0
    noisy = deepcopy(request)
    noisy["correction_result"] = process_survey(parent, request["correction_result"]["processing"]["config"])
    with pytest.raises(GravityContractError, match="noise"):
        admit(noisy)
    stale = deepcopy(request)
    stale["correction_result"]["processing"]["input_sha256"] = "0"*64
    with pytest.raises(GravityContractError):
        admit(stale)
    assert request["correction_result"]["processing"]["full_method_accepted"] is False
    # No private field bytes or fabricated field SD/datum are consumed here.


def test_stage_authorization_and_nonclaims():
    text = (FEATURE / "tasks.md").read_text(encoding="utf-8")
    assert "96b583eefad4e8c8c4281800df219432c3b5a45e" in text
    assert "--produce-course-records OUTPUT_ROOT" in text and "explicitly authorized" in text
    assert "MAIN" in text and "ledger" in text
