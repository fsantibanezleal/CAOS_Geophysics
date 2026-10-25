"""Separate owned-Joseph source epochs, preserving actual native physical CG.

No historical export mutation, callback SPD/terminal approval, retry or copied
CG. Adapter source/physics/native admission and independent fit accuracy remain
separate obligations; a typed receipt does not grant online execution authority.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np
from scipy.sparse.linalg import LinearOperator
from simpeg import optimization

import physical_optimizer as linear
import physical_nonlinear_optimizer as nonlinear
import physical_owned_spd as spd


LINEAR_EPOCH = 'physical-gncg-linear-joseph-candidate-2'
NONLINEAR_EPOCH = 'physical-gncg-nonlinear-joseph-candidate-3'
POLICY = spd.POLICY
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
VENDOR_SOURCE_SHA256 = nonlinear.VENDOR_SOURCE_SHA256


@dataclass(frozen=True)
class ConditionedBinding:
    accepted_export: str
    optimizer_source_sha256: str
    metric_source_sha256: str
    numeric_kernel_source_sha256: str
    vendor_source_sha256: str
    certificate_source_sha256: str
    source_inventory_sha256: str
    runtime_epoch: str
    policy: str


@dataclass(frozen=True)
class ConditionedBudget:
    deadline: float
    remaining_steps: int
    resource_limit_bytes: int
    admitted_bytes: int
    allocation_plan_sha256: str


def _identity(objective, mode, expected_epoch=None):
    value = objective.identity()
    if type(value) is not dict or set(value) != linear._IDENTITY_KEYS:
        raise ValueError('conditioned: original exact13 physical identity')
    epoch = expected_epoch or (LINEAR_EPOCH if mode == 'fixed_linear_quadratic' else NONLINEAR_EPOCH)
    if value['mode'] != mode or value['runtime_epoch'] != epoch:
        raise ValueError('conditioned: explicit separate mode/source epoch')
    for name in ('objective_sha256', 'source_inventory_sha256', 'allocation_plan_sha256'):
        if not spd._hash(value[name]):
            raise ValueError('conditioned: original source/physics/allocation hashes')
    for name in ('parameter_count', 'observation_rows', 'observation_components'):
        if type(value[name]) is not int or value[name] <= 0:
            raise ValueError('conditioned: literal physical counts')
    if (value['parameter_count'] > 4096 or value['observation_rows'] > 2048
        or value['observation_components'] not in (1, 2, 3)
        or value['observation_rows']*value['observation_components'] > 2048
        or type(value['stage_index']) is not int or not 0 <= value['stage_index'] <= 25
        or not linear._finite(value['beta_engine'], positive=True)):
        raise ValueError('conditioned: original bounded physical counts/stage/beta')
    for name in ('q_unit', 'physical_unit'):
        if type(value[name]) is not str or not 1 <= len(value[name]) <= 96:
            raise ValueError('conditioned: literal physical unit')
    scale = value['physical_scale']
    scales = scale if type(scale) is tuple else (scale,)
    if len(scales) not in (1, 2) or any(not linear._finite(s, positive=True) for s in scales):
        raise ValueError('conditioned: original positive physical scale')
    return value.copy()


def _preflight(objective, lower, upper, start, budget, binding, terminal, mode, source_epoch=None):
    methods = ('identity', 'evaluate', 'components', 'binding_diagonal', 'metric_operands', 'release_state')
    if mode == 'fixed_linear_quadratic':
        methods += ('certify',)
    else:
        methods += ('exact_hessian',)
    if any(not callable(getattr(objective, name, None)) for name in methods):
        raise ValueError('conditioned: complete trusted ORIGINAL physical DTO adapter')
    # Only source-owned exports call this internal seam; no public recipe DTO.
    module, source, policy, expected_epoch = source_epoch or (
        'physical_conditioned_optimizer', SOURCE_SHA256, POLICY, None)
    identity = _identity(objective, mode, expected_epoch)
    epoch = identity['runtime_epoch']
    export = 'solve_bounded_linear' if mode == 'fixed_linear_quadratic' else 'solve_bounded_nonlinear'
    if (type(binding) is not ConditionedBinding or binding.accepted_export != module+'.'+export
        or binding.optimizer_source_sha256 != source or binding.metric_source_sha256 != spd.SOURCE_SHA256
        or binding.numeric_kernel_source_sha256 != spd.KERNEL_SHA256
        or binding.vendor_source_sha256 != VENDOR_SOURCE_SHA256 or not spd._hash(binding.certificate_source_sha256)
        or binding.source_inventory_sha256 != identity['source_inventory_sha256']
        or binding.runtime_epoch != epoch or binding.policy != policy):
        raise ValueError('conditioned: exact reviewed loaded binding required')
    cap = 200 if mode == 'fixed_linear_quadratic' else 250
    if (type(budget) is not ConditionedBudget or not linear._finite(budget.deadline)
        or type(budget.remaining_steps) is not int or not 0 <= budget.remaining_steps <= cap
        or type(budget.resource_limit_bytes) is not int or not 0 < budget.resource_limit_bytes <= 2*1024**3
        or type(budget.admitted_bytes) is not int or not 0 < budget.admitted_bytes <= budget.resource_limit_bytes
        or budget.allocation_plan_sha256 != identity['allocation_plan_sha256']):
        raise ValueError('conditioned: ORIGINAL source-bound resource/step/deadline budget')
    a = identity['parameter_count']
    if any(not linear._array(v, a) for v in (lower, upper, start)) or (
        np.any(lower >= upper) or np.any(start < lower) or np.any(start > upper)):
        raise ValueError('conditioned: original finite native box/start, no projection')
    bounds = spd.validate_terminal(terminal)
    if bounds and (mode != 'fixed_linear_quadratic' or not callable(getattr(objective, 'quadratic_operands', None))):
        raise ValueError('conditioned: ORIGINAL quadratic factors required; no GN global bound')
    # Absolute caller lower deadline remains binding. No finish/restart clock.
    seconds = 120. if mode == 'fixed_linear_quadratic' else 1800.
    budget = ConditionedBudget(min(budget.deadline, monotonic()+seconds), budget.remaining_steps,
        budget.resource_limit_bytes, budget.admitted_bytes, budget.allocation_plan_sha256)
    return identity, budget


class _Conditioning:
    def prepare_owned(self, terminal, mode, source_epoch=None):
        self.terminal_policy, self.mode = terminal, mode
        self.owned_metric = None
        self.conditioning_attempts, self.terminal_audits = [], []
        self.line_search_trials = []
        self.source_epoch = source_epoch or ('physical_conditioned_optimizer', SOURCE_SHA256, POLICY, None)

    def check_identity(self):
        try:
            current = _identity(self.objective, self.mode, self.source_epoch[3])
        except (ValueError, TypeError, KeyError):
            self.fail('state_mismatch')
        if current != self.identity_value:
            self.fail('state_mismatch')

    def check(self):
        if monotonic() > self.budget.deadline:
            self.fail('wall_cap')
        self.check_identity()

    def dispose_metric(self):
        self.approxHinv = None
        if self.owned_metric is not None:
            self.owned_metric.close()
        self.owned_metric = None

    def stronger_terminal(self):
        self.check()
        started = monotonic()
        row = dict(iteration=int(self.iter), q=self.xc.copy(), seconds=0., check=None, failure=None)
        self.terminal_audits.append(row)
        try:
            operands = self.objective.metric_operands(linear._owned(self.xc))
            allocation = spd.validate_operands(operands, self.identity_value, self.xc, self.budget.resource_limit_bytes)
            if allocation['maximum'] > self.budget.admitted_bytes:
                raise ValueError('conditioned: source plan omits owned metric phases')
            bounds = spd.validate_terminal(self.terminal_policy)
            quadratic = self.objective.quadratic_operands(linear._owned(self.xc)) if bounds else None
            row['check'] = spd.terminal_check(self.terminal_policy, self.xc, self.g, self.lower, self.upper,
                self.initial_norm, identity=self.identity_value, deadline=self.budget.deadline,
                quadratic=quadratic, source_components=operands.source_components)
            self.check()
            return row['check']['passed']
        except spd.intervals._Expired:
            row['failure'] = 'wall_cap'
            self.fail('wall_cap')
        except (ValueError, TypeError, KeyError, ArithmeticError) as error:
            row['failure'] = type(error).__name__+':'+str(error)[:160]
            self.fail('terminal_operands_failed')
        finally:
            row['seconds'] = monotonic()-started

    def stoppingCriteria(self, inLS=False):
        if inLS:
            chord = self._LS_xt-self.xc
            phi_trial = float(self._LS_ft)
            slope = float(np.inner(self.g, chord))
            # Scalar-only history; direction/q/g already retained once/step.
            row = dict(iteration=int(self.iter), trial=int(self.iterLS), alpha=float(self._LS_t),
                phi_current=float(self.f), phi_trial=phi_trial if np.isfinite(phi_trial) else None,
                projected_slope=slope if np.isfinite(slope) else None,
                trial_model_sha256=spd.digest(self._LS_xt), accepted=False)
            limit = (self.budget.remaining_steps+1)*(20 if self.mode == 'fixed_linear_quadratic' else 30)
            if len(self.line_search_trials) >= limit:
                self.fail('state_mismatch')
            self.line_search_trials.append(row)
            answer = super().stoppingCriteria(True)
            row['accepted'] = bool(answer)
            return answer
        answer = super().stoppingCriteria(False)
        if inLS or not answer or self.reason not in ('absolute_stationary', 'kkt_stable', 'kkt'):
            return answer
        if self.stronger_terminal():
            return True
        self.reason = None
        if self.iter >= self.budget.remaining_steps:
            self.reason = 'terminal_precision_cap'
            return True
        # Original terminal rejected: continue SAME native minimize, no reset of
        # state/normalization/history/deadline or extra accepted-step allowance.
        active, binding = self.activeSet(self.xc), self.bindingSet(self.xc)
        self.release_next = bool(np.any(active & ~binding))
        self.initial_residual = float(np.linalg.norm((~active)*self.g))
        self.active_count, self.binding_count = int(active.sum()), int(binding.sum())
        if self.initial_residual == 0. and not self.release_next:
            self.reason = 'terminal_precision_stalled'
            return True
        return False

    def findSearchDirection(self):
        self.check()
        a = self.identity_value['parameter_count']
        diagonal = self.objective.binding_diagonal(linear._owned(self.xc))
        self.check()
        if not linear._array(diagonal, a) or np.any(diagonal <= 0.):
            self.fail('nonfinite')
        if self.diagonal is None:
            self.diagonal = diagonal.copy()
        elif not np.array_equal(diagonal, self.diagonal):
            self.fail('state_mismatch')
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            inverse = 1./self.diagonal
        if not np.isfinite(inverse).all() or np.any(inverse <= 0.):
            self.fail('nonfinite')
        self.dispose_metric()  # BEFORE next factor/source DTO, not after setup.
        self.cg_count, self.cg_abs_resid, self.cg_rel_resid = 0, None, None
        active = self.activeSet(self.xc)
        free = np.flatnonzero(~active).astype(np.int64)
        started = monotonic()
        row = dict(iteration=int(self.iter), q=self.xc.copy(), free_indices=free.copy(), branch='pg' if self.release_next else 'cg',
            gradient=self.g.copy(), direction=None, iterations=0, true_absolute_residual=None,
            true_relative_residual=None, rhs_norm=self.initial_residual, seconds=0.,
            setup_seconds=0., metric_actions=0, metric_action_seconds=0., payload_bytes=0,
            operand_sha256=None, face_sha256=None, allocation=None, failure=None)
        self.conditioning_attempts.append(row)
        setup_started = None
        try:
            if self.release_next:
                self.branch = 0
                direction = self.projection(self.xc-inverse*self.g)-self.xc
            else:
                self.branch = 1
                operands = self.objective.metric_operands(linear._owned(self.xc))
                self.check()
                allocation = spd.validate_operands(operands, self.identity_value, self.xc, self.budget.resource_limit_bytes)
                if allocation['maximum'] > self.budget.admitted_bytes:
                    raise ValueError('conditioned: source plan omits owned metric phases')
                setup_started = monotonic()
                self.owned_metric = spd.OwnedMetric(operands, self.identity_value, self.xc, free,
                                                   self.budget.deadline, self.budget.resource_limit_bytes)
                row.update(setup_seconds=self.owned_metric.setup_seconds, allocation=self.owned_metric.allocation.copy(),
                    operand_sha256=self.owned_metric.operand_sha256, face_sha256=self.owned_metric.face_sha256,
                    payload_bytes=self.owned_metric.live_payload_bytes)
                operands = None
                def action(v):
                    self.check()
                    result = self.owned_metric.apply(v)
                    self.check()
                    return result
                self.approxHinv = LinearOperator((a, a), matvec=action, dtype=np.float64)
                # Actual installed vendor loop, no copied CG/SciPy retry/oracle.
                direction = optimization.ProjectedGNCG.findSearchDirection(self)
                row['direction'] = direction.copy()
                if not linear._array(direction, a) or np.any(direction[active] != 0.):
                    self.fail('state_mismatch')
                residual = (~active)*(-self.g-self.H@direction)
                if not linear._array(residual, a):
                    self.fail('nonfinite')
                actual = float(np.linalg.norm(residual))
                self.cg_abs_resid, self.cg_rel_resid = actual, actual/self.initial_residual
                row.update(true_absolute_residual=actual, true_relative_residual=self.cg_rel_resid)
                self.check()
                cap = 200 if self.mode == 'fixed_linear_quadratic' else 512
                if not np.isfinite(self.cg_rel_resid):
                    self.fail('nonfinite')
                if self.cg_count > cap or actual > 1e-6*self.initial_residual:
                    self.fail('cg_cap')
            row['direction'] = direction.copy()
            slope = float(np.inner(self.g, direction))
            if not linear._array(direction, a) or not np.isfinite(slope):
                self.fail('nonfinite')
            if not np.any(direction) or slope >= 0.:
                self.fail('zero_free_direction')
            return direction
        except spd.kernel.DeadlineExceeded:
            row['failure'] = 'wall_cap'
            self.fail('wall_cap')
        except (linear._Failure, nonlinear._Failure):
            row['failure'] = self.reason
            raise
        except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError) as error:
            row['failure'] = type(error).__name__+':'+str(error)[:160]
            self.fail('metric_construction_failed')
        finally:
            if setup_started is not None and self.owned_metric is None:
                row['setup_seconds'] = monotonic()-setup_started
            row.update(iterations=int(self.cg_count), seconds=monotonic()-started)
            if self.owned_metric is not None:
                row.update(metric_actions=self.owned_metric.actions,
                           metric_action_seconds=self.owned_metric.action_seconds)
            self.dispose_metric()


class _Linear(_Conditioning, linear._NativeRecorded):
    pass


class _Nonlinear(_Conditioning, nonlinear._NativeRecorded):
    pass


def _solve(objective, lower, upper, start, *, budget, binding, terminal, mode, source_epoch=None, optimizer_class=None):
    identity, budget = _preflight(objective, lower, upper, start, budget, binding, terminal, mode, source_epoch)
    cls = optimizer_class or (_Linear if mode == 'fixed_linear_quadratic' else _Nonlinear)
    opt = cls(objective, identity, lower, upper, budget)
    opt.prepare_owned(terminal, mode, source_epoch)
    try:
        opt.check()
        q = opt.minimize(opt.evaluate, start.copy())
        if not opt.states or not np.array_equal(q, opt.states[-1][0]):
            opt.fail('state_mismatch')
        phi, _ = opt.evaluate(q, True, False)
        opt.components(q, phi)
        if phi != opt.states[-1][3]:
            opt.fail('state_mismatch')
    except (linear._Failure, nonlinear._Failure):
        pass
    except ArithmeticError:
        opt.reason = 'nonfinite'
    except (ValueError, RuntimeError, KeyError, TypeError):
        opt.reason = 'engine_error'
    finally:
        opt.dispose_metric()
        try:
            objective.release_state()
        except (ValueError, RuntimeError, KeyError, TypeError, ArithmeticError):
            opt.reason = 'engine_error'
    reason = opt.reason or 'state_mismatch'
    a = identity['parameter_count']
    result = (linear._result(opt.states, a, reason, opt.cg_counts, opt.ls_counts) if mode == 'fixed_linear_quadratic'
              else nonlinear._result(opt.states, opt.steps, a, reason))
    result.update(runtime_epoch=identity['runtime_epoch'], policy=opt.source_epoch[2],
        conditioning_attempts=tuple(opt.conditioning_attempts), terminal_audits=tuple(opt.terminal_audits),
        line_search_trials=tuple(opt.line_search_trials),
        source_binding=dict(optimizer=opt.source_epoch[1], metric=spd.SOURCE_SHA256, numeric_kernel=spd.KERNEL_SHA256,
                            vendor=VENDOR_SOURCE_SHA256, original_linear=linear.SOURCE_SHA256,
                            original_nonlinear=nonlinear.SOURCE_SHA256))
    if source_epoch is not None:
        result['source_binding']['conditioned_dependency'] = SOURCE_SHA256
        result['ray_initializations'] = tuple(opt.ray_initializations)
    if result['status'] != 'converged' and opt.line_search_trials:
        result['failed_trial'].update(last_actual_line_search=opt.line_search_trials[-1].copy(),
            model_q=linear._owned(opt._LS_xt),
            best_observed_phi=min(r['phi_trial'] for r in opt.line_search_trials if r['phi_trial'] is not None))
    return result


def solve_bounded_linear(objective, lower_q, upper_q, start_q, *, budget, binding, terminal):
    return _solve(objective, lower_q, upper_q, start_q, budget=budget, binding=binding, terminal=terminal,
                  mode='fixed_linear_quadratic')


def solve_bounded_nonlinear(objective, lower_q, upper_q, start_q, *, budget, binding, terminal):
    return _solve(objective, lower_q, upper_q, start_q, budget=budget, binding=binding, terminal=terminal,
                  mode='nonlinear_gauss_newton')
