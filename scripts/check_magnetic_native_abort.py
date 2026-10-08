"""Actual cancel/controller-crash gates for the fixed local magnetic worker.

Uses supplied existing runtimes and fresh external roots. Independently held
ancestor Job proves group extinction without a late numeric PID acquisition.
No production controller activation.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
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
    parser.add_argument('--case', choices=('A:secondary_enu_nT', 'F:secondary_enu_nT'), default='A:secondary_enu_nT')
    parser.add_argument('--cancel-after', type=float, default=45.)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--conditioned-core', action='store_true')
    mode.add_argument('--feasible-core', action='store_true')
    mode.add_argument('--original-core', action='store_true')
    parser.add_argument('--final-fit-qualification')
    parser.add_argument('--qualification-sha256')
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).parents[1]/'data-pipeline'))
    sys.path.extend(args.dependencies)
    from magnetic_local_paths import external_path
    from magnetic_survey_json import canonical
    from magnetic_abort_observer import AbortObserver, verify_final_qualification
    data, scratch = external_path(args.data_root), external_path(args.temp_root)
    if not data.is_dir() or not scratch.is_dir() or list(data.iterdir()) or list(scratch.iterdir()):
        raise ValueError('Fresh empty explicit external roots required')
    if args.original_core:
        from run_magnetic_survey import source_inventory
        from magnetic_original_adapter import binding_for_sources
        from magnetic_survey_json import digest
        from check_magnetic_original_workflow_allocation import workflow_allocation
        sources = source_inventory(conditioned=True, original=True)
        binding = binding_for_sources(sources, digest(sources))
        fixture = Path(__file__).parents[1]/'tests/fixtures/magnetic_survey/full_request.py'
        spec = importlib.util.spec_from_file_location('original_abort_input', fixture)
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        regime, quantity = args.case.split(':')
        document, _, _ = generator.generate(regime, quantity, binding)
        prerequisite = workflow_allocation(canonical(document))
        with (data/'abort-prerequisite.json').open('xb') as stream:
            stream.write(canonical(prerequisite)); stream.flush(); os.fsync(stream.fileno())
        if prerequisite['status'] != 'within_original_envelope':
            print('Original workflow allocation refused BEFORE controller birth')
            return 2
        if not args.final_fit_qualification or not args.qualification_sha256:
            raise ValueError('Source-bound final648 fit/precision qualification required before science birth')
        from run_magnetic_survey import read_bounded
        qualifier_raw = read_bounded(external_path(args.final_fit_qualification), 1024**2)
        if hashlib.sha256(qualifier_raw).hexdigest() != args.qualification_sha256:
            raise ValueError('Exact external final-fit qualifier SHA refused')
        a_document, a_original, _ = generator.generate('A', 'secondary_enu_nT', binding)
        verify_final_qualification(json.loads(qualifier_raw), sources=sources,
            request_sha256=hashlib.sha256(canonical(a_document)).hexdigest(),
            original_sha256=hashlib.sha256(a_original).hexdigest())
    runner = Path(__file__).with_name('run_magnetic_frozen_matrix.py')
    boot = ('import sys,runpy;sys.path.insert(0,sys.argv.pop(1));'
            'target=sys.argv.pop(1);sys.argv[0]=target;runpy.run_path(target,run_name="__main__")')
    command = [args.executable, '-B', '-S', '-c', boot, args.packages, str(runner),
        '--data-root', str(data), '--temp-root', str(scratch), '--executable', args.executable,
        '--packages', args.packages, '--dependencies', *args.dependencies,
        '--cases', args.case, '--wall-seconds', '7200']
    if args.conditioned_core:
        command += ['--conditioned-core']
    if args.feasible_core:
        command += ['--feasible-core']
    if args.original_core:
        command += ['--original-core']
    if args.mode == 'cancel':
        command += ['--cancel-after', str(args.cancel_after)]
    started = time.monotonic()
    with (scratch/'controller.stdout').open('xb') as stdout, (scratch/'controller.stderr').open('xb') as stderr:
        observer = AbortObserver()
        try:
            controller = observer.launch(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            case_name = args.case.replace(':', '-')
            born = scratch/case_name/'worker-born.json'
            while not born.exists():
                if controller.poll() is not None or time.monotonic()-started > 60.:
                    raise AssertionError('No actual verified magnetic child birth within 60s')
                time.sleep(.05)
            birth = json.loads(born.read_bytes())
            assert birth['actual_job_verified'] and birth['inherited_job_lease_closed']
            native_log = scratch/case_name/'native.stderr'
            while True:
                log = native_log.read_text(encoding='utf-8')
                scientific_started = bool(re.search(r'^\s+1\s+[\d.e+\-]+', log, re.M)) if args.case.startswith('A:') else 'Projected GNCG' in log
                if scientific_started:
                    break
                if controller.poll() is not None or time.monotonic()-started > 75.:
                    raise AssertionError('No actual accepted scientific objective state before stop; no import-only PASS')
                time.sleep(.05)
            if args.mode == 'controller-crash':
                crashed = time.monotonic()
                controller.kill()  # Only this exact controller, not a discovered outside process.
                controller.wait(timeout=10.)
                group = observer.empty(crashed+10., expected_total=2)
                drained = time.monotonic()-crashed
                # Kill-on-last-Job-close can use exit 0. Only a published and
                # fully verified generation establishes scientific completion.
                assert not (data/case_name/'generation'/'manifest.json').exists()
                actual = dict(controller_exit=controller.returncode, **group,
                    independent_retained_ancestor='fresh_empty', stop_drain_s=drained, orphan=False,
                    published_generation=False, exit_zero_is_not_scientific_success=True)
            else:
                # Scientific birth can precede the configured cancellation by
                # more than30s. This observation reserve does NOT extend the
                # child's original cancellation/CPU/wall budgets.
                observation_deadline = time.monotonic()+args.cancel_after+20.
                while controller.poll() is None and time.monotonic() < observation_deadline:
                    time.sleep(.05)
                controller.wait(timeout=1.)
                lifetime = json.loads((scratch/case_name/'native-lifetime.json').read_bytes())
                assert lifetime['cause'] == 'cancelled' and lifetime['active_processes'] == 0
                assert lifetime['total_processes'] == 1 and lifetime['exit_code'] != 0
                assert lifetime['stop_drain_s'] <= 10.
                group = observer.empty(observation_deadline, expected_total=2)
                assert not (data/case_name/'generation'/'manifest.json').exists()
                actual = dict(lifetime, ancestor_group=group)
            proof = dict(schema='magnetic-native-abort-proof-1', gate=args.mode, verdict='pass', actual=actual,
                case=args.case, actual_scientific_objective_started=True,
                conditioned_core=args.conditioned_core,
                feasible_core=args.feasible_core,
                native_log_sha256=hashlib.sha256(native_log.read_bytes()).hexdigest(),
                birth=birth, fixed_runner_sha256=hashlib.sha256(runner.read_bytes()).hexdigest(),
                field_accepted=False, scientific_acceptance=False, native_security_admitted=False,
                online_admitted=False)
            with (data/'abort-proof.json').open('xb') as stream:
                stream.write(canonical(proof))
                stream.flush()
                os.fsync(stream.fileno())
            print(args.mode+' actual drain pass')
        finally:
            observer.cleanup()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
