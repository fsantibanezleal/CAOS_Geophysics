"""Nonroot kernel/owned DELETE drill, not a scientific execution certificate.

The original profile is parsed and preserved by the actual API. A declared
cancelled-before-compute custody fixture tests deletion mechanics only. Existing
actual recovered-profile evidence is independently read, never moved or edited.
"""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from app.physical_contract import canonical
from app.physical_leases import WriterLeases
from app.physical_participation import WorkerExclusion, WriterParticipation, install_participation
from app.profile_archive_custody import retained_inventory


def digest(body):
    return hashlib.sha256(body).hexdigest()


def write(path, body):
    with path.open('xb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


async def live_audit(private, approved):
    """Read-only consistent SQL/file audit, not all-writer exclusion admission."""
    from app.physical_posix import PrivateFiles
    from app.config import Settings
    from app.profile_archive_delete import archive_relations
    from sqlalchemy.ext.asyncio import async_sessionmaker
    settings=Settings(data_dir=private,auth_secret='independent-read-only-audit-20261008-123456',
        public_origin='http://testserver',cookie_secure=False)
    # Explicit SQLite read-only URL; no authentication, rate or migration writes.
    from sqlalchemy.ext.asyncio import create_async_engine
    engine=create_async_engine('sqlite+aiosqlite:///file:'+str(settings.database_path)+'?mode=ro&uri=true')
    try:
        async with async_sessionmaker(engine)() as session:
            from sqlalchemy import text
            await session.execute(text('BEGIN'))
            relations,receipts=await archive_relations(session)
            with PrivateFiles(private) as files:
                records=retained_inventory(files,relations,receipts,approved_installations=approved)
            await session.rollback()
            return records
    finally:
        await engine.dispose()


async def kernel_tests(leases, worker):
    held=False
    async with leases.acquire(exclusive=True,timeout=0):
        leases.require_held(exclusive=True)
        async with worker.acquire():
            worker.require_held()
            held=True
        # Context propagated to a spawned task is not authority to borrow FDs.
        async def foreign_task():
            try: leases.require_held(exclusive=True)
            except ValueError: return True
            return False
        assert await asyncio.create_task(foreign_task())
    # Fixed trusted child retains the ORIGINAL worker singleton, not a toy mutex.
    child=subprocess.Popen([sys.executable,'-I','-B','-c',
        'import fcntl,os,sys; f=open(sys.argv[1],"r+b"); fcntl.flock(f,fcntl.LOCK_EX); '
        'print("held",flush=True); sys.stdin.read(1)',str(leases.files.root_path/'.processing-worker.lock')],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
    try:
        assert child.stdout.readline(16)==b'held\n'
        async with leases.acquire(exclusive=True,timeout=0):
            try:
                async with worker.acquire(): raise AssertionError('original live worker bypassed')
            except ValueError as error: assert str(error)=='physical_worker_busy'
    finally:
        child.communicate(b'x',timeout=5)
        assert child.returncode==0
    # Actual descriptor remains locked through delayed streamed sends.
    stream_checks=[]
    async def handler(scope,receive,send):
        leases.require_held()
        await send(dict(type='http.response.start',status=200))
        await asyncio.sleep(0)
        await send(dict(type='http.response.body',body=b'final'))
    async def send(message):
        leases.require_held()
        async def contender():
            try:
                async with leases.acquire(exclusive=True,timeout=0):
                    raise AssertionError('stream lease ended before final send')
            except ValueError as error: assert str(error)=='physical_writer_busy'
        await asyncio.create_task(contender())
        stream_checks.append(message['type'])
    await WriterParticipation(handler,leases=leases,worker_exclusion=worker)(dict(type='http',method='GET'),None,send)
    assert stream_checks==['http.response.start','http.response.body']
    return dict(actual_same_task_exclusive=held,foreign_task_refused=True,actual_original_worker_refused=True,
        actual_streamed_body_exclusion=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--original',required=True)
    parser.add_argument('--actual-private',required=True)
    parser.add_argument('--actual-receipt',required=True)
    args=parser.parse_args()
    root=Path(args.root)
    assert os.name=='posix' and os.geteuid()==61901 and root.is_absolute() and not any(root.iterdir())
    with sqlite3.connect(':memory:') as probe:
        native_identity=probe.execute('SELECT sqlite_version(),sqlite_source_id()').fetchone()
    assert native_identity==('3.51.3','2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient
    from app.config import Settings
    from app.server import create_app
    from tests.api.conftest import ApiHarness
    from test_local_auth import provision, login
    from test_profile_jobs import owned_dataset
    from test_profile_archive_custody import archive_fixture
    actual=json.loads(Path(args.actual_receipt).read_bytes())
    manifest=actual['cancellation']['archive']
    assert actual['source_commit']=='320f0afd2cb7934a2501e3c2ccae4f3fbdf2a085'
    approved={manifest['job_id']:manifest['installation']}
    actual_records=asyncio.run(live_audit(Path(args.actual_private),approved))
    assert len(actual_records)==1 and actual_records[0]['manifest']==manifest
    os.environ['GEOPHYSICS_DB_PATH']=str(root/'api.sqlite3')
    source=Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(source/'app/alembic.ini')),'head')
    for name,body in (('.physical-writers.lock',b'\0'),('.processing-worker.lock',b'0')):
        write(root/name,body)
    lock=(root/'.physical-writers.lock').stat()
    leases=WriterLeases(root,device=lock.st_dev,inode=lock.st_ino,uid=os.geteuid())
    original_lock=(root/'.processing-worker.lock').stat()
    worker=WorkerExclusion(leases,device=original_lock.st_dev,inode=original_lock.st_ino,uid=os.geteuid())
    runtime=Path('/opt/fasl-admission/geophysics-profile-python31316-20261008-i05/profile-env/bin/python')
    settings=Settings(data_dir=root,auth_secret='private-owned-deletion-drill-20261008-123456',
        public_origin='http://testserver',cookie_secure=False,auth_mode='local',
        profile_online_enabled=True,profile_python=runtime,
        profile_linux_supervisor=Path('/opt/fasl-admission/geophysics-profile-api-320f0af-20261008-q10/science-source/scripts/profile_linux_supervisor.py'))
    messages=[]
    async def capture(*args): messages.append(args)
    approval_registry={}
    app=create_app(settings,capture)
    # Register authority after obtaining actual SQL fixture identities, before
    # serving a NEW app. No mutable authority is borrowed from an archive.
    try:
        kernel=asyncio.run(kernel_tests(leases,worker))
        with TestClient(app) as client:
            harness=ApiHarness(client,app,settings,messages)
            provision(harness); assert login(harness).status_code==204
            original=Path(args.original).read_bytes()
            project,asset,dataset,meta=owned_dataset(harness,original,'ert_ohm',38,222)
            base=f'/api/projects/{project["id"]}/jobs'
            response=harness.request('POST',base,json=dict(dataset_id=dataset['dataset_id'],method_id=meta['method'],parameters={}))
            assert response.status_code==202,response.text
            job=response.json()['job_id']
            assert harness.request('POST',base+'/'+job+'/cancel').json()['state']=='cancelled'
            async def read_relation():
                async with app.state.sessions() as active:
                    rows,_=await __import__('app.profile_archive_delete',fromlist=['archive_relations']).archive_relations(active)
                    return next(r for r in rows if r['id']==job)
            declared=asyncio.run(read_relation())
            approval_registry[job]=manifest['installation']
        # This is a *new* assembled app, so middleware precedes security/auth SQL.
        # The queued cancellation above has no live child or scientific result.
        _,_,fixture_manifest,_,_=archive_fixture(root,declared_relation=declared,
            declared_installation=approval_registry[job])
        for path in (root/'.profile-retained',root/'.profile-retained'/job): path.chmod(0o700)
        for path in (root/'.profile-retained').rglob('*'):
            if path.is_file(): path.chmod(0o600)
        app=create_app(settings,capture)
        install_participation(app,leases,worker,approved_installations=approval_registry)
        before={str(p.relative_to(root)):digest(p.read_bytes()) for p in (root/'.profile-retained').rglob('*') if p.is_file()}
        with TestClient(app) as client:
            harness=ApiHarness(client,app,settings,messages)
            assert login(harness).status_code==204
            assert client.get(asset['download_url']).content==original
            provision(harness,username='different-owner@example.org')
            assert login(harness,username='different-owner@example.org').status_code==204
            assert harness.request('DELETE',f'/api/projects/{project["id"]}').status_code==404
            assert login(harness).status_code==204
            unknown=root/'.profile-retained'/job/'unknown-native-fixture'
            write(unknown,b'preserve until exact test cleanup')
            assert harness.request('DELETE',f'/api/projects/{project["id"]}').status_code==409
            assert unknown.read_bytes()==b'preserve until exact test cleanup'
            assert client.get(asset['download_url']).content==original
            # Only the exact file created by this test is removed, no discovery.
            unknown.unlink(); parent=os.open(unknown.parent,os.O_RDONLY|os.O_DIRECTORY); os.fsync(parent); os.close(parent)
            deleted=harness.request('DELETE',f'/api/projects/{project["id"]}')
            assert deleted.status_code==200,deleted.text
            assert deleted.json()['retained_profile_archives']==1
            assert client.get(asset['download_url']).status_code==404
            assert client.get(base+'/'+job).status_code==404
        with sqlite3.connect(root/'api.sqlite3') as db:
            receipt=db.execute('SELECT id,owner_id,project_id,derived_manifest FROM deletion_receipts WHERE project_id=?',(project['id'],)).fetchone()
            assert receipt and db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
            assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
            assert db.execute('SELECT count(*) FROM projects WHERE id=?',(project['id'],)).fetchone()==(0,)
            assert db.execute('SELECT raw_bytes FROM account_usage WHERE user_id=?',(declared['owner_id'],)).fetchone()==(0,)
        async def saved_read():
            async with leases.acquire(exclusive=True):
                async with worker.acquire():
                    records=retained_inventory(leases.files,[],[dict(id=receipt[0],owner_id=receipt[1],project_id=receipt[2],
                        derived_manifest=json.loads(receipt[3]))],approved_installations=approval_registry)
                    return records
        saved=asyncio.run(saved_read())
        assert len(saved)==1 and saved[0]['manifest']==fixture_manifest
        assert before=={str(p.relative_to(root)):digest(p.read_bytes()) for p in (root/'.profile-retained').rglob('*') if p.is_file()}
        assert not messages
        print(json.dumps(dict(schema='geophysics.private-native-profile-delete/v1',uid=os.geteuid(),kernel=kernel,
            sqlite_version=native_identity[0],sqlite_source_id=native_identity[1],
            actual_q10_readonly_record_sha256=digest(canonical(actual_records[0])),actual_q10_charged_bytes=actual_records[0]['charged_bytes'],
            original_input_sha256=digest(original),fixture_job=job,fixture_archive_sha256=digest(canonical(fixture_manifest)),
            retained_bytes=saved[0]['charged_bytes'],foreign_delete_refused=True,unknown_member_preserved=True,
            actual_existing_http_delete=True,deleted_saved_custody_reverified=True,archive_bytes_unchanged=True,
            raw_quota_zero_after_logical_delete=True,mail_messages=len(messages),scientific_execution_performed=False,
            production_activated=False),sort_keys=True))
    finally:
        leases.close()


if __name__=='__main__': main()
