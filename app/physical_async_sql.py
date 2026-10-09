"""Closed native operations on the API session's existing SQLite transaction.

Transport only: caller retains the writer/worker lease and runtime authority.
This neither admits WAL durability nor opens, commits or closes a connection.
"""

import asyncio
import sqlite3

import aiosqlite
from sqlalchemy.ext.asyncio import AsyncSession

from app.physical_contract import require

_BUSY = 'physical_native_operation_running'
_NAMES = frozenset(('classify_snapshot','project_inventory','observe_receipt','save_current_tombstone',
    'prepare_project_deletion','retire_project_forest_relations','retire_project_forest_families','transfer_project_deletion',
    'cleanup_project_deletion_file','prepare_root_transaction','publish_root_transaction',
    'classify_startup_snapshot','account_private_charge_transaction',
    'reserve_root_transaction','seal_root_transaction','read_dataset_transaction','read_dataset_bytes_transaction',
    'reserve_child_intent_transaction','publish_correction_transaction','publish_transform_transaction',
    'list_datasets_transaction','lineage_transaction'))


def _operation(name):
    require(type(name) is str and name in _NAMES,'physical_async_operation')
    if name in ('classify_snapshot','classify_startup_snapshot'):
        from app import physical_classifier
        return getattr(physical_classifier,name)
    if name in ('prepare_root_transaction','publish_root_transaction'):
        from app import physical_roots
        return getattr(physical_roots,name)
    if name == 'account_private_charge_transaction':
        from app.physical_accounting import account_private_charge_transaction
        return account_private_charge_transaction
    if name in ('reserve_root_transaction','seal_root_transaction'):
        from app import physical_root_intake
        return getattr(physical_root_intake,name)
    if name in ('read_dataset_transaction','read_dataset_bytes_transaction'):
        from app import physical_read
        return getattr(physical_read,name)
    if name in ('list_datasets_transaction','lineage_transaction'):
        from app import physical_catalog
        return getattr(physical_catalog,name)
    if name == 'reserve_child_intent_transaction':
        from app.physical_forest import reserve_child_intent_transaction
        return reserve_child_intent_transaction
    if name in ('publish_correction_transaction','publish_transform_transaction'):
        from app import physical_publication
        return getattr(physical_publication,name)
    if name in ('prepare_project_deletion','retire_project_forest_relations','retire_project_forest_families','transfer_project_deletion',
                'cleanup_project_deletion_file'):
        from app import physical_project_deletion
        return getattr(physical_project_deletion,name)
    from app import physical_deleted_inventory
    return getattr(physical_deleted_inventory,name)


def _invoke(driver,operation,arguments):
    # Runs on the original aiosqlite thread, not the event loop or a second
    # connection. Preserve native TEXT/BLOB/tuple values without ORM coercion.
    connection=driver._conn
    require(type(connection) is sqlite3.Connection and connection.in_transaction,
            'physical_async_native_transaction')
    require(connection.row_factory is None and connection.text_factory is str
            and connection.execute('PRAGMA foreign_keys').fetchone()==(1,),
            'physical_async_native_representation')
    result=operation(connection,**arguments)
    require(driver._conn is connection and connection.in_transaction,
            'physical_async_transaction_escaped')
    return result


async def run_native_transaction(session,operation,**arguments):
    """Use one closed source-owned operation within the caller's transaction.

    Flush original ORM rows first. Concurrent use of this session is forbidden.
    Cancellation drains native work before releasing caller-held lifetime guards;
    the caller still decides rollback. No callback or SQL comes from an HTTP DTO.
    """
    callback=_operation(operation)
    require(isinstance(session,AsyncSession) and session.in_transaction(),
            'physical_async_transaction')
    require(not session.new and not session.dirty and not session.deleted,
            'physical_async_unflushed_orm')
    require(_BUSY not in session.info,'physical_async_reentry')
    bind=session.get_bind()
    require(bind.dialect.name=='sqlite' and bind.dialect.driver=='aiosqlite',
            'physical_async_driver')
    token=object()
    session.info[_BUSY]=token
    pending=None
    try:
        sqlalchemy_connection=await session.connection()
        pooled=await sqlalchemy_connection.get_raw_connection()
        driver=pooled.driver_connection
        require(type(driver) is aiosqlite.Connection and driver._running,
                'physical_async_driver')
        pending=asyncio.create_task(driver._execute(_invoke,driver,callback,arguments))
        try:
            return await asyncio.shield(pending)
        except asyncio.CancelledError as cancelled:
            # A cancelled aiosqlite Future does not cancel queued SQLite work.
            # Repeated cancellation likewise cannot release the lifetime early.
            while not pending.done():
                try:
                    await asyncio.shield(pending)
                except asyncio.CancelledError:
                    continue
                except BaseException:
                    break
            if not pending.cancelled() and pending.exception() is not None:
                cancelled.add_note('Native operation also failed: '+repr(pending.exception()))
            raise
    finally:
        require(pending is None or pending.done(),'physical_async_operation_not_drained')
        require(session.info.get(_BUSY) is token,'physical_async_guard_changed')
        del session.info[_BUSY]
