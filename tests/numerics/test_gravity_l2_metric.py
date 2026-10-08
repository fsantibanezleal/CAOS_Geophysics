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


def test_MP04_actual_wrapper_copies_and_setup_scratch_released_before_action(monkeypatch):
    # Inspect actual installed wrapper arguments. A sampled RSS cannot establish
    # these independent copies or the end of their simultaneously-live phase.
    lower=sp.diags((-np.ones(4),np.full(5,2.25),-np.ones(4)),(-1,0,1),format='csr')
    g=np.arange(20,dtype=np.float64).reshape(4,5)/100.
    triangular=metric.spsolve_triangular
    gstrs=metric._superlu.gstrs
    factor=metric.la.cho_factor
    solve=metric.la.cho_solve
    state={}
    scratch=[]
    calls=[]
    def native(*args,**kwargs):
        original_a,original_b=state['operands']
        # gstrs arguments: trans, N, L.nnz, L.data, L.indices, L.indptr,
        # N, U.nnz, U.data, U.indices, U.indptr, b. The Python wrapper
        # already owns independent sparse and dense copies before native entry.
        assert not np.shares_memory(args[3],original_a.data)
        assert not np.shares_memory(args[8],original_a.data)
        assert not np.shares_memory(args[11],original_b)
        for v in (args[3],args[8],args[11]): scratch.append(weakref.ref(v))
        calls.append((args[0],original_b.shape))
        return gstrs(*args,**kwargs)
    def tri(a,b,**kwargs):
        state['operands']=(a,b)
        try: return triangular(a,b,**kwargs)
        finally: state.clear()
    def chol(a,**kwargs):
        result=factor(a,**kwargs)
        scratch.extend((weakref.ref(a),weakref.ref(result[0])))
        return result
    def rhs(*args,**kwargs):
        result=solve(*args,**kwargs)
        scratch.append(weakref.ref(result))
        return result
    monkeypatch.setattr(metric._superlu,'gstrs',native)
    monkeypatch.setattr(metric,'spsolve_triangular',tri)
    monkeypatch.setattr(metric.la,'cho_factor',chol)
    monkeypatch.setattr(metric.la,'cho_solve',rhs)
    value=metric.JosephMetric(lower,g,sp.eye(4,format='csr'),np.arange(5,dtype=np.int64),monotonic()+120.)
    assert len(calls)==2 and all(ref() is None for ref in scratch)
    before=len(calls)
    assert np.isfinite(value.apply(np.ones(5))).all()
    assert len(calls)==before+2 and all(ref() is None for ref in scratch)
    value.close()


@pytest.mark.parametrize('chained',[False,True])
def test_MP04_exception_traceback_cannot_retain_dense_setup_scratch(monkeypatch,chained):
    # Keep the REAL exception/traceback alive, as an external failure receipt can.
    # Disposal must not depend on exception deletion or a cycle collector.
    lower=sp.eye(3,format='csr')
    paired=metric._paired
    refs=[]
    def record(*args,**kwargs):
        result=paired(*args,**kwargs)
        refs.append(weakref.ref(result))
        return result
    def failed(a,**kwargs):
        refs.append(weakref.ref(a))
        if chained:
            def cause(operand): raise ValueError('retained inner native error')
            try: cause(a)
            except ValueError as exc: raise RuntimeError('retained Cholesky failure') from exc
        raise RuntimeError('retained Cholesky failure')
    monkeypatch.setattr(metric,'_paired',record)
    monkeypatch.setattr(metric.la,'cho_factor',failed)
    with pytest.raises(RuntimeError,match='retained Cholesky') as caught:
        metric.JosephMetric(lower,np.ones((4,3)),sp.eye(4,format='csr'),
                            np.arange(3,dtype=np.int64),monotonic()+120.)
    assert caught.value.__traceback__ is not None
    if chained: assert type(caught.value.__cause__) is ValueError
    assert refs and all(ref() is None for ref in refs)


@pytest.mark.parametrize('fault',['data_short','index_short','index_rank','ptr_rank'])
def test_MP03_malformed_CSR_storage_refuses_before_factor_copy(monkeypatch,fault):
    matrix=sp.eye(3,format='csr')
    if fault=='data_short': matrix.data=matrix.data[:-1]
    if fault=='index_short': matrix.indices=matrix.indices[:-1]
    if fault=='index_rank': matrix.indices=matrix.indices.reshape(1,-1)
    if fault=='ptr_rank': matrix.indptr=matrix.indptr.reshape(1,-1)
    def forbidden(*args,**kwargs): raise AssertionError('copy before structural refusal')
    monkeypatch.setattr(sp.csr_matrix,'copy',forbidden)
    with pytest.raises(ValueError): metric._factor(matrix,monotonic()+120.)


@pytest.mark.parametrize('fault',['platform','python','binary','threads','objects'])
def test_MP03_unknown_workspace_tuple_remains_closed(monkeypatch,fault):
    if fault=='platform': monkeypatch.setattr(metric.sys,'platform','linux')
    if fault=='python': monkeypatch.setattr(metric.sys,'version_info',(3,12,3))
    if fault=='binary': monkeypatch.setattr(metric,'_LOADED_PINS',('0'*64,)*3)
    if fault=='threads': monkeypatch.setenv('OPENBLAS_NUM_THREADS','2')
    if fault=='objects': monkeypatch.setattr(metric.sys,'getsizeof',lambda value:9999)
    with pytest.raises(ValueError): metric._workspace_closure()


def test_MP02_old_face_callback_does_not_keep_optimizer_parent_alive(monkeypatch):
    import gravity_l2 as l2
    from test_gravity_l2 import tiny,noise
    req,data,prior,_,_=tiny()
    problem=l2._build_problem(req,data,noise(),prior,np.arange(4,dtype=np.int64),.01)
    opt=l2._RecordedProjectedGNCG(problem,prior,monotonic()+120.)
    opt.xc=np.zeros(5)
    opt.iter=0
    opt.H=sp.eye(5,format='csr')
    diagonal=sp.eye(5,format='csr')
    opt._diagonal_metric=diagonal
    opt._set_free_metric()
    owner=opt._joseph
    callback=opt.approxHinv
    ref=weakref.ref(opt)
    arrays=[weakref.ref(v) for v in (owner.lower,owner.b,owner.f,owner.pivots)]
    opt.close_metric()
    del opt
    assert ref() is None and all(v() is None for v in arrays)
    # Retaining even a native operator from an old face cannot resurrect it.
    with pytest.raises(ValueError,match='disposed'): callback@np.ones(5)


@pytest.mark.parametrize('fault',['false_recurrence','count201'])
def test_MP06_false_native_recurrence_or_count_cannot_bypass_true_H(monkeypatch,fault):
    import gravity_l2 as l2
    from test_gravity_l2 import tiny,noise
    req,data,prior,_,_=tiny()
    problem=l2._build_problem(req,data,noise(),prior,np.arange(4,dtype=np.int64),.01)
    original=l2.optimization.ProjectedGNCG.findSearchDirection
    calls=[]
    def damaged(self):
        actual=original(self)
        assert self._joseph is not None
        calls.append(self._joseph)
        # A native recurrence PASS is necessary but not sufficient. Returning
        # the wrong actual H direction must be rejected BEFORE any trial.
        if fault=='false_recurrence':
            self.cg_abs_resid=0.
            self.cg_rel_resid=0.
            return actual+np.ones_like(actual)
        self.cg_count=201
        return actual
    monkeypatch.setattr(l2.optimization.ProjectedGNCG,'findSearchDirection',damaged)
    result=l2._solve_partition(problem,prior)
    assert calls and result['status']=='nonconverged' and result['reason']=='cg_cap'
    assert result['iterations']==0
    assert not problem['optimizer_evidence']['precision_trials']
    assert problem['metric_evidence']['metric_disposed'] is True
    assert all(v.live_payload_bytes==0 for v in calls)


def test_MP04_exception_cycle_keeps_cause_but_not_native_scratch(monkeypatch):
    refs=[]
    def cyclic(a,**kwargs):
        refs.append(weakref.ref(a))
        outer=RuntimeError('cyclic native diagnostic')
        inner=ValueError('preserved cause identity')
        outer.__cause__=inner
        inner.__context__=outer
        raise outer
    monkeypatch.setattr(metric.la,'cho_factor',cyclic)
    with pytest.raises(RuntimeError,match='cyclic native diagnostic') as caught:
        metric.JosephMetric(sp.eye(3,format='csr'),np.ones((4,3)),sp.eye(4,format='csr'),
                            np.arange(3,dtype=np.int64),monotonic()+120.)
    assert caught.value.__cause__.__context__ is caught.value
    assert all(v() is None for v in refs)


def test_MP02_native_face_change_disposes_previous_payload_BEFORE_new_setup(monkeypatch):
    import gravity_l2 as l2
    from test_gravity_l2 import tiny,noise
    req,data,prior,_,_=tiny()
    problem=l2._build_problem(req,data,noise(),prior,np.arange(4,dtype=np.int64),.01)
    opt=l2._RecordedProjectedGNCG(problem,prior,monotonic()+120.)
    n=len(prior['start_kg_m3'])
    opt.H=sp.eye(n,format='csr')
    opt.iter=0
    opt._diagonal_metric=sp.eye(n,format='csr')
    opt.xc=np.zeros(n)
    native=metric.JosephMetric
    owners=[]
    references=[]
    callbacks=[]
    def observed(*args,**kwargs):
        # No overlap between old-face B/F and the next factor construction,
        # including when an external native LinearOperator retains its owner.
        assert all(owner.live_payload_bytes==0 for owner in owners)
        assert all(ref() is None for refs in references for ref in refs)
        owner=native(*args,**kwargs)
        owners.append(owner)
        references.append([weakref.ref(v) for v in (owner.lower,owner.b,owner.f,owner.pivots)])
        return owner
    monkeypatch.setattr(metric,'JosephMetric',observed)
    try:
        for active in ((),(1,3),(0,2,4),()):
            opt.xc=np.zeros(n)
            opt.xc[list(active)]=opt.lower[list(active)]
            opt._set_free_metric()
            owner=opt._joseph
            callbacks.append(opt.approxHinv)
            free=np.flatnonzero(~opt.activeSet(opt.xc))
            np.testing.assert_array_equal(owner.free,free)
            actual=opt.approxHinv@np.ones(n)
            np.testing.assert_array_equal(actual[list(active)],np.zeros(len(active)))
            assert np.inner(actual,np.ones(n))>0.
            # Reusing exactly this face does not allocate a second metric.
            count=len(owners)
            opt._set_free_metric()
            assert opt._joseph is owner and len(owners)==count
            opt.iter+=1
    finally:
        opt.close_metric()
    assert len(owners)==4 and all(owner.live_payload_bytes==0 for owner in owners)
    assert all(ref() is None for refs in references for ref in refs)
    for callback in callbacks:
        with pytest.raises(ValueError,match='disposed'): callback@np.ones(n)


def test_MP05_full_covariance_cap_refuses_before_principal_factor_or_RHS(monkeypatch):
    # The caller's already-present immutable operands do not justify allocating
    # a metric for an original-source profile outside the unchanged2GiB bound.
    reg=sp.eye(4096,format='csr')
    g=np.broadcast_to(np.float64(0.),(4,4096))
    w=sp.eye(4,format='csr')
    free=np.arange(4096,dtype=np.int64)
    def forbidden(*args,**kwargs): raise AssertionError('metric copy before cap refusal')
    monkeypatch.setattr(sp.csr_matrix,'copy',forbidden)
    monkeypatch.setattr(metric,'_paired',forbidden)
    with pytest.raises(ValueError,match='original2GiB'):
        metric.JosephMetric(reg,g,w,free,monotonic()+120.,profile=(2048,2048,4096,True))


def test_MP07_expired_action_refuses_before_any_native_triangular_entry(monkeypatch):
    owner=metric.JosephMetric(sp.eye(3,format='csr'),np.ones((4,3)),sp.eye(4,format='csr'),
                             np.arange(3,dtype=np.int64),monotonic()+120.)
    refs=[weakref.ref(v) for v in (owner.lower,owner.b,owner.f,owner.pivots)]
    owner.deadline=monotonic()-1.
    def forbidden(*args,**kwargs): raise AssertionError('expired action entered native solver')
    monkeypatch.setattr(metric,'spsolve_triangular',forbidden)
    try:
        with pytest.raises(metric.DeadlineExceeded,match='wall_cap'): owner.apply(np.ones(3))
    finally:
        owner.close()
    assert owner.live_payload_bytes==0 and all(ref() is None for ref in refs)
