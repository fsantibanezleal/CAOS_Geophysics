"""Compare committed learned outputs with a rebuilt candidate, excluding provenance-only fields."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "data-pipeline"
sys.path.insert(0, str(PIPELINE))
from provenance import generator_fingerprint, matches_generator_fingerprint  # noqa: E402

CASES = ("LEARNED_CNN", "LEARNED_AUTOENCODER")
VARIANTS = ("reference", "contrast", "noise", "acquisition", "coverage", "regularization")
ALLOWED_CHANGES = {"provenance.generator_fingerprint", "provenance.version", "runtime_seconds"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def differences(left, right, path=""):
    if isinstance(left, dict) and isinstance(right, dict):
        result = []
        for key in sorted(set(left) | set(right)):
            child = f"{path}.{key}" if path else key
            if key not in left or key not in right:
                result.append(child)
            else:
                result.extend(differences(left[key], right[key], child))
        return result
    if isinstance(left, list) and isinstance(right, list):
        result = [item for index, (a, b) in enumerate(zip(left, right))
                  for item in differences(a, b, f"{path}[{index}]")]
        return result + ([f"{path}.length"] if len(left) != len(right) else [])
    return [] if left == right else [path]


def compare(canonical: Path, candidate: Path) -> dict:
    records = []
    for case in CASES:
        for variant in VARIANTS:
            relative = Path(case) / f"{variant}.json"
            source_path, candidate_path = canonical / relative, candidate / relative
            source = json.loads(source_path.read_text(encoding="utf-8"))
            rebuilt = json.loads(candidate_path.read_text(encoding="utf-8"))
            if source.get("id") != case or rebuilt.get("id") != case:
                raise ValueError(f"Case identity mismatch: {relative}")
            if source.get("variant") != variant or rebuilt.get("variant") != variant:
                raise ValueError(f"Variant identity mismatch: {relative}")
            source_provenance = source.get("provenance", {})
            rebuilt_provenance = rebuilt.get("provenance", {})
            if not matches_generator_fingerprint(
                "learned", source_provenance.get("generator_fingerprint"),
                version=source_provenance.get("version"),
            ):
                raise ValueError(f"Unsupported source provenance: {relative}")
            if rebuilt_provenance.get("generator_fingerprint") != generator_fingerprint(
                "learned", version=rebuilt_provenance.get("version"),
            ):
                raise ValueError(f"Candidate provenance is not current: {relative}")
            changed = differences(source, rebuilt)
            unexpected = sorted(set(changed) - ALLOWED_CHANGES)
            if unexpected:
                raise ValueError(f"Scientific output changed in {relative}: {unexpected}")
            records.append({
                "path": relative.as_posix(),
                "canonical_sha256": sha256(source_path),
                "candidate_sha256": sha256(candidate_path),
                "changed_metadata": changed,
                "scientific_fields_identical": True,
            })
    return {
        "schema": "inverse-earth/learned-replay-parity/v1",
        "canonical_root": "data/derived/v2",
        "candidate_root": "external candidate directory",
        "compared_artifacts": len(records),
        "allowed_metadata_changes": sorted(ALLOWED_CHANGES),
        "all_scientific_fields_identical": True,
        "artifacts": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, default=ROOT / "data/derived/v2")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = compare(args.canonical, args.candidate)
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    print(f"PASS: {report['compared_artifacts']} learned artifacts; all scientific fields identical")


if __name__ == "__main__":
    main()
