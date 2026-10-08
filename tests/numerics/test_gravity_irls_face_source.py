"""Actual original source derivative controls, no minimize, CG or recurrence."""
from decimal import Decimal, localcontext
from time import monotonic
from sys import getsizeof

import numpy as np
import pytest

import gravity_irls_face as face
import gravity_irls_original as physical
from test_gravity_l2 import tiny, noise
from test_gravity_irls import policy


def owner_and_model(branch, offset=0.):
    request, observed, prior, *_ = tiny()
    request['mesh']['active'][:] = True
    for key, value in (('lower_kg_m3', -1500.), ('upper_kg_m3', 1500.),
            ('start_kg_m3', 0.), ('reference_kg_m3', offset*1000.)):
        prior[key] = np.full(12, value)
    q = offset+np.linspace(-.2, .4, 12)
    if branch == 'binding_plateau':
        q[:2] = -1.5
        # Control source only: force literal lower signs through actual data
        # misfit, not an injected gradient or chosen free mask. No fit is run.
        observed = request['background_mgal']+np.full(4, 1000.)
    elif branch == 'free_tie':
        q[:2] = [offset-.6, offset+.6]
    owner = physical.GravityIRLSPartition(request, observed, noise(), prior,
        np.arange(4, dtype=np.int64), .01, deadline=monotonic()+120.)
    return owner, q


@pytest.mark.parametrize('branch', ['binding_plateau', 'free_unique'])
@pytest.mark.parametrize('offset', [0., .137])
def test_actual_original_closed_free_principal_derivative(branch, offset):
    owner, q = owner_and_model(branch, offset)
    derivative = None
    try:
        derivative = face._CanonicalFaceLinearization(owner, q, policy(), 17, policy()['epsilon_floor'])
        assert derivative.face['branch'] == ('native_binding_max_constant_scale'
            if branch == 'binding_plateau' else 'native_free_unique_max_rank_one')
        free = derivative.face['free']
        problem = owner.problem
        stage = derivative._stage
        G = problem['simulation'].G
        W = problem['misfit'].W.toarray()
        h0 = (W@G).T@(W@G)  # Independent dense TEST-only reference.
        for alpha, child in zip(stage['problem']['regularization'].multipliers[1:],
                stage['problem']['regularization'].objfcts[1:]):
            B = (child.W@child.f_m_deriv(problem['reference_q'])).toarray()
            h0 += problem['beta_engine']*alpha*(B.T@B)
        x = q-problem['reference_q']; eps = stage['epsilon'][0]
        v = problem['beta_engine']*problem['regularization'].multipliers[0]*problem['regularization'].objfcts[0].W.diagonal()**2
        s = np.sqrt(max(abs(x))**2+eps**2)
        M = h0+np.diag(v*s*eps**2/(x*x+eps*eps)**1.5)
        vector = np.linspace(.017, -.023, len(free))
        expected = M[np.ix_(free, free)]@vector
        np.testing.assert_allclose(derivative.action(vector), expected, rtol=1e-13, atol=1e-13)
        full = expected.copy()
        if not derivative.face['constant_scale']:
            j = derivative.face['maximum_index']
            full += (v*x*x[j]/(np.sqrt(x*x+eps*eps)*s))[free]*vector[np.flatnonzero(free == j)[0]]
        np.testing.assert_allclose(derivative.action(vector, full=True), full, rtol=1e-13, atol=1e-13)
        # Independent high-precision nonlinear smallness FD on this literal
        # fixed face. This is NOT the retained cf2 gradient-tolerance gate.
        embedded = np.zeros(len(q)); embedded[free] = vector
        def nonlinear(value):
            e = Decimal.from_float(eps)
            maximum = max(z.copy_abs() for z in value)
            scale = (maximum*maximum+e*e).sqrt()
            return [Decimal.from_float(float(weight))*scale*z/(z*z+e*e).sqrt()
                for weight, z in zip(v, value)]
        last = None
        for digits in (80, 120):
            with localcontext() as context:
                context.prec = digits
                # Literal source normalized displacement, not a rounded
                # different reference after a finite-difference perturbation.
                center = [Decimal.from_float(float(z)) for z in x]
                step = Decimal('1e-20')
                plus = nonlinear([z+step*Decimal.from_float(float(d)) for z, d in zip(center, embedded)])
                minus = nonlinear([z-step*Decimal.from_float(float(d)) for z, d in zip(center, embedded)])
                result = [(plus[i]-minus[i])/(2*step) for i in free]
                if last is not None:
                    assert max(abs(a-b) for a, b in zip(last, result)) < Decimal('1e-50')
                last = result
                difference = full-h0[np.ix_(free, free)]@vector
                np.testing.assert_allclose(np.array(list(map(float, result))), difference, rtol=1e-11, atol=1e-13)
        metric = derivative.metric()
        assert metric is derivative.metric() and metric.live_payload_bytes > 0
        assert derivative.record['metric_constructed'] and derivative.record['derivative_constructed']
        assert not derivative.record['native_fit_accepted'] and not derivative.record['recurrence_enabled']
        assert derivative.live_payload_bytes < derivative.allocation['maximum'] <= 2*1024**3
        assert derivative.record['metric_identity']['stage_index'] == 17
        def retained_bytes(value):
            if type(value) is dict:
                return getsizeof(value)+sum(retained_bytes(k)+retained_bytes(v) for k, v in value.items())
            if type(value) in (tuple, list):
                return getsizeof(value)+sum(map(retained_bytes, value))
            return getsizeof(value)
        assert retained_bytes(derivative.record)+retained_bytes(derivative.face) < (
            derivative.allocation['metadata_bytes']+derivative.allocation['derivative_source_parameter_workspace_bytes'])
    finally:
        if derivative is not None:
            derivative.close()
            assert derivative.live_payload_bytes == 0
        owner.close()


def test_actual_free_tie_disables_before_operator_or_metric(monkeypatch):
    owner, q = owner_and_model('free_tie')
    try:
        monkeypatch.setattr(face.interior, '_linearization', lambda *a: pytest.fail('unsupported face constructed derivative'))
        derivative = face._CanonicalFaceLinearization(owner, q, policy(), 17, policy()['epsilon_floor'])
        assert derivative.face['branch'] == 'disabled_free_tied_max'
        assert not derivative.record['derivative_constructed'] and not derivative.record['metric_constructed']
        with pytest.raises(ValueError, match='disabled before metric'):
            derivative.metric()
        derivative.close()
        assert derivative.live_payload_bytes == 0
    finally:
        owner.close()


@pytest.mark.parametrize('kind', ['deadline', 'source', 'dispose', 'model', 'root', 'branch'])
def test_owned_derivative_source_deadline_and_terminal_lifetime(kind, monkeypatch):
    owner, q = owner_and_model('free_unique')
    derivative = None
    try:
        derivative = face._CanonicalFaceLinearization(owner, q, policy(), 17, policy()['epsilon_floor'])
        derivative.metric()
        if kind == 'deadline':
            owner.deadline = monotonic()-1.
        elif kind == 'source':
            monkeypatch.setattr(face, 'SOURCE_SHA256', '0'*64)
        elif kind == 'dispose':
            owner.close()
        elif kind == 'branch':
            derivative.face['branch'] = 'native_binding_max_constant_scale'
        else:
            value = getattr(derivative, 'q' if kind == 'model' else 'root').copy()
            value[0] += .1
            setattr(derivative, 'q' if kind == 'model' else 'root', value)
        with pytest.raises((ValueError, physical.original.physics.metric.DeadlineExceeded)):
            derivative.action(np.ones(len(derivative.face['free'])))
        assert derivative.live_payload_bytes == 0 and derivative.record['disposed']
    finally:
        if derivative is not None:
            derivative.close()
        owner.close()


def test_caller_objects_are_not_physical_owner_admission():
    with pytest.raises(TypeError, match='exact closed original physical owner'):
        face._CanonicalFaceLinearization(object(), np.zeros(12), policy(), 17, policy()['epsilon_floor'])


@pytest.mark.parametrize('covariance', [False, True])
def test_original_full48_coexisting_derivative_phase_dictionary(covariance):
    original = physical.allocation_plan(288, 192, 48, covariance)
    value = face._derivative_allocation(original)
    assert value['maximum'] == sum(v for k, v in value.items() if k != 'maximum')
    assert value['original_partition_bytes'] == original['admitted_bytes']
    assert value['derivative_kernel_bytes'] == physical.original.owned.kernel.allocation(288, 192, 48, covariance)['maximum']
    assert value['derivative_source_jacobian_bytes'] == 16*192*48
    assert value['maximum'] <= 2*1024**3
    assert value['maximum'] == (2147055016 if covariance else 2139977128)
    bad = dict(original, admitted_bytes=original['admitted_bytes']-1)
    with pytest.raises(ValueError, match='exact original retained partition dictionary'):
        face._derivative_allocation(bad)
