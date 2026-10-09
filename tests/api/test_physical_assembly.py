"""Actual optional server/SQL assembly; portable locks are explicit test transport."""

import asyncio
from contextlib import asynccontextmanager, closing
import json
import sqlite3
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.physical_assembly import PhysicalAssembly, run_forever_participating
from app.physical_contract import canonical
from app.physical_project_delete import PhysicalProjectDeletion
from app.server import create_app
from tests.api.test_physical_deleted_inventory import case, POLICY
from tests.api.test_physical_participation import TransportWorker
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_startup import assembly
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


def bound_fixture(root_case, monkeypatch):
    """Only fixture constructors/locks; actual server, WAL, classifier and auth."""
    _, existing = assembly(root_case)
    settings = Settings(data_dir=root_case[1].root, db_path=root_case[0],
        auth_secret='isolated-fixture-secret-more-than-thirty-two-characters',
        public_origin='http://testserver', cookie_secure=False, auth_mode='local')

    class FixtureParticipant(PhysicalProjectDeletion):
        def __init__(self, leases, worker_exclusion, **registry):
            self.leases, self.worker = leases, worker_exclusion
            self.source_policy = registry.pop('source_policy_sha256')
            self.registration = canonical(registry)

        def check(self, settings):
            self.leases.require_held(exclusive=True)
            assert self.worker.held and settings.data_dir == self.leases.files.root_path

    class FixtureWorker(TransportWorker):
        def require_held(self):
            self.leases.require_held(exclusive=True)
            assert self.held

        def require_processing_held(self):
            self.leases.require_held()
            assert self.held and self.task is asyncio.current_task()

        @asynccontextmanager
        async def acquire_processing(self):
            self.leases.require_held()
            assert not self.held
            self.held = True
            self.task = asyncio.current_task()
            try:
                yield
            finally:
                self.held = False

    worker = FixtureWorker(existing.leases)
    registry = json.loads(existing.registration)
    participant = FixtureParticipant(existing.leases, worker,
        source_policy_sha256=POLICY, **registry)
    physical = object.__new__(PhysicalAssembly)
    physical.leases, physical.worker, physical.participant = existing.leases, worker, participant
    monkeypatch.setattr('app.physical_project_delete.PhysicalProjectDeletion', FixtureParticipant)
    return settings, physical


def test_optional_create_app_performs_full_wal_reconcile_and_local_auth_under_outer_lease(root_case, monkeypatch):
    from fastapi_users.password import PasswordHelper
    from uuid import uuid4
    case(root_case)
    settings, physical = bound_fixture(root_case, monkeypatch)
    password = 'correct horse battery staple'
    other = str(uuid4())
    with closing(sqlite3.connect(settings.database_path)) as connection:
        connection.execute('INSERT INTO user VALUES (?,?,?,1,0,0)',
            (other, 'actual-optional-assembly@example.org', PasswordHelper().hash(password)))
        connection.commit()
    messages = []

    async def mail(*args):
        messages.append(args)

    app = create_app(settings, mail, physical=physical)
    assert app.state.physical_assembly is physical
    assert app.user_middleware[0].cls.__name__ == 'WriterParticipation'

    @app.get('/api/fixture-held')
    async def held():
        physical.leases.require_held()
        return dict(same_task=True)

    with TestClient(app) as client:
        assert client.get('/api/fixture-held').json() == {'same_task': True}
        token = client.get('/api/auth/csrf').json()['csrf_token']
        assert client.get('/api/auth/config').json() == dict(
            mode='local', registration_enabled=False, mail_flows_enabled=False)
        response = client.post('/api/auth/cookie/login',
            data=dict(username='actual-optional-assembly@example.org', password=password),
            headers={'Origin': 'http://testserver', 'X-CSRF-Token': token})
        assert response.status_code == 204, response.text
        assert client.get('/api/auth/me').json()['id'] == other
        assert client.get(f"/api/projects/{root_case[2]['project_id']}").status_code == 404
        assert not physical.leases.held and not physical.worker.held
    assert messages == []
    assert ('enter', True) in physical.leases.events
    with closing(sqlite3.connect(settings.database_path)) as connection:
        assert connection.execute('SELECT version_num FROM alembic_version').fetchall() == [('0005_physical_forest',)]
        assert connection.execute('SELECT count(*) FROM user').fetchone() == (2,)
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []


@pytest.mark.parametrize('damage', ['unknown', 'prepared'])
def test_normal_startup_refuses_unknown_or_uncommitted_root_without_legacy_mutation(root_case, monkeypatch, damage):
    if damage == 'unknown':
        case(root_case)
        (root_case[1].root / 'unknown-preserved').write_bytes(b'keep unchanged')
    settings, physical = bound_fixture(root_case, monkeypatch)
    before = {p.relative_to(settings.data_dir).as_posix(): p.read_bytes()
              for p in settings.data_dir.rglob('*') if p.is_file()}
    with closing(sqlite3.connect(settings.database_path)) as connection:
        rows = connection.execute('SELECT * FROM physical_custody_batches').fetchall()
    with pytest.raises(ValueError, match='physical_startup_' + ('inconsistent' if damage == 'unknown' else 'recovery_required')):
        with TestClient(create_app(settings, physical=physical)):
            raise AssertionError('Unresolved startup served a request')
    assert before == {p.relative_to(settings.data_dir).as_posix(): p.read_bytes()
                      for p in settings.data_dir.rglob('*') if p.is_file()}
    with closing(sqlite3.connect(settings.database_path)) as connection:
        assert connection.execute('SELECT * FROM physical_custody_batches').fetchall() == rows
    assert not physical.leases.held and not physical.worker.held


def test_unbound_operator_object_is_refused_before_engine_open(root_case):
    settings = Settings(data_dir=root_case[1].root,
        db_path=root_case[0].with_name('must-not-open.sqlite3'),
        auth_secret='isolated-fixture-secret-more-than-thirty-two-characters',
        public_origin='http://testserver', cookie_secure=False)
    with pytest.raises(ValueError, match='physical_operator_assembly_required'):
        create_app(settings, physical=object())
    assert not settings.database_path.exists()


def test_forever_worker_keeps_claim_cleanup_guard_through_repeated_stop(root_case, monkeypatch):
    case(root_case)
    settings, physical = bound_fixture(root_case, monkeypatch)

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        trace = []

        async def claim(sessions, identifier):
            physical.leases.require_held()
            physical.worker.require_processing_held()
            trace.append('original-claim')
            return SimpleNamespace(id='fixture-lifetime-only')

        async def execute(settings, sessions, job, interval):
            physical.leases.require_held()
            physical.worker.require_processing_held()
            trace.append('bounded-executor')
            entered.set()
            await release.wait()
            physical.leases.require_held()
            physical.worker.require_processing_held()
            trace.append('final-publication-cleanup')

        monkeypatch.setattr('app.worker._claim', claim)
        monkeypatch.setattr('app.worker._execute', execute)
        task = asyncio.create_task(run_forever_participating(settings, physical, poll_interval=.01))
        try:
            await asyncio.wait_for(entered.wait(), 5)
            task.cancel()
            await asyncio.sleep(.01)
            task.cancel()
            await asyncio.sleep(.01)
            assert not task.done() and physical.leases.held and physical.worker.held
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert trace == ['original-claim', 'bounded-executor', 'final-publication-cleanup']
        assert not physical.leases.held and not physical.worker.held

    asyncio.run(scenario())
