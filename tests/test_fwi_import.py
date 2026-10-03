"""Migration/path/rollback controls on temporary trees only; never import real canonical data."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

import artifact_versions as versions
from provenance import generator_fingerprint

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import import_fwi_candidate as importer  # noqa: E402

spec = importlib.util.spec_from_file_location('migration_artifact_gate', ROOT/'scripts/check_artifacts.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(importer.encoded(value))


@pytest.mark.parametrize('container,producer', [
    ('0.04.000', '0.04.000'), ('0.04.001', '0.04.000'), ('0.04.001', '0.04.001'),
    ('0.04.002', '0.04.000'), ('0.04.002', '0.04.001'), ('0.04.002', '0.04.002')])
def test_explicit_version_reuse_requires_actual_version_specific_source(container, producer):
    prior = dict(version=producer, generator_fingerprint=generator_fingerprint('seismic', version=producer))
    gate.assert_run_provenance('seismic', prior, container)
    prior['generator_fingerprint'] = '0'*64
    with pytest.raises(AssertionError, match='Stale scientific'):
        gate.assert_run_provenance('seismic', prior, container)


@pytest.mark.parametrize('container,producer', [('0.04.003', '0.04.003'), ('0.04.002', 'oldmain'),
                                              ('0.04.001', '0.04.002'), ('0.04.002', '0.04.003')])
def test_unreviewed_version_is_not_accepted_even_if_matching(container, producer):
    with pytest.raises(AssertionError):
        versions.allowed_run_version(container, producer)


def test_header_migration_preserves_all_scientific_bytes():
    raw = b'{"schema":"catalog","version":"0.04.001","metric":1.2345678901}\n'
    changed = versions.header_bytes(raw, '0.04.001', '0.04.002')
    assert changed == raw.replace(b'0.04.001', b'0.04.002')
    assert versions.header_bytes(changed, '0.04.002', '0.04.001') == raw
    with pytest.raises(AssertionError):
        versions.header_bytes(raw, '0.04.000', '0.04.002')
    with pytest.raises(AssertionError, match='Ambiguous'):
        versions.header_bytes(b'{"version":"0.04.001","nested":{"version":"0.04.001"}}', '0.04.001', '0.04.002')


@pytest.fixture
def migration_tree(tmp_path):
    root = tmp_path/'staged'
    preserved, cases = [], []
    for case in range(20):
        variants = []
        for variant in range(6):
            relative = f'CASE{case}/variant{variant}.json'
            write(root/relative, dict(original=True, case=case, variant=variant))
            preserved.append(dict(path=relative, sha256=versions.digest(root/relative), bytes=(root/relative).stat().st_size))
            variants.append(dict(path=relative))
        cases.append(dict(variants=variants))
    for index in range(13):
        relative = f'{"models" if index < 3 else "edi"}/fixture{index}.json'
        write(root/relative, dict(original=True, index=index))
        preserved.append(dict(path=relative, sha256=versions.digest(root/relative), bytes=(root/relative).stat().st_size))
    original = importer.encoded(dict(version='0.04.001', cases=cases))
    raw = versions.header_bytes(original, '0.04.001', '0.04.002')
    (root/'catalog.json').write_bytes(raw)
    matrix = dict(cases=20, runs=120, method_results=348)
    write(root/'mt-replay.json', dict(status='PASS', catalog_sha256=hashlib.sha256(original).hexdigest(),
          release_sha256='original-release-pin', conditions=120, method_results=348,
          states_replayed=4038, bootstrap_refits=3072, artifact_gate=matrix,
          source_sha256={n: versions.digest(versions.REPO/n) for n in versions.REPLAY_SOURCE_FILES}))
    write(root/'fwi-replay.json', dict(conditions=24, method_results=48, records=[{}]*48))
    migration = dict(schema='inverse-earth/byte-preserving-container-migration/v1', from_version='0.04.001',
                     to_version='0.04.002', reused_producer_versions=['0.04.000', '0.04.001'], plan_sha256='plan-pin',
                     source_catalog_sha256=hashlib.sha256(original).hexdigest(), catalog_sha256=hashlib.sha256(raw).hexdigest(),
                     source_release_sha256='original-release-pin', preserved_files=preserved,
                     independent_review_source_sha256=importer.read(root/'mt-replay.json')['source_sha256'],
                     guard_epoch_differences={},
                     scientific_source_sha256={n: versions.digest(versions.REPO/n) for n in versions.SCIENTIFIC_FILES},
                     gate_sha256={n: versions.digest(versions.REPO/n) for n in ('scripts/check_artifacts.py', 'data-pipeline/artifact_versions.py')},
                     independent_receipts={n: versions.digest(root/n) for n in ('fwi-replay.json', 'mt-replay.json')})
    write(root/'migration.json', migration)
    write(root/'validation.json', dict(schema='inverse-earth/container-validation/v1', container_version='0.04.002',
          plan_sha256='plan-pin', source_artifact_matrix=matrix, independent_receipts=migration['independent_receipts']))
    release = dict(container_migration_sha256=versions.digest(root/'migration.json'),
                   container_validation_sha256=versions.digest(root/'validation.json'))
    write(root/'release.json', release)
    return root, json.loads(raw), release, migration


def test_migration_requires_133_preserved_byte_hashes_and_independent_receipts(migration_tree):
    root, catalog, release, _ = migration_tree
    versions.validate_migration(root, catalog, release)
    assert len(importer.snapshot(root)) == 139


@pytest.mark.parametrize('fault', ['scientific', 'gate', 'duplicate', 'fixture', 'header', 'receipt', 'version',
                                 'validation', 'epoch', 'old-tool', 'other-replay'])
def test_rehashed_migration_cannot_hide_stale_source_or_changed_evidence(migration_tree, fault):
    root, catalog, release, migration = migration_tree
    if fault == 'scientific':
        migration['scientific_source_sha256']['data-pipeline/seismic.py'] = 'stale'
    elif fault == 'gate':
        migration['gate_sha256']['scripts/check_artifacts.py'] = 'stale'
    elif fault == 'duplicate':
        migration['preserved_files'][-1] = migration['preserved_files'][0]
    elif fault == 'fixture':
        write(root/migration['preserved_files'][0]['path'], dict(changed=True))
    elif fault == 'header':
        catalog['unreviewed'] = True
        write(root/'catalog.json', catalog)
        migration['catalog_sha256'] = versions.digest(root/'catalog.json')
    elif fault == 'receipt':
        write(root/'fwi-replay.json', dict(conditions=24, method_results=48, records=[{}]*47))
        migration['independent_receipts']['fwi-replay.json'] = versions.digest(root/'fwi-replay.json')
    elif fault == 'version':
        migration['reused_producer_versions'] = ['0.04.001']
    elif fault == 'validation':
        write(root/'validation.json', dict(schema='forged'))
    elif fault == 'epoch':
        migration['guard_epoch_differences']['scripts/check_artifacts.py'] = dict(
            independent_review_sha256='fake-old-tool', migration_guard_sha256='fake-new-tool')
    elif fault == 'old-tool':
        migration['independent_review_source_sha256']['scripts/check_artifacts.py'] = 'fake-old-tool'
    elif fault == 'other-replay':
        mt = importer.read(root/'mt-replay.json')
        mt['source_sha256']['scripts/validate_fwi_exports.py'] = 'unreviewed-checker'
        migration['independent_review_source_sha256'] = mt['source_sha256']
        write(root/'mt-replay.json', mt)
        migration['independent_receipts']['mt-replay.json'] = versions.digest(root/'mt-replay.json')
    write(root/'migration.json', migration)
    release['container_migration_sha256'] = versions.digest(root/'migration.json')
    with pytest.raises(AssertionError):
        versions.validate_migration(root, catalog, release)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    repo = tmp_path/'repo'
    canonical = repo/'data/derived/v2'
    for index in range(137):
        write(canonical/f'original{index}.json', dict(index=index))
    monkeypatch.setattr(importer, 'REPO', repo)
    monkeypatch.setattr(importer, 'CANONICAL', canonical)
    monkeypatch.setattr(importer, 'EXPERIMENTS', repo/'data/experiments')
    monkeypatch.setattr(importer, 'BACKUPS', repo/'data/raw/canonical-backups')
    monkeypatch.setattr(importer.subprocess, 'run', lambda *_a, **_k: SimpleNamespace(returncode=0))
    tracked = '\n'.join(p.relative_to(repo).as_posix() for p in sorted(canonical.rglob('*')) if p.is_file())
    monkeypatch.setattr(importer.subprocess, 'check_output', lambda args, **_k: '' if 'status' in args else tracked)
    return canonical


def test_canonical_only_exact_clean_frozen_137_files(workspace, monkeypatch):
    canonical = workspace
    entries = importer.snapshot(canonical)
    frozen = importer.tree_sha(entries)
    assert importer.clean_canonical(frozen) == entries
    with pytest.raises(ValueError, match='exact'):
        importer.exact_target(canonical.parent)
    write(canonical/'original0.json', dict(changed=True))
    with pytest.raises(ValueError, match='Changed canonical'):
        importer.clean_canonical(frozen)
    monkeypatch.setattr(importer.subprocess, 'check_output', lambda *_a, **_k: ' M data/derived/v2/original0.json')
    with pytest.raises(ValueError, match='Dirty canonical'):
        importer.clean_canonical(frozen)


def test_paths_must_be_private_ignored_children_without_links(workspace, monkeypatch):
    root = importer.EXPERIMENTS
    with pytest.raises(ValueError, match='distinct child'):
        importer.ignored_child(root, root)
    with pytest.raises(ValueError, match='distinct child'):
        importer.ignored_child(root.parent/'escape', root)
    assert importer.ignored_child(root/'staging', root).is_relative_to(root)
    monkeypatch.setattr(importer.subprocess, 'run', lambda *_a, **_k: SimpleNamespace(returncode=1))
    with pytest.raises(ValueError, match='ignored'):
        importer.ignored_child(root/'staging', root)
    monkeypatch.setattr(Path, 'is_junction', lambda self: self == root)
    with pytest.raises(ValueError, match='junction'):
        importer.safe_path(root/'staging')


def test_independent_receipt_pin_checked_before_parsing(tmp_path):
    path = tmp_path/'receipt.json'
    path.write_bytes(b'not a receipt')
    with pytest.raises(ValueError, match='receipt hash'):
        importer.independent_acceptance(tmp_path, path, path, 'wrong', 'wrong')


@pytest.mark.parametrize('approval', [None, '', 'IMPORT', 'IMPORT-old-plan'])
def test_no_operator_approval_means_no_import(tmp_path, monkeypatch, approval):
    plan = tmp_path/'plan.json'
    write(plan, {})
    monkeypatch.setattr(importer, 'verify_plan', lambda *_a: pytest.fail('No filesystem preflight before approval'))
    with pytest.raises(ValueError, match='operator approval'):
        importer.import_container(plan, approval)


def test_frozen_plan_drift_rejects_without_mutation(tmp_path, monkeypatch):
    receipts = tmp_path/'receipts'
    plan = dict(receipts=str(receipts), target='target', stage='stage', backup='backup', canonical_tree_sha256='digest',
                inputs=dict(candidate='candidate', fwi='fwi', mt='mt', fwi_pin='fwi-pin', mt_pin='mt-pin'))
    write(receipts/'plan.json', plan)
    monkeypatch.setattr(importer, 'make_plan', lambda *_a: {**plan, 'changed': True})
    with pytest.raises(ValueError, match='Frozen plan'):
        importer.verify_plan(receipts/'plan.json')
    assert not (tmp_path/'backup').exists()


@pytest.mark.parametrize('failure', ['none', 'rename', 'postgate', 'external'])
def test_publication_retains_original_backup_and_safe_recovery(tmp_path, monkeypatch, failure):
    target, stage, backup, failed = [tmp_path/name for name in ('canonical', 'stage', 'private-backup', 'failed')]
    write(target/'old.json', dict(original=True))
    write(stage/'new.json', dict(corrected=True))
    original, staged = importer.snapshot(target), importer.snapshot(stage)
    replace = importer.os.replace
    if failure in ('rename', 'external'):
        def interrupted(source, destination):
            if source == stage:
                if failure == 'external':
                    write(target/'external.json', dict(preserve=True))
                raise OSError('Injected publication failure')
            replace(source, destination)
        monkeypatch.setattr(importer.os, 'replace', interrupted)
    def check(_target):
        if failure == 'postgate':
            raise ValueError('Injected gate failure')
    if failure == 'none':
        result = importer.publish(stage, target, backup, original, staged, failed, check)
        assert result['original_backup_retained'] and importer.snapshot(target) == staged
    else:
        with pytest.raises((OSError, ValueError), match='Injected'):
            importer.publish(stage, target, backup, original, staged, failed, check)
        if failure == 'external':
            assert (target/'external.json').exists() and not (target/'old.json').exists()
        else:
            assert importer.snapshot(target) == original
        if failure == 'postgate':
            assert importer.snapshot(failed) == staged
    assert importer.snapshot(backup) == original


def test_publication_drift_or_existing_backup_never_moves_originals(tmp_path):
    target, stage, backup, failed = [tmp_path/name for name in ('canonical', 'stage', 'backup', 'failed')]
    write(target/'old.json', dict(original=True))
    write(stage/'new.json', dict(corrected=True))
    original, staged = importer.snapshot(target), importer.snapshot(stage)
    with pytest.raises(ValueError, match='input drift'):
        importer.publish(stage, target, backup, original, [], failed, lambda *_a: None)
    backup.mkdir()
    with pytest.raises(ValueError, match='Fresh private'):
        importer.publish(stage, target, backup, original, staged, failed, lambda *_a: None)
    assert importer.snapshot(target) == original


def test_failed_import_writes_recovery_receipt_without_hiding_error(tmp_path, monkeypatch):
    receipts, target, stage, backup = [tmp_path/name for name in ('receipts', 'target', 'stage', 'backup')]
    write(target/'old.json', dict(original=True))
    write(stage/'new.json', dict(corrected=True))
    plan = dict(receipts=str(receipts), stage=str(stage), target=str(target), backup=str(backup),
                canonical=importer.snapshot(target))
    write(receipts/'plan.json', plan)
    write(receipts/'stage.json', dict(plan_sha256=versions.digest(receipts/'plan.json'), inventory=importer.snapshot(stage)))
    monkeypatch.setattr(importer, 'verify_plan', lambda *_a: plan)
    monkeypatch.setattr(importer, 'artifact_gate', lambda *_a: None)
    def fail(*_a):
        raise OSError('Injected failure before mutation')
    monkeypatch.setattr(importer, 'publish', fail)
    with pytest.raises(OSError, match='Injected failure'):
        importer.import_container(receipts/'plan.json', 'IMPORT-'+versions.digest(receipts/'plan.json'))
    recovery = importer.read(receipts/'import-error.json')
    assert recovery['canonical_matches_original'] is True and recovery['backup_exists'] is False
    assert importer.snapshot(target) == plan['canonical']
