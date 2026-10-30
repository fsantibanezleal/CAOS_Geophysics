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


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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
    raw_profiles = (data_root / "data/downloads/pygimli/slagdump.ohm", data_root / "data/downloads/pygimli/koenigsee.sgt")
    if args.keyword is None and any(path.is_file() for path in raw_profiles) and not profile_python.is_file():
        parser.error(f"pyGIMLi profile environment is missing: {profile_python}; install data-pipeline/requirements-ert.txt")

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
    command = [str(pipeline_python), "-m", "pytest", "tests", "-x", "--tb=short", "-q",
               f"--junitxml={junit}", f"--basetemp={scratch}",
               "--ignore-glob=tests/data/test_waveform_*.py",
               "--ignore=tests/adversarial/test_waveform_user_data_adversarial.py"]
    if args.keyword:
        command.extend(["-k", args.keyword])
    started = dt.datetime.now(dt.timezone.utc)
    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
    m08_result = None
    if result.returncode == 0 and args.keyword is None:
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
        print("Running isolated M08 data-layer suite with the pinned waveform engine:", flush=True)
        m08_result = subprocess.run(waveform_command, cwd=ROOT, env=waveform_env, check=False)
    try:
        import torch
        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        cuda = torch.version.cuda
        torch_version = torch.__version__
    except Exception:
        gpu = cuda = torch_version = None
    record = {
        "started_utc": started.isoformat(),
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "exit_code": result.returncode,
        "m08_waveform_exit_code": m08_result.returncode if m08_result else None,
        "python": str(pipeline_python),
        "data_root": str(data_root),
        "m11_database": str(m11_path) if m11_path is not None else None,
        "m11_database_sha256": digest(m11_path) if m11_path is not None else None,
        "pytest_command": command,
        "torch": torch_version,
        "cuda": cuda,
        "gpu": gpu,
        "native_thread_policy": thread_policy,
        "junit": str(junit),
    }
    (run_root / "environment.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Validation evidence: {run_root}")
    return result.returncode if result.returncode else (m08_result.returncode if m08_result else 0)


if __name__ == "__main__":
    raise SystemExit(main())
