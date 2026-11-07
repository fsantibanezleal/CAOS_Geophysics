"""Run an existing focused pytest case as an adversarial feature gate.

The production test remains the source of behavior and assertions. Running it
through pytest preserves its normal fixture lifecycle while giving the feature
contract a clearly named adversarial entry point.
"""

from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run_existing(*nodeids: str) -> None:
    if not nodeids:
        raise AssertionError("an adversarial wrapper must name at least one existing pytest case")
    local_venv = ROOT / ".venv-pipeline" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    interpreter = os.environ.get("CAOS_TEST_PYTHON") or str(local_venv if local_venv.is_file() else sys.executable)
    command = [interpreter, "-m", "pytest", "-q"]
    basetemp = os.environ.get("CAOS_TEST_BASETEMP")
    if basetemp:
        command.extend(("--basetemp", basetemp))
    completed = subprocess.run(
        [*command, *nodeids],
        cwd=ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"wrapped existing pytest cases failed with exit code {completed.returncode}")
