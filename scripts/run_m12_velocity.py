"""Explicit external-output entry point for the unchanged historical M12 protocol."""

import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("m12_path_custody", ROOT / "scripts" / "validate_local.py")
paths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paths)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.epochs <= 10000:
            raise paths.Refusal("epochs must be 1..10000")
        output = paths.external(args.output, exists=False)
    except (paths.Refusal, OSError, ValueError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    command = [sys.executable, "-B", str(ROOT / "data-pipeline" / "velocity_validation.py"),
               "--output", str(output)]
    if args.verify:
        command.append("--verify")
    else:
        command.extend(["--device", args.device, "--epochs", str(args.epochs)])
        if args.fixture:
            command.append("--fixture")
    # Local trusted launcher only; scientific evaluation and evidence remain in
    # the unchanged protocol. This is not native/server containment or admission.
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
