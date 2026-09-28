"""Reproducible *pilot* audit of the upstream PhaseNet test-data archive.

This does not train or evaluate M13. It validates ingestion, station/event
splitting and the fixed M08 classical comparator on attributable field traces.
The source archive remains ignored and private pending a rights decision.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import statistics

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline"))
from phase_picking import (  # noqa: E402
    classical_stalta_picks,
    evaluate_matched_picks,
    load_phase_archive,
    normalized_window,
    split_by_event_and_station,
)


SOURCE_SHA256 = "60476821a71697ded05884c225c75ae7e0099bd9a7b79c4e2bdc9e7b3a5706b3"
SOURCE_URL = "https://github.com/AI4EPS/PhaseNet/releases/download/test_data/test_data.zip"
SALT = "phasenet-fixture-v1"
WINDOW_START = 4096
WINDOW_SAMPLES = 4096


def summarize_phase(phase: dict) -> dict:
    signed = phase["timing_signed_s"]
    absolute = phase["timing_absolute_s"]
    return {
        key: phase[key] for key in (
            "total", "correct_within_tolerance", "missed", "outside_tolerance",
            "false_without_reference", "recall",
        )
    } | {
        "picked_count": len(signed),
        "median_absolute_error_s": statistics.median(absolute) if absolute else None,
        "mean_signed_error_s": statistics.mean(signed) if signed else None,
    }


def audit(source: Path) -> dict:
    traces = load_phase_archive(source, expected_sha256=SOURCE_SHA256, reject_ambiguous=False)
    split = split_by_event_and_station(traces, salt=SALT)
    records = {trace.trace_id: trace for trace in traces}
    partitions = {}
    for name, ids in split.members.items():
        labels = {}
        classical = {}
        units = {"m/s": 0, "m/s**2": 0}
        for trace_id in ids:
            trace = records[trace_id]
            if trace.sample_interval_s != 0.01:
                raise ValueError("the pinned fixture window requires exactly 100 Hz")
            values, _ = normalized_window(trace, start_sample=WINDOW_START, sample_count=WINDOW_SAMPLES)
            offset_s = WINDOW_START * trace.sample_interval_s
            labels[trace_id] = {phase: time_s - offset_s for phase, time_s in trace.labels_s.items()}
            classical[trace_id] = classical_stalta_picks(
                values, sample_interval_s=trace.sample_interval_s, threshold=2.5,
            )
            units[trace.unit] += 1
        evaluated = evaluate_matched_picks(
            labels, {"M08": classical}, tolerance_s=0.5
        )["M08"]
        partitions[name] = {
            "trace_count": len(ids),
            "unit_counts": units,
            "M08_classical": {phase: summarize_phase(evaluated[phase]) for phase in ("P", "S")},
        }
    return {
        "schema": "caos.phase-fixture-audit.v1",
        "classification": "exploratory engineering-pilot; test partition inspected; not M13 acceptance or field generalization",
        "source": {
            "url": SOURCE_URL,
            "sha256": SOURCE_SHA256,
            "bytes": source.stat().st_size,
            "raw_redistribution": "not authorized by this receipt; provider-link-only",
            "catalogue_trace_count": 100,
            "eligible_unambiguous_trace_count": len(traces),
            "quarantined_orientation_count": 100 - len(traces),
        },
        "split": {
            "salt": SALT,
            "member_sha256": split.source_member_sha256,
            "partition_sha256": split.partition_sha256,
            "partition_counts": {name: len(ids) for name, ids in split.members.items()},
            "station_and_event_disjoint": True,
        },
        "window": {"start_sample": WINDOW_START, "samples": WINDOW_SAMPLES, "sample_interval_s": 0.01},
        "classical": {
            "definition": "first and second 2.5-threshold STA/LTA upward crossings; 0.12 s STA, 1.2 s LTA, 0.4 s minimum P-S spacing",
            "phase_tolerance_s": 0.5,
            "reference": "analyst labels contained in upstream NPZ/CSV; not geological ground truth",
            "partitions": partitions,
        },
        "limitations": [
            "Only 100 upstream fixture traces; 7 have ambiguous component orientation and are quarantined.",
            "The second classical trigger is a provisional S assignment, not a phase classifier.",
            "No PhaseNet-family model is trained or evaluated by this receipt.",
            "Rights for republishing raw waveforms or derived model weights remain unresolved.",
            "All partitions were read during this pilot; they cannot be treated as a fresh untouched final test.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Write a deterministic JSON receipt")
    args = parser.parse_args()
    report = audit(args.archive)
    content = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
