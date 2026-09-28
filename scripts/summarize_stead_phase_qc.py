"""Publish aggregate train/dev waveform-QC counts without trace identities or samples.

The raw arrays and per-trace indices remain ignored. This deterministic report
is only an extraction receipt; it is not model or held-out performance.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from stead_phase import METADATA_SHA256, file_sha256  # noqa: E402


def summarize(extraction_dir: Path) -> dict:
    partitions: dict[str, dict] = {}
    source_sha256: str | None = None
    for partition in ("train", "dev"):
        index_path = extraction_dir / f"stead-{partition}-index.json"
        array_path = extraction_dir / f"stead-{partition}-normalized.npy"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        entries = index.get("members")
        shape = index.get("array_shape")
        if (index.get("schema") != "caos.stead-phase-local-array.v1"
                or index.get("partition") != partition
                or not isinstance(entries, list) or not entries
                or shape != [len(entries), 3, 6000]
                or not re.fullmatch(r"[0-9a-f]{64}", index.get("array_sha256", ""))
                or not re.fullmatch(r"[0-9a-f]{64}", index.get("selection_sha256", ""))
                or not re.fullmatch(r"[0-9a-f]{64}", index.get("waveform_source_sha256", ""))):
            raise ValueError(f"{partition} extraction index is incompatible or incomplete")
        if array_path.is_symlink() or file_sha256(array_path) != index["array_sha256"]:
            raise ValueError(f"{partition} extracted array differs from its pinned index")
        array = np.load(array_path, mmap_mode="r", allow_pickle=False)
        if array.shape != tuple(shape) or array.dtype != np.float32:
            raise ValueError(f"{partition} extracted array shape or type drifted")
        if source_sha256 is not None and source_sha256 != index["waveform_source_sha256"]:
            raise ValueError("train/dev extracted arrays name different waveform sources")
        source_sha256 = index["waveform_source_sha256"]
        reasons: Counter[str] = Counter()
        categories: Counter[str] = Counter()
        for row in entries:
            if row.get("valid") is True:
                categories[row["member"]["category"]] += 1
            elif row.get("valid") is False and isinstance(row.get("reason"), str):
                reasons[row["reason"]] += 1
            else:
                raise ValueError(f"{partition} row lacks a typed QC outcome")
        partitions[partition] = {
            "selected": len(entries),
            "valid": sum(categories.values()),
            "quarantined": sum(reasons.values()),
            "valid_categories": dict(sorted(categories.items())),
            "quarantine_reasons": dict(sorted(reasons.items())),
            "selection_sha256": index["selection_sha256"],
            "private_array_sha256": index["array_sha256"],
        }
    return {
        "schema": "caos.stead-phase-train-dev-qc.v1",
        "metadata_sha256": METADATA_SHA256,
        "waveform_source_sha256": source_sha256,
        "partitions": partitions,
        "test_waveforms_opened": False,
        "model_trained": False,
        "heldout_performance_established": False,
        "contains_trace_ids_or_waveform_samples": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction-dir", type=Path,
                        default=ROOT / "data/raw/phase/extracted")
    parser.add_argument("--report", type=Path,
                        default=ROOT / "data/derived/phase/stead-train-dev-qc.json")
    args = parser.parse_args()
    target = args.report.resolve()
    if (not target.is_relative_to((ROOT / "data/derived").resolve())
            or args.report.is_symlink() or target.exists()):
        raise ValueError("new aggregate QC report must be under data/derived/")
    report = summarize(args.extraction_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
