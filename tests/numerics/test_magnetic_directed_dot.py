"""Exact rational corners independently verify the fixed-coefficient enclosure."""
from decimal import Decimal, getcontext, localcontext, Rounded
from fractions import Fraction
from itertools import product
from time import monotonic

import numpy as np
import pytest

from magnetic_inverse_precision import _Arithmetic, _Clock, _Range


@pytest.mark.parametrize('digits', [34, 50, 80])
@pytest.mark.parametrize('coefficients', [
    [.1, -.3, 0., 2., -1e100, 1e-100],
    [1e308, -1e308, np.nextafter(0., 1.), -np.nextafter(0., 1.), -0., 1.],
])
def test_all_independent_rational_corners_and_old_enclosure(digits, coefficients):
    ar = _Arithmetic(digits, monotonic()+120.)
    vector = [(Decimal('-0.125'), Decimal('0.25')),
              (Decimal('0.1'), Decimal('0.3')),
              (Decimal('-1e100'), Decimal('1e100')),
              (Decimal('-1e-100'), Decimal('3e-100')),
              (Decimal('-0.5'), Decimal('-0.25')),
              (Decimal('1.001'), Decimal('1.002'))]
    actual = ar.dot(coefficients, vector)
    old = ar.sum(ar.mul(ar.exact(a), x) for a, x in zip(coefficients, vector))
    assert old[0] <= actual[0] <= actual[1] <= old[1]
    for corner in product(*vector):
        exact = sum((Fraction(float(a))*Fraction(x) for a, x in zip(coefficients, corner)), Fraction(0))
        assert Fraction(actual[0]) <= exact <= Fraction(actual[1])


@pytest.mark.parametrize('digits', [34, 50, 80])
def test_exact_cancellation_and_caller_context_isolation(digits):
    ar = _Arithmetic(digits, monotonic()+120.)
    coefficients = [1e100, 1., -1e100, -.1]
    vector = [ar.exact(1.), ar.exact(np.nextafter(1., 2.)), ar.exact(1.), ar.exact(10.)]
    before = getcontext().copy()
    with localcontext() as context:
        context.prec, context.Emax = 3, 2
        context.traps[Rounded] = True
        actual = ar.dot(coefficients, vector)
    exact = sum((Fraction(a)*Fraction(x[0]) for a, x in zip(coefficients, vector)), Fraction(0))
    assert Fraction(actual[0]) <= exact <= Fraction(actual[1])
    assert getcontext().prec == before.prec and getcontext().flags == before.flags


def test_long_dot_checks_deadline_inside_accumulation(monkeypatch):
    import magnetic_inverse_precision as precision
    ar = _Arithmetic(34, 1.)
    ticks = iter([0., 0., 2.])
    monkeypatch.setattr(precision, 'monotonic', lambda: next(ticks, 2.))
    with pytest.raises(_Clock):
        ar.dot(np.ones(528), [ar.exact(1.)]*528)


def test_nonfinite_native_coefficient_refuses():
    ar = _Arithmetic(34, monotonic()+120.)
    with pytest.raises(_Range):
        ar.dot([float('inf')], [ar.exact(1.)])
