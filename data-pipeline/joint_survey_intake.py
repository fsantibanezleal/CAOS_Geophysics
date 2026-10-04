"""Confined original-byte M11 development intake; no fit or sealed-value I/O.

Private caller diagnostics, not safe HTTP errors. Source hashes are integrity,
not rights/correction science. This is not a concurrent filesystem snapshot.
"""
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import stat

import numpy as np

import joint_survey_plan as planner
import joint_survey_objective as objective


MAX_DIRECTORY_BYTES = 256*1024**2
MAX_HEADER_BYTES = 4096
_MODALITIES = ('gravity','magnetic')
_SURVEY_PATHS = {
    'mesh_origin':('mesh','origin_m'), 'mesh_hx':('mesh','hx_m'),
    'mesh_hy':('mesh','hy_m'), 'mesh_hz':('mesh','hz_m'),
    'mesh_active':('mesh','active'), 'prior_lengths':('prior','lengths_m'),
}
for _modality in _MODALITIES:
    for _key in ('receivers','mask','groups','partition'):
        _SURVEY_PATHS[_modality+'_'+_key]=(_modality,_key+'_m' if _key=='receivers' else _key)
for _prop in ('density','susceptibility'):
    for _key in ('lower','upper','start','reference'):
        _SURVEY_PATHS[_prop+'_'+_key]=('prior',_prop,_key)
_DEVELOPMENT_PATHS = {m+'_development_'+label:(m,key) for m in _MODALITIES
                      for label,key in (('rows','rows'),('observed','observed'),('noise','noise_values'))}
_IDS = set(_SURVEY_PATHS)|set(_DEVELOPMENT_PATHS)
_DTYPES = {key: ('|b1' if key in ('mesh_active','gravity_mask','magnetic_mask')
                else '<i8' if key.endswith(('_groups','_partition','_rows')) else '<f8') for key in _IDS}


def _ordinary(path, directory=False):
    info=path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError('intake: link/reparse input rejected')
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError('intake: ordinary directory/file required')
    return info


def _identity(info):
    return info.st_size,info.st_mtime_ns,info.st_ino,info.st_dev


def _unchanged(path, previous):
    if _identity(_ordinary(path))!=_identity(previous):
        raise ValueError('intake: file identity drift')


def _file_sha(path):
    before=_ordinary(path)
    if before.st_size>MAX_DIRECTORY_BYTES: raise ValueError('intake: hash byte cap')
    digest=hashlib.sha256()
    consumed=0
    with path.open('rb') as stream:
        if _identity(os.fstat(stream.fileno()))!=_identity(before):
            raise ValueError('intake: open file identity drift')
        while block:=stream.read(min(65536,before.st_size-consumed+1)):
            consumed+=len(block)
            if consumed>before.st_size: raise ValueError('intake: growing file hash drift')
            digest.update(block)
    _unchanged(path,before)
    return digest.hexdigest()


def _read_bounded(path, maximum):
    before=_ordinary(path)
    if not 0<before.st_size<=maximum: raise ValueError('intake: file byte cap')
    with path.open('rb') as stream:
        if _identity(os.fstat(stream.fileno()))!=_identity(before):
            raise ValueError('intake: open file identity drift')
        content=stream.read(maximum+1)
    _unchanged(path,before)
    if len(content)!=before.st_size: raise ValueError('intake: file size drift')
    return content


def _parse_json(content):
    text=content.decode('utf-8',errors='strict')
    if text.startswith('\ufeff'): raise ValueError('intake: BOM rejected')
    # Bound structural depth BEFORE building the decoded tree. String escapes
    # do not change depth, including braces inside scientific citations.
    depth=0; quoted=False; escaped=False
    for char in text:
        if quoted:
            if escaped: escaped=False
            elif char=='\\': escaped=True
            elif char=='"': quoted=False
        elif char=='"': quoted=True
        elif char in '{[':
            depth+=1
            if depth>8: raise ValueError('intake: JSON depth exceeds8')
        elif char in '}]': depth-=1
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: raise ValueError('intake: duplicate JSON key')
            result[key]=value
        return result
    def constant(value): raise ValueError('intake: nonfinite JSON constant')
    result=json.loads(text,object_pairs_hook=pairs,parse_constant=constant)
    def finite(node):
        if type(node) is dict:
            for value in node.values(): finite(value)
        elif type(node) is list:
            for value in node: finite(value)
        elif type(node) is float and not math.isfinite(node):
            raise ValueError('intake: nonfinite JSON float')
    finite(result)
    return result


def _header(path, descriptor):
    before=_ordinary(path)
    if before.st_size!=descriptor['file_bytes']: raise ValueError('intake: NPY declared file length')
    with path.open('rb') as stream:
        prefix=stream.read(10)
        if len(prefix)!=10 or prefix[:8]!=b'\x93NUMPY\x01\x00':
            raise ValueError('intake: NPY v1.0 only')
        length=int.from_bytes(prefix[8:],'little')
        if not 1<=length<=MAX_HEADER_BYTES: raise ValueError('intake: NPY header cap')
        text=stream.read(length)
    _unchanged(path,before)
    if len(text)!=length or not text.endswith(b'\n'):
        raise ValueError('intake: NPY header truncated/newline')
    try:
        tree=ast.parse(text.decode('latin1').strip(),mode='eval')
        nodes=list(ast.walk(tree))
        if len(nodes)>64 or any(type(n) not in (ast.Expression,ast.Dict,ast.Constant,ast.Tuple,ast.Load) for n in nodes):
            raise ValueError('intake: bounded literal NPY header required')
        if type(tree.body) is not ast.Dict:
            raise ValueError('intake: NPY header dictionary required')
        keys=[n.value if type(n) is ast.Constant and type(n.value) is str else None for n in tree.body.keys]
        if len(keys)!=3 or set(keys)!={'descr','fortran_order','shape'}:
            raise ValueError('intake: exact unique NPY header keys')
        header=ast.literal_eval(tree)
    except (SyntaxError,UnicodeError,RecursionError) as exc:
        raise ValueError('intake: invalid NPY header') from exc
    if (type(header['descr']) is not str or header['descr']!=descriptor['dtype']
            or type(header['fortran_order']) is not bool or header['fortran_order']
            or type(header['shape']) is not tuple or any(type(n) is not int for n in header['shape'])
            or list(header['shape'])!=descriptor['shape']):
        raise ValueError('intake: NPY header descriptor mismatch')
    logical=math.prod(descriptor['shape'])*np.dtype(descriptor['dtype']).itemsize
    if before.st_size!=10+length+logical:
        raise ValueError('intake: NPY trailing/truncated values')
    return before


def _replace(container, paths, arrays):
    for identifier,path in paths.items():
        node=container
        for key in path[:-1]:
            if type(node) is not dict or key not in node: raise ValueError('intake: required native path')
            node=node[key]
        if type(node) is not dict or path[-1] not in node: raise ValueError('intake: required native field')
        reference=node[path[-1]]
        planner._keys(reference,('array',),'intake.array_reference')
        if type(reference['array']) is not str or reference['array']!=identifier:
            raise ValueError('intake: exact one-field array binding')
        node[path[-1]]=arrays[identifier]


def _materialize(document, arrays):
    # JSON-derived exact builtins only. This copying is metadata, not array
    # allocation or conversion from custom objects. No supplied path executes.
    def clone(v):
        if type(v) is dict: return {k:clone(child) for k,child in v.items()}
        if type(v) is list: return [clone(child) for child in v]
        return v
    survey=clone(document['survey']);development=clone(document['development'])
    _replace(survey,_SURVEY_PATHS,arrays);_replace(development,_DEVELOPMENT_PATHS,arrays)
    if type(survey.get('frame')) is not dict or type(survey['frame'].get('axes')) is not list:
        raise TypeError('intake: serialized frame.axes list required')
    survey['frame']['axes']=tuple(survey['frame']['axes'])
    for m in _MODALITIES:
        if type(survey.get(m)) is not dict or type(survey[m].get('missing_reasons')) is not list:
            raise TypeError('intake: serialized missing_reasons list required')
        survey[m]['missing_reasons']=tuple(survey[m]['missing_reasons'])
    return survey,development


def _development_metadata(survey,development):
    planner._contract(survey)
    planner._keys(development,('plan_sha256','gravity','magnetic'),'development')
    objective._sha(development['plan_sha256'],'development.plan_sha256')
    for m in _MODALITIES:
        d=development[m]
        planner._keys(d,('rows','observed','noise_values','observations_sha256','noise_sha256'),'development.'+m)
        rows=d['rows']
        if type(rows) is not np.ndarray or rows.dtype!=np.dtype('int64'):
            raise TypeError('intake: exact native development rows')
        if rows.ndim!=1 or not 2<=len(rows)<=min(2048,len(survey[m]['receivers_m'])):
            raise ValueError('intake: development row count')
        planner._array(d['observed'],(len(rows),),'development.observed')
        shape=(len(rows),)*2 if survey[m]['noise']['kind']=='full_covariance' else (len(rows),)
        planner._array(d['noise_values'],shape,'development.noise_values')
        for key in ('observations_sha256','noise_sha256'): objective._sha(d[key],key)
    planner._metadata_budget({'survey':survey,'development':development})


def _preflight(document, inventory):
    planner._keys(document,('schema','survey','development','arrays','sealed_manifest','raw_access'),'intake')
    planner._enum(document['schema'],('joint-survey-intake-1',),'intake.schema')
    descriptors=document['arrays'];planner._keys(descriptors,_IDS,'intake.arrays')
    placeholders={};logical=0
    for identifier,d in descriptors.items():
        planner._keys(d,('dtype','shape','file_bytes','file_sha256','data_sha256'),'array.descriptor')
        if type(d['dtype']) is not str or d['dtype']!=_DTYPES[identifier]:
            raise ValueError('intake: exact native descriptor dtype')
        shape=d['shape']
        if (type(shape) is not list or not 1<=len(shape)<=2
                or any(type(n) is not int or not 1<=n<=4096 for n in shape)):
            raise ValueError('intake: bounded native descriptor shape')
        if type(d['file_bytes']) is not int or not 10<d['file_bytes']<=MAX_DIRECTORY_BYTES:
            raise ValueError('intake: descriptor file byte cap')
        for key in ('file_sha256','data_sha256'): objective._sha(d[key],key)
        logical+=math.prod(shape)*np.dtype(d['dtype']).itemsize
        if logical>planner.MAX_ARRAY_BYTES: raise ValueError('intake: logical arrays exceed96MiB')
        # Metadata-only zero-stride arrays backed by ONE native scalar. These
        # descriptors are NEVER scanned, hashed, returned or sent to physics.
        placeholders[identifier]=np.lib.stride_tricks.as_strided(np.zeros(1,dtype=d['dtype']),
            shape=tuple(shape),strides=(0,)*len(shape),writeable=False)
    survey,development=_materialize(document,placeholders)
    _development_metadata(survey,development)
    sealed=document['sealed_manifest']
    planner._keys(sealed,('schema','gravity','magnetic'),'sealed_manifest')
    planner._enum(sealed['schema'],('joint-survey-sealed-manifest-1',),'sealed.schema')
    access=document['raw_access'];planner._keys(access,_MODALITIES,'raw_access')
    expected={'request.json'}|{identifier+'.npy' for identifier in _IDS}
    for m in _MODALITIES:
        s=sealed[m];planner._keys(s,('rows_sha256','observations_file_sha256','noise_file_sha256','count','noise_kind'),'sealed.'+m)
        for key in ('rows_sha256','observations_file_sha256','noise_file_sha256'): objective._sha(s[key],key)
        if type(s['count']) is not int or not 1<=s['count']<=2048:
            raise ValueError('intake: sealed count integer1..2048')
        if type(s['noise_kind']) is not str or s['noise_kind']!=survey[m]['noise']['kind']:
            raise ValueError('intake: sealed noise kind mismatch')
        a=access[m];planner._keys(a,('availability','raw_present','correction_present'),'raw_access.'+m)
        planner._enum(a['availability'],('provided','provider_reference_only'),'availability')
        provided=a['availability']=='provided'
        if any(type(a[k]) is not bool or a[k]!=provided for k in ('raw_present','correction_present')):
            raise ValueError('intake: raw presence/availability mismatch')
        if provided:
            expected.update((m+'.raw',m+'.corrections.json'))
            if inventory.get(m+'.raw',None) is None or inventory[m+'.raw'].st_size!=survey[m]['source']['raw_bytes']:
                raise ValueError('intake: provided original raw size')
            correction=inventory.get(m+'.corrections.json')
            if correction is None or not 0<correction.st_size<=planner.MAX_METADATA_BYTES:
                raise ValueError('intake: correction receipt byte cap')
    if set(inventory)!=expected: raise ValueError('intake: exact input file inventory required')
    return survey,development


def load_joint_development(directory: str) -> dict:
    """Admit original development bytes without loading any sealed observations."""
    if type(directory) is not str: raise TypeError('intake: exact builtin directory string')
    root=Path(directory)
    if not directory or not root.is_absolute(): raise ValueError('intake: absolute local directory required')
    # Check each component BEFORE resolve can erase evidence of a junction.
    for parent in reversed((root,*root.parents)): _ordinary(parent,directory=True)
    root=root.resolve(strict=True)
    allowed={'request.json'}|{i+'.npy' for i in _IDS}|{m+suffix for m in _MODALITIES for suffix in ('.raw','.corrections.json')}
    inventory={};total=0
    with os.scandir(root) as entries:
        for entry in entries:
            if entry.name not in allowed or entry.name in inventory:
                raise ValueError('intake: unexpected/case-variant input file')
            info=_ordinary(root/entry.name)
            inventory[entry.name]=info;total+=info.st_size
            if total>MAX_DIRECTORY_BYTES: raise ValueError('intake: directory exceeds256MiB')
    if 'request.json' not in inventory: raise ValueError('intake: request.json required')
    original=_read_bounded(root/'request.json',planner.MAX_METADATA_BYTES)
    document=_parse_json(original)
    _preflight(document,inventory)
    for identifier,d in document['arrays'].items(): _header(root/(identifier+'.npy'),d)
    # EVERY descriptor/header/native metadata guard above precedes value hashes,
    # array loading, finite scans, raw reads and TensorMesh construction below.
    hashes={};arrays={}
    for identifier,d in document['arrays'].items():
        path=root/(identifier+'.npy');_unchanged(path,inventory[path.name])
        hashes[path.name]=_file_sha(path)
        if hashes[path.name]!=d['file_sha256']: raise ValueError('intake: NPY file hash mismatch')
        with path.open('rb') as stream: value=np.load(stream,allow_pickle=False,max_header_size=MAX_HEADER_BYTES)
        if type(value) is not np.ndarray or value.dtype.str!=d['dtype'] or list(value.shape)!=d['shape']:
            raise ValueError('intake: loaded native descriptor drift')
        owned=planner._snapshot(value)
        if hashlib.sha256(owned.tobytes(order='C')).hexdigest()!=d['data_sha256']:
            raise ValueError('intake: native data hash mismatch')
        _unchanged(path,inventory[path.name])
        if _file_sha(path)!=hashes[path.name]: raise ValueError('intake: post-load content hash drift')
        arrays[identifier]=owned
    survey,development=_materialize(document,arrays)
    _development_metadata(survey,development)
    planner._finite({'survey':survey,'development':development})
    plan=planner.plan_joint_survey(survey)
    if development['plan_sha256']!=plan['plan_sha256']: raise ValueError('intake: stale native plan binding')
    raw_sha={};correction_sha={}
    for m in _MODALITIES:
        s=plan[m];d=development[m];sealed=document['sealed_manifest'][m]
        if not np.array_equal(d['rows'],np.r_[s['training_rows'],s['validation_rows']]):
            raise ValueError('intake: exact training then validation rows required')
        if planner._digest({'rows':d['rows'],'observed':d['observed'],'unit':s['unit'],
                            'plan_sha256':plan['plan_sha256']})!=d['observations_sha256']:
            raise ValueError('intake: observation identity drift')
        if planner._digest({'rows':d['rows'],'noise_values':d['noise_values'],'unit':s['noise']['unit'],
                            'kind':s['noise']['kind'],'plan_sha256':plan['plan_sha256']})!=d['noise_sha256']:
            raise ValueError('intake: noise identity drift')
        objective._weights(s,d,len(s['training_rows']))
        if (sealed['count']!=len(s['sealed_rows'])
                or sealed['rows_sha256']!=hashlib.sha256(s['sealed_rows'].tobytes(order='C')).hexdigest()):
            raise ValueError('intake: sealed row identity/count mismatch')
        raw_sha[m]=None;correction_sha[m]=None
        if document['raw_access'][m]['availability']=='provided':
            for suffix,key,target in (('.raw','raw_sha256',raw_sha),('.corrections.json','correction_sha256',correction_sha)):
                name=m+suffix;_unchanged(root/name,inventory[name]);hashes[name]=_file_sha(root/name)
                if hashes[name]!=s['source'][key]: raise ValueError('intake: original source/correction hash mismatch')
                target[m]=hashes[name]
    hashes['request.json']=hashlib.sha256(original).hexdigest()
    for name,expected in hashes.items():
        _unchanged(root/name,inventory[name])
        if _file_sha(root/name)!=expected: raise ValueError('intake: final consumed input hash drift')
    # No success if an extra/removed input appeared while native admission ran.
    with os.scandir(root) as entries:
        current=set()
        for entry in entries:
            if entry.name not in inventory: raise ValueError('intake: input inventory drift')
            current.add(entry.name)
        if current!=set(inventory): raise ValueError('intake: removed input inventory drift')
    _ordinary(root,directory=True)
    content={name:{'bytes':inventory[name].st_size,'sha256':h} for name,h in hashes.items()}
    return {'schema':'joint-survey-development-intake-1','survey_request':planner._snapshot(survey),
        'plan':plan,'development':planner._snapshot(development),'sealed_manifest':document['sealed_manifest'],
        'bindings':{'request_file_sha256':hashes['request.json'],
            'directory_content_sha256':hashlib.sha256(planner._json(content).encode('utf-8')).hexdigest(),
            'development_sha256':planner._digest(development),'raw_sha256':raw_sha,'correction_sha256':correction_sha},
        'diagnostics':{'rights_verified':False,'source_bytes_verified':{m:raw_sha[m] is not None for m in _MODALITIES},
            'correction_bytes_verified':{m:correction_sha[m] is not None for m in _MODALITIES},
            'correction_science_verified':False,'field_eligible':False,'inverse_completed':False,
            'sealed_values_loaded':False,'concurrent_snapshot_guaranteed':False}}
