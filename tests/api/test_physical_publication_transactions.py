"""Caller-WAL proof using exact retained original science, never another fit."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3

import pytest

from app.physical_contract import byte_sha
from app.physical_publication import publish_correction_transaction, publish_transform_transaction
from tests.api.test_physical_publication import decoded, publication as publication
from tests.api.test_physical_transform_publication import transform_publication as transform_publication
from tests.api.test_physical_successor import successor as successor


def retained(name, expected):
    path = Path(os.environ[name])
    assert path.is_absolute() and all(not (p/'.git').exists() for p in (path,*path.parents))
    body = path.read_bytes()
    assert byte_sha(body) == expected, 'retained original science packet changed; never replace it with a rerun'
    return decoded(json.loads(body))


@pytest.fixture(scope='session')
def actual_science():
    return retained('M01_RETAINED_CORRECTION_PACKET', '44eca87a1f5750fede3f7f4530ea550a368538f3b5fdbd073b3713e7d950722a')


@pytest.fixture(scope='session')
def actual_transforms():
    return retained('M01_RETAINED_TRANSFORM_PACKET', '6881c30e13e39de03c7530a2b6fd2e1bb49b1b50d361fdf41dfb7cc44c8dbcb8')


def native(connection):
    assert connection.execute('PRAGMA journal_mode=WAL').fetchone() == ('wal',)
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA synchronous=FULL')
    connection.execute('PRAGMA trusted_schema=OFF')
    connection.execute('BEGIN IMMEDIATE')
    connection.execute("UPDATE projects SET name='Uncommitted caller change'")


def terminal(connection):
    return connection.execute('SELECT id,state,result_bytes,result_sha256 FROM processing_jobs ORDER BY id').fetchall()


@pytest.mark.parametrize('commit', [False,True])
def test_full_original_correction_publication_visibility_owned_by_caller(publication, commit):
    path, files, values, packet = publication
    bodies = {str(p.relative_to(files.root)): p.read_bytes() for p in files.root.rglob('*') if p.is_file()}
    with closing(sqlite3.connect(path)) as db, closing(sqlite3.connect(path)) as reader:
        before = terminal(reader)
        native(db)
        assert publish_correction_transaction(db, files, **values) == packet['snapshot']
        assert db.in_transaction and terminal(reader) == before
        assert db.execute('SELECT state FROM processing_jobs').fetchone() == ('succeeded',)
        assert db.execute('SELECT count(*) FROM physical_publication_intents').fetchone() == (0,)
        db.commit() if commit else db.rollback()
        assert (terminal(reader) != before) == commit
        assert reader.execute('SELECT reserved_count,published_count FROM physical_dataset_families').fetchone() == ((0,2) if commit else (1,1))
        assert reader.execute('PRAGMA foreign_key_check').fetchall() == []
    assert {str(p.relative_to(files.root)): p.read_bytes() for p in files.root.rglob('*') if p.is_file()} == bodies


@pytest.mark.parametrize('cut', ['child','production','terminal','retired'])
def test_original_terminal_cuts_keep_caller_work_and_all_installed_copies(publication, cut):
    path, files, values, _ = publication
    bodies = {str(p.relative_to(files.root)): p.read_bytes() for p in files.root.rglob('*') if p.is_file()}
    with closing(sqlite3.connect(path)) as db:
        native(db)
        before = terminal(db)
        def fail(point):
            if point == cut: raise RuntimeError('original_publication_cut')
        with pytest.raises(RuntimeError, match='original_publication_cut'):
            publish_correction_transaction(db, files, **values, failure_cut=fail)
        assert db.in_transaction and terminal(db) == before
        assert db.execute('SELECT name FROM projects').fetchone() == ('Uncommitted caller change',)
        assert db.execute('SELECT count(*) FROM physical_publication_intents').fetchone() == (1,)
        assert db.execute('SELECT count(*) FROM physical_publication_targets').fetchone() == (2,)
        assert db.execute('SELECT permanent_reservation_bytes FROM physical_job_controls').fetchone()[0] == 80*1048576
        db.rollback()
    assert {str(p.relative_to(files.root)): p.read_bytes() for p in files.root.rglob('*') if p.is_file()} == bodies


@pytest.mark.parametrize('commit', [False,True])
def test_saved_original_transform_pass_and_height_nonpass_do_not_change(transform_publication, commit):
    path, files, values, packet = transform_publication
    with closing(sqlite3.connect(path)) as db, closing(sqlite3.connect(path)) as reader:
        before = terminal(reader)
        native(db)
        result = publish_transform_transaction(db, files, **values)
        expected = json.loads(packet['child_bytes'])['production']['scientific_verdict']
        assert result['production']['scientific_verdict'] == expected
        assert db.in_transaction and terminal(reader) == before
        db.commit() if commit else db.rollback()
        assert (terminal(reader) != before) == commit
        assert reader.execute('PRAGMA foreign_key_check').fetchall() == []
