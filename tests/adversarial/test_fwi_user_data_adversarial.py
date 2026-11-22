"""Adversarial gates for supplied acoustic data and local-only browser replay."""

import os
from pathlib import Path
import subprocess
import sys

from tests.adversarial._existing_pytest_gate import run_existing


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def test_adversarial_fu_01_rejects_invalid_source():
    run_existing("tests/data/test_fwi_user_data.py::test_admission_before_engine")


def test_adversarial_fu_02_uses_supplied_gpu_inputs(monkeypatch):
    monkeypatch.setenv("CAOS_TEST_PYTHON", sys.executable)
    monkeypatch.setenv("GEOPHYSICS_FWI_GPU_TEST", "1")
    run_existing("tests/data/test_fwi_user_data.py::test_actual_gpu_input_and_parameter_effect")


def test_adversarial_fu_03_retains_full_budget_lineage(monkeypatch):
    monkeypatch.setenv("CAOS_TEST_PYTHON", sys.executable)
    monkeypatch.setenv("GEOPHYSICS_FWI_FULL_GPU_TEST", "1")
    monkeypatch.setenv("OMP_NUM_THREADS", "2")
    monkeypatch.setenv("MKL_NUM_THREADS", "2")
    run_existing(
        "tests/data/test_fwi_user_data.py::test_lineage_and_no_truth",
        "tests/data/test_fwi_user_data.py::test_full_budget_supplied_gpu_replay",
    )


def test_adversarial_fu_04_rejects_tampered_generations():
    run_existing("tests/data/test_fwi_user_data.py::test_export_roundtrip_and_tampering")


def test_adversarial_fu_05_cli_fails_closed():
    run_existing(
        "tests/data/test_fwi_user_data.py::test_cli_and_no_overwrite",
        "tests/data/test_fwi_user_data.py::test_prepare_original_cli_preserves_and_rejects_before_output",
    )


def test_adversarial_fu_06_browser_rejects_unverified_generation():
    required = ("GEOPHYSICS_FWI_GENERATION", "GEOPHYSICS_FWI_EVIDENCE")
    for name in required:
        value = os.environ.get(name)
        if not value or not Path(value).is_dir():
            raise AssertionError(f"{name} must point to retained external test data")
    build = Path(os.environ.get("GEOPHYSICS_FWI_BUILD", FRONTEND / "dist"))
    if not build.is_dir():
        raise AssertionError("GEOPHYSICS_FWI_BUILD must name a completed frontend build")

    env = os.environ.copy()
    env["GEOPHYSICS_FWI_BUILD"] = str(build.resolve())
    env["GEOPHYSICS_FWI_QA_OUTPUT"] = str(
        Path(env["GEOPHYSICS_FWI_EVIDENCE"]) / "playwright-output"
    )
    vitest = FRONTEND / "node_modules" / "vitest" / "vitest.mjs"
    playwright = FRONTEND / "node_modules" / "@playwright" / "test" / "cli.js"
    subprocess.run(
        ["node", str(vitest), "run", "src/test/fwi-local-contracts.test.ts"],
        cwd=FRONTEND, env=env, check=True, timeout=180,
    )
    subprocess.run(
        ["node", str(playwright), "test", "-c", "playwright.fwi.config.ts",
         "--grep", "actual local CUDA generation"],
        cwd=FRONTEND, env=env, check=True, timeout=900,
    )
