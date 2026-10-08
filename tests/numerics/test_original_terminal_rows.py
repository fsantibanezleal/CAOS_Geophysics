"""Independent rational oracle for the prospective closed terminal arithmetic."""
from decimal import Decimal, Context, localcontext, ROUND_DOWN, ROUND_CEILING
from fractions import Fraction
from time import monotonic

import numpy as np
import pytest
import scipy.sparse as sp

from gravity_l2_precision import _Intervals, _Expired
from physical_original_rows import OriginalTerminalIntervals, _prepare
from physical_original_rows import _aligned, _integer_bytes, ENDPOINT_SLOT_BYTES, ROW_WORKSPACE_BYTES
import sys


def check_rows(matrix, values, digits=34):
    ar = OriginalTerminalIntervals(digits, monotonic()+30.)
    actual = ar.matrix(matrix, values)
    reference = _Intervals(digits, monotonic()+30.)
    reference._use_native_rows = False
    old = reference.matrix(matrix, values)
    for row, pair, previous in zip(matrix, actual, old):
        lower = upper = Fraction(0)
        for coefficient, endpoints in zip(row, values):
            c = Fraction(float(coefficient))
            lo, hi = map(Fraction, endpoints)
            lower += c*(lo if c >= 0 else hi)
            upper += c*(hi if c >= 0 else lo)
        assert Fraction(pair[0]) <= lower <= upper <= Fraction(pair[1])
        assert previous[0] <= pair[0] <= pair[1] <= previous[1]
    return actual


@pytest.mark.parametrize('digits', [34, 50, 80])
def test_rational_signed_cancellation_subnormal_and_transpose(digits):
    rng = np.random.default_rng(20261008)
    matrix = rng.normal(size=(17, 19))
    matrix[0] = 0.
    matrix[1, :4] = [np.nextafter(0., 1.), -np.nextafter(0., 1.), 1e308, -1e308]
    ctx = Context(prec=1200, rounding=ROUND_CEILING)
    values = [(Decimal.from_float(float(v)), ctx.add(Decimal.from_float(float(v)), Decimal('1e-30')))
        for v in rng.normal(size=19)]
    values[:4] = [(Decimal('1e300'), Decimal('1e300')),
        (Decimal('1e300'), Decimal('1e300')), (Decimal('1e-300'), Decimal('1e-300')),
        (Decimal('1e-300'), Decimal('1e-300'))]
    check_rows(matrix, values, digits)
    check_rows(matrix.T, values[:17], digits)


def test_exact_cancellation_and_extreme_bounded_endpoints():
    matrix = np.zeros((2, 9), dtype=np.float64)
    matrix[0, :2] = [1e308, -1e308]
    matrix[1, :2] = [np.nextafter(0., 1.), -np.nextafter(0., 1.)]
    values = [(Decimal('1e1200'), Decimal('1e1200'))]*9
    assert check_rows(matrix, values) == [(Decimal(0), Decimal(0))]*2
    check_rows(matrix, [(Decimal('1e-1200'), Decimal('2e-1200'))]*9)


def test_ambient_context_cannot_round_exact_conversion():
    rng = np.random.default_rng(71)
    matrix = rng.normal(size=(9, 11))
    values = [(Decimal('1.0000000000000000000000000000000001'), Decimal('1.1'))]*11
    expected = check_rows(matrix, values)
    with localcontext() as ambient:
        ambient.prec = 2
        ambient.rounding = ROUND_DOWN
        assert check_rows(matrix, values) == expected


def test_sparse_unchanged_source_action():
    dense = np.eye(11, dtype=np.float64)*1.7
    values = [(Decimal('1.001'), Decimal('1.002'))]*11
    ar = OriginalTerminalIntervals(34, monotonic()+30.)
    original = _Intervals(34, monotonic()+30.)
    original._use_native_rows = False
    csr = sp.csr_matrix(dense)
    assert ar.matrix(csr, values) == original.matrix(csr, values)


@pytest.mark.parametrize('endpoint', [Decimal('1e1201'), Decimal('1e-1201'),
    Decimal('1.'+'1'*1200), Decimal('NaN'), Decimal('Infinity')])
def test_closed_endpoint_range_failure(endpoint):
    with pytest.raises((ValueError, ArithmeticError)):
        _prepare([(endpoint, endpoint)], lambda: None)


def test_closed_shape_and_expiry():
    ar = OriginalTerminalIntervals(34, monotonic()+30.)
    values = [(Decimal(0), Decimal(1))]*9
    with pytest.raises(ValueError):
        ar.matrix(np.ones((9, 9), dtype=np.float32), values)
    with pytest.raises(ValueError):
        ar.matrix(np.ones((9, 9)), values[:8])
    with pytest.raises(ValueError):
        _prepare(values*500, lambda: None)
    ar.deadline = monotonic()-1.
    with pytest.raises(_Expired):
        ar.matrix(np.ones((9, 9)), values)


def test_loaded_real_integer_endpoint_objects_and_capacity_denials():
    big = Decimal('9'*1200+'e-1200')
    prepared, exponent = _prepare([(big, big)]*4096, lambda: None)
    aligned = _aligned(prepared, exponent)
    assert aligned.shape == (2, 4096)
    for pair in prepared:
        actual = (sys.getsizeof(pair)+sum(sys.getsizeof(p)+sum(sys.getsizeof(v) for v in p) for p in pair)+16)
        assert actual <= ENDPOINT_SLOT_BYTES
    for bits in (0, 53, 1074, 14100, 17000):
        assert sys.getsizeof((1 << bits)-1) <= _integer_bytes(bits)
    # The existing8MiB row scratch includes decoded <=8-row native arrays and
    # all multiplication/conversion temporaries; no RSS-based memory grant.
    assert sys.getsizeof(Decimal('9'*5100))+sys.getsizeof(('9',)*5100) < 262144
    with pytest.raises(ValueError, match='aligned endpoint slot'):
        p, e = _prepare([(Decimal('1e-1200'), Decimal('1e-1200')),
            (Decimal('9'*1200+'e1200'), Decimal('9'*1200+'e1200'))], lambda: None)
        _aligned(p, e)
    ar = OriginalTerminalIntervals(34, monotonic()+30.)
    # No dense arithmetic executes after the preallocation workspace denial.
    m = np.full((8, 4096), 1e308)
    m[0, 0] = np.nextafter(0., 1.)
    # Even one row cannot fit the simultaneous workspace at this admitted
    # endpoint width. It is a denial, not scalar-row or precision fallback.
    with pytest.raises(ValueError, match='workspace capacity'):
        ar.matrix(m, [(big, big)]*4096)
    assert ROW_WORKSPACE_BYTES == 8388608


def test_exact_zero_exponent_not_subnormal_nonzero_loss():
    matrix = np.ones((9, 12), dtype=np.float64)
    matrix[:, ::3] = 0.
    matrix[0, 1] = np.nextafter(0., 1.)
    values = [(Decimal('0e-1200'), Decimal('0e-1200')) if i % 3 == 0
        else (Decimal('1e100'), Decimal('1e100')) for i in range(12)]
    actual = check_rows(matrix, values)
    assert actual[0] != actual[1]
    isolated = np.zeros((9, 12), dtype=np.float64)
    isolated[0, 1] = np.nextafter(0., 1.)
    tiny = check_rows(isolated, values)
    assert tiny[0][0] > 0 and all(v == (Decimal(0), Decimal(0)) for v in tiny[1:])


def test_bound_row_source_drift_is_not_accepted(monkeypatch):
    import physical_original_terminal as terminal
    monkeypatch.setattr(terminal.exact_rows, 'SOURCE_SHA256', '0'*64)
    with pytest.raises(ValueError, match='source drift'):
        terminal.original_row_arithmetic(34, monotonic()+30.)
