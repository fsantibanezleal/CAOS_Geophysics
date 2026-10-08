"""Source-original linear map/SD-division/stored-Cholesky arithmetic.

Closed trusted in-process operands, not upload, native, source or SPD admission.
No rounded reciprocal/projection product, caller inverse, optimizer or fallback.
"""
from dataclasses import dataclass
from decimal import Decimal
import hashlib
from pathlib import Path
from sys import getsizeof
from time import monotonic

import numpy as np
import scipy.linalg as la
import scipy.sparse as sp

import physical_owned_spd as owned
import physical_optimizer as native
import gravity_l2_precision as intervals


SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
RESERVE_BYTES = 8*1024**2
ENDPOINT_PAIR_BYTES = 2048
ALLOCATION_EPOCH = 'original-source-disjoint-native-factory-certificate-1'


def _owned_source_allocation(n, m, a, covariance, payload, arithmetic):
    """Internal original-source phases, never a caller disjointness grant.

    All native/setup/action reserves are retained. The generic certificate's
    interval workspace is not live in this source-owned original certificate.
    Its independently bounded original arithmetic replaces that PHASE, not H,
    the numeric metric, native reserve, limit or original noise nesting.
    """
    native_phases = owned.kernel.allocation(n, m, a, covariance)
    if (type(payload) is not int or not 0 < payload <= RESERVE_BYTES
            or type(arithmetic) is not dict or set(arithmetic) != {
                'operand_and_sparse_copy_bytes', 'endpoint_bytes',
                'native_row_scratch_bytes', 'metadata_bytes'}
            or any(type(v) is not int or v <= 0 for v in arithmetic.values())
            or arithmetic['operand_and_sparse_copy_bytes'] != 2*payload):
        raise ValueError('original quadratic: owned complete source phase storage')
    source_bytes = sum(arithmetic.values())
    factory = native_phases['setup']+2*payload+arithmetic['metadata_bytes']
    certificate = native_phases['action']+max(RESERVE_BYTES, source_bytes)
    return dict(epoch=ALLOCATION_EPOCH, original_native_phases=native_phases,
        factory_bytes=factory, original_certificate_bytes=certificate,
        original_arithmetic_bytes=source_bytes,
        maximum=max(factory, certificate))


@dataclass(frozen=True)
class OriginalWhitening:
    kind: str
    values: np.ndarray
    covariance: np.ndarray | None = None


@dataclass(frozen=True)
class OriginalQuadraticOperands:
    binding: owned.OperandBinding
    source_components: int
    sensitivity: np.ndarray
    projection: np.ndarray | None
    whitening: OriginalWhitening
    observations: np.ndarray
    reference: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    likelihood_scale: float
    beta: float
    terms: tuple
    prediction_sensitivity: np.ndarray
    prediction_projection: np.ndarray | None


def _map_metadata(matrix, projection, rows, a, source):
    if projection is None:
        raw = rows
    elif (owned._vector(projection, 3) and rows*3 <= source):
        raw = rows*3
    else:
        raise ValueError('original quadratic: closed identity or grouped3 map')
    if not owned._matrix(matrix, raw, a):
        raise ValueError('original quadratic: original contiguous sensitivity')
    return raw


def _identity_metadata(identity):
    # Do not index/multiply untrusted counts before literal metadata checks.
    if type(identity) is not dict or set(identity) != native._IDENTITY_KEYS:
        raise ValueError('original quadratic: exact13 original identity')
    if any(not native._digest(identity[k]) for k in (
        'objective_sha256', 'source_inventory_sha256', 'allocation_plan_sha256')):
        raise ValueError('original quadratic: literal source digests')
    if any(type(identity[k]) is not str or not 1 <= len(identity[k]) <= 96
        for k in ('runtime_epoch', 'q_unit', 'physical_unit')):
        raise ValueError('original quadratic: original unit/epoch strings')
    if (identity['mode'] != 'fixed_linear_quadratic'
        or type(identity['parameter_count']) is not int or not 1 <= identity['parameter_count'] <= 4096
        or type(identity['observation_rows']) is not int or not 1 <= identity['observation_rows'] <= 2048
        or type(identity['observation_components']) is not int or identity['observation_components'] not in (1, 3)
        or type(identity['stage_index']) is not int or not 0 <= identity['stage_index'] <= 20
        or any(not native._finite(identity[k], positive=True) for k in ('physical_scale', 'beta_engine'))):
        raise ValueError('original quadratic: literal original counts/scalars/mode')
    return identity['parameter_count'], identity['observation_rows']*identity['observation_components']


def _vector(v, count):
    return owned._vector(v, count) and v.flags.c_contiguous


def _backing_bytes(value):
    while value.base is not None:
        if type(value.base) is not np.ndarray:
            raise ValueError('original quadratic: closed ndarray backing only')
        value = value.base
    if not value.flags.c_contiguous:
        raise ValueError('original quadratic: contiguous ultimate source backing')
    return value.nbytes


def _csr_metadata(v, rows, cols, maximum):
    if (type(v) is not sp.csr_matrix or v.shape != (rows, cols)
        or any(type(x) is not np.ndarray or x.ndim != 1 or not x.flags.c_contiguous
            for x in (v.data, v.indices, v.indptr))
        or v.data.dtype != np.float64 or v.indices.dtype != np.int32 or v.indptr.dtype != np.int32
        or len(v.data) != len(v.indices) or len(v.data) > maximum or len(v.indptr) != rows+1):
        raise ValueError('original quadratic: bounded original CSR metadata')


def validate(o, identity, q, *, deadline, resource_limit_bytes, admitted_bytes):
    """Dimensions/storage/accounting BEFORE scans, factor checks or arithmetic."""
    a, m = _identity_metadata(identity)
    if (type(o) is not OriginalQuadraticOperands or type(o.binding) is not owned.OperandBinding
        or type(o.whitening) is not OriginalWhitening
        or identity['mode'] != 'fixed_linear_quadratic'
        or type(o.source_components) is not int or not m <= o.source_components <= 2048
        or type(a) is not int or not 1 <= a <= 4096
        or type(deadline) is not float or not np.isfinite(deadline)
        or type(resource_limit_bytes) is not int or not 0 < resource_limit_bytes <= 2*1024**3
        or type(admitted_bytes) is not int or not 0 < admitted_bytes <= resource_limit_bytes):
        raise ValueError('original quadratic: closed source/count/mode/budget')
    _map_metadata(o.sensitivity, o.projection, m, a, o.source_components)
    if o.projection is not None and identity['observation_components'] != 1:
        raise ValueError('original quadratic: grouped3 projection produces scalar observations')
    if (type(o.prediction_sensitivity) is not np.ndarray or o.prediction_sensitivity.ndim != 2):
        raise ValueError('original quadratic: original prediction map')
    raw_rows = o.prediction_sensitivity.shape[0]
    prediction_rows = raw_rows if o.prediction_projection is None else raw_rows//3
    if not 1 <= prediction_rows <= o.source_components:
        raise ValueError('original quadratic: bounded original prediction rows')
    _map_metadata(o.prediction_sensitivity, o.prediction_projection,
        prediction_rows, a, o.source_components)
    if (any(not _vector(v, a) for v in (q, o.reference, o.lower, o.upper))
        or not _vector(o.observations, m)
        or type(o.likelihood_scale) is not float or o.likelihood_scale not in (.5, 1.)
        or type(o.beta) is not float or not np.isfinite(o.beta) or o.beta <= 0.
        or o.beta != identity['beta_engine']
        or type(o.terms) is not tuple or not 1 <= len(o.terms) <= 7):
        raise ValueError('original quadratic: literal original physical factors')
    noise = o.whitening
    if type(noise.kind) is not str or noise.kind not in (
        'diagonal_sd', 'stored_lower_cholesky', 'stored_symmetric_precision_root'):
        raise ValueError('original quadratic: no inferred whitening')
    covariance = noise.kind != 'diagonal_sd'
    if covariance:
        if m > 512 or not owned._matrix(noise.values, m, m) or not owned._matrix(noise.covariance, m, m):
            raise ValueError('original quadratic: original storedL/covariance cap')
    elif not _vector(noise.values, m) or noise.covariance is not None:
        raise ValueError('original quadratic: original SD vector')
    for term in o.terms:
        if (type(term) is not owned.QuadraticTerm or type(term.alpha) is not float
            or not np.isfinite(term.alpha) or term.alpha <= 0.
            or type(term.derivative) is not sp.csr_matrix
            or not 1 <= term.derivative.shape[0] <= 2*a):
            raise ValueError('original quadratic: original fixed positive term')
        rows = term.derivative.shape[0]
        _csr_metadata(term.derivative, rows, a, 8*a)
        _csr_metadata(term.weights, rows, rows, 8*a)
    allocation = owned.kernel.allocation(o.source_components, m, a, covariance)
    payload = sum(_backing_bytes(v) for v in (o.sensitivity, o.prediction_sensitivity,
        o.observations, o.reference, o.lower, o.upper, noise.values))
    payload += 0 if noise.covariance is None else _backing_bytes(noise.covariance)
    payload += sum(sum(_backing_bytes(v) for matrix in (t.weights, t.derivative)
        for v in (matrix.data, matrix.indices, matrix.indptr)) for t in o.terms)
    payload += 0 if o.projection is None else _backing_bytes(o.projection)
    payload += 0 if o.prediction_projection is None else _backing_bytes(o.prediction_projection)
    longest = Decimal.from_float(float.fromhex('0x0.0000000000001p-1022'))
    if 2*getsizeof(longest)+getsizeof((None, None))+8+64 > ENDPOINT_PAIR_BYTES:
        raise ValueError('original quadratic: loaded endpoint storage unsupported')
    maximum_term_rows = max(t.derivative.shape[0] for t in o.terms)
    phase = dict(operand_and_sparse_copy_bytes=2*payload,
        endpoint_bytes=ENDPOINT_PAIR_BYTES*(6*a+6*o.source_components+4*maximum_term_rows),
        native_row_scratch_bytes=8*16*(a+o.source_components+maximum_term_rows), metadata_bytes=32768)
    arithmetic_phase_bytes = sum(phase.values())
    owned_phases = _owned_source_allocation(o.source_components, m, a,
        covariance, payload, phase)
    maximum = owned_phases['maximum']
    if payload > RESERVE_BYTES or maximum > admitted_bytes:
        raise ValueError('original quadratic: source-bound original phases plus operand reserve')
    if monotonic() > deadline:
        raise intervals._Expired
    if o.binding != owned.binding_for(identity, q):
        raise ValueError('original quadratic: exact original source/model binding')
    for term in o.terms:
        rows = term.derivative.shape[0]
        owned._csr(term.derivative, rows, a, 8*a)
        owned._csr(term.weights, rows, rows, 8*a)
    if any(not np.isfinite(v).all() for v in (q, o.sensitivity, o.prediction_sensitivity,
        o.observations, o.reference, o.lower, o.upper, noise.values)):
        raise ValueError('original quadratic: finite source-original operands')
    if np.any(o.lower >= o.upper) or np.any(q < o.lower) or np.any(q > o.upper):
        raise ValueError('original quadratic: original feasible box')
    for projection in (o.projection, o.prediction_projection):
        if projection is not None and (not np.isfinite(projection).all()
            or abs(float(np.linalg.norm(projection))-1.) > 1e-12):
            raise ValueError('original quadratic: original unit physical projection')
    small = o.terms[0]
    if (small.derivative.shape != (a, a) or small.weights.shape != (a, a)
        or not np.array_equal(small.derivative.indptr, np.arange(a+1, dtype=np.int32))
        or not np.array_equal(small.derivative.indices, np.arange(a, dtype=np.int32))
        or not np.array_equal(small.derivative.data, np.ones(a))
        or not np.array_equal(small.weights.indptr, small.derivative.indptr)
        or not np.array_equal(small.weights.indices, small.derivative.indices)
        or np.any(small.weights.data <= 0.)):
        raise ValueError('original quadratic: unchanged positive diagonal smallness')
    if covariance:
        if (not np.isfinite(noise.covariance).all()
            or not np.array_equal(noise.covariance, noise.covariance.T)):
            raise ValueError('original quadratic: exact original covariance storage')
        owned.kernel._workspace_closure()
        condition = float(np.linalg.cond(noise.covariance, 2))
        if not np.isfinite(condition) or condition > 1e8:
            raise ValueError('original quadratic: original covariance condition2<=1e8')
        if noise.kind == 'stored_lower_cholesky':
            if (np.any(np.triu(noise.values, 1) != 0.) or np.any(np.diag(noise.values) <= 0.)
                or not np.array_equal(np.linalg.cholesky(noise.covariance), noise.values)):
                raise ValueError('original quadratic: stored native original Cholesky mismatch')
        else:
            # The original gravity producer stores this symmetric root, NOT L.
            # Its rounded stored W is the unchanged native source authority.
            # Reproduce the fixed native recipe exactly; no arbitrary caller W,
            # inferred noise, covariance symmetrization, jitter or tolerance.
            la.cholesky(noise.covariance, lower=True, check_finite=True)
            eigenvalues, vectors = la.eigh(noise.covariance, driver='evd', check_finite=True)
            if np.any(eigenvalues <= 0.) or eigenvalues[-1]/eigenvalues[0] > 1e8:
                raise ValueError('original quadratic: original gravity positive eigenvalues')
            with np.errstate(over='raise', invalid='raise', divide='raise'):
                expected = (vectors*(1./np.sqrt(eigenvalues)))@vectors.T
                expected = (expected+expected.T)*.5
            if not np.array_equal(expected, noise.values):
                raise ValueError('original quadratic: stored native symmetric precision root mismatch')
    elif np.any(noise.values <= 0.):
        raise ValueError('original quadratic: strictly positive original SD')
    if monotonic() > deadline:
        raise intervals._Expired
    return dict(original=allocation, operand_payload_bytes=payload,
        reserve_bytes=RESERVE_BYTES, arithmetic_phase=phase,
        arithmetic_phase_bytes=arithmetic_phase_bytes,
        owned_source_phases=owned_phases, maximum=maximum)


def _divide(ar, pair, positive):
    value = Decimal.from_float(float(positive))
    if value <= 0:
        raise ValueError('original quadratic: positive stored divisor')
    return ar.lo.divide(pair[0], value), ar.hi.divide(pair[1], value)


def _whiten(ar, noise, vector, transpose=False):
    if noise.kind == 'diagonal_sd':
        return [_divide(ar, v, s) for v, s in zip(vector, noise.values)]
    if noise.kind == 'stored_symmetric_precision_root':
        return ar.matrix(noise.values.T if transpose else noise.values, vector)
    lower = noise.values
    result = [None]*len(vector)
    order = range(len(vector)-1, -1, -1) if transpose else range(len(vector))
    for i in order:
        ar.check()
        if transpose:
            v = ar.sub(vector[i], ar.dot(lower[i+1:, i], result[i+1:]))
        else:
            v = ar.sub(vector[i], ar.dot(lower[i, :i], result[:i]))
        result[i] = _divide(ar, v, lower[i, i])
    return result


def _map(ar, sensitivity, projection, vector):
    values = ar.matrix(sensitivity, vector)
    if projection is None:
        return values
    return [ar.dot(projection, values[i:i+3]) for i in range(0, len(values), 3)]


def _adjoint(ar, sensitivity, projection, vector):
    if projection is not None:
        vector = [ar.scalar(p, v) for v in vector for p in projection]
    return ar.matrix(sensitivity.T, vector)


def _gradient(ar, o, q):
    qv = [ar.exact(v) for v in q]
    residual = [ar.sub(v, ar.exact(d)) for v, d in zip(_map(ar, o.sensitivity, o.projection, qv), o.observations)]
    twice = _whiten(ar, o.whitening, _whiten(ar, o.whitening, residual), True)
    result = [ar.scalar(2.*o.likelihood_scale, v) for v in _adjoint(ar, o.sensitivity, o.projection, twice)]
    delta = [ar.sub(v, ar.exact(ref)) for v, ref in zip(qv, o.reference)]
    for term in o.terms:
        v = ar.matrix(term.weights, ar.matrix(term.derivative, delta))
        v = ar.matrix(term.derivative.T.tocsr(), ar.matrix(term.weights.T.tocsr(), v))
        result = [ar.add(old, ar.scalar(o.beta, ar.scalar(term.alpha, ar.scalar(2., x))))
            for old, x in zip(result, v)]
    return result


def source_gradient(o, identity, q, *, deadline, resource_limit_bytes, admitted_bytes, digits=34):
    validate(o, identity, q, deadline=deadline, resource_limit_bytes=resource_limit_bytes, admitted_bytes=admitted_bytes)
    if type(digits) is not int or digits not in (34, 50, 80):
        raise ValueError('original quadratic: fixed original precision ladder')
    ar = intervals._Intervals(digits, deadline)
    ar._use_native_rows = False
    return _gradient(ar, o, q)


def certify_chord(o, identity, q, qt, native_gradient, native_phi, native_phi_trial,
        iteration, trial, *, deadline, resource_limit_bytes, admitted_bytes):
    """Original14-key strict native-gradient / nested actual displacement proof."""
    a, _ = _identity_metadata(identity)
    if (any(not _vector(v, a) for v in (qt, native_gradient))
        or type(native_phi) is not float or type(native_phi_trial) is not float
        or type(iteration) is not int or not 0 <= iteration <= 199
        or type(trial) is not int or not 0 <= trial <= 19):
        raise ValueError('original quadratic: actual native chord/counters')
    record = intervals._record(iteration, trial, native_phi, native_phi_trial)
    try:
        validate(o, identity, q, deadline=deadline, resource_limit_bytes=resource_limit_bytes, admitted_bytes=admitted_bytes)
    except intervals._Expired:
        record['cause'] = 'wall_cap'
        return intervals._validate_record(record)
    if (not np.isfinite(qt).all() or not np.isfinite(native_gradient).all()
        or record['native_phi_current'] is None or record['native_phi_trial'] is None):
        return intervals._validate_record(record)
    if np.any(qt < o.lower) or np.any(qt > o.upper):
        raise ValueError('original quadratic: actual native trial outside box')
    record['displacement_inf_q'] = float(np.max(np.abs(qt-q)))
    if not np.any(qt != q):
        record['cause'] = 'zero_displacement'
        return intervals._validate_record(record)
    for passes, digits, native_rows in ((1, 34, True), (1, 34, False), (2, 50, False), (3, 80, False)):
        if native_rows:
            ar = intervals._Intervals(digits, deadline)
            ar._use_native_rows = True
        else:
            # Same source reductions, unchanged precision ladder and factors.
            # Import only at execution to keep the source/terminal ABI acyclic.
            import physical_original_terminal as terminal
            ar = terminal.original_row_arithmetic(digits, deadline)
        try:
            ar.check()
            qv = [ar.exact(v) for v in q]
            dq = [ar.sub(ar.exact(v), old) for v, old in zip(qt, qv)]
            slope = ar.dot(native_gradient, dq)
            if slope[0] >= 0:
                record.update(passes=passes, precision_digits=digits,
                    slope_interval=tuple(map(str, slope)), decision='certified_reject', cause='non_descent')
                return intervals._validate_record(record)
            residual = [ar.sub(v, ar.exact(d)) for v, d in zip(
                _map(ar, o.sensitivity, o.projection, qv), o.observations)]
            wr = _whiten(ar, o.whitening, residual)
            dy = _whiten(ar, o.whitening, _map(ar, o.sensitivity, o.projection, dq))
            change = ar.scalar(o.likelihood_scale, ar.change(wr, dy))
            delta = [ar.sub(v, ar.exact(ref)) for v, ref in zip(qv, o.reference)]
            for term in o.terms:
                r = ar.matrix(term.weights, ar.matrix(term.derivative, delta))
                dr = ar.matrix(term.weights, ar.matrix(term.derivative, dq))
                change = ar.add(change, ar.scalar(o.beta, ar.scalar(term.alpha, ar.change(r, dr))))
            margin = ar.sub(change, ar.scalar(1e-4, slope))
            record.update(passes=passes, precision_digits=digits,
                slope_interval=tuple(map(str, slope)), delta_interval=tuple(map(str, change)),
                armijo_margin_interval=tuple(map(str, margin)))
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
