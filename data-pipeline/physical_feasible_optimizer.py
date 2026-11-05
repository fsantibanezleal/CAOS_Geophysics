"""Source-owned initial feasible ray, not failed-search rescue or private CG."""
from fractions import Fraction
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np

import physical_conditioned_optimizer as core


LINEAR_EPOCH = 'physical-gncg-linear-joseph-contact-candidate-4'
POLICY = 'closed-firstorder-joseph-contact-native-true-residual-terminal-1'
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
VENDOR_SOURCE_SHA256 = core.VENDOR_SOURCE_SHA256
ConditionedBinding = core.ConditionedBinding
ConditionedBudget = core.ConditionedBudget


def initial_ray(q, p, gradient, lower, upper, *, pg, deadline):
    """Exact stored-real ratios, contact-rounded once, no floor/snap/extra trial."""
    if type(pg) is not bool or not core.linear._finite(deadline):
        raise ValueError('ray: literal branch/deadline')
    if type(q) is not np.ndarray or q.ndim != 1 or not 1 <= len(q) <= 4096:
        raise ValueError('ray: bounded native model')
    if any(not core.linear._array(v, len(q)) for v in (q, p, gradient, lower, upper)):
        raise ValueError('ray: finite native original operands')
    if np.any(lower >= upper) or np.any(q < lower) or np.any(q > upper):
        raise ValueError('ray: original feasible box/model')
    slope = float(np.inner(gradient, p))
    if not np.any(p) or not np.isfinite(slope) or slope >= 0.:
        raise ValueError('ray: actual native descent required')
    if monotonic() > deadline:
        raise core.spd.kernel.DeadlineExceeded('ray clock')
    if pg:
        # The source-owned PG branch already produced its original feasible
        # full diagonal chord before any metric/CG, not a failed-CG fallback.
        return 1., -1
    active = (q == lower) | (q == upper)
    if np.any(p[active] != 0.):
        raise ValueError('ray: nonzero active CG direction')
    best, coordinate = Fraction(1), -1
    for i in range(len(q)):
        if monotonic() > deadline:
            raise core.spd.kernel.DeadlineExceeded('ray clock')
        if p[i] == 0.:
            continue
        bound = upper[i] if p[i] > 0. else lower[i]
        ratio = (Fraction(float(bound))-Fraction(float(q[i])))/Fraction(float(p[i]))
        if ratio <= 0:
            raise ValueError('ray: nonpositive exact first-bound ratio')
        if ratio < best:
            best, coordinate = ratio, i
    alpha = float(best)
    if Fraction(alpha) < best:
        alpha = float(np.nextafter(alpha, np.inf))
    if not np.isfinite(alpha) or not 0. < alpha <= 1.:
        raise ValueError('ray: no positive representable initial step')
    return alpha, coordinate


class _Linear(core._Linear):
    def prepare_owned(self, terminal, mode, source_epoch=None):
        super().prepare_owned(terminal, mode, source_epoch)
        self.ray_initializations = []

    def modifySearchDirection(self, p):
        self.check()
        row = dict(iteration=int(self.iter), branch='pg' if self.release_next else 'cg',
            model_sha256=core.spd.digest(self.xc), direction_sha256=core.spd.digest(p),
            alpha0=None, coordinate=None, seconds=0., failure=None)
        self.ray_initializations.append(row)
        started = monotonic()
        try:
            alpha, coordinate = initial_ray(self.xc, p, self.g, self.lower, self.upper,
                pg=bool(self.release_next), deadline=self.budget.deadline)
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
        # Native loop, projection and actual ORIGINAL certificate unchanged.
        # Native vendor t is now the multiplier of this source-owned proposal.
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
    return core._solve(objective, lower_q, upper_q, start_q, budget=budget, binding=binding,
        terminal=terminal, mode='fixed_linear_quadratic', optimizer_class=_Linear,
        source_epoch=('physical_feasible_optimizer', SOURCE_SHA256, POLICY, LINEAR_EPOCH))
