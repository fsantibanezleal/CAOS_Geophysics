"""Distinct full-rank augmented DGELS epoch; original objective unchanged."""
from hashlib import sha256
import math
from pathlib import Path

import magnetic_line_survey as core
import magnetic_line_survey_hp as hp

EPOCH = 'm03-augmented-direct-qr/1'
CONDITION_DOMAIN = 'cond2(B) <= Frobenius(R)*Frobenius(inverse(R)); B=[A;sqrt(lambda)I]P'
FLAPACK_SHA = '000d0bf5b84cee94ead7022b9e6a55d1bdcb4b4e9fe4b7f218921cd35f06e2fa'
DLL_PINS = {
    'scipy.libs': '6b2103f2ae4d8547998b5d188e9801fba6cb12404ae8e4bfff319e8cc1949000',
    'numpy.libs': '6547e9fb966e9773caee2755e91a8bf4d6f3a2f0eebf9646b0158f8675ea4ab5',
}


def dense_capacity(n, m, *, lwork=None):
    """Metadata-only native query, then integer proof BEFORE B allocation."""
    core._count(n, 1, 8000000); core._count(m, 1, min(n, 65536))
    r=n+m
    minimum=m+max(m,1)
    # Refuse oversized shapes even before importing/querying a native wrapper.
    def reserve(work): return 8*(4*r*m+4*m*m+8*r+16*m+work)+33554432
    if reserve(minimum)>core.RSS_LIMIT: raise core.SurveyError('resource_refused','seal')
    if lwork is None:
        from scipy.linalg.lapack import dgels_lwork
        work,info=dgels_lwork(r,m,1,trans='N')
        if info!=0 or not math.isfinite(work) or work!=int(work):
            raise core.SurveyError('resource_refused','seal')
        lwork=int(work)
    core._count(lwork, minimum, 2**31-1)
    extra=reserve(lwork)
    if extra>core.RSS_LIMIT:raise core.SurveyError('resource_refused','seal')
    return dict(rows=n,sources=m,augmented_rows=r,lwork=lwork,
        augmented_matrix_bytes=8*r*m,triangular_matrix_bytes=8*m*m,
        extra_peak_bytes=extra,factorization_work_bound=8*r*m*m+8*m*m*m,
        augmented_buffer_slots=4,triangular_buffer_slots=4)


def engine_identity():
    """Installed bytes and actual loaded widths; not a deployment authority."""
    import numpy
    import scipy
    import scipy.linalg._flapack as native
    from threadpoolctl import threadpool_info
    if numpy.__version__!='2.2.6' or scipy.__version__!='1.15.2':
        raise core.SurveyError('custody_mismatch','fit')
    wrapper=Path(native.__file__).resolve(strict=True)
    if sha256(wrapper.read_bytes()).hexdigest()!=FLAPACK_SHA:
        raise core.SurveyError('custody_mismatch','fit')
    pools=threadpool_info();blas=[]
    for pool in pools:
        if pool['num_threads']!=1:raise core.SurveyError('resource_refused','fit')
        if pool['user_api']=='blas':
            path=Path(pool['filepath']).resolve(strict=True)
            digest=sha256(path.read_bytes()).hexdigest()
            library=path.parent.name
            if digest!=DLL_PINS.get(library):raise core.SurveyError('custody_mismatch','fit')
            blas.append(dict(library=library,prefix=pool['prefix'],sha256=digest,threads=pool['num_threads']))
    if len(blas)!=2 or len({item['sha256'] for item in blas})!=2:
        raise core.SurveyError('custody_mismatch','fit')
    return dict(numpy=numpy.__version__,scipy=scipy.__version__,flapack_sha256=FLAPACK_SHA,
        blas=sorted(blas,key=lambda item:item['library']),threads=1)


def augmented_matrix(model,damping,p):
    """Owned F buffer; both data and penalty blocks receive the SAME P."""
    np=model.np
    matrix=np.zeros((model.n+model.m,model.m),dtype='<f8',order='F')
    for row in core._chunks(model.n,model.r):
        for col in core._chunks(model.m,model.c):
            matrix[row,col]=model._direct(row,col)*model.root_weights[row,None]/model.scales[col]*p[col]
    for j in range(model.m):matrix[model.n+j,j]=math.sqrt(damping)*p[j]
    core._finite(np,matrix)
    return matrix


def triangular_diagnostic(r):
    """DTRTRI is diagnostic only; never used to calculate c or q."""
    from scipy.linalg.lapack import dtrtri
    import numpy as np
    if type(r) is not np.ndarray or r.dtype!=np.dtype('<f8') or r.ndim!=2 or r.shape[0]!=r.shape[1] or \
       not r.flags.f_contiguous or not r.flags.owndata or not r.flags.writeable:
        raise core.SurveyError('invalid_contract','fit')
    def norm(array):
        value=0.
        for entry in array.flat:value=math.hypot(value,float(entry))
        return value
    original_norm=norm(r)
    inverse,info=dtrtri(r.copy(order='F'),lower=0,unitdiag=0,overwrite_c=1)
    core._finite(np,inverse)
    bound=original_norm*norm(inverse)
    return inverse,int(info),bound


def solve_qr(model,values,damping):
    """Store native failure state BEFORE original numerical acceptance."""
    from scipy.linalg.lapack import dgels
    from threadpoolctl import threadpool_limits
    if type(model) is not core.GlobalOperator:raise core.SurveyError('invalid_contract','fit')
    np=model.np; damping=core._damping(damping)
    y=core._array(np,values,(model.n,));core._finite(np,y)
    with threadpool_limits(limits=1),np.errstate(over='raise',invalid='raise',divide='raise'):
        capacity=dense_capacity(model.n,model.m)
        identity=engine_identity()
        p=hp.preconditioner(model,damping)
        matrix=augmented_matrix(model,damping,p)
        rhs=np.zeros((model.n+model.m,1),dtype='<f8',order='F')
        rhs[:model.n,0]=model.root_weights*y
        if not all(a.flags.owndata and a.flags.f_contiguous and a.flags.writeable for a in (matrix,rhs)):
            raise core.SurveyError('resource_refused','fit')
        factored,solution,info=dgels(matrix,rhs,trans='N',lwork=capacity['lwork'],overwrite_a=1,overwrite_b=1)
        # Explicitly count non-aliasing wrapper buffers, rather than assuming
        # overwrite eliminated copies. Four slots conservatively include them.
        bslots=1+int(not np.shares_memory(matrix,factored))
        if bslots>capacity['augmented_buffer_slots'] or factored.nbytes!=matrix.nbytes or solution.nbytes!=rhs.nbytes:
            raise core.SurveyError('resource_refused','fit')
        c=np.ascontiguousarray(p*solution[:model.m,0],dtype='<f8')
        q=np.ascontiguousarray(c/model.scales,dtype='<f8')
        r=np.zeros((model.m,model.m),dtype='<f8',order='F')
        for j in range(model.m):r[:j+1,j]=factored[:j+1,j]
        diagonal=np.abs(np.diag(r))
        receipt=dict(schema='m03-qr-solve/1',epoch=EPOCH,rows=model.n,sources=model.m,
            augmented_rows=model.n+model.m,damping=damping,preconditioner_sha256=hp.content_sha256(p),
            column_scales_sha256=hp.content_sha256(model.scales),coefficients_sha256=hp.content_sha256(q),
            scaled_coefficients_sha256=hp.content_sha256(c),lapack_info=int(info),triangular_inverse_info=None,
            lwork=capacity['lwork'],condition_domain=CONDITION_DOMAIN,condition_upper_bound=None,
            triangular_diagonal_min_abs=float(np.min(diagonal)),triangular_diagonal_max_abs=float(np.max(diagonal)),
            original_diagnostics=None,dense_capacity=capacity,engine_identity=identity,numerical_verdict='fail')
        model.qr_failure_state=dict(receipt=receipt,scaled_coefficients=c,coefficients=q,
            preconditioner=p,triangular=r,triangular_inverse=None)
        def refuse():
            error=core.SurveyError('nonconverged','fit');error.partial_solve=receipt;raise error
        for a in (c,q,r):
            if not np.isfinite(a).all():refuse()
            a.flags.writeable=False
        # Diagnostic receives separate owned writable upper triangular storage.
        inverse,inverse_info,bound=triangular_diagnostic(r.copy(order='F'))
        inverse.flags.writeable=False
        model.qr_failure_state['triangular_inverse']=inverse
        receipt['triangular_inverse_info']=inverse_info
        receipt['condition_upper_bound']=bound
        receipt['original_diagnostics']=hp.original_diagnostics(model,y,damping,c)
        if info!=0 or inverse_info!=0 or not math.isfinite(bound) or bound>=1e8 or \
           receipt['triangular_diagonal_min_abs']<=0 or receipt['original_diagnostics']['stationarity_relative']>1e-9:
            refuse()
        receipt['numerical_verdict']='component_pass'
        return model.qr_failure_state
