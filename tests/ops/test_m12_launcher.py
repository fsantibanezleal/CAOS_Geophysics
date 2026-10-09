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
@pytest.mark.parametrize("protocol", ["historical-v1", "physics-v2"])
def test_actual_cli_refuses_before_science(target, protocol):
    scientific = ROOT / "data-pipeline" / "velocity_validation.py"
    before = hashlib.sha256(scientific.read_bytes()).hexdigest()
    child = subprocess.run([sys.executable, "-B", str(SCRIPT), "--output", target,
                            "--protocol", protocol, "--verify"],
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


@pytest.mark.parametrize("mode", ["train", "verify", "fixture"])
def test_exact_physics_protocol_forwarding(tmp_path, monkeypatch, mode):
    calls = []
    def capture(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=7)
    monkeypatch.setattr(launcher.subprocess, "run", capture)
    output = tmp_path / "new-physics-run"
    args = ["--output", str(output), "--protocol", "physics-v2", "--device", "cuda"]
    if mode != "train":
        args.append("--"+mode)
    assert launcher.main(args) == 7
    command, options = calls[0]
    assert command[:5] == [sys.executable, "-B", str(ROOT / "data-pipeline" / "velocity_physics_refinement.py"),
                           "--output", str(output)]
    assert command[5:] == (["--verify"] if mode == "verify" else
                          ["--device", "cuda"]+(["--fixture"] if mode == "fixture" else []))
    assert options == {"cwd": ROOT, "check": False}
    assert not output.exists()


@pytest.mark.parametrize("mode", ["train", "verify"])
def test_physics_epoch_change_is_refused_before_science(tmp_path, monkeypatch, mode):
    def forbidden(*_, **__):
        pytest.fail("Changed frozen protocol must not launch science")
    monkeypatch.setattr(launcher.subprocess, "run", forbidden)
    args = ["--output", str(tmp_path / "new-run"), "--protocol", "physics-v2", "--epochs", "41"]
    if mode == "verify":
        args.append("--verify")
    assert launcher.main(args) == 2


def test_physics_documentation_uses_external_launch_and_keeps_negative_verdict():
    guide = (ROOT / "models/experimental/m12-physics-cuda-20261004/README.md").read_text(encoding="utf-8")
    assert "--protocol physics-v2" in guide and "M12_OUTPUT" in guide
    assert "--output data/" not in guide and "--output models/" not in guide
    assert "ratio2.1875" in guide and "ratio5.4173" in guide


@pytest.mark.skipif(os.name != "nt", reason="Actual Windows launcher control")
@pytest.mark.parametrize("protocol", ["historical-v1", "physics-v2"])
def test_powershell_requires_explicit_output(protocol):
    image = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    child = subprocess.run([str(image), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                            "-File", str(ROOT / "scripts" / "run_m12_velocity.ps1"), "-Protocol", protocol],
                           capture_output=True, text=True, timeout=20)
    assert child.returncode != 0 and "explicit absolute external" in child.stderr


@pytest.mark.skipif(os.name != "nt", reason="Actual configured Git Bash launcher control")
@pytest.mark.parametrize("protocol", ["historical-v1", "physics-v2"])
def test_bash_requires_explicit_output(protocol):
    image = Path(os.environ["ProgramFiles"]) / "Git" / "bin" / "bash.exe"
    env = {**os.environ, "M12_PYTHON": Path(sys.executable).as_posix(), "M12_PROTOCOL": protocol}
    child = subprocess.run([str(image), (ROOT / "scripts" / "run_m12_velocity.sh").as_posix(), "cpu"],
                           env=env, capture_output=True, text=True, timeout=20)
    assert child.returncode == 2 and "--output" in child.stderr


@pytest.mark.skipif(os.name != "nt", reason="Actual configured Git Bash protocol control")
def test_bash_unknown_protocol_is_not_ignored(tmp_path):
    image = Path(os.environ["ProgramFiles"]) / "Git" / "bin" / "bash.exe"
    env = {**os.environ, "M12_PYTHON": Path(sys.executable).as_posix(), "M12_PROTOCOL": "unknown-protocol"}
    child = subprocess.run([str(image), (ROOT / "scripts" / "run_m12_velocity.sh").as_posix(), "cpu",
                            "--output", (tmp_path / "not-created").as_posix()],
                           env=env, capture_output=True, text=True, timeout=20)
    assert child.returncode == 2 and "invalid choice" in child.stderr and "unknown-protocol" in child.stderr
    assert not (tmp_path / "not-created").exists()
