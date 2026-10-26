"""Fixed -S magnetic child, actual Job membership before numerical imports."""

import argparse
import ctypes
from pathlib import Path
import sys
from time import monotonic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--packages', required=True)
    parser.add_argument('--dependencies', required=True, nargs='+')
    parser.add_argument('--job-handle', required=True, type=int)
    parser.add_argument('--plan', required=True)
    args = parser.parse_args()
    sys.path.extend([str(Path(args.packages).resolve(strict=True)), *args.dependencies])
    from magnetic_line_survey_runtime import require_job, apis
    require_job(args.job_handle)
    api, _ = apis()
    # Only parent retains the Job after birth verification. Child must not hold
    # a last-handle lease defeating kill-on-parent-close during a real crash.
    if not api.CloseHandle(args.job_handle):
        return 4
    from magnetic_local_paths import external_path
    from magnetic_survey_json import _Lexer, keys, canonical
    plan_path = external_path(args.plan)
    with plan_path.open('rb') as stream:
        raw = stream.read(16385)
    plan = _Lexer(raw, max_bytes=16384, defer=False).document()
    keys(plan, 'schema request original output data_root temp_root binding_receipt wall_seconds', '$/native-plan')
    if plan['schema'] != 'magnetic-fixed-native-plan-1':
        return 2
    for key in ('request', 'original', 'output', 'data_root', 'temp_root', 'binding_receipt'):
        external_path(plan[key])
    with (plan_path.parent/'worker-born.json').open('xb') as stream:
        stream.write(canonical(dict(schema='magnetic-local-birth-1', actual_job_verified=True,
                                    inherited_job_lease_closed=True, before_scientific_imports=True)))
    from run_magnetic_survey import main as calibrate
    argv = ['calibrate', '--allow-candidate-core', '--request', plan['request'], '--original', plan['original'],
        '--output', plan['output'], '--data-root', plan['data_root'], '--temp-root', plan['temp_root'],
        '--binding-receipt', plan['binding_receipt'], '--wall-seconds', str(plan['wall_seconds'])]
    original_deadline = monotonic()+float(plan['wall_seconds'])
    code = calibrate(argv)
    if code == 0:
        # Independent release-target baseline is computed only AFTER fitting,
        # in the SAME retained native Job and original workflow deadline.
        from magnetic_result_bundle import read_bundle
        from magnetic_likelihood import SealedLikelihood
        from magnetic_inverse import build_operator
        from magnetic_calibration import metrics
        import numpy as np
        imported = read_bundle(Path(plan['output']))
        result, request = imported['result'], imported['request']
        reader = SealedLikelihood(canonical(request))
        reader.freeze(result['selected'], np.array(result['model']['chi_si']['data']))
        rows = tuple(result['partition']['outer_rows']['data'])
        observed, noise = reader.read(rows, role='outer')
        baseline = metrics(build_operator(canonical(request), rows, deadline=original_deadline).evaluate(
            np.zeros(len(result['model']['chi_si']['data'])))['prediction_nT'], observed, noise)
        with (plan_path.parent/'zero-baseline.json').open('xb') as stream:
            stream.write(canonical(baseline))
    return code


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TypeError, ctypes.ArgumentError):
        print('{"schema":"magnetic-local-native-error-1","code":"resource"}')
        raise SystemExit(4)
