"""Actual WAL root intake reservations and retained-cut SQL, not POSIX proof."""

from contextlib import closing
import sqlite3
from uuid import uuid4

import pytest

from app.physical_persistence import M
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


@pytest.fixture
def intake(root_case):
    path, files, values, _, original = root_case
    # A newly uploaded original, before any root namespace has been allocated.
    with closing(sqlite3.connect(path)) as connection:
        connection.execute('DELETE FROM physical_custody_files')
        connection.execute('DELETE FROM physical_custody_batches')
        connection.commit()
    stage = files.root / '.job-staging' / values['root_dataset_id']
    for leaf in ('input.json', 'dataset.json'):
        (stage / leaf).unlink()
    stage.rmdir()
    values = {key: values[key] for key in ('owner_id', 'project_id', 'raw_asset_id', 'root_dataset_id', 'created_us')}
    values['batch_id'] = str(uuid4())
    return path, files, values, original


def wal(path):
    connection = sqlite3.connect(path)
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('PRAGMA synchronous=FULL')
    connection.execute('PRAGMA trusted_schema=OFF')
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('BEGIN IMMEDIATE')
    return connection


def test_root_reservation_is_durable_before_any_stage_copy_and_owned_by_caller(intake):
    from app.physical_root_intake import reserve_root_transaction
    path, files, values, original = intake
    with closing(wal(path)) as connection:
        result = reserve_root_transaction(connection, files, **values)
        assert connection.in_transaction
        assert result['original'] == original and result['dataset_key'].endswith(values['root_dataset_id'] + '.json')
        assert not (files.root / '.job-staging' / values['root_dataset_id']).exists()
        assert connection.execute('SELECT state,capacity_bytes,charged_bytes,inventory_bytes FROM physical_custody_batches').fetchone() == ('reserved', 32*M, 32*M, None)
        assert connection.execute('SELECT ordinal,leaf,state,actual_bytes FROM physical_custody_files ORDER BY ordinal').fetchall() == [(1, 'input.json', 'reserved', None), (2, 'dataset.json', 'reserved', None)]
        with closing(sqlite3.connect(path)) as independent:
            assert independent.execute('SELECT count(*) FROM physical_custody_batches').fetchone() == (0,)
        connection.commit()
    with closing(sqlite3.connect(path)) as independent:
        assert independent.execute('SELECT charged_bytes FROM physical_custody_batches').fetchone() == (32*M,)


@pytest.mark.parametrize('damage', ['quota', 'foreign-owner', 'unattested', 'changed-raw'])
def test_root_intake_refuses_before_namespace_or_reservation(intake, damage):
    from app.physical_root_intake import reserve_root_transaction
    path, files, values, _ = intake
    with closing(wal(path)) as connection:
        if damage == 'foreign-owner': values['owner_id'] = str(uuid4())
        if damage == 'unattested': connection.execute("UPDATE source_records SET private_storage_permission='not_attested'")
        if damage == 'changed-raw':
            raw = files.root / f"projects/{values['owner_id']}/{values['project_id']}/{values['raw_asset_id']}"
            raw.write_bytes(b'changed bytes retained')
        options = dict(quota_bytes=48*M) if damage == 'quota' else {}
        with pytest.raises(ValueError):
            reserve_root_transaction(connection, files, **values, **options)
        assert connection.execute('SELECT count(*) FROM physical_custody_batches').fetchone() == (0,)
        assert not (files.root / '.job-staging' / values['root_dataset_id']).exists()


def test_concurrent_serialized_duplicate_rejected_before_second_root_allocation(intake):
    from app.physical_root_intake import reserve_root_transaction
    path, files, values, _ = intake
    with closing(wal(path)) as connection:
        reserve_root_transaction(connection, files, **values)
        connection.commit()
    with closing(wal(path)) as connection:
        other = dict(values, root_dataset_id=str(uuid4()), batch_id=str(uuid4()))
        with pytest.raises(ValueError, match='physical_root_already_reserved'):
            reserve_root_transaction(connection, files, **other)
        assert connection.execute('SELECT count(*) FROM physical_custody_batches').fetchone() == (1,)
        assert not (files.root / '.job-staging' / other['root_dataset_id']).exists()


@pytest.mark.parametrize('damage', [None, 'unknown', 'input-changed', 'envelope-changed'])
def test_sealing_checks_complete_original_and_envelope_then_reduces_only_measured_charge(intake, damage):
    from app.physical_root_intake import reserve_root_transaction, seal_root_transaction
    from app.physical_contract import byte_sha, parse_record
    path, files, values, original = intake
    with closing(wal(path)) as connection:
        prepared = reserve_root_transaction(connection, files, **values)
        connection.commit()
    stage = files.root / '.job-staging' / values['root_dataset_id']
    stage.mkdir()
    (stage/'input.json').write_bytes(original)
    (stage/'dataset.json').write_bytes(prepared['body'])
    if damage == 'unknown': (stage/'unknown').write_bytes(b'preserve')
    if damage == 'input-changed': (stage/'input.json').write_bytes(b'changed')
    if damage == 'envelope-changed': (stage/'dataset.json').write_bytes(prepared['body'] + b' ')
    before = {p.name: p.read_bytes() for p in stage.iterdir()}
    with closing(wal(path)) as connection:
        arguments = {key: values[key] for key in ('owner_id', 'project_id', 'root_dataset_id', 'batch_id')}
        if damage is not None:
            with pytest.raises(ValueError):
                seal_root_transaction(connection, files, **arguments, sealed_us=3)
            assert connection.execute('SELECT state,charged_bytes FROM physical_custody_batches').fetchone() == ('reserved', 32*M)
        else:
            seal_root_transaction(connection, files, **arguments, sealed_us=3)
            state, charge, body, sha = connection.execute('SELECT state,charged_bytes,inventory_bytes,inventory_sha256 FROM physical_custody_batches').fetchone()
            assert state == 'sealed' and charge == len(original) + len(prepared['body'])
            assert byte_sha(body) == sha and parse_record([body])['removed_ordinals'] == []
            assert connection.execute("SELECT count(*) FROM physical_custody_files WHERE state='present'").fetchone() == (2,)
        assert connection.in_transaction
        connection.commit()
    assert {p.name: p.read_bytes() for p in stage.iterdir()} == before
