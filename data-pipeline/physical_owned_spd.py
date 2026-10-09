"""Closed physical operands and owned first-order Joseph metric.

Trusted in-process ABI, NOT upload/source/native admission. Numeric kernel owns
no survey/physics/CG. No caller factor/action, jitter, retry or SPD boolean.
"""
from dataclasses import dataclass
from decimal import Decimal
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np
import scipy.sparse as sp

import gravity_l2_metric as kernel
import gravity_l2_precision as intervals


SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
KERNEL_SHA256 = kernel.SOURCE_SHA256
POLICY = 'closed-firstorder-joseph-native-true-residual-terminal-1'
COMPLETE_POLICY = 'closed-firstorder-complete-prior-joseph-native-residual-1'


def digest(value):
    """Bound exact literal native operands; never serialize a sparse object."""
    h = hashlib.sha256()
    def add(v):
        if type(v) is np.ndarray:
            h.update(repr((v.dtype.str, v.shape)).encode())
            h.update(memoryview(np.ascontiguousarray(v)).cast('B'))
        elif type(v) is sp.csr_matrix:
            h.update(repr(v.shape).encode())
            for x in (v.data, v.indices, v.indptr):
                add(x)
        elif type(v) in (tuple, list):
            h.update(str(len(v)).encode())
            for x in v:
                add(x)
        elif type(v) in (str, int, float, bool) or v is None:
            h.update(repr((type(v).__name__, v)).encode())
        else:
            raise TypeError('SPD: closed native digest operands')
    add(value)
    return h.hexdigest()


def _hash(v):
    return type(v) is str and len(v) == 64 and all(c in '0123456789abcdef' for c in v)


def _vector(v, a):
    return type(v) is np.ndarray and v.dtype == np.float64 and v.shape == (a,)


def _matrix(v, rows, cols):
    return (type(v) is np.ndarray and v.dtype == np.float64 and v.shape == (rows, cols)
            and v.flags.c_contiguous)


def _csr(v, rows, cols, maximum):
    # Backing pointer validation BEFORE scans/properties/copy/native indexing.
    if (type(v) is not sp.csr_matrix or v.shape != (rows, cols)
        or any(type(x) is not np.ndarray or x.ndim != 1 or not x.flags.c_contiguous
               for x in (v.data, v.indices, v.indptr))
        or v.data.dtype != np.float64 or v.indices.dtype != np.int32 or v.indptr.dtype != np.int32
        or len(v.data) != len(v.indices) or len(v.data) > maximum or len(v.indptr) != rows+1):
        raise ValueError('SPD: exact bounded float64/int32 CSR backing')
    if (v.indptr[0] != 0 or v.indptr[-1] != len(v.data) or np.any(v.indptr < 0)
        or np.any(v.indptr > len(v.data)) or np.any(np.diff(v.indptr) < 0)
        or np.any(v.indices < 0) or np.any(v.indices >= cols) or not np.isfinite(v.data).all()):
        raise ValueError('SPD: malformed CSR backing')
    for i in range(rows):
        indices = v.indices[v.indptr[i]:v.indptr[i+1]]
        if np.any(np.diff(indices) <= 0):
            raise ValueError('SPD: canonical CSR required')


@dataclass(frozen=True)
class OperandBinding:
    objective_sha256: str
    source_inventory_sha256: str
    allocation_plan_sha256: str
    model_sha256: str


@dataclass(frozen=True)
class MetricOperands:
    binding: OperandBinding
    source_components: int
    fit_components: int
    parameters: int
    covariance: bool
    regularizer: sp.csr_matrix
    whitened_jacobian: np.ndarray
    likelihood_scale: float = 1.


def binding_for(identity, q):
    if not _vector(q, identity['parameter_count']):
        raise ValueError('SPD: actual model metadata')
    return OperandBinding(identity['objective_sha256'], identity['source_inventory_sha256'],
                          identity['allocation_plan_sha256'], digest(q))


def validate_operands(operands, identity, q, limit):
    if type(operands) is not MetricOperands or type(operands.binding) is not OperandBinding:
        raise TypeError('SPD: exact closed operand DTO; no metric callback')
    if (any(type(v) is not int for v in (operands.source_components, operands.fit_components, operands.parameters))
        or type(operands.covariance) is not bool
        or operands.parameters != identity['parameter_count']
        or operands.fit_components != identity['observation_rows']*identity['observation_components']
        or type(operands.likelihood_scale) is not float or operands.likelihood_scale not in (.5, 1.)
        or type(limit) is not int or not 0 < limit <= 2*1024**3):
        raise ValueError('SPD: actual source/fit COMPONENT counts and original limit')
    allocation = kernel.allocation(operands.source_components, operands.fit_components,
                                   operands.parameters, operands.covariance)
    if allocation['maximum'] > limit:
        raise ValueError('SPD: original adapter resource dictionary exceeded')
    a, m = operands.parameters, operands.fit_components
    if not _matrix(operands.whitened_jacobian, m, a):
        raise ValueError('SPD: actual whitened Jacobian metadata')
    _csr(operands.regularizer, a, a, 7*a)
    # Hash/value scans occur ONLY after all dimension/storage/resource guards.
    if operands.binding != binding_for(identity, q) or any(not _hash(v) for v in (
        operands.binding.objective_sha256, operands.binding.source_inventory_sha256,
        operands.binding.allocation_plan_sha256, operands.binding.model_sha256)):
        raise ValueError('SPD: original objective/source/allocation/actual-model binding')
    kernel._stencil(operands.regularizer)
    if not np.isfinite(operands.whitened_jacobian).all():
        raise ValueError('SPD: finite Jacobian')
    return allocation


class OwnedMetric:
    """Public construction/lifetime; retained numeric factors only, no source DTO."""
    def __init__(self, operands, identity, q, free, deadline, limit):
        self._numeric = None
        self.actions = 0
        self.action_seconds = 0.
        self.allocation = validate_operands(operands, identity, q, limit)
        a = operands.parameters
        if type(self) is _COMPLETE_OWNER:
            additional = kernel.complete_prior_workspace(a)
            self.allocation = dict(self.allocation,
                complete_prior_workspace_bytes=additional,
                maximum=self.allocation['maximum']+additional)
            if self.allocation['maximum'] > limit:
                raise ValueError('SPD complete prior: unchanged original live-phase limit')
            kernel._time(deadline)
        elif type(self) is not _IC0_OWNER:
            raise TypeError('SPD: exact owned class, no numeric factor callback')
        if (type(free) is not np.ndarray or free.dtype != np.int64 or free.ndim != 1
            or not 1 <= len(free) <= a or np.any(free < 0) or np.any(free >= a)
            or np.any(np.diff(free) <= 0)):
            raise ValueError('SPD: actual increasing principal free face')
        self.operand_sha256 = digest((operands.binding.objective_sha256, operands.binding.model_sha256,
            operands.regularizer, operands.whitened_jacobian, operands.likelihood_scale, free))
        self.face_sha256 = digest(free)
        # K is ALREADY whitened by original physical adapter; original literal
        # likelihood normalization only. No noise inference or dense K rescale.
        if type(self) is _IC0_OWNER:
            numeric_type = kernel.JosephMetric
        elif type(self) is _COMPLETE_OWNER:
            numeric_type = kernel.CompleteFirstOrderJosephMetric
        else:
            raise TypeError('SPD: exact owned class, no numeric factor callback')
        self._numeric = numeric_type(operands.regularizer, operands.whitened_jacobian,
            sp.diags(np.full(operands.fit_components, np.sqrt(operands.likelihood_scale)), format='csr'), free, deadline,
            profile=(operands.source_components, operands.fit_components, a, operands.covariance))
        self.setup_seconds = self._numeric.setup_seconds

    @property
    def live_payload_bytes(self):
        return 0 if self._numeric is None else self._numeric.live_payload_bytes

    def apply(self, v):
        if self._numeric is None:
            raise ValueError('SPD: disposed public face')
        started = monotonic()
        self.actions += 1
        try:
            return self._numeric.apply(v)
        finally:
            self.action_seconds += monotonic()-started

    def close(self):
        if self._numeric is not None:
            self._numeric.close()
        self._numeric = None


class OwnedCompletePriorMetric(OwnedMetric):
    """Separate complete original first-order prior; no caller SPD factor."""


_IC0_OWNER = OwnedMetric
_COMPLETE_OWNER = OwnedCompletePriorMetric


@dataclass(frozen=True)
class QuadraticTerm:
    alpha: float
    weights: sp.csr_matrix
    derivative: sp.csr_matrix


@dataclass(frozen=True)
class QuadraticOperands:
    binding: OperandBinding
    g: np.ndarray
    w: sp.csr_matrix
    dobs: np.ndarray
    reference: np.ndarray
    likelihood_scale: float
    beta: float
    terms: tuple
    physical_prediction_rows: np.ndarray


@dataclass(frozen=True)
class TerminalPolicy:
    required_kkt_normalized: float
    model_error_limit: float | None = None
    objective_gap_limit: float | None = None
    physical_prediction_error_limit: float | None = None


def validate_terminal(policy):
    if (type(policy) is not TerminalPolicy or type(policy.required_kkt_normalized) is not float
        or not 0. < policy.required_kkt_normalized <= 1e-5):
        raise ValueError('SPD terminal: stronger declared ORIGINAL KKT required')
    for v in (policy.model_error_limit, policy.objective_gap_limit, policy.physical_prediction_error_limit):
        if v is not None and (type(v) is not float or not np.isfinite(v) or v <= 0.):
            raise ValueError('SPD terminal: positive original absolute error limits')
    return any(v is not None for v in (policy.model_error_limit, policy.objective_gap_limit,
                                       policy.physical_prediction_error_limit))


def _quadratic_metadata(o, identity, q, source_components):
    a, m = identity['parameter_count'], identity['observation_rows']*identity['observation_components']
    if type(o) is not QuadraticOperands or type(o.binding) is not OperandBinding:
        raise TypeError('SPD terminal: closed ORIGINAL quadratic DTO required')
    if (not _matrix(o.g, m, a) or not _vector(o.dobs, m) or not _vector(o.reference, a)
        or type(o.physical_prediction_rows) is not np.ndarray or o.physical_prediction_rows.dtype != np.float64
        or o.physical_prediction_rows.ndim != 2 or o.physical_prediction_rows.shape[1] != a
        or not 1 <= o.physical_prediction_rows.shape[0] <= source_components
        or not o.physical_prediction_rows.flags.c_contiguous
        or type(o.terms) is not tuple or not 1 <= len(o.terms) <= 7
        or any(type(v) is not float or not np.isfinite(v) or v <= 0. for v in (o.likelihood_scale, o.beta))):
        raise ValueError('SPD terminal: bounded ORIGINAL factor metadata')
    _csr(o.w, m, m, m*m)
    for term in o.terms:
        if type(term) is not QuadraticTerm or type(term.alpha) is not float or not np.isfinite(term.alpha) or term.alpha <= 0.:
            raise ValueError('SPD terminal: original positive term')
        if type(term.derivative) is not sp.csr_matrix or not 1 <= term.derivative.shape[0] <= 2*a:
            raise ValueError('SPD terminal: original bounded derivative')
        r = term.derivative.shape[0]
        _csr(term.derivative, r, a, 8*a)
        _csr(term.weights, r, r, 8*a)
    small = o.terms[0]
    if (small.derivative.shape != (a, a) or small.weights.shape != (a, a)
        or not np.array_equal(small.derivative.indptr, np.arange(a+1, dtype=np.int32))
        or not np.array_equal(small.derivative.indices, np.arange(a, dtype=np.int32))
        or not np.array_equal(small.derivative.data, np.ones(a))
        or not np.array_equal(small.weights.indptr, small.derivative.indptr)
        or not np.array_equal(small.weights.indices, small.derivative.indices)
        or np.any(small.weights.data <= 0.)):
        raise ValueError('SPD terminal: ORIGINAL positive diagonal smallness, not supplied mu')
    if o.binding != binding_for(identity, q):
        raise ValueError('SPD terminal: actual source/model binding')
    if not all(np.isfinite(v).all() for v in (o.g, o.dobs, o.reference, o.physical_prediction_rows)):
        raise ValueError('SPD terminal: finite ORIGINAL values')
    return a, m


def quadratic_bounds(o, identity, q, lower, upper, deadline, source_components):
    """Outward ORIGINAL nested gradient/mu; no GN global bound or scalar oracle."""
    a, _ = _quadratic_metadata(o, identity, q, source_components)
    if any(not _vector(v, a) for v in (q, lower, upper)) or np.any(q < lower) or np.any(q > upper):
        raise ValueError('SPD terminal: literal feasible physical model')
    arithmetic = intervals._Intervals(34, deadline)
    arithmetic.check()
    qv = [arithmetic.exact(v) for v in q]
    delta = [arithmetic.sub(v, arithmetic.exact(ref)) for v, ref in zip(qv, o.reference)]
    residual = [arithmetic.sub(v, arithmetic.exact(d)) for v, d in zip(arithmetic.matrix(o.g, qv), o.dobs)]
    wr = arithmetic.matrix(o.w, residual)
    wtr = arithmetic.matrix(o.w.T.tocsr(), wr)
    gradient = [arithmetic.scalar(2.*o.likelihood_scale, v) for v in arithmetic.matrix(o.g.T, wtr)]
    # Never pre-round beta*alpha or W*D for the physical acceptance bounds.
    for term in o.terms:
        r = arithmetic.matrix(term.weights, arithmetic.matrix(term.derivative, delta))
        x = arithmetic.matrix(term.derivative.T.tocsr(), arithmetic.matrix(term.weights.T.tocsr(), r))
        for i, v in enumerate(x):
            gradient[i] = arithmetic.add(gradient[i], arithmetic.scalar(o.beta,
                arithmetic.scalar(term.alpha, arithmetic.scalar(2., v))))
    small = o.terms[0]
    mu = min(arithmetic.scalar(o.beta, arithmetic.scalar(small.alpha,
        arithmetic.scalar(2., arithmetic.mul(arithmetic.exact(w), arithmetic.exact(w)))))[0]
        for w in small.weights.data)
    if mu <= 0:
        raise ValueError('SPD terminal: positive ORIGINAL physical curvature unavailable')
    zero = Decimal(0)
    squared = zero
    inf = zero
    for i, (lo, hi) in enumerate(gradient):
        if q[i] == lower[i]:
            lo, hi = min(lo, zero), min(hi, zero)
        elif q[i] == upper[i]:
            lo, hi = max(lo, zero), max(hi, zero)
        absolute = max(lo.copy_abs(), hi.copy_abs())
        inf = max(inf, absolute)
        squared = arithmetic.hi.add(squared, arithmetic.hi.multiply(absolute, absolute))
    # Decimal sqrt uses nearest rounding even in directed contexts; explicitly
    # widen one ulp outward rather than assuming the context rounding suffices.
    norm = arithmetic.hi.next_plus(arithmetic.hi.sqrt(squared)) if squared else zero
    error = arithmetic.hi.divide(norm, mu)
    gap = arithmetic.hi.divide(squared, arithmetic.lo.multiply(Decimal(2), mu))
    maximum = zero
    for i, row in enumerate(o.physical_prediction_rows):
        if i % 16 == 0:
            arithmetic.check()
        square = arithmetic.dot(row, [arithmetic.exact(v) for v in row])[1]
        row_norm = arithmetic.hi.next_plus(arithmetic.hi.sqrt(max(zero, square))) if square else zero
        maximum = max(maximum, row_norm)
    prediction = arithmetic.hi.multiply(maximum, error)
    arithmetic.check()
    return dict(domain='original_nested_strongly_convex_quadratic', precision_digits=34,
        physical_prediction_rows=o.physical_prediction_rows.shape[0],
        mu_lower=str(mu), feasible_gradient_inf_upper=str(inf), residual_norm_upper=str(norm),
        model_error_upper=str(error), objective_gap_upper=str(gap), physical_prediction_error_upper=str(prediction))


def terminal_check(policy, q, gradient, lower, upper, initial_norm, *, identity,
                   deadline, quadratic=None, source_components=None):
    bounds_required = validate_terminal(policy)
    a = identity['parameter_count']
    if any(not _vector(v, a) for v in (q, gradient, lower, upper)) or not np.isfinite(gradient).all():
        raise ValueError('SPD terminal: ORIGINAL native gradient metadata')
    residual = gradient.copy()
    residual[q == lower] = np.minimum(residual[q == lower], 0.)
    residual[q == upper] = np.maximum(residual[q == upper], 0.)
    kkt = float(np.linalg.norm(residual, np.inf)/initial_norm)
    record = dict(normalized_exact_bound_kkt=kkt, required_normalized_kkt=policy.required_kkt_normalized,
                  bounds=None, passed=bool(kkt <= policy.required_kkt_normalized))
    if bounds_required:
        if identity['mode'] != 'fixed_linear_quadratic':
            raise ValueError('SPD terminal: nonlinear GN is not global physical curvature')
        record['bounds'] = quadratic_bounds(quadratic, identity, q, lower, upper, deadline, source_components)
        # Use enclosed physical residual ALSO for KKT when claiming bounds.
        outward = intervals._Intervals(34, deadline)
        upper_kkt = outward.hi.divide(Decimal(record['bounds']['feasible_gradient_inf_upper']), Decimal.from_float(initial_norm))
        record['passed'] = record['passed'] and upper_kkt <= Decimal.from_float(policy.required_kkt_normalized)
        for name, limit in (('model_error_upper', policy.model_error_limit),
            ('objective_gap_upper', policy.objective_gap_limit),
            ('physical_prediction_error_upper', policy.physical_prediction_error_limit)):
            if limit is not None:
                record['passed'] = record['passed'] and Decimal(record['bounds'][name]) <= Decimal.from_float(limit)
    return record


def certify_quadratic_chord(operands, identity, q, qt, native_gradient, native_phi,
        native_phi_trial, iteration, trial, deadline, *, source_components,
        covariance, resource_limit_bytes):
    """PUBLIC strict actual-chord proof from closed ORIGINAL nested operands.

Original literal c=.5or1, no prepared rounded WG/WD/delta, supplied decision,
private adapter helper or optimizer. Numerical source/native admission separate.
"""
    a = identity['parameter_count']
    m = identity['observation_rows']*identity['observation_components']
    allocation = kernel.allocation(source_components, m, a, covariance)
    if (type(resource_limit_bytes) is not int or not 0 < resource_limit_bytes <= 2*1024**3
        or allocation['maximum'] > resource_limit_bytes):
        raise ValueError('SPD certificate: ORIGINAL complete resource dictionary')
    _quadratic_metadata(operands, identity, q, source_components)
    if identity['mode'] != 'fixed_linear_quadratic' or operands.likelihood_scale not in (.5, 1.):
        raise ValueError('SPD certificate: ORIGINAL linear normalization/mode')
    if (type(iteration) is not int or not 0 <= iteration <= 199 or type(trial) is not int or not 0 <= trial <= 19
        or type(deadline) is not float or not np.isfinite(deadline)
        or not _vector(qt, a) or not _vector(native_gradient, a)
        or type(native_phi) is not float or type(native_phi_trial) is not float):
        raise ValueError('SPD certificate: exact actual native chord/count/clock metadata')
    record = intervals._record(iteration, trial, native_phi, native_phi_trial)
    if (not np.isfinite(q).all() or not np.isfinite(qt).all() or not np.isfinite(native_gradient).all()
        or record['native_phi_current'] is None or record['native_phi_trial'] is None):
        return intervals._validate_record(record)
    # Bounds belong to the actual optimizer; source-bound q was already checked
    # by its evaluate/projection. This public arithmetic API proves the recorded
    # literal chord, not an independent caller's unprovided box feasibility.
    try:
        record['displacement_inf_q'] = float(np.max(np.abs(qt-q)))
    except ArithmeticError:
        return intervals._validate_record(record)
    if not np.any(qt != q):
        record['cause'] = 'zero_displacement'
        return intervals._validate_record(record)
    if monotonic() > deadline:
        record['cause'] = 'wall_cap'
        return intervals._validate_record(record)
    for passes, digits, native_rows in ((1, 34, True), (1, 34, False), (2, 50, False), (3, 80, False)):
        arithmetic = intervals._Intervals(digits, deadline)
        arithmetic._use_native_rows = native_rows
        try:
            arithmetic.check()
            qv = [arithmetic.exact(v) for v in q]
            dq = [arithmetic.sub(arithmetic.exact(v), before) for v, before in zip(qt, qv)]
            slope = arithmetic.dot(native_gradient, dq)
            if slope[0] >= 0:
                record.update(passes=passes, precision_digits=digits, slope_interval=tuple(map(str, slope)),
                              decision='certified_reject', cause='non_descent')
                return intervals._validate_record(record)
            residual = [arithmetic.sub(value, arithmetic.exact(d))
                        for value, d in zip(arithmetic.matrix(operands.g, qv), operands.dobs)]
            residual = arithmetic.matrix(operands.w, residual)
            dy = arithmetic.matrix(operands.w, arithmetic.matrix(operands.g, dq))
            change = arithmetic.scalar(operands.likelihood_scale, arithmetic.change(residual, dy))
            delta = [arithmetic.sub(value, arithmetic.exact(ref)) for value, ref in zip(qv, operands.reference)]
            for term in operands.terms:
                arithmetic.check()
                r = arithmetic.matrix(term.weights, arithmetic.matrix(term.derivative, delta))
                dr = arithmetic.matrix(term.weights, arithmetic.matrix(term.derivative, dq))
                change = arithmetic.add(change, arithmetic.scalar(operands.beta,
                    arithmetic.scalar(term.alpha, arithmetic.change(r, dr))))
            margin = arithmetic.sub(change, arithmetic.scalar(1e-4, slope))
            record.update(passes=passes, precision_digits=digits, slope_interval=tuple(map(str, slope)),
                delta_interval=tuple(map(str, change)), armijo_margin_interval=tuple(map(str, margin)))
            if slope[1] < 0 and margin[1] < 0:
                record.update(decision='certified_accept', cause='armijo')
                return intervals._validate_record(record)
            if margin[0] > 0:
                record.update(decision='certified_reject', cause='armijo')
                return intervals._validate_record(record)
        except intervals._Expired:
            record = intervals._record(iteration, trial, native_phi, native_phi_trial)
            record['cause'] = 'wall_cap'
            return intervals._validate_record(record)
        except (ArithmeticError, ValueError):
            record = intervals._record(iteration, trial, native_phi, native_phi_trial)
            record['cause'] = 'range_unsupported'
            return intervals._validate_record(record)
    record.update(decision='unresolved', cause='precision_limit')
    return intervals._validate_record(record)
