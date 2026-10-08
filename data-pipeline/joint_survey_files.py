"""Closed-grammar array directories for M11; no user paths or executable objects."""
from copy import deepcopy
import hashlib
import json
import math
import os

import numpy as np

import joint_survey_intake as intake
import joint_survey_objective as objective
import joint_survey_plan as planner
from joint_survey_serialization import _external, _npy_header


def _content(payload):
    return json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def metadata_budget(value,*,max_array_bytes=planner.MAX_ARRAY_BYTES):
    """Incremental closed JSON admission, BEFORE full-tree copy/serialization."""
    used=0;scalars=0;logical=0
    def charge(count):
        nonlocal used
        used+=count
        if used>planner.MAX_METADATA_BYTES: raise ValueError('joint files: metadata byte cap')
    def walk(node,depth):
        nonlocal scalars,logical
        if depth>8: raise ValueError('joint files: metadata depth exceeds8')
        if type(node) is dict:
            charge(2+max(0,len(node)-1))
            for key in node:
                planner._text(key,'metadata key');charge(len(_content(key))+1)
            for child in node.values(): walk(child,depth+1)
        elif type(node) in (tuple,list):
            charge(2+max(0,len(node)-1))
            for child in node: walk(child,depth+1)
        elif type(node) is np.ndarray:
            if node.dtype.str not in ('<f8','<i8','|b1') or node.ndim>2:
                raise ValueError('joint files: metadata native array')
            logical+=node.nbytes
            if logical>max_array_bytes: raise ValueError('joint files: logical arrays cap')
            charge(len(_content({'dtype':node.dtype.str,'shape':list(node.shape),'sha256':'0'*64})))
        elif node is None or type(node) in (str,int,float,bool):
            scalars+=1
            if scalars>32768: raise ValueError('joint files: metadata scalar cap')
            if type(node) is str: planner._text(node,'metadata text',empty=True)
            if type(node) is int and abs(node)>2**63-1: raise ValueError('joint files: metadata integer cap')
            charge(len(_content(node)))
        else: raise TypeError('joint files: exact builtin metadata types')
    walk(value,0)
    return used


def _descriptors(arrays,*,max_array_bytes=planner.MAX_ARRAY_BYTES):
    descriptors={};headers={};logical=0
    for name,value in arrays.items():
        if type(name) is not str or not name or any(c not in 'abcdefghijklmnopqrstuvwxyz_0123456789' for c in name):
            raise ValueError('joint files: fixed identifier required')
        if (type(value) is not np.ndarray or value.dtype.str not in ('<f8','<i8','|b1')
                or not 1<=value.ndim<=2 or any(not 0<=n<=8192 for n in value.shape)):
            raise ValueError('joint files: native bounded array required')
        logical+=value.nbytes
        if logical>max_array_bytes: raise ValueError('joint files: logical arrays cap')
    # Whole logical admission precedes finite scan, copying, hash or header generation.
    planner._finite(arrays)
    owned=planner._snapshot(arrays)
    for name,value in owned.items():
        header=_npy_header(value);headers[name]=header
        raw=memoryview(value).cast('B') if value.nbytes else b''
        digest=hashlib.sha256(header);digest.update(raw)
        descriptors[name]={'dtype':value.dtype.str,'shape':list(value.shape),'file_bytes':len(header)+value.nbytes,
            'file_sha256':digest.hexdigest(),'data_sha256':hashlib.sha256(raw).hexdigest()}
    return owned,descriptors,headers


def write_arrays(directory,filename,schema,payload,arrays,*,max_array_bytes=planner.MAX_ARRAY_BYTES):
    """Caller owns a CLOSED record grammar; envelope and file inventory are exact."""
    root=_external(directory)
    if root.exists(): raise FileExistsError('joint files: destination exists')
    intake._ordinary(root.parent,directory=True)
    metadata_budget({'payload':payload,'arrays':arrays},max_array_bytes=max_array_bytes)
    owned,descriptors,headers=_descriptors(arrays,max_array_bytes=max_array_bytes)
    content=_content({'schema':schema,'payload':payload,'arrays':descriptors})
    if len(content)>planner.MAX_METADATA_BYTES: raise ValueError('joint files: serialized metadata cap')
    if len(content)+sum(d['file_bytes'] for d in descriptors.values())>intake.MAX_DIRECTORY_BYTES:
        raise ValueError('joint files: directory cap')
    root.mkdir(mode=0o700)
    for name,value in owned.items():
        with (root/(name+'.npy')).open('xb') as stream:
            stream.write(headers[name])
            if value.nbytes: stream.write(memoryview(value).cast('B'))
    with (root/filename).open('xb') as stream: stream.write(content)
    return {'manifest_sha256':hashlib.sha256(content).hexdigest(),'arrays':deepcopy(descriptors)}


def read_arrays(directory,filename,schema,specs,validate_payload,validate_descriptors=None,*,max_array_bytes=planner.MAX_ARRAY_BYTES):
    """Validate ALL record metadata and headers before any value load/hash."""
    root=_external(directory,existing=True)
    allowed={filename}|{name+'.npy' for name in specs};inventory={};total=0
    with os.scandir(root) as entries:
        for entry in entries:
            if entry.name not in allowed or entry.name in inventory:
                raise ValueError('joint files: unexpected/case-variant file')
            info=intake._ordinary(root/entry.name);total+=info.st_size;inventory[entry.name]=info
            if total>intake.MAX_DIRECTORY_BYTES: raise ValueError('joint files: directory cap')
    if set(inventory)!=allowed: raise ValueError('joint files: exact inventory required')
    original=intake._read_bounded(root/filename,planner.MAX_METADATA_BYTES)
    doc=intake._parse_json(original)
    planner._keys(doc,('schema','payload','arrays'),'joint file')
    planner._enum(doc['schema'],(schema,),'joint file.schema')
    planner._keys(doc['arrays'],specs,'joint file.arrays')
    validate_payload(doc['payload'])
    logical=0
    for name,(dtype,shape) in specs.items():
        d=doc['arrays'][name]
        planner._keys(d,('dtype','shape','file_bytes','file_sha256','data_sha256'),'descriptor')
        if (type(d['dtype']) is not str or d['dtype']!=dtype or type(d['shape']) is not list
                or any(type(n) is not int for n in d['shape']) or tuple(d['shape'])!=shape):
            raise ValueError('joint files: exact dtype/shape')
        if type(d['file_bytes']) is not int or not 10<d['file_bytes']<=intake.MAX_DIRECTORY_BYTES:
            raise ValueError('joint files: file bytes cap')
        for key in ('file_sha256','data_sha256'): objective._sha(d[key],key)
        logical+=math.prod(shape)*np.dtype(dtype).itemsize
        if logical>max_array_bytes: raise ValueError('joint files: logical arrays cap')
    if validate_descriptors is not None: validate_descriptors(doc['arrays'])
    for name,d in doc['arrays'].items(): intake._header(root/(name+'.npy'),d)
    arrays={}
    for name,d in doc['arrays'].items():
        path=root/(name+'.npy');intake._unchanged(path,inventory[path.name])
        if intake._file_sha(path)!=d['file_sha256']: raise ValueError('joint files: original file hash mismatch')
        with path.open('rb') as stream:
            value=np.load(stream,allow_pickle=False,max_header_size=intake.MAX_HEADER_BYTES)
        if type(value) is not np.ndarray or value.dtype.str!=d['dtype'] or list(value.shape)!=d['shape']:
            raise ValueError('joint files: loaded array drift')
        if hashlib.sha256(memoryview(value).cast('B') if value.nbytes else b'').hexdigest()!=d['data_sha256']:
            raise ValueError('joint files: data hash mismatch')
        arrays[name]=planner._snapshot(value)
        intake._unchanged(path,inventory[path.name])
        if intake._file_sha(path)!=d['file_sha256']: raise ValueError('joint files: post-load hash drift')
    for name,info in inventory.items(): intake._unchanged(root/name,info)
    if intake._file_sha(root/filename)!=hashlib.sha256(original).hexdigest():
        raise ValueError('joint files: manifest drift')
    if set(os.listdir(root))!=allowed: raise ValueError('joint files: inventory drift')
    planner._finite(arrays)
    return doc['payload'],arrays,{'manifest_sha256':hashlib.sha256(original).hexdigest(),'arrays':doc['arrays']}
