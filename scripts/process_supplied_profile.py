"""Path-invoked local profile processing; never upload or fetch an original."""
from pathlib import Path
import argparse
from contextlib import contextmanager, redirect_stdout
import json
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline"))
import supplied_profiles as workflow


@contextmanager
def engine_diagnostics():
    """Keep Python and native engine logs off the machine-readable stdout lane."""
    sys.stdout.flush()
    sys.stderr.flush()
    original_stdout = os.dup(1)
    try:
        os.dup2(2, 1)
        with redirect_stdout(sys.stderr):
            yield
            sys.stderr.flush()
    finally:
        os.dup2(original_stdout, 1)
        os.close(original_stdout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path,
                        help="new explicit directory; existing output is never overwritten")
    args = parser.parse_args(argv)
    try:
        with engine_diagnostics():
            result = workflow.process_profile(args.input, workflow.read_metadata(args.metadata))
            manifest = workflow.export_result(result, args.output)
    except (workflow.ProfileError, OSError, ValueError, RuntimeError):
        print(json.dumps({"status": "rejected", "published": False}))
        return 2
    verdict = result["engine_report"]["inverse_status"]
    print(json.dumps({"status": verdict, "result_sha256": manifest["result"]["sha256"],
                      "content_sha256": result["content_sha256"], "published": True}))
    return 0 if verdict == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
