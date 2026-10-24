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
M11_PATH = Path("E:/_Temp/m11cu5/test_actual_full_native_public0/case-0/private/api.sqlite3")
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
    args = parser.parse_args()
    data_root = args.data_root.resolve() if args.data_root else None
    if data_root is None or not data_root.is_dir() or (data_root / ".git").exists() or data_root.is_relative_to(ROOT):
        parser.error("--data-root (or GEOPHYSICS_LOCAL_DATA_ROOT) must name an existing external directory outside the repository")

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
        if not M11_PATH.is_file() or digest(M11_PATH) != M11_SHA256:
            missing.append(f"M11 retained native database unavailable or hash-mismatched: {M11_PATH} (SHA-256 {M11_SHA256})")
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
    junit = run_root / "numerical.junit.xml"
    env = os.environ.copy()
    env["GEOPHYSICS_LOCAL_DATA_ROOT"] = str(data_root)
    env["GEOPHYSICS_SCIENCE_TEST_PYTHON"] = str(pipeline_python)
    env["GEOPHYSICS_PROFILE_TEST_PYTHON"] = str(pipeline_python)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [str(pipeline_python), "-m", "pytest", "tests", "-x", "--tb=short", "-q",
               f"--junitxml={junit}", f"--basetemp={scratch}"]
    if args.keyword:
        command.extend(["-k", args.keyword])
    started = dt.datetime.now(dt.timezone.utc)
    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
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
        "python": str(pipeline_python),
        "data_root": str(data_root),
        "pytest_command": command,
        "torch": torch_version,
        "cuda": cuda,
        "gpu": gpu,
        "junit": str(junit),
    }
    (run_root / "environment.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Validation evidence: {run_root}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
