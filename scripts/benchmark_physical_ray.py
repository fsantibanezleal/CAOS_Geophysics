"""Measure certified bound-ray initialization against its exact scalar baseline."""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys
from time import monotonic, perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'data-pipeline'))
import physical_reduced_optimizer as reduced  # noqa: E402


def exact_scalar(q, p, gradient, lower, upper, deadline):
    """Reference the previous exhaustive exact-rational scan for measurement."""
    best, coordinate = Fraction(1), -1
    for i in range(len(q)):
        if monotonic() > deadline:
            raise TimeoutError('exact ray benchmark deadline')
        if p[i] == 0.:
            continue
        bound = upper[i] if p[i] > 0. else lower[i]
        ratio = (Fraction(float(bound))-Fraction(float(q[i])))/Fraction(float(p[i]))
        if ratio <= 0:
            raise ValueError('benchmark generated an invalid ray')
        if ratio < best:
            best, coordinate = ratio, i
    alpha = float(best)
    if Fraction(alpha) < best:
        alpha = float(np.nextafter(alpha, np.inf))
    return alpha, coordinate


def measure(size: int, repetitions: int, seed: int) -> dict[str, float | int | str]:
    rng = np.random.default_rng(seed)
    q = rng.uniform(-.8, .8, size=size).astype(np.float64)
    p = rng.normal(size=size).astype(np.float64)
    p[rng.random(size) < .1] = 0.
    if not np.any(p):
        p[0] = 1.
    gradient = -p
    lower, upper = np.full(size, -1.), np.full(size, 1.)
    deadline = monotonic()+120.

    reference = exact_scalar(q, p, gradient, lower, upper, deadline)
    candidate = reduced.initial_ray(q, p, gradient, lower, upper, deadline=deadline)
    if candidate != reference:
        raise AssertionError(f'exact ray parity failed: {candidate!r} != {reference!r}')

    started = perf_counter()
    for _ in range(repetitions):
        exact_scalar(q, p, gradient, lower, upper, deadline)
    baseline_seconds = perf_counter()-started
    started = perf_counter()
    for _ in range(repetitions):
        reduced.initial_ray(q, p, gradient, lower, upper, deadline=deadline)
    screened_seconds = perf_counter()-started
    return {
        'size': size,
        'repetitions': repetitions,
        'seed': seed,
        'exact_result': repr(reference),
        'baseline_seconds': baseline_seconds,
        'screened_seconds': screened_seconds,
        'speedup': baseline_seconds/screened_seconds,
        'parity': 'exact',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size', type=int, default=528)
    parser.add_argument('--repetitions', type=int, default=120)
    parser.add_argument('--seed', type=int, default=7)
    args = parser.parse_args()
    if not 1 <= args.size <= 4096 or not 1 <= args.repetitions <= 10000:
        parser.error('size must be 1..4096 and repetitions 1..10000')
    print(json.dumps(measure(args.size, args.repetitions, args.seed), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
