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
from magnetic_survey_json import InputError, canonical, digest


def exclusive(path, raw):
    import os
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def original_prerequisite_failed(record):
    """Fail-first ledger gate, not authority to run an unqualified full matrix."""
    return record['scientific_verdict'].startswith('failed') or record['scientific_verdict'] == 'synthetic_predictive_fail'


def refused_native_observation(error):
    from magnetic_line_survey import SurveyError
    if type(error) is InputError:
        reason = error.envelope()
    elif type(error) is SurveyError:
        reason = dict(InputError('resource', '$/native', 'Public observation reader refused').envelope(),
                      observation_error=error.error)
    elif isinstance(error, OSError):
        # Do not expose arbitrary OS messages or promote missing files to zero.
        reason = dict(InputError('resource', '$/native', 'Native file/process operation refused').envelope(),
                      os_errno=error.errno)
    else:
        raise TypeError('Exact native refusal required')
    return dict(native=None, scientific_verdict='failed_native_observation', reason=reason)


def observe_frozen_model(result, doc, evaluator, *, matched_a=None):
    """Observe an already verified/frozen generation; never a fitting callback.

    Structural fixtures in unit tests exercise wiring, not scientific fits.
    The actual caller supplies read_bundle's full verified native result.
    """
    if (result['status'] != 'complete' or evaluator['schema'] != 'magnetic-s2-evaluator-1'
            or evaluator['modelling_request_sha256'] != digest(doc)
            or evaluator['original_bytes'] != doc['source']['original_bytes']
            or evaluator['provenance']['original_sha256'] != doc['source']['original_sha256']
            or evaluator['quantity'] != doc['processing']['quantity']
            or evaluator['field_truth'] is not False or evaluator['frozen_generator_modified'] is not False):
        raise ValueError('Original frozen evaluator/request identity required')
    from magnetic_s2_evaluation import evaluate_model, adverse_verdict
    regime = evaluator['regime']
    if regime not in tuple('ABCDEF'):
        raise ValueError('Exact original S2 regime required')
    model = result['model']['chi_si']['data']
    observed = dict(model_evaluation=evaluate_model(doc['geometry']['mesh'], evaluator['bodies'], model))
    if regime in 'DE':
        # Never use another quantity's A or a partial/failed metric substitute.
        matched = (matched_a['outer']['rms_nT'] if matched_a is not None
            and matched_a['case'] == 'A:'+evaluator['quantity']
            and matched_a['scientific_verdict'] == 'synthetic_predictive_pass' else None)
        observed['adverse_discrimination'] = adverse_verdict(result['metrics']['outer']['rms_nT'], matched)
    if regime == 'F':
        values = result['prediction']['values_nT']['data']
        observed['null_control'] = dict(model_exactly_zero=bool(model) and all(value == 0. for value in model),
            predictions_exactly_zero=bool(values) and all(value == 0. for value in values),
            linear_quantity=evaluator['quantity'] in ('secondary_enu_nT', 'linear_tmi_nT'))
    return observed


def matrix_observation_gate(results, requested):
    """Process-level fail-first signal, never a product/native admission."""
    permitted = {regime+':'+quantity for regime in 'ABCDEF'
        for quantity in ('secondary_enu_nT', 'linear_tmi_nT', 'exact_total_anomaly_nT')}
    if (type(requested) is not list or not requested or len(requested) != len(set(requested))
            or not set(requested) <= permitted or [item['case'] for item in results] != requested):
        raise ValueError('Exact unique requested matrix controls required')
    passed = {'synthetic_predictive_pass', 'adverse_degradation_demonstrated', 'null_numerical_control'}
    verdicts = [item['scientific_verdict'] for item in results]
    successful = all(verdict in passed for verdict in verdicts)
    linear_matrix = {regime+':'+quantity for regime in 'ABCDEF'
        for quantity in ('secondary_enu_nT', 'linear_tmi_nT')}
    return dict(status='selected_scientific_controls_passed' if successful else 'scientific_controls_not_passed',
        selected_controls_passed=successful, complete_original_linear_coverage=set(requested) == linear_matrix,
        full_method_accepted=False, field_source_verified=False, native_security_admitted=False)


def frozen_result_observation(result, doc, evaluator, baseline, *, matched_a=None):
    if baseline is None:
        # This refusal must reach the COMMON dependency gate, not continue into
        # a fresh downstream scientific birth merely because a ZIP exists.
        return dict(result_status=result['status'], scientific_verdict='failed_no_complete_result',
            reason='Actual contained zero-model baseline unavailable')
    regime = evaluator['regime']
    outer = result['metrics']['outer']
    improvement = None if baseline['rms_nT'] == 0. else 1.-outer['rms_nT']/baseline['rms_nT']
    passed = outer['normalized_rms'] <= 2. and improvement is not None and improvement >= .2
    record = dict(result_status=result['status'], selected=result['selected'], outer=outer,
        zero_baseline=baseline, raw_rms_improvement_fraction=improvement,
        scientific_verdict='synthetic_predictive_pass' if passed and regime in 'ABC' else
            'null_numerical_control' if regime == 'F' else 'synthetic_predictive_fail' if regime in 'ABC' else
            'adverse_discrimination_requires_matched_A')
    observed = observe_frozen_model(result, doc, evaluator, matched_a=matched_a)
    record.update(observed)
    if regime in 'DE':
        record['scientific_verdict'] = observed['adverse_discrimination']['verdict']
    if regime == 'F':
        null = observed['null_control']
        record['scientific_verdict'] = ('null_numerical_control' if all(null.values()) else
            'failed_null_control' if null['linear_quantity'] else 'unresolved_nonlinear_null_baseline')
    return record


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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--conditioned-core', action='store_true')
    mode.add_argument('--feasible-core', action='store_true')
    mode.add_argument('--reduced-core', action='store_true')
    mode.add_argument('--original-core', action='store_true')
    args = parser.parse_args()
    # Refuse malformed/duplicate case identities BEFORE numerical imports or birth.
    matrix_observation_gate([dict(case=label, scientific_verdict='not_run') for label in args.cases], args.cases)
    root, scratch_root = external_path(args.data_root), external_path(args.temp_root)
    if not root.is_dir() or not scratch_root.is_dir() or not 0. < args.wall_seconds <= 7200.:
        raise ValueError('Explicit existing external roots and bounded wall budget required')
    sys.path.extend(args.dependencies)
    import physical_optimizer as linear
    import physical_nonlinear_optimizer as nonlinear
    from run_magnetic_survey import source_inventory
    from magnetic_native_runtime import run_local_survey
    from magnetic_line_survey import SurveyError
    conditioned = args.conditioned_core or args.feasible_core or args.reduced_core or args.original_core
    if (args.feasible_core or args.reduced_core or args.original_core) and any(label.endswith(':exact_total_anomaly_nT') for label in args.cases):
        raise ValueError('Public contact/reduced source is LINEAR-only')
    sources = source_inventory(conditioned=conditioned, feasible=args.feasible_core,
        reduced=args.reduced_core, original=args.original_core)
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
        if conditioned:
            from magnetic_conditioned_adapter import binding_for_sources
            import physical_conditioned_optimizer as core
            binding = binding_for_sources(sources, inventory_hash, nonlinear=quantity == 'exact_total_anomaly_nT', feasible=args.feasible_core)
            if args.reduced_core:
                from magnetic_reduced_adapter import binding_for_sources as reduced_binding
                binding = reduced_binding(sources, inventory_hash)
            if args.original_core:
                from magnetic_original_adapter import binding_for_sources as original_binding
                binding = original_binding(sources, inventory_hash)
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
            sources=sources, source_inventory_sha256=inventory_hash, runtime_epoch=binding.runtime_epoch, policy=binding.policy)
        exclusive(data/'binding.json', canonical(receipt))
        plan = dict(schema='magnetic-fixed-native-plan-1', request=str(data/'request.json'),
            original=str(data/'original.json'), output=str(data/'generation'), data_root=str(root),
            temp_root=str(scratch), binding_receipt=str(data/'binding.json'), wall_seconds=args.wall_seconds)
        exclusive(scratch/'plan.json', canonical(plan))
        print('START '+label, flush=True)
        native_error = None
        try:
            lifetime = run_local_survey(args.executable, args.packages, tuple(args.dependencies), scratch/'plan.json',
                                       cancel_after=args.cancel_after)
        except (InputError, SurveyError, OSError) as error:
            # A refused observer supplies NO resource/lifetime receipt. Preserve
            # this exact non-success and reach the common dependency gate.
            lifetime = None
            native_error = refused_native_observation(error)
        output = data/'generation'
        record = dict(case=label, source_sha256=doc['source']['original_sha256'], rows=288, active_cells=528,
            native=lifetime, scientific_verdict='failed_no_complete_result', result_status=None, reason=None,
            selected=None, outer=None, full_method_accepted=False, field_source_verified=False)
        audit_path = scratch/'optimizer-audit.jsonl'
        if conditioned and audit_path.exists():
            record['optimizer_audit_sha256'] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
            record['optimizer_audit_bytes'] = audit_path.stat().st_size
        if native_error is not None:
            record.update(native_error)
        elif (output/'manifest.json').exists() and lifetime['cause'] is None and lifetime['exit_code'] == 0:
            from magnetic_result_bundle import read_bundle
            result = read_bundle(output)['result']
            # Observe zero-model baseline ONLY AFTER already frozen one-time fit.
            baseline_path = scratch/'zero-baseline.json'
            baseline = json.loads(baseline_path.read_bytes()) if baseline_path.exists() else None
            matched_a = next((item for item in results if item['case'] == 'A:'+quantity), None)
            record.update(frozen_result_observation(result, doc, evaluator, baseline, matched_a=matched_a))
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
        if args.original_core and original_prerequisite_failed(record):
            # New source is explicitly fail-first. No downstream native birth,
            # fabricated evaluation, or unchanged failed-matrix repetition.
            for dependent in args.cases[len(results):]:
                results.append(dict(case=dependent, scientific_verdict='not_run',
                    reason='prerequisite_failed:'+label, full_method_accepted=False,
                    field_source_verified=False))
            break
    observation = matrix_observation_gate(results, args.cases)
    exclusive(root/'matrix.json', canonical(dict(schema='magnetic-frozen-matrix-1', cases=results, observation=observation,
        field_truth=False, online_admitted=False, native_security_admitted=False,
        frozen_scientific_gates_modified=False, source_inventory=sources)))
    return 0 if observation['selected_controls_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
