"""Replay exact terminal weights and projected KKT for an archived IRLS fit book.

Research-only diagnostic. It does not modify the archive, approve a terminal
state, or change the production three-transition rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from time import monotonic

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_name] = '1'

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'data-pipeline'))

import gravity_irls_corrected as corrected
import gravity_irls_corrected_workflow as workflow
import gravity_irls_original as original
import gravity_irls_pool as pool
import gravity_l2 as l2
import gravity_workflow_io as transport


def _external(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise ValueError(f'{label}: absolute path required')
    if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
           for p in (path, *path.parents)):
        raise ValueError(f'{label}: reparse-point path refused')
    resolved = path.resolve(strict=False)
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError(f'{label}: path must be outside the repository')
    if any((p / '.git').exists() for p in (resolved, *resolved.parents)):
        raise ValueError(f'{label}: repository storage refused')
    return resolved


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def audit(archive_path: Path, candidates: list[int], folds: list[int]) -> dict:
    archive_path = _external(archive_path, 'archive')
    if archive_path.suffix != '.gza' or not archive_path.is_file():
        raise ValueError('archive: one existing .gza file required')
    archive = transport.read_archive(archive_path.parent, archive_path.name)
    result = archive['result']
    owner_workflow = workflow._Workflow('cpu3')
    if (result['runtime_epoch'] != original.RUNTIME_EPOCH
            or result['source_inventory'] != owner_workflow.sources):
        raise ValueError('archive is not bound to the loaded current cpu3 source inventory')
    accepted = owner_workflow.admit(archive['request'])
    plan = accepted['plan']
    policy = accepted['policy']['irls']
    observations = accepted['observations']['gz_up_mgal']
    noise = {key: accepted['noise'][key] for key in ('kind', 'values')}
    records = []

    for candidate in candidates:
        if not 0 <= candidate < len(accepted['policy']['beta_candidates']):
            raise ValueError(f'candidate out of range: {candidate}')
        for fold in folds:
            if fold not in range(len(plan['folds'])):
                raise ValueError(f'fold out of range: {fold}')
            fit_index = candidate * len(plan['folds']) + fold
            fit = pool.decode(result['fits'][fit_index])
            if not fit['stages'] or not len(fit['models_q']):
                raise ValueError(f'fit {fit_index} has no complete terminal stage')
            native_q = np.array(fit['models_q'][-1], dtype=np.float64, copy=True)
            stage_q = fit['stages'][-1]['inner']['trace']['models_q'][-1]
            if not np.array_equal(native_q, stage_q):
                raise ValueError(f'fit {fit_index} archive terminal differs from its native stage trace')
            rows = plan['folds'][fold]['fit_rows']
            owner = original.GravityIRLSPartition(
                plan['request'], observations, noise, accepted['prior'], rows,
                accepted['policy']['beta_candidates'][candidate],
                observation_rows=plan['development_rows'], deadline=float(monotonic() + 120.0))
            try:
                stage = corrected._stage(owner.problem, native_q, policy, 20,
                                         fit['initial_epsilon'])
                recorded_weights = fit['stages'][-1]['adopted_weights']
                recomputed_weights = stage['weights'][0]
                regularization = stage['problem']['regularization']
                smallness = (float(stage['problem']['beta_engine'])
                    * float(regularization.multipliers[0])
                    * regularization.objfcts[0].W.diagonal() ** 2
                    * recomputed_weights)
                if not np.isfinite(smallness).all() or np.any(smallness <= 0.0):
                    raise ValueError(f'fit {fit_index} lacks a positive smallness diagonal')
                adapter = owner._adapter(stage['problem'], native_q, 20, stage)
                gradient = adapter.evaluate(native_q, True)[1]
                projected = l2._kkt_gradient(native_q, gradient, adapter.lower, adapter.upper)
                absolute_kkt = float(np.linalg.norm(projected, np.inf))
                relative_weight_difference = float(np.linalg.norm(
                    recomputed_weights - recorded_weights, np.inf) /
                    max(1.0, float(np.linalg.norm(recorded_weights, np.inf))))
                changes = fit['terminal']['stage_changes']
                records.append(dict(candidate=candidate, fold=fold, fit_index=fit_index,
                    original_status=fit['terminal']['status'],
                    original_reason=fit['terminal']['reason'],
                    final_inner_status=fit['stages'][-1]['inner']['status'],
                    final_inner_reason=fit['stages'][-1]['inner']['reason'],
                    stage_index=fit['stages'][-1]['index'],
                    weight_updates=fit['terminal']['weight_updates'],
                    final_three_changes=[dict(change) for change in changes[-3:]],
                    terminal_q_sha256=l2.survey._digest(native_q),
                    recorded_weights_sha256=l2.survey._digest(recorded_weights),
                    recomputed_weights_sha256=l2.survey._digest(recomputed_weights),
                    weights_array_equal=bool(np.array_equal(recomputed_weights, recorded_weights)),
                    relative_weight_difference=relative_weight_difference,
                    positive_smallness_diagonal_min=float(np.min(smallness)),
                    projected_kkt_inf=absolute_kkt,
                    operator_sha256=stage['operator_sha256'],
                    weight_sha256=stage['weight_sha256']))
            finally:
                owner.close()

    receipt = dict(schema='gravity-irls-terminal-certificate-audit-1',
        research_only=True, terminal_policy_changed=False, production_acceptance=False,
        archive_path=str(archive_path), archive_sha256=_sha_file(archive_path),
        request_sha256=result['request_sha256'], result_sha256=result['result_sha256'],
        source_inventory_sha256=l2.survey._digest(result['source_inventory']),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        candidates=candidates, folds=folds, records=records)
    receipt['receipt_sha256'] = l2.survey._digest(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--candidate', type=int, action='append', required=True)
    parser.add_argument('--fold', type=int, action='append', default=None)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = _external(args.output, 'receipt')
    if output.exists():
        raise FileExistsError(output)
    folds = args.fold if args.fold is not None else [0, 1, 2]
    receipt = audit(args.archive, args.candidate, folds)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(receipt, stream, sort_keys=True, allow_nan=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status='research_only', records=len(receipt['records']),
        archive_sha256=receipt['archive_sha256'], receipt_sha256=receipt['receipt_sha256']),
        sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
