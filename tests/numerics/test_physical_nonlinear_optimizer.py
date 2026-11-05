"""Native nonlinear contract, actual prism data and actual quartic coupling."""
from dataclasses import replace
from time import monotonic

import discretize
import numpy as np
import pytest
from scipy.sparse.linalg import LinearOperator
from simpeg import maps
from simpeg.regularization import CrossGradient

import gravity_forward
import physical_nonlinear_optimizer as solver


class ActualObjective:
    def __init__(self):
        mesh=discretize.TensorMesh([[1.,1.3],[1.2,1.4],[1.,1.5]],origin=[0.,0.,-3.])
        self.n=mesh.nC
        active=np.ones(self.n,dtype=bool)
        active[2]=False
        self.n=int(active.sum())
        wire=maps.Wires(('density',self.n),('susceptibility',self.n))
        self.cross=CrossGradient(mesh,wire_map=wire,active_cells=active,approx_hessian=False)
        self.psd=CrossGradient(mesh,wire_map=wire,active_cells=active,approx_hessian=True)
        receivers=np.array([[.2,.3,1.],[2.,.5,1.2],[.6,2.,1.3]])
        response=gravity_forward.forward_gravity({'schema':'gravity-prism-forward-request-1',
            'frame':dict(gravity_forward.FRAME),
            'mesh':{'hx_m':np.array([1.,1.3]),'hy_m':np.array([1.2,1.4]),'hz_m':np.array([1.,1.5]),
                    'origin_m':np.array([0.,0.,-3.]),'active':active},
            'receivers_m':receivers,'density_kg_m3':np.zeros(self.n),'engine':gravity_forward.ENGINE})
        self.A=np.zeros((len(receivers),2*self.n))
        self.A[:,:self.n]=response['jacobian_mgal_per_kg_m3']*1000./.005
        self.reference=np.linspace(.1,.6,2*self.n)
        self.d=self.A@self.reference
        self.beta=.1
        self.weight=.01
        self.start=np.full(2*self.n,.2)
        h=self.hessian(self.start,False)
        self.diag=np.array([(h@np.eye(2*self.n)[i])[i] for i in range(2*self.n)])
        self.released=False

    def identity(self):
        return {'mode':'nonlinear_gauss_newton','runtime_epoch':solver.RUNTIME_EPOCH,
            'objective_sha256':'1'*64,'source_inventory_sha256':'2'*64,
            'q_unit':'normalized_two_property_blocks','physical_unit':'kg_m3_and_si',
            'physical_scale':(1000.,.01),'parameter_count':2*self.n,'observation_rows':3,
            'observation_components':1,'beta_engine':1.,'stage_index':0,'allocation_plan_sha256':'3'*64}

    def components(self,q):
        residual=self.A@q-self.d
        delta=q-self.reference
        data=float(.5*(residual@residual))
        regularization=float(.5*self.beta*(delta@delta))
        coupling=float(self.weight*self.cross(q))
        penalty=regularization+coupling
        return {'phi_d':data,'phi_m':penalty,'phi_engine':data+regularization+coupling,
                'engine_terms':(data,0.,regularization,0.,coupling)}

    def hessian(self,q,exact):
        state=q.copy()
        coupling=self.cross if exact else self.psd
        return LinearOperator((len(q),len(q)),dtype=np.float64,
            matvec=lambda v:self.A.T@(self.A@v)+self.beta*v+self.weight*coupling.deriv2(state,v))

    def evaluate(self,q,return_g=False,return_H=False):
        value=self.components(q)['phi_engine']
        result=[value]
        if return_g:
            result.append(self.A.T@(self.A@q-self.d)+self.beta*(q-self.reference)+self.weight*self.cross.deriv(q))
        if return_H: result.append(self.hessian(q,False))
        return tuple(result) if len(result)>1 else value

    def exact_hessian(self,q): return self.hessian(q,True)
    def binding_diagonal(self,q): return self.diag.copy()
    def free_metric(self,q,indices):
        diagonal=np.zeros(len(q));diagonal[indices]=1./self.diag[indices]
        return LinearOperator((len(q),len(q)),dtype=np.float64,matvec=lambda v:diagonal*v)
    def release_state(self): self.released=True


def binding():
    return solver.NonlinearBinding('physical_nonlinear_optimizer.solve_bounded_nonlinear',
        solver.SOURCE_SHA256,solver.VENDOR_SOURCE_SHA256,'2'*64,solver.RUNTIME_EPOCH,solver.POLICY)


def budget(steps=250):
    return solver.NonlinearBudget(monotonic()+60.,steps,2*1024**3,1024**2,'3'*64)


def run(obj=None,*,start=None,steps=250,admission=None,source=None):
    obj=ActualObjective() if obj is None else obj
    start=obj.start.copy() if start is None else start
    return solver.solve_bounded_nonlinear(obj,np.zeros(len(start)),np.ones(len(start)),start,
        budget=budget(steps) if admission is None else admission,binding=binding() if source is None else source)


def test_exact_bounds_nextafter_is_not_active():
    lower=np.zeros(3);upper=np.ones(3)
    q=np.array([0.,1.,np.nextafter(0.,1.)]);g=np.array([1.,-1.,1.])
    np.testing.assert_array_equal(solver.feasible_gradient(q,g,lower,upper),[0.,0.,1.])


def test_actual_quartic_exact_and_psd_hv_are_distinct():
    obj=ActualObjective();q=obj.reference+.08*np.cos(np.arange(2*obj.n))
    h=solver.audit_hessians(obj,q)
    v=np.sin(np.arange(len(q))+.4)
    step=1e-6
    fd=(obj.evaluate(q+step*v,True)[1]-obj.evaluate(q-step*v,True)[1])/(2*step)
    np.testing.assert_allclose(h['exact']@v,fd,rtol=2e-6,atol=1e-9)
    assert v@(h['search_psd']@v)>=0.
    assert not np.allclose(h['exact']@v,h['search_psd']@v,rtol=1e-8,atol=1e-12)


@pytest.mark.parametrize('at_lower',[False,True])
def test_actual_native_nonlinear_solve(at_lower):
    obj=ActualObjective()
    start=np.zeros(len(obj.start)) if at_lower else obj.start.copy()
    result=run(obj,start=start)
    assert result['status']=='converged',result['reason']
    assert result['kkt_normalized']<=1e-5
    assert 0<result['iterations']<=250 and obj.released
    trace=result['trace']
    assert np.all(np.diff(trace['phi_engine'])<0.)
    assert np.all(trace['projected_slopes']<0.) and np.all(trace['armijo_margins']<=0.)
    assert np.all(trace['cg_counts']<=512) and np.all(trace['line_search_counts']<=30)
    assert np.any(trace['branches']==1)
    if at_lower:
        assert trace['branches'][0]==0 and not trace['cg_residuals_available'][0]
    for index,q in enumerate(trace['models_q']):
        phi,g=obj.evaluate(q,True)
        assert phi==trace['phi_engine'][index]
        scale=max(1.,np.linalg.norm(obj.evaluate(start,True)[1],np.inf))
        assert np.linalg.norm(solver.feasible_gradient(q,g,np.zeros(len(q)),np.ones(len(q))),np.inf)/scale==trace['kkt_normalized'][index]
    assert all(not a.flags.writeable for a in trace.values())


@pytest.mark.parametrize('fault',['steps','deadline','memory','vendor','source','inventory','allocation','start','dtype'])
def test_preflight_rejects_without_objective_evaluation(fault):
    obj=ActualObjective();b=budget();s=binding();start=obj.start.copy()
    if fault=='steps': b=replace(b,remaining_steps=251)
    elif fault=='deadline': b=replace(b,deadline=monotonic()+1801.)
    elif fault=='memory': b=replace(b,admitted_bytes=2*1024**3+1)
    elif fault=='vendor': s=replace(s,vendor_source_sha256='f'*64)
    elif fault=='source': s=replace(s,optimizer_source_sha256='f'*64)
    elif fault=='inventory': s=replace(s,source_inventory_sha256='f'*64)
    elif fault=='allocation': b=replace(b,allocation_plan_sha256='f'*64)
    elif fault=='start': start[0]=-1.
    else: start=start.astype(np.float32)
    obj.evaluate=lambda *a,**k:pytest.fail('evaluate before complete preflight')
    with pytest.raises(ValueError): run(obj,start=start,admission=b,source=s)


def test_expired_deadline_retains_empty_trace_and_releases():
    obj=ActualObjective()
    result=run(obj,admission=replace(budget(),deadline=monotonic()-1.))
    assert result['reason']=='wall_cap' and result['q'] is None
    assert result['iterations']==0 and obj.released


def test_step_cap_not_convergence():
    result=run(steps=0)
    assert result['status']=='nonconverged' and result['reason']=='iteration_cap'
    assert result['iterations']==0 and len(result['trace']['models_q'])==1


def test_native_limits_and_no_copied_cg(monkeypatch):
    actual=solver.optimization.ProjectedGNCG.findSearchDirection
    calls=[]
    def native(self):
        calls.append((self.cg_maxiter,self.cg_rtol,self.cg_atol,self.maxIterLS,self.maxIter))
        return actual(self)
    monkeypatch.setattr(solver.optimization.ProjectedGNCG,'findSearchDirection',native)
    assert run()['status']=='converged'
    assert calls and all(c==(512,1e-6,0.,30,250) for c in calls)


@pytest.mark.parametrize('fault',['diagonal','metric','exact','identity','nonfinite'])
def test_runtime_contract_failures(fault):
    obj=ActualObjective()
    if fault=='diagonal': obj.binding_diagonal=lambda q:np.zeros(len(q))
    elif fault=='metric': obj.free_metric=lambda q,i:LinearOperator((len(q),len(q)),dtype=np.float64,matvec=lambda v:2.*v)
    elif fault=='exact': obj.exact_hessian=lambda q:np.eye(len(q))
    elif fault=='identity':
        original=obj.evaluate
        def changed(*a,**k):
            value=original(*a,**k)
            obj.identity=lambda :dict(ActualObjective.identity(obj),stage_index=1)
            return value
        obj.evaluate=changed
    else: obj.evaluate=lambda *a,**k:float('nan')
    result=run(obj)
    assert result['status']=='failed' and obj.released


def test_accepted_state_survives_later_hessian_failure():
    obj=ActualObjective();original=obj.evaluate;count=0
    def failing(q,return_g=False,return_H=False):
        nonlocal count
        if return_H:
            count+=1
            if count==2: raise RuntimeError('later actual H failure')
        return original(q,return_g,return_H)
    obj.evaluate=failing
    result=run(obj)
    assert result['reason']=='engine_error' and result['iterations']==1
    assert len(result['trace']['models_q'])==2 and len(result['trace']['branches'])==1
    assert not np.array_equal(result['q'],obj.start)


def test_rounded_zero_objective_change_is_not_accepted():
    obj=ActualObjective()
    original=obj.evaluate
    def plateau(q,return_g=False,return_H=False):
        value=original(q,return_g,return_H)
        return (1.,*value[1:]) if isinstance(value,tuple) else 1.
    obj.evaluate=plateau
    obj.components=lambda q:{'phi_d':1.,'phi_m':0.,'phi_engine':1.,'engine_terms':(1.,0.,0.,0.,0.)}
    result=run(obj)
    assert result['status']=='nonconverged' and result['reason']=='line_search_failed'
    assert result['iterations']==0


def test_exact_stationary_bound_stops_without_direction():
    obj=ActualObjective()
    original=obj.evaluate
    def outward(q,return_g=False,return_H=False):
        value=original(q,return_g,return_H)
        if return_g: return (value[0],np.ones(len(q)),*value[2:])
        return value
    obj.evaluate=outward
    obj.binding_diagonal=lambda q:pytest.fail('stationary bound requested direction')
    result=run(obj,start=np.zeros(len(obj.start)))
    assert result['status']=='converged' and result['iterations']==0
    assert result['kkt_normalized']==0.


def test_five_operand_order_preserved_without_regrouping_tolerance():
    obj=ActualObjective()
    native=solver._NativeRecorded(obj,obj.identity(),np.zeros(len(obj.start)),np.ones(len(obj.start)),budget())
    terms=(1e16,0.,1.,1.,1.)
    actual=(((terms[0]+terms[1])+terms[2])+terms[3])+terms[4]
    obj.components=lambda q:{'phi_d':1e16,'phi_m':3.,'phi_engine':actual,'engine_terms':terms}
    assert 1e16+3.!=actual
    assert native.components(obj.start,actual)['engine_terms']==terms
    obj.components=lambda q:{'phi_d':1e16,'phi_m':3.,'phi_engine':1e16+3.,'engine_terms':terms}
    with pytest.raises(RuntimeError): native.components(obj.start,1e16+3.)
