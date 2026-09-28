"""Publish only aggregate train/dev pick-position structure before training.

Test member statistics and waveform bytes are not inspected. This check guards
against learning STEAD's constructed window clock rather than a phase onset.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from extract_stead_phase import _members  # noqa: E402
from stead_phase import file_sha256  # noqa: E402


QUANTILES = (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)


def profile(manifest: Path) -> dict:
    partitions = {}
    for partition in ("train", "dev"):
        members, selection_sha256 = _members(manifest, partition)
        quake = [member for member in members if member.p_index is not None]
        if not quake or any(member.s_index is None for member in quake):
            raise ValueError("selected train/dev inventory lacks paired earthquake picks")
        p = np.asarray([member.p_index for member in quake], dtype=np.int32)
        s = np.asarray([member.s_index for member in quake], dtype=np.int32)
        partitions[partition] = {
            "selected_count": len(members),
            "earthquake_count": len(quake),
            "noise_count": len(members) - len(quake),
            "selection_sha256": selection_sha256,
            "quantile_probabilities": list(QUANTILES),
            "P_sample_quantiles": np.quantile(p, QUANTILES).tolist(),
            "S_sample_quantiles": np.quantile(s, QUANTILES).tolist(),
            "P_between_400_and_1000_fraction": float(np.mean((p >= 400) & (p <= 1000))),
            "P_between_400_and_1000_inclusive_count": int(np.sum((p >= 400) & (p <= 1000))),
        }
    return {
        "schema": "caos.stead-train-dev-pick-position.v1",
        "source": "STEAD metadata via SeisBench mirror",
        "selection_manifest_sha256": file_sha256(manifest),
        "sample_rate_hz": 100,
        "test_member_statistics_computed": False,
        "test_waveforms_opened": False,
        "interpretation": (
            "The selected train/dev P clock is a constructed-window prior. A learned picker "
            "must beat an input-free position baseline and survive predeclared time translation."
        ),
        "partitions": partitions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/raw/phase/stead-selection.json")
    parser.add_argument("--report", type=Path,
                        default=ROOT / "data/derived/phase/stead-pick-position-profile.json")
    args = parser.parse_args()
    report_path = args.report.resolve()
    if (not report_path.is_relative_to((ROOT / "data/derived/phase").resolve())
            or report_path.exists()):
        raise ValueError("aggregate report must be a new file under data/derived/phase")
    result = profile(args.manifest)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
