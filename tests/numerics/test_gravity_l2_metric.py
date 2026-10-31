"""CPU5 fixed natural IC0/Joseph and exact live-buffer admission controls."""
from time import monotonic
import weakref

import numpy as np
import pytest
import scipy.linalg as la
import scipy.sparse as sp

import gravity_l2_metric as metric


@pytest.mark.parametrize('a',[1,3,7,13])
def test_MP01_same_stored_L_D_paired_inverse_and_rounded_F_SPD(a):
    matrix=sp.diags((-np.ones(max(0,a-1)),np.full(a,2.25),-np.ones(max(0,a-1))),
                    (-1,0,1),shape=(a,a),format='csr')
    lower,pivots=metric._factor(matrix,monotonic()+120.)
    assert np.all(lower.diagonal()==1.) and np.all(pivots>0.)
    a0=lower.toarray()@np.diag(pivots)@lower.toarray().T
    inverse=la.solve(a0,np.eye(a),assume_a='pos')
    rng=np.random.Generator(np.random.PCG64(20261004+a))
    b=rng.normal(size=(4,a))
    t=metric._paired(lower,pivots,b.T,monotonic()+120.)
    s=np.eye(4)+b@t
    f=la.cho_solve(la.cho_factor(.5*(s+s.T),lower=True),t.T).T
    for perturbation in (0.,.01):
        stored=f+perturbation*rng.normal(size=f.shape)
        c=np.eye(a)-stored@b
        expected=c@inverse@c.T+stored@stored.T
        assert np.min(la.eigvalsh(expected))>0.
        for _ in range(7):
            v=rng.normal(size=a)
            np.testing.assert_allclose(metric._paired(lower,pivots,v,monotonic()+120.),
                                       inverse@v,rtol=1e-12,atol=1e-12)
            np.testing.assert_allclose(metric._joseph(lower,pivots,b,stored,v,monotonic()+120.),
                                       expected@v,rtol=1e-12,atol=1e-12)


@pytest.mark.parametrize('fault',['dense','dtype','indices','nan','duplicate','stencil','positive_offdiag','pivot'])
def test_MP03_refuse_foreign_stencil_index_nonfinite_and_nonpositive(fault):
    a=sp.diags((-np.ones(4),np.full(5,2.25),-np.ones(4)),(-1,0,1),format='csr')
    if fault=='dense': a=a.toarray()
    if fault=='dtype': a=a.astype(np.float32)
    if fault=='indices': a.indices=a.indices.astype(np.int64)
    if fault=='nan': a.data[0]=np.nan
    if fault=='duplicate':
        a=sp.csr_matrix((np.array([1.,1.]),np.array([0,0],dtype=np.int32),
                         np.array([0,2,2,2,2,2],dtype=np.int32)),shape=(5,5))
    if fault=='stencil': a=sp.csr_matrix(np.ones((9,9)))
    if fault=='positive_offdiag': a.data[1]=1.
    if fault=='pivot': a=sp.csr_matrix(np.array([[1.,-2.],[-2.,1.]]))
    with pytest.raises((ValueError,ArithmeticError)): metric._factor(a,monotonic()+120.)


def test_MP03_expired_factor_does_not_publish_partial_L_D():
    with pytest.raises(metric.DeadlineExceeded):
        metric._factor(sp.eye(2,format='csr'),monotonic()-1.)


def test_MP05_exact_phase_bound_not_observed_RSS_and_original_cap():
    bound=metric.allocation(2048,2048,4096,False)
    assert bound['native']==1140850688 and bound['interval']==838860800
    assert bound['setup']==2088763392 and bound['line_search']==2123956240
    assert bound['maximum']==2123956240 and bound['ceiling']==2147483648
    assert bound['maximum']<=bound['ceiling']
    with pytest.raises(ValueError): metric.allocation(2048,2048,4096,True)
    for values in [(2049,2048,4096,False),(2048,2048,4097,False),(True,1,1,False),
                   (1,2,1,False),(1,1,1,0)]:
        with pytest.raises(ValueError): metric.allocation(*values)


def test_MP02_actual_free_principal_face_scatter_and_explicit_disposal():
    reg=sp.diags((-np.ones(4),np.full(5,2.25),-np.ones(4)),(-1,0,1),format='csr')
    free=np.array([0,2,4],dtype=np.int64)
    g=np.arange(20,dtype=np.float64).reshape(4,5)/100.
    value=metric.JosephMetric(reg,g,sp.eye(4,format='csr'),free,monotonic()+120.)
    assert value.live_payload_bytes>0
    references=[weakref.ref(x) for x in (value.b,value.f,value.lower,value.pivots)]
    actual=value.apply(np.ones(5))
    assert actual.shape==(5,) and np.all(actual[[1,3]]==0.) and np.inner(actual,np.ones(5))>0.
    value.close()
    assert value.live_payload_bytes==0 and all(ref() is None for ref in references)
    with pytest.raises(ValueError): value.apply(np.ones(5))


def test_MP04_failed_native_factor_has_no_partial_metric_publication(monkeypatch):
    def failed(*args,**kwargs): raise RuntimeError('retained native factor refusal')
    monkeypatch.setattr(metric.la,'cho_factor',failed)
    with pytest.raises(RuntimeError,match='native factor refusal'):
        metric.JosephMetric(sp.eye(3,format='csr'),np.ones((4,3)),sp.eye(4,format='csr'),
                            np.arange(3,dtype=np.int64),monotonic()+120.)


def test_MP04_owner_native_success_closes_metric_before_partition_return(monkeypatch):
    import gravity_l2 as l2
    from test_gravity_l2 import tiny,noise
    req,data,prior,_,_=tiny()
    problem=l2._build_problem(req,data,noise(),prior,np.arange(4,dtype=np.int64),.01)
    native=metric.JosephMetric
    created=[]
    def build(*args,**kwargs):
        value=native(*args,**kwargs)
        created.append(value)
        return value
    monkeypatch.setattr(metric,'JosephMetric',build)
    solved=l2._solve_partition(problem,prior)
    assert solved['status']=='converged',solved
    assert created and all(v.live_payload_bytes==0 for v in created)
    assert all(v.lower is v.pivots is v.b is v.f is v.free is None for v in created)
