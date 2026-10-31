"""Run explicitly declared external acoustic observations, not a cached case."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"data-pipeline"))
from fwi_user_data import calculate, export_generation, external


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), required=True)
    args = parser.parse_args(argv)
    try:
        output = external(args.output)
        if output.exists() or not output.parent.is_dir():
            raise ValueError()
        manifest, arrays = calculate(args.input, device=args.device)
        export_generation(manifest, arrays, output)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        print("Acoustic operation failed; input, engine or fresh external output is invalid", file=sys.stderr)
        return 2
    print("Actual local acoustic inversion and verified array export completed; finite-budget, no field-truth claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
