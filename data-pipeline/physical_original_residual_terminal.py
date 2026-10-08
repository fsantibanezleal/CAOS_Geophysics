"""Separate original convex state certificate, not native fit admission.

One owned floating Joseph witness is checked through the original real H/g.
Scientific smallness bounds its residual error. No inverse-defect assumption,
caller witness, accepted model move, proof fallback or nonlinear/GN theorem.
"""
from decimal import Decimal
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np

import physical_original_terminal as original

SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
STATE_EPOCH = 'original-physical-residual-strong-convexity-state-1'
ZERO = Decimal(0)


def _hessian_action(ar, o, vector):
    mapped = original.source._map(ar, o.sensitivity, o.projection, vector)
    twice = original.source._whiten(ar, o.whitening,
        original.source._whiten(ar, o.whitening, mapped), True)
    result = [ar.scalar(2.*o.likelihood_scale, v) for v in
        original.source._adjoint(ar, o.sensitivity, o.projection, twice)]
    for t in o.terms:
        v = ar.matrix(t.weights, ar.matrix(t.derivative, vector))
        v = ar.matrix(t.derivative.T.tocsr(), ar.matrix(t.weights.T.tocsr(), v))
        result = [ar.add(old, ar.scalar(o.beta, ar.scalar(t.alpha, ar.scalar(2., x))))
            for old, x in zip(result, v)]
    return result


class OwnedOriginalResidualTerminal(original.OwnedOriginalTerminal):
    """Same original owner; additional witness capacity is reserved pre-factory."""
    def __init__(self, metric_operands, operands, identity, q, gradient, initial_norm,
            *, deadline, resource_limit_bytes, admitted_bytes, retained_audit_bytes=0):
        a, _ = original.source._identity_metadata(identity)
        if not original.source._vector(q, a) or type(retained_audit_bytes) is not int or retained_audit_bytes < 0:
            raise ValueError('original residual: closed original vector/audit count')
        # Full native center/witness plus error and expression temporaries. The
        # original12f/source endpoint allowance also remains fully reserved.
        witness_charge = 128*a
        super().__init__(metric_operands, operands, identity, q, gradient, initial_norm,
            deadline=deadline, resource_limit_bytes=resource_limit_bytes,
            admitted_bytes=admitted_bytes, retained_audit_bytes=retained_audit_bytes+witness_charge)
        self.witness_charge = witness_charge

    def certify(self, policy):
        record = dict(domain=STATE_EPOCH, proof_basis='original_physical_residual_strong_convexity',
            passed=False, reason=None, source_sha256=self.source_sha256,
            model_sha256=self.model_sha256, face_sha256=self.face_sha256,
            factor_sha256=self.factor_sha256, allocation=self.allocation,
            setup_seconds=self.setup_seconds, seconds=0., actions=0, disposed=False,
            native_fit_accepted=False, full_method_accepted=False, host_accepted=False)
        started = monotonic()
        try:
            self._check()
            original.owned.validate_terminal(policy)
            ar = original.original_row_arithmetic(34, self.deadline)
            o, q, free = self._original, self._q, self.free
            gradient = original.source._gradient(ar, o, q)
            projected = []
            for i, pair in enumerate(gradient):
                lo, hi = pair
                if q[i] == o.lower[i]:
                    lo, hi = min(lo, ZERO), min(hi, ZERO)
                elif q[i] == o.upper[i]:
                    lo, hi = max(lo, ZERO), max(hi, ZERO)
                projected.append((lo, hi))
            small = o.terms[0]
            mu = min(ar.scalar(o.beta, ar.scalar(small.alpha,
                ar.scalar(2., ar.mul(ar.exact(v), ar.exact(v)))))[0] for v in small.weights.data)
            if mu <= ZERO:
                raise ValueError('original residual: unchanged positive scientific smallness')
            native = self._native_gradient.copy()
            native[q == o.lower] = np.minimum(native[q == o.lower], 0.)
            native[q == o.upper] = np.maximum(native[q == o.upper], 0.)
            native_kkt = float(np.linalg.norm(native, np.inf)/self.initial_norm)
            inf = max(map(original._absolute, projected))
            source_kkt = ar.hi.divide(inf, Decimal.from_float(self.initial_norm))
            square = ZERO
            for v in map(original._absolute, projected):
                square = ar.hi.add(square, ar.hi.multiply(v, v))
            gap = ar.hi.divide(square, ar.lo.multiply(Decimal(2), mu))
            witness = np.zeros(len(q), dtype=np.float64)
            rho = ZERO
            residual = gradient
            if len(free):
                center = np.zeros(len(q), dtype=np.float64)
                for j in free:
                    lo, hi = gradient[j]
                    center[j] = float(ar.lo.divide(ar.lo.add(lo, hi), Decimal(2)))
                if not np.isfinite(center).all():
                    raise ValueError('original residual: finite source gradient center')
                self._check()
                witness = -self._metric.apply(center)
                self.actions += 1
                self._check()
                if not np.isfinite(witness).all() or np.any(witness[np.setdiff1d(np.arange(len(q)), free)] != 0.):
                    raise ValueError('original residual: finite own free-face witness')
                hd = _hessian_action(ar, o, [ar.exact(v) for v in witness])
                residual = [ar.add(g, h) for g, h in zip(gradient, hd)]
                rho = ar.hi.divide(original._norm(ar, [residual[i] for i in free]), mu)
            # The virtual q+d is an exact real sum, not a rounded new model.
            shifted = [ar.add(ar.exact(x), ar.exact(d)) for x, d in zip(q, witness)]
            inside = all(ar.lo.subtract(shifted[i][0], rho) > Decimal.from_float(float(o.lower[i]))
                and ar.hi.add(shifted[i][1], rho) < Decimal.from_float(float(o.upper[i])) for i in free)
            coupling = self._coupling(ar) if len(free) and rho else [ZERO]*len(q)
            active = np.ones(len(q), dtype=bool)
            active[free] = False
            margins = []
            for i in np.flatnonzero(active):
                lo, hi = residual[i]
                signed = lo if q[i] == o.lower[i] else hi.copy_negate()
                margins.append(dict(index=int(i), sign_margin_lower=str(ar.lo.subtract(
                    signed, ar.hi.multiply(coupling[i], rho)))))
            signs = all(Decimal(v['sign_margin_lower']) >= ZERO for v in margins)
            model = ar.hi.add(original._norm(ar, [ar.exact(witness[i]) for i in free]), rho)
            maximum = ZERO
            rows = o.prediction_sensitivity
            for i in range((len(rows) if o.prediction_projection is None else len(rows)//3) if model else 0):
                ar.check()
                if o.prediction_projection is None:
                    values = [ar.exact(v) for v in rows[i]]
                else:
                    values = [ar.dot(o.prediction_projection,
                        [ar.exact(v) for v in rows[3*i:3*i+3, j]]) for j in range(len(q))]
                maximum = max(maximum, original._norm(ar, values))
            prediction = ar.hi.multiply(maximum, model)
            passed = (inside and signs and native_kkt <= policy.required_kkt_normalized
                and source_kkt <= Decimal.from_float(policy.required_kkt_normalized))
            for value, limit in ((model, policy.model_error_limit), (gap, policy.objective_gap_limit),
                    (prediction, policy.physical_prediction_error_limit)):
                passed = passed and (limit is None or value <= Decimal.from_float(limit))
            self._check()
            record.update(passed=bool(passed), reason='original_accuracy_certified' if passed else 'original_accuracy_not_certified',
                normalized_exact_bound_kkt=native_kkt, source_normalized_kkt_upper=str(source_kkt),
                required_normalized_kkt=policy.required_kkt_normalized, free_indices=free.tolist(),
                witness_q=witness.tolist(), witness_residual_intervals=[tuple(map(str, v)) for v in residual],
                residual_radius_upper=str(rho), inside_original_bounds=bool(inside),
                active_signs=margins, active_sign_pass=bool(signs), witness_workspace_charge_bytes=self.witness_charge,
                bounds=dict(mu_lower=str(mu), feasible_gradient_inf_upper=str(inf), model_error_upper=str(model),
                    objective_gap_upper=str(gap), physical_prediction_error_upper=str(prediction)))
            return record
        finally:
            record.update(seconds=monotonic()-started, actions=self.actions)
            self.close()
            record['disposed'] = self.live_payload_bytes == 0
