"""Real pinned engines versus independent volume physics; no field surrogate gate."""

from copy import deepcopy
from hashlib import sha256
import json
import io
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import harmonica as hm
import numpy as np
import pytest
import gravity_transforms as transforms

from gravity_processing import GravityContractError, digest, process_survey
from gravity_transform_controls import control_request, prism_integral
from gravity_transforms import admit, export_bundle, fit_layer, read_request, replay_grid, transform_survey

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def controls():
    return [control_request(case) for case in range(3)]


@pytest.fixture(scope="module")
def results(controls):
    return [transform_survey(request) for request, _ in controls]


def rebuild(request, indices, delta=0, sigma=None):
    result = deepcopy(request)
    old = result["correction_result"]
    original = deepcopy(old["dataset"])
    original.update(state="observed_absolute", history=[])
    for index, row in enumerate(original["stations"]):
        if index in indices:
            row["original_value"] += delta
            if sigma is not None:
                row["gravity_sigma"] = sigma
        row["value_mgal"] = row["original_value"]
    result["correction_result"] = process_survey(original, old["processing"]["config"])
    return result


def test_contract_lineage_and_originals(controls, results):
    for (request, _), result in zip(controls, results, strict=True):
        before = digest(request)
        admit(request)
        assert digest(request) == before
        assert result["original_correction_result"] == request["correction_result"]
        assert result["geometry"] == request["geometry"]
        assert result["provenance"]["corrections_reapplied"] is False
        assert result["provenance"]["full_method_accepted"] is False
        assert result["provenance"]["field_gate"] == "open"
        assert result["stations"]["observed_mgal"] == [
            r["value_mgal"] for r in request["correction_result"]["dataset"]["stations"]
        ]
        for index, mask in enumerate(request["geometry"]["mask"]):
            if mask:
                assert result["split"]["partition"][index] == "masked"
                assert result["stations"]["predicted_mgal"][index] is None
    corrupted = deepcopy(controls[0][0])
    corrupted["correction_result"]["dataset"]["stations"][0]["value_mgal"] += 0.1
    with pytest.raises(GravityContractError, match="history|lineage|hash"):
        admit(corrupted)


@pytest.mark.parametrize(
    "key,value",
    [
        ("method", "renamed-correction-method"),
        ("input_sha256", "0" * 64),
        ("input_sha256", ["0" * 64]),
        ("module_sha256", "0" * 64),
        ("output_sha256", "1" * 64),
        ("python", "3.11.10"),
        ("python", "3.12.nan"),
        ("python", "3.12.10-stale"),
        ("full_method_accepted", True),
        ("full_method_accepted", 0),
        ("warnings", []),
        ("engines", {"boule": "unreviewed engine"}),
        (
            "config",
            {
                "target": "gravity_disturbance",
                "uncertainty_model": "independent_first_order",
                "unknown_config_key": "forbidden",
            },
        ),
        ("uncertainty_model", "conservative_marginals"),
        ("uncertainty_mgal", [123.0] * 196),
        ("uncertainty_components_mgal", {"unknown": [0.0] * 196}),
        ("unexpected", "unverified provenance"),
    ],
)
def test_full_processing_identity(key, value, controls):
    request = deepcopy(controls[0][0])
    request["correction_result"]["processing"][key] = value
    if key != "output_sha256":
        request["correction_result"]["processing"]["output_sha256"] = digest(request["correction_result"]["dataset"])
    # Rehashing the container does not make stale inner provenance verifiable.
    assert len(digest(request)) == 64
    with pytest.raises(GravityContractError, match="processing|receipt|config"):
        admit(request)
    missing = deepcopy(controls[0][0])
    del missing["correction_result"]["processing"][key if key != "unexpected" else "warnings"]
    with pytest.raises(GravityContractError, match="processing"):
        admit(missing)


def test_reconstructable_resume_and_python_provenance(controls):
    request = deepcopy(controls[0][0])
    original_python = request["correction_result"]["processing"]["python"]
    declared_patch = "3.12.11" if original_python != "3.12.11" else "3.12.10"
    first_parent = deepcopy(request["correction_result"]["dataset"])
    request["correction_result"] = process_survey(
        first_parent,
        {
            "target": "bouguer_disturbance",
            "density_kg_m3": 2670.0,
            "density_sigma_kg_m3": 0.0,
            "uncertainty_model": "independent_first_order",
        },
    )
    request["correction_result"]["processing"]["python"] = declared_patch
    identity = admit(request, return_identity=True)[-1]
    assert identity["input_state"] == "gravity_disturbance"
    assert identity["input_sha256"] == digest(first_parent)
    assert identity["recorded_python"] == declared_patch
    assert identity["recorded_runtime_origin_verified"] is False
    result = transform_survey(request)
    assert result["original_correction_result"] == request["correction_result"]
    assert result["provenance"]["correction_identity"] == identity
    second_parent = deepcopy(request["correction_result"]["dataset"])
    n = len(request["geometry"]["station_ids"])
    terrain = {
        "kind": "additive_residual_to_plate",
        "unit": "mGal",
        "height_reference": "WGS84_ellipsoid",
        "density_kg_m3": 2670.0,
        "source_sha256": digest({"authored": "flat terrain residual zero"}),
        "method": "Authored flat no-terrain control, not a field DEM",
        "station_ids": request["geometry"]["station_ids"],
        "additions_mgal": [0.0] * n,
        "sigma_mgal": [0.0] * n,
    }
    request["correction_result"] = process_survey(
        second_parent,
        {
            "target": "terrain_adjusted_disturbance",
            "density_kg_m3": 2670.0,
            "density_sigma_kg_m3": 0.0,
            "uncertainty_model": "conservative_marginals",
            "terrain": terrain,
        },
    )
    sigma = np.array(request["correction_result"]["processing"]["uncertainty_mgal"])
    request["config"].update(
        error_model="supplied_covariance",
        covariance_mgal2=np.diag(sigma**2).tolist(),
        covariance_citation="Only authored independent gravity error is nonzero in this flat control",
    )
    assert admit(request, return_identity=True)[-1]["input_state"] == "bouguer_disturbance"
    stale = deepcopy(request)
    stale["correction_result"]["processing"]["input_sha256"] = digest(second_parent | {"history": []})
    with pytest.raises(GravityContractError, match="reconstructable"):
        admit(stale)


def test_unreconstructable_input_serialization_is_explicit(controls):
    request = deepcopy(controls[0][0])
    original = deepcopy(request["correction_result"]["dataset"])
    original.update(state="observed_absolute", history=[])
    for row in original["stations"]:
        row["value_mgal"] = row["original_value"]
    original["stations"][0].update(original_value=980000.0, value_mgal=980000)
    original["metadata"]["source_sha256"] = digest({"authored": "integer raw current-value serialization control"})
    request["correction_result"] = process_survey(
        original, {"target": "gravity_disturbance", "uncertainty_model": "independent_first_order"}
    )
    with pytest.raises(GravityContractError, match="exact parent needed"):
        admit(request)


def test_bounded_strict_request_reader(tmp_path, monkeypatch):
    target = tmp_path / "input.json"
    for content in (
        '{"x":NaN}',
        '{"x":Infinity}',
        '{"x":-Infinity}',
        '{"x":1e999}',
        '{"x":1,"x":2}',
        "[" * 17 + "0" + "]" * 17,
    ):
        target.write_text(content, encoding="utf-8")
        with pytest.raises(GravityContractError):
            read_request(target)
    target.write_bytes(b"\xff")
    with pytest.raises(UnicodeError):
        read_request(target)
    valid = {"citation": '"' + ("[" * 40) + ("]" * 40) + "\\"}
    target.write_text(json.dumps(valid), encoding="utf-8")
    assert read_request(target) == valid  # quoted brackets/escapes are not structural depth
    target.write_text('{"x":1}', encoding="utf-8")
    real_open = Path.open

    def changed_after_stat(path, *args, **kwargs):
        if path == target and args == ("rb",):
            return io.BytesIO(b" " * 65)
        return real_open(path, *args, **kwargs)

    with monkeypatch.context() as limited:
        limited.setattr(transforms, "MAX_INPUT_BYTES", 64)
        limited.setattr(Path, "open", changed_after_stat)
        assert target.stat().st_size < 64
        with pytest.raises(GravityContractError, match="actual bytes read"):
            read_request(target)
    for content in ('{"x":NaN}', "[" * 17 + "0" + "]" * 17):
        target.write_text(content, encoding="utf-8")
        with monkeypatch.context() as guarded:

            def forbidden_engine(*args, **kwargs):
                raise AssertionError("Invalid parser input reached numerical transform")

            guarded.setattr(transforms, "transform_survey", forbidden_engine)
            assert transforms.main(["--input", str(target), "--output-dir", str(tmp_path / "not-created")]) == 2
        assert not (tmp_path / "not-created").exists()


@pytest.mark.parametrize("case", range(3))
def test_independent_prism_and_continuation(case, controls, results):
    request, truth = controls[case]
    result = results[case]
    coords, prisms, densities = truth["coordinates"], truth["prisms"], truth["densities"]
    quadrature = prism_integral(coords, prisms, densities, order=22)
    analytic = hm.prism_gravity(coords, prisms, densities, field="g_z", parallel=False)
    assert np.max(np.abs(quadrature - truth["true_observed_mgal"])) < 1e-7
    assert np.max(np.abs(quadrature - analytic)) < 1e-7
    assert np.max(quadrature) > 0  # positive/negative contrasting sources, down-positive
    assert result["evaluation"]["holdout"]["covered_count"] >= 20
    assert result["evaluation"]["holdout"]["rmse_mgal"] < 0.1
    xx, yy = np.meshgrid(result["axes"]["easting_m"], result["axes"]["northing_m"])
    for grid in result["grids"]:
        indices = np.flatnonzero(grid["covered"])[::13]
        query = (xx.ravel()[indices], yy.ravel()[indices], np.full(len(indices), grid["height_m"]))
        independent = prism_integral(query, prisms, densities, order=22)
        predicted = np.array(grid["predicted_mgal"], dtype=float)[indices]
        assert np.sqrt(np.mean((predicted - independent) ** 2)) < 0.1
    indices = result["split"]["train_indices"][:12]
    query = tuple(c[indices] for c in coords)
    points = tuple(np.array(p) for p in result["model"]["points_m"])
    jacobian = hm.EquivalentSources(parallel=False).jacobian(query, points)
    independent_j = 1 / np.sqrt(sum((q[:, None] - p[None, :]) ** 2 for q, p in zip(query, points, strict=True)))
    assert np.max(np.abs(jacobian - independent_j)) < 1e-12
    assert request["correction_result"]["dataset"]["metadata"]["source_kind"] == "synthetic_control"


def test_blocked_selection_no_holdout_leakage(controls, results):
    request, _ = controls[0]
    result = results[0]
    split = result["split"]
    block_for_index = dict(zip(split["active_indices"], split["block_ids_active"], strict=True))
    train_blocks = {block_for_index[i] for i in split["train_indices"]}
    test_blocks = {block_for_index[i] for i in split["holdout_indices"]}
    assert train_blocks.isdisjoint(test_blocks)
    for candidate in result["selection"]["candidates"]:
        for fold in candidate["folds"]:
            assert set(fold["train_indices"]).isdisjoint(fold["validation_indices"])
            assert set(fold["train_indices"] + fold["validation_indices"]) <= set(split["train_indices"])
    changed = rebuild(request, split["holdout_indices"], delta=7)
    alternate = transform_survey(changed)
    assert result["selection"] == alternate["selection"]
    assert result["model"] == alternate["model"]
    assert result["grids"] == alternate["grids"]
    assert result["nonuniqueness"] == alternate["nonuniqueness"]
    assert alternate["evaluation"]["holdout"]["rmse_mgal"] > 6


def test_masks_condition_and_covariance(controls, results):
    request, _ = controls[0]
    result = results[0]
    assert result["condition"]["damped_condition"] < request["config"]["max_condition"]
    assert result["condition"]["weighted_design_condition"] > result["condition"]["damped_condition"]
    for index, grid in enumerate(result["grids"]):
        assert replay_grid(result, index) == pytest.approx(grid["predicted_mgal"], nan_ok=True)
        for keep, hull, radius, prediction, sigma in zip(
            grid["covered"],
            grid["outside_hull"],
            grid["outside_radius"],
            grid["predicted_mgal"],
            grid["conditional_sigma_mgal"],
            strict=True,
        ):
            assert keep == (not hull and not radius)
            if not keep:
                assert prediction is None and sigma is None
            else:
                assert sigma >= 0
        assert any(grid["outside_hull"]) and any(grid["outside_radius"])
    coords, values, sigma, covariance, active = admit(request)
    small = active[:24]
    xyz = tuple(c[small] for c in coords)
    engine, scale, transfer, _ = fit_layer(xyz, values[small], sigma[small], 360, 100, 1e10)
    target = (xyz[0][:5], xyz[1][:5], np.full(5, 600.0))
    kernel = engine.jacobian(target, engine.points_) / scale
    linear = kernel @ transfer
    # Independent solve of the unscaled coefficient system and propagated covariance.
    j = engine.jacobian(xyz, engine.points_)
    regularizer = 100 * np.diag(scale**2)
    direct = np.linalg.solve(j.T @ (j / sigma[small, None] ** 2) + regularizer, j.T / sigma[small] ** 2)
    independent_l = engine.jacobian(target, engine.points_) @ direct
    assert np.allclose(linear, independent_l, rtol=1e-7, atol=1e-9)
    c = covariance[np.ix_(small, small)]
    assert np.allclose(linear @ c @ linear.T, independent_l @ c @ independent_l.T, rtol=1e-7, atol=1e-12)
    supplied = deepcopy(request)
    supplied["config"].update(
        error_model="supplied_covariance",
        covariance_mgal2=covariance.tolist(),
        covariance_citation="Authored independent control covariance",
    )
    assert np.array_equal(admit(supplied)[3], covariance)
    supplied["config"]["covariance_mgal2"] = (0.8 * covariance + 0.2 * np.outer(sigma, sigma)).tolist()
    correlated = transform_survey(supplied)
    assert correlated["model"] == result["model"]  # diagonal weights unchanged; not GLS
    original_sd = np.array(result["grids"][-1]["conditional_sigma_mgal"], dtype=float)
    correlated_sd = np.array(correlated["grids"][-1]["conditional_sigma_mgal"], dtype=float)
    assert np.nanmax(np.abs(original_sd - correlated_sd)) > 0.001
    supplied["config"]["covariance_mgal2"][0][1] = 1
    with pytest.raises(GravityContractError, match="covariance"):
        admit(supplied)
    supplied["config"]["covariance_mgal2"][1][0] = 1
    with pytest.raises(GravityContractError, match="PSD"):
        admit(supplied)


@pytest.mark.parametrize(
    "mutation",
    [
        ("geometry", "coordinate_unit", "km"),
        ("geometry", "data_unit", "microGal"),
        ("geometry", "component", "g_z_upward"),
        ("geometry", "vertical_reference", "unresolved"),
        ("geometry", "metric_crs", "EPSG:4326"),
        ("geometry", "geometry_error_model", "unknown"),
        ("config", "heights_m", [100.0]),
        ("config", "depths_m", [-100.0]),
        ("config", "dampings", [0.0]),
        ("config", "max_input_sigma_mgal", 0.001),
        ("config", "error_model", "inferred"),
        ("config", "grid_spacing_m", 0.1),
    ],
)
def test_strong_negative_controls(mutation, controls):
    request = deepcopy(controls[0][0])
    section, key, value = mutation
    request[section][key] = value
    with pytest.raises(GravityContractError):
        admit(request)


def test_missing_lineage_geometry_and_high_noise(controls):
    for field in ("easting_m", "northing_m", "upward_m"):
        request = deepcopy(controls[0][0])
        request["geometry"][field][83] = None  # masking never licenses invented coordinates
        with pytest.raises(GravityContractError):
            admit(request)
    request = deepcopy(controls[0][0])
    request["geometry"]["northing_m"] = request["geometry"]["easting_m"][:]
    with pytest.raises(GravityContractError, match="noncollinear"):
        admit(request)
    for bad_sigma in (0, 1):
        noisy = rebuild(controls[0][0], range(196), sigma=bad_sigma)
        with pytest.raises(GravityContractError, match="noise"):
            admit(noisy)
    request = deepcopy(controls[0][0])
    request["correction_result"]["dataset"]["metadata"]["height_datum"] = "unresolved_NVD29"
    with pytest.raises(GravityContractError, match="datum"):
        admit(request)
    request = deepcopy(controls[0][0])
    request["correction_result"]["dataset"]["stations"][0]["gravity_sigma"] = None
    with pytest.raises(GravityContractError):
        admit(request)
    request = deepcopy(controls[0][0])
    request["correction_result"]["dataset"]["state"] = "provider_principal_facts"
    with pytest.raises(GravityContractError, match="state"):
        admit(request)


def test_nonuniqueness_is_not_density(results):
    for result in results:
        alternatives = result["nonuniqueness"]["training_only_alternatives"]
        fitting = [a for a in alternatives if a["status"] == "passed" and a["training_rmse_mgal"] < 0.02]
        assert len({a["depth_m"] for a in fitting}) >= 2
        assert max(a["coefficient_l2_mgal_m"] for a in fitting) > 2 * min(a["coefficient_l2_mgal_m"] for a in fitting)
        assert "not density" in result["model"]["interpretation"]
        assert "Geological uncertainty" in result["uncertainty"]["excludes"]


def test_unmet_height_precision_and_resource_rejection(controls):
    request = deepcopy(controls[0][0])
    request["config"]["max_transfer_sigma_mgal"] = 1e-6
    result = transform_survey(request)
    assert result["selection"]["status"] == "unmet_height_precision"
    assert result["selection"]["height_m"] is None
    assert all(not grid["height_precision_passed"] for grid in result["grids"])
    for key, value, reason in (
        ("grid_spacing_m", 60.0, "oversampling"),
        ("coverage_radius_m", 1.0, "candidates"),
        ("max_condition", 2.0, "candidates"),
    ):
        bad = deepcopy(controls[0][0])
        bad["config"][key] = value
        with pytest.raises(GravityContractError, match=reason):
            transform_survey(bad)
    bad = deepcopy(controls[0][0])
    bad["geometry"]["mask_reasons"][83] = None
    with pytest.raises(GravityContractError, match="mask"):
        admit(bad)


def test_shared_error_and_covariance_contract(controls):
    request = deepcopy(controls[0][0])
    old = request["correction_result"]
    original = deepcopy(old["dataset"])
    original.update(state="observed_absolute", history=[])
    for row in original["stations"]:
        row["value_mgal"] = row["original_value"]
        row["surface_height_m"] = 100.0
    request["correction_result"] = process_survey(
        original,
        {
            "target": "bouguer_disturbance",
            "density_kg_m3": 2670.0,
            "density_sigma_kg_m3": 1.0,
            "uncertainty_model": "independent_first_order",
        },
    )
    with pytest.raises(GravityContractError, match="shared"):
        admit(request)
    sigmas = np.array(request["correction_result"]["processing"]["uncertainty_mgal"])
    density_error = np.array(request["correction_result"]["processing"]["uncertainty_components_mgal"]["density"])
    covariance = np.diag(sigmas**2 - density_error**2) + np.outer(density_error, density_error)
    request["config"].update(
        error_model="supplied_covariance",
        covariance_mgal2=covariance.tolist(),
        covariance_citation="Authored shared density with independent station noise",
    )
    assert np.allclose(admit(request)[3], covariance)
    for value in (None, True, float("nan")):
        bad = deepcopy(request)
        bad["config"]["covariance_mgal2"][0][0] = value
        with pytest.raises(GravityContractError):
            admit(bad)


def test_conservative_bounds_are_not_standard_deviations(controls):
    request = deepcopy(controls[0][0])
    original = deepcopy(request["correction_result"]["dataset"])
    original.update(state="observed_absolute", history=[])
    for row in original["stations"]:
        row["value_mgal"] = row["original_value"]
        row["receiver_sigma_m"] = 0.1
    request["correction_result"] = process_survey(
        original, {"target": "gravity_disturbance", "uncertainty_model": "conservative_marginals"}
    )
    with pytest.raises(GravityContractError, match="not standard deviations"):
        admit(request)
    independent = process_survey(
        original, {"target": "gravity_disturbance", "uncertainty_model": "independent_first_order"}
    )
    true_sd = np.array(independent["processing"]["uncertainty_mgal"])
    request["config"].update(
        error_model="supplied_covariance",
        covariance_mgal2=np.diag(true_sd**2).tolist(),
        covariance_citation="Authored control: independent primitive height and observation errors, RSS variance",
    )
    assert np.allclose(admit(request)[2], true_sd)
    result = transform_survey(request)
    assert result["uncertainty"]["error_model"] == "supplied_covariance"
    assert result["original_correction_result"] == request["correction_result"]
    bad = deepcopy(request)
    del bad["config"]["covariance_citation"]
    with pytest.raises(GravityContractError, match="citation"):
        admit(bad)
    bad = deepcopy(request)
    bad["config"]["covariance_mgal2"][0][0] = 0.09
    with pytest.raises(GravityContractError, match="bound"):
        admit(bad)


def test_export_and_paired_scripts(controls, results, tmp_path):
    request = controls[0][0]
    result = results[0]
    output = tmp_path / "bundle"
    receipt = export_bundle(request, result, output)
    for item in receipt["files"]:
        path = output / item["name"]
        assert path.stat().st_size == item["bytes"]
        assert sha256(path.read_bytes()).hexdigest() == item["sha256"]
    assert json.loads((output / "request.json").read_text()) == request
    assert json.loads((output / "result.json").read_text()) == result
    for theme in ("light", "dark"):
        for kind in ("maps", "diagnostics"):
            svg = (output / f"{kind}-{theme}.svg").read_text()
            ET.fromstring(svg)
            assert "mGal" in svg
            assert (output / f"{kind}-{theme}.png").stat().st_size > 100000
    with pytest.raises(GravityContractError, match="already exists"):
        export_bundle(request, result, output)
    with pytest.raises(GravityContractError, match="external"):
        export_bundle(request, result, ROOT / "data/processed/not-authorized")
    alias = ROOT.parent / "not-created" / ".." / ROOT.name / "data/derived/not-authorized"
    with pytest.raises(GravityContractError, match="external"):
        export_bundle(request, result, alias)
    unrelated = deepcopy(request)
    unrelated["config"]["seed"] += 1
    with pytest.raises(GravityContractError, match="does not belong"):
        export_bundle(unrelated, result, tmp_path / "unrelated")
    for suffix in ("ps1", "sh"):
        text = (ROOT / f"scripts/run_m01_transforms.{suffix}").read_text()
        assert ".venv-m01" in text and "gravity_transforms.py" in text
    malformed = tmp_path / "duplicate.json"
    malformed.write_text('{"schema_version":"bad","schema_version":"bad"}')
    run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "data-pipeline/gravity_transforms.py"),
            "--input",
            str(malformed),
            "--output-dir",
            str(tmp_path / "not-created"),
        ],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 2 and not (tmp_path / "not-created").exists()


def test_theory_and_svg():
    guide = (ROOT / "docs/methods/gravity-processing/02_equivalent-source-transforms.md").read_text(encoding="utf-8")
    for phrase in (
        "training-only",
        "nonuniqueness",
        "WGS84",
        "conditional",
        "166.7",
        "2929",
        "Exercise",
        "Other data",
        "1/r",
    ):
        assert phrase in guide
    assert len(guide.split()) > 1800
    svg = ROOT / "docs/methods/gravity-processing/assets/equivalent-source-transforms.svg"
    root = ET.parse(svg).getroot()
    assert root.attrib["viewBox"] == "0 0 1200 820"
    text = svg.read_text(encoding="utf-8")
    assert "prefers-color-scheme: dark" in text and "<title" in text and "<desc" in text
    assert "training" in text and "holdout" in text and "density" in text


def test_committed_scientific_evidence(results):
    """Receipts/screenshots are actual labelled controls, not detached acceptance claims."""
    directory = ROOT / "docs/design/features/m01-gravity-transforms/evidence"
    verification = json.loads((directory / "verification-current.json").read_text(encoding="utf-8"))
    assert verification["field_bytes_read"] == 0
    assert verification["protected_source_published"] is False
    assert verification["full_method_accepted"] is False
    assert "closed" in verification["field_eligibility"]
    assert verification["engines"] == results[0]["provenance"]["engines"]
    for control, result in zip(verification["controls"], results, strict=True):
        assert control["source_kind"] == "synthetic_control"
        assert control["source_sha256"] == result["provenance"]["source_sha256"]
        assert control["stations"] == 196 and control["masked"] == 4
        recorded = control["evaluation"]["holdout"]
        actual = result["evaluation"]["holdout"]
        assert recorded["covered_count"] == actual["covered_count"]
        assert recorded["unsupported_count"] == actual["unsupported_count"]
        assert recorded["rmse_mgal"] == pytest.approx(actual["rmse_mgal"], rel=1e-8, abs=1e-10)
        identity = control["correction_identity"]
        assert identity["deterministic_receipt_verified"] is True
        assert identity["recorded_runtime_origin_verified"] is False
        assert identity["input_state"] == "observed_absolute"
        assert len(control["transform_module_sha256"]) == 64
    for reference in verification["primary_document_receipts"]:
        assert reference["status"] == 200 and reference["bytes"] > 1000
        assert reference["url"].startswith("https://www.fatiando.org/")
        assert len(reference["sha256"]) == 64
    receipt = json.loads((directory / "control-export-current.json").read_text(encoding="utf-8"))
    assert receipt["analytical_control_only"] and receipt["protected_field_bytes_read"] == 0
    assert receipt["paired_results_equal"] and len(set(receipt["paired_result_file_sha256"])) == 1
    for item in receipt["files"]:
        if item["name"].endswith(".png"):
            image = directory / item["name"]
            assert image.stat().st_size == item["bytes"]
            assert sha256(image.read_bytes()).hexdigest() == item["sha256"]
    rendered = json.loads((directory / "svg-render.json").read_text(encoding="utf-8"))
    source = ROOT / "docs/methods/gravity-processing/assets/equivalent-source-transforms.svg"
    assert sha256(source.read_bytes()).hexdigest() == rendered["source_sha256"]
    assert rendered["web_acceptance"] is False
    for item in rendered["receipt"]:
        assert item["outside"] == []
        assert item["dark"] == (item["theme"] == "dark")
        image = directory / f"theory-{item['theme']}.png"
        assert image.stat().st_size == item["bytes"]
        assert sha256(image.read_bytes()).hexdigest() == item["sha256"]
    history = json.loads((directory / "history.json").read_text(encoding="utf-8"))
    assert history["api_approval"] is False and history["field_bytes_read"] == 0
    assert history["historical_revision"].startswith("bfa5c24")
    assert all(image["unchanged"] for image in history["plot_artifacts"])
