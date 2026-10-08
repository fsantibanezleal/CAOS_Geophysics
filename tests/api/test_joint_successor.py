"""Literal allocated schema, immutable public predecessor and rollback controls.

No science, canonical registry change, host activation or private migration.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest

from app import joint_successor as joint
from app.joint_models import JointDatasetSource, JointResultArtifact

OWN = Path(__file__).resolve().parents[2]
M01_COMMIT = '16b911dc58744c53e936677436a63370dbc0c02b'
PINS = {
    'app/migrations/versions/0001_api_foundation.py':'f595ce71642f8555c9a7e3e615aeccf1f642eaf2a1be09f8864b25a8797e52ae',
    'app/migrations/versions/0002_private_storage_permission.py':'572a55739d70b0fc54f6bfdc3fa19ed3ab514fac2136feb817a3c8c89f2551ca',
    'app/migrations/versions/0003_processing_jobs.py':'06a9437a41e6665e1689cb85af0789c741e420dc380888139ed138c2abe4939f',
    'app/migrations/candidates/0004_waveform_artifacts.py':'82c827b94940d803fae42eb7137fda63f2b4d816e11dddd481f79c5b3cb41ac3',
    'app/migrations/candidates/0005_physical_forest.py':'77610d1f49dc1ffe2b4cd8bbb5c8f3afa39c63266c1a89850c2f17afa7803a8f',
    'app/physical_persistence.py':'37281cd0af47128b72f9783834e2aafb00a826a97e9d716dfc5727bd0637ce2a',
    'app/physical_successor.py':'0ec64cc98ce35cea03ede8eb97a3b0641ae5cc37b18befde7f1e76b222f9f97d',
    'app/migrations/physical_successor/env.py':'50e71e32a227481f92e420cb7d54e5e9d2c0c15762f7a6f0ed1643ed334aeb2b',
}


@pytest.fixture
def successor(tmp_path,monkeypatch):
    root=Path(os.environ['GEOPHYSICS_M11_M01_PREREQUISITE']).resolve(strict=True)
    assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==M01_COMMIT
    assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain'],text=True).strip()
    for name,pin in PINS.items(): assert hashlib.sha256((root/name).read_bytes()).hexdigest()==pin,name
    for leaf in ('physical_persistence','physical_successor'):
        name='app.'+leaf
        spec=importlib.util.spec_from_file_location(name,root/'app'/f'{leaf}.py')
        module=importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules,name,module);spec.loader.exec_module(module)
    versions=tmp_path/'versions';versions.mkdir()
    for name in PINS:
        if '/versions/' in name or '/candidates/' in name: shutil.copyfile(root/name,versions/Path(name).name)
    shutil.copyfile(OWN/'app/migrations/candidates/0006_joint_artifacts.py',versions/'0006_joint_artifacts.py')
    config=Config(str(OWN/'app/alembic.ini'))
    config.set_main_option('script_location',str(root/'app/migrations/physical_successor'))
    config.set_main_option('version_locations',str(versions))
    config.attributes['m01_successor_candidate_only']=True
    path=tmp_path/'joint-allocated.sqlite3'
    monkeypatch.setenv('GEOPHYSICS_DB_PATH',str(path));monkeypatch.setenv('GEOPHYSICS_CANDIDATE_ROOT',str(tmp_path))
    assert ScriptDirectory.from_config(config).get_heads()==[joint.REVISION]
    command.upgrade(config,'0004_waveform_artifacts')
    with sqlite3.connect(path) as db:
        identities=[seed(db,parser,modality) for parser,modality in (
            ('gravity-station-csv/v1','gravity_station'),('edi-strict-envelope/v1','edi_transfer_function'),
            ('supplied-profile-original/v1','ert_profile'),('supplied-profile-original/v1','traveltime_profile'),
            ('m08/v1/'+'c'*64,'waveform_counts_response'))]
        owner,project,raw,dataset,job,source=identities[-1]
        db.execute('INSERT INTO waveform_dataset_sources VALUES (?,?,?,?,?,?,?)',(dataset,'counts',raw,source,'a'*64,7,1))
        db.execute('INSERT INTO waveform_result_artifacts VALUES (?,?,?,?,?)',(job,'receipt.json','immutable-waveform',19,'d'*64))
    command.upgrade(config,joint.PREDECESSOR)
    with sqlite3.connect(path) as db: assert joint.ddl_digest(sql_rows(db))==joint.PREDECESSOR_DDL
    yield config,path,identities
    assert not path.with_name(path.name+'-wal').exists()
    assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==pin for name,pin in PINS.items())


def seed(db,parser,modality):
    owner,project,raw,dataset,job,source=[str(uuid4()) for _ in range(6)]
    stamp='2026-09-27 12:00:00.123456';native=' {"epsilon":1.0,"text":"Señal", "nested":null} '
    db.execute('INSERT INTO user VALUES (?,?,?,1,0,1)',(owner,owner+'@example.org','fixture'))
    db.execute('INSERT INTO projects VALUES (?,?,?,?,?,?)',(project,owner,'Joint migration preservation','',stamp,stamp))
    db.execute('INSERT INTO source_records(id,project_id,owner_id,original_filename,version,provider,retrieved_at,rights_statement,rights_decision,declared_format,sha256,attribution) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
               (source,project,owner,'original.csv',1,'fixture',stamp,'original','mirror','gravity_csv','a'*64,'fixture'))
    db.execute('INSERT INTO raw_assets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (raw,project,owner,source,'original.csv','text/csv','gravity_csv',7,'a'*64,f'projects/{owner}/{project}/{raw}',native,'valid',stamp))
    db.execute('INSERT INTO observation_datasets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (dataset,project,owner,raw,1,parser,modality,2,'a'*64,'b'*64,9,f'derived/{owner}/{project}/datasets/{dataset}.json',stamp))
    method={'ert_profile':'ert.topographic-profile/v1','traveltime_profile':'traveltime.first-arrival-profile/v1',
            'waveform_counts_response':'seismic.waveform-qc-classical/v1'}.get(modality,'gravity.station-outlier-flags/v1')
    db.execute('INSERT INTO processing_jobs(id,project_id,owner_id,dataset_id,dataset_sha256,method_id,request_json,request_sha256,preflight,state,cancel_requested,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
               (job,project,owner,dataset,'b'*64,method,native,'c'*64,native,'failed',0,stamp))
    return owner,project,raw,dataset,job,source


def sql_rows(db):
    return db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name').fetchall()


def snapshot(path):
    with sqlite3.connect(path) as db:
        rows={}
        for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            columns=[r[1] for r in db.execute(f'PRAGMA table_info("{name}")')]
            projection=','.join(f'"{c}",typeof("{c}")' for c in columns)
            rows[name]=db.execute(f'SELECT {projection} FROM "{name}" ORDER BY 1').fetchall()
        return sql_rows(db),rows


def test_allocated_schema_preserves_plural_native_rows_and_exact_empty_roundtrip(successor):
    config,path,_=successor;before=snapshot(path)
    command.upgrade(config,joint.REVISION)
    after=snapshot(path)
    assert all(after[1][t]==rows for t,rows in before[1].items() if t!='alembic_version')
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
        assert joint.ROOT in db.execute("SELECT sql FROM sqlite_master WHERE name='observation_datasets'").fetchone()[0]
        for table in (JointDatasetSource.__table__,JointResultArtifact.__table__):
            assert [r[1] for r in db.execute(f'PRAGMA table_info({table.name})')]==list(table.columns.keys())
        print('JOINT_SUCCESSOR_DDL_SHA256='+joint.ddl_digest(sql_rows(db)))
    command.downgrade(config,joint.PREDECESSOR)
    assert snapshot(path)==before
    # M01 owns this refusal; never reinterpret empty0006 downgrade as0005->0004.
    with pytest.raises(ValueError,match='successor_downgrade_forbidden'):
        command.downgrade(config,'0004_waveform_artifacts')
    assert snapshot(path)==before


@pytest.mark.parametrize('cut',['dataset_copy','dataset_rename','joint_dataset_sources','joint_result_artifacts','checked','version_before','version_after'])
def test_every_actual_upgrade_cut_rolls_back_ddl_rows_and_revision(successor,cut):
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    config,path,_=successor;before=snapshot(path)
    def fail(name):
        if name==cut: raise ValueError('joint_injected_cut')
    def revision(connection,cursor,statement,parameters,context,executemany):
        if statement.startswith('UPDATE alembic_version'): raise ValueError('joint_injected_cut')
    config.attributes['m11_successor_failure_cut']=fail
    event_name='before_cursor_execute' if cut=='version_before' else 'after_cursor_execute'
    if cut.startswith('version_'): event.listen(Engine,event_name,revision)
    try:
        with pytest.raises(ValueError,match='joint_injected_cut'): command.upgrade(config,joint.REVISION)
    finally:
        if cut.startswith('version_'): event.remove(Engine,event_name,revision)
    assert snapshot(path)==before
    config.attributes.pop('m11_successor_failure_cut')
    command.upgrade(config,joint.REVISION)


@pytest.mark.parametrize('cut',['drop_joint_result_artifacts','drop_joint_dataset_sources','dataset_copy','dataset_rename','checked','version_before','version_after'])
def test_every_actual_downgrade_cut_preserves_all_successor_state(successor,cut):
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    config,path,_=successor;command.upgrade(config,joint.REVISION);before=snapshot(path)
    def fail(name):
        if name==cut: raise ValueError('joint_injected_cut')
    def revision(connection,cursor,statement,parameters,context,executemany):
        if statement.startswith('UPDATE alembic_version'): raise ValueError('joint_injected_cut')
    config.attributes['m11_successor_failure_cut']=fail
    event_name='before_cursor_execute' if cut=='version_before' else 'after_cursor_execute'
    if cut.startswith('version_'): event.listen(Engine,event_name,revision)
    try:
        with pytest.raises(ValueError,match='joint_injected_cut'): command.downgrade(config,joint.PREDECESSOR)
    finally:
        if cut.startswith('version_'): event.remove(Engine,event_name,revision)
    assert snapshot(path)==before


@pytest.mark.parametrize('sql,error',[
    ('ALTER TABLE projects ADD COLUMN guessed TEXT','unknown_predecessor_ddl'),
    ("UPDATE processing_jobs SET state='running'",'active_job_refusal'),
    ("UPDATE alembic_version SET version_num='0004_waveform_artifacts'",'unsupported_predecessor_ddl'),
    ("UPDATE observation_datasets SET owner_id='ffffffff-ffff-4fff-8fff-ffffffffffff'",'inconsistent_predecessor'),
])
def test_wrong_predecessor_and_active_state_refuse_before_mutation(successor,sql,error):
    config,path,_=successor
    with sqlite3.connect(path) as db: db.execute(sql)
    before=snapshot(path)
    with pytest.raises(ValueError,match=error): command.upgrade(config,joint.REVISION)
    assert snapshot(path)==before


@pytest.mark.parametrize('retained',['dependency','job','artifact','family','root'])
def test_retained_joint_custody_cannot_be_downgraded(successor,retained):
    config,path,ids=successor;command.upgrade(config,joint.REVISION)
    owner,project,raw,dataset,job,source=ids[0]
    with sqlite3.connect(path) as db:
        if retained=='dependency': db.execute('INSERT INTO joint_dataset_sources VALUES (?,?,?,?,?,?,?,?)',(dataset,'development','request.json',raw,source,'a'*64,7,1))
        if retained in ('job','artifact'): db.execute("UPDATE processing_jobs SET method_id='joint.gravity-magnetic-native/v1' WHERE id=?",(job,))
        if retained=='artifact': db.execute('INSERT INTO joint_result_artifacts VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (job,'instrument/manifest.json',owner,project,dataset,'b'*64,'joint.gravity-magnetic-native/v1','c'*64,
             f'derived/{owner}/{project}/joint/{job}/instrument/manifest.json',19,'d'*64))
        if retained in ('family','root'): db.execute("UPDATE physical_dataset_families SET parser_version='m11-native-members/v1' WHERE root_dataset_id=?",(dataset,))
        if retained=='root': db.execute("UPDATE observation_datasets SET parser_version='m11-native-members/v1',modality='joint_gravity_magnetic_native',payload_schema='geophysics.joint-native-dataset/v1' WHERE id=?",(dataset,))
    before=snapshot(path)
    with pytest.raises(ValueError,match='retained_custody_refused' if retained!='family' else 'inconsistent_predecessor'):
        command.downgrade(config,joint.PREDECESSOR)
    assert snapshot(path)==before


@pytest.mark.parametrize('change',['owner','project','dataset','request','hash','method','path','name','dot_segment','bytes','sha','blob_sha'])
def test_artifact_complete_owner_identity_bounds_and_paths_enforced_by_sql(successor,change):
    config,path,ids=successor;command.upgrade(config,joint.REVISION)
    owner,project,_,dataset,job,_=ids[0]
    row=[job,'instrument/manifest.json',owner,project,dataset,'b'*64,'joint.gravity-magnetic-native/v1','c'*64,
         f'derived/{owner}/{project}/joint/{job}/instrument/manifest.json',19,'d'*64]
    with sqlite3.connect(path) as db:
        db.execute("UPDATE processing_jobs SET method_id='joint.gravity-magnetic-native/v1' WHERE id=?",(job,))
        db.commit();db.execute('PRAGMA foreign_keys=ON')
        altered=list(row)
        for key,index in {'owner':2,'project':3,'dataset':4,'request':7,'hash':5}.items():
            if change==key: altered[index]=ids[1][0] if index<5 else 'e'*64
        if change=='method': altered[6]='future/v1'
        if change=='path': altered[8]='derived/foreign/result.json'
        if change=='name': altered[1]='../manifest.json'
        if change=='dot_segment':
            altered[1]='instrument/./manifest.json';altered[8]=f'derived/{owner}/{project}/joint/{job}/instrument/./manifest.json'
        if change=='bytes': altered[9]=268435457
        if change=='sha': altered[10]='G'*64
        if change=='blob_sha': altered[10]=b'd'*64
        with pytest.raises(sqlite3.IntegrityError): db.execute('INSERT INTO joint_result_artifacts VALUES (?,?,?,?,?,?,?,?,?,?,?)',altered)
        db.execute('INSERT INTO joint_result_artifacts VALUES (?,?,?,?,?,?,?,?,?,?,?)',row)
        with pytest.raises(sqlite3.IntegrityError): db.execute('DELETE FROM processing_jobs WHERE id=?',(job,))
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_unknown_successor_object_refuses_downgrade_without_erasure(successor):
    config,path,_=successor;command.upgrade(config,joint.REVISION)
    with sqlite3.connect(path) as db: db.execute('CREATE INDEX future_joint_index ON joint_result_artifacts(sha256)')
    before=snapshot(path)
    with pytest.raises(ValueError,match='unknown_successor_ddl'): command.downgrade(config,joint.PREDECESSOR)
    assert snapshot(path)==before


def test_direct_joint_body_cannot_skip_literal_predecessor(successor):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine
    config,path,_=successor;before=snapshot(path)
    engine=create_engine('sqlite:///'+path.as_posix())
    try:
        with engine.connect() as db:
            db.exec_driver_sql('PRAGMA foreign_keys=OFF');db.commit()
            with db.begin():
                db.exec_driver_sql('BEGIN IMMEDIATE')
                db.exec_driver_sql("UPDATE alembic_version SET version_num='0004_waveform_artifacts'")
                context=MigrationContext.configure(db,opts={'transactional_ddl':True})
                with pytest.raises(ValueError,match='requires_exact_allocated_head'): joint.upgrade(Operations(context))
                db.rollback()
    finally: engine.dispose()
    assert snapshot(path)==before


def test_registration_binds_actual_source_blobs_and_measured_successor(successor):
    config,path,_=successor
    record=json.loads((OWN/'docs/design/features/joint-protected-processing/successor-schema-registration.json').read_bytes())
    assert record['schema']=='geophysics.joint-schema-registration/v1'
    assert (record['revision'],record['down_revision'])==(joint.REVISION,joint.PREDECESSOR)
    assert record['predecessor_commit']==M01_COMMIT and record['predecessor_ddl_sha256']==joint.PREDECESSOR_DDL
    assert set(record['sources'])=={'app/migrations/candidates/0006_joint_artifacts.py','app/joint_successor.py','app/joint_models.py','app/joint_roots.py','app/joint_datasets.py'}
    for name,binding in record['sources'].items():
        body=(OWN/name).read_bytes()
        assert hashlib.sha256(body).hexdigest()==binding['sha256']
        assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==binding['git_blob']
    assert all(record[key] is False for key in ('canonical_mount','source_policy_admitted','scientific_acceptance','native_host_admission'))
    command.upgrade(config,joint.REVISION)
    with sqlite3.connect(path) as db: assert joint.ddl_digest(sql_rows(db))==record['ddl_sha256']


async def original_root(session,ids):
    """Real opaque original role-pair metadata, SQL custody fixture only."""
    from uuid import UUID
    from app import joint_contract as native
    from app.joint_datasets import SCHEMA,close_manifests
    from app.models import SourceRecord,RawAsset,ObservationDataset,utcnow
    root=Path(os.environ['GEOPHYSICS_JOINT_MATRIX_FIXTURE'])/'joint-control-00'
    owner,project,*_=ids
    bindings={};manifests={};primary=None
    for role in ('development','sealed'):
        bindings[role]={}
        main='request.json' if role=='development' else 'sealed.json'
        manifests[role]=native.bounded_json((root/role/main).read_bytes())
        for path in sorted((root/role).iterdir()):
            body=path.read_bytes();digest=hashlib.sha256(body).hexdigest()
            source=SourceRecord(id=str(uuid4()),owner_id=UUID(owner),project_id=project,
                original_filename=path.name,version=1,provider='Actual local originals',
                rights_statement='Explicit private fixture attestation',rights_decision='mirror',
                private_storage_permission='attested',declared_format='joint_native',sha256=digest,
                expected_bytes=len(body),attribution='Original native control00')
            session.add(source);await session.flush()
            descriptor=manifests[role]['arrays'][path.stem] if path.suffix=='.npy' else None
            identity=str(uuid4())
            raw=RawAsset(id=identity,owner_id=UUID(owner),project_id=project,source_id=source.id,
                filename=path.name,client_mime='application/octet-stream',detected_format='joint_native',
                byte_count=len(body),sha256=digest,storage_key=f'projects/{owner}/{project}/{identity}',
                physical_metadata={'schema':'joint-native-member-1','role':role,'name':path.name,
                    'descriptor':descriptor,'scientific_values_decoded':False,'scientific_accepted':False})
            session.add(raw);await session.flush()
            bindings[role][path.name]={**native.source_identity(raw,source,owner_id=UUID(owner),project_id=project),'descriptor':descriptor}
            if role=='development' and path.name==main: primary=raw
    identity=str(uuid4())
    payload={'schema':SCHEMA,'dataset_id':identity,'version':1,'owner_id':owner,'project_id':project,
        'raw_asset_id':primary.id,'parent_raw_sha256':primary.sha256,'parser_version':native.PARSER,
        'modality':native.MODALITY,'dimensions':{},'manifests':manifests,'members':bindings,
        'qc_verdict':'structural_native_members_only','scientific_values_decoded':False,'scientific_accepted':False}
    count=close_manifests(payload);payload['dimensions']={'source_observations':count}
    body=json.dumps(payload,separators=(',',':'),sort_keys=True).encode()
    dataset=ObservationDataset(id=identity,owner_id=UUID(owner),project_id=project,raw_asset_id=primary.id,
        version=1,parser_version=native.PARSER,modality=native.MODALITY,row_count=count,raw_sha256=primary.sha256,
        sha256=hashlib.sha256(body).hexdigest(),byte_count=len(body),storage_key=f'derived/{owner}/{project}/datasets/{identity}.json',created_at=utcnow())
    return dataset,payload


def test_actual_native_family_root_publication_is_one_transaction(successor):
    import asyncio
    from sqlalchemy import event,text
    from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
    from app.joint_roots import register_root
    config,path,ids=successor;command.upgrade(config,joint.REVISION);before=snapshot(path)
    async def execute(commit):
        engine=create_async_engine('sqlite+aiosqlite:///'+path.as_posix())
        @event.listens_for(engine.sync_engine,'connect')
        def foreign_keys(db,record): db.execute('PRAGMA foreign_keys=ON')
        try:
            async with async_sessionmaker(engine,expire_on_commit=False)() as session:
                await session.execute(text('BEGIN IMMEDIATE'))
                draft,payload=await original_root(session,ids[0])
                registered=await register_root(session,draft,payload)
                assert registered.id==draft.id and registered.sha256==draft.sha256
                for role,members in payload['members'].items():
                    for name,binding in members.items(): session.add(JointDatasetSource(dataset_id=draft.id,role=role,name=name,
                        **{k:binding[k] for k in ('asset_id','source_id','raw_sha256','raw_bytes','source_version')}))
                await session.flush()
                family=(await session.execute(text('SELECT root_dataset_id,state,next_ordinal,published_count,reserved_count FROM physical_dataset_families WHERE root_dataset_id=:id'),{'id':draft.id})).one()
                assert tuple(family)==(draft.id,'published',2,1,0)
                assert (await session.execute(text('PRAGMA foreign_key_check'))).all()==[]
                if commit: await session.commit()
                else: await session.rollback()
                return draft.id
        finally: await engine.dispose()
    asyncio.run(execute(False));assert snapshot(path)==before
    identity=asyncio.run(execute(True))
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT kind,root_dataset_id,parent_dataset_id,payload_schema FROM observation_datasets WHERE id=?',(identity,)).fetchone()==('root',identity,None,'geophysics.joint-native-dataset/v1')
        assert db.execute('SELECT count(*) FROM joint_dataset_sources WHERE dataset_id=?',(identity,)).fetchone()==(36,)
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    retained=snapshot(path)
    with pytest.raises(ValueError,match='retained_custody_refused'): command.downgrade(config,joint.PREDECESSOR)
    assert snapshot(path)==retained


@pytest.mark.parametrize('changed',['owner','version','hash','acceptance','head'])
def test_native_root_source_and_authority_contradictions_cannot_publish(successor,changed):
    import asyncio
    from uuid import UUID
    from sqlalchemy import event,text
    from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
    from app.joint_roots import register_root
    config,path,ids=successor;command.upgrade(config,joint.REVISION);before=snapshot(path)
    async def execute():
        engine=create_async_engine('sqlite+aiosqlite:///'+path.as_posix())
        @event.listens_for(engine.sync_engine,'connect')
        def foreign_keys(db,record): db.execute('PRAGMA foreign_keys=ON')
        try:
            async with async_sessionmaker(engine,expire_on_commit=False)() as session:
                await session.execute(text('BEGIN IMMEDIATE'))
                draft,payload=await original_root(session,ids[0])
                if changed=='owner': draft.owner_id=UUID(ids[1][0]);payload['owner_id']=ids[1][0]
                if changed=='version': payload['members']['development']['request.json']['source_version']=2
                if changed=='hash': draft.raw_sha256='f'*64;payload['parent_raw_sha256']='f'*64
                if changed=='acceptance': payload['scientific_accepted']=True
                with pytest.raises(ValueError): await register_root(session,draft,payload,expected_head='0004_waveform_artifacts' if changed=='head' else joint.REVISION)
                assert (await session.execute(text('SELECT count(*) FROM physical_dataset_families WHERE root_dataset_id=:id'),{'id':draft.id})).scalar_one()==0
                await session.rollback()
        finally: await engine.dispose()
    asyncio.run(execute());assert snapshot(path)==before
