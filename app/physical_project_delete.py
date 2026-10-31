"""Fixed participant in the original route, not an alternate DELETE service.

Assembly must bind the already qualified native SQLite/runtime/source authority
before opening the private target. This object never creates or infers that
authority, starts a worker or changes the default migration/configuration.
"""

import asyncio
import json
from pathlib import Path
import time
from uuid import uuid4

from sqlalchemy import text

from app.errors import ApiError
from app.physical_async_sql import run_native_transaction
from app.physical_contract import canonical, require, sha


class PhysicalProjectDeletion:
    def __init__(self,leases,worker_exclusion,*,source_policy_sha256,approved_manifests,
                 approved_installations,native_metadata):
        from app.physical_leases import WriterLeases
        from app.physical_participation import WorkerExclusion
        from app.physical_posix import PrivateFiles
        require(isinstance(leases,WriterLeases) and isinstance(leases.files,PrivateFiles), 'project_delete_native_files')
        require(isinstance(worker_exclusion,WorkerExclusion) and worker_exclusion.leases is leases,'project_delete_worker_binding')
        self.leases,self.worker=leases,worker_exclusion
        self.source_policy=sha(source_policy_sha256)
        self.registration=canonical(dict(approved_manifests=approved_manifests,
            approved_installations=approved_installations,native_metadata=native_metadata))
        require(len(self.registration)<=4*1048576,'project_delete_registry_cap')

    def check(self,settings):
        self.leases.require_held(exclusive=True); self.worker.require_held()
        require(Path(settings.data_dir)==self.leases.files.root_path,'project_delete_root_binding')

    def arguments(self):
        return dict(json.loads(self.registration),expected_source_policy_sha256=self.source_policy)

    async def prepare(self,settings,session,owner,project,archives):
        self.check(settings)
        plan=await run_native_transaction(session,'prepare_project_deletion',files=self.leases.files,
            owner_id=owner,project_id=project,batch_id=str(uuid4()),receipt_id=str(uuid4()),
            created_us=time.time_ns()//1000,profile_records=archives,**self.arguments())
        self.check(settings)
        return plan

    async def recheck(self,settings,session,plan):
        self.check(settings)
        result=await run_native_transaction(session,'classify_snapshot',files=self.leases.files,**self.arguments())
        require(result.classification=='prepared_uncommitted'
                and result.operations.get(plan['custody']['batch_id'])=='abandon_only','project_delete_preparation_unresolved:'+result.reason)
        inv=await run_native_transaction(session,'project_inventory',owner_id=plan['custody']['owner_id'],
            project_id=plan['custody']['project_id'],source_policy_sha256=self.source_policy,
            profile_records=plan['inventory']['profile_archives'])
        require(canonical(inv)==canonical(plan['inventory']),'project_delete_snapshot_changed')
        self.check(settings)

    async def move(self,settings,plan,lane,*,reverse=False):
        self.check(settings)
        pending=asyncio.create_task(asyncio.to_thread(self.leases.files.move_project_directory,plan['custody']['owner_id'],
            plan['custody']['project_id'],lane,reverse=reverse))
        try:
            await asyncio.shield(pending)
        except asyncio.CancelledError as cancelled:
            while not pending.done():
                try: await asyncio.shield(pending)
                except asyncio.CancelledError: continue
                except BaseException: break
            if not pending.cancelled() and pending.exception() is not None:
                cancelled.add_note('Native move also failed: '+repr(pending.exception()))
            raise
        self.check(settings)

    async def transfer(self,settings,session,plan):
        self.check(settings)
        body=await run_native_transaction(session,'transfer_project_deletion',inventory=plan['inventory'],
            custody=plan['custody'],expected_source_policy_sha256=self.source_policy,
            approved_installations=json.loads(self.registration)['approved_installations'])
        self.check(settings)
        return body

    async def cleanup(self,settings,session,plan):
        # Logical deletion is already committed. Every later unlink/fsync/SQL
        # acknowledgement is independently committed; any cut retains debt.
        for slot in plan['custody']['initial_files']:
            self.check(settings)
            await session.execute(text('BEGIN IMMEDIATE'))
            try:
                result=await run_native_transaction(session,'classify_snapshot',files=self.leases.files,**self.arguments())
                require(result.classification=='coherent_committed','project_delete_cleanup_unresolved:'+result.reason)
                await run_native_transaction(session,'cleanup_project_deletion_file',files=self.leases.files,
                    owner_id=plan['custody']['owner_id'],batch_id=plan['custody']['batch_id'],
                    ordinal=slot['ordinal'],removed_us=time.time_ns()//1000)
                await session.commit()
            except BaseException:
                await session.rollback()
                raise
        self.check(settings)


async def prepare_physical_project_deletion(app,settings,session,owner,project,archives):
    from app.physical_successor import PREDECESSOR
    from app.physical_schema import DDL
    revision=(await session.execute(text('SELECT version_num FROM alembic_version'))).scalars().all()
    if revision==[PREDECESSOR]: return None,None
    participant=getattr(app.state,'physical_project_deletion',None)
    if len(revision)!=1 or revision[0] not in DDL or not isinstance(participant,PhysicalProjectDeletion):
        raise ApiError(409,'physical_deletion_unavailable','Physical project deletion requires its recognized native participant')
    try:
        return participant,await participant.prepare(settings,session,owner,project,archives)
    except (ValueError,OSError):
        raise ApiError(409,'physical_deletion_unresolved','Physical project custody is unresolved; originals and rows are preserved') from None


def install_project_deletion(app,*,source_policy_sha256,approved_manifests,approved_installations,native_metadata):
    require(app.middleware_stack is None and not hasattr(app.state,'physical_project_deletion'),
            'project_delete_installation_lifetime')
    archived=getattr(app.state,'profile_archive_deletion',None)
    require(archived is not None,'project_delete_writer_participation_required')
    app.state.physical_project_deletion=PhysicalProjectDeletion(archived.leases,archived.worker_exclusion,
        source_policy_sha256=source_policy_sha256,approved_manifests=approved_manifests,
        approved_installations=approved_installations,native_metadata=native_metadata)
