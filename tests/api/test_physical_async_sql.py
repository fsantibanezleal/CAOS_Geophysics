"""Actual SQLite transaction transport, not runtime/WAL admission."""

import asyncio
import sqlite3
import threading

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.physical_async_sql import run_native_transaction
from tests.api.test_physical_deleted_inventory import POLICY, case, deleted_case
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


def engine_at(path):
    engine = create_async_engine('sqlite+aiosqlite:///'+path.as_posix())
    @event.listens_for(engine.sync_engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    return engine


def test_native_projection_sees_original_session_uncommitted_rows_and_rollback(root_case):
    expected, _ = case(root_case)
    async def scenario():
        engine = engine_at(root_case[0])
        try:
            async with async_sessionmaker(engine)() as session:
                await session.execute(text('BEGIN IMMEDIATE'))
                await session.execute(text("UPDATE projects SET name='Pending same transaction'"))
                actual = await run_native_transaction(session, 'project_inventory',
                    owner_id=root_case[2]['owner_id'],project_id=root_case[2]['project_id'],
                    source_policy_sha256=POLICY,profile_records=[])
                assert actual == expected and session.in_transaction()
                with sqlite3.connect(root_case[0]) as independent:
                    assert independent.execute('SELECT name FROM projects').fetchone()[0] != 'Pending same transaction'
                assert (await session.execute(text('SELECT name FROM projects'))).scalar_one() == 'Pending same transaction'
                await session.rollback()
                assert (await session.execute(text('SELECT name FROM projects'))).scalar_one() != 'Pending same transaction'
        finally:
            await engine.dispose()
    asyncio.run(scenario())


@pytest.mark.parametrize('commit',[False,True])
def test_original_native_receipt_and_extension_share_caller_commit(root_case,commit):
    path,receipt_id,_ = deleted_case(root_case)
    with sqlite3.connect(path) as connection:
        original = connection.execute('SELECT tombstone_bytes FROM physical_deletion_extensions').fetchone()[0]
        connection.execute('DELETE FROM physical_deletion_extensions')
    import json
    inventory=json.loads(original)['physical_inventory']
    async def scenario():
        engine=engine_at(path)
        try:
            async with async_sessionmaker(engine)() as session:
                await session.execute(text('BEGIN IMMEDIATE'))
                observed=await run_native_transaction(session,'observe_receipt',receipt_id=receipt_id)
                assert observed['asset_manifest']['utf8'].startswith('[\n ')
                body=await run_native_transaction(session,'save_current_tombstone',receipt_id=receipt_id,
                    inventory=inventory,expected_source_policy_sha256=POLICY,approved_installations={})
                assert body==original and session.in_transaction()
                with sqlite3.connect(path) as independent:
                    assert independent.execute('SELECT count(*) FROM physical_deletion_extensions').fetchone()==(0,)
                if commit: await session.commit()
                else: await session.rollback()
            with sqlite3.connect(path) as independent:
                assert independent.execute('SELECT count(*) FROM physical_deletion_extensions').fetchone()==(int(commit),)
                assert independent.execute('PRAGMA foreign_key_check').fetchall()==[]
        finally:
            await engine.dispose()
    asyncio.run(scenario())


def test_unknown_operation_and_non_native_transaction_never_start_sql(tmp_path):
    async def scenario():
        engine=engine_at(tmp_path/'no-transaction.sqlite3')
        try:
            async with async_sessionmaker(engine)() as session:
                with pytest.raises(ValueError,match='physical_async_operation'):
                    await run_native_transaction(session,lambda _:None)
                assert not session.in_transaction()
                with pytest.raises(ValueError,match='physical_async_transaction'):
                    await run_native_transaction(session,'observe_receipt',receipt_id='not-admitted')
                assert not session.in_transaction()
                # SQLAlchemy autobegin on a SELECT is not native BEGIN IMMEDIATE.
                await session.execute(text('SELECT 1'))
                with pytest.raises(ValueError,match='physical_async_native_transaction'):
                    await run_native_transaction(session,'observe_receipt',receipt_id='not-admitted')
                await session.rollback()
        finally:
            await engine.dispose()
    asyncio.run(scenario())


def test_cancellation_drains_actual_native_thread_before_guard_release(tmp_path,monkeypatch):
    from app import physical_deleted_inventory
    entered,release=threading.Event(),threading.Event()
    completed=[]
    def held(connection,**_):
        entered.set()
        assert release.wait(5),'bounded test thread deadline'
        connection.execute("INSERT INTO proof VALUES('drained')")
        completed.append(True)
        return {}
    monkeypatch.setattr(physical_deleted_inventory,'observe_receipt',held)
    async def scenario():
        engine=engine_at(tmp_path/'drain.sqlite3')
        try:
            async with async_sessionmaker(engine)() as session:
                await session.execute(text('CREATE TABLE proof(value TEXT)'))
                await session.commit()
                await session.execute(text('BEGIN IMMEDIATE'))
                operation=asyncio.create_task(run_native_transaction(session,'observe_receipt',receipt_id='test'))
                try:
                    assert await asyncio.to_thread(entered.wait,3)
                    operation.cancel()
                    with pytest.raises(ValueError,match='physical_async_reentry'):
                        await run_native_transaction(session,'observe_receipt',receipt_id='test')
                    assert not operation.done() and not completed
                    operation.cancel()
                    await asyncio.sleep(0)
                    assert not operation.done() and not completed
                finally:
                    release.set()
                with pytest.raises(asyncio.CancelledError): await operation
                assert completed==[True] and session.in_transaction()
                assert (await session.execute(text('SELECT count(*) FROM proof'))).scalar_one()==1
                await session.rollback()
                assert (await session.execute(text('SELECT count(*) FROM proof'))).scalar_one()==0
        finally:
            release.set()
            await engine.dispose()
    asyncio.run(scenario())


def test_unflushed_original_orm_is_not_silently_omitted(root_case):
    from app.models import Project
    async def scenario():
        engine=engine_at(root_case[0])
        try:
            async with async_sessionmaker(engine)() as session:
                await session.execute(text('BEGIN IMMEDIATE'))
                project=await session.get(Project,root_case[2]['project_id'])
                project.name='Not flushed'
                with pytest.raises(ValueError,match='physical_async_unflushed_orm'):
                    await run_native_transaction(session,'project_inventory',
                        owner_id=project.owner_id,project_id=project.id,source_policy_sha256=POLICY,profile_records=[])
                assert session.in_transaction() and project in session.dirty
                await session.rollback()
        finally:
            await engine.dispose()
    asyncio.run(scenario())


def test_native_rejection_preserves_original_transaction_and_next_operation(root_case):
    path,receipt_id,_=deleted_case(root_case)
    async def scenario():
        engine=engine_at(path)
        try:
            async with async_sessionmaker(engine)() as session:
                await session.execute(text('BEGIN IMMEDIATE'))
                await session.execute(text('UPDATE account_usage SET raw_bytes=1'))
                with pytest.raises(ValueError,match='current_deletion_receipt_identity'):
                    await run_native_transaction(session,'observe_receipt',receipt_id='00000000-0000-4000-8000-000000000001')
                assert session.in_transaction()
                assert (await run_native_transaction(session,'observe_receipt',receipt_id=receipt_id))['id']==receipt_id
                assert (await session.execute(text('SELECT raw_bytes FROM account_usage'))).scalar_one()==1
                await session.rollback()
                assert (await session.execute(text('SELECT raw_bytes FROM account_usage'))).scalar_one()==0
        finally:
            await engine.dispose()
    asyncio.run(scenario())


def test_full_source_positive_classifier_uses_same_native_snapshot_without_mutation(root_case):
    from tests.api.test_physical_classifier import CensusFiles
    case(root_case)
    async def scenario():
        engine=engine_at(root_case[0])
        try:
            async with async_sessionmaker(engine)() as session:
                await session.execute(text('BEGIN IMMEDIATE'))
                changes=(await session.execute(text('SELECT total_changes()'))).scalar_one()
                result=await run_native_transaction(session,'classify_snapshot',files=CensusFiles(root_case[1]),
                    approved_manifests={},approved_installations={},native_metadata={},expected_source_policy_sha256=POLICY)
                assert result.classification=='coherent_committed',result.reason
                assert result.runtime is False and session.in_transaction()
                assert (await session.execute(text('SELECT total_changes()'))).scalar_one()==changes
                await session.rollback()
        finally:
            await engine.dispose()
    asyncio.run(scenario())
