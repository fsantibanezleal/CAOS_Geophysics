"""Adversarial input, split, and claim-boundary tests for M07 ERT."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

import ert  # noqa: E402
from ert import ERTError, Survey, assumed_resistance_sigma, flat_halfspace_factors, parse_ohm, qc  # noqa: E402
from sources import SourceError, acquire_source, load_ledger  # noqa: E402


def _synthetic_ohm() -> str:
    lines = ["# A Wenner array with 2m was applied.", "8# Number of sensors", "#x z"]
    lines.extend(f"{2 * i} 0" for i in range(8))
    lines.extend(["5# Number of data", "#a b m n R"])
    lines.extend(f"{i + 1} {i + 4} {i + 2} {i + 3} {1 + i / 10}" for i in range(5))
    return "\n".join(lines) + "\n"


def test_wrong_source_bytes_are_not_imported(tmp_path):
    source = load_ledger()["pygimli-slagdump"]
    wrong = tmp_path / "slagdump.ohm"
    wrong.write_bytes(b"not the pinned provider object")
    with pytest.raises(SourceError, match="byte/hash mismatch"):
        acquire_source("pygimli-slagdump", local_file=wrong, root=tmp_path)
    assert not (tmp_path / source["raw_path"]).exists()
    assert not (tmp_path / "data/raw/acquisition/pygimli-slagdump.json").exists()


def test_malformed_ohm_rows_fail_closed(tmp_path):
    path = tmp_path / "survey.ohm"
    good = _synthetic_ohm()
    for bad, reason in (
        (good.replace("2 0", "nan 0", 1), "non-finite"),
        (good.replace("1 4 2 3", "1 9 2 3", 1), "outside 1..8"),
        (good.replace("1 4 2 3 1.0", "1 4 2 3 0.0", 1), "zero resistance"),
        (good + "unlisted row\n", "trailing payload"),
    ):
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(ERTError, match=reason):
            parse_ohm(path)


def test_absent_reciprocals_do_not_create_uncertainty(tmp_path):
    path = tmp_path / "survey.ohm"
    path.write_text(_synthetic_ohm(), encoding="utf-8")
    result = qc(parse_ohm(path))
    assert result["reciprocal_status"] == "not_available"
    assert result["instrument_error_status"] == "not_supplied"
    assert result["reciprocal_pairs"] == []


def test_flat_factor_matches_independent_signed_equation(tmp_path):
    path = tmp_path / "survey.ohm"
    path.write_text(_synthetic_ohm(), encoding="utf-8")
    survey = parse_ohm(path)
    actual = flat_halfspace_factors(survey)
    x = survey.sensors_xz_m[:, 0]
    expected = []
    for a, b, m, n in survey.abmn:
        denominator = (1 / abs(x[a] - x[m]) - 1 / abs(x[a] - x[n])
                       - 1 / abs(x[b] - x[m]) + 1 / abs(x[b] - x[n]))
        expected.append(2 * np.pi / denominator)
    assert np.all(np.isfinite(actual)) and np.all(actual > 0)
    assert actual == pytest.approx(expected, rel=1e-13)


def test_assumed_sigma_refuses_invalid_resistance():
    values = np.asarray([0.01, 1.0, 10.0])
    assert assumed_resistance_sigma(values).tolist() == pytest.approx([0.001, 0.03, 0.3])
    for invalid in (np.asarray([0.0]), np.asarray([-1.0]), np.asarray([np.nan])):
        with pytest.raises(ERTError, match="finite positive"):
            assumed_resistance_sigma(invalid)


def test_holdouts_are_disjoint_and_spatially_frozen():
    x = np.arange(100, dtype=float)
    abmn = np.asarray([[i, i + 3, i + 1, i + 2] for i in range(97)], dtype=int)
    survey = Survey(np.column_stack((x, np.zeros_like(x))), abmn, np.ones(len(abmn)), ())
    train, held = ert.holdout_indices(survey)
    block_train, block_held = ert.blocked_holdout_indices(survey)
    assert not set(train) & set(held) and len(train) + len(held) == len(abmn)
    assert not set(block_train) & set(block_held) and len(block_train) + len(block_held) == len(abmn)
    midpoint = (x[abmn[:, 0]] + x[abmn[:, 1]]) / 2
    assert np.all((midpoint[block_held] >= x[0] + 0.4 * (x[-1] - x[0]))
                  & (midpoint[block_held] <= x[0] + 0.6 * (x[-1] - x[0])))


def test_factor_failure_cannot_claim_field_inverse(tmp_path, monkeypatch):
    path = tmp_path / "survey.ohm"
    path.write_text(_synthetic_ohm(), encoding="utf-8")

    def fail_oracle(*args, **kwargs):
        raise ERTError("injected independent factor mismatch")

    monkeypatch.setattr(ert, "factors", fail_oracle)
    result = ert.run(path, source_sha256="a" * 64)
    assert result["inverse_status"] == "unverified"
    assert result["truth"] is None and result["field_geology_claim"] is None
    assert "inverse" not in result


def test_source_and_convergence_docs_preserve_nonclaims():
    requirements = (ROOT / "docs/design/features/m07-slagdump-ert/requirements.md").read_text(encoding="utf-8")
    convergence = (ROOT / "docs/design/features/m07-slagdump-ert/convergence.md").read_text(encoding="utf-8")
    assert "unresolved redistribution rights" in requirements
    assert "provider link only" in convergence.lower()
    assert "analytic-only run" in convergence.lower()
    assert "known geology" in requirements.lower()
    assert "known truth" in convergence.lower()
