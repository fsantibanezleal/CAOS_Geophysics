"""Real supplied-file conditioned CLI and complete optimizer receipt, not field."""
import importlib.util
import json
from pathlib import Path

import pytest

import run_magnetic_survey as cli
from magnetic_survey_json import canonical, digest
from magnetic_conditioned_adapter import binding_for_sources

spec = importlib.util.spec_from_file_location('conditioned_cli_control', Path(__file__).with_name('test_magnetic_local_cli.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@pytest.mark.parametrize('quantity,feasible', [('secondary_enu_nT', False), ('exact_total_anomaly_nT', False),
                                              ('secondary_enu_nT', True)])
def test_full_supplied_file_sequence_under_distinct_public_epoch(tmp_path, quantity, feasible):
    doc = control.inputs(tmp_path)
    nonlinear = quantity == 'exact_total_anomaly_nT'
    if nonlinear:
        from magnetic_survey_support import descriptor, rehash
        doc['observations']['quantity'] = doc['processing']['quantity'] = quantity
        doc['observations']['values'] = descriptor('float64', [288, 1], [0.]*288)
        doc['processing']['background_relation'] = 'total_norm_minus_declared_uniform_F'
        doc['noise']['values'] = descriptor('float64', [288, 1], [.5]*288)
        rehash(doc, 'observations/values')
    sources = cli.source_inventory(conditioned=True, feasible=feasible)
    binding = binding_for_sources(sources, digest(sources), nonlinear=nonlinear, feasible=feasible)
    doc['policy']['optimizer_binding'] = dict(accepted_source=binding.optimizer_source_sha256,
        accepted_export=binding.accepted_export, epoch=binding.runtime_epoch)
    (tmp_path/'request.json').write_bytes(canonical(doc))
    receipt = dict(schema='magnetic-local-binding-1', scope='local_candidate_only',
        review_reference='Authored full-row supplied control, not scientific acceptance',
        sources=sources, source_inventory_sha256=digest(sources), runtime_epoch=binding.runtime_epoch, policy=binding.policy)
    (tmp_path/'conditioned-receipt.json').write_bytes(canonical(receipt))
    scratch = tmp_path/'scratch'
    scratch.mkdir()
    code, result = control.run('calibrate', '--request', tmp_path/'request.json', '--original', tmp_path/'original.bin',
        '--output', tmp_path/'conditioned-generation', '--data-root', tmp_path, '--temp-root', scratch,
        '--binding-receipt', tmp_path/'conditioned-receipt.json', '--allow-candidate-core', '--wall-seconds', '120')
    assert code == 0, result
    assert result['identity']['engine_epoch'] == binding.runtime_epoch
    assert result['status'] == 'complete' and not any(result['claims'].values())
    records = [json.loads(line) for line in (scratch/'optimizer-audit.jsonl').read_bytes().splitlines()]
    assert len(records) >= 49 and len(records) == len({r['solve'] for r in records})
    assert all(r['source_inventory_sha256'] == digest(sources) for r in records)
    assert all(r['actual_result']['runtime_epoch'] == binding.runtime_epoch for r in records)
    assert all(r['actual_result']['terminal_audits'][-1]['check']['passed'] for r in records)
    code, imported = control.run('import', '--bundle', tmp_path/'conditioned-generation', '--temp-root', scratch)
    assert code == 0 and imported['generation_sha256'] == result['generation_sha256']
    code, evaluated = control.run('evaluate', '--bundle', tmp_path/'conditioned-generation', '--temp-root', scratch)
    assert code == 0 and evaluated['evaluation'] == 'reused_sealed_evaluation'
