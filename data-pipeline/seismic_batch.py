"""Portable coordinated seismic candidate bake; never writes a catalogue.

prepare is CPU-only. run requires the explicit --gpu-released handoff flag.
Only four FWI child folders in the parent-owned candidate root may be written.
Two independent fresh interpreters share no CUDA tensors and retain all 28 calls.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT/'data/experiments'
CANDIDATE = EXPERIMENTS/'fwi-candidate'
RECEIPTS = EXPERIMENTS/'fwi-batch-receipts'
PLAN = RECEIPTS/'plan.json'
LEDGER = RECEIPTS/'ledger.json'
MEMORY_LOG = RECEIPTS/'memory.jsonl'
FROZEN_SOURCE = hashlib.sha256((ROOT/'data-pipeline/seismic.py').read_bytes()).hexdigest()
FROZEN_GEOLOGY = hashlib.sha256((ROOT/'data-pipeline/geology.py').read_bytes()).hexdigest()
VRAM_LIMIT_BYTES = 6_000_000_000
ALLOCATOR_FRACTION = .29
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, obj):
    # Diagnostic file, or a validated FWI child path, never a canonical target.
    assert path.resolve().is_relative_to(EXPERIMENTS.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f'.{os.getpid()}.partial')
    temporary.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def modules():
    sys.path.insert(0, str(ROOT/'data-pipeline'))
    from geology import registry, VARIANTS
    from rebuild import annotate, save, generator_fingerprint, RELEASE_VERSION
    assert RELEASE_VERSION
    assert digest(ROOT/'data-pipeline/seismic.py') == FROZEN_SOURCE, 'Frozen seismic source changed'
    assert digest(ROOT/'data-pipeline/geology.py') == FROZEN_GEOLOGY, 'Frozen geological target changed'
    return registry, VARIANTS, annotate, save, generator_fingerprint


def result_path(case_id, variant):
    assert case_id in ('FWI_LAYERED', 'FWI_FAULT', 'FWI_CYCLE_SKIP', 'FWI_NOISY')
    assert variant in ('reference', 'contrast', 'noise', 'acquisition', 'coverage', 'regularization')
    path = (CANDIDATE/case_id/f'{variant}.json').resolve()
    assert path.is_relative_to(CANDIDATE.resolve())
    return path


def save_result(path, result, save):
    temporary = path.with_suffix(f'.{os.getpid()}.partial.json')
    receipt = save(temporary, result)
    temporary.replace(path)
    return receipt


def complete(path, fingerprint):
    if not path.exists():
        return False
    try:
        run = json.loads(path.read_text(encoding='utf-8'))
        if run.get('provenance', {}).get('generator_fingerprint') != fingerprint:
            return False
        assert run['parameters']['iterations'] == 28
        assert run['id'] == path.parent.name and run['variant'] == path.stem
        assert set(run['methods']) == {'fwi-l2', 'fwi-multiscale'}
        for method in run['methods'].values():
            assert method['solver']['optimizer_calls'] == 112
            assert method['frames'][-1] == method['model']
            assert method['state_identity']['final_frame_index'] == len(method['frames'])-1
            assert method['solver']['terminal_update_evaluated']
            assert method['evaluation']['status'] in ('recovered', 'failed', 'unresolved', 'negative-control')
        return True
    except (AssertionError, ValueError, KeyError, TypeError):
        return False


def prepare(reuse_directory=None):
    """Freeze all settings and create a resumable full 24-condition plan on CPU."""
    registry, variants, annotate, save, fingerprint = modules()
    from rebuild import RELEASE_VERSION
    generation = fingerprint('seismic', 28, 180)
    references, jobs = [], []
    current = (ROOT/'data-pipeline/seismic.py').read_bytes()
    for case in registry():
        if case['family'] != 'seismic':
            continue
        if reuse_directory is not None:
            source = reuse_directory/f"fwi-{case['id']}-reference.json"
            run = json.loads(source.read_text(encoding='utf-8'))
            original_digest = run['probe_solver_sha256']
            labels = []
            if original_digest != FROZEN_SOURCE:
                # A byte-exact proof accepts only this declared label migration.
                assert current.count(b'"negative-control"') == 1
                restored = current.replace(b'"negative-control"', b'"expected-negative-control"')
                assert hashlib.sha256(restored).hexdigest() == original_digest, 'Not an alias-only source migration'
                for key, method in run['methods'].items():
                    if method['evaluation']['status'] == 'expected-negative-control':
                        method['evaluation']['status'] = 'negative-control'
                        labels.append(key)
            assert run['id'] == case['id'] and run['seed'] == case['seed'] and run['variant'] == 'reference'
            run['provenance'] = dict(reference_reuse=dict(
                source_artifact_sha256=digest(source), source_solver_sha256=original_digest,
                normalized_solver_sha256=FROZEN_SOURCE,
                migration='Only evaluation status expected-negative-control becomes negative-control' if labels else 'No label change',
                byte_equivalence_verified=True, changed_method_labels=labels))
            annotate(run, case, run['parameters']['runtime_seconds'], iterations=28, epochs=180)
            destination = result_path(case['id'], 'reference')
            if not complete(destination, generation):
                receipt = save_result(destination, run, save)
            else:
                receipt = dict(sha256=digest(destination), bytes=destination.stat().st_size)
            assert complete(destination, generation)
            references.append(dict(case=case['id'], path=str(destination), **receipt))
        for variant, _, _ in variants:
            jobs.append(dict(case=case, variant=variant))
    plan = dict(
        schema='inverse-earth.fwi-candidate-plan/v1', version=RELEASE_VERSION,
        candidate_root=str(CANDIDATE), solver_sha256=FROZEN_SOURCE, geology_sha256=FROZEN_GEOLOGY,
        generator_fingerprint=generation, reference_reuse=references, jobs=jobs,
        controls=dict(iterations_per_stage=28, actual_calls_per_pair=196, workers=2,
                      per_process_allocator_fraction=ALLOCATOR_FRACTION,
                      total_vram_guard_bytes=VRAM_LIMIT_BYTES, threads_per_worker=2),
        gpu_state='waiting for explicit GPU release; preparation allocated no CUDA tensors')
    atomic_json(PLAN, plan)
    pending = sum(not complete(result_path(j['case']['id'], j['variant']), generation) for j in jobs)
    print(json.dumps(dict(conditions=len(jobs), reused_references=len(references), pending_jobs=pending,
                          solver_sha256=FROZEN_SOURCE, generator_fingerprint=generation, plan=str(PLAN))), flush=True)


def worker(case_id, variant):
    registry, _, annotate, save, fingerprint = modules()
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    assert plan['solver_sha256'] == FROZEN_SOURCE and plan['geology_sha256'] == FROZEN_GEOLOGY
    assert plan['generator_fingerprint'] == fingerprint('seismic', 28, 180)
    import torch
    import seismic
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.cuda.set_per_process_memory_fraction(ALLOCATOR_FRACTION, 0)
    torch.cuda.reset_peak_memory_stats()
    case = next(c for c in registry() if c['id'] == case_id)
    frozen_fingerprint = fingerprint('seismic', 28, 180)
    path = result_path(case_id, variant)
    started = time.perf_counter()
    print(json.dumps(dict(event='start', case=case_id, variant=variant, pid=os.getpid())), flush=True)

    def progress(state):
        if state['update'] in (8, 16, 24, 28):
            print(json.dumps(dict(event='stage', case=case_id, variant=variant,
                                  peak_allocated=torch.cuda.max_memory_allocated(),
                                  peak_reserved=torch.cuda.max_memory_reserved(), **state)), flush=True)

    run = seismic.solve_case(case, variant, iterations=28, progress=progress)
    assert fingerprint('seismic', 28, 180) == frozen_fingerprint, 'Generator changed during solve'
    elapsed = time.perf_counter()-started
    run['provenance'] = dict(candidate_execution=dict(
        solver_sha256=FROZEN_SOURCE, geology_sha256=FROZEN_GEOLOGY, threads=2,
        peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved(),
        allocator_fraction=ALLOCATOR_FRACTION, independent_worker=True))
    annotate(run, case, elapsed, iterations=28, epochs=180)
    receipt = save_result(path, run, save)
    assert complete(path, frozen_fingerprint)
    print(json.dumps(dict(event='done', case=case_id, variant=variant, seconds=elapsed,
                          peak_allocated=torch.cuda.max_memory_allocated(),
                          peak_reserved=torch.cuda.max_memory_reserved(), **receipt,
                          evaluations={k:m['evaluation'] for k,m in run['methods'].items()})), flush=True)


def gpu_state():
    output = subprocess.check_output(
        ['nvidia-smi', '--query-gpu=memory.used,utilization.gpu,temperature.gpu', '--format=csv,noheader,nounits'],
        text=True, creationflags=CREATE_NO_WINDOW, timeout=10)
    memory, utilization, temperature = [int(x.strip()) for x in output.strip().splitlines()[0].split(',')]
    return dict(memory_used_bytes=memory*1024**2, utilization_percent=utilization, temperature_c=temperature)


def stop_owned_worker(process):
    """Windows venv launchers can spawn the real interpreter as a child.

    Stop only this still-live Popen process tree, not a name-matched Python list.
    """
    if process.poll() is not None:
        return
    if os.name == 'nt':
        stopped = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                 capture_output=True, text=True, creationflags=CREATE_NO_WINDOW, timeout=20)
        if stopped.returncode and process.poll() is None:
            raise RuntimeError(f'Could not stop owned worker tree {process.pid}: {stopped.stderr}')
    else:
        process.terminate()
    process.wait(timeout=20)


def coordinate(workers, limit):
    modules()
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    assert plan['solver_sha256'] == FROZEN_SOURCE and plan['geology_sha256'] == FROZEN_GEOLOGY
    from rebuild import generator_fingerprint
    assert plan['generator_fingerprint'] == generator_fingerprint('seismic', 28, 180)
    pending = deque(j for j in plan['jobs']
                    if not complete(result_path(j['case']['id'], j['variant']), plan['generator_fingerprint']))
    if limit:
        pending = deque(list(pending)[:limit])
    active, done, events = [], [], []
    started = time.perf_counter()
    baseline = gpu_state()
    # Preflight headroom includes non-allocator context/driver overhead. Baseline
    # alone is never treated as authorization; CLI handoff flag is also required.
    predicted_bytes = baseline['memory_used_bytes']+workers*2_650_000_000
    if predicted_bytes >= VRAM_LIMIT_BYTES:
        raise RuntimeError(f'Insufficient monitored headroom: {baseline}; no GPU worker launched')
    maximum = baseline['memory_used_bytes']
    last_report = 0.
    print(json.dumps(dict(event='coordinator_start', workers=workers, jobs=len(pending), baseline=baseline)), flush=True)
    try:
        while pending or active:
            while pending and len(active) < workers:
                job = pending.popleft()
                log_path = RECEIPTS/f"worker-{job['case']['id']}-{job['variant']}.log"
                handle = log_path.open('w', encoding='utf-8')
                environment = os.environ.copy()
                environment.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2')
                process = subprocess.Popen(
                    [sys.executable, '-u', str(Path(__file__).resolve()), 'worker',
                     '--case', job['case']['id'], '--variant', job['variant'], '--gpu-released',
                     '--output', str(CANDIDATE), '--receipts', str(RECEIPTS)],
                    cwd=ROOT, env=environment, stdout=handle, stderr=subprocess.STDOUT,
                    creationflags=CREATE_NO_WINDOW)
                active.append(dict(job=job, process=process, log=handle, log_path=log_path))
                print(json.dumps(dict(event='worker_launch', pid=process.pid, case=job['case']['id'],
                                      variant=job['variant'], log=str(log_path))), flush=True)
            state = gpu_state()
            maximum = max(maximum, state['memory_used_bytes'])
            with MEMORY_LOG.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(dict(time=time.time(), workers=len(active), **state))+'\n')
            if state['memory_used_bytes'] >= VRAM_LIMIT_BYTES:
                # Only handles created above can be stopped; unrelated jobs are never touched.
                victim = active.pop()
                stop_owned_worker(victim['process'])
                victim['log'].close()
                pending.appendleft(victim['job'])
                workers = 1
                events.append(dict(event='vram_guard_serial_fallback', **state))
                print(json.dumps(events[-1]), flush=True)
                if not active:
                    raise RuntimeError('VRAM guard reached with one worker; stopped own worker, external load requires review')
            for record in active[:]:
                code = record['process'].poll()
                if code is None:
                    continue
                record['log'].close()
                active.remove(record)
                job = record['job']
                path = result_path(job['case']['id'], job['variant'])
                if code != 0 or not complete(path, plan['generator_fingerprint']):
                    raise RuntimeError(f"Worker failed ({code}); inspect {record['log_path']}")
                item = dict(case=job['case']['id'], variant=job['variant'], sha256=digest(path), bytes=path.stat().st_size)
                done.append(item)
                print(json.dumps(dict(event='verified_complete', **item)), flush=True)
            if time.perf_counter()-last_report >= 30:
                last_report = time.perf_counter()
                print(json.dumps(dict(event='progress', done=len(done), active=len(active), pending=len(pending),
                                      seconds=time.perf_counter()-started, **state)), flush=True)
            atomic_json(LEDGER, dict(status='running' if pending or active else 'complete',
                                    source_sha256=FROZEN_SOURCE, completed=done, events=events,
                                    peak_total_vram_bytes=maximum, seconds=time.perf_counter()-started))
            if pending or active:
                time.sleep(2)
    finally:
        for record in active:
            if record['process'].poll() is None:
                stop_owned_worker(record['process'])
            record['log'].close()
    print(json.dumps(dict(event='coordinator_complete', jobs=len(done), seconds=time.perf_counter()-started,
                          peak_total_vram_bytes=maximum)), flush=True)


def main():
    global CANDIDATE, RECEIPTS, PLAN, LEDGER, MEMORY_LOG
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'run', 'worker'])
    parser.add_argument('--gpu-released', action='store_true')
    parser.add_argument('--workers', type=int, choices=[1, 2], default=2)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--output', type=Path, default=CANDIDATE)
    parser.add_argument('--receipts', type=Path, default=RECEIPTS)
    parser.add_argument('--reuse-references', type=Path, help='Optional original local probe directory; otherwise all 24 run')
    parser.add_argument('--case')
    parser.add_argument('--variant')
    args = parser.parse_args()
    CANDIDATE, RECEIPTS = args.output.resolve(), args.receipts.resolve()
    for location in (CANDIDATE, RECEIPTS):
        if location == EXPERIMENTS.resolve() or not location.is_relative_to(EXPERIMENTS.resolve()):
            parser.error('Output and receipts must be distinct children of this repository data/experiments directory')
    if CANDIDATE == RECEIPTS or CANDIDATE.is_relative_to(RECEIPTS) or RECEIPTS.is_relative_to(CANDIDATE):
        parser.error('Keep receipts separate from candidate child artifacts')
    PLAN, LEDGER, MEMORY_LOG = RECEIPTS/'plan.json', RECEIPTS/'ledger.json', RECEIPTS/'memory.jsonl'
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    if args.mode == 'prepare':
        prepare(args.reuse_references)
    else:
        if not args.gpu_released:
            parser.error('GPU modes require explicit parent release; do not infer release from idle GPU state')
        if args.mode == 'worker':
            worker(args.case, args.variant)
        else:
            coordinate(args.workers, args.limit)


if __name__ == '__main__':
    main()
