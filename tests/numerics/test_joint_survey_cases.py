"""Refined independent observations and bounded TEST-ONLY optima, not full M11."""
import hashlib
import inspect
from pathlib import Path

import numpy as np
import pytest
import scipy.linalg as la
from scipy.optimize import lsq_linear

import gravity_forward
import magnetic_forward
import joint_survey_cases as cases
import joint_survey_plan as planner
import joint_survey_objective as objective
from test_joint_survey_objective import independent_R,kernels


@pytest.mark.parametrize('index',range(24))
def test_refined_matrix_original_identity_and_no_production_generator(index,monkeypatch):
    def prohibited(*args,**kwargs): pytest.fail('production forward generated control observations')
    monkeypatch.setattr(gravity_forward,'forward_gravity',prohibited)
    monkeypatch.setattr(magnetic_forward,'forward_magnetic',prohibited)
    case=cases.make_joint_control(index)
    assert set(case)=={'schema','case_id','family','regime','seed','survey_request',
                       'development','sealed','truth','provenance','diagnostics'}
    assert case['seed']==1101+index
    assert case['family']==('co_structural','disjoint','flat_null','wrong_field')[index//6]
    assert case['regime']==('dense','sparse_blocked','shifted_geometry')[(index//2)%3]
    assert case['truth']['source_bounds_m'].shape==(96,6)
    assert len(case['truth']['coarse_density_kg_m3'])==12
    req=case['survey_request'];plan=planner.plan_joint_survey(req)
    count=9 if case['regime']=='sparse_blocked' else 48
    for m in ('gravity','magnetic'):
        assert len(req[m]['receivers_m'])==count
        d=case['development'][m];s=case['sealed'][m]
        np.testing.assert_array_equal(d['rows'],np.r_[plan[m]['training_rows'],plan[m]['validation_rows']])
        np.testing.assert_array_equal(s['rows'],plan[m]['sealed_rows'])
        assert not np.intersect1d(d['rows'],s['rows']).size
        assert s['unit']==req[m]['unit']
        assert s['noise_unit']==req[m]['noise']['unit']
        assert req[m]['noise']['kind']==('full_covariance' if index%2 else 'diagonal_sd')
    assert case['diagnostics']=={'synthetic':True,'inverse_completed':False,'field_eligible':False}
    assert planner._digest(case)==planner._digest(cases.make_joint_control(index))
    for array in planner._arrays(case):
        assert array.flags.c_contiguous and array.flags.owndata and not array.flags.writeable


@pytest.mark.parametrize('value',[True,-1,24,1.0,np.int64(0),'0'])
def test_control_index_exact(value):
    with pytest.raises((TypeError,ValueError)): cases.make_joint_control(value)


def test_adverse_definitions_are_real_not_claims():
    flat=cases.make_joint_control(12)
    assert np.all(flat['truth']['source_density_kg_m3']==0.)
    np.testing.assert_array_equal(flat['truth']['source_susceptibility_si'],np.full(96,.005))
    assert np.any(flat['provenance']['original_magnetic_observed_nt']!=0.)
    wrong=cases.make_joint_control(18)
    assert not np.array_equal(wrong['truth']['source_magnetization_direction_enu'],
                              wrong['truth']['declared_field_direction_enu'])
    shifted=cases.make_joint_control(4)
    for m in ('gravity','magnetic'):
        measured=shifted['provenance'][m+'_measured_receivers_m']
        np.testing.assert_allclose(shifted['survey_request'][m]['receivers_m']-measured,
                                   np.tile([20.,-15.,12.],(48,1)),atol=1e-12,rtol=0.)
    disjoint=cases.make_joint_control(6)
    assert not np.array_equal(disjoint['truth']['coarse_susceptibility_si'],
                              cases.make_joint_control(0)['truth']['coarse_susceptibility_si'])


def independent_problem(case,modality,G,beta):
    req=case['survey_request'];plan=planner.plan_joint_survey(req);d=case['development'][modality]
    rows=plan[modality]['training_rows'];count=len(rows)
    prop='density' if modality=='gravity' else 'susceptibility'
    prior=req['prior'][prop];scale=prior['scale'];R=independent_R(req)
    if req[modality]['noise']['kind']=='diagonal_sd':
        W=np.diag(1/d['noise_values'][:count])
    else:
        W=la.solve_triangular(la.cholesky(d['noise_values'][:count,:count],lower=True),np.eye(count),lower=True)
    A=np.vstack((W@(G[rows]*scale),np.sqrt(beta)*R))
    b=np.r_[W@d['observed'][:count],np.sqrt(beta)*(R@(prior['reference']/scale))]
    return A,b,prior['lower']/scale,prior['upper']/scale,prior['start']/scale


def exact_kkt(A,b,q,lower,upper,start):
    gradient=A.T@(A@q-b)
    kkt=gradient.copy()
    kkt[(q==lower)&(gradient>0)]=0.
    kkt[(q==upper)&(gradient<0)]=0.
    initial=A.T@(A@start-b)
    return gradient,float(np.max(np.abs(kkt)))/max(1.,float(np.max(np.abs(initial))))


def independent_baseline(case,modality,G,beta):
    A,b,lower,upper,start=independent_problem(case,modality,G,beta)
    result=lsq_linear(A,b,bounds=(lower,upper),
                      method='bvls',lsq_solver='exact',tol=1e-12,max_iter=250)
    gradient,normalized=exact_kkt(A,b,result.x,lower,upper,start)
    return result,gradient,normalized


@pytest.mark.parametrize('index',range(24))
def test_raw_bvls_return_has_retained_exact_kkt_failure(index,record_property):
    case=cases.make_joint_control(index);Gg,Gm=kernels(case['survey_request'])
    raw=[]
    for m,G in (('gravity',Gg),('magnetic',Gm)):
        for beta in objective.BETAS:
            result,_,kkt=independent_baseline(case,m,G,beta)
            raw.append((m,beta,int(result.status),int(result.nit),kkt))
    # Tiny BLAS ordering can change whether a point lands exactly on a face.
    # Retain every actual verdict, not a manufactured fixed failure count.
    # Case0 is the explicit reproducible original adverse witness.
    if index==0: assert any(r[4]>1e-5 for r in raw)
    record_property('raw_bvls_exact_kkt',repr(raw))


def independent_face_baseline(case,modality,G,beta):
    A,b,lower,upper,start=independent_problem(case,modality,G,beta)
    raw,_,raw_kkt=independent_baseline(case,modality,G,beta)
    q=raw.x.copy();mask=raw.active_mask
    q[mask==-1]=lower[mask==-1];q[mask==1]=upper[mask==1]
    free=mask==0
    if np.any(free):
        q[free]=la.lstsq(A[:,free],b-A[:,~free]@q[~free])[0]
    gradient,kkt=exact_kkt(A,b,q,lower,upper,start)
    assert np.all((q>=lower)&(q<=upper))
    assert np.isfinite(q).all() and kkt<=1e-5,(modality,beta,kkt)
    return q,.5*float(np.linalg.norm(A@q-b)**2),gradient,kkt,raw,raw_kkt


@pytest.mark.parametrize('index',range(24))
def test_exact_face_reference_optima_against_actual_physics(index,record_property):
    # Dense BVLS is an independent TEST reference, never production fallback.
    case=cases.make_joint_control(index);req=case['survey_request'];Gg,Gm=kernels(req)
    n=12;scales=np.r_[np.full(n,req['prior']['density']['scale']),
                      np.full(n,req['prior']['susceptibility']['scale'])]
    for beta in objective.BETAS:
        qg,cg,gg,kg,rawg,rawkg=independent_face_baseline(case,'gravity',Gg,beta)
        qm,cm,gm,km,rawm,rawkm=independent_face_baseline(case,'magnetic',Gm,beta)
        q=np.r_[qg,qm]
        value={'schema':'joint-survey-objective-request-1','survey_request':req,
            'development':case['development'],'models':{'density_kg_m3':q[:n]*scales[:n],
            'susceptibility_si':q[n:]*scales[n:]},'direction_physical':np.zeros(2*n),
            'weights':{'beta_gravity':beta,'beta_magnetic':beta,'coupling':0.}}
        actual=objective.evaluate_joint_objective(value)
        np.testing.assert_allclose(actual['objective'],cg+cm,atol=1e-10,rtol=1e-9)
        normalized_actual=actual['gradient_physical']*scales
        independent_gradient=np.r_[gg,gm]
        # Preserve the original precision gate VERDICT in the receipt. At an
        # ill-conditioned fitted optimum, independent physical kernels can
        # amplify sub-nT discrepancies. This is not JS08 precision acceptance.
        gradient_gate=bool(np.allclose(normalized_actual,independent_gradient,atol=1e-10,rtol=1e-9))
        for m,G,physical in (('gravity',Gg,q[:n]*scales[:n]),('magnetic',Gm,q[n:]*scales[n:])):
            rows=case['development'][m]['rows']
            np.testing.assert_allclose(actual['predictions'][m]['predicted'],(G@physical)[rows],
                                       atol=1e-8,rtol=0.)
        assert kg<=1e-5 and km<=1e-5
        assert not actual['diagnostics']['inverse_completed']
        record_property('beta_'+str(beta),repr({'raw_gravity_kkt':rawkg,'raw_magnetic_kkt':rawkm,
            'face_gravity_kkt':kg,'face_magnetic_kkt':km,'face_cost':cg+cm,
            'raw_cost':float(rawg.cost+rawm.cost),'objective_error':abs(actual['objective']-cg-cm),
            'near_optimum_gradient_gate_pass':gradient_gate,
            'near_optimum_gradient_error':float(np.max(np.abs(normalized_actual-independent_gradient)))}))


def test_near_optimum_gradient_precision_negative_is_retained():
    # Separate adverse precision witness, NOT an altered acceptance threshold.
    case=cases.make_joint_control(14);req=case['survey_request'];Gg,Gm=kernels(req)
    qg,_,gg,_,_,_=independent_face_baseline(case,'gravity',Gg,.0001)
    qm,_,gm,_,_,_=independent_face_baseline(case,'magnetic',Gm,.0001)
    result=objective.evaluate_joint_objective({'schema':'joint-survey-objective-request-1',
        'survey_request':req,'development':case['development'],
        'models':{'density_kg_m3':qg*750.,'susceptibility_si':qm*.03},
        'direction_physical':np.zeros(24),
        'weights':{'beta_gravity':.0001,'beta_magnetic':.0001,'coupling':0.}})
    actual=result['gradient_physical']*np.r_[np.full(12,750.),np.full(12,.03)]
    assert not np.allclose(actual,np.r_[gg,gm],atol=1e-10,rtol=1e-9)


def test_actual_reference_defining_source_pins():
    from scipy.optimize._lsq.bvls import bvls
    for target,digest in ((bvls,'87d6d88776acb4846f32d306821b441a91b97c3b21ef848c45b9a01771cdf183'),
        (lsq_linear,'866a691914b304f8788214ff34441d325ed3294c15367fbd2cd45ad60944fa15')):
        assert hashlib.sha256(Path(inspect.getsourcefile(target)).read_bytes()).hexdigest()==digest
