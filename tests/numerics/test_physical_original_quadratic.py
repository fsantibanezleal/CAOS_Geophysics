"""Independent Fraction source-real arithmetic, NOT a native fit acceptance."""
from dataclasses import replace
from fractions import Fraction
from time import monotonic

import numpy as np
import pytest
import scipy.sparse as sp

import physical_original_quadratic as original


def operands(covariance=False, projected=False, half=False):
    q = np.array([.2, -.3, .1])
    identity = dict(mode='fixed_linear_quadratic', runtime_epoch='source-original-test-1',
        objective_sha256='a'*64, source_inventory_sha256='b'*64, q_unit='test-native',
        physical_unit='test-physical', physical_scale=1., parameter_count=3,
        observation_rows=2, observation_components=1, beta_engine=.2, stage_index=0,
        allocation_plan_sha256='c'*64)
    g = np.array([[.1, .7, -.4], [-.2, .5, .9]])
    projection = None
    if projected:
        g = np.array([[.1, .7, -.4], [-.2, .5, .9], [.3, -.1, .4],
            [.4, -.6, .2], [.8, .2, -.3], [-.2, .7, .1]])
        projection = np.array([.6, 0., .8])
    noise = original.OriginalWhitening('diagonal_sd', np.array([.3, .7]))
    if covariance:
        c = np.array([[.16, .048], [.048, .25]])
        noise = original.OriginalWhitening('stored_lower_cholesky', np.linalg.cholesky(c), c)
    terms = (original.owned.QuadraticTerm(1., sp.diags(np.array([.7, .8, .9]), format='csr'), sp.eye(3, format='csr')),
        original.owned.QuadraticTerm(2., sp.eye(2, format='csr'),
            sp.csr_matrix(np.array([[-1., 1., 0.], [0., -1., 1.]]))))
    dto = original.OriginalQuadraticOperands(original.owned.binding_for(identity, q), 6,
        g, projection, noise, np.array([.4, -.1]), np.array([-.1, .05, 0.]),
        -np.ones(3), np.ones(3), .5 if half else 1., .2, terms, g, projection)
    return dto, identity, q


def budget(seconds=120.):
    return dict(deadline=monotonic()+seconds, resource_limit_bytes=2*1024**3, admitted_bytes=2*1024**3)


def mat(a, vector):
    values = a.toarray() if sp.issparse(a) else a
    return [sum(Fraction(float(v))*x for v, x in zip(row, vector)) for row in values]


def mapping(o, v, adjoint=False):
    if adjoint:
        if o.projection is not None:
            v = [Fraction(float(p))*x for x in v for p in o.projection]
        return mat(o.sensitivity.T, v)
    value = mat(o.sensitivity, v)
    if o.projection is None:
        return value
    return [sum(Fraction(float(p))*x for p, x in zip(o.projection, value[i:i+3])) for i in range(0, len(value), 3)]


def whiten(o, v, adjoint=False):
    if o.whitening.kind == 'diagonal_sd':
        return [x/Fraction(float(s)) for x, s in zip(v, o.whitening.values)]
    l = o.whitening.values
    result = [None]*len(v)
    order = range(len(v)-1, -1, -1) if adjoint else range(len(v))
    for i in order:
        columns = range(i+1, len(v)) if adjoint else range(i)
        result[i] = (v[i]-sum(Fraction(float(l[j, i] if adjoint else l[i, j]))*result[j]
            for j in columns))/Fraction(float(l[i, i]))
    return result


def exact(o, q):
    qv = [Fraction(float(v)) for v in q]
    residual = [v-Fraction(float(d)) for v, d in zip(mapping(o, qv), o.observations)]
    wr = whiten(o, residual)
    phi = Fraction(o.likelihood_scale)*sum(v*v for v in wr)
    g = [2*Fraction(o.likelihood_scale)*v for v in mapping(o, whiten(o, wr, True), True)]
    delta = [v-Fraction(float(ref)) for v, ref in zip(qv, o.reference)]
    for term in o.terms:
        r = mat(term.weights, mat(term.derivative, delta))
        phi += Fraction(o.beta)*Fraction(term.alpha)*sum(v*v for v in r)
        term_g = mat(term.derivative.T, mat(term.weights.T, r))
        g = [old+2*Fraction(o.beta)*Fraction(term.alpha)*v for old, v in zip(g, term_g)]
    return phi, g


@pytest.mark.parametrize('covariance', [False, True])
@pytest.mark.parametrize('projected', [False, True])
@pytest.mark.parametrize('half', [False, True])
def test_original_fraction_gradient_delta_and_native_slope(covariance, projected, half):
    o, identity, q = operands(covariance, projected, half)
    phi, exact_gradient = exact(o, q)
    enclosed = original.source_gradient(o, identity, q, **budget())
    for value, (lo, hi) in zip(exact_gradient, enclosed):
        assert Fraction(lo) <= value <= Fraction(hi)
    g = np.array([float(v) for v in exact_gradient])
    qt = q-1e-3*g
    trial, _ = exact(o, qt)
    record = original.certify_chord(o, identity, q, qt, g, float(phi), float(trial), 0, 0, **budget())
    original.intervals._validate_record(record)
    assert record['decision'] == 'certified_accept'
    assert Fraction(record['delta_interval'][0]) <= trial-phi <= Fraction(record['delta_interval'][1])
    slope = sum(Fraction(float(v))*(Fraction(float(y))-Fraction(float(x))) for v, x, y in zip(g, q, qt))
    assert Fraction(record['slope_interval'][0]) <= slope <= Fraction(record['slope_interval'][1])
    assert Fraction(record['armijo_margin_interval'][1]) < 0


def test_original_sd_division_not_rounded_reciprocal_reinterpretation():
    o, _, q = operands()
    phi, _ = exact(o, q)
    r = mapping(o, [Fraction(float(v)) for v in q])
    residual = [x-Fraction(float(d)) for x, d in zip(r, o.observations)]
    original_data = sum((x/Fraction(float(s)))**2 for x, s in zip(residual, o.whitening.values))
    rounded_data = sum((x*Fraction(float(1./s)))**2 for x, s in zip(residual, o.whitening.values))
    assert original_data != rounded_data and phi > original_data


@pytest.mark.parametrize('fault', ['model', 'beta', 'kind', 'sd', 'smallness', 'projection', 'budget', 'csr'])
def test_closed_original_faults_before_arithmetic(fault):
    o, identity, q = operands()
    args = budget()
    if fault == 'model':
        o = replace(o, binding=replace(o.binding, model_sha256='f'*64))
    elif fault == 'beta':
        o = replace(o, beta=.3)
    elif fault == 'kind':
        o = replace(o, whitening=replace(o.whitening, kind='inverse_callback'))
    elif fault == 'sd':
        o.whitening.values[0] = 0.
    elif fault == 'smallness':
        o.terms[0].weights.data[0] = -1.
    elif fault == 'projection':
        o = replace(o, projection=np.array([2., 0., 0.]))
    elif fault == 'budget':
        args['admitted_bytes'] = 1
    elif fault == 'csr':
        o.terms[0].derivative.indptr[-1] += 1
    with pytest.raises((TypeError, ValueError)):
        original.source_gradient(o, identity, q, **args)


@pytest.mark.parametrize('fault', ['factor', 'symmetry', 'triangle'])
def test_original_native_stored_factor_not_arbitrary_SPD(fault):
    o, identity, q = operands(True)
    if fault == 'factor':
        o.whitening.values[0, 0] = np.nextafter(o.whitening.values[0, 0], np.inf)
    elif fault == 'symmetry':
        o.whitening.covariance[0, 1] += .1
    else:
        o.whitening.values[0, 1] = .1
    with pytest.raises(ValueError):
        original.source_gradient(o, identity, q, **budget())


def test_original_zero_non_descent_box_and_expiry():
    o, identity, q = operands()
    phi, gg = exact(o, q)
    g = np.array([float(v) for v in gg])
    zero = original.certify_chord(o, identity, q, q, g, float(phi), float(phi), 0, 0, **budget())
    assert zero['cause'] == 'zero_displacement' and zero['decision'] == 'not_run'
    qt = q+1e-3*g
    reject = original.certify_chord(o, identity, q, qt, g, float(phi), float(exact(o, qt)[0]), 0, 0, **budget())
    assert reject['cause'] == 'non_descent' and reject['decision'] == 'certified_reject'
    expired = original.certify_chord(o, identity, q, qt, g, float(phi), float(phi), 0, 0, **budget(-1.))
    assert expired['cause'] == 'wall_cap' and expired['decision'] == 'not_run'
    with pytest.raises(ValueError, match='outside box'):
        original.certify_chord(o, identity, q, np.full(3, 2.), g, float(phi), float(phi), 0, 0, **budget())
    with pytest.raises(ValueError):
        original.certify_chord(o, identity, q, qt, g, float(phi), float(phi), True, 0, **budget())


@pytest.mark.parametrize('key,value', [
    ('parameter_count', True), ('observation_rows', '2'), ('observation_components', True),
    ('observation_components', 2), ('observation_rows', 2049), ('parameter_count', 4097),
    ('stage_index', 21), ('stage_index', False), ('physical_scale', 1),
    ('beta_engine', float('nan')), ('objective_sha256', 'X'*64),
    ('runtime_epoch', ''), ('mode', 'nonlinear_gauss_newton'), ('extra', 'not_closed'),
])
def test_literal_identity_refuses_before_source_access(key, value):
    o, identity, q = operands()
    identity[key] = value
    # Bad source proves no matrix/factor scan was used to validate identity.
    o = replace(o, sensitivity=None)
    with pytest.raises(ValueError, match='identity|digest|strings|counts'):
        original.source_gradient(o, identity, q, **budget())


def test_original_covariance_condition_not_relaxed():
    o, identity, q = operands(True)
    c = np.diag(np.array([1., 1e-9]))
    o = replace(o, whitening=original.OriginalWhitening('stored_lower_cholesky', np.linalg.cholesky(c), c))
    with pytest.raises(ValueError, match='condition2'):
        original.source_gradient(o, identity, q, **budget())


def test_original_source_vectors_must_have_closed_contiguous_storage():
    o, identity, q = operands()
    q = np.array([q[0], 0., q[1], 0., q[2], 0.])[::2]
    assert not q.flags.c_contiguous
    with pytest.raises(ValueError, match='physical factors'):
        original.source_gradient(o, identity, q, **budget())


def test_original_grouped_projection_cannot_change_vector_observation_contract():
    o, identity, q = operands(projected=True)
    identity['observation_rows'] = 2
    identity['observation_components'] = 3
    o = replace(o, source_components=18, sensitivity=np.ones((18, 3)),
        observations=np.zeros(6), whitening=original.OriginalWhitening('diagonal_sd', np.ones(6)))
    with pytest.raises(ValueError, match='scalar observations'):
        original.source_gradient(o, identity, q, **budget())


def test_literal_source_phase_bound_and_one_byte_short_refusal():
    o, identity, q = operands()
    result = original.validate(o, identity, q, **budget())
    phase = result['arithmetic_phase']
    assert phase['endpoint_bytes'] == 2048*(6*3+6*6+4*3)
    assert phase['operand_and_sparse_copy_bytes'] == 2*result['operand_payload_bytes']
    assert result['maximum'] == result['original']['maximum']+max(8*1024**2, sum(phase.values()))
    args = budget()
    args['admitted_bytes'] = result['maximum']-1
    with pytest.raises(ValueError, match='source-bound original phases'):
        original.source_gradient(o, identity, q, **args)


def test_small_view_does_not_hide_large_original_backing():
    o, identity, q = operands()
    hidden = np.zeros(1_100_000)[:2]
    assert hidden.nbytes == 16 and hidden.base.nbytes > original.RESERVE_BYTES
    with pytest.raises(ValueError, match='source-bound original phases'):
        original.source_gradient(replace(o, observations=hidden), identity, q, **budget())


def test_foreign_buffer_backing_is_not_native_source_storage():
    o, identity, q = operands()
    foreign = np.frombuffer(bytearray(16), dtype=np.float64)
    with pytest.raises(ValueError, match='ndarray backing'):
        original.source_gradient(replace(o, observations=foreign), identity, q, **budget())


def test_loaded_endpoint_pair_storage_guard(monkeypatch):
    o, identity, q = operands()
    monkeypatch.setattr(original, 'getsizeof', lambda _: 2048)
    with pytest.raises(ValueError, match='endpoint storage'):
        original.source_gradient(o, identity, q, **budget())
