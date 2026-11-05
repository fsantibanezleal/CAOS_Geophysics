"""32 actual fixed-recipe conditional data-noise refits, not a posterior."""
from time import monotonic

import numpy as np

import gravity_irls as irls
import gravity_l2 as l2
import gravity_survey_l2 as survey
import gravity_workflow_io as workflow

SEED = 20261008
COUNT = 32


def _pool(values,dtype):
    size=len(values)
    array=np.zeros(((size+4095)//4096,4096),dtype=dtype)
    if size: array.reshape(-1)[:size]=values
    return survey._readonly(array)


def _records(fits,books):
    value={'fits':fits,'stage_books':books}
    l2._result_native_metadata(value)
    nodes,edges,strings=[],[],[]
    pools=[[],[],[]]
    def encode(item):
        index=len(nodes)
        nodes.append([0,0,0,0,0])
        kind=type(item)
        if kind is dict or kind is tuple:
            children=tuple(v for pair in item.items() for v in pair) if kind is dict else item
            start=len(edges)
            edges.extend([0]*len(children))
            nodes[index]=[8 if kind is dict else 9,start,len(children),0,0]
            for offset,child in enumerate(children): edges[start+offset]=encode(child)
        elif kind is str:
            if item not in strings: strings.append(item)
            nodes[index]=[4,strings.index(item),0,0,0]
        elif kind is np.ndarray:
            pool={'f':0,'i':1,'b':2}[item.dtype.kind]
            start=len(pools[pool])
            pools[pool].extend(item.reshape(-1).tolist())
            nodes[index]=[5+pool,start,item.size,item.shape[0],item.shape[1] if item.ndim==2 else -1]
        elif kind in (bool,int,float):
            pool={bool:2,int:1,float:0}[kind]
            start=len(pools[pool])
            pools[pool].append(item)
            nodes[index]=[{bool:1,int:2,float:3}[kind],start,1,0,0]
        elif item is not None: raise TypeError('refits: native record type')
        return index
    encode(value)
    table=np.zeros(((len(nodes)+4095)//4096*4096,5),dtype=np.int64)
    table[:len(nodes)]=nodes
    return {'schema':'gravity-refit-record-book-1','strings':tuple(strings),
        'nodes':tuple(survey._readonly(table[i:i+4096]) for i in range(0,len(table),4096)),
        'edges':_pool(edges,np.int64),'floats':_pool(pools[0],np.float64),
        'integers':_pool(pools[1],np.int64),'booleans':_pool(pools[2],bool),
        'lengths':survey._readonly(np.array([len(nodes),len(edges),*(len(v) for v in pools)],dtype=np.int64))}


def _decode_records(book):
    """Complete structural barrier before any fit is available for replay."""
    survey._keys(book,('schema','strings','nodes','edges','floats','integers','booleans','lengths'),'refit record book')
    survey._enum(book['schema'],'gravity-refit-record-book-1','record schema')
    survey._array(book['lengths'],(5,),'record lengths',np.int64)
    lengths=book['lengths']
    if np.any(lengths<0) or not 1<=lengths[0]<=65536 or lengths[1]>65536: raise ValueError('refits: bounded nodes/edges')
    strings=book['strings']
    if type(strings) is not tuple or len(strings)>32768 or any(type(v) is not str for v in strings) or len(set(strings))!=len(strings):
        raise ValueError('refits: exact distinct string table')
    chunks=book['nodes']
    if type(chunks) is not tuple or len(chunks)!=(int(lengths[0])+4095)//4096: raise ValueError('refits: node blocks')
    for chunk in chunks: survey._array(chunk,(4096,5),'record nodes',np.int64)
    nodes=np.concatenate(chunks)[:lengths[0]]
    if np.any(chunks[-1][int(lengths[0])%4096:]!=0) and int(lengths[0])%4096:
        raise ValueError('refits: node padding')
    buffers=[]
    for key,dtype,length in zip(('edges','floats','integers','booleans'),(np.int64,np.float64,np.int64,np.bool_),lengths[1:]):
        value=book[key]
        survey._array(value,((int(length)+4095)//4096,4096),'record '+key,dtype)
        flat=value.reshape(-1)
        if np.any(flat[int(length):]!=0): raise ValueError('refits: pool padding')
        buffers.append(flat[:length])
    edges,*pools=buffers
    visited=set()
    used_strings=set()
    cursors=[0,0,0]
    edge_cursor=0
    scalar_count=0
    def decode(index,depth=0):
        nonlocal edge_cursor,scalar_count
        if type(index) is not int or not 0<=index<len(nodes) or index in visited or depth>8:
            raise ValueError('refits: node identity/parent/depth')
        visited.add(index)
        code,start,count,dim1,dim2=map(int,nodes[index])
        if code in (8,9):
            if dim1 or dim2 or count<0 or start!=edge_cursor or start+count>len(edges) or code==8 and count%2:
                raise ValueError('refits: contiguous container edges')
            edge_cursor+=count
            children=[decode(int(i),depth+1) for i in edges[start:start+count]]
            if code==9: return tuple(children)
            result={}
            for key,value in zip(children[::2],children[1::2]):
                if type(key) is not str or key in result: raise ValueError('refits: closed dictionary node keys')
                result[key]=value
            return result
        if code==4:
            if count or dim1 or dim2 or not 0<=start<len(strings): raise ValueError('refits: string node')
            used_strings.add(start)
            scalar_count+=1
            return strings[start]
        if code==0:
            if start or count or dim1 or dim2: raise ValueError('refits: canonical None node')
            scalar_count+=1
            return None
        if not 1<=code<=7: raise ValueError('refits: closed node code')
        pool={1:2,2:1,3:0,5:0,6:1,7:2}[code]
        if start!=cursors[pool] or count<0 or start+count>len(pools[pool]): raise ValueError('refits: sequential distinct operand spans')
        cursors[pool]+=count
        values=pools[pool][start:start+count]
        if code<4:
            if count!=1 or dim1 or dim2: raise ValueError('refits: exact scalar node')
            scalar_count+=1
            return {1:bool,2:int,3:float}[code](values[0])
        if not 0<=dim1<=4096 or not -1<=dim2<=4096 or count!=dim1*(1 if dim2==-1 else dim2):
            raise ValueError('refits: original native array shape')
        return values.reshape((dim1,) if dim2==-1 else (dim1,dim2))
    value=decode(0)
    if (len(visited)!=len(nodes) or edge_cursor!=len(edges) or cursors!=[len(v) for v in pools]
        or used_strings!=set(range(len(strings))) or scalar_count>32768):
        raise ValueError('refits: complete node/edge/string/pool barrier')
    survey._keys(value,('fits','stage_books'),'decoded records')
    return value


def _frozen(request, frozen):
    workflow.verify_calibration({'schema':'gravity-calibration-archive-1','request':request,'result':frozen})
    if frozen['selection_status']!='selected': raise ValueError('refits: unsuccessful frozen calibration')
    sparse = frozen['schema'] in ('gravity-survey-irls-calibration-result-3',
        'gravity-survey-irls-corrected-calibration-result-1', 'gravity-survey-irls-original-calibration-result-1')
    engine = _corrected_engine(frozen)
    admitted = engine.admit(request) if engine else irls._admit_request(request) if sparse else l2._admit_calibration(request)
    return sparse, admitted, l2.BETA_CANDIDATES[frozen['selected_index']]


def _corrected_engine(frozen):
    if frozen['schema'] == 'gravity-survey-irls-corrected-calibration-result-1':
        from gravity_irls_corrected_workflow import _Workflow
        return _Workflow('cpu2')
    if frozen['schema'] == 'gravity-survey-irls-original-calibration-result-1':
        from gravity_irls_corrected_workflow import _Workflow
        return _Workflow('cpu3')
    return None


def _targets(admitted):
    observed = admitted['observations']['gz_up_mgal']
    noise = admitted['noise']
    generator = np.random.Generator(np.random.PCG64(SEED))
    draws = generator.standard_normal((COUNT,len(observed)))
    if noise['kind']=='diagonal_sd': draws *= noise['values']
    else: draws = draws@np.linalg.cholesky(noise['values']).T
    return draws+observed


def _perturbed(admitted, values):
    result = dict(admitted)
    observations = dict(admitted['observations'],gz_up_mgal=values)
    observations['values_sha256']=survey._digest({k:v for k,v in observations.items() if k!='values_sha256'})
    result['observations']=observations
    return result


def _pack_fit(fit):
    result=dict(fit)
    terminal=dict(fit['irls_terminal'])
    changes=terminal['stage_changes']
    values=np.zeros((len(changes),2),dtype=np.float64)
    available=np.zeros(values.shape,dtype=bool)
    for index,change in enumerate(changes):
        for column,key in enumerate(('model_relative','weights_relative')):
            if change[key] is not None: values[index,column],available[index,column]=change[key],True
    terminal['stage_changes']={'values':survey._readonly(values),'available':survey._readonly(available)}
    result['irls_terminal']=terminal
    return result


def _unpack_fit(fit):
    result=dict(fit)
    terminal=dict(fit['irls_terminal'])
    changes=terminal['stage_changes']
    survey._keys(changes,('values','available'),'refit transition columns')
    survey._array(changes['values'],(None,2),'refit change values')
    survey._array(changes['available'],changes['values'].shape,'refit change availability',np.bool_)
    if len(changes['values'])>20 or np.any(changes['values']<0.) or np.any(changes['values'][~changes['available']]!=0.):
        raise ValueError('refits: transition columns canonical nonnegative/null values')
    terminal['stage_changes']=tuple({key:float(changes['values'][index,column]) if changes['available'][index,column] else None
        for column,key in enumerate(('model_relative','weights_relative'))} for index in range(len(changes['values'])))
    result['irls_terminal']=terminal
    return result


def refit_gravity_noise(request, frozen):
    started = monotonic()
    sparse, admitted, beta = _frozen(request,frozen)
    plan,prior = admitted['plan'],admitted['prior']
    rows = plan['development_rows']
    targets = _targets(admitted)
    l2._result_native_metadata({'targets':targets,'request':request})
    fits,books = [],[]
    noise = {k:admitted['noise'][k] for k in ('kind','values')}
    deadline = started+1800.
    engine = _corrected_engine(frozen)
    for index,values in enumerate(targets):
        if engine:
            fit = engine._fit(_perturbed(admitted, values), rows, beta, deadline)
        elif sparse:
            fit,book = irls._workflow_fit(plan['request'],values,noise,prior,rows,beta,rows,
                admitted['policy']['irls'],deadline,index)
            books.append(book)
        else: fit = l2._run_fit(plan['request'],values,noise,prior,rows,beta,rows,deadline)
        fits.append(_pack_fit(fit) if sparse and not engine else fit)
    result = {'schema':'gravity-noise-refits-result-1','calibration_sha256':frozen['result_sha256'],
        'request_sha256':survey._digest(request),'method':'irls' if sparse else 'l2',
        'seed':SEED,'generator':'numpy-2.2.6-PCG64','count':COUNT,'beta_candidate':beta,
        'rows':survey._readonly(rows),'targets_mgal':survey._readonly(targets),
        'records':_records(tuple(fits),tuple(books)),
        'successful':survey._readonly(np.array([
            engine._summary(engine_pool_decode(f))[0]=='converged' if engine else f['status']=='converged'
            for f in fits],dtype=bool)),
        'wall_seconds':monotonic()-started,'conditioning':'declared_gaussian_data_noise_fixed_recipe',
        'posterior':False,'coverage_calibrated':False,'field_truth':None,'field_eligible':False,'full_M02_accepted':False}
    l2._result_native_metadata(result)
    result['result_sha256']=survey._digest(result)
    return result


def engine_pool_decode(value):
    from gravity_irls_pool import decode
    return decode(value)


def validate_noise_refits(result, request, frozen):
    # Charge the complete envelope before original calibration or array traversal.
    l2._result_native_metadata({'refits':result,'request':request,'frozen':frozen})
    survey._keys(result,('schema','calibration_sha256','request_sha256','method','seed','generator','count',
        'beta_candidate','rows','targets_mgal','records','successful','wall_seconds','conditioning',
        'posterior','coverage_calibrated','field_truth','field_eligible','full_M02_accepted','result_sha256'),'noise refits')
    survey._enum(result['schema'],'gravity-noise-refits-result-1','refits schema')
    sparse, admitted, beta = _frozen(request,frozen)
    rows = admitted['plan']['development_rows']
    survey._array(result['rows'],rows.shape,'refit rows',np.int64)
    survey._array(result['targets_mgal'],(COUNT,len(rows)),'refit targets')
    survey._array(result['successful'],(COUNT,),'refit success',np.bool_)
    survey._float(result['wall_seconds'],'refit timing')
    if result['wall_seconds']<0.: raise ValueError('refits: negative elapsed')
    survey._finite(result)
    if type(result['seed']) is not int or type(result['count']) is not int or result['seed']!=SEED or result['count']!=COUNT:
        raise ValueError('refits: exact frozen count/seed')
    for key,value in {'calibration_sha256':frozen['result_sha256'],'request_sha256':survey._digest(request),
        'method':'irls' if sparse else 'l2','generator':'numpy-2.2.6-PCG64',
        'conditioning':'declared_gaussian_data_noise_fixed_recipe'}.items():
        survey._enum(result[key],value,key)
    survey._float(result['beta_candidate'],'refit beta')
    if result['beta_candidate']!=beta: raise ValueError('refits: frozen beta')
    for key in ('posterior','coverage_calibrated','field_eligible','full_M02_accepted'):
        if type(result[key]) is not bool or result[key] is not False: raise ValueError('refits: exact nonclaim')
    if result['field_truth'] is not None: raise ValueError('refits: no field truth')
    if not np.array_equal(result['rows'],rows) or not np.array_equal(result['targets_mgal'],_targets(admitted)):
        raise ValueError('refits: exact regenerated development-only targets')
    records=_decode_records(result['records'])
    fits,books = records['fits'],records['stage_books']
    engine = _corrected_engine(frozen)
    if type(fits) is not tuple or len(fits)!=COUNT or type(books) is not tuple or len(books)!=(COUNT if sparse and not engine else 0):
        raise ValueError('refits: every actual fit/book retained')
    if survey._digest({k:v for k,v in result.items() if k!='result_sha256'})!=result['result_sha256']:
        raise ValueError('refits: complete result hash')
    a = len(admitted['prior']['start_kg_m3'])
    for index,fit in enumerate(fits):
        current = _perturbed(admitted,result['targets_mgal'][index])
        if engine:
            raw = engine_pool_decode(fit)
            status = engine._summary(raw)[0]
            if raw['schema'] == 'gravity-corrected-unstarted-1':
                survey._keys(raw, ('schema','status','reason','fit_rows','beta_candidate','iterations','model_kg_m3'), 'unstarted refit')
                if (raw['iterations'] != 0 or raw['model_kg_m3'] is not None
                    or raw['reason'] not in ('wall_cap','engine_error','nonfinite')
                    or raw['status'] not in ('nonconverged','failed') or raw['beta_candidate'] != beta
                    or not np.array_equal(raw['fit_rows'], rows)):
                    raise ValueError('refits: unavailable corrected state')
            elif engine.recipe == 'cpu3':
                engine.engine.validate_partition(raw, current['plan']['request'], result['targets_mgal'][index],
                    {k:current['noise'][k] for k in ('kind','values')}, current['prior'], rows, beta,
                    policy=current['policy']['irls'], observation_rows=rows)
            else:
                problem = l2._build_problem(current['plan']['request'], result['targets_mgal'][index],
                    {k:current['noise'][k] for k in ('kind','values')}, current['prior'], rows, beta,
                    observation_rows=rows)
                engine.engine.validate_partition(raw, problem, current['prior'], current['policy']['irls'])
        elif sparse:
            fit=_unpack_fit(fit)
            irls._fit_metadata(fit,a,rows,beta,max_book_index=31)
            if fit['stages']!=index: raise ValueError('refits: distinct ordered book')
            irls._replay_fit(fit,books[index],current,rows,beta)
        else:
            l2._solve_metadata(fit,a,rows,beta)
            workflow.replay_l2_fit(fit,current,rows,beta)
        if not engine:
            status = fit['status']
        if bool(result['successful'][index])!=(status=='converged'): raise ValueError('refits: actual success mask')
    return result
