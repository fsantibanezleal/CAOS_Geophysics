"""No event or station may leak between training, development and test."""

from dataclasses import replace

import numpy as np

from phase_picking import PhaseTrace, split_by_event_and_station


def trace(event, station, suffix):
    return PhaseTrace(
        trace_id=suffix, event_id=event, station_id=station, source_sha256="a" * 64,
        values=np.zeros((512, 3), dtype=np.float32), sample_interval_s=0.01,
        unit="m/s", channels=("HHE", "HHN", "HHZ"),
        component_present=(True, True, True), p_index=120, s_index=180,
    )


def test_disjoint_station_event_and_reproducible_hash():
    records = [trace(f"E{i}", f"S{i}", f"T{i}") for i in range(30)]
    records += [replace(records[0], trace_id="same-event-different-station", station_id="S-new")]
    records += [replace(records[1], trace_id="same-station-different-event", event_id="E-new")]
    first = split_by_event_and_station(records, salt="phase-test-v1")
    second = split_by_event_and_station(list(reversed(records)), salt="phase-test-v1")
    assert first == second
    assert all(first.members[k] for k in ("train", "dev", "test"))
    by_id = {r.trace_id: r for r in records}
    for a in ("train", "dev", "test"):
        for b in ("train", "dev", "test"):
            if a >= b:
                continue
            aa = [by_id[k] for k in first.members[a]]
            bb = [by_id[k] for k in first.members[b]]
            assert not {r.event_id for r in aa} & {r.event_id for r in bb}
            assert not {r.station_id for r in aa} & {r.station_id for r in bb}
    assert first.partition_of["T0"] == first.partition_of["same-event-different-station"]
    assert first.partition_of["T1"] == first.partition_of["same-station-different-event"]
