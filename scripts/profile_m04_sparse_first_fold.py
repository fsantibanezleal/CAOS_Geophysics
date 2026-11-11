"""Profile one frozen M04 sparse fold without changing its numerical limits."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'data-pipeline'))
import magnetic_calibration as calibration  # noqa: E402
import physical_reduced_optimizer as reduced  # noqa: E402


def profile(request_path: Path) -> dict:
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

    reduced._Linear.findSearchDirection = observe
    started = monotonic()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result = calibration.fit_sparse_fold(raw, 0, 0.0001, wall_seconds=120.)
    finally:
        reduced._Linear.findSearchDirection = original
    elapsed = monotonic()-started
    history = result.get('history', ())
    summary = {
        'schema': 'm04-sparse-first-fold-phase-profile-1',
        'request_sha256': hashlib.sha256(raw).hexdigest(),
        'optimizer_sha256': hashlib.sha256(Path(reduced.__file__).read_bytes()).hexdigest(),
        'calibration_sha256': hashlib.sha256(Path(calibration.__file__).read_bytes()).hexdigest(),
        'status': result.get('status'),
        'reason': result.get('reason'),
        'elapsed_seconds': elapsed,
        'epsilon_stages': [{
            'epsilon_q': row.get('epsilon_q'),
            'inner_status': row.get('inner_status'),
            'inner_reason': row.get('inner_reason'),
            'inner_iterations': row.get('inner_iterations'),
            'conditioning_attempt_count': row.get('conditioning_attempt_count'),
        } for row in history],
        'claims': result.get('claims'),
        'direction_count': len(directions),
        'directions': directions,
        'phase_count': sum(len(item['phases']) for item in directions),
        'phase_count_distribution': {
            str(n): sum(len(item['phases']) == n for item in directions)
            for n in sorted({len(item['phases']) for item in directions})
        },
        'phase_limit': reduced.PHASE_LIMIT,
        'wall_limit_seconds': 120,
        'resource_limit_bytes': calibration.RESOURCE_LIMIT_BYTES,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='receipt path outside the repository data tree')
    parser.add_argument('--request', type=Path, default=(
        ROOT/'tests/fixtures/magnetic_survey/generated/requests/S2-A-linear_tmi_nT.json'))
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT.resolve()):
        parser.error('--output must resolve outside the repository')
    result = profile(args.request)
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
