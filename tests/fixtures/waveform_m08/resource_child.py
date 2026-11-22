"""Fixed real-OS adversaries, never selected by the public scientific CLI.

Every actual invocation must use a NEW private fixture root and the exact A4
native launch primitives. Authoring/importing is NOT an actual safety pass.
"""

import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from waveform_m08_windows import Native, EXTENDED, MEMORY, require, ControlError

MODES = frozenset(("nominal", "short_cpu", "cpu_stop", "memory", "hang", "crash", "forbidden_child", "controller_tail"))


def main(argv):
    require(type(argv) is list and len(argv) == 1 and type(argv[0]) is str and argv[0] in MODES)
    native = Native()
    native.membership(native.api.GetCurrentProcess(), None)
    limits = native.query(None, 9, EXTENDED)
    require(
        limits.basic.flags == 0x220C
        and limits.basic.job_user == 600000000
        and limits.job_memory == MEMORY
        and limits.basic.active in (2, 8)
    )
    mode = argv[0]
    if mode == "crash":
        os._exit(23)
    if mode == "hang":
        time.sleep(65)
        return 0
    if mode == "memory":
        blocks = []
        for _ in range(80):
            block = bytearray(16777216)
            for index in range(0, len(block), 4096):
                block[index] = 1
            blocks.append(block)
        return 0  # Surviving this is a negative control, not a cap pass.
    if mode == "forbidden_child":
        import msvcrt

        inherited = tuple(msvcrt.get_osfhandle(fd) for fd in (0, 1, 2))
        # Same job inheritance and no breakaway. A nominal two-process job must refuse process three.
        process = native.launch(
            sys.executable,
            ["-I", "-B", str(Path(__file__).resolve()), "short_cpu"],
            inherited,
            inherited,
            Path(os.environ["TEMP"]),
        )
        native.membership(process.process, None)
        native.resume(process)
        while not native.signalled(process.process):
            time.sleep(0.005)
        code = native.exit_code(process.process)
        native.cleanup()
        return code
    seconds = {"nominal": 0.01, "short_cpu": 0.25, "cpu_stop": 65, "controller_tail": 0.5}[mode]
    until, value = time.process_time() + seconds, 0
    while time.process_time() < until:
        value = (value + 1) % 104729
    print(
        json.dumps(
            {
                "schema": "caos.m08-authored-resource-control.v1",
                "mode": mode,
                "status": "exited",
                "native_safety_pass": False,
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (ControlError, OSError, ValueError):
        raise SystemExit(3) from None
