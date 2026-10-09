"""Fixed source-bound physical scientific child, never an HTTP-side solve.

Supervisor owns containment, cancellation, aggregate telemetry and publication.
This child preserves original input/request/output, installs no dependencies,
never overwrites an output and never declares host or full-method acceptance.
"""

import hashlib
from importlib.metadata import version
import os
from pathlib import Path
import platform
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
CORE_SHA = 'dc6d529bdaef766012d076a5786fefd8388f6e6ad310c6239aa91ca43da425fe'
ADAPTER_SHA = '77e855b63bf31bd292ef8302253a06e49db3e0a332f936e0a06b53b478e492fd'
TRANSFORM_SHA = '25ba24d4aaf442641d15924139e4ef1a131d7f6fe0dabab3eaa6549a5ba15312'
PARSER_SHA = '83d62675e47e9db97d3b93be2e1ccf2b268717c42aca32f167b8526b1f95bb6e'
DECODER_SHA = 'fc493a8ee4c5d204cf27436a9746364e72585499587dc75ced03db7aa3562fb2'
PINS = dict(boule='0.5.0', harmonica='0.7.0', numpy='2.2.6', scipy='1.15.2')
TRANSFORM_PINS = {**PINS, 'verde':'1.9.0', 'scikit-learn':'1.9.1', 'matplotlib':'3.10.8'}


def need(value):
    if not value:
        raise ValueError('physical_child_integrity')


def sha(body):
    return hashlib.sha256(body).hexdigest()


def source(path, expected):
    need(path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == expected)


def read(stage, name, cap):
    path = stage/name
    need(not path.is_symlink())
    flags=os.O_RDONLY|getattr(os,'O_CLOEXEC',0)|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
    descriptor=os.open(path,flags)
    with os.fdopen(descriptor,'rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= cap)
        body = stream.read(cap+1)
        after = os.fstat(stream.fileno())
        need(len(body) == before.st_size <= cap and
             (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) ==
             (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns))
        return body


def save(stage, name, body):
    # Uncertain exclusive output stays charged for the supervisor's fresh audit.
    with (stage/name).open('xb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    if os.name == 'posix':
        descriptor=os.open(stage,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def run(stage):
    need(sys.flags.isolated and sys.flags.dont_write_bytecode)
    need(stage.is_absolute() and stage.is_dir() and not stage.is_symlink())
    for parent in (stage,*stage.parents):
        need(not (parent/'.git').exists() and not parent.is_symlink() and
             not (hasattr(parent,'is_junction') and parent.is_junction()))
    need(platform.python_implementation() == 'CPython' and sys.version_info[:2] == (3,12))
    source(ROOT/'app/physical_contract.py',DECODER_SHA)
    source(ROOT/'data-pipeline/gravity_station_json.py',PARSER_SHA)
    source(ROOT/'data-pipeline/gravity_processing.py',CORE_SHA)
    sys.path.insert(0,str(ROOT))
    sys.path.insert(0,str(ROOT/'data-pipeline'))
    from app.physical_contract import canonical, decode_source, digest, fields, uuid
    request_bytes=read(stage,'request.json',34*1048576)
    request=decode_source([request_bytes],max_bytes=34*1048576,depth=24,nodes=500000)
    fields(request,'schema job_id owner_id project_id dataset_id dataset_sha256 root_dataset_id raw_asset_id raw_sha256 raw_bytes method_id parameters submitted_parameters_sha256 scientific_request scientific_request_sha256 parent_production module_manifest module_manifest_sha256 limits admission_receipt_sha256')
    need(request['schema']=='geophysics.physical-request/v2' and uuid(request['job_id'])==stage.name)
    for key in ('owner_id','project_id','dataset_id','root_dataset_id','raw_asset_id'):
        uuid(request[key])
    parent_bytes=read(stage,'input.json',16*1048576)
    need(sha(parent_bytes)==request['dataset_sha256'])
    parent=decode_source([parent_bytes],max_bytes=16*1048576,depth=32,nodes=2250000)
    fields(parent,'schema dataset_id version owner_id project_id raw_asset_id raw_sha256 raw_bytes parser_version root_dataset_id parent_dataset_id parent_dataset_sha256 kind modality payload_schema scientific_payload_sha256 payload source production structural_verdict')
    need(parent['schema']=='geophysics.physical-dataset/v2' and parent['dataset_id']==request['dataset_id'] and
         parent['parser_version']=='gravity-stations-json/v1')
    for key in ('owner_id','project_id','root_dataset_id','raw_asset_id','raw_sha256','raw_bytes'):
        need(parent[key]==request[key])
    need(digest(parent['payload'],scientific=True)==parent['scientific_payload_sha256'])
    if parent['kind']=='derived':
        prior=request['parent_production']
        fields(prior,'schema owner_id project_id root_dataset_id raw_asset_id raw_sha256 raw_bytes output_dataset_id output_dataset_version output_dataset_sha256 output_dataset_bytes job_id method_id state scientific_verdict input_dataset_id input_dataset_sha256 request_sha256 submitted_parameters_sha256 scientific_request_sha256 result_sha256 result_bytes module_manifest module_manifest_sha256 adapter_result_sha256 adapter_receipt adapter_receipt_sha256 core_result_sha256 submitted_config_sha256 normalized_config_sha256')
        need(all(v is not None for v in prior.values()) and prior['schema']=='geophysics.physical-parent-production/v1' and
             prior['method_id']=='gravity.station-corrections/v1' and prior['state']=='succeeded' and prior['scientific_verdict']=='passed')
        need((prior['output_dataset_id'],prior['output_dataset_version'],prior['output_dataset_sha256'],prior['output_dataset_bytes'])==
             (parent['dataset_id'],parent['version'],sha(parent_bytes),len(parent_bytes)))
        for key in ('owner_id','project_id','root_dataset_id','raw_asset_id','raw_sha256','raw_bytes'):
            need(prior[key]==parent[key])
        need(prior['adapter_result_sha256']==parent['scientific_payload_sha256'] and
             canonical(prior['adapter_receipt'],scientific=True)==canonical(parent['payload']['receipt'],scientific=True) and
             digest(prior['adapter_receipt'],scientific=True)==prior['adapter_receipt_sha256'])
        for key in ('job_id','method_id','request_sha256','adapter_result_sha256','module_manifest_sha256','scientific_verdict'):
            need(parent['production'][key]==prior[key])
        need(parent['production']['scientific_result_sha256']==prior['adapter_result_sha256'])
    method=request['method_id']
    need(method in ('gravity.station-corrections/v1','gravity.equivalent-source-transform/v1'))
    correction=method=='gravity.station-corrections/v1'
    packages=PINS if correction else TRANSFORM_PINS
    need({name:version(name) for name in packages}==packages)
    expected=dict(schema='geophysics.physical-modules/v1',parser_sha256=PARSER_SHA,
                  wrapper_sha256=sha(Path(__file__).read_bytes()),adapter_sha256=ADAPTER_SHA if correction else None,
                  core_sha256=CORE_SHA,transform_sha256=None if correction else TRANSFORM_SHA,
                  runtime_manifest=dict(python=platform.python_version(),python_implementation='CPython',packages=packages))
    need(canonical(request['module_manifest'])==canonical(expected) and
         digest(expected)==request['module_manifest_sha256'])
    science=request['scientific_request']
    need(len(canonical(science,scientific=True))<=16*1048576 and
         digest(science,scientific=True)==request['scientific_request_sha256'] and
         digest(request['parameters'])==request['submitted_parameters_sha256'])
    if correction:
        source(ROOT/'data-pipeline/gravity_station_adapter.py',ADAPTER_SHA)
        fields(science,'schema_version method dataset config input_dataset_sha256 submitted_config_sha256')
        need(science['schema_version']=='gravity-station-adapter-request-1' and science['method']==method)
        if parent['kind']=='root':
            need(parent['payload_schema']=='gravity-stations-1' and request['parent_production'] is None)
            selected=parent['payload']
        else:
            need(parent['kind']=='derived' and parent['payload_schema']=='gravity-station-adapter-result-1' and
                 type(request['parent_production']) is dict)
            selected=parent['payload']['correction_result']['dataset']
        need(canonical(science['dataset'],scientific=True)==canonical(selected,scientific=True) and
             canonical(science['config'],scientific=True)==canonical(request['parameters'],scientific=True))
        from gravity_station_adapter import run_station_corrections
        result=run_station_corrections(science)
        verdict='passed'
    else:
        source(ROOT/'data-pipeline/gravity_transforms.py',TRANSFORM_SHA)
        fields(science,'schema_version correction_result geometry config')
        fields(request['parameters'],'geometry config')
        need(science['schema_version']=='gravity-transform-request-1' and parent['kind']=='derived' and
             parent['payload_schema']=='gravity-station-adapter-result-1' and type(request['parent_production']) is dict)
        need(canonical(science['correction_result'],scientific=True)==canonical(parent['payload']['correction_result'],scientific=True))
        for key in ('geometry','config'):
            need(canonical(science[key],scientific=True)==canonical(request['parameters'][key],scientific=True))
        from gravity_transforms import transform_survey
        result=transform_survey(science)
        verdict='passed' if result['selection']['status']=='passed' else 'non_pass'
    body=canonical(result,scientific=True)
    need(0<len(body)<= (16 if correction else 64)*1048576)
    save(stage,'scientific.json',body)
    completion=dict(schema='geophysics.physical-child-completion/v1',job_id=request['job_id'],method_id=method,
                    scientific_request_sha256=request['scientific_request_sha256'],scientific_result_sha256=digest(result,scientific=True),
                    output_bytes=len(body),output_sha256=sha(body),scientific_verdict=verdict)
    marker=canonical(completion)
    need(len(marker)<=4096)
    save(stage,'complete.json',marker)


if __name__=='__main__':
    try:
        need(len(sys.argv)==2)
        run(Path(sys.argv[1]))
    except Exception:
        # Original logs remain in the supervisor; never disclose request values.
        print('{"code":"physical_child_failed","retryable":false}',file=sys.stderr)
        raise SystemExit(2) from None
