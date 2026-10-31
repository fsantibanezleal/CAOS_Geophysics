"""Ordinary CLI/path controls; an absent native supervisor never runs science."""

import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from contextlib import redirect_stdout

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(ROOT / "tests/data"))
from test_waveform_input import source, inventory, request
from waveform_input import WaveformInputError


def files():
    return importlib.import_module("waveform_m08_files")


def fixtures(tmp_path):
    for name, data in (
        ("counts.ms", source()),
        ("response.xml", inventory()),
        ("request.json", json.dumps(request()).encode()),
    ):
        (tmp_path / name).write_bytes(data)
    return [
        "--mseed",
        str(tmp_path / "counts.ms"),
        "--stationxml",
        str(tmp_path / "response.xml"),
        "--request",
        str(tmp_path / "request.json"),
        "--out",
        str(tmp_path / "new"),
        "--python",
        sys.executable,
    ]


def test_regular_read_bounds_and_unchanged_identity(tmp_path):
    module = files()
    path = tmp_path / "raw"
    path.write_bytes(b"abc")
    with module.open_input(path, 3) as opened:
        assert opened.read_bytes() == b"abc"
        assert opened.sha256 == hashlib.sha256(b"abc").hexdigest()
        with pytest.raises(WaveformInputError):
            opened.read_bytes()
    with pytest.raises(WaveformInputError):
        module.open_input(path, 2)
    assert path.read_bytes() == b"abc"


@pytest.mark.parametrize("name", ["https://SECRET/", "../relative", "file*", "file?", "a/../b"])
def test_invalid_literal_paths_fail_without_creation(name):
    with pytest.raises(WaveformInputError):
        files().validate_path(name)


@pytest.mark.parametrize("role", ["mseed", "stationxml", "request", "out", "admission", "evaluate-with"])
def test_cli_rejects_repository_working_paths_before_reads_or_native_calls(tmp_path, monkeypatch, role):
    cli = importlib.import_module("process_waveform_m08")
    args = fixtures(tmp_path)
    forbidden = str(ROOT / "data/derived/waveform/new-working-file")
    if role in ("admission", "evaluate-with"):
        args += ["--" + role, forbidden]
    else:
        args[args.index("--" + role) + 1] = forbidden
    monkeypatch.setattr(files(), "open_input", lambda *_args: pytest.fail("Rejected path must never be read"))
    output = io.StringIO()
    with redirect_stdout(output):
        assert cli.main(args) == 3
    assert json.loads(output.getvalue()) == {"status": "rejected", "reason": "path_contract"}
    assert not (tmp_path / "new").exists()


def test_only_new_output_beneath_exact_explicit_parent(tmp_path):
    module = files()
    with module.create_output(tmp_path / "new", trusted_parent=tmp_path) as directory:
        assert directory.names(55) == []
        with directory.create_regular("receipt.json") as f:
            f.write(b"{}")
            directory.flush_file(f)
        assert directory.names(55) == ["receipt.json"]
        with pytest.raises(WaveformInputError):
            directory.create_regular("receipt.json")
    with pytest.raises(WaveformInputError):
        module.create_output(tmp_path / "new", trusted_parent=tmp_path)
    with pytest.raises(WaveformInputError):
        module.create_output(tmp_path / "other", trusted_parent=tmp_path.parent)
    assert (tmp_path / "new/receipt.json").read_bytes() == b"{}"


def test_hardlinked_source_refused_and_no_original_changed(tmp_path):
    module = files()
    (tmp_path / "raw").write_bytes(b"abc")
    os.link(tmp_path / "raw", tmp_path / "linked")
    with pytest.raises(WaveformInputError):
        module.open_input(tmp_path / "linked", 3)
    assert (tmp_path / "raw").read_bytes() == b"abc"


def test_actual_cli_unavailable_no_native_fallback_or_output(tmp_path):
    args = fixtures(tmp_path)
    command = [sys.executable, "-B", str(ROOT / "scripts/process_waveform_m08.py"), *args]
    environment = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "SystemDrive": os.environ.get("SystemDrive", ""),
        "USERPROFILE": str(tmp_path),
        "APPDATA": str(tmp_path / "appdata"),
        "LOCALAPPDATA": str(tmp_path / "localappdata"),
        "TEMP": str(tmp_path),
        "TMP": str(tmp_path),
    }
    (tmp_path / "appdata").mkdir()
    (tmp_path / "localappdata").mkdir()
    done = subprocess.run(command, capture_output=True, check=False, timeout=10, env=environment, cwd=tmp_path)
    assert done.returncode == 4
    assert done.stderr == b""
    assert json.loads(done.stdout) == {"status": "engine_unavailable", "reason": "supervisor_unavailable"}
    assert not (tmp_path / "new").exists()


def test_reference_is_unopened_when_supervisor_unavailable(tmp_path, monkeypatch):
    module = importlib.import_module("process_waveform_m08")
    args = fixtures(tmp_path)
    reference = tmp_path / "reference.json"
    reference.write_bytes(b"SECRET reference")
    calls = []
    import waveform_m08_files

    monkeypatch.setattr(waveform_m08_files, "open_input", lambda *a, **k: calls.append(a))
    output = io.StringIO()
    with redirect_stdout(output):
        exit_code = module.main(args + ["--evaluate-with", str(reference)])
    assert exit_code == 4 and calls == []
    assert "SECRET" not in output.getvalue()


def test_safe_unknown_flags_and_existing_destination(tmp_path):
    module = importlib.import_module("process_waveform_m08")
    args = fixtures(tmp_path)
    for argv in (args + ["--unsafe-direct", "SECRET"], args + ["--mseed", "https://SECRET/"]):
        output = io.StringIO()
        with redirect_stdout(output):
            assert module.main(argv) == 3
        assert "SECRET" not in output.getvalue()
    (tmp_path / "new").mkdir()
    output = io.StringIO()
    with redirect_stdout(output):
        assert module.main(args) == 3
    assert (tmp_path / "new").is_dir()


def test_ordinary_child_same_input_science_and_json_byte_identity():
    child = importlib.import_module("waveform_m08_child")
    raw_request = json.dumps(request()).encode()
    out, sealed = child.calculate_bytes(source(), inventory(), raw_request)
    assert out.metadata["status"] == "computed"
    assert out.metadata["request"]["original_json_sha256"] == hashlib.sha256(raw_request).hexdigest()
    assert out.metadata["request"]["original_json_bytes"] == len(raw_request)
    assert sealed.calculation_sha256 == hashlib.sha256(sealed.metadata_bytes).hexdigest()
    assert out.metadata["acceptance"]["host_admitted"] is False


def test_actual_powershell_wrapper_propagates_unavailable_and_safe_path_error(tmp_path):
    if os.name != "nt":
        pytest.skip("Windows wrapper only; no Linux/native capability claim")
    import shutil

    shell = shutil.which("pwsh")
    if shell is None:
        pytest.skip("PowerShell7 unavailable")
    args = fixtures(tmp_path)[:-2]
    env = dict(os.environ)
    env.update(
        PYTHONDONTWRITEBYTECODE="1",
        TEMP=str(tmp_path),
        TMP=str(tmp_path),
        USERPROFILE=str(tmp_path),
        APPDATA=str(tmp_path),
        LOCALAPPDATA=str(tmp_path),
    )
    base = [shell, "-NoProfile", "-NonInteractive", "-File", str(ROOT / "scripts/process_waveform_m08.ps1")]
    for python, expected, status in ((sys.executable, 4, "engine_unavailable"), ("SECRET-relative", 3, "rejected")):
        done = subprocess.run(
            [*base, "-PythonPath", python, *args], cwd=tmp_path, env=env, capture_output=True, timeout=20, check=False
        )
        assert done.returncode == expected
        assert done.stderr == b""
        assert json.loads(done.stdout)["status"] == status
        assert b"SECRET" not in done.stdout
    assert not (tmp_path / "new").exists()
