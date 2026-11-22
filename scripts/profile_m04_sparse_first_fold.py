"""Profile one frozen M04 sparse fold without changing its numerical limits."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'data-pipeline'))
import magnetic_calibration as calibration  # noqa: E402
import physical_reduced_optimizer as reduced  # noqa: E402


def profile(request_path: Path, wall_seconds: float = 120.) -> dict:
    if (type(wall_seconds) not in (int, float) or not 0. < wall_seconds
            or wall_seconds > calibration.MAX_WALL_SECONDS):
        raise ValueError('wall_seconds must be positive and within the local M04 cap')
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        if os.environ.get(name) != '1':
            raise RuntimeError(f'{name}=1 is required by the reviewed native workspace')

    raw = request_path.read_bytes()
    directions: list[dict] = []
    original = reduced._Linear.findSearchDirection

    def observe(optimizer):
        start = len(optimizer.conditioning_attempts)
        started = monotonic()
        try:
            return original(optimizer)
        finally:
            rows = optimizer.conditioning_attempts[start:]
            directions.append({
                'outer_iteration': int(optimizer.iter),
                'elapsed_seconds': monotonic()-started,
                'phases': [{
                    'phase': row.get('phase'),
                    'branch': row.get('branch'),
                    'failure': row.get('failure'),
                    'cg_iterations': row.get('iterations'),
                    'cumulative_cg': row.get('cumulative_CG'),
                    'newly_frozen_cells': len(row.get('frozen_delta', ())),
                    'preflight_seconds': row.get('preflight_seconds'),
                    'total_phase_seconds': row.get('total_phase_seconds'),
                    'prospective_peak_bytes': row.get('resource', {}).get('prospective_peak_bytes'),
                } for row in rows],
            })

    started = monotonic()
    l2_result = None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            l2_result = calibration.fit_l2_fold(
                raw, 0, 0.0001, wall_seconds=float(wall_seconds)
            )
            if l2_result.get('status') == 'converged':
                reduced._Linear.findSearchDirection = observe
                result = calibration.fit_sparse_fold(
                    raw, 0, 0.0001, l2_result=l2_result,
                    wall_seconds=float(wall_seconds),
                )
            else:
                result = {
                    'schema': 'magnetic-linear-sparse-fold-result-1',
                    'status': 'failed',
                    'reason': 'same_fold_same_beta_l2_start_failed',
                    'stages': [],
                    'history': [],
                    'claims': {
                        'candidate_selected': False,
                        'field_geology_validated': False,
                        'field_observations': False,
                        'method_accepted': False,
                        'online_admitted': False,
                        'outer_evaluation_performed': False,
                    },
                }
    finally:
        reduced._Linear.findSearchDirection = original
    elapsed = monotonic()-started
    history = result.get('history', ())
    def model_digest(value):
        if value is None:
            return None
        import numpy as np
        array = np.ascontiguousarray(value, dtype='<f8')
        return hashlib.sha256(array.tobytes()).hexdigest()

    def array_values(value):
        return value.tolist() if hasattr(value, 'tolist') else value

    def compact_audit(rows):
        compact = []
        for row in rows:
            check = (row.get('check', row) if type(row) is dict else {})
            compact.append({
                'check': {key: value for key, value in check.items()
                          if type(value) in (int, float, str, bool) or value is None},
                'certificate_sha256': hashlib.sha256(
                    json.dumps(row, sort_keys=True, separators=(',', ':'), default=str).encode()
                ).hexdigest(),
            })
        return compact

    fit_history = [{
        key: row.get(key) for key in (
            'epsilon_q', 'outer_iteration', 'true_objective', 'previous_true_objective',
            'monotonic_allowance', 'model_relative', 'weights_relative',
            'projected_gradient_inf', 'gradient_limit', 'inner_iterations',
            'inner_status', 'inner_reason', 'core_certificate', 'monotonicity_pass',
            'inner_model_q_sha256', 'inner_failed_trial', 'last_conditioning_attempt',
        ) if key in row
    } | {
        'inner_model_q': array_values(row.get('inner_model_q')),
        'model_q_sha256': model_digest(row.get('model_q')),
        'terminal_audits': compact_audit(row.get('terminal_audits', ())),
    } for row in history]
    fit_summary = {
        'schema': result.get('schema'),
        'status': result.get('status'),
        'reason': result.get('reason'),
        'quantity': result.get('quantity'),
        'fold_index': result.get('fold_index'),
        'fit_rows': result.get('fit_rows'),
        'geometry_seal_sha256': result.get('geometry_seal_sha256'),
        'source_inventory_sha256': result.get('source_inventory_sha256'),
        'allocation_plan_sha256': result.get('allocation_plan_sha256'),
        'start_policy': result.get('start_policy'),
        'start_model_q_sha256': result.get('start_model_q_sha256'),
        'beta': result.get('beta'),
        'parameter_unit': result.get('parameter_unit'),
        'epsilon_schedule_q': result.get('epsilon_schedule_q'),
        'stages': result.get('stages'),
        'history': fit_history,
        'model_q': array_values(result.get('model_q')),
        'model_q_sha256': model_digest(result.get('model_q')),
        'prediction_nT': array_values(result.get('prediction_nT')),
        'residual_observed_minus_predicted_nT': array_values(
            result.get('residual_observed_minus_predicted_nT')),
        'objective': result.get('objective'),
        'normalized_projected_gradient_inf': result.get('normalized_projected_gradient_inf'),
        'final_gradient_limit': result.get('final_gradient_limit'),
        'elapsed_seconds': result.get('elapsed_seconds'),
        'claims': result.get('claims'),
    }
    l2_start_summary = None if l2_result is None else {
        'status': l2_result.get('status'),
        'reason': l2_result.get('reason'),
        'fold_index': l2_result.get('fold_index'),
        'beta': l2_result.get('beta'),
        'fit_rows': l2_result.get('fit_rows'),
        'model_q': array_values(l2_result.get('model_q')),
        'model_q_sha256': model_digest(l2_result.get('model_q')),
        'normalized_projected_kkt_inf': l2_result.get('normalized_projected_kkt_inf'),
        'terminal_audits': compact_audit(l2_result.get('terminal_audits', ())),
        'elapsed_seconds': l2_result.get('elapsed_seconds'),
        'source_inventory_sha256': l2_result.get('source_inventory_sha256'),
    }
    summary = {
        'schema': 'm04-sparse-first-fold-evidence-3',
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'product_commit': subprocess.run(
            ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
            check=True, capture_output=True, text=True,
        ).stdout.strip(),
        'profile_runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runtime': {
            'python': platform.python_version(),
            'platform': platform.platform(),
            'numpy': version('numpy'),
            'scipy': version('scipy'),
            'simpeg': version('simpeg'),
            'discretize': version('discretize'),
        },
        'request_sha256': hashlib.sha256(raw).hexdigest(),
        'optimizer_sha256': hashlib.sha256(Path(reduced.__file__).read_bytes()).hexdigest(),
        'calibration_sha256': hashlib.sha256(Path(calibration.__file__).read_bytes()).hexdigest(),
        'status': result.get('status'),
        'reason': result.get('reason'),
        'elapsed_seconds': elapsed,
        'epsilon_stages': result.get('stages', []),
        'fit': fit_summary,
        'l2_start': l2_start_summary,
        'claims': result.get('claims'),
        'direction_count': len(directions),
        'directions': directions,
        'phase_count': sum(len(item['phases']) for item in directions),
        'phase_count_distribution': {
            str(n): sum(len(item['phases']) == n for item in directions)
            for n in sorted({len(item['phases']) for item in directions})
        },
        'phase_limit': reduced.PHASE_LIMIT,
        'wall_limit_seconds': float(wall_seconds),
        'resource_limit_bytes': calibration.RESOURCE_LIMIT_BYTES,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='receipt path outside the repository data tree')
    parser.add_argument('--request', type=Path, default=(
        ROOT/'tests/fixtures/magnetic_survey/generated/requests/S2-A-linear_tmi_nT.json'))
    parser.add_argument('--wall-seconds', type=float, default=120.,
                        help='local fit wall budget, bounded by the M02 120-second policy')
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT.resolve()):
        parser.error('--output must resolve outside the repository')
    result = profile(args.request, args.wall_seconds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in (
        'status', 'reason', 'elapsed_seconds', 'direction_count', 'phase_count',
        'phase_count_distribution', 'epsilon_stages', 'phase_limit',
        'wall_limit_seconds', 'resource_limit_bytes')}, sort_keys=True))
    print(f"receipt={args.output}")
    return 0 if result['status'] == 'converged' else 2


if __name__ == '__main__':
    raise SystemExit(main())
