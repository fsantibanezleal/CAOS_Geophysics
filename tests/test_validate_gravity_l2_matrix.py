import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_gravity_l2_matrix", ROOT / "scripts" / "validate_gravity_l2_matrix.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def write_junit(path: Path, *, omit=None, bad_condition=None, duplicate=False):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", name="pytest", tests="24", failures="0", errors="0", skipped="0")
    cells = [(condition, family) for condition in range(4) for family in range(6)]
    if omit is not None:
        cells.remove(omit)
    for condition, family in cells:
        wrms = 1.2 if bad_condition == (condition, family) else 3.0 if condition == 3 else 1.2
        outcome = {
            "condition": condition,
            "family": family,
            "selection_status": "selected",
            "selected_index": 7,
            "input_sha256": "a" * 64,
            "calibration_sha256": f"{condition:02x}{family:02x}".ljust(64, "b"),
            "outer_wrms": wrms,
            "model_rmse_ratio": 0.9,
            "candidates": [{"index": index, "folds": [{}, {}, {}]} for index in range(8)],
        }
        case = ET.SubElement(suite, "testcase", classname="tests.numerics.test_gravity_l2_selection",
                             name=f"test_complete_locked_l2_control_matrix[{condition}-{family}]")
        props = ET.SubElement(case, "properties")
        ET.SubElement(props, "property", name="locked_l2_outcome", value=json.dumps(outcome, sort_keys=True))
    if duplicate and omit is None:
        condition, family = cells[0]
        case = ET.SubElement(suite, "testcase", classname="tests.numerics.test_gravity_l2_selection",
                             name=f"test_complete_locked_l2_control_matrix[{condition}-{family}]")
        props = ET.SubElement(case, "properties")
        outcome = {
            "condition": condition, "family": family, "selection_status": "selected", "selected_index": 7,
            "input_sha256": "a" * 64, "calibration_sha256": f"{condition:02x}{family:02x}".ljust(64, "b"),
            "outer_wrms": 1.2, "model_rmse_ratio": 0.9,
            "candidates": [{"index": index, "folds": [{}, {}, {}]} for index in range(8)],
        }
        ET.SubElement(props, "property", name="locked_l2_outcome", value=json.dumps(outcome, sort_keys=True))
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def test_all_cells_and_identical_replay_are_accounted_once(tmp_path):
    receipt = tmp_path / "matrix.xml"
    write_junit(receipt, duplicate=True)
    result = CHECK.validate_junit([receipt])
    assert result["cell_count"] == 24
    assert result["duplicate_identical_replays"] == 1
    assert result["conditions"]["0"]["outer_wrms_max"] == 1.2
    assert result["conditions"]["3"]["classification"] == "poor_under_declared_noise"
    assert result["scientific_acceptance"] is False


def test_missing_cell_is_not_mistaken_for_a_complete_matrix(tmp_path):
    receipt = tmp_path / "missing.xml"
    write_junit(receipt, omit=(2, 4))
    with pytest.raises(ValueError, match="missing locked matrix cells"):
        CHECK.validate_junit([receipt])


def test_outlier_condition_must_be_classified_as_poor(tmp_path):
    receipt = tmp_path / "false-clean.xml"
    write_junit(receipt, bad_condition=(3, 2))
    with pytest.raises(ValueError, match="unmodelled nuisance control"):
        CHECK.validate_junit([receipt])


def test_nonidentical_duplicate_is_rejected(tmp_path):
    receipt = tmp_path / "duplicate.xml"
    write_junit(receipt, duplicate=True)
    tree = ET.parse(receipt)
    suite = tree.getroot().find("testsuite")
    duplicate = suite.findall("testcase")[-1]
    payload = duplicate.find("./properties/property")
    outcome = json.loads(payload.attrib["value"])
    outcome["outer_wrms"] = 1.3
    payload.set("value", json.dumps(outcome, sort_keys=True))
    tree.write(receipt, encoding="utf-8", xml_declaration=True)
    with pytest.raises(ValueError, match="nonidentical duplicate"):
        CHECK.validate_junit([receipt])
