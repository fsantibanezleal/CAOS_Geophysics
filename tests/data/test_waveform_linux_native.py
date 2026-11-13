"""Opt-in ACTUAL Linux system-manager waveform processing, never a launch double."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(ROOT / "tests/fixtures/waveform_m08"))


@pytest.mark.skipif(sys.platform != "linux" or os.environ.get("M08_RUN_LINUX_NATIVE") != "1",
                    reason="Actual Linux fixed-lane qualification requires explicit opt-in")
@pytest.mark.parametrize("case", ["nominal1", "nominal3", "upper3"])
def test_real_linux_fixed_lane_full_processing(tmp_path, case):
    from full_workflow import make_case
    from waveform_m08_files import external_work_path, open_output
    from waveform_m08_export import verify_export
    from waveform_m08_linux import run_cli
    from waveform_m08_child import calculate_bytes

    external_work_path(tmp_path)
    fixture = make_case(case)
    for name, key in (("input.ms", "mseed"), ("station.xml", "stationxml"), ("request.json", "request"), ("reference.json", "reference")):
        (tmp_path / name).write_bytes(fixture[key])
    interpreter = str(Path(sys._base_executable).resolve())
    site = str(Path(sys.prefix) / f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
    # Windows-owned linked worktrees have a Windows .git target not resolvable
    # by WSL git. The caller may supply its actual host-measured revision; exact
    # live source hashes are independently pinned by qualification in either case.
    revision = os.environ.get("M08_TEST_SOURCE_REVISION") or subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    qualified = subprocess.run([interpreter, "-I", "-B", str(ROOT / "scripts/qualify_waveform_m08_linux.py"),
        "--data-root", str(tmp_path), "--python", interpreter, "--site-packages", site,
        "--mseed", str(tmp_path / "input.ms"), "--stationxml", str(tmp_path / "station.xml"),
        "--request", str(tmp_path / "request.json"), "--source-revision", revision, "--uid", "65534", "--gid", "65534"],
        capture_output=True, timeout=150)
    assert qualified.returncode == 0, qualified.stderr.decode(errors="replace")
    outcome = run_cli({"mseed": tmp_path / "input.ms", "stationxml": tmp_path / "station.xml",
                       "request": tmp_path / "request.json", "python": Path(interpreter),
                       "out": tmp_path / ".job-staging/export"}, tmp_path / "reference.json",
                      tmp_path / ".waveform-context/admission.json")
    assert outcome["status"] == "computed", outcome
    assert outcome["reason"] == "measured" and outcome["runtime_authorized"] is False
    native = tmp_path / (".job-staging/export.a4-" + outcome["run_id"])
    receipt = json.loads((native / "eligibility.json").read_bytes())
    release = json.loads((native / "release.json").read_bytes())
    assert receipt["cpu_ns"] < receipt["stop_ns"] == 57000000000
    assert receipt["memory_kind"] == "linux_cgroup_charge" and receipt["active_processes"] == 0
    assert receipt["max_sample_gap_ns"] <= 100000000 and release["scope_removed"] is True
    with open_output(tmp_path / ".job-staging/export") as directory:
        reopened = verify_export(directory)
        expected, sealed = calculate_bytes(fixture["mseed"], fixture["stationxml"], fixture["request"])
        assert reopened.calculation_sha256 == sealed.calculation_sha256
        assert json.loads(reopened.metadata_bytes)["array_descriptors"] == expected.metadata["array_descriptors"]
        assert "evaluation.json" in directory.names(55)
