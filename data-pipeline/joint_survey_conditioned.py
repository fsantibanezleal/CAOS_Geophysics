"""Actual original single-property M11 objective through public owned metric.

Separate source epoch, not historical calibration/archive rewrite, full26-fit
or exact quartic coupling acceptance. Public dependencies are independently
reviewed committed product sources, never user factories or private helpers.
"""
from dataclasses import asdict
import hashlib
from pathlib import Path

import numpy as np
from scipy import sparse

import joint_survey_optimizer as original
import joint_survey_plan as planner
import joint_survey_resources as resources
import physical_conditioned_optimizer as public
import physical_owned_spd as spd


PUBLIC_COMMIT='c184e3cadcd94a94f46b129009bfc7b6810d115b'
PINS={
    'physical_conditioned_optimizer.py':'3da9709208dd440e62f9d83960ca2d267b1b8a5cb390bec49b9edf09e4cc82a8',
    'physical_owned_spd.py':'8924508c3328b70bb9e08ac11a81e107bcdd713402812ba64afec838892d36c2',
    'gravity_l2_metric.py':'d09a2b4630258d2c26a1a82ea92a3cd79b42143695d3e630d5252df5ba8dfe8b',
    'gravity_l2_precision.py':'57727cac9ab6550eab902d20d6c43e662be8f9fac406896c6797d1e29b3e7c1a',
    'physical_optimizer.py':'4745d41ff8afb908260611601861db8303ce7bd612ff0ea614cceb201a20bc86',
}


def source_inventory():
    inventory=original.reviewed_source_inventory()
    for module in (public,spd,spd.kernel,spd.intervals,public.linear):
        path=Path(module.__file__);actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if PINS.get(path.name)!=actual or getattr(module,'SOURCE_SHA256',actual)!=actual:
            raise RuntimeError('M11: unreviewed conditioned public source')
        inventory[path.name]=actual
    inventory['joint_survey_conditioned.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if public.LINEAR_EPOCH!='physical-gncg-linear-joseph-candidate-2' or public.POLICY!='closed-firstorder-joseph-native-true-residual-terminal-1':
        raise RuntimeError('M11: unreviewed conditioned policy')
    return inventory


def allocation_plan(problem,modality):
    planner._enum(modality,('gravity','magnetic'),'conditioned.modality')
    old=original.allocation_plan(problem)
    nsource=len(problem.plan[modality]['receivers_m']);nfit=len(problem.plan[modality]['training_rows'])
    phases=spd.kernel.allocation(nsource,nfit,problem.n,problem.plan[modality]['noise']['kind']=='full_covariance')
    admitted=old['admitted_bytes']+phases['maximum']
    if admitted>resources.MAX_RSS: raise ValueError('M11: original plus owned metric exceeds2GiB')
    value={'original_problem':old,'owned_metric':phases,'admitted_bytes':admitted,
        'source_components':nsource,'fit_components':nfit,'parameters':problem.n,
        'maximum_cg_steps':200,'maximum_accepted_steps':200,'maximum_ls_trials':20,'fit_wall_seconds':120.}
    value['allocation_plan_sha256']=planner._digest(value)
    return value


def original_terms(problem):
    """Exact stored R entries, split by original mesh neighbor axis only."""
    R=problem.R;n=problem.n
    if type(R) is not sparse.csr_matrix or R.shape[1]!=n or R.shape[0]>4*n or R.nnz>7*n:
        raise ValueError('M11: actual first-order original R required')
    small=R[:n].tocsr();small.sort_indices()
    if (not np.array_equal(small.indptr,np.arange(n+1,dtype=np.int32))
            or not np.array_equal(small.indices,np.arange(n,dtype=np.int32)) or np.any(small.data<=0.)):
        raise ValueError('M11: original positive diagonal smallness required')
    terms=[spd.QuadraticTerm(.5,small,sparse.eye(n,format='csr'))]
    full=np.flatnonzero(problem.plan['mesh']['active']);nx=len(problem.plan['mesh']['hx_m']);ny=len(problem.plan['mesh']['hy_m'])
    groups=[[],[],[]]
    for row in range(n,R.shape[0]):
        start,end=R.indptr[row:row+2];cols=R.indices[start:end];values=R.data[start:end]
        if (len(cols)!=2 or not cols[0]<cols[1] or not values[0]<0. or values[1]!=-values[0]):
            raise ValueError('M11: exact original signed neighbor row required')
        difference=int(full[cols[1]]-full[cols[0]])
        if difference not in (1,nx,nx*ny): raise ValueError('M11: original mesh neighbor axis required')
        groups[(1,nx,nx*ny).index(difference)].append(row)
    for rows in groups:
        if not rows: continue
        block=R[rows].tocsr();weights=block.data[1::2].copy()
        D=block.copy();D.data[0::2]=-1.;D.data[1::2]=1.
        W=sparse.diags(weights,format='csr')
        if (W@D-block).nnz: raise RuntimeError('M11: stored original factor reconstruction changed')
        terms.append(spd.QuadraticTerm(.5,W,D))
    return tuple(terms)


class JointQuadraticObjective(original.JointOptimizerObjective):
    """Trusted compiled single-property adapter, original native potential/H/g."""
    def __init__(self,problem,modality,beta,stage,inventory,allocation,budget):
        planner._enum(modality,('gravity','magnetic'),'conditioned.modality')
        if type(beta) is not float or beta not in original.objective.BETAS:
            raise ValueError('M11: frozen original beta required')
        weights={'beta_gravity':beta if modality=='gravity' else .0001,
            'beta_magnetic':beta if modality=='magnetic' else .0001,'coupling':0.}
        sl=slice(0,problem.n) if modality=='gravity' else slice(problem.n,2*problem.n)
        super().__init__(problem,weights,problem.start[sl],stage,inventory,allocation,budget,modality)
        self._identity.update(mode='fixed_linear_quadratic',runtime_epoch=public.LINEAR_EPOCH)
        self.allocation=allocation;self.regularizer=(beta*(problem.R.T@problem.R)).tocsr();self.regularizer.sort_indices()
        self.factors=original_terms(problem)
        self.A=np.ascontiguousarray(problem.A[modality]);self.d=problem.d[modality]
        self.prediction_rows=np.ascontiguousarray(problem.J[modality]*problem.scales[sl])
        self.W=sparse.eye(len(self.d),format='csr')

    def components(self,q):
        data,penalty,_,_=self._state(q)
        return {'phi_d':data,'phi_m':penalty,'phi_engine':data+penalty}

    def metric_operands(self,q):
        self._state(q)
        return spd.MetricOperands(spd.binding_for(self.identity(),q),self.allocation['source_components'],
            self.allocation['fit_components'],self.n,self.problem.plan[self.modality]['noise']['kind']=='full_covariance',
            self.regularizer,self.A,.5)

    def quadratic_operands(self,q):
        self._state(q)
        return spd.QuadraticOperands(spd.binding_for(self.identity(),q),self.A,self.W,self.d,
            self.problem.reference[self.slice],.5,self.weights['beta_'+self.modality],self.factors,self.prediction_rows)

    def certify(self,q,qt,native_gradient,native_phi,native_phi_trial,iteration,trial,deadline):
        self.budget.checkpoint()
        result=spd.certify_quadratic_chord(self.quadratic_operands(q),self.identity(),q,qt,native_gradient,
            native_phi,native_phi_trial,iteration,trial,deadline,source_components=self.allocation['source_components'],
            covariance=self.problem.plan[self.modality]['noise']['kind']=='full_covariance',resource_limit_bytes=resources.MAX_RSS)
        self.budget.checkpoint()
        return result


def solve_original_baseline(problem,modality,beta,stage,budget):
    """Actual fixed original data, no oracle, sealed values, fallback or refit."""
    if type(budget) is not resources.JointResourceBudget:
        raise TypeError('M11: actual original measured workflow budget required')
    budget.checkpoint();inventory=source_inventory();allocation=allocation_plan(problem,modality)
    adapter=JointQuadraticObjective(problem,modality,beta,stage,inventory,allocation,budget)
    identity=adapter.identity();binding=public.ConditionedBinding('physical_conditioned_optimizer.solve_bounded_linear',
        public.SOURCE_SHA256,spd.SOURCE_SHA256,spd.KERNEL_SHA256,public.VENDOR_SOURCE_SHA256,
        spd.SOURCE_SHA256,identity['source_inventory_sha256'],public.LINEAR_EPOCH,public.POLICY)
    declared=public.ConditionedBudget(budget.deadline,200,resources.MAX_RSS,allocation['admitted_bytes'],allocation['allocation_plan_sha256'])
    terminal=spd.TerminalPolicy(1e-5,model_error_limit=1e-5,objective_gap_limit=1e-10,physical_prediction_error_limit=1e-8)
    result=public.solve_bounded_linear(adapter,problem.lower[adapter.slice],problem.upper[adapter.slice],
        problem.start[adapter.slice],budget=declared,binding=binding,terminal=terminal)
    return {'schema':'joint-conditioned-baseline-1','stage':stage,'modality':modality,'beta':beta,
        'identity':identity,'source_inventory':inventory,'optimizer_binding':asdict(binding),
        'allocation_plan':allocation,'terminal_policy':asdict(terminal),'result':result,
        'coupled_inversion_performed':False,'scientific_acceptance_verified':False,'public_activation':False}
