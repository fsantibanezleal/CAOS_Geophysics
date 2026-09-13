from __future__ import annotations

from ..io.contract import validate_observations


def run(rows: list[dict]) -> dict:
    return validate_observations(rows)
