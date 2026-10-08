"""Actual original-route/plural SQL/lease/delete drill on a private copied root.

Explicit qualification assembly, not default server startup or scientific run.
No live accounts, service configuration, current pointer or original fixture is
modified. Scientific inputs are saved source-bound bytes, never substitutes.
"""

import argparse
from contextlib import asynccontextmanager
from functools import partial
import json
import os
from pathlib import Path
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_users.password import PasswordHelper
from sqlalchemy import event,text
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine

from app.auth import install_auth
from app.accounts import provision_account
from app.config import Settings
from app.errors import ApiError,api_error_handler
from app.physical_async_sql import run_native_transaction
from app.physical_contract import byte_sha
from app.physical_leases import WriterLeases
from app.physical_participation import WorkerExclusion,install_participation
from app.physical_project_delete import install_project_deletion
from app.projects import install_project_routes
from app.security import install_security


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--root',required=True); parser.add_argument('--policy',required=True)
    args=parser.parse_args(); root=Path(args.root); private=root/'private'; database=root/'fixture.sqlite'
    assert os.name=='posix' and os.geteuid()==61901 and root.is_absolute()
    os.umask(0o077)
    with sqlite3.connect(database) as db:
        actual=db.execute('SELECT sqlite_version(),sqlite_source_id()').fetchone()
        assert actual==('3.51.3','2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618')
        owner,project=db.execute('SELECT owner_id,id FROM projects').fetchone()
        email=db.execute('SELECT email FROM user WHERE id=?',(owner,)).fetchone()[0]
        original_assets=db.execute('SELECT id,storage_key,sha256,byte_count FROM raw_assets ORDER BY id').fetchall()
        manifests={h:json.loads(body) for h,body in db.execute('SELECT module_manifest_sha256,module_manifest_bytes FROM physical_job_controls')}
        # The fixture explicitly has a non-login seed. Replace only its copied
        # ordinary password field using the original library; not a live owner.
        password='private-qualification-password-872'
        db.execute('UPDATE user SET hashed_password=? WHERE id=?',(PasswordHelper().hash(password),owner))
    retained={p.relative_to(private).as_posix():byte_sha(p.read_bytes()) for p in (private/'.job-staging').rglob('*') if p.is_file()}
    assert all(byte_sha((private/key).read_bytes())==h and (private/key).stat().st_size==n for _,key,h,n in original_assets)
    for name,body in (('.physical-writers.lock',b'\0'),('.processing-worker.lock',b'0')):
        with (private/name).open('xb') as stream:
            stream.write(body); stream.flush(); os.fsync(stream.fileno())
        (private/name).chmod(0o600)
    lock=(private/'.physical-writers.lock').stat(); old=(private/'.processing-worker.lock').stat()
    leases=WriterLeases(private,device=lock.st_dev,inode=lock.st_ino,uid=os.geteuid())
    worker=WorkerExclusion(leases,device=old.st_dev,inode=old.st_ino,uid=os.geteuid())
    metadata={name:dict(cap=1,bytes=1,sha256=byte_sha(body),required=True)
              for name,body in (('.physical-writers.lock',b'\0'),('.processing-worker.lock',b'0'))}
    engine=create_async_engine('sqlite+aiosqlite:///'+database.as_posix(),connect_args={'timeout':30})
    @event.listens_for(engine.sync_engine,'connect')
    def configure(connection,_):
        cursor=connection.cursor()
        try:
            cursor.execute('PRAGMA foreign_keys=ON'); cursor.execute('PRAGMA journal_mode=WAL'); assert cursor.fetchone()==('wal',)
            cursor.execute('PRAGMA synchronous=FULL'); cursor.execute('PRAGMA trusted_schema=OFF')
        finally: cursor.close()
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    async def audit():
        async with leases.acquire(exclusive=True):
            async with worker.acquire():
                async with sessions() as session:
                    await session.execute(text('BEGIN IMMEDIATE'))
                    result=await run_native_transaction(session,'classify_snapshot',files=leases.files,
                        approved_manifests=manifests,approved_installations={},native_metadata=metadata,
                        expected_source_policy_sha256=args.policy)
                    assert result.classification=='coherent_committed',result.reason
                    await session.rollback()
                    return dict(result.account_charges[owner])
    observations=[]
    @asynccontextmanager
    async def lifetime(_):
        observations.append(await audit())
        try: yield
        finally: await engine.dispose()
    # Reuse the original authentication/security/project router unchanged. The
    # production0004 startup remains closed to0005; this is a declared private
    # candidate, with full positive classifier before each serving lifetime.
    app=FastAPI(lifespan=lifetime); app.state.sessions=sessions
    app.add_exception_handler(ApiError,api_error_handler)
    messages=[]
    async def capture(*args): messages.append(args)
    current_user,get_session=install_auth(app,Settings(data_dir=private,db_path=database,
        auth_secret='actual-private-M01-delete-qualification-1234567890',public_origin='http://testserver',
        cookie_secure=False,auth_mode='local'),capture)
    settings=Settings(data_dir=private,db_path=database,auth_secret='actual-private-M01-delete-qualification-1234567890',
                      public_origin='http://testserver',cookie_secure=False,auth_mode='local')
    install_security(app,settings); install_project_routes(app,settings,current_user,get_session)
    install_participation(app,leases,worker,approved_installations={})
    install_project_deletion(app,source_policy_sha256=args.policy,approved_manifests=manifests,
                             approved_installations={},native_metadata=metadata)
    def login(client,user):
        csrf=client.get('/api/auth/csrf').json()['csrf_token']
        headers={'Origin':'http://testserver','X-CSRF-Token':csrf}
        response=client.post('/api/auth/cookie/login',data={'username':user,'password':password},headers=headers)
        assert response.status_code==204,response.text
        return headers
    try:
        with TestClient(app) as client:
            headers=login(client,email)
            before_raw=client.get(f'/api/projects/{project}/assets/{original_assets[0][0]}/download')
            assert before_raw.status_code==200 and byte_sha(before_raw.content)==original_assets[0][2]
            # Explicit private fixture-only second account through the original
            # provisioning function, not an operator/production owner duplicate.
            client.portal.call(partial(provision_account,sessions,'other-private-qualification@example.org',password))
            foreign=login(client,'other-private-qualification@example.org')
            assert client.delete(f'/api/projects/{project}',headers=foreign).status_code==404
            headers=login(client,email)
            unknown=private/'unknown-qualification-control'
            with unknown.open('xb') as out: out.write(b'preserve exact introduced negative until test removes it')
            assert client.delete(f'/api/projects/{project}',headers=headers).status_code==409
            assert unknown.read_bytes()==b'preserve exact introduced negative until test removes it'
            assert byte_sha((private/original_assets[0][1]).read_bytes())==original_assets[0][2]
            # Only this named newly authored negative, never any original file.
            unknown.unlink(); os.fsync(leases.files.fd)
            deleted=client.delete(f'/api/projects/{project}',headers=headers)
            assert deleted.status_code==200,deleted.text
            assert client.get(f'/api/projects/{project}').status_code==404
            assert client.get(f'/api/projects/{project}/assets/{original_assets[0][0]}/download').status_code==404
            assert not messages
        with sqlite3.connect(database) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
            assert not db.execute('PRAGMA foreign_key_check').fetchall()
            receipt,body,hash_value=db.execute('SELECT receipt_id,tombstone_bytes,tombstone_sha256 FROM physical_deletion_extensions').fetchone()
            assert byte_sha(body)==hash_value
            assert db.execute('SELECT raw_bytes FROM account_usage WHERE user_id=?',(owner,)).fetchone()==(0,)
            assert db.execute("SELECT count(*) FROM physical_custody_batches WHERE origin_kind='project_deletion' AND state='removed' AND charged_bytes=0").fetchone()==(1,)
            assert db.execute('SELECT count(*) FROM observation_datasets').fetchone()==(0,)
        assert retained=={p.relative_to(private).as_posix():byte_sha(p.read_bytes()) for p in (private/'.job-staging').rglob('*') if p.is_file()}
        # Actual new serving lifetime performs a fresh WAL-aware source-positive
        # audit of the deleted partition plus retained original stage debt.
        with TestClient(app): pass
        assert observations[1]['raw']==observations[1]['datasets']==observations[1]['results']==0
        assert observations[1]['custody']==observations[0]['custody']
        print(json.dumps(dict(schema='geophysics.private-native-physical-project-delete/v1',uid=os.geteuid(),
            sqlite_version=actual[0],sqlite_source_id=actual[1],actual_original_http_delete=True,
            actual_global_exclusive_and_original_worker=True,foreign_owner_404=True,unknown_original_preserved=True,
            original_stages_unchanged=True,original_raw_sha256=original_assets[0][2],deletion_receipt=receipt,
            tombstone_sha256=hash_value,charges_before=observations[0],charges_restart=observations[1],mail_messages=0,
            fixture_only=True,saved_science_recomputed=False,default_server_startup_inferred=False,
            runtime_admission_inferred=False,production_activated=False),sort_keys=True))
    finally:
        leases.close()


if __name__=='__main__': main()
