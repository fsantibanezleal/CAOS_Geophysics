"""Extract one already-selected STEAD partition to ignored local training arrays.

Test trace bytes are inaccessible through this command without a frozen
checkpoint path. QC failures remain in the private index rather than being
silently replaced by another trace. No output is a public release asset.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from stead_phase import (  # noqa: E402
    METADATA_SHA256, TRACE_NAME, SteadFormatError, SteadHdfReader, SteadMember,
    WAVEFORM_BYTES, file_sha256, normalize_counts,
)


def _members(path: Path, partition: str) -> tuple[list[SteadMember], str]:
    if not path.is_file() or path.is_symlink():
        raise SteadFormatError("private selection manifest is missing or a symlink")
    document = json.loads(path.read_text(encoding="utf-8"))
    if (document.get("schema") != "caos.stead-phase-members.v1"
            or document.get("report", {}).get("metadata_sha256") != METADATA_SHA256):
        raise SteadFormatError("selection manifest does not bind the pinned STEAD metadata")
    rows = document.get("members", {}).get(partition)
    if not isinstance(rows, list) or not rows:
        raise SteadFormatError(f"selection manifest lacks {partition} members")
    members = [SteadMember(**row) for row in rows]
    if any(member.partition != partition for member in members):
        raise SteadFormatError("selection manifest partition labels disagree")
    if any(not TRACE_NAME.fullmatch(member.trace_name) for member in members):
        raise SteadFormatError("selection manifest has an unsupported bucket slice")
    ids = [member.trace_id for member in members]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise SteadFormatError("selection manifest IDs are unsorted or duplicated")
    digest = hashlib.sha256("\n".join(ids).encode()).hexdigest()
    if digest != document["report"]["selected"][partition]["ids_sha256"]:
        raise SteadFormatError("selection manifest member digest disagrees with report")
    return members, digest


def _frozen_model_receipt(path: Path, *, member_hash: str, source_hash: str,
                          private_root: Path) -> str:
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(private_root.resolve()):
        raise ValueError("test extraction requires a private frozen checkpoint receipt")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("frozen checkpoint receipt is unreadable") from error
    filename = receipt.get("checkpoint_filename")
    if (receipt.get("schema") != "caos.phase-freeze.v1" or receipt.get("frozen_before_test") is not True
            or receipt.get("test_selection_sha256") != member_hash
            or receipt.get("waveform_source_sha256") != source_hash
            or not isinstance(filename, str) or filename != Path(filename).name
            or not filename.endswith(".pt")
            or type(receipt.get("chosen_epoch")) is not int or receipt["chosen_epoch"] < 1
            or any(not isinstance(receipt.get(key), (int, float)) or not 0 < receipt[key] <= 1
                   for key in ("p_threshold", "s_threshold"))):
        raise ValueError("frozen checkpoint receipt lacks model, source, test split or dev thresholds")
    checkpoint = path.parent / filename
    checkpoint_hash = file_sha256(checkpoint)
    if checkpoint_hash != receipt.get("checkpoint_sha256"):
        raise ValueError("frozen checkpoint file hash disagrees with receipt")
    return checkpoint_hash


def extract_partition(
    manifest: Path,
    waveform_path: Path,
    output_dir: Path,
    *,
    partition: str,
    waveform_sha256: str,
    expected_bytes: int = WAVEFORM_BYTES,
    frozen_checkpoint: Path | None = None,
    private_root: Path = ROOT / "data/raw",
) -> dict:
    if partition not in ("train", "dev", "test"):
        raise ValueError("partition must be train, dev or test")
    members, member_hash = _members(manifest, partition)
    if partition == "test":
        if frozen_checkpoint is None:
            raise ValueError("test extraction requires a private frozen checkpoint receipt")
        checkpoint_hash = _frozen_model_receipt(frozen_checkpoint, member_hash=member_hash,
                                                source_hash=waveform_sha256,
                                                private_root=private_root)
    else:
        checkpoint_hash = None
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(private_root.resolve()):
        raise ValueError("waveform arrays must stay in ignored repository data/raw/")
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"stead-{partition}-normalized.npy"
    index_path = output_dir / f"stead-{partition}-index.json"
    if target.exists() or index_path.exists():
        raise FileExistsError("partition output exists; verify its receipt, never overwrite it")
    fd, temp_name = tempfile.mkstemp(prefix=f".stead-{partition}-", suffix=".npy", dir=output_dir)
    os.close(fd)
    staged = Path(temp_name)
    stage_index: Path | None = None
    failures: Counter[str] = Counter()
    entries: list[dict] = []
    try:
        values = np.lib.format.open_memmap(staged, mode="w+", dtype=np.float32,
                                           shape=(len(members), 3, 6000))
        values[:] = 0  # invalid rows are masked in index, never used as measured noise
        ordered = sorted(enumerate(members), key=lambda item: (
            item[1].trace_name.split("$", 1)[0],
            int(item[1].trace_name.split("$", 1)[1].split(",", 1)[0]),
        ))
        entries = [{"member": member.__dict__, "valid": False, "reason": "not-read"}
                   for member in members]
        with SteadHdfReader(waveform_path, expected_sha256=waveform_sha256,
                            expected_bytes=expected_bytes) as reader:
            for output_index, member in ordered:
                try:
                    waveform = reader.read(member)
                    normalized, scales = normalize_counts(waveform.values_counts_enz)
                    values[output_index] = normalized.T
                    entries[output_index] = {"member": member.__dict__, "valid": True,
                                             "scales": scales, "unit": "counts",
                                             "sample_interval_s": waveform.sample_interval_s}
                except (SteadFormatError, OSError, KeyError) as error:
                    reason = type(error).__name__ + ": " + str(error)
                    failures[reason] += 1
                    entries[output_index] = {"member": member.__dict__, "valid": False,
                                             "reason": reason}
        values.flush()
        del values
        array_sha256 = file_sha256(staged)
        index = {
            "schema": "caos.stead-phase-local-array.v1",
            "partition": partition,
            "selection_sha256": member_hash,
            "waveform_source_bytes": expected_bytes,
            "waveform_source_sha256": waveform_sha256,
            "frozen_checkpoint_sha256": checkpoint_hash,
            "array_sha256": array_sha256,
            "array_shape": [len(members), 3, 6000],
            "array_axis_order": ["trace", "E/N/Z", "sample"],
            "array_unit": "dimensionless normalized counts",
            "original_unit": "unrestituted instrument counts",
            "members": entries,
        }
        fd, temp_index = tempfile.mkstemp(prefix=f".stead-{partition}-", suffix=".json", dir=output_dir)
        os.close(fd)
        stage_index = Path(temp_index)
        stage_index.write_text(json.dumps(index, sort_keys=True) + "\n", encoding="utf-8")
        os.link(staged, target)
        os.link(stage_index, index_path)
    finally:
        staged.unlink(missing_ok=True)
        if stage_index is not None:
            stage_index.unlink(missing_ok=True)
    return {
        "schema": "caos.stead-phase-qc-summary.v1",
        "partition": partition,
        "source_sha256": waveform_sha256,
        "selected": len(members),
        "valid": sum(row["valid"] for row in entries),
        "quarantined": dict(sorted(failures.items())),
        "array_sha256": array_sha256,
        "frozen_checkpoint_sha256": checkpoint_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/raw/phase/stead-selection.json")
    parser.add_argument("--waveforms", type=Path, required=True)
    parser.add_argument("--waveform-sha256", required=True)
    parser.add_argument("--partition", choices=("train", "dev", "test"), required=True)
    parser.add_argument("--frozen-checkpoint", type=Path,
                        help="Private JSON freeze receipt, required before reading test waveforms")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/raw/phase/extracted")
    args = parser.parse_args()
    report = extract_partition(args.manifest, args.waveforms, args.output_dir,
                               partition=args.partition, waveform_sha256=args.waveform_sha256,
                               frozen_checkpoint=args.frozen_checkpoint)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
