"""Owned original-noise free-face accuracy certificate for convex quadratics.

The owner constructs its own principal Joseph metric. No caller inverse, mask,
factor, success callback, fit restart or nonlinear curvature admission exists.
All source and stored-factor actions below use pure outward Decimal arithmetic.
"""
from dataclasses import replace
from decimal import Decimal
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np

import physical_original_quadratic as source
import physical_owned_spd as owned
import physical_original_rows as exact_rows


SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
ZERO, ONE = Decimal(0), Decimal(1)
# Transitive closed source binding until consumers add the named module to
# their full inventories. The literal terminal file itself binds this hash.
ROWS_SHA256 = '8a18a0ae04bfd09336480e06d2e9526aecab79a232033e9ca5d0040b16e9f399'


def original_row_arithmetic(digits, deadline):
    if (exact_rows.SOURCE_SHA256 != ROWS_SHA256 or
        hashlib.sha256(Path(exact_rows.__file__).read_bytes()).hexdigest() != ROWS_SHA256):
        raise ValueError('original terminal: closed exact row source drift')
    if type(digits) is not int or digits not in (34, 50, 80):
        raise ValueError('original terminal: unchanged original precision ladder')
    return exact_rows.OriginalTerminalIntervals(digits, deadline)


def _absolute(pair):
    return max(pair[0].copy_abs(), pair[1].copy_abs())


def _norm(ar, pairs):
    square = ZERO
    for pair in pairs:
        v = _absolute(pair)
        square = ar.hi.add(square, ar.hi.multiply(v, v))
    return ar.hi.next_plus(ar.hi.sqrt(square)) if square else ZERO


def _array(v):
    out = v.copy(order='C')
    out.flags.writeable = False
    return out


def _sparse(v):
    out = v.copy()
    for backing in (out.data, out.indices, out.indptr):
        backing.flags.writeable = False
    return out


def _snapshot(o):
    noise = source.OriginalWhitening(o.whitening.kind, _array(o.whitening.values),
        None if o.whitening.covariance is None else _array(o.whitening.covariance))
    return replace(o, sensitivity=_array(o.sensitivity),
        projection=None if o.projection is None else _array(o.projection), whitening=noise,
        observations=_array(o.observations), reference=_array(o.reference),
        lower=_array(o.lower), upper=_array(o.upper), terms=tuple(
            owned.QuadraticTerm(t.alpha, _sparse(t.weights), _sparse(t.derivative)) for t in o.terms),
        prediction_sensitivity=_array(o.prediction_sensitivity),
        prediction_projection=None if o.prediction_projection is None else _array(o.prediction_projection))


def _source_digest(o):
    return owned.digest((o.sensitivity, o.projection, o.whitening.kind,
        o.whitening.values, o.whitening.covariance, o.observations, o.reference,
        o.lower, o.upper, o.likelihood_scale, o.beta,
        tuple((t.alpha, t.weights, t.derivative) for t in o.terms),
        o.prediction_sensitivity, o.prediction_projection))


class OwnedOriginalTerminal:
    """One model/source/face owner; certify closes on every successful or failed proof.

    This is a trusted in-process numerical ABI, not source or native-host admission.
    Original native H/g are not replaced; a certificate does not move the model.
    """
    def __init__(self, metric_operands, original, identity, q, native_gradient,
            initial_norm, *, deadline, resource_limit_bytes, admitted_bytes,
            retained_audit_bytes=0):
        self._metric = self._original = self._q = self._native_gradient = None
        self._identity = None
        self.actions = 0
        self._closed = True
        started = monotonic()
        if (exact_rows.SOURCE_SHA256 != ROWS_SHA256 or
            hashlib.sha256(Path(exact_rows.__file__).read_bytes()).hexdigest() != ROWS_SHA256):
            raise ValueError('original terminal: closed exact row source drift')
        allocation = source.validate(original, identity, q, deadline=deadline,
            resource_limit_bytes=resource_limit_bytes, admitted_bytes=admitted_bytes)
        a, m = source._identity_metadata(identity)
        if (not source._vector(native_gradient, a) or not np.isfinite(native_gradient).all()
            or type(initial_norm) is not float or not np.isfinite(initial_norm) or initial_norm <= 0.
            or type(retained_audit_bytes) is not int or retained_audit_bytes < 0):
            raise ValueError('original terminal: literal native normalization/audit metadata')
        owned.validate_operands(metric_operands, identity, q, resource_limit_bytes)
        # The native kernel dictionary charges these literal bounded arrays,
        # not arbitrary oversized/foreign ultimate backing supplied via views.
        if (source._backing_bytes(metric_operands.whitened_jacobian) > 8*m*a
            or any(source._backing_bytes(v) > cap for v, cap in zip(
                (metric_operands.regularizer.data, metric_operands.regularizer.indices,
                    metric_operands.regularizer.indptr), (8*7*a, 4*7*a, 4*(a+1))))):
            raise ValueError('original terminal: closed native metric backing capacities')
        if (metric_operands.binding != original.binding
            or metric_operands.source_components != original.source_components
            or metric_operands.likelihood_scale != original.likelihood_scale
            or metric_operands.covariance != (original.whitening.kind != 'diagonal_sd')):
            raise ValueError('original terminal: same original source/model/noise normalization')
        # Count before index allocation. Exact bound equalities, never a supplied
        # working mask or proximity threshold, define this terminal face.
        f = int(np.count_nonzero((q != original.lower) & (q != original.upper)))
        phase = dict(source_arithmetic_bytes=allocation['arithmetic_phase_bytes'],
            free_endpoint_bytes=source.ENDPOINT_PAIR_BYTES*12*f,
            factor_and_transpose_bytes=16*m*f+16*7*f+64*f+4*(f+1),
            retained_audit_bytes=retained_audit_bytes,
            native_workspace_bytes=source.RESERVE_BYTES, metadata_bytes=32768)
        maximum = allocation['maximum']+sum(v for k, v in phase.items() if k != 'source_arithmetic_bytes')
        if maximum > admitted_bytes or maximum > resource_limit_bytes:
            raise ValueError('original terminal: simultaneous original source/factor/audit resource cap')
        self.allocation = dict(original=allocation, terminal_phase=phase,
            maximum=maximum, admitted_bytes=admitted_bytes, resource_limit_bytes=resource_limit_bytes)
        self.deadline = deadline
        self.initial_norm = initial_norm
        self._identity = identity.copy()
        try:
            self._q, self._native_gradient = _array(q), _array(native_gradient)
            self._original = _snapshot(original)
            self.free = np.flatnonzero((self._q != self._original.lower)
                & (self._q != self._original.upper)).astype(np.int64)
            self.free.flags.writeable = False
            self.source_sha256 = _source_digest(self._original)
            self.model_sha256 = owned.digest(self._q)
            self.face_sha256 = owned.digest(self.free)
            self.factor_sha256 = None
            if f:
                self._metric = owned.OwnedMetric(metric_operands, self._identity,
                    self._q, self.free, deadline, resource_limit_bytes)
                numeric = self._metric._numeric
                # The factory's own finite canonical factors, never caller factors.
                owned._csr(numeric.lower, f, f, 7*f)
                if (not np.array_equal(numeric.lower.diagonal(), np.ones(f))
                    or np.any(numeric.lower.tocoo().col > numeric.lower.tocoo().row)
                    or not np.isfinite(numeric.pivots).all() or np.any(numeric.pivots <= 0.)
                    or numeric.b.shape != (m, f) or numeric.f.shape != (f, m)
                    or not np.isfinite(numeric.b).all() or not np.isfinite(numeric.f).all()
                    or not np.array_equal(numeric.free, self.free)):
                    raise ValueError('original terminal: owned unit lower/positive pivot/source face')
                self.factor_sha256 = owned.digest((numeric.lower, numeric.pivots,
                    numeric.b, numeric.f, numeric.free))
            self._closed = False
            self._check()
        except BaseException:
            self.close()
            raise
        self.setup_seconds = monotonic()-started

    @property
    def live_payload_bytes(self):
        if self._closed:
            return 0
        o = self._original
        return (source_payload(o)+self._q.nbytes+self._native_gradient.nbytes+self.free.nbytes
            + (0 if self._metric is None else self._metric.live_payload_bytes))

    def _check(self):
        if self._closed:
            raise ValueError('original terminal: disposed owner')
        if monotonic() > self.deadline:
            raise source.intervals._Expired

    def _stored_action(self, ar, vector, transpose):
        self._check()
        numeric = self._metric._numeric
        f = len(self.free)
        if len(vector) != f:
            raise ValueError('original terminal: own principal action dimensions')
        self.actions += 1
        def triangular(matrix, values, reverse=False):
            result = [None]*f
            for i in (range(f-1, -1, -1) if reverse else range(f)):
                ar.check()
                begin, end = matrix.indptr[i:i+2]
                js, cs = matrix.indices[begin:end], matrix.data[begin:end]
                selected = [(int(j), c) for j, c in zip(js, cs)
                    if (j > i if reverse else j < i)]
                result[i] = ar.sub(values[i], ar.dot([c for _, c in selected],
                    [result[j] for j, _ in selected]))
            return result
        z = ar.matrix(numeric.f.T, vector)
        w = [ar.sub(v, x) for v, x in zip(vector, ar.matrix(numeric.b.T, z))]
        x = triangular(numeric.lower, w)
        x = [source._divide(ar, v, d) for v, d in zip(x, numeric.pivots)]
        y = triangular(transpose, x, True)
        by = ar.matrix(numeric.b, y)
        fy, fz = ar.matrix(numeric.f, by), ar.matrix(numeric.f, z)
        return [ar.add(ar.sub(v, left), right) for v, left, right in zip(y, fy, fz)]

    def _free_column(self, ar, j, restricted_g, restricted_terms):
        o = self._original
        raw = [ar.exact(v) for v in o.sensitivity[:, j]]
        mapped = raw if o.projection is None else [ar.dot(o.projection, raw[i:i+3])
            for i in range(0, len(raw), 3)]
        twice = source._whiten(ar, o.whitening, source._whiten(ar, o.whitening, mapped), True)
        result = [ar.scalar(2.*o.likelihood_scale, v)
            for v in source._adjoint(ar, restricted_g, o.projection, twice)]
        for term, dt in restricted_terms:
            col = term.derivative.getcol(j).toarray().ravel()
            values = ar.matrix(term.weights, [ar.exact(v) for v in col])
            values = ar.matrix(dt, ar.matrix(term.weights.T.tocsr(), values))
            result = [ar.add(old, ar.scalar(o.beta, ar.scalar(term.alpha, ar.scalar(2., v))))
                for old, v in zip(result, values)]
        return result

    def _coupling(self, ar):
        """Original |H_iF| row sums, without forming a dense physical Hessian."""
        o, a = self._original, len(self._q)
        norms = []
        for j in range(a):
            ar.check()
            raw = [ar.exact(v) for v in o.sensitivity[:, j]]
            mapped = raw if o.projection is None else [ar.dot(o.projection, raw[i:i+3])
                for i in range(0, len(raw), 3)]
            norms.append(_norm(ar, source._whiten(ar, o.whitening, mapped)))
        total = ZERO
        for j in self.free:
            total = ar.hi.add(total, norms[j])
        coupling = [ar.hi.multiply(Decimal.from_float(2.*o.likelihood_scale), ar.hi.multiply(v, total)) for v in norms]
        free_mask = np.zeros(a, dtype=bool)
        free_mask[self.free] = True
        for term in o.terms:
            d = term.derivative
            abs_d, abs_w = abs(d), abs(term.weights)
            row_sums = []
            for row in range(d.shape[0]):
                ar.check()
                begin, end = d.indptr[row:row+2]
                total = ZERO
                for j, v in zip(d.indices[begin:end], d.data[begin:end]):
                    if free_mask[j]:
                        total = ar.hi.add(total, Decimal.from_float(float(v)).copy_abs())
                row_sums.append((ZERO, total))
            values = ar.matrix(abs_d.T.tocsr(), ar.matrix(abs_w.T.tocsr(), ar.matrix(abs_w, row_sums)))
            for i, v in enumerate(values):
                coupling[i] = ar.hi.add(coupling[i],
                    ar.scalar(o.beta, ar.scalar(term.alpha, ar.scalar(2., v)))[1])
        return coupling

    def certify(self, policy):
        try:
            self._check()
            owned.validate_terminal(policy)
        except BaseException:
            self.close()
            raise
        started = monotonic()
        o, q, f = self._original, self._q, len(self.free)
        ar = original_row_arithmetic(34, self.deadline)
        record = dict(domain='original_noise_strongly_convex_free_face', passed=False,
            reason=None, source_sha256=self.source_sha256, model_sha256=self.model_sha256,
            face_sha256=self.face_sha256, factor_sha256=self.factor_sha256,
            free_indices=self.free.tolist(), precision_digits=34, allocation=self.allocation,
            setup_seconds=self.setup_seconds, seconds=0., actions=0, disposed=False, bounds=None)
        record.update(terminal_arithmetic_epoch=exact_rows.ARITHMETIC_EPOCH,
            terminal_arithmetic_sha256=ROWS_SHA256,
            exact_row_workspace_limit_bytes=exact_rows.ROW_WORKSPACE_BYTES)
        try:
            gradient = source._gradient(ar, o, q)
            projected, squared, inf = [], ZERO, ZERO
            for i, (lo, hi) in enumerate(gradient):
                if q[i] == o.lower[i]:
                    lo, hi = min(lo, ZERO), min(hi, ZERO)
                elif q[i] == o.upper[i]:
                    lo, hi = max(lo, ZERO), max(hi, ZERO)
                value = _absolute((lo, hi))
                inf = max(inf, value)
                squared = ar.hi.add(squared, ar.hi.multiply(value, value))
                projected.append((lo, hi))
            small = o.terms[0]
            mu = min(ar.scalar(o.beta, ar.scalar(small.alpha,
                ar.scalar(2., ar.mul(ar.exact(v), ar.exact(v)))))[0] for v in small.weights.data)
            if mu <= ZERO:
                raise ValueError('original terminal: original positive smallness')
            source_kkt = ar.hi.divide(inf, Decimal.from_float(self.initial_norm))
            native = self._native_gradient.copy()
            native[q == o.lower] = np.minimum(native[q == o.lower], 0.)
            native[q == o.upper] = np.maximum(native[q == o.upper], 0.)
            native_kkt = float(np.linalg.norm(native, np.inf)/self.initial_norm)
            gap = ar.hi.divide(squared, ar.lo.multiply(Decimal(2), mu))
            record.update(normalized_exact_bound_kkt=native_kkt,
                source_normalized_kkt_upper=str(source_kkt), required_normalized_kkt=policy.required_kkt_normalized)
            # Exact source KKT plus the ORIGINAL positive scientific smallness
            # proves q is the unique box optimum directly. This is not a float
            # nearzero test or an uncomputed assertion about P H. All source
            # operands, native KKT, free-box and active signs still apply.
            exact_stationary = squared == ZERO
            record['proof_basis'] = ('exact_source_feasible_kkt' if exact_stationary else 'free_face_neumann')
            error, kappa, eta = ZERO, ZERO, ZERO
            if f and not exact_stationary:
                restricted = np.ascontiguousarray(o.sensitivity[:, self.free])
                terms = [(t, t.derivative[:, self.free].T.tocsr()) for t in o.terms]
                transpose = self._metric._numeric.lower.T.tocsr()
                rows = [ZERO]*f
                for index, j in enumerate(self.free):
                    v = self._stored_action(ar, self._free_column(ar, int(j), restricted, terms), transpose)
                    for i, pair in enumerate(v):
                        value = _absolute(ar.sub(ar.exact(1. if i == index else 0.), pair))
                        rows[i] = ar.hi.add(rows[i], value)
                kappa = max(rows)
                record.update(kappa_upper=str(kappa), contraction_row_sums=list(map(str, rows)))
                if kappa >= ONE:
                    record['reason'] = 'contraction_not_certified'
                    return record
                eta = max(map(_absolute, self._stored_action(ar, [gradient[i] for i in self.free], transpose)))
                error = ar.hi.divide(eta, ar.lo.subtract(ONE, kappa))
            inside = all(ar.lo.subtract(Decimal.from_float(float(q[i])), error) > Decimal.from_float(float(o.lower[i]))
                and ar.hi.add(Decimal.from_float(float(q[i])), error) < Decimal.from_float(float(o.upper[i])) for i in self.free)
            coupling = self._coupling(ar) if f and error else [ZERO]*len(q)
            free_mask = np.zeros(len(q), dtype=bool)
            free_mask[self.free] = True
            margins = []
            for i in np.flatnonzero(~free_mask):
                lo, hi = gradient[i]
                signed = lo if q[i] == o.lower[i] else hi.copy_negate()
                margins.append(dict(index=int(i), sign_margin_lower=str(
                    ar.lo.subtract(signed, ar.hi.multiply(coupling[i], error)))))
            signs = all(Decimal(v['sign_margin_lower']) >= ZERO for v in margins)
            model = ar.hi.multiply(ar.hi.next_plus(ar.hi.sqrt(Decimal(f))), error) if f else ZERO
            maximum = ZERO
            rows = o.prediction_sensitivity
            for i in range((len(rows) if o.prediction_projection is None else len(rows)//3) if model else 0):
                ar.check()
                if o.prediction_projection is None:
                    values = [ar.exact(v) for v in rows[i]]
                else:
                    values = [ar.dot(o.prediction_projection, [ar.exact(v) for v in rows[3*i:3*i+3, j]])
                        for j in range(len(q))]
                maximum = max(maximum, _norm(ar, values))
            prediction = ar.hi.multiply(maximum, model)
            record.update(kappa_upper=None if exact_stationary else str(kappa),
                eta_upper=None if exact_stationary else str(eta), free_error_inf_upper=str(error),
                inside_original_bounds=bool(inside), active_signs=margins, active_sign_pass=bool(signs),
                bounds=dict(mu_lower=str(mu), feasible_gradient_inf_upper=str(inf),
                    model_error_upper=str(model), objective_gap_upper=str(gap),
                    physical_prediction_error_upper=str(prediction)))
            passed = (inside and signs and native_kkt <= policy.required_kkt_normalized
                and source_kkt <= Decimal.from_float(policy.required_kkt_normalized))
            for value, limit in ((model, policy.model_error_limit), (gap, policy.objective_gap_limit),
                (prediction, policy.physical_prediction_error_limit)):
                passed = passed and (limit is None or value <= Decimal.from_float(limit))
            self._check()
            record.update(passed=bool(passed), reason='original_accuracy_certified' if passed else 'original_accuracy_not_certified')
            return record
        finally:
            record.update(actions=self.actions, seconds=monotonic()-started)
            self.close()
            record['disposed'] = self.live_payload_bytes == 0

    def close(self):
        if self._metric is not None:
            self._metric.close()
        self._metric = self._original = self._q = self._native_gradient = self._identity = None
        self.free = None
        self._closed = True


def source_payload(o):
    values = (o.sensitivity, o.observations, o.reference, o.lower, o.upper,
        o.whitening.values, o.prediction_sensitivity)
    total = sum(v.nbytes for v in values)
    total += sum(v.nbytes for v in (o.projection, o.prediction_projection, o.whitening.covariance) if v is not None)
    return total+sum(v.nbytes for t in o.terms for m in (t.weights, t.derivative)
        for v in (m.data, m.indices, m.indptr))
