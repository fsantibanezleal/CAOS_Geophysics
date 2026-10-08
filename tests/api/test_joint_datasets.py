"""Actual M08-predecessor/native dependency migration and private API controls."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3

import pytest

from app import joint_contract as native
from app import joint_datasets as joint
from test_joint_protected import joint_harness, original_member, upload_member


@pytest.fixture
def dataset_harness(joint_harness,monkeypatch):
    from alembic import command
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, select, text
    from app import database, processing_contract, processing, processing_storage, server
    from app.joint_models import JointDatasetSource
    from app.joint_schema import upgrade
    from app.models import ObservationDataset

    # Read-only official committed prerequisite. No copied M08 source/MAIN edits.
    migration = Path(os.environ['GEOPHYSICS_M11_M08_MIGRATION'])
    assert hashlib.sha256(migration.read_bytes()).hexdigest() == '82c827b94940d803fae42eb7137fda63f2b4d816e11dddd481f79c5b3cb41ac3'
    spec = importlib.util.spec_from_file_location('joint_actual_m08_predecessor',migration)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    original_upgrade = command.upgrade
    def apply(config,revision):
        original_upgrade(config,revision)
        engine = create_engine('sqlite:///'+Path(os.environ['GEOPHYSICS_DB_PATH']).as_posix())
        with engine.begin() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                module.upgrade()
                connection.execute(text("UPDATE alembic_version SET version_num='0004_waveform_artifacts'"))
                upgrade(Operations(context))
                connection.execute(text("UPDATE alembic_version SET version_num='0005_joint_native_sources'"))
        engine.dispose()
    monkeypatch.setattr(command,'upgrade',apply)
    monkeypatch.setattr(database,'MIGRATION_HEAD','0005_joint_native_sources')
    original_validator = processing_contract.validate_dataset_identity
    def validate(payload,dataset):
        if dataset.modality == native.MODALITY: return joint.validate_dataset(payload,dataset)
        return original_validator(payload,dataset)
    for target in (processing_contract,processing,database,processing_storage):
        monkeypatch.setattr(target,'validate_dataset_identity',validate)
    original_audit = server.reconcile_private_files
    async def audit(settings,sessions):
        await original_audit(settings,sessions)
        async with sessions() as session:
            datasets = (await session.execute(select(ObservationDataset).where(ObservationDataset.modality==native.MODALITY))).scalars().all()
            await joint.audit_dependencies(settings,session,datasets)
    monkeypatch.setattr(server,'reconcile_private_files',audit)
    original_install = server.install_processing_routes
    def install(app,settings,current_user,get_session):
        original_install(app,settings,current_user,get_session)
        joint.install_joint_dataset_routes(app,settings,current_user,get_session)
    monkeypatch.setattr(server,'install_processing_routes',install)
    return joint_harness


def upload_pair(harness,project):
    root = Path(os.environ['GEOPHYSICS_JOINT_MATRIX_FIXTURE'])/'joint-control-00'
    members = {}
    for role in ('development','sealed'):
        members[role] = {}
        for path in sorted((root/role).iterdir()):
            response = upload_member(harness,project,role,path.name)
            assert response.status_code == 201,response.text
            members[role][path.name] = response.json()['asset_id']
    return members


def create_dataset(harness,project,members):
    return harness.request('POST',f'/api/projects/{project}/joint-datasets',json=members)


def test_actual_dataset_dependencies_and_lifecycle(dataset_harness,tmp_path):
    from fastapi.testclient import TestClient
    from app.server import create_app
    harness=dataset_harness();harness.account();project=harness.project()['id']
    members = upload_pair(harness,project)
    response = create_dataset(harness,project,members)
    assert response.status_code == 201,response.text
    receipt = response.json(); assert receipt['scientific_accepted'] is False
    downloaded = harness.request('GET',receipt['receipt_url'])
    assert downloaded.status_code == 200,downloaded.text
    assert downloaded.headers['cache-control']=='no-store'
    payload = downloaded.json()
    assert payload['scientific_values_decoded'] is False and payload['scientific_accepted'] is False
    assert payload['dimensions']=={'source_observations':96}
    async def materialize():
        from app.models import ObservationDataset
        stage=tmp_path/'actual-native-stage';stage.mkdir()
        async with harness.app.state.sessions() as session:
            dataset=await session.get(ObservationDataset,receipt['dataset_id'])
            paths=await joint.materialize_inputs(harness.settings,session,dataset,payload,stage)
            for role,directory in paths.items():
                for name in members[role]: assert (directory/name).read_bytes()==original_member(role,name)[0]
            with pytest.raises(ValueError,match='exclusive_stage'):
                await joint.materialize_inputs(harness.settings,session,dataset,payload,stage)
    harness.client.portal.call(materialize)
    assert create_dataset(harness,project,members).status_code==409
    with sqlite3.connect(harness.settings.db_path) as connection:
        assert connection.execute('SELECT count(*) FROM joint_dataset_sources').fetchone()[0]==sum(map(len,members.values()))
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='0005_joint_native_sources'
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='waveform_result_artifacts'").fetchone()
    # Real canonical startup/derived quota/index download plus explicit source union.
    async def mail(*args): pass
    with TestClient(create_app(harness.settings,mail)) as reopened:
        assert reopened.get('/api/auth/csrf').status_code==200
    # Corruption bypassing SQLite FK enforcement is not accepted at startup.
    orphan='55555555-5555-4555-8555-555555555555'
    with sqlite3.connect(harness.settings.db_path) as connection:
        connection.execute('INSERT INTO joint_dataset_sources SELECT ?,role,name,asset_id,source_id,raw_sha256,raw_bytes,source_version FROM joint_dataset_sources LIMIT 1',(orphan,))
    with pytest.raises(ValueError,match='orphan_dependency'):
        with TestClient(create_app(harness.settings,mail)): pass
    with sqlite3.connect(harness.settings.db_path) as connection:
        connection.execute('DELETE FROM joint_dataset_sources WHERE dataset_id=?',(orphan,))
    canonical=harness.request('GET',f'/api/projects/{project}/datasets/{receipt["dataset_id"]}')
    assert canonical.status_code==200 and canonical.json()==payload
    deleted=harness.request('DELETE',f'/api/projects/{project}')
    assert deleted.status_code==200,deleted.text
    with sqlite3.connect(harness.settings.db_path) as connection:
        assert connection.execute('SELECT count(*) FROM joint_dataset_sources').fetchone()[0]==0
    with TestClient(create_app(harness.settings,mail)) as reopened:
        assert reopened.get('/api/auth/csrf').status_code==200


def test_dataset_request_closed_bound_before_source_reads(dataset_harness,monkeypatch):
    harness=dataset_harness();harness.account();project=harness.project()['id']
    calls=[]
    def forbidden(*args): calls.append(args);raise AssertionError('invalid request scanned originals')
    monkeypatch.setattr(joint,'scan_member',forbidden)
    bad=[{}, {'development':{},'sealed':{}}, {'development':{'request.json':'bad'},'sealed':{}},
        {'development':{'../../escape':'11111111-1111-4111-8111-111111111111'},'sealed':{}}]
    for members in bad: assert create_dataset(harness,project,members).status_code==422
    url=f'/api/projects/{project}/joint-datasets'
    assert harness.request('POST',url,content=b'{"development":{},"development":{},"sealed":{}}').status_code==422
    assert harness.request('POST',url,content=b' '*65537).status_code==413
    assert not calls


def test_missing_extra_wrong_role_or_cross_owner_reject(dataset_harness):
    harness=dataset_harness();harness.account();project=harness.project()['id'];members=upload_pair(harness,project)
    altered=json.loads(json.dumps(members));del altered['sealed']['gravity_rows.npy']
    assert create_dataset(harness,project,altered).status_code==422
    altered=json.loads(json.dumps(members));altered['development']['density_start.npy']=members['development']['density_reference.npy']
    assert create_dataset(harness,project,altered).status_code==422
    second=harness.project('Other owned project')['id']
    assert create_dataset(harness,second,members).status_code==404
    response=create_dataset(harness,project,members);assert response.status_code==201
    harness.account('other-owner@example.org')
    assert harness.request('GET',response.json()['receipt_url']).status_code==404
    assert create_dataset(harness,project,members).status_code==404


@pytest.mark.parametrize('changed',['source_version','dependency','bytes','missing'])
def test_actual_dependency_tampering_blocks_access(dataset_harness,changed):
    harness=dataset_harness();harness.account();project=harness.project()['id'];members=upload_pair(harness,project)
    receipt=create_dataset(harness,project,members);assert receipt.status_code==201,receipt.text
    asset=members['sealed']['gravity_observed.npy']
    with sqlite3.connect(harness.settings.db_path) as connection:
        source,key=connection.execute('SELECT source_id,storage_key FROM raw_assets WHERE id=?',(asset,)).fetchone()
        if changed=='source_version': connection.execute('UPDATE source_records SET version=version+1 WHERE id=?',(source,))
        if changed=='dependency': connection.execute("UPDATE joint_dataset_sources SET raw_sha256=? WHERE asset_id=?",('a'*64,asset))
    if changed in ('bytes','missing'):
        path=harness.settings.data_dir/key
        if changed=='bytes':
            # Mechanical corruption in an isolated generated fixture, not user input.
            with path.open('r+b') as stream:
                stream.seek(-1,2);value=stream.read(1);stream.seek(-1,2);stream.write(bytes([value[0]^1]))
        else: path.rename(path.with_name(path.name+'.retained'))
    assert harness.request('GET',receipt.json()['receipt_url']).status_code==409


@pytest.mark.parametrize('committed',[False,True])
def test_uncertain_dataset_commit_preserves_index(dataset_harness,monkeypatch,committed):
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi.testclient import TestClient
    from app.server import create_app
    harness=dataset_harness();harness.account();project=harness.project()['id'];members=upload_pair(harness,project)
    original=AsyncSession.commit;triggered=False
    async def uncertain(session):
        nonlocal triggered
        root=harness.settings.data_dir/'derived'
        if not triggered and root.exists() and any(p.is_file() for p in root.rglob('*')):
            triggered=True
            if committed: await original(session)
            raise RuntimeError('dataset_unknown_commit_outcome')
        return await original(session)
    monkeypatch.setattr(AsyncSession,'commit',uncertain)
    with pytest.raises(RuntimeError,match='dataset_unknown_commit_outcome'): create_dataset(harness,project,members)
    assert triggered
    indexes=list((harness.settings.data_dir/'derived').rglob('*.json'));assert len(indexes)==1
    payload=json.loads(indexes[0].read_bytes());assert payload['scientific_accepted'] is False
    async def mail(*args): pass
    if committed:
        with TestClient(create_app(harness.settings,mail)) as reopened: assert reopened.get('/api/auth/csrf').status_code==200
        assert harness.request('GET',f'/api/projects/{project}/joint-datasets/{payload["dataset_id"]}').status_code==200
    else:
        with pytest.raises(RuntimeError,match='private_recovery_required'):
            with TestClient(create_app(harness.settings,mail)): pass


def test_migration_refuses_missing_predecessor_before_create(tmp_path):
    from sqlalchemy import create_engine,text
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from app.joint_schema import upgrade
    engine=create_engine('sqlite:///'+(tmp_path/'refusal.sqlite3').as_posix())
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE alembic_version(version_num VARCHAR(32))'))
        connection.execute(text("INSERT INTO alembic_version VALUES('0003_processing_jobs')"))
        with pytest.raises(RuntimeError,match='M08 predecessor'): upgrade(Operations(MigrationContext.configure(connection)))
        assert not connection.execute(text("SELECT name FROM sqlite_master WHERE name='joint_dataset_sources'")).fetchall()
        connection.execute(text("UPDATE alembic_version SET version_num='0004_waveform_artifacts'"))
        with pytest.raises(RuntimeError,match='actual M08 predecessor'): upgrade(Operations(MigrationContext.configure(connection)))
        assert not connection.execute(text("SELECT name FROM sqlite_master WHERE name='joint_dataset_sources'")).fetchall()
    engine.dispose()


def test_held_file_exact_identity_and_mutation(tmp_path):
    from types import SimpleNamespace
    from uuid import UUID
    owner=UUID('11111111-1111-4111-8111-111111111111')
    project='22222222-2222-4222-8222-222222222222';asset_id='33333333-3333-4333-8333-333333333333'
    key=f'projects/{owner}/{project}/{asset_id}';path=tmp_path/key;path.parent.mkdir(parents=True)
    path.write_bytes(b'original')
    asset=SimpleNamespace(owner_id=owner,project_id=project,id=asset_id,storage_key=key,byte_count=8)
    with joint.held_original(SimpleNamespace(data_dir=tmp_path),asset) as stream: assert stream.read()==b'original'
    with pytest.raises(ValueError,match='file_changed'):
        with joint.held_original(SimpleNamespace(data_dir=tmp_path),asset) as stream:
            before=path.stat();path.write_bytes(b'changed!')
            os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns+1000000000))
    asset.byte_count=9
    with pytest.raises(ValueError,match='file_size'):
        with joint.held_original(SimpleNamespace(data_dir=tmp_path),asset): pass
