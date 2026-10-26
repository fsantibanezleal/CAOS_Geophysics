"""Actual local tools on supplied files; no saved-case replay as calibration."""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

import run_magnetic_survey as cli
from magnetic_survey_json import canonical, digest

spec = importlib.util.spec_from_file_location('cli_control', Path(__file__).parents[1]/'numerics'/'test_magnetic_full_calibration.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


def inputs(tmp_path):
    doc, binding = control.small_request()
    original = b'Owner supplied authored local acquisition original, not provider field.'
    doc['source']['original_sha256'] = hashlib.sha256(original).hexdigest()
    doc['source']['original_bytes'] = len(original)
    doc['processing']['nodes'][0]['input_sha256'] = doc['source']['original_sha256']
    (tmp_path/'original.bin').write_bytes(original)
    (tmp_path/'request.json').write_bytes(canonical(doc))
    inventory = cli.source_inventory()
    receipt = dict(schema='magnetic-local-binding-1', scope='local_candidate_only',
        review_reference='Automated numerical control ONLY, not an accepted field/native registry',
        sources=inventory, source_inventory_sha256=digest(inventory), runtime_epoch=binding.runtime_epoch, policy=binding.policy)
    (tmp_path/'receipt.json').write_bytes(canonical(receipt))
    return doc


def run(*args):
    process = subprocess.run([sys.executable, '-B', str(Path(cli.__file__)), *map(str, args)],
        capture_output=True, text=True, timeout=120., check=False)
    assert len(process.stdout.splitlines()) == 1, process.stdout[:400]
    return process.returncode, json.loads(process.stdout)


def test_actual_file_cli_calibrate_import_and_reused_evaluation(tmp_path):
    inputs(tmp_path)
    common = ('--request', tmp_path/'request.json', '--original', tmp_path/'original.bin',
              '--data-root', tmp_path, '--temp-root', tmp_path)
    code, geometry = run('validate', *common, '--output', tmp_path/'geometry.json')
    assert code == 0 and geometry['original_bytes_verified'] is True
    assert geometry['field_source_verified'] is False
    code, unadmitted = run('calibrate', *common, '--output', tmp_path/'refused', '--binding-receipt', tmp_path/'receipt.json')
    assert code == 3 and unadmitted['code'] == 'dependency' and not (tmp_path/'refused').exists()
    code, result = run('calibrate', *common, '--output', tmp_path/'generation', '--binding-receipt',
        tmp_path/'receipt.json', '--allow-candidate-core', '--wall-seconds', '120')
    assert code == 0, result
    assert result['execution_scope'] == 'local_candidate_only' and not any(result['claims'].values())
    freeze = json.loads((tmp_path/'generation.frozen.json').read_bytes())
    assert freeze['state'] == 'frozen_before_outer_evaluation' and freeze['candidate'] == result['selected']
    previous = (tmp_path/'generation'/'manifest.json').read_bytes()
    code, refused = run('calibrate', *common, '--output', tmp_path/'generation', '--binding-receipt',
        tmp_path/'receipt.json', '--allow-candidate-core')
    assert code == 5 and refused['code'] == 'durability'
    assert (tmp_path/'generation'/'manifest.json').read_bytes() == previous
    code, imported = run('import', '--bundle', tmp_path/'generation', '--temp-root', tmp_path)
    assert code == 0 and imported['generation_sha256'] == result['generation_sha256']
    code, evaluated = run('evaluate', '--bundle', tmp_path/'generation', '--temp-root', tmp_path)
    assert code == 0 and evaluated['evaluation'] == 'reused_sealed_evaluation'
    assert evaluated['outer']['phi_d'] == 0.
    assert evaluated['identity'] == result['identity']
    code, failed = run('calibrate', *common, '--output', tmp_path/'timed_out', '--binding-receipt',
        tmp_path/'receipt.json', '--allow-candidate-core', '--wall-seconds', '0.000000001')
    assert code == 3 and failed['status'] == 'failed'
    ledger = json.loads((tmp_path/'timed_out'/'failure.json').read_bytes())
    assert ledger['status'] == 'failed' and ledger['model'] is None and ledger['selected'] is None
    assert not (tmp_path/'timed_out'/'manifest.json').exists()


def test_cli_raw_identity_rejection_and_external_root_mandatory(tmp_path, monkeypatch):
    inputs(tmp_path)
    monkeypatch.delenv('GEOPHYSICS_LOCAL_DATA_ROOT', raising=False)
    code, result = run('validate', '--request', tmp_path/'request.json', '--original', tmp_path/'original.bin',
        '--output', tmp_path/'rejected.json', '--temp-root', tmp_path)
    assert code == 5 and result['code'] == 'durability' and not (tmp_path/'rejected.json').exists()
    (tmp_path/'original.bin').write_bytes(b'wrong')
    code, result = run('validate', '--request', tmp_path/'request.json', '--original', tmp_path/'original.bin',
        '--output', tmp_path/'rejected.json', '--data-root', tmp_path, '--temp-root', tmp_path)
    assert code == 2 and result['code'] == 'bytes' and not (tmp_path/'rejected.json').exists()


def test_operator_receipt_cannot_hide_transitive_certificate_validator(tmp_path):
    inputs(tmp_path)
    receipt = json.loads((tmp_path/'receipt.json').read_bytes())
    receipt['sources'].pop('gravity_l2_precision')
    receipt['source_inventory_sha256'] = digest(receipt['sources'])
    (tmp_path/'receipt.json').write_bytes(canonical(receipt))
    with pytest.raises(ValueError, match='inventory mismatch'):
        cli.reviewed_binding(tmp_path/'receipt.json', True)


def test_existing_output_gate_precedes_request_original_and_source_io(tmp_path):
    output = tmp_path/'old.json'
    output.write_bytes(b'Prior external generation')
    code, result = run('validate', '--request', tmp_path/'missing_request', '--original', tmp_path/'missing_original',
        '--output', output, '--data-root', tmp_path, '--temp-root', tmp_path)
    assert code == 5 and result['code'] == 'durability' and 'before fitting' in result['message']
    assert output.read_bytes() == b'Prior external generation'
