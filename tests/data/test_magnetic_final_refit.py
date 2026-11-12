"""Fail-closed selection verification and write-once M04 final freeze."""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "data-pipeline"))
import magnetic_calibration  # noqa: E402
import magnetic_candidate_matrix as matrix  # noqa: E402
import magnetic_final_refit as final_refit  # noqa: E402
import magnetic_fold_score  # noqa: E402
import magnetic_survey  # noqa: E402


def _write_matrix(tmp_path, raw, *, selected_penalty="l2"):
    matrix_dir = tmp_path / "research-runs" / "selected-matrix"
    matrix_dir.mkdir(parents=True)
    plan = {
        "identity": {"seal_sha256": "c" * 64},
        "partition": {
            "sha256": "d" * 64,
            "development_rows": {"data": [0, 1, 2]},
            "outer_rows": {"data": [3]},
        },
        "preflight": {"active_cells": 3},
        "final_refit_rows": {"data": [0, 1, 2]},
    }
    identity = {
        "product_commit": "a" * 40,
        "request_sha256": hashlib.sha256(raw).hexdigest(),
        "geometry_seal_sha256": plan["identity"]["seal_sha256"],
        "partition_sha256": plan["partition"]["sha256"],
        "sources": {
            "magnetic_calibration.py": hashlib.sha256(Path(magnetic_calibration.__file__).read_bytes()).hexdigest(),
            "magnetic_fold_score.py": hashlib.sha256(Path(magnetic_fold_score.__file__).read_bytes()).hexdigest(),
            "magnetic_survey.py": hashlib.sha256(Path(magnetic_survey.__file__).read_bytes()).hexdigest(),
        },
    }
    rows = []
    declarations = []
    for beta_index, beta in enumerate(matrix.BETAS):
        for fold in matrix.FOLDS:
            row = {"beta": float(beta), "fold": fold, "candidates": {}}
            scores = ((10., 20.) if selected_penalty == "l2" else (20., 10.))
            for (penalty, phi_d) in zip(("l2", "sparse"), scores, strict=True):
                row["candidates"][penalty] = {"metric": {
                    "fold": fold, "status": "converged", "reason": None,
                    "n_rows": 1, "n_components": 1, "phi_d": phi_d,
                    "rms_nT": 1., "normalized_rms": 1., "kkt_inf": 0.,
                    "model_sha256": "e" * 64,
                }}
            name = f"beta-{beta_index:02d}-fold-{fold}.json"
            receipt = matrix._receipt_with_hash({
                "schema": matrix.CELL_SCHEMA, "complete": True,
                "identity": identity, "row": row,
            })
            encoded = matrix._canonical(receipt) + b"\n"
            (matrix_dir / name).write_bytes(encoded)
            declarations.append({"path": name, "sha256": hashlib.sha256(encoded).hexdigest()})
            rows.append(row)
    candidates, selected = matrix.aggregate_candidates(rows)
    aggregate = {
        "schema": matrix.SCHEMA,
        "identity": identity,
        "candidates": candidates,
        "selected": selected,
        "cell_receipts": declarations,
        "claims": {"candidate_matrix_complete": True},
    }
    (matrix_dir / "matrix.json").write_bytes(matrix._canonical(aggregate) + b"\n")
    return matrix_dir, plan, aggregate


def _fit(rows, beta):
    return {
        "schema": "magnetic-linear-l2-fold-result-1",
        "status": "converged", "reason": None, "fold_index": -1,
        "fit_rows": list(rows), "beta": beta,
        "model_q": np.array([.1, .2, .3], dtype=np.float64),
        "prediction_nT": np.array([[1.], [2.], [3.]], dtype=np.float64),
        "residual_observed_minus_predicted_nT": np.array([[.1], [-.1], [0.]], dtype=np.float64),
        "normalized_projected_kkt_inf": 1e-13,
        "terminal_audits": [{"passed": True}],
        "objective": {"phi_d": 1., "phi_m": 2.},
        "claims": {"candidate_selected": False, "outer_evaluation_performed": False,
                   "method_accepted": False, "online_admitted": False},
    }


def _configure(monkeypatch, tmp_path, plan):
    monkeypatch.setattr(final_refit, "local_data_root", lambda: tmp_path.resolve())
    monkeypatch.setattr(final_refit, "_current_commit", lambda: "b" * 40)
    monkeypatch.setattr(final_refit, "_is_ancestor", lambda old, new: True)
    monkeypatch.setattr(
        final_refit, "parse_request",
        lambda raw: SimpleNamespace(metadata=lambda: {"processing": {"quantity": "linear_tmi_nT"}}),
    )
    monkeypatch.setattr(final_refit.magnetic_survey, "plan_geometry", lambda handle: plan)


def test_recomputes_all_fold_scores_then_freezes_selected_dev_only_model(tmp_path, monkeypatch):
    raw = b"sealed request bytes"
    matrix_dir, plan, aggregate = _write_matrix(tmp_path, raw)
    _configure(monkeypatch, tmp_path, plan)
    seen = []

    def fit(raw_bytes, beta, *, wall_seconds):
        seen.append((raw_bytes, beta, wall_seconds))
        return _fit(plan["final_refit_rows"]["data"], beta)

    monkeypatch.setattr(final_refit.magnetic_calibration, "fit_l2_final_refit", fit)
    target = matrix_dir / f"final-refit-{aggregate['selected']}.json"
    receipt = final_refit.run_final_refit(raw, matrix_dir, target)

    assert receipt["status"] == "converged"
    assert receipt["identity"]["selected_candidate"] == "beta-1000-l2"
    assert receipt["partition"] == {
        "fit_rows": [0, 1, 2], "fit_row_count": 3,
        "outer_rows_read_for_scoring": False, "outer_evaluation_performed": False,
    }
    assert receipt["claims"]["model_frozen_before_outer_evaluation"] is True
    assert receipt["claims"]["outer_evaluation_performed"] is False
    assert seen == [(raw, 1000., 120.)]
    assert json.loads(target.read_bytes())["receipt_sha256"] == receipt["receipt_sha256"]

    repo = Path(__file__).parents[2]
    def committed_blob(command, *, check, capture_output):
        relative = command[-1].split(":", 1)[1]
        return SimpleNamespace(stdout=(repo / relative).read_bytes())
    monkeypatch.setattr(final_refit.subprocess, "run", committed_blob)
    verified = final_refit.verify_final_refit(raw, matrix_dir, target)
    assert verified["receipt_sha256"] == receipt["receipt_sha256"]
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        final_refit.run_final_refit(raw, matrix_dir, target)


def test_refuses_tampered_cell_before_running_solver(tmp_path, monkeypatch):
    raw = b"sealed request bytes"
    matrix_dir, plan, aggregate = _write_matrix(tmp_path, raw)
    _configure(monkeypatch, tmp_path, plan)
    (matrix_dir / "beta-07-fold-2.json").write_bytes(b"{}");
    called = []
    monkeypatch.setattr(final_refit.magnetic_calibration, "fit_l2_final_refit",
                        lambda *args, **kwargs: called.append(True))

    with pytest.raises(ValueError, match="cell receipt hash mismatch"):
        final_refit.run_final_refit(
            raw, matrix_dir,
            matrix_dir / f"final-refit-{aggregate['selected']}.json",
        )
    assert not called


def test_refuses_failed_final_refit_certificate_as_model_freeze(tmp_path, monkeypatch):
    raw = b"sealed request bytes"
    matrix_dir, plan, aggregate = _write_matrix(tmp_path, raw)
    _configure(monkeypatch, tmp_path, plan)
    failed = _fit(plan["final_refit_rows"]["data"], 1000.)
    failed["terminal_audits"] = [{"passed": False}]
    monkeypatch.setattr(final_refit.magnetic_calibration, "fit_l2_final_refit",
                        lambda *args, **kwargs: failed)
    receipt = final_refit.run_final_refit(
        raw, matrix_dir,
        matrix_dir / f"final-refit-{aggregate['selected']}.json",
    )
    assert receipt["status"] == "failed"
    assert receipt["frozen_model_sha256"] is None
    assert receipt["claims"]["model_frozen_before_outer_evaluation"] is False
    assert receipt["claims"]["method_accepted"] is False


def test_sparse_selection_refits_from_same_beta_final_l2_model(tmp_path, monkeypatch):
    raw = b"sealed request bytes"
    matrix_dir, plan, aggregate = _write_matrix(tmp_path, raw, selected_penalty="sparse_smallness")
    _configure(monkeypatch, tmp_path, plan)
    l2_start = _fit(plan["final_refit_rows"]["data"], 1000.)
    sparse_fit = {
        "schema": "magnetic-linear-sparse-fold-result-1",
        "status": "converged", "fold_index": -1, "beta": 1000.,
        "fit_rows": [0, 1, 2],
        "model_q": np.array([.1, .2, .3], dtype=np.float64),
        "prediction_nT": np.ones((3, 1), dtype=np.float64),
        "residual_observed_minus_predicted_nT": np.zeros((3, 1), dtype=np.float64),
        "stages": [{"status": "converged"} for _ in range(8)],
        "normalized_projected_gradient_inf": 1e-12,
        "final_gradient_limit": 1e-8,
        "claims": {"candidate_selected": False, "outer_evaluation_performed": False,
                   "method_accepted": False, "online_admitted": False},
    }
    calls = []
    monkeypatch.setattr(final_refit.magnetic_calibration, "fit_l2_final_refit",
                        lambda *args, **kwargs: l2_start)
    monkeypatch.setattr(final_refit.magnetic_calibration, "fit_sparse_final_refit",
                        lambda *args, **kwargs: calls.append((args, kwargs)) or sparse_fit)
    receipt = final_refit.run_final_refit(
        raw, matrix_dir,
        matrix_dir / f"final-refit-{aggregate['selected']}.json",
    )
    assert aggregate["selected"] == "beta-1000-sparse_smallness"
    assert receipt["status"] == "converged"
    assert receipt["identity"]["selected_candidate"] == aggregate["selected"]
    assert calls == [((raw, 1000.), {"l2_result": l2_start, "wall_seconds": 120.})]
