"""Execute frozen S2 in real provisional Windows Jobs and retain all verdicts.

Explicit existing interpreter/packages/dependencies and external roots only.
Actual native failure/cap != convergence; this is not online/native admission.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]/'data-pipeline'))
from magnetic_local_paths import external_path
from magnetic_survey_json import canonical, digest


def exclusive(path, raw):
    import os
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-root', required=True)
    parser.add_argument('--temp-root', required=True)
    parser.add_argument('--executable', required=True)
    parser.add_argument('--packages', required=True)
    parser.add_argument('--dependencies', required=True, nargs='+')
    parser.add_argument('--cases', required=True, nargs='+')
    parser.add_argument('--wall-seconds', required=True, type=float)
    parser.add_argument('--cancel-after', type=float)
    parser.add_argument('--conditioned-core', action='store_true')
    args = parser.parse_args()
    root, scratch_root = external_path(args.data_root), external_path(args.temp_root)
    if not root.is_dir() or not scratch_root.is_dir() or not 0. < args.wall_seconds <= 7200.:
        raise ValueError('Explicit existing external roots and bounded wall budget required')
    sys.path.extend(args.dependencies)
    import physical_optimizer as linear
    import physical_nonlinear_optimizer as nonlinear
    from run_magnetic_survey import source_inventory
    from magnetic_native_runtime import run_local_survey
    sources = source_inventory(conditioned=args.conditioned_core)
    inventory_hash = digest(sources)
    fixture = Path(__file__).parents[1]/'tests'/'fixtures'/'magnetic_survey'/'full_request.py'
    spec = importlib.util.spec_from_file_location('full_frozen_s2', fixture)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    results = []
    for label in args.cases:
        regime, quantity = label.split(':')
        if regime not in 'ABCDEF' or quantity not in ('secondary_enu_nT', 'linear_tmi_nT', 'exact_total_anomaly_nT'):
            raise ValueError('Exact frozen scientific case required')
        core = nonlinear if quantity == 'exact_total_anomaly_nT' else linear
        binding = core.NonlinearBinding('physical_nonlinear_optimizer.solve_bounded_nonlinear', core.SOURCE_SHA256,
            core.VENDOR_SOURCE_SHA256, inventory_hash, core.RUNTIME_EPOCH, core.POLICY) if core is nonlinear else \
            core.OptimizerBinding('physical_optimizer.solve_bounded_physical', core.SOURCE_SHA256,
                sources['magnetic_inverse_precision'], inventory_hash, core.RUNTIME_EPOCH, core.POLICY)
        if args.conditioned_core:
            from magnetic_conditioned_adapter import binding_for_sources
            import physical_conditioned_optimizer as core
            binding = binding_for_sources(sources, inventory_hash, nonlinear=quantity == 'exact_total_anomaly_nT')
        doc, original, evaluator = generator.generate(regime, quantity, binding)
        name = regime+'-'+quantity
        data, scratch = root/name, scratch_root/name
        data.mkdir()
        scratch.mkdir()
        for filename, raw in (('original.json', original), ('request.json', canonical(doc)),
                              ('evaluator.json', canonical(evaluator))):
            exclusive(data/filename, raw)
        receipt = dict(schema='magnetic-local-binding-1', scope='local_candidate_only',
            review_reference='Explicit reviewed public nonlinear/linear local source, frozen authored control only',
            sources=sources, source_inventory_sha256=inventory_hash, runtime_epoch=binding.runtime_epoch, policy=core.POLICY)
        exclusive(data/'binding.json', canonical(receipt))
        plan = dict(schema='magnetic-fixed-native-plan-1', request=str(data/'request.json'),
            original=str(data/'original.json'), output=str(data/'generation'), data_root=str(root),
            temp_root=str(scratch), binding_receipt=str(data/'binding.json'), wall_seconds=args.wall_seconds)
        exclusive(scratch/'plan.json', canonical(plan))
        print('START '+label, flush=True)
        lifetime = run_local_survey(args.executable, args.packages, tuple(args.dependencies), scratch/'plan.json',
                                   cancel_after=args.cancel_after)
        output = data/'generation'
        record = dict(case=label, source_sha256=doc['source']['original_sha256'], rows=288, active_cells=528,
            native=lifetime, scientific_verdict='failed_no_complete_result', result_status=None, reason=None,
            selected=None, outer=None, full_method_accepted=False, field_source_verified=False)
        audit_path = scratch/'optimizer-audit.jsonl'
        if args.conditioned_core and audit_path.exists():
            record['optimizer_audit_sha256'] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
            record['optimizer_audit_bytes'] = audit_path.stat().st_size
        if (output/'manifest.json').exists() and lifetime['cause'] is None and lifetime['exit_code'] == 0:
            from magnetic_result_bundle import read_bundle
            result = read_bundle(output)['result']
            # Observe zero-model baseline ONLY AFTER already frozen one-time fit.
            baseline_path = scratch/'zero-baseline.json'
            if not baseline_path.exists():
                record.update(result_status=result['status'], reason='Actual contained zero-model baseline unavailable')
                exclusive(data/'scientific-verdict.json', canonical(record))
                results.append(record)
                print('END '+label+' '+record['reason'], flush=True)
                continue
            baseline = json.loads(baseline_path.read_bytes())
            outer = result['metrics']['outer']
            improvement = None if baseline['rms_nT'] == 0. else 1.-outer['rms_nT']/baseline['rms_nT']
            passed = outer['normalized_rms'] <= 2. and improvement is not None and improvement >= .2
            record.update(result_status=result['status'], selected=result['selected'], outer=outer,
                zero_baseline=baseline, raw_rms_improvement_fraction=improvement,
                scientific_verdict='synthetic_predictive_pass' if passed and regime in 'ABC' else
                    'null_numerical_control' if regime == 'F' else 'synthetic_predictive_fail' if regime in 'ABC' else
                    'adverse_discrimination_requires_matched_A')
        elif (output/'manifest.json').exists():
            record.update(scientific_verdict='failed_native_lifetime',
                          reason='Complete generation exists but actual native lifetime refused it')
        elif (output/'failure.json').exists():
            failed = json.loads((output/'failure.json').read_bytes())
            record.update(result_status=failed['status'], reason=failed['diagnostics']['reason'],
                candidates=failed['candidates'], history_records=len(failed['history']),
                failure_sha256=hashlib.sha256((output/'failure.json').read_bytes()).hexdigest())
        else:
            record['reason'] = (scratch/'native.stdout').read_text(encoding='utf-8', errors='strict')[-4096:]
        exclusive(data/'scientific-verdict.json', canonical(record))
        results.append(record)
        print('END '+label+' '+record['scientific_verdict']+' '+str(record['reason']), flush=True)
    exclusive(root/'matrix.json', canonical(dict(schema='magnetic-frozen-matrix-1', cases=results,
        field_truth=False, online_admitted=False, native_security_admitted=False,
        frozen_scientific_gates_modified=False, source_inventory=sources)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
