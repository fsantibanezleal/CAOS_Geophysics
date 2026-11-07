"""Closed linear working-face epoch; actual installed physical native CG.

No caller mask/SPD, copied CG, failed-solve fallback or historical upgrade.
Each successful refinement shares the ORIGINAL direction's 200-CG allowance.
"""
from fractions import Fraction
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np

import physical_conditioned_optimizer as core


LINEAR_EPOCH = 'physical-gncg-linear-reduced-joseph-candidate-5'
POLICY = 'closed-reduced-firstorder-joseph-native-true-residual-terminal-1'
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
VENDOR_SOURCE_SHA256 = core.VENDOR_SOURCE_SHA256
ConditionedBinding = core.ConditionedBinding
ConditionedBudget = core.ConditionedBudget
WORKSPACE_BYTES = 8*1024**2
PHASE_METADATA_BYTES = 8192
PHASE_LIMIT = 512


def initial_ray(q, p, gradient, lower, upper, *, deadline):
    """Inward released bounds are free; outward exact-bound motion refuses."""
    if not core.linear._finite(deadline):
        raise ValueError('reduced ray: literal deadline')
    if type(q) is not np.ndarray or q.ndim != 1 or not 1 <= len(q) <= 4096:
        raise ValueError('reduced ray: bounded native model')
    if any(not core.linear._array(v, len(q)) for v in (q, p, gradient, lower, upper)):
        raise ValueError('reduced ray: finite original operands')
    if np.any(lower >= upper) or np.any(q < lower) or np.any(q > upper):
        raise ValueError('reduced ray: original feasible box/model')
    slope = float(np.inner(gradient, p))
    if not np.any(p) or not np.isfinite(slope) or slope >= 0.:
        raise ValueError('reduced ray: actual descent required')
    if np.any(((q == lower) & (p < 0.)) | ((q == upper) & (p > 0.))):
        raise ValueError('reduced ray: outward bound direction')
    best, coordinate = Fraction(1), -1
    for i in range(len(q)):
        if monotonic() > deadline:
            raise core.spd.kernel.DeadlineExceeded('reduced ray clock')
        if p[i] == 0.:
            continue
        bound = upper[i] if p[i] > 0. else lower[i]
        ratio = (Fraction(float(bound))-Fraction(float(q[i])))/Fraction(float(p[i]))
        if ratio <= 0:
            raise ValueError('reduced ray: nonpositive exact first-bound ratio')
        if ratio < best:
            best, coordinate = ratio, i
    alpha = float(best)
    if Fraction(alpha) < best:
        alpha = float(np.nextafter(alpha, np.inf))
    if not np.isfinite(alpha) or not 0. < alpha <= 1.:
        raise ValueError('reduced ray: unrepresentable first-bound step')
    return alpha, coordinate


class _Linear(core._Linear):
    def prepare_owned(self, terminal, mode, source_epoch=None):
        super().prepare_owned(terminal, mode, source_epoch)
        self.ray_initializations = []
        self._working = None
        self._audit_bytes = 0
        self._base_bytes = 0
        self._resource_peak = 0
        # BEFORE any native direction. The vendor active gradient add-on would
        # violate a refined working face; this is not a patched/copied loop.
        self.step_active_set = False

    def activeSet(self, q):
        if self._working is not None:
            return self._working.copy()
        return self.bindingSet(q)

    def _admit_phase(self, phase):
        self.check()
        a = self.identity_value['parameter_count']
        try:
            operands = self.objective.metric_operands(core.linear._owned(self.xc))
            self.check()
            allocation = core.spd.validate_operands(operands, self.identity_value,
                self.xc, self.budget.resource_limit_bytes)
            operands = None
        except core.linear._Failure:
            raise
        except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError) as error:
            self.conditioning_attempts.append(dict(iteration=int(self.iter),
                phase=int(phase), branch='admission_refusal',
                failure=type(error).__name__+':'+str(error)[:160], iterations=0,
                cumulative_CG=int(self.cg_count)))
            self.fail('metric_construction_failed')
        self._base_bytes = max(self._base_bytes, allocation['maximum'])
        phase_bytes = 8*a+PHASE_METADATA_BYTES+(16*a if phase == 0 else 0)
        # Reserve the prospective new index delta BEFORE its allocation.
        prospective = self._base_bytes+WORKSPACE_BYTES+self._audit_bytes+phase_bytes+8*a
        if (len(self.conditioning_attempts) >= PHASE_LIMIT
            or prospective > self.budget.admitted_bytes
            or prospective > self.budget.resource_limit_bytes):
            # Small failure receipt, no new vector/native phase on refusal.
            self.conditioning_attempts.append(dict(iteration=int(self.iter),
                phase=int(phase), branch='admission_refusal', failure='resource_cap',
                iterations=0, cumulative_CG=int(self.cg_count),
                resource=dict(base_bytes=self._base_bytes, workspace_bytes=WORKSPACE_BYTES,
                    retained_audit_bytes=self._audit_bytes, prospective_bytes=prospective,
                    admitted_bytes=self.budget.admitted_bytes, phase_limit=PHASE_LIMIT)))
            self.fail('resource_cap')
        self._resource_peak = max(self._resource_peak, prospective)
        return phase_bytes

    def findSearchDirection(self):
        self.check()
        a = self.identity_value['parameter_count']
        self._working = self.bindingSet(self.xc).copy()
        self.release_next = False
        used, phase = 0, 0
        delta = np.empty(0, dtype=np.int64)
        try:
            while True:
                self.check()
                self.initial_residual = float(np.linalg.norm((~self._working)*self.g))
                if not np.isfinite(self.initial_residual):
                    self.fail('nonfinite')
                if self.initial_residual == 0.:
                    self.fail('zero_free_direction')
                if used >= 200:
                    self.fail('cg_cap')
                self.cg_maxiter = 200-used
                self.cg_count = used
                phase_started = monotonic()
                phase_bytes = self._admit_phase(phase)
                preflight_seconds = monotonic()-phase_started
                before = len(self.conditioning_attempts)
                try:
                    p = super().findSearchDirection()
                finally:
                    if len(self.conditioning_attempts) > before:
                        row = self.conditioning_attempts[-1]
                        used += row['iterations']
                        self._audit_bytes += phase_bytes+8*len(delta)
                        row.update(phase=phase, cumulative_CG=used,
                            cg_remaining=200-used, frozen_delta=delta.copy(),
                            preflight_seconds=preflight_seconds,
                            total_phase_seconds=monotonic()-phase_started,
                            working_mask_sha256=core.spd.digest(self._working),
                            resource=dict(base_bytes=self._base_bytes, workspace_bytes=WORKSPACE_BYTES,
                                retained_audit_bytes=self._audit_bytes,
                                prospective_peak_bytes=self._resource_peak,
                                admitted_bytes=self.budget.admitted_bytes, phase_limit=PHASE_LIMIT))
                        # q/g once per original direction; reconstruct free sets
                        # from native binding(q,g) plus the successive deltas.
                        row.pop('free_indices')
                        if phase:
                            row.pop('q')
                            row.pop('gradient')
                self.cg_count = used
                if used > 200:
                    self.fail('cg_cap')
                outward = ((self.xc == self.lower) & (p < 0.)) | ((self.xc == self.upper) & (p > 0.))
                if not np.any(outward):
                    return p
                if np.any(self._working & outward):
                    self.fail('state_mismatch')
                delta = np.flatnonzero(outward).astype(np.int64)
                self._working |= outward
                phase += 1
                if phase > a:
                    self.fail('state_mismatch')
        finally:
            self._working = None
            self.cg_count = used
            self.cg_maxiter = 200
            self.dispose_metric()

    def modifySearchDirection(self, p):
        self.check()
        row = dict(iteration=int(self.iter), branch='reduced_cg',
            model_sha256=core.spd.digest(self.xc), direction_sha256=core.spd.digest(p),
            alpha0=None, coordinate=None, seconds=0., failure=None)
        self.ray_initializations.append(row)
        started = monotonic()
        try:
            alpha, coordinate = initial_ray(self.xc, p, self.g, self.lower, self.upper,
                deadline=self.budget.deadline)
            row.update(alpha0=alpha, coordinate=coordinate)
            self.check()
        except core.spd.kernel.DeadlineExceeded:
            row['failure'] = 'wall_cap'
            self.fail('wall_cap')
        except (ValueError, ArithmeticError) as error:
            row['failure'] = str(error)[:160]
            self.fail('ray_initialization_failed')
        finally:
            row['seconds'] = monotonic()-started
        with np.errstate(over='raise', invalid='raise', under='ignore'):
            scaled = alpha*p
        if not core.linear._array(scaled, len(p)) or not np.any(scaled):
            row['failure'] = 'unrepresentable_scaled_direction'
            self.fail('ray_initialization_failed')
        return super().modifySearchDirection(scaled)

    def stoppingCriteria(self, inLS=False):
        answer = super().stoppingCriteria(inLS)
        if inLS:
            row = self.line_search_trials[-1]
            row['ray_alpha0'] = self.ray_initializations[-1]['alpha0']
            row['effective_alpha'] = row['ray_alpha0']*row['alpha']
        return answer


def solve_bounded_linear(objective, lower_q, upper_q, start_q, *, budget, binding, terminal):
    return core._solve(objective, lower_q, upper_q, start_q, budget=budget,
        binding=binding, terminal=terminal, mode='fixed_linear_quadratic',
        optimizer_class=_Linear, source_epoch=(
            'physical_reduced_optimizer', SOURCE_SHA256, POLICY, LINEAR_EPOCH))
