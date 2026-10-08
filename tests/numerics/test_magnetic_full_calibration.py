"""Full nested fitting on separate small mesh, not the frozen S2 truth gates."""

import copy
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]/'data'))
from magnetic_survey_support import request, descriptor, encode, rehash
import magnetic_calibration as calibration
from magnetic_inverse import build_operator
from magnetic_optimizer_adapter import certificate_source
from magnetic_survey_json import InputError
import physical_optimizer as core
import magnetic_result_bundle as bundle


def small_request():
    doc = request()
    mesh = doc['geometry']['mesh']
    for key, data in (('origin_m', [-140., -180., -260.]), ('widths_x_m', [40., 70.]),
                      ('widths_y_m', [30., 50., 90.]), ('widths_z_m', [60., 110.])):
        mesh[key] = descriptor('float64', [len(data)], data)
    mesh['active'] = descriptor('bool', [12], [i in (0, 1, 2, 3, 6, 7, 11) for i in range(12)])
    for name in ('start_si', 'reference_si', 'lower_si', 'upper_si'):
        doc['prior'][name] = descriptor('float64', [7], [.1 if name == 'upper_si' else 0.]*7)
    binding = core.OptimizerBinding('physical_optimizer.solve_bounded_physical', core.SOURCE_SHA256,
        hashlib.sha256(Path(certificate_source()).read_bytes()).hexdigest(), 'a'*64, core.RUNTIME_EPOCH, core.POLICY)
    doc['policy']['optimizer_binding'] = dict(accepted_source=binding.optimizer_source_sha256,
        accepted_export=binding.accepted_export, epoch=binding.runtime_epoch)
    return doc, binding


@pytest.fixture(scope='module')
def fitted():
    doc, binding = small_request()
    return doc, calibration.calibrate(encode(doc), binding=binding, source_inventory_sha256='a'*64,
                                    deadline=monotonic()+120.)


def test_actual_complete_null_candidate_inventory_and_diagnostics(fitted):
    doc, result = fitted
    assert result['status'] == 'complete'
    assert len(result['candidates']) == 16 and all(c['status'] == 'complete' for c in result['candidates'])
    assert result['selected'] == 'b07-l2'
    assert all(c['score'] == 0. for c in result['candidates'])
    np.testing.assert_array_equal(result['model']['chi_si']['data'], np.zeros(7))
    assert result['metrics']['outer']['n_rows'] == 72
    assert result['diagnostics']['resolution_kind'] == 'local_fixed_objective'
    assert result['diagnostics']['resolution_arrays']['matrix']['shape'] == [7, 7]
    assert not any(result['claims'].values())
    bundle.validate_result(result, doc)


def test_full_fitting_outer_value_counterfactual_and_access_trap(fitted, monkeypatch):
    doc, original = fitted
    other = copy.deepcopy(doc)
    outer = original['partition']['outer_rows']['data']
    for i in outer:
        other['observations']['values']['data'][3*i:3*i+3] = [17., -23., 5.]
    rehash(other, 'observations/values')
    from magnetic_likelihood import SealedLikelihood
    read = SealedLikelihood.read
    events = []
    def trap(self, rows, *, role, fold=None):
        if role == 'outer':
            assert self.frozen() is not None
        if role in ('fit', 'validation', 'refit'):
            assert not set(rows)&set(outer)
        events.append(role)
        return read(self, rows, role=role, fold=fold)
    monkeypatch.setattr(SealedLikelihood, 'read', trap)
    _, binding = small_request()
    result = calibration.calibrate(encode(other), binding=binding, source_inventory_sha256='a'*64,
                                   deadline=monotonic()+120.)
    assert events.count('outer') == 1 and 'fit' not in events[events.index('outer'):]
    assert result['model'] == original['model'] and result['candidates'] == original['candidates']
    assert result['selected'] == original['selected'] and result['history'] == original['history']
    assert result['identity']['configuration_sha256'] == original['identity']['configuration_sha256']
    assert result['identity']['observations_sha256'] != original['identity']['observations_sha256']
    assert result['metrics']['outer']['rms_nT'] > 0.
    bundle.validate_result(result, other)


def test_fitted_bundle_actual_roundtrip_and_hash_corruption(fitted, tmp_path):
    doc, result = fitted
    root = tmp_path/'fitted'
    generation = bundle.write_bundle(root, result, doc)
    imported = bundle.read_bundle(root)
    assert imported['generation_sha256'] == generation and imported['result'] == result
    assert imported['request'] == doc
    with pytest.raises(InputError, match='Fresh'):
        bundle.write_bundle(root, result, doc)
    array = next(root.glob('*.npy'))
    raw = array.read_bytes()
    with array.open('r+b') as stream:
        stream.seek(len(raw)-1)
        stream.write(bytes([raw[-1]^1]))
    with pytest.raises(InputError, match='hash'):
        bundle.read_bundle(root)


def test_loaded_dependency_gate_before_kernel_and_no_exact_fallback(monkeypatch):
    doc, binding = small_request()
    import magnetic_calibration
    monkeypatch.setattr(magnetic_calibration, 'build_operator', lambda *a, **k: pytest.fail('kernel built before gate'))
    doc['policy']['optimizer_binding']['accepted_source'] = 'd'*64
    with pytest.raises(InputError, match='binding'):
        calibration.calibrate(encode(doc), binding=binding, source_inventory_sha256='a'*64, deadline=monotonic()+120.)
    assert callable(build_operator)


def test_whole_calibration_timeout_retains_failed_original_inventory():
    doc, binding = small_request()
    result = calibration.calibrate(encode(doc), binding=binding, source_inventory_sha256='a'*64,
                                   deadline=monotonic()-1.)
    assert result['status'] == 'failed' and result['selected'] is None and result['model'] is None
    assert 'wall/CPU cap' in result['diagnostics']['reason']
    assert len(result['inventory']['row_ids']) == 288 and len(result['candidates']) == 16
    assert all(candidate['score'] is None for candidate in result['candidates'])
    assert result['candidates'][0]['folds'][0]['reason'] == 'resource'
    assert all(fold['reason'] == 'not_run' for candidate in result['candidates'][1:] for fold in candidate['folds'])
    assert not any(result['claims'].values())


def test_closed_failure_ledger_readback_never_success_bundle(tmp_path):
    doc, binding = small_request()
    result = calibration.calibrate(encode(doc), binding=binding, source_inventory_sha256='a'*64,
                                   deadline=monotonic()-1.)
    root = tmp_path/'failed'
    identity = bundle.write_failure(root, result, doc)
    assert hashlib.sha256((root/'failure.json').read_bytes()).hexdigest() == identity
    assert json.loads((root/'failure.json').read_bytes()) == result
    assert not (root/'manifest.json').exists()
    with pytest.raises(InputError, match='complete fitted'):
        bundle.write_bundle(tmp_path/'not_success', result, doc)
    with pytest.raises(InputError, match='Fresh'):
        bundle.write_failure(root, result, doc)
    malformed = copy.deepcopy(result)
    malformed['selected'] = 'b00-l2'
    with pytest.raises(InputError, match='fallback'):
        bundle.write_failure(tmp_path/'bad', malformed, doc)
    assert not (tmp_path/'bad').exists()


def test_nonzero_nested_supplied_data_offgrid_generation_and_failed_sparse_retention(tmp_path):
    doc, binding = small_request()
    location = Path(__file__).parents[1]/'fixtures'/'magnetic_survey'/'local_nonzero_control.py'
    import importlib.util
    spec = importlib.util.spec_from_file_location('offgrid_local_control', location)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    original, evaluator = generator.populate(doc)
    assert hashlib.sha256(original).hexdigest() == doc['source']['original_sha256']
    assert evaluator['scope'] == 'separate_authored_tiny_evaluator_only'
    assert 'bounds_m' not in doc and 'truth' not in doc
    freeze = tmp_path/'model.frozen.json'
    result = calibration.calibrate(encode(doc), binding=binding, source_inventory_sha256='a'*64,
                                   deadline=monotonic()+300., freeze_receipt=freeze)
    assert result['status'] == 'complete', result['diagnostics']['reason']
    assert np.any(np.array(result['model']['chi_si']['data']) > 0.)
    assert len(result['candidates']) == 16 and 0 < len(result['history']) <= 4096
    selected = next(candidate for candidate in result['candidates'] if candidate['id'] == result['selected'])
    assert selected['status'] == 'complete'
    for candidate in result['candidates']:
        if any(fold['status'] == 'failed' for fold in candidate['folds']):
            assert candidate['status'] == 'failed' and candidate['score'] is None
            assert all(fold['reason'] is not None for fold in candidate['folds'] if fold['status'] == 'failed')
    assert result['metrics']['outer']['normalized_rms'] <= 2.
    assert not any(result['claims'].values())
    stored = json.loads(freeze.read_bytes())
    assert stored['model_sha256'] == result['model']['sha256'] and stored['candidate'] == result['selected']
    identity = bundle.write_bundle(tmp_path/'nonzero', result, doc)
    assert bundle.read_bundle(tmp_path/'nonzero')['generation_sha256'] == identity


@pytest.mark.parametrize('attack', ['traversal', 'dtype', 'shape_bomb', 'unit', 'extra', 'duplicate_reference', 'history', 'claims', 'metric', 'beta'])
def test_rehashed_fitted_bundle_rejects_closed_contract_attacks(fitted, tmp_path, attack):
    doc, result = fitted
    root = tmp_path/'fitted'
    bundle.write_bundle(root, result, doc)
    manifest = json.loads((root/'manifest.json').read_bytes())
    if attack == 'traversal':
        manifest['members'][0]['name'] = '../outside.npy'
    elif attack == 'dtype':
        manifest['members'][0]['dtype'] = 'object'
    elif attack == 'shape_bomb':
        manifest['members'][0]['shape'] = [2**60, 2**60]
    elif attack == 'unit':
        manifest['members'][0]['unit'] = 'wrong'
    elif attack == 'extra':
        manifest['result']['owner'] = 'untrusted'
    elif attack == 'duplicate_reference':
        manifest['result']['model']['chi_si'] = manifest['result']['model']['active_indices']
    elif attack == 'history':
        manifest['result']['history']['codec'] = 'hash_truncated'
    elif attack == 'claims':
        manifest['result']['claims']['full_method_accepted'] = True
    elif attack == 'metric':
        manifest['result']['metrics']['outer']['normalized_rms'] = True
    else:
        manifest['result']['candidates'][0]['beta'] = 999.
    manifest.pop('generation_sha256')
    manifest['generation_sha256'] = bundle.digest(manifest)
    (root/'manifest.json').write_bytes(bundle.canonical(manifest))
    with pytest.raises(InputError):
        bundle.read_bundle(root)


@pytest.mark.parametrize('failure', ['disk_full', 'publication_interrupt'])
def test_new_generation_failure_preserves_prior_success(fitted, tmp_path, monkeypatch, failure):
    doc, result = fitted
    old = tmp_path/'old'
    identity = bundle.write_bundle(old, result, doc)
    previous = {p.name: p.read_bytes() for p in old.iterdir()}
    def fail_io(*args):
        raise OSError('injected local failure')
    with monkeypatch.context() as patch:
        patch.setattr(bundle.os, 'fsync' if failure == 'disk_full' else 'replace', fail_io)
        with pytest.raises(OSError, match='injected'):
            bundle.write_bundle(tmp_path/'new', result, doc)
    assert not (tmp_path/'new').exists()
    assert previous == {p.name: p.read_bytes() for p in old.iterdir()}
    assert bundle.read_bundle(old)['generation_sha256'] == identity
