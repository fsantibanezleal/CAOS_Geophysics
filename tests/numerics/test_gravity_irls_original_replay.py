"""Actual producer books: source, native phase, proof and disposal denials."""
from copy import deepcopy
from time import monotonic

import numpy as np
import pytest

import gravity_irls_original as public
import gravity_irls_pool as pool
from test_gravity_irls import policy
from test_gravity_l2 import tiny, noise


@pytest.fixture(scope='module')
def actual():
    req, observed, prior, _, _ = tiny()
    req['mesh']['active'][:] = True
    for key, v in [('lower_kg_m3', -1500.), ('upper_kg_m3', 1500.),
                   ('start_kg_m3', 0.), ('reference_kg_m3', 0.)]:
        prior[key] = np.full(12, v)
    rows = np.arange(4, dtype=np.int64)
    result = public.solve_partition(req, observed, noise(), prior, rows, .01,
        policy=policy(), deadline=monotonic()+120.)
    assert result['terminal']['status'] == 'converged'
    return req, observed, prior, rows, result


def test_actual_book_replay_without_any_minimize(actual, monkeypatch):
    req, observed, prior, rows, result = actual
    monkeypatch.setattr(public.original.reduced.core, '_solve', lambda *a, **k: pytest.fail('replay minimized'))
    public.validate_partition(result, req, observed, noise(), prior, rows, .01, policy=policy())


@pytest.mark.parametrize('fault', ('source', 'extra', 'q', 'count', 'true_residual', 'proof_basis', 'bound', 'phase'))
def test_rehashed_actual_native_book_denials(actual, fault):
    req, observed, prior, rows, value = actual
    bad = deepcopy(value)
    native = pool.decode(bad['initialization_evidence'])
    if fault == 'source': native['source_binding']['vendor'] = 'f'*64
    if fault == 'extra': native['ignored'] = 'not admitted'
    if fault == 'q': native['q'] = native['q']+.01
    if fault == 'count': native['conditioning_attempts'][0]['iterations'] = -1
    if fault == 'true_residual': native['conditioning_attempts'][0]['true_relative_residual'] = 0.
    if fault == 'proof_basis': native['terminal_audits'][-1]['check']['proof_basis'] = 'callback_approved'
    if fault == 'bound': native['terminal_audits'][-1]['check']['bounds']['model_error_upper'] = '0'
    if fault == 'phase': native['conditioning_attempts'][0]['phase'] = 1
    bad['initialization_evidence'] = pool.encode(native)
    bad['result_sha256'] = public.original.physics.survey._digest({k:v for k,v in bad.items() if k!='result_sha256'})
    with pytest.raises((ValueError, TypeError)):
        public.validate_partition(bad, req, observed, noise(), prior, rows, .01, policy=policy())
