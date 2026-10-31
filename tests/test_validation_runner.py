"""Validation runner keeps pyGIMLi-backed scientific gates in their runtime."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("geophysics_validation_runner", ROOT / "tests/run_validation.py")
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_profile_lane_uses_dedicated_interpreter_and_all_native_profile_gates(tmp_path):
    interpreter = tmp_path / "profile-python.exe"
    junit = tmp_path / "profile.junit.xml"
    scratch = tmp_path / "profile-scratch"

    command = RUNNER.profile_lane_command(interpreter, junit, scratch, "field_result")

    assert command[0] == str(interpreter)
    assert command[1:3] == ["-m", "pytest"]
    assert command[3:6] == list(RUNNER.PROFILE_TESTS)
    assert "--basetemp=" + str(scratch) in command
    assert "--junitxml=" + str(junit) in command
    assert command[-2:] == ["-k", "field_result"]


def test_profile_lane_is_runnable_without_a_keyword(tmp_path):
    command = RUNNER.profile_lane_command(tmp_path / "python.exe", tmp_path / "out.xml", tmp_path / "scratch")

    assert command[3:6] == list(RUNNER.PROFILE_TESTS)
    assert "-k" not in command


def test_real_cap_resource_lane_isolated_from_suite_collection(tmp_path):
    interpreter = tmp_path / "pipeline-python.exe"
    junit = tmp_path / "resource.junit.xml"
    scratch = tmp_path / "resource-scratch"

    command = RUNNER.resource_lane_command(interpreter, junit, scratch, "real_cap")

    assert command[0] == str(interpreter)
    assert command[1:3] == ["-m", "pytest"]
    assert command[3] == RUNNER.RESOURCE_TEST
    assert "--basetemp=" + str(scratch) in command
    assert "--junitxml=" + str(junit) in command
    assert command[-2:] == ["-k", "real_cap"]


def test_offline_science_deselects_receipt_backed_and_isolated_resource_cases(tmp_path):
    command = RUNNER.offline_lane_command(
        tmp_path / "pipeline-python.exe", tmp_path / "science.junit.xml", tmp_path / "science-scratch")

    assert command.count("--deselect=" + RUNNER.RESOURCE_TEST) == 1
    assert command.count("--deselect=" + RUNNER.LOCKED_L2_MATRIX_TEST) == 1
    assert "--ignore=tests/numerics/test_gravity_l2_precision.py" not in command
    assert "--sw" in command


def test_retained_matrix_lane_receives_only_nine_unique_junit_reports(tmp_path):
    reports = tuple(tmp_path / f"{index:02d}-report.xml" for index in range(9))
    command = RUNNER.locked_l2_matrix_receipt_command(
        tmp_path / "pipeline-python.exe", tmp_path / "matrix-summary.json", reports)

    assert command[0] == str(tmp_path / "pipeline-python.exe")
    assert command[1] == str(ROOT / "scripts/validate_gravity_l2_matrix.py")
    assert command.count("--junit") == 9
    assert all(str(path) in command for path in reports)
    assert str(tmp_path / "09-replay.xml") not in command
