"""Assembly guards operate on metadata/copies, never run an inverse or alter canonical data."""
import hashlib
import json

import pytest

import assemble_fwi_candidate as assembly
from geology import registry
from provenance import generator_fingerprint


def encoded(run):
    raw = json.dumps(run).encode()
    return raw, dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), methods=list(run['methods']))


def sample(family='gravity', version='0.04.000'):
    case = next(c for c in registry() if c['family'] == family)
    methods = {'fwi-l2': {}, 'fwi-multiscale': {}} if family == 'seismic' else {'l2': {}, 'irls': {}}
    run = dict(**case, variant='reference', methods=methods, provenance=dict(
        version=version, generator_fingerprint=generator_fingerprint(family, version=version)))
    if family == 'seismic':
        run['export_precision_significant_digits'] = 10
        run['parameters'] = dict(iterations=28)
        run['provenance']['candidate_execution'] = {
            key: assembly.sha((assembly.ROOT/'data-pipeline'/name).read_bytes())
            for key, name in [('solver_sha256', 'seismic.py'), ('geology_sha256', 'geology.py'),
                              ('batch_writer_sha256', 'seismic_batch.py')]}
        for method in methods.values():
            method['solver'] = dict(optimizer_calls=112, lbfgs_max_eval_per_call=25)
    return case, run


def test_reuse_is_original_version_and_source_bound():
    case, run = sample()
    raw, expected = encoded(run)
    result = assembly.validate_run(raw, case, 'reference', expected)
    assert result['version'] == '0.04.000'
    assert result['generator_fingerprint'] == run['provenance']['generator_fingerprint']
    assert assembly.VERSION_SEMANTICS['published'] is False
    assert assembly.VERSION_SEMANTICS['release_version_assigned'] is False
    assert assembly.VERSION_SEMANTICS['next_release_required'] is True


@pytest.mark.parametrize('fault,match', [
    ('hash', 'hash/size'), ('bytes', 'hash/size'), ('seed', 'identity'), ('variant', 'identity'),
    ('fingerprint', 'Stale scientific'), ('version', 'version migration'), ('methods', 'method matrix'),
])
def test_reuse_rejects_forged_metadata(fault, match):
    case, run = sample()
    _, expected = encoded(run)
    if fault == 'seed':
        run['seed'] += 1
    elif fault == 'variant':
        run['variant'] = 'noise'
    elif fault == 'fingerprint':
        run['provenance']['generator_fingerprint'] = 'stale'
    elif fault == 'version':
        run['provenance']['version'] = '0.04.002'
    elif fault == 'methods':
        del run['methods']['irls']
    raw, changed = encoded(run)
    if fault == 'hash':
        changed['sha256'] = 'wrong'
    elif fault == 'bytes':
        changed['bytes'] += 1
    elif fault == 'methods':
        changed['methods'] = expected['methods']
    with pytest.raises(ValueError, match=match):
        assembly.validate_run(raw, case, 'reference', changed)


@pytest.mark.parametrize('fault', ['precision', 'iterations', 'calls', 'search', 'solver', 'writer', 'geology'])
def test_seismic_rejects_reduced_or_stale_candidate(fault):
    case, run = sample('seismic', '0.04.001')
    if fault == 'precision':
        run['export_precision_significant_digits'] = 7
    elif fault == 'iterations':
        run['parameters']['iterations'] = 7
    elif fault in ('calls', 'search'):
        run['methods']['fwi-l2']['solver']['optimizer_calls' if fault == 'calls' else 'lbfgs_max_eval_per_call'] = 1
    else:
        run['provenance']['candidate_execution'][dict(solver='solver_sha256', writer='batch_writer_sha256', geology='geology_sha256')[fault]] = 'stale'
    raw, expected = encoded(run)
    with pytest.raises(ValueError):
        assembly.validate_run(raw, case, 'reference', expected, seismic=True)


def test_seismic_validates_actual_source_provenance():
    case, run = sample('seismic', '0.04.001')
    raw, expected = encoded(run)
    assert assembly.validate_run(raw, case, 'reference', expected, seismic=True)['version'] == '0.04.001'


def test_changed_family_modules_cannot_be_reused(monkeypatch):
    monkeypatch.setattr(assembly, 'baseline_bytes', lambda _commit, relative: (assembly.ROOT/relative).read_bytes())
    assert assembly.family_proof('gravity', 'baseline')['unchanged']
    monkeypatch.setattr(assembly, 'baseline_bytes', lambda *_args: b'changed')
    with pytest.raises(ValueError, match='changed family'):
        assembly.family_proof('gravity', 'baseline')


def test_outputs_cannot_overwrite_or_overlap_any_input(tmp_path, monkeypatch):
    experiments = tmp_path/'experiments'
    experiments.mkdir()
    monkeypatch.setattr(assembly, 'EXPERIMENTS', experiments)
    canonical = tmp_path/'data/derived/v2'
    source = experiments/'seismic'
    receipts = experiments/'receipts'
    destination = experiments/'candidate'
    with pytest.raises(ValueError, match='children'):
        assembly.output_paths(canonical, receipts, [source])
    with pytest.raises(ValueError, match='overlap'):
        assembly.output_paths(source/'candidate', receipts, [source])
    with pytest.raises(ValueError, match='overlap'):
        assembly.output_paths(destination, destination/'receipts', [source])
    destination.mkdir()
    protected = destination/'user.txt'
    protected.write_text('preserve')
    with pytest.raises(ValueError, match='fresh'):
        assembly.output_paths(destination, receipts, [source])
    assert protected.read_text() == 'preserve'


def test_frozen_plan_drift_rejects_before_copy(tmp_path, monkeypatch):
    receipts = tmp_path/'receipts'
    receipts.mkdir()
    destination = tmp_path/'candidate'
    plan = dict(receipts=str(receipts), output=str(destination), baseline_commit='baseline',
                inputs={key: str(tmp_path/key) for key in ('source', 'seismic', 'ledger')})
    path = receipts/'plan.json'
    path.write_text(json.dumps(plan))
    monkeypatch.setattr(assembly, 'build_plan', lambda *_args: {**plan, 'changed': True})
    with pytest.raises(ValueError, match='Frozen assembly plan'):
        assembly.assemble(path)
    assert not destination.exists()
