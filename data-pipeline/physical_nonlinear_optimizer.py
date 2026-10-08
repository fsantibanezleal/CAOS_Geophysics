"""Trusted nonlinear physical objectives composed with actual SimPEG GNCG.

No upload callback, copied CG, quadratic certificate or scientific acceptance
registry. Adapters own physics, exact/PSD Hessian proofs and allocation receipts.
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

RUNTIME_EPOCH = 'physical-gncg-nonlinear-candidate-2'
POLICY = 'exact-bound-native-gncg-actual-armijo-1'
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
VENDOR_SOURCE_SHA256 = hashlib.sha256(Path(optimization.__file__).read_bytes()).hexdigest()
_DIGEST = re.compile('[0-9a-f]{64}\\Z', re.ASCII)
_IDENTITY_KEYS = {'mode','runtime_epoch','objective_sha256','source_inventory_sha256',
    'q_unit','physical_unit','physical_scale','parameter_count','observation_rows',
    'observation_components','beta_engine','stage_index','allocation_plan_sha256'}


@dataclass(frozen=True)
class NonlinearBinding:
    accepted_export: str
    optimizer_source_sha256: str
    vendor_source_sha256: str
    source_inventory_sha256: str
    runtime_epoch: str
    policy: str


@dataclass(frozen=True)
class NonlinearBudget:
    deadline: float
    remaining_steps: int
    resource_limit_bytes: int
    admitted_bytes: int
    allocation_plan_sha256: str


class NonlinearObjective(Protocol):
    def identity(self) -> dict: ...
    def evaluate(self, q, return_g=False, return_H=False): ...
    def components(self, q) -> dict: ...
    def binding_diagonal(self, q): ...
    def free_metric(self, q, free_indices) -> LinearOperator: ...
    def exact_hessian(self, q) -> LinearOperator: ...
    def release_state(self): ...


class _Failure(RuntimeError):
    pass


def _digest(value):
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def _finite(value, *, positive=False):
    return type(value) is float and np.isfinite(value) and (not positive or value>0.)


def _array(value, n):
    return (type(value) is np.ndarray and value.dtype==np.float64 and value.shape==(n,)
            and np.isfinite(value).all())


def _operator(value, n):
    return (isinstance(value,LinearOperator) and value.shape==(n,n)
            and value.dtype==np.dtype(np.float64))


def _owned(value):
    result=value.copy()
    result.flags.writeable=False
    return result


def _identity(objective):
    value=objective.identity()
    if type(value) is not dict or set(value)!=_IDENTITY_KEYS:
        raise ValueError('nonlinear: exact13 identity keys required')
    for key in ('objective_sha256','source_inventory_sha256','allocation_plan_sha256'):
        if not _digest(value[key]): raise ValueError('nonlinear: identity digest')
    for key in ('runtime_epoch','q_unit','physical_unit'):
        if type(value[key]) is not str or not 1<=len(value[key])<=96:
            raise ValueError('nonlinear: registered identity strings')
    if value['mode']!='nonlinear_gauss_newton' or value['runtime_epoch']!=RUNTIME_EPOCH:
        raise ValueError('nonlinear: distinct objective epoch required')
    if value['physical_unit'] not in ('kg_m3','si','kg_m3_and_si'):
        raise ValueError('nonlinear: explicit physical units')
    scales=value['physical_scale']
    if type(scales) is not tuple or len(scales) not in (1,2) or any(
            not _finite(s,positive=True) for s in scales):
        raise ValueError('nonlinear: positive property scale tuple')
    if len(scales)!=(2 if value['physical_unit']=='kg_m3_and_si' else 1):
        raise ValueError('nonlinear: scale/unit blocks')
    if not _finite(value['beta_engine']) or value['beta_engine']!=1.:
        raise ValueError('nonlinear: actual weighted component decomposition')
    for key in ('parameter_count','observation_rows','observation_components'):
        if type(value[key]) is not int or value[key]<=0:
            raise ValueError('nonlinear: positive native count')
    if value['parameter_count']>8192 or value['observation_rows']>4096 or (
            value['observation_components'] not in (1,2)):
        raise ValueError('nonlinear: literal M11 count caps')
    if type(value['stage_index']) is not int or not 0<=value['stage_index']<=25:
        raise ValueError('nonlinear: stage index')
    return value.copy()


def _preflight(objective,lower,upper,start,budget,binding):
    if any(not callable(getattr(objective,key,None)) for key in (
        'identity','evaluate','components','binding_diagonal','free_metric','exact_hessian','release_state')):
        raise ValueError('nonlinear: complete trusted seven-method objective required')
    identity=_identity(objective)
    if type(binding) is not NonlinearBinding or (
        binding.accepted_export!='physical_nonlinear_optimizer.solve_bounded_nonlinear'
        or binding.optimizer_source_sha256!=SOURCE_SHA256
        or binding.vendor_source_sha256!=VENDOR_SOURCE_SHA256
        or binding.runtime_epoch!=RUNTIME_EPOCH or binding.policy!=POLICY
        or binding.source_inventory_sha256!=identity['source_inventory_sha256']):
        raise ValueError('nonlinear: reviewed loaded source/binding required')
    if type(budget) is not NonlinearBudget or (
        not _finite(budget.deadline) or budget.deadline>monotonic()+1800.
        or type(budget.remaining_steps) is not int or not 0<=budget.remaining_steps<=250
        or type(budget.resource_limit_bytes) is not int or not 0<budget.resource_limit_bytes<=2*1024**3
        or type(budget.admitted_bytes) is not int or not 0<budget.admitted_bytes<=budget.resource_limit_bytes
        or budget.allocation_plan_sha256!=identity['allocation_plan_sha256']):
        raise ValueError('nonlinear: original bounded workflow admission required')
    n=identity['parameter_count']
    if any(not _array(v,n) for v in (lower,upper,start)) or (
        np.any(lower>=upper) or np.any(start<lower) or np.any(start>upper)):
        raise ValueError('nonlinear: finite native box/start, no projection')
    return identity


def feasible_gradient(q,gradient,lower,upper):
    """Exact-bound KKT gradient; no near-bound tolerance or clipping of q."""
    n=q.size if type(q) is np.ndarray else 0
    if any(not _array(v,n) for v in (q,gradient,lower,upper)) or (
            np.any(lower>=upper) or np.any(q<lower) or np.any(q>upper)):
        raise ValueError('nonlinear: finite feasible exact-bound operands')
    result=gradient.copy()
    result[q==lower]=np.minimum(gradient[q==lower],0.)
    result[q==upper]=np.maximum(gradient[q==upper],0.)
    return result


def audit_hessians(objective,q):
    """Return distinct declared exact and PSD operators for independent audits.

Shape/dtype checks do not prove symmetry, PSD, or derivative correctness. The
physical adapter's independent finite-difference/analytic tests supply those.
"""
    identity=_identity(objective)
    n=identity['parameter_count']
    if not _array(q,n): raise ValueError('nonlinear: native audit q')
    value=objective.evaluate(_owned(q),False,True)
    exact=objective.exact_hessian(_owned(q))
    if (type(value) is not tuple or len(value)!=2 or not _finite(value[0])
        or not _operator(value[1],n) or not _operator(exact,n)
        or value[1] is exact or _identity(objective)!=identity):
        raise ValueError('nonlinear: distinct stable exact/PSD operators')
    return {'exact':exact,'search_psd':value[1]}


class _NativeRecorded(optimization.ProjectedGNCG):
    def __init__(self,objective,identity,lower,upper,budget):
        super().__init__(lower=lower.copy(),upper=upper.copy(),maxIter=budget.remaining_steps,
            maxIterLS=30,cg_maxiter=512,cg_rtol=1e-6,cg_atol=0.,step_active_set=False,
            LSreduction=1e-4,LSshorten=.5,use_WolfeCurvature=False,
            require_decrease=True,maxStep=np.inf)
        self.objective,self.identity_value,self.budget=objective,identity,budget
        self.states,self.steps=[],[]
        self.reason,self.initial_norm,self.diagonal=None,None,None
        self.pending_state,self.pending_step=None,None
        self.release_next=False
        self.cg_count,self.cg_abs_resid,self.cg_rel_resid=0,None,None

    def fail(self,reason):
        self.reason=reason
        raise _Failure(reason)

    def check(self):
        if monotonic()>self.budget.deadline: self.fail('wall_cap')
        try: current=_identity(self.objective)
        except (ValueError,TypeError,KeyError): self.fail('state_mismatch')
        if current!=self.identity_value: self.fail('state_mismatch')

    def checked_operator(self,supplied):
        n=self.identity_value['parameter_count']
        if not _operator(supplied,n): self.fail('state_mismatch')
        def action(v):
            self.check()
            if not _array(v,n): self.fail('nonfinite')
            result=supplied@_owned(v)
            self.check()
            if not _array(result,n): self.fail('nonfinite')
            return result
        return LinearOperator((n,n),matvec=action,dtype=np.float64)

    def evaluate(self,q,return_g=False,return_H=False):
        self.check()
        n=self.identity_value['parameter_count']
        if not _array(q,n): self.fail('nonfinite')
        if np.any(q<self.lower) or np.any(q>self.upper): self.fail('state_mismatch')
        value=self.objective.evaluate(_owned(q),return_g,return_H)
        self.check()
        count=1+int(return_g)+int(return_H)
        if count==1:
            if not _finite(value): self.fail('nonfinite')
            return value
        if type(value) is not tuple or len(value)!=count: self.fail('state_mismatch')
        if not _finite(value[0]): self.fail('nonfinite')
        if return_g and not _array(value[1],n): self.fail('nonfinite')
        if return_H:
            search=value[-1]
            value=(*value[:-1],self.checked_operator(search))
            if self.initial_norm is None:
                exact=self.objective.exact_hessian(_owned(q))
                self.check()
                if not _operator(exact,n) or exact is search: self.fail('state_mismatch')
        return value

    def components(self,q,phi):
        self.check()
        values=self.objective.components(_owned(q))
        self.check()
        if type(values) is not dict or set(values)!={'phi_d','phi_m','phi_engine','engine_terms'}:
            self.fail('state_mismatch')
        terms=values['engine_terms']
        if type(terms) is not tuple or len(terms)!=5: self.fail('state_mismatch')
        if any(not _finite(v) or v<0. for v in (*terms,*(values[k] for k in ('phi_d','phi_m','phi_engine')))):
            self.fail('nonfinite')
        if (values['phi_engine']!=phi or (((terms[0]+terms[1])+terms[2])+terms[3])+terms[4]!=phi
            or values['phi_d']!=terms[0]+terms[1] or values['phi_m']!=(terms[2]+terms[3])+terms[4]):
            self.fail('state_mismatch')
        return values

    def state(self,q,gradient,phi):
        values=self.components(q,phi)
        kkt=float(np.linalg.norm(feasible_gradient(q,gradient,self.lower,self.upper),
                                 ord=np.inf))/self.initial_norm
        return (q.copy(),values['phi_d'],values['phi_m'],phi,kkt)

    def stoppingCriteria(self,inLS=False):
        self.check()
        if inLS:
            chord=self._LS_xt-self.xc
            slope=float(np.inner(self.g,chord))
            phi_trial=float(self._LS_ft)
            if not np.isfinite(chord).all() or not _finite(slope) or not _finite(phi_trial):
                self.fail('nonfinite')
            if not np.any(chord): self.fail('zero_free_direction')
            if slope>=0.: return False
            margin=(phi_trial-float(self.f))-1e-4*slope
            if not _finite(margin): self.fail('nonfinite')
            if margin>0.: return False
            phi,gradient=self.evaluate(self._LS_xt,True,False)
            if phi!=phi_trial: self.fail('state_mismatch')
            pending=self.state(self._LS_xt,gradient,phi)
            self.check()
            self.pending_state=pending
            self.pending_step=(self.branch,int(self.active_count),int(self.binding_count),
                int(self.cg_count),self.cg_abs_resid,self.cg_rel_resid,
                int(self.iterLS)+1,float(self._LS_t),slope,margin)
            return True
        if self.initial_norm is None:
            self.initial_norm=max(1.,float(np.linalg.norm(self.g,ord=np.inf)))
            self.f0=float(self.f)
        state=self.state(self.xc,self.g,float(self.f))
        if len(self.states)==self.iter:
            self.states.append(state)
        elif (len(self.states)!=self.iter+1 or not np.array_equal(state[0],self.states[-1][0])
              or state[1:]!=self.states[-1][1:]): self.fail('state_mismatch')
        if state[4]<=1e-5:
            self.reason='kkt'
            return True
        if self.iter>=self.budget.remaining_steps:
            self.reason='iteration_cap'
            return True
        active,binding=self.activeSet(self.xc),self.bindingSet(self.xc)
        self.active_count,self.binding_count=int(active.sum()),int(binding.sum())
        self.release_next=bool(np.any(active&~binding))
        self.initial_residual=float(np.linalg.norm((~active)*self.g))
        if self.initial_residual==0. and not self.release_next:
            self.reason='zero_free_direction'
            return True
        return False

    def findSearchDirection(self):
        self.check()
        n=self.identity_value['parameter_count']
        diagonal=self.objective.binding_diagonal(_owned(self.xc))
        self.check()
        if not _array(diagonal,n) or np.any(diagonal<=0.): self.fail('nonfinite')
        if self.diagonal is None: self.diagonal=diagonal.copy()
        elif not np.array_equal(diagonal,self.diagonal): self.fail('state_mismatch')
        with np.errstate(over='raise',invalid='raise',divide='raise'):
            inverse=1./self.diagonal
        if not np.isfinite(inverse).all() or np.any(inverse<=0.): self.fail('nonfinite')
        self.cg_count,self.cg_abs_resid,self.cg_rel_resid=0,None,None
        if self.release_next:
            self.branch=0
            direction=self.projection(self.xc-inverse*self.g)-self.xc
        else:
            self.branch=1
            active=self.activeSet(self.xc)
            free=np.flatnonzero(~active).astype(np.int64)
            supplied=self.objective.free_metric(_owned(self.xc),_owned(free))
            self.check()
            if not _operator(supplied,n): self.fail('state_mismatch')
            def action(v):
                self.check()
                result=supplied@_owned(v)
                self.check()
                expected=np.zeros(n)
                expected[free]=inverse[free]*v[free]
                if not _array(result,n): self.fail('nonfinite')
                if not np.array_equal(result,expected): self.fail('state_mismatch')
                return result
            self.approxHinv=LinearOperator((n,n),matvec=action,dtype=np.float64)
            direction=super().findSearchDirection()
            if not _array(direction,n): self.fail('nonfinite')
            if np.any(direction[active]!=0.): self.fail('state_mismatch')
            residual=(~active)*(-self.g-self.H@direction)
            if not _array(residual,n): self.fail('nonfinite')
            actual=float(np.linalg.norm(residual))
            self.cg_abs_resid,self.cg_rel_resid=actual,actual/self.initial_residual
            if not _finite(actual) or not _finite(self.cg_rel_resid): self.fail('nonfinite')
            if self.cg_count>512 or actual>1e-6*self.initial_residual: self.fail('cg_cap')
        slope=float(np.inner(self.g,direction))
        if not _array(direction,n) or not _finite(slope): self.fail('nonfinite')
        if not np.any(direction) or slope>=0.: self.fail('zero_free_direction')
        return direction

    def modifySearchDirection(self,p):
        trial,accepted=super().modifySearchDirection(p)
        if not accepted: self.reason='line_search_failed'
        return trial,accepted

    def doEndIteration(self,xt):
        if (self.pending_state is None or self.pending_step is None
            or not np.array_equal(xt,self.pending_state[0])
            or len(self.states)!=int(self.iter)+1): self.fail('state_mismatch')
        # Record the actual accepted step before vendor hooks or a later clock
        # check can fail. The acceptance predicate was already fully checked.
        self.states.append(self.pending_state)
        self.steps.append(self.pending_step)
        self.pending_state,self.pending_step=None,None
        super().doEndIteration(xt)


def _result(states,steps,n,reason):
    k=len(states)
    phi=np.array([s[3] for s in states],dtype=np.float64)
    trace={'models_q':_owned(np.array([s[0] for s in states],dtype=np.float64).reshape(k,n)),
        'phi_d':_owned(np.array([s[1] for s in states],dtype=np.float64)),
        'phi_m':_owned(np.array([s[2] for s in states],dtype=np.float64)),
        'phi_engine':_owned(phi),
        'kkt_normalized':_owned(np.array([s[4] for s in states],dtype=np.float64)),
        'relative_changes':_owned(np.abs(np.diff(phi))/np.maximum(1.,np.abs(phi[:-1])))}
    fields=(('branches',0,np.int64),('active_counts',1,np.int64),('binding_counts',2,np.int64),
        ('cg_counts',3,np.int64),('cg_abs_residuals',4,np.float64),
        ('cg_relative_residuals',5,np.float64),('line_search_counts',6,np.int64),
        ('line_search_alphas',7,np.float64),('projected_slopes',8,np.float64),
        ('armijo_margins',9,np.float64))
    for name,index,dtype in fields:
        trace[name]=_owned(np.array([s[index] if s[index] is not None else 0 for s in steps],dtype=dtype))
    trace['cg_residuals_available']=_owned(np.array([s[4] is not None for s in steps],dtype=np.bool_))
    converged=reason=='kkt'
    return {'status':'converged' if converged else 'failed' if reason in (
        'state_mismatch','nonfinite','engine_error') else 'nonconverged',
        'reason':reason,'q':_owned(states[-1][0]) if k else None,
        'phi_d':states[-1][1] if k else None,'phi_m':states[-1][2] if k else None,
        'phi_engine':states[-1][3] if k else None,'kkt_normalized':states[-1][4] if k else None,
        'iterations':max(0,k-1),'trace':trace,
        'failed_trial':None if converged else {'iteration':max(0,k-1),'reason':reason}}


def solve_bounded_nonlinear(objective: NonlinearObjective,lower_q,upper_q,start_q,*,budget,binding):
    """One reviewed physical recipe, sharing the original workflow deadline.

No reset, retry, fallback or tolerance relaxation. Declared admission and
operator identities are not independent scientific/resource acceptance.
"""
    identity=_preflight(objective,lower_q,upper_q,start_q,budget,binding)
    n=identity['parameter_count']
    opt=_NativeRecorded(objective,identity,lower_q,upper_q,budget)
    try:
        if monotonic()>budget.deadline: opt.fail('wall_cap')
        terminal=opt.minimize(opt.evaluate,start_q.copy())
        if not opt.states or not np.array_equal(terminal,opt.states[-1][0]): opt.fail('state_mismatch')
        replay,_=opt.evaluate(terminal,True,False)
        opt.components(terminal,replay)
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
            opt.reason='engine_error'
    return _result(opt.states,opt.steps,n,opt.reason or 'state_mismatch')
