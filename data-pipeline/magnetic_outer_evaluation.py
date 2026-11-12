"""One-time sealed outer scoring of an independently verified frozen M04 model."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np

import magnetic_final_refit
import magnetic_inverse
from magnetic_fit_assembly import read_selected_likelihood
from magnetic_likelihood import GaussianWhitener
from magnetic_survey_json import parse_request
from sources import local_data_root


SCHEMA = "magnetic-m04-sealed-outer-evaluation-1"
INTENT_SCHEMA = "magnetic-m04-sealed-outer-intent-1"
COMPONENTS = {"secondary_enu_nT": 3, "linear_tmi_nT": 1}


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _jsonable(value):
    if hasattr(value, "tolist") and callable(value.tolist):
        return _jsonable(value.tolist())
    if hasattr(value, "item") and callable(value.item):
        return _jsonable(value.item())
    if type(value) is dict:
        return {str(key): _jsonable(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_jsonable(item) for item in value]
    if value is None or type(value) in (str, int, float, bool):
        if type(value) is float and not math.isfinite(value):
            raise ValueError("evaluation contains non-finite values")
        return value
    raise TypeError(f"unsupported evaluation value: {type(value).__name__}")


def _metric(document, observed, predicted, selected_noise, kind, component_count):
    indices = np.arange(len(observed), dtype=np.int64)
    whitener = GaussianWhitener(kind, selected_noise, indices)
    residual_predicted_minus_observed = predicted - observed
    whitened = whitener.whiten(residual_predicted_minus_observed)
    phi_d = float(np.sum(whitened * whitened, dtype=np.float64))
    if not math.isfinite(phi_d) or phi_d < 0.:
        raise FloatingPointError("outer metric: nonfinite weighted residual")
    return {
        "n_rows": int(len(observed) // component_count),
        "n_components": int(len(observed)),
        "phi_d": phi_d,
        "rms_nT": float(np.sqrt(np.mean(residual_predicted_minus_observed ** 2))),
        "normalized_rms": float(np.sqrt(phi_d / len(observed))),
        "cross_partition_dependence": document["noise"]["cross_partition_dependence"],
    }


def _identity(raw, matrix_path, freeze_path, freeze, plan, *, runner_path, cli_path):
    root = Path(__file__).resolve().parents[1]
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    matrix_bytes = matrix_path.read_bytes()
    freeze_bytes = freeze_path.read_bytes()
    return {
        "product_commit": commit,
        "matrix_sha256": _hash(matrix_bytes),
        "matrix_product_commit": freeze["identity"]["matrix_product_commit"],
        "final_refit_product_commit": freeze["identity"]["final_refit_product_commit"],
        "freeze_file_sha256": _hash(freeze_bytes),
        "freeze_receipt_sha256": freeze["receipt_sha256"],
        "model_q_sha256": freeze["frozen_model_sha256"],
        "request_sha256": _hash(raw),
        "geometry_seal_sha256": plan["identity"]["seal_sha256"],
        "partition_sha256": plan["partition"]["sha256"],
        "runner_sha256": _hash(runner_path.read_bytes()),
        "cli_sha256": _hash(cli_path.read_bytes()),
    }


def evaluation_paths(matrix_sha256: str) -> tuple[Path, Path]:
    if type(matrix_sha256) is not str or len(matrix_sha256) != 64:
        raise ValueError("matrix_sha256: lowercase SHA-256 required")
    if any(char not in "0123456789abcdef" for char in matrix_sha256):
        raise ValueError("matrix_sha256: lowercase SHA-256 required")
    base = local_data_root() / "research-runs" / "m04-outer-evaluations"
    return (base / f"{matrix_sha256}.intent.json",
            base / f"{matrix_sha256}.json")


def _read_receipt(path: Path, schema: str) -> dict:
    try:
        receipt = json.loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"receipt: unreadable {schema}") from error
    if (type(receipt) is not dict or receipt.get("schema") != schema
            or receipt.get("receipt_sha256") != magnetic_final_refit._receipt_hash(receipt)):
        raise ValueError(f"receipt: invalid {schema} integrity")
    return receipt


def verify_outer_evaluation(raw: bytes, matrix_dir: Path, freeze_path: Path,
                            result_path: Path) -> dict:
    """Verify immutable outer evidence without recomputing predictions or metrics."""
    if type(raw) is not bytes or len(raw) > 8_388_608:
        raise ValueError("request: bounded immutable bytes under the 8 MiB contract required")
    matrix_path = magnetic_final_refit._safe_data_path(matrix_dir, must_exist=True) / "matrix.json"
    freeze_path = magnetic_final_refit._safe_data_path(freeze_path, must_exist=True)
    result_path = magnetic_final_refit._safe_data_path(result_path, must_exist=True)
    freeze = magnetic_final_refit.verify_final_refit(raw, matrix_dir, freeze_path)
    matrix, selected, plan, _handle = magnetic_final_refit._load_and_verify_matrix(raw, matrix_dir)
    matrix_sha = _hash(matrix_path.read_bytes())
    expected_intent_path, expected_result_path = evaluation_paths(matrix_sha)
    if result_path != expected_result_path.resolve(strict=True):
        raise ValueError("receipt: result path is not the one-time matrix ledger location")
    intent_path = expected_intent_path.resolve(strict=True)
    intent = _read_receipt(intent_path, INTENT_SCHEMA)
    result = _read_receipt(result_path, SCHEMA)
    metadata = parse_request(raw).metadata()
    if metadata["processing"]["quantity"] not in COMPONENTS:
        raise ValueError("quantity: this outer-evaluation verifier supports secondary ENU or linear TMI")
    identity = _identity(
        raw, matrix_path, freeze_path, freeze, plan,
        runner_path=Path(__file__).resolve(),
        cli_path=Path(__file__).resolve().parents[1] / "scripts" / "run_m04_outer_evaluation.py",
    )
    if (intent.get("status") != "started" or intent.get("identity") != identity
            or result.get("status") != "complete" or result.get("identity") != identity
            or result.get("intent_receipt_sha256") != intent.get("receipt_sha256")):
        raise ValueError("receipt: run, freeze or source identity mismatch")
    if result.get("selection", {}).get("candidate_id") != selected["id"]:
        raise ValueError("receipt: selected candidate differs from frozen matrix")
    prediction = result.get("prediction")
    if type(prediction) is not dict:
        raise ValueError("receipt: missing prediction arrays")
    count = COMPONENTS[metadata["processing"]["quantity"]]
    usable = [index for index, keep in enumerate(plan["inventory"]["usable"]["data"]) if keep is True]
    expected_rows = sorted(usable)
    values = np.asarray(prediction.get("values_nT"), dtype=np.float64)
    residual = np.asarray(prediction.get("residual_observed_minus_predicted_nT"), dtype=np.float64)
    if (prediction.get("quantity") != metadata["processing"]["quantity"]
            or prediction.get("rows") != expected_rows
            or values.shape != (len(expected_rows), count)
            or residual.shape != values.shape
            or not np.isfinite(values).all() or not np.isfinite(residual).all()):
        raise ValueError("receipt: prediction shape, row order or finiteness failed")
    partition = result.get("partition")
    if (type(partition) is not dict
            or partition.get("development_rows") != plan["partition"]["development_rows"]["data"]
            or partition.get("outer_rows") != plan["partition"]["outer_rows"]["data"]
            or partition.get("outer_evaluation_performed_once") is not True
            or partition.get("outer_rows_used_for_fit_or_selection") is not False):
        raise ValueError("receipt: partition scope differs from sealed plan")
    claims = result.get("claims")
    expected_claims = {
        "outer_evaluation_performed": True, "field_source_verified": False,
        "field_geology_known": False, "method_accepted": False,
        "online_admitted": False,
    }
    if claims != expected_claims:
        raise ValueError("receipt: scientific acceptance boundary changed")
    return result


def run_outer_evaluation(raw: bytes, matrix_dir: Path, freeze_path: Path) -> dict:
    """Score the already selected model once; an intent permanently consumes this matrix hash."""
    if type(raw) is not bytes or len(raw) > 8_388_608:
        raise ValueError("request: bounded immutable bytes under the 8 MiB contract required")
    matrix_path = magnetic_final_refit._safe_data_path(matrix_dir, must_exist=True) / "matrix.json"
    freeze_path = magnetic_final_refit._safe_data_path(freeze_path, must_exist=True)
    freeze = magnetic_final_refit.verify_final_refit(raw, matrix_dir, freeze_path)
    matrix, selected, plan, handle = magnetic_final_refit._load_and_verify_matrix(raw, matrix_dir)
    if freeze["identity"]["selected_candidate"] != selected["id"]:
        raise ValueError("freeze: selected candidate differs from completed matrix")
    metadata = handle.metadata()
    quantity = metadata["processing"]["quantity"]
    if quantity not in COMPONENTS:
        raise ValueError("quantity: the accepted affine outer lane supports secondary ENU or linear TMI")
    component_count = COMPONENTS[quantity]
    usable = tuple(index for index, keep in enumerate(plan["inventory"]["usable"]["data"])
                   if keep is True)
    development_rows = tuple(plan["partition"]["development_rows"]["data"])
    outer_rows = tuple(plan["partition"]["outer_rows"]["data"])
    if (not outer_rows or not set(outer_rows).issubset(usable)
            or not set(development_rows).issubset(usable)
            or set(outer_rows).intersection(development_rows)
            or tuple(sorted((*outer_rows, *development_rows))) != usable
            or development_rows != tuple(sorted(development_rows))
            or outer_rows != tuple(sorted(outer_rows))):
        raise ValueError("partition: original usable rows must partition into development and outer")

    root = local_data_root().resolve()
    base = (root / "research-runs" / "m04-outer-evaluations").resolve()
    if base == root or root not in base.parents:
        raise ValueError("output: one-time evaluation ledger must stay under the external data root")
    base.mkdir(parents=True, exist_ok=True)
    matrix_sha = _hash(matrix_path.read_bytes())
    intent_path, result_path = evaluation_paths(matrix_sha)
    intent_path = magnetic_final_refit._safe_data_path(intent_path, must_exist=False)
    result_path = magnetic_final_refit._safe_data_path(result_path, must_exist=False)
    if (intent_path.exists() or intent_path.is_symlink()
            or result_path.exists() or result_path.is_symlink()):
        raise FileExistsError("outer evaluation: this candidate matrix already has a consumed one-time evaluation")

    module_path = Path(__file__).resolve()
    cli_path = Path(__file__).resolve().parents[1] / "scripts" / "run_m04_outer_evaluation.py"
    identity = _identity(raw, matrix_path, freeze_path, freeze, plan,
                         runner_path=module_path, cli_path=cli_path)
    intent = magnetic_final_refit._write_once(intent_path, {
        "schema": INTENT_SCHEMA,
        "status": "started",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "identity": identity,
        "scope": "single selected frozen model; sealed outer rows only for outer metrics",
    })

    try:
        model_q = np.asarray(freeze["fit"]["model_q"], dtype=np.float64)
        all_rows = tuple(sorted(usable))
        development_indices = np.asarray(development_rows, dtype=np.int64)
        outer_indices = np.asarray(outer_rows, dtype=np.int64)
        operator = magnetic_inverse.build_operator(
            raw, all_rows, deadline=float(time.monotonic() + 120.),
        )
        if operator.quantity != quantity or operator.parameters != len(model_q):
            raise ValueError("forward: operator quantity or model size differs from the frozen request")
        prediction_flat = operator.evaluate(model_q)["prediction_nT"]
        if prediction_flat.shape != (len(all_rows) * component_count,):
            raise ValueError("forward: predicted vector does not match original row/component order")
        prediction = prediction_flat.reshape(len(all_rows), component_count, order="C")
        row_position = {int(row): index for index, row in enumerate(all_rows)}
        development_positions = np.asarray([row_position[int(row)] for row in development_indices])
        outer_positions = np.asarray([row_position[int(row)] for row in outer_indices])

        def selected_rows(row_ids):
            flat = (row_ids[:, None] * component_count
                    + np.arange(component_count, dtype=np.int64)).reshape(-1)
            document, observed, noise = read_selected_likelihood(
                handle, tuple(int(value) for value in flat), plan["identity"]["seal_sha256"],
            )
            return document, observed, noise

        development_document, development_observed, development_noise = selected_rows(development_indices)
        outer_document, outer_observed, outer_noise = selected_rows(outer_indices)
        if development_document["noise"]["kind"] != outer_document["noise"]["kind"]:
            raise ValueError("noise: partition likelihood kinds differ")
        noise_kind = development_document["noise"]["kind"]
        development_prediction = prediction[development_positions].reshape(-1, order="C")
        outer_prediction = prediction[outer_positions].reshape(-1, order="C")
        development_metric = _metric(development_document, development_observed,
                                     development_prediction, development_noise, noise_kind,
                                     component_count)
        outer_metric = _metric(outer_document, outer_observed,
                               outer_prediction, outer_noise, noise_kind, component_count)

        fit = freeze["fit"]
        fit_rows = tuple(fit["fit_rows"])
        fit_positions = np.asarray([row_position[index] for index in fit_rows], dtype=np.int64)
        frozen_predictions = np.asarray(fit["prediction_nT"], dtype=np.float64).reshape(-1)
        frozen_residuals = np.asarray(fit["residual_observed_minus_predicted_nT"], dtype=np.float64).reshape(-1)
        fit_prediction = prediction[fit_positions].reshape(-1, order="C")
        fit_observed = development_observed.reshape(len(development_rows), component_count)[
            np.asarray([development_rows.index(row) for row in fit_rows], dtype=np.int64)
        ].reshape(-1, order="C")
        if (not np.allclose(fit_prediction, frozen_predictions, rtol=2e-13, atol=1e-12)
                or not np.allclose(fit_observed - fit_prediction, frozen_residuals,
                                   rtol=2e-13, atol=1e-12)):
            raise ValueError("freeze: full-row forward replay differs from final-refit predictions")

        all_observed = np.empty((len(all_rows), component_count), dtype=np.float64)
        all_observed[development_positions] = development_observed.reshape(-1, component_count)
        all_observed[outer_positions] = outer_observed.reshape(-1, component_count)
        residual = all_observed - prediction
        row_ids = metadata["acquisition"]["row_ids"]
        candidate_rows = matrix["candidates"]
        best_l2 = min((row for row in candidate_rows
                       if row["penalty"] == "l2" and row["status"] == "complete"),
                      key=lambda row: (row["score"], -row["beta"], row["id"]))
        sparse_complete = [row for row in candidate_rows
                           if row["penalty"] == "sparse_smallness" and row["status"] == "complete"]
        best_sparse = (min(sparse_complete, key=lambda row: (row["score"], -row["beta"], row["id"]))
                       if sparse_complete else None)
        result_body = {
            "schema": SCHEMA,
            "status": "complete",
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "identity": identity,
            "intent_receipt_sha256": intent["receipt_sha256"],
            "selection": {
                "candidate_id": selected["id"], "beta": selected["beta"],
                "penalty": selected["penalty"], "development_cv_score": selected["score"],
                "l2_candidate_id": best_l2["id"],
                "best_complete_sparse_candidate_id": best_sparse["id"] if best_sparse else None,
                "selected_model_sha256": freeze["frozen_model_sha256"],
            },
            "prediction": {
                "quantity": quantity,
                "components": ["E", "N", "U"] if component_count == 3 else ["scalar"],
                "rows": list(all_rows),
                "row_ids": [row_ids[index] for index in all_rows],
                "values_nT": _jsonable(prediction),
                "residual_observed_minus_predicted_nT": _jsonable(residual),
            },
            "metrics": {"development": development_metric, "outer": outer_metric},
            "partition": {
                "development_rows": list(development_rows),
                "outer_rows": list(outer_rows),
                "outer_evaluation_performed_once": True,
                "outer_rows_used_for_fit_or_selection": False,
            },
            "claims": {
                "outer_evaluation_performed": True,
                "field_source_verified": False,
                "field_geology_known": False,
                "method_accepted": False,
                "online_admitted": False,
            },
        }
        return magnetic_final_refit._write_once(result_path, result_body)
    except Exception as error:
        failure = {
            "schema": SCHEMA,
            "status": "failed",
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "identity": identity,
            "intent_receipt_sha256": intent["receipt_sha256"],
            "failure": {"type": type(error).__name__, "message": str(error)[:240]},
            "claims": {
                "outer_evaluation_performed": False,
                "field_source_verified": False,
                "field_geology_known": False,
                "method_accepted": False,
                "online_admitted": False,
            },
        }
        magnetic_final_refit._write_once(result_path, failure)
        raise
