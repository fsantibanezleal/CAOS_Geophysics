import hashlib
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_candidate_release import FAMILY_METHODS, ReleaseValidationError, _check_mt_response_closure, verify_candidate_release
sys.path.insert(0, str(ROOT / "data-pipeline"))
from geology import VARIANTS, registry
from rebuild import RELEASE_VERSION, generator_fingerprint


VERSION = RELEASE_VERSION
MU = 4.0e-7 * math.pi


def _curves(real, imag, frequencies):
    return {
        "real": real,
        "imag": imag,
        "apparent": [(re * re + im * im) / (MU * 2 * math.pi * frequency)
                     for re, im, frequency in zip(real, imag, frequencies)],
        "phase": [math.degrees(math.atan2(im, re)) for re, im in zip(real, imag)],
    }


def test_mt_residual_is_complex_difference_not_difference_of_apparent_or_phase():
    frequencies = [0.5, 2.0]
    observed = _curves([0.1, 0.3], [0.2, 0.4], frequencies)
    predicted = _curves([0.05, 0.2], [0.1, 0.1], frequencies)
    residual = _curves([0.05, 0.1], [0.1, 0.3], frequencies)
    _check_mt_response_closure(observed, predicted, residual, frequencies, 16, "mt/sample")

    wrong = {**residual, "apparent": [a - b for a, b in zip(observed["apparent"], predicted["apparent"])]}
    with pytest.raises(ReleaseValidationError, match="residual apparent resistivity"):
        _check_mt_response_closure(observed, predicted, wrong, frequencies, 16, "mt/sample")


def _write_candidate(root: Path, *, nonfinite: bool = False, learned: bool = False) -> Path:
    case = next(item for item in registry() if item["id"] == ("LEARNED_CNN" if learned else "GRAVITY_INTRUSION"))
    case_id, family = case["id"], case["family"]
    sample_count = 32 * 32
    observed = [1.0] * sample_count
    methods = {}
    for method_id in FAMILY_METHODS[family]:
        predicted = [] if learned and method_id == "cnn" else [0.5] * sample_count
        residual = [0.1] * 4 if learned and method_id == "cnn" else [0.5] * sample_count
        model = [0.2] * 4
        metrics = {"rmse": 0.1}
        extra = {}
        if learned and method_id == "autoencoder":
            model = [0.0625] * sample_count
            metrics = {"reconstruction_mse": 0.0625, "threshold": 0.1,
                       "above_threshold": False, "raw_observation_mse": 0.0625}
            extra = {"network_input": observed}
        methods[method_id] = {
            "name": method_id, "name_es": method_id, "metrics": metrics,
            "evaluation": {"status": "recovered", "reason_codes": []},
            "target": {"quantity": "density"}, "applicability": None,
            "model": model, "predicted": predicted, "residual": residual, **extra,
        }
    units, data_units = {
        "gravity": ("g/cm³", "mGal"), "learned": ("g/cm³", "mGal"),
    }[family]
    artifact = {
        "schema": "inverse-earth/v2",
        "id": case_id,
        "family": family,
        "variant": "reference", "provenance": {
            "version": VERSION, "synthetic": True,
            "generator_fingerprint": generator_fingerprint(family, version=VERSION),
        },
        "truth": [0.0] * 10752, "units": units, "data_units": data_units,
        "grid": {"shape": [16, 24, 28], "spacing": [80.0, 80.0, 70.0]},
        "survey": {"shape": [32, 32], "locations": [[0.0, 0.0, 0.0]] * sample_count,
                   "observed": observed, "clean": observed, "active": [True] * sample_count},
        "export_precision_significant_digits": 7, "methods": methods,
    }
    artifact_path = root / case_id / "reference.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")
    variants = []
    for variant_id, label, label_es in VARIANTS:
        path = root / case_id / f"{variant_id}.json"
        if variant_id != "reference":
            path.write_text(json.dumps({**artifact, "variant": variant_id}, separators=(",", ":")), encoding="utf-8")
        raw = path.read_bytes()
        variant_artifact = json.loads(raw)
        summary = {name: {
            "name": method["name"], "name_es": method["name_es"], "metrics": method["metrics"],
            "evaluation": method["evaluation"], "target": method["target"],
            "applicability": method["applicability"],
        } for name, method in variant_artifact["methods"].items()}
        variants.append({"id": variant_id, "name": label, "name_es": label_es,
                         "path": f"{case_id}/{variant_id}.json", "sha256": hashlib.sha256(raw).hexdigest(),
                         "bytes": len(raw), "methods": summary})
    catalog = {
        "schema": "inverse-earth.catalog/v2", "version": VERSION, "complete": False,
        "cases": [{**case, "variants": variants}],
    }
    release = {
        "schema": "inverse-earth.release/v2", "version": VERSION, "complete": False,
        "cases": 1, "runs": len(VARIANTS), "methods": len(VARIANTS) * len(FAMILY_METHODS[family]),
        "synthetic": True,
    }
    (root / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    (root / "release.json").write_text(json.dumps(release), encoding="utf-8")
    if nonfinite:
        artifact_path.write_text('{"x":NaN}', encoding="utf-8")
        raw = artifact_path.read_bytes()
        variants[0].update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        (root / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    if learned:
        model_dir = root / "models"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_entries = {}
        for name in ("cnn", "autoencoder"):
            checkpoint = model_dir / f"{name}.json"
            checkpoint.write_text(json.dumps({"weights": [0.1, 0.2]}), encoding="utf-8")
            model_entries[name] = {
                "checkpoint": f"models/{name}.json",
                "sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            }
        ledger = {
            "schema": "inverse-earth.learning/v3",
            "survey_shape": [32, 32],
            "input_scale": 2.0,
            "novelty_threshold": 0.1,
            "models": model_entries,
        }
        (model_dir / "training.json").write_text(json.dumps(ledger), encoding="utf-8")
    return root


def _edit_reference(candidate: Path, edit) -> None:
    catalog_path = candidate / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    variant = catalog["cases"][0]["variants"][0]
    artifact_path = candidate / variant["path"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    edit(artifact)
    artifact_path.write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")
    raw = artifact_path.read_bytes()
    variant.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    for method_id, method in artifact["methods"].items():
        variant["methods"][method_id].update(
            metrics=method["metrics"], evaluation=method["evaluation"],
            target=method["target"], applicability=method["applicability"],
        )
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")


def test_consistent_subset_requires_explicit_flag(tmp_path):
    candidate = _write_candidate(tmp_path)
    with pytest.raises(ReleaseValidationError, match="incomplete case/variant subset"):
        verify_candidate_release(candidate)
    assert verify_candidate_release(candidate, allow_subset=True) == {
        "version": VERSION, "cases": 1, "runs": len(VARIANTS),
        "methods": len(VARIANTS) * len(FAMILY_METHODS["gravity"]),
    }


def test_release_contract_covers_twenty_registered_cases_and_all_families():
    assert len(registry()) == 20
    assert {case["family"] for case in registry()} == set(FAMILY_METHODS)
    assert len(VARIANTS) == 6


@pytest.mark.parametrize("damage, message", [
    ("survey_shape", "acquisition grid shape"),
    ("grid_spacing", "volume spacing"),
    ("units", "physical units"),
    ("sample_count", "survey observed shape"),
    ("residual", "residual closure"),
    ("truth_missing", "explicit top-level truth"),
    ("field_truth", "survey measurements must not contain truth"),
    ("synthetic_flag", "synthetic provenance"),
    ("method_matrix", "family method matrix"),
    ("evaluation", "unknown evaluation state"),
    ("variant_identity", "variant id"),
    ("case_identity", "case id"),
])
def test_scientific_contract_rejects_invalid_candidate_artifact(tmp_path, damage, message):
    candidate = _write_candidate(tmp_path)
    def edit(artifact):
        if damage == "survey_shape":
            artifact["survey"]["shape"] = [16, 16]
        elif damage == "grid_spacing":
            artifact["grid"]["spacing"] = [80.0, 80.0, 80.0]
        elif damage == "units":
            artifact["units"] = "kg/m³"
        elif damage == "sample_count":
            artifact["survey"]["observed"].pop()
        elif damage == "residual":
            artifact["methods"]["l2"]["residual"][0] = 0.0
        elif damage == "truth_missing":
            artifact.pop("truth")
        elif damage == "field_truth":
            artifact["survey"]["truth"] = artifact["truth"]
        elif damage == "synthetic_flag":
            artifact["provenance"]["synthetic"] = False
        elif damage == "method_matrix":
            artifact["methods"].pop("irls")
        elif damage == "evaluation":
            artifact["methods"]["l2"]["evaluation"]["status"] = "maybe"
        elif damage == "variant_identity":
            artifact["variant"] = "contrast"
        elif damage == "case_identity":
            artifact["id"] = "MAGNETIC_DYKE"
    _edit_reference(candidate, edit)
    with pytest.raises(ReleaseValidationError, match=message):
        verify_candidate_release(candidate, allow_subset=True)


def test_residual_closure_allows_rounding_at_declared_export_precision(tmp_path):
    candidate = _write_candidate(tmp_path)
    def edit(artifact):
        artifact["survey"]["observed"][0] = 1.234567
        for method in artifact["methods"].values():
            method["predicted"][0] = 1.234566
            method["residual"][0] = 0.000001
    _edit_reference(candidate, edit)
    assert verify_candidate_release(candidate, allow_subset=True)["runs"] == len(VARIANTS)


def test_subset_case_must_retain_all_six_variants(tmp_path):
    candidate = _write_candidate(tmp_path)
    path = candidate / "catalog.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    catalog["cases"][0]["variants"].pop()
    path.write_text(json.dumps(catalog), encoding="utf-8")
    with pytest.raises(ReleaseValidationError, match="each of the six release variants"):
        verify_candidate_release(candidate, allow_subset=True)


@pytest.mark.parametrize("damage, message", [
    ("catalog_sha", "SHA-256"), ("catalog_bytes", "byte count"),
    ("metric_mismatch", "metrics"), ("artifact_version", "scientific source fingerprint"),
    ("artifact_schema", "schema"), ("catalog_complete", "completeness flag"),
    ("release_count", "run count"), ("catalog_version", "catalog version"),
    ("release_version", "release version"), ("catalog_schema", "catalog schema"),
    ("release_schema", "release schema"),
])
def test_integrity_mismatches_fail_closed(tmp_path, damage, message):
    candidate = _write_candidate(tmp_path)
    catalog_path = candidate / "catalog.json"
    release_path = candidate / "release.json"
    catalog = json.loads(catalog_path.read_text())
    if damage in ("catalog_sha", "catalog_bytes"):
        variant = catalog["cases"][0]["variants"][0]
        variant["sha256" if damage == "catalog_sha" else "bytes"] = "bad" if damage == "catalog_sha" else 0
    elif damage == "metric_mismatch":
        catalog["cases"][0]["variants"][0]["methods"]["l2"]["metrics"]["rmse"] = 9
    elif damage == "catalog_complete":
        catalog["complete"] = True
    elif damage == "catalog_version":
        catalog["version"] = "0.04.001"
    elif damage == "catalog_schema":
        catalog["schema"] = "wrong/catalog"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    if damage == "artifact_version":
        p = candidate / "GRAVITY_INTRUSION/reference.json"
        artifact = json.loads(p.read_text())
        artifact["provenance"]["version"] = "0.04.001"
        p.write_text(json.dumps(artifact), encoding="utf-8")
        raw = p.read_bytes()
        catalog["cases"][0]["variants"][0].update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    if damage == "artifact_schema":
        p = candidate / "GRAVITY_INTRUSION/reference.json"
        artifact = json.loads(p.read_text())
        artifact["schema"] = "wrong/schema"
        p.write_text(json.dumps(artifact), encoding="utf-8")
        raw = p.read_bytes()
        catalog["cases"][0]["variants"][0].update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    if damage in ("release_count", "release_version", "release_schema"):
        release = json.loads(release_path.read_text())
        if damage == "release_count":
            release["runs"] = 99
        elif damage == "release_version":
            release["version"] = "0.04.001"
        else:
            release["schema"] = "wrong/release"
        release_path.write_text(json.dumps(release), encoding="utf-8")
    with pytest.raises(ReleaseValidationError, match=message):
        verify_candidate_release(candidate, allow_subset=True)


def test_missing_artifact_fails(tmp_path):
    candidate = _write_candidate(tmp_path)
    (candidate / "GRAVITY_INTRUSION/reference.json").unlink()
    with pytest.raises(ReleaseValidationError, match="missing artifact file"):
        verify_candidate_release(candidate, allow_subset=True)


def test_nonfinite_json_constant_fails(tmp_path):
    candidate = _write_candidate(tmp_path, nonfinite=True)
    with pytest.raises(ReleaseValidationError, match="non-standard JSON numeric constant"):
        verify_candidate_release(candidate, allow_subset=True)


def test_path_traversal_fails(tmp_path):
    candidate = _write_candidate(tmp_path)
    path = candidate / "catalog.json"
    catalog = json.loads(path.read_text())
    catalog["cases"][0]["variants"][0]["path"] = "../outside.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    with pytest.raises(ReleaseValidationError, match="escapes candidate root"):
        verify_candidate_release(candidate, allow_subset=True)


def test_learned_subset_requires_and_verifies_training_bundle(tmp_path):
    candidate = _write_candidate(tmp_path, learned=True)
    assert verify_candidate_release(candidate, allow_subset=True)["cases"] == 1


@pytest.mark.parametrize("missing", ["training.json", "cnn.json", "autoencoder.json"])
def test_learned_release_rejects_missing_training_files(tmp_path, missing):
    candidate = _write_candidate(tmp_path, learned=True)
    (candidate / "models" / missing).unlink()
    with pytest.raises(ReleaseValidationError, match="requires models/"):
        verify_candidate_release(candidate, allow_subset=True)


@pytest.mark.parametrize("damage, message", [
    ("checkpoint_bytes", "cnn checkpoint SHA-256"),
    ("ledger_hash", "cnn checkpoint SHA-256"),
    ("ledger_schema", "training ledger schema"),
    ("survey_shape", "survey_shape"),
])
def test_learned_release_rejects_tampered_or_incompatible_bundle(tmp_path, damage, message):
    candidate = _write_candidate(tmp_path, learned=True)
    ledger_path = candidate / "models/training.json"
    ledger = json.loads(ledger_path.read_text())
    if damage == "checkpoint_bytes":
        checkpoint = candidate / "models/cnn.json"
        checkpoint.write_text('{"weights":[9]}', encoding="utf-8")
    elif damage == "ledger_hash":
        ledger["models"]["cnn"]["sha256"] = "0" * 64
    elif damage == "ledger_schema":
        ledger["schema"] = "inverse-earth.learning/v2"
    elif damage == "survey_shape":
        ledger["survey_shape"] = [16, 16]
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    with pytest.raises(ReleaseValidationError, match=message):
        verify_candidate_release(candidate, allow_subset=True)
