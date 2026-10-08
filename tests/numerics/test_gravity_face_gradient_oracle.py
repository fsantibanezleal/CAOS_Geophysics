"""Independent original nested-gradient controls; no optimizer acceptance."""
from decimal import localcontext, ROUND_DOWN
from fractions import Fraction as F

import numpy as np
import pytest
import scipy.sparse as sp

import gravity_irls_face as face
import gravity_face_gradient_oracle as oracle
from test_gravity_irls_face_source import owner_and_model, policy


@pytest.mark.parametrize('sparse', [False, True])
def test_signed_cancellation_and_subnormal_exact_enclosure(sparse):
    matrix = np.array([[1e12, -1e12, .7], [np.nextafter(0., 1.), 0., 0.], [-.9, .3, 1.]])
    value = oracle._literal(np.array([1.1, 1.1, .13]))
    if sparse:
        matrix = sp.csr_matrix(matrix)
    result = oracle._mat(matrix, value, lambda: None)
    assert abs(F(float(result[0][0]))-result[1][0]) <= result[2][0]
    assert result[1][1] == oracle.TINY*F(1.1)
    changed = result[0].copy(); changed[0] += 1.
    with pytest.raises(ValueError, match='enclosure failed'):
        oracle._enclose(changed, result[1], result[2])


@pytest.mark.parametrize('branch', ['free_unique', 'binding_plateau'])
@pytest.mark.parametrize('offset', [0., .137])
def test_literal_original_native_gradient_decomposition(branch, offset):
    owner, q = owner_and_model(branch, offset)
    derivative = None
    try:
        derivative = face._CanonicalFaceLinearization(owner, q, policy(), 17, policy()['epsilon_floor'])
        evidence = oracle.gradient_evidence(owner, derivative)
        assert evidence['enclosure_passed']
        assert F(evidence['arithmetic_error_exact']) <= F(evidence['arithmetic_bound_exact'])
        assert not evidence['recurrence_enabled'] and not evidence['native_fit_accepted']
        assert evidence['actual_CG_calls'] == evidence['actual_minimize_calls'] == 0
        with localcontext() as context:
            context.prec = 3; context.rounding = ROUND_DOWN
            other = oracle.gradient_evidence(owner, derivative)
        for key in ('arithmetic_error_exact', 'arithmetic_bound_exact',
                'stored_weight_ideal_error', 'native_ideal_error', 'ideal_precision_stability'):
            assert other[key] == evidence[key]
    finally:
        if derivative is not None:
            derivative.close()
        owner.close()


def test_arbitrary_owner_or_derivative_is_not_evidence():
    with pytest.raises(TypeError, match='closed original source'):
        oracle.gradient_evidence(object(), object())


@pytest.mark.parametrize('failure', ['source', 'oracle_source', 'model', 'expired'])
def test_gradient_evidence_source_state_and_deadline(failure, monkeypatch):
    from time import monotonic
    owner, q = owner_and_model('free_unique')
    derivative = None
    try:
        derivative = face._CanonicalFaceLinearization(owner, q, policy(), 17, policy()['epsilon_floor'])
        if failure == 'source':
            monkeypatch.setattr(face, 'SOURCE_SHA256', '0'*64)
        elif failure == 'oracle_source':
            monkeypatch.setattr(oracle, 'SOURCE_SHA256', '0'*64)
        elif failure == 'model':
            derivative.q = q.copy(); derivative.q[3] += .1
        else:
            owner.deadline = monotonic()-1.
        with pytest.raises((ValueError, RuntimeError)):
            oracle.gradient_evidence(owner, derivative)
        assert derivative.live_payload_bytes == 0
    finally:
        if derivative is not None:
            derivative.close()
        owner.close()
