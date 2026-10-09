"""Separate complete source-prior proof; no CG, minimize or fit in this file."""
from fractions import Fraction
from sys import getsizeof
from time import monotonic
import weakref

import numpy as np
import pytest
import scipy.sparse as sp

import gravity_l2_metric as kernel
import physical_owned_spd as owned
from test_physical_owned_spd import Physical


def cycle():
    # First-order square graph with genuine natural-elimination fill.
    return sp.csr_matrix(np.array([[5., -1., 0., -1.], [-1., 5., -1., 0.],
        [0., -1., 5., -1.], [-1., 0., -1., 5.]]))


def exact_ldlt(matrix):
    # Independent rational oracle of literal stored inputs, TEST only.
    n = len(matrix)
    lower = [[Fraction(int(i == j)) for j in range(n)] for i in range(n)]
    pivots = []
    for i in range(n):
        for j in range(i):
            lower[i][j] = (Fraction(float(matrix[i][j]))-sum(
                lower[i][k]*pivots[k]*lower[j][k] for k in range(j)))/pivots[j]
        pivots.append(Fraction(float(matrix[i][i]))-sum(
            lower[i][k]**2*pivots[k] for k in range(i)))
    return np.array([[float(x) for x in row] for row in lower]), np.array([float(x) for x in pivots])


def test_fraction_fill_factor_and_original_default_are_distinct():
    prior = cycle()
    lower, pivots = kernel._factor_complete(prior, monotonic()+120.)
    rational_l, rational_d = exact_ldlt(prior.toarray())
    np.testing.assert_allclose(lower.toarray(), rational_l, rtol=1e-14, atol=1e-15)
    np.testing.assert_allclose(pivots, rational_d, rtol=1e-14, atol=1e-15)
    np.testing.assert_allclose(lower.toarray()@np.diag(pivots)@lower.toarray().T,
        prior.toarray(), rtol=1e-14, atol=1e-15)
    assert prior[3, 1] == 0. and lower[3, 1] != 0.
    old_lower, old_pivots = kernel._factor(prior, monotonic()+120.)
    assert old_lower[3, 1] == 0. and not np.array_equal(old_pivots, pivots)
    rhs = np.array([1., .2, -.3, .1])
    np.testing.assert_allclose(kernel._paired(lower, pivots, rhs, monotonic()+120.),
        np.linalg.solve(prior.toarray(), rhs), rtol=1e-13, atol=1e-14)


@pytest.mark.parametrize('free', [np.arange(4, dtype=np.int64), np.array([0, 2, 3], dtype=np.int64)])
def test_stored_joseph_spd_source_inverse_principal_and_disposal(free):
    prior = cycle()
    g = np.array([[.2, -.1, .4, .2], [.1, .3, -.2, .1]])
    owner = kernel.CompleteFirstOrderJosephMetric(prior, g, sp.eye(2, format='csr'),
        free, monotonic()+120., profile=(2, 2, 4, False))
    try:
        full = np.eye(4)
        actual = np.column_stack([owner.apply(v) for v in full])
        principal = actual[np.ix_(free, free)]
        expected = np.linalg.inv(prior.toarray()[np.ix_(free, free)]+2*g[:, free].T@g[:, free])
        np.testing.assert_allclose(principal, expected, rtol=1e-13, atol=1e-14)
        np.testing.assert_allclose(principal, principal.T, rtol=1e-13, atol=1e-14)
        assert np.linalg.eigvalsh(principal).min() > 0.
        fixed = np.setdiff1d(np.arange(4), free)
        assert np.all(actual[fixed] == 0.) and np.all(actual[:, fixed] == 0.)
        assert owner.allocation['complete_prior_workspace_bytes'] == kernel.complete_prior_workspace(4)
        refs = [weakref.ref(v) for v in (owner.lower, owner.pivots, owner.b, owner.f)]
    finally:
        owner.close()
    assert owner.live_payload_bytes == 0 and all(ref() is None for ref in refs)
    with pytest.raises(ValueError, match='disposed'):
        owner.apply(np.ones(4))


@pytest.mark.parametrize('fault', ['indices', 'asymmetry', 'duplicate', 'positive', 'nonpositive', 'nan', 'dense'])
def test_complete_source_refusal_not_shift_retry_or_partial_factor(fault):
    prior = cycle()
    if fault == 'indices': prior.indices = prior.indices.astype(np.int64)
    elif fault == 'asymmetry': prior[0, 1] = -.5
    elif fault == 'duplicate': prior.indices[1] = prior.indices[0]
    elif fault == 'positive': prior[0, 1] = prior[1, 0] = 1.
    elif fault == 'nonpositive': prior = sp.csr_matrix(np.array([[1., -2.], [-2., 1.]]))
    elif fault == 'nan': prior.data[0] = np.nan
    else: prior = prior.toarray()
    with pytest.raises((ValueError, ArithmeticError)):
        kernel._factor_complete(prior, monotonic()+120.)


def test_expiry_is_checked_during_fill_not_only_before_factor(monkeypatch):
    calls = []
    original = kernel._time
    def check(deadline):
        calls.append(deadline)
        original(deadline)
        if len(calls) == 5:
            raise kernel.DeadlineExceeded('actual fill deadline')
    monkeypatch.setattr(kernel, '_time', check)
    with pytest.raises(kernel.DeadlineExceeded, match='fill deadline'):
        kernel._factor_complete(cycle(), monotonic()+120.)
    assert len(calls) == 5


def test_complete_bound_and_exact_limit_refuse_before_native_factor(monkeypatch):
    physical = Physical()
    try:
        identity, q = physical.identity(), physical.start
        dto = physical.metric_operands(q)
        old = owned.validate_operands(dto, identity, q, 2*1024**3)
        limit = old['maximum']+kernel.complete_prior_workspace(len(q))-1
        def forbidden(*args, **kwargs):
            raise AssertionError('one-byte-short must precede native factor')
        monkeypatch.setattr(kernel, '_factor_complete', forbidden)
        with pytest.raises(ValueError, match='original live-phase limit'):
            owned.OwnedCompletePriorMetric(dto, identity, q, np.arange(len(q), dtype=np.int64),
                monotonic()+120., limit)
    finally:
        physical.release_state()


def test_full4096_extra_fill_ceiling_refuses_before_native_copy(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('unchanged2GiB refusal must precede factor')
    monkeypatch.setattr(kernel, '_factor_complete', forbidden)
    with pytest.raises(ValueError, match='unchanged2GiB'):
        kernel.CompleteFirstOrderJosephMetric(sp.eye(4096, format='csr'), np.ones((1, 4096)),
            sp.eye(1, format='csr'), np.arange(4096, dtype=np.int64), monotonic()+120.,
            profile=(1, 1, 4096, False))


def test_literal_closed_class_and_bad_parameter_count():
    class Foreign(kernel.CompleteFirstOrderJosephMetric):
        pass
    with pytest.raises(TypeError, match='exact closed numeric class'):
        Foreign(cycle(), np.ones((2, 4)), sp.eye(2, format='csr'), np.arange(4, dtype=np.int64), monotonic()+120.)
    for value in (True, 0, 4097, 4., np.int64(4)):
        with pytest.raises(ValueError): kernel.complete_prior_workspace(value)


def test_actual_python_dense_fill_workspace_is_bounded_not_rss():
    # Worst-row storage is tested at every admitted a. No physical matrix/factor.
    for n in range(1, 4097):
        # CPython table capacity depends only on cardinality; reuse one dict.
        if n == 1: row = {}
        row[n-1] = float(n-1)
        assert getsizeof(row)+n*(getsizeof(n)+getsizeof(1.)+8) <= 128*n+1024
    n = 48
    rows = [{j: float(j+1) for j in range(i)} for i in range(n)]
    values = [v for row in rows for v in row.values()]
    columns = [k for row in rows for k in row]
    # Stored rows, construction lists, CSR/factor/transpose copies and reach.
    charged = getsizeof(rows)+sum(getsizeof(row)+sum(getsizeof(k)+getsizeof(v)
        for k, v in row.items()) for row in rows)
    charged += getsizeof(values)+getsizeof(columns)+2*12*(n*(n+1)//2)+8*n*n
    charged += 4*getsizeof(set(range(n)))+4*getsizeof(list(range(n)))+32*n+4096
    assert charged <= kernel.complete_prior_workspace(n)
