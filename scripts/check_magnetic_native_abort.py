"""Actual cancel/controller-crash gates for the fixed local magnetic worker.

Uses supplied existing runtimes and fresh external roots. Independent retained
Win32 process handle proves crash drain. No production controller activation.
"""

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-root', required=True)
    parser.add_argument('--temp-root', required=True)
    parser.add_argument('--executable', required=True)
    parser.add_argument('--packages', required=True)
    parser.add_argument('--dependencies', required=True, nargs='+')
    parser.add_argument('--mode', choices=('cancel', 'controller-crash'), required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).parents[1]/'data-pipeline'))
    sys.path.extend(args.dependencies)
    from magnetic_local_paths import external_path
    from magnetic_survey_json import canonical
    from magnetic_line_survey_runtime import apis
    import psutil
    data, scratch = external_path(args.data_root), external_path(args.temp_root)
    if not data.is_dir() or not scratch.is_dir() or list(data.iterdir()) or list(scratch.iterdir()):
        raise ValueError('Fresh empty explicit external roots required')
    runner = Path(__file__).with_name('run_magnetic_frozen_matrix.py')
    boot = ('import sys,runpy;sys.path.insert(0,sys.argv.pop(1));'
            'target=sys.argv.pop(1);sys.argv[0]=target;runpy.run_path(target,run_name="__main__")')
    command = [args.executable, '-B', '-S', '-c', boot, args.packages, str(runner),
        '--data-root', str(data), '--temp-root', str(scratch), '--executable', args.executable,
        '--packages', args.packages, '--dependencies', *args.dependencies,
        '--cases', 'F:secondary_enu_nT', '--wall-seconds', '7200']
    if args.mode == 'cancel':
        command += ['--cancel-after', '5.0']
    api, _ = apis()
    api.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    api.OpenProcess.restype = ctypes.c_void_p
    started = time.monotonic()
    child_handle = None
    with (scratch/'controller.stdout').open('xb') as stdout, (scratch/'controller.stderr').open('xb') as stderr:
        controller = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), creationflags=0x08000000)
        try:
            born = scratch/'F-secondary_enu_nT'/'worker-born.json'
            while not born.exists():
                if controller.poll() is not None or time.monotonic()-started > 60.:
                    raise AssertionError('No actual verified magnetic child birth within 60s')
                time.sleep(.05)
            birth = json.loads(born.read_bytes())
            assert birth['actual_job_verified'] and birth['inherited_job_lease_closed']
            if args.mode == 'controller-crash':
                children = psutil.Process(controller.pid).children(recursive=False)
                owned = [p for p in children if str(Path(__file__).parents[1]/'data-pipeline'/'magnetic_native_worker.py') in p.cmdline()
                         and str(scratch/'F-secondary_enu_nT'/'plan.json') in p.cmdline()]
                assert len(owned) == 1, 'Exact just-launched fixed-worker child identity required'
                child_handle = api.OpenProcess(0x100000 | 0x1000, False, owned[0].pid)
                assert child_handle, 'Retained independent child handle required BEFORE crash'
                crashed = time.monotonic()
                controller.kill()  # Only this exact controller, not a discovered outside process.
                controller.wait(timeout=10.)
                assert api.WaitForSingleObject(child_handle, 10000) == 0
                drained = time.monotonic()-crashed
                code = ctypes.c_ulong()
                # Kill-on-last-Job-close can use exit 0. Only a published and
                # fully verified generation establishes scientific completion.
                assert api.GetExitCodeProcess(child_handle, ctypes.byref(code)) and code.value != 259
                assert not (data/'F-secondary_enu_nT'/'generation'/'manifest.json').exists()
                actual = dict(controller_exit=controller.returncode, retained_child_exit=int(code.value),
                    independent_retained_child_wait='signalled', stop_drain_s=drained, orphan=False,
                    published_generation=False, exit_zero_is_not_scientific_success=True)
            else:
                controller.wait(timeout=30.)
                lifetime = json.loads((scratch/'F-secondary_enu_nT'/'native-lifetime.json').read_bytes())
                assert lifetime['cause'] == 'cancelled' and lifetime['active_processes'] == 0
                assert lifetime['total_processes'] == 1 and lifetime['exit_code'] != 0
                assert lifetime['stop_drain_s'] <= 10.
                assert not (data/'F-secondary_enu_nT'/'generation'/'manifest.json').exists()
                actual = lifetime
            proof = dict(schema='magnetic-native-abort-proof-1', gate=args.mode, verdict='pass', actual=actual,
                birth=birth, fixed_runner_sha256=hashlib.sha256(runner.read_bytes()).hexdigest(),
                field_accepted=False, scientific_acceptance=False, native_security_admitted=False,
                online_admitted=False)
            with (data/'abort-proof.json').open('xb') as stream:
                stream.write(canonical(proof))
                stream.flush()
                os.fsync(stream.fileno())
            print(args.mode+' actual drain pass')
        finally:
            if controller.poll() is None:
                controller.kill()
                controller.wait(timeout=10.)
            if child_handle:
                api.CloseHandle(child_handle)


if __name__ == '__main__':
    main()
