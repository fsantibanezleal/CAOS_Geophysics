"""Explicit portable owner lock/file transport. No Linux mode/FD proof claimed."""
import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
from types import SimpleNamespace

import app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.magnetic_custody_owner import MagneticCustodyOwner
from app.magnetic_line_survey_models import SurveyDatasetAttempt
from app.models import AccountUsage
from app.processing_storage import account_derived_usage


class Leases:
    def __init__(self, root):
        self.files = Files(root)
        self.tasks = {}

    @asynccontextmanager
    async def acquire(self, *, exclusive=False):
        task = asyncio.current_task()
        self.tasks[task] = self.tasks.get(task, 0) + 1
        try:
            yield
        finally:
            self.tasks[task] -= 1
            if not self.tasks[task]:
                del self.tasks[task]

    def require_held(self, *, exclusive=False):
        assert asyncio.current_task() in self.tasks


class Worker:
    def __init__(self, leases):
        self.leases, self.task = leases, None

    @asynccontextmanager
    async def acquire_processing(self):
        self.leases.require_held()
        assert self.task is None
        self.task = asyncio.current_task()
        try:
            yield
        finally:
            self.task = None

    def require_processing_held(self):
        assert self.task is asyncio.current_task()

    def require_held(self):
        self.require_processing_held()


class Files:
    def __init__(self, root):
        self.root_path = root

    def path(self, key):
        path = self.root_path / key
        assert path.is_relative_to(self.root_path)
        for ancestor in (path, *path.parents):
            assert not ancestor.is_symlink() and not ancestor.is_junction()
            if ancestor == self.root_path:
                break
        return path

    def create_directory(self, key, *, exist_ok=False):
        self.path(key).mkdir(mode=0o700, exist_ok=exist_ok)

    def private_directory_identity(self, key):
        path = self.path(key)
        assert path.is_dir()
        info = path.stat()
        return dict(device=info.st_dev, inode=info.st_ino)

    def verify_directory(self, key, *, expected_files):
        assert set(self.path(key).iterdir()) == {self.path(key) / name for name in expected_files}

    def names(self, key, *, limit):
        names = [path.name for path in self.path(key).iterdir()]
        assert len(names) <= limit
        return names

    def write_new(self, key, raw, *, cap):
        assert len(raw) <= cap
        fd = os.open(self.path(key), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        assert self.path(key).read_bytes() == raw


def bind_sessions(sessions, root):
    source = Path(os.environ["GEOPHYSICS_MAGNETIC_OWNER_ASSEMBLY_SOURCE"])
    if str(source / "app") not in app.__path__:
        app.__path__.append(str(source / "app"))
    from app.physical_assembly import PhysicalAssembly
    physical = object.__new__(PhysicalAssembly)
    physical.leases = Leases(root)
    physical.worker = Worker(physical.leases)

    async def base_charge(session, owner_id):
        usage = await session.get(AccountUsage, owner_id)
        assert usage is not None
        return usage.raw_bytes + await account_derived_usage(session, owner_id)

    async def device_charge(session):
        rows = (await session.execute(select(SurveyDatasetAttempt))).scalars().all()
        return sum(row.reservation_bytes for row in rows if row.state != "published")

    owner = MagneticCustodyOwner(physical, base_charge=base_charge, device_charge=device_charge)

    class HeldSession(AsyncSession):
        async def __aenter__(self):
            self.test_guard = physical.leases.acquire()
            await self.test_guard.__aenter__()
            return await super().__aenter__()

        async def __aexit__(self, *args):
            try:
                return await super().__aexit__(*args)
            finally:
                await self.test_guard.__aexit__(*args)

    sessions.class_ = HeldSession
    sessions.configure(info={"physical_assembly":physical})
    owner.bind_sessions(sessions)
    return SimpleNamespace(owner=owner, physical=physical)
