"""Actual fixed scientific child; not production containment or queue proof."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
import sys
from uuid import uuid4

import pytest

from app.physical_contract import canonical, digest
from tests.numerics.test_physical_producer import packet as packet
from scripts.process_physical_job import PINS, PARSER_SHA, CORE_SHA, ADAPTER_SHA


ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'scripts/process_physical_job.py'


def child_case(packet, tmp_path):
    req=json.loads(packet['request_bytes'])
    stage=tmp_path/req['job_id']
    stage.mkdir()
    manifest=dict(schema='geophysics.physical-modules/v1',parser_sha256=PARSER_SHA,
                  wrapper_sha256=sha256(SCRIPT.read_bytes()).hexdigest(),adapter_sha256=ADAPTER_SHA,
                  core_sha256=CORE_SHA,transform_sha256=None,
                  runtime_manifest=dict(python=platform.python_version(),python_implementation='CPython',packages=PINS))
    req.update(module_manifest=manifest,module_manifest_sha256=digest(manifest))
    (stage/'input.json').write_bytes(packet['input_bytes'])
    (stage/'request.json').write_bytes(canonical(req))
    return stage,req


def execute(stage):
    return subprocess.run([sys.executable,'-I','-B',str(SCRIPT),str(stage)],
                          cwd=stage,capture_output=True,timeout=120)


def test_actual_fixed_child_preserves_exact_adapter_result(packet, tmp_path):
    stage,req=child_case(packet,tmp_path)
    before={name:(stage/name).read_bytes() for name in ('input.json','request.json')}
    actual=execute(stage)
    assert actual.returncode==0 and actual.stdout==actual.stderr==b''
    output=(stage/'scientific.json').read_bytes()
    expected=json.loads(packet['child_bytes'])['payload']
    assert output==canonical(expected,scientific=True)
    complete=json.loads((stage/'complete.json').read_bytes())
    assert complete==dict(schema='geophysics.physical-child-completion/v1',job_id=req['job_id'],method_id=req['method_id'],
                          scientific_request_sha256=req['scientific_request_sha256'],scientific_result_sha256=digest(expected,scientific=True),
                          output_bytes=len(output),output_sha256=sha256(output).hexdigest(),scientific_verdict='passed')
    assert {name:(stage/name).read_bytes() for name in before}==before
    assert {p.name for p in stage.iterdir()}=={'input.json','request.json','scientific.json','complete.json'}
    assert json.loads(output)['receipt']['acceptance']==dict(host_approved=False,full_method_accepted=False,field_source_verified=False)


@pytest.mark.parametrize('damage',['foreign_parent','stale_input','wrapper_source','core_source','runtime','method','private_contract','duplicate','trailing','existing_output'])
def test_actual_fixed_child_negative_no_success_marker(packet,tmp_path,damage):
    stage,req=child_case(packet,tmp_path)
    if damage=='foreign_parent':
        req['owner_id']=str(uuid4())
    elif damage=='stale_input':
        req['dataset_sha256']='0'*64
    elif damage in ('wrapper_source','core_source'):
        req['module_manifest']['wrapper_sha256' if damage=='wrapper_source' else 'core_sha256']='0'*64
        req['module_manifest_sha256']=digest(req['module_manifest'])
    elif damage=='runtime':
        req['module_manifest']['runtime_manifest']['packages']['boule']='wrong'
        req['module_manifest_sha256']=digest(req['module_manifest'])
    elif damage=='method':
        req['method_id']='gravity.station-outlier-flags/v1'
    elif damage=='private_contract':
        req['scientific_request']['dataset']=deepcopy(req['scientific_request']['dataset'])
        req['scientific_request']['dataset']['metadata']['height_datum']='PRIVATE_SOURCE_D:/not-a-real-path'
        req['scientific_request']['input_dataset_sha256']=digest(req['scientific_request']['dataset'],scientific=True)
        req['scientific_request_sha256']=digest(req['scientific_request'],scientific=True)
    elif damage=='existing_output':
        (stage/'scientific.json').write_bytes(b'preserved prior bytes')
    body=canonical(req)
    if damage=='duplicate':
        body=body[:-1]+b',"method_id":"gravity.station-corrections/v1"}'
    elif damage=='trailing':
        body+=b' {}'
    (stage/'request.json').write_bytes(body)
    original=(stage/'input.json').read_bytes()
    actual=execute(stage)
    assert actual.returncode==2 and actual.stdout==b''
    assert actual.stderr==b'{"code":"physical_child_failed","retryable":false}\r\n' or actual.stderr==b'{"code":"physical_child_failed","retryable":false}\n'
    assert not (stage/'complete.json').exists()
    assert (stage/'input.json').read_bytes()==original
    assert (stage/'request.json').read_bytes()==body
    if damage=='existing_output':
        assert (stage/'scientific.json').read_bytes()==b'preserved prior bytes'
    else:
        assert not (stage/'scientific.json').exists()
