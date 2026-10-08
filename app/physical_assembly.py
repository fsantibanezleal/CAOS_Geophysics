"""Explicit normal API/worker assembly from an already fixed operator binding.

No environment flag manufactures authority. No account, schema, data directory,
lock, runtime or service is created here. The unbound legacy assembly is intact.
"""

import asyncio
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.physical_contract import require
from app.physical_project_delete import PhysicalProjectDeletion
from app.physical_startup import audit_startup_participating


class PhysicalAssembly:
    def __init__(self, leases, worker_exclusion, *, source_policy_sha256,
                 approved_manifests, approved_installations, native_metadata):
        self.participant = PhysicalProjectDeletion(leases, worker_exclusion,
            source_policy_sha256=source_policy_sha256, approved_manifests=approved_manifests,
            approved_installations=approved_installations, native_metadata=native_metadata)
        self.leases, self.worker = leases, worker_exclusion

    def bind_engine(self, settings, engine):
        require(Path(settings.data_dir) == self.leases.files.root_path
                and engine.url.drivername == 'sqlite+aiosqlite'
                and engine.url.database is not None
                and Path(engine.url.database) == Path(settings.database_path),
                'physical_assembly_root_binding')

        @event.listens_for(engine.sync_engine, 'connect')
        def durability(connection, _):
            cursor = connection.cursor()
            try:
                # Connection-local configuration of the private selected engine;
                # startup independently reads it before any application writer.
                cursor.execute('PRAGMA synchronous=FULL')
                cursor.execute('PRAGMA trusted_schema=OFF')
            finally:
                cursor.close()

    def install(self, app, settings):
        from app.physical_participation import install_participation
        from app.physical_project_delete import install_project_deletion
        require(app.middleware_stack is None and not hasattr(app.state, 'physical_assembly'),
                'physical_assembly_already_serving')
        require(Path(settings.data_dir) == self.leases.files.root_path,
                'physical_assembly_root_binding')
        arguments = self.participant.arguments()
        install_participation(app, self.leases, self.worker,
            approved_installations=arguments['approved_installations'])
        install_project_deletion(app, source_policy_sha256=self.participant.source_policy,
            approved_manifests=arguments['approved_manifests'],
            approved_installations=arguments['approved_installations'],
            native_metadata=arguments['native_metadata'])
        app.state.physical_assembly = self
        self.bind_sessions(app.state.sessions)

    def bind_sessions(self, sessions):
        require(isinstance(sessions, async_sessionmaker), 'physical_session_factory')
        info = dict(sessions.kw.get('info', {}))
        require('physical_assembly' not in info, 'physical_session_already_bound')
        info['physical_assembly'] = self
        sessions.configure(info=info)

    async def derived_charge(self, session, owner_id):
        from app.physical_async_sql import run_native_transaction
        from app.profile_archive_custody import archive_inventory
        from app.profile_archive_delete import archive_relations, excluded_read
        self.leases.require_held()
        require(session.info.get('physical_assembly') is self, 'physical_session_binding')
        arguments = self.participant.arguments()
        relations, receipts = await archive_relations(session)
        records = await excluded_read(archive_inventory, self.leases.files, relations, receipts,
            approved_installations=arguments['approved_installations'])
        charge = await run_native_transaction(session, 'account_private_charge_transaction',
            owner_id=str(owner_id), profile_records=records,
            approved_installations=arguments['approved_installations'])
        self.leases.require_held()
        return charge['total'] - charge['raw']

    async def startup(self, settings, sessions):
        # This is the recognized full reconcile, not legacy v1 re-parsing or an
        # unconditional interrupted-row mutation ahead of custody observation.
        return await audit_startup_participating(settings, sessions, self.participant,
                                                require_ready=True)


async def _drain(pending):
    try:
        return await asyncio.shield(pending)
    except asyncio.CancelledError as cancelled:
        while not pending.done():
            try:
                await asyncio.shield(pending)
            except asyncio.CancelledError:
                continue
            except BaseException:
                break
        if not pending.cancelled() and pending.exception() is not None:
            cancelled.add_note('Participating worker also failed: ' + repr(pending.exception()))
        raise


async def run_forever_participating(settings, physical, *, poll_interval=0.5):
    """Original claim/executor under SH from claim through final cleanup.

    Idle workers hold no singleton lock, permitting the one original DELETE.
    Each cycle owns the initialized original lock before claiming any SQL row.
    Cancellation drains the bounded executor before either lock unwinds. This
    does not substitute its future distinct physical scientific dispatcher.
    """
    import os
    from uuid import uuid4
    from app.database import make_engine
    from app import worker as original
    require(isinstance(physical, PhysicalAssembly) and type(poll_interval) in (int, float)
            and 0 < poll_interval <= 30, 'physical_worker_assembly')
    engine = make_engine(settings)
    physical.bind_engine(settings, engine)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    physical.bind_sessions(sessions)
    identifier = f'{os.getpid()}-{uuid4()}'
    try:
        await physical.startup(settings, sessions)
        while True:
            async def cycle():
                # ContextVar inheritance does not transfer the parent's
                # same-task authority. The drained task owns both descriptors
                # itself, from claim through the final executor/EOF cleanup.
                async with physical.leases.acquire():
                    physical.leases.require_held()
                    async with physical.worker.acquire_processing():
                        physical.worker.require_processing_held()
                        job = await original._claim(sessions, identifier)
                        if job is not None:
                            await original._execute(settings, sessions, job, min(poll_interval, 0.1))
                        physical.worker.require_processing_held()
                    physical.leases.require_held()
                    return job
            # Parent cancellation shields/drains outside the lifetime guards;
            # it cannot release guards owned by the executing cycle task.
            job = await _drain(asyncio.create_task(cycle()))
            if job is None:
                await asyncio.sleep(poll_interval)
    finally:
        await engine.dispose()
