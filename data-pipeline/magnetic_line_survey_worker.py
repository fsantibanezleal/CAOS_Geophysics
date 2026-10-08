"""Fixed cold worker. No executable payloads or arbitrary user commands."""
from __future__ import annotations

import argparse
from hashlib import sha256
import os
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--packages', required=True)
    parser.add_argument('--job-handle', required=True, type=int)
    parser.add_argument('--plan', required=True)
    args = parser.parse_args(argv)
    # Explicit already installed package directory; -S forbids site hooks.
    sys.path.insert(0, str(Path(args.packages).resolve(strict=True)))
    import magnetic_line_contract as base
    import magnetic_line_survey as core
    import magnetic_line_survey_io as io
    from magnetic_line_survey_runtime import require_job
    phase = 'containment'
    try:
        require_job(args.job_handle)  # Before numerical imports/input decoding.
        phase = 'plan'
        plan_path = io.external_path(args.plan, directory=False)
        plan = base.strict_json(base.read_bounded(plan_path, 2097152))
        if type(plan) is dict and plan.get('schema') == 'm03-training-diagnosis-plan/1':
            from magnetic_line_survey_diagnosis import diagnose_retained_s1
            return diagnose_retained_s1(plan,plan_path.parent,args.job_handle)
        if type(plan) is dict and plan.get('schema') == 'm03-global-control-plan/1':
            from magnetic_line_survey_diagnostic import run_opened_s1
            return run_opened_s1(plan,plan_path.parent,args.job_handle)
        if type(plan) is not dict or set(plan) != {'schema', 'mode', 'input_root', 'coordinates', 'sources', 'damping'} or \
           plan['schema'] != 'm03-native-probe-plan/1' or plan['mode'] not in ('zero', 'cancel'):
            raise core.SurveyError('invalid_contract', 'seal')
        reader = io.Reader(plan['input_root'])
        xyz_ref, sources_ref = plan['coordinates'], plan['sources']
        import magnetic_line_survey_contract as contract
        for ref, role in ((xyz_ref, 'navigation'), (sources_ref, 'source_position')):
            contract.validate('ArrayRef', ref)
            if ref['role'] != role or ref['dtype'] != 'float64' or ref['unit'] != 'm' or \
               len(ref['shape']) != 2 or ref['shape'][1] != 3 or ref['mask_array_id'] is not None:
                raise core.SurveyError('invalid_contract', 'seal')
        capacity = core.plan_capacity(xyz_ref['shape'][0], sources_ref['shape'][0])
        phase = 'engines'
        print('m03-worker:engines', file=sys.stderr, flush=True)
        np, _ = core.engines()
        phase = 'geometry'
        print('m03-worker:geometry', file=sys.stderr, flush=True)
        arrays = []
        for index, ref in enumerate((xyz_ref, sources_ref)):
            member = plan_path.parent / f'probe-{index}.bin'
            with member.open('xb') as stream:
                for chunk in reader.chunks(ref):
                    stream.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())
            arrays.append(np.memmap(member, dtype='<f8', mode='r', shape=tuple(ref['shape'])))
        reader.reject_unknown()
        values = np.zeros(len(arrays[0]), dtype=np.float64)
        values.flags.writeable = False
        phase = 'operator'
        print('m03-worker:operator', file=sys.stderr, flush=True)
        operator = core.GlobalOperator(*arrays, job_handle=args.job_handle)
        phase = 'solve'
        first = core.solve_global(operator, values, plan['damping'])
        # Windows App Execution Aliases can differ from the actually loaded
        # binary even when the parent launches its real absolute path.
        import ctypes
        from ctypes import wintypes
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
        api.GetModuleFileNameW.restype = wintypes.DWORD
        buffer = ctypes.create_unicode_buffer(32768)
        count = api.GetModuleFileNameW(None, buffer, len(buffer))
        if not 0 < count < len(buffer)-1:
            raise core.SurveyError('custody_mismatch', 'fit')
        actual_binary = Path(buffer.value).resolve(strict=True)
        receipt = dict(schema='m03-native-zero-probe/1', plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),
            rows=operator.n, sources=operator.m, capacity=capacity, zero_target=True,
            objective=first['objective'], stationarity_relative=first['stationarity_relative'],
            istop=first['istop'], iterations=first['iterations'],
            operator_forward_calls=first['operator_forward_calls'], operator_adjoint_calls=first['operator_adjoint_calls'],
            worker_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
            core_sha256=sha256(Path(core.__file__).read_bytes()).hexdigest(),
            actual_executable_sha256=sha256(actual_binary.read_bytes()).hexdigest(),
            engine_pins=core.ENGINE_PINS, source_pins={k:v[2] for k,v in core.SOURCE_PINS.items()},
            scientific_acceptance='not_established')
        core._write_member(plan_path.parent, 'native-ready.json', base.canonical_bytes(receipt))
        if plan['mode'] == 'cancel':
            # Real pinned block kernels, forward AND adjoint after a completed
            # solve. No sleep or pretend native workload; parent terminates Job.
            direction = np.ones(operator.m, dtype=np.float64)
            while True:
                action = operator.operator.matvec(direction)
                operator.operator.rmatvec(action)
        return 0
    except core.SurveyError as error:
        print(base.canonical_bytes(error.error).decode('ascii'), flush=True)
        return 2
    except (OSError, ValueError, TypeError, KeyError) as error:
        print('m03-worker:'+phase+':'+type(error).__name__, file=sys.stderr, flush=True)
        print(base.canonical_bytes(core.SurveyError('invalid_contract', 'ingest').error).decode('ascii'), flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
