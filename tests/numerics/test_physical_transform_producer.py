"""Original full-volume transforms and saved transport bindings, no OS claim."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import platform
from uuid import uuid4

import pytest

from app.physical_contract import ContractError, TRANSFORM, canonical, digest
from app.physical_transform_producer import verify_transform_producer
from app.physical_wire import scientific_digest
from gravity_transform_controls import control_request
from gravity_transforms import TRANSFORM_PINS, transform_survey
from tests.numerics.test_gravity_station_adapter import request as correction_request
from tests.numerics.test_physical_producer import packet_from_science


def transform_packet(non_pass=False, *, with_parent=False):
    science, _ = control_request(0)
    original = deepcopy(science['correction_result']['dataset'])
    original.update(state='observed_absolute', history=[])
    for row in original['stations']:
        row['value_mgal'] = row['original_value']
    saved = packet_from_science(original, correction_request(original, science['correction_result']['processing']['config']))
    if non_pass:
        science['config']['max_transfer_sigma_mgal'] = 1e-6
    assert canonical(science['correction_result'], scientific=True) == canonical(
        json.loads(saved['child_bytes'])['payload']['correction_result'], scientific=True)
    computed = transform_survey(science)
    req = json.loads(saved['request_bytes'])
    runtime = dict(python=platform.python_version(), python_implementation='CPython', packages=TRANSFORM_PINS)
    manifest = dict(req['module_manifest'], adapter_sha256=None,
        transform_sha256=sha256(Path(__import__('gravity_transforms').__file__).read_bytes()).hexdigest(), runtime_manifest=runtime)
    req.update(job_id=str(uuid4()), dataset_id=saved['snapshot']['output_dataset_id'],
        dataset_sha256=sha256(saved['child_bytes']).hexdigest(), method_id=TRANSFORM,
        parent_production=saved['snapshot'], parameters={k:deepcopy(science[k]) for k in ('geometry','config')},
        scientific_request=science, scientific_request_sha256=scientific_digest(science),
        module_manifest=manifest, module_manifest_sha256=digest(manifest))
    req['submitted_parameters_sha256'] = digest(req['parameters'])
    req['limits'].update(cpu_ms=120000, wall_seconds=180, scratch_bytes=512*1048576)
    verdict = 'non_pass' if non_pass else 'passed'
    inner = dict(job_id=req['job_id'], method_id=TRANSFORM, request_sha256=digest(req),
        adapter_result_sha256=None, scientific_result_sha256=scientific_digest(computed),
        module_manifest_sha256=digest(manifest), scientific_verdict=verdict)
    envelope = json.loads(saved['child_bytes'])
    envelope.update(dataset_id=str(uuid4()), version=3, parent_dataset_id=req['dataset_id'],
        parent_dataset_sha256=req['dataset_sha256'], modality='gravity_equivalent_source_transform',
        payload_schema='gravity-transform-result-1', payload=computed,
        scientific_payload_sha256=scientific_digest(computed), production=inner)
    measured = dict(wall_ms=20, cpu_ms=10, peak_rss_bytes=1048576, scratch_peak_bytes=4096,
        child_output_bytes=len(canonical(computed, scientific=True)), environment=runtime,
        environment_sha256=digest(runtime), admission_receipt_sha256=req['admission_receipt_sha256'])
    result = json.loads(saved['result_bytes'])
    result.update({k:req[k] for k in ('job_id','dataset_id','dataset_sha256','method_id',
        'submitted_parameters_sha256','scientific_request_sha256','module_manifest','module_manifest_sha256')})
    result.update(output_dataset_id=envelope['dataset_id'], output_dataset_sha256=sha256(canonical(envelope)).hexdigest(),
        request_sha256=digest(req), scientific_result_sha256=scientific_digest(computed),
        scientific_verdict=verdict, scientific_result=computed, receipt=measured)
    job = dict(saved['job'], id=req['job_id'], dataset_id=req['dataset_id'], dataset_sha256=req['dataset_sha256'],
        method_id=TRANSFORM, request_sha256=digest(req), result_sha256=sha256(canonical(result)).hexdigest(),
        result_bytes=len(canonical(result)), result_key=f"derived/{req['owner_id']}/{req['project_id']}/results/{req['job_id']}.json")
    production = dict(saved['production'], child_dataset_id=envelope['dataset_id'], job_id=req['job_id'],
        parent_dataset_id=req['dataset_id'], parent_dataset_sha256=req['dataset_sha256'], method_id=TRANSFORM,
        request_sha256=digest(req), submitted_parameters_sha256=req['submitted_parameters_sha256'],
        scientific_request_sha256=req['scientific_request_sha256'], scientific_result_sha256=scientific_digest(computed),
        module_manifest_sha256=digest(manifest), result_sha256=job['result_sha256'], result_bytes=job['result_bytes'],
        scientific_verdict=verdict)
    for key in ('adapter_result_sha256','adapter_receipt_sha256','core_result_sha256','submitted_config_sha256',
                'normalized_config_sha256','adapter_receipt_bytes'):
        production[key] = None
    packet = dict(parent_snapshot=saved['snapshot'], input_bytes=saved['child_bytes'], child_bytes=canonical(envelope),
        request_bytes=canonical(req), result_bytes=canonical(result), approved_manifest=manifest, job=job, production=production)
    return (saved, packet) if with_parent else packet


@pytest.fixture(scope='module', params=[False, True], ids=['original-pass','original-height-non-pass'])
def saved_transform(request):
    return transform_packet(request.param)


def test_original_transform_saved_output_no_solver_or_source_read(saved_transform, monkeypatch):
    packet = deepcopy(saved_transform)
    monkeypatch.setattr(__import__('gravity_transforms'), 'transform_survey', lambda *a:pytest.fail('Parent solved science'))
    monkeypatch.setattr(Path, 'read_bytes', lambda *a:pytest.fail('Parent read scientific source'))
    child = verify_transform_producer(**packet)
    assert child == json.loads(packet['child_bytes'])
    assert len(child['payload']['stations']['station_ids']) == 196
    assert len(child['payload']['selection']['candidates']) == 9
    assert child['production']['scientific_verdict'] == ('passed' if child['payload']['selection']['status']=='passed' else 'non_pass')


@pytest.mark.parametrize('damage', ['parent','null_adapter','manifest','resource','output_length','native_number','grid_null',
    'grid_shape','coverage','partition','precision','verdict','source','receipt','terminal_transform_parent',
    'split_hash','selected_candidate','model_interpretation','uncertainty','correction_identity','seed_type'])
def test_rehashed_internal_conflicts_refuse(saved_transform, damage):
    packet = deepcopy(saved_transform)
    child,req,result = [json.loads(packet[k]) for k in ('child_bytes','request_bytes','result_bytes')]
    payload = child['payload']
    if damage=='parent':
        req['parent_production']['core_result_sha256'] = '0'*64
    elif damage=='null_adapter':
        packet['production']['adapter_result_sha256'] = '0'*64
    elif damage=='manifest':
        packet['approved_manifest']['transform_sha256'] = '0'*64
    elif damage=='resource':
        result['receipt']['environment']['python'] = '3.12.11'
        result['receipt']['environment_sha256'] = digest(result['receipt']['environment'])
    elif damage=='output_length':
        result['receipt']['child_output_bytes'] += 1
    elif damage=='native_number':
        req['scientific_request']['config']['seed'] = float(req['scientific_request']['config']['seed'])
    elif damage=='grid_null':
        grid = payload['grids'][0]
        i = grid['covered'].index(False)
        grid['predicted_mgal'][i] = 0
    elif damage=='grid_shape':
        payload['grids'][0]['shape'][0] += 1
    elif damage=='coverage':
        payload['stations']['prediction_covered'][0] = 1
    elif damage=='partition':
        payload['split']['partition'][0] = 'unknown'
    elif damage=='precision':
        payload['grids'][0]['height_precision_passed'] = not payload['grids'][0]['height_precision_passed']
    elif damage=='verdict':
        child['production']['scientific_verdict'] = 'non_pass' if child['production']['scientific_verdict']=='passed' else 'passed'
        result['scientific_verdict'] = packet['production']['scientific_verdict'] = child['production']['scientific_verdict']
    elif damage=='source':
        child['source']['attribution'] = 'rehashed wrong source'
    elif damage=='receipt':
        payload['provenance']['full_method_accepted'] = True
    elif damage=='terminal_transform_parent':
        parent = json.loads(packet['input_bytes'])
        parent['payload_schema'] = 'gravity-transform-result-1'
        packet['input_bytes'] = canonical(parent)
    elif damage=='split_hash':
        payload['split']['sha256'] = '0'*64
    elif damage=='selected_candidate':
        payload['selection']['depth_m'] = 999
    elif damage=='model_interpretation':
        payload['model']['interpretation'] = 'Density and geological confidence'
    elif damage=='uncertainty':
        payload['uncertainty']['kind'] = 'full_uncertainty'
    elif damage=='correction_identity':
        payload['provenance']['correction_identity']['recorded_runtime_origin_verified'] = True
    elif damage=='seed_type':
        req['parameters']['config']['seed'] = float(req['parameters']['config']['seed'])
        req['scientific_request']['config']['seed'] = req['parameters']['config']['seed']
        payload['config']['seed'] = req['parameters']['config']['seed']
    # Bind every changed OUTER byte identity. These are internal contradictions,
    # not tests that pass merely because a stale file hash was noticed.
    child['scientific_payload_sha256'] = scientific_digest(payload)
    child['production']['scientific_result_sha256'] = scientific_digest(payload)
    result['scientific_result'] = deepcopy(payload)
    result['scientific_result_sha256'] = packet['production']['scientific_result_sha256'] = scientific_digest(payload)
    req['submitted_parameters_sha256'] = digest(req['parameters'])
    req['scientific_request_sha256'] = scientific_digest(req['scientific_request'])
    payload['provenance']['request_sha256'] = req['scientific_request_sha256']
    child['scientific_payload_sha256'] = child['production']['scientific_result_sha256'] = scientific_digest(payload)
    result['scientific_result'] = deepcopy(payload)
    result['scientific_result_sha256'] = packet['production']['scientific_result_sha256'] = scientific_digest(payload)
    child['production']['request_sha256'] = result['request_sha256'] = packet['job']['request_sha256'] = packet['production']['request_sha256'] = digest(req)
    for key in ('submitted_parameters_sha256','scientific_request_sha256'):
        result[key] = packet['production'][key] = req[key]
    packet['child_bytes'] = canonical(child)
    result['output_dataset_sha256'] = sha256(packet['child_bytes']).hexdigest()
    packet['request_bytes'] = canonical(req)
    packet['result_bytes'] = canonical(result)
    packet['job'].update(result_sha256=sha256(packet['result_bytes']).hexdigest(), result_bytes=len(packet['result_bytes']))
    packet['production'].update(result_sha256=packet['job']['result_sha256'], result_bytes=packet['job']['result_bytes'])
    with pytest.raises(ContractError):
        verify_transform_producer(**packet)
