"""Real WAL root SQL on the original API session; not OS/science admission."""

import asyncio
from contextlib import closing
import sqlite3

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.physical_async_sql import run_native_transaction
from app.physical_contract import byte_sha
from app.physical_roots import prepare_root, publish_root
from tests.api.test_physical_roots import (
    install_fixture, publish_values, root_case as root_case,
)
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


def wal_at(path):
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute('PRAGMA journal_mode=WAL').fetchone() == ('wal',)
    engine = create_async_engine('sqlite+aiosqlite:///' + path.as_posix())

    @event.listens_for(engine.sync_engine, 'connect')
    def setup(connection, _):
        for pragma in ('foreign_keys=ON', 'synchronous=FULL', 'trusted_schema=OFF'):
            connection.execute('PRAGMA ' + pragma)

    return engine


@pytest.mark.parametrize('commit', [False, True])
def test_root_prepare_and_publish_share_original_wal_session(root_case, commit):
    path, files, values, body, original = root_case

    async def scenario():
        engine = wal_at(path)
        try:
            async with async_sessionmaker(engine)() as session:
                await session.execute(text('BEGIN IMMEDIATE'))
                await session.execute(text("UPDATE projects SET name='Original pending mutation'"))
                await run_native_transaction(session, 'prepare_root_transaction', files=files, **values)
                assert session.in_transaction()
                with closing(sqlite3.connect(path)) as reader:
                    assert reader.execute('SELECT count(*) FROM physical_publication_intents').fetchone() == (0,)
                install_fixture(files, values, body)
                result = await run_native_transaction(session, 'publish_root_transaction',
                    files=files, **publish_values(values))
                assert result == values['root_dataset_id'] and session.in_transaction()
                assert (await session.execute(text('SELECT count(*) FROM observation_datasets'))).scalar_one() == 1
                with closing(sqlite3.connect(path)) as reader:
                    assert reader.execute('SELECT count(*) FROM observation_datasets').fetchone() == (0,)
                if commit:
                    await session.commit()
                else:
                    await session.rollback()
            with closing(sqlite3.connect(path)) as reader:
                assert reader.execute('SELECT count(*) FROM observation_datasets').fetchone() == (int(commit),)
                assert reader.execute('SELECT count(*) FROM physical_publication_intents').fetchone() == (0,)
                assert reader.execute('PRAGMA foreign_key_check').fetchall() == []
                if commit:
                    assert reader.execute('SELECT sha256,byte_count,kind FROM observation_datasets').fetchone() == (
                        byte_sha(body), len(body), 'root')
                    assert reader.execute('SELECT state,charged_bytes FROM physical_custody_batches').fetchone() == (
                        'cleanup_pending', len(original) + len(body))
                else:
                    assert reader.execute('SELECT state FROM physical_custody_batches').fetchone() == ('sealed',)
            assert (files.root / f".job-staging/{values['root_dataset_id']}/input.json").read_bytes() == original
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize('cut', ['prepared', 'published'])
def test_root_operation_cut_rolls_back_only_its_savepoint(root_case, cut):
    path, files, values, body, _ = root_case

    def fail(point):
        if point == cut:
            raise RuntimeError('original_root_cut')

    async def scenario():
        engine = wal_at(path)
        try:
            async with async_sessionmaker(engine)() as session:
                await session.execute(text('BEGIN IMMEDIATE'))
                await session.execute(text("UPDATE projects SET name='Retained caller change'"))
                if cut == 'published':
                    await run_native_transaction(session, 'prepare_root_transaction', files=files, **values)
                    install_fixture(files, values, body)
                with pytest.raises(RuntimeError, match='original_root_cut'):
                    await run_native_transaction(session,
                        'prepare_root_transaction' if cut == 'prepared' else 'publish_root_transaction',
                        files=files, failure_cut=fail, **(values if cut == 'prepared' else publish_values(values)))
                assert session.in_transaction()
                assert (await session.execute(text('SELECT name FROM projects'))).scalar_one() == 'Retained caller change'
                assert (await session.execute(text('SELECT count(*) FROM observation_datasets'))).scalar_one() == 0
                assert (await session.execute(text('SELECT count(*) FROM physical_publication_intents'))).scalar_one() == int(cut == 'published')
                assert (await session.execute(text('SELECT state FROM physical_custody_batches'))).scalar_one() == 'sealed'
                await session.rollback()
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize('change', ['schema', 'foreign_keys', 'synchronous', 'trusted_schema', 'no_transaction'])
def test_root_native_lane_refuses_unbound_snapshot_without_mutation(root_case, change):
    from app.physical_roots import prepare_root_transaction
    path, files, values, _, _ = root_case
    with closing(sqlite3.connect(path)) as connection:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('PRAGMA trusted_schema=OFF')
        if change in ('foreign_keys', 'synchronous', 'trusted_schema'):
            pragma = {'foreign_keys': 'foreign_keys=OFF', 'synchronous': 'synchronous=NORMAL',
                      'trusted_schema': 'trusted_schema=ON'}[change]
            connection.execute('PRAGMA ' + pragma)
        if change != 'no_transaction':
            connection.execute('BEGIN IMMEDIATE')
        if change == 'schema':
            connection.execute('CREATE TABLE unregistered(value TEXT)')
        before = connection.total_changes
        with pytest.raises(ValueError, match='physical_root_native_transaction'):
            prepare_root_transaction(connection, files, **values)
        assert connection.total_changes == before
        assert connection.execute('SELECT count(*) FROM physical_dataset_families').fetchone() == (0,)
        assert connection.in_transaction == (change != 'no_transaction')
        connection.rollback()


def test_original_candidate_operations_still_refuse_wal(root_case):
    path, files, values, _, _ = root_case
    with closing(sqlite3.connect(path)) as connection:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA foreign_keys=ON')
        with pytest.raises(ValueError, match='physical_native_wal_not_admitted'):
            prepare_root(connection, files, **values)
        with pytest.raises(ValueError, match='physical_native_wal_not_admitted'):
            publish_root(connection, files, **publish_values(values))
        assert not connection.in_transaction
