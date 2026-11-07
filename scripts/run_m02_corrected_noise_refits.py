"""Run one source-bound CPU2 32-draw fixed-recipe refit and retain it first.

The immutable archive is written before replay validation. If validation finds
a production defect, the exact expensive fit batch remains available for
diagnosis and is never silently rerun or discarded.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def _external(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError('noise-refit evidence requires an absolute external path')
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or (hasattr(ancestor, 'is_junction') and ancestor.is_junction()):
            raise ValueError('noise-refit evidence reparse ancestor forbidden')
        if (ancestor / '.git').exists():
            raise ValueError('noise-refit evidence must be outside repositories')
    resolved = path.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError('noise-refit evidence must be outside repository')
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--temp-root', type=Path, required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    data, temp, report_path, log_path = map(_external,
        (args.data_root, args.temp_root, args.report, args.log))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists() or log_path.exists():
        raise FileExistsError('preserving pre-existing noise-refit report/log')
    sys.path.insert(0, str(ROOT / 'data-pipeline'))
    import gravity_irls_corrected_workflow as corrected
    import gravity_irls_pool as pool
    import gravity_noise_refits as refits
    import gravity_workflow_io as workflow

    calibration = workflow.verify_calibration(workflow.read_archive(data, args.input))
    request, frozen = calibration['request'], calibration['result']
    engine = corrected._Workflow('cpu2')
    report = {'runtime_epoch': engine.engine.RUNTIME_EPOCH,
              'policy': engine.engine.POLICY,
              'source_inventory': engine.sources,
              'request_sha256': frozen['request_sha256'],
              'calibration_sha256': frozen['result_sha256'],
              'status': 'computing'}
    with log_path.open('x', encoding='utf-8') as log, redirect_stdout(log):
        result = refits.refit_gravity_noise(request, frozen)
        # Custody first: the complete actual result survives a subsequent
        # strict replay rejection and can be inspected without recomputing.
        archive = workflow.publish_archive(data, temp, args.output, result)
        decoded = refits._decode_records(result['records'])
        fits = decoded['fits']
        counts = {}
        for fit in fits:
            if fit.get('schema') == 'gravity-corrected-unstarted-1':
                key = f"{fit['status']}:{fit['reason']}"
            else:
                raw = pool.decode(fit)
                status, reason = engine._summary(raw)[:2]
                key = f'{status}:{reason}'
            counts[key] = counts.get(key, 0) + 1
        report.update(archive=str(archive), result_sha256=result['result_sha256'],
                      refit_count=len(fits), success_count=int(result['successful'].sum()),
                      outcome_counts=counts, solver_wall_seconds=result['wall_seconds'],
                      result_bytes=archive.stat().st_size,
                      result_sha256_file=hashlib.sha256(archive.read_bytes()).hexdigest())
        try:
            refits.validate_noise_refits(result, request, frozen)
            report['status'] = 'replay_passed'
        except Exception as error:
            report.update(status='replay_failed', error_type=type(error).__name__,
                          error=str(error))
    with report_path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, sort_keys=True, allow_nan=False, indent=2)
        stream.write('\n')
    print(json.dumps(report, sort_keys=True))
    return 0 if report['status'] == 'replay_passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
