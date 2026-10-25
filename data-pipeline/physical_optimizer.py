"""Source-bound trusted linear objectives composed with native ProjectedGNCG.

This is not an upload callback, driver admission, nonlinear solver, or scientific
acceptance registry. Separately reviewed adapters own physics, sealed operands,
source inventories, allocation proofs and the actual directed certificate.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from time import monotonic
from typing import Protocol

import numpy as np
from scipy.sparse.linalg import LinearOperator
from simpeg import optimization

import gravity_l2_precision as certificate_contract


RUNTIME_EPOCH = 'physical-gncg-linear-candidate-1'
POLICY = 'projected-gncg-binding-release-certified-delta-1'
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_DIGEST = re.compile('[0-9a-f]{64}\\Z', re.ASCII)
_IDENTITY_KEYS = {'mode','runtime_epoch','objective_sha256','source_inventory_sha256',
    'q_unit','physical_unit','physical_scale','parameter_count','observation_rows',
    'observation_components','beta_engine','stage_index','allocation_plan_sha256'}


@dataclass(frozen=True)
class OptimizerBinding:
    accepted_export: str
    optimizer_source_sha256: str
    certificate_source_sha256: str
    source_inventory_sha256: str
    runtime_epoch: str
    policy: str


@dataclass(frozen=True)
class OptimizerBudget:
    deadline: float
    remaining_steps: int
    resource_limit_bytes: int
    admitted_bytes: int
    allocation_plan_sha256: str


class PhysicalObjective(Protocol):
    def identity(self) -> dict: ...
    def evaluate(self, q, return_g=False, return_H=False): ...
    def components(self, q) -> dict: ...
    def binding_diagonal(self, q): ...
    def free_metric(self, q, free_indices) -> LinearOperator: ...
    def certify(self, q, qt, native_gradient, native_phi, native_phi_trial,
                iteration, trial, deadline) -> dict: ...
    def release_state(self): ...


class _Failure(RuntimeError):
    pass


def _digest(value):
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def _finite(value, *, positive=False):
    return type(value) is float and np.isfinite(value) and (not positive or value>0.)


def _array(value, a):
    return (type(value) is np.ndarray and value.dtype==np.float64 and value.shape==(a,)
            and np.isfinite(value).all())


def _owned(value):
    result=value.copy()
    result.flags.writeable=False
    return result


def _identity(objective):
    value=objective.identity()
    if type(value) is not dict or set(value)!=_IDENTITY_KEYS:
        raise ValueError('optimizer: exact13 identity keys required')
    for key in ('objective_sha256','source_inventory_sha256','allocation_plan_sha256'):
        if not _digest(value[key]): raise ValueError('optimizer: source identity digest')
    for key in ('runtime_epoch','q_unit','physical_unit'):
        if type(value[key]) is not str or not 1<=len(value[key])<=96:
            raise ValueError('optimizer: registered identity strings required')
    for key in ('physical_scale','beta_engine'):
        if not _finite(value[key],positive=True): raise ValueError('optimizer: positive native scalar')
    for key in ('parameter_count','observation_rows','observation_components'):
        if type(value[key]) is not int or value[key]<=0:
            raise ValueError('optimizer: positive native count')
    if type(value['stage_index']) is not int or not 0<=value['stage_index']<=20:
        raise ValueError('optimizer: stage index')
    if value['mode'] not in ('fixed_linear_quadratic','nonlinear_gauss_newton'):
        raise ValueError('optimizer: declared objective mode')
    return value.copy()


def _preflight(objective, lower, upper, start, budget, binding):
    if any(not callable(getattr(objective,key,None)) for key in (
        'identity','evaluate','components','binding_diagonal','free_metric','certify','release_state')):
        raise ValueError('optimizer: complete trusted seven-method objective required')
    identity=_identity(objective)
    if type(binding) is not OptimizerBinding or (
        binding.accepted_export!='physical_optimizer.solve_bounded_physical'
        or binding.optimizer_source_sha256!=SOURCE_SHA256
        or binding.runtime_epoch!=RUNTIME_EPOCH or identity['runtime_epoch']!=RUNTIME_EPOCH
        or binding.policy!=POLICY
        or binding.source_inventory_sha256!=identity['source_inventory_sha256']
        or not _digest(binding.certificate_source_sha256)):
        raise ValueError('optimizer: reviewed loaded source/binding required')
    # This checks the trusted driver's declared receipt, not actual memory or a
    # registered source inventory. Those proofs remain adapter/owner obligations.
    if type(budget) is not OptimizerBudget or (
        not _finite(budget.deadline)
        or type(budget.remaining_steps) is not int or not 0<=budget.remaining_steps<=200
        or type(budget.resource_limit_bytes) is not int or not 0<budget.resource_limit_bytes<=2*1024**3
        or type(budget.admitted_bytes) is not int or not 0<budget.admitted_bytes<=budget.resource_limit_bytes
        or budget.allocation_plan_sha256!=identity['allocation_plan_sha256']):
        raise ValueError('optimizer: bounded source-bound admission required')
    a=identity['parameter_count']
    if any(not _array(v,a) for v in (lower,upper,start)) or (
        np.any(lower>=upper) or np.any(start<lower) or np.any(start>upper)):
        raise ValueError('optimizer: finite native box/start vectors required, no projection')
    return identity


def _projected(q, gradient, lower, upper):
    tolerance=32*np.finfo(np.float64).eps*np.maximum.reduce(
        [np.ones_like(q),np.abs(q),np.abs(lower),np.abs(upper)])
    result=gradient.copy()
    result[(q<=lower+tolerance)&(gradient>0.)]=0.
    result[(q>=upper-tolerance)&(gradient<0.)]=0.
    return result


class _NativeRecorded(optimization.ProjectedGNCG):
    """ONE native minimize recipe; no copied CG or inverse-constructor dependency."""
    def __init__(self, objective, identity, lower, upper, budget):
        super().__init__(lower=lower.copy(),upper=upper.copy(),maxIter=budget.remaining_steps,
            maxIterLS=20,cg_maxiter=200,cg_rtol=1e-6,cg_atol=0.,step_active_set=True,
            active_set_grad_scale=.01,LSreduction=1e-4,LSshorten=.5,
            use_WolfeCurvature=False,require_decrease=True,maxStep=np.inf)
        self.objective,self.identity_value,self.budget=objective,identity,budget
        self.states,self.cg_counts,self.ls_counts=[],[],[]
        self.reason,self.initial_norm,self.diagonal=None,None,None
        self.pending_state=None
        self.release_next=False
        self.cg_count,self.cg_abs_resid,self.cg_rel_resid=0,None,None

    def fail(self,reason):
        self.reason=reason
        raise _Failure(reason)

    def check_identity(self):
        try: current=_identity(self.objective)
        except (ValueError,TypeError,KeyError): self.fail('state_mismatch')
        if current!=self.identity_value: self.fail('state_mismatch')

    def check_time(self):
        if monotonic()>self.budget.deadline: self.fail('wall_cap')

    def evaluate(self,q,return_g=False,return_H=False):
        self.check_time()
        self.check_identity()
        a=self.identity_value['parameter_count']
        if not _array(q,a): self.fail('nonfinite')
        if np.any(q<self.lower) or np.any(q>self.upper): self.fail('state_mismatch')
        value=self.objective.evaluate(_owned(q),return_g,return_H)
        self.check_identity()
        self.check_time()
        count=1+int(return_g)+int(return_H)
        if count==1:
            if not _finite(value): self.fail('nonfinite')
            return value
        if type(value) is not tuple or len(value)!=count: self.fail('state_mismatch')
        if not _finite(value[0]): self.fail('nonfinite')
        if return_g and not _array(value[1],a): self.fail('nonfinite')
        if return_H and (not isinstance(value[-1],LinearOperator) or value[-1].shape!=(a,a)
                         or value[-1].dtype!=np.dtype(np.float64)):
            self.fail('state_mismatch')
        return value

    def components(self,q,phi):
        self.check_identity()
        values=self.objective.components(_owned(q))
        self.check_identity()
        if type(values) is not dict or set(values)!={'phi_d','phi_m','phi_engine'}:
            self.fail('state_mismatch')
        if any(not _finite(v) or v<0. for v in values.values()): self.fail('nonfinite')
        if values['phi_engine']!=phi or values['phi_d']+self.identity_value['beta_engine']*values['phi_m']!=phi:
            self.fail('state_mismatch')
        return values

    def stoppingCriteria(self,inLS=False):
        if inLS:
            self.check_time()
            self.check_identity()
            if not _array(self._LS_xt,self.identity_value['parameter_count']) or not _finite(float(self._LS_ft)):
                self.fail('nonfinite')
            chord=self._LS_xt-self.xc
            slope=float(np.inner(self.g,chord))
            if not np.isfinite(chord).all() or not np.isfinite(slope): self.fail('nonfinite')
            if not np.any(chord): self.fail('zero_free_direction')
            if slope>=0.: return False
            try:
                record=self.objective.certify(_owned(self.xc),_owned(self._LS_xt),_owned(self.g),
                    float(self.f),float(self._LS_ft),int(self.iter),int(self.iterLS),self.budget.deadline)
                certificate_contract._validate_record(record)
            except (ValueError,KeyError,TypeError): self.fail('state_mismatch')
            self.check_identity()
            self.check_time()
            if (record['iteration']!=int(self.iter) or record['trial']!=int(self.iterLS)
                or record['native_phi_current']!=float(self.f)
                or record['native_phi_trial']!=float(self._LS_ft)
                or record['displacement_inf_q']!=float(np.max(np.abs(chord)))):
                self.fail('state_mismatch')
            if record['cause']=='wall_cap': self.fail('wall_cap')
            if record['decision']!='certified_accept': return False
            # Capture the real trial gradient/components BEFORE acceptance. If
            # the next Hessian evaluation reaches the clock cap, the already
            # accepted native state/step must not disappear from the ledger.
            phi,gradient=self.evaluate(self._LS_xt,True,False)
            values=self.components(self._LS_xt,phi)
            if phi!=float(self._LS_ft): self.fail('state_mismatch')
            kkt=float(np.linalg.norm(_projected(self._LS_xt,gradient,self.lower,self.upper),
                                     ord=np.inf))/self.initial_norm
            self.check_time()
            self.pending_state=(self._LS_xt.copy(),values['phi_d'],values['phi_m'],phi,kkt)
            return True
        self.check_time()
        self.check_identity()
        components=self.components(self.xc,float(self.f))
        if len(self.states) not in (self.iter,self.iter+1) or len(self.states)>201:
            self.fail('state_mismatch')
        if self.initial_norm is None:
            self.initial_norm=max(1.,float(np.linalg.norm(self.g,ord=np.inf)))
            self.f0=float(self.f)
        absolute=float(np.linalg.norm(_projected(self.xc,self.g,self.lower,self.upper),ord=np.inf))
        kkt=absolute/self.initial_norm
        state=(self.xc.copy(),components['phi_d'],components['phi_m'],float(self.f),kkt)
        if len(self.states)==self.iter:
            self.states.append(state)
        elif not np.array_equal(state[0],self.states[-1][0]) or state[1:]!=self.states[-1][1:]:
            self.fail('state_mismatch')
        if absolute<=1e-12:
            self.reason='absolute_stationary'
            return True
        if len(self.states)>=4:
            phi=np.array([s[3] for s in self.states[-4:]])
            if kkt<=1e-5 and np.all(np.abs(np.diff(phi))/np.maximum(1.,np.abs(phi[:-1]))<=1e-6):
                self.reason='kkt_stable'
                return True
        if self.iter>=self.budget.remaining_steps:
            self.reason='iteration_cap'
            return True
        active=self.activeSet(self.xc)
        self.release_next=bool(np.any(active&~self.bindingSet(self.xc)))
        self.initial_residual=float(np.linalg.norm((~active)*self.g))
        if self.initial_residual==0. and not self.release_next:
            self.reason='zero_free_direction'
            return True
        return False

    def findSearchDirection(self):
        self.check_time()
        self.check_identity()
        a=self.identity_value['parameter_count']
        diagonal=self.objective.binding_diagonal(_owned(self.xc))
        self.check_identity()
        if not _array(diagonal,a) or np.any(diagonal<=0.): self.fail('nonfinite')
        if self.diagonal is None: self.diagonal=diagonal.copy()
        elif not np.array_equal(diagonal,self.diagonal): self.fail('state_mismatch')
        with np.errstate(over='raise',invalid='raise',divide='raise'):
            inverse=1./diagonal
        if not np.isfinite(inverse).all() or np.any(inverse<=0.): self.fail('nonfinite')
        self.cg_count,self.cg_abs_resid,self.cg_rel_resid=0,None,None
        if self.release_next:
            direction=self.projection(self.xc-inverse*self.g)-self.xc
            metric_norm=float(np.sum(direction**2/inverse))
            if not np.isfinite(metric_norm) or metric_norm<=0.: self.fail('zero_free_direction')
        else:
            active=self.activeSet(self.xc)
            free=np.flatnonzero(~active).astype(np.int64)
            supplied=self.objective.free_metric(_owned(self.xc),_owned(free))
            self.check_identity()
            if (not isinstance(supplied,LinearOperator) or supplied.shape!=(a,a)
                or supplied.dtype!=np.dtype(np.float64)):
                self.fail('state_mismatch')
            def action(v):
                self.check_time()
                self.check_identity()
                result=supplied@v
                expected=np.zeros(a)
                expected[free]=inverse[free]*v[free]
                if not _array(result,a): self.fail('nonfinite')
                # This epoch admits ONLY the original exact diagonal policy.
                # A Joseph/non-diagonal policy needs its separate source review.
                if not np.array_equal(result,expected): self.fail('state_mismatch')
                return result
            self.approxHinv=LinearOperator((a,a),matvec=action,dtype=np.float64)
            direction=super().findSearchDirection()
            if not _array(direction,a) or np.any(direction[active]!=0.): self.fail('state_mismatch')
            # The native minimizer deletes H immediately after this method.
            # Check the actual free-H equation HERE, not just CG's recurrence.
            residual=(~active)*(-self.g-self.H@direction)
            if not _array(residual,a): self.fail('nonfinite')
            actual=float(np.linalg.norm(residual))
            self.cg_abs_resid=actual
            self.cg_rel_resid=actual/self.initial_residual
            if not np.isfinite(actual) or not np.isfinite(self.cg_rel_resid): self.fail('nonfinite')
            if self.cg_count>200 or actual>1e-6*self.initial_residual: self.fail('cg_cap')
        if not _array(direction,a): self.fail('nonfinite')
        slope=float(np.inner(self.g,direction))
        if not np.isfinite(slope): self.fail('nonfinite')
        if not np.any(direction) or slope>=0.: self.fail('zero_free_direction')
        return direction

    def modifySearchDirection(self,p):
        trial,accepted=super().modifySearchDirection(p)
        if not accepted: self.reason='line_search_failed'
        return trial,accepted

    def doEndIteration(self,xt):
        if self._LS_ft-float(self.f)>1e-12*max(1.,abs(float(self.f))): self.fail('state_mismatch')
        if (self.pending_state is None or not np.array_equal(xt,self.pending_state[0])
            or len(self.states)!=int(self.iter)+1):
            self.fail('state_mismatch')
        self.cg_counts.append(int(self.cg_count))
        self.ls_counts.append(int(self.iterLS)+1)
        super().doEndIteration(xt)
        self.states.append(self.pending_state)
        self.pending_state=None


def _result(states,a,reason,cg_counts=(),ls_counts=()):
    k=len(states)
    phi=np.array([s[3] for s in states],dtype=np.float64)
    converged=reason in ('absolute_stationary','kkt_stable')
    trace={
        'models_q':_owned(np.array([s[0] for s in states],dtype=np.float64).reshape(k,a)),
        'phi_d':_owned(np.array([s[1] for s in states],dtype=np.float64)),
        'phi_m':_owned(np.array([s[2] for s in states],dtype=np.float64)),
        'phi_engine':_owned(phi),
        'kkt_normalized':_owned(np.array([s[4] for s in states],dtype=np.float64)),
        'relative_changes':_owned(np.abs(np.diff(phi))/np.maximum(1.,np.abs(phi[:-1]))),
        'line_search_counts':_owned(np.array(ls_counts[:max(0,k-1)],dtype=np.int64)),
        'cg_counts':_owned(np.array(cg_counts[:max(0,k-1)],dtype=np.int64))}
    return {'status':'converged' if converged else 'failed' if reason in (
                'state_mismatch','nonfinite','engine_error','dependency_unsupported') else 'nonconverged',
        'reason':reason,'q':_owned(states[-1][0]) if k else None,
        'phi_d':states[-1][1] if k else None,'phi_m':states[-1][2] if k else None,
        'phi_engine':states[-1][3] if k else None,'kkt_normalized':states[-1][4] if k else None,
        'iterations':max(0,k-1),'trace':trace,
        'failed_trial':None if converged else {'iteration':max(0,k-1),'reason':reason}}


def solve_bounded_physical(objective: PhysicalObjective,lower_q,upper_q,start_q,*,budget,binding):
    """Bounded candidate linear composition; not a source/admission authority.

No retry recipe or criterion relaxation. The adapter must verify its actual
complete source inventory, literal physics/certificate and allocation receipt.
"""
    identity=_preflight(objective,lower_q,upper_q,start_q,budget,binding)
    a=identity['parameter_count']
    if identity['mode']!='fixed_linear_quadratic':
        return _result([],a,'dependency_unsupported')
    if monotonic()>budget.deadline: return _result([],a,'wall_cap')
    # Enforce the ordinary per-fit cap independently of a longer workflow clock.
    budget=OptimizerBudget(min(budget.deadline,monotonic()+120.),budget.remaining_steps,
        budget.resource_limit_bytes,budget.admitted_bytes,budget.allocation_plan_sha256)
    opt=_NativeRecorded(objective,identity,lower_q,upper_q,budget)
    terminal=None
    try:
        terminal=opt.minimize(opt.evaluate,start_q.copy())
        if not opt.states or not np.array_equal(terminal,opt.states[-1][0]): opt.fail('state_mismatch')
        replay,_=opt.evaluate(opt.states[-1][0],True,False)
        opt.components(opt.states[-1][0],replay)
        if replay!=opt.states[-1][3]: opt.fail('state_mismatch')
    except _Failure:
        pass
    except ArithmeticError:
        opt.reason='nonfinite'
    except (RuntimeError,ValueError,TypeError,KeyError):
        opt.reason='engine_error'
    finally:
        try: objective.release_state()
        except (RuntimeError,ValueError,TypeError,KeyError,ArithmeticError):
            if opt.reason not in ('state_mismatch','nonfinite','engine_error'): opt.reason='engine_error'
    return _result(opt.states,a,opt.reason or 'state_mismatch',opt.cg_counts,opt.ls_counts)
