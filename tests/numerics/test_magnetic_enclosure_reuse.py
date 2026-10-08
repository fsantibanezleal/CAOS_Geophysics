"""Bounded scalar reuse is equivalent enclosure work, never optimizer admission."""
from decimal import Decimal
from time import monotonic

import numpy as np
import pytest

import magnetic_inverse_precision as precision
from test_magnetic_inverse_precision import operands


def test_bit_identical_scalar_reuse(monkeypatch):
    _, cert, _, _, _ = operands()
    original, calls = cert._objective, []

    def counted(model, ar):
        calls.append((model.copy(), ar.lo.prec))
        return original(model, ar)

    monkeypatch.setattr(cert, '_objective', counted)
    args = [np.ones(2), np.full(2, .5), np.ones(2), 1., .2, 0, 0, monotonic()+120.]
    first = cert.certify(*args)
    assert len(calls) == 2
    assert cert.certify(*args) == first and len(calls) == 2
    changed_gradient = cert.certify(args[0], args[1], -args[2], 99., 88., 1, 1, args[-1])
    assert changed_gradient['decision'] == 'certified_reject' and changed_gradient['cause'] == 'non_descent'
    assert changed_gradient['native_phi_current'] == 99. and changed_gradient['iteration'] == 1
    assert len(calls) == 2  # Reused objective never reuses gradient/decision.
    # Identical real zeros with different native bits are not the same key.
    ar = precision._Arithmetic(34, monotonic()+120.)
    cert._enclosed_objective(np.array([0., .5]), ar)
    cert._enclosed_objective(np.array([-0., .5]), ar)
    assert len(calls) == 4


def test_two_model_bound_and_charge(monkeypatch):
    _, cert, _, _, _ = operands()
    original, calls = cert._objective, []

    def counted(model, ar):
        calls.append((tuple(model), ar.lo.prec))
        return original(model, ar)

    monkeypatch.setattr(cert, '_objective', counted)
    for model in (np.array([1., .5]), np.array([.5, 1.]), np.array([2., 1.])):
        for digits in (34, 50, 80):
            cert._enclosed_objective(model, precision._Arithmetic(digits, monotonic()+120.))
    assert len(calls) == 9
    cert._enclosed_objective(np.array([.5, 1.]), precision._Arithmetic(34, monotonic()+120.))
    assert len(calls) == 9
    cert._enclosed_objective(np.array([1., .5]), precision._Arithmetic(34, monotonic()+120.))
    assert len(calls) == 10  # First model was evicted, not unbounded retained.
    slots = cert._MagneticCertificate__enclosures
    assert len(slots) == 2 and all(len(values) <= 3 for _, values in slots)
    assert all(not model.flags.writeable and model.flags.c_contiguous for model, _ in slots)
    assert precision._reuse_charge(2048) == 57344
    op, _, observed, noise, terms = operands()
    monkeypatch.setattr(precision, '_reuse_charge', lambda _: 805306369)
    monkeypatch.setattr(precision, 'owned', lambda _: pytest.fail('Snapshot before budget refusal'))
    with pytest.raises(ValueError, match='budget'):
        precision.MagneticCertificate(op, observed, noise, np.zeros(2), np.zeros(2), np.full(2, 10.), .3, terms)


@pytest.mark.parametrize('error', [precision._Clock, precision._Range])
def test_expiration_and_partial_refusal(monkeypatch, error):
    _, cert, _, _, _ = operands()
    q, qt = np.ones(2), np.full(2, .5)
    expected = cert.certify(q, qt, np.ones(2), 1., .2, 0, 0, monotonic()+120.)
    assert expected['decision'] == 'certified_accept'
    with pytest.raises(precision._Clock):
        cert._enclosed_objective(q, precision._Arithmetic(34, monotonic()-1.))
    _, partial, _, _, _ = operands()

    def failed(model, ar):
        raise error('authored construction refusal')

    monkeypatch.setattr(partial, '_objective', failed)
    record = partial.certify(q, qt, np.ones(2), 1., .2, 0, 0, monotonic()+120.)
    assert record['cause'] == ('wall_cap' if error is precision._Clock else 'range_unsupported')
    assert record['decision'] == 'not_run'
    assert record['passes'] == 0 and record['precision_digits'] is None
    assert all(record[key] is None for key in ('delta_interval', 'slope_interval', 'armijo_margin_interval'))
    assert partial._MagneticCertificate__enclosures == []
    ticks = iter([0., 2.])
    monkeypatch.setattr(precision, 'monotonic', lambda: next(ticks, 2.))
    with pytest.raises(precision._Clock):
        cert._enclosed_objective(q, precision._Arithmetic(34, 1.))
    monkeypatch.setattr(precision, 'monotonic', monotonic)
    # A completed calculation which expired before publication is also absent.
    monkeypatch.setattr(partial, '_objective', lambda model, ar: (setattr(ar, 'deadline', monotonic()-1.) or (Decimal(1), Decimal(1))))
    with pytest.raises(precision._Clock):
        partial._enclosed_objective(q, precision._Arithmetic(34, monotonic()+120.))
    assert partial._MagneticCertificate__enclosures == []


def test_mutation_and_instance_isolation(monkeypatch):
    _, cert, observed, noise, terms = operands(covariance=True)
    q, qt, gradient = np.ones(2), np.full(2, .5), np.ones(2)
    first = cert.certify(q, qt, gradient, 1., .2, 0, 0, monotonic()+120.)
    observed[:] = 999.; noise['values'][:] = 0.; terms[0]['weights'][:] = 999.
    terms[0]['derivative'].data[:] = 999.
    assert cert.certify(q, qt, gradient, 1., .2, 0, 0, monotonic()+120.) == first
    original, calls = cert._objective, []

    def counted(model, ar):
        calls.append(model.copy())
        return original(model, ar)

    monkeypatch.setattr(cert, '_objective', counted)
    qt[0] = .25
    cert.certify(q, qt, gradient, 1., .2, 0, 0, monotonic()+120.)
    assert len(calls) == 1  # Owned key did not alias caller mutation.
    _, another, _, _, _ = operands()
    assert another._MagneticCertificate__enclosures == []


@pytest.mark.parametrize('quantity', ['secondary_enu_nT', 'linear_tmi_nT', 'exact_total_anomaly_nT'])
@pytest.mark.parametrize('covariance', [False, True])
def test_uncached_record_parity(quantity, covariance, monkeypatch):
    _, cached, _, _, _ = operands(quantity, covariance)
    _, uncached, _, _, _ = operands(quantity, covariance)
    monkeypatch.setattr(uncached, '_enclosed_objective', uncached._objective)
    for q, qt, gradient in [(np.array([1., .8]), np.array([.3, .25]), np.ones(2)),
                            (np.array([.3, .25]), np.array([1., .8]), -np.ones(2)),
                            (np.array([1e-20, 2e-20]), np.array([2e-20, 1e-20]), np.array([0., 1.]))]*2:
        args = [q, qt, gradient, 1., .2, 0, 0, monotonic()+120.]
        assert cached.certify(*args) == uncached.certify(*args)
