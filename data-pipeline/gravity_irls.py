"""Owned ordinary fixed-beta Sparse stages with predeclared log17/floor3.

Trusted private partition unit, NOT an uploaded/prepared-engine entry, public
calibration schema, field claim or source registry. Selection, refit, frozen
evaluation and complete user-data/export admission remain distinct obligations.
"""
import hashlib
import inspect
import math
from pathlib import Path
from time import monotonic

import numpy as np
from scipy.sparse.linalg import LinearOperator, aslinearoperator
import scipy.sparse as sp
from simpeg import regularization, maps

import gravity_l2 as l2
import gravity_l2_precision as precision
import gravity_survey_l2 as survey
import physical_optimizer as optimizer


POLICY='ordinary-irls-fixed-beta-log17-stage-1'
RUNTIME_EPOCH='m02-survey-irls-cpu-1'
_KEYS={'norms','gradient_type','irls_scaled','epsilon_floor','epsilon_units',
    'epsilon_initialization','epsilon_continuation','beta_transition','max_weight_updates',
    'overall_stop_policy'}
_UNITS=('g/cc','g/cc/m','g/cc/m','g/cc/m')
# Import-time loaded source inventory, not a caller path or numerical I/O.
# A trusted driver still must independently review full native/source closure.
_SOURCES={str(Path(path).name):hashlib.sha256(Path(path).read_bytes()).hexdigest()
    for path in (__file__,l2.__file__,precision.__file__,optimizer.__file__,survey.__file__,
                 l2.forward.__file__,l2.metric.__file__,inspect.getfile(regularization.WeightedLeastSquares),
                 inspect.getfile(regularization.Sparse),inspect.getfile(l2.data_misfit.L2DataMisfit),
                 inspect.getfile(optimizer.optimization.ProjectedGNCG))}
_INVENTORY=survey._digest(_SOURCES)

_BOOK_METRICS=('phi_d_initial','phi_m_initial','phi_engine_initial','kkt_initial',
               'phi_d_final','phi_m_final','phi_engine_final','kkt_final')
_BOOK_STATUS=('converged','nonconverged','failed')
_BOOK_REASON=('absolute_stationary','kkt_stable','iteration_cap','cg_cap',
              'line_search_failed','wall_cap','zero_free_direction','nonfinite',
              'engine_error','state_mismatch')
_BOOK_KEYS={'schema','count','index','accepted_span','model_span','beta_engine','epsilon',
    'epsilon_units','norms','hash_encoding','weight_sha256_words','operator_sha256_words',
    'smallness_weights','status','reason','metrics','logical_stage_sha256','book_sha256',
    'trace_binding_sha256'}
_ROW_KEYS={'index','accepted_start','accepted_stop','model_row_start','model_row_stop',
    'beta_engine','epsilon','epsilon_units','norms','weight_sha256','smallness_weights',
    'operator_sha256','status','reason','metrics'}


def _hash_words(value):
    survey._sha(value,'stage digest')
    raw=bytes.fromhex(value)
    return np.array([int.from_bytes(raw[i:i+8],'big',signed=True) for i in range(0,32,8)],dtype='<i8')


def _words_hash(value):
    survey._array(value,(4,),'digest words',dtype=np.dtype('<i8'))
    return b''.join(int(word).to_bytes(8,'big',signed=True) for word in value).hex()


def _book_context(trace,parameter_count,beta_engine,initial_epsilon,policy,count):
    if type(parameter_count) is not int or not 1<=parameter_count<=4096:
        raise ValueError('stage book: exact active count')
    survey._float(beta_engine,'stage beta',positive=True)
    policy=_validate_policy(policy)
    if not (count==0 and initial_epsilon is None) and (type(initial_epsilon) is not tuple or len(initial_epsilon)!=4
        or any(type(v) is not float or not np.isfinite(v) or v<f
               for v,f in zip(initial_epsilon,policy['epsilon_floor']))):
        raise ValueError('stage book: actual initial thresholds required')
    survey._keys(trace,('models_kg_m3','stage_indices'),'shared trace')
    survey._array(trace['models_kg_m3'],(None,parameter_count),'shared models')
    n=len(trace['models_kg_m3'])
    if not 0<=n<=201 or (count and n==0): raise ValueError('stage book: actual shared row cap')
    survey._array(trace['stage_indices'],(n,),'shared labels',dtype=np.int64)
    if (not np.isfinite(trace['models_kg_m3']).all()
        or np.any(trace['stage_indices']< -1) or np.any(trace['stage_indices']>20)):
        raise ValueError('stage book: finite actual models and closed labels')
    return policy


def _validate_stage_rows(rows,trace,parameter_count,beta_engine,initial_epsilon,policy):
    if type(rows) is not tuple or not 0<=len(rows)<=21:
        raise ValueError('stage book: bounded actual row tuple')
    policy=_book_context(trace,parameter_count,beta_engine,initial_epsilon,policy,len(rows))
    previous=None
    for index,row in enumerate(rows):
        survey._keys(row,_ROW_KEYS,'logical stage')
        for name in ('index','accepted_start','accepted_stop','model_row_start','model_row_stop'):
            if type(row[name]) is not int or not 0<=row[name]<=200:
                raise ValueError('stage book: native bounded row/span integer')
        left,right=row['accepted_start'],row['accepted_stop']
        ml,mr=row['model_row_start'],row['model_row_stop']
        if (row['index']!=index or left>right or ml!=left or mr!=right
            or mr>=len(trace['stage_indices']) or (previous is not None and left!=previous)):
            raise ValueError('stage book: contiguous actual accepted/model spans')
        if index==0 and np.any(trace['stage_indices'][:ml+1]!=-1):
            raise ValueError('stage book: initialization label binding')
        if np.any(trace['stage_indices'][ml+1:mr+1]!=index):
            raise ValueError('stage book: actual accepted row labels')
        previous=right
        if type(row['beta_engine']) is not float or row['beta_engine']!=beta_engine:
            raise ValueError('stage book: fixed native beta')
        expected=tuple(_epsilon(v,f,index) for v,f in zip(initial_epsilon,policy['epsilon_floor']))
        for name,literal in (('epsilon',expected),('norms',policy['norms'])):
            if (type(row[name]) is not tuple or len(row[name])!=4
                or any(type(v) is not float for v in row[name]) or row[name]!=literal):
                raise ValueError('stage book: pinned thresholds/norms')
        if (type(row['epsilon_units']) is not tuple or len(row['epsilon_units'])!=4
            or any(type(v) is not str for v in row['epsilon_units']) or row['epsilon_units']!=_UNITS):
            raise ValueError('stage book: exact component units')
        for name in ('weight_sha256','operator_sha256'):
            if type(row[name]) is not tuple or len(row[name])!=4:
                raise ValueError('stage book: four component digests')
            for digest in row[name]: survey._sha(digest,name)
        survey._array(row['smallness_weights'],(parameter_count,),'actual p1 weights')
        if (not np.isfinite(row['smallness_weights']).all() or np.any(row['smallness_weights']<=0.)
            or survey._digest(row['smallness_weights'])!=row['weight_sha256'][0]):
            raise ValueError('stage book: actual positive smallness weights/digest')
        status,reason=row['status'],row['reason']
        if type(status) is not str or type(reason) is not str or status not in _BOOK_STATUS or reason not in _BOOK_REASON:
            raise ValueError('stage book: closed stage outcome')
        code=_BOOK_REASON.index(reason)
        if _BOOK_STATUS.index(status)!=(0 if code<2 else 1 if code<7 else 2):
            raise ValueError('stage book: positive status/reason pairing')
        survey._keys(row['metrics'],_BOOK_METRICS,'nullable stage metrics')
        for value in row['metrics'].values():
            if value is not None and (type(value) is not float or not np.isfinite(value) or value<0.):
                raise ValueError('stage book: nullable finite nonnegative metric')
    if rows and previous!=len(trace['stage_indices'])-1:
        raise ValueError('stage book: no unaccounted shared model rows')
    if not rows and np.any(trace['stage_indices']!=-1):
        raise ValueError('stage book: empty stages bind initialization only')


def encode_stage_book(stages,trace,*,parameter_count,beta_engine,initial_epsilon,policy):
    """Lossless bounded representation, not native/source/scientific admission.

    Metadata on the COMPLETE supplied envelope precedes numeric scans/digests.
    Full result/archive drivers must still admit their entire wrapper and finish
    all-member/EOF/source/operator replay before exposing verified science.
    """
    context={'trace':trace,'parameter_count':parameter_count,'beta_engine':beta_engine,
             'initial_epsilon':initial_epsilon,'policy':policy}
    l2._result_native_metadata({'stages':stages,**context})
    _validate_stage_rows(stages,**context)
    s=len(stages)
    indexes=np.full((s,8),-1,dtype=np.int64)
    values=[]
    for i,row in enumerate(stages):
        for j,name in enumerate(_BOOK_METRICS):
            if row['metrics'][name] is not None:
                indexes[i,j]=len(values)
                values.append(row['metrics'][name])
    book={'schema':'gravity-survey-irls-stage-book-1','count':s,
        'index':np.arange(s,dtype=np.int64),
        'accepted_span':np.array([(r['accepted_start'],r['accepted_stop']) for r in stages],dtype=np.int64).reshape(s,2),
        'model_span':np.array([(r['model_row_start'],r['model_row_stop']) for r in stages],dtype=np.int64).reshape(s,2),
        'beta_engine':np.array([r['beta_engine'] for r in stages]),
        'epsilon':np.array([r['epsilon'] for r in stages],dtype=np.float64).reshape(s,4),
        'epsilon_units':_UNITS,'norms':(1.,2.,2.,2.),
        'hash_encoding':'sha256-big-endian-signed64x4-1',
        'weight_sha256_words':np.array([_hash_words(h) for r in stages for h in r['weight_sha256']],dtype=np.int64).reshape(4*s,4),
        'operator_sha256_words':np.array([_hash_words(h) for r in stages for h in r['operator_sha256']],dtype=np.int64).reshape(4*s,4),
        'smallness_weights':np.array([r['smallness_weights'] for r in stages],dtype=np.float64).reshape(s,parameter_count),
        'status':np.array([_BOOK_STATUS.index(r['status']) for r in stages],dtype=np.int64),
        'reason':np.array([_BOOK_REASON.index(r['reason']) for r in stages],dtype=np.int64),
        'metrics':{'columns':_BOOK_METRICS,'index':indexes,'values':np.array(values,dtype=np.float64)},
        'logical_stage_sha256':survey._digest(stages),'trace_binding_sha256':survey._digest(trace)}
    book['book_sha256']=survey._digest(book)
    for key,value in book.items():
        if type(value) is np.ndarray: book[key]=survey._readonly(value)
    for key in ('index','values'): book['metrics'][key]=survey._readonly(book['metrics'][key])
    l2._result_native_metadata({'book':book,**context})
    return book


def decode_stage_book(book,trace,*,parameter_count,beta_engine,initial_epsilon,policy):
    """Validate the complete book/trace before returning any logical stage.

    Not a lazy verified-stage iterator and not an archive EOF/source verifier.
    Source/actual native operator replay is a separate trusted driver obligation.
    """
    context={'trace':trace,'parameter_count':parameter_count,'beta_engine':beta_engine,
             'initial_epsilon':initial_epsilon,'policy':policy}
    l2._result_native_metadata({'book':book,**context})
    survey._keys(book,_BOOK_KEYS,'stage book')
    survey._enum(book['schema'],'gravity-survey-irls-stage-book-1','stage book schema')
    survey._enum(book['hash_encoding'],'sha256-big-endian-signed64x4-1','hash encoding')
    s=book['count']
    if type(s) is not int or not 0<=s<=21: raise ValueError('stage book: bounded exact count')
    _book_context(**context,count=s)
    if (type(book['epsilon_units']) is not tuple or len(book['epsilon_units'])!=4
        or any(type(x) is not str for x in book['epsilon_units']) or book['epsilon_units']!=_UNITS
        or type(book['norms']) is not tuple or len(book['norms'])!=4
        or any(type(x) is not float for x in book['norms']) or book['norms']!=(1.,2.,2.,2.)):
        raise ValueError('stage book: exact units/norms even for empty stages')
    for key,shape in (('index',(s,)),('accepted_span',(s,2)),('model_span',(s,2)),
        ('weight_sha256_words',(4*s,4)),('operator_sha256_words',(4*s,4)),('status',(s,)),('reason',(s,))):
        survey._array(book[key],shape,key,dtype=np.dtype('<i8'))
    for key,shape in (('beta_engine',(s,)),('epsilon',(s,4)),('smallness_weights',(s,parameter_count))):
        survey._array(book[key],shape,key,dtype=np.dtype('<f8'))
        if not np.isfinite(book[key]).all(): raise ValueError('stage book: finite actual arrays')
    if not np.array_equal(book['index'],np.arange(s,dtype=np.int64)):
        raise ValueError('stage book: contiguous index')
    if (np.any(book['status']<0) or np.any(book['status']>=len(_BOOK_STATUS))
        or np.any(book['reason']<0) or np.any(book['reason']>=len(_BOOK_REASON))):
        raise ValueError('stage book: unknown outcome code')
    metrics=book['metrics']
    survey._keys(metrics,('columns','index','values'),'metric table')
    if (type(metrics['columns']) is not tuple or len(metrics['columns'])!=8
        or any(type(v) is not str for v in metrics['columns']) or metrics['columns']!=_BOOK_METRICS):
        raise ValueError('stage book: exact metric columns')
    survey._array(metrics['index'],(s,8),'metric ordinals',dtype=np.int64)
    survey._array(metrics['values'],(None,),'metric values')
    v=len(metrics['values'])
    present=metrics['index'][metrics['index']!=-1]
    if (v>8*s or np.any(metrics['index']< -1) or not np.array_equal(present,np.arange(v,dtype=np.int64))
        or not np.isfinite(metrics['values']).all() or np.any(metrics['values']<0.)):
        raise ValueError('stage book: exact nullable contiguous metric ordinals')
    for key in ('logical_stage_sha256','book_sha256','trace_binding_sha256'): survey._sha(book[key],key)
    if (survey._digest({k:v for k,v in book.items() if k!='book_sha256'})!=book['book_sha256']
        or survey._digest(trace)!=book['trace_binding_sha256']):
        raise ValueError('stage book: complete book/trace binding mismatch')
    rows=[]
    for i in range(s):
        rows.append({'index':int(book['index'][i]),
            'accepted_start':int(book['accepted_span'][i,0]),'accepted_stop':int(book['accepted_span'][i,1]),
            'model_row_start':int(book['model_span'][i,0]),'model_row_stop':int(book['model_span'][i,1]),
            'beta_engine':float(book['beta_engine'][i]),'epsilon':tuple(float(x) for x in book['epsilon'][i]),
            'epsilon_units':book['epsilon_units'],'norms':book['norms'],
            'weight_sha256':tuple(_words_hash(x) for x in book['weight_sha256_words'][4*i:4*i+4]),
            'operator_sha256':tuple(_words_hash(x) for x in book['operator_sha256_words'][4*i:4*i+4]),
            'smallness_weights':survey._readonly(book['smallness_weights'][i]),
            'status':_BOOK_STATUS[int(book['status'][i])],'reason':_BOOK_REASON[int(book['reason'][i])],
            'metrics':{name:None if metrics['index'][i,j]==-1 else float(metrics['values'][metrics['index'][i,j]])
                       for j,name in enumerate(_BOOK_METRICS)}})
    rows=tuple(rows)
    _validate_stage_rows(rows,**context)
    if survey._digest(rows)!=book['logical_stage_sha256']:
        raise ValueError('stage book: exact original logical stage digest mismatch')
    return rows


def _validate_policy(value):
    if type(value) is not dict or any(type(k) is not str for k in value) or set(value)!=_KEYS:
        raise ValueError('irls: exact ten-key corrected policy')
    if (type(value['norms']) is not tuple or len(value['norms'])!=4
        or any(type(x) is not float for x in value['norms']) or value['norms']!=(1.,2.,2.,2.)
        or type(value['gradient_type']) is not str or value['gradient_type']!='components'
        or type(value['irls_scaled']) is not bool or not value['irls_scaled']):
        raise ValueError('irls: fixed native Sparse recipe')
    floors=value['epsilon_floor']
    if (type(floors) is not tuple or len(floors)!=4
        or any(type(x) is not float or not np.isfinite(x) or x<=0. for x in floors)
        or type(value['epsilon_units']) is not tuple or len(value['epsilon_units'])!=4
        or any(type(x) is not str for x in value['epsilon_units']) or value['epsilon_units']!=_UNITS):
        raise ValueError('irls: explicit positive native floors and physical units')
    continuation=value['epsilon_continuation']
    if (type(continuation) is not dict or any(type(k) is not str for k in continuation)
        or set(continuation)!={'name','floor_update','max_updates','rounding'}):
        raise ValueError('irls: exact continuation')
    if (type(continuation['name']) is not str or continuation['name']!='log17_floor3_1'
        or type(continuation['floor_update']) is not int or continuation['floor_update']!=17
        or type(continuation['max_updates']) is not int or continuation['max_updates']!=20
        or type(continuation['rounding']) is not str
        or continuation['rounding']!='native_log_exp_clamp_endpoints'
        or type(value['max_weight_updates']) is not int or value['max_weight_updates']!=20):
        raise ValueError('irls: exact log17/floor3 schedule')
    for key,literal in (
        ('epsilon_initialization','max_submitted_floor_and_fit_L2_kernel_max'),
        ('beta_transition','fixed_initial_beta_every_stage'),
        ('overall_stop_policy','saturated_floor_three_stage_fixed_point_1')):
        if type(value[key]) is not str or value[key]!=literal: raise ValueError('irls: fixed stage policy')
    return survey._snapshot(value)


def _epsilon(initial,floor,index):
    if (type(initial) is not float or type(floor) is not float or not np.isfinite(initial)
        or not np.isfinite(floor) or not 0.<floor<=initial
        or type(index) is not int or not 0<=index<=20):
        raise ValueError('irls: positive finite log domain and exact update')
    if index==0: return initial
    if index>=17 or initial==floor: return floor
    # Never form initial/floor or floor/initial; no score-selected retry schedule.
    left,right=math.log(initial),math.log(floor)
    difference=right-left
    scaled=(float(index)/17.)*difference
    exponent=left+scaled
    if not all(math.isfinite(v) for v in (left,right,difference,scaled,exponent)):
        raise ValueError('irls: nonfinite continuation')
    result=math.exp(exponent)
    if not math.isfinite(result) or result<=0.: raise ValueError('irls: continuation underflow/nonfinite')
    return min(initial,max(floor,result))


def _sparse_snapshot(matrix):
    csr=matrix.tocsr(copy=False)
    return {'shape':tuple(int(x) for x in csr.shape),'data':csr.data,
            'indices':csr.indices,'indptr':csr.indptr}


def _seal(problem,epsilon,policy_hash):
    reg=problem['regularization']
    if (type(reg) is not regularization.Sparse or len(reg.objfcts)!=4
        or type(reg.mapping) is not maps.IdentityMap
        or reg.mapping.nP!=len(problem['reference_q'])
        or any(type(c.mapping) is not maps.IdentityMap
               or c.mapping.nP!=len(problem['reference_q']) for c in reg.objfcts)):
        raise ValueError('irls: frozen stage ordinary mapping mismatch')
    return survey._digest({'G':problem['simulation'].G,'W':_sparse_snapshot(problem['misfit'].W),
        'dobs':problem['misfit'].data.dobs,'reference':problem['reference_q'],
        'beta':float(problem['beta_engine']),'alpha':tuple(float(x) for x in reg.multipliers),
        'components':tuple({'W':_sparse_snapshot(c.W),
            'D':_sparse_snapshot(c.f_m_deriv(problem['reference_q'])),
            'reference':c.reference_model,'norm':c.norm,'scaled':bool(c.irls_scaled),
            'weights':c.get_weights('irls'),'epsilon':float(c.irls_threshold)} for c in reg.objfcts),
        'epsilon':epsilon,'policy_sha256':policy_hash})


def _build_stage(problem,q,policy,index,initial):
    policy=_validate_policy(policy)
    if type(initial) is not tuple or len(initial)!=4: raise ValueError('irls: actual four kernel initials')
    a=len(problem['reference_q'])
    if not optimizer._array(q,a): raise ValueError('irls: exact finite native model')
    epsilon=tuple(_epsilon(v,f,index) for v,f in zip(initial,policy['epsilon_floor']))
    alpha=problem['alpha']
    reg=regularization.Sparse(problem['simulation'].mesh,
        active_cells=problem['simulation'].active_cells,mapping=maps.IdentityMap(nP=a),
        reference_model=problem['reference_q'].copy(),reference_model_in_smooth=True,
        alpha_s=alpha[0],alpha_x=alpha[1],alpha_y=alpha[2],alpha_z=alpha[3],
        norms=[1.,2.,2.,2.],gradient_type='components',irls_scaled=True)
    if len(reg.objfcts)!=4: raise ValueError('irls: native four components required')
    for component,threshold in zip(reg.objfcts,epsilon):
        kernel=component.f_m(q)
        if kernel.size==0: raise ValueError('unsupported_sparse_empty_face')
        if not np.isfinite(kernel).all(): raise ValueError('irls: nonfinite native kernel')
        component.irls_threshold=threshold
    with np.errstate(over='raise',invalid='raise',divide='raise',under='ignore'):
        reg.update_weights(q)
    weights=tuple(survey._readonly(c.get_weights('irls')) for c in reg.objfcts)
    if any(not np.isfinite(w).all() or np.any(w<=0.) for w in weights):
        raise ValueError('irls: finite positive actual native weights required')
    if any(not np.array_equal(w,np.ones_like(w)) for w in weights[1:]):
        raise ValueError('irls: fixed p2 directional weights')
    stage_problem=dict(problem,regularization=reg)
    policy_hash=survey._digest({'name':POLICY,'irls':policy})
    return {'problem':stage_problem,'epsilon':epsilon,'weights':weights,
        'weight_sha256':tuple(survey._digest(w) for w in weights),
        'operator_sha256':tuple(survey._digest({'W':_sparse_snapshot(c.W),
            'D':_sparse_snapshot(c.f_m_deriv(problem['reference_q']))}) for c in reg.objfcts),
        'policy_sha256':policy_hash,'objective_sha256':_seal(stage_problem,epsilon,policy_hash)}


class _StageObjective:
    """Private reviewed construction boundary, no user-created objective object."""
    def __init__(self,stage,index,lower,upper,allocation_hash):
        self.stage,self.problem,self.index=stage,stage['problem'],index
        self.lower,self.upper,self.allocation_hash=lower,upper,allocation_hash
        self.proof=None
        self.diagonal=None

    def identity(self):
        p=self.problem
        actual=_seal(p,self.stage['epsilon'],self.stage['policy_sha256'])
        if actual!=self.stage['objective_sha256']: raise ValueError('irls: frozen stage identity mismatch')
        # Replay the actual fixed stage factors, not a mutable caller tag.
        return {'mode':'fixed_linear_quadratic','runtime_epoch':optimizer.RUNTIME_EPOCH,
            'objective_sha256':actual,
            'source_inventory_sha256':_INVENTORY,'q_unit':'g/cc','physical_unit':'kg/m3',
            'physical_scale':1000.,'parameter_count':len(self.lower),
            'observation_rows':len(p['observations']),'observation_components':1,
            'beta_engine':float(p['beta_engine']),'stage_index':self.index,
            'allocation_plan_sha256':self.allocation_hash}

    def components(self,q):
        pd,pm=float(self.problem['misfit'](q)),float(self.problem['regularization'](q))
        return {'phi_d':pd,'phi_m':pm,'phi_engine':float(pd+self.problem['beta_engine']*pm)}

    def evaluate(self,q,return_g=False,return_H=False):
        misfit,reg,beta=self.problem['misfit'],self.problem['regularization'],self.problem['beta_engine']
        values=[self.components(q)['phi_engine']]
        if return_g: values.append(misfit.deriv(q)+beta*reg.deriv(q))
        if return_H:
            a=len(q)
            values.append(LinearOperator((a,a),matvec=lambda v:misfit.deriv2(q,v)+beta*reg.deriv2(q,v),
                                         dtype=np.float64))
        return tuple(values) if return_g or return_H else values[0]

    def binding_diagonal(self,q):
        if self.diagonal is None:
            wg=self.problem['misfit'].W@self.problem['simulation'].G
            self.diagonal=2*np.sum(wg*wg,axis=0)+self.problem['beta_engine']*self.problem['regularization'].deriv2(q).diagonal()
        return self.diagonal.copy()

    def free_metric(self,q,free_indices):
        diagonal=self.binding_diagonal(q)
        values=np.zeros(len(q))
        values[free_indices]=1./diagonal[free_indices]
        return aslinearoperator(sp.diags(values,format='csr'))

    def certify(self,q,qt,native_gradient,native_phi,native_phi_trial,iteration,trial,deadline):
        if self.proof is None: self.proof=precision._CertifiedDelta(self.problem,self.lower,self.upper,deadline)
        self.proof.deadline=deadline
        return self.proof.evaluate(q,qt,native_gradient,iteration,trial,native_phi,native_phi_trial)

    def release_state(self):
        self.proof,self.diagonal=None,None


def _fixed_point(index,saturated,changes):
    if index!=20 or saturated is not True or len(changes)!=20: return False
    return all(type(c) is dict and set(c)=={'model_relative','weights_relative'}
        and all(type(v) is float and np.isfinite(v) and 0.<=v<=1e-6 for v in c.values())
        for c in changes[-3:])


def _solve_partition(problem,prior,policy,deadline,*,_stage_solutions=None):
    """Real L2 initialization and0..20 immutable fixed Sparse stages.

    Private six-key unit result; NOT a public L2/IRLS calibration result or bundle.
    Shared accepted model rows, stage-specific Phi only (no global monotone Phi).
    """
    policy=_validate_policy(policy)
    if _stage_solutions is not None and type(_stage_solutions) is not list:
        raise TypeError('irls: private exact stage ledger')
    if type(deadline) is not float or not np.isfinite(deadline): raise ValueError('irls: finite native deadline')
    deadline=min(deadline,monotonic()+120.)
    initialization=l2._solve_partition(problem,prior,deadline)
    stages,changes=[],[]
    steps=initialization['iterations']
    model=initialization['model_kg_m3']
    models=[row.copy() for row in initialization['trace']['models_kg_m3']]
    labels=[-1]*len(models)
    lower,upper=prior['lower_kg_m3']/1000.,prior['upper_kg_m3']/1000.
    n,a=problem['simulation'].G.shape
    # Trusted private unit charges WORST full covariance, never guesses the
    # submitted noise representation from a diagonal-looking W. Full wrapper
    # admission and less-conservative declared profile belong to the driver.
    admitted=8*(8*n*a)+12*(8*n*n)+4096*(44*a+12*n)+576*1024**2
    allocation_hash=survey._digest({'n':n,'a':a,'bytes':admitted,
                                   'rule':'original_full_covariance_upper_plus_fixed_stage_1'})
    initial=None
    previous_weights=None
    reason=initialization['reason']
    status='nonconverged' if initialization['status']=='nonconverged' else 'failed'
    saturated=False
    updates=0
    if initialization['status']=='converged':
        q=model/1000.
        try:
            if admitted>2*1024**3: raise ValueError('irls: projected native workspace outside existing2GiB')
            kernels=[c.f_m(q) for alpha,c in zip(problem['regularization'].multipliers,
                                                problem['regularization'].objfcts) if alpha>0.]
            if len(kernels)!=4 or any(v.size==0 for v in kernels):
                raise ValueError('unsupported_sparse_empty_face')
            if any(not np.isfinite(v).all() for v in kernels): raise ArithmeticError('nonfinite kernel')
            initial=tuple(max(f,float(np.max(np.abs(v)))) for f,v in zip(policy['epsilon_floor'],kernels))
            for index in range(21):
                if monotonic()>deadline:
                    reason,status='wall_cap','nonconverged'
                    break
                previous=q.copy()
                stage=_build_stage(problem,q,policy,index,initial)
                # Each applied update is counted even when the following solve fails.
                updates=index
                saturated=stage['epsilon']==policy['epsilon_floor']
                current_weights=stage['weights'][0]
                if previous_weights is not None:
                    weight_change=float(np.linalg.norm(current_weights-previous_weights,ord=np.inf)
                        /max(1.,float(np.linalg.norm(previous_weights,ord=np.inf))))
                objective=_StageObjective(stage,index,lower,upper,allocation_hash)
                binding=optimizer.OptimizerBinding('physical_optimizer.solve_bounded_physical',
                    optimizer.SOURCE_SHA256,_SOURCES[Path(precision.__file__).name],_INVENTORY,
                    optimizer.RUNTIME_EPOCH,optimizer.POLICY)
                budget=optimizer.OptimizerBudget(deadline,200-steps,2*1024**3,admitted,allocation_hash)
                solved=optimizer.solve_bounded_physical(objective,lower,upper,q,budget=budget,binding=binding)
                if _stage_solutions is not None: _stage_solutions.append(solved)
                start_row=max(0,len(models)-1)
                accepted_start=steps
                steps+=solved['iterations']
                for row in solved['trace']['models_q'][1:]:
                    models.append(row*1000.)
                    labels.append(index)
                metrics={}
                for label,key in (('phi_d','phi_d'),('phi_m','phi_m'),('phi_engine','phi_engine'),
                                  ('kkt','kkt_normalized')):
                    values=solved['trace'][key]
                    metrics[label+'_initial']=float(values[0]) if len(values) else None
                    metrics[label+'_final']=float(values[-1]) if len(values) else None
                stages.append({'index':index,'accepted_start':accepted_start,'accepted_stop':steps,
                    'model_row_start':start_row,'model_row_stop':max(0,len(models)-1),
                    'beta_engine':float(problem['beta_engine']),'epsilon':stage['epsilon'],
                    'epsilon_units':_UNITS,'norms':policy['norms'],'weight_sha256':stage['weight_sha256'],
                    'smallness_weights':current_weights,'operator_sha256':stage['operator_sha256'],
                    'status':solved['status'],'reason':solved['reason'],'metrics':metrics})
                if solved['q'] is not None:
                    q=solved['q'].copy()
                    model=survey._readonly(q*1000.)
                if index>0:
                    changes.append({'model_relative':float(np.linalg.norm(q-previous,ord=np.inf)
                        /max(1.,float(np.linalg.norm(previous,ord=np.inf)))) if solved['q'] is not None else None,
                        'weights_relative':weight_change})
                if solved['status']!='converged':
                    reason,status=solved['reason'],solved['status']
                    break
                previous_weights=current_weights.copy()
                if _fixed_point(index,saturated,tuple(changes)):
                    gradient=objective.evaluate(q,True,False)[1]
                    if not np.isfinite(gradient).all(): raise ArithmeticError('nonfinite terminal')
                    null=(not np.any(q-problem['reference_q']) and not np.any(gradient))
                    reason,status='irls_stationary_null' if null else 'irls_fixed_point','converged'
                    break
            else:
                reason,status='irls_iteration_cap','nonconverged'
        except ArithmeticError:
            reason,status='nonfinite','failed'
        except (ValueError,RuntimeError):
            reason,status='engine_error','failed'
            if initial is None and any(c.f_m(q).size==0 for alpha,c in zip(
                problem['regularization'].multipliers,problem['regularization'].objfcts) if alpha>0.):
                reason,status='unsupported_sparse_empty_face','unsupported'
    if monotonic()>deadline and status=='converged': reason,status='wall_cap','nonconverged'
    return {'l2_initialization':initialization,'stages':tuple(stages),
        'irls_terminal':{'status':status,'reason':reason,'weight_updates':updates,
                         'epsilon_saturated':saturated,'stage_changes':tuple(changes)},
        'model_kg_m3':model,'iterations':steps,
        'trace':{'models_kg_m3':survey._readonly(np.array(models,dtype=np.float64).reshape(-1,a)),
                 'stage_indices':survey._readonly(np.array(labels,dtype=np.int64))}}


def _admit_request(request):
    """Complete native admission before conversion into the existing L2 input."""
    survey._native_metadata(request)
    survey._keys(request,('schema','plan','observations','noise','prior','policy','runtime_epoch'),'irls request')
    survey._enum(request['schema'],'gravity-survey-irls-calibration-request-1','irls schema')
    survey._enum(request['runtime_epoch'],RUNTIME_EPOCH,'irls epoch')
    policy=request['policy']
    survey._keys(policy,('name','beta_candidates','optimizer','training','irls'),'irls policy')
    survey._enum(policy['name'],POLICY,'irls policy name')
    _validate_policy(policy['irls'])
    # Reuse the real strict source/geometry/observation/noise/prior admission.
    # This private projection is never accepted as an IRLS result by L2.
    linear=dict(request,schema='gravity-survey-l2-calibration-request-1',runtime_epoch=l2.RUNTIME_EPOCH,
        policy={k:v for k,v in policy.items() if k!='irls'})
    linear['policy']['name']='ordinary-l2-beta-grid-1'
    l2._preflight_calibration(linear)
    admitted=l2._admit_calibration(linear)
    admitted.update(schema=request['schema'],runtime_epoch=RUNTIME_EPOCH,policy=survey._snapshot(policy))
    return admitted


def _initial_thresholds(problem,initialization,policy):
    if initialization['status']!='converged': return None
    kernels=[c.f_m(initialization['model_kg_m3']/1000.) for alpha,c in
        zip(problem['regularization'].multipliers,problem['regularization'].objfcts) if alpha>0.]
    if len(kernels)!=4 or any(k.size==0 for k in kernels): return None
    return tuple(max(f,float(np.max(np.abs(k)))) for f,k in zip(policy['epsilon_floor'],kernels))


def _workflow_fit(req,observed,noise,prior,rows,beta,observation_rows,policy,deadline,book_index):
    started=monotonic()
    parts=[]
    problem=None
    initial=None
    try:
        if started>deadline: raise l2._SolveFailure('wall_cap')
        problem=l2._build_problem(req,observed,noise,prior,rows,beta,observation_rows=observation_rows)
        raw=_solve_partition(problem,prior,policy,deadline,_stage_solutions=parts)
        initialization=raw['l2_initialization']
        initial=_initial_thresholds(problem,initialization,policy)
    except (ArithmeticError,ValueError,RuntimeError) as error:
        reason='wall_cap' if isinstance(error,l2._SolveFailure) else 'nonfinite' if isinstance(error,ArithmeticError) else 'engine_error'
        initialization=l2._unstarted_solve(rows,prior,beta,reason)
        raw={'l2_initialization':initialization,'stages':(),
            'irls_terminal':{'status':initialization['status'],'reason':reason,'weight_updates':0,
                'epsilon_saturated':False,'stage_changes':()},'model_kg_m3':None,'iterations':0,
            'trace':{'models_kg_m3':initialization['trace']['models_kg_m3'],
                'stage_indices':survey._readonly(np.empty(0,dtype=np.int64))}}
    shared=raw['trace']
    book=encode_stage_book(raw['stages'],shared,parameter_count=len(prior['start_kg_m3']),
        beta_engine=float(len(rows)*beta),initial_epsilon=initial,policy=policy)
    trace=dict(shared)
    trace['models_q']=survey._readonly(np.concatenate([initialization['trace']['models_kg_m3']/1000.]+
        [s['trace']['models_q'][1:] for s in parts]))
    for key in ('phi_d','phi_m','phi_engine','kkt_normalized'):
        trace[key]=survey._readonly(np.concatenate([initialization['trace'][key]]+
            [s['trace'][key][1:] for s in parts]))
    for key in ('relative_changes','line_search_counts','cg_counts'):
        trace[key]=survey._readonly(np.concatenate([initialization['trace'][key]]+
            [s['trace'][key] for s in parts]))
    terminal=raw['irls_terminal']
    result=dict(initialization,status=terminal['status'],reason=terminal['reason'],
        model_kg_m3=raw['model_kg_m3'],trace=trace,iterations=raw['iterations'],
        wall_seconds=float(monotonic()-started),l2_initialization=initialization,
        stages=book_index,irls_terminal=terminal,initial_epsilon=initial,
        failed_trial=None if terminal['status']=='converged' else
            {'iteration':raw['iterations'],'reason':terminal['reason']})
    for key in ('phi_d','phi_m','phi_engine','kkt_normalized'):
        name='kkt_final' if key=='kkt_normalized' else key+'_final'
        result[key]=raw['stages'][-1]['metrics'][name] if raw['stages'] else initialization[key]
    result['wrms']=float(np.sqrt(result['phi_d']/len(rows))) if result['phi_d'] is not None else None
    prediction=None
    if result['model_kg_m3'] is not None and problem is not None:
        prediction=problem['simulation'].dpred(result['model_kg_m3']/1000.)+problem['background']
        if not np.isfinite(prediction).all(): raise ArithmeticError('irls: nonfinite fit prediction')
    result['predicted_mgal']=survey._readonly(prediction) if prediction is not None else None
    positions=np.searchsorted(observation_rows,rows)
    result['residual_observed_minus_predicted_mgal']=survey._readonly(observed[positions]-prediction) if prediction is not None else None
    if monotonic()>deadline and result['status']=='converged':
        terminal.update(status='nonconverged',reason='wall_cap')
        result.update(status='nonconverged',reason='wall_cap',failed_trial={'iteration':result['iterations'],'reason':'wall_cap'})
    l2._result_native_metadata({'solve':result,'book':book})
    return result,book


def calibrate_gravity_irls(request):
    """All actual 8x3 stage workflows and one selected development refit.

    Every incomplete fold is retained and ineligible. No numerical retry,
    partial-fold score, L2 substitution or outer observation enters this call.
    """
    started=monotonic()
    admitted=_admit_request(request)
    plan,prior,policy=(admitted[k] for k in ('plan','prior','policy'))
    req,rows=plan['request'],plan['development_rows']
    observed=admitted['observations']['gz_up_mgal']
    noise={k:admitted['noise'][k] for k in ('kind','values')}
    l2._weights(noise,np.arange(len(rows),dtype=np.int64))
    diagnostics=l2._fit_diagnostics(req,noise,observed,prior,plan)
    warnings=list(diagnostics['warnings'])
    if admitted['noise']['basis']=='explicit_conditional_gaussian': warnings.append('error_assumed_conditional')
    warnings.append('geometry_uncertainty_not_propagated')
    if admitted['noise']['cross_partition_dependence']=='possible_not_removed': warnings.append('cross_partition_dependence')
    diagnostics['warnings']=tuple(warnings)
    deadline=started+1800.
    candidates,books=[],[]
    for i,beta in enumerate(l2.BETA_CANDIDATES):
        folds=[]
        for fold in plan['folds']:
            solved,book=_workflow_fit(req,observed,noise,prior,fold['fit_rows'],beta,rows,
                policy['irls'],deadline,len(books))
            books.append(book)
            metrics=(None,None,None)
            if solved['status']=='converged' and monotonic()<=deadline:
                try:
                    prediction=l2._bounded_prediction(req,solved['model_kg_m3'],deadline)
                    positions=np.searchsorted(rows,fold['validation_rows'])
                    measured=l2._marginal_metrics(prediction[fold['validation_rows']],observed[positions],noise,positions)
                    if monotonic()<=deadline: metrics=measured[:3]
                except (ArithmeticError,ValueError,RuntimeError): pass
            folds.append({'fold':fold['fold'],'solve':solved,'validation_rows':survey._readonly(fold['validation_rows']),
                'validation_phi_d':metrics[0],'validation_wrms':metrics[1],'validation_rmse_mgal':metrics[2]})
        valid=all(f['solve']['status']=='converged' for f in folds)
        scored=valid and all(f['validation_phi_d'] is not None for f in folds)
        score=float(sum(f['validation_phi_d'] for f in folds)/sum(len(f['validation_rows']) for f in folds)) if scored else None
        if score is not None and not np.isfinite(score): scored,score=False,None
        candidates.append({'index':i,'beta_candidate':beta,'eligible':bool(scored),'folds':tuple(folds),
            'score_q':score,'reason':'eligible' if scored else 'invalid_score' if valid else 'fold_failure'})
    selected=l2._selected_index(candidates)
    final,prediction,status=None,None,'insufficient_candidates'
    if selected is not None:
        final,book=_workflow_fit(req,observed,noise,prior,rows,l2.BETA_CANDIDATES[selected],rows,
            policy['irls'],deadline,len(books))
        books.append(book)
        status='selected' if final['status']=='converged' else 'final_nonconverged'
        if final['model_kg_m3'] is not None:
            try: prediction=l2._bounded_prediction(req,final['model_kg_m3'],deadline)
            except (ArithmeticError,ValueError,RuntimeError) as error:
                reason='wall_cap' if isinstance(error,l2._SolveFailure) else 'nonfinite' if isinstance(error,ArithmeticError) else 'engine_error'
                if final['status']=='converged':
                    final['irls_terminal'].update(status='nonconverged' if reason=='wall_cap' else 'failed',reason=reason)
                    final.update(status=final['irls_terminal']['status'],reason=reason,
                        failed_trial={'iteration':final['iterations'],'reason':reason})
                    status='final_nonconverged'
    fits=tuple(f['solve'] for c in candidates for f in c['folds'])+((final,) if final is not None else ())
    for candidate in candidates:
        for fold in candidate['folds']: fold['solve']=fold['solve']['stages']
    result={'schema':'gravity-survey-irls-calibration-result-3','plan':plan,
        'provenance':{'source':survey._snapshot(req['source']),'plan_sha256':plan['plan_sha256'],
            'normalized_values_sha256':admitted['observations']['values_sha256'],
            'noise_sha256':admitted['noise']['values_sha256'],'prior_sha256':survey._digest(prior),
            'policy_sha256':survey._digest(policy),'forward_source_sha256':l2.FORWARD_SOURCE,
            'runtime_epoch':RUNTIME_EPOCH,'runtime_versions':l2.forward._runtime(),
            'source_verification':'external_required_not_performed_by_solver'},
        'candidates':tuple(candidates),'selected_index':selected,'selection_status':status,
        'final_solve':24 if final is not None else None,'fits':fits,
        'predictions':{'rows':survey._readonly(np.arange(len(req['background_mgal']),dtype=np.int64)),
            'gz_up_mgal':survey._readonly(prediction) if prediction is not None else None},
        'diagnostics':diagnostics,'scope':{'training':'not_applicable_classical','inverse':'weighted_bounded_irls',
            'field_eligible':False,'full_M02_accepted':False,'API_accepted':False,'GPU_accepted':False,
            'host_accepted':False,'geometry_error':'not_propagated'},
        'irls_policy_sha256':survey._digest(policy['irls']),'stage_books':tuple(books)}
    l2._result_native_metadata(result)
    result['result_sha256']=survey._digest(result)
    l2._result_native_metadata(result)
    return result


_FIT_KEYS={'status','reason','model_kg_m3','beta_candidate','beta_engine','fit_rows','predicted_mgal',
    'residual_observed_minus_predicted_mgal','phi_d','phi_m','phi_engine','wrms','kkt_normalized','trace',
    'iterations','wall_seconds','failed_trial','l2_initialization','stages','irls_terminal','initial_epsilon'}
_TERMINAL_REASONS=l2._REASONS+('irls_fixed_point','irls_stationary_null','irls_iteration_cap','unsupported_sparse_empty_face')


def _fit_metadata(fit,a,rows,beta,*,max_book_index=24):
    survey._keys(fit,_FIT_KEYS,'irls solve')
    l2._solve_metadata(fit['l2_initialization'],a,rows,beta)
    survey._enum(fit['status'],('converged','nonconverged','failed','unsupported'),'irls status')
    survey._enum(fit['reason'],_TERMINAL_REASONS,'irls reason')
    l2._int(fit['stages'],max_book_index,'book reference')
    terminal=fit['irls_terminal']
    survey._keys(terminal,('status','reason','weight_updates','epsilon_saturated','stage_changes'),'irls terminal')
    survey._enum(terminal['status'],('converged','nonconverged','failed','unsupported'),'terminal status')
    survey._enum(terminal['reason'],_TERMINAL_REASONS,'terminal reason')
    l2._int(terminal['weight_updates'],20,'weight updates')
    if type(terminal['epsilon_saturated']) is not bool: raise TypeError('irls: exact saturation bool')
    if type(terminal['stage_changes']) is not tuple or len(terminal['stage_changes'])>20:
        raise ValueError('irls: bounded transition ledger')
    for change in terminal['stage_changes']:
        survey._keys(change,('model_relative','weights_relative'),'stage change')
        for v in change.values():
            if v is not None:
                survey._float(v,'stage change')
                if v<0.: raise ValueError('irls: negative change')
    initial=fit['initial_epsilon']
    if initial is not None and (type(initial) is not tuple or len(initial)!=4
        or any(type(v) is not float or not np.isfinite(v) or v<=0. for v in initial)):
        raise ValueError('irls: four actual initial thresholds or None')
    trace=fit['trace']
    survey._keys(trace,('models_kg_m3','models_q','stage_indices','phi_d','phi_m','phi_engine','kkt_normalized',
        'relative_changes','line_search_counts','cg_counts'),'irls trace')
    survey._array(trace['models_kg_m3'],(None,a),'physical trace')
    survey._array(trace['models_q'],trace['models_kg_m3'].shape,'native q trace')
    survey._array(trace['stage_indices'],(len(trace['models_q']),),'stage labels',np.int64)
    # Common exact native shapes/metrics/counts without calling the L2 result
    # dispatcher on a foreign discriminator or promoting an IRLS terminal.
    view={k:v for k,v in fit.items() if k in _FIT_KEYS-{'l2_initialization','stages','irls_terminal','initial_epsilon'}}
    view['trace']={k:v for k,v in trace.items() if k not in ('models_q','stage_indices')}
    view.update(status='nonconverged',reason='wall_cap',failed_trial={'iteration':fit['iterations'],'reason':'wall_cap'})
    l2._solve_metadata(view,a,rows,beta)
    failed=fit['failed_trial']
    if failed is not None:
        survey._keys(failed,('iteration','reason'),'irls failed trial')
        l2._int(failed['iteration'],200,'failed iteration')
        survey._enum(failed['reason'],_TERMINAL_REASONS,'failed reason')


def _full_metadata(result):
    survey._keys(result,('schema','plan','provenance','candidates','selected_index','selection_status','final_solve',
        'fits','predictions','diagnostics','scope','result_sha256','irls_policy_sha256','stage_books'),'irls result')
    survey._enum(result['schema'],'gravity-survey-irls-calibration-result-3','irls result schema')
    survey._sha(result['irls_policy_sha256'],'irls policy hash')
    fits,books=result['fits'],result['stage_books']
    count=24 if result['final_solve'] is None else 25
    if type(fits) is not tuple or type(books) is not tuple or len(fits)!=count or len(books)!=count:
        raise ValueError('irls: complete distinct fit/book pools')
    if result['final_solve'] is not None and (type(result['final_solve']) is not int or result['final_solve']!=24):
        raise ValueError('irls: once-only final fit reference')
    candidates=result['candidates']
    if type(candidates) is not tuple or len(candidates)!=8: raise ValueError('irls: exact eight candidates')
    plan=result['plan']
    survey._plan_result_metadata(plan)
    a=len(plan['geometry']['active_cell_indices'])
    view=dict(result)
    for key in ('fits','stage_books','irls_policy_sha256'): del view[key]
    view['schema']='gravity-survey-l2-calibration-result-1'
    survey._keys(result['provenance'],('source','plan_sha256','normalized_values_sha256','noise_sha256',
        'prior_sha256','policy_sha256','forward_source_sha256','runtime_epoch','runtime_versions','source_verification'),'provenance')
    survey._enum(result['provenance']['runtime_epoch'],RUNTIME_EPOCH,'irls provenance epoch')
    view['provenance']=dict(result['provenance'],runtime_epoch=l2.RUNTIME_EPOCH)
    survey._enum(result['scope']['inverse'],'weighted_bounded_irls','irls scope')
    view['scope']=dict(result['scope'],inverse='weighted_bounded_l2')
    linear_candidates=[]
    for i,candidate in enumerate(candidates):
        survey._keys(candidate,('index','beta_candidate','eligible','folds','score_q','reason'),'candidate')
        if type(candidate['folds']) is not tuple or len(candidate['folds'])!=3: raise ValueError('irls: exact three folds')
        folds=[]
        for j,fold in enumerate(candidate['folds']):
            survey._keys(fold,('fold','solve','validation_rows','validation_phi_d','validation_wrms','validation_rmse_mgal'),'fold')
            if type(fold['solve']) is not int or fold['solve']!=3*i+j: raise ValueError('irls: exact ordered fit reference')
            _fit_metadata(fits[3*i+j],a,plan['folds'][j]['fit_rows'],l2.BETA_CANDIDATES[i])
            if fits[3*i+j]['stages']!=3*i+j: raise ValueError('irls: exact ordered book reference')
            folds.append(dict(fold,solve=fits[3*i+j]['l2_initialization']))
        linear_candidates.append(dict(candidate,folds=tuple(folds)))
    view['candidates']=tuple(linear_candidates)
    if count==25:
        selected=result['selected_index']
        l2._int(selected,7,'selected index')
        _fit_metadata(fits[24],a,plan['development_rows'],l2.BETA_CANDIDATES[selected])
        if fits[24]['stages']!=24: raise ValueError('irls: final book identity')
        view['final_solve']=fits[24]['l2_initialization']
    l2._calibration_result_metadata(view)


def _close(actual,expected,field):
    if not np.allclose(actual,expected,rtol=1e-10,atol=1e-12):
        raise ValueError('irls replay: '+field)


def _replay_fit(fit,book,admitted,rows,beta):
    plan,prior,policy=(admitted[k] for k in ('plan','prior','policy'))
    req=plan['request']
    observed=admitted['observations']['gz_up_mgal']
    noise={k:admitted['noise'][k] for k in ('kind','values')}
    trace=fit['trace']
    shared={k:trace[k] for k in ('models_kg_m3','stage_indices')}
    stages=decode_stage_book(book,shared,parameter_count=len(prior['start_kg_m3']),
        beta_engine=float(len(rows)*beta),initial_epsilon=fit['initial_epsilon'],policy=policy['irls'])
    init=fit['l2_initialization']
    l2._validate_solve_state(init,rows)
    if not np.array_equal(fit['fit_rows'],rows): raise ValueError('irls: fit row binding')
    k=len(trace['models_q'])
    if fit['iterations']!=max(0,k-1): raise ValueError('irls: accepted count')
    initial_rows=len(init['trace']['models_kg_m3'])
    for key,value in init['trace'].items():
        if not np.array_equal(trace[key][:len(value)],value): raise ValueError('irls: full initialization prefix')
    if not np.array_equal(trace['models_q'][:initial_rows],init['trace']['models_kg_m3']/1000.):
        raise ValueError('irls: native initialization coordinates')
    if k and (fit['model_kg_m3'] is None or not np.array_equal(fit['model_kg_m3'],trace['models_kg_m3'][-1])):
        raise ValueError('irls: actual terminal model')
    if np.any(trace['models_q']<prior['lower_kg_m3']/1000.) or np.any(trace['models_q']>prior['upper_kg_m3']/1000.):
        raise ValueError('irls: native trace box')
    if initial_rows<k and not np.array_equal(trace['models_kg_m3'][initial_rows:],trace['models_q'][initial_rows:]*1000.):
        raise ValueError('irls: physical native model conversion')
    if (np.any(trace['line_search_counts']<1) or np.any(trace['line_search_counts']>20)
        or np.any(trace['cg_counts']<0) or np.any(trace['cg_counts']>200)):
        raise ValueError('irls: actual original trial/CG caps')
    for key in ('phi_d','phi_m','phi_engine','kkt_normalized'):
        name='kkt_final' if key=='kkt_normalized' else key+'_final'
        expected=stages[-1]['metrics'][name] if stages else init[key]
        if np.any(trace[key]<0.) or fit[key]!=expected:
            raise ValueError('irls: actual terminal metric')
    if fit['wrms']!=(float(np.sqrt(fit['phi_d']/len(rows))) if fit['phi_d'] is not None else None): raise ValueError('irls: terminal WRMS')
    terminal=fit['irls_terminal']
    if (fit['status'],fit['reason'])!=(terminal['status'],terminal['reason']): raise ValueError('irls: terminal identity')
    success=fit['status']=='converged'
    expected_status=('converged' if fit['reason'] in ('irls_fixed_point','irls_stationary_null') else
        'unsupported' if fit['reason']=='unsupported_sparse_empty_face' else
        'failed' if fit['reason'] in ('engine_error','state_mismatch','nonfinite') else 'nonconverged')
    if fit['status']!=expected_status or (fit['failed_trial'] is None)!=success:
        raise ValueError('irls: exact status/failure pairing')
    if not success and (fit['failed_trial']['reason']!=fit['reason'] or fit['failed_trial']['iteration']!=fit['iterations']):
        raise ValueError('irls: failure ledger')
    if terminal['weight_updates']!=max(0,len(stages)-1) or len(terminal['stage_changes'])!=max(0,len(stages)-1):
        raise ValueError('irls: actual applied update count')
    if not stages and init['status']!='converged' and fit['initial_epsilon'] is not None:
        raise ValueError('irls: thresholds after failed initialization')
    if not k:
        if stages or fit['model_kg_m3'] is not None or fit['predicted_mgal'] is not None:
            raise ValueError('irls: unstarted unavailable state')
        return
    problem=l2._build_problem(req,observed,noise,prior,rows,beta,observation_rows=plan['development_rows'])
    if fit['initial_epsilon']!=_initial_thresholds(problem,init,policy['irls']):
        raise ValueError('irls: actual initialization thresholds')
    lower,upper=prior['lower_kg_m3']/1000.,prior['upper_kg_m3']/1000.
    # Replay original initial L2 metrics without optimizing or changing beta.
    q0=trace['models_q'][0]
    norm0=max(1.,float(np.linalg.norm(problem['misfit'].deriv(q0)+problem['beta_engine']*problem['regularization'].deriv(q0),ord=np.inf)))
    for i in range(initial_rows):
        q=trace['models_q'][i]
        pd,pm=float(problem['misfit'](q)),float(problem['regularization'](q))
        _close([pd,pm,pd+problem['beta_engine']*pm],[trace[x][i] for x in ('phi_d','phi_m','phi_engine')],'L2 metrics')
        g=problem['misfit'].deriv(q)+problem['beta_engine']*problem['regularization'].deriv(q)
        _close(float(np.linalg.norm(l2._kkt_gradient(q,g,lower,upper),ord=np.inf))/norm0,trace['kkt_normalized'][i],'L2 KKT')
    last_weights=None
    saturated=False
    for index,row in enumerate(stages):
        left,right=row['model_row_start'],row['model_row_stop']
        qstart=trace['models_q'][left]
        stage=_build_stage(problem,qstart,policy['irls'],index,fit['initial_epsilon'])
        if (stage['weight_sha256']!=row['weight_sha256'] or stage['operator_sha256']!=row['operator_sha256']
            or not np.array_equal(stage['weights'][0],row['smallness_weights'])):
            raise ValueError('irls: actual native stage weights/operator replay')
        objective=_StageObjective(stage,index,lower,upper,'0'*64)
        unavailable=all(value is None for value in row['metrics'].values())
        if unavailable:
            if index!=len(stages)-1 or left!=right or row['status']=='converged':
                raise ValueError('irls: unavailable metrics only on terminal unstarted failed stage')
            if index:
                change={'model_relative':None,
                    'weights_relative':float(np.linalg.norm(stage['weights'][0]-last_weights,ord=np.inf)
                        /max(1.,float(np.linalg.norm(last_weights,ord=np.inf))))}
                if change!=terminal['stage_changes'][index-1]:
                    raise ValueError('irls: actual unavailable terminal transition')
            last_weights=stage['weights'][0]
            saturated=stage['epsilon']==policy['irls']['epsilon_floor']
            continue
        norm=max(1.,float(np.linalg.norm(objective.evaluate(qstart,True,False)[1],ord=np.inf)))
        previous_phi=None
        values=None
        for i in range(left,right+1):
            q=trace['models_q'][i]
            components=objective.components(q)
            gradient=objective.evaluate(q,True,False)[1]
            absolute=float(np.linalg.norm(l2._kkt_gradient(q,gradient,lower,upper),ord=np.inf))
            values=(components['phi_d'],components['phi_m'],components['phi_engine'],absolute/norm)
            if i==left:
                _close(values,[row['metrics'][name] for name in _BOOK_METRICS[:4]],'stage initial metrics')
            else:
                _close(values,[trace[name][i] for name in ('phi_d','phi_m','phi_engine','kkt_normalized')],'stage accepted metrics')
                _close(abs(values[2]-previous_phi)/max(1.,abs(previous_phi)),trace['relative_changes'][i-1],'within-stage change')
            previous_phi=values[2]
        _close(values,[row['metrics'][name] for name in _BOOK_METRICS[4:]],'stage final metrics')
        if row['status']=='converged':
            if row['reason']=='absolute_stationary' and absolute>1e-12: raise ValueError('irls: absolute native stage stop')
            if row['reason']=='kkt_stable' and (right-left<3 or values[3]>1e-5 or np.any(trace['relative_changes'][right-3:right]>1e-6)):
                raise ValueError('irls: native stage three-change stop')
        if index:
            change={'model_relative':float(np.linalg.norm(trace['models_q'][right]-qstart,ord=np.inf)/max(1.,float(np.linalg.norm(qstart,ord=np.inf)))),
                'weights_relative':float(np.linalg.norm(stage['weights'][0]-last_weights,ord=np.inf)/max(1.,float(np.linalg.norm(last_weights,ord=np.inf))))}
            if change!=terminal['stage_changes'][index-1]: raise ValueError('irls: actual fixed-point transition')
        last_weights=stage['weights'][0]
        saturated=stage['epsilon']==policy['irls']['epsilon_floor']
    if terminal['epsilon_saturated']!=saturated: raise ValueError('irls: actual saturation')
    if success and (len(stages)!=21 or not all(s['status']=='converged' for s in stages)
        or not _fixed_point(20,saturated,terminal['stage_changes'])):
        raise ValueError('irls: unchanged overall fixed-point criterion')
    if success and fit['reason']=='irls_stationary_null' and (np.any(trace['models_q'][-1]-problem['reference_q']) or np.any(gradient)):
        raise ValueError('irls: exact native null')
    prediction=problem['simulation'].dpred(trace['models_q'][-1])+problem['background']
    if fit['predicted_mgal'] is None or fit['residual_observed_minus_predicted_mgal'] is None:
        raise ValueError('irls: missing finite physical state')
    _close(prediction,fit['predicted_mgal'],'physical fit prediction')
    if not np.array_equal(fit['residual_observed_minus_predicted_mgal'],problem['observations']-fit['predicted_mgal']):
        raise ValueError('irls: literal residual')


def validate_gravity_irls(result,calibration_request):
    """Complete typed and native physics replay; no optimizer or partial return."""
    l2._result_native_metadata({'result':result,'request':calibration_request})
    _full_metadata(result)
    admitted=_admit_request(calibration_request)
    survey._finite(result)
    if survey._digest({k:v for k,v in result.items() if k!='result_sha256'})!=result['result_sha256']:
        raise ValueError('irls: complete result hash')
    plan,provenance=result['plan'],result['provenance']
    if survey._digest(plan)!=survey._digest(admitted['plan']): raise ValueError('irls: original plan')
    expected={'source':plan['request']['source'],'plan_sha256':plan['plan_sha256'],
        'normalized_values_sha256':admitted['observations']['values_sha256'],'noise_sha256':admitted['noise']['values_sha256'],
        'prior_sha256':survey._digest(admitted['prior']),'policy_sha256':survey._digest(admitted['policy']),
        'forward_source_sha256':l2.FORWARD_SOURCE,'runtime_epoch':RUNTIME_EPOCH,'runtime_versions':l2.forward._runtime(),
        'source_verification':'external_required_not_performed_by_solver'}
    if provenance!=expected or result['irls_policy_sha256']!=survey._digest(admitted['policy']['irls']):
        raise ValueError('irls: complete request/source/policy binding')
    noise={k:admitted['noise'][k] for k in ('kind','values')}
    for i,candidate in enumerate(result['candidates']):
        for j,fold in enumerate(candidate['folds']):
            rows=plan['folds'][j]['fit_rows']
            fit=result['fits'][3*i+j]
            _replay_fit(fit,result['stage_books'][3*i+j],admitted,rows,l2.BETA_CANDIDATES[i])
            if not np.array_equal(fold['validation_rows'],plan['folds'][j]['validation_rows']): raise ValueError('irls: validation rows')
            metrics=[fold[k] for k in ('validation_phi_d','validation_wrms','validation_rmse_mgal')]
            if any(v is not None for v in metrics):
                if fit['status']!='converged' or any(v is None for v in metrics): raise ValueError('irls: no partial score')
                prediction=l2._physical_prediction(plan['request'],fit['model_kg_m3'])
                positions=np.searchsorted(plan['development_rows'],fold['validation_rows'])
                actual=l2._marginal_metrics(prediction[fold['validation_rows']],admitted['observations']['gz_up_mgal'][positions],noise,positions)
                _close(actual[:3],metrics,'validation marginal score')
        valid=all(result['fits'][f['solve']]['status']=='converged' for f in candidate['folds'])
        eligible=valid and all(f['validation_phi_d'] is not None for f in candidate['folds'])
        score=float(sum(f['validation_phi_d'] for f in candidate['folds'])/sum(len(f['validation_rows']) for f in candidate['folds'])) if eligible else None
        reason='eligible' if eligible else 'invalid_score' if valid else 'fold_failure'
        if (candidate['eligible'],candidate['score_q'],candidate['reason'])!=(eligible,score,reason): raise ValueError('irls: complete eligibility/score')
    selected=l2._selected_index(result['candidates'])
    if result['selected_index']!=selected: raise ValueError('irls: fixed selection/tie')
    if selected is None:
        if result['final_solve'] is not None or result['selection_status']!='insufficient_candidates': raise ValueError('irls: unselected refit')
        if result['predictions']['gz_up_mgal'] is not None: raise ValueError('irls: unselected prediction')
    else:
        if result['final_solve']!=24: raise ValueError('irls: missing selected refit')
        final=result['fits'][24]
        _replay_fit(final,result['stage_books'][24],admitted,plan['development_rows'],l2.BETA_CANDIDATES[selected])
        status='selected' if final['status']=='converged' else 'final_nonconverged'
        if result['selection_status']!=status: raise ValueError('irls: selected refit status')
        if result['predictions']['gz_up_mgal'] is not None:
            _close(l2._physical_prediction(plan['request'],final['model_kg_m3']),result['predictions']['gz_up_mgal'],'full prediction')
        elif status=='selected': raise ValueError('irls: unavailable selected prediction')
    if not np.array_equal(result['predictions']['rows'],np.arange(len(plan['request']['background_mgal']),dtype=np.int64)):
        raise ValueError('irls: complete original prediction rows')
    expected_diagnostics=l2._fit_diagnostics(plan['request'],noise,admitted['observations']['gz_up_mgal'],admitted['prior'],plan)
    warnings=list(expected_diagnostics['warnings'])
    if admitted['noise']['basis']=='explicit_conditional_gaussian': warnings.append('error_assumed_conditional')
    warnings.append('geometry_uncertainty_not_propagated')
    if admitted['noise']['cross_partition_dependence']=='possible_not_removed': warnings.append('cross_partition_dependence')
    expected_diagnostics['warnings']=tuple(warnings)
    for key in expected_diagnostics:
        if type(expected_diagnostics[key]) is np.ndarray: _close(expected_diagnostics[key],result['diagnostics'][key],'fit diagnostics')
        elif expected_diagnostics[key]!=result['diagnostics'][key]: raise ValueError('irls: diagnostic identity')
    return result


def evaluate_gravity_irls(request):
    """Separate frozen outer marginal evaluation, with complete native replay."""
    l2._result_native_metadata(request)
    survey._keys(request,('schema','frozen_calibration','calibration_request','observations','noise'),'irls evaluation')
    survey._enum(request['schema'],'gravity-survey-irls-evaluation-request-3','irls evaluation schema')
    frozen=validate_gravity_irls(request['frozen_calibration'],request['calibration_request'])
    if frozen['selection_status']!='selected': raise ValueError('irls: unsuccessful frozen calibration')
    # Reuse strict normalized observation/noise validators with an outer-only
    # shape receipt, never invoking the optimizer or passing IRLS to L2 dispatch.
    rows=frozen['plan']['outer_rows']
    observed,noise=request['observations'],request['noise']
    survey._keys(observed,('rows','gz_up_mgal','values_sha256','acceleration_unit','vertical_positive'),'outer observations')
    survey._array(observed['rows'],rows.shape,'outer rows',np.int64)
    survey._array(observed['gz_up_mgal'],rows.shape,'outer values')
    survey._enum(observed['acceleration_unit'],'mGal','outer unit')
    survey._enum(observed['vertical_positive'],'up','outer sign')
    survey._sha(observed['values_sha256'],'outer value hash')
    survey._keys(noise,('kind','values','unit','basis','citation','values_sha256','cross_partition_dependence'),'outer noise')
    survey._enum(noise['kind'],('diagonal_sd','full_covariance'),'outer noise kind')
    covariance=noise['kind']=='full_covariance'
    survey._array(noise['values'],(len(rows),len(rows)) if covariance else rows.shape,'outer noise values')
    survey._enum(noise['unit'],'mGal^2' if covariance else 'mGal','outer noise unit')
    survey._enum(noise['basis'],('measured_gaussian','propagated_independent_gaussian','explicit_conditional_gaussian'),'outer basis')
    survey._enum(noise['cross_partition_dependence'],('declared_absent','possible_not_removed'),'outer dependence')
    survey._text(noise['citation'],'outer noise citation')
    survey._sha(noise['values_sha256'],'outer noise hash')
    survey._finite({'observations':observed,'noise':noise})
    if not np.array_equal(rows,observed['rows']): raise ValueError('irls: outer row identity')
    if survey._digest({k:v for k,v in observed.items() if k!='values_sha256'})!=observed['values_sha256']:
        raise ValueError('irls: outer observation hash')
    if survey._digest({k:noise[k] for k in ('kind','unit','values')}|{'rows':rows})!=noise['values_sha256']:
        raise ValueError('irls: outer noise hash')
    prediction=survey._readonly(frozen['predictions']['gz_up_mgal'][rows])
    phi,wrms,rmse,residual,whitened=l2._marginal_metrics(prediction,observed['gz_up_mgal'],
        {k:noise[k] for k in ('kind','values')},np.arange(len(rows),dtype=np.int64))
    result={'schema':'gravity-survey-irls-evaluation-result-3','calibration_sha256':frozen['result_sha256'],
        'observations':survey._snapshot(observed),'noise_sha256':noise['values_sha256'],'rows':survey._readonly(rows),
        'predicted_mgal':prediction,'residual_observed_minus_predicted_mgal':survey._readonly(residual),
        'whitened_residual':survey._readonly(whitened),'phi_d':phi,'wrms':wrms,'rmse_mgal':rmse,
        'prediction_quality':'within_declared_noise' if wrms<=2. else 'poor_under_declared_noise',
        'dependence':noise['cross_partition_dependence'],'geometry_conditioning':'fixed_not_propagated',
        'field_truth':None,'model_accuracy':None,'field_eligible':False,'full_M02_accepted':False}
    result['result_sha256']=survey._digest(result)
    l2._result_native_metadata({'evaluation':result,'frozen':frozen})
    return result
