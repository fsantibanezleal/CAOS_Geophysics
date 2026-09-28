"""Build the metadata-only, station/event-independent M13 training inventory.

Raw trace IDs and bucket addresses are local-only in the ignored manifest.
The aggregate report can be committed. No waveform bytes are opened here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from stead_phase import select_metadata, serializable_members  # noqa: E402


CAPS = {
    "train": {"earthquake_local": 60_000, "noise": 5_000},
    "dev": {"earthquake_local": 5_000, "noise": 1_000},
    "test": {"earthquake_local": 5_000, "noise": 1_000},
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/raw/phase/stead-selection.json")
    parser.add_argument("--report", type=Path, default=ROOT / "data/derived/phase/stead-selection-profile.json")
    args = parser.parse_args()
    selected, report = select_metadata(args.metadata, caps=CAPS)
    if not args.manifest.resolve().is_relative_to((ROOT / "data/raw").resolve()):
        raise ValueError("trace-identity manifest must stay in ignored data/raw/")
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps({"schema": "caos.stead-phase-members.v1",
                                         "report": report, "members": serializable_members(selected)},
                                        sort_keys=True) + "\n", encoding="utf-8")
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(args.manifest), "report": str(args.report),
                      "selected": report["selected"], "reasons": report["reasons"]}, indent=2))


if __name__ == "__main__":
    main()
