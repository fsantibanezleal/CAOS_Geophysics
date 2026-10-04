"""Independent development-only physical objective, not optimization/recovery."""

from copy import deepcopy
import math

import choclo
from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as MU0
import numpy as np
import pytest
import scipy.linalg as la
import torch

import joint_survey_plan as planner
import joint_survey_objective as objective
from test_joint_survey_plan import request,Hook,arrays
from test_joint_survey_oracles import explicit_faces,independent_bounds,models,torch_function


def kernels(req):
    bounds=independent_bounds(req)
    Gg=np.array([[choclo.prism.gravity_u(*r,*b,1.)*1e5 for b in bounds]
                 for r in req['gravity']['receivers_m']])
    field=req['magnetic']['inducing_field']; inc,dec=map(math.radians,[field['inclination_deg'],field['declination_deg']])
    f=np.array([math.cos(inc)*math.sin(dec),math.cos(inc)*math.cos(dec),-math.sin(inc)])
    m=field['amplitude_nt']*1e-9*f/MU0
    Gm=np.array([[np.array(choclo.prism.magnetic_field(*r,*b,*m))@f*1e9 for b in bounds]
                 for r in req['magnetic']['receivers_m']])
    return Gg,Gm


def body(covariance=False,receivers=6):
    req=request(); req['mesh']['active'][:]=False; req['mesh']['active'][[0,1,4,6,9,11]]=True
    if receivers==5:
        for modality in ('gravity','magnetic'):
            for key in ('receivers_m','mask','groups','partition'):
                req[modality][key]=req[modality][key][:5].copy()
            req[modality]['missing_reasons']=req[modality]['missing_reasons'][:5]
    for prop in ('density','susceptibility'):
        for key in ('lower','upper','start','reference'):
            req['prior'][prop][key]=req['prior'][prop][key][req['mesh']['active']]
    if covariance:
        for modality in ('gravity','magnetic'):
            req[modality]['noise'].update(kind='full_covariance',unit=req[modality]['unit']+'^2',
                                          cross_partition='possible_not_removed')
    plan=planner.plan_joint_survey(req); q,scale,direction=models(req); n=len(q)//2
    truth=q+.05*np.cos(np.arange(2*n)); Gg,Gm=kernels(req)
    development={'plan_sha256':plan['plan_sha256']}
    for modality,G,sigma,physical in (('gravity',Gg,.005,truth[:n]*scale[:n]),
                                     ('magnetic',Gm,1.,truth[n:]*scale[n:])):
        rows=np.r_[plan[modality]['training_rows'],plan[modality]['validation_rows']]
        observed=(G@physical)[rows]+sigma*np.array([.2,-.1,.3,-.2])
        noise=sigma**2*(.65*np.eye(len(rows))+.35*np.ones((len(rows),len(rows)))) if covariance else np.full(len(rows),sigma)
        development[modality]={'rows':rows,'observed':observed,'noise_values':noise,
                                'observations_sha256':'0'*64,'noise_sha256':'0'*64}
    result={'schema':'joint-survey-objective-request-1','survey_request':req,
            'development':development,'models':{'density_kg_m3':q[:n]*scale[:n],
            'susceptibility_si':q[n:]*scale[n:]},'direction_physical':direction*scale,
            'weights':{'beta_gravity':.01,'beta_magnetic':.1,'coupling':.1}}
    rehash(result)
    return result


def rehash(value):
    for modality in ('gravity','magnetic'):
        d=value['development'][modality]; survey=value['survey_request'][modality]
        binding={'rows':d['rows'],'observed':d['observed'],'unit':survey['unit'],
                 'plan_sha256':value['development']['plan_sha256']}
        d['observations_sha256']=planner._digest(binding)
        binding={'rows':d['rows'],'noise_values':d['noise_values'],'unit':survey['noise']['unit'],
                 'kind':survey['noise']['kind'],'plan_sha256':value['development']['plan_sha256']}
        d['noise_sha256']=planner._digest(binding)


def independent_R(req):
    # Independent sparse-active neighbor enumeration from the preceding oracle,
    # but explicit physical areas/distances, no candidate regularizer helpers.
    G,A,v,axes=explicit_faces(req); mesh=req['mesh']; nx=len(mesh['hx_m']);ny=len(mesh['hy_m'])
    full=np.flatnonzero(mesh['active']); widths=[mesh[k] for k in ('hx_m','hy_m','hz_m')]
    factors=[]
    for row,axis in zip(G,axes):
        pos=int(np.flatnonzero(row>0)[0]); f=int(full[pos])
        cell=(f%nx,(f//nx)%ny,f//(nx*ny)); distance=1/row[pos]
        area=math.prod(widths[a][cell[a]] for a in range(3) if a!=axis)
        factors.append(math.sqrt(area*distance/v.sum())*req['prior']['lengths_m'][axis])
    return np.vstack((np.diag(np.sqrt(v/v.sum())),np.asarray(factors)[:,None]*G))


def independent_function(value):
    req=value['survey_request']; q,scale,direction=models(req); n=len(q)//2
    Gg,Gm=kernels(req); R=torch.tensor(independent_R(req),dtype=torch.float64)
    reference=np.r_[req['prior']['density']['reference'],req['prior']['susceptibility']['reference']]/scale
    ref=torch.tensor(reference); cross=torch_function(req); pieces=[]
    for modality,G,s,beta in (('gravity',Gg,scale[:n],value['weights']['beta_gravity']),
                             ('magnetic',Gm,scale[n:],value['weights']['beta_magnetic'])):
        d=value['development'][modality]; indices=d['rows'][:2]
        if req[modality]['noise']['kind']=='full_covariance':
            W=la.solve_triangular(la.cholesky(d['noise_values'][:2,:2],lower=True),np.eye(2),lower=True)
        else: W=np.diag(1/d['noise_values'][:2])
        pieces.append((torch.tensor(W@(G[indices]*s)),torch.tensor(W@d['observed'][:2]),beta))
    def f(qt):
        gravity=pieces[0][0]@qt[:n]-pieces[0][1]; magnetic=pieces[1][0]@qt[n:]-pieces[1][1]
        r=R@(qt[:n]-ref[:n]);c=R@(qt[n:]-ref[n:])
        return (.5*(gravity@gravity+magnetic@magnetic)+.5*pieces[0][2]*(r@r)
                +.5*pieces[1][2]*(c@c)+value['weights']['coupling']*cross(qt))
    return f,q,scale,direction


@pytest.mark.parametrize('covariance',[False,True])
@pytest.mark.parametrize('receivers',[5,6])
def test_objective_chain(covariance,receivers):
    value=body(covariance,receivers); result=objective.evaluate_joint_objective(value)
    f,q,scale,direction=independent_function(value); qt=torch.tensor(q,dtype=torch.float64,requires_grad=True)
    expected=f(qt);gradient=torch.autograd.grad(expected,qt)[0].detach().numpy()
    hessian=torch.autograd.functional.hessian(f,qt).detach().numpy()
    np.testing.assert_allclose(result['objective'],expected.item(),atol=1e-10,rtol=1e-9)
    np.testing.assert_allclose(result['gradient_physical']*scale,gradient,atol=1e-10,rtol=1e-9)
    np.testing.assert_allclose(result['exact_hessian_vector_physical']*scale,hessian@direction,atol=1e-10,rtol=1e-9)
    # Independent full search-Hv: replace ONLY the exact quartic contribution
    # with its PSD Gram approximation, retaining real Choclo data and own R/W.
    req=value['survey_request'];G,A,volumes,_=explicit_faces(req);n=len(volumes)
    B=np.sqrt(volumes)[:,None]*A;a=G@q[:n];b=G@q[n:]
    block11=B.T@(B@(b*b));block12=-B.T@(B@(a*b));block22=B.T@(B@(a*a))
    u=G@direction[:n];w=G@direction[n:]
    approx_cross=2*req['prior']['coupling_length_m']**4/volumes.sum()*np.r_[
        G.T@(block11*u+block12*w),G.T@(block12*u+block22*w)]
    exact_cross=torch.autograd.functional.hessian(torch_function(req),qt).detach().numpy()@direction
    expected_approx=hessian@direction+value['weights']['coupling']*(approx_cross-exact_cross)
    np.testing.assert_allclose(result['approx_hessian_vector_physical']*scale,expected_approx,atol=1e-10,rtol=1e-9)
    assert direction@expected_approx>=-1e-10*max(1.,np.linalg.norm(expected_approx))
    slope=float(gradient@direction)
    for step in (1e-4,1e-5,1e-6):
        fd=(f(torch.tensor(q+step*direction)).item()-f(torch.tensor(q-step*direction)).item())/(2*step)
        assert abs(fd-slope)/max(1.,abs(slope))<=2e-6
    assert not result['diagnostics']['inverse_completed']
    assert not result['diagnostics']['sealed_consumed']


@pytest.mark.parametrize('bad',['rows2049','covariance_shape','descriptor_bytes','empty_container_citation'])
def test_objective_preflight_before_scans_copies_hash_or_engines(bad,monkeypatch):
    value=body()
    if bad=='rows2049': value['development']['gravity']['rows']=np.zeros(2049,np.int64)
    elif bad=='covariance_shape': value['development']['magnetic']['noise_values']=np.zeros((5,5))
    elif bad=='descriptor_bytes':
        n=70
        value['survey_request']['gravity'].update(receivers_m=np.zeros((n,3)),mask=np.ones(n,bool),
            missing_reasons=('a'*4096,)*n,groups=np.arange(n,dtype=np.int64),partition=np.zeros(n,np.int64))
    else: value['survey_request']['gravity']['source']['citation']=(((),)*32768,)*5
    for key in ('_finite','_snapshot','_digest'):
        monkeypatch.setattr(planner,key,lambda *a:pytest.fail('value work before complete preflight'))
    monkeypatch.setattr(planner.discretize,'TensorMesh',lambda *a,**k:pytest.fail('mesh before preflight'))
    monkeypatch.setattr(objective.gravity_forward,'forward_gravity',lambda *a:pytest.fail('physics before preflight'))
    with pytest.raises((TypeError,ValueError)): objective.evaluate_joint_objective(value)


def test_objective_result_ownership_and_inputs_unchanged():
    value=body(True);before=planner._digest(value)
    result=objective.evaluate_joint_objective(value)
    assert planner._digest(value)==before
    for a in arrays(result):
        assert a.flags.owndata and a.flags.c_contiguous and not a.flags.writeable
        assert all(not np.shares_memory(a,b) for b in arrays(value))
    terms=result['terms'];weights=value['weights']
    assert result['objective']==(terms['data_gravity']+terms['data_magnetic']
        +weights['beta_gravity']*terms['regularization_gravity']
        +weights['beta_magnetic']*terms['regularization_magnetic']+weights['coupling']*terms['coupling'])


@pytest.mark.parametrize('bad',['rows_dtype','rows_duplicate','rows_order','sealed_rows','observed_shape',
    'noise_shape','float32','array_subclass','extra_truth','injected_kernel','callback',
    'beta_hook','beta_int','beta_unfrozen','coupling_hook','direction_shape','plan_hash','value_hash','noise_hash'])
def test_contract_and_bindings(bad,monkeypatch):
    value=body()
    if bad=='rows_dtype': value['development']['gravity']['rows']=np.arange(4,dtype=np.int32)
    elif bad=='rows_duplicate': value['development']['gravity']['rows'][1]=0
    elif bad=='rows_order': value['development']['gravity']['rows']=np.array([1,0,2,3],np.int64)
    elif bad=='sealed_rows': value['development']['gravity']['rows']=np.array([0,1,4,5],np.int64)
    elif bad=='observed_shape': value['development']['gravity']['observed']=np.zeros(5)
    elif bad=='noise_shape': value['development']['gravity']['noise_values']=np.zeros((4,4))
    elif bad=='float32': value['models']['density_kg_m3']=value['models']['density_kg_m3'].astype('float32')
    elif bad=='array_subclass': value['models']['susceptibility_si']=value['models']['susceptibility_si'].view(type('Sub',(np.ndarray,),{}))
    elif bad=='extra_truth': value['truth']=np.zeros(6)
    elif bad=='injected_kernel': value['kernel']=np.zeros((6,6))
    elif bad=='callback': value['models']['density_kg_m3']=lambda *a:0.
    elif bad=='beta_hook': value['weights']['beta_gravity']=Hook()
    elif bad=='beta_int': value['weights']['beta_gravity']=1
    elif bad=='beta_unfrozen': value['weights']['beta_gravity']=.02
    elif bad=='coupling_hook': value['weights']['coupling']=Hook()
    elif bad=='direction_shape': value['direction_physical']=np.zeros(13)
    elif bad=='plan_hash': value['development']['plan_sha256']='f'*64
    elif bad=='value_hash': value['development']['gravity']['observations_sha256']='f'*64
    else: value['development']['magnetic']['noise_sha256']='f'*64
    monkeypatch.setattr(objective.gravity_forward,'forward_gravity',lambda *a:pytest.fail('forward before rejection'))
    if bad in ('rows_dtype','observed_shape','noise_shape','float32','array_subclass','extra_truth',
               'injected_kernel','callback','beta_hook','beta_int','beta_unfrozen','coupling_hook','direction_shape'):
        monkeypatch.setattr(planner,'_finite',lambda *a:pytest.fail('finite before ALL metadata'))
    with pytest.raises((TypeError,ValueError)): objective.evaluate_joint_objective(value)


@pytest.mark.parametrize('bad',['zero_sd','negative_sd','asymmetric','semidefinite','negative_cov',
                               'false_independence','nan_observed','model_bound'])
def test_noise_and_value_failures(bad,monkeypatch):
    value=body(bad in ('asymmetric','semidefinite','negative_cov','false_independence'))
    d=value['development']['gravity']
    if bad=='zero_sd': d['noise_values'][0]=0.
    elif bad=='negative_sd': d['noise_values'][0]=-1.
    elif bad=='asymmetric': d['noise_values'][0,1]+=.001
    elif bad=='semidefinite': d['noise_values'][0,:]=0.;d['noise_values'][:,0]=0.
    elif bad=='negative_cov': d['noise_values'][0,0]=-1.
    elif bad=='false_independence':
        value['survey_request']['gravity']['noise']['cross_partition']='declared_absent'
        value['development']['plan_sha256']=planner.plan_joint_survey(value['survey_request'])['plan_sha256']
    elif bad=='nan_observed': d['observed'][0]=np.nan
    else: value['models']['susceptibility_si'][0]=.101
    if bad!='nan_observed': rehash(value)
    monkeypatch.setattr(objective.gravity_forward,'forward_gravity',lambda *a:pytest.fail('forward before invalid noise/model'))
    with pytest.raises((ValueError,la.LinAlgError)): objective.evaluate_joint_objective(value)


@pytest.mark.parametrize('covariance',[False,True])
def test_validation_not_used_in_objective(covariance):
    value=body(covariance); original=objective.evaluate_joint_objective(value)
    changed=deepcopy(value)
    changed['development']['gravity']['observed'][2:]+=100.
    changed['development']['magnetic']['observed'][2:]-=10000.
    rehash(changed); result=objective.evaluate_joint_objective(changed)
    assert result['objective']==original['objective']
    for key in ('gradient_physical','exact_hessian_vector_physical','approx_hessian_vector_physical'):
        np.testing.assert_array_equal(result[key],original[key])
    changed['development']['gravity']['observed'][0]+=.01;rehash(changed)
    assert objective.evaluate_joint_objective(changed)['objective']!=original['objective']


def test_defining_regularization_mesh_source_and_no_callback_imports():
    import ast
    import hashlib
    import inspect
    from pathlib import Path
    from simpeg.regularization import RegularizationMesh
    # Its class __module__ names a public re-export wrapper. A defining property
    # is the correct trusted source locator for the actual mesh implementation.
    defining=Path(inspect.getsourcefile(RegularizationMesh.cell_gradient.fget))
    assert hashlib.sha256(defining.read_bytes()).hexdigest()=='5283b4f854906aeb05c216ff1c83174c99a7c53fe6a3ce8227b8ea483e785f44'
    tree=ast.parse(Path(objective.__file__).read_text(encoding='utf-8'))
    imported=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    imported += [a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
    assert not any(n and ('gravity_l2' in n or 'gravity_survey_l2' in n) for n in imported)
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                   and n.func.id in ('open','eval','exec','__import__') for n in ast.walk(tree))
