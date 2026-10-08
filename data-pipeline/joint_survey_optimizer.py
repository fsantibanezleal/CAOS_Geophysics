"""Trusted physical adapter and actual leakage-safe26-fit M11 calibration."""
from dataclasses import asdict
import hashlib
import inspect
from pathlib import Path

import numpy as np
from scipy.sparse.linalg import LinearOperator
from simpeg import maps,optimization
from simpeg.regularization import CrossGradient,RegularizationMesh,BaseSimilarityMeasure
from discretize import TensorMesh
from discretize.operators.differential_operators import DiffOperators

import joint_survey_compiled as compiled
import joint_survey_evaluation as evaluation
import joint_survey_objective as objective
import joint_survey_plan as planner
import joint_survey_resources as resources
import physical_nonlinear_optimizer as solver


SOLVER_SHA='772c4de0b7747bbc9075b6fbf1357b04de752bfd900f88c9a5ddead2a91931fd'
VENDOR_SHA='0ac858cc310b32bb9aa59c78aaaa9c79b5f28438db52fb06ec73d976b63196a4'
_VENDOR_PINS=((CrossGradient,'85ff1c1e39ec9e8973707a7debd83706db23027b13832298c4e468b052e3298c'),
    (RegularizationMesh,'942ac3fffded92f48c7a5294575082713ebde716918d0e8fbe117c084607ff8f'),
    (BaseSimilarityMeasure,'aae7dbd3cb4887246f38c8ceba4fe8fbeeb5592110341635e06fdb70246a92b5'),
    (maps.Wires,'6bdd7455d17467ed547091526735df560a35c9b204ab2f4105dfab096ed6c90e'),
    (TensorMesh,'2e8a97a5449f490dbf4128c8696833a8770c896d260f5ecf087e2f622b3be65d'),
    (DiffOperators,'f3c7ca3c54a50232202d08bf9768411273fcee7ce95eb5b110a79de6c42db70a'))


class JointCalibrationFailure(RuntimeError):
    """Durable driver failure evidence, never an optimized selection."""
    def __init__(self,reason,last_attempt):
        super().__init__(reason);self.reason=reason;self.last_attempt=last_attempt
        self.verified_candidates=();self.source_inventory={};self.optimizer_binding={}


def reviewed_source_inventory():
    """Loaded official defining source pins, not a user chosen import/root."""
    planner._runtime()
    actual=hashlib.sha256(Path(solver.__file__).read_bytes()).hexdigest()
    vendor=hashlib.sha256(Path(optimization.__file__).read_bytes()).hexdigest()
    if actual!=SOLVER_SHA or solver.SOURCE_SHA256!=actual or vendor!=VENDOR_SHA or solver.VENDOR_SOURCE_SHA256!=vendor:
        raise RuntimeError('M11: unreviewed public nonlinear source')
    if solver.RUNTIME_EPOCH!='physical-gncg-nonlinear-candidate-2' or solver.POLICY!='exact-bound-native-gncg-actual-armijo-1':
        raise RuntimeError('M11: unreviewed nonlinear policy')
    inventory={'physical_nonlinear_optimizer.py':actual,'simpeg.optimization':vendor}
    for target,expected in _VENDOR_PINS:
        actual=hashlib.sha256(Path(inspect.getsourcefile(target)).read_bytes()).hexdigest()
        if actual!=expected: raise RuntimeError('M11: defining structural source drift')
        inventory[target.__name__]=actual
    defining=Path(inspect.getsourcefile(RegularizationMesh.cell_gradient.fget))
    actual=hashlib.sha256(defining.read_bytes()).hexdigest()
    if actual!='5283b4f854906aeb05c216ff1c83174c99a7c53fe6a3ce8227b8ea483e785f44':
        raise RuntimeError('M11: defining regularization mesh drift')
    inventory['RegularizationMesh.cell_gradient']=actual
    for name in ('joint_survey_optimizer','joint_survey_compiled','joint_survey_objective','joint_survey_plan',
                 'joint_survey_structure','gravity_forward','magnetic_forward'):
        inventory[name+'.py']=hashlib.sha256((Path(__file__).parent/(name+'.py')).read_bytes()).hexdigest()
    return inventory


def allocation_plan(problem):
    # Dense kernels plus working vectors, marginal arrays, sparse operators and
    # all36 property traces at literal251 states. Conservative admission only.
    n=problem.n;kernel=sum(v.nbytes for v in problem.J.values())
    development=sum(v.nbytes for v in planner._arrays(problem.development))
    projected=int(kernel*4+development*4+36*251*n*8+512*(2*n)*8+64*1024**2)
    if projected>resources.MAX_RSS: raise ValueError('M11: projected allocation exceeds2GiB')
    result={'active_cells':n,'kernel_bytes':kernel,'development_bytes':development,'admitted_bytes':projected,
        'trace_states_per_fit':251,'fits':26,'maximum_cg_steps':512,'maximum_ls_trials':30}
    result['allocation_plan_sha256']=planner._digest(result)
    return result


class JointOptimizerObjective:
    """Native trusted adapter, never accepted from uploaded Python objects."""
    def __init__(self,problem,weights,start,stage,inventory,allocation,budget,modality=None):
        if type(problem) is not compiled.JointDevelopmentProblem: raise TypeError('M11: trusted compiled problem required')
        if modality is not None: planner._enum(modality,evaluation.MODALITIES,'modality')
        self.problem=problem;self.weights=dict(weights);self.modality=modality;self.budget=budget
        self.slice=slice(0,problem.n) if modality=='gravity' else slice(problem.n,2*problem.n) if modality=='magnetic' else slice(None)
        self.n=problem.n if modality else 2*problem.n
        planner._array(start,(self.n,),'adapter.start');planner._finite(start)
        self.start=planner._snapshot(start);self.diagonal=None
        physical=(problem.plan['prior']['density']['scale'],problem.plan['prior']['susceptibility']['scale'])
        self._identity={'mode':'nonlinear_gauss_newton','runtime_epoch':solver.RUNTIME_EPOCH,
            'objective_sha256':planner._digest({'development_sha256':problem.development_sha256,'weights':self.weights,
                                               'modality':modality,'start':self.start}),
            'source_inventory_sha256':planner._digest(inventory),'q_unit':'normalized_two_property_blocks' if not modality else 'normalized_property_block',
            'physical_unit':'kg_m3' if modality=='gravity' else 'si' if modality=='magnetic' else 'kg_m3_and_si',
            'physical_scale':physical if not modality else (physical[0 if modality=='gravity' else 1],),
            'parameter_count':self.n,'observation_rows':sum(len(problem.plan[m]['training_rows']) for m in ((modality,) if modality else evaluation.MODALITIES)),
            'observation_components':1 if modality else 2,'beta_engine':1.,'stage_index':stage,
            'allocation_plan_sha256':allocation['allocation_plan_sha256']}

    def identity(self): return dict(self._identity)

    def _state(self,q):
        self.budget.checkpoint();planner._array(q,(self.n,),'adapter.q');planner._finite(q)
        lo=self.problem.lower[self.slice];hi=self.problem.upper[self.slice]
        if np.any((q<lo)|(q>hi)): raise ValueError('M11: exact adapter bounds')
        if self.modality is None:
            state=self.problem.state(q,self.weights);terms=state['terms']
            data=float(terms['data_gravity']+terms['data_magnetic'])
            penalty=float(self.weights['beta_gravity']*terms['regularization_gravity']
                +self.weights['beta_magnetic']*terms['regularization_magnetic']+self.weights['coupling']*terms['coupling'])
            return data,penalty,state['gradient_normalized'],terms
        m=self.modality;p=self.problem;residual=p.A[m]@q-p.d[m];delta=p.R@(q-p.reference[self.slice])
        data=.5*float(residual@residual);reg=.5*float(delta@delta);penalty=self.weights['beta_'+m]*reg
        gradient=p.A[m].T@residual+self.weights['beta_'+m]*(p.R.T@delta)
        terms={key:0. for key in ('data_gravity','data_magnetic','regularization_gravity','regularization_magnetic','coupling')}
        terms['data_'+m]=data;terms['regularization_'+m]=reg
        return data,penalty,gradient,terms

    def components(self,q):
        _,_,_,terms=self._state(q)
        engine=(float(terms['data_gravity']),float(terms['data_magnetic']),
            float(self.weights['beta_gravity']*terms['regularization_gravity']),
            float(self.weights['beta_magnetic']*terms['regularization_magnetic']),float(self.weights['coupling']*terms['coupling']))
        return {'phi_d':engine[0]+engine[1],'phi_m':(engine[2]+engine[3])+engine[4],
            'phi_engine':(((engine[0]+engine[1])+engine[2])+engine[3])+engine[4],'engine_terms':engine}

    def terms(self,q): return self._state(q)[3]

    def hessian(self,q,exact=False):
        self._state(q)
        if self.modality is None: base=self.problem.hessian(q,self.weights,exact=exact)
        else:
            p=self.problem;m=self.modality;beta=self.weights['beta_'+m]
            base=LinearOperator((self.n,self.n),dtype=np.float64,
                matvec=lambda v:p.A[m].T@(p.A[m]@v)+beta*(p.R.T@(p.R@v)))
        def action(v):
            self.budget.checkpoint();result=base@v;self.budget.checkpoint();return result
        return LinearOperator((self.n,self.n),dtype=np.float64,matvec=action,rmatvec=action)

    def evaluate(self,q,return_g=False,return_H=False):
        _,_,g,_=self._state(q);values=[self.components(q)['phi_engine']]
        if return_g: values.append(planner._snapshot(g))
        if return_H: values.append(self.hessian(q))
        self.budget.checkpoint()
        return tuple(values) if len(values)>1 else values[0]

    def exact_hessian(self,q): return self.hessian(q,exact=True)

    def binding_diagonal(self,q):
        if self.diagonal is None:
            p=self.problem;diagonals=[];reg=np.asarray(p.R.power(2).sum(axis=0)).ravel()
            for m in ((self.modality,) if self.modality else evaluation.MODALITIES):
                diagonals.append(np.sum(p.A[m]**2,axis=0)+self.weights['beta_'+m]*reg)
            diagonal=np.concatenate(diagonals)
            if self.modality is None:
                diagonal+=self.weights['coupling']*p.factor*p.cross_approximate.deriv2(self.start).diagonal()
            if not np.isfinite(diagonal).all() or np.any(diagonal<=0.): raise RuntimeError('M11: invalid fixed initial diagonal')
            self.diagonal=planner._snapshot(diagonal)
        return planner._snapshot(self.diagonal)

    def free_metric(self,q,indices):
        if type(indices) is not np.ndarray or indices.dtype!=np.int64 or indices.ndim!=1 or (
                np.any(indices<0) or np.any(indices>=self.n) or np.any(np.diff(indices)<=0)):
            raise ValueError('M11: exact sorted free indices')
        diagonal=np.zeros(self.n);diagonal[indices]=1./self.binding_diagonal(q)[indices]
        return LinearOperator((self.n,self.n),dtype=np.float64,matvec=lambda v:diagonal*v)

    def release_state(self): self.diagonal=None


def validation_wrms(problem,q,modality=None):
    predictions=problem.predict(q);result={}
    for m in ((modality,) if modality else evaluation.MODALITIES):
        survey=problem.plan[m];d=problem.development[m];n=len(survey['training_rows']);rows=d['rows'][n:]
        noise=d['noise_values'][n:,n:] if survey['noise']['kind']=='full_covariance' else d['noise_values'][n:]
        whitened=objective._whiten(evaluation._noise(survey,noise),predictions[m][rows]-d['observed'][n:])
        result[m]=float(np.sqrt((whitened@whitened)/len(rows)))
    return result


def _candidate_impl(problem,weights,start,stage,start_kind,inventory,allocation,budget,binding,modality,capture):
    budget.checkpoint()
    adapter=JointOptimizerObjective(problem,weights,start,stage,inventory,allocation,budget,modality)
    sl=adapter.slice
    declaration=solver.NonlinearBudget(budget.deadline,250,resources.MAX_RSS,allocation['admitted_bytes'],allocation['allocation_plan_sha256'])
    result=solver.solve_bounded_nonlinear(adapter,problem.lower[sl],problem.upper[sl],start,budget=declaration,binding=binding)
    # Capture the genuine accepted states before ANY later budget/replay call.
    # This is failure evidence only until exact scientific replay completes.
    capture.update(stage=stage,modality=modality,weights=dict(weights),start_kind=start_kind,
        identity=adapter.identity(),result=result,scientific_replay_completed=False)
    traces=result['trace']['models_q'];initial=adapter.evaluate(start,True)[1]
    norm=max(1.,float(np.linalg.norm(initial,np.inf)));verified=[];terms=[]
    for index,q in enumerate(traces):
        phi,g=adapter.evaluate(q,True);actual=evaluation.projected_kkt(q,g,problem.lower[sl],problem.upper[sl])/norm
        if phi!=result['trace']['phi_engine'][index] or actual!=result['trace']['kkt_normalized'][index]:
            raise RuntimeError('M11: actual optimizer trace replay mismatch')
        terms.append(tuple(adapter.terms(q)[key] for key in ('data_gravity','data_magnetic','regularization_gravity','regularization_magnetic','coupling')))
        verified.append(actual)
    stationary=result['status']=='converged' and bool(verified) and verified[-1]<=1e-5
    fullq=None;wrms={}
    if result['q'] is not None:
        fullq=problem.start.copy();fullq[sl]=result['q']
        wrms=validation_wrms(problem,fullq,modality)
    physical=traces*problem.scales[sl]
    return {'stage':stage,'modality':modality,'weights':dict(weights),'start_kind':start_kind,'identity':adapter.identity(),
        'result':result,'physical_trace':planner._snapshot(physical),
        'terms_trace':planner._snapshot(np.array(terms,dtype=np.float64).reshape(len(traces),5)),
        'validation_wrms':wrms,'stationarity_verified':stationary,'eligible':False}


def _candidate(problem,weights,start,stage,start_kind,inventory,allocation,budget,binding,modality=None):
    captured={}
    try: return _candidate_impl(problem,weights,start,stage,start_kind,inventory,allocation,budget,binding,modality,captured)
    except RuntimeError as exc:
        reason=budget.failure if budget.failure is not None else 'workflow_scientific_replay_failure'
        raise JointCalibrationFailure(reason,captured or None) from exc


def calibrate_joint_development(problem,budget):
    """Actual train-only fits; sealed/truth/optimizer arguments do not exist."""
    if type(problem) is not compiled.JointDevelopmentProblem or type(budget) is not resources.JointResourceBudget:
        raise TypeError('M11: exact compiled problem/measured workflow budget required')
    inventory=reviewed_source_inventory();allocation=allocation_plan(problem);digest=planner._digest(inventory)
    binding=solver.NonlinearBinding('physical_nonlinear_optimizer.solve_bounded_nonlinear',SOLVER_SHA,VENDOR_SHA,digest,solver.RUNTIME_EPOCH,solver.POLICY)
    candidates=[];selected={};stage=0
    def attempt(weights,start,stage,start_kind,modality=None):
        try: return _candidate(problem,weights,start,stage,start_kind,inventory,allocation,budget,binding,modality)
        except JointCalibrationFailure as exc:
            exc.verified_candidates=tuple(candidates);exc.source_inventory=dict(inventory);exc.optimizer_binding=asdict(binding)
            raise
    for m in evaluation.MODALITIES:
        sl=slice(0,problem.n) if m=='gravity' else slice(problem.n,2*problem.n)
        for beta in objective.BETAS:
            weights={'beta_gravity':beta if m=='gravity' else .0001,
                'beta_magnetic':beta if m=='magnetic' else .0001,'coupling':0.}
            record=attempt(weights,problem.start[sl],stage,'submitted',m)
            candidates.append(record);stage+=1
        eligible=[c for c in candidates if c['modality']==m and c['stationarity_verified']]
        if eligible:
            chosen=min(eligible,key=lambda c:(c['validation_wrms'][m],-c['weights']['beta_'+m],c['stage']))
            selected[m]=chosen['stage']
    status='failed';reason='no_stationary_separate_baseline';selection=None
    if len(selected)==2:
        pair=np.r_[candidates[selected['gravity']]['result']['q'],candidates[selected['magnetic']]['result']['q']]
        bg=candidates[selected['gravity']]['weights']['beta_gravity'];bm=candidates[selected['magnetic']]['weights']['beta_magnetic']
        baseline=validation_wrms(problem,pair)
        for coupling in objective.LAMBDAS[1:]:
            for start_kind,start in (('submitted',problem.start),('baseline',pair)):
                weights={'beta_gravity':bg,'beta_magnetic':bm,'coupling':coupling}
                record=attempt(weights,start,stage,start_kind)
                record['eligible']=record['stationarity_verified'] and all(record['validation_wrms'][m]<=1.05*baseline[m] for m in evaluation.MODALITIES)
                candidates.append(record);stage+=1
        positive=[c for c in candidates[16:] if c['eligible']]
        if positive:
            chosen=min(positive,key=lambda c:(sum(c['validation_wrms'][m]**2 for m in evaluation.MODALITIES)/2,
                c['weights']['coupling'],0 if c['start_kind']=='baseline' else 1,c['stage']))
            q=chosen['result']['q'];weights=chosen['weights'];chosen_stage=chosen['stage'];reason='validated_coupled_selection'
        else:
            q=pair;weights={'beta_gravity':bg,'beta_magnetic':bm,'coupling':0.};chosen_stage=None;reason='no_validated_coupling_benefit'
        status='selected';selection={'q':planner._snapshot(q),'weights':dict(weights),'stage':chosen_stage,
            'baseline_validation_wrms':baseline,'validation_wrms':validation_wrms(problem,q),'refit':False,'lambda0_refitted':False}
    result={'schema':'joint-survey-calibration-1','plan_sha256':problem.plan['plan_sha256'],
        'development_sha256':problem.development_sha256,'optimizer_binding':asdict(binding),'source_inventory':inventory,
        'allocation_plan':allocation,'status':status,'reason':reason,'candidates':tuple(candidates),
        'selected_baselines':selected,'selection':selection}
    # Full traces may exceed native input96MiB at the admitted maximum. Export
    # admission is checked before serialization; it is not input array admission.
    result['calibration_sha256']=planner._digest(result)
    try: budget.checkpoint()
    except RuntimeError as exc:
        failure=JointCalibrationFailure(budget.failure or 'workflow_scientific_replay_failure',None)
        failure.verified_candidates=tuple(candidates);failure.source_inventory=dict(inventory);failure.optimizer_binding=asdict(binding)
        raise failure from exc
    return result
