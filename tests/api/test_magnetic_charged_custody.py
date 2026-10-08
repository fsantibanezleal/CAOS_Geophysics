"""Actual SQLite/held-thread controls; explicit portable locks, NOT OS proof."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import os
from types import SimpleNamespace
import threading
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import app
from app.config import Settings
from app.errors import ApiError
from app.magnetic_custody_owner import MagneticCustodyOwner, bounded_work, attempt_charge, SCHEMA, LIFETIME
from app.magnetic_line_survey_models import SurveyDatasetAttempt
from app.models import Base, User, Project, SourceRecord, RawAsset, ObservationDataset

# The old leaf consumes the reviewed existing assembly, never reimplements it.
# This source binding is a test dependency, not a product filesystem default.
assembly_source = Path(os.environ["GEOPHYSICS_MAGNETIC_OWNER_ASSEMBLY_SOURCE"])
app.__path__.append(str(assembly_source / "app"))
from app.physical_assembly import PhysicalAssembly  # noqa: E402


class TaskLease:
    def __init__(self, root):
        self.files = SimpleNamespace(root_path=root)
        self.task = None

    @asynccontextmanager
    async def acquire(self):
        assert self.task is None
        self.task = asyncio.current_task()
        try:
            yield
        finally:
            self.task = None

    def require_held(self, *, exclusive=False):
        assert self.task is asyncio.current_task()


class TaskWorker:
    def __init__(self, lease):
        self.lease, self.task = lease, None

    @asynccontextmanager
    async def acquire_processing(self):
        self.lease.require_held()
        assert self.task is None
        self.task = asyncio.current_task()
        try:
            yield
        finally:
            self.task = None

    def require_processing_held(self):
        self.lease.require_held()
        assert self.task is asyncio.current_task()


async def case(root):
    settings = Settings(data_dir=root, auth_secret="x"*40, public_origin="http://testserver", cookie_secure=False)
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    user = User(id=uuid4(), email="owned@example.org", hashed_password="not-auth-tested", is_active=True, is_verified=True)
    project, asset, source, dataset = (str(uuid4()) for _ in range(4))
    row = ObservationDataset(id=dataset, owner_id=user.id, project_id=project, raw_asset_id=asset,
        version=1, parser_version="mag-survey/v1:"+"a"*64, modality="magnetic_survey", row_count=288,
        raw_sha256="b"*64, sha256="a"*64, byte_count=10, storage_key=f"derived/{user.id}/{project}/datasets/{dataset}.json")
    async with sessions() as session:
        session.add_all([user, Project(id=project, owner_id=user.id, name="Portable custody control"),
            SourceRecord(id=source, owner_id=user.id, project_id=project, original_filename="control.csv",
                version=1, provider="Authored", rights_statement="Private", rights_decision="mirror",
                private_storage_permission="attested", declared_format="magnetic_csv", sha256="b"*64,
                expected_bytes=10, attribution="Authored control"),
            RawAsset(id=asset, owner_id=user.id, project_id=project, source_id=source, filename="control.csv",
                client_mime="text/csv", detected_format="magnetic_csv", byte_count=10, sha256="b"*64,
                storage_key=f"projects/{user.id}/{project}/{asset}", physical_metadata={}), row])
        await session.commit()
    physical = object.__new__(PhysicalAssembly)
    physical.leases = TaskLease(root)
    physical.worker = TaskWorker(physical.leases)

    async def base(session, owner):
        assert owner == user.id and session.in_transaction()
        return 20

    async def device(session):
        assert session.in_transaction()
        return 0

    owner = MagneticCustodyOwner(physical, base_charge=base, device_charge=device)
    sessions.configure(info={"magnetic_custody_owner":owner, "physical_assembly":physical})
    owner.test_sources = dict(dataset_id=dataset, dataset_sha256="a"*64, raw_asset_id=asset,
        raw_sha256="b"*64, raw_bytes=10, source_record_id=source,
        rights_decision="mirror", private_storage_permission="attested")
    return engine, sessions, settings, user, row, owner


def test_reservation_visible_to_independent_connection_before_any_directory(tmp_path):
    async def gate():
        engine, sessions, settings, user, dataset, owner = await case(tmp_path)
        try:
            async with sessions() as session, owner.lifetime(session, settings):
                row = await owner.reserve(session, settings, user, dataset, operation="import", sources=owner.test_sources, job_id=str(uuid4()))
                assert not (tmp_path / ".magnetic-custody").exists()
                async with sessions() as other:
                    persisted = await other.get(SurveyDatasetAttempt, row.id)
                    assert persisted.state == "reserved" and persisted.reservation_bytes == 512*1024**2
                    assert await attempt_charge(other, user.id) == 512*1024**2
                assert row.input_json["schema"] == SCHEMA
                with pytest.raises(ApiError, match="owner reconciliation"):
                    await owner.reserve(session, settings, user, dataset, operation="read", sources=owner.test_sources, job_id=str(uuid4()))
        finally:
            await engine.dispose()
    asyncio.run(gate())


@pytest.mark.parametrize("attack", ["quota", "device", "unbound"])
def test_refusal_has_no_stage_or_attempt(tmp_path, attack):
    async def gate():
        from dataclasses import replace
        engine, sessions, settings, user, dataset, owner = await case(tmp_path)
        try:
            if attack == "quota":
                settings = replace(settings, max_upload_bytes=1, account_quota_bytes=512*1024**2+19)
            if attack == "device":
                settings = replace(settings, worker_scratch_bytes=512*1024**2-1)
            async with sessions() as session, owner.lifetime(session, settings):
                if attack == "unbound":
                    session.info.pop("magnetic_custody_owner")
                with pytest.raises(ApiError):
                    await owner.reserve(session, settings, user, dataset, operation="import", sources=owner.test_sources, job_id=str(uuid4()))
                if attack == "unbound":
                    session.info["magnetic_custody_owner"] = owner
            async with sessions() as session:
                assert (await session.execute(select(SurveyDatasetAttempt))).scalars().all() == []
            assert not (tmp_path / ".magnetic-custody").exists()
        finally:
            await engine.dispose()
    asyncio.run(gate())


@pytest.mark.parametrize("terminal", ["failed", "publication_uncertain", "published", "forged_published"])
def test_unreleased_debt_and_closed_terminal_charge(tmp_path, terminal):
    async def gate():
        engine, sessions, settings, user, dataset, owner = await case(tmp_path)
        try:
            async with sessions() as session, owner.lifetime(session, settings):
                row = await owner.reserve(session, settings, user, dataset, operation="export", sources=owner.test_sources, job_id=str(uuid4()))
                row.state = "published" if terminal == "forged_published" else terminal
                if terminal == "published":
                    row.lifetime = dict(schema=LIFETIME, work_completed=True, scratch_removed=True, native_admission=False)
                await session.commit()
                if terminal == "forged_published":
                    with pytest.raises(ApiError):
                        await attempt_charge(session, user.id)
                else:
                    assert await attempt_charge(session, user.id) == (0 if terminal == "published" else 256*1024**2)
        finally:
            await engine.dispose()
    asyncio.run(gate())


@pytest.mark.parametrize("stop", ["timeout", "cancel"])
def test_actual_held_work_finishes_before_guards_release_even_repeated_cancel(tmp_path, stop):
    async def gate():
        engine, sessions, settings, _, _, owner = await case(tmp_path)
        started, release, finished = threading.Event(), threading.Event(), threading.Event()
        def held():
            started.set()
            assert release.wait(5)
            finished.set()
            return b"actual held worker"
        async def run():
            async with sessions() as session, owner.lifetime(session, settings):
                await bounded_work(held, timeout=0.02 if stop == "timeout" else 5)
        pending = asyncio.create_task(run())
        try:
            while not started.is_set():
                await asyncio.sleep(0.001)
            if stop == "cancel":
                pending.cancel()
            await asyncio.sleep(0.04)
            pending.cancel()  # second cancellation must not break final drain
            await asyncio.sleep(0.02)
            assert not pending.done() and not finished.is_set()
            assert owner.physical.worker.task is pending and owner.physical.leases.task is pending
            release.set()
            with pytest.raises((TimeoutError, asyncio.CancelledError)):
                await pending
            assert finished.is_set() and owner.physical.worker.task is None and owner.physical.leases.task is None
        finally:
            release.set()
            if not pending.done():
                await pending
            await engine.dispose()
    asyncio.run(gate())
