"""Generate or verify the frozen independent M04 S2 acquisition fixtures."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
GENERATOR_PATH = ROOT / "tests" / "fixtures" / "magnetic_survey" / "generate.py"
DEFAULT_OUTPUT = ROOT / "tests" / "fixtures" / "magnetic_survey" / "generated"
SPEC = importlib.util.spec_from_file_location("m04_s2_generator", GENERATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("M04 generator source cannot be loaded")
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def products() -> tuple[dict[str, bytes], dict]:
    files: dict[str, bytes] = {}
    entries = []
    for regime in "ABCDEF":
        for quantity in GENERATOR._QUANTITIES:
            request, truth = GENERATOR.acquisition_case(regime, quantity)
            stem = f"S2-{regime}-{quantity}"
            request_name = f"requests/{stem}.json"
            truth_name = f"truth/{stem}.json"
            request_raw, truth_raw = canonical(request), canonical(truth)
            files[request_name] = request_raw
            files[truth_name] = truth_raw
            entries.append({
                "regime": regime, "quantity": quantity,
                "request": {"path": request_name, "bytes": len(request_raw), "sha256": digest(request_raw)},
                "truth": {"path": truth_name, "bytes": len(truth_raw), "sha256": digest(truth_raw)},
                "field_observation": False, "inversion_accepted": False,
            })
    manifest = {
        "schema": "m04-independent-s2-acquisitions-1",
        "generator": GENERATOR.SOURCE_VERSION,
        "truth_engine": GENERATOR.ENGINE_VERSION,
        "noise": {"engine": f"NumPy {GENERATOR.NUMPY_VERSION} PCG64", "base_seed": GENERATOR.BASE_SEED,
                  "sd_nT": 0.5, "basis": "explicit conditional Gaussian; F is exact zero realization"},
        "geometry": {"source": "sealed authored S2 local ENU geometry",
                     "complete_lines": 12, "coverage_negative_lines": 4},
        "separation": "truth bodies and noise-free predictions are stored only under truth/",
        "cases": entries,
        "claims": {"field_observations": False, "geology_truth": False,
                   "inverse_results": False, "method_acceptance": False},
    }
    return files, manifest


def write_new(output: Path, files: dict[str, bytes], manifest: dict) -> str:
    manifest_raw = canonical(manifest)
    targets = {name: output / Path(name) for name in files}
    manifest_path = output / "manifest.json"
    all_targets = [*targets.values(), manifest_path]
    if any(path.exists() or path.is_symlink() for path in all_targets):
        raise FileExistsError("refusing to overwrite any existing M04 fixture member")
    created: list[Path] = []
    try:
        for name, path in targets.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                created.append(path)
                stream.write(files[name])
                stream.flush()
                os.fsync(stream.fileno())
        with manifest_path.open("xb") as stream:
            created.append(manifest_path)
            stream.write(manifest_raw)
            stream.flush()
            os.fsync(stream.fileno())
        for name, path in targets.items():
            if path.stat().st_size != len(files[name]) or digest(path.read_bytes()) != digest(files[name]):
                raise OSError(f"fixture readback differs: {name}")
        if digest(manifest_path.read_bytes()) != digest(manifest_raw):
            raise OSError("fixture manifest readback differs")
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    return digest(manifest_raw)


def verify(output: Path, files: dict[str, bytes], manifest: dict) -> str:
    expected_manifest = canonical(manifest)
    actual_manifest_path = output / "manifest.json"
    if actual_manifest_path.is_symlink() or not actual_manifest_path.is_file():
        raise FileNotFoundError("generated M04 manifest is missing or unsafe")
    if actual_manifest_path.read_bytes() != expected_manifest:
        raise ValueError("generated M04 manifest differs from deterministic replay")
    for name, expected in files.items():
        path = output / Path(name)
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(f"generated M04 fixture is missing or unsafe: {name}")
        actual = path.read_bytes()
        if len(actual) != len(expected) or digest(actual) != digest(expected):
            raise ValueError(f"generated M04 fixture differs from deterministic replay: {name}")
    expected_files = {"manifest.json", *files}
    actual_files = {path.relative_to(output).as_posix()
                    for path in output.rglob("*") if path.is_file() or path.is_symlink()}
    if actual_files != expected_files:
        raise ValueError("generated M04 fixture directory contains missing or unexpected members")
    return digest(expected_manifest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="explicit fixture directory (default: tests/fixtures/magnetic_survey/generated)")
    parser.add_argument("--check", action="store_true", help="verify exact deterministic replay without writing")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    files, manifest = products()
    try:
        identity = verify(output, files, manifest) if args.check else write_new(output, files, manifest)
    except (OSError, ValueError) as error:
        print(f"M04 fixture generation failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"schema": manifest["schema"], "cases": len(manifest["cases"]),
                      "request_count": len(manifest["cases"]), "truth_count": len(manifest["cases"]),
                      "artifact_files": len(files), "manifest_sha256": identity,
                      "output": str(output), "claims": manifest["claims"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
