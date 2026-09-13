"""Standard compact JSON and CSV helpers used by the release bake."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_json(path: str | Path, obj: Any) -> int:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    target.write_bytes(encoded)
    return len(encoded)


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
