"""Actual fresh SQL/classifier, portable guards; no native admission claim."""
import asyncio
from contextlib import closing
import json
import sqlite3
from types import SimpleNamespace

import pytest

from app.physical_project_delete import PhysicalProjectDeletion
from app.physical_startup import audit_startup_participating
from tests.api.test_physical_async_sql import engine_at
from tests.api.test_physical_classifier import CensusFiles
from tests.api.test_physical_deleted_inventory import case,POLICY
from tests.api.test_physical_participation import TransportLease,TransportWorker
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


def startup_engine(path,*,wal=True):
    from sqlalchemy import event
    engine=engine_at(path)
    @event.listens_for(engine.sync_engine,'connect')
    def configure(connection,_):
        cursor=connection.cursor()
        try:
            if wal:
                cursor.execute('PRAGMA journal_mode=WAL')
                assert cursor.fetchone()==('wal',)
            cursor.execute('PRAGMA synchronous=FULL')
            cursor.execute('PRAGMA trusted_schema=OFF')
        finally: cursor.close()
    return engine


def assembly(root_case):
    path,files,*_=root_case
    leases=TransportLease()
    census=CensusFiles(files);census.root_path=files.root
    leases.files=census
    worker=TransportWorker(leases)
    class BoundFixture(PhysicalProjectDeletion):
        """Only this test replaces native constructor/lock checks."""
        def check(self,settings):
            self.leases.require_held(exclusive=True)
            assert self.worker.held and settings.data_dir==self.leases.files.root_path
    participant=object.__new__(BoundFixture)
    participant.leases,participant.worker=leases,worker
    participant.source_policy=POLICY
    participant.registration=json.dumps(dict(approved_manifests={},approved_installations={},native_metadata={})).encode()
    return SimpleNamespace(data_dir=files.root,database_path=path),participant


@pytest.mark.parametrize('prepared',[False,True])
def test_fresh_whole_snapshot_is_read_only_and_not_lasting_admission(root_case,prepared):
    from sqlalchemy.ext.asyncio import async_sessionmaker
    if not prepared: case(root_case)
    settings,participant=assembly(root_case)
    path=root_case[0]
    with closing(sqlite3.connect(path)) as db:
        before=db.execute('SELECT * FROM projects').fetchall()
    async def run():
        engine=startup_engine(path)
        try:
            result=await audit_startup_participating(settings,async_sessionmaker(engine),participant)
            assert result.runtime is False
            assert result.classification==('prepared_uncommitted' if prepared else 'coherent_committed'),result.reason
            assert not participant.leases.held and not participant.worker.held
            return result
        finally: await engine.dispose()
    result=asyncio.run(run())
    assert result.inventory_sha256
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('SELECT * FROM projects').fetchall()==before
        assert db.execute('SELECT version_num FROM alembic_version').fetchall()==[('0005_physical_forest',)]


@pytest.mark.parametrize('damage',['unknown','foreign-database','foreign-root','busy','unregistered','non-wal'])
def test_startup_refusal_preserves_all_rows_and_originals(root_case,damage):
    from sqlalchemy.ext.asyncio import async_sessionmaker
    case(root_case)
    settings,participant=assembly(root_case)
    if damage=='unknown': (settings.data_dir/'unknown').write_bytes(b'keep')
    if damage=='foreign-database': settings.database_path=settings.database_path.with_name('unopened.sqlite')
    if damage=='foreign-root': settings.data_dir=settings.data_dir/'foreign'
    if damage=='busy': participant.worker.busy=True
    if damage=='unregistered': participant=object()
    original=root_case[1].root
    before={p.relative_to(original).as_posix():p.read_bytes() for p in original.rglob('*') if p.is_file()}
    async def run():
        engine=startup_engine(root_case[0],wal=damage!='non-wal')
        try:
            with pytest.raises((ValueError,AssertionError)):
                await audit_startup_participating(settings,async_sessionmaker(engine),participant)
        finally: await engine.dispose()
    asyncio.run(run())
    assert not root_case[0].with_name('unopened.sqlite').exists()
    assert before=={p.relative_to(original).as_posix():p.read_bytes() for p in original.rglob('*') if p.is_file()}


def test_repeated_cancel_cannot_release_guard_before_transaction_and_session_settle(root_case,monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker
    import app.physical_startup as startup
    case(root_case)
    settings,participant=assembly(root_case)
    async def run():
        engine=startup_engine(root_case[0])
        started,finish=asyncio.Event(),asyncio.Event()
        original=startup.run_native_transaction
        async def delayed(session,*args,**kwargs):
            assert session.in_transaction() and participant.leases.held and participant.worker.held
            started.set()
            await finish.wait()
            return await original(session,*args,**kwargs)
        monkeypatch.setattr(startup,'run_native_transaction',delayed)
        try:
            task=asyncio.create_task(audit_startup_participating(settings,async_sessionmaker(engine),participant))
            await started.wait()
            task.cancel();await asyncio.sleep(.01);task.cancel();await asyncio.sleep(.01)
            assert not task.done() and participant.leases.held and participant.worker.held
            finish.set()
            with pytest.raises(asyncio.CancelledError): await task
            assert not participant.leases.held and not participant.worker.held
            assert not root_case[0].with_name(root_case[0].name+'-journal').exists()
        finally:
            finish.set()
            await engine.dispose()
    asyncio.run(run())
