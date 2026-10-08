"""Actual public planner/full frozen geometry, no kernel or fit authority."""
import ast
import copy
import hashlib
import importlib.util
import inspect
import os
from pathlib import Path

import pytest

import magnetic_original_adapter as adapter
import magnetic_original_optimizer as public
import physical_original_optimizer as core
from magnetic_survey_json import InputError, canonical, digest
from run_magnetic_survey import reviewed_binding, source_inventory


ROOT = Path(__file__).parents[2]
spec = importlib.util.spec_from_file_location('m04_public_workflow_gate',
    ROOT/'scripts/check_magnetic_original_workflow_allocation.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_exact_public_plan_is_delegated_without_local_arithmetic(monkeypatch):
    expected = public.allocation_plan(864, 648, 528, False, 120112128, 3)
    calls = []
    def observed(*args):
        calls.append(args)
        return expected
    monkeypatch.setattr(public, 'allocation_plan', observed)
    result = adapter.allocation(864, 648, 528, False, 120112128, 3)
    assert calls == [(864, 648, 528, False, 120112128, 3)]
    assert result is expected
    assert result['minimum_phase_bytes'] == 723407520
    assert result['admitted_bytes'] == 805306368
    # The consumer contains no private phase/helper invocation or native/local
    # allocation formula. The public planner's own internals remain its owner's.
    tree = ast.parse(inspect.getsource(adapter.allocation))
    attributes = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)]
    assert not any(n.func.attr.startswith('_') for n in attributes)
    assert not any(n.func.attr == 'allocation' for n in attributes)


@pytest.mark.parametrize('components,fit', [(3, 432), (3, 648), (1, 144), (1, 216)])
def test_actual_fold_final_scalar_vector_public_plans_are_unchanged(components, fit):
    arguments = (864, fit, 528, False, 120112128, components)
    expected = public.allocation_plan(*arguments)
    actual = adapter.allocation(*arguments)
    assert actual == expected
    assert actual['source_binding'] == adapter.source_binding()
    assert actual['admitted_bytes'] == 805306368
    assert actual['minimum_phase_bytes'] < actual['admitted_bytes']


@pytest.mark.parametrize('attack', ['unknown', 'schema', 'source', 'epoch', 'policy',
    'cap', 'count', 'count_type', 'phase_member', 'phase_epoch', 'native_member',
    'native_type', 'phase_type', 'arithmetic_member', 'payload', 'minimum', 'terminal'])
def test_changed_public_contract_refuses_before_fit(monkeypatch, attack):
    result = copy.deepcopy(public.allocation_plan(864, 648, 528, False, 120112128, 3))
    if attack == 'unknown': result['disjoint'] = True
    elif attack == 'schema': result['schema'] = 'magnetic-original-allocation-1'
    elif attack == 'source': result['source_binding']['physical_original_quadratic'] = '0'*64
    elif attack == 'epoch': result['epoch'] = 'physical-gncg-original-noise-reduced-joseph-candidate-9'
    elif attack == 'policy': result['policy'] = 'unknown'
    elif attack == 'cap': result['admitted_bytes'] += 1
    elif attack == 'count': result['fit_components'] = 432
    elif attack == 'count_type': result['parameters'] = 528.
    elif attack == 'phase_member': result['owned_source_phases']['disjoint'] = True
    elif attack == 'phase_epoch': result['owned_source_phases']['epoch'] = 'unknown'
    elif attack == 'native_member': result['native_phases']['caller_credit'] = 1
    elif attack == 'native_type': result['native_phases']['native'] = True
    elif attack == 'phase_type': result['owned_source_phases']['maximum'] = True
    elif attack == 'arithmetic_member': result['source_arithmetic_upper']['caller_credit'] = 1
    elif attack == 'payload': result['source_payload_upper_bytes'] = 8388609
    elif attack == 'minimum': result['minimum_phase_bytes'] = 805306369
    else: result['actual_terminal_phase_gate'] = 'caller-approved'
    monkeypatch.setattr(public, 'allocation_plan', lambda *args: result)
    monkeypatch.setattr(public, 'solve_magnetic_original', lambda *a, **k: pytest.fail('Refusal reached fit'))
    with pytest.raises(ValueError, match='closed public allocation'):
        adapter.allocation(864, 648, 528, False, 120112128, 3)


@pytest.mark.parametrize('arguments', [
    (True, 648, 528, False, 120112128, 3), (863, 648, 528, False, 120112128, 3),
    (864, 647, 528, False, 120112128, 3), (864, 648, 528, 1, 120112128, 3),
    (864, 648, 528, False, 120112128, 2), (864, 648, 528, False, 805306369, 3),
    (864, 648, 528, True, 120112128, 3), (864, 648, 4096, False, 120112128, 3)])
def test_actual_public_literal_and_resource_refusals(arguments):
    with pytest.raises(ValueError):
        adapter.allocation(*arguments)


@pytest.mark.parametrize('fault', ['missing_public', 'old_epoch', 'source_constant', 'cap'])
def test_unsupported_or_drifted_source_refuses_before_public_plan(monkeypatch, fault):
    if fault == 'missing_public': monkeypatch.delattr(public, 'allocation_plan')
    else:
        monkeypatch.setattr(public, 'allocation_plan', lambda *a: pytest.fail('Refusal reached public planner'))
        if fault == 'old_epoch': monkeypatch.setattr(core, 'LINEAR_EPOCH', 'physical-gncg-original-noise-reduced-joseph-candidate-9')
        elif fault == 'source_constant': monkeypatch.setattr(core, 'SOURCE_SHA256', '0'*64)
        else: monkeypatch.setattr(adapter, 'LIMIT', 805306369)
    with pytest.raises(ValueError):
        adapter.allocation(864, 648, 528, False, 120112128, 3)


def test_old_epoch_receipt_is_not_upgraded(tmp_path):
    sources = source_inventory(original=True)
    receipt = dict(schema='magnetic-local-binding-1', scope='local_candidate_only',
        review_reference='Historical refusal preserved, never authority for changed source',
        sources=sources, source_inventory_sha256=digest(sources),
        runtime_epoch='physical-gncg-original-noise-reduced-joseph-candidate-9', policy=core.POLICY)
    path = tmp_path/'old-receipt.json'
    raw = canonical(receipt)
    path.write_bytes(raw)
    with pytest.raises(InputError):
        reviewed_binding(path, True)
    assert path.read_bytes() == raw


def test_original_frozen_request_all_phases_without_kernel_or_child(tmp_path, monkeypatch):
    from magnetic_survey_json import _Lexer, MAX_BYTES
    import magnetic_inverse
    import subprocess
    # Exact retained authored source9 A bytes are supplied externally. This
    # prospective request changes ONLY optimizer source authority, not data.
    path = Path(os.environ['GEOPHYSICS_MAGNETIC_ORIGINAL_REQUEST'])
    raw = path.read_bytes()
    old_sha = hashlib.sha256(raw).hexdigest()
    doc = _Lexer(raw, max_bytes=MAX_BYTES, max_tokens=1000000, defer=False).document()
    old_policy = doc['policy']['optimizer_binding']
    assert old_policy['epoch'] == 'physical-gncg-original-noise-reduced-joseph-candidate-9'
    doc['policy']['optimizer_binding'] = dict(accepted_source=core.SOURCE_SHA256,
        accepted_export='physical_original_optimizer.solve_bounded_linear', epoch=core.LINEAR_EPOCH)
    prospective = canonical(doc)
    monkeypatch.setattr(magnetic_inverse, 'build_operator', lambda *a, **k: pytest.fail('No sensitivity kernel'))
    monkeypatch.setattr(public, 'solve_magnetic_original', lambda *a, **k: pytest.fail('No numerical fit'))
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('No native child'))
    report = gate.workflow_allocation(prospective)
    assert report['status'] == 'within_original_envelope'
    assert report['source_components'] == 864 and report['active_cells'] == 528
    assert report['inner_fit_rows'] == [144, 144, 144]
    assert report['final_refit_rows'] == 216
    assert [p['fit_components'] for p in report['phases']] == [432, 648]
    assert report['phases'][-1]['plan']['minimum_phase_bytes'] == 723407520
    assert all(p['plan']['source_binding'] == adapter.source_binding() for p in report['phases'])
    assert not any(report[k] for k in ('original_bytes_verified', 'fit_started',
        'native_process_started', 'full_method_accepted', 'field_source_verified'))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == old_sha
    (tmp_path/'prospective-request.json').write_bytes(prospective)
    (tmp_path/'workflow-allocation.json').write_bytes(canonical(report))
    (tmp_path/'retained-source.json').write_bytes(canonical(dict(old_request_sha256=old_sha,
        prospective_request_sha256=hashlib.sha256(prospective).hexdigest(),
        only_changed_member='policy.optimizer_binding', old_epoch=old_policy['epoch'],
        allocation_only=True, source_inventory=source_inventory(original=True))))
