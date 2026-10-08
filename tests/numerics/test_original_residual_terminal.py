"""Independent exact-original proofs of the state-only residual certificate."""
from decimal import Decimal, localcontext
from dataclasses import replace
from fractions import Fraction
from time import monotonic

import numpy as np
import pytest
import scipy.sparse as sp

import physical_original_residual_terminal as residual
from test_physical_original_terminal import fixture, metric, exact, mapping, budget, scalar, hessian, fraction_solve


@pytest.mark.parametrize('side', [-1., 1.])
@pytest.mark.parametrize('correct_sign', [False, True])
def test_independent_coupled_active_face_optimum_and_signs(side, correct_sign):
    o, identity, *_ = fixture()
    target = np.array([side, .125, -.25])
    identity = dict(identity, observation_rows=3)
    sensitivity = np.array([[1., .5, .25], [.25, 1., -.5], [.5, .25, 1.]])
    o = replace(o, sensitivity=sensitivity, source_components=9,
        observations=np.zeros(3), prediction_sensitivity=sensitivity,
        whitening=residual.original.source.OriginalWhitening('diagonal_sd', np.ones(3)))
    h = hessian(o)
    _, base = exact(o, target)
    sign = -side if correct_sign else side
    desired = [Fraction(sign)/4, Fraction(0), Fraction(0)]
    adjoint = [[2*Fraction(float(sensitivity[j, i])) for j in range(3)] for i in range(3)]
    observations = fraction_solve(adjoint, [g-w for g, w in zip(base, desired)])
    o = replace(o, observations=np.array(list(map(float, observations))))
    # Solve only the constrained face in the independent TEST oracle. No
    # caller optimum, gradient, face or inverse enters the production owner.
    _, at_target = exact(o, target)
    correction = fraction_solve([row[1:] for row in h[1:]], [-v for v in at_target[1:]])
    optimum = [Fraction(float(target[0]))]+[Fraction(float(v))+d for v, d in zip(target[1:], correction)]
    q = np.array(list(map(float, optimum)))
    q[1:] += np.array([1e-10, -2e-10])
    o = replace(o, binding=residual.original.owned.binding_for(identity, q))
    _, gradient = exact(o, q)
    owner = residual.OwnedOriginalResidualTerminal(metric(o, identity, q), o, identity, q,
        np.array(list(map(float, gradient))), 1., **budget())
    record = owner.certify(residual.original.owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert record['passed'] == correct_sign and record['active_sign_pass'] == correct_sign
    assert record['inside_original_bounds'] and record['disposed']
    assert record['free_indices'] == [1, 2] and record['witness_q'][0] == 0.
    d = list(map(Fraction, record['witness_q']))
    for row, g, pair in zip(h, gradient, record['witness_residual_intervals']):
        actual = g+sum(v*x for v, x in zip(row, d))
        assert Fraction(Decimal(pair[0])) <= actual <= Fraction(Decimal(pair[1]))
    if correct_sign:
        delta = [Fraction(float(v))-w for v, w in zip(q, optimum)]
        bound = Fraction(Decimal(record['bounds']['model_error_upper']))
        assert bound*bound >= sum(v*v for v in delta)
        # Active displacement is exactly zero, so the independent constrained
        # objective difference has no linear active contribution.
        gap = sum(v*sum(c*w for c, w in zip(row, delta)) for v, row in zip(delta, h))/2
        assert Fraction(Decimal(record['bounds']['objective_gap_upper'])) >= gap


@pytest.mark.parametrize('covariance', [False, True])
@pytest.mark.parametrize('projected', [False, True])
@pytest.mark.parametrize('half', [False, True])
@pytest.mark.parametrize('ambient', [6, 28, 80])
def test_actual_source_residual_and_strong_bounds_fraction(covariance, projected, half, ambient):
    o, identity, q, g, optimum, h = fixture(covariance, projected, half)
    owner = residual.OwnedOriginalResidualTerminal(metric(o, identity, q), o, identity, q, g, 1., **budget())
    with localcontext() as context:
        context.prec = ambient
        record = owner.certify(residual.original.owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert record['passed'] and record['disposed'] and owner.live_payload_bytes == 0
    assert record['actions'] == 1 and record['inside_original_bounds'] and record['active_sign_pass']
    d = list(map(Fraction, record['witness_q']))
    _, gradient = exact(o, q)
    for row, v, pair in zip(h, gradient, record['witness_residual_intervals']):
        actual = v+sum(c*x for c, x in zip(row, d))
        assert Fraction(Decimal(pair[0])) <= actual <= Fraction(Decimal(pair[1]))
    delta = [Fraction(float(v))-target for v, target in zip(q, optimum)]
    bound = Fraction(Decimal(record['bounds']['model_error_upper']))
    assert bound*bound >= sum(v*v for v in delta)
    gap = sum(v*sum(c*w for c, w in zip(row, delta)) for v, row in zip(delta, h))/2
    assert Fraction(Decimal(record['bounds']['objective_gap_upper'])) >= gap
    assert Fraction(Decimal(record['bounds']['physical_prediction_error_upper'])) >= max(map(abs, mapping(o, delta)))
    assert not any(record[k] for k in ('native_fit_accepted', 'full_method_accepted', 'host_accepted'))
    assert record['witness_workspace_charge_bytes'] == 128*len(q)


@pytest.mark.parametrize('q,d,passed', [(-1., -3., True), (1., 3., True), (-1., 0., False),
    (1., 0., False), (0., 0., True)])
def test_original_active_face_signs_and_null(q, d, passed):
    o, identity, model, g = scalar(q, d)
    owner = residual.OwnedOriginalResidualTerminal(metric(o, identity, model), o, identity, model, g, 1., **budget())
    record = owner.certify(residual.original.owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert record['passed'] == passed and record['disposed']


def test_virtual_corrector_cannot_cross_original_bounds_or_hide_wrong_sign():
    o, identity, model, g = scalar(float(np.nextafter(1., 0.)), 2.0000000001)
    owner = residual.OwnedOriginalResidualTerminal(metric(o, identity, model), o, identity, model, g, 1., **budget())
    record = owner.certify(residual.original.owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert not record['passed'] and not record['inside_original_bounds'] and record['disposed']


def test_wrong_owned_action_is_source_residual_checked_not_self_approval(monkeypatch):
    o, identity, q, g, *_ = fixture()
    owner = residual.OwnedOriginalResidualTerminal(metric(o, identity, q), o, identity, q, g, 1., **budget())
    monkeypatch.setattr(owner._metric, 'apply', lambda v: np.full(len(q), 1e6))
    record = owner.certify(residual.original.owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert not record['passed'] and record['disposed']
    assert Decimal(record['bounds']['model_error_upper']) > Decimal('1e6')


def test_extra_witness_capacity_and_expiry_disposal():
    o, identity, q, g, *_ = fixture()
    dto = metric(o, identity, q)
    owner = residual.OwnedOriginalResidualTerminal(dto, o, identity, q, g, 1., **budget())
    minimum = owner.allocation['maximum']
    owner.close()
    with pytest.raises(ValueError, match='simultaneous'):
        residual.OwnedOriginalResidualTerminal(dto, o, identity, q, g, 1.,
            deadline=monotonic()+120., resource_limit_bytes=2*1024**3, admitted_bytes=minimum-1)
    owner = residual.OwnedOriginalResidualTerminal(dto, o, identity, q, g, 1., **budget())
    owner.deadline = monotonic()-1.
    with pytest.raises(residual.original.source.intervals._Expired):
        owner.certify(residual.original.owned.TerminalPolicy(1e-7))
    assert owner.live_payload_bytes == 0


def test_owned_snapshot_disposed_reuse_and_witness_storage():
    o, identity, q, g, optimum, _ = fixture(True, True)
    owner = residual.OwnedOriginalResidualTerminal(metric(o, identity, q), o, identity, q, g, 1., **budget())
    plain = residual.original.OwnedOriginalTerminal(metric(o, identity, q), o, identity, q, g, 1., **budget())
    assert owner.allocation['maximum']-plain.allocation['maximum'] == 128*len(q)
    assert owner.live_payload_bytes < owner.allocation['maximum']
    plain.close()
    old_q = q.copy()
    o.sensitivity[:] = 1e9
    o.whitening.values[:] = 1e9
    q[:] = .5
    g[:] = 1e9
    record = owner.certify(residual.original.owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert record['passed'] and record['disposed']
    bound = Fraction(Decimal(record['bounds']['model_error_upper']))
    assert bound*bound >= sum((Fraction(float(v))-target)**2 for v, target in zip(old_q, optimum))
    with pytest.raises(ValueError, match='disposed'):
        owner.certify(residual.original.owned.TerminalPolicy(1e-7))


def test_expiry_during_original_action_closes_owner(monkeypatch):
    o, identity, q, g, *_ = fixture()
    owner = residual.OwnedOriginalResidualTerminal(metric(o, identity, q), o, identity, q, g, 1., **budget())
    action = residual._hessian_action
    def expired(ar, operands, vector):
        ar.deadline = monotonic()-1.
        return action(ar, operands, vector)
    monkeypatch.setattr(residual, '_hessian_action', expired)
    with pytest.raises(residual.original.source.intervals._Expired):
        owner.certify(residual.original.owned.TerminalPolicy(1e-7))
    assert owner.live_payload_bytes == 0
