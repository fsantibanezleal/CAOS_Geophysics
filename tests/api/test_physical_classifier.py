"""Whole successor snapshot tests. Portable files are not native admission."""

from copy import deepcopy

import pytest

from app.physical_classifier import classify_snapshot
from app.physical_contract import byte_sha
from app.physical_contract import M, canonical, digest
from app.physical_roots import prepare_root, publish_root
from app.physical_publication import publish_correction, publish_transform
from app.physical_debt import retire_failed_job
from tests.api.test_physical_forest import connect
from tests.api.test_physical_roots import root_case as root_case, install_fixture, publish_values
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey
from tests.api.test_physical_publication import actual_science as actual_science, publication as publication
from tests.api.test_physical_transform_publication import actual_transforms as actual_transforms, transform_publication as transform_publication


class CensusFiles:
    def __init__(self, original):
        self.original = original
        self.root = original.root

    def read(self, *args, **kwargs):
        return self.original.read(*args, **kwargs)

    def verify_directory(self, *args, **kwargs):
        return self.original.verify_directory(*args, **kwargs)

    def names(self, key, *, limit):
        names = [p.name for p in (self.root / key).iterdir()]
        if len(names) > limit:
            raise ValueError('fixture_name_cap')
        return names

    def directory_identity(self, key):
        info = (self.root / key).stat()
        return dict(device=info.st_dev, inode=info.st_ino)

    def census(self, expected, *, empty_directories=()):
        # Test-only ordinary file walk: no descriptor/native durability claim.
        actual = {}
        allowed = set(empty_directories)
        for key in expected:
            parts = key.split('/')
            allowed.update('/'.join(parts[:n]) for n in range(1, len(parts)))
        for path in self.root.rglob('*'):
            key = path.relative_to(self.root).as_posix()
            if path.is_symlink() or (path.is_dir() and key not in allowed):
                raise ValueError('fixture_unknown_namespace')
            if not path.is_file():
                continue
            if key not in expected:
                raise ValueError('fixture_unknown_namespace')
            rule = expected[key]
            body = self.read(key, cap=rule['cap'], expected_bytes=rule['bytes'] if rule['bytes'] is not None else path.stat().st_size,
                             expected_sha256=rule['sha256'] if rule['sha256'] is not None else byte_sha(path.read_bytes()))
            actual[key] = dict(bytes=len(body), sha256=byte_sha(body))
        if any(v['required'] and k not in actual for k, v in expected.items()):
            raise ValueError('fixture_missing_file')
        return actual


def classify(db, files, *, manifests=None):
    db.execute('BEGIN IMMEDIATE')
    before = db.total_changes
    try:
        result = classify_snapshot(db, CensusFiles(files), approved_manifests=manifests or {},
                                   approved_installations={}, native_metadata={})
        assert db.in_transaction and db.total_changes == before
        return result
    finally:
        db.rollback()


def complete_fixture_root_custody(db, files):
    """Existing publication fixtures omit prior root-stage history; add exact
    literal copies from their original registered bytes, not scientific data.
    This does not retrofit a production database or replace a source failure.
    """
    from uuid import uuid4
    from tests.ops.physical_sql_fixture import insert
    cursor = db.execute("SELECT * FROM observation_datasets WHERE kind='root' AND parser_version='gravity-stations-json/v1'")
    headers = [c[0] for c in cursor.description]
    for values in cursor.fetchall():
        root = dict(zip(headers, values))
        raw_cursor = db.execute('SELECT * FROM raw_assets WHERE id=?', (root['raw_asset_id'],))
        raw = dict(zip([c[0] for c in raw_cursor.description], raw_cursor.fetchone()))
        stage = files.root / '.job-staging' / root['id']
        stage.mkdir()
        copies = [('input_spool', None, 'input.json', (files.root / raw['storage_key']).read_bytes()),
                  ('dataset_copy', root['id'], 'dataset.json', (files.root / root['storage_key']).read_bytes())]
        slots = []
        for ordinal, (role, artifact, leaf, body) in enumerate(copies, 1):
            (stage / leaf).write_bytes(body)
            slots.append(dict(ordinal=ordinal, role=role, location='stage', artifact_id=artifact, leaf=leaf,
                              max_bytes=16*M, actual_bytes=len(body), actual_sha256=byte_sha(body)))
        inv = dict(schema='geophysics.physical-custody/v1', batch_id=str(uuid4()), owner_id=root['owner_id'],
            project_id=root['project_id'], origin_kind='root_stage', origin_id=root['id'], stage_id=root['id'],
            deletion_receipt_id=None, raw_asset_id=raw['id'], raw_sha256=raw['sha256'], raw_bytes=raw['byte_count'],
            parser_version='gravity-stations-json/v1', method_id=None, capacity_bytes=32*M, initial_files=slots, removed_ordinals=[])
        insert(db, 'physical_custody_batches', dict({k:v for k,v in inv.items() if k not in ('schema','initial_files','removed_ordinals')},
            state='cleanup_pending', charged_bytes=sum(s['actual_bytes'] for s in slots), inventory_bytes=canonical(inv),
            inventory_sha256=digest(inv), created_us=1, sealed_us=2, removed_us=None))
        for slot in slots:
            insert(db, 'physical_custody_files', dict(slot, batch_id=inv['batch_id'], state='present'))


def test_complete_prepared_root_before_or_after_file_install_is_abandon_only(root_case):
    path, files, values, body, _ = root_case
    with connect(path) as db:
        prepare_root(db, files, **values)
        before = classify(db, files)
        assert before.classification == 'prepared_uncommitted'
        assert before.operations[values['intent_id']] == 'abandon_only'
        install_fixture(files, values, body)
        after = classify(db, files)
        assert after.classification == 'prepared_uncommitted'
        assert after.operations == before.operations and after.inventory_sha256 != before.inventory_sha256
        assert db.execute('SELECT count(*) FROM observation_datasets').fetchone() == (0,)


def test_published_root_and_every_retained_stage_copy_are_classified(root_case):
    path, files, values, body, original = root_case
    with connect(path) as db:
        prepare_root(db, files, **values)
        install_fixture(files, values, body)
        publish_root(db, files, **publish_values(values))
        result = classify(db, files)
        assert result.classification == 'coherent_committed'
        assert result.operations[values['root_dataset_id']] == 'retain_committed'
        assert result.account_charges[values['owner_id']]['custody'] == len(original) + len(body)
        assert result.runtime is False


@pytest.mark.parametrize('damage', ['unknown', 'original', 'stage', 'charge', 'family', 'source', 'other-family'])
def test_complete_failure_never_partially_grants_recovery(root_case, damage):
    path, files, values, body, _ = root_case
    with connect(path) as db:
        prepare_root(db, files, **values)
        install_fixture(files, values, body)
        publish_root(db, files, **publish_values(values))
        if damage == 'unknown':
            (files.root / 'unknown.bin').write_bytes(b'never adopt')
        elif damage == 'original':
            raw = db.execute('SELECT storage_key FROM raw_assets').fetchone()[0]
            (files.root / raw).write_bytes(b'changed')
        elif damage == 'stage':
            (files.root / f".job-staging/{values['root_dataset_id']}/dataset.json").unlink()
        elif damage == 'charge':
            db.execute('UPDATE physical_custody_batches SET charged_bytes=charged_bytes-1')
        elif damage == 'family':
            db.execute('UPDATE physical_dataset_families SET published_count=2')
        elif damage == 'source':
            db.execute("UPDATE source_records SET citation='tampered source'")
        else:
            # Orphan family corruption is global; no selected-project filter.
            db.execute('PRAGMA foreign_keys=OFF')
            row = list(db.execute('SELECT * FROM physical_dataset_families').fetchone())
            row[0] = 'ffffffff-ffff-4fff-8fff-ffffffffffff'
            row[1] = 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'
            db.execute('INSERT INTO physical_dataset_families VALUES(' + ','.join('?' for _ in row) + ')', row)
            db.execute('PRAGMA foreign_keys=ON')
        snapshot = deepcopy(db.execute('SELECT * FROM physical_dataset_families').fetchall())
        result = classify(db, files)
        assert result.classification == 'inconsistent' and not result.operations
        assert result.inventory_sha256 is None
        assert db.execute('SELECT * FROM physical_dataset_families').fetchall() == snapshot


def test_requires_existing_consistent_transaction(root_case):
    path, files, _, _, _ = root_case
    with connect(path) as db:
        result = classify_snapshot(db, CensusFiles(files), approved_manifests={},
                                   approved_installations={}, native_metadata={})
        assert result.classification == 'inconsistent' and result.reason == 'physical_classifier_transaction'


def test_actual_saved_correction_is_audited_without_new_scientific_solve(publication):
    path, files, values, packet = publication
    with connect(path) as db:
        complete_fixture_root_custody(db, files)
        prepared = classify(db, files, manifests=values['approved_manifests'])
        assert prepared.classification == 'prepared_uncommitted', prepared.reason
        publish_correction(db, files, **values)
        result = classify(db, files, manifests=values['approved_manifests'])
        assert result.classification == 'coherent_committed', result.reason
        assert result.operations[packet['job']['id']] == 'retain_success'


def test_actual_terminal_transform_preserves_original_pass_and_non_pass(transform_publication):
    path, files, values, packet = transform_publication
    with connect(path) as db:
        complete_fixture_root_custody(db, files)
        child = publish_transform(db, files, **values)
        result = classify(db, files, manifests=values['approved_manifests'])
        assert result.classification == 'coherent_committed', result.reason
        assert child['production']['scientific_verdict'] in ('passed', 'non_pass')
        assert result.operations[child['dataset_id']] == 'retain_committed'


@pytest.mark.parametrize('state', ['failed', 'cancelled'])
def test_actual_prepared_nonsuccess_retains_all_installed_copies(publication, state):
    from uuid import uuid4
    path, files, values, packet = publication
    with connect(path) as db:
        complete_fixture_root_custody(db, files)
        targets = [dict(zip(('kind', 'artifact_id', 'storage_key', 'bytes', 'sha256'), row)) for row in
            db.execute('SELECT kind,artifact_id,storage_key,bytes,sha256 FROM physical_publication_targets ORDER BY kind')]
        retire_failed_job(db, owner_id=values['owner_id'], project_id=values['project_id'], job_id=packet['job']['id'],
            state=state, error_code='physical_cancelled' if state == 'cancelled' else 'physical_execution_failed',
            metrics=values['metrics'], finished_at=values['finished_at'], finished_us=5,
            installed_targets=targets, abandon_batch_id=str(uuid4()))
        result = classify(db, files, manifests=values['approved_manifests'])
        assert result.classification == 'coherent_committed', result.reason
        assert result.operations[packet['job']['id']] == 'retain_nonsuccess'
        assert db.execute('SELECT count(*) FROM physical_dataset_productions').fetchone() == (0,)


@pytest.mark.parametrize('damage', ['control', 'approval', 'production', 'stage', 'unknown', 'root-history'])
def test_rehashed_published_science_and_control_negatives_preserve_global_state(publication, damage):
    path, files, values, packet = publication
    with connect(path) as db:
        if damage != 'root-history':
            complete_fixture_root_custody(db, files)
        publish_correction(db, files, **values)
        manifests = deepcopy(values['approved_manifests'])
        if damage == 'control':
            db.execute("UPDATE physical_job_controls SET admission_receipt_sha256=?", ('a'*64,))
        elif damage == 'approval':
            manifests.clear()
        elif damage == 'production':
            db.execute("UPDATE physical_dataset_productions SET scientific_request_sha256=?", ('a'*64,))
        elif damage == 'stage':
            (files.root / f".job-staging/{packet['job']['id']}/request.json").write_bytes(b'changed')
        elif damage == 'unknown':
            (files.root / 'hidden.bin').write_bytes(b'unknown')
        before = db.execute('SELECT state,result_sha256 FROM processing_jobs').fetchall()
        result = classify(db, files, manifests=manifests)
        assert result.classification == 'inconsistent' and not result.operations
        assert db.execute('SELECT state,result_sha256 FROM processing_jobs').fetchall() == before
