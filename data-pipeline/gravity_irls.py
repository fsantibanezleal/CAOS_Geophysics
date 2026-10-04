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


def _solve_partition(problem,prior,policy,deadline):
    """Real L2 initialization and0..20 immutable fixed Sparse stages.

    Private six-key unit result; NOT a public L2/IRLS calibration result or bundle.
    Shared accepted model rows, stage-specific Phi only (no global monotone Phi).
    """
    policy=_validate_policy(policy)
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
