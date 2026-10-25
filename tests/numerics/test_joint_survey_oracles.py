"""Independent M11 structure assembly/autograd and physical forward oracles."""

import math

import choclo
from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as MU0
import numpy as np
import pytest
import torch

import gravity_forward
import magnetic_forward
import joint_survey_structure as st
from test_joint_survey_plan import request


def explicit_faces(req):
    """Enumerate shared active faces, no candidate/SimPEG/discretize operators."""
    mesh=req['mesh']; h=[mesh[k] for k in ('hx_m','hy_m','hz_m')]; nx,ny,nz=map(len,h)
    full=np.flatnonzero(mesh['active']); index={int(f):i for i,f in enumerate(full)}
    gradients=[]; averages=[]; axes=[]
    for axis in range(3):
        dims=[nx,ny,nz]; dims[axis]+=1
        for k in range(dims[2]):
            for j in range(dims[1]):
                for i in range(dims[0]):
                    point=[i,j,k]; t=point[axis]
                    if not 0<t<len(h[axis]): continue
                    left=point.copy(); left[axis]-=1
                    f0=left[0]+nx*left[1]+nx*ny*left[2]
                    f1=point[0]+nx*point[1]+nx*ny*point[2]
                    if f0 not in index or f1 not in index: continue
                    row=np.zeros(len(full)); avg=np.zeros(len(full))
                    distance=(h[axis][t-1]+h[axis][t])/2
                    row[index[f0]]=-1/distance; row[index[f1]]=1/distance
                    avg[index[f0]]=.5; avg[index[f1]]=.5
                    gradients.append(row); averages.append(avg); axes.append(axis)
    G=np.asarray(gradients).reshape(-1,len(full)); A=np.asarray(averages).reshape(-1,len(full)).T
    volumes=np.array([h[0][f%nx]*h[1][(f//nx)%ny]*h[2][f//(nx*ny)] for f in full])
    return G,A,volumes,np.asarray(axes)


def models(req):
    n=len(req['prior']['density']['lower'])
    q=np.r_[np.linspace(-.6,.4,n)+.13*np.sin(np.arange(n)*2.),
            .7+.2*np.cos(np.arange(n)*1.7)]
    scale=np.r_[np.full(n,req['prior']['density']['scale']),
                np.full(n,req['prior']['susceptibility']['scale'])]
    direction=np.sin(np.arange(2*n)+.3); direction/=np.linalg.norm(direction)
    return q,scale,direction


def structure_request(req,q,scale,direction):
    n=len(q)//2
    return {'schema':'joint-survey-structure-request-1','survey_request':req,
            'density_kg_m3':q[:n]*scale[:n],'susceptibility_si':q[n:]*scale[n:],
            'direction_physical':direction*scale}


def torch_function(req):
    G,A,v,_=explicit_faces(req)
    g=torch.tensor(G,dtype=torch.float64); b=torch.tensor(np.sqrt(v)[:,None]*A,dtype=torch.float64)
    factor=req['prior']['coupling_length_m']**4/v.sum(); n=len(v)
    def objective(q):
        a=g@q[:n]; d=g@q[n:]
        return factor*torch.sum((b@(a*a))*(b@(d*d))-(b@(a*d))**2)
    return objective


@pytest.mark.parametrize('sparse',[False,True])
def test_cross_gradient_derivatives(sparse):
    req=request()
    if sparse:
        req['mesh']['active'][[2,5,8]]=False
        for prop in ('density','susceptibility'):
            for key in ('lower','upper','start','reference'):
                req['prior'][prop][key]=req['prior'][prop][key][req['mesh']['active']]
    q,scale,direction=models(req); result=st.evaluate_joint_structure(structure_request(req,q,scale,direction))
    f=torch_function(req); qt=torch.tensor(q,dtype=torch.float64,requires_grad=True)
    value=f(qt); grad=torch.autograd.grad(value,qt)[0].detach().numpy()
    hess=torch.autograd.functional.hessian(f,qt).detach().numpy()
    np.testing.assert_allclose(result['objective'],value.item(),atol=1e-10,rtol=1e-9)
    np.testing.assert_allclose(result['gradient_physical']*scale,grad,atol=1e-10,rtol=1e-9)
    np.testing.assert_allclose(result['exact_hessian_vector_physical']*scale,hess@direction,atol=1e-10,rtol=1e-9)
    slope=float(grad@direction)
    for step in (1e-4,1e-5,1e-6):
        plus=f(torch.tensor(q+step*direction)).item(); minus=f(torch.tensor(q-step*direction)).item()
        assert abs((plus-minus)/(2*step)-slope)/max(1.,abs(slope))<=2e-6
    G,A,v,axes=explicit_faces(req); a=G@q[:len(v)]; b=G@q[len(v):]
    B=np.sqrt(v)[:,None]*A
    block11=B.T@(B@(b*b)); block12=-(B.T@(B@(a*b))); block22=B.T@(B@(a*a))
    u=G@direction[:len(v)]; w=G@direction[len(v):]
    expected=2*req['prior']['coupling_length_m']**4/v.sum()*np.r_[
        G.T@(block11*u+block12*w), G.T@(block12*u+block22*w)]
    np.testing.assert_allclose(result['approx_hessian_vector_physical']*scale,expected,atol=1e-10,rtol=1e-9)
    assert direction@expected>=-1e-10*max(1.,np.linalg.norm(expected))
    averaged_r=np.column_stack([A[:,axes==i]@a[axes==i] for i in range(3)])
    averaged_c=np.column_stack([A[:,axes==i]@b[axes==i] for i in range(3)])
    centre=np.linalg.norm(np.cross(averaged_r,averaged_c),axis=1)
    np.testing.assert_allclose(result['cell_centre_cross_gradient'],centre,atol=1e-10,rtol=1e-9)
    plotted_energy=req['prior']['coupling_length_m']**4*np.sum(v*centre**2)/v.sum()
    assert abs(plotted_energy-result['objective'])>1e-8
    assert result['optimizer_completed'] is False


@pytest.mark.parametrize('kind',['constant','parallel','antiparallel','orthogonal'])
def test_structure_null_and_sign_controls(kind):
    req=request()
    x=np.tile(np.arange(3),4).astype(float)/3; y=np.tile(np.repeat(np.arange(2),3),2).astype(float)/2
    first=x.copy(); second=.5+.2*x
    if kind=='constant': first[:]=.3
    if kind=='antiparallel': second=.8-.2*x
    if kind=='orthogonal': second=.5+.2*y
    q=np.r_[first,second]; _,scale,direction=models(req)
    result=st.evaluate_joint_structure(structure_request(req,q,scale,direction))
    if kind=='orthogonal': assert result['objective']>1e-8
    else: assert abs(result['objective'])<=1e-12


def independent_bounds(req):
    h=[req['mesh'][k] for k in ('hx_m','hy_m','hz_m')]
    edges=[float(o)+np.r_[0.,np.cumsum(w)] for o,w in zip(req['mesh']['origin_m'],h)]
    result=[]; index=0
    for k in range(len(h[2])):
        for j in range(len(h[1])):
            for i in range(len(h[0])):
                if req['mesh']['active'][index]:
                    result.append([edges[0][i],edges[0][i+1],edges[1][j],edges[1][j+1],edges[2][k],edges[2][k+1]])
                index+=1
    return np.asarray(result)


def test_prism_oracles():
    req=request(); q,scales,_=models(req); n=len(q)//2
    rho=q[:n]*scales[:n]; chi=q[n:]*scales[n:]
    frame={k:req['frame'][k] for k in ('kind','axes','length_unit','vertical_positive')}
    gr=gravity_forward.forward_gravity({'schema':'gravity-prism-forward-request-1',
        'engine':gravity_forward.ENGINE,'frame':frame,'mesh':req['mesh'],
        'receivers_m':req['gravity']['receivers_m'],'density_kg_m3':rho})
    mr=magnetic_forward.forward_magnetic({'schema':'magnetic-prism-forward-request-1',
        'engine':magnetic_forward.ENGINE,'frame':frame,'mesh':req['mesh'],
        'receivers_m':req['magnetic']['receivers_m'],'susceptibility_si':chi,
        'inducing_field':req['magnetic']['inducing_field']})
    bounds=independent_bounds(req)
    Jg=np.array([[choclo.prism.gravity_u(*r,*b,1.)*1e5 for b in bounds]
                 for r in req['gravity']['receivers_m']])
    field=req['magnetic']['inducing_field']; i=math.radians(field['inclination_deg']); d=math.radians(field['declination_deg'])
    f=np.array([math.cos(i)*math.sin(d),math.cos(i)*math.cos(d),-math.sin(i)])
    unit_m=field['amplitude_nt']*1e-9*f/MU0
    components=np.array([[choclo.prism.magnetic_field(*r,*b,*unit_m) for b in bounds]
                         for r in req['magnetic']['receivers_m']])*1e9
    Jm=np.einsum('nca,a->nc',components,f)
    np.testing.assert_allclose(gr['jacobian_mgal_per_kg_m3'],Jg,atol=1e-10,rtol=2e-8)
    np.testing.assert_allclose(gr['gz_up_mgal'],Jg@rho,atol=1e-10,rtol=2e-8)
    np.testing.assert_allclose(mr['linear_jacobian_nt_per_si'],Jm,atol=1e-7,rtol=2e-8)
    np.testing.assert_allclose(mr['linear_tmi_nt'],Jm@chi,atol=1e-7,rtol=2e-8)
    np.testing.assert_allclose(mr['field_components_nt'],np.einsum('nca,c->na',components,chi),atol=1e-7,rtol=2e-8)


@pytest.mark.parametrize('bad',['density_shape','direction_float32','chi_subclass','density_nonfinite','model_bounds'])
def test_structure_negative_metadata_and_values(bad,monkeypatch):
    req=request(); q,scale,direction=models(req); body=structure_request(req,q,scale,direction)
    if bad=='density_shape': body['density_kg_m3']=np.zeros(13)
    elif bad=='direction_float32': body['direction_physical']=body['direction_physical'].astype('float32')
    elif bad=='chi_subclass': body['susceptibility_si']=body['susceptibility_si'].view(type('Sub',(np.ndarray,),{}))
    elif bad=='density_nonfinite': body['density_kg_m3'][0]=np.nan
    else: body['susceptibility_si'][0]=.101
    monkeypatch.setattr(st,'CrossGradient',lambda *a,**k:pytest.fail('engine before rejection'))
    if bad in ('density_shape','direction_float32','chi_subclass'):
        monkeypatch.setattr(st.planner,'_finite',lambda *a:pytest.fail('planner finite before ALL metadata'))
    with pytest.raises((TypeError,ValueError)): st.evaluate_joint_structure(body)


def test_structure_snapshots_and_actual_engine_failures(monkeypatch):
    req=request(); q,scale,direction=models(req); body=structure_request(req,q,scale,direction)
    result=st.evaluate_joint_structure(body)
    for key in ('gradient_physical','exact_hessian_vector_physical',
                'approx_hessian_vector_physical','cell_centre_cross_gradient'):
        a=result[key]
        assert a.flags.owndata and a.flags.c_contiguous and not a.flags.writeable
        assert all(not np.shares_memory(a,body[k]) for k in ('density_kg_m3','susceptibility_si','direction_physical'))
    monkeypatch.setattr(st.CrossGradient,'deriv',lambda *a:np.full(24,np.nan))
    with pytest.raises(RuntimeError): st.evaluate_joint_structure(body)


def test_disjoint_sources_not_a_coupling_certificate():
    req=request(); n=12; rho=np.zeros(n); rho[0]=500.; chi=np.zeros(n); chi[-1]=.06
    # Independent sources have no common occupied cell. The cross-gradient can
    # vanish where changes have no shared support; it cannot certify co-geology.
    q=np.r_[rho/750.,chi/.03]; scale=np.r_[np.full(n,750.),np.full(n,.03)]
    result=st.evaluate_joint_structure(structure_request(req,q,scale,np.zeros(2*n)))
    assert abs(result['objective'])<=1e-12
    bounds=independent_bounds(req)
    gravity=np.array([choclo.prism.gravity_u(*rx,*bounds[0],500.)*1e5 for rx in req['gravity']['receivers_m']])
    assert np.max(abs(gravity))>1e-5
    field=req['magnetic']['inducing_field']; i=math.radians(field['inclination_deg']); d=math.radians(field['declination_deg'])
    f=np.array([math.cos(i)*math.sin(d),math.cos(i)*math.cos(d),-math.sin(i)])
    m=.06*field['amplitude_nt']*1e-9*f/MU0
    magnetic=np.array([choclo.prism.magnetic_field(*rx,*bounds[-1],*m) for rx in req['magnetic']['receivers_m']])*1e9
    assert np.max(abs(magnetic@f))>1.
    assert result['optimizer_completed'] is False


@pytest.mark.parametrize('name,expected',[
    ('CrossGradient','85ff1c1e39ec9e8973707a7debd83706db23027b13832298c4e468b052e3298c'),
    ('RegularizationMesh','942ac3fffded92f48c7a5294575082713ebde716918d0e8fbe117c084607ff8f'),
    ('BaseSimilarityMeasure','aae7dbd3cb4887246f38c8ceba4fe8fbeeb5592110341635e06fdb70246a92b5'),
    ('Wires','6bdd7455d17467ed547091526735df560a35c9b204ab2f4105dfab096ed6c90e'),
    ('TensorMesh','2e8a97a5449f490dbf4128c8696833a8770c896d260f5ecf087e2f622b3be65d'),
    ('DiffOperators','f3c7ca3c54a50232202d08bf9768411273fcee7ce95eb5b110a79de6c42db70a')])
def test_trusted_loaded_structural_source_pins(name,expected):
    import hashlib
    import inspect
    from pathlib import Path
    from simpeg.regularization import CrossGradient,RegularizationMesh,BaseSimilarityMeasure
    from simpeg.maps import Wires
    from discretize import TensorMesh
    from discretize.operators.differential_operators import DiffOperators
    target={'CrossGradient':CrossGradient,'RegularizationMesh':RegularizationMesh,
            'BaseSimilarityMeasure':BaseSimilarityMeasure,'Wires':Wires,
            'TensorMesh':TensorMesh,'DiffOperators':DiffOperators}[name]
    # External trusted harness reads the already loaded official class source,
    # not a user-supplied path. No callable/file-I/O/source-installation change.
    assert hashlib.sha256(Path(inspect.getsourcefile(target)).read_bytes()).hexdigest()==expected
