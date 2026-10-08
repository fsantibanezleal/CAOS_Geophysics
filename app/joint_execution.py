"""Closed fixed-child controls. Installation configuration is not upload input."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import stat
import time
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ('calibration_io','compiled','evaluation','files','instrument','intake',
            'model_export','objective','optimizer','plan','resources','serialization','structure','workflow')
SOURCE_FILES = ('app/__init__.py','app/joint_contract.py','app/joint_execution.py','app/joint_worker.py','scripts/joint_processing_child.py',
    'docs/design/features/m02-prism-operator/runtime-pins.json',
    'data-pipeline/gravity_forward.py','data-pipeline/magnetic_forward.py',
    'data-pipeline/physical_nonlinear_optimizer.py',
    *(f'data-pipeline/joint_survey_{name}.py' for name in PIPELINE))
CAP = 256 * 1024**2


def require(value, code):
    if not value: raise ValueError(code)


def fields(value, keys):
    require(type(value) is dict and set(value)==set(keys),'joint_closed_fields')


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf8')


def digest(raw): return hashlib.sha256(raw).hexdigest()


def sha(value):
    require(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value),'joint_digest')
    return value


def identity(value):
    require(type(value) is str and str(UUID(value))==value,'joint_uuid')
    return value


def ordinary(path, *, directory=False, external=False):
    path=Path(path)
    require(path.is_absolute(),'joint_absolute_path')
    if external:
        temporary=[Path('/tmp'),Path('/var/tmp'),Path('/dev/shm')]
        if os.name=='nt':
            require(os.environ.get('SYSTEMROOT') and os.environ.get('LOCALAPPDATA'),'joint_installation_windows_roots')
            temporary=[Path(os.environ['SYSTEMROOT'])/'Temp',Path(os.environ['LOCALAPPDATA'])/'Temp']
        require(not any(path==root or path.is_relative_to(root) for root in temporary),'joint_system_temp_forbidden')
    for parent in (path,*path.parents):
        info=parent.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT,
                'joint_reparse_path')
        if parent==path:
            require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),'joint_ordinary_path')
        else: require(stat.S_ISDIR(info.st_mode),'joint_parent_directory')
        if external: require(not (parent/'.git').exists(),'joint_external_path')
    return path


def read_json(path, cap=65536):
    path=ordinary(path)
    require(path.stat().st_size<=cap,'joint_metadata_cap')
    raw=path.read_bytes();require(0<len(raw)<=cap,'joint_metadata_cap')
    def pairs(values):
        result={}
        for key,value in values:
            require(key not in result,'joint_duplicate_key');result[key]=value
        return result
    def invalid(_): raise ValueError('joint_nonfinite_json')
    return json.loads(raw.decode('utf8'),object_pairs_hook=pairs,parse_constant=invalid),raw


def source_inventory():
    return {name:digest(ordinary(ROOT/name).read_bytes()) for name in SOURCE_FILES}


def validate_context(value):
    fields(value,('schema','source_root','python','python_sha256','site_root','source_hashes'))
    require(value['schema']=='geophysics.joint-fixed-context/v1','joint_context_schema')
    require(ordinary(value['source_root'],directory=True)==ROOT,'joint_selected_source_root')
    python=ordinary(value['python']);site=ordinary(value['site_root'],directory=True)
    require(site==python.parent.parent/'Lib'/'site-packages','joint_selected_site_tree')
    require(digest(python.read_bytes())==sha(value['python_sha256']),'joint_interpreter_changed')
    fields(value['source_hashes'],SOURCE_FILES)
    require(value['source_hashes']==source_inventory(),'joint_product_source_changed')
    pins,_=read_json(ROOT/'docs/design/features/m02-prism-operator/runtime-pins.json')
    for name,expected in pins['targeted_source_sha256'].items():
        require(digest(ordinary(site/name).read_bytes())==expected,'joint_targeted_vendor_changed')
    return python,site


def validate_control(value, context, *, now=None):
    fields(value,('schema','job_id','owner_id','project_id','dataset_id','dataset_sha256',
        'context_path','context_sha256','data_root','stage','scratch','deadline','limits','members'))
    require(value['schema']=='geophysics.joint-fixed-control/v1','joint_control_schema')
    for key in ('job_id','owner_id','project_id','dataset_id'): identity(value[key])
    sha(value['dataset_sha256']);sha(value['context_sha256'])
    data=ordinary(value['data_root'],directory=True,external=True)
    stage=ordinary(value['stage'],directory=True,external=True)
    scratch=ordinary(value['scratch'],directory=True,external=True)
    require(stage.is_relative_to(data) and stage!=data and stage.name==value['job_id'],'joint_stage_binding')
    require(not (scratch==stage or scratch.is_relative_to(stage) or stage.is_relative_to(scratch)),'joint_scratch_overlap')
    require(not data.is_relative_to(ROOT) and not ROOT.is_relative_to(data),'joint_data_source_overlap')
    require(not scratch.is_relative_to(ROOT) and not ROOT.is_relative_to(scratch),'joint_scratch_source_overlap')
    fields(value['limits'],('wall_seconds','memory_bytes','scratch_bytes'))
    for key,maximum in (('wall_seconds',600),('memory_bytes',2*1024**3),('scratch_bytes',CAP)):
        number=value['limits'][key]
        require(type(number) is int and 0<number<=maximum,'joint_original_lower_limits')
    now=time.monotonic() if now is None else now
    require(type(value['deadline']) is float and math.isfinite(value['deadline']) and
        0<value['deadline']-now<=value['limits']['wall_seconds'],'joint_same_job_deadline')
    installed,raw=read_json(ordinary(value['context_path'],external=True))
    require(installed==context and digest(raw)==value['context_sha256'],'joint_selected_context_changed')
    fields(value['members'],('development','sealed'))
    # Keep stdlib-only bootstrap; grammar is checked against the immutable source
    # manifests below and the API's admitted dependency map, never caller paths.
    count=0;total=0
    from app import joint_contract as native
    for role,members in value['members'].items():
        require(type(members) is dict and members,'joint_input_inventory')
        for name,binding in members.items():
            require(type(name) is str and name not in ('.','..') and '/' not in name and '\\' not in name,
                    'joint_member_basename')
            fields(binding,('bytes','sha256'))
            require(type(binding['bytes']) is int and 0<binding['bytes']<=CAP,'joint_input_bytes')
            sha(binding['sha256']);count+=1;total+=binding['bytes']
    require(count<=40 and total<=CAP,'joint_whole_input_cap')
    for role,members in value['members'].items():
        directory=ordinary(stage/'inputs'/role,directory=True,external=True)
        require({p.name for p in directory.iterdir()}==set(members),'joint_input_inventory')
        main='request.json' if role=='development' else 'sealed.json'
        require(main in members,'joint_input_manifest_required')
        metadata=ordinary(directory/main,external=True)
        require(metadata.stat().st_size<=native.MAX_JSON,'joint_input_manifest_cap')
        manifest,expected=native.manifest(metadata.read_bytes(),role)
        require(set(expected)==set(members),'joint_input_manifest_inventory')
        for name,binding in members.items():
            path=ordinary(directory/name,external=True)
            require(path.stat().st_size==binding['bytes'],'joint_input_size_changed')
            with path.open('rb') as stream:
                hashed=hashlib.file_digest(stream,'sha256').hexdigest()
            require(hashed==binding['sha256'],'joint_input_digest_changed')
    return data,stage,scratch


def write_json(path, value):
    raw=canonical(value);require(len(raw)<=65536,'joint_metadata_cap')
    with Path(path).open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


def loaded_inventory(site):
    """Actual imported source/binary bytes; NOT transitive or host acceptance."""
    import sys
    result={}
    for name,module in tuple(sys.modules.items()):
        filename=getattr(module,'__file__',None)
        if not filename: continue
        path=Path(filename).resolve()
        if path.is_relative_to(site):
            relative=path.relative_to(site).as_posix()
            result[relative]=digest(ordinary(path).read_bytes())
        elif path.is_relative_to(ROOT) and path.suffix in ('.py','.pyd'):
            require(path.relative_to(ROOT).as_posix() in SOURCE_FILES,'joint_unbound_product_module')
    return result
