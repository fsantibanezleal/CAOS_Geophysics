"""Contract 1: raw observations to validated processing records."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .schema import ObservationContract

REQUIRED_FIELDS = ("station_id", "x_m", "y_m", "frequency_hz", "value", "unit")
UNITS = {"gravity_mgal", "magnetic_nT", "ohm_m", "phase_deg", "trace_amplitude"}


def validate_observations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        missing = [name for name in REQUIRED_FIELDS if name not in row]
        if missing:
            rejected.append({"row": index, "reason": f"missing fields: {missing}"})
            continue
        try:
            record = ObservationContract(
                station_id=str(row["station_id"]),
                x_m=float(row["x_m"]),
                y_m=float(row["y_m"]),
                frequency_hz=float(row["frequency_hz"]),
                value=float(row["value"]),
                unit=str(row["unit"]),
            )
        except (TypeError, ValueError) as exc:
            rejected.append({"row": index, "reason": f"not numeric: {exc}"})
            continue
        values = (record.x_m, record.y_m, record.frequency_hz, record.value)
        if any(not value == value for value in values):
            rejected.append({"row": index, "reason": "NaN is not accepted"})
        elif record.frequency_hz <= 0:
            rejected.append({"row": index, "reason": "frequency_hz must be positive"})
        elif record.unit not in UNITS:
            rejected.append({"row": index, "reason": f"unit must be one of {sorted(UNITS)}"})
        elif abs(record.value) > 1e9:
            flagged.append({"row": index, "reason": "extreme value retained for review"})
            accepted.append(asdict(record))
        else:
            accepted.append(asdict(record))
    return {"accepted": accepted, "rejected": rejected, "flagged": flagged, "n_rows": len(rows)}
