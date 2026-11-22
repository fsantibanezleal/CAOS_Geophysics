"""Bounded owned dataset reading and unchanged full producer ancestry checks."""

from app.physical_contract import canonical, require, uuid
from app.physical_forest import _row
from app.physical_publication import audit_correction_ancestry, audit_transform_producer, decode
from app.physical_roots import _ledger
from app.physical_persistence import M


def _verified_body(connection, files, *, owner_id, project_id, dataset_id, approved_manifests):
    row = _row(connection, 'SELECT * FROM observation_datasets WHERE id=? AND owner_id=? AND project_id=?',
        (dataset_id, owner_id, project_id))
    require(row['parser_version'] == 'gravity-stations-json/v1', 'physical_read_schema')
    if row['payload_schema'] == 'gravity-transform-result-1':
        value = audit_transform_producer(connection, files, row, approved_manifests=approved_manifests)
        body = files.read(row['storage_key'], cap=64*M, expected_bytes=row['byte_count'], expected_sha256=row['sha256'])
        require(canonical(decode(body,64*M)) == canonical(value), 'physical_read_snapshot_changed')
        return body
    body, _ = audit_correction_ancestry(connection, files, row, approved_manifests=approved_manifests)
    return body


def read_dataset_bytes_transaction(connection, files, *, owner_id, project_id, dataset_id,
                                   approved_manifests):
    """Return exact audited stored bytes, not a reserialized Python/JS object."""
    for value in (owner_id, project_id, dataset_id):
        uuid(value)
    with _ledger(connection, caller_owned=True):
        return _verified_body(connection, files, owner_id=owner_id, project_id=project_id,
            dataset_id=dataset_id, approved_manifests=approved_manifests)


def read_dataset_transaction(connection, files, **arguments):
    """Structural object for internal method inspection; never a wire digest."""
    return decode(read_dataset_bytes_transaction(connection,files,**arguments),64*M)


async def owned_dataset_payload(session, physical, dataset):
    return await _owned_dataset_read(session,physical,dataset,'read_dataset_transaction')


async def owned_dataset_bytes(session, physical, dataset):
    return await _owned_dataset_read(session,physical,dataset,'read_dataset_bytes_transaction')


def dataset_bytes_response(body):
    """Original-byte HTTP projection only, after the complete owned read."""
    from fastapi.responses import Response
    require(type(body) is bytes and 0 < len(body) <= 64*M, 'physical_read_response_bytes')
    return Response(body,media_type='application/json',headers={'Cache-Control':'no-store'})


async def _owned_dataset_read(session, physical, dataset, operation):
    from app.physical_assembly import PhysicalAssembly
    from app.physical_async_sql import run_native_transaction
    from app.errors import ApiError
    require(isinstance(physical, PhysicalAssembly) and session.info.get('physical_assembly') is physical,
            'physical_operator_assembly_required')
    physical.leases.require_held()
    try:
        owner_id, project_id, dataset_id = str(dataset.owner_id), dataset.project_id, dataset.id
        # SQLite SELECT does not open a native snapshot merely because
        # SQLAlchemy has an autobegun logical transaction. This GET seam owns
        # only clean read work and establishes an actual deferred snapshot.
        from sqlalchemy import text
        require(not session.new and not session.dirty and not session.deleted,
                'physical_read_pending_writer')
        await session.rollback()
        await session.execute(text('BEGIN'))
        value = await run_native_transaction(session, operation, files=physical.leases.files,
            owner_id=owner_id, project_id=project_id, dataset_id=dataset_id,
            approved_manifests=physical.participant.arguments()['approved_manifests'])
        await session.refresh(dataset)
        physical.leases.require_held()
        return value
    except (ValueError, OSError) as error:
        raise ApiError(409, 'derived_integrity_failed', 'Physical dataset or saved ancestry differs from its receipt') from error
