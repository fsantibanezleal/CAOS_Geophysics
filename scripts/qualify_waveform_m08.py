"""Record a Windows local context; never grant scientific or host acceptance.

An explicit external root and an independently compiled/reviewed SDK layout
probe are required. This utility measures that executable and the loaded
science image inventory. Actual contained runs remain separate validation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "data-pipeline"))

from app.config import external_storage_path
from waveform_m08_windows import Native, binary_sha, canonical, code_paths, parse_abi, prepare_engine, environment as native_environment
from waveform_m08_files import open_output, open_input


def write_new(path, raw):
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def qualify(root, executable, expected_probe_sha, review, revision):
    if os.name != "nt":
        raise ValueError("This qualifier measures Windows only; no Linux fallback")
    import re
    if re.fullmatch("[a-f0-9]{40}", revision) is None:
        raise ValueError("Exact selected source revision required")
    root = external_storage_path(root, "qualification data root")
    executable = external_storage_path(executable, "SDK probe executable")
    review = external_storage_path(review, "review evidence")
    root.mkdir(parents=True, exist_ok=True)
    native = Native()
    baseline_images = set(native.loaded_paths())
    images = [p for p in baseline_images if p.lower().endswith(".exe")]
    if len(images) != 1:
        raise ValueError("Exactly one measured Python process image required")
    python_image = images[0]
    site_packages = Path(sys.prefix) / "Lib" / "site-packages"
    with open_output(site_packages):
        pass
    # The API observer starts with a closed environment; inventory that exact
    # bootstrap separately. DLLs loaded transiently there can disappear after
    # engine preparation and must not be lost from the measured union.
    bootstrap_env = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "SYSTEMDRIVE"}}
    bootstrap_env.update(TMP=str(root), TEMP=str(root), TMPDIR=str(root), PYTHONDONTWRITEBYTECODE="1")
    bootstrap = subprocess.run([
        sys.executable, "-I", "-B", "-c",
        "import sys,json;sys.path.insert(0,sys.argv[1]);import waveform_m08_windows as w;"
        "n=w.Native();print(json.dumps(n.loaded_paths()));n.cleanup()", str(ROOT / "scripts"),
    ], cwd=ROOT, env=bootstrap_env, stdin=subprocess.DEVNULL, capture_output=True, timeout=15, check=True)
    if bootstrap.stderr or len(bootstrap.stdout) > 65536:
        raise ValueError("Closed observer bootstrap inventory failed")
    initial = json.loads(bootstrap.stdout)
    if not isinstance(initial, list) or not 1 <= len(initial) <= 256 or any(not isinstance(p, str) for p in initial):
        raise ValueError("Closed observer image inventory malformed")
    baseline_images.update(initial)
    context_root = root / ".waveform-context"
    context_root.mkdir(mode=0o700)
    os.environ["MPLCONFIGDIR"] = str(context_root / "matplotlib")
    direct_env = dict(item.split("=", 1) for item in native_environment(context_root).split("\0") if item)
    direct = subprocess.run([
        python_image, "-I", "-B", "-c",
        "import sys,json;sys.path.insert(0,sys.argv[1]);import waveform_m08_windows as w;"
        "n=w.Native();print(json.dumps(n.loaded_paths()));n.cleanup()", str(ROOT / "scripts"),
    ], cwd=context_root, env=direct_env, stdin=subprocess.DEVNULL, capture_output=True, timeout=15, check=True)
    if direct.stderr or len(direct.stdout) > 65536:
        raise ValueError("Direct native Python image inventory failed")
    direct_images = json.loads(direct.stdout)
    if not isinstance(direct_images, list) or not 1 <= len(direct_images) <= 256 or any(not isinstance(p, str) for p in direct_images):
        raise ValueError("Direct native image inventory malformed")
    baseline_images.update(direct_images)
    staging = root / ".job-staging"
    staging.mkdir(mode=0o700)
    if binary_sha(executable) != expected_probe_sha:
        raise ValueError("SDK probe executable differs from its reviewed bytes")
    with open_input(review, 65536) as handle:
        review_sha = hashlib.sha256(handle.read_bytes()).hexdigest()
    environment = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "SYSTEMDRIVE"}}
    environment.update(TMP=str(context_root), TEMP=str(context_root), PYTHONDONTWRITEBYTECODE="1")
    measured = subprocess.run([str(executable)], cwd=context_root, env=environment, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=True)
    if measured.stderr:
        raise ValueError("SDK layout probe produced diagnostics")
    parse_abi(measured.stdout)
    stdout = context_root / "abi.stdout"
    write_new(stdout, measured.stdout)
    # Discover genuine loaded images, including the actual full response/FFT
    # reader plugins. The discovery calculation is authored, NOT containment
    # evidence, field evidence, or a passed resource profile.
    prepare_engine()
    spec = importlib.util.spec_from_file_location("m08_qualification_fixture", ROOT / "tests/fixtures/waveform_m08/full_workflow.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    from waveform_m08_child import calculate_bytes
    case = fixture.make_case("nominal3")
    calculate_bytes(case["mseed"], case["stationxml"], case["request"])
    paths = baseline_images | set(native.loaded_paths()) | {str(Path(sys.executable).resolve())}
    for _ in range(8):
        if len(paths) > 256:
            raise ValueError("Selected runtime exceeds the fixed image inventory cap")
        runtime = [{"path": p, "sha256": binary_sha(p)} for p in sorted(paths, key=str.casefold)]
        after = paths | set(native.loaded_paths()) | {str(Path(sys.executable).resolve())}
        if after == paths:
            break
        paths = after
    else:
        raise ValueError("Selected runtime image inventory did not stabilize")
    native.cleanup()
    source = ROOT / "tests/fixtures/waveform_m08/abi_probe.c"
    with open_output(staging) as directory:
        parent = {"path": str(staging), "identity": list(directory.identity), "context_receipt_sha256": review_sha}
    admission = {
        "schema": "caos.m08-private-admission.v1", "source_revision": revision,
        "scientific_site_packages": str(site_packages),
        "parent": parent, "review_receipt_sha256": review_sha,
        "abi": {"source": str(source), "source_sha256": binary_sha(source), "executable": str(executable),
                "executable_sha256": expected_probe_sha, "stdout": str(stdout),
                "stdout_sha256": hashlib.sha256(measured.stdout).hexdigest(), "review_receipt_sha256": review_sha},
        "code": [{"path": p, "sha256": binary_sha(p)} for p in sorted(code_paths())], "runtime": runtime,
    }
    raw = canonical(admission)
    path = context_root / "admission.json"
    write_new(path, raw)
    context = {"schema": "geophysics.waveform-worker-context/v1", "platform": "windows",
               "python": python_image, "python_sha256": binary_sha(python_image),
               "admission_path": str(path), "admission_sha256": hashlib.sha256(raw).hexdigest()}
    write_new(context_root / "context.json", canonical(context))
    return {"schema": "geophysics.waveform-context-measurement/v1", "abi_measured": True,
            "runtime_image_count": len(runtime), "authored_image_discovery_only": True,
            "runtime_authorized": False, "method_accepted": False, "host_admitted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--abi-executable", required=True, type=Path)
    parser.add_argument("--abi-sha256", required=True)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    print(json.dumps(qualify(args.data_root, args.abi_executable, args.abi_sha256, args.review, args.source_revision), sort_keys=True))


if __name__ == "__main__":
    main()
