"""Replay an immutable v1.1 M12 receipt with float-safe calibration checks.

The original verifier compares a mapping of recomputed floating-point
candidate scores by exact equality. This wrapper preserves the hash-bound
scientific sources and relaxes only that comparison to a tight tolerance.
Selected lambda, source hashes, checkpoint, manifests, alpha, calibration
metrics, held-out metrics, and final status remain checked by the original
verifier.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

import velocity_nullspace_refinement_v11 as study  # noqa: E402
import velocity_validation as physics  # noqa: E402

RTOL = 1e-10
ATOL = 1e-12


class _ReplayScores(dict):
    """Mapping equality with tight float tolerance for candidate metrics."""

    def __eq__(self, other):
        if not isinstance(other, dict) or self.keys() != other.keys():
            return False
        return all(
            np.isclose(float(self[key]), float(other[key]), rtol=RTOL, atol=ATOL)
            for key in self
        )

    def __ne__(self, other):
        return not self.__eq__(other)


def _script_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def verify_compat(output: Path) -> dict:
    """Run the original full replay while tolerating score serialization noise."""
    original_selector = physics.select_classical

    def select_with_float_safe_scores(calibration, operators):
        selected, scores = original_selector(calibration, operators)
        return selected, _ReplayScores(scores)

    physics.select_classical = select_with_float_safe_scores
    try:
        result = study.verify(output)
    finally:
        physics.select_classical = original_selector
    receipt_path = Path(output) / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return {
        "verification": "compatibility-replay-passed",
        "replay": result,
        "receipt_status": receipt["status"],
        "scientific_acceptance": receipt["scientific_acceptance"],
        "selected_lambda": receipt["classical"]["selected_lambda"],
        "selected_alpha": receipt["refinement"]["alpha_selection"]["selected_alpha"],
        "calibration_score_rtol": RTOL,
        "calibration_score_atol": ATOL,
        "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "compatibility_verifier_sha256": _script_sha256(),
        "original_bound_sources_verified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if any((parent / ".git").exists() for parent in (output, *output.parents)):
        parser.error("--output must identify a retained external research run")
    print(json.dumps(verify_compat(output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
