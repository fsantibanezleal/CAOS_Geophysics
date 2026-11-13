"""Run source-pinned corrected-CPU2 nominal and deadline-bound resource trials.

The 20 nominal children each perform a fresh full calibration; they do not use
the workflow archive cache. The 20 cap children execute the predeclared actual
CPU2 fold that hit the 120 s fit deadline in the frozen family0/condition1
matrix. Receipts and scratch are external to the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / '.venv-pipeline' / 'Scripts' / 'python.exe'
FIT_CAP_SECONDS = 120.0
CHILD_TIMEOUT_SECONDS = 1900.0
LEGACY_RESOURCE_RUNNER_SHA256 = frozenset({
    '9466da310040342a161a0c1fd5f0289ea779bbe4fe3cc830d53c2385df076df2',
    '7c0355690166a84618d20477fa8a72da2490d3ff29c75a8b056f6b449e580c46',
})
RESOURCE_RUNNER_PATH = 'scripts\\validate_m02_corrected_resources.py'


def _external(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError('resource output must be an absolute external path')
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or (hasattr(ancestor, 'is_junction') and ancestor.is_junction()):
            raise ValueError('resource output reparse ancestor forbidden')
        if (ancestor / '.git').exists():
            raise ValueError('resource output must be outside repositories')
    resolved = path.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError('resource output must be outside this repository')
    return resolved


def _write(path: Path, value: dict) -> None:
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False, indent=2)
        stream.write('\n')


def _modules():
    sys.path.insert(0, str(ROOT / 'data-pipeline'))
    sys.path.insert(0, str(ROOT / 'tests' / 'numerics'))
    import gravity_irls_corrected_workflow as workflow
    import gravity_irls_pool as pool
    import gravity_survey_l2 as survey
    import test_gravity_irls_corrected_matrix as matrix
    return workflow, pool, survey, matrix


def child(kind: str, output: Path, index: int) -> int:
    output = _external(output)
    workflow, pool, survey, matrix = _modules()
    started = time.monotonic()
    row = {'kind': kind, 'index': index, 'status': 'failed'}
    try:
        family, condition = (0, 0) if kind == 'nominal' else (0, 1)
        request, _, _ = matrix.corrected_request(family, condition)
        runner = workflow._Workflow('cpu2')
        inventory = runner.sources
        row.update(runtime_epoch=runner.engine.RUNTIME_EPOCH,
                   policy=runner.engine.POLICY,
                   request_sha256=survey._digest(request),
                   source_inventory=inventory)
        if kind == 'nominal':
            result = workflow.calibrate(request)
            runner.validate(result, request)
            if result['selection_status'] != 'selected' or result['selected_index'] is None:
                raise ValueError('full nominal CPU2 calibration did not select a candidate')
            row.update(status='passed', result_sha256=result['result_sha256'],
                       selected_index=result['selected_index'],
                       candidate_count=len(result['candidates']),
                       fit_count=len(result['fits']),
                       solver_wall_seconds=result['wall_seconds'])
        elif kind == 'cap':
            admitted = runner.admit(request)
            # Candidate 1 / fold 0 is the frozen family0-condition1 fit whose
            # original24 receipt records wall_cap at 118.234 s.
            fold = admitted['plan']['folds'][0]
            beta = float(l2_beta_candidates()[1])
            fit_started = time.monotonic()
            encoded = runner._fit(admitted, fold['fit_rows'], beta,
                                  fit_started + FIT_CAP_SECONDS)
            fit = pool.decode(encoded)
            problem = workflow.l2._build_problem(admitted['plan']['request'],
                admitted['observations']['gz_up_mgal'],
                {key: admitted['noise'][key] for key in ('kind', 'values')},
                admitted['prior'], fold['fit_rows'], beta,
                observation_rows=admitted['plan']['development_rows'])
            runner.engine.validate_partition(fit, problem, admitted['prior'],
                                             admitted['policy']['irls'])
            status, reason = runner._summary(fit)[:2]
            duration = float(fit.get('wall_seconds', time.monotonic() - fit_started))
            if status != 'nonconverged' or reason != 'wall_cap' or duration > FIT_CAP_SECONDS:
                raise ValueError(f'predeclared capped fit outcome changed: {status}/{reason}/{duration:.6f}s')
            row.update(status='passed', fit_status=status, fit_reason=reason,
                       fit_wall_seconds=duration, fit_iterations=fit['iterations'],
                       fit_result_sha256=survey._digest(fit))
        else:
            raise ValueError('closed resource trial kind')
    except Exception as error:
        row.update(error_type=type(error).__name__, error=str(error))
    row['child_wall_seconds'] = time.monotonic() - started
    row['source_hashes'] = _source_hashes()
    _write(output, row)
    return 0 if row['status'] == 'passed' else 1


def l2_beta_candidates():
    import gravity_irls_corrected_workflow as workflow
    return workflow.l2.BETA_CANDIDATES


def _source_hashes() -> dict[str, str]:
    files = sorted((ROOT / 'data-pipeline').glob('*.py'))
    files += [ROOT / 'tests' / 'numerics' / 'test_gravity_irls_corrected_matrix.py',
              Path(__file__).resolve()]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files}


def _same_sources(actual: dict, expected: dict) -> bool:
    if actual == expected:
        return True
    # Reuse only the earlier sampler's source-bound receipts. The numerical
    # source inventory and matrix test must remain byte-identical; the sole
    # permitted difference is this runner's known hash before resume support.
    legacy = dict(actual)
    if legacy.get(RESOURCE_RUNNER_PATH) not in LEGACY_RESOURCE_RUNNER_SHA256:
        return False
    legacy[RESOURCE_RUNNER_PATH] = expected.get(RESOURCE_RUNNER_PATH)
    return legacy == expected


def _child_running(data_path: Path) -> bool:
    expected = str(data_path.resolve()).casefold()
    for process in psutil.process_iter(['cmdline']):
        try:
            command = process.info.get('cmdline') or []
            if ('--child' in command and expected in ' '.join(command).casefold()):
                return True
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
        except psutil.AccessDenied as error:
            raise RuntimeError('cannot establish whether an earlier resource child is still running') from error
    return False


def _completed(prefix: Path, kind: str, index: int, sources: dict) -> dict | None:
    data = prefix.with_suffix('.json')
    resource = prefix.with_suffix('.resource.json')
    if not data.exists() or not resource.exists():
        return None
    record = json.loads(resource.read_text(encoding='utf-8'))
    science = json.loads(data.read_text(encoding='utf-8'))
    if (record.get('kind') != kind or record.get('index') != index
            or type(record.get('exit_code')) is not int
            or (record['exit_code'] == 0) != (science.get('status') == 'passed')
            or record.get('sampling_complete') is not True
            or record.get('sampled_process_tree_peak_rss_bytes', 0) <= 0
            or not _same_sources(science.get('source_hashes', {}), sources)):
        raise ValueError(f'incomplete or source-mismatched prior receipt: {prefix}')
    return record


def _resume_attempt(output: Path, kind: str, index: int,
                    sources: dict) -> tuple[Path, dict | None]:
    """Reuse a valid receipt or choose a new path after a sampler-only failure.

    Solver failures and source mismatches fail closed. A successful scientific
    child with a complete solver result but incomplete process sampling is
    retried into a new, numbered prefix; its original files are never changed.
    """
    base = output / f'{kind}-{index:02d}'
    for attempt in range(0, 100):
        prefix = base if attempt == 0 else output / f'{kind}-{index:02d}-retry-{attempt}'
        data, resource = prefix.with_suffix('.json'), prefix.with_suffix('.resource.json')
        log = prefix.with_suffix('.log')
        if not any(path.exists() for path in (data, resource, log)):
            return prefix, None
        if data.exists() and resource.exists():
            record = json.loads(resource.read_text(encoding='utf-8'))
            science = json.loads(data.read_text(encoding='utf-8'))
            if (record.get('kind') != kind or record.get('index') != index
                    or type(record.get('exit_code')) is not int
                    or (record['exit_code'] == 0) != (science.get('status') == 'passed')
                    or record.get('sampled_process_tree_peak_rss_bytes', 0) <= 0
                    or not _same_sources(science.get('source_hashes', {}), sources)):
                raise ValueError(f'failed or source-mismatched prior attempt: {prefix}')
            if record.get('sampling_complete') is True:
                return prefix, record
            if record['exit_code'] != 0 or science.get('status') != 'passed':
                raise ValueError(f'sampler failure is not independently recoverable: {prefix}')
            # Keep the failed resource measurement and child result immutable.
            continue
        if data.exists() and not resource.exists():
            if _child_running(data):
                raise ValueError(f'prior child is still running: {prefix}')
            science = json.loads(data.read_text(encoding='utf-8'))
            if (science.get('status') != 'passed'
                    or not _same_sources(science.get('source_hashes', {}), sources)):
                raise ValueError(f'incomplete or source-mismatched prior child result: {prefix}')
            # The child finished successfully but the parent ended before the
            # sampler could persist a receipt. Preserve it and rerun under a
            # fresh prefix to obtain an auditable process-tree measurement.
            continue
        if log.exists() and not data.exists() and not resource.exists():
            if _child_running(data):
                raise ValueError(f'prior child is still running: {prefix}')
            # An interrupted child has no terminal scientific receipt. Retain
            # the log and retry only after confirming its exact output is idle.
            continue
        # A partial write without both terminal receipts is ambiguous. Preserve
        # it and require an explicit diagnosis rather than guessing it is safe.
        raise ValueError(f'incomplete prior attempt without a complete pair of receipts: {prefix}')
    raise RuntimeError(f'resource trial exceeded retry path limit: {kind}-{index:02d}')


def _summary_target(output: Path) -> Path:
    base = output / 'summary.json'
    if not base.exists():
        return base
    for attempt in range(1, 100):
        candidate = output / f'summary-retry-{attempt}.json'
        if not candidate.exists():
            return candidate
    raise RuntimeError('resource summary exceeded retry path limit')


def run(output: Path, resume: bool = False) -> int:
    output = _external(output)
    output.mkdir(parents=True, exist_ok=resume)
    sources = _source_hashes()
    measurements = []
    for kind in ('cap', 'nominal'):
        for index in range(20):
            if resume:
                prefix, done = _resume_attempt(output, kind, index, sources)
                if done is not None:
                    measurements.append(done)
                    continue
            else:
                prefix = output / f'{kind}-{index:02d}'
            child_path = prefix.with_suffix('.json')
            resource_path = prefix.with_suffix('.resource.json')
            log_path = prefix.with_suffix('.log')
            if any(p.exists() for p in (child_path, resource_path, log_path)):
                raise FileExistsError(f'preserving incomplete prior attempt: {prefix}')
            env = dict(os.environ)
            for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
                env[key] = '1'
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            with log_path.open('xb') as log:
                process = subprocess.Popen([str(VENV_PYTHON), str(Path(__file__).resolve()),
                    '--child', kind, '--output', str(child_path), '--index', str(index)],
                    cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
                root = psutil.Process(process.pid)
                peak = 0
                errors = []
                start = time.monotonic()
                killed = False
                while process.poll() is None:
                    try:
                        tree = (root, *root.children(recursive=True))
                        peak = max(peak, sum(p.memory_info().rss for p in tree if p.is_running()))
                    except psutil.NoSuchProcess:
                        pass
                    except OSError as error:
                        errors.append({'type': type(error).__name__,
                                       'winerror': getattr(error, 'winerror', None)})
                    if time.monotonic() - start > CHILD_TIMEOUT_SECONDS:
                        for owned in reversed(root.children(recursive=True)):
                            try:
                                owned.kill()
                            except psutil.NoSuchProcess:
                                pass
                        process.kill()
                        killed = True
                        break
                    time.sleep(.05)
                code = process.wait()
            record = {'kind': kind, 'index': index, 'exit_code': code,
                      'hard_timeout': killed, 'sampled_process_tree_peak_rss_bytes': peak,
                      'wall_seconds': time.monotonic() - start,
                      'sampling_complete': not errors, 'sampling_errors': errors}
            _write(resource_path, record)
            measurements.append(record)
            print(json.dumps(record, sort_keys=True), flush=True)
            if code != 0 or errors:
                print(f'FAIL {kind}-{index:02d}; retaining receipt and stopping; '
                      'a later --resume retries only a successful child with incomplete sampling', flush=True)
                break
        # Sampling errors invalidate the resource receipt even when the child
        # solver returned its expected scientific status. Stop the outer loop
        # as well as the inner loop; continuing to nominal calibrations after
        # an incomplete cap measurement would consume compute without making
        # this gate more conclusive.
        if measurements and (measurements[-1].get('exit_code') != 0
                             or measurements[-1].get('sampling_complete') is not True):
            break
    groups = {}
    for kind in ('cap', 'nominal'):
        actual = [row for row in measurements if row['kind'] == kind]
        groups[kind] = {'count': len(actual), 'passed': sum(r['exit_code'] == 0 for r in actual),
                        'sampling_complete_count': sum(r['sampling_complete'] for r in actual),
                        'sampled_process_tree_peak_rss_p95_bytes':
                            float(__import__('numpy').percentile(
                                [r['sampled_process_tree_peak_rss_bytes'] for r in actual], 95)) if actual else None,
                        'total_wall_p95_seconds':
                            float(__import__('numpy').percentile([r['wall_seconds'] for r in actual], 95)) if actual else None,
                        'resource_upper_proof': False, 'host_accepted': False}
    summary = _summary_target(output)
    _write(summary, {'runtime_epoch': 'm02-survey-irls-cpu-2-terminal-certificate-exact-q-replay-legacy-init-1',
                     'source_hashes': sources,
                     'accepted_legacy_runner_sha256': sorted(LEGACY_RESOURCE_RUNNER_SHA256),
                     'groups': groups})
    print(json.dumps({'summary': str(summary), 'groups': groups}, sort_keys=True), flush=True)
    return int(any(group['count'] != 20 or group['passed'] != 20
                   or group['sampling_complete_count'] != 20 for group in groups.values()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--child', choices=('cap', 'nominal'), help=argparse.SUPPRESS)
    parser.add_argument('--index', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        if args.index is None or not 0 <= args.index < 20:
            parser.error('child index must be 0..19')
        return child(args.child, args.output, args.index)
    return run(args.output, args.resume)


if __name__ == '__main__':
    raise SystemExit(main())
