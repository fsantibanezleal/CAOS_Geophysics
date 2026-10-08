"""Actual adapter output with saved-edge fixtures, never host/resource approval."""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest

import gravity_processing as core
import gravity_station_adapter as adapter
from app.physical_contract import ContractError, byte_sha, canonical, digest
from app.physical_producer import PARENT_KEYS, verify_correction_producer
from app.physical_wire import make_root_envelope, scientific_digest
from tests.numerics.test_gravity_station_adapter import request as scientific_request, survey


@pytest.fixture
def packet():
    original = survey()
    original['metadata']['source_citation'] += ' \u00e1'
    original['stations'][0].update(original_value=980000, value_mgal=980000)
    scientific = scientific_request(original)
    return packet_from_science(original, scientific)


def packet_from_science(original, scientific):
    """Saved transport fixture; caller supplies real unchanged science input."""
    owner, project, raw, root, child, job_id = [str(uuid4()) for _ in range(6)]
    computed = adapter.run_station_corrections(scientific)
    receipt = computed['receipt']
    runtime = dict(python=receipt['python'], python_implementation='CPython', packages=receipt['engines'])
    # Transport registration is an explicit fixture, not fabricated OS evidence.
    manifest = dict(schema='geophysics.physical-modules/v1',
                    parser_sha256=sha256(b'fixture parser registration').hexdigest(),
                    wrapper_sha256=sha256(b'fixture transport registration').hexdigest(),
                    adapter_sha256=receipt['adapter_module_sha256'], core_sha256=adapter.CORE_SHA256,
                    transform_sha256=None, runtime_manifest=runtime)
    source = dict(provider='Authored station control', exact_url=None, doi=None, citation=None,
                  rights_decision='mirror', rights_statement='Authored test control', attribution='Control author')
    raw_body = canonical(original)
    input_body = make_root_envelope(original, dataset_id=root, owner_id=owner, project_id=project,
                                    raw_asset_id=raw, raw_sha256=byte_sha(raw_body), raw_bytes=len(raw_body), source=source)
    req = dict(schema='geophysics.physical-request/v2', job_id=job_id, owner_id=owner, project_id=project,
               dataset_id=root, dataset_sha256=byte_sha(input_body), root_dataset_id=root,
               raw_asset_id=raw, raw_sha256=byte_sha(raw_body), raw_bytes=len(raw_body), method_id=adapter.METHOD,
               parameters=scientific['config'], submitted_parameters_sha256=digest(scientific['config']),
               scientific_request=scientific, scientific_request_sha256=scientific_digest(scientific),
               parent_production=None, module_manifest=manifest, module_manifest_sha256=digest(manifest),
               limits=dict(cpu_ms=60000, wall_seconds=120, rss_bytes=768*1048576, scratch_bytes=256*1048576,
                           scientific_input_bytes=16777216, child_output_bytes=67108864, stdout_bytes=65536, stderr_bytes=65536),
               admission_receipt_sha256=sha256(b'fixture only, not a host receipt').hexdigest())
    inner = dict(job_id=job_id, method_id=adapter.METHOD, request_sha256=digest(req),
                 adapter_result_sha256=scientific_digest(computed), scientific_result_sha256=scientific_digest(computed),
                 module_manifest_sha256=digest(manifest), scientific_verdict='passed')
    envelope = dict(schema='geophysics.physical-dataset/v2', dataset_id=child, version=2, owner_id=owner,
                    project_id=project, raw_asset_id=raw, raw_sha256=req['raw_sha256'], raw_bytes=req['raw_bytes'],
                    parser_version='gravity-stations-json/v1', root_dataset_id=root, parent_dataset_id=root,
                    parent_dataset_sha256=byte_sha(input_body), kind='derived', modality='gravity_physical_station',
                    payload_schema='gravity-station-adapter-result-1', scientific_payload_sha256=scientific_digest(computed),
                    payload=computed, source=source, production=inner, structural_verdict='child_verified')
    child_body = canonical(envelope)
    # Literal fixture telemetry exercises bindings only; not claimed measured.
    measured = dict(wall_ms=20, cpu_ms=10, peak_rss_bytes=1048576, scratch_peak_bytes=4096,
                    child_output_bytes=len(canonical(computed)), environment=runtime,
                    environment_sha256=digest(runtime), admission_receipt_sha256=req['admission_receipt_sha256'])
    result = dict(schema='geophysics.physical-result/v2', job_id=job_id, owner_id=owner, project_id=project,
                  dataset_id=root, dataset_sha256=byte_sha(input_body), output_dataset_id=child,
                  output_dataset_sha256=byte_sha(child_body), raw_asset_id=raw, raw_sha256=req['raw_sha256'],
                  raw_bytes=req['raw_bytes'], method_id=adapter.METHOD, request_sha256=digest(req),
                  submitted_parameters_sha256=req['submitted_parameters_sha256'], scientific_request_sha256=req['scientific_request_sha256'],
                  scientific_result_sha256=scientific_digest(computed), module_manifest=manifest,
                  module_manifest_sha256=digest(manifest), scientific_verdict='passed', scientific_result=computed, receipt=measured)
    result_body = canonical(result)
    snapshot = dict(schema='geophysics.physical-parent-production/v1', owner_id=owner, project_id=project,
                    root_dataset_id=root, raw_asset_id=raw, raw_sha256=req['raw_sha256'], raw_bytes=req['raw_bytes'],
                    output_dataset_id=child, output_dataset_version=2, output_dataset_sha256=byte_sha(child_body),
                    output_dataset_bytes=len(child_body), job_id=job_id, method_id=adapter.METHOD, state='succeeded', scientific_verdict='passed',
                    input_dataset_id=root, input_dataset_sha256=byte_sha(input_body), request_sha256=digest(req),
                    submitted_parameters_sha256=req['submitted_parameters_sha256'], scientific_request_sha256=req['scientific_request_sha256'],
                    result_sha256=byte_sha(result_body), result_bytes=len(result_body), module_manifest=manifest,
                    module_manifest_sha256=digest(manifest), adapter_result_sha256=scientific_digest(computed), adapter_receipt=receipt,
                    adapter_receipt_sha256=scientific_digest(receipt), core_result_sha256=receipt['correction_result_sha256'],
                    submitted_config_sha256=receipt['submitted_config_sha256'], normalized_config_sha256=receipt['normalized_config_sha256'])
    relation = {k: snapshot[{'child_dataset_id':'output_dataset_id','parent_dataset_id':'input_dataset_id',
                            'parent_dataset_sha256':'input_dataset_sha256','scientific_result_sha256':'adapter_result_sha256'}.get(k,k)]
                for k in 'child_dataset_id job_id owner_id project_id root_dataset_id raw_asset_id parent_dataset_id parent_dataset_sha256 method_id request_sha256 submitted_parameters_sha256 scientific_request_sha256 scientific_result_sha256 module_manifest_sha256 result_sha256 result_bytes scientific_verdict adapter_result_sha256 adapter_receipt_sha256 core_result_sha256 submitted_config_sha256 normalized_config_sha256'.split()}
    relation['adapter_receipt_bytes'] = canonical(receipt)
    saved_job = dict(id=job_id, owner_id=owner, project_id=project, dataset_id=root, dataset_sha256=byte_sha(input_body),
                     method_id=adapter.METHOD, state='succeeded', request_sha256=digest(req), result_sha256=byte_sha(result_body),
                     result_bytes=len(result_body), wall_ms=20, physical_cpu_ms=10, peak_rss_bytes=1048576, scratch_bytes=4096,
                     result_key=f'derived/{owner}/{project}/results/{job_id}.json', finished_at='2026-10-08T01:00:00Z', error_code=None, error_message=None)
    return dict(snapshot=snapshot, input_bytes=input_body, child_bytes=child_body, request_bytes=canonical(req),
                result_bytes=result_body, approved_manifest=manifest, job=saved_job, production=relation)


def verify(packet):
    return verify_correction_producer(**packet)


def test_actual_adapter_saved_edge_complete_without_solver(packet, monkeypatch):
    original = deepcopy(packet)
    monkeypatch.setattr(core, 'process_survey', lambda *args: pytest.fail('Parent replayed science'))
    monkeypatch.setattr(adapter, 'run_station_corrections', lambda *args: pytest.fail('Parent invoked adapter'))
    monkeypatch.setattr(Path, 'read_bytes', lambda *args: pytest.fail('Pure verifier opened source'))
    assert len(packet['snapshot']) == 30 and set(packet['snapshot']) == set(PARENT_KEYS.split())
    assert verify(packet) is packet['snapshot']
    assert packet == original


@pytest.mark.parametrize('field', PARENT_KEYS.split())
def test_every_snapshot_key_required(packet, field):
    del packet['snapshot'][field]
    with pytest.raises(ContractError):
        verify(packet)


@pytest.mark.parametrize('field', PARENT_KEYS.split())
def test_every_snapshot_field_nonnull(packet, field):
    packet['snapshot'][field] = None
    with pytest.raises(ContractError):
        verify(packet)


@pytest.mark.parametrize('field', ['input_bytes', 'child_bytes', 'request_bytes', 'result_bytes'])
def test_original_saved_bytes_eof_barrier(packet, field):
    packet[field] += b'\n{}'
    with pytest.raises(ContractError):
        verify(packet)


@pytest.mark.parametrize('field', ['owner_id','project_id','output_dataset_id','input_dataset_id','root_dataset_id',
                                 'raw_asset_id','job_id','result_sha256','adapter_result_sha256','core_result_sha256',
                                 'request_sha256','submitted_config_sha256','normalized_config_sha256'])
def test_well_typed_foreign_identity_refused(packet, field):
    packet['snapshot'][field] = str(uuid4()) if field.endswith('_id') else '0'*64
    with pytest.raises(ContractError):
        verify(packet)


@pytest.mark.parametrize('field', ['wall_ms','physical_cpu_ms','peak_rss_bytes','scratch_bytes','result_key','finished_at','error_code','error_message'])
def test_saved_sql_job_cannot_disagree(packet, field):
    packet['job'][field] = None if field == 'finished_at' else 'mismatched' if field in ('result_key','error_code','error_message') else 1
    with pytest.raises(ContractError):
        verify(packet)


def test_actual_source_and_runtime_manifest_needs_registration(packet):
    packet['approved_manifest'] = deepcopy(packet['approved_manifest'])
    packet['approved_manifest']['adapter_sha256'] = '0'*64
    with pytest.raises(ContractError):
        verify(packet)


def test_saved_adapter_receipt_cannot_be_inner_or_app_hash(packet):
    packet['production']['adapter_receipt_bytes'] = canonical(packet['snapshot']['adapter_receipt']['acceptance'])
    with pytest.raises(ContractError):
        verify(packet)
