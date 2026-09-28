"""Strict local STEAD/SeisBench waveform selection and decoding for M08/M13.

The mirror is not a web asset. Source bytes stay in ignored raw storage. Its
published trace-level split is deliberately not used for scientific scoring.
"""

from __future__ import annotations

from collections import Counter
import csv
from dataclasses import asdict, dataclass
import hashlib
import heapq
import math
from pathlib import Path
import re

import h5py
import numpy as np


METADATA_BYTES = 402_560_190
METADATA_SHA256 = "9b9007406ebfef8c182060c8bb4266d29bbc433985f91f7e2dc476c8aca08efe"
WAVEFORM_BYTES = 91_127_786_704
SPLIT_SALT = "caos-stead-station-event-v1"
SELECT_SALT = "caos-stead-trace-rank-v1"
TRACE_NAME = re.compile(r"^(bucket[0-9]+)\$([0-9]+),:3,:6000$")
PARTITIONS = ("train", "dev", "test")
REQUIRED = {
    "station_network_code", "station_code", "source_id", "trace_category",
    "trace_p_arrival_sample", "trace_s_arrival_sample", "trace_p_status",
    "trace_s_status", "trace_name_original", "trace_name", "trace_channel",
}


class SteadFormatError(ValueError):
    """Source format or identity was not proven; do not use this trace."""


@dataclass(frozen=True)
class SteadMember:
    trace_id: str
    trace_name: str
    event_id: str | None
    station_id: str
    partition: str
    category: str
    channel: str
    p_index: int | None
    s_index: int | None


@dataclass(frozen=True)
class SteadWaveform:
    member: SteadMember
    values_counts_enz: np.ndarray  # [sample, E/N/Z], unrestituted counts
    sample_interval_s: float = 0.01


def file_sha256(path: Path, *, expected_bytes: int | None = None) -> str:
    if not path.is_file() or path.is_symlink():
        raise SteadFormatError(f"source is missing or a symlink: {path}")
    if expected_bytes is not None and path.stat().st_size != expected_bytes:
        raise SteadFormatError(f"source byte count differs: expected {expected_bytes}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path: Path, *, expected_bytes: int, expected_sha256: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise SteadFormatError("expected SHA-256 must be a lowercase digest")
    if file_sha256(path, expected_bytes=expected_bytes) != expected_sha256:
        raise SteadFormatError("source SHA-256 differs from pinned receipt")


def hash_partition(kind: str, identifier: str) -> str:
    digest = hashlib.sha256(f"{SPLIT_SALT}|{kind}|{identifier}".encode()).digest()
    fraction = int.from_bytes(digest[:8], "big") / 2**64
    return "train" if fraction < 0.70 else "dev" if fraction < 0.85 else "test"


def _pick_index(text: str) -> int | None:
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    if math.isfinite(value) and 0 <= value < 6000 and int(value) == value:
        return int(value)
    return None


def _member(row: dict[str, str]) -> tuple[SteadMember | None, str]:
    trace_id = row["trace_name_original"]
    trace_name = row["trace_name"]
    network = row["station_network_code"]
    station = row["station_code"]
    if (not trace_id or not network or not station or not row["trace_channel"]
            or not TRACE_NAME.fullmatch(trace_name)):
        return None, "missing-id-station-channel-or-unsupported-slice"
    station_id = f"{network}.{station}"
    station_partition = hash_partition("station", station_id)
    category = row["trace_category"]
    if category == "noise":
        if row["source_id"] or row["trace_p_arrival_sample"] or row["trace_s_arrival_sample"]:
            return None, "noise-has-event-or-pick"
        return SteadMember(trace_id, trace_name, None, station_id, station_partition,
                           "noise", row["trace_channel"], None, None), "accepted"
    if category != "earthquake_local":
        return None, "unsupported-category"
    event = row["source_id"]
    p_index = _pick_index(row["trace_p_arrival_sample"])
    s_index = _pick_index(row["trace_s_arrival_sample"])
    if not event or p_index is None or s_index is None or p_index >= s_index:
        return None, "missing-event-or-ordered-picks"
    if row["trace_p_status"] != "manual" or row["trace_s_status"] != "manual":
        return None, "nonmanual-analyst-pick"
    event_partition = hash_partition("event", event)
    if event_partition != station_partition:
        return None, "event-station-partition-conflict"
    return SteadMember(trace_id, trace_name, event, station_id, station_partition,
                       "earthquake_local", row["trace_channel"], p_index, s_index), "accepted"


def select_metadata(
    path: Path,
    *,
    caps: dict[str, dict[str, int]],
    expected_bytes: int = METADATA_BYTES,
    expected_sha256: str = METADATA_SHA256,
) -> tuple[dict[str, list[SteadMember]], dict]:
    """Select by metadata-only hash rank after independent event/station partitioning.

    `caps` has train/dev/test keys, each with earthquake_local and noise limits.
    It is fixed before waveform inspection. The test inventory is only named,
    not opened or scored, at this stage.
    """
    verify_file(path, expected_bytes=expected_bytes, expected_sha256=expected_sha256)
    if set(caps) != set(PARTITIONS) or any(set(caps[p]) != {"earthquake_local", "noise"}
                                          or any(type(n) is not int or n < 1 for n in caps[p].values())
                                          for p in PARTITIONS):
        raise ValueError("caps must supply positive earthquake_local/noise limits for train/dev/test")
    heaps: dict[tuple[str, str], list[tuple[int, str, SteadMember]]] = {
        (partition, category): [] for partition in PARTITIONS
        for category in ("earthquake_local", "noise")
    }
    reasons: Counter[str] = Counter()
    candidates: Counter[str] = Counter()
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not REQUIRED.issubset(reader.fieldnames or ()):
            raise SteadFormatError("STEAD metadata lacks required identity/pick columns")
        for row in reader:
            member, reason = _member(row)
            reasons[reason] += 1
            if member is None:
                continue
            key = (member.partition, member.category)
            candidates[f"{key[0]}/{key[1]}"] += 1
            rank = int.from_bytes(hashlib.sha256(
                f"{SELECT_SALT}|{member.trace_id}".encode()).digest()[:8], "big")
            heap = heaps[key]
            entry = (-rank, member.trace_id, member)
            if len(heap) < caps[key[0]][key[1]]:
                heapq.heappush(heap, entry)
            elif entry > heap[0]:
                heapq.heapreplace(heap, entry)
    selected = {partition: sorted(
        (entry[2] for category in ("earthquake_local", "noise")
         for entry in heaps[(partition, category)]), key=lambda member: member.trace_id)
        for partition in PARTITIONS}
    stations = {partition: {member.station_id for member in selected[partition]}
                for partition in PARTITIONS}
    events = {partition: {member.event_id for member in selected[partition]
                          if member.event_id is not None} for partition in PARTITIONS}
    for index, first in enumerate(PARTITIONS):
        for second in PARTITIONS[index + 1:]:
            if stations[first] & stations[second] or events[first] & events[second]:
                raise SteadFormatError("selected partitions leak an event or station")
    ids = [member.trace_id for partition in PARTITIONS for member in selected[partition]]
    if len(ids) != len(set(ids)):
        raise SteadFormatError("duplicate selected original trace ID")
    report = {
        "schema": "caos.stead-phase-selection.v1",
        "metadata_bytes": expected_bytes,
        "metadata_sha256": expected_sha256,
        "source_split_ignored": True,
        "partition_salt": SPLIT_SALT,
        "rank_salt": SELECT_SALT,
        "caps": caps,
        "reasons": dict(sorted(reasons.items())),
        "eligible_candidates": dict(sorted(candidates.items())),
        "selected": {partition: {
            "earthquake_local": sum(member.category == "earthquake_local" for member in selected[partition]),
            "noise": sum(member.category == "noise" for member in selected[partition]),
            "ids_sha256": hashlib.sha256("\n".join(member.trace_id for member in selected[partition]).encode()).hexdigest(),
        } for partition in PARTITIONS},
    }
    return selected, report


def serializable_members(selected: dict[str, list[SteadMember]]) -> dict[str, list[dict]]:
    return {partition: [asdict(member) for member in members]
            for partition, members in selected.items()}


def _format_value(group: h5py.Group, key: str) -> str:
    if key in group:
        value = group[key][()]
    elif key in group.attrs:
        value = group.attrs[key]
    else:
        raise SteadFormatError(f"HDF5 data_format lacks {key}")
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, np.ndarray) and value.ndim == 0:
        value = value.item()
    return str(value)


class SteadHdfReader:
    """Read one verified mirror trace; never eval SeisBench slice expressions."""

    def __init__(self, path: Path, *, expected_sha256: str, expected_bytes: int = WAVEFORM_BYTES):
        verify_file(path, expected_bytes=expected_bytes, expected_sha256=expected_sha256)
        self._handle = h5py.File(path, "r")
        try:
            if "data" not in self._handle or "data_format" not in self._handle:
                raise SteadFormatError("HDF5 lacks data and data_format groups")
            fmt = self._handle["data_format"]
            required = {"dimension_order": "CW", "component_order": "ZNE",
                        "unit": "counts", "instrument_response": "not restituted"}
            for key, expected in required.items():
                if _format_value(fmt, key) != expected:
                    raise SteadFormatError(f"HDF5 {key} is not declared {expected}")
            if float(_format_value(fmt, "sampling_rate")) != 100.0:
                raise SteadFormatError("HDF5 sample rate is not 100 Hz")
        except Exception:
            self._handle.close()
            raise

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> SteadHdfReader:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def read(self, member: SteadMember) -> SteadWaveform:
        match = TRACE_NAME.fullmatch(member.trace_name)
        if not match:
            raise SteadFormatError("trace_name is not the reviewed STEAD bucket slice")
        bucket, index_text = match.groups()
        if bucket not in self._handle["data"]:
            raise SteadFormatError(f"HDF5 bucket is missing: {bucket}")
        block = self._handle["data"][bucket]
        index = int(index_text)
        if (not isinstance(block, h5py.Dataset) or len(block.shape) != 3
                or block.shape[1] < 3 or block.shape[2] < 6000 or index >= block.shape[0]):
            raise SteadFormatError("HDF5 bucket shape or trace index is invalid")
        zne = np.asarray(block[index, :3, :6000], dtype=np.float32)
        if zne.shape != (3, 6000) or not np.all(np.isfinite(zne)):
            raise SteadFormatError("HDF5 trace contains missing/nonfinite samples")
        values = np.ascontiguousarray(zne[[2, 1, 0]].T)
        if np.any(np.ptp(values, axis=0) <= 0):
            raise SteadFormatError("HDF5 trace has a flat component; not three measured channels")
        return SteadWaveform(member, values)


def normalize_counts(values: np.ndarray) -> tuple[np.ndarray, dict[str, list[float]]]:
    """Label-independent, single-trace normalization, identical for browser input."""
    if values.shape != (6000, 3) or not np.all(np.isfinite(values)):
        raise SteadFormatError("normalization expects finite [6000,E/N/Z] counts")
    means = np.mean(values, axis=0, dtype=np.float64)
    centered = values.astype(np.float32) - means.astype(np.float32)
    peaks = np.max(np.abs(centered), axis=0)
    if np.any(peaks <= 0):
        raise SteadFormatError("cannot normalize flat channel")
    normalized = centered / peaks
    return np.ascontiguousarray(normalized), {
        "component_order": ["E", "N", "Z"],
        "mean_counts": means.astype(float).tolist(),
        "peak_centered_counts": peaks.astype(float).tolist(),
    }
