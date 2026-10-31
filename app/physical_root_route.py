"""Original dataset-route root birth with persisted preallocation custody."""

import time
from uuid import uuid4

from sqlalchemy import select, text

from app.errors import ApiError
from app.models import ObservationDataset, utcnow
from app.physical_assembly import PhysicalAssembly
from app.physical_async_sql import run_native_transaction
from app.physical_contract import byte_sha, require
from app.physical_persistence import M
from app.profile_archive_custody import archive_inventory
from app.profile_archive_delete import archive_relations, excluded_read


async def create_physical_root(settings, session, physical, *, owner_id, project_id, raw_asset_id):
    require(isinstance(physical, PhysicalAssembly) and session.info.get('physical_assembly') is physical,
            'physical_operator_assembly_required')
    physical.leases.require_held()
    require(session.in_transaction(), 'physical_root_route_transaction')
    files = physical.leases.files
    root, batch, intent = (str(uuid4()) for _ in range(3))
    try:
        registry = physical.participant.arguments()
        relations, receipts = await archive_relations(session)
        archives = await excluded_read(archive_inventory, files, relations, receipts,
            approved_installations=registry['approved_installations'])
        prepared = await run_native_transaction(session, 'reserve_root_transaction', files=files,
            owner_id=owner_id, project_id=project_id, raw_asset_id=raw_asset_id,
            root_dataset_id=root, batch_id=batch, created_us=time.time_ns()//1000,
            quota_bytes=min(settings.account_quota_bytes, 1024*M), profile_records=archives,
            approved_installations=registry['approved_installations'])
        await session.commit()  # reservation is durable BEFORE namespace allocation
        physical.leases.require_held()
        await excluded_read(files.create_directory, '.job-staging', exist_ok=True)
        await excluded_read(files.create_directory, f'.job-staging/{root}')
        await excluded_read(files.write_new, f'.job-staging/{root}/input.json', prepared['original'], cap=16*M)
        await excluded_read(files.write_new, f'.job-staging/{root}/dataset.json', prepared['body'], cap=16*M)
        await session.execute(text('BEGIN IMMEDIATE'))
        await run_native_transaction(session, 'seal_root_transaction', files=files,
            owner_id=owner_id, project_id=project_id, root_dataset_id=root,
            batch_id=batch, sealed_us=time.time_ns()//1000)
        await run_native_transaction(session, 'prepare_root_transaction', files=files,
            owner_id=owner_id, project_id=project_id, raw_asset_id=raw_asset_id,
            root_dataset_id=root, intent_id=intent, created_us=time.time_ns()//1000,
            profile_records=archives, approved_installations=registry['approved_installations'])
        await session.commit()  # intent and independent-target reservation before install
        physical.leases.require_held()
        for key in ('derived', f'derived/{owner_id}', f'derived/{owner_id}/{project_id}',
                    f'derived/{owner_id}/{project_id}/datasets'):
            await excluded_read(files.create_directory, key, exist_ok=True)
        await excluded_read(files.install, f'.job-staging/{root}/dataset.json', prepared['dataset_key'],
            cap=16*M, expected_bytes=len(prepared['body']), expected_sha256=byte_sha(prepared['body']))
        await session.execute(text('BEGIN IMMEDIATE'))
        await run_native_transaction(session, 'publish_root_transaction', files=files,
            owner_id=owner_id, project_id=project_id, intent_id=intent,
            created_at=utcnow().isoformat(sep=' '))
        await session.commit()
        physical.leases.require_held()
        item = (await session.execute(select(ObservationDataset).where(
            ObservationDataset.id == root, ObservationDataset.owner_id == owner_id,
            ObservationDataset.project_id == project_id))).scalar_one()
        return item
    except BaseException as error:
        # Only the caller's active SQL work is rolled back. Every committed
        # reservation/intent and partially allocated copy stays for fresh audit.
        await session.rollback()
        if isinstance(error, ValueError):
            code = 'dataset_exists' if str(error) == 'physical_root_already_reserved' else 'physical_state_unresolved'
            if str(error) == 'physical_account_quota':
                raise ApiError(507, 'account_quota_exceeded', 'Account private-byte quota exceeded') from error
            raise ApiError(409, code, 'Physical dataset state requires an owned consistent receipt') from error
        raise
