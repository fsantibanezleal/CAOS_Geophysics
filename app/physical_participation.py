"""Fixed writer participation before authentication, SQL and streamed bodies.

Assembly is explicit. No live configuration, lock creation or migration occurs
here. All processing/recovery entry points must use these wrappers. Exclusive
requests also hold the original worker's exact initialized singleton lock, so
an older active worker refuses deletion rather than being silently ignored.
"""

from contextlib import asynccontextmanager
from contextvars import ContextVar
import asyncio
import os
from pathlib import Path
import stat

from app.physical_contract import require
from app.physical_leases import WriterLeases

_worker_held = ContextVar('physical_worker_exclusion', default=None)


class WorkerExclusion:
    def __init__(self, leases, *, device, inode, uid):
        require(isinstance(leases, WriterLeases), 'physical_native_writer_lease')
        self.leases = leases
        self.identity = device, inode
        self.uid = uid

    def _check(self, fd):
        self.leases.files.check_root()
        info = os.fstat(fd)
        current = os.stat('.processing-worker.lock', dir_fd=self.leases.files.fd, follow_symlinks=False)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size == 1 and
                stat.S_IMODE(info.st_mode) == 0o600 and info.st_uid == self.uid and
                (info.st_dev, info.st_ino) == self.identity == (current.st_dev, current.st_ino) and
                os.pread(fd, 2, 0) == b'0' and not os.get_inheritable(fd), 'physical_worker_lock_identity')

    @asynccontextmanager
    async def acquire(self):
        import fcntl
        self.leases.require_held(exclusive=True)
        require(_worker_held.get() is None, 'physical_worker_lock_reentry')
        fd = os.open('.processing-worker.lock', os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=self.leases.files.fd)
        token = None
        acquired = False
        try:
            self._check(fd)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except BlockingIOError:
                raise ValueError('physical_worker_busy') from None
            self._check(fd)
            token = _worker_held.set((asyncio.current_task(), self, fd))
            yield
        finally:
            if token is not None:
                _worker_held.reset(token)
            if acquired:
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def require_held(self):
        self.leases.require_held(exclusive=True)
        held = _worker_held.get()
        require(held is not None and held[0] is asyncio.current_task() and held[1] is self,
                'physical_worker_exclusion_required')
        self._check(held[2])


class WriterParticipation:
    """Pure ASGI: no new task loses the same-task lease authority.

    The context covers the final send and disconnect/cancellation unwinding,
    not merely construction of a response or an export generator.
    """
    def __init__(self, app, *, leases, worker_exclusion):
        require(isinstance(leases, WriterLeases) and isinstance(worker_exclusion, WorkerExclusion) and
                worker_exclusion.leases is leases, 'physical_participation_identity')
        self.app = app
        self.leases = leases
        self.worker_exclusion = worker_exclusion

    async def __call__(self, scope, receive, send):
        if scope['type'] not in ('http', 'websocket'):
            return await self.app(scope, receive, send)
        exclusive = scope['type'] == 'http' and scope['method'] == 'DELETE'
        lease = self.leases.acquire(exclusive=exclusive)
        # Catch acquisition only. Never replace an already started downstream
        # response, suppress application errors or claim its rollback completed.
        try:
            await lease.__aenter__()
        except (ValueError, OSError):
            return await self._refuse(scope, send)
        worker = None
        try:
            if exclusive:
                worker = self.worker_exclusion.acquire()
                try:
                    await worker.__aenter__()
                except (ValueError, OSError):
                    worker = None
                    return await self._refuse(scope, send)
            await self.app(scope, receive, send)
        finally:
            try:
                if worker is not None:
                    await worker.__aexit__(None, None, None)
            finally:
                await lease.__aexit__(None, None, None)

    @staticmethod
    async def _refuse(scope, send):
        if scope['type'] == 'websocket':
            return await send(dict(type='websocket.close', code=1013))
        body = b'{"code":"physical_writer_busy","message":"Private writer exclusion is unavailable; no mutation was admitted"}'
        await send(dict(type='http.response.start', status=409, headers=[(b'content-type', b'application/json')]))
        await send(dict(type='http.response.body', body=body))


def install_participation(app, leases, worker_exclusion, *, approved_installations):
    """Install before serving; registry comes from the fixed operator authority."""
    from app.profile_archive_delete import ProfileArchiveDeletion
    from starlette.middleware.base import BaseHTTPMiddleware
    require(app.middleware_stack is None and not hasattr(app.state, 'physical_writer_leases'),
            'physical_participation_already_serving')
    require(not any(issubclass(item.cls, BaseHTTPMiddleware) for item in app.user_middleware),
            'physical_task_splitting_middleware')
    participant = ProfileArchiveDeletion(leases, worker_exclusion=worker_exclusion,
                                       approved_installations=approved_installations)
    app.state.physical_writer_leases = leases
    app.state.profile_archive_deletion = participant
    app.add_middleware(WriterParticipation, leases=leases, worker_exclusion=worker_exclusion)


async def run_one_participating(settings, leases, *, poll_interval=0.05):
    """Lease includes claim, actual child lifetime, publication and cleanup."""
    from app.worker import run_one
    require(isinstance(leases, WriterLeases) and Path(settings.data_dir) == leases.files.root_path,
            'physical_worker_root_binding')
    async with leases.acquire():
        return await run_one(settings, poll_interval=poll_interval)


async def recover_profile_participating(settings, identifier, worker_exclusion):
    """Original exact recovery under both locks; never another recovery engine."""
    from app.profile_linux_recovery import recover_job
    require(isinstance(worker_exclusion, WorkerExclusion) and
            Path(settings.data_dir) == worker_exclusion.leases.files.root_path, 'physical_recovery_root_binding')
    async with worker_exclusion.leases.acquire(exclusive=True):
        async with worker_exclusion.acquire():
            return await recover_job(settings, identifier)
