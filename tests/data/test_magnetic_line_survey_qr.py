"""Independent QR physics/objective/native controls before candidate39."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_survey as core
import magnetic_line_survey_qr as qr
import magnetic_line_survey_hp as hp
import magnetic_line_survey_capacity_qr as capacity
from test_magnetic_line_survey_hp import dense_case


@pytest.mark.parametrize('weighted',[False,True])
def test_independent_actions_objective_svd_and_original_gradient(weighted):
    np,xyz,sources,sigma,y,scales,a,b=dense_case(weighted)
    damping=.0001
    model=core.GlobalOperator(xyz,sources,sigma,chunk_rows=2,chunk_sources=2)
    p=1/np.sqrt(np.sum(a*a,axis=0)+damping)
    h=np.vstack((a,np.sqrt(damping)*np.eye(3)));B=h*p
    actual=qr.augmented_matrix(model,damping,hp.preconditioner(model,damping))
    np.testing.assert_allclose(actual,B,rtol=1e-13)
    z=np.array([2.,-3.,4.]);u=np.arange(9,dtype=np.float64)-3
    np.testing.assert_allclose(actual@z,B@z,rtol=1e-13,atol=1e-13)
    np.testing.assert_allclose(actual.T@u,B.T@u,rtol=1e-13,atol=1e-13)
    assert u@(actual@z)==pytest.approx(z@(actual.T@u),rel=1e-13)
    rhs=np.concatenate((b,np.zeros(3)));c=p*z
    expected=np.sum((a@c-b)**2)+damping*np.dot(c,c)
    assert np.sum((B@z-rhs)**2)==pytest.approx(expected,rel=1e-13)
    assert abs(expected-(np.sum((a@c-b)**2)+damping*np.dot(z,z)))>.0001
    solved=qr.solve_qr(model,y,damping)
    # Independent SVD, no production construction or QR/P helper in oracle.
    U,s,Vt=np.linalg.svd(h,full_matrices=False)
    oracle=Vt.T@((U.T@rhs)/s)
    np.testing.assert_allclose(solved['scaled_coefficients'],oracle,rtol=1e-9,atol=1e-9)
    np.testing.assert_allclose(solved['coefficients'],oracle/scales,rtol=1e-9,atol=1e-9)
    grad=a.T@(a@solved['scaled_coefficients']-b)+damping*solved['scaled_coefficients']
    d=solved['receipt']['original_diagnostics']
    assert d['stationarity_inf']==pytest.approx(np.max(np.abs(grad)),abs=3e-12)
    assert d['stationarity_relative']<=1e-9
    assert d['objective']==pytest.approx(np.sum((h@oracle-rhs)**2),rel=1e-12)
    assert solved['receipt']['epoch']==qr.EPOCH
    assert solved['receipt']['lapack_info']==0
    assert 'iterations' not in solved['receipt'] and 'istop' not in solved['receipt']
    _,R=np.linalg.qr(B,mode='reduced')
    inverse=np.linalg.inv(R)
    bound=np.linalg.norm(R,'fro')*np.linalg.norm(inverse,'fro')
    assert solved['receipt']['condition_upper_bound']==pytest.approx(bound,rel=1e-10)
    assert bound>=np.linalg.cond(B,2)
    np.testing.assert_allclose(solved['triangular']@solved['triangular_inverse'],np.eye(3),rtol=1e-12,atol=1e-12)


def test_correlated_columns_and_zero_target():
    np,xyz,sources,_,y,_,_,_=dense_case(False)
    correlated=sources.copy();correlated[1]=correlated[0]+np.array([1e-8,0.,0.]);correlated.flags.writeable=False
    G=1/np.sqrt(np.sum((xyz[:,None,:]-correlated[None,:,:])**2,axis=2))
    A=G/np.std(G,axis=0)
    H=np.vstack((A,.01*np.eye(3)));rhs=np.r_[y,np.zeros(3)]
    U,s,Vt=np.linalg.svd(H,full_matrices=False);oracle=Vt.T@((U.T@rhs)/s)
    state=qr.solve_qr(core.GlobalOperator(xyz,correlated),y,.0001)
    np.testing.assert_allclose(state['scaled_coefficients'],oracle,rtol=1e-7,atol=1e-8)
    zero=np.zeros(6);zero.flags.writeable=False
    state=qr.solve_qr(core.GlobalOperator(xyz,sources),zero,.0001)
    assert state['receipt']['original_diagnostics']['stationarity_relative']==0
    assert state['receipt']['original_diagnostics']['objective']==0


@pytest.mark.parametrize('wrong',[True,0.,-1.,float('nan'),float('inf')])
def test_invalid_lambda_precedes_native_allocation(wrong,monkeypatch):
    np,xyz,sources,_,y,_,_,_=dense_case(False)
    monkeypatch.setattr(qr,'augmented_matrix',lambda *a:pytest.fail('allocated before invalid lambda refusal'))
    with pytest.raises(core.SurveyError):qr.solve_qr(core.GlobalOperator(xyz,sources),y,wrong)


def test_rank_native_info_and_condition_failure_state(monkeypatch):
    import scipy.linalg.lapack as lapack
    np,xyz,sources,_,y,_,_,_=dense_case(False)
    real=lapack.dgels
    def rank_failure(*args,**kwargs):
        factor,solution,_=real(*args,**kwargs);return factor,solution,2
    monkeypatch.setattr(lapack,'dgels',rank_failure)
    model=core.GlobalOperator(xyz,sources)
    with pytest.raises(core.SurveyError):qr.solve_qr(model,y,.0001)
    assert model.qr_failure_state['receipt']['lapack_info']==2
    assert model.qr_failure_state['receipt']['numerical_verdict']=='fail'
    assert model.qr_failure_state['receipt']['coefficients_sha256']==hp.content_sha256(model.qr_failure_state['coefficients'])
    monkeypatch.setattr(lapack,'dgels',real)
    diagnostic=qr.triangular_diagnostic
    def condition_failure(r):
        inverse,info,_=diagnostic(r);return inverse,info,1e8
    monkeypatch.setattr(qr,'triangular_diagnostic',condition_failure)
    model=core.GlobalOperator(xyz,sources)
    with pytest.raises(core.SurveyError):qr.solve_qr(model,y,.0001)
    assert model.qr_failure_state['receipt']['condition_upper_bound']==1e8
    assert model.qr_failure_state['receipt']['lapack_info']==0
    assert model.qr_failure_state['receipt']['numerical_verdict']=='fail'


def test_workspace_overflow_and_copy_controls(monkeypatch):
    import scipy.linalg.lapack as lapack
    for n,m,L in ((True,3,100),(6,3,True),(6,3,5),(8000000,65536,None),(6,3,2**31)):
        with pytest.raises(core.SurveyError):qr.dense_capacity(n,m,lwork=L)
    monkeypatch.setattr(lapack,'dgels_lwork',lambda *a,**k:(float('inf'),0))
    with pytest.raises(core.SurveyError):qr.dense_capacity(6,3)
    np,xyz,sources,_,y,_,_,_=dense_case(False)
    monkeypatch.undo()
    real=lapack.dgels
    def copied(*args,**kwargs):
        factor,solution,info=real(*args,**kwargs);return factor.copy(order='F'),solution.copy(order='F'),info
    monkeypatch.setattr(lapack,'dgels',copied)
    assert qr.solve_qr(core.GlobalOperator(xyz,sources),y,.0001)['receipt']['numerical_verdict']=='component_pass'
    def unexpected(*args,**kwargs):
        factor,solution,info=real(*args,**kwargs);return np.vstack((factor,factor)),solution,info
    monkeypatch.setattr(lapack,'dgels',unexpected)
    with pytest.raises(core.SurveyError):qr.solve_qr(core.GlobalOperator(xyz,sources),y,.0001)


def test_singular_triangular_info_not_a_solver_pass():
    np,_,_,_,_,_,_,_=dense_case(False)
    inverse,info,_=qr.triangular_diagnostic(np.zeros((3,3),dtype='<f8',order='F'))
    assert info==1 and np.isfinite(inverse).all()


def test_actual_97_shape_bound_and_member_negative():
    training=[294,168,195,249];validation=[33,66,66,33]
    sources=[[66,45,48,57],[148,91,101,127],[240,137,164,203],[292,168,193,247]]
    cap,proof=capacity.plan_capacity(363,training,validation,sources,logical_members=125,arrays=104)
    assert proof['logical_members']==127 and proof['mandatory_fit_count']==97
    assert proof['maximum_fit_count']==97 and len(proof['qr_shapes'])==16
    assert proof['additional_dense_bytes']==42559584
    expected=sum(8*(8*(training[f]+sources[g][f])*sources[g][f]**2+8*sources[g][f]**3)
        for g in range(4) for f in range(1,4))+max(8*(training[0]+row[0])*row[0]**2+8*row[0]**3 for row in sources)
    assert proof['factorization_work_bound']==expected
    assert cap['kernel_pair_bound']<10**15
    assert proof['kernel_passes_per_fit']==6
    assert proof['additional_physical_members']==4
    with pytest.raises(core.SurveyError):capacity.plan_capacity(363,training,validation,sources,logical_members=191)
