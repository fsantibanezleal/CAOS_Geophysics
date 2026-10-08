"""Prospective HP epoch: invertible right scaling of the WHOLE objective.

Never substituted for frozen v1/v2 receipts. P depends on training geometry,
uncertainty and lambda, not responses. No dense survey matrices are constructed.
"""
from hashlib import sha256
import math

import magnetic_line_survey as core

EPOCH = 'augmented_hp/1'
LSMR_SHA256 = 'f1e60be3f5216f602bf33535acc72474aa80fbe0149d5929145d0432bc29e0ce'


def content_sha256(array):
    return sha256(memoryview(array).cast('B')).hexdigest()


def preconditioner(model, damping):
    """One compensated weighted-column pass; no response argument exists."""
    if type(model) is not core.GlobalOperator:
        raise core.SurveyError('invalid_contract', 'fit')
    np = model.np
    damping = core._damping(damping)
    total, compensation = np.zeros(model.m), np.zeros(model.m)
    with np.errstate(over='raise', invalid='raise', divide='raise'):
        for row in core._chunks(model.n, model.r):
            for col in core._chunks(model.m, model.c):
                a = model._direct(row, col)*model.root_weights[row, None]/model.scales[col]
                core._sum_into(total[col], compensation[col], np.sum(a*a, axis=0))
        p = 1/np.sqrt(total+damping)
    core._finite(np, p)
    if np.any(p <= 0):
        raise core.SurveyError('nonconverged', 'fit')
    p.flags.writeable = False
    return p


class AugmentedOperator:
    def __init__(self, model, damping):
        from scipy.sparse.linalg import LinearOperator
        self.model, self.damping = model, core._damping(damping)
        self.p = preconditioner(model, damping)
        self.root = math.sqrt(self.damping)
        self.forward_calls = self.adjoint_calls = 0
        self.operator = LinearOperator((model.n+model.m, model.m), dtype=model.np.float64,
            matvec=self.forward, rmatvec=self.adjoint)

    def _vector(self, value, length):
        np = self.model.np
        if type(value) is not np.ndarray or value.dtype != np.dtype('<f8') or \
           value.shape not in ((length,), (length, 1)):
            raise core.SurveyError('invalid_contract', 'fit')
        core._finite(np, value)
        return value.reshape(length)

    def forward(self, value):
        c = self.p*self._vector(value, self.model.m)
        result = self.model.np.concatenate((self.model._forward(c), self.root*c))
        core._finite(self.model.np, result)
        self.forward_calls += 1
        return result

    def adjoint(self, value):
        u = self._vector(value, self.model.n+self.model.m)
        result = self.p*(self.model._adjoint(u[:self.model.n])+self.root*u[self.model.n:])
        core._finite(self.model.np, result)
        self.adjoint_calls += 1
        return result


def original_diagnostics(model, values, damping, c):
    """Direct-kernel predicate, calculated even for iteration-limit failures.

    This diagnostic does not accept a stop code; solve_hp separately requires
    both the actual successful B termination AND this original-coordinate gate.
    """
    np = model.np
    y = core._array(np, values, (model.n,))
    c = core._array(np, c, (model.m,))
    damping = core._damping(damping)
    core._finite(np, y)
    core._finite(np, c)
    atb, atprediction, gradient, cb, cp, cg = (np.zeros(model.m) for _ in range(6))
    terms = []
    for row in core._chunks(model.n, model.r):
        prediction, compensation = np.zeros(row.stop-row.start), np.zeros(row.stop-row.start)
        for col in core._chunks(model.m, model.c):
            a = model._direct(row, col)*model.root_weights[row, None]/model.scales[col]
            core._sum_into(prediction, compensation, a@c[col])
        b = model.root_weights[row]*y[row]
        residual = prediction-b
        terms.append(core._squared_norm(residual))
        for col in core._chunks(model.m, model.c):
            a = model._direct(row, col)*model.root_weights[row, None]/model.scales[col]
            core._sum_into(atb[col], cb[col], a.T@b)
            core._sum_into(atprediction[col], cp[col], a.T@prediction)
            core._sum_into(gradient[col], cg[col], a.T@residual)
    gradient += damping*c
    data = math.fsum(terms)
    square = core._squared_norm(c)
    penalty = damping*square
    if square > 0 and penalty == 0:
        raise core.SurveyError('nonconverged', 'fit')
    denominator = max(float(np.max(np.abs(atb))), float(np.max(np.abs(atprediction))),
        damping*float(np.max(np.abs(c))))
    absolute = float(np.max(np.abs(gradient)))
    relative = absolute/denominator if denominator else (0. if not absolute else math.inf)
    diagnostics = dict(data_term=data, regularization_term=penalty, objective=data+penalty,
        gradient_denominator=denominator, stationarity_inf=absolute,
        stationarity_relative=relative, coefficient_error_bound_nT=math.hypot(*gradient)/damping)
    if not all(math.isfinite(value) for value in diagnostics.values()):
        raise core.SurveyError('nonconverged', 'fit')
    return diagnostics


def solve_hp(model, values, damping):
    """Retain actual failure state before refusing, never a SurveyResult PASS."""
    from scipy.sparse.linalg import lsmr
    from threadpoolctl import threadpool_limits
    np = model.np
    y = core._array(np, values, (model.n,))
    core._finite(np, y)
    with threadpool_limits(limits=1), np.errstate(over='raise', invalid='raise', divide='raise'):
        augmented = AugmentedOperator(model, damping)
        rhs = np.concatenate((model.root_weights*y, np.zeros(model.m)))
        output = lsmr(augmented.operator, rhs, damp=0., atol=1e-12, btol=1e-12,
            conlim=1e8, maxiter=2000, show=False, x0=None)
        z = np.asarray(output[0], dtype='<f8')
        c = np.ascontiguousarray(augmented.p*z, dtype='<f8')
        q = np.ascontiguousarray(c/model.scales, dtype='<f8')
        for array in (z, c, q):
            core._finite(np, array)
            array.flags.writeable = False
        estimates = dict(zip(('normr', 'normar', 'norma', 'conda', 'normx'), map(float, output[3:]), strict=True))
        receipt = dict(schema='m03-hp-solve/1', policy_epoch=EPOCH, rows=model.n,
            sources=model.m, augmented_rows=model.n+model.m, damping=core._damping(damping),
            scalar_lsmr_damp=0., condition_domain='B=HP_recurrence_estimate_not_A_bound',
            istop=int(output[1]), iterations=int(output[2]), recurrence=estimates,
            preconditioner_sha256=content_sha256(augmented.p),
            preconditioner_min=float(np.min(augmented.p)), preconditioner_max=float(np.max(augmented.p)),
            scales_sha256=content_sha256(model.scales), sources_sha256=content_sha256(model.sources),
            scaled_coefficients_sha256=content_sha256(c), coefficients_sha256=content_sha256(q),
            original_diagnostics=None, diagnostic_error=None,
            operator_forward_calls=augmented.forward_calls, operator_adjoint_calls=augmented.adjoint_calls,
            numerical_verdict='fail', field_acceptance='not_established')
        model.hp_failure_state = dict(receipt=receipt, scaled_coefficients=c, coefficients=q)
        try:
            diagnostics = original_diagnostics(model, y, damping, c)
            receipt['original_diagnostics'] = diagnostics
        except core.SurveyError as error:
            receipt['diagnostic_error'] = error.error
            raise
        if receipt['istop'] not in (0, 1, 2, 4, 5) or \
           not all(math.isfinite(t) and t >= 0 for t in estimates.values()) or \
           estimates['conda'] >= 1e8 or diagnostics['stationarity_relative'] > 1e-9 or \
           augmented.forward_calls > 2000 or augmented.adjoint_calls > 2001:
            error = core.SurveyError('nonconverged', 'fit')
            error.partial_solve = receipt
            raise error
        receipt['numerical_verdict'] = 'component_pass'
        return dict(receipt=receipt, scaled_coefficients=c, coefficients=q)
