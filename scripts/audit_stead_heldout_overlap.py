"""Post-score audit for exact waveform and metadata leakage into STEAD test.

This checks the frozen train/dev/test arrays after, never before, the one-pass
held-out benchmark. It does not change the split or refit the model. Exact
equality cannot rule out approximate waveform copies or source mislabelling.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from evaluate_stead_phase import _load_locked_test  # noqa: E402
from extract_stead_phase import _members  # noqa: E402
from train_stead_phase import ExtractedPhaseDataset  # noqa: E402


def audit(extraction_dir: Path, manifest_path: Path, frozen_receipt_path: Path,
          benchmark_path: Path, report_path: Path) -> dict:
    if report_path.exists() or report_path.is_symlink():
        raise FileExistsError("post-score overlap report already exists; never overwrite")
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    if (benchmark.get("schema") != "caos.stead-phase-heldout-benchmark.v1"
            or benchmark.get("status") != "computed-on-real-heldout-waveforms"):
        raise ValueError("locked held-out benchmark must exist before overlap audit")
    training = ExtractedPhaseDataset(extraction_dir, "train")
    development = ExtractedPhaseDataset(extraction_dir, "dev")
    _test_members, test_index, test_values, frozen, _checkpoint, checkpoint_hash = _load_locked_test(
        extraction_dir, manifest_path, frozen_receipt_path, ROOT / "data/raw",
    )
    if (benchmark.get("checkpoint_sha256") != checkpoint_hash
            or benchmark.get("test_array_sha256") != test_index["array_sha256"]
            or benchmark.get("valid") != sum(row["valid"] is True for row in test_index["members"])):
        raise ValueError("held-out benchmark is not bound to the extracted test array")
    partitions = {
        "train": (training.index, training.array, training.valid_indices),
        "dev": (development.index, development.array, development.valid_indices),
        "test": (test_index, test_values, [
            i for i, row in enumerate(test_index["members"]) if row["valid"] is True
        ]),
    }
    if any(index["waveform_source_sha256"] != frozen["waveform_source_sha256"]
           for index, _array, _valid in partitions.values()):
        raise ValueError("partitions do not share the frozen waveform source")
    if any(index["selection_sha256"] != _members(manifest_path, name)[1]
           for name, (index, _array, _valid) in partitions.items()):
        raise ValueError("partition index differs from its locked metadata selection")
    metadata_seen: dict[str, dict[str, str]] = {"event": {}, "station": {}}
    metadata_overlap = Counter()
    for partition, (index, _array, _valid) in partitions.items():
        for row in index["members"]:
            member = row["member"]
            for kind, identifier in (("event", member["event_id"]),
                                     ("station", member["station_id"])):
                if identifier is None:
                    continue
                previous = metadata_seen[kind].setdefault(identifier, partition)
                if previous != partition:
                    metadata_overlap[f"{kind}:{'/'.join(sorted((previous, partition)))}"] += 1
    hashes: dict[bytes, str] = {}
    duplicate_counts = Counter()
    within = {}
    for partition, (_index, values, valid_indices) in partitions.items():
        local = set()
        repeated = 0
        for row_index in valid_indices:
            digest = hashlib.sha256(values[row_index].tobytes(order="C")).digest()
            if digest in local:
                repeated += 1
            local.add(digest)
            previous = hashes.setdefault(digest, partition)
            if previous != partition:
                duplicate_counts[f"{previous}/{partition}"] += 1
        within[partition] = repeated
    status = "no-exact-cross-partition-overlap" if not duplicate_counts and not metadata_overlap else "overlap-detected"
    report = {
        "schema": "caos.stead-phase-heldout-overlap.v1",
        "status": status,
        "performed_after_locked_heldout_scoring": True,
        "checkpoint_sha256": checkpoint_hash,
        "waveform_source_sha256": frozen["waveform_source_sha256"],
        "array_sha256": {name: index["array_sha256"]
                         for name, (index, _array, _valid) in partitions.items()},
        "valid": {name: len(valid) for name, (_index, _array, valid) in partitions.items()},
        "basis": "SHA-256 of each complete 3x6000 normalized float32 E/N/Z array",
        "within_partition_exact_duplicates": within,
        "cross_partition_exact_duplicates": dict(sorted(duplicate_counts.items())),
        "cross_partition_event_station_id_reuse": dict(sorted(metadata_overlap.items())),
        "non_claim": "does not detect approximate copies, related events under other IDs or source label errors",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction-dir", type=Path, default=ROOT / "data/raw/phase/extracted")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/raw/phase/stead-selection.json")
    parser.add_argument("--frozen-receipt", type=Path,
                        default=ROOT / "data/raw/phase/models-amp2/phase-freeze.json")
    parser.add_argument("--benchmark", type=Path,
                        default=ROOT / "data/derived/phase/stead-heldout-benchmark.json")
    parser.add_argument("--report", type=Path,
                        default=ROOT / "data/derived/phase/stead-heldout-overlap.json")
    args = parser.parse_args()
    print(json.dumps(audit(args.extraction_dir, args.manifest, args.frozen_receipt,
                           args.benchmark, args.report), indent=2))


if __name__ == "__main__":
    main()
