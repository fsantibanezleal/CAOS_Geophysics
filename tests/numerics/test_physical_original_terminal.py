"""Independent exact Fraction optima, original noise, and owner denial controls."""
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction
from time import monotonic

import numpy as np
import pytest
import scipy.sparse as sp
from scipy.linalg import solve_triangular

import physical_original_terminal as terminal
from test_physical_original_quadratic import operands, exact, mapping, whiten, mat, budget


def fraction_solve(matrix, vector):
    rows = [list(row)+[value] for row, value in zip(matrix, vector)]
    for i in range(len(rows)):
        pivot = rows[i][i]
        assert pivot
        rows[i] = [v/pivot for v in rows[i]]
        for j in range(len(rows)):
            if i != j:
                coefficient = rows[j][i]
                rows[j] = [v-coefficient*w for v, w in zip(rows[j], rows[i])]
    return [row[-1] for row in rows]


def hessian(o):
    n = len(o.reference)
    cols = []
    for j in range(n):
        unit = [Fraction(int(i == j)) for i in range(n)]
        col = [2*Fraction(o.likelihood_scale)*v for v in mapping(o,
            whiten(o, whiten(o, mapping(o, unit)), True), True)]
        for t in o.terms:
            v = mat(t.derivative.T, mat(t.weights.T, mat(t.weights, mat(t.derivative, unit))))
            col = [old+2*Fraction(o.beta)*Fraction(t.alpha)*value for old, value in zip(col, v)]
        cols.append(col)
    return list(map(list, zip(*cols)))


def metric(o, identity, q):
    g = o.sensitivity
    if o.projection is not None:
        g = np.einsum('sja,j->sa', g.reshape(-1, 3, len(q)), o.projection)
    noise = o.whitening
    j = (g/noise.values[:, None] if noise.kind == 'diagonal_sd'
        else solve_triangular(noise.values, g, lower=True))
    r = sp.csr_matrix((len(q), len(q)))
    for t in o.terms:
        wd = t.weights@t.derivative
        r += 2.*o.beta*t.alpha*(wd.T@wd)
    r.sum_duplicates()
    r.sort_indices()
    return terminal.owned.MetricOperands(o.binding, o.source_components,
        identity['observation_rows']*identity['observation_components'], len(q),
        noise.kind == 'stored_lower_cholesky', r, np.ascontiguousarray(j), o.likelihood_scale)


def fixture(covariance=False, projected=False, half=False):
    o, identity, _ = operands(covariance, projected, half)
    h = hessian(o)
    _, zero_g = exact(o, np.zeros(3))
    optimum = fraction_solve(h, [-v for v in zero_g])
    q = np.array([float(v) for v in optimum])
    assert np.all(abs(q) < 1.)
    o = replace(o, binding=terminal.owned.binding_for(identity, q))
    _, gradient = exact(o, q)
    return o, identity, q, np.array([float(v) for v in gradient]), optimum, h


@pytest.mark.parametrize('covariance', [False, True])
@pytest.mark.parametrize('projected', [False, True])
@pytest.mark.parametrize('half', [False, True])
@pytest.mark.parametrize('ambient', [6, 28, 80])
def test_original_exact_optimum_and_factor_actions_enclosed(covariance, projected, half, ambient):
    o, identity, q, g, optimum, h = fixture(covariance, projected, half)
    owner = terminal.OwnedOriginalTerminal(metric(o, identity, q), o, identity, q, g, 1., **budget())
    assert owner.live_payload_bytes > 0
    numeric = owner._metric._numeric
    ar = terminal.source.intervals._Intervals(34, monotonic()+120.)
    ar._use_native_rows = False
    # Exact independent Fraction interpretation of the factory factors, not
    # an inverse or success flag supplied to production.
    def stored(values):
        z = mat(numeric.f.T, values)
        w = [v-x for v, x in zip(values, mat(numeric.b.T, z))]
        lower = numeric.lower.toarray()
        x = []
        for i in range(3):
            x.append(w[i]-sum(Fraction(float(lower[i, j]))*x[j] for j in range(i)))
        x = [v/Fraction(float(d)) for v, d in zip(x, numeric.pivots)]
        y = [None]*3
        for i in range(2, -1, -1):
            y[i] = x[i]-sum(Fraction(float(lower[j, i]))*y[j] for j in range(i+1, 3))
        fy, fz = mat(numeric.f, mat(numeric.b, y)), mat(numeric.f, z)
        return [v-left+right for v, left, right in zip(y, fy, fz)]
    with localcontext() as context:
        context.prec = ambient
        for j in range(3):
            values = [Fraction(int(i == j)) for i in range(3)]
            enclosed = owner._stored_action(ar, [ar.exact(float(v)) for v in values], numeric.lower.T.tocsr())
            for value, (lo, hi) in zip(stored(values), enclosed):
                assert Fraction(lo) <= value <= Fraction(hi)
        result = owner.certify(terminal.owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert result['passed'] and result['disposed']
    assert result['inside_original_bounds'] and result['active_sign_pass']
    assert result['actions'] == 7  # 3 independent probes, 3 columns, 1 residual.
    exact_delta = [Fraction(float(v))-target for v, target in zip(q, optimum)]
    error_squared = sum(v*v for v in exact_delta)
    bound = Fraction(Decimal(result['bounds']['model_error_upper']))
    assert bound*bound >= error_squared
    gap = sum(v*sum(c*w for c, w in zip(row, exact_delta)) for v, row in zip(exact_delta, h))/2
    assert Fraction(Decimal(result['bounds']['objective_gap_upper'])) >= gap
    pred = mapping(o, exact_delta)
    assert Fraction(Decimal(result['bounds']['physical_prediction_error_upper'])) >= max(map(abs, pred))
    assert owner.live_payload_bytes == 0 and owner.free is None
    with pytest.raises(ValueError, match='disposed'):
        owner.certify(terminal.owned.TerminalPolicy(1e-7))


def scalar(qvalue, d, lower=-1., upper=1.):
    o, identity, _ = operands()
    q = np.array([qvalue])
    identity = dict(identity, parameter_count=1, observation_rows=1, beta_engine=1.)
    o = replace(o, binding=terminal.owned.binding_for(identity, q), sensitivity=np.ones((1, 1)),
        source_components=1, observations=np.array([d]), reference=np.zeros(1), lower=np.array([lower]),
        upper=np.array([upper]), whitening=terminal.source.OriginalWhitening('diagonal_sd', np.ones(1)),
        beta=1., terms=(terminal.owned.QuadraticTerm(1., sp.eye(1, format='csr'), sp.eye(1, format='csr')),),
        prediction_sensitivity=np.ones((1, 1)))
    _, g = exact(o, q)
    return o, identity, q, np.array(list(map(float, g)))


@pytest.mark.parametrize('q,d,passed', [(-1., -3., True), (1., 3., True), (-1., 0., False),
    (1., 0., False), (0., 0., True)])
def test_exact_active_signs_and_empty_face(q, d, passed):
    o, identity, model, g = scalar(q, d)
    owner = terminal.OwnedOriginalTerminal(metric(o, identity, model), o, identity, model, g, 1., **budget())
    result = owner.certify(terminal.owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert result['passed'] == passed and result['disposed']
    if abs(q) == 1.:
        assert result['actions'] == 0
        assert result['active_sign_pass'] == passed


def test_free_interval_crossing_original_bound_is_not_accepted():
    o, identity, q, g = scalar(float(np.nextafter(1., 0.)), 2.0000000001)
    owner = terminal.OwnedOriginalTerminal(metric(o, identity, q), o, identity, q, g, 1., **budget())
    result = owner.certify(terminal.owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert not result['passed'] and not result['inside_original_bounds'] and result['disposed']


def test_simultaneous_phase_one_byte_short_and_wrong_source_binding():
    o, identity, q, g, _, _ = fixture()
    dto = metric(o, identity, q)
    owner = terminal.OwnedOriginalTerminal(dto, o, identity, q, g, 1., **budget())
    minimum = owner.allocation['maximum']
    owner.close()
    with pytest.raises(ValueError, match='simultaneous'):
        terminal.OwnedOriginalTerminal(dto, o, identity, q, g, 1.,
            deadline=monotonic()+120., resource_limit_bytes=2*1024**3, admitted_bytes=minimum-1)
    wrong = replace(dto, covariance=True)
    with pytest.raises(ValueError, match='same original'):
        terminal.OwnedOriginalTerminal(wrong, o, identity, q, g, 1., **budget())
    stale = replace(o, binding=replace(o.binding, model_sha256='f'*64))
    with pytest.raises(ValueError, match='binding'):
        terminal.OwnedOriginalTerminal(dto, stale, identity, q, g, 1., **budget())


def test_immutable_snapshot_and_expiry_disposal():
    o, identity, q, g, _, _ = fixture()
    owner = terminal.OwnedOriginalTerminal(metric(o, identity, q), o, identity, q, g, 1., **budget())
    o.sensitivity[:] = 1e9
    q[:] = .5
    g[:] = 1e9
    result = owner.certify(terminal.owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert result['passed'] and result['disposed']
    o, identity, q, g, _, _ = fixture()
    owner = terminal.OwnedOriginalTerminal(metric(o, identity, q), o, identity, q, g, 1., **budget())
    owner.deadline = monotonic()-1.
    with pytest.raises(terminal.source.intervals._Expired):
        owner.certify(terminal.owned.TerminalPolicy(1e-7))
    assert owner.live_payload_bytes == 0


def test_hidden_native_jacobian_backing_is_not_an_unaccounted_input():
    o, identity, q, g, _, _ = fixture()
    dto = metric(o, identity, q)
    storage = np.zeros((100, 3))
    storage[:2] = dto.whitened_jacobian
    hidden = replace(dto, whitened_jacobian=storage[:2])
    with pytest.raises(ValueError, match='backing capacities'):
        terminal.OwnedOriginalTerminal(hidden, o, identity, q, g, 1., **budget())


def test_no_caller_metric_mask_or_factor_constructor_and_null_pivot(monkeypatch):
    o, identity, q, g, _, _ = fixture()
    with pytest.raises(TypeError):
        terminal.OwnedOriginalTerminal(metric(o, identity, q), o, identity, q, g, 1., free=np.array([0]), **budget())
    factory = terminal.owned.OwnedMetric
    made = []
    def corrupt(*args):
        owner = factory(*args)
        made.append(owner)
        owner._numeric.pivots.flags.writeable = True
        owner._numeric.pivots[0] = 0.
        return owner
    monkeypatch.setattr(terminal.owned, 'OwnedMetric', corrupt)
    with pytest.raises(ValueError, match='positive pivot'):
        terminal.OwnedOriginalTerminal(metric(o, identity, q), o, identity, q, g, 1., **budget())
    assert made[0].live_payload_bytes == 0


def test_contraction_failure_retains_denial_and_disposes(monkeypatch):
    o, identity, q, g, _, _ = fixture()
    owner = terminal.OwnedOriginalTerminal(metric(o, identity, q), o, identity, q, g, 1., **budget())
    # Negative test instrumentation, never a public construction operand.
    monkeypatch.setattr(owner, '_stored_action', lambda ar, v, t: [(Decimal(0), Decimal(0))]*len(v))
    result = owner.certify(terminal.owned.TerminalPolicy(1e-7))
    assert not result['passed'] and result['reason'] == 'contraction_not_certified'
    assert Decimal(result['kappa_upper']) == 1 and result['disposed']
