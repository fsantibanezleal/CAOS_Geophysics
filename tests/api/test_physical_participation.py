"""ASGI order/lifetime fixtures; actual kernel locks are a separate Linux drill."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.physical_leases import WriterLeases
from app.physical_participation import WriterParticipation, WorkerExclusion, run_one_participating


class TransportLease(WriterLeases):
    def __init__(self):
        self.events = []
        self.held = False
        self.task = None
        self.files = SimpleNamespace(root_path=Path('/private'))

    @asynccontextmanager
    async def acquire(self, *, exclusive=False):
        assert not self.held
        self.events.append(('enter', exclusive))
        self.held = True
        self.task = asyncio.current_task()
        try:
            yield
        finally:
            self.held = False
            self.events.append(('exit', exclusive))

    def require_held(self, *, exclusive=False):
        assert self.held and self.task is asyncio.current_task()
        if exclusive:
            assert self.events[-1] == ('enter', True)


class TransportWorker(WorkerExclusion):
    def __init__(self, leases, *, busy=False):
        self.leases = leases
        self.held = False
        self.busy = busy

    @asynccontextmanager
    async def acquire(self):
        self.leases.require_held(exclusive=True)
        if self.busy:
            raise ValueError('physical_worker_busy')
        self.held = True
        try:
            yield
        finally:
            self.held = False


@pytest.mark.parametrize('method', ['GET','POST','DELETE'])
def test_lease_precedes_handler_and_covers_last_stream_send(method):
    async def run():
        leases = TransportLease(); worker = TransportWorker(leases)
        events = []
        async def handler(scope, receive, send):
            leases.require_held(exclusive=method=='DELETE')
            assert worker.held == (method=='DELETE')
            events.append('auth-session-handler')
            await send(dict(type='http.response.start', status=200))
            await send(dict(type='http.response.body', body=b'first', more_body=True))
            await asyncio.sleep(0)
            await send(dict(type='http.response.body', body=b'last'))
        async def send(message):
            assert leases.held and leases.task is asyncio.current_task()
            events.append(message['type'])
        await WriterParticipation(handler,leases=leases,worker_exclusion=worker)(
            dict(type='http',method=method), None, send)
        assert leases.events==[('enter',method=='DELETE'),('exit',method=='DELETE')]
        assert events==['auth-session-handler','http.response.start','http.response.body','http.response.body']
        assert not worker.held
    asyncio.run(run())


def test_busy_original_worker_refuses_before_authentication_or_mutation():
    async def run():
        leases = TransportLease(); worker = TransportWorker(leases,busy=True)
        messages = []
        async def forbidden(*args):
            raise AssertionError('authentication/session accessed before exclusion')
        async def send(message): messages.append(message)
        await WriterParticipation(forbidden,leases=leases,worker_exclusion=worker)(
            dict(type='http',method='DELETE'), None, send)
        assert messages[0]['status']==409 and b'physical_writer_busy' in messages[1]['body']
        assert not leases.held
    asyncio.run(run())


@pytest.mark.parametrize('failure', ['disconnect','handler','cancel'])
def test_uncertain_handler_or_stream_does_not_leak_or_fabricate_response(failure):
    async def run():
        leases = TransportLease(); worker = TransportWorker(leases)
        calls = []
        async def handler(scope, receive, send):
            if failure=='handler': raise RuntimeError('original-error')
            if failure=='cancel': raise asyncio.CancelledError()
            await send(dict(type='http.response.start',status=200))
        async def send(message):
            calls.append(message)
            raise OSError('disconnected')
        error = RuntimeError if failure=='handler' else asyncio.CancelledError if failure=='cancel' else OSError
        with pytest.raises(error):
            await WriterParticipation(handler,leases=leases,worker_exclusion=worker)(
                dict(type='http',method='DELETE'), None, send)
        assert not leases.held and not worker.held
        assert len(calls)==(1 if failure=='disconnect' else 0)
    asyncio.run(run())


def test_existing_worker_wrapper_holds_lease_for_actual_executor_boundary(monkeypatch):
    async def run():
        leases = TransportLease()
        async def original(settings, *, poll_interval):
            leases.require_held()
            assert poll_interval==0.03
            await asyncio.sleep(0)
            leases.require_held()
            return 'terminal-job'
        monkeypatch.setattr('app.worker.run_one',original)
        result = await run_one_participating(SimpleNamespace(data_dir=Path('/private')),leases,poll_interval=0.03)
        assert result=='terminal-job' and not leases.held
        with pytest.raises(ValueError):
            await run_one_participating(SimpleNamespace(data_dir=Path('/foreign')),leases)
    asyncio.run(run())


def test_security_keeps_the_real_route_in_outer_task(harness):
    # Existing auth/CSRF/rate SQL still executes. This spy is explicitly not a
    # native lease, but will detect the former BaseHTTPMiddleware task split.
    from app.security import _SecurityGuard
    assert any(item.cls is _SecurityGuard for item in harness.app.user_middleware)
    outer_task = []
    route_task = []
    original = harness.app.middleware_stack
    async def spy(scope, receive, send):
        outer_task.append(asyncio.current_task())
        await original(scope, receive, send)
    @harness.app.get('/api/participation-task-probe')
    async def probe():
        route_task.append(asyncio.current_task())
        return {'held':True}
    harness.app.middleware_stack = spy
    assert harness.client.get('/api/participation-task-probe').json()=={'held':True}
    assert outer_task==route_task
