"""Adversarial entry points for the protected waveform workflow."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile

from tests.adversarial._existing_pytest_gate import run_existing

ROOT = Path(__file__).resolve().parents[2]
M08_PYTHON = ROOT / ".venv-m08" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def test_adversarial_waveform_service_ownership_and_lifecycle():
    science_python = M08_PYTHON
    if not science_python.is_file():
        raise AssertionError("the pinned .venv-m08 interpreter is required for protected publication")
    previous = os.environ.get("M08_TEST_SCIENCE_PYTHON")
    previous_basetemp = os.environ.get("CAOS_TEST_BASETEMP")
    temp_root = os.environ.get("CAOS_TEMP_ROOT")
    if not temp_root or not Path(temp_root).is_absolute() or not Path(temp_root).is_dir():
        raise AssertionError("set CAOS_TEMP_ROOT to an existing external writable scratch directory")
    os.environ["M08_TEST_SCIENCE_PYTHON"] = str(science_python)
    try:
        with tempfile.TemporaryDirectory(prefix="wa-", dir=temp_root) as scratch:
            os.environ["CAOS_TEST_BASETEMP"] = scratch
            run_existing(
                "tests/api/test_waveform_service.py::test_owned_pair_and_request_index",
                "tests/api/test_waveform_service.py::test_pair_rejections",
                "tests/api/test_waveform_service.py::test_worker_dispatch_and_closed_context",
                "tests/api/test_waveform_service.py::test_publication_and_roundtrip",
                "tests/api/test_waveform_service.py::test_inventory_quota_delete",
                "tests/api/test_waveform_service.py::test_migration_and_unknown_revision",
            )
    finally:
        if previous is None:
            os.environ.pop("M08_TEST_SCIENCE_PYTHON", None)
        else:
            os.environ["M08_TEST_SCIENCE_PYTHON"] = previous
        if previous_basetemp is None:
            os.environ.pop("CAOS_TEST_BASETEMP", None)
        else:
            os.environ["CAOS_TEST_BASETEMP"] = previous_basetemp


def test_adversarial_waveform_client_rejects_contract_and_export_tampering():
    npm = "npm.cmd" if os.name == "nt" else "npm"
    completed = subprocess.run(
        [npm, "run", "test", "--", "--run", "src/test/waveform-project.test.tsx"],
        cwd=ROOT / "frontend",
        check=False,
    )
    if completed.returncode:
        raise AssertionError(f"waveform client contract tests failed: {completed.returncode}")


def test_adversarial_waveform_same_input_and_postseal_export():
    interpreter = M08_PYTHON
    if not interpreter.is_file():
        raise AssertionError("the pinned .venv-m08 interpreter is required for waveform science")
    temp_root = os.environ.get("CAOS_TEMP_ROOT")
    if not temp_root or not Path(temp_root).is_absolute() or not Path(temp_root).is_dir():
        raise AssertionError("set CAOS_TEMP_ROOT to an existing external writable scratch directory")
    with tempfile.TemporaryDirectory(prefix="wa-same-", dir=temp_root) as scratch:
        basetemp = str(Path(scratch) / "pytest")
        child_env = os.environ.copy()
        child_env.update({"TMP": scratch, "TEMP": scratch, "TMPDIR": scratch})
        completed = subprocess.run(
            [str(interpreter), "-m", "pytest", "-q",
             "tests/data/test_waveform_full_workflow.py::test_actual_full_science_same_input_and_postseal_export",
             f"--basetemp={basetemp}"],
            cwd=ROOT,
            env=child_env,
            check=False,
        )
    if completed.returncode:
        raise AssertionError(f"same-input waveform workflow tests failed: {completed.returncode}")
