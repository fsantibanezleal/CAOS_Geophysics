"""Linux-local async all-writer lease on an initialized, immutable lock file.

Initialization/maintenance is separate. Normal acquisition never creates or
replaces the file. No lease expiry, shared-to-exclusive upgrade or inherited
descriptor is permitted. This mechanism alone cannot exclude nonparticipants.
"""

import asyncio
from contextlib import asynccontextmanager
from contextvars import ContextVar
import os
import stat
import time

from app.physical_contract import require
from app.physical_posix import PrivateFiles


_held = ContextVar("physical_writer_lease", default=None)


class WriterLeases:
    def __init__(self, root, *, device, inode, uid):
        self.files = PrivateFiles(root)
        self.identity = device, inode
        self.uid = uid
        self.pid = os.getpid()

    def _open(self):
        require(os.getpid() == self.pid, "physical_fork_unsupported")
        descriptor = os.open(".physical-writers.lock", os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=self.files.fd)
        try:
            self._check(descriptor)
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def _check(self, descriptor):
        self.files.check_root()
        info = os.fstat(descriptor)
        current = os.stat(".physical-writers.lock", dir_fd=self.files.fd, follow_symlinks=False)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size == 1
                and stat.S_IMODE(info.st_mode) == 0o600 and info.st_uid == self.uid
                and (info.st_dev, info.st_ino) == self.identity == (current.st_dev, current.st_ino)
                and os.pread(descriptor, 2, 0) == b"\0" and not os.get_inheritable(descriptor),
                "physical_lock_identity")

    @asynccontextmanager
    async def acquire(self, *, exclusive=False, timeout=30):
        import fcntl
        require(type(exclusive) is bool and type(timeout) in (int, float) and 0 <= timeout <= 30,
                "physical_lease_options")
        task = asyncio.current_task()
        require(task is not None and os.getpid() == self.pid, "physical_lease_task")
        held = _held.get()
        if held is not None and held[0] is task:
            require(held[1] is self and not exclusive and not held[3], "physical_lease_upgrade_or_reentry")
            self._check(held[2])
            yield
            return
        descriptor = self._open()
        acquired, token = False, None
        deadline = time.monotonic() + timeout
        try:
            while True:
                self._check(descriptor)
                try:
                    fcntl.flock(descriptor, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
                    acquired = True
                    break
                except BlockingIOError:
                    require(time.monotonic() < deadline, "physical_writer_busy")
                    await asyncio.sleep(min(0.01, max(0, deadline - time.monotonic())))
            self._check(descriptor)
            token = _held.set((task, self, descriptor, exclusive))
            yield
        finally:
            if token is not None:
                _held.reset(token)
            if acquired:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def close(self):
        require(_held.get() is None or _held.get()[1] is not self, "physical_lease_still_held")
        self.files.close()
