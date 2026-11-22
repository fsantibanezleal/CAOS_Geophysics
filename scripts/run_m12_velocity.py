"""Explicit external-output entry point for the two unchanged M12 protocols."""

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
    parser.add_argument("--protocol", choices=("historical-v1", "physics-v2"), default="historical-v1")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.epochs <= 10000:
            raise paths.Refusal("epochs must be 1..10000")
        if args.protocol == "physics-v2" and args.epochs != 40:
            raise paths.Refusal("physics-v2 has a frozen forty-epoch protocol")
        output = paths.external(args.output, exists=False)
    except (paths.Refusal, OSError, ValueError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    module = "velocity_validation.py" if args.protocol == "historical-v1" else "velocity_physics_refinement.py"
    command = [sys.executable, "-B", str(ROOT / "data-pipeline" / module),
               "--output", str(output)]
    if args.verify:
        command.append("--verify")
    else:
        command.extend(["--device", args.device])
        if args.protocol == "historical-v1":
            command.extend(["--epochs", str(args.epochs)])
        if args.fixture:
            command.append("--fixture")
    # Local trusted launcher only; scientific evaluation and evidence remain in
    # the unchanged protocol. This is not native/server containment or admission.
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
