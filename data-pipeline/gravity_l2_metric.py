"""CPU5 fixed natural IC0/Joseph action; never replaces native H or CG.

Exact-real SPD follows from STORED unit-lower L, positive D and arbitrary
finite rounded F/B. Unknown workspace/source closure refuses, not RSS-based
admission. This candidate is not native/host/scientific acceptance authority.
"""
import hashlib
import math
import os
from pathlib import Path
import sys
import traceback
from time import monotonic

import numpy as np
import scipy.linalg as la
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve_triangular
from scipy.sparse.linalg._dsolve import linsolve, _superlu
from scipy.linalg import _flapack


POLICY='projected-gncg-binding-release-joseph-ic0-certified-delta-1'
SOURCE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
CEILING=2*1024**3
# Read only already-loaded dependency source/binaries ONCE at import. No file
# or installed-metadata scans occur inside the pure numerical callable.
_CLOSURE_EXPECTED=(
    '616ab442a96cccea5b09ba1ed70a0f118c2d771a5b721531e7b9e59696700ccf',
    '4b8eaea83fb58bcae42504d36500211375c69be9e15f189225a0ee86b0f9c10e',
    '000d0bf5b84cee94ead7022b9e6a55d1bdcb4b4e9fe4b7f218921cd35f06e2fa')
_LOADED_PINS=tuple(hashlib.sha256(Path(p).read_bytes()).hexdigest()
                   for p in (linsolve.__file__,_superlu.__file__,_flapack.__file__))


class DeadlineExceeded(RuntimeError):
    """Cooperative deadline, not hard native/OS preemption."""


def _time(deadline):
    if type(deadline) is not float or not math.isfinite(deadline):
        raise ValueError('metric: finite absolute deadline')
    if monotonic()>deadline: raise DeadlineExceeded('wall_cap')


def allocation(n,m,a,covariance):
    if (any(type(v) is not int for v in (n,m,a)) or not 1<=m<=n<=2048
        or not 1<=a<=4096 or type(covariance) is not bool):
        raise ValueError('metric: exact original source/fit/active/covariance caps')
    g0,g,c,s=8*n*a,8*m*a,8*m*m if covariance else 0,8*m*m
    native=8*g0+12*c+576*1024**2
    interval=4096*(44*a+12*m)
    lower=12*(4*a)+4*(a+1)
    setup=native+8*g+12*s+8*1024**2
    action=native+2*g+4*lower+128*(a+m)+8*1024**2
    line_search=action+interval
    maximum=max(setup,line_search)
    if g0>64*1024**2 or c>32*1024**2 or maximum>CEILING:
        raise ValueError('metric: original2GiB simultaneous live phase admission')
    return {'native':native,'interval':interval,'setup':setup,'action':action,
            'line_search':line_search,'maximum':maximum,'ceiling':CEILING}


def _workspace_closure():
    # One actual examined installed candidate tuple, not generic version>=,
    # URLs-as-binary-proof or an invented native workspace fallback. Extension
    # to another native build requires independently reviewed source closure.
    if sys.version_info[:3]!=(3,12,10) or sys.platform!='win32':
        raise ValueError('metric: native workspace candidate tuple not registered')
    if _LOADED_PINS!=_CLOSURE_EXPECTED:
        raise ValueError('metric: native workspace source/build identity mismatch')
    if any(os.environ.get(k)!='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')):
        raise ValueError('metric: reviewed single-thread native workspace required')
    # Bounded row dictionaries/list capacities are included in8MiB, not an
    # observed RSS subtraction. Refuse unknown Python header/container sizes.
    if (sys.getsizeof(4096)>64 or sys.getsizeof(1.)>64
        or sys.getsizeof({0:0.,1:1.,2:2.})>256
        or sys.getsizeof([0]*4)>128 or sys.getsizeof(np.empty(0))>256):
        raise ValueError('metric: Python object workspace closure unsupported')


def _csr_storage(matrix,n,maximum):
    # Validate backing arrays BEFORE dtype/nnz properties, sparse slicing/copy
    # or a native entry can index malformed pointers. No user refusal assert.
    if (type(matrix) is not sp.csr_matrix or matrix.shape!=(n,n)
        or any(type(v) is not np.ndarray or v.ndim!=1 or not v.flags.c_contiguous
               for v in (matrix.data,matrix.indices,matrix.indptr))
        or matrix.data.dtype!=np.float64 or matrix.indices.dtype!=np.int32
        or matrix.indptr.dtype!=np.int32 or len(matrix.data)!=len(matrix.indices)
        or len(matrix.data)>maximum or len(matrix.indptr)!=n+1):
        raise ValueError('metric: exact bounded float64/int32 CSR storage')
    count=len(matrix.data)
    if (matrix.indptr[0]!=0 or matrix.indptr[-1]!=count
        or np.any(matrix.indptr<0) or np.any(matrix.indptr>count)
        or np.any(np.diff(matrix.indptr)<0) or np.any(matrix.indices<0) or np.any(matrix.indices>=n)
        or not np.isfinite(matrix.data).all()):
        raise ValueError('metric: invalid CSR index structure')


def _stencil(matrix):
    if (type(matrix) is not sp.csr_matrix or not 1<=matrix.shape[0]<=4096
        or matrix.shape[0]!=matrix.shape[1]):
        raise ValueError('metric: native first-order square CSR required')
    n=matrix.shape[0]
    _csr_storage(matrix,n,7*n)
    for i in range(n):
        columns=matrix.indices[matrix.indptr[i]:matrix.indptr[i+1]]
        values=matrix.data[matrix.indptr[i]:matrix.indptr[i+1]]
        if (len(columns)>7 or len(set(int(x) for x in columns))!=len(columns)
            or np.count_nonzero(columns<i)>3 or np.count_nonzero(columns>i)>3
            or np.count_nonzero(columns==i)!=1 or np.any(values[columns!=i]>0.)
            or float(values[columns==i][0])<=0.):
            raise ValueError('metric: unsupported first-order stencil/duplicate/diagonal')
    # Sparse bounded difference, never a dense native Hessian.
    if (matrix-matrix.T).nnz: raise ValueError('metric: exact native symmetry required')


def _number(value):
    if not math.isfinite(value): raise ArithmeticError('metric: nonfinite intermediate')
    return value


def _factor(matrix,deadline):
    _time(deadline)
    _stencil(matrix)  # Before factor-only copies, dictionaries or dense RHS.
    a=matrix.copy()
    a.sort_indices()
    n=len(a.indptr)-1
    rows=[]
    pivots=np.empty(n,dtype=np.float64)
    for i in range(n):
        _time(deadline)
        row={}
        for pos in range(a.indptr[i],a.indptr[i+1]):
            j=int(a.indices[pos])
            if j>=i: continue
            total=0.
            for k in sorted(row.keys() & rows[j].keys()):
                product=_number(row[k]*float(pivots[k]))
                product=_number(product*rows[j][k])
                total=_number(total+product)
            numerator=_number(float(a.data[pos])-total)
            row[j]=_number(numerator/float(pivots[j]))
        diagonal=float(a[i,i])
        for k in sorted(row):
            square=_number(row[k]*row[k])
            product=_number(square*float(pivots[k]))
            diagonal=_number(diagonal-product)
        if diagonal<=0.: raise ValueError('metric: nonpositive natural IC0 pivot, no shift/retry')
        pivots[i]=diagonal
        rows.append(row)
    ptr=[0]
    indices,values=[],[]
    for i,row in enumerate(rows):
        _time(deadline)
        for j in sorted(row): indices.append(j); values.append(row[j])
        indices.append(i); values.append(1.)
        ptr.append(len(indices))
    lower=sp.csr_matrix((np.array(values,dtype=np.float64),np.array(indices,dtype=np.int32),
                         np.array(ptr,dtype=np.int32)),shape=a.shape)
    _time(deadline)
    return lower,pivots


def _finite_array(value):
    if not np.isfinite(value).all(): raise ArithmeticError('metric: nonfinite native intermediate')
    return value


def _paired(lower,pivots,v,deadline):
    _time(deadline)
    x=_finite_array(spsolve_triangular(lower,v,lower=True,unit_diagonal=True))
    _time(deadline)
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        x=_finite_array(x/(pivots if x.ndim==1 else pivots[:,None]))
    _time(deadline)
    y=_finite_array(spsolve_triangular(lower.T,x,lower=False,unit_diagonal=True))
    _time(deadline)
    return y


def _joseph(lower,pivots,b,f,v,deadline):
    _time(deadline)
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        z=_finite_array(f.T@v)
        w=_finite_array(v-_finite_array(b.T@z))
        y=_paired(lower,pivots,w,deadline)
        by=_finite_array(b@y)
        result=_finite_array(_finite_array(y-_finite_array(f@by))+_finite_array(f@z))
        value=float(np.inner(v,result))
    if not math.isfinite(value) or (np.any(v) and value<=0.):
        raise ArithmeticError('metric: nonpositive native Joseph action, no fallback')
    _time(deadline)
    return result


class JosephMetric:
    """Own only bounded factor arrays; no problem/parent/optimizer closure."""
    def __init__(self,regularizer,g,weights,free,deadline,*,profile=None):
        self.lower=self.pivots=self.b=self.f=self.free=None
        if type(g) is not np.ndarray or g.dtype!=np.float64 or g.ndim!=2:
            raise ValueError('metric: exact native sensitivity')
        self.a,self.deadline=g.shape[1],deadline
        self.setup_seconds=0.
        started=monotonic()
        _time(deadline)
        _workspace_closure()
        _stencil(regularizer)
        # No noise-kind inference from diagonal-looking W. Tiny private math
        # controls use the conservative covariance profile; owner construction
        # supplies exact original source/compact/noise facts, not a public knob.
        if profile is None: profile=(g.shape[0],g.shape[0],self.a,True)
        if (type(profile) is not tuple or len(profile)!=4 or profile[2]!=self.a
            or type(profile[1]) is not int or profile[1]<g.shape[0]):
            raise ValueError('metric: exact trusted full operand profile')
        self.allocation=allocation(*profile)
        if (type(g) is not np.ndarray or g.dtype!=np.float64 or g.ndim!=2
            or not 1<=g.shape[0]<=2048 or not 1<=g.shape[1]<=4096 or not np.isfinite(g).all()
            or type(weights) is not sp.csr_matrix or weights.dtype!=np.float64
            or weights.shape!=(g.shape[0],g.shape[0]) or not np.isfinite(weights.data).all()
            or regularizer.shape!=(self.a,self.a) or type(free) is not np.ndarray
            or free.dtype!=np.int64 or free.ndim!=1 or not 1<=len(free)<=self.a
            or np.any(free<0) or np.any(free>=self.a) or np.any(np.diff(free)<=0)):
            raise ValueError('metric: exact native operands/free principal face')
        _csr_storage(weights,g.shape[0],g.shape[0]**2)
        principal=t=s=chol=None
        try:
            principal=regularizer[free][:,free].tocsr()
            self.lower,self.pivots=_factor(principal,deadline)
            principal=None
            _time(deadline)
            with np.errstate(over='raise',invalid='raise'):
                self.b=_finite_array(np.sqrt(2.)*(weights@g[:,free]))
            t=_paired(self.lower,self.pivots,self.b.T,deadline)
            _time(deadline)
            with np.errstate(over='raise',invalid='raise'):
                s=_finite_array(np.eye(len(weights.indptr)-1)+self.b@t)
                s=_finite_array(.5*(s+s.T))
            _time(deadline)
            chol=la.cho_factor(s,lower=True,overwrite_a=True,check_finite=True)
            _finite_array(chol[0])
            _time(deadline)
            for begin in range(0,len(free),64):
                _time(deadline)
                end=min(len(free),begin+64)
                t[begin:end]=_finite_array(la.cho_solve(chol,t[begin:end].T,check_finite=True).T)
                _time(deadline)
            self.f=t
            # Actual independent S/factor/multi-RHS scratch cannot coexist with
            # CG or NI. Stored F reuses T; no parent/closure holds local scratch.
            s=chol=t=None
            self.free=free.copy()
            for value in (self.pivots,self.b,self.f,self.free): value.flags.writeable=False
            for value in (self.lower.data,self.lower.indices,self.lower.indptr): value.flags.writeable=False
            _time(deadline)
            self.setup_seconds=monotonic()-started
        except BaseException as exc:
            self.close()
            # Keep the original exception/cause/stack identity, but dispose
            # inactive native-wrapper/factor frames even when a caller retains
            # the failure traceback. The current executing frame is cleared by
            # the explicit finally below, not by relying on cycle collection.
            pending,seen=[exc],set()
            while pending:
                failure=pending.pop()
                if id(failure) in seen: continue
                seen.add(id(failure))
                traceback.clear_frames(failure.__traceback__)
                for linked in (failure.__cause__,failure.__context__):
                    if linked is not None and id(linked) not in seen: pending.append(linked)
            raise
        finally:
            principal=t=s=chol=None
            pending=seen=failure=linked=None

    @property
    def live_payload_bytes(self):
        if self.lower is None: return 0
        return sum(v.nbytes for v in (self.lower.data,self.lower.indices,self.lower.indptr,
                                      self.pivots,self.b,self.f,self.free))

    def apply(self,v):
        if self.lower is None: raise ValueError('metric: disposed face')
        if type(v) is not np.ndarray or v.dtype!=np.float64 or v.shape!=(self.a,):
            raise ValueError('metric: exact native CG vector')
        _finite_array(v)
        result=np.zeros_like(v)
        result[self.free]=_joseph(self.lower,self.pivots,self.b,self.f,v[self.free],self.deadline)
        return result

    def close(self):
        self.lower=self.pivots=self.b=self.f=self.free=None
