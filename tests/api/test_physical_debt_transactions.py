"""Actual caller-WAL retirement; authored custody is not a scientific receipt."""

import asyncio
from contextlib import closing
import copy
import sqlite3

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.physical_async_sql import run_native_transaction
from app.physical_debt import retire_failed_job, retire_failed_job_transaction
from app.physical_forest import reserve_child_intent
from tests.api.test_physical_debt import terminal
from tests.api.test_physical_forest import forest as forest
from tests.api.test_physical_successor import successor as successor


def configure(connection):
    assert connection.execute('PRAGMA journal_mode=WAL').fetchone() == ('wal',)
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA synchronous=FULL')
    connection.execute('PRAGMA trusted_schema=OFF')


def prepare(forest):
    path, values = forest
    with closing(sqlite3.connect(path, isolation_level=None)) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        reserve_child_intent(connection, **values)
    return path, values


def pending(connection):
    connection.execute('BEGIN IMMEDIATE')
    connection.execute("UPDATE projects SET name='Unrelated caller change'")


def summary(connection):
    return (
        connection.execute('SELECT state,result_key FROM processing_jobs').fetchone(),
        connection.execute('SELECT count(*) FROM physical_publication_intents').fetchone(),
        connection.execute('SELECT next_ordinal,reserved_count FROM physical_dataset_families').fetchone(),
        connection.execute('SELECT sum(charged_bytes) FROM physical_custody_batches').fetchone(),
    )


@pytest.mark.parametrize('commit', [False, True])
@pytest.mark.parametrize('installed_count', [0, 1, 2])
def test_terminal_visibility_and_copy_charge_belong_to_caller(forest, commit, installed_count):
    path, values = prepare(forest)
    with closing(sqlite3.connect(path)) as writer, closing(sqlite3.connect(path)) as reader:
        configure(writer)
        pending(writer)
        original = summary(reader)
        copies = values['targets'][:installed_count]
        retire_failed_job_transaction(writer, **terminal(values, copies))
        assert writer.in_transaction
        assert summary(reader) == original
        expected = (('failed', None), (0,), (3, 0), (20+sum(v['bytes'] for v in copies),))
        assert summary(writer) == expected
        assert writer.execute('SELECT count(*) FROM physical_dataset_productions').fetchone() == (0,)
        assert writer.execute('SELECT count(*) FROM observation_datasets').fetchone() == (1,)
        assert writer.execute('PRAGMA foreign_key_check').fetchall() == []
        if commit:
            writer.commit()
        else:
            writer.rollback()
        assert summary(reader) == (expected if commit else original)
        assert reader.execute('SELECT name FROM projects').fetchone() == (
            'Unrelated caller change' if commit else 'Survey',)


@pytest.mark.parametrize('cut', ['debt', 'terminal'])
def test_failure_cut_preserves_caller_and_original_liability(forest, cut):
    path, values = prepare(forest)
    with closing(sqlite3.connect(path)) as writer:
        configure(writer)
        pending(writer)
        original = summary(writer)

        def fail(point):
            if point == cut:
                raise RuntimeError('terminal failure cut')

        with pytest.raises(RuntimeError, match='terminal failure cut'):
            retire_failed_job_transaction(writer, **terminal(values, values['targets']), failure_cut=fail)
        assert writer.in_transaction and summary(writer) == original
        assert writer.execute('SELECT name FROM projects').fetchone() == ('Unrelated caller change',)
        assert writer.execute('SELECT count(*) FROM physical_publication_targets').fetchone() == (2,)
        writer.commit()


@pytest.mark.parametrize('damage', ['schema', 'foreign_keys', 'synchronous', 'trusted_schema',
                                  'no_transaction', 'row_factory', 'text_factory'])
def test_invalid_native_boundary_refuses_before_changes(forest, damage):
    path, values = prepare(forest)
    with closing(sqlite3.connect(path)) as writer:
        configure(writer)
        if damage in ('foreign_keys', 'synchronous', 'trusted_schema'):
            writer.execute('PRAGMA '+{'foreign_keys': 'foreign_keys=OFF',
                'synchronous': 'synchronous=NORMAL', 'trusted_schema': 'trusted_schema=ON'}[damage])
        if damage != 'no_transaction':
            writer.execute('BEGIN IMMEDIATE')
        if damage == 'schema':
            writer.execute('CREATE TABLE unregistered(value TEXT)')
        if damage == 'row_factory':
            writer.row_factory = sqlite3.Row
        if damage == 'text_factory':
            writer.text_factory = bytes
        before = writer.total_changes
        with pytest.raises(ValueError, match='physical_root_native_transaction'):
            retire_failed_job_transaction(writer, **terminal(values, []))
        assert writer.total_changes == before
        writer.rollback()


@pytest.mark.parametrize('damage', ['foreign_owner', 'copy_hash', 'duplicate_copy', 'stage_charge'])
def test_foreign_or_unknown_copy_keeps_custody(forest, damage):
    path, values = prepare(forest)
    request = terminal(values, copy.deepcopy(values['targets']))
    if damage == 'foreign_owner':
        request['owner_id'] = values['child_dataset_id']
    if damage == 'copy_hash':
        request['installed_targets'][0]['sha256'] = 'a'*64
    if damage == 'duplicate_copy':
        request['installed_targets'][1] = request['installed_targets'][0]
    with closing(sqlite3.connect(path)) as writer:
        configure(writer)
        pending(writer)
        if damage == 'stage_charge':
            writer.execute('UPDATE physical_custody_batches SET charged_bytes=0')
        original = summary(writer)
        with pytest.raises(ValueError):
            retire_failed_job_transaction(writer, **request)
        assert writer.in_transaction and summary(writer) == original
        assert writer.execute('SELECT permanent_reservation_bytes FROM physical_job_controls').fetchone()[0] > 0
        writer.rollback()


def test_original_entry_does_not_gain_wal_admission(forest):
    path, values = prepare(forest)
    with closing(sqlite3.connect(path)) as writer:
        configure(writer)
        with pytest.raises(ValueError, match='physical_native_wal_not_admitted'):
            retire_failed_job(writer, **terminal(values, []))
        assert not writer.in_transaction


@pytest.mark.parametrize('commit', [False, True])
def test_async_terminal_uses_original_session_transaction(forest, commit):
    path, values = prepare(forest)
    with closing(sqlite3.connect(path)) as connection:
        configure(connection)
        original = summary(connection)

    async def scenario():
        engine = create_async_engine('sqlite+aiosqlite:///'+path.as_posix())

        @event.listens_for(engine.sync_engine, 'connect')
        def native(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA synchronous=FULL')
            connection.execute('PRAGMA trusted_schema=OFF')

        try:
            async with async_sessionmaker(engine)() as session:
                await session.execute(text('BEGIN IMMEDIATE'))
                await session.execute(text("UPDATE projects SET name='Unrelated caller change'"))
                await run_native_transaction(session, 'retire_failed_job_transaction',
                    **terminal(values, values['targets']))
                assert session.in_transaction()
                assert (await session.execute(text('SELECT state FROM processing_jobs'))).scalar_one() == 'failed'
                with closing(sqlite3.connect(path)) as reader:
                    assert summary(reader) == original
                if commit:
                    await session.commit()
                else:
                    await session.rollback()
            with closing(sqlite3.connect(path)) as reader:
                assert summary(reader) == ((('failed', None), (0,), (3, 0), (40,)) if commit else original)
        finally:
            await engine.dispose()

    asyncio.run(scenario())
