"""Bounded supplied-survey M11 planner, not an inverse or field admission.

No file/network/environment I/O. Caller must keep inputs private during snapshot.
Errors are private caller diagnostics, not safe HTTP payloads. Source/rights
verification requires an external trusted receipt, never a caller assertion alone.
"""

import hashlib
import json
import math
import sys

import discretize
import geoana
import numpy as np
import scipy
import simpeg


MAX_METADATA_BYTES = 262144
MAX_ARRAY_BYTES = 96*1024**2
MAX_KERNEL_BYTES = 128*1024**2
MAX_EXPORT_BYTES = 256*1024**2
GEOMETRY_RTOL = 1e-10
VERSIONS = {'numpy':'2.2.6','scipy':'1.15.2','simpeg':'0.25.2',
            'geoana':'0.8.1','discretize':'0.12.0'}
POLICY = {'name':'joint-survey-l2-cross-gradient-1','seed':42,'cell_order':'x-fast',
          'training':'not_applicable_classical','group_scope':'global_acquisition',
          'modal_covariance':'independent'}


def _keys(value, keys, field):
    if type(value) is not dict:
        raise TypeError(f'{field}: builtin dict required')
    if len(value)!=len(keys) or any(type(k) is not str for k in value) or set(value)!=set(keys):
        raise ValueError(f'{field}: exact keys required')


def _text(value, field, empty=False):
    if type(value) is not str:
        raise TypeError(f'{field}: builtin string required')
    if len(value)>4096 or (not value and not empty) or len(value.encode('utf-8'))>4096:
        raise ValueError(f'{field}: text outside declared byte limit')


def _enum(value, allowed, field):
    _text(value,field)
    if value not in allowed:
        raise ValueError(f'{field}: unsupported value')


def _float(value, lower, upper, field):
    if type(value) is not float:
        raise TypeError(f'{field}: builtin float required')
    if not math.isfinite(value) or not lower<=value<=upper:
        raise ValueError(f'{field}: outside physical bounds')


def _array(value, shape, field, dtype=np.float64):
    if type(value) is not np.ndarray or value.dtype!=np.dtype(dtype):
        raise TypeError(f'{field}: exact native dtype/ndarray required')
    if value.shape!=shape:
        raise ValueError(f'{field}: wrong shape')


def _json(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def _metadata_budget(value, maximum=None):
    """Incremental native descriptor bytes; NO hash/copy/array-value traversal.

    Empty containers consume punctuation. Logical aliases are charged per use.
    This is separate from closed ABI checks, never a coercion/serialization API.
    """
    maximum=MAX_METADATA_BYTES if maximum is None else maximum
    used=0; scalars=0; array_bytes=0

    def charge(n):
        nonlocal used
        used+=n
        if used>maximum:
            raise ValueError('metadata: compact descriptor exceeds byte cap')

    def walk(node,depth):
        nonlocal scalars,array_bytes
        if depth>8:
            raise ValueError('metadata: depth exceeds8')
        if type(node) is dict:
            # Key types before sorting/equality; container punctuation before
            # visits. Keys themselves have a bounded string serialization.
            if len(node)>maximum:
                raise ValueError('metadata: container exceeds byte cap')
            if any(type(k) is not str for k in node):
                raise TypeError('metadata: native string keys required')
            charge(2+max(0,len(node)-1))
            for key in node:
                _text(key,'metadata.key'); charge(len(_json(key).encode('utf-8'))+1)
            for child in node.values(): walk(child,depth+1)
        elif type(node) is tuple:
            charge(2+max(0,len(node)-1))
            for child in node: walk(child,depth+1)
        elif type(node) is np.ndarray:
            if node.dtype not in (np.dtype('float64'),np.dtype('int64'),np.dtype('bool')) or node.ndim>2:
                raise TypeError('metadata: unsupported array dtype/dimensions')
            array_bytes+=node.nbytes
            if array_bytes>MAX_ARRAY_BYTES:
                raise ValueError('metadata: logical arrays exceed96MiB')
            descriptor={'dtype':node.dtype.str,'shape':list(node.shape),'sha256':'0'*64}
            charge(len(_json(descriptor).encode('utf-8')))
        elif type(node) in (str,int,float,bool):
            scalars+=1
            if scalars>32768: raise ValueError('metadata: scalar limit exceeded')
            if type(node) is str: _text(node,'metadata.text',empty=True)
            if type(node) is int and abs(node)>2**63-1: raise ValueError('metadata: integer range')
            if type(node) is float and not math.isfinite(node): raise ValueError('metadata: finite float required')
            charge(len(_json(node).encode('utf-8')))
        else:
            raise TypeError('metadata: unsupported native type')

    walk(value,0)
    return used


def _contract(req):
    _keys(req,('schema','frame','mesh','gravity','magnetic','prior','policy'),'request')
    _enum(req['schema'],('joint-survey-plan-request-1',),'schema')
    frame=req['frame']
    _keys(frame,('kind','axes','length_unit','vertical_positive','reference_id',
                 'horizontal_datum','vertical_datum'),'frame')
    for key,expected in (('kind','local_cartesian'),('length_unit','m'),('vertical_positive','up')):
        _enum(frame[key],(expected,),'frame.'+key)
    axes=frame['axes']
    if type(axes) is not tuple or len(axes)!=3 or any(type(a) is not str for a in axes):
        raise TypeError('frame.axes: builtin tuple of three strings required')
    if axes!=('east','north','up'): raise ValueError('frame.axes: ENU required')
    for key in ('reference_id','horizontal_datum','vertical_datum'): _text(frame[key],'frame.'+key)
    mesh=req['mesh']; _keys(mesh,('origin_m','hx_m','hy_m','hz_m','active'),'mesh')
    _array(mesh['origin_m'],(3,),'mesh.origin_m')
    dims=[]
    for key in ('hx_m','hy_m','hz_m'):
        a=mesh[key]
        if type(a) is not np.ndarray or a.dtype!=np.dtype('float64'):
            raise TypeError('mesh widths: native float64 ndarray required')
        if a.ndim!=1 or not 2<=len(a)<=64: raise ValueError('mesh widths: axis length2..64 required')
        dims.append(len(a))
    full=math.prod(dims)
    if full>4096: raise ValueError('mesh: full cells exceed4096')
    _array(mesh['active'],(full,),'mesh.active',np.bool_)
    n_active=None
    prior=req['prior']
    _keys(prior,('density','susceptibility','lengths_m','coupling_length_m','basis'),'prior')
    for prop,lo,hi in (('density',1e-3,5000.),('susceptibility',1e-8,.1)):
        p=prior[prop]; _keys(p,('lower','upper','start','reference','scale'),'prior.'+prop)
        v=p['lower']
        if type(v) is not np.ndarray or v.dtype!=np.dtype('float64'):
            raise TypeError('prior.lower: native float64 ndarray required')
        if v.ndim!=1 or not 1<=len(v)<=full: raise ValueError('prior.lower: active length cap')
        if n_active is None: n_active=len(v)
        if len(v)!=n_active: raise ValueError('prior: properties must have common active count')
        for key in ('lower','upper','start','reference'): _array(p[key],(n_active,),'prior.'+prop+'.'+key)
        _float(p['scale'],lo,hi,'prior.'+prop+'.scale')
    _array(prior['lengths_m'],(3,),'prior.lengths_m')
    _float(prior['coupling_length_m'],1e-3,1e5,'prior.coupling_length_m'); _text(prior['basis'],'prior.basis')
    counts=[]
    for modality,component,unit in (('gravity','gz_up','mGal'),('magnetic','linear_tmi','nT')):
        s=req[modality]
        expected=('source','reference_id','component','unit','receivers_m','mask','missing_reasons',
                  'groups','partition','noise')+(('inducing_field',) if modality=='magnetic' else ())
        _keys(s,expected,modality); _enum(s['component'],(component,),modality+'.component')
        _enum(s['unit'],(unit,),modality+'.unit'); _text(s['reference_id'],modality+'.reference_id')
        r=s['receivers_m']
        if type(r) is not np.ndarray or r.dtype!=np.dtype('float64'):
            raise TypeError(modality+'.receivers_m: native float64 ndarray required')
        if r.ndim!=2 or r.shape[1]!=3 or not 3<=len(r)<=2048:
            raise ValueError(modality+'.receivers_m: shape3..2048 by3 required')
        n=len(r); counts.append(n)
        _array(s['mask'],(n,),modality+'.mask',np.bool_)
        for key in ('groups','partition'): _array(s[key],(n,),modality+'.'+key,np.int64)
        reasons=s['missing_reasons']
        if type(reasons) is not tuple or len(reasons)!=n: raise TypeError(modality+'.missing_reasons: tuple(N)')
        for reason in reasons: _text(reason,modality+'.missing_reasons',empty=True)
        source=s['source']
        _keys(source,('source_id','citation','raw_sha256','raw_bytes','rights','correction_sha256'),modality+'.source')
        for key in ('source_id','citation'): _text(source[key],modality+'.source.'+key)
        for key in ('raw_sha256','correction_sha256'):
            v=source[key]; _text(v,modality+'.source.'+key)
            if len(v)!=64 or any(c not in '0123456789abcdef' for c in v): raise ValueError('source: lowercase SHA256')
        if type(source['raw_bytes']) is not int or not 1<=source['raw_bytes']<=1073741824:
            raise ValueError('source.raw_bytes: builtin integer byte limit')
        _enum(source['rights'],('private_use','provider_link_only','redistributable'),'source.rights')
        noise=s['noise']; _keys(noise,('kind','unit','basis','cross_partition','citation'),modality+'.noise')
        _enum(noise['kind'],('diagonal_sd','full_covariance'),'noise.kind')
        _enum(noise['unit'],(unit+'^2' if noise['kind']=='full_covariance' else unit,),'noise.unit')
        _enum(noise['basis'],('measured_gaussian','propagated_gaussian','conditional_gaussian'),'noise.basis')
        _enum(noise['cross_partition'],('declared_absent','possible_not_removed'),'noise.cross_partition')
        _text(noise['citation'],'noise.citation')
        if modality=='magnetic':
            field=s['inducing_field']; _keys(field,('amplitude_nt','inclination_deg','declination_deg'),'inducing_field')
            for key,lo,hi in (('amplitude_nt',1.,1e6),('inclination_deg',-90.,90.),('declination_deg',-180.,180.)):
                _float(field[key],lo,hi,'inducing_field.'+key)
            if field['declination_deg']==180.: raise ValueError('inducing_field.declination_deg: half-open upper bound')
    policy=req['policy']; _keys(policy,POLICY,'policy')
    for key,expected in POLICY.items():
        if type(policy[key]) is not type(expected): raise TypeError('policy: exact builtin field types')
        if policy[key]!=expected: raise ValueError('policy: frozen values required')
    descriptor_bytes=_metadata_budget(req)
    kernel_bytes=(counts[0]+3*counts[1])*n_active*8
    export_bytes=(kernel_bytes+sum(a.nbytes for a in _arrays(req))
                  +36*251*n_active*8+54*sum(counts)*8)
    if kernel_bytes>MAX_KERNEL_BYTES: raise ValueError('resources: projected kernels exceed128MiB')
    if export_bytes>MAX_EXPORT_BYTES: raise ValueError('resources: projected export exceeds256MiB')
    return descriptor_bytes,kernel_bytes,export_bytes


def _arrays(value):
    if type(value) is dict:
        return [a for child in value.values() for a in _arrays(child)]
    if type(value) is tuple:
        return [a for child in value for a in _arrays(child)]
    return [value] if type(value) is np.ndarray else []


def _finite(req):
    if any(not np.isfinite(a).all() for a in _arrays(req)):
        raise ValueError('arrays: finite values required, no zero replacement')


def _snapshot(value):
    if type(value) is dict: return {k:_snapshot(v) for k,v in value.items()}
    if type(value) is tuple: return tuple(_snapshot(v) for v in value)
    if type(value) is np.ndarray:
        owned=np.array(value,copy=True,order='C'); owned.flags.writeable=False; return owned
    return value


def _digest(value):
    def descriptor(v):
        if type(v) is dict: return {k:descriptor(c) for k,c in v.items()}
        if type(v) is tuple: return [descriptor(c) for c in v]
        if type(v) is np.ndarray:
            return {'dtype':v.dtype.str,'shape':list(v.shape),
                    'sha256':hashlib.sha256(v.tobytes(order='C')).hexdigest()}
        return v
    return hashlib.sha256(_json(descriptor(value)).encode('utf-8')).hexdigest()


def _geometry(req):
    mesh=req['mesh']; widths=[mesh[k] for k in ('hx_m','hy_m','hz_m')]; origin=mesh['origin_m']
    if np.any(abs(origin)>1e7): raise ValueError('mesh: coordinate cap')
    if any(np.any((w<1e-3)|(w>1e5)) or float(np.sum(w))>1e5 for w in widths):
        raise ValueError('mesh: widths/span outside bounds')
    edges=[o+np.r_[0.,np.cumsum(w)] for o,w in zip(origin,widths)]
    for e,w in zip(edges,widths):
        if (not np.isfinite(e).all() or np.any(abs(e)>1e7) or np.any(np.diff(e)<=0)
                or np.any(abs(np.diff(e)-w)>GEOMETRY_RTOL*w)):
            raise ValueError('mesh: unfaithful or invalid edges')
        centre=e[:-1]+np.diff(e)/2
        if not np.all((centre>e[:-1])&(centre<e[1:])): raise ValueError('mesh: unrepresentable interior centre')
    # Genuine TensorMesh state, not imagined bounds from centre +/- half width.
    tensor=discretize.TensorMesh(widths,origin=origin)
    for actual,e,w in zip((tensor.nodes_x,tensor.nodes_y,tensor.nodes_z),edges,widths):
        local=np.r_[w[0],np.minimum(w[:-1],w[1:]),w[-1]]
        if (actual.shape!=e.shape or not np.isfinite(actual).all()
                or np.any(np.diff(actual)<=0) or np.any(abs(np.diff(actual)-w)>GEOMETRY_RTOL*w)
                or np.any(abs(actual-e)>GEOMETRY_RTOL*local)):
            raise ValueError('mesh: actual nodes disagree with declared edges')
    shape=tuple(len(w) for w in widths)
    ijk=np.unravel_index(np.arange(math.prod(shape)),shape,order='F')
    bounds=np.column_stack([e[i+side] for e,i in zip(edges,ijk) for side in (0,1)])
    lengths=np.column_stack([w[i] for w,i in zip(widths,ijk)])
    actual=tensor.cell_bounds; centres=tensor.cell_centers; volumes=tensor.cell_volumes
    if (actual.shape!=bounds.shape or not np.isfinite(actual).all()
            or np.any(abs(actual-bounds)>GEOMETRY_RTOL*np.repeat(lengths,2,axis=1))
            or centres.shape!=(len(bounds),3) or not np.isfinite(centres).all()
            or not np.all((centres>actual[:,::2])&(centres<actual[:,1::2]))
            or np.any(abs(centres-(bounds[:,::2]+lengths/2))>GEOMETRY_RTOL*lengths)):
        raise ValueError('mesh: actual bounds/interior centres disagree')
    declared_volume=np.prod(lengths,axis=1); actual_volume=np.prod(actual[:,1::2]-actual[:,::2],axis=1)
    if (volumes.shape!=declared_volume.shape or not np.isfinite(volumes).all()
            or np.any(declared_volume<=0) or np.any(actual_volume<=0)
            or np.any(abs(actual_volume-declared_volume)>GEOMETRY_RTOL*declared_volume)
            or np.any(abs(volumes-declared_volume)>GEOMETRY_RTOL*declared_volume)):
        raise ValueError('mesh: actual/declared volume fidelity')
    lower=np.array([e[0] for e in edges]); upper=np.array([e[-1] for e in edges])
    for modality in ('gravity','magnetic'):
        rx=req[modality]['receivers_m']
        if np.any(abs(rx)>1e7) or not np.all(np.any((rx<lower)|(rx>upper),axis=1)):
            raise ValueError(modality+': receivers must be strictly outside closed full source box')
        if len(np.unique(rx,axis=0))!=len(rx): raise ValueError(modality+': duplicate receiver geometry')


def _values(req):
    n_active=int(np.count_nonzero(req['mesh']['active']))
    if n_active!=len(req['prior']['density']['lower']): raise ValueError('mesh: active population mismatch')
    p=req['prior']
    if np.any((p['lengths_m']<1e-3)|(p['lengths_m']>1e5)): raise ValueError('prior: physical length bounds')
    for prop,lo,hi in (('density',-5000.,5000.),('susceptibility',0.,.1)):
        v=p[prop]
        if np.any(v['lower']<lo) or np.any(v['upper']>hi) or np.any(v['lower']>=v['upper']):
            raise ValueError('prior: strict physical property bounds')
        for key in ('start','reference'):
            if np.any((v[key]<v['lower'])|(v[key]>v['upper'])): raise ValueError('prior: model outside supplied bounds')
    assignments={}
    for modality in ('gravity','magnetic'):
        survey=req[modality]
        if survey['reference_id']!=req['frame']['reference_id']: raise ValueError('frame: co-registration reference mismatch')
        if np.any(survey['groups']<0) or np.any((survey['partition']<0)|(survey['partition']>2)):
            raise ValueError('split: invalid group/partition')
        for group,part in zip(survey['groups'],survey['partition']):
            g,p=int(group),int(part)
            if g in assignments and assignments[g]!=p: raise ValueError('split: global group crosses partitions')
            assignments[g]=p
        for masked,reason in zip(survey['mask'],survey['missing_reasons']):
            if bool(masked)!=bool(reason): raise ValueError('mask: exact missingness reason alignment')
        for part in (0,1,2):
            if not np.any((survey['partition']==part)&~survey['mask']): raise ValueError('split: empty unmasked partition')
    if req['gravity']['source']['source_id']==req['magnetic']['source']['source_id']:
        raise ValueError('source: distinct modality source records required')
    _geometry(req)
    return n_active


def _runtime():
    observed={m.__name__:m.__version__ for m in (np,scipy,simpeg,geoana,discretize)}
    if any(type(v) is not str for v in observed.values()) or observed!=VERSIONS:
        raise RuntimeError('runtime: loaded official versions differ')
    if (sys.version_info[:3]!=(3,12,10) or sys.platform!='win32'
            or sys.implementation.name!='cpython' or sys.maxsize!=2**63-1):
        raise RuntimeError('runtime: unreviewed source/platform epoch')


def plan_joint_survey(request: dict) -> dict:
    """Admit/snapshot supplied geometry and fixed split; never fit observations."""
    descriptor_bytes,kernel_bytes,export_bytes=_contract(request)
    _finite(request)
    _runtime()
    n_active=_values(request)
    plan=_snapshot(request); plan['schema']='joint-survey-plan-1'
    for modality in ('gravity','magnetic'):
        s=plan[modality]
        for part,key in enumerate(('training_rows','validation_rows','sealed_rows')):
            s[key]=_snapshot(np.flatnonzero((s['partition']==part)&~s['mask']).astype(np.int64))
    plan['resources']={'logical_input_bytes':sum(a.nbytes for a in _arrays(request)),
                       'projected_kernel_bytes':kernel_bytes,'projected_export_bytes':export_bytes,
                       'descriptor_bytes':descriptor_bytes}
    plan['diagnostics']={'rights_verified':False,'source_bytes_verified':False,'field_eligible':False,
                         'inverse_completed':False,'active_cells':n_active,
                         'shared_raw_bytes':request['gravity']['source']['raw_sha256']==request['magnetic']['source']['raw_sha256'],
                         'common_frame_declared':True,'rank_not_assessed':True}
    plan['plan_sha256']=_digest(plan)
    return plan
