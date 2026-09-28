"""Attributable field-trace import and leakage-safe phase-picking evaluation.

This module does not make the 100-trace PhaseNet test archive a trained benchmark.
It supplies strict input, split and same-input evaluation contracts for M08/M13.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import io
import math
from pathlib import Path, PurePosixPath
import zipfile

import numpy as np


class ArchiveError(ValueError):
    """Unsafe archive or scientifically ineligible trace."""


@dataclass(frozen=True, eq=False)
class PhaseTrace:
    trace_id: str
    event_id: str
    station_id: str
    source_sha256: str
    values: np.ndarray  # [sample, E/N/Z slots]; absent channels are masked
    sample_interval_s: float
    unit: str
    channels: tuple[str, ...]
    component_present: tuple[bool, bool, bool]
    p_index: int
    s_index: int

    @property
    def labels_s(self) -> dict[str, float]:
        return {"P": self.p_index * self.sample_interval_s, "S": self.s_index * self.sample_interval_s}


@dataclass(frozen=True)
class TraceSplit:
    members: dict[str, tuple[str, ...]]
    partition_of: dict[str, str]
    source_member_sha256: str
    partition_sha256: dict[str, str]
    salt: str


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_members(entries: list[zipfile.ZipInfo], *, max_entries: int, max_uncompressed: int) -> None:
    if len(entries) > max_entries:
        raise ArchiveError("archive entry count exceeds limit")
    names: set[str] = set()
    total = 0
    for entry in entries:
        name = entry.filename
        path = PurePosixPath(name)
        drive_prefixed = bool(path.parts and len(path.parts[0]) >= 2 and path.parts[0][1] == ":")
        if not name or "\\" in name or path.is_absolute() or drive_prefixed or ".." in path.parts:
            raise ArchiveError(f"unsafe archive path: {name!r}")
        if name in names:
            raise ArchiveError(f"duplicate archive entry: {name!r}")
        names.add(name)
        total += entry.file_size
        if total > max_uncompressed:
            raise ArchiveError("archive uncompressed size exceeds limit")
        if entry.file_size > 100 * max(1, entry.compress_size):
            raise ArchiveError(f"archive entry expansion ratio exceeds limit: {name!r}")


def _scalar(record: np.lib.npyio.NpzFile, key: str) -> object:
    if key not in record:
        raise ArchiveError(f"missing trace field: {key}")
    value = record[key]
    if value.ndim != 0:
        raise ArchiveError(f"trace field is not scalar: {key}")
    return value.item()


def _component_contract(values: np.ndarray, channel_text: str) -> tuple[tuple[str, ...], tuple[bool, bool, bool]]:
    channels = tuple(channel_text.split(","))
    if not channels or any(not channel for channel in channels):
        raise ArchiveError("missing channel description")
    slots = [channel[-1].upper() for channel in channels]
    if any(slot not in "ENZ" for slot in slots) or len(slots) != len(set(slots)):
        raise ArchiveError("ambiguous channel orientation; E/N/Z required")
    if slots != sorted(slots, key="ENZ".index):
        raise ArchiveError("channel order is not E/N/Z")
    present = tuple(slot in slots for slot in "ENZ")
    for index, measured in enumerate(present):
        if not measured and np.any(values[:, index] != 0):
            raise ArchiveError("unmeasured component has nonzero samples")
    return channels, present


def _read_npz_member(raw: bytes, row: dict[str, str], source_sha256: str) -> PhaseTrace:
    # A .npz is itself a ZIP. Bound its expansion before NumPy allocates arrays.
    with zipfile.ZipFile(io.BytesIO(raw)) as nested:
        _check_members(nested.infolist(), max_entries=40, max_uncompressed=32 * 1024 * 1024)
    try:
        with np.load(io.BytesIO(raw), allow_pickle=False) as record:
            values = np.asarray(record["data"])
            if values.ndim != 2 or values.shape[1] != 3 or not 32 <= values.shape[0] <= 100_000:
                raise ArchiveError("trace shape must be [32..100000, 3]")
            if values.dtype.kind != "f" or not np.all(np.isfinite(values)):
                raise ArchiveError("trace values must be finite floating point")
            values = values.astype(np.float32, copy=True)
            dt = float(_scalar(record, "dt"))
            if not math.isfinite(dt) or not 0 < dt <= 1:
                raise ArchiveError("invalid sample interval")
            if not math.isclose(dt, float(row["dt"]), rel_tol=1e-8, abs_tol=1e-10):
                raise ArchiveError("sample interval differs from catalogue")
            p_index = int(_scalar(record, "p_idx"))
            s_index = int(_scalar(record, "s_idx"))
            if (p_index != int(row["p_idx"]) or s_index != int(row["s_idx"])
                    or not 0 <= p_index < s_index < len(values)):
                raise ArchiveError("invalid or conflicting P/S pick indices")
            unit = str(_scalar(record, "unit"))
            if unit not in {"m/s", "m/s**2"} or unit != row["unit"]:
                raise ArchiveError("invalid or conflicting physical unit")
            channel_text = str(_scalar(record, "channels"))
            if channel_text != row["channels"]:
                raise ArchiveError("channel metadata conflict")
            channels, component_present = _component_contract(values, channel_text)
            network = str(_scalar(record, "network"))
            station = str(_scalar(record, "station"))
            event_index = str(_scalar(record, "event_index"))
            if (network != row["network"] or station != row["station"]
                    or event_index != str(row["event_index"])):
                raise ArchiveError("event/station metadata conflict")
            trace_id = row["fname"].removesuffix(".npz")
            return PhaseTrace(
                trace_id=trace_id,
                event_id=event_index,
                station_id=f"{network}.{station}",
                source_sha256=source_sha256,
                values=values,
                sample_interval_s=dt,
                unit=unit,
                channels=channels,
                component_present=component_present,
                p_index=p_index,
                s_index=s_index,
            )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, ArchiveError):
            raise
        raise ArchiveError(f"invalid NPZ trace: {exc}") from exc


def load_phase_archive(
    path: str | Path,
    *,
    expected_sha256: str,
    max_archive_bytes: int = 100 * 1024 * 1024,
    max_entries: int = 1500,
    max_uncompressed: int = 256 * 1024 * 1024,
    reject_ambiguous: bool = True,
) -> list[PhaseTrace]:
    """Load the official PhaseNet NPZ sample only after its exact receipt.

    Ambiguous component orientation can be quarantined by setting
    `reject_ambiguous=False`; such traces are excluded rather than guessed.
    """
    source = Path(path)
    if source.stat().st_size > max_archive_bytes:
        raise ArchiveError("archive byte count exceeds limit")
    digest = _sha256_file(source)
    if digest.lower() != expected_sha256.lower():
        raise ArchiveError("source SHA-256 mismatch")
    try:
        with zipfile.ZipFile(source) as archive:
            _check_members(archive.infolist(), max_entries=max_entries, max_uncompressed=max_uncompressed)
            with archive.open("test_data/npz.csv") as handle:
                text = io.TextIOWrapper(handle, encoding="utf-8-sig", newline="")
                rows = list(csv.DictReader(text, delimiter="\t"))
            if not rows or len(rows) > max_entries:
                raise ArchiveError("missing or excessive trace catalogue rows")
            required = {"fname", "network", "station", "p_idx", "s_idx", "dt", "unit", "event_index", "channels"}
            if any(not required.issubset(row) for row in rows):
                raise ArchiveError("trace catalogue lacks required fields")
            traces: list[PhaseTrace] = []
            seen: set[str] = set()
            for row in rows:
                name = row["fname"]
                if not name or Path(name).name != name or not name.endswith(".npz") or name in seen:
                    raise ArchiveError("unsafe or duplicate trace filename")
                seen.add(name)
                member = f"test_data/npz/{name}"
                try:
                    raw = archive.read(member)
                except KeyError as exc:
                    raise ArchiveError(f"missing trace archive entry: {member}") from exc
                try:
                    traces.append(_read_npz_member(raw, row, digest))
                except ArchiveError as exc:
                    if not reject_ambiguous and "ambiguous channel orientation" in str(exc):
                        continue
                    raise
            if not traces:
                raise ArchiveError("no eligible traces")
            return traces
    except (zipfile.BadZipFile, UnicodeError) as exc:
        raise ArchiveError(f"invalid archive: {exc}") from exc


def split_by_event_and_station(traces: list[PhaseTrace], *, salt: str) -> TraceSplit:
    """Hash connected event/station groups, so neither can cross partitions."""
    if len({trace.trace_id for trace in traces}) != len(traces):
        raise ValueError("duplicate trace ID")
    parent = list(range(len(traces)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(a: int, b: int) -> None:
        parent[find(a)] = find(b)

    events: dict[str, int] = {}
    stations: dict[str, int] = {}
    for index, trace in enumerate(traces):
        if trace.event_id in events:
            union(index, events[trace.event_id])
        else:
            events[trace.event_id] = index
        if trace.station_id in stations:
            union(index, stations[trace.station_id])
        else:
            stations[trace.station_id] = index
    components: dict[int, list[PhaseTrace]] = {}
    for index, trace in enumerate(traces):
        components.setdefault(find(index), []).append(trace)
    members: dict[str, list[str]] = {"train": [], "dev": [], "test": []}
    for group in components.values():
        anchors = sorted({f"E:{trace.event_id}" for trace in group} | {f"S:{trace.station_id}" for trace in group})
        key = hashlib.sha256((salt + "|" + "|".join(anchors)).encode()).digest()
        fraction = int.from_bytes(key[:8], "big") / 2**64
        partition = "train" if fraction < 0.70 else "dev" if fraction < 0.85 else "test"
        members[partition].extend(trace.trace_id for trace in group)
    normalized = {key: tuple(sorted(value)) for key, value in members.items()}
    if any(not value for value in normalized.values()):
        raise ValueError("event/station groups do not populate train, dev and test")
    partition_of = {trace_id: partition for partition, ids in normalized.items() for trace_id in ids}
    member_digest = hashlib.sha256("\n".join(sorted(partition_of)).encode()).hexdigest()
    partition_digest = {
        partition: hashlib.sha256("\n".join(ids).encode()).hexdigest() for partition, ids in normalized.items()
    }
    return TraceSplit(normalized, partition_of, member_digest, partition_digest, salt)


def normalized_window(
    trace: PhaseTrace, *, start_sample: int, sample_count: int = 4096
) -> tuple[np.ndarray, dict[str, float]]:
    """Return [E,N,Z] float32 values with explicit per-component scale.

    The normalization is trace-local and executable identically at inference;
    it does not fit a cross-split statistic. The physical unit is retained on
    PhaseTrace and the scale factors are part of the derived-data provenance.
    """
    if start_sample < 0 or sample_count < 32 or start_sample + sample_count > len(trace.values):
        raise ValueError("window is outside source trace")
    values = trace.values[start_sample : start_sample + sample_count].copy()
    if not np.all(np.isfinite(values)):
        raise ValueError("nonfinite waveform window")
    scale: dict[str, float] = {}
    for axis, present in enumerate(trace.component_present):
        key = "ENZ"[axis]
        if not present:
            values[:, axis] = 0
            scale[key] = 0.0
            continue
        signal = values[:, axis]
        signal -= np.mean(signal[: max(32, min(256, sample_count // 8))])
        peak = float(np.max(np.abs(signal)))
        if peak <= 0:
            raise ValueError("measured component has zero amplitude")
        values[:, axis] = signal / peak
        scale[key] = peak
    return values, scale


def classical_stalta_picks(
    values: np.ndarray,
    *,
    sample_interval_s: float,
    threshold: float = 2.5,
    sta_s: float = 0.12,
    lta_s: float = 1.2,
    minimum_ps_s: float = 0.4,
) -> dict[str, float | None]:
    """Fixed-parameter classical M08 baseline; no analyst label is consulted.

    This is an onset detector, not a phase classifier: the second trigger is
    provisionally named S and may be wrong. Its failures remain in evaluation.
    """
    if values.ndim != 2 or values.shape[1] != 3 or not np.all(np.isfinite(values)):
        raise ValueError("expected finite [sample, component] waveform")
    if not math.isfinite(sample_interval_s) or sample_interval_s <= 0:
        raise ValueError("invalid sample interval")
    short = max(2, round(sta_s / sample_interval_s))
    long = max(short + 1, round(lta_s / sample_interval_s))
    if len(values) < 3 * long:
        raise ValueError("window too short for STA/LTA")
    energy = np.sum(np.square(values.astype(np.float64)), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(energy)))
    sta = (cumulative[short:] - cumulative[:-short]) / short
    lta = (cumulative[long:] - cumulative[:-long]) / long
    characteristic = np.zeros(len(values))
    characteristic[long - 1 :] = sta[long - short :] / np.maximum(lta, 1e-12)
    # Require an actual upward crossing. A max selected from a known label
    # neighbourhood would leak the reference onset into the comparator.
    crossings = np.flatnonzero((characteristic[1:] >= threshold) & (characteristic[:-1] < threshold)) + 1
    if not len(crossings):
        return {"P": None, "S": None}
    p_index = int(crossings[0])
    s_candidates = crossings[crossings >= p_index + round(minimum_ps_s / sample_interval_s)]
    s_index = int(s_candidates[0]) if len(s_candidates) else None
    return {
        "P": p_index * sample_interval_s,
        "S": s_index * sample_interval_s if s_index is not None else None,
    }


def evaluate_matched_picks(
    labels: dict[str, dict[str, float | None]],
    predictions: dict[str, dict[str, dict[str, float | None]]],
    *,
    tolerance_s: float,
) -> dict[str, dict[str, dict[str, object]]]:
    """Evaluate all models over the exact same labelled trace IDs."""
    if tolerance_s <= 0 or not math.isfinite(tolerance_s):
        raise ValueError("tolerance_s must be positive")
    expected_ids = set(labels)
    if any(set(model) != expected_ids for model in predictions.values()):
        raise ValueError("models must use identical labelled trace IDs")
    result: dict[str, dict[str, dict[str, object]]] = {}
    for method, model in predictions.items():
        result[method] = {}
        for phase in ("P", "S"):
            truth_count = missed = false = correct = outside = 0
            signed: list[float] = []
            for trace_id, label in labels.items():
                truth = label.get(phase)
                pick = model[trace_id].get(phase)
                if truth is None:
                    false += int(pick is not None)
                    continue
                truth_count += 1
                if pick is None:
                    missed += 1
                    continue
                if not math.isfinite(truth) or not math.isfinite(pick):
                    raise ValueError("pick times must be finite")
                residual = float(pick - truth)
                signed.append(residual)
                if abs(residual) <= tolerance_s + 1e-12:
                    correct += 1
                else:
                    outside += 1
            result[method][phase] = {
                "total": truth_count,
                "correct_within_tolerance": correct,
                "missed": missed,
                "outside_tolerance": outside,
                "false_without_reference": false,
                "recall": correct / truth_count if truth_count else None,
                "timing_signed_s": signed,
                "timing_absolute_s": [abs(value) for value in signed],
            }
    return result
