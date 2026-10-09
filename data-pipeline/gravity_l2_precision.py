"""Private cpu-4 nested-operand outward Armijo evaluator, no inverse fallback.

No I/O, caller hook, dense product/normal matrix, Fraction, vendor mutation,
stopping shortcut or precision-selected acceptance tolerance. Only the genuine
owner-created fixed linear problem supplies operands. Native outputs stay native.
"""
from decimal import (Decimal, Context, ROUND_FLOOR, ROUND_CEILING, InvalidOperation,
                     DivisionByZero, Overflow, Underflow, Subnormal, Clamped, FloatOperation,
                     DecimalException)
import re
from time import monotonic

import numpy as np
import scipy.sparse as sp


_KEYS = ('iteration', 'trial', 'native_phi_current', 'native_phi_trial', 'displacement_inf_q',
         'precision_digits', 'slope_interval', 'delta_interval', 'armijo_margin_interval',
         'arithmetic_domain', 'slope_domain', 'decision', 'cause', 'passes')
_DECIMAL = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:E[+-]?[0-9]+)?\Z', re.ASCII)
_ZERO, _TWO = Decimal(0), Decimal(2)


def _record(iteration, trial, phi, phit):
    return dict(zip(_KEYS, (iteration, trial,
        float(phi) if np.isfinite(phi) else None, float(phit) if np.isfinite(phit) else None,
        None, None, None, None, None, 'fixed_native_operand_quadratic', 'recorded_native_gradient',
        'not_run', 'native_failure', 0)))


def _validate_record(r):
    if type(r) is not dict or set(r) != set(_KEYS): raise ValueError('precision: exact14keys required')
    for key, maximum in [('iteration', 199), ('trial', 19), ('passes', 3)]:
        if type(r[key]) is not int or not 0 <= r[key] <= maximum: raise ValueError('precision: counter')
    for key in ('native_phi_current', 'native_phi_trial', 'displacement_inf_q'):
        value = r[key]
        if value is not None and (type(value) is not float or not np.isfinite(value)):
            raise ValueError('precision: finite native scalar or None')
    if r['displacement_inf_q'] is not None and r['displacement_inf_q'] < 0: raise ValueError('precision: displacement')
    if r['precision_digits'] is not None and (type(r['precision_digits']) is not int or r['precision_digits'] not in (34,50,80)):
        raise ValueError('precision: fixed ladder')
    for key in ('slope_interval', 'delta_interval', 'armijo_margin_interval'):
        pair = r[key]
        if pair is None: continue
        if type(pair) is not tuple or len(pair) != 2: raise ValueError('precision: interval pair')
        if any(type(v) is not str or len(v)>192 or not _DECIMAL.fullmatch(v) for v in pair):
            raise ValueError('precision: bounded decimal grammar')
        lo, hi = map(Decimal, pair)
        if not lo.is_finite() or not hi.is_finite() or lo>hi or any(abs(v.adjusted())>9999 for v in (lo,hi)):
            raise ValueError('precision: interval range/order')
    if r['arithmetic_domain'] != 'fixed_native_operand_quadratic' or r['slope_domain'] != 'recorded_native_gradient':
        raise ValueError('precision: exact domain')
    if r['decision'] not in ('certified_accept','certified_reject','unresolved','not_run'):
        raise ValueError('precision: decision')
    if r['cause'] not in ('armijo','non_descent','zero_displacement','precision_limit','range_unsupported','wall_cap','native_failure'):
        raise ValueError('precision: cause')
    intervals = [r[k] for k in ('slope_interval','delta_interval','armijo_margin_interval')]
    if r['passes'] == 0:
        if r['precision_digits'] is not None or any(x is not None for x in intervals): raise ValueError('precision: unavailable')
    elif r['precision_digits'] != (34,50,80)[r['passes']-1]: raise ValueError('precision: actual passes')
    if r['decision'] == 'certified_accept':
        if (r['cause'] != 'armijo' or r['passes']==0 or any(x is None for x in intervals)
                or r['native_phi_current'] is None or r['native_phi_trial'] is None
                or r['displacement_inf_q'] is None or r['displacement_inf_q']<=0
                or Decimal(r['slope_interval'][1])>=0 or Decimal(r['armijo_margin_interval'][1])>=0):
            raise ValueError('precision: strict acceptance certificate')
    elif r['decision']=='not_run':
        if r['passes']!=0 or r['cause'] in ('armijo','precision_limit'):
            raise ValueError('precision: no partial/unexecuted certificate')
    elif r['decision']=='certified_reject':
        if r['passes']==0 or r['slope_interval'] is None: raise ValueError('precision: rejection evidence')
        if r['cause']=='non_descent':
            if Decimal(r['slope_interval'][0])<0: raise ValueError('precision: certified non-descent sign')
        elif r['cause']=='armijo':
            if any(x is None for x in intervals) or Decimal(r['armijo_margin_interval'][0])<=0:
                raise ValueError('precision: certified rejection sign')
        else: raise ValueError('precision: rejection cause')
    elif (r['cause']!='precision_limit' or r['passes']!=3 or any(x is None for x in intervals)):
        raise ValueError('precision: complete exhausted ladder required')
    return r


class _Expired(Exception):
    pass


class _Intervals:
    """Explicit isolated contexts; never operates through the caller context."""
    def __init__(self, digits, deadline):
        traps = [InvalidOperation,DivisionByZero,Overflow,Underflow,Subnormal,Clamped,FloatOperation]
        self.lo = Context(prec=digits,rounding=ROUND_FLOOR,Emin=-9999,Emax=9999,traps=traps)
        self.hi = Context(prec=digits,rounding=ROUND_CEILING,Emin=-9999,Emax=9999,traps=traps)
        self.deadline = deadline
        self._use_native_rows = digits == 34
        self._bounds = {}

    def check(self):
        if monotonic()>self.deadline: raise _Expired

    @staticmethod
    def exact(value):
        v = Decimal.from_float(float(value))
        return v,v

    def add(self, a, b):
        return self.lo.add(a[0],b[0]),self.hi.add(a[1],b[1])

    def sub(self, a, b):
        return self.lo.subtract(a[0],b[1]),self.hi.subtract(a[1],b[0])

    def mul(self, a, b):
        return (min(self.lo.multiply(x,y) for x in a for y in b),
                max(self.hi.multiply(x,y) for x in a for y in b))

    def scalar(self, value, pair):
        # Coefficient conversion is exact; native binary64 is not reinterpreted as decimal text.
        v = Decimal.from_float(float(value))
        if v>=0: return self.lo.multiply(v,pair[0]),self.hi.multiply(v,pair[1])
        return self.lo.multiply(v,pair[1]),self.hi.multiply(v,pair[0])

    def dot(self, coefficients, values):
        lower = upper = _ZERO
        for coefficient, value in zip(coefficients,values):
            lo,hi = self.scalar(coefficient,value)
            lower,upper = self.lo.add(lower,lo),self.hi.add(upper,hi)
        return lower,upper

    def _reduction_bound(self, k):
        """Outward product AND reduction error, no scientific error floor."""
        if k in self._bounds: return self._bounds[k]
        m = Decimal(2*k)
        epsilon = Decimal.from_float(2.**-52)
        tiny = Decimal.from_float(float(np.finfo(np.float64).tiny))
        me = self.hi.multiply(m,epsilon)
        denominator = self.lo.subtract(Decimal(1),me)
        if denominator<=0: raise ValueError('precision: reduction length')
        gamma = self.hi.divide(me,denominator)
        divisor = self.lo.subtract(Decimal(1),gamma)
        if divisor<=0: raise ValueError('precision: error divisor')
        loss = self.hi.multiply(self.hi.multiply(m,tiny),self.hi.add(Decimal(1),gamma))
        self._bounds[k] = gamma,divisor,loss
        return self._bounds[k]

    def _row_vectors(self, vector):
        centers,radii = np.empty(len(vector)),np.empty(len(vector))
        tiny = float(np.finfo(np.float64).tiny)
        for i,(lo,hi) in enumerate(vector):
            if i % 16 == 0: self.check()
            center = float(lo)
            if not np.isfinite(center) or (center!=0. and abs(center)<tiny):
                raise ValueError('precision: unsupported native center')
            dc = Decimal.from_float(center)
            radius = max(self.hi.subtract(dc,lo),self.hi.subtract(hi,dc),_ZERO)
            native_radius = float(radius)
            # A tiny conversion followed by a huge coefficient cannot be
            # hidden in the accumulation's absolute-underflow allowance.
            if radius!=0 and (native_radius<tiny or not np.isfinite(native_radius)):
                raise ValueError('precision: unsupported radius conversion')
            centers[i] = center
            radii[i] = 0. if radius==0 else np.nextafter(native_radius,np.inf)
            if not np.isfinite(radii[i]): raise ValueError('precision: radius overflow')
        return centers,radii

    def _enclosed_row(self, coefficients, centers, radii):
        k = len(coefficients)
        if k==0: return _ZERO,_ZERO
        tiny = float(np.finfo(np.float64).tiny)
        if np.any((np.abs(coefficients)<tiny)&(coefficients!=0.)):
            raise ValueError('precision: unsupported native coefficient')
        # Row-local native products/reductions, never a pre-rounded WG/D/Wj.
        # 2k epsilon and lambda compensation bound every product/addition,
        # arbitrary reduction ordering and absolute underflow loss.
        with np.errstate(over='raise',invalid='raise',under='ignore'):
            products = coefficients*centers
            center = float(np.sum(products,dtype=np.float64))
            a = float(np.sum(np.abs(products),dtype=np.float64))
            radius_products = np.abs(coefficients)*radii
            q = float(np.sum(radius_products,dtype=np.float64))
        if not np.isfinite([center,a,q]).all(): raise ValueError('precision: nonfinite row')
        gamma,divisor,loss = self._reduction_bound(k)
        au = self.hi.divide(self.hi.add(Decimal.from_float(a),loss),divisor)
        qu = self.hi.divide(self.hi.add(Decimal.from_float(q),loss),divisor)
        error = self.hi.add(self.hi.add(self.hi.multiply(gamma,au),loss),qu)
        c = Decimal.from_float(center)
        return self.lo.subtract(c,error),self.hi.add(c,error)

    def matrix(self, matrix, vector):
        self.check()
        if not self._use_native_rows: return self._decimal_matrix(matrix,vector)
        # Fixed narrow stencils are cheaper and tighter in the original exact
        # stream. This chooses arithmetic by operator arity, never by score,
        # gradient size, a changed precision/sign rule or an accepted-step cap.
        if (matrix.shape[1]<=8 or
                (sp.issparse(matrix) and np.max(np.diff(matrix.indptr),initial=0)<=8)):
            return self._decimal_matrix(matrix,vector)
        try:
            centers,radii = self._row_vectors(vector)
        except (ArithmeticError,ValueError,OverflowError):
            return self._decimal_matrix(matrix,vector)
        output = []
        sparse = sp.issparse(matrix)
        for i in range(matrix.shape[0]):
            if i % 16 == 0: self.check()
            if sparse:
                start,end = matrix.indptr[i:i+2]
                indices,coefficients = matrix.indices[start:end],matrix.data[start:end]
            else:
                indices = np.flatnonzero(matrix[i])
                coefficients = matrix[i,indices]
            try:
                output.append(self._enclosed_row(coefficients,centers[indices],radii[indices]))
            except (ArithmeticError,ValueError,OverflowError):
                output.append(self.dot(coefficients,(vector[j] for j in indices)))
        self.check()
        return output

    def _decimal_matrix(self, matrix, vector):
        self.check()
        output = []  # O(rows) interval pairs, never O(rows*cols) Decimal objects.
        sparse = sp.issparse(matrix)
        for i in range(matrix.shape[0]):
            if i % 16 == 0: self.check()
            if sparse:
                start,end = matrix.indptr[i:i+2]
                indices, coefficients = matrix.indices[start:end],matrix.data[start:end]
            else:
                indices = np.flatnonzero(matrix[i])  # one bounded native row index array
                coefficients = matrix[i,indices]
            output.append(self.dot(coefficients,(vector[j] for j in indices)))
        self.check()
        return output

    def change(self, residual, dy):
        value = (_ZERO,_ZERO)
        for i,(r,d) in enumerate(zip(residual,dy)):
            if i % 16 == 0: self.check()
            term = self.add(self.scalar(2.,self.mul(r,d)),self.mul(d,d))
            value = self.add(value,term)
        return value


def _csr(matrix, rows, cols):
    if not sp.issparse(matrix) or matrix.shape != (rows,cols) or matrix.dtype != np.float64:
        raise ValueError('precision: fixed float64 sparse operator shape')
    if matrix.nnz>rows*cols or not np.isfinite(matrix.data).all(): raise ValueError('precision: operator count/finite')
    # CSR conversion preserves literal coefficients, never multiplies/rounds factors.
    result = matrix.tocsr(copy=False)
    if not result.has_canonical_format: raise ValueError('precision: duplicate/unsorted sparse coefficients')
    return result


class _CertifiedDelta:
    """Bounded stream of nested owner operands, not a public prepared-engine API."""
    def __init__(self, problem, lower, upper, deadline):
        self.deadline = deadline
        self.g = problem['simulation'].G
        if type(self.g) is not np.ndarray or self.g.dtype != np.float64 or self.g.ndim != 2:
            raise ValueError('precision: fixed native G')
        n,a = self.g.shape
        if not 1<=n<=2048 or not 1<=a<=4096 or self.g.nbytes>64*1024**2:
            raise ValueError('precision: ordinary matrix caps')
        self.n,self.a = n,a
        for value in (lower,upper,problem['reference_q']):
            if type(value) is not np.ndarray or value.dtype != np.float64 or value.shape!=(a,):
                raise ValueError('precision: exact vector shape/dtype')
            if not np.isfinite(value).all(): raise ValueError('precision: vector finite')
        if not np.isfinite(self.g).all() or not np.isfinite(deadline): raise ValueError('precision: source/deadline finite')
        self.lower,self.upper = lower,upper
        if np.any(lower>=upper): raise ValueError('precision: strict bounds')
        self.w = _csr(problem['misfit'].W,n,n)
        self.dobs = problem['misfit'].data.dobs
        if type(self.dobs) is not np.ndarray or self.dobs.dtype!=np.float64 or self.dobs.shape!=(n,) or not np.isfinite(self.dobs).all():
            raise ValueError('precision: fixed stored dobs')
        self.reference = problem['reference_q']
        self.beta = float(problem['beta_engine'])
        if not np.isfinite(self.beta) or self.beta<=0: raise ValueError('precision: beta')
        self.reg = []
        regularizer = problem['regularization']
        if len(regularizer.multipliers)!=len(regularizer.objfcts) or len(regularizer.objfcts)>7:
            raise ValueError('precision: fixed regularization component cap')
        for alpha,component in zip(regularizer.multipliers,regularizer.objfcts):
            if not np.isfinite(alpha) or alpha<0: raise ValueError('precision: alpha')
            if alpha==0: continue
            derivative = component.f_m_deriv(self.reference)
            rows = derivative.shape[0]
            if not 0<=rows<=2*a: raise ValueError('precision: stencil rows')
            derivative = _csr(derivative,rows,a)
            weights = _csr(component.W,rows,rows)
            if derivative.nnz>8*a or weights.nnz>8*a: raise ValueError('precision: stencil storage')
            self.reg.append((float(alpha),weights,derivative))
        # Conservative live interval-vector allowance, independent of actual values.
        self.interval_workspace_bytes = 4096*(12*a+12*n+sum(8*d.shape[0] for _,_,d in self.reg))
        source_bytes = self.g.nbytes+sum(m.data.nbytes+m.indices.nbytes+m.indptr.nbytes for m in (self.w,*(m for _,w,d in self.reg for m in (w,d))))
        if self.interval_workspace_bytes+8*source_bytes+256*1024**2>2*1024**3:
            raise ValueError('precision: projected workspace outside existing2GiB')

    def evaluate(self,q,qt,gradient,iteration,trial,phi,phit):
        if type(iteration) is not int or not 0<=iteration<=199 or type(trial) is not int or not 0<=trial<=19:
            raise ValueError('precision: actual trial index')
        r = _record(iteration,trial,phi,phit)
        if any(type(x) is not np.ndarray or x.dtype!=np.float64 or x.shape!=(self.a,) for x in (q,qt,gradient)):
            raise ValueError('precision: chord/gradient exact shape')
        if any(not np.isfinite(x).all() for x in (q,qt,gradient)) or r['native_phi_current'] is None or r['native_phi_trial'] is None:
            return _validate_record(r)
        with np.errstate(over='raise',invalid='raise'):
            try: r['displacement_inf_q'] = float(np.max(np.abs(qt-q)))
            except ArithmeticError: return _validate_record(r)
        if not np.any(qt!=q):
            r['cause'] = 'zero_displacement'
            return _validate_record(r)
        if np.any(q<self.lower) or np.any(q>self.upper) or np.any(qt<self.lower) or np.any(qt>self.upper):
            r['cause'] = 'range_unsupported'
            return _validate_record(r)
        if monotonic()>self.deadline:
            r['cause'] = 'wall_cap'
            return _validate_record(r)
        for passes,digits,native_rows in ((1,34,True),(1,34,False),(2,50,False),(3,80,False)):
            arithmetic = _Intervals(digits,self.deadline)
            arithmetic._use_native_rows = native_rows
            try:
                arithmetic.check()
                qv = [arithmetic.exact(v) for v in q]
                dq = [arithmetic.sub(arithmetic.exact(v),x) for v,x in zip(qt,qv)]
                slope = arithmetic.dot(gradient,dq)
                if slope[0]>=0:
                    r.update(passes=passes,precision_digits=digits,slope_interval=tuple(map(str,slope)),
                             decision='certified_reject',cause='non_descent')
                    return _validate_record(r)
                residual = [arithmetic.sub(v,arithmetic.exact(d)) for v,d in zip(arithmetic.matrix(self.g,qv),self.dobs)]
                residual = arithmetic.matrix(self.w,residual)
                dy = arithmetic.matrix(self.w,arithmetic.matrix(self.g,dq))
                change = arithmetic.change(residual,dy)
                reference_delta = [arithmetic.sub(v,arithmetic.exact(ref)) for v,ref in zip(qv,self.reference)]
                for alpha,weights,derivative in self.reg:
                    arithmetic.check()
                    rm = arithmetic.matrix(weights,arithmetic.matrix(derivative,reference_delta))
                    dm = arithmetic.matrix(weights,arithmetic.matrix(derivative,dq))
                    change = arithmetic.add(change,arithmetic.scalar(self.beta,arithmetic.scalar(alpha,arithmetic.change(rm,dm))))
                margin = arithmetic.sub(change,arithmetic.scalar(1e-4,slope))
                arithmetic.check()
                r.update(passes=passes,precision_digits=digits,slope_interval=tuple(map(str,slope)),
                         delta_interval=tuple(map(str,change)),armijo_margin_interval=tuple(map(str,margin)))
                if slope[1]<0 and margin[1]<0:
                    r.update(decision='certified_accept',cause='armijo')
                    return _validate_record(r)
                if margin[0]>0:
                    r.update(decision='certified_reject',cause='armijo')
                    return _validate_record(r)
            except _Expired:
                # Incomplete work never publishes interval objects as a certificate.
                r.update(decision='not_run',cause='wall_cap',passes=0,precision_digits=None,
                         slope_interval=None,delta_interval=None,armijo_margin_interval=None)
                return _validate_record(r)
            except (DecimalException,OverflowError,ValueError):
                r.update(decision='not_run',cause='range_unsupported',passes=0,precision_digits=None,
                         slope_interval=None,delta_interval=None,armijo_margin_interval=None)
                return _validate_record(r)
        r.update(decision='unresolved',cause='precision_limit')
        return _validate_record(r)
