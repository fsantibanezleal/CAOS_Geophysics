"""Assembly guards operate on metadata/copies, never run an inverse or alter canonical data."""
import hashlib
import json

import pytest
import sys

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
    with pytest.raises(ValueError, match='changed family'):
        assembly.family_proof('mt', 'baseline')
    assert assembly.family_proof('mt', 'baseline', fresh_mt=True)['unchanged'] is False
    with pytest.raises(ValueError, match='changed family'):
        assembly.family_proof('gravity', 'baseline', fresh_mt=True)


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


@pytest.fixture
def mt_handoff(tmp_path):
    from geology import VARIANTS
    mt, source = tmp_path/'mt', tmp_path/'source'
    entries, cases = [], []
    for case in registry():
        if case['family'] != 'mt':
            continue
        variants = []
        for variant, _, _ in VARIANTS:
            relative = f'{case["id"]}/{variant}.json'
            assembly.write_json(source/relative, dict(original=True))
            assembly.write_json(mt/relative, dict(fresh=True))
            raw = (mt/relative).read_bytes()
            entry = dict(path=relative, sha256=assembly.sha(raw), bytes=len(raw), source_valid=True,
                         reference_sha256=assembly.sha((source/relative).read_bytes()))
            entries.append(entry)
            variants.append(dict(id=variant, methods={'mt-lm': {}, 'mt-adam': {}, 'mt-nn': {}}, **entry))
        cases.append(dict(id=case['id'], variants=variants))
    assembly.write_json(mt/'catalog.json', dict(complete=False, cases=cases))
    assembly.write_json(mt/'release.json', dict(complete=False, cases=4, runs=24, methods=72))
    field = dict(artifact='edi/clear-lake-cl061-screen.json', source_sha256='source-pin', source_bytes=16411)
    assembly.write_json(mt/field['artifact'], dict(truth=None, methods={}, inversion_performed=False,
                       one_d_inversion_eligible=False, compatibility=dict(passes_screen=False)))
    raw = (mt/field['artifact']).read_bytes()
    field.update(sha256=assembly.sha(raw), bytes=len(raw))
    entry = dict(artifact='clear-lake-cl061-screen.json', source_sha256=field['source_sha256'],
                 source_bytes=field['source_bytes'], artifact_sha256=field['sha256'], artifact_bytes=field['bytes'],
                 parser_source_sha256=assembly.sha((assembly.ROOT/'data-pipeline/edi.py').read_bytes()),
                 one_d_inversion_eligible=False)
    manifest = dict(fixtures=[dict(original=True)], calibration=[dict(original=True)], field_screens=[entry])
    assembly.write_json(source/'edi/manifest.json', manifest)
    assembly.write_json(mt/'edi/manifest.json', manifest)
    names = ['data-pipeline/'+n for n in ('electromagnetics.py', 'edi.py', 'geology.py', 'provenance.py', 'rebuild.py', 'seismic.py')]
    names += ['scripts/build_field_screen.py', 'scripts/validate_mt_replays.py']
    receipt = dict(schema='inverse-earth/mt-source-reconciliation/v1', status='PASS', conditions=24,
                   method_results=72, bootstrap_refits=3072, canonical_unchanged=True, artifacts=entries,
                   source_sha256={n: assembly.sha((assembly.ROOT/n).read_bytes()) for n in names},
                   catalog_sha256=assembly.sha((mt/'catalog.json').read_bytes()),
                   release_sha256=assembly.sha((mt/'release.json').read_bytes()),
                   edi_manifest_sha256=assembly.sha((mt/'edi/manifest.json').read_bytes()), field_screen=field)
    assembly.write_json(mt/'mt-replay.json', receipt)
    return mt, source, receipt


def test_mt_handoff_binds_actual_bytes_and_does_not_relabel(mt_handoff):
    mt, source, _ = mt_handoff
    raw = (mt/'mt-replay.json').read_bytes()
    proof = assembly.mt_contribution(mt, assembly.sha(raw), source)
    assert len(proof['entries']) == 24
    assert proof['inherited_edi_manifest_except_field_unchanged']
    assert (mt/'mt-replay.json').read_bytes() == raw


@pytest.mark.parametrize('fault', ['pin', 'source', 'duplicate', 'missing', 'reference', 'catalog',
                                 'release', 'manifest', 'field-bytes', 'field-source', 'field-verdict'])
def test_mt_handoff_rejects_stale_forged_or_incomplete_inputs(mt_handoff, fault):
    mt, source, receipt = mt_handoff
    if fault == 'source':
        receipt['source_sha256']['data-pipeline/electromagnetics.py'] = 'stale'
    elif fault == 'duplicate':
        receipt['artifacts'][-1] = receipt['artifacts'][0]
    elif fault == 'missing':
        receipt['artifacts'].pop()
    elif fault == 'reference':
        receipt['artifacts'][0]['reference_sha256'] = 'other'
    elif fault == 'catalog':
        receipt['catalog_sha256'] = 'wrong'
    elif fault == 'release':
        value = assembly.read_json(mt/'release.json')
        value['complete'] = True
        assembly.write_json(mt/'release.json', value)
        receipt['release_sha256'] = assembly.sha((mt/'release.json').read_bytes())
    elif fault in ('manifest', 'field-source'):
        value = assembly.read_json(mt/'edi/manifest.json')
        if fault == 'manifest':
            value['fixtures'] = []
        else:
            value['field_screens'][0]['source_sha256'] = 'another-station'
        assembly.write_json(mt/'edi/manifest.json', value)
        receipt['edi_manifest_sha256'] = assembly.sha((mt/'edi/manifest.json').read_bytes())
    elif fault in ('field-bytes', 'field-verdict'):
        value = assembly.read_json(mt/'edi/clear-lake-cl061-screen.json')
        value['one_d_inversion_eligible'] = True
        assembly.write_json(mt/'edi/clear-lake-cl061-screen.json', value)
        if fault == 'field-verdict':
            raw = (mt/'edi/clear-lake-cl061-screen.json').read_bytes()
            receipt['field_screen'].update(sha256=assembly.sha(raw), bytes=len(raw))
            manifest = assembly.read_json(mt/'edi/manifest.json')
            manifest['field_screens'][0].update(artifact_sha256=assembly.sha(raw), artifact_bytes=len(raw))
            assembly.write_json(mt/'edi/manifest.json', manifest)
            receipt['edi_manifest_sha256'] = assembly.sha((mt/'edi/manifest.json').read_bytes())
    assembly.write_json(mt/'mt-replay.json', receipt)
    pin = 'wrong' if fault == 'pin' else assembly.sha((mt/'mt-replay.json').read_bytes())
    with pytest.raises(ValueError):
        assembly.mt_contribution(mt, pin, source)


def test_full_replay_does_not_weaken_partial_matrix_gate():
    sys.path.insert(0, str(assembly.ROOT/'scripts'))
    from validate_fwi_mt_candidate import full_matrix
    from validate_mt_replays import validate_matrix
    catalog = assembly.read_json(assembly.ROOT/'data/derived/v2/catalog.json')
    full_matrix(catalog)
    with pytest.raises(AssertionError):
        validate_matrix(catalog)
    catalog['cases'][0]['variants'][1] = catalog['cases'][0]['variants'][0]
    with pytest.raises(AssertionError, match='unique full matrix'):
        full_matrix(catalog)
