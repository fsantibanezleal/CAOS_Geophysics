"""Run an explicit local first-arrival survey, without network or training."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline"))
from velocity_user_data import calculate, export_generation, read_regular, MAX_INPUT


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--checkpoint-sha256")
    parser.add_argument("--checkpoint-protocol", choices=("original", "physics-v2"), default="original")
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise FileExistsError()
        raw = read_regular(args.input, MAX_INPUT)
        result = calculate(raw, checkpoint=args.checkpoint, checkpoint_sha256=args.checkpoint_sha256,
                           checkpoint_protocol=args.checkpoint_protocol)
        export_generation(result, args.output)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        print("First-arrival operation failed; input, engine or fresh output is invalid", file=sys.stderr)
        return 2
    print("Local first-arrival calculation and verified export completed; no field-validity claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
