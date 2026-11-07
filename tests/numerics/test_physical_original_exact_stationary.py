"""Exact original KKT proof; not nearzero, a callback flag or CG fallback."""
from decimal import Decimal

import numpy as np
import pytest

import physical_original_terminal as terminal
from test_physical_original_terminal import scalar, metric, budget


@pytest.mark.parametrize('q,d', [(0., 0.), (-1., -3.), (1., 3.)])
def test_source_exact_stationary_unique_optimum_without_contraction(q, d, monkeypatch):
    o, identity, model, g = scalar(q, d)
    owner = terminal.OwnedOriginalTerminal(metric(o, identity, model), o, identity, model, g, 1., **budget())
    monkeypatch.setattr(owner, '_stored_action', lambda *a: pytest.fail('exact source optimum used contraction action'))
    result = owner.certify(terminal.owned.TerminalPolicy(1e-7, 1e-8, 1e-8, 1e-6))
    assert result['passed'] and result['disposed'] and owner.live_payload_bytes == 0
    assert result['proof_basis'] == 'exact_source_feasible_kkt'
    assert result['kappa_upper'] is result['eta_upper'] is None and result['actions'] == 0
    assert result['inside_original_bounds'] and result['active_sign_pass']
    assert all(Decimal(result['bounds'][key]) == 0 for key in (
        'model_error_upper', 'objective_gap_upper', 'physical_prediction_error_upper'))
    assert Decimal(result['bounds']['mu_lower']) > 0
    # Independent scalar physical optimum with SAME objective: (q-d)^2+q^2.
    assert np.clip(d/2., -1., 1.) == q


def test_one_ulp_nonzero_original_residual_is_not_exact_zero():
    o, identity, model, g = scalar(0., float(np.nextafter(0., 1.)))
    owner = terminal.OwnedOriginalTerminal(metric(o, identity, model), o, identity, model, g, 1., **budget())
    result = owner.certify(terminal.owned.TerminalPolicy(1e-7, 1e-8, 1e-8, 1e-6))
    assert result['proof_basis'] == 'free_face_neumann' and result['actions'] == 2
    assert result['kappa_upper'] is not None and result['eta_upper'] is not None
    assert Decimal(result['bounds']['model_error_upper']) > 0 and result['disposed']


def test_native_disagreement_and_wrong_bound_sign_do_not_pass():
    o, identity, q, g = scalar(0., 0.)
    owner = terminal.OwnedOriginalTerminal(metric(o, identity, q), o, identity, q,
        np.ones(1), 1., **budget())
    result = owner.certify(terminal.owned.TerminalPolicy(1e-7, 1e-8, 1e-8, 1e-6))
    assert not result['passed'] and result['proof_basis'] == 'exact_source_feasible_kkt' and result['disposed']
    o, identity, q, g = scalar(-1., 0.)
    owner = terminal.OwnedOriginalTerminal(metric(o, identity, q), o, identity, q, g, 1., **budget())
    result = owner.certify(terminal.owned.TerminalPolicy(1e-7, 1e-8, 1e-8, 1e-6))
    assert not result['passed'] and result['proof_basis'] == 'free_face_neumann' and result['disposed']
