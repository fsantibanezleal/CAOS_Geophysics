"""Pin actual Linux runtime closure; this is NOT native resource qualification."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "data-pipeline"))
from waveform_m08_linux import ADMISSION, TOOLS, code_hashes, image_sha, loaded_images, canonical, prepare_engine
from waveform_m08_files import external_work_path, open_output, open_input
from waveform_m08_windows import require


def capture(site, mseed, xml, request, destination):
    sys.path.insert(0, str(site))
    prepare_engine()
    before = loaded_images()
    from waveform_m08_child import calculate_bytes
    from waveform_m08_export import plan_export, write_export
    from waveform_m08_files import create_output
    with open_input(mseed, 16777216) as a, open_input(xml, 2097152) as b, open_input(request, 65536) as c:
        result, seal = calculate_bytes(a.read_bytes(), b.read_bytes(), c.read_bytes())
    with create_output(destination, trusted_parent=destination.parent) as directory:
        write_export(plan_export(result, seal), directory)
    combined = {**before, **loaded_images()}
    print(json.dumps({"runtime": [{"path": name, "sha256": combined[name]} for name in sorted(combined)],
                      "scientific_status": result.metadata["status"]}, sort_keys=True, separators=(",", ":")))


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--capture", action="store_true")
    for name in ("data-root", "python", "site-packages", "mseed", "stationxml", "request", "source-revision"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--uid", type=int, required=True)
    parser.add_argument("--gid", type=int, required=True)
    args = parser.parse_args(argv)
    import re
    require(sys.platform == "linux" and re.fullmatch("[a-f0-9]{40}", args.source_revision) is not None
            and 1 <= args.uid < 2**32 and 1 <= args.gid < 2**32)
    root = external_work_path(args.data_root)
    if args.capture:
        capture(Path(args.site_packages), external_work_path(args.mseed), external_work_path(args.stationxml),
                external_work_path(args.request), root / ".waveform-context/closure-export")
        return 0
    context = root / ".waveform-context"
    context.mkdir(mode=0o700)
    staging = root / ".job-staging"
    staging.mkdir(mode=0o700, exist_ok=True)
    environment = {"PATH": "/usr/bin:/bin", "TMPDIR": str(context), "TMP": str(context), "TEMP": str(context),
                   "HOME": str(context), "MPLCONFIGDIR": str(context / "matplotlib"), "XDG_CACHE_HOME": str(context / "cache"),
                   "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    result = subprocess.run([args.python, "-I", "-B", str(Path(__file__).resolve()), "--capture", *(argv or sys.argv[1:])],
                            env=environment, stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
    require(result.returncode == 0 and len(result.stdout) <= 65536)
    captured = json.loads(result.stdout)
    with open_output(staging) as held:
        admission = {"schema": ADMISSION, "platform": "linux", "source_revision": args.source_revision,
                     "observer_uid": os.geteuid(), "uid": args.uid, "gid": args.gid,
                     "python": args.python, "python_sha256": image_sha(args.python), "site_packages": args.site_packages,
                     "parent": {"path": str(staging), "identity": list(held.identity),
                                "context_receipt_sha256": __import__("hashlib").sha256(canonical(captured)).hexdigest()},
                     "code": code_hashes(), "runtime": captured["runtime"],
                     "supervisor": {role: image_sha(path) for role, path in TOOLS.items()}}
    encoded = canonical(admission)
    path = context / "admission.json"
    with path.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    from waveform_input import sha
    value = {"schema": "geophysics.waveform-worker-context/v1", "platform": "linux", "python": args.python,
             "python_sha256": admission["python_sha256"], "admission_path": str(path), "admission_sha256": sha(encoded)}
    with (context / "context.json").open("xb") as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"context_sha256": sha(canonical(value)), "runtime_authorized": False,
                      "native_resource_qualification": "not_run", "capture_status": captured["scientific_status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
