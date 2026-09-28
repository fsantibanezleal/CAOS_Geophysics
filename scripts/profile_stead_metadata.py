"""Stream a verified STEAD/SeisBench metadata mirror and audit split leakage.

No waveform data are downloaded or claimed by this script. The original
STEAD repo declares CC BY 4.0; this local metadata file is kept in ignored
raw storage. The aggregate report is safe to publish with source attribution.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path


SOURCE_URL = "https://seisbench.gfz-potsdam.de/mirror/datasets/stead/metadata.csv"
SOURCE_SHA256 = "9b9007406ebfef8c182060c8bb4266d29bbc433985f91f7e2dc476c8aca08efe"
SOURCE_BYTES = 402_560_190
SALT = "caos-stead-station-event-v1"
PARTITIONS = ("train", "dev", "test")
BIT = {"train": 1, "dev": 2, "test": 4}


def hash_partition(kind: str, identifier: str) -> str:
    digest = hashlib.sha256(f"{SALT}|{kind}|{identifier}".encode()).digest()
    value = int.from_bytes(digest[:8], "big") / 2**64
    return "train" if value < 0.70 else "dev" if value < 0.85 else "test"


def valid_index(text: str) -> int | None:
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0 or int(number) != number:
        return None
    return int(number)


def profile(path: Path) -> dict:
    if path.stat().st_size != SOURCE_BYTES:
        raise ValueError("STEAD metadata byte count does not match pinned mirror")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != SOURCE_SHA256:
        raise ValueError("STEAD metadata SHA-256 does not match pinned mirror")

    categories: Counter[str] = Counter()
    published_split: Counter[str] = Counter()
    eligible_p_s = 0
    missing_p = missing_s = invalid_order = 0
    proposed: Counter[str] = Counter()
    quarantine_mismatch = 0
    event_masks: dict[str, int] = {}
    station_masks: dict[str, int] = {}
    event_partitions: dict[str, str] = {}
    station_partitions: dict[str, str] = {}
    unique_trace_names: set[str] = set()
    duplicate_trace_names = 0

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "station_network_code", "station_code", "source_id", "trace_category",
            "trace_p_arrival_sample", "trace_s_arrival_sample", "trace_name_original", "split",
        }
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError("STEAD metadata schema lacks required fields")
        for row in reader:
            category = row["trace_category"] or "missing"
            categories[category] += 1
            old = row["split"] or "missing"
            published_split[old] += 1
            trace_name = row["trace_name_original"]
            if trace_name in unique_trace_names:
                duplicate_trace_names += 1
            else:
                unique_trace_names.add(trace_name)
            if category != "earthquake_local":
                continue
            p = valid_index(row["trace_p_arrival_sample"])
            s = valid_index(row["trace_s_arrival_sample"])
            if p is None:
                missing_p += 1
            if s is None:
                missing_s += 1
            if p is None or s is None:
                continue
            if p >= s or s >= 6000:
                invalid_order += 1
                continue
            event = row["source_id"]
            station = f"{row['station_network_code']}.{row['station_code']}"
            if not event or not station or "." not in station or station.startswith(".") or station.endswith("."):
                continue
            eligible_p_s += 1
            if old in BIT:
                event_masks[event] = event_masks.get(event, 0) | BIT[old]
                station_masks[station] = station_masks.get(station, 0) | BIT[old]
            ep = event_partitions.setdefault(event, hash_partition("event", event))
            sp = station_partitions.setdefault(station, hash_partition("station", station))
            if ep == sp:
                proposed[ep] += 1
            else:
                quarantine_mismatch += 1
    leaked_events = sum(mask.bit_count() > 1 for mask in event_masks.values())
    leaked_stations = sum(mask.bit_count() > 1 for mask in station_masks.values())
    return {
        "schema": "caos.stead-metadata-profile.v1",
        "source": {
            "url": SOURCE_URL,
            "bytes": SOURCE_BYTES,
            "sha256": SOURCE_SHA256,
            "upstream_dataset": "STEAD, Mousavi et al. 2019, DOI 10.1109/ACCESS.2019.2947848",
            "upstream_license": "CC BY 4.0, as declared by the original STEAD repository",
            "waveforms_downloaded_by_this_receipt": False,
        },
        "rows": {
            "total": sum(categories.values()),
            "categories": dict(sorted(categories.items())),
            "published_split": dict(sorted(published_split.items())),
            "duplicate_original_trace_names": duplicate_trace_names,
            "earthquake_eligible_p_before_s": eligible_p_s,
            "earthquake_missing_p": missing_p,
            "earthquake_missing_s": missing_s,
            "earthquake_invalid_order_or_range": invalid_order,
        },
        "published_split_leakage_on_eligible_earthquakes": {
            "unique_events": len(event_masks),
            "events_in_multiple_partitions": leaked_events,
            "unique_stations": len(station_masks),
            "stations_in_multiple_partitions": leaked_stations,
            "interpretation": "Published trace-level split is not accepted as event/station independent.",
        },
        "proposed_joint_hash_split": {
            "salt": SALT,
            "method": "independent deterministic event and station hashes; keep a trace only when their partitions match",
            "eligible_counts": {key: proposed[key] for key in PARTITIONS},
            "cross_partition_event_station_traces_quarantined": quarantine_mismatch,
            "event_and_station_disjoint_by_construction": True,
            "caution": "This is metadata planning only; waveform bytes, QC and model generalization are not yet evaluated.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = profile(args.metadata)
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
