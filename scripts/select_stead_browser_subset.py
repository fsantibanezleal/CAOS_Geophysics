"""Lock a diverse metadata-only test display subset before held-out scoring.

The full predeclared 6000-trace test cohort, not this 24-trace display subset,
defines accuracy. This selector reads no waveform samples or model predictions.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELECTION_SALT = "caos-phase-browser-v1"
QUAKE_NETWORKS = ("PB", "NC", "CI", "BK", "AZ", "AV", "GS", "AK")
NOISE_NETWORKS = ("NC", "AV", "CI", "PB")
PER_NETWORK = 2


def select(manifest: Path, private_path: Path, public_path: Path) -> dict:
    from extract_stead_phase import _members

    if (not private_path.resolve().is_relative_to((ROOT / "data/raw").resolve())
            or not public_path.resolve().is_relative_to((ROOT / "data/derived/phase").resolve())
            or private_path.exists() or public_path.exists()
            or private_path.is_symlink() or public_path.is_symlink()):
        raise ValueError("browser subset requires new private/public receipt paths")
    if (ROOT / "data/derived/phase/stead-heldout-benchmark.json").exists():
        raise ValueError("display subset must be fixed before held-out scoring")
    members, test_selection_hash = _members(manifest, "test")
    chosen = []
    for category, networks in (("earthquake_local", QUAKE_NETWORKS),
                               ("noise", NOISE_NETWORKS)):
        for network in networks:
            candidates = [member for member in members
                          if member.category == category
                          and member.station_id.split(".", 1)[0] == network]
            if len(candidates) < PER_NETWORK:
                raise ValueError(f"test inventory lacks {category}/{network} display members")
            candidates.sort(key=lambda member: hashlib.sha256(
                f"{SELECTION_SALT}|{category}|{network}|{member.trace_id}".encode()
            ).digest())
            chosen.extend(candidates[:PER_NETWORK])
    identifiers = sorted(member.trace_id for member in chosen)
    if len(identifiers) != 24 or len(set(identifiers)) != len(identifiers):
        raise ValueError("browser display selection duplicated a trace")
    digest = hashlib.sha256("\n".join(identifiers).encode()).hexdigest()
    private = {
        "schema": "caos.stead-browser-members.v1",
        "test_selection_sha256": test_selection_hash,
        "display_ids_sha256": digest,
        "selection_salt": SELECTION_SALT,
        "members": [member.__dict__ for member in chosen],
        "waveform_values_used_to_select": False,
        "model_predictions_used_to_select": False,
    }
    public = {
        "schema": "caos.stead-browser-selection-profile.v1",
        "test_selection_sha256": test_selection_hash,
        "display_ids_sha256": digest,
        "selection_salt": SELECTION_SALT,
        "earthquake_networks": list(QUAKE_NETWORKS),
        "noise_networks": list(NOISE_NETWORKS),
        "per_network": PER_NETWORK,
        "earthquake_count": len(QUAKE_NETWORKS) * PER_NETWORK,
        "noise_count": len(NOISE_NETWORKS) * PER_NETWORK,
        "purpose": "predeclared browser display and numerical parity; all 6000 selected test traces define accuracy",
        "chosen_using_trace_metadata_only": True,
        "test_performance_known_when_selected": False,
        "contains_trace_ids_or_waveform_samples": False,
    }
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_text(json.dumps(private, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    public_path.write_text(json.dumps(public, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return public


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path,
                        default=ROOT / "data/raw/phase/stead-selection.json")
    parser.add_argument("--private", type=Path,
                        default=ROOT / "data/raw/phase/stead-browser-selection.json")
    parser.add_argument("--public", type=Path,
                        default=ROOT / "data/derived/phase/stead-browser-selection-profile.json")
    args = parser.parse_args()
    print(json.dumps(select(args.manifest, args.private, args.public), indent=2))


if __name__ == "__main__":
    main()
