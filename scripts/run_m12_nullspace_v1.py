"""Run or independently replay the predeclared M12 nullspace experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

import velocity_nullspace_refinement as study  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-run", type=Path,
                        help="external failed v3.1 run containing receipt.json and its checkpoint")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--fixture", action="store_true", help="run a 12-case calibration smoke fixture only")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if any((parent / ".git").exists() for parent in (output, *output.parents)):
        parser.error("--output must be outside every repository checkout")
    if args.verify:
        print(json.dumps(study.verify(output), sort_keys=True))
        return 0
    if args.source_run is None:
        parser.error("--source-run is required for a new execution")
    source_run = args.source_run.expanduser().resolve()
    if any((parent / ".git").exists() for parent in (source_run, *source_run.parents)):
        parser.error("--source-run must identify an external research run")
    receipt = study.execute(output, source_run,
                            device=args.device, fixture=args.fixture)
    print(json.dumps({"status": receipt["status"], "selected_lambda": receipt["classical"]["selected_lambda"],
                      "selected_alpha": receipt["refinement"]["alpha_selection"]["selected_alpha"],
                      "calibration_supported": receipt["refinement"]["alpha_selection"]["calibration_supported"],
                      "joint_ood": receipt["cohorts"].get("joint_ood"),
                      "wall_seconds": receipt["wall_seconds"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
