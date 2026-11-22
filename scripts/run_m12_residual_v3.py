"""Run or independently replay the predeclared M12 residual study."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "data-pipeline"
sys.path.insert(0, str(PIPELINE))

import velocity_residual_learning as study  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if not output.is_absolute() or output == ROOT or ROOT in output.parents:
        parser.error("--output must be a new directory outside the repository checkout")
    if args.verify:
        print(json.dumps(study.verify(output), sort_keys=True))
        return 0
    receipt = study.execute(output, device=args.device)
    print(json.dumps({key: receipt[key] for key in ("status", "device", "gpu", "selected_epoch",
                 "classical", "cohorts", "wall_seconds")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
