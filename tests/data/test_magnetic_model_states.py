"""Genuine retained native null trace and explicit adversarial replay controls."""
import copy
import hashlib
import json
import os
from pathlib import Path

import pytest

import magnetic_model_states as states
from magnetic_calibration import descriptor
from magnetic_result_bundle import read_bundle
from magnetic_survey_json import InputError, canonical


@pytest.fixture(scope='module')
def actual():
    root = Path(os.environ['GEOPHYSICS_MAGNETIC_STATE_CONTROL'])
    audit = root/'scratch/optimizer-audit.jsonl'
    imported = read_bundle(root/'generation')
    raw = audit.read_bytes()
    records = [json.loads(line) for line in raw.splitlines()]
    assert hashlib.sha256(raw).hexdigest() == '1b80e987438af768ec877a750b8452ddd8418af9faad84a90a507741a69e46da'
    assert imported['generation_sha256'] == '6d41247de60ebc5a48fc1416bfb594378803d3a83d33aa134e69e5aa8de328e1'
    return audit, imported, records, hashlib.sha256(raw).hexdigest()


def call(actual, path=None, result=None, inventory=None):
    audit, imported, records, _ = actual
    return states.from_closed_audit(path or audit, result or imported['result'],
        imported['request'], inventory or records[0]['source_inventory_sha256'])


def test_retained_actual_selected_final_null_state(actual, tmp_path):
    audit, imported, records, original_sha = actual
    saved = call(actual)
    assert saved['candidate'] == 'b07-l2' and saved['fold'] == -1
    assert saved['q_models']['shape'] == saved['chi_si']['shape'] == [1, 7]
    assert saved['q_models']['data'] == saved['chi_si']['data'] == [0.]*7
    assert saved['audit_sha256'] == original_sha
    indices = saved['history_indices']['data']
    assert len(indices) == 1 and imported['result']['history'][indices[0]]['fold'] == -1
    selected = [r for r in records if r['candidate'] == saved['candidate'] and r['fold'] is None]
    assert len(selected) == 1 and selected[0]['actual_result']['iterations'] == 0
    assert selected[0]['actual_result']['runtime_epoch'].endswith('-6')
    assert imported['result']['identity']['engine_epoch'].endswith('-6')
    assert hashlib.sha256(audit.read_bytes()).hexdigest() == original_sha
    (tmp_path/'actual-selected-final-states.json').write_bytes(canonical(saved))


@pytest.mark.parametrize('attack', ['inventory', 'order', 'claims', 'unknown', 'selected',
    'fold', 'status', 'epoch', 'optimizer', 'iterations', 'terminal', 'disposed',
    'model', 'trace_count', 'phi', 'missing', 'partial'])
def test_selected_trace_continuity_and_history_binding(actual, tmp_path, attack):
    audit, imported, records, old_sha = actual
    records = copy.deepcopy(records)
    final = records[-1]
    if attack == 'inventory': final['source_inventory_sha256'] = '0'*64
    elif attack == 'order': final['solve'] += 1
    elif attack == 'claims': final['online_admitted'] = True
    elif attack == 'unknown': final['fabricated_state'] = True
    elif attack == 'selected': final['candidate'] = 'b06-l2'
    elif attack == 'fold': final['fold'] = 0
    elif attack == 'status': final['actual_result']['status'] = 'failed'
    elif attack == 'epoch': final['actual_result']['runtime_epoch'] += '-invented'
    elif attack == 'optimizer': final['actual_result']['source_binding']['optimizer'] = '0'*64
    elif attack == 'iterations': final['actual_result']['iterations'] = True
    elif attack == 'terminal': final['actual_result']['terminal_audits'][-1]['check']['passed'] = False
    elif attack == 'disposed': final['actual_result']['terminal_audits'][-1]['check']['disposed'] = False
    elif attack == 'model': final['actual_result']['trace']['models_q'][0][0] = 1.
    elif attack == 'trace_count': final['actual_result']['trace']['models_q'].append([0.]*7)
    elif attack == 'phi': final['actual_result']['trace']['phi_engine'][0] = 1.
    elif attack == 'missing': records.pop()
    raw = b''.join(canonical(record)+b'\n' for record in records)
    if attack == 'partial': raw = raw[:-1]
    changed = tmp_path/'changed-audit.jsonl'
    changed.write_bytes(raw)
    with pytest.raises(InputError):
        call(actual, path=changed)
    assert hashlib.sha256(audit.read_bytes()).hexdigest() == old_sha
    assert imported['result']['schema'] == 'magnetic-survey-result-1'


@pytest.mark.parametrize('attack', ['audit_bytes', 'line_bytes', 'state_count', 'index',
    'physical', 'model_hash', 'scale', 'quota_before_array'])
def test_audit_and_state_capacity_refusals(actual, tmp_path, monkeypatch, attack):
    if attack in ('audit_bytes', 'line_bytes'):
        changed = tmp_path/'over-cap.jsonl'
        with changed.open('wb') as stream:
            if attack == 'audit_bytes': stream.truncate(states.MAX_AUDIT+1)
            else: stream.write(b' '*(states.MAX_LINE+1)+b'\n')
        with pytest.raises(InputError): call(actual, path=changed)
        return
    saved = copy.deepcopy(call(actual))
    if attack == 'state_count': saved['q_models']['shape'][0] = 202
    elif attack == 'index': saved['history_indices']['data'][0] = 0
    elif attack == 'physical':
        import numpy as np
        saved['chi_si'] = descriptor(np.array([[.01]+[0.]*6]))
    elif attack == 'model_hash': saved['q_models']['sha256'] = '0'*64
    elif attack == 'scale': saved['physical_scale'] = .1
    else:
        monkeypatch.setattr(states, 'MAX_STATE_BYTES', 1)
        import numpy as np
        monkeypatch.setattr(np, 'asarray', lambda *a, **k: pytest.fail('Capacity refusal allocated array'))
    with pytest.raises(InputError):
        states.validate(saved, actual[1]['result'], actual[1]['request'])


def test_failed_result_and_foreign_inventory_do_not_publish(actual, tmp_path):
    with pytest.raises(InputError): call(actual, inventory='0'*64)
    # A result shape with an invented status is refused by the original reader,
    # not silently repaired to a successful replay by the state extractor.
    changed = dict(actual[1]['result'], status='failed')
    with pytest.raises(InputError): call(actual, result=changed)
    assert list(tmp_path.iterdir()) == []


def test_actual_v2_numeric_zip_and_owner_projection_keep_v1_closed(actual, tmp_path):
    from magnetic_result_bundle import validate_result, write_bundle
    from magnetic_result_export import export_zip, import_zip, inspect_zip_bytes
    from magnetic_result_view import project_result
    imported = actual[1]
    saved = call(actual)
    legacy = imported['result']
    raw_legacy = canonical(legacy)
    extended = dict(legacy, schema='magnetic-survey-result-2', model_states=saved)
    assert validate_result(extended, imported['request']) == extended
    with pytest.raises(InputError):
        validate_result(dict(legacy, model_states=saved), imported['request'])
    with pytest.raises(InputError):
        validate_result(dict(extended, unknown='No sibling exemption'), imported['request'])
    target = tmp_path/'new-generation'
    generation = write_bundle(target, extended, imported['request'])
    assert generation != imported['generation_sha256']
    assert read_bundle(target)['result'] == extended
    archive = tmp_path/'states.zip'
    receipt = export_zip(target, archive)
    manifest = inspect_zip_bytes(archive.read_bytes())
    assert manifest['result']['schema'] == 'magnetic-survey-result-2'
    assert any(m['unit'] == 'chi_over_0.01' for m in manifest['members'])
    assert len(manifest['members']) <= 64
    replay = import_zip(archive, tmp_path/'reimported')
    assert replay['result'] == extended and replay['generation_sha256'] == generation
    binding = dict(job_id='00000000-0000-4000-8000-000000000001',
        dataset_id='00000000-0000-4000-8000-000000000002',
        source_id=imported['request']['source']['id'], generation_sha256=generation,
        configuration_sha256=extended['identity']['configuration_sha256'],
        original_sha256=imported['request']['source']['original_sha256'])
    view = project_result(target, binding)
    assert view['schema'] == 'magnetic-owner-result-view-2'
    assert view['model_states'] == saved and not any(view['claims'].values())
    assert canonical(legacy) == raw_legacy
    control = dict(schema='magnetic-model-state-browser-control-1',
        source_generation_sha256=imported['generation_sha256'], source_epoch=legacy['identity']['engine_epoch'],
        extended_generation_sha256=generation, saved_model_count=1, nonzero_fit=False,
        host_qualified=False, accepted_method=False, view=view, zip_receipt=receipt,
        zip_path=str(archive), extraction_only=True)
    (tmp_path/'state-browser-control.json').write_bytes(canonical(control))
    (tmp_path/'state-view.json').write_bytes(canonical(view))


@pytest.mark.parametrize('attack', ['extra_file', 'removed_file', 'rehash_model', 'wrong_unit'])
def test_v2_declared_inventory_and_exact_states_refuse(actual, tmp_path, attack):
    from magnetic_result_bundle import write_bundle
    from magnetic_survey_json import digest
    imported = actual[1]
    extended = dict(imported['result'], schema='magnetic-survey-result-2', model_states=call(actual))
    target = tmp_path/'new-generation'
    write_bundle(target, extended, imported['request'])
    if attack == 'extra_file':
        (target/'unknown.npy').write_bytes(b'Unknown sibling remains refusal')
    elif attack == 'removed_file':
        (target/'a00.npy').unlink()
    else:
        path = target/'manifest.json'
        manifest = json.loads(path.read_bytes())
        if attack == 'rehash_model':
            manifest['result']['model_states']['candidate'] = 'b06-l2'
        else:
            for member in manifest['members']:
                if member['unit'] == 'chi_over_0.01': member['unit'] = 'SI'
        manifest['generation_sha256'] = digest({k:v for k,v in manifest.items() if k != 'generation_sha256'})
        path.write_bytes(canonical(manifest))
    with pytest.raises(InputError): read_bundle(target)
