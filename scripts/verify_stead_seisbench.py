"""Independently compare the strict STEAD adapter with SeisBench on train/dev.

This local-only check never opens selected test waveforms. It requires the
complete pinned STEAD mirror and records no waveform samples in the receipt.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

import numpy as np
from seisbench.data import WaveformDataset


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from stead_phase import (  # noqa: E402
    METADATA_SHA256, WAVEFORM_BYTES, SteadHdfReader, SteadMember, file_sha256,
)


def _sample_members(manifest: Path, partition: str, count: int) -> list[SteadMember]:
    document = json.loads(manifest.read_text(encoding="utf-8"))
    if (document.get("schema") != "caos.stead-phase-members.v1"
            or document.get("report", {}).get("metadata_sha256") != METADATA_SHA256):
        raise ValueError("selection manifest does not bind the pinned metadata")
    rows = document.get("members", {}).get(partition)
    if not isinstance(rows, list) or len(rows) < count:
        raise ValueError(f"selection manifest lacks {partition} members")
    ordered = sorted(rows, key=lambda row: hashlib.sha256(
        ("caos-seisbench-adapter-v1|" + row["trace_id"]).encode()).digest())
    return [SteadMember(**row) for row in ordered[:count]]


def verify(source_dir: Path, manifest: Path, *, count_per_partition: int = 3) -> dict:
    if count_per_partition < 1 or count_per_partition > 20:
        raise ValueError("verification sample count must be between 1 and 20")
    if version("seisbench") != "0.11.5":
        raise ValueError("independent reader must use pinned SeisBench 0.11.5")
    metadata_path = source_dir / "metadata.csv"
    waveform_path = source_dir / "waveforms.hdf5"
    if (metadata_path.stat().st_size != 402_560_190
            or file_sha256(metadata_path) != METADATA_SHA256):
        raise ValueError("SeisBench metadata differs from the pinned source")
    selected = [
        (partition, member)
        for partition in ("train", "dev")
        for member in _sample_members(manifest, partition, count_per_partition)
    ]
    if len({member.trace_id for _, member in selected}) != len(selected):
        raise ValueError("independent sample repeats a trace")
    dataset = WaveformDataset(
        path=source_dir, component_order="ENZ", sampling_rate=100, cache=None,
    )
    lookup = dataset.metadata.reset_index().set_index("trace_name")["index"]
    rows = []
    expected_sha256 = "4d73f567d9ea85fcdea5f2d8bf9cf47fd2e0c25b602793d41f56713efba62b1b"
    with SteadHdfReader(
        waveform_path, expected_sha256=expected_sha256, expected_bytes=WAVEFORM_BYTES,
    ) as strict:
        for partition, member in selected:
            index = int(lookup.loc[member.trace_name])
            external = dataset.get_waveforms(idx=index)
            local = strict.read(member).values_counts_enz.T
            if external.shape != (3, 6000) or local.shape != external.shape:
                raise ValueError("SeisBench and strict adapter disagree on trace shape")
            if not np.all(np.isfinite(external)):
                raise ValueError("SeisBench returned nonfinite samples")
            error = float(np.max(np.abs(external.astype(np.float64) - local)))
            if error != 0:
                raise ValueError(f"SeisBench and strict adapter differ on {member.trace_id}")
            rows.append({
                "partition": partition,
                "trace_id_sha256": hashlib.sha256(member.trace_id.encode()).hexdigest(),
                "source_index": index,
                "shape": list(external.shape),
                "max_abs_difference_counts": error,
            })
    return {
        "schema": "caos.stead-seisbench-parity.v1",
        "source": "SeisBench STEAD mirror",
        "metadata_sha256": METADATA_SHA256,
        "waveform_sha256": expected_sha256,
        "waveform_bytes": WAVEFORM_BYTES,
        "selection": "train/dev only, SHA-256 rank independent of waveform values",
        "seisbench_version": version("seisbench"),
        "component_order": "ENZ",
        "sampling_rate_hz": 100,
        "unit": "unrestituted instrument counts",
        "records": rows,
        "test_waveforms_opened": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/raw/phase/stead-selection.json")
    parser.add_argument("--count-per-partition", type=int, default=3)
    parser.add_argument("--receipt", type=Path, default=ROOT / "data/raw/phase/stead-seisbench-parity.json")
    args = parser.parse_args()
    report = verify(
        args.source_dir, args.manifest, count_per_partition=args.count_per_partition,
    )
    target = args.receipt.resolve()
    if not target.is_relative_to((ROOT / "data/raw").resolve()) or target.exists():
        raise ValueError("private SeisBench receipt must be new and under ignored data/raw")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": str(target), "compared": len(report["records"]),
                      "maximum_absolute_difference_counts": max(
                          row["max_abs_difference_counts"] for row in report["records"]
                      )}, indent=2))


if __name__ == "__main__":
    main()
