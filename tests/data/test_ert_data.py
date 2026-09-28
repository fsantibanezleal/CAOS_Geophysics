"""Slagdump source identity, strict physical parse and rights boundary."""
import hashlib
from pathlib import Path
import subprocess

import numpy as np
import pytest

from ert import ERTError, Survey, parse_ohm, qc
from sources import acquire_source, load_ledger

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/downloads/pygimli/slagdump.ohm"


def _synthetic_ohm() -> str:
    lines = ["# A Wenner array with 2m was applied.", "8# Number of sensors", "#x z"]
    lines.extend(f"{2*i} 0" for i in range(8))
    lines.extend(["5# Number of data", "#a b m n R"])
    lines.extend(f"{i+1} {i+4} {i+2} {i+3} {1+i/10}" for i in range(5))
    return "\n".join(lines) + "\n"


def test_pinned_source_and_ignored_receipt():
    record = load_ledger()["pygimli-slagdump"]
    assert record["acquisition"] == "manual" and record["rights_decision"] == "provider-link-only"
    assert record["expected_bytes"] == 5435
    assert record["sha256"] == "c010a11b78ea4392cb926d675e847c74010b4cdec536aacaf8db6a644e886de2"
    assert "3bab9c6b96a606e2ca12cbdafc8c7da4f1b73c67" in record["object_url"]
    tracked = subprocess.run(["git", "ls-files", "data/downloads", "data/raw"], cwd=ROOT,
                             capture_output=True, text=True, check=True)
    assert tracked.stdout.strip() == ""
    if RAW.exists():
        assert hashlib.sha256(RAW.read_bytes()).hexdigest() == record["sha256"]
        _, target, receipt = acquire_source("pygimli-slagdump")
        assert target == RAW and receipt["validation_status"] == "hash-verified"


def test_strict_sensor_and_quadrupole_contract(tmp_path):
    path = tmp_path / "survey.ohm"
    valid = _synthetic_ohm()
    path.write_text(valid, encoding="utf-8")
    survey = parse_ohm(path)
    assert survey.sensors_xz_m.shape == (8, 2)
    assert survey.abmn.shape == (5, 4)
    assert np.array_equal(survey.abmn[0], [0, 3, 1, 2])
    assert survey.resistance_ohm.tolist() == [1, 1.1, 1.2, 1.3, 1.4]
    invalid = [
        (valid.replace("#x z", "#x y"), "sensor columns"),
        (valid.replace("#a b m n R", "#a b m n rhoa"), "measurement columns"),
        (valid.replace("2 0", "nan 0", 1), "non-finite"),
        (valid.replace("2 0", "0 0", 1), "strictly increasing"),
        (valid.replace("1 4 2 3", "1 9 2 3", 1), "outside 1..8"),
        (valid.replace("2 5 3 4", "1 4 2 3", 1), "duplicate ABMN"),
        (valid.replace("1 4 2 3", "1 4 3 2", 1), "invalid distinct"),
        (valid.replace("1 4 2 3", "1 5 2 3", 1), "equally spaced Wenner"),
        (valid.replace("1 4 2 3 1.0", "1 4 2 3 0.0", 1), "zero resistance"),
        (valid + "unexpected payload\n", "trailing payload"),
        (valid.replace("5# Number of data", "6# Number of data"), "truncated"),
    ]
    for text, message in invalid:
        path.write_text(text, encoding="utf-8")
        with pytest.raises(ERTError, match=message):
            parse_ohm(path)


def test_qc_and_absent_reciprocals(tmp_path):
    path = tmp_path / "survey.ohm"
    path.write_text(_synthetic_ohm(), encoding="utf-8")
    survey = parse_ohm(path)
    result = qc(survey)
    assert result["measurement_count"] == 5
    assert result["reciprocal_status"] == "not_available"
    assert result["instrument_error_status"] == "not_supplied"
    assert result["flagged_rows"] == []
    assert result["ab_distance_m_range"] == [6.0, 6.0]
    assert result["duplicate_quadrupoles"] == 0
    reciprocal = _synthetic_ohm().replace("5 8 6 7 1.4", "2 3 1 4 1.4")
    path.write_text(reciprocal, encoding="utf-8")
    pairs = qc(parse_ohm(path))["reciprocal_pairs"]
    assert pairs == [[0, 4]]
    flag_survey = Survey(np.column_stack((np.arange(20, dtype=float), np.zeros(20))),
                         np.asarray([[i, i + 3, i + 1, i + 2] for i in range(16)]),
                         np.asarray([1 + 0.01 * i for i in range(15)] + [1000.0]), ())
    flagged = qc(flag_survey)
    assert flagged["measurement_count"] == 16 and flagged["flagged_rows"] == [15]
    if RAW.exists():
        field = qc(parse_ohm(RAW))
        assert field["sensor_count"] == 38 and field["measurement_count"] == 222
        assert field["topographic_relief_m"] > 0
        assert field["reciprocal_status"] == "not_available"
        assert all(0 <= row < field["measurement_count"] for row in field["flagged_rows"])


def test_m07_documented_boundaries():
    guide = (ROOT / "docs/guides/05_sources.md").read_text(encoding="utf-8")
    design = (ROOT / "docs/design/features/m07-slagdump-ert/design.md").read_text(encoding="utf-8")
    for term in ("Slagdump", "BGR", "reciprocal", "held-out", "pyGIMLi", "provider-link-only"):
        assert term in guide and term in design
