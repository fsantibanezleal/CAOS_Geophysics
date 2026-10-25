"""Read-only physical integration gate against an explicitly selected M11 tree.

This validation harness imports the product's native compiler/test oracle, not
an upload-selected production callback. All generated receipts remain external.
"""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
from pathlib import Path
import sys
from time import monotonic

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'data-pipeline'))

import numpy as np  # noqa: E402
from scipy.sparse.linalg import LinearOperator  # noqa: E402
import physical_nonlinear_optimizer as solver  # noqa: E402
import gravity_workflow_io as transport  # noqa: E402


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--m11-root',required=True)
    parser.add_argument('--data-root',required=True)
    parser.add_argument('--temp-root',required=True)
    args=parser.parse_args()
    root=Path(args.m11_root).resolve(strict=True)
    if not (root/'.git').exists(): raise ValueError('validation: explicit product checkout required')
    data=transport.external_root(args.data_root,'GEOPHYSICS_LOCAL_DATA_ROOT')
    temp=transport.external_root(args.temp_root,'GEOPHYSICS_LOCAL_TEMP_ROOT')
    # Loading transport already imported gravity_forward. The compiler must see
    # the exact same public source, not an accidental cross-tree replacement.
    import gravity_forward
    if Path(gravity_forward.__file__).read_bytes()!=(root/'data-pipeline/gravity_forward.py').read_bytes():
        raise ValueError('validation: gravity public sources differ between selected trees')
    sys.path[:0]=[str(root/'data-pipeline'),str(root/'tests/numerics')]
    from joint_survey_compiled import compile_joint_development
    from test_joint_survey_objective import body,independent_function
    records=[]
    deadline=monotonic()+1800.
    for covariance in (False,True):
        value=body(covariance)
        problem=compile_joint_development({'schema':'joint-survey-compile-request-1',
            'survey_request':value['survey_request'],'development':value['development']})
        weights=value['weights']
        f,q,_,direction=independent_function(value)
        import torch
        qt=torch.tensor(q,dtype=torch.float64,requires_grad=True)
        gradient=torch.autograd.grad(f(qt),qt)[0].detach().numpy()
        exact=torch.autograd.functional.hessian(f,qt).detach().numpy()
        state=problem.state(q,weights)
        np.testing.assert_allclose(state['gradient_normalized'],gradient,rtol=1e-9,atol=1e-10)
        np.testing.assert_allclose(problem.hessian(q,weights,exact=True)@direction,exact@direction,rtol=1e-9,atol=1e-10)
        assert direction@(state['search_hessian']@direction)>=0.
        for boundary in (False,True):
            start=problem.lower.copy() if boundary else problem.start.copy()
            class Adapter:
                def __init__(self):
                    h=problem.hessian(start,weights)
                    self.diagonal=np.array([(h@np.eye(len(start))[i])[i] for i in range(len(start))])
                    self.released=False
                def identity(self):
                    return {'mode':'nonlinear_gauss_newton','runtime_epoch':solver.RUNTIME_EPOCH,
                        'objective_sha256':problem.development_sha256,'source_inventory_sha256':'2'*64,
                        'q_unit':'normalized_two_property_blocks','physical_unit':'kg_m3_and_si',
                        'physical_scale':(float(problem.scales[0]),float(problem.scales[-1])),
                        'parameter_count':len(start),'observation_rows':sum(len(problem.plan[m]['training_rows']) for m in ('gravity','magnetic')),
                        'observation_components':2,'beta_engine':1.,'stage_index':0,'allocation_plan_sha256':'3'*64}
                def evaluate(self,q,return_g=False,return_H=False):
                    s=problem.state(q,weights);result=[s['objective']]
                    if return_g: result.append(s['gradient_normalized'])
                    if return_H: result.append(s['search_hessian'])
                    return tuple(result) if len(result)>1 else result[0]
                def components(self,q):
                    s=problem.state(q,weights);t=s['terms']
                    operands=(float(t['data_gravity']),float(t['data_magnetic']),
                        float(weights['beta_gravity']*t['regularization_gravity']),
                        float(weights['beta_magnetic']*t['regularization_magnetic']),float(weights['coupling']*t['coupling']))
                    return {'phi_d':float(t['data_gravity']+t['data_magnetic']),
                        'phi_m':float(weights['beta_gravity']*t['regularization_gravity']
                            +weights['beta_magnetic']*t['regularization_magnetic']+weights['coupling']*t['coupling']),
                        'phi_engine':s['objective'],'engine_terms':operands}
                def binding_diagonal(self,q): return self.diagonal.copy()
                def free_metric(self,q,indices):
                    d=np.zeros(len(q));d[indices]=1./self.diagonal[indices]
                    return LinearOperator((len(q),len(q)),dtype=np.float64,matvec=lambda v:d*v)
                def exact_hessian(self,q): return problem.hessian(q,weights,exact=True)
                def release_state(self): self.released=True
            adapter=Adapter()
            source=solver.NonlinearBinding('physical_nonlinear_optimizer.solve_bounded_nonlinear',
                solver.SOURCE_SHA256,solver.VENDOR_SOURCE_SHA256,'2'*64,solver.RUNTIME_EPOCH,solver.POLICY)
            budget=solver.NonlinearBudget(deadline,250,2*1024**3,1024**2,'3'*64)
            with redirect_stdout(io.StringIO()):
                result=solver.solve_bounded_nonlinear(adapter,problem.lower,problem.upper,start,budget=budget,binding=source)
            records.append({'full_covariance':covariance,'boundary_start':boundary,'result':result})
            print(covariance,boundary,result['status'],result['reason'],result['iterations'],flush=True)
            assert adapter.released
            trace=result['trace']
            scale=max(1.,float(np.linalg.norm(problem.state(start,weights)['gradient_normalized'],np.inf)))
            for index,point in enumerate(trace['models_q']):
                actual=problem.state(point,weights)
                assert actual['objective']==trace['phi_engine'][index]
                kkt=float(np.linalg.norm(solver.feasible_gradient(point,actual['gradient_normalized'],problem.lower,problem.upper),np.inf))/scale
                assert kkt==trace['kkt_normalized'][index]
                if index:
                    previous=problem.state(trace['models_q'][index-1],weights)
                    slope=float(previous['gradient_normalized']@(point-trace['models_q'][index-1]))
                    margin=(actual['objective']-previous['objective'])-1e-4*slope
                    assert slope==trace['projected_slopes'][index-1]<0.
                    assert margin==trace['armijo_margins'][index-1]<=0.
    inventory={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        Path(solver.__file__),Path(__file__),root/'data-pipeline/joint_survey_compiled.py',
        root/'data-pipeline/joint_survey_objective.py',root/'data-pipeline/joint_survey_plan.py',
        root/'data-pipeline/gravity_forward.py',root/'data-pipeline/magnetic_forward.py',
        root/'tests/numerics/test_joint_survey_objective.py',root/'tests/numerics/test_joint_survey_oracles.py')}
    transport.publish_archive(data,temp,'nonlinear-joint.gza',{'schema':'nonlinear-joint-validation-1',
        'source_sha256':inventory,'records':tuple(records),'complete_pipeline_accepted':False})
    assert all(r['result']['status']=='converged' for r in records), 'actual physical integration failure retained'
    return 0


if __name__=='__main__': raise SystemExit(main())
