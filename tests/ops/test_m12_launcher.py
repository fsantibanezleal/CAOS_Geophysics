"""Launcher boundaries only; no new training, checkpoint or scientific verdict."""

import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_m12_velocity.py"
spec = importlib.util.spec_from_file_location("m12_launcher", SCRIPT)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.mark.parametrize("target", ["relative-output", str(ROOT / "data" / "new-output"),
                                   str(ROOT / "models" / "new-output"), str(Path(ROOT.anchor))])
def test_actual_cli_refuses_before_science(target):
    scientific = ROOT / "data-pipeline" / "velocity_validation.py"
    before = hashlib.sha256(scientific.read_bytes()).hexdigest()
    child = subprocess.run([sys.executable, "-B", str(SCRIPT), "--output", target, "--verify"],
                           capture_output=True, text=True, timeout=20)
    assert child.returncode == 2 and "REFUSED:" in child.stderr
    assert hashlib.sha256(scientific.read_bytes()).hexdigest() == before
    if target.startswith(str(ROOT)):
        assert not Path(target).exists()


def test_missing_output_cannot_default_to_repository():
    child = subprocess.run([sys.executable, "-B", str(SCRIPT)], capture_output=True, text=True, timeout=20)
    assert child.returncode == 2 and "--output" in child.stderr


@pytest.mark.parametrize("mode", ["train", "verify", "fixture"])
def test_exact_protocol_forwarding(tmp_path, monkeypatch, mode):
    calls = []
    def capture(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=7)
    monkeypatch.setattr(launcher.subprocess, "run", capture)
    output = tmp_path / "new-run"
    args = ["--output", str(output), "--device", "cuda", "--epochs", "40"]
    if mode != "train":
        args.append("--" + mode)
    assert launcher.main(args) == 7
    command, options = calls[0]
    assert command[:5] == [sys.executable, "-B", str(ROOT / "data-pipeline" / "velocity_validation.py"),
                           "--output", str(output)]
    assert command[5:] == (["--verify"] if mode == "verify" else
                          ["--device", "cuda", "--epochs", "40"] + (["--fixture"] if mode == "fixture" else []))
    assert options == {"cwd": ROOT, "check": False}
    assert not output.exists()


@pytest.mark.parametrize("epochs", ["0", "10001"])
def test_invalid_epoch_count_refused(tmp_path, epochs):
    assert launcher.main(["--output", str(tmp_path / "new-run"), "--epochs", epochs]) == 2


@pytest.mark.skipif(os.name != "nt", reason="Actual Windows launcher control")
def test_powershell_requires_explicit_output():
    image = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    child = subprocess.run([str(image), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                            "-File", str(ROOT / "scripts" / "run_m12_velocity.ps1")],
                           capture_output=True, text=True, timeout=20)
    assert child.returncode != 0 and "explicit absolute external" in child.stderr


@pytest.mark.skipif(os.name != "nt", reason="Actual configured Git Bash launcher control")
def test_bash_requires_explicit_output():
    image = Path(os.environ["ProgramFiles"]) / "Git" / "bin" / "bash.exe"
    env = {**os.environ, "M12_PYTHON": Path(sys.executable).as_posix()}
    child = subprocess.run([str(image), (ROOT / "scripts" / "run_m12_velocity.sh").as_posix(), "cpu"],
                           env=env, capture_output=True, text=True, timeout=20)
    assert child.returncode == 2 and "--output" in child.stderr
