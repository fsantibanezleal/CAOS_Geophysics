"""Exclusive external development serialization; no solve, publication or bake."""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path

import numpy as np

import joint_survey_intake as intake
import joint_survey_objective as objective
import joint_survey_plan as planner


def _external(path,*,existing=False):
    if type(path) is not str or not path or not Path(path).is_absolute():
        raise ValueError('joint storage: explicit absolute external path required')
    candidate=Path(path)
    for parent in reversed((candidate,*candidate.parents)):
        if parent.exists() or parent.is_symlink():
            intake._ordinary(parent,directory=True)
            if (parent/'.git').exists(): raise ValueError('joint storage: repository path forbidden')
    resolved=candidate.resolve(strict=existing)
    return resolved


def local_joint_data_root(root=None):
    """Resolve only explicit external configuration; no creation or cwd fallback."""
    if root is None: root=os.environ.get('GEOPHYSICS_LOCAL_DATA_ROOT')
    return _external(root,existing=True)


def _npy_header(value):
    stream=io.BytesIO()
    np.lib.format.write_array_header_1_0(stream,{'descr':value.dtype.str,'fortran_order':False,'shape':value.shape})
    header=stream.getvalue()
    if len(header)>intake.MAX_HEADER_BYTES: raise ValueError('joint storage: NPY header cap')
    return header


def _set(node,path,value):
    for key in path[:-1]: node=node[key]
    node[path[-1]]=value


def _get(node,path):
    for key in path: node=node[key]
    return node


def _manifest(value,plan):
    planner._keys(value,('schema','gravity','magnetic'),'sealed_manifest')
    planner._enum(value['schema'],('joint-survey-sealed-manifest-1',),'sealed_manifest.schema')
    for m in ('gravity','magnetic'):
        entry=value[m]
        planner._keys(entry,('rows_sha256','observations_file_sha256','noise_file_sha256','count','noise_kind'),'sealed.'+m)
        for key in ('rows_sha256','observations_file_sha256','noise_file_sha256'): objective._sha(entry[key],key)
        if type(entry['count']) is not int or entry['count']!=len(plan[m]['sealed_rows']):
            raise ValueError('joint storage: sealed count drift')
        if type(entry['noise_kind']) is not str or entry['noise_kind']!=plan[m]['noise']['kind']:
            raise ValueError('joint storage: sealed uncertainty drift')
        if entry['rows_sha256']!=hashlib.sha256(plan[m]['sealed_rows'].tobytes(order='C')).hexdigest():
            raise ValueError('joint storage: sealed row identity drift')


def write_joint_development(directory: str, request: dict) -> dict:
    """Write admitted exact native inputs to a NEW external private directory."""
    planner._keys(request,('schema','survey_request','development','sealed_manifest','originals'),'writer')
    planner._enum(request['schema'],('joint-survey-write-request-1',),'writer.schema')
    root=_external(directory)
    if root.exists(): raise FileExistsError('joint storage: destination exists')
    intake._ordinary(root.parent,directory=True)
    survey=request['survey_request'];planner._contract(survey)
    # Metadata before originals copying, hash, finite scan, snapshot or physics.
    intake._development_metadata(survey,request['development'])
    planner._metadata_budget({'survey_request':survey,'development':request['development'],'sealed_manifest':request['sealed_manifest']})
    originals=request['originals'];total_original=0
    if originals is not None:
        planner._keys(originals,('gravity','magnetic'),'originals')
        for m in ('gravity','magnetic'):
            planner._keys(originals[m],('raw','correction'),'originals.'+m)
            for key in ('raw','correction'):
                if type(originals[m][key]) is not bytes: raise TypeError('joint storage: exact original bytes')
                total_original+=len(originals[m][key])
            if len(originals[m]['raw'])!=survey[m]['source']['raw_bytes']:
                raise ValueError('joint storage: original byte count drift')
            if not 0<len(originals[m]['correction'])<=planner.MAX_METADATA_BYTES:
                raise ValueError('joint storage: correction byte cap')
    array_total=sum(a.nbytes for a in planner._arrays(survey)+planner._arrays(request['development']))
    if array_total+total_original+28*intake.MAX_HEADER_BYTES+planner.MAX_METADATA_BYTES>intake.MAX_DIRECTORY_BYTES:
        raise ValueError('joint storage: output directory exceeds256MiB')
    n=len(survey['prior']['density']['start'])
    native={'schema':'joint-survey-objective-request-1','survey_request':survey,'development':request['development'],
        'models':{'density_kg_m3':survey['prior']['density']['start'],
                  'susceptibility_si':survey['prior']['susceptibility']['start']},
        'direction_physical':np.zeros(2*n),'weights':{'beta_gravity':.0001,'beta_magnetic':.0001,'coupling':0.}}
    admitted,plan,_=objective._admit(native)
    _manifest(request['sealed_manifest'],plan)
    if originals is not None:
        for m in ('gravity','magnetic'):
            for key,source_key in (('raw','raw_sha256'),('correction','correction_sha256')):
                if hashlib.sha256(originals[m][key]).hexdigest()!=plan[m]['source'][source_key]:
                    raise ValueError('joint storage: original hash drift')
    encoded_survey=deepcopy(admitted['survey_request']);encoded_dev=deepcopy(admitted['development'])
    arrays={};descriptors={};headers={}
    for node,paths in ((encoded_survey,intake._SURVEY_PATHS),(encoded_dev,intake._DEVELOPMENT_PATHS)):
        for identifier,path in paths.items():
            value=_get(node,path);arrays[identifier]=value;_set(node,path,{'array':identifier})
            header=_npy_header(value);headers[identifier]=header
            digest=hashlib.sha256(header);digest.update(memoryview(value).cast('B'))
            descriptors[identifier]={'dtype':value.dtype.str,'shape':list(value.shape),'file_bytes':len(header)+value.nbytes,
                'file_sha256':digest.hexdigest(),'data_sha256':hashlib.sha256(memoryview(value).cast('B')).hexdigest()}
    encoded_survey['frame']['axes']=list(encoded_survey['frame']['axes'])
    for m in ('gravity','magnetic'): encoded_survey[m]['missing_reasons']=list(encoded_survey[m]['missing_reasons'])
    document={'schema':'joint-survey-intake-1','survey':encoded_survey,'development':encoded_dev,'arrays':descriptors,
        'sealed_manifest':deepcopy(request['sealed_manifest']),
        'raw_access':{m:{'availability':'provided' if originals is not None else 'provider_reference_only',
            'raw_present':originals is not None,'correction_present':originals is not None} for m in ('gravity','magnetic')}}
    content=json.dumps(document,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    if len(content)>planner.MAX_METADATA_BYTES: raise ValueError('joint storage: serialized metadata cap')
    if len(content)+sum(d['file_bytes'] for d in descriptors.values())+total_original>intake.MAX_DIRECTORY_BYTES:
        raise ValueError('joint storage: actual output directory cap')
    root.mkdir(mode=0o700)
    for identifier,value in arrays.items():
        with (root/(identifier+'.npy')).open('xb') as stream:
            stream.write(headers[identifier]);stream.write(memoryview(value).cast('B'))
    if originals is not None:
        for m in ('gravity','magnetic'):
            for key,suffix in (('raw','.raw'),('correction','.corrections.json')):
                with (root/(m+suffix)).open('xb') as stream: stream.write(originals[m][key])
    with (root/'request.json').open('xb') as stream: stream.write(content)
    result=intake.load_joint_development(str(root))
    if result['plan']['plan_sha256']!=plan['plan_sha256']: raise RuntimeError('joint storage: final identity drift')
    return result
