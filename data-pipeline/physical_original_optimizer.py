"""Original-noise linear reduced native solver with owned accuracy termination.

Separate prospective epoch. Native original objective/H/g, 200 summed CG,
200 accepted steps, 20 Armijo trials and the uninterrupted 120s clock remain.
No nonlinear, quartic, arbitrary factor, callback terminal or oracle fallback.
"""
from dataclasses import dataclass
from decimal import Decimal
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np

import physical_reduced_optimizer as reduced
import physical_original_quadratic as source
import physical_original_terminal as accuracy
import physical_original_residual_terminal as residual_accuracy


SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
LINEAR_EPOCH = 'physical-gncg-original-noise-reduced-joseph-candidate-9'
POLICY = 'closed-original-noise-reduced-joseph-free-face-residual-accuracy-2'
RESIDUAL_TERMINAL_SHA256 = 'a9bf32a6c4e932d7d4efa1f38540778e2993f74982adb9f29985d921ecb5ddf7'
ConditionedBinding = reduced.ConditionedBinding
ConditionedBudget = reduced.ConditionedBudget
VENDOR_SOURCE_SHA256 = reduced.VENDOR_SOURCE_SHA256


def _check_residual_source():
    if (residual_accuracy.SOURCE_SHA256 != RESIDUAL_TERMINAL_SHA256 or
            hashlib.sha256(Path(residual_accuracy.__file__).read_bytes()).hexdigest() != RESIDUAL_TERMINAL_SHA256):
        raise ValueError('original solver: closed residual certificate source drift')


@dataclass(frozen=True)
class OriginalMagneticDomain:
    binding: source.owned.OperandBinding
    background: np.ndarray
    field_norm: float
    direction: np.ndarray
    quantity: str


def _validate_domain(domain, operands):
    if (type(domain) is not OriginalMagneticDomain or domain.binding != operands.binding
        or not source._vector(domain.background, 3) or not source._vector(domain.direction, 3)
        or not np.isfinite(domain.background).all() or not np.isfinite(domain.direction).all()
        or type(domain.field_norm) is not float or not np.isfinite(domain.field_norm) or domain.field_norm <= 0.
        or type(domain.quantity) is not str or domain.quantity not in ('secondary_enu_nT', 'linear_tmi_nT')
        or operands.sensitivity.shape[0] % 3
        or abs(float(np.linalg.norm(domain.direction))-1.) > 1e-12):
        raise ValueError('original magnetic domain: bound native original field/direction/linear quantity')
    if ((domain.quantity == 'secondary_enu_nT' and operands.projection is not None)
        or (domain.quantity == 'linear_tmi_nT' and (operands.projection is None
            or not np.array_equal(domain.direction, operands.projection)))):
        raise ValueError('original magnetic domain: original nested prediction quantity')


def magnetic_domain_check(domain, operands, q, qt, *, deadline):
    """Both original real affine endpoints retain strict ||B0+Gq||/F > 1e-8."""
    _validate_domain(domain, operands)
    ar = accuracy.original_row_arithmetic(34, deadline)
    minimum = None
    for model in (q, qt):
        raw = ar.matrix(operands.sensitivity, [ar.exact(v) for v in model])
        for i in range(0, len(raw), 3):
            ar.check()
            total = [ar.add(ar.exact(b), v) for b, v in zip(domain.background, raw[i:i+3])]
            square = Decimal(0)
            for lo, hi in total:
                lower = (Decimal(0) if lo <= 0 <= hi else
                    min(ar.lo.multiply(v, v) for v in (lo, hi)))
                square = ar.lo.add(square, lower)
            if square <= 0:
                return False, '0'
            norm_lower = ar.lo.next_minus(ar.lo.sqrt(square))
            ratio = ar.lo.divide(norm_lower, Decimal.from_float(domain.field_norm))
            minimum = ratio if minimum is None else min(minimum, ratio)
            if ratio <= Decimal.from_float(1e-8):
                return False, str(minimum)
    ar.check()
    return True, str(minimum)


class _OriginalObjective:
    def __init__(self, objective, budget):
        self.native, self.budget = objective, budget
        self.domain_checks = []
        self.original_source_sha256 = None
        for name in ('quadratic_operands', 'magnetic_domain', 'metric_operands'):
            if not callable(getattr(objective, name, None)):
                raise ValueError('original solver: complete closed physical source DTOs')

    def __getattr__(self, name):
        return getattr(self.native, name)

    def quadratic_operands(self, q):
        operands = self.native.quadratic_operands(q)
        source.validate(operands, self.identity(), q, deadline=self.budget.deadline,
            resource_limit_bytes=self.budget.resource_limit_bytes, admitted_bytes=self.budget.admitted_bytes)
        sha = accuracy._source_digest(operands)
        if self.original_source_sha256 is None:
            self.original_source_sha256 = sha
        elif self.original_source_sha256 != sha:
            raise ValueError('original solver: frozen original physical operand drift')
        return operands

    def certify(self, q, qt, gradient, phi, phit, iteration, trial, deadline):
        operands = self.quadratic_operands(q)
        if not source._vector(qt, len(q)) or not np.isfinite(qt).all():
            raise ValueError('original solver: actual finite native endpoint')
        domain = self.native.magnetic_domain(q)
        try:
            passed, ratio = magnetic_domain_check(domain, operands, q, qt, deadline=deadline)
        except source.intervals._Expired:
            record = source.intervals._record(iteration, trial, phi, phit)
            record['cause'] = 'wall_cap'
            return source.intervals._validate_record(record)
        self.domain_checks.append(dict(iteration=iteration, trial=trial,
            ratio_lower=ratio, passed=passed, model_sha256=source.owned.digest(q),
            trial_model_sha256=source.owned.digest(qt)))
        if not passed:
            record = source.intervals._record(iteration, trial, phi, phit)
            record['cause'] = 'range_unsupported'
            return source.intervals._validate_record(record)
        return source.certify_chord(operands, self.identity(), q, qt, gradient, phi, phit,
            iteration, trial, deadline=deadline, resource_limit_bytes=self.budget.resource_limit_bytes,
            admitted_bytes=self.budget.admitted_bytes)


class _Linear(reduced._Linear):
    def stronger_terminal(self):
        self.check()
        _check_residual_source()
        self.dispose_metric()
        started = monotonic()
        row = dict(iteration=int(self.iter), q=self.xc.copy(), seconds=0., check=None, failure=None)
        self.terminal_audits.append(row)
        owner = None
        try:
            q = reduced.core.linear._owned(self.xc)
            original = self.objective.quadratic_operands(q)
            domain = self.objective.magnetic_domain(q)
            source.validate(original, self.identity_value, q, deadline=self.budget.deadline,
                resource_limit_bytes=self.budget.resource_limit_bytes, admitted_bytes=self.budget.admitted_bytes)
            passed, ratio = magnetic_domain_check(domain, original, q, q, deadline=self.budget.deadline)
            if not passed:
                raise ValueError('original terminal: physical field direction domain')
            row['domain_ratio_lower'] = ratio
            # Retained native states, line-search scalar receipts and previous
            # terminal proofs coexist with the source owner. Count them here,
            # not by a caller-supplied terminal success/accounting callback.
            audits = self._audit_bytes + sum(s[0].nbytes+128 for s in self.states)
            audits += 2048*len(self.line_search_trials)+4096*len(self.objective.domain_checks)
            audits += (32768+1024*len(q))*len(self.terminal_audits)
            owner = residual_accuracy.OwnedOriginalResidualTerminal(self.objective.metric_operands(q),
                original, self.identity_value, q, self.g, float(self.initial_norm),
                deadline=self.budget.deadline, resource_limit_bytes=self.budget.resource_limit_bytes,
                admitted_bytes=self.budget.admitted_bytes, retained_audit_bytes=audits)
            row['check'] = owner.certify(self.terminal_policy)
            _check_residual_source()
            self.check()
            return row['check']['passed']
        except source.intervals._Expired:
            row['failure'] = 'wall_cap'
            self.fail('wall_cap')
        except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError) as error:
            row['failure'] = type(error).__name__+':'+str(error)[:160]
            self.fail('terminal_operands_failed')
        finally:
            if owner is not None:
                owner.close()
            row['seconds'] = monotonic()-started


def solve_bounded_linear(objective, lower_q, upper_q, start_q, *, budget, binding, terminal):
    """Trusted original magnetic DTO bridge only, not a general callback recipe."""
    _check_residual_source()
    proxy = _OriginalObjective(objective, budget)
    # First source/box binding before native initialization; no caller recipe
    # can certify a different box than the one whose native directions run.
    original = proxy.quadratic_operands(start_q)
    if not np.array_equal(original.lower, lower_q) or not np.array_equal(original.upper, upper_q):
        raise ValueError('original solver: exact original source/native bounds')
    _validate_domain(objective.magnetic_domain(start_q), original)
    original = None
    result = reduced.core._solve(proxy, lower_q, upper_q, start_q, budget=budget,
        binding=binding, terminal=terminal, mode='fixed_linear_quadratic', optimizer_class=_Linear,
        source_epoch=('physical_original_optimizer', SOURCE_SHA256, POLICY, LINEAR_EPOCH))
    result['magnetic_domain_checks'] = tuple(proxy.domain_checks)
    result['source_binding'].update(original_arithmetic=source.SOURCE_SHA256,
        original_terminal=accuracy.SOURCE_SHA256, original_residual_terminal=RESIDUAL_TERMINAL_SHA256,
        reduced_dependency=reduced.SOURCE_SHA256)
    return result
