"""Actual local request bytes, geometry-only exit truth and no overwrite."""

import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from magnetic_survey_support import encode, request

SCRIPT = Path(__file__).parents[2]/"data-pipeline"/"magnetic_survey.py"


def run(*args):
    return subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True, env=os.environ.copy(), timeout=20)


def test_actual_geometry_bytes_and_exports(tmp_path):
    original = tmp_path/"request.json"
    target = tmp_path/"geometry.json"
    raw = encode(request())
    original.write_bytes(raw)
    result = run("validate", "--request", original, "--export", target)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "magnetic-geometry-plan-1"
    assert not any(payload["claims"].values())
    assert "optimizer_unbound" in payload["eligibility"]["reasons"]
    previous = target.read_bytes()
    retry = run("validate", "--request", original, "--export", target)
    assert retry.returncode == 5
    assert target.read_bytes() == previous
    assert original.read_bytes() == raw
    # Actual parameter change produces a new configuration hash, not replay.
    doc = request()
    doc["inducing_field"]["D_deg"] = -72.0
    original.write_bytes(encode(doc))
    changed = run("validate", "--request", original, "--export", tmp_path/"changed.json")
    assert changed.returncode == 0
    assert json.loads(changed.stdout)["identity"]["configuration_sha256"] != payload["identity"]["configuration_sha256"]
    assert json.loads(changed.stdout)["identity"]["seal_sha256"] == payload["identity"]["seal_sha256"]


@pytest.mark.parametrize("attack", ["calibrate", "flag", "invalid_bytes", "missing_file"])
def test_cli_failure_is_not_inverse_success(tmp_path, attack):
    original = tmp_path/"request.json"
    target = tmp_path/"geometry.json"
    original.write_bytes(encode(request()) if attack != "invalid_bytes" else b"{}")
    args = ["calibrate" if attack == "calibrate" else "validate", "--request", original, "--export", target]
    if attack == "flag":
        args.extend(["--assume-approved", "true"])
    if attack == "missing_file":
        original.unlink()
    result = run(*args)
    assert result.returncode == (5 if attack == "missing_file" else 2)
    assert not target.exists()
