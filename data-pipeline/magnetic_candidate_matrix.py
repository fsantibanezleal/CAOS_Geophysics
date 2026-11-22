"""Resumable, source-bound M04 development candidate matrix.

This runner evaluates the frozen eight-beta L2/sparse comparison on the three
sealed development folds. It never reads sealed outer observations for scoring,
never selects from a partial candidate, and writes one hash-bound receipt after
each beta/fold pair so a process interruption does not repeat completed solves.
Final refit and sealed outer evaluation are separate pipeline stages.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version

from magnetic_survey_json import BETAS, parse_request
import magnetic_survey
import magnetic_calibration
from magnetic_fold_score import model_q_sha256, score_magnetic_validation_fold
from sources import local_data_root


PENALTIES = ("l2", "sparse_smallness")
FOLDS = (0, 1, 2)
SCHEMA = "magnetic-m04-candidate-matrix-1"
CELL_SCHEMA = "magnetic-m04-candidate-fold-receipt-1"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _jsonable(value):
    """Convert only known numerical result containers to strict JSON values."""
    if hasattr(value, "tolist") and callable(value.tolist):
        return _jsonable(value.tolist())
    if hasattr(value, "item") and callable(value.item):
        return _jsonable(value.item())
    if type(value) is dict:
        return {str(key): _jsonable(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_jsonable(item) for item in value]
    if value is None or type(value) in (str, int, float, bool):
        if type(value) is float and not __import__("math").isfinite(value):
            raise ValueError("result contains a non-finite value")
        return value
    raise TypeError(f"unsupported result value type: {type(value).__name__}")


def candidate_id(beta: float, penalty: str) -> str:
    if type(beta) is not float or beta not in BETAS or penalty not in PENALTIES:
        raise ValueError("candidate: beta and penalty must follow the frozen M04 grid")
    token = format(beta, ".4g").replace(".", "p").replace("-", "m")
    return f"beta-{token}-{penalty}"


def candidate_specs() -> list[dict]:
    """Return the exact beta-major, L2-before-sparse frozen candidate order."""
    return [
        {"id": candidate_id(float(beta), penalty), "beta": float(beta), "penalty": penalty}
        for beta in BETAS for penalty in PENALTIES
    ]


def _receipt_with_hash(receipt: dict) -> dict:
    body = dict(receipt)
    body.pop("receipt_sha256", None)
    body["receipt_sha256"] = _hash(_canonical(body))
    return body


def _validate_existing(path: Path, identity: dict) -> dict:
    try:
        receipt = json.loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot resume malformed cell receipt {path.name}") from error
    claimed = receipt.get("receipt_sha256")
    if type(claimed) is not str:
        raise RuntimeError(f"cell receipt has no integrity hash: {path.name}")
    if receipt.get("identity") != identity or _receipt_with_hash(receipt)["receipt_sha256"] != claimed:
        raise RuntimeError(f"cell receipt identity or bytes differ: {path.name}")
    if receipt.get("schema") != CELL_SCHEMA or receipt.get("complete") is not True:
        raise RuntimeError(f"cell receipt is not a complete solver outcome: {path.name}")
    return receipt


def _fold_metric(fit: dict, score: dict | None, fold: int) -> dict:
    if fit.get("status") != "converged" or score is None:
        return {
            "fold": fold, "status": "failed",
            "reason": fit.get("reason") or "validation_score_unavailable",
            "n_rows": 0, "n_components": 0, "phi_d": None,
            "rms_nT": None, "normalized_rms": None, "kkt_inf": None,
            "model_sha256": None,
        }
    return {
        "fold": fold, "status": "converged", "reason": None,
        "n_rows": int(score["receiver_count"]),
        "n_components": int(score["observation_count"]),
        "phi_d": float(score["phi_d"]),
        "rms_nT": float(score["residual_rms_nT"]),
        "normalized_rms": float(score["mean_standardized_quadratic"] ** .5),
        "kkt_inf": float(fit.get("normalized_projected_gradient_inf"
                                  if fit.get("schema", "").endswith("sparse-fold-result-1")
                                  else "normalized_projected_kkt_inf")),
        "model_sha256": model_q_sha256(fit["model_q"]),
    }


def aggregate_candidates(cell_receipts: list[dict]) -> tuple[list[dict], str | None]:
    """Score only candidates with three converged, finite held-out folds."""
    by_key = {(row["beta"], row["fold"]): row for row in cell_receipts}
    candidates = []
    for spec in candidate_specs():
        folds = []
        for fold in FOLDS:
            cell = by_key.get((spec["beta"], fold))
            if cell is None:
                raise ValueError("matrix: missing a frozen beta/fold receipt")
            key = "l2" if spec["penalty"] == "l2" else "sparse"
            folds.append(cell["candidates"][key]["metric"])
        complete = all(row["status"] == "converged" for row in folds)
        if complete:
            denominator = sum(row["n_components"] for row in folds)
            score = sum(row["phi_d"] for row in folds) / denominator
            if denominator <= 0:
                raise ValueError("matrix: complete candidate has no validation observations")
        else:
            score = None
        candidates.append({
            "id": spec["id"], "beta": spec["beta"], "penalty": spec["penalty"],
            "folds": folds, "status": "complete" if complete else "failed", "score": score,
        })

    eligible = [row for row in candidates if row["status"] == "complete"]
    if not eligible:
        return candidates, None
    minimum = min(row["score"] for row in eligible)
    tied = [row for row in eligible if abs(row["score"] - minimum) <=
            64. * sys.float_info.epsilon * max(1., abs(row["score"]), abs(minimum))]
    selected = min(tied, key=lambda row: (
        0 if row["penalty"] == "l2" else 1, -row["beta"], row["id"]
    ))
    return candidates, selected["id"]


def _summarize_fit(fit: dict, score: dict | None) -> dict:
    return {
        "status": fit.get("status"), "reason": fit.get("reason"),
        "fit_rows": fit.get("fit_rows"), "model_q": fit.get("model_q"),
        "model_q_sha256": (model_q_sha256(fit["model_q"])
                           if fit.get("status") == "converged" else None),
        "objective": fit.get("objective"),
        "normalized_projected_kkt_inf": fit.get("normalized_projected_kkt_inf"),
        "normalized_projected_gradient_inf": fit.get("normalized_projected_gradient_inf"),
        "source_inventory": fit.get("source_inventory"),
        "source_inventory_sha256": fit.get("source_inventory_sha256"),
        "elapsed_seconds": fit.get("elapsed_seconds"),
        "terminal_audits": fit.get("terminal_audits"),
        "stages": fit.get("stages"), "history": fit.get("history"),
        "score": score,
        "claims": fit.get("claims"),
    }


def _score_fit(handle, fit: dict, fold: int) -> dict | None:
    if fit.get("status") != "converged":
        return None
    model = fit.get("model_q")
    digest = model_q_sha256(model)
    return score_magnetic_validation_fold(handle, fold, model, digest)


def run_matrix(raw: bytes, output_dir: Path, *, wall_seconds: float = 120.) -> dict:
    """Run/resume all 24 beta-fold pairs and write the aggregate selection table."""
    if type(raw) is not bytes:
        raise TypeError("request: immutable bytes required")
    if not isinstance(output_dir, Path) or not output_dir.is_absolute():
        raise ValueError("output_dir: an absolute external data-root path is required")
    if type(wall_seconds) not in (int, float) or not 0. < wall_seconds <= 120.:
        raise ValueError("wall_seconds: must remain within the approved 120-second fit cap")
    root = Path(__file__).resolve().parents[1]
    resolved = output_dir.resolve()
    if resolved == root or root in resolved.parents:
        raise ValueError("output_dir: research receipts may not be written inside the repository")
    data_root = local_data_root()
    if resolved != data_root and data_root not in resolved.parents:
        raise ValueError("output_dir: research receipts must remain under GEOPHYSICS_LOCAL_DATA_ROOT")
    handle = parse_request(raw)
    plan = magnetic_survey.plan_geometry(handle)
    if not plan["eligibility"]["local_processing"]:
        raise ValueError("survey: local processing is not eligible")
    if handle.metadata()["processing"]["quantity"] not in magnetic_calibration.adapter.LINEAR_QUANTITIES:
        raise ValueError("survey: frozen candidate matrix supports affine magnetic quantities only")

    output_dir.mkdir(parents=True, exist_ok=True)
    request_sha = _hash(raw)
    source_files = {
        "magnetic_calibration.py": magnetic_calibration.__file__,
        "magnetic_fold_score.py": sys.modules["magnetic_fold_score"].__file__,
        "magnetic_survey.py": magnetic_survey.__file__,
    }
    identity = {
        "product_commit": subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
            capture_output=True, text=True,
        ).stdout.strip(),
        "request_sha256": request_sha,
        "geometry_seal_sha256": plan["identity"]["seal_sha256"],
        "partition_sha256": plan["partition"]["sha256"],
        "sources": {name: _hash(Path(path).read_bytes()) for name, path in source_files.items()},
        "runner_sha256": _hash(Path(__file__).read_bytes()),
        "cli_sha256": _hash((root / "scripts" / "run_m04_candidate_matrix.py").read_bytes()),
        "wall_seconds": float(wall_seconds),
    }
    rows = []
    for beta_index, beta_value in enumerate(BETAS):
        beta = float(beta_value)
        for fold in FOLDS:
            path = output_dir / f"beta-{beta_index:02d}-fold-{fold}.json"
            if path.exists():
                cell = _validate_existing(path, identity)
                rows.append(cell["row"])
                print(f"RESUME beta={beta:g} fold={fold} l2={cell['row']['candidates']['l2']['metric']['status']} "
                      f"sparse={cell['row']['candidates']['sparse']['metric']['status']}", flush=True)
                continue

            l2 = magnetic_calibration.fit_l2_fold(raw, fold, beta, wall_seconds=float(wall_seconds))
            l2_score = _score_fit(handle, l2, fold)
            if l2.get("status") == "converged":
                sparse = magnetic_calibration.fit_sparse_fold(
                    raw, fold, beta, l2_result=l2, wall_seconds=float(wall_seconds)
                )
                sparse_score = _score_fit(handle, sparse, fold)
            else:
                sparse = {
                    "schema": "magnetic-linear-sparse-fold-result-1", "status": "failed",
                    "reason": "same_fold_same_beta_l2_start_failed", "claims": {
                        "candidate_selected": False, "outer_evaluation_performed": False,
                        "method_accepted": False, "online_admitted": False,
                    },
                }
                sparse_score = None

            row = {
                "beta": beta, "fold": fold,
                "candidates": {
                    "l2": {"id": candidate_id(beta, "l2"),
                           "metric": _fold_metric(l2, l2_score, fold),
                           "fit": _summarize_fit(l2, l2_score)},
                    "sparse": {"id": candidate_id(beta, "sparse_smallness"),
                               "metric": _fold_metric(sparse, sparse_score, fold),
                               "fit": _summarize_fit(sparse, sparse_score)},
                },
            }
            cell = _receipt_with_hash({
                "schema": CELL_SCHEMA, "complete": True,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "identity": identity, "row": _jsonable(row),
                "runtime": {"python": platform.python_version(),
                            "numpy": version("numpy"), "scipy": version("scipy"),
                            "simpeg": version("simpeg"), "discretize": version("discretize")},
            })
            temporary = path.with_suffix(".json.part")
            temporary.write_bytes(_canonical(cell) + b"\n")
            os.replace(temporary, path)
            rows.append(row)
            print(f"DONE beta={beta:g} fold={fold} l2={row['candidates']['l2']['metric']['status']} "
                  f"sparse={row['candidates']['sparse']['metric']['status']}", flush=True)

    candidates, selected = aggregate_candidates(rows)
    matrix = {
        "schema": SCHEMA, "identity": identity,
        "candidates": candidates, "selected": selected,
        "cell_receipts": [
            {"path": f"beta-{index:02d}-fold-{fold}.json",
             "sha256": _hash((output_dir / f"beta-{index:02d}-fold-{fold}.json").read_bytes())}
            for index in range(len(BETAS)) for fold in FOLDS
        ],
        "claims": {"candidate_matrix_complete": True, "final_refit_performed": False,
                   "outer_evaluation_performed": False, "field_validation": False,
                   "method_accepted": False, "online_admitted": False},
    }
    encoded = _canonical(matrix) + b"\n"
    temporary = output_dir / "matrix.json.part"
    temporary.write_bytes(encoded)
    os.replace(temporary, output_dir / "matrix.json")
    print(f"MATRIX selected={selected or 'none'} complete="
          f"{sum(candidate['status'] == 'complete' for candidate in candidates)} of {len(candidates)}")
    return matrix
