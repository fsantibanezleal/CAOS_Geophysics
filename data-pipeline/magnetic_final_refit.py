"""Source-bound M04 final development refit and immutable model freeze."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import version

import numpy as np
import magnetic_calibration
import magnetic_candidate_matrix as candidate_matrix
import magnetic_fold_score
import magnetic_survey
from magnetic_survey_json import BETAS, parse_request
from sources import local_data_root


SCHEMA = "magnetic-m04-final-refit-freeze-1"


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
            raise ValueError("receipt contains non-finite values")
        return value
    raise TypeError(f"unsupported receipt value: {type(value).__name__}")


def _receipt_hash(receipt: dict) -> str:
    body = dict(receipt)
    body.pop("receipt_sha256", None)
    return _hash(_canonical(body))


def _safe_data_path(path: Path, *, must_exist: bool) -> Path:
    if not isinstance(path, Path) or not path.is_absolute() or path.is_symlink():
        raise ValueError("path: expected an absolute non-symlink path under the local data root")
    root = local_data_root().resolve()
    resolved = path.resolve(strict=must_exist)
    if resolved == root or root not in resolved.parents:
        raise ValueError("path: must remain below GEOPHYSICS_LOCAL_DATA_ROOT")
    repo = Path(__file__).resolve().parents[1]
    if resolved == repo or repo in resolved.parents:
        raise ValueError("path: research receipts cannot be written inside the product repository")
    return resolved


def _current_commit() -> str:
    repo = Path(__file__).resolve().parents[1]
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def _is_ancestor(older: str, newer: str) -> bool:
    repo = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer],
        check=False, capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError("git: could not verify matrix commit ancestry")
    return result.returncode == 0


def _load_and_verify_matrix(raw: bytes, matrix_dir: Path) -> tuple[dict, dict, dict]:
    directory = _safe_data_path(matrix_dir, must_exist=True)
    matrix_path = directory / "matrix.json"
    if matrix_path.is_symlink() or not matrix_path.is_file():
        raise ValueError("matrix: missing regular matrix.json")
    try:
        frozen = json.loads(matrix_path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("matrix: malformed matrix.json") from error
    if type(frozen) is not dict or frozen.get("schema") != candidate_matrix.SCHEMA:
        raise ValueError("matrix: unsupported schema")
    identity = frozen.get("identity")
    if type(identity) is not dict:
        raise ValueError("matrix: missing source identity")
    if identity.get("request_sha256") != _hash(raw):
        raise ValueError("matrix: request bytes do not match the selected run")
    claims = frozen.get("claims")
    if type(claims) is not dict or claims.get("candidate_matrix_complete") is not True:
        raise ValueError("matrix: declared run is incomplete")

    current_commit = _current_commit()
    matrix_commit = identity.get("product_commit")
    if type(matrix_commit) is not str or not _is_ancestor(matrix_commit, current_commit):
        raise ValueError("matrix: source commit is not an ancestor of current HEAD")

    handle = parse_request(raw)
    plan = magnetic_survey.plan_geometry(handle)
    if (identity.get("geometry_seal_sha256") != plan["identity"]["seal_sha256"]
            or identity.get("partition_sha256") != plan["partition"]["sha256"]):
        raise ValueError("matrix: geometry seal or partition differs from the request")
    required_sources = {
        "magnetic_calibration.py": magnetic_calibration.__file__,
        "magnetic_fold_score.py": magnetic_fold_score.__file__,
        "magnetic_survey.py": magnetic_survey.__file__,
    }
    expected_sources = identity.get("sources")
    if type(expected_sources) is not dict:
        raise ValueError("matrix: missing solver source hashes")
    for name, source in required_sources.items():
        if expected_sources.get(name) != _hash(Path(source).read_bytes()):
            raise ValueError(f"matrix: source changed since candidate selection: {name}")

    expected_names = [
        f"beta-{index:02d}-fold-{fold}.json"
        for index in range(len(BETAS)) for fold in candidate_matrix.FOLDS
    ]
    declarations = frozen.get("cell_receipts")
    if type(declarations) is not list or len(declarations) != len(expected_names):
        raise ValueError("matrix: expected all 24 cell receipt declarations")
    rows = []
    for expected_name, declaration in zip(expected_names, declarations, strict=True):
        if type(declaration) is not dict or declaration.get("path") != expected_name:
            raise ValueError("matrix: cell receipt order or name differs from frozen contract")
        path = directory / expected_name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"matrix: missing regular cell receipt {expected_name}")
        encoded = path.read_bytes()
        if declaration.get("sha256") != _hash(encoded):
            raise ValueError(f"matrix: cell receipt hash mismatch {expected_name}")
        try:
            cell = json.loads(encoded)
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"matrix: malformed cell receipt {expected_name}") from error
        if (cell.get("schema") != candidate_matrix.CELL_SCHEMA
                or cell.get("complete") is not True
                or cell.get("identity") != identity
                or cell.get("receipt_sha256") != _receipt_hash(cell)):
            raise ValueError(f"matrix: invalid cell receipt integrity {expected_name}")
        row = cell.get("row")
        if type(row) is not dict or row.get("beta") != float(BETAS[len(rows) // 3]) \
                or row.get("fold") != len(rows) % 3:
            raise ValueError(f"matrix: cell receipt order differs from frozen contract {expected_name}")
        rows.append(row)

    candidates, selected = candidate_matrix.aggregate_candidates(rows)
    if candidates != frozen.get("candidates") or selected != frozen.get("selected"):
        raise ValueError("matrix: candidate scores or selection do not reproduce from cell receipts")
    if selected is None:
        raise ValueError("matrix: no candidate completed every required fold")
    selected_row = next(row for row in candidates if row["id"] == selected)
    if selected_row["status"] != "complete":
        raise ValueError("matrix: selected candidate is not complete")
    return frozen, selected_row, plan, handle


def _write_once(path: Path, body: dict) -> dict:
    destination = _safe_data_path(path, must_exist=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination = _safe_data_path(destination, must_exist=False)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite final-refit receipt: {destination}")
    receipt = dict(body)
    receipt["receipt_sha256"] = _receipt_hash(receipt)
    encoded = _canonical(receipt) + b"\n"
    staging = destination.with_name(destination.name + ".part")
    if staging.exists() or staging.is_symlink():
        raise FileExistsError(f"refusing to overwrite staging file: {staging}")
    fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        # An exclusive hard-link publishes the complete bytes atomically and
        # refuses an existing destination on Windows and POSIX filesystems.
        os.link(staging, destination)
    finally:
        try:
            staging.unlink()
        except FileNotFoundError:
            pass
    return receipt


def run_final_refit(raw: bytes, matrix_dir: Path, output_path: Path, *,
                    wall_seconds: float = 120.) -> dict:
    """Validate the complete selected matrix, fit only final development rows, and freeze once."""
    if type(raw) is not bytes or len(raw) > 8_388_608:
        raise ValueError("request: bounded immutable bytes under the 8 MiB contract required")
    if type(wall_seconds) not in (int, float) or not 0. < wall_seconds <= 120.:
        raise ValueError("wall_seconds: the approved per-fit cap is (0, 120]")
    matrix_path = _safe_data_path(matrix_dir, must_exist=True) / "matrix.json"
    frozen, selected, plan, handle = _load_and_verify_matrix(raw, matrix_dir)
    if output_path.name != f"final-refit-{selected['id']}.json":
        raise ValueError("output: filename must identify the frozen selected candidate")
    fit_rows = tuple(plan["final_refit_rows"]["data"])
    development = set(plan["partition"]["development_rows"]["data"])
    outer = set(plan["partition"]["outer_rows"]["data"])
    if not set(fit_rows).issubset(development) or not set(fit_rows).isdisjoint(outer):
        raise ValueError("partition: final refit rows must be development-only and outer-disjoint")

    beta = float(selected["beta"])
    l2_start = magnetic_calibration.fit_l2_final_refit(
        raw, beta, wall_seconds=float(wall_seconds),
    )
    if selected["penalty"] == "l2":
        fit = l2_start
    elif l2_start.get("status") == "converged":
        fit = magnetic_calibration.fit_sparse_final_refit(
            raw, beta, l2_result=l2_start, wall_seconds=float(wall_seconds),
        )
    else:
        fit = {
            "schema": "magnetic-linear-sparse-fold-result-1",
            "status": "failed", "reason": "final_refit_l2_start_failed",
            "fold_index": -1, "fit_rows": list(fit_rows), "beta": beta,
            "l2_start": l2_start,
            "claims": {"candidate_selected": False,
                       "outer_evaluation_performed": False,
                       "method_accepted": False, "online_admitted": False},
        }

    if fit.get("schema") == "magnetic-linear-l2-fold-result-1":
        terminal = fit.get("terminal_audits")
        kkt = fit.get("normalized_projected_kkt_inf")
        numerically_certified = (
            type(terminal) in (tuple, list) and bool(terminal)
            and all(type(row) is dict and row.get("passed") is True for row in terminal)
            and type(kkt) in (int, float)
            and math.isfinite(kkt)
            and kkt <= magnetic_calibration.TERMINAL.required_kkt_normalized
        )
    else:
        stages = fit.get("stages")
        numerically_certified = (
            type(stages) is list
            and len(stages) == len(magnetic_calibration.magnetic_regularization.SPARSE_EPSILON_Q)
            and all(type(stage) is dict and stage.get("status") == "converged"
                    for stage in stages)
            and type(fit.get("normalized_projected_gradient_inf")) in (int, float)
            and type(fit.get("final_gradient_limit")) in (int, float)
            and math.isfinite(fit["normalized_projected_gradient_inf"])
            and math.isfinite(fit["final_gradient_limit"])
            and fit["normalized_projected_gradient_inf"] <= fit["final_gradient_limit"]
        )
    converged = (
        fit.get("status") == "converged"
        and fit.get("fold_index") == -1
        and fit.get("beta") == beta
        and tuple(fit.get("fit_rows", ())) == fit_rows
        and numerically_certified
    )
    if converged:
        model = fit.get("model_q")
        expected_active = plan["preflight"]["active_cells"]
        prediction = fit.get("prediction_nT")
        residual = fit.get("residual_observed_minus_predicted_nT")
        if (getattr(model, "dtype", None) != "float64"
                or getattr(model, "ndim", None) != 1
                or getattr(model, "size", None) != expected_active):
            converged = False
        elif not np.isfinite(model).all():
            converged = False
        elif (getattr(prediction, "shape", (None,))[0] != len(fit_rows)
              or getattr(residual, "shape", None) != getattr(prediction, "shape", None)):
            converged = False
    current_commit = _current_commit()
    matrix_bytes = matrix_path.read_bytes()
    cli_path = Path(__file__).resolve().parents[1] / "scripts" / "run_m04_final_refit.py"
    body = {
        "schema": SCHEMA,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "converged" if converged else "failed",
        "identity": {
            "matrix_sha256": _hash(matrix_bytes),
            "matrix_product_commit": frozen["identity"]["product_commit"],
            "final_refit_product_commit": current_commit,
            "request_sha256": _hash(raw),
            "geometry_seal_sha256": plan["identity"]["seal_sha256"],
            "partition_sha256": plan["partition"]["sha256"],
            "selected_candidate": selected["id"],
            "selected_score": selected["score"],
            "runner_sha256": _hash(Path(__file__).read_bytes()),
            "cli_sha256": _hash(cli_path.read_bytes()),
            "wall_seconds": float(wall_seconds),
            "sources": {
                "magnetic_calibration.py": _hash(Path(magnetic_calibration.__file__).read_bytes()),
                "magnetic_candidate_matrix.py": _hash(Path(candidate_matrix.__file__).read_bytes()),
                "magnetic_fold_score.py": _hash(Path(magnetic_fold_score.__file__).read_bytes()),
                "magnetic_survey.py": _hash(Path(magnetic_survey.__file__).read_bytes()),
            },
        },
        "partition": {
            "fit_rows": list(fit_rows),
            "fit_row_count": len(fit_rows),
            "outer_rows_read_for_scoring": False,
            "outer_evaluation_performed": False,
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": version("numpy"),
            "scipy": version("scipy"),
            "simpeg": version("simpeg"),
            "discretize": version("discretize"),
        },
        "fit": _jsonable(fit),
        "l2_final_refit_start": (
            _jsonable(l2_start) if selected["penalty"] == "sparse_smallness" else None
        ),
        "frozen_model_sha256": (
            candidate_matrix.model_q_sha256(fit["model_q"]) if converged else None
        ),
        "claims": {
            "candidate_selected_by_complete_development_folds": True,
            "final_development_refit_performed": True,
            "model_frozen_before_outer_evaluation": converged,
            "outer_evaluation_performed": False,
            "field_validation": False,
            "method_accepted": False,
            "online_admitted": False,
        },
    }
    receipt = _write_once(output_path, body)
    return receipt


def verify_final_refit(raw: bytes, matrix_dir: Path, receipt_path: Path) -> dict:
    """Reopen and verify the write-once freeze against its exact source commits."""
    directory = _safe_data_path(matrix_dir, must_exist=True)
    path = _safe_data_path(receipt_path, must_exist=True)
    if path.parent != directory:
        raise ValueError("receipt: final-refit file must be beside its candidate matrix")
    frozen, selected, plan, handle = _load_and_verify_matrix(raw, matrix_dir)
    if path.name != f"final-refit-{selected['id']}.json":
        raise ValueError("receipt: filename does not match the selected candidate")
    if path.stat().st_size > 128 * 1024 * 1024:
        raise ValueError("receipt: exceeds the bounded M04 result size")
    try:
        receipt = json.loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("receipt: malformed final-refit JSON") from error
    if (type(receipt) is not dict or receipt.get("schema") != SCHEMA
            or receipt.get("receipt_sha256") != _receipt_hash(receipt)
            or receipt.get("status") != "converged"):
        raise ValueError("receipt: schema, integrity, or convergence check failed")
    identity = receipt.get("identity")
    final_commit = identity.get("final_refit_product_commit") if type(identity) is dict else None
    current_commit = _current_commit()
    if (type(final_commit) is not str or len(final_commit) != 40
            or any(char not in "0123456789abcdef" for char in final_commit)
            or not _is_ancestor(final_commit, current_commit)):
        raise ValueError("receipt: final-refit source commit is not an ancestor of current HEAD")
    expected = {
        "matrix_sha256": _hash((directory / "matrix.json").read_bytes()),
        "matrix_product_commit": frozen["identity"]["product_commit"],
        "request_sha256": _hash(raw),
        "geometry_seal_sha256": plan["identity"]["seal_sha256"],
        "partition_sha256": plan["partition"]["sha256"],
        "selected_candidate": selected["id"],
        "selected_score": selected["score"],
    }
    if any(identity.get(key) != value for key, value in expected.items()):
        raise ValueError("receipt: matrix, request, partition, or selection identity mismatch")

    root = Path(__file__).resolve().parents[1]
    committed_files = {
        "runner_sha256": "data-pipeline/magnetic_final_refit.py",
        "cli_sha256": "scripts/run_m04_final_refit.py",
    }
    for identity_key, relative in committed_files.items():
        blob = subprocess.run(
            ["git", "-C", str(root), "show", f"{final_commit}:{relative}"],
            check=True, capture_output=True,
        ).stdout
        if identity.get(identity_key) != _hash(blob):
            raise ValueError(f"receipt: committed source hash mismatch for {relative}")
    source_paths = {
        "magnetic_calibration.py": "data-pipeline/magnetic_calibration.py",
        "magnetic_candidate_matrix.py": "data-pipeline/magnetic_candidate_matrix.py",
        "magnetic_fold_score.py": "data-pipeline/magnetic_fold_score.py",
        "magnetic_survey.py": "data-pipeline/magnetic_survey.py",
    }
    source_hashes = identity.get("sources")
    if type(source_hashes) is not dict:
        raise ValueError("receipt: missing source hashes")
    for name, relative in source_paths.items():
        blob = subprocess.run(
            ["git", "-C", str(root), "show", f"{final_commit}:{relative}"],
            check=True, capture_output=True,
        ).stdout
        if source_hashes.get(name) != _hash(blob):
            raise ValueError(f"receipt: committed source hash mismatch for {relative}")

    partition = receipt.get("partition")
    fit = receipt.get("fit")
    if type(partition) is not dict or type(fit) is not dict:
        raise ValueError("receipt: missing fit or partition")
    rows = tuple(plan["final_refit_rows"]["data"])
    if (partition.get("fit_rows") != list(rows)
            or partition.get("fit_row_count") != len(rows)
            or partition.get("outer_rows_read_for_scoring") is not False
            or partition.get("outer_evaluation_performed") is not False
            or not set(rows).issubset(plan["partition"]["development_rows"]["data"])
            or not set(rows).isdisjoint(plan["partition"]["outer_rows"]["data"])):
        raise ValueError("receipt: final refit is not the sealed development-only partition")
    expected_schema = ("magnetic-linear-l2-fold-result-1" if selected["penalty"] == "l2"
                       else "magnetic-linear-sparse-fold-result-1")
    model_values = fit.get("model_q")
    model = np.asarray(model_values, dtype=np.float64)
    if (fit.get("schema") != expected_schema or fit.get("status") != "converged"
            or fit.get("fold_index") != -1 or fit.get("beta") != selected["beta"]
            or fit.get("fit_rows") != list(rows) or model.ndim != 1
            or model.size != plan["preflight"]["active_cells"]
            or not np.isfinite(model).all()
            or candidate_matrix.model_q_sha256(model) != receipt.get("frozen_model_sha256")):
        raise ValueError("receipt: fitted model does not match the selected source-bound refit")
    prediction = np.asarray(fit.get("prediction_nT"), dtype=np.float64)
    residual = np.asarray(fit.get("residual_observed_minus_predicted_nT"), dtype=np.float64)
    component_count = 1 if handle.metadata()["processing"]["quantity"] == "linear_tmi_nT" else 3
    if prediction.ndim == 1 and component_count == 1 and prediction.size == len(rows):
        prediction = prediction.reshape(len(rows), 1)
    if residual.ndim == 1 and component_count == 1 and residual.size == len(rows):
        residual = residual.reshape(len(rows), 1)
    if (prediction.ndim != 2 or prediction.shape != (len(rows), component_count)
            or residual.shape != prediction.shape or not np.isfinite(prediction).all()
            or not np.isfinite(residual).all()):
        raise ValueError("receipt: fit predictions/residuals are incomplete or non-finite")
    claims = receipt.get("claims")
    if (type(claims) is not dict
            or claims.get("model_frozen_before_outer_evaluation") is not True
            or claims.get("outer_evaluation_performed") is not False
            or claims.get("field_validation") is not False
            or claims.get("method_accepted") is not False
            or claims.get("online_admitted") is not False):
        raise ValueError("receipt: scientific acceptance boundary is inconsistent")
    return receipt
