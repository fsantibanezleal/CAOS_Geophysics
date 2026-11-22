r"""Fail-fast full local test gate with all mutable evidence outside the repository.

Example (PowerShell):
  .\.venv-pipeline\Scripts\python.exe tests\run_validation.py `
    --data-root E:\_Datos\CAOS_Geophysics `
    --output-root E:\_Datos\CAOS_Geophysics\validation

The retained-original custody proofs are intentionally not regenerated. Supply
those exact source receipts when available; this command verifies their presence
before spending time on a full run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RETAINED = {
    "M01_RETAINED_CORRECTION_PACKET": "44eca87a1f5750fede3f7f4530ea550a368538f3b5fdbd073b3713e7d950722a",
    "M01_RETAINED_TRANSFORM_PACKET": "6881c30e13e39de03c7530a2b6fd2e1bb49b1b50d361fdf41dfb7cc44c8dbcb8",
    "GEOPHYSICS_PROFILE_INCOMPLETE_RECEIPT": "5a13e2c51abcd5c4ec90661d237f421e0c3a363b61ed6e5aa7bfc9fe43dccb89",
}
M11_SHA256 = "30cf3f3e06649c98a2ce4810186e413582a428cf45e334a079f9e92621ece21b"
PROFILE_TESTS = (
    "tests/numerics/test_ert.py",
    "tests/numerics/test_traveltime.py",
    "tests/numerics/test_profile_mesh.py",
)
RESOURCE_TEST = "tests/numerics/test_gravity_l2_precision.py::test_certified_delta_real_cap_resource_measurement"
LOCKED_L2_MATRIX_TEST = "tests/numerics/test_gravity_l2_selection.py::test_complete_locked_l2_control_matrix"
LOCKED_L2_EVIDENCE = Path("docs/design/features/m02-survey-l2/evidence/2026-10-31")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def profile_lane_command(profile_python: Path, junit: Path, scratch: Path,
                         keyword: str | None = None) -> list[str]:
    """Run pyGIMLi-backed ERT, travel-time and mesh tests in their pinned env."""
    command = [str(profile_python), "-m", "pytest", *PROFILE_TESTS, "-x", "--tb=short", "-q",
               f"--junitxml={junit}", f"--basetemp={scratch}"]
    if keyword:
        command.extend(["-k", keyword])
    return command


def resource_lane_command(pipeline_python: Path, junit: Path, scratch: Path,
                          keyword: str | None = None) -> list[str]:
    """Run the real-cap RSS acceptance in a fresh process, isolated from suite accumulation."""
    command = [str(pipeline_python), "-m", "pytest", RESOURCE_TEST, "-x", "--tb=short", "-q",
               f"--junitxml={junit}", f"--basetemp={scratch}"]
    if keyword:
        command.extend(["-k", keyword])
    return command


def locked_l2_matrix_junit_paths(root: Path = ROOT) -> tuple[Path, ...]:
    """Return the nine frozen unique-cell reports only when their solver/source hashes still match."""
    evidence = root / LOCKED_L2_EVIDENCE
    source = json.loads((evidence / "source-hashes.json").read_text(encoding="utf-8"))
    if source.get("schema") != "geophysics.m02-locked-source-hashes/v1":
        raise ValueError("M02 locked matrix source manifest schema mismatch")
    for item in source.get("source_files", []):
        path = (root / item["path"]).resolve()
        if not path.is_file() or path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError(f"M02 locked matrix source changed; replay required: {item['path']}")
    index = json.loads((evidence / "junit-sha256.json").read_text(encoding="utf-8"))
    records = {item["path"]: item for item in index}
    for item in index:
        path = (root / item["path"]).resolve()
        if not path.is_file() or path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError(f"M02 locked matrix JUnit receipt changed: {item['path']}")
    # The first nine reports cover the unique 24-cell matrix. The 09 replay is
    # deliberately nonidentical and must never be counted as a duplicate cell.
    expected = tuple(sorted((path for path in evidence.glob("*.xml")
                             if path.name[:2].isdigit() and 0 <= int(path.name[:2]) <= 8),
                            key=lambda path: path.name))
    if len(expected) != 9:
        raise ValueError(f"M02 locked matrix requires nine unique JUnit files, found {len(expected)}")
    for path in expected:
        relative = path.relative_to(root).as_posix()
        item = records.get(relative)
        if item is None or path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError(f"M02 locked matrix JUnit receipt changed: {relative}")
    return expected


def locked_l2_matrix_receipt_command(pipeline_python: Path, output: Path,
                                     junit_paths: tuple[Path, ...]) -> list[str]:
    """Check retained matrix evidence without rerunning its 24 costly inverse cases."""
    command = [str(pipeline_python), str(ROOT / "scripts/validate_gravity_l2_matrix.py")]
    for path in junit_paths:
        command.extend(["--junit", str(path)])
    command.extend(["--output", str(output)])
    return command


def offline_lane_command(pipeline_python: Path, junit: Path, scratch: Path,
                        keyword: str | None = None) -> list[str]:
    """Run ordinary offline tests; isolated profile and RSS cases have their own lanes."""
    command = [str(pipeline_python), "-m", "pytest", "tests", "--ignore=tests/api",
               "--ignore=tests/ops", "--ignore=tests/data/test_formats.py",
               "--ignore=tests/adversarial", "--ignore=tests/numerics/test_waveform_picks.py",
               *(f"--ignore={path}" for path in PROFILE_TESTS), f"--deselect={RESOURCE_TEST}",
               f"--deselect={LOCKED_L2_MATRIX_TEST}",
               "-x", "--sw", "--tb=short", "-q", f"--junitxml={junit}", f"--basetemp={scratch}",
               "--ignore-glob=tests/data/test_waveform_*.py",
               "--ignore=tests/adversarial/test_waveform_user_data_adversarial.py"]
    if keyword:
        command.extend(["-k", keyword])
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", type=Path, default=Path(os.environ["GEOPHYSICS_LOCAL_DATA_ROOT"]) if os.environ.get("GEOPHYSICS_LOCAL_DATA_ROOT") else None)
    parser.add_argument("--output-root", type=Path, help="external directory for pytest scratch and reports; defaults to <data-root>/validation")
    parser.add_argument("-k", "--keyword", help="optional pytest expression")
    parser.add_argument("--m11-database", type=Path, default=Path(os.environ["GEOPHYSICS_M11_TEST_DATABASE"]) if os.environ.get("GEOPHYSICS_M11_TEST_DATABASE") else None, help="exact retained M11 API database outside the repository")
    args = parser.parse_args()
    m11_path = args.m11_database.resolve() if args.m11_database else None
    if m11_path is not None and (not m11_path.is_file() or m11_path.is_relative_to(ROOT)):
        parser.error("--m11-database (or GEOPHYSICS_M11_TEST_DATABASE) must name an existing file outside the repository")
    data_root = args.data_root.resolve() if args.data_root else None
    if data_root is None or not data_root.is_dir() or (data_root / ".git").exists() or data_root.is_relative_to(ROOT):
        parser.error("--data-root (or GEOPHYSICS_LOCAL_DATA_ROOT) must name an existing external directory outside the repository")

    profile_python = ROOT / ".venv-ert" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    m08_python = ROOT / ".venv-m08" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if args.keyword is None and not m08_python.is_file():
        parser.error(f"M08 scientific environment is missing: {m08_python}; run scripts/setup.ps1 -M08 first")
    if args.keyword is None and not profile_python.is_file():
        parser.error(f"pyGIMLi profile environment is missing: {profile_python}; run scripts/setup.ps1 -ERT")

    output_root = (args.output_root or data_root / "validation").resolve()
    if output_root.is_relative_to(ROOT) or any((parent / ".git").exists() for parent in (output_root, *output_root.parents)):
        parser.error("--output-root must stay outside every Git checkout")

    if args.keyword is None:
        missing = []
        for name, expected in RETAINED.items():
            raw = os.environ.get(name)
            path = Path(raw).resolve() if raw else None
            if path is None or not path.is_file():
                missing.append(f"{name}: provide the exact retained original file (SHA-256 {expected})")
            elif digest(path) != expected:
                missing.append(f"{name}: SHA-256 mismatch at {path}")
        if m11_path is None:
            missing.append(f"M11 retained native database unavailable; set GEOPHYSICS_M11_TEST_DATABASE to the exact external file (SHA-256 {M11_SHA256})")
        elif digest(m11_path) != M11_SHA256:
            missing.append(f"M11 retained native database SHA-256 mismatch at {m11_path} (expected {M11_SHA256})")
        if missing:
            print("Full validation not started; original-evidence prerequisites are missing:", file=sys.stderr)
            for item in missing:
                print(f"  - {item}", file=sys.stderr)
            return 2

    pipeline_python = ROOT / ".venv-pipeline" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not pipeline_python.is_file():
        parser.error(f"offline Python environment is missing: {pipeline_python}; run scripts/setup.ps1 -Gpu first")
    api_python = ROOT / ".venv-api" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not api_python.is_file():
        parser.error(f"API test environment is missing: {api_python}; run scripts/setup.ps1 -Api first")
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_root = output_root / run_id
    run_root.mkdir(parents=True, exist_ok=False)
    scratch = run_root / "pytest-basetemp"
    scratch.mkdir()
    # API private-storage fixtures use a short external root: the application
    # enforces Windows MAX_PATH and pytest's nested node IDs can exceed it.
    api_scratch = data_root / "_Temp" / f"gph-{run_id[-10:]}"
    api_scratch.mkdir(parents=True)
    junit = run_root / "numerical.junit.xml"
    env = os.environ.copy()
    env["GEOPHYSICS_LOCAL_DATA_ROOT"] = str(data_root)
    env["GEOPHYSICS_SCIENCE_TEST_PYTHON"] = str(pipeline_python)
    env["GEOPHYSICS_PROFILE_TEST_PYTHON"] = str(profile_python)
    env["M08_TEST_SCIENCE_PYTHON"] = str(m08_python)
    env["CAOS_TEMP_ROOT"] = str(api_scratch.parent)
    if m11_path is not None:
        env["GEOPHYSICS_M11_TEST_DATABASE"] = str(m11_path)
    env["GEOPHYSICS_TEST_SCRATCH"] = str(api_scratch)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    # The native M02/M04 workspace and RSS receipts are qualified only with
    # these library thread pools capped before Python imports NumPy/SciPy.
    # Set them in the child environment so direct shell state cannot silently
    # change solver workspaces or invalidate a bounded-resource run.
    thread_policy = {
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    }
    env.update(thread_policy)
    command = offline_lane_command(pipeline_python, junit, scratch, args.keyword)
    api_junit = run_root / "api.junit.xml"
    api_pytest_scratch = data_root / "_Temp" / f"pytest-{run_id[-10:]}"
    api_pytest_scratch.mkdir(parents=True)
    api_command = [str(api_python), "-m", "pytest", "tests/api", "tests/ops",
                   "tests/data/test_formats.py", "tests/adversarial/test_client_first_access_adversarial.py",
                   "tests/adversarial/test_protected_waveform_adversarial.py", "-x", "--tb=short", "-q",
                   "--ignore=tests/ops/test_backup.py", "--ignore=tests/ops/test_backup_mt.py",
                   "--ignore=tests/ops/test_local_validation.py",
                   f"--junitxml={api_junit}", f"--basetemp={api_pytest_scratch}"]
    if args.keyword:
        api_command.extend(["-k", args.keyword])
    profile_junit = run_root / "pygimli-profile.junit.xml"
    profile_scratch = run_root / "pytest-profile-basetemp"
    profile_scratch.mkdir()
    profile_command = profile_lane_command(profile_python, profile_junit, profile_scratch, args.keyword)
    matrix_summary = run_root / "m02-locked-matrix-summary.json"
    matrix_paths = locked_l2_matrix_junit_paths(ROOT)
    matrix_command = locked_l2_matrix_receipt_command(pipeline_python, matrix_summary, matrix_paths)
    resource_junit = run_root / "real-cap-resource.junit.xml"
    resource_scratch = run_root / "pytest-resource-basetemp"
    resource_scratch.mkdir()
    resource_command = resource_lane_command(pipeline_python, resource_junit, resource_scratch, args.keyword)
    started = dt.datetime.now(dt.timezone.utc)

    def run_lane(label: str, lane_command: list[str], lane_env: dict[str, str] = env) -> subprocess.CompletedProcess[str] | None:
        print(f"Running {label} suite in {lane_command[0]}:", flush=True)
        completed = subprocess.run(lane_command, cwd=ROOT, env=lane_env, check=False)
        # Let pytest determine whether a filtered lane contains a match in a
        # single collection pass; a separate --collect-only probe doubled the
        # expensive plugin/import discovery for each validation run.
        if args.keyword and completed.returncode == 5:
            print(f"No tests selected for {label}; lane skipped.", flush=True)
            return None
        return completed

    matrix_result = run_lane("retained M02 locked L2 receipt", matrix_command)
    resource_result = run_lane("isolated real-cap RSS resource", resource_command)
    result = run_lane("offline scientific", command)
    profile_result = run_lane("pyGIMLi ERT/travel-time/profile mesh", profile_command)
    api_env = env.copy()
    api_env["CAOS_TEST_PYTHON"] = str(api_python)
    api_env["CAOS_TEST_BASETEMP"] = str(api_scratch.parent / f"{api_scratch.name}-nested")
    api_result = run_lane("API", api_command, api_env)
    pipeline_code = result.returncode if result is not None else 0
    resource_code = resource_result.returncode if resource_result is not None else 0
    profile_code = profile_result.returncode if profile_result is not None else 0
    api_code = api_result.returncode if api_result is not None else 0
    matrix_code = matrix_result.returncode if matrix_result is not None else 0
    m08_result = None
    waveform_command = None
    if pipeline_code == 0 and profile_code == 0 and resource_code == 0 and api_code == 0 and m08_python.is_file():
        waveform_tests = sorted((ROOT / "tests" / "data").glob("test_waveform_*.py"))
        waveform_tests.extend((ROOT / "tests" / "numerics" / "test_waveform_picks.py",
                              ROOT / "tests" / "adversarial" / "test_waveform_user_data_adversarial.py"))
        waveform_scratch = api_scratch.parent / f"{api_scratch.name}-m08"
        waveform_scratch.mkdir()
        waveform_env = env.copy()
        waveform_env["CAOS_TEST_PYTHON"] = str(m08_python)
        waveform_env["CAOS_TEST_BASETEMP"] = str(api_scratch.parent / f"{api_scratch.name}-m08-nested")
        waveform_junit = run_root / "m08-waveform.junit.xml"
        waveform_command = [str(m08_python), "-m", "pytest", *(str(path) for path in waveform_tests),
                            "-x", "--tb=short", "-q", f"--junitxml={waveform_junit}",
                            f"--basetemp={waveform_scratch}"]
        if args.keyword:
            waveform_command.extend(["-k", args.keyword])
        m08_result = run_lane("M08 waveform", waveform_command, waveform_env)
    elif pipeline_code == 0 and profile_code == 0 and resource_code == 0 and api_code == 0 and args.keyword is None:
        parser.error(f"M08 scientific environment is missing: {m08_python}; run scripts/setup.ps1 -M08 first")
    try:
        import torch
        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        cuda = torch.version.cuda
        torch_version = torch.__version__
    except Exception:
        gpu = cuda = torch_version = None
    overall_code = matrix_code or pipeline_code or profile_code or resource_code or api_code or (m08_result.returncode if m08_result else 0)
    record = {
        "started_utc": started.isoformat(),
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "exit_code": overall_code,
        "pipeline_exit_code": pipeline_code,
        "profile_exit_code": profile_code,
        "resource_exit_code": resource_code,
        "api_exit_code": api_code,
        "locked_l2_receipt_exit_code": matrix_code,
        "m08_waveform_exit_code": m08_result.returncode if m08_result else None,
        "python": str(pipeline_python),
        "data_root": str(data_root),
        "m11_database": str(m11_path) if m11_path is not None else None,
        "m11_database_sha256": digest(m11_path) if m11_path is not None else None,
        "pytest_command": command,
        "profile_pytest_command": profile_command,
        "resource_pytest_command": resource_command,
        "api_pytest_command": api_command,
        "locked_l2_receipt_command": matrix_command,
        "m08_pytest_command": waveform_command,
        "torch": torch_version,
        "cuda": cuda,
        "gpu": gpu,
        "native_thread_policy": thread_policy,
        "junit": str(junit),
        "resource_junit": str(resource_junit),
        "locked_l2_summary": str(matrix_summary),
    }
    (run_root / "environment.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Validation evidence: {run_root}")
    return overall_code


if __name__ == "__main__":
    raise SystemExit(main())
