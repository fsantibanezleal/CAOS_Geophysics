"""Caller-WAL child intent atomicity only; no science/native-files qualification."""

from contextlib import closing
import sqlite3

import pytest

from app.physical_forest import reserve_child_intent, reserve_child_intent_transaction
from tests.api.test_physical_forest import forest as forest
from tests.api.test_physical_successor import successor as successor


def configure(connection):
    assert connection.execute('PRAGMA journal_mode=WAL').fetchone() == ('wal',)
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA synchronous=FULL')
    connection.execute('PRAGMA trusted_schema=OFF')


@pytest.mark.parametrize('commit', [False, True])
def test_same_dual_target_allocator_is_invisible_until_caller_commit(forest, commit):
    path, values = forest
    with closing(sqlite3.connect(path)) as connection, closing(sqlite3.connect(path)) as reader:
        configure(connection)
        connection.execute('BEGIN IMMEDIATE')
        connection.execute("UPDATE projects SET name='Caller pending unrelated change'")
        assert reserve_child_intent_transaction(connection, **values) == 2
        assert connection.in_transaction
        assert connection.execute('SELECT count(*) FROM physical_publication_targets').fetchone() == (2,)
        assert reader.execute('SELECT count(*) FROM physical_publication_targets').fetchone() == (0,)
        assert reader.execute('SELECT next_ordinal,reserved_count FROM physical_dataset_families').fetchone() == (2, 0)
        if commit:
            connection.commit()
        else:
            connection.rollback()
        assert reader.execute('SELECT count(*) FROM physical_publication_targets').fetchone() == (2 if commit else 0,)
        assert reader.execute('SELECT next_ordinal,reserved_count FROM physical_dataset_families').fetchone() == ((3, 1) if commit else (2, 0))
        assert reader.execute('SELECT name FROM projects').fetchone() == (('Caller pending unrelated change' if commit else 'Survey'),)
        assert reader.execute('PRAGMA foreign_key_check').fetchall() == []


def test_allocator_cut_rolls_back_only_the_operation_savepoint(forest):
    path, values = forest
    with closing(sqlite3.connect(path)) as connection:
        configure(connection)
        connection.execute('BEGIN IMMEDIATE')
        connection.execute("UPDATE projects SET name='Retain caller writer'")

        def cut():
            raise RuntimeError('original allocator cut')

        with pytest.raises(RuntimeError, match='original allocator cut'):
            reserve_child_intent_transaction(connection, **values, failure_cut=cut)
        assert connection.in_transaction
        assert connection.execute('SELECT next_ordinal,reserved_count FROM physical_dataset_families').fetchone() == (2, 0)
        assert connection.execute('SELECT count(*) FROM physical_publication_intents').fetchone() == (0,)
        assert connection.execute('SELECT count(*) FROM physical_publication_targets').fetchone() == (0,)
        assert connection.execute('SELECT name FROM projects').fetchone() == ('Retain caller writer',)
        connection.commit()


@pytest.mark.parametrize('damage', ['schema', 'foreign_keys', 'synchronous', 'trusted_schema', 'no_transaction'])
def test_caller_lane_never_relaxes_native_snapshot_requirements(forest, damage):
    path, values = forest
    with closing(sqlite3.connect(path)) as connection:
        configure(connection)
        if damage in ('foreign_keys', 'synchronous', 'trusted_schema'):
            connection.execute('PRAGMA '+{'foreign_keys': 'foreign_keys=OFF',
                'synchronous': 'synchronous=NORMAL', 'trusted_schema': 'trusted_schema=ON'}[damage])
        if damage != 'no_transaction':
            connection.execute('BEGIN IMMEDIATE')
        if damage == 'schema':
            connection.execute('CREATE TABLE unregistered(value TEXT)')
        before = connection.total_changes
        with pytest.raises(ValueError, match='physical_root_native_transaction'):
            reserve_child_intent_transaction(connection, **values)
        assert connection.total_changes == before
        assert connection.execute('SELECT next_ordinal,reserved_count FROM physical_dataset_families').fetchone() == (2, 0)
        connection.rollback()


def test_original_candidate_entry_does_not_gain_live_wal_admission(forest):
    path, values = forest
    with closing(sqlite3.connect(path)) as connection:
        configure(connection)
        with pytest.raises(ValueError, match='forest_native_wal_not_admitted'):
            reserve_child_intent(connection, **values)
        assert not connection.in_transaction
        assert connection.execute('SELECT count(*) FROM physical_publication_targets').fetchone() == (0,)
