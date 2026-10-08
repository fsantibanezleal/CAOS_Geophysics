"""TEST/research only: exact frozen-row target and nested float error bounds.

Never imported by a product pipeline, optimizer, terminal or source admission.
No Hessian/solve, tolerance substitution or rounded native gradient oracle.
"""
from decimal import Decimal, Context, localcontext, ROUND_HALF_EVEN
from fractions import Fraction as F
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np
import scipy.sparse as sp

U = F(1, 2**53)
TINY = F(1, 2**1074)
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _gamma(count):
    if type(count) is not int or not 0 <= count <= 8192:
        raise ValueError('bounded research arithmetic count')
    return count*U/(1-count*U)


def _enclose(actual, exact, bounds):
    if (type(actual) is not np.ndarray or actual.dtype != np.float64
            or actual.ndim != 1 or len(actual) != len(exact)
            or len(bounds) != len(exact) or not np.isfinite(actual).all()
            or any(b < 0 for b in bounds)):
        raise ValueError('finite bounded binary64 research operation')
    if any(abs(F(float(a))-e) > b for a, e, b in zip(actual, exact, bounds)):
        raise ValueError('independent nested arithmetic enclosure failed')
    return actual, exact, bounds


def _literal(value):
    actual = np.asarray(value, dtype=np.float64)
    return _enclose(actual, list(map(lambda x: F(float(x)), actual)), [F(0)]*len(actual))


def _mat(matrix, value, check):
    check()
    if sp.issparse(matrix):
        matrix = matrix.tocsr()
        if matrix.dtype != np.float64 or not np.isfinite(matrix.data).all():
            raise ValueError('literal finite binary64 sparse source')
        def row(i):
            begin, end = matrix.indptr[i:i+2]
            return zip(matrix.indices[begin:end], matrix.data[begin:end])
    else:
        if type(matrix) is not np.ndarray or matrix.dtype != np.float64 or not np.isfinite(matrix).all():
            raise ValueError('literal finite binary64 dense source')
        def row(i):
            return enumerate(matrix[i])
    actual, target, error = value
    if matrix.ndim != 2 or matrix.shape[1] != len(actual) or max(matrix.shape) > 4096:
        raise ValueError('bounded literal research source shape')
    exact, bounds = [], []
    for i in range(matrix.shape[0]):
        check()
        terms = [(int(j), F(float(a))) for j, a in row(i)]
        exact.append(sum((a*target[j] for j, a in terms), F(0)))
        propagated = sum((abs(a)*error[j] for j, a in terms), F(0))
        magnitude = sum((abs(a*F(float(actual[j]))) for j, a in terms), F(0))
        bounds.append(propagated+_gamma(2*len(terms))*magnitude+len(terms)*TINY)
    result = _enclose(np.asarray(matrix@actual), exact, bounds)
    check()
    return result


def _scale(coefficient, value):
    actual, exact, bounds = value
    coefficient = float(coefficient)
    if not np.isfinite(coefficient):
        raise ValueError('finite binary64 research multiplier')
    c = F(coefficient)
    return _enclose(coefficient*actual, [c*x for x in exact],
        [abs(c)*b+_gamma(1)*abs(c*F(float(a)))+TINY for a, b in zip(actual, bounds)])


def _add(left, right):
    a, x, b = left; c, y, d = right
    if len(a) != len(c):
        raise ValueError('literal research sum shape')
    return _enclose(a+c, [s+t for s, t in zip(x, y)],
        [bb+dd+_gamma(1)*abs(F(float(aa))+F(float(cc)))+TINY
            for aa, cc, bb, dd in zip(a, c, b, d)])


def _decimal(value):
    return Decimal(value.numerator)/Decimal(value.denominator)


def gradient_evidence(owner, derivative):
    """Bound actual nested native rounding; distinguish stored/ideal weights.

    The result is research evidence, not an optimizer gate or fit receipt.
    Fraction is confined to at most64 parameters/256 observations/30seconds.
    """
    import gravity_irls_original as original
    import gravity_irls_face as face
    if type(owner) is not original.GravityIRLSPartition or type(derivative) is not face._CanonicalFaceLinearization:
        raise TypeError('closed original source research owners')
    if derivative.owner is not owner or not derivative.face['derivative_supported']:
        raise ValueError('same original derivative owner and supported face')
    deadline = min(owner.deadline, monotonic()+30.)
    def check():
        # The derivative performs owner.check inside its disposal boundary.
        # A direct preliminary owner expiry must not bypass that boundary.
        derivative.check()
        if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != SOURCE_SHA256:
            derivative.close()
            raise ValueError('test gradient arithmetic loaded source drift')
        if monotonic() > deadline:
            raise TimeoutError('bounded gradient arithmetic research30s')
    check()
    problem, stage, q = owner.problem, derivative._stage, derivative.q
    G, W = problem['simulation'].G, problem['misfit'].W
    if G.shape[1] > 64 or G.shape[0] > 256:
        raise ValueError('small original research shape64/256, not matrix authorization')
    # Native literal nesting, no A=W@G substitution or squared rounded W.
    displacement = _add(_literal(q), _scale(-1., _literal(problem['reference_q'])))
    residual = _add(_mat(G, _literal(q), check), _scale(-1., _literal(problem['misfit'].data.dobs)))
    data = _scale(2., _mat(G.T, _mat(W.T, _mat(W, residual, check), check), check))
    terms = []
    for alpha, child in zip(stage['problem']['regularization'].multipliers,
            stage['problem']['regularization'].objfcts):
        D = child.f_m_deriv(q)
        fm = _mat(D, displacement, check)
        # SparseSmallness's identity mapping and each original smoothness
        # reference flag are verified by literal native f_m, not assumed.
        if not np.array_equal(fm[0], child.f_m(q)):
            raise ValueError('original source reference/mapping nesting mismatch')
        term = _mat(2.*D.T, _mat(child.W.T, _mat(child.W, fm, check), check), check)
        terms.append(_scale(alpha, term))
    regularizer = _literal(np.zeros(len(q)))
    for term in terms:
        regularizer = _add(regularizer, term)
    total = _add(data, _scale(problem['beta_engine'], regularizer))
    check()
    native = derivative._objective.evaluate(q, True, False)[1]
    if not np.array_equal(total[0], native):
        raise ValueError('literal actual native gradient operation mismatch')
    # Exact frozen stored-weight gradient versus real ideal p1 smallness.
    # Smoothness and data retain their original literal source operands.
    frozen_other = [data[1][i]+F(float(problem['beta_engine']))*
        sum((term[1][i] for term in terms[1:]), F(0)) for i in range(len(q))]
    baseW = problem['regularization'].objfcts[0].W.diagonal()
    ideal = []
    for digits in (80, 120):
        with localcontext(Context(prec=digits, rounding=ROUND_HALF_EVEN)):
            x = list(map(_decimal, displacement[1]))
            eps = Decimal.from_float(float(stage['epsilon'][0]))
            s = (max(abs(v) for v in x)**2+eps**2).sqrt()
            beta = Decimal.from_float(float(problem['beta_engine']))
            alpha = Decimal.from_float(float(stage['problem']['regularization'].multipliers[0]))
            ideal.append([_decimal(other)+2*beta*alpha*Decimal.from_float(float(w))**2*s*v/(v*v+eps*eps).sqrt()
                for other, w, v in zip(frozen_other, baseW, x)])
            check()
    with localcontext(Context(prec=120, rounding=ROUND_HALF_EVEN)):
        stability = max(abs(a-b) for a, b in zip(*ideal))
        if stability > Decimal('1e-60'):
            raise ValueError('independent ideal precision stability failed')
        weight_error = max(abs(_decimal(v)-i) for v, i in zip(total[1], ideal[-1]))
        native_ideal_error = max(abs(Decimal.from_float(float(v))-i) for v, i in zip(native, ideal[-1]))
    arithmetic_error = max(abs(F(float(a))-e) for a, e in zip(native, total[1]))
    check()
    return dict(schema='m02-test-native-gradient-decomposition-1',
        source_sha256=face.SOURCE_SHA256, oracle_source_sha256=SOURCE_SHA256,
        stage_sha256=stage['objective_sha256'],
        native_gradient=native.copy(), exact_frozen_gradient=tuple(map(str, total[1])),
        arithmetic_error_exact=str(arithmetic_error), arithmetic_bound_exact=str(max(total[2])),
        stored_weight_ideal_error=str(weight_error), native_ideal_error=str(native_ideal_error),
        ideal_precision_stability=str(stability), enclosure_passed=True,
        original_retained_1e12_gate_upgraded=False, native_fit_accepted=False,
        recurrence_enabled=False, actual_CG_calls=0, actual_minimize_calls=0)
