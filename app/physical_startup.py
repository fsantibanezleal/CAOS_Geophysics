"""Fresh excluded startup observation; never recovery or lasting admission.

Uses the already fixed operator-bound project participant and original native
transaction transport. It creates no locks, mounts, schemas, accounts or files.
Every later writer must still participate and recheck its own fresh snapshot.
"""
import asyncio
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.physical_async_sql import run_native_transaction
from app.physical_contract import require
from app.physical_project_delete import PhysicalProjectDeletion


async def audit_startup_participating(settings, sessions, participant, *, require_ready=False):
    require(type(require_ready) is bool, 'physical_startup_options')
    require(isinstance(participant,PhysicalProjectDeletion) and isinstance(sessions,async_sessionmaker),
            'physical_startup_bound_participant')
    engine=sessions.kw.get('bind')
    require(isinstance(engine,AsyncEngine) and engine.url.drivername=='sqlite+aiosqlite' and
            engine.url.database is not None and Path(engine.url.database)==Path(settings.database_path),
            'physical_startup_database_binding')
    arguments=participant.arguments()
    async with participant.leases.acquire(exclusive=True):
        async with participant.worker.acquire():
            participant.check(settings)

            async def observation():
                # This subordinate operation borrows no task's lease authority.
                # Its parent retains both actual locks through session close.
                async with sessions() as session:
                    for pragma,expected in (('journal_mode','wal'),('synchronous',2),
                                            ('foreign_keys',1),('trusted_schema',0)):
                        value=(await session.execute(text('PRAGMA '+pragma))).scalar_one()
                        require(value==expected,'physical_startup_sql_configuration:'+pragma)
                    await session.execute(text('BEGIN IMMEDIATE'))
                    try:
                        result=await run_native_transaction(session,
                            'classify_startup_snapshot' if require_ready else 'classify_snapshot',
                            files=participant.leases.files,**arguments)
                        require(result.classification in ('coherent_committed','prepared_uncommitted'),
                                'physical_startup_inconsistent:'+result.reason)
                        return result
                    finally:
                        await session.rollback()

            pending=asyncio.create_task(observation())
            try:
                result=await asyncio.shield(pending)
            except asyncio.CancelledError as cancelled:
                # Includes classifier thread, original rollback and pool return.
                # Repeated cancellation cannot release either lock early.
                while not pending.done():
                    try: await asyncio.shield(pending)
                    except asyncio.CancelledError: continue
                    except BaseException: break
                if not pending.cancelled() and pending.exception() is not None:
                    cancelled.add_note('Startup observation also failed: '+repr(pending.exception()))
                raise
            participant.check(settings)
            return result  # runtime=False, not a token permitting later writes.
