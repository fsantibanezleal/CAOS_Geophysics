"""No-fit full original workflow phase gate; never numerical/native admission."""
import argparse
import hashlib
import os
from pathlib import Path
import sys


def workflow_allocation(raw):
    from magnetic_survey_json import parse_request
    from magnetic_survey import plan_geometry
    from magnetic_original_adapter import allocation, source_binding, LIMIT
    import physical_original_optimizer as core
    import gravity_l2_metric as metric
    public_sources = source_binding()
    sources = dict(public_sources)
    metric_hash = hashlib.sha256(Path(metric.__file__).read_bytes()).hexdigest()
    if metric.SOURCE_SHA256 != metric_hash or LIMIT != 805306368:
        raise ValueError('Exact original phase source and768MiB envelope required')
    sources['gravity_l2_metric'] = metric_hash
    handle = parse_request(raw)
    metadata, plan = handle.metadata(), plan_geometry(handle)
    if (metadata['policy']['optimizer_binding'] != dict(accepted_source=core.SOURCE_SHA256,
            accepted_export='physical_original_optimizer.solve_bounded_linear', epoch=core.LINEAR_EPOCH)
            or metadata['processing']['quantity'] not in ('secondary_enu_nT', 'linear_tmi_nT')):
        raise ValueError('Exact current public original LINEAR request required')
    preflight = plan['preflight']
    fit_rows = [len(f['fit_rows']['data']) for f in plan['partition']['folds']]
    final_rows = len(plan['final_refit_rows']['data'])
    phases = []
    for count in dict.fromkeys([*fit_rows, final_rows]):
        components = count*preflight['components']
        item = dict(fit_rows=count, fit_components=components, plan=None, status='refused', reason=None)
        try:
            actual = allocation(3*preflight['rows'], components, preflight['active_cells'],
                metadata['noise']['kind'] == 'full_covariance', preflight['conservative_bytes'],
                preflight['components'])
            if (actual['admitted_bytes'] != LIMIT or actual['fit_components'] != components
                    or actual['parameters'] != preflight['active_cells']
                    or actual['source_binding'] != public_sources):
                raise ValueError('Production allocation identity drift')
            item.update(status='within_original_envelope', plan=actual)
        except ValueError as error:
            item['reason'] = str(error)
        phases.append(item)
    passed = all(phase['status'] == 'within_original_envelope' for phase in phases)
    return dict(schema='magnetic-original-workflow-allocation-1',
        observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        status='within_original_envelope' if passed else 'refused',
        request_sha256=hashlib.sha256(raw).hexdigest(), original_sha256=metadata['source']['original_sha256'],
        quantity=metadata['processing']['quantity'], source_components=3*preflight['rows'],
        active_cells=preflight['active_cells'], noise_kind=metadata['noise']['kind'],
        original_preflight_bytes=preflight['conservative_bytes'], original_admitted_bytes=LIMIT,
        inner_fit_rows=fit_rows, final_refit_rows=final_rows, phases=phases, sources=sources,
        original_bytes_verified=False, fit_started=False, native_process_started=False,
        full_method_accepted=False, field_source_verified=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--dependencies', required=True, nargs='+')
    parser.add_argument('--data-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    sys.path[:0] = [str(Path(__file__).parents[1]/'data-pipeline'),
                   *(str(Path(root).resolve(strict=True)) for root in args.dependencies)]
    from magnetic_local_paths import external_path
    from magnetic_survey_json import canonical, MAX_BYTES
    from run_magnetic_survey import read_bounded
    root = external_path(args.data_root)
    request, output = external_path(args.request), external_path(args.output)
    if (not root.is_dir() or not request.is_relative_to(root) or not output.is_relative_to(root)
            or not output.parent.is_dir() or output.exists()):
        raise ValueError('Existing external input root and fresh output required')
    report = workflow_allocation(read_bounded(request, MAX_BYTES))
    with output.open('xb') as stream:
        stream.write(canonical(report))
        stream.flush()
        os.fsync(stream.fileno())
    print(report['status'])
    return 0 if report['status'] == 'within_original_envelope' else 2


if __name__ == '__main__':
    raise SystemExit(main())
