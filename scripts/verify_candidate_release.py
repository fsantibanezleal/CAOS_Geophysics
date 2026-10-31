"""Fail-closed integrity checks for a data-pipeline/rebuild.py output directory."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "data-pipeline"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

from geology import registry, VARIANTS, SURVEY_SHAPE, VOLUME_SHAPE, VOLUME_SPACING, SEISMIC_SHAPE, SEISMIC_SPACING  # noqa: E402
from rebuild import RELEASE_VERSION, REUSABLE_VERSIONS  # noqa: E402
from provenance import matches_generator_fingerprint  # noqa: E402
from artifact_versions import RUN_VERSIONS  # noqa: E402


class ReleaseValidationError(ValueError):
    """Raised when a candidate directory cannot be trusted as a release."""


FAMILY_METHODS = {
    "gravity": {"l2", "irls"},
    "magnetics": {"l2", "irls", "vector"},
    "mt": {"mt-lm", "mt-adam", "mt-neural"},
    "seismic": {"fwi-l2", "fwi-multiscale"},
    "joint": {"l2", "irls", "joint-uncoupled", "joint", "pgi"},
    "learned": {"l2", "irls", "cnn", "autoencoder"},
}
FAMILY_UNITS = {
    "gravity": ("g/cm³", "mGal"), "magnetics": ("SI", "nT"),
    "mt": ("ohm m", "ohm"), "seismic": ("m/s", "amplitude"),
    "joint": ("g/cm³", "mGal"), "learned": ("g/cm³", "mGal"),
}
EVALUATION_STATES = {"recovered", "unresolved", "failed", "negative-control"}
TRUTH_KEYS = {"truth", "ground_truth", "true_model", "known_model"}


def _numeric_array(value: Any, where: str) -> tuple[list[float], tuple[int, ...]]:
    """Flatten a rectangular JSON numeric array and return its shape."""
    if isinstance(value, list):
        if not value:
            return [], (0,)
        children = [_numeric_array(item, f"{where}[{index}]") for index, item in enumerate(value)]
        child_shape = children[0][1]
        if any(shape != child_shape for _, shape in children):
            _fail(f"ragged numeric array at {where}")
        return [number for values, _ in children for number in values], (len(value), *child_shape)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"expected a numeric array at {where}")
    number = float(value)
    if not math.isfinite(number):
        _fail(f"non-finite numeric array value at {where}")
    return [number], ()


def _array_tree(value: Any, where: str) -> dict[str, tuple[list[float], tuple[int, ...]]]:
    def walk(node: Any, path: str) -> dict[str, tuple[list[float], tuple[int, ...]]]:
        if isinstance(node, dict):
            if not node:
                _fail(f"empty numeric mapping at {where}")
            return {key: item for name, child in node.items()
                    for key, item in walk(child, f"{path}.{name}" if path else name).items()}
        key = path or "values"
        return {key: _numeric_array(node, f"{where}.{key}")}
    return walk(value, "")


def _require_shape(actual: tuple[int, ...], expected: tuple[int, ...], where: str) -> None:
    if actual != expected:
        _fail(f"{where} shape {list(actual)} does not match required {list(expected)}")


def _json_shape(value: Any, where: str) -> tuple[int, ...]:
    if not isinstance(value, list):
        return ()
    if not value:
        return (0,)
    child_shapes = [_json_shape(item, f"{where}[{index}]") for index, item in enumerate(value)]
    if any(shape != child_shapes[0] for shape in child_shapes):
        _fail(f"ragged array at {where}")
    return (len(value), *child_shapes[0])


def _check_residual_closure(observed: Any, predicted: Any, residual: Any, precision: Any, where: str,
                            working_epsilon: float = 0.0) -> None:
    obs_tree = _array_tree(observed, f"{where}.observed")
    pred_tree = _array_tree(predicted, f"{where}.predicted")
    residual_tree = _array_tree(residual, f"{where}.residual")
    _same(set(obs_tree), set(pred_tree), f"{where} observed/predicted components")
    _same(set(obs_tree), set(residual_tree), f"{where} observed/residual components")
    if type(precision) is not int or not 1 <= precision <= 16:
        _fail(f"invalid export precision at {where}")
    for component in obs_tree:
        obs, obs_shape = obs_tree[component]
        pred, pred_shape = pred_tree[component]
        res, res_shape = residual_tree[component]
        _same(obs_shape, pred_shape, f"{where} {component} observation/prediction shape")
        _same(obs_shape, res_shape, f"{where} {component} observation/residual shape")
        _same(len(obs), len(pred), f"{where} {component} observation/prediction length")
        _same(len(obs), len(res), f"{where} {component} observation/residual length")
        for index, (o, p, r) in enumerate(zip(obs, pred, res)):
            scale = max(abs(o), abs(p), abs(r))
            quantum = (10.0 ** (math.floor(math.log10(scale)) - precision + 1)) if scale else 0.0
            tolerance = 1.6 * quantum + working_epsilon * scale * 1.5 + 8 * math.ulp(scale)
            if abs((o - p) - r) > tolerance:
                _fail(f"residual closure failed at {where}.{component}[{index}] (tolerance {tolerance:g})")


def _check_mt_response_closure(observed: Any, predicted: Any, residual: Any,
                               frequencies: list[float], precision: int, where: str) -> None:
    """Check MT's complex residual and its nonlinear apparent/phase encodings.

    Apparent resistivity and phase of Zobs-Zpred are not the differences of the
    corresponding apparent-resistivity and phase curves. The real/imaginary
    impedance components close linearly; each reported curve is then checked
    against the invariant rho_a=|Z|^2/(mu*2*pi*f), phi=arg(Z).
    """
    if not isinstance(observed, dict) or not isinstance(predicted, dict) or not isinstance(residual, dict):
        _fail(f"{where} MT response components must be mappings")
    expected = {"real", "imag", "apparent", "phase"}
    _same(set(observed), expected, f"{where} MT observed response components")
    _same(set(predicted), expected, f"{where} MT predicted response components")
    _same(set(residual), expected, f"{where} MT residual response components")
    if type(precision) is not int or not 1 <= precision <= 16:
        _fail(f"invalid export precision at {where}")
    count = len(frequencies)
    if count < 2 or any(not math.isfinite(float(f)) or float(f) <= 0 for f in frequencies):
        _fail(f"{where} MT frequencies must be finite positive samples")
    for field, values in (("observed", observed), ("predicted", predicted), ("residual", residual)):
        for component in expected:
            _, shape = _numeric_array(values[component], f"{where}.{field}.{component}")
            _require_shape(shape, (count,), f"{where} MT {field} {component}")

    _check_residual_closure(
        {key: observed[key] for key in ("real", "imag")},
        {key: predicted[key] for key in ("real", "imag")},
        {key: residual[key] for key in ("real", "imag")}, precision, where)

    mu = 4.0e-7 * math.pi
    for label, values in (("observed", observed), ("predicted", predicted), ("residual", residual)):
        real = [float(v) for v in values["real"]]
        imag = [float(v) for v in values["imag"]]
        apparent = [float(v) for v in values["apparent"]]
        phase = [float(v) for v in values["phase"]]
        for index, (re_z, im_z, rho, phase_deg, frequency) in enumerate(
                zip(real, imag, apparent, phase, frequencies)):
            power = re_z * re_z + im_z * im_z
            expected_rho = power / (mu * 2.0 * math.pi * float(frequency))
            expected_phase = math.degrees(math.atan2(im_z, re_z))
            rho_quantum = (10.0 ** (math.floor(math.log10(abs(rho))) - precision + 1)) if rho else 0.0
            re_quantum = (10.0 ** (math.floor(math.log10(abs(re_z))) - precision + 1)) if re_z else 0.0
            im_quantum = (10.0 ** (math.floor(math.log10(abs(im_z))) - precision + 1)) if im_z else 0.0
            rho_input_error = (2.0 * abs(re_z) * re_quantum + re_quantum**2
                               + 2.0 * abs(im_z) * im_quantum + im_quantum**2)
            rho_input_error /= mu * 2.0 * math.pi * float(frequency)
            frequency_quantum = (10.0 ** (math.floor(math.log10(abs(float(frequency))) - precision + 1))
                                 if frequency else 0.0)
            rho_input_error += abs(expected_rho) * frequency_quantum / max(abs(float(frequency)), 1e-300)
            rho_tolerance = 0.5 * rho_quantum + rho_input_error + 16.0 * math.ulp(max(abs(rho), abs(expected_rho), 1e-300))
            if abs(expected_rho - rho) > rho_tolerance:
                _fail(f"{where} MT {label} apparent resistivity does not match complex impedance at sample {index}")
            phase_quantum = (10.0 ** (math.floor(math.log10(abs(phase_deg))) - precision + 1)) if phase_deg else 0.0
            phase_input_error = (abs(re_z) * im_quantum + abs(im_z) * re_quantum)
            phase_input_error /= max(power, 1e-300)
            phase_tolerance = (0.5 * phase_quantum + math.degrees(phase_input_error)
                               + 16.0 * math.ulp(max(abs(phase_deg), abs(expected_phase), 1.0)))
            delta = (expected_phase - phase_deg + 180.0) % 360.0 - 180.0
            if abs(delta) > phase_tolerance:
                _fail(f"{where} MT {label} phase does not match complex impedance at sample {index}")


def _contains_truth_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(str(key).lower() in TRUTH_KEYS or _contains_truth_key(child)
                   for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_truth_key(child) for child in value)
    return False


def _verify_autoencoder(artifact: dict[str, Any], method: dict[str, Any], where: str, root: Path) -> None:
    survey = artifact["survey"]
    raw, raw_shape = _numeric_array(survey["observed"], f"{where}.survey.observed")
    network, network_shape = _numeric_array(method.get("network_input"), f"{where}.network_input")
    predicted, predicted_shape = _numeric_array(method.get("predicted"), f"{where}.predicted")
    residual, residual_shape = _numeric_array(method.get("residual"), f"{where}.residual")
    model, model_shape = _numeric_array(method.get("model"), f"{where}.model")
    expected_size = math.prod(raw_shape)
    for label, shape in (("network input", network_shape), ("prediction", predicted_shape),
                         ("residual", residual_shape), ("error map", model_shape)):
        _same(math.prod(shape), expected_size, f"{where} autoencoder {label} size")
    active = survey.get("active")
    if not isinstance(active, list) or len(active) != len(raw) or any(type(value) is not bool for value in active):
        _fail(f"{where} autoencoder requires the original boolean acquisition mask")
    for index, is_active in enumerate(active):
        if is_active and network[index] != raw[index]:
            _fail(f"{where} autoencoder changed acquired observation {index}")
        if not is_active and artifact.get("variant") != "coverage":
            _fail(f"{where} autoencoder changed an observation outside a coverage experiment")
    precision = artifact.get("export_precision_significant_digits", 7)
    _check_residual_closure(method["network_input"], method["predicted"], method["residual"],
                            precision, f"{where}::autoencoder.network_input")

    ledger_path = _safe_artifact_path(root, "models/training.json")
    ledger = _load_json(ledger_path)
    scale = ledger.get("input_scale")
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
        _fail(f"{where} autoencoder training ledger has an invalid input scale")
    squared_error = [((network[i] - predicted[i]) / scale) ** 2 for i in range(len(network))]
    raw_squared_error = [((raw[i] - predicted[i]) / scale) ** 2 for i in range(len(raw))]
    if len(model) != len(squared_error):
        _fail(f"{where} autoencoder error-map length does not match the survey")
    def quantum(value: float) -> float:
        return 10.0 ** (math.floor(math.log10(abs(value))) - precision + 1) if value else 0.0

    for index, (actual, expected) in enumerate(zip(model, squared_error)):
        delta = 0.5 * (quantum(network[index]) + quantum(predicted[index]))
        propagated = (2.0 * abs(network[index] - predicted[index]) * delta + delta * delta) / (scale * scale)
        magnitude = max(abs(actual), abs(expected), 1e-300)
        tolerance = propagated + 0.5 * quantum(actual) + 16 * math.ulp(magnitude)
        if abs(actual - expected) > tolerance:
            _fail(f"{where} autoencoder normalized squared-error map is inconsistent at sample {index}")
    metrics = method.get("metrics")
    if not isinstance(metrics, dict):
        _fail(f"{where} autoencoder metrics are missing")
    expected_mse = math.fsum(model) / len(model)
    expected_raw_mse = math.fsum(raw_squared_error) / len(raw_squared_error)
    for name, expected in (("reconstruction_mse", expected_mse), ("raw_observation_mse", expected_raw_mse)):
        actual = metrics.get(name)
        tolerance = max(2e-5 * max(abs(actual or 0), abs(expected), 1e-300),
                        2 * (10.0 ** (math.floor(math.log10(abs(expected))) - precision + 1)
                             if expected else 0.0))
        if isinstance(actual, bool) or not isinstance(actual, (int, float)) or abs(actual - expected) > tolerance:
            _fail(f"{where} autoencoder {name} does not match its exported arrays")
    threshold = metrics.get("threshold")
    declared_threshold = ledger.get("novelty_threshold")
    if not _catalog_summary_matches(threshold, declared_threshold):
        _fail(f"{where} autoencoder threshold differs from the frozen training ledger")
    if type(metrics.get("above_threshold")) is not bool or metrics["above_threshold"] != (expected_mse > declared_threshold):
        _fail(f"{where} autoencoder threshold flag is inconsistent")


def _verify_scientific_contract(artifact: dict[str, Any], case: dict[str, Any], where: str, root: Path) -> None:
    family = case["family"]
    _same(artifact.get("provenance", {}).get("synthetic"), True, f"{where} synthetic provenance")
    if "truth" not in artifact or artifact["truth"] is None:
        _fail(f"synthetic artifact must keep its truth in an explicit top-level truth field: {where}")
    if _contains_truth_key(artifact.get("survey", {})):
        _fail(f"survey measurements must not contain truth fields: {where}")
    units, data_units = FAMILY_UNITS[family]
    _same(artifact.get("units"), units, f"{where} model physical units")
    _same(artifact.get("data_units"), data_units, f"{where} observation physical units")

    if family in {"gravity", "magnetics", "joint", "learned"}:
        grid = artifact.get("grid")
        survey = artifact.get("survey")
        if not isinstance(grid, dict) or not isinstance(survey, dict):
            _fail(f"{where} requires explicit grid and survey metadata")
        _require_shape(tuple(grid.get("shape", ())), tuple(VOLUME_SHAPE), f"{where} volume grid")
        _require_shape(tuple(survey.get("shape", ())), tuple(SURVEY_SHAPE), f"{where} acquisition grid")
        _require_shape(_json_shape(grid.get("spacing"), f"{where}.grid.spacing"), (3,),
                       f"{where} grid spacing")
        if tuple(grid.get("spacing", ())) != tuple(VOLUME_SPACING):
            _fail(f"{where} volume spacing must be in metres and match the declared mesh")
        for key, shape in (("locations", (SURVEY_SHAPE[0] * SURVEY_SHAPE[1], 3)),
                           ("observed", (SURVEY_SHAPE[0] * SURVEY_SHAPE[1],))):
            _, actual = _numeric_array(survey.get(key), f"{where}.survey.{key}")
            _require_shape(actual, shape, f"{where} survey {key}")
        _require_shape(_json_shape(survey.get("active"), f"{where}.survey.active"),
                       (SURVEY_SHAPE[0] * SURVEY_SHAPE[1],), f"{where} survey active mask")
        observed = survey["observed"]
    elif family == "mt":
        frequencies = artifact.get("frequencies")
        _, frequency_shape = _numeric_array(frequencies, f"{where}.frequencies")
        if len(frequency_shape) != 1 or frequency_shape[0] < 2:
            _fail(f"{where} MT frequencies must be a one-dimensional sampled axis")
        if not isinstance(artifact.get("thickness"), list) or not artifact["thickness"]:
            _fail(f"{where} MT layered model requires thicknesses in metres")
        observed = artifact.get("observed")
        if not isinstance(observed, dict):
            _fail(f"{where} MT observations must map response components to samples")
        if any(len(values) != frequency_shape[0] for values in observed.values() if isinstance(values, list)):
            _fail(f"{where} MT observation lengths must match its frequency axis")
    else:
        grid = artifact.get("grid")
        if not isinstance(grid, dict):
            _fail(f"{where} seismic artifact requires grid metadata")
        # Generator constants are [distance, depth]; exported sections are
        # [depth, distance], matching the renderer's physical image axes.
        _require_shape(tuple(grid.get("shape", ())), tuple(reversed(SEISMIC_SHAPE)),
                       f"{where} seismic grid")
        if tuple(grid.get("spacing", ())) != (SEISMIC_SPACING, SEISMIC_SPACING):
            _fail(f"{where} seismic grid spacing must be in metres")
        observed = artifact.get("observed")

    methods = artifact.get("methods")
    if not isinstance(methods, dict) or any(not isinstance(method, dict) for method in methods.values()):
        _fail(f"{where} method entries must be objects")
    _same(set(methods), FAMILY_METHODS[family], f"{where} family method matrix")
    for method_id, method in methods.items():
        evaluation = method.get("evaluation")
        if not isinstance(evaluation, dict) or evaluation.get("status") not in EVALUATION_STATES:
            _fail(f"{where}::{method_id} has a missing or unknown evaluation state")
        if not isinstance(evaluation.get("reason_codes"), list):
            _fail(f"{where}::{method_id} evaluation must include reason_codes")
        predicted, residual = method.get("predicted"), method.get("residual")
        # CNN column-density estimates are model-space outputs and intentionally have no data prediction.
        if family == "learned" and method_id == "cnn" and predicted == []:
            if not isinstance(residual, list) or not residual:
                _fail(f"{where}::{method_id} model-space residual must be present")
            continue
        if family == "mt":
            _check_mt_response_closure(observed, predicted, residual, artifact["frequencies"],
                                       artifact.get("export_precision_significant_digits", 7),
                                       f"{where}::{method_id}")
        elif family == "learned" and method_id == "autoencoder":
            _verify_autoencoder(artifact, method, where, root)
        else:
            _check_residual_closure(observed, predicted, residual,
                                    artifact.get("export_precision_significant_digits", 7),
                                f"{where}::{method_id}",
                                working_epsilon=2.0 ** -23 if family == "seismic" else 0.0)


def _fail(message: str) -> None:
    raise ReleaseValidationError(message)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    _fail(f"non-standard JSON numeric constant: {value}")


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except ReleaseValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"cannot read valid JSON from {path}: {exc}")
    _assert_finite(value, str(path))
    return value


def _assert_finite(value: Any, where: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        _fail(f"non-finite JSON number at {where}")
    if isinstance(value, dict):
        for key, child in value.items():
            _assert_finite(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_finite(child, f"{where}[{index}]")


def _expected_catalog() -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in registry()}


def _safe_artifact_path(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative:
        _fail("catalog artifact path must be a non-empty string")
    rel = Path(relative)
    if rel.is_absolute():
        _fail(f"absolute artifact path is forbidden: {relative}")
    target = (root / rel).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        _fail(f"artifact path escapes candidate root: {relative}")
    return target


def _same(left: Any, right: Any, description: str) -> None:
    if left != right:
        _fail(f"catalog/artifact mismatch for {description}")


def _catalog_summary_matches(summary: Any, artifact: Any, precision: int = 7) -> bool:
    """Check a summary at the significant-digit precision of its release catalog."""
    if isinstance(artifact, dict):
        return (isinstance(summary, dict) and set(summary) == set(artifact)
                and all(_catalog_summary_matches(summary[key], value, precision) for key, value in artifact.items()))
    if isinstance(artifact, list):
        return (isinstance(summary, list) and len(summary) == len(artifact)
                and all(_catalog_summary_matches(a, b, precision) for a, b in zip(summary, artifact)))
    if isinstance(artifact, bool) or artifact is None or isinstance(artifact, str):
        return type(summary) is type(artifact) and summary == artifact
    if isinstance(artifact, (int, float)):
        if isinstance(summary, bool) or not isinstance(summary, (int, float)):
            return False
        if isinstance(artifact, int):
            return type(summary) is int and summary == artifact
        rounded = float(f"{artifact:.{precision}g}")
        return summary == rounded
    return type(summary) is type(artifact) and summary == artifact


def _verify_learned_bundle(root: Path) -> None:
    ledger_path = _safe_artifact_path(root, "models/training.json")
    if not ledger_path.is_file():
        _fail("learned case requires models/training.json")
    ledger = _load_json(ledger_path)
    if not isinstance(ledger, dict):
        _fail("learned training ledger must contain a JSON object")
    _same(ledger.get("schema"), "inverse-earth.learning/v3", "learned training ledger schema")
    _same(ledger.get("survey_shape"), [32, 32], "learned training ledger survey_shape")
    models = ledger.get("models")
    if not isinstance(models, dict):
        _fail("learned training ledger is missing model entries")
    for name in ("cnn", "autoencoder"):
        entry = models.get(name)
        if not isinstance(entry, dict):
            _fail(f"learned training ledger is missing the {name} model entry")
        expected_relative = f"models/{name}.json"
        _same(entry.get("checkpoint"), expected_relative, f"{name} checkpoint path")
        checkpoint = _safe_artifact_path(root, expected_relative)
        if not checkpoint.is_file():
            _fail(f"learned case requires {expected_relative}")
        digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        _same(entry.get("sha256"), digest, f"{name} checkpoint SHA-256 in training ledger")
        if not isinstance(_load_json(checkpoint), dict):
            _fail(f"learned checkpoint must contain a JSON object: {expected_relative}")


def verify_candidate_release(directory: str | Path, *, allow_subset: bool = False,
                            container_version: str = RELEASE_VERSION) -> dict[str, int | str]:
    """Validate catalog, release summary, listed artifact bytes and mirrored method data.

    A subset is accepted only when explicitly requested. Its catalog and release must
    still consistently declare an incomplete release, and every included case must
    contain the full six-variant experiment axis and the full method matrix for each
    included case. Partial builds select cases, not partial scientific dimensions.
    """
    root = Path(directory).resolve()
    if container_version not in RUN_VERSIONS:
        _fail(f"unsupported release container version: {container_version}")
    if not root.is_dir():
        _fail(f"candidate directory does not exist: {root}")
    catalog_path, release_path = root / "catalog.json", root / "release.json"
    catalog, release = _load_json(catalog_path), _load_json(release_path)
    if not isinstance(catalog, dict) or not isinstance(release, dict):
        _fail("catalog.json and release.json must contain JSON objects")
    _same(catalog.get("schema"), "inverse-earth.catalog/v2", "catalog schema")
    _same(release.get("schema"), "inverse-earth.release/v2", "release schema")
    _same(catalog.get("version"), container_version, "catalog version")
    _same(release.get("version"), container_version, "release version")
    if not isinstance(catalog.get("cases"), list) or not catalog["cases"]:
        _fail("catalog has no cases")
    if any(isinstance(case, dict) and case.get("family") == "learned" for case in catalog["cases"]):
        _verify_learned_bundle(root)

    expected = _expected_catalog()
    expected_variants = {variant[0] for variant in VARIANTS}
    case_ids: set[str] = set()
    seen_paths: set[Path] = set()
    run_count = method_count = 0
    is_complete = True
    for case in catalog["cases"]:
        if not isinstance(case, dict):
            _fail("catalog case entries must be objects")
        case_id = case.get("id")
        if case_id not in expected:
            _fail(f"unknown case id: {case_id!r}")
        if case_id in case_ids:
            _fail(f"duplicate case id: {case_id}")
        case_ids.add(case_id)
        for field in ("family", "name", "name_es", "geometry", "seed"):
            _same(case.get(field), expected[case_id][field], f"case {case_id}.{field}")
        variants = case.get("variants")
        if not isinstance(variants, list) or not variants:
            _fail(f"case {case_id} has no variants")
        variant_ids: set[str] = set()
        for variant in variants:
            if not isinstance(variant, dict):
                _fail(f"case {case_id} variant entries must be objects")
            variant_id = variant.get("id")
            if variant_id not in expected_variants:
                _fail(f"unknown variant {variant_id!r} in {case_id}")
            if variant_id in variant_ids:
                _fail(f"duplicate variant {variant_id} in {case_id}")
            variant_ids.add(variant_id)
            run_count += 1
            artifact_path = _safe_artifact_path(root, variant.get("path"))
            if artifact_path in seen_paths:
                _fail(f"catalog lists artifact path more than once: {variant['path']}")
            seen_paths.add(artifact_path)
            if not artifact_path.is_file():
                _fail(f"missing artifact file: {variant['path']}")
            raw = artifact_path.read_bytes()
            _same(variant.get("bytes"), len(raw), f"{variant['path']} byte count")
            _same(variant.get("sha256"), hashlib.sha256(raw).hexdigest(), f"{variant['path']} SHA-256")
            artifact = _load_json(artifact_path)
            if not isinstance(artifact, dict):
                _fail(f"artifact must contain a JSON object: {variant['path']}")
            _same(artifact.get("schema"), "inverse-earth/v2", f"{variant['path']} schema")
            _same(artifact.get("id"), case_id, f"{variant['path']} case id")
            _same(artifact.get("variant"), variant_id, f"{variant['path']} variant id")
            _same(artifact.get("family"), case["family"], f"{variant['path']} family")
            provenance = artifact.get("provenance", {})
            producer_version = provenance.get("version")
            if producer_version not in REUSABLE_VERSIONS:
                _fail(f"{variant['path']} has an unsupported producer version")
            if not matches_generator_fingerprint(case["family"], provenance.get("generator_fingerprint"), version=producer_version):
                _fail(f"{variant['path']} scientific source fingerprint")
            if not isinstance(artifact.get("methods"), dict) or not artifact["methods"]:
                _fail(f"artifact has no methods: {variant['path']}")
            _verify_scientific_contract(artifact, case, variant["path"], root)
            catalog_methods = variant.get("methods")
            if not isinstance(catalog_methods, dict):
                _fail(f"catalog method summary is missing: {variant['path']}")
            _same(set(catalog_methods), set(artifact["methods"]), f"{variant['path']} method ids")
            for method_id, method in artifact["methods"].items():
                summary = catalog_methods[method_id]
                if not isinstance(method, dict) or not isinstance(summary, dict):
                    _fail(f"method entries must be objects: {variant['path']}::{method_id}")
                for field in ("name", "name_es"):
                    _same(summary.get(field), method.get(field), f"{variant['path']}::{method_id}.{field}")
                for field in ("metrics", "evaluation", "target", "applicability"):
                    summary_precision = 10 if catalog.get("version") == "0.04.003" else 7
                    if not _catalog_summary_matches(summary.get(field), method.get(field), summary_precision):
                        _fail(f"catalog/artifact mismatch for {variant['path']}::{method_id}.{field} at the catalog's {summary_precision}-significant-digit precision")
            method_count += len(artifact["methods"])
        if variant_ids != expected_variants:
            _fail(f"case {case_id} must include each of the six release variants")
        if len(variants) != len(expected_variants):
            is_complete = False

    if case_ids != set(expected):
        is_complete = False
    if is_complete:
        pass
    elif not allow_subset:
        _fail("candidate is an incomplete case/variant subset; pass --allow-subset only for deliberate subset builds")

    _same(catalog.get("complete"), is_complete, "catalog completeness flag")
    _same(release.get("complete"), is_complete, "release completeness flag")
    _same(release.get("cases"), len(case_ids), "release case count")
    _same(release.get("runs"), run_count, "release run count")
    _same(release.get("methods"), method_count, "release method count")
    if release.get("synthetic") is not True:
        _fail("release must explicitly identify this generated candidate as synthetic")
    return {"version": container_version, "cases": len(case_ids), "runs": run_count, "methods": method_count}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="output directory produced by data-pipeline/rebuild.py")
    parser.add_argument("--allow-subset", action="store_true", help="accept a consistent, explicitly partial build")
    parser.add_argument("--container-version", choices=sorted(RUN_VERSIONS), default=RELEASE_VERSION,
                        help="validate an existing versioned container while still checking every producer fingerprint")
    args = parser.parse_args()
    try:
        counts = verify_candidate_release(args.directory, allow_subset=args.allow_subset,
                                          container_version=args.container_version)
    except ReleaseValidationError as exc:
        parser.error(str(exc))
    print("Candidate release integrity verified: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
