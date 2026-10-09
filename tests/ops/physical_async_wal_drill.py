"""Actual ordinary WAL transaction seam; not power-loss or runtime admission."""

import argparse
import asyncio
import json
import os
from pathlib import Path
import sqlite3

from sqlalchemy import event,text
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine

from app.physical_async_sql import run_native_transaction
from app.physical_contract import byte_sha
from app.physical_leases import WriterLeases
from app.physical_participation import WorkerExclusion


async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--policy',required=True)
    parser.add_argument('--waveform-member',action='store_true')
    args=parser.parse_args()
    assert os.name=='posix' and os.geteuid()==61901 and args.waveform_member
    root=Path(args.root); private=root/'private'; database=root/'fixture.sqlite'
    os.umask(0o077)
    native=sqlite3.connect(database,isolation_level=None,timeout=30)
    try:
        source=native.execute('SELECT sqlite_version(),sqlite_source_id()').fetchone()
        assert source==('3.51.3','2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618')
        rid,old_body,old_sha=native.execute('SELECT receipt_id,tombstone_bytes,tombstone_sha256 FROM physical_deletion_extensions').fetchone()
        assert byte_sha(old_body)==old_sha
    finally:
        native.close()
    for name,body in (('.physical-writers.lock',b'\0'),('.processing-worker.lock',b'0')):
        with (private/name).open('xb') as stream:
            stream.write(body); stream.flush(); os.fsync(stream.fileno())
        (private/name).chmod(0o600)
    lock=(private/'.physical-writers.lock').stat(); old=(private/'.processing-worker.lock').stat()
    leases=WriterLeases(private,device=lock.st_dev,inode=lock.st_ino,uid=os.geteuid())
    worker=WorkerExclusion(leases,device=old.st_dev,inode=old.st_ino,uid=os.geteuid())
    engine=create_async_engine('sqlite+aiosqlite:///'+database.as_posix(),connect_args={'timeout':30})
    observed=[]
    @event.listens_for(engine.sync_engine,'connect')
    def configure(connection,_):
        cursor=connection.cursor()
        try:
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute('PRAGMA journal_mode=WAL')
            assert cursor.fetchone()==('wal',)
            cursor.execute('PRAGMA synchronous=FULL')
            cursor.execute('PRAGMA trusted_schema=OFF')
        finally:
            cursor.close()
    try:
        async with leases.acquire(exclusive=True):
            async with worker.acquire():
                for commit in (False,True):
                    async with async_sessionmaker(engine)() as session:
                        await session.execute(text('BEGIN IMMEDIATE'))
                        assert (await session.execute(text('PRAGMA synchronous'))).scalar_one()==2
                        assert (await session.execute(text('PRAGMA journal_mode'))).scalar_one()=='wal'
                        assert (await session.execute(text('PRAGMA foreign_keys'))).scalar_one()==1
                        leases.require_held(exclusive=True); worker.require_held()
                        original=await run_native_transaction(session,'observe_receipt',receipt_id=rid)
                        await session.execute(text('DELETE FROM physical_deletion_extensions WHERE receipt_id=:id'),{'id':rid})
                        assert (await session.execute(text('SELECT count(*) FROM physical_deletion_extensions'))).scalar_one()==0
                        # A real separate ordinary reader observes committed old
                        # state while this same API/native transaction is pending.
                        with sqlite3.connect(database,timeout=5) as reader:
                            assert reader.execute('SELECT tombstone_bytes,tombstone_sha256 FROM physical_deletion_extensions').fetchone()==(old_body,old_sha)
                        restored=await run_native_transaction(session,'save_current_tombstone',receipt_id=rid,
                            inventory=json.loads(old_body)['physical_inventory'],expected_source_policy_sha256=args.policy,
                            approved_installations={})
                        assert restored==old_body and session.in_transaction()
                        assert await run_native_transaction(session,'observe_receipt',receipt_id=rid)==original
                        leases.require_held(exclusive=True); worker.require_held()
                        if commit: await session.commit()
                        else: await session.rollback()
                        observed.append(dict(commit=commit,same_transaction_native_json=True,independent_committed_reader=True))
                with sqlite3.connect(database,timeout=5) as reader:
                    assert reader.execute('SELECT tombstone_bytes,tombstone_sha256 FROM physical_deletion_extensions').fetchone()==(old_body,old_sha)
                    assert reader.execute('PRAGMA foreign_key_check').fetchall()==[]
                    assert reader.execute('PRAGMA integrity_check').fetchone()==('ok',)
        print(json.dumps(dict(schema='geophysics.physical-native-async-wal-drill/v1',uid=os.geteuid(),
            sqlite_version=source[0],sqlite_source_id=source[1],wal=True,synchronous_full=True,
            actual_exclusive_and_original_worker=True,original_tombstone_and_native_receipt_unchanged=True,
            phases=observed,actual_http_delete_performed=False,runtime_admission_inferred=False,
            power_loss_inferred=False,production_activated=False),sort_keys=True))
    finally:
        await engine.dispose()
        leases.close()


if __name__=='__main__':
    asyncio.run(main())
