"""Offline controls for the sealed one-time M04 outer evaluator."""
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "data-pipeline"))
import magnetic_final_refit  # noqa: E402
import magnetic_inverse  # noqa: E402
import magnetic_outer_evaluation as outer  # noqa: E402


def _fixture(monkeypatch, tmp_path, *, fail_forward=False):
    root = tmp_path.resolve()
    matrix_dir = root / "research-runs" / "matrix"
    matrix_dir.mkdir(parents=True)
    matrix_path = matrix_dir / "matrix.json"
    matrix_path.write_text("{}", encoding="utf-8")
    freeze_path = matrix_dir / "final-refit-beta-1.json"
    freeze_path.write_text("freeze", encoding="utf-8")
    raw = b"immutable-request"
    rows = [0, 1, 2, 3]
    plan = {
        "identity": {"seal_sha256": "a" * 64},
        "partition": {
            "sha256": "b" * 64,
            "development_rows": {"data": [0, 1, 2]},
            "outer_rows": {"data": [3]},
        },
        "inventory": {"usable": {"data": [True] * 4}},
    }
    selected = {"id": "beta-1-l2", "beta": 1., "penalty": "l2", "score": 2.}
    matrix = {"candidates": [
        {"id": "beta-1-l2", "penalty": "l2", "status": "complete", "score": 2., "beta": 1.},
        {"id": "beta-1-sparse", "penalty": "sparse_smallness", "status": "complete", "score": 3., "beta": 1.},
    ]}
    prediction = np.array([.5, 1.5, 2., 3.], dtype=np.float64)
    freeze = {
        "identity": {
            "selected_candidate": selected["id"],
            "matrix_product_commit": "c" * 40,
            "final_refit_product_commit": "d" * 40,
        },
        "receipt_sha256": "e" * 64,
        "frozen_model_sha256": "f" * 64,
        "fit": {
            "model_q": [.1], "fit_rows": [0, 1],
            "prediction_nT": [.5, 1.5],
            "residual_observed_minus_predicted_nT": [.5, .5],
        },
    }
    handle_metadata = {
        "processing": {"quantity": "linear_tmi_nT"},
        "acquisition": {"row_ids": [f"r{row}" for row in rows]},
    }
    handle = SimpleNamespace(metadata=lambda: handle_metadata)
    monkeypatch.setattr(outer, "local_data_root", lambda: root)
    monkeypatch.setattr(outer, "_committed_source_bytes",
                        lambda path, _commit, require_worktree_match: path.read_bytes())
    monkeypatch.setattr(magnetic_final_refit, "local_data_root", lambda: root)
    monkeypatch.setattr(magnetic_final_refit, "verify_final_refit", lambda *args: freeze)
    monkeypatch.setattr(magnetic_final_refit, "_load_and_verify_matrix",
                        lambda *args: (matrix, selected, plan, handle))
    monkeypatch.setattr(outer, "parse_request",
                        lambda raw_bytes: SimpleNamespace(metadata=lambda: handle_metadata))

    class Operator:
        quantity = "linear_tmi_nT"
        parameters = 1

        def evaluate(self, model):
            return {"prediction_nT": prediction.copy()}

    def build_operator(*args, **kwargs):
        if fail_forward:
            raise RuntimeError("controlled forward failure")
        return Operator()

    monkeypatch.setattr(magnetic_inverse, "build_operator", build_operator)
    observed_all = np.array([1., 2., 2.5, 3.5], dtype=np.float64)

    def selected_likelihood(_handle, flat_indices, _seal):
        indices = np.asarray(flat_indices, dtype=np.int64)
        document = {
            "observations": {"values": {"shape": [len(indices), 1]}},
            "noise": {"kind": "diagonal_sd", "cross_partition_dependence": "none"},
        }
        return document, observed_all[indices].copy(), np.ones((len(indices), 1), dtype=np.float64)

    monkeypatch.setattr(outer, "read_selected_likelihood", selected_likelihood)
    return raw, matrix_dir, freeze_path, matrix_path


def test_outer_evaluation_is_write_once_and_verifiable(monkeypatch, tmp_path):
    raw, matrix_dir, freeze_path, matrix_path = _fixture(monkeypatch, tmp_path)

    receipt = outer.run_outer_evaluation(raw, matrix_dir, freeze_path)

    assert receipt["status"] == "complete"
    assert receipt["selection"]["candidate_id"] == "beta-1-l2"
    assert receipt["prediction"]["rows"] == [0, 1, 2, 3]
    assert receipt["prediction"]["row_ids"] == ["r0", "r1", "r2", "r3"]
    assert receipt["prediction"]["residual_observed_minus_predicted_nT"] == [
        [.5], [.5], [.5], [.5],
    ]
    assert receipt["metrics"]["development"]["phi_d"] == pytest.approx(.75)
    assert receipt["metrics"]["outer"]["phi_d"] == pytest.approx(.25)
    assert receipt["metrics"]["outer"]["rms_nT"] == pytest.approx(.5)
    intent_path, result_path = outer.evaluation_paths(hashlib.sha256(matrix_path.read_bytes()).hexdigest())
    verified = outer.verify_outer_evaluation(raw, matrix_dir, freeze_path, result_path)
    assert verified["receipt_sha256"] == receipt["receipt_sha256"]
    with pytest.raises(FileExistsError, match="consumed one-time evaluation"):
        outer.run_outer_evaluation(raw, matrix_dir, freeze_path)
    assert intent_path.is_file() and result_path.is_file()


def test_failed_outer_attempt_also_consumes_matrix_token(monkeypatch, tmp_path):
    raw, matrix_dir, freeze_path, matrix_path = _fixture(monkeypatch, tmp_path, fail_forward=True)
    with pytest.raises(RuntimeError, match="controlled forward failure"):
        outer.run_outer_evaluation(raw, matrix_dir, freeze_path)
    intent_path, result_path = outer.evaluation_paths(hashlib.sha256(matrix_path.read_bytes()).hexdigest())
    assert outer._read_receipt(intent_path, outer.INTENT_SCHEMA)["status"] == "started"
    assert outer._read_receipt(result_path, outer.SCHEMA)["status"] == "failed"
    with pytest.raises(FileExistsError, match="consumed one-time evaluation"):
        outer.run_outer_evaluation(raw, matrix_dir, freeze_path)
