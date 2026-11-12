"""Frozen M04 candidate order, complete-fold scoring, and tie semantics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "data-pipeline"))
import magnetic_candidate_matrix as matrix  # noqa: E402


def _cell(beta, fold, l2_score, sparse_score, *, sparse_failed=False):
    def candidate(score, failed=False):
        metric = {
            "fold": fold, "status": "failed" if failed else "converged",
            "reason": "retained_solver_failure" if failed else None,
            "n_rows": 10, "n_components": 10 if score is None else score[1],
            "phi_d": None if score is None else score[0],
            "rms_nT": None if failed else 1.0,
            "normalized_rms": None if failed else 1.0,
            "kkt_inf": None if failed else 1e-10,
            "model_sha256": None if failed else "a" * 64,
        }
        return {"metric": metric}

    return {
        "beta": beta, "fold": fold,
        "candidates": {
            "l2": candidate(l2_score),
            "sparse": candidate(sparse_score, sparse_failed),
        },
    }


def test_fixed_beta_major_candidate_order_and_ids():
    specs = matrix.candidate_specs()
    assert len(specs) == 16
    assert [row["penalty"] for row in specs[:4]] == [
        "l2", "sparse_smallness", "l2", "sparse_smallness"
    ]
    assert specs[0]["beta"] == .0001
    assert specs[-1]["beta"] == 1000.
    assert specs[0]["id"] == "beta-0p0001-l2"
    assert specs[1]["id"] == "beta-0p0001-sparse_smallness"


def test_candidate_requires_every_fold_and_uses_pooled_phi_over_components():
    cells = []
    for beta in matrix.BETAS:
        for fold in matrix.FOLDS:
            if beta == .0001:
                l2, sparse = ((10., 10.) if fold == 0 else (20., 20.)), (5., 10.)
            else:
                l2, sparse = (40., 10.), (40., 10.)
            cells.append(_cell(float(beta), fold, l2, sparse,
                               sparse_failed=beta == .0001 and fold == 2))

    candidates, selected = matrix.aggregate_candidates(cells)
    first_l2, first_sparse = candidates[:2]
    assert first_l2["status"] == "complete"
    assert first_l2["score"] == (10. + 20. + 20.) / (10. + 20. + 20.)
    assert first_sparse["status"] == "failed"
    assert first_sparse["score"] is None
    assert selected == first_l2["id"]


def test_score_ties_prefer_l2_then_larger_beta_then_id():
    cells = [
        _cell(float(beta), fold, (10., 10.), (10., 10.))
        for beta in matrix.BETAS for fold in matrix.FOLDS
    ]
    candidates, selected = matrix.aggregate_candidates(cells)
    assert all(row["status"] == "complete" and row["score"] == 1. for row in candidates)
    assert selected == matrix.candidate_id(1000., "l2")

\n