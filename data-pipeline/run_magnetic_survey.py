"""Bounded supplied-data local tools; no public service or source download.

Local candidate execution needs an explicit operator-reviewed binding receipt
AND --allow-candidate-core. That receipt binds loaded source, not independent
scientific acceptance. Nonlinear/source/online gates cannot be opted out here.
"""

import argparse
from contextlib import redirect_stdout
import hashlib
import importlib
import json
from pathlib import Path
import sys
from time import monotonic

from magnetic_survey_json import InputError, MAX_BYTES, _Lexer, canonical, digest, fail, keys, parse_request
from magnetic_survey import plan_geometry
from magnetic_local_paths import configure_scratch, data_output, external_path


SOURCES = ('physical_optimizer', 'physical_nonlinear_optimizer', 'gravity_l2_precision', 'magnetic_forward', 'magnetic_inverse',
           'magnetic_inverse_precision', 'magnetic_optimizer_adapter', 'magnetic_likelihood',
           'magnetic_calibration', 'magnetic_diagnostics', 'magnetic_survey', 'magnetic_survey_json',
           'magnetic_result_bundle', 'magnetic_local_paths', 'magnetic_nonlinear_adapter', 'run_magnetic_survey',
           'magnetic_native_runtime', 'magnetic_native_worker', 'simpeg.optimization',
           'magnetic_line_survey_runtime', 'magnetic_line_survey', 'magnetic_line_survey_io',
           'magnetic_line_contract', 'magnetic_line_survey_contract')


CONDITIONED_SOURCES = ('physical_conditioned_optimizer', 'physical_owned_spd', 'gravity_l2_metric',
                       'magnetic_conditioned_adapter')


def source_inventory(*, conditioned=False):
    # An operator receipt must include the actual transitive generic certificate
    # validator dependency. Do not hash a filename without loading that source.
    return {name: hashlib.sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest()
            for name in SOURCES+(CONDITIONED_SOURCES if conditioned else ())}


def read_bounded(path, limit):
    from magnetic_result_bundle import _read_regular
    value = Path(path)
    if not value.is_absolute():
        fail('durability', '$/input', 'Explicit absolute read-only input required')
    return _read_regular(value, limit)


def verify_original(path, source):
    import os
    import stat
    value = Path(path)
    if not value.is_absolute() or value.is_symlink():
        fail('durability', '$/original', 'Absolute regular retained original required')
    maximum = 128*1024**2
    identity, count = hashlib.sha256(), 0
    with value.open('rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != source['original_bytes'] or info.st_size > maximum:
            fail('bytes', '$/original', 'Actual complete original size mismatch or cap')
        while block := stream.read(1024**2):
            count += len(block)
            if count > maximum:
                fail('bytes', '$/original', 'Retained original grew beyond cap')
            identity.update(block)
    if count != source['original_bytes'] or identity.hexdigest() != source['original_sha256']:
        fail('hash', '$/original', 'Retained original byte count/hash mismatch')


def reviewed_binding(path, allow_candidate, quantity='secondary_enu_nT'):
    if not allow_candidate:
        fail('dependency', '$/binding', 'Current generic core is candidate-only; actual acceptance registry remains required')
    receipt = _Lexer(read_bounded(path, 16384), max_bytes=16384, max_tokens=4096, defer=False).document()
    keys(receipt, 'schema scope review_reference sources source_inventory_sha256 runtime_epoch policy', '$/binding')
    if (receipt['schema'] != 'magnetic-local-binding-1' or receipt['scope'] != 'local_candidate_only'
            or type(receipt['review_reference']) is not str or not 1 <= len(receipt['review_reference']) <= 512):
        fail('dependency', '$/binding', 'Explicit operator-reviewed local-candidate receipt required')
    conditioned = receipt['runtime_epoch'] in ('physical-gncg-linear-joseph-candidate-2', 'physical-gncg-nonlinear-joseph-candidate-3')
    sources = source_inventory(conditioned=conditioned)
    if receipt['sources'] != sources or receipt['source_inventory_sha256'] != digest(sources):
        fail('dependency', '$/binding', 'Complete reviewed loaded-source inventory mismatch')
    import physical_optimizer as core
    if quantity == 'exact_total_anomaly_nT':
        import physical_nonlinear_optimizer as core
    if conditioned:
        import physical_conditioned_optimizer as core
    epoch = (core.NONLINEAR_EPOCH if quantity == 'exact_total_anomaly_nT' else core.LINEAR_EPOCH) if conditioned else core.RUNTIME_EPOCH
    if receipt['runtime_epoch'] != epoch or receipt['policy'] != core.POLICY:
        fail('dependency', '$/binding', 'Exact public dependency epoch/policy mismatch')
    if conditioned:
        from magnetic_conditioned_adapter import binding_for_sources
        return binding_for_sources(sources, receipt['source_inventory_sha256'], nonlinear=quantity == 'exact_total_anomaly_nT')
    if quantity == 'exact_total_anomaly_nT':
        return core.NonlinearBinding('physical_nonlinear_optimizer.solve_bounded_nonlinear', core.SOURCE_SHA256,
            core.VENDOR_SOURCE_SHA256, receipt['source_inventory_sha256'], core.RUNTIME_EPOCH, core.POLICY)
    return core.OptimizerBinding('physical_optimizer.solve_bounded_physical', core.SOURCE_SHA256,
        sources['magnetic_inverse_precision'], receipt['source_inventory_sha256'], core.RUNTIME_EPOCH, core.POLICY)


def main(argv=None):
    parser = argparse.ArgumentParser(description='M04 actual local supplied-data candidate calibration; no field/online acceptance')
    sub = parser.add_subparsers(dest='operation', required=True)
    for operation in ('validate', 'calibrate'):
        command = sub.add_parser(operation)
        command.add_argument('--request', required=True)
        command.add_argument('--original', required=True)
        command.add_argument('--output', required=True)
        command.add_argument('--data-root')
        command.add_argument('--temp-root', required=True)
        if operation == 'calibrate':
            command.add_argument('--binding-receipt', required=True)
            command.add_argument('--allow-candidate-core', action='store_true')
            command.add_argument('--wall-seconds', type=float, default=7200.)
    for operation in ('import', 'evaluate'):
        command = sub.add_parser(operation)
        command.add_argument('--bundle', required=True)
        command.add_argument('--temp-root', required=True)
    args = parser.parse_args(argv)
    try:
        configure_scratch(args.temp_root)
        if args.operation in ('import', 'evaluate'):
            from magnetic_result_bundle import read_bundle
            imported = read_bundle(external_path(args.bundle))
            result = imported['result']
            summary = dict(schema=result['schema'], status=result['status'], identity=result['identity'],
                selected=result['selected'], generation_sha256=imported['generation_sha256'], claims=result['claims'])
            if args.operation == 'evaluate':
                # This is REUSED sealed evaluation, never a fresh heldout fit.
                # Import replay validates literal residuals/partition/noise and
                # recomputes metrics independently of the saved metric fields.
                from magnetic_calibration import metrics
                import numpy as np
                request = imported['request']
                prediction = result['prediction']
                c = len(prediction['components'])
                row_lookup = {row: i for i, row in enumerate(prediction['rows']['data'])}
                rows = result['partition']['outer_rows']['data']
                values = np.array(prediction['values_nT']['data']).reshape(-1, c)[[row_lookup[i] for i in rows]]
                observed = np.array(request['observations']['values']['data']).reshape(-1, c)[rows]
                noise = request['noise']
                raw_noise = np.array(noise['values']['data']).reshape(noise['values']['shape'])
                ids = [i*c+j for i in rows for j in range(c)]
                subset = raw_noise[np.ix_(ids, ids)] if noise['kind'] == 'full_covariance' else raw_noise[rows]
                replay = metrics(values, observed, dict(kind=noise['kind'], values=subset))
                if replay != result['metrics']['outer']:
                    fail('numerical', '$/metrics', 'Actual reused outer evaluation mismatch')
                summary.update(evaluation='reused_sealed_evaluation', outer=replay)
        else:
            output = data_output(args.output, args.data_root)
            if output.exists() or (args.operation == 'calibrate' and output.with_name(output.name+'.frozen.json').exists()):
                fail('durability', '$/output', 'Fresh external output and model-freeze paths required before fitting')
            raw = read_bounded(args.request, MAX_BYTES)
            handle = parse_request(raw)
            verify_original(args.original, handle.metadata()['source'])
            if args.operation == 'validate':
                from magnetic_survey_bundle import write_geometry
                write_geometry(output, handle)
                plan = plan_geometry(handle)
                summary = dict(schema=plan['schema'], identity=plan['identity'], claims=plan['claims'],
                               original_bytes_verified=True, field_source_verified=False)
            else:
                if not 0. < args.wall_seconds <= 7200.:
                    fail('resource', '$/wall-seconds', 'Finite whole local wall cap in (0,7200] required')
                binding = reviewed_binding(args.binding_receipt, args.allow_candidate_core, handle.metadata()['processing']['quantity'])
                from magnetic_calibration import calibrate
                from magnetic_result_bundle import write_bundle, write_failure
                # Keep vendor diagnostics out of the one-line JSON protocol;
                # actual complete iteration trace is in the bounded result.
                audit = None
                if type(binding).__module__ == 'physical_conditioned_optimizer':
                    from magnetic_conditioned_adapter import OptimizerAudit
                    audit = OptimizerAudit(external_path(args.temp_root)/'optimizer-audit.jsonl', binding.source_inventory_sha256)
                try:
                    with redirect_stdout(sys.stderr):
                        result = calibrate(raw, binding=binding, source_inventory_sha256=binding.source_inventory_sha256,
                                           deadline=monotonic()+args.wall_seconds,
                                           freeze_receipt=output.with_name(output.name+'.frozen.json'),
                                           optimizer_audit=audit.append if audit is not None else None)
                finally:
                    if audit is not None:
                        audit.close()
                request = _Lexer(raw, defer=False).document()
                if result['status'] != 'complete':
                    # A failure ledger is not a fitted bundle or success pointer.
                    # Keep actual candidate/trace evidence, including not_run.
                    write_failure(output, result, request)
                    print(canonical(dict(schema=result['schema'], status='failed', identity=result['identity'],
                        reason=result['diagnostics']['reason'], claims=result['claims'])).decode())
                    return 3
                generation = write_bundle(output, result, request)
                summary = dict(schema=result['schema'], status=result['status'], identity=result['identity'],
                    selected=result['selected'], generation_sha256=generation, original_bytes_verified=True,
                    execution_scope='local_candidate_only', claims=result['claims'])
        print(canonical(summary).decode())
        return 0
    except InputError as error:
        print(canonical(error.envelope()).decode())
        return 5 if error.code == 'durability' else 3 if error.code in ('dependency', 'resource', 'convergence', 'numerical') else 2
    except OSError:
        print(json.dumps(dict(schema='magnetic-input-error-1', code='durability', path='$/local',
            message='Explicit local file operation unavailable'), sort_keys=True))
        return 5
    except ImportError:
        print(json.dumps(dict(schema='magnetic-input-error-1', code='dependency', path='$/local',
            message='Reviewed local source dependency unavailable'), sort_keys=True))
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
