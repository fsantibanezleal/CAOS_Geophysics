"""Actual supplied288row/null7cell tools; NOT nonzero528 matrix acceptance."""
import importlib.util
import json
from pathlib import Path

import pytest

import run_magnetic_survey as cli
from magnetic_reduced_adapter import binding_for_sources
from magnetic_survey_json import canonical, digest, InputError

spec = importlib.util.spec_from_file_location('reduced_cli_original_control',
    Path(__file__).with_name('test_magnetic_conditioned_cli.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@pytest.mark.parametrize('quantity', ['secondary_enu_nT', 'linear_tmi_nT'])
def test_original_supplied_calibration_evaluation_import_and_numeric_export(tmp_path, quantity):
    doc = control.control.inputs(tmp_path)
    if quantity == 'linear_tmi_nT':
        from magnetic_survey_support import descriptor, rehash
        doc['observations']['quantity'] = doc['processing']['quantity'] = quantity
        doc['processing']['background_relation'] = 'projection_of_secondary_declared'
        doc['observations']['values'] = descriptor('float64', [288, 1], [0.]*288)
        doc['noise']['values'] = descriptor('float64', [288, 1], [.5]*288)
        rehash(doc, 'observations/values')
    sources = cli.source_inventory(reduced=True)
    assert 'physical_reduced_optimizer' in sources and 'magnetic_reduced_adapter' in sources
    binding = binding_for_sources(sources, digest(sources))
    doc['policy']['optimizer_binding'] = dict(accepted_source=binding.optimizer_source_sha256,
        accepted_export=binding.accepted_export, epoch=binding.runtime_epoch)
    (tmp_path/'request.json').write_bytes(canonical(doc))
    receipt = dict(schema='magnetic-local-binding-1', scope='local_candidate_only',
        review_reference='Actual null7cell tool control, not field/host/full528 acceptance',
        sources=sources, source_inventory_sha256=digest(sources), runtime_epoch=binding.runtime_epoch, policy=binding.policy)
    (tmp_path/'reduced-receipt.json').write_bytes(canonical(receipt))
    scratch = tmp_path/'scratch'
    scratch.mkdir()
    code, result = control.control.run('calibrate', '--request', tmp_path/'request.json',
        '--original', tmp_path/'original.bin', '--output', tmp_path/'generation',
        '--data-root', tmp_path, '--temp-root', scratch, '--binding-receipt', tmp_path/'reduced-receipt.json',
        '--allow-candidate-core', '--wall-seconds', '120')
    assert code == 0, result
    assert result['status'] == 'complete' and result['identity']['engine_epoch'] == binding.runtime_epoch
    assert not any(result['claims'].values())
    audits = [json.loads(line) for line in (scratch/'optimizer-audit.jsonl').read_bytes().splitlines()]
    assert len(audits) >= 49
    assert all(a['actual_result']['runtime_epoch'] == binding.runtime_epoch for a in audits)
    assert all(a['actual_result']['terminal_audits'][-1]['check']['passed'] for a in audits)
    code, imported = control.control.run('import', '--bundle', tmp_path/'generation', '--temp-root', scratch)
    assert code == 0 and imported['generation_sha256'] == result['generation_sha256']
    code, evaluated = control.control.run('evaluate', '--bundle', tmp_path/'generation', '--temp-root', scratch)
    assert code == 0 and evaluated['evaluation'] == 'reused_sealed_evaluation'
    from magnetic_result_export import export_zip, import_zip
    export_zip(tmp_path/'generation', tmp_path/'numeric.zip')
    import_zip(tmp_path/'numeric.zip', tmp_path/'reimported')
    from magnetic_result_bundle import read_bundle
    assert read_bundle(tmp_path/'reimported')['generation_sha256'] == imported['generation_sha256']


def test_exactnorm_cannot_inherit_reduced_linear_before_kernel(tmp_path):
    sources = cli.source_inventory(reduced=True)
    binding = binding_for_sources(sources, digest(sources))
    receipt = dict(schema='magnetic-local-binding-1', scope='local_candidate_only', review_reference='negative control',
        sources=sources, source_inventory_sha256=digest(sources), runtime_epoch=binding.runtime_epoch, policy=binding.policy)
    (tmp_path/'receipt.json').write_bytes(canonical(receipt))
    with pytest.raises(InputError, match='LINEAR'):
        cli.reviewed_binding(tmp_path/'receipt.json', True, 'exact_total_anomaly_nT')


def test_no_combined_contact_reduced_epoch():
    with pytest.raises(ValueError, match='[Dd]istinct'):
        cli.source_inventory(reduced=True, feasible=True)
