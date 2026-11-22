"""Research-only bounded continuation of an archived cpu3 IRLS fit at epsilon floor.

This does not alter or rewrite a calibration archive. It reuses its exact request,
source inventory and terminal fit state, then independently replays each additional
floor solve. Results are written only to a new file outside the repository.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from time import monotonic

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'data-pipeline'))

import gravity_irls_corrected as corrected
import gravity_irls_original as original
import gravity_irls_pool as pool
import gravity_irls_corrected_workflow as corrected_workflow
import gravity_workflow_io as transport
import gravity_irls as plain


def _external(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise ValueError(f'{label}: absolute path required')
    original = path
    if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
           for p in (original, *original.parents)):
        raise ValueError(f'{label}: reparse-point path refused')
    path = original.resolve(strict=False)
    if path == ROOT or ROOT in path.parents:
        raise ValueError(f'{label}: output/input must be outside the repository')
    if any((p / '.git').exists() for p in (path, *path.parents)):
        raise ValueError(f'{label}: repository storage refused')
    return path


def _write_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, allow_nan=False, indent=2) + '\n'
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(payload)


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _archived_terminal_q(fit: dict) -> np.ndarray:
    """Return the exact native terminal state and reject inconsistent books."""
    if not fit['stages'] or not len(fit['models_q']):
        raise ValueError('research: archived fit has no native terminal q')
    q = np.array(fit['models_q'][-1], dtype=np.float64, copy=True)
    stage_trace = fit['stages'][-1]['inner']['trace']['models_q']
    if not len(stage_trace) or q.shape != stage_trace[-1].shape:
        raise ValueError('research: archived native terminal q shape')
    if not np.array_equal(q, stage_trace[-1]):
        raise ValueError('research: archived terminal q differs from final native stage')
    return q


def run(args) -> dict:
    data_root = _external(args.archive_root, 'archive root')
    output = _external(args.output, 'research receipt')
    archive_path = data_root / args.archive_name
    if archive_path.parent != data_root or archive_path.suffix != '.gza' or not archive_path.is_file():
        raise ValueError('archive: one existing flat .gza file required')
    if output.exists():
        raise FileExistsError(output)

    archive = transport.read_archive(data_root, args.archive_name)
    result = archive['result']
    workflow = corrected_workflow._Workflow('cpu3')
    if result['runtime_epoch'] != original.RUNTIME_EPOCH or result['source_inventory'] != workflow.sources:
        raise ValueError('research: archive is not exact current cpu3 source evidence')
    if result['selection_status'] not in ('insufficient_candidates', 'selected'):
        raise ValueError('research: closed original calibration result required')
    fit_index = args.candidate * 3 + args.fold
    if not 0 <= args.candidate < len(plain.l2.BETA_CANDIDATES) or not 0 <= fit_index < len(result['fits']):
        raise ValueError('research: candidate/fold outside archived fit book')
    fit = pool.decode(result['fits'][fit_index])
    terminal = fit['terminal']
    if terminal['status'] == 'converged':
        raise ValueError('research: selected archived fit is already converged')
    if terminal['reason'] != 'irls_iteration_cap' or not fit['stages']:
        raise ValueError('research: only a completed IRLS iteration-cap fit is eligible')

    request = archive['request']
    accepted = workflow.admit(request)
    plan = accepted['plan']
    beta = accepted['policy']['beta_candidates'][args.candidate]
    rows = plan['folds'][args.fold]['fit_rows']
    started = monotonic()
    remaining_fit_seconds = max(0.0, 120.0 - float(fit['wall_seconds']) - 0.25)
    deadline = started + min(remaining_fit_seconds, args.wall_budget)
    owner = original.GravityIRLSPartition(
        plan['request'], accepted['observations']['gz_up_mgal'],
        {k: accepted['noise'][k] for k in ('kind', 'values')}, accepted['prior'],
        rows, beta, observation_rows=plan['development_rows'], deadline=deadline)
    steps = int(fit['iterations'])
    # Preserve the native terminal state. Reconstructing q from the physical
    # kg/m3 output via division can move a float by one ULP and would make this
    # a new initial condition rather than a continuation of the archived fit.
    q = _archived_terminal_q(fit)
    initial = fit['initial_epsilon']
    policy = accepted['policy']['irls']
    prior_weights = fit['stages'][-1]['adopted_weights'].copy()
    changes = [dict(row) for row in terminal['stage_changes']]
    observations = []
    final_status = 'iteration_cap'
    previous_residual = None
    previous_output = None
    pending_fallback = None
    pending_residual_norm = None
    lower = accepted['prior']['lower_kg_m3'] / 1000.0
    upper = accepted['prior']['upper_kg_m3'] / 1000.0
    try:
        for update in range(1, args.max_floor_updates + 1):
            if monotonic() >= deadline:
                final_status = 'wall_cap'
                break
            if steps >= 200:
                final_status = 'accepted_step_cap'
                break
            stage = corrected._stage(owner.problem, q, policy, 20, initial)
            weights = stage['weights'][0]
            solve_started = monotonic()
            with redirect_stdout(io.StringIO()):
                solved = owner.solve_stage(q.copy(), policy, 20, initial, 200 - steps)
            solve_seconds = monotonic() - solve_started
            steps += int(solved['iterations'])
            if solved['q'] is None or solved['status'] != 'converged':
                final_status = solved['reason']
                observations.append(dict(update=update, status=solved['status'],
                    reason=solved['reason'], iterations=solved['iterations'],
                    solve_seconds=solve_seconds, replay='not_run'))
                break

            # Recompute the complete native stage trace and trial certificates.
            solve_deadline = owner.deadline
            owner.deadline = monotonic() + 120.0
            try:
                owner.replay_native(solved, stage['problem'], q, 20, stage, solved, physical=False)
            finally:
                owner.deadline = solve_deadline
            picard_output = solved['q']
            residual = picard_output - q
            residual_norm = float(np.linalg.norm(residual))
            mixing = 0.0
            q_next = picard_output
            predicted_residual_norm = residual_norm
            safeguard = 'picard'
            if pending_fallback is not None:
                if residual_norm < pending_residual_norm:
                    safeguard = 'accelerated_residual_decreased'
                else:
                    q_next = pending_fallback
                    safeguard = 'accelerated_residual_rejected'
                    previous_residual = None
                    previous_output = None
                pending_fallback = None
                pending_residual_norm = None
            if args.acceleration == 'aa1' and previous_residual is not None:
                delta = previous_residual - residual
                denominator = float(np.inner(delta, delta))
                if denominator > 0.0 and np.isfinite(denominator):
                    mixing = float(np.clip(np.inner(residual, residual - previous_residual) /
                        denominator, -5.0, 5.0))
                    mixed_residual = (1.0 - mixing) * residual + mixing * previous_residual
                    predicted_residual_norm = float(np.linalg.norm(mixed_residual))
                    if mixing != 0.0 and predicted_residual_norm < residual_norm:
                        candidate = np.clip((1.0 - mixing) * picard_output +
                            mixing * previous_output, lower, upper)
                        if not np.array_equal(candidate, picard_output):
                            q_next = candidate
                            safeguard = 'accelerated_trial'
                            pending_fallback = picard_output.copy()
                            pending_residual_norm = residual_norm
            model_change = float(np.linalg.norm(q_next - q, ord=np.inf) /
                max(1.0, float(np.linalg.norm(q, ord=np.inf))))
            weight_change = float(np.linalg.norm(weights - prior_weights, ord=np.inf) /
                max(1.0, float(np.linalg.norm(prior_weights, ord=np.inf))))
            changes.append(dict(model_relative=model_change, weights_relative=weight_change))
            prior_weights = weights.copy()
            observations.append(dict(update=update, status='converged', reason=solved['reason'],
                iterations=solved['iterations'], cumulative_steps=steps, solve_seconds=solve_seconds,
                model_relative=model_change, weights_relative=weight_change,
                independent_replay='passed', map_residual_l2=residual_norm,
                predicted_residual_l2=predicted_residual_norm, mixing=mixing,
                accelerated=bool(not np.array_equal(q_next, picard_output)), safeguard=safeguard))
            if safeguard == 'accelerated_residual_rejected':
                previous_residual = None
                previous_output = None
            else:
                previous_residual = residual.copy()
                previous_output = picard_output.copy()
            q = q_next
            if len(changes) >= 3 and all(
                row['model_relative'] <= 1e-6 and row['weights_relative'] <= 1e-6
                for row in changes[-3:]
            ):
                final_status = 'floor_fixed_point'
                break
        else:
            final_status = 'floor_update_cap'
    finally:
        owner.close()

    validation = None
    final_model = q * 1000.0
    if final_status == 'floor_fixed_point':
        prediction = plain.l2._physical_prediction(plan['request'], final_model)
        fold = plan['folds'][args.fold]
        validation_rows = fold['validation_rows']
        positions = np.searchsorted(plan['development_rows'], validation_rows)
        observed = accepted['observations']['gz_up_mgal'][positions]
        noise = {k: accepted['noise'][k] for k in ('kind', 'values')}
        phi_d, wrms, rmse, residual, whitened = plain.l2._marginal_metrics(
            prediction[validation_rows], observed, noise, positions)
        validation = dict(rows=validation_rows.tolist(), phi_d=phi_d, wrms=wrms,
            rmse_mgal=rmse,
            prediction_sha256=plain.survey._digest(prediction[validation_rows]),
            residual_sha256=plain.survey._digest(residual),
            whitened_residual_sha256=plain.survey._digest(whitened))

    receipt = dict(schema='gravity-irls-floor-continuation-research-1',
        status=final_status, research_only=True, product_method_acceptance=False,
        policy_boundary=dict(original_max_weight_updates=20,
            extension_adds_weight_updates_beyond_original_cap=True,
            production_terminal_eligible=False),
        archive_path=str(archive_path), archive_sha256=_digest(archive_path),
        request_sha256=result['request_sha256'], result_sha256=result['result_sha256'],
        archived_terminal_q_sha256=plain.survey._digest(q),
        source_inventory_sha256=plain.survey._digest(result['source_inventory']),
        runtime_epoch=original.RUNTIME_EPOCH, candidate=args.candidate, fold=args.fold,
        fit_index=fit_index, beta_candidate=float(beta), original_reason=terminal['reason'],
        original_weight_updates=int(terminal['weight_updates']),
        original_iterations=int(fit['iterations']), original_wall_seconds=float(fit['wall_seconds']),
        acceleration=args.acceleration,
        added_floor_updates=len(observations), cumulative_iterations=steps,
        additional_wall_seconds=float(monotonic() - started),
        unchanged_limits=dict(per_fit_seconds=120, total_accepted_steps=200,
            model_relative=1e-6, weights_relative=1e-6, terminal_consecutive_transitions=3),
        updates=observations, final_three_transitions=changes[-3:],
        final_model_kg_m3=final_model.tolist() if validation is not None else None,
        final_model_sha256=plain.survey._digest(final_model) if validation is not None else None,
        heldout_validation=validation)
    receipt['receipt_sha256'] = plain.survey._digest(receipt)
    _write_new(output, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-root', type=Path, required=True)
    parser.add_argument('--archive-name', required=True)
    parser.add_argument('--candidate', type=int, required=True)
    parser.add_argument('--fold', type=int, required=True, choices=range(3))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-floor-updates', type=int, default=12, choices=range(1, 33))
    parser.add_argument('--wall-budget', type=float, default=110.0)
    parser.add_argument('--acceleration', choices=('picard', 'aa1'), default='picard')
    args = parser.parse_args()
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '1'
    receipt = run(args)
    print(json.dumps(receipt, sort_keys=True, allow_nan=False))
    return 0 if receipt['status'] == 'floor_fixed_point' else 1


if __name__ == '__main__':
    raise SystemExit(main())
