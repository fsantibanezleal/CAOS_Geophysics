"""Explicit local CLI; no unreviewed native supervisor/in-process fallback."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline"))
from waveform_input import WaveformInputError, fail
from waveform_m08_files import validate_path, external_work_path


class StrictParser(argparse.ArgumentParser):
    def error(self, message):
        fail("waveform_contract")


def main(argv=None):
    status, reason, code = "engine_unavailable", "supervisor_unavailable", 4
    try:
        argv = sys.argv[1:] if argv is None else argv
        if type(argv) not in (list, tuple) or len(argv) > 14 or any(type(x) is not str or len(x) > 4096 for x in argv):
            fail("waveform_contract")
        parser = StrictParser(add_help=False, allow_abbrev=False)
        for name in ("mseed", "stationxml", "request", "out", "python"):
            parser.add_argument("--" + name, required=True)
        parser.add_argument("--evaluate-with")
        parser.add_argument("--admission")
        names = [x for x in argv if x.startswith("--")]
        if len(names) != len(set(names)):
            fail("waveform_contract")
        args = parser.parse_args(argv)
        paths = {
            name: (validate_path if name == "python" else external_work_path)(getattr(args, name))
            for name in ("mseed", "stationxml", "request", "out", "python")
        }
        if len(set(paths.values())) != len(paths) or paths["out"].exists():
            fail("waveform_contract")
        reference = None
        if args.evaluate_with is not None:
            reference = external_work_path(args.evaluate_with)
            if reference in paths.values():
                fail("waveform_contract")
        if args.admission is not None:
            admission = external_work_path(args.admission)
            if admission in paths.values() or admission == reference:
                fail("waveform_contract")
            from waveform_m08_windows import run_cli, exit_status

            result = run_cli(paths, reference, admission)
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
            return exit_status(result)
        # No admission: refuse before any original/reference read or native call.
    except (WaveformInputError, OSError, ValueError):
        status, reason, code = "rejected", "path_contract", 3
    print(json.dumps({"status": status, "reason": reason}, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
