"""Directed actual-native-operand magnetic objective displacement certificates.

The real affine extension binds rounded A_b, B0, F and native Cholesky L.
It is not a quadratic approximation to a norm likelihood, an optimizer,
true-p1 stationarity proof, or complete native/resource admission.
"""

from decimal import (Decimal, Context, ROUND_FLOOR, ROUND_CEILING,
                     InvalidOperation, DivisionByZero, Overflow, Underflow,
                     Subnormal, Clamped, FloatOperation)
import math
from time import monotonic

import numpy as np
from scipy.sparse import csr_matrix

from magnetic_inverse import MagneticQuantity, native_array, owned, finite_float


class _Range(ArithmeticError):
    pass


class _Clock(ArithmeticError):
    pass


def _reuse_charge(parameters):
    """Two model keys plus twelve bounded scalar endpoints and containers."""
    return 16*parameters+24576


class _Arithmetic:
    """Each operation uses its own explicit context, never caller getcontext."""

    def __init__(self, digits, deadline):
        self.lo = Context(prec=digits, rounding=ROUND_FLOOR, Emin=-9999, Emax=9999)
        self.hi = Context(prec=digits, rounding=ROUND_CEILING, Emin=-9999, Emax=9999)
        for ctx in (self.lo, self.hi):
            for signal in (InvalidOperation, DivisionByZero, Overflow, Underflow,
                           Subnormal, Clamped, FloatOperation):
                ctx.traps[signal] = True
        self.deadline = deadline

    def check(self):
        if monotonic() > self.deadline:
            raise _Clock('wall_cap')

    def exact(self, value):
        v = Decimal.from_float(float(value))
        if not v.is_finite():
            raise _Range('nonfinite operand')
        return v, v

    def add(self, a, b):
        return self.lo.add(a[0], b[0]), self.hi.add(a[1], b[1])

    def sub(self, a, b):
        return self.lo.subtract(a[0], b[1]), self.hi.subtract(a[1], b[0])

    def mul(self, a, b):
        lower = [self.lo.multiply(x, y) for x in a for y in b]
        upper = [self.hi.multiply(x, y) for x in a for y in b]
        return min(lower), max(upper)

    def div(self, a, b):
        if b[0] <= 0 <= b[1]:
            raise _Range('division domain')
        return (min(self.lo.divide(x, y) for x in a for y in b),
                max(self.hi.divide(x, y) for x in a for y in b))

    def square(self, a):
        lo = Decimal(0) if a[0] <= 0 <= a[1] else min(self.lo.multiply(x, x) for x in a)
        return lo, max(self.hi.multiply(x, x) for x in a)

    def sqrt(self, a):
        if not (a[0].is_finite() and a[1].is_finite() and 0 < a[0] <= a[1]):
            raise _Range('positive radicand domain')
        # sqrt is HALF_EVEN even under FLOOR/CEILING. Neighbors enlarge it.
        lo = self.lo.next_minus(self.lo.sqrt(a[0]))
        hi = self.hi.next_plus(self.hi.sqrt(a[1]))
        if not (lo.is_finite() and hi.is_finite() and 0 < lo <= hi):
            raise _Range('positive norm enclosure domain')
        return lo, hi

    def sum(self, values):
        result = self.exact(0.)
        for value in values:
            result = self.add(result, value)
        return result

    def dot(self, coefficients, vector):
        self.check()
        lower = upper = Decimal(0)
        for index, (coefficient, interval) in enumerate(zip(coefficients, vector)):
            if index % 128 == 0:
                self.check()
            exact = self.exact(coefficient)[0]
            lo, hi = interval if exact >= 0 else (interval[1], interval[0])
            # Fixed exact coefficient: monotone endpoint selection followed by
            # directed fused multiply-add encloses the SAME stored-real sum.
            # No rounded coefficient, BLAS approximation or Decimal matrix cache.
            lower = self.lo.fma(exact, lo, lower)
            upper = self.hi.fma(exact, hi, upper)
        return lower, upper

    def strings(self, value):
        if not value[0].is_finite() or not value[1].is_finite() or value[0] > value[1]:
            raise _Range('ordered finite endpoint domain')
        strings = tuple(str(v) for v in value)
        if any(len(s) > 192 for s in strings):
            raise _Range('bounded endpoint serialization')
        return strings


def _keys(value, expected, name):
    if type(value) is not dict or any(type(k) is not str for k in value) or set(value) != set(expected):
        raise ValueError(f'{name}: exact closed keys required')


def _csr_metadata(matrix, a):
    if type(matrix) is not csr_matrix or matrix.dtype != np.dtype('float64'):
        raise TypeError('derivative: native float64 CSR matrix required')
    if len(matrix.shape) != 2 or matrix.shape[1] != a or not 1 <= matrix.shape[0] <= 2*a:
        raise ValueError('derivative: bounded physical shape required')
    k = matrix.shape[0]
    for value, dtype in ((matrix.data, 'float64'), (matrix.indices, 'int32'), (matrix.indptr, 'int32')):
        if type(value) is not np.ndarray or value.dtype != np.dtype(dtype) or value.ndim != 1:
            raise TypeError('derivative: closed native backing-array metadata')
    if len(matrix.data) != len(matrix.indices) or len(matrix.data) > 8*a or len(matrix.indptr) != k+1:
        raise ValueError('derivative: count/structure cap')
    return k


def _csr_scan(matrix):
    ptr, col = matrix.indptr, matrix.indices
    if (ptr[0] != 0 or ptr[-1] != len(col) or np.any(ptr < 0) or np.any(np.diff(ptr) < 0)
            or np.any(col < 0) or np.any(col >= matrix.shape[1]) or not np.isfinite(matrix.data).all()):
        raise ValueError('derivative: malformed finite CSR structure')
    for i in range(matrix.shape[0]):
        if np.any(np.diff(col[ptr[i]:ptr[i+1]]) <= 0):
            raise ValueError('derivative: canonical strictly ordered unique columns required')


class MagneticCertificate:
    """Own frozen physical, likelihood and fixed-surrogate regularization operands."""

    def __init__(self, operator, observed, noise, reference_q, lower_q, upper_q, beta, terms):
        if type(operator) is not MagneticQuantity:
            raise TypeError('operator: actual closed magnetic quantity required')
        n, a, c = operator.rows, operator.parameters, operator.components
        if any(type(v) is not int for v in (n, a, c)) or not (1 <= n <= 2048 and 1 <= a <= 2048 and c in (1, 3)):
            raise ValueError('operator: bounded native metadata required')
        d = n*c
        native_array(observed, (n, c), 'observed')
        for name, value in (('reference', reference_q), ('lower', lower_q), ('upper', upper_q)):
            native_array(value, (a,), name)
        finite_float(beta, 'beta', positive=True)
        _keys(noise, ('kind', 'values'), 'noise')
        if type(noise['kind']) is not str or noise['kind'] not in ('diagonal_sd', 'full_covariance'):
            raise ValueError('noise: exact kind required')
        covariance = noise['kind'] == 'full_covariance'
        if covariance and d > 512:
            raise ValueError('noise: full covariance component cap512')
        native_array(noise['values'], (d, d) if covariance else (n, c), 'noise.values')
        if type(terms) is not tuple or len(terms) > 7:
            raise TypeError('terms: bounded native tuple required')
        ks, nnz = 0, 0
        for term in terms:
            _keys(term, ('alpha', 'weights', 'derivative'), 'term')
            finite_float(term['alpha'], 'alpha')
            if term['alpha'] < 0.:
                raise ValueError('alpha: nonnegative required')
            k = _csr_metadata(term['derivative'], a)
            native_array(term['weights'], (k,), 'weights')
            ks += k
            nnz += len(term['derivative'].data)
        # Count native copies/workspace and conservative live Decimal/vector
        # storage before any scans/snapshots. Not a native allocator peak proof.
        budget = (8*(6*d*a+6*d*d+8*a*a+16*(d+a+ks)+4*nnz)
                  +2048*(6*d+4*a+2*ks)+32768+_reuse_charge(a))
        if budget > 805306368:
            raise ValueError('certificate: conservative live operand/vector budget')
        self.__d, self.__ref = owned(observed).ravel(), owned(reference_q)
        self.__lower, self.__upper = owned(lower_q), owned(upper_q)
        if (np.any(self.__lower < 0.) or np.any(self.__upper > 10.) or np.any(self.__lower >= self.__upper)
                or np.any(self.__ref < self.__lower) or np.any(self.__ref > self.__upper)):
            raise ValueError('certificate: strict production bounds and reference')
        self.__ab, self.__b0, self.__direction, self.__f, self.__quantity = operator.operand_snapshot()
        if self.__ab.shape != (3*n, a):
            raise ValueError('operator: source-state metadata mismatch')
        self.__noise = owned(noise['values'])
        self.__covariance = covariance
        if covariance:
            if not np.array_equal(self.__noise, self.__noise.T):
                raise ValueError('noise: exact covariance symmetry required')
            try:
                self.__lower_factor = owned(np.linalg.cholesky(self.__noise))
            except np.linalg.LinAlgError as exc:
                raise ValueError('noise: SPD covariance required') from exc
            condition = float(np.linalg.cond(self.__noise, 2))
            if not math.isfinite(condition) or condition > 1e8:
                raise ValueError('noise: covariance condition2<=1e8 required')
        elif np.any(self.__noise <= 0.):
            raise ValueError('noise: strictly positive declared SD')
        self.__terms = []
        for term in terms:
            _csr_scan(term['derivative'])
            weights = owned(term['weights'])
            if np.any(weights <= 0.):
                raise ValueError('weights: positive fixed weights required')
            matrix = term['derivative'].copy()
            for value in (matrix.data, matrix.indices, matrix.indptr):
                value.flags.writeable = False
            self.__terms.append((term['alpha'], weights, matrix))
        self.__beta, self.__n, self.__a = beta, n, a
        self.__enclosures = []
        self.arithmetic_domain = ('fixed_native_operand_magnetic_norm' if
            self.__quantity == 'exact_total_anomaly_nT' else 'fixed_native_operand_quadratic')

    def _predictions(self, q, ar):
        predictions = []
        f, background = ar.exact(self.__f), [ar.exact(x) for x in self.__b0]
        delta0 = ar.sub(ar.sum(ar.square(x) for x in background), ar.square(f))
        for i in range(self.__n):
            b = [ar.dot(row, q) for row in self.__ab[3*i:3*i+3]]
            total = [ar.add(x, y) for x, y in zip(background, b)]
            norm = ar.sqrt(ar.sum(ar.square(x) for x in total))
            if ar.div(norm, f)[0] <= Decimal.from_float(1e-8):
                raise _Range('total field direction domain')
            if self.__quantity == 'secondary_enu_nT':
                predictions.extend(b)
            elif self.__quantity == 'linear_tmi_nT':
                predictions.append(ar.dot(self.__direction, b))
            else:
                numerator = ar.add(delta0, ar.add(
                    ar.mul(ar.exact(2.), ar.sum(ar.mul(x, y) for x, y in zip(background, b))),
                    ar.sum(ar.square(x) for x in b)))
                rational = ar.div(numerator, ar.add(norm, f))
                direct = ar.sub(norm, f)
                value = max(rational[0], direct[0]), min(rational[1], direct[1])
                if value[0] > value[1]:
                    raise _Range('same native norm chain enclosure disagreement')
                predictions.append(value)
        return predictions

    def _objective(self, model, ar):
        q = [ar.exact(x) for x in model]
        residual = [ar.sub(x, ar.exact(d)) for x, d in zip(self._predictions(q, ar), self.__d)]
        if self.__covariance:
            whitened = []
            for i, value in enumerate(residual):
                lower = self.__lower_factor
                whitened.append(ar.div(ar.sub(value, ar.dot(lower[i, :i], whitened)), ar.exact(lower[i, i])))
        else:
            whitened = [ar.div(x, ar.exact(s)) for x, s in zip(residual, self.__noise.ravel())]
        phi = ar.sum(ar.square(x) for x in whitened)
        delta = [ar.sub(x, ar.exact(ref)) for x, ref in zip(q, self.__ref)]
        for alpha, weights, matrix in self.__terms:
            if alpha == 0.:
                continue
            rows = []
            for i, weight in enumerate(weights):
                start, end = matrix.indptr[i:i+2]
                vector = [delta[j] for j in matrix.indices[start:end]]
                rows.append(ar.square(ar.mul(ar.exact(weight), ar.dot(matrix.data[start:end], vector))))
            phi = ar.add(phi, ar.mul(ar.mul(ar.exact(self.__beta), ar.exact(alpha)), ar.sum(rows)))
        ar.check()
        return phi

    def _enclosed_objective(self, model, ar):
        """Same frozen operands/model bits/precision, never cached acceptance."""
        ar.check()
        digits = ar.lo.prec
        if digits not in (34, 50, 80) or ar.hi.prec != digits:
            raise ValueError('certificate: original explicit precision ladder')
        slot = None
        for index, (stored, values) in enumerate(self.__enclosures):
            if np.array_equal(stored.view(np.uint64), model.view(np.uint64)):
                slot = self.__enclosures.pop(index)
                self.__enclosures.append(slot)
                if digits in values:
                    ar.check()
                    return values[digits]
                break
        value = self._objective(model, ar)
        ar.strings(value)  # Bounded finite ordered scalar endpoints only.
        ar.check()  # Expired/partial construction is never published.
        if slot is None:
            if len(self.__enclosures) == 2:
                self.__enclosures.pop(0)
            slot = (owned(model), {})
            self.__enclosures.append(slot)
        slot[1][digits] = value
        return value

    def certify(self, q, qt, native_gradient, native_phi, native_phi_trial, iteration, trial, deadline):
        for name, value in (('q', q), ('qt', qt), ('native_gradient', native_gradient)):
            native_array(value, (self.__a,), name)
            if not np.isfinite(value).all():
                raise ValueError('certificate: finite model/gradient required')
        for name, value in (('native_phi', native_phi), ('native_phi_trial', native_phi_trial), ('deadline', deadline)):
            finite_float(value, name)
        if (type(iteration) is not int or not 0 <= iteration <= 199 or
                type(trial) is not int or not 0 <= trial <= 19):
            raise ValueError('certificate: exact bounded native counters required')
        if any(np.any(v < self.__lower) or np.any(v > self.__upper) for v in (q, qt)):
            raise ValueError('certificate: actual projected endpoints outside bounds')
        record = dict(iteration=iteration, trial=trial, native_phi_current=native_phi,
            native_phi_trial=native_phi_trial, displacement_inf_q=float(np.max(np.abs(qt-q))),
            precision_digits=None, slope_interval=None, delta_interval=None,
            armijo_margin_interval=None, arithmetic_domain=self.arithmetic_domain,
            slope_domain='recorded_native_gradient', decision='not_run', cause='native_failure', passes=0)
        if monotonic() > deadline:
            record['cause'] = 'wall_cap'
            return record
        if np.array_equal(q, qt):
            record['cause'] = 'zero_displacement'
            return record
        try:
            for count, digits in enumerate((34, 50, 80), 1):
                ar = _Arithmetic(digits, deadline)
                chord = [ar.sub(ar.exact(y), ar.exact(x)) for x, y in zip(q, qt)]
                slope = ar.dot(native_gradient, chord)
                delta = ar.sub(self._enclosed_objective(qt, ar), self._enclosed_objective(q, ar))
                margin = ar.sub(delta, ar.mul(ar.exact(1e-4), slope))
                ar.check()
                record.update(precision_digits=digits, passes=count,
                              slope_interval=ar.strings(slope), delta_interval=ar.strings(delta),
                              armijo_margin_interval=ar.strings(margin))
                if slope[0] >= 0:
                    record.update(decision='certified_reject', cause='non_descent')
                    return record
                if margin[0] > 0:
                    record.update(decision='certified_reject', cause='armijo')
                    return record
                if slope[1] < 0 and margin[1] < 0:
                    record.update(decision='certified_accept', cause='armijo')
                    return record
            record.update(decision='unresolved', cause='precision_limit')
            return record
        except (_Range, InvalidOperation, DivisionByZero, Overflow, Underflow, Subnormal, Clamped, FloatOperation):
            cause = 'range_unsupported'
        except _Clock:
            cause = 'wall_cap'
        record.update(precision_digits=None, slope_interval=None, delta_interval=None,
                      armijo_margin_interval=None, passes=0, decision='not_run', cause=cause)
        return record
