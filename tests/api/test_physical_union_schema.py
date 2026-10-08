"""Actual combined copied-fixture chain; no default mount or science claim."""
import hashlib
import json
import sqlite3
import subprocess
from uuid import uuid4

from alembic import command
import pytest

from app.physical_successor import ddl_sha256
from tests.api.test_physical_persistence_schema import seed, inventory, insert
from tests.api.test_physical_successor import ROOTS
from tests.ops.physical_union_fixture import capsule, mount_packet

R4='0004_waveform_artifacts'
R5='0005_physical_forest'
R6='0006_joint_artifacts'
R7='0007_magnetic_line_artifacts'


def snapshot(path):
    with sqlite3.connect(path) as db:
        return (db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall(),
                inventory(db),db.execute('SELECT version_num FROM alembic_version').fetchall())


@pytest.fixture
def union(tmp_path,monkeypatch):
    config,path=capsule(tmp_path/'copied-union')
    predecessor=path.with_name('retained-0004.sqlite3')
    monkeypatch.setenv('GEOPHYSICS_DB_PATH',str(predecessor))
    monkeypatch.setenv('GEOPHYSICS_CANDIDATE_ROOT',str(path.parent))
    command.upgrade(config,R4)
    with sqlite3.connect(predecessor) as db:
        ids=[]
        for parser,modality,_ in ROOTS:
            owner,project,raw,dataset,job=seed(db,parser=parser,modality=modality)
            ids.append((owner,project,raw,dataset,job))
            if modality=='waveform_counts_response':
                source=db.execute('SELECT source_id FROM raw_assets WHERE id=?',(raw,)).fetchone()[0]
                db.execute("UPDATE processing_jobs SET method_id='seismic.waveform-qc-classical/v1' WHERE id=?",(job,))
                db.execute('INSERT INTO waveform_dataset_sources VALUES (?,?,?,?,?,?,?)',(dataset,'counts',raw,source,'a'*64,7,1))
                db.execute('INSERT INTO waveform_result_artifacts VALUES (?,?,?,?,?)',(job,'receipt.json','immutable-waveform-'+job,19,'d'*64))
            elif modality in ('ert_profile','traveltime_profile'):
                method='ert.topographic-profile/v1' if modality=='ert_profile' else 'traveltime.first-arrival-profile/v1'
                fmt='ert_ohm' if modality=='ert_profile' else 'traveltime_sgt'
                db.execute('UPDATE processing_jobs SET method_id=? WHERE id=?',(method,job))
                db.execute('UPDATE raw_assets SET detected_format=? WHERE id=?',(fmt,raw))
                db.execute('UPDATE source_records SET declared_format=? WHERE id=(SELECT source_id FROM raw_assets WHERE id=?)',(fmt,raw))
        db.commit();before=inventory(db)
        # Real SQLite consistent copy of the closed plural0004 fixture. The
        # retained predecessor is never migrated, edited, stamped or replaced.
        with sqlite3.connect(path) as target: db.backup(target)
    predecessor_sha=hashlib.sha256(predecessor.read_bytes()).hexdigest()
    monkeypatch.setenv('GEOPHYSICS_DB_PATH',str(path))
    originals=path.parent/'retained-original.bin'
    originals.write_bytes(b'original copied custody\x00\xff\n')
    original_sha=hashlib.sha256(originals.read_bytes()).hexdigest()
    yield config,path,ids,before
    assert hashlib.sha256(originals.read_bytes()).hexdigest()==original_sha
    assert hashlib.sha256(predecessor.read_bytes()).hexdigest()==predecessor_sha
    assert not path.with_name(path.name+'-wal').exists()


def healthy(path,revision):
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT version_num FROM alembic_version').fetchall()==[(revision,)]
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
        assert db.execute('SELECT count(*) FROM user').fetchone()==(5,)
        print('UNION_DDL_'+revision+'='+ddl_sha256(db))


def test_literal_one_head_up_retained_rows_empty_down_and_m01_refusal(union):
    config,path,_,before=union
    for revision in (R5,R6,R7):
        command.upgrade(config,revision)
        with sqlite3.connect(path) as db:
            for table,(columns,rows) in before.items():
                projection=','.join(f'"{c}",typeof("{c}")' for c in columns)
                assert db.execute(f'SELECT {projection} FROM "{table}" ORDER BY 1').fetchall()==rows
        healthy(path,revision)
    command.downgrade(config,R6);healthy(path,R6)
    command.downgrade(config,R5);healthy(path,R5)
    saved=snapshot(path)
    with pytest.raises(ValueError,match='successor_downgrade_forbidden'):
        command.downgrade(config,R4)
    assert snapshot(path)==saved


@pytest.mark.parametrize('table',['magnetic_survey_intakes','magnetic_survey_admissions',
    'magnetic_survey_attempts','magnetic_survey_members','magnetic_survey_exports'])
def test_every_m03_retained_custody_table_refuses_before_any_drop(table,union):
    config,path,ids,_=union;command.upgrade(config,R7)
    owner,project,raw,dataset,job=ids[0]
    intake,attempt,member,export=[str(uuid4()) for _ in range(4)]
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA foreign_keys=ON')
        if table=='magnetic_survey_intakes':
            db.execute('INSERT INTO magnetic_survey_intakes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                (intake,owner,project,'original','{}','failed',32,7,'[]',None,raw,'2026-10-08'))
        elif table=='magnetic_survey_admissions':
            db.execute('INSERT INTO magnetic_survey_admissions VALUES (?,?,?,?,?)',(job,'{}','[]','a'*64,32))
        else:
            db.execute('INSERT INTO magnetic_survey_attempts VALUES (?,?,?,?,?,?,?,?,?,?)',
                (attempt,job,1,'drained','fixture','2026-10-08',None,None,7,'[]'))
            if table in ('magnetic_survey_members','magnetic_survey_exports'):
                db.execute('INSERT INTO magnetic_survey_members VALUES (?,?,?,?,?,?)',(member,attempt,'receipt.json',7,'a'*64,'receipt'))
            if table=='magnetic_survey_exports':
                db.execute('INSERT INTO magnetic_survey_exports VALUES (?,?,?,?,?,?,?)',(export,attempt,'private',member,7,'a'*64,'2026-10-08'))
        db.commit()
    before=snapshot(path)
    with pytest.raises(RuntimeError,match='m03_custody_retained'):
        command.downgrade(config,R6)
    assert snapshot(path)==before


def test_joint_retained_dependency_refuses_and_preserves_m01_debt(union):
    config,path,ids,_=union;command.upgrade(config,R5)
    owner,project,raw,dataset,job=ids[0]
    batch=str(uuid4())
    with sqlite3.connect(path) as db:
        insert(db,'physical_custody_batches',dict(batch_id=batch,owner_id=owner,project_id=project,
            origin_kind='root_stage',origin_id=batch,stage_id=batch,deletion_receipt_id=None,
            raw_asset_id=raw,raw_sha256='a'*64,raw_bytes=7,parser_version='gravity-stations-json/v1',method_id=None,
            state='reserved',capacity_bytes=32*1048576,charged_bytes=32*1048576,inventory_bytes=None,
            inventory_sha256=None,created_us=1,sealed_us=None,removed_us=None))
    retained=snapshot(path)[1]['physical_custody_batches']
    command.upgrade(config,R7)
    command.downgrade(config,R6)
    with sqlite3.connect(path) as db:
        assert inventory(db)['physical_custody_batches']==retained
        source=db.execute('SELECT source_id FROM raw_assets WHERE id=?',(raw,)).fetchone()[0]
        db.execute('INSERT INTO joint_dataset_sources VALUES (?,?,?,?,?,?,?,?)',(dataset,'development','request.json',raw,source,'a'*64,7,1))
    before=snapshot(path)
    with pytest.raises(ValueError,match='joint_downgrade_retained_custody_refused'):
        command.downgrade(config,R5)
    assert snapshot(path)==before


@pytest.mark.parametrize('field',['owner','project','dataset','hash','request'])
def test_plural_joint_artifact_identity_constraint_survives_m03(field,union):
    config,path,ids,_=union;command.upgrade(config,R7)
    owner,project,raw,dataset,job=ids[0]
    row=[job,'instrument/manifest.json',owner,project,dataset,'b'*64,'joint.gravity-magnetic-native/v1','c'*64,
         f'derived/{owner}/{project}/joint/{job}/instrument/manifest.json',19,'d'*64]
    with sqlite3.connect(path) as db:
        db.execute("UPDATE processing_jobs SET method_id='joint.gravity-magnetic-native/v1' WHERE id=?",(job,))
        db.commit();db.execute('PRAGMA foreign_keys=ON')
        changed=list(row)
        index={'owner':2,'project':3,'dataset':4,'hash':5,'request':7}[field]
        changed[index]={'owner':ids[1][0],'project':ids[1][1],'dataset':ids[1][3]}.get(field,'e'*64)
        if field in ('owner','project'):
            changed[8]=f'derived/{changed[2]}/{changed[3]}/joint/{job}/instrument/manifest.json'
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('INSERT INTO joint_result_artifacts VALUES (?,?,?,?,?,?,?,?,?,?,?)',changed)
        db.execute('INSERT INTO joint_result_artifacts VALUES (?,?,?,?,?,?,?,?,?,?,?)',row)
        with pytest.raises(sqlite3.IntegrityError): db.execute('DELETE FROM processing_jobs WHERE id=?',(job,))
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_m03_cross_owner_intake_is_not_granted_by_separate_foreign_keys(union):
    """Required adverse gate: exact literal DDL cannot prove composite ownership."""
    config,path,ids,_=union;command.upgrade(config,R7)
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA foreign_keys=ON')
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('INSERT INTO magnetic_survey_intakes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                (str(uuid4()),ids[1][0],ids[0][1],'original','{}','failed',32,7,'[]',None,ids[0][2],'2026-10-08'))


@pytest.mark.parametrize('field',['owner_id','project_id'])
def test_plural_physical_dataset_family_identity_survives_union(field,union):
    config,path,ids,_=union;command.upgrade(config,R7)
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA foreign_keys=ON')
        value=ids[1][0 if field=='owner_id' else 1]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(f'UPDATE observation_datasets SET {field}=? WHERE id=?',(value,ids[0][3]))
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]


@pytest.mark.parametrize('revision,cut',[(R6,'dataset_copy'),(R6,'dataset_rename'),
    (R6,'joint_dataset_sources'),(R6,'joint_result_artifacts'),(R6,'checked'),
    (R7,'table'),(R7,'revision_before'),(R7,'revision_after')])
def test_actual_combined_migration_cut_keeps_ddl_rows_and_head(revision,cut,union):
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    config,path,_,_=union
    command.upgrade(config,R5 if revision==R6 else R6)
    before=snapshot(path)
    def fail(name):
        if name==cut: raise ValueError('union_injected_cut')
    def sql_fail(connection,cursor,statement,parameters,context,executemany):
        if ((cut=='table' and statement.lstrip().startswith('CREATE TABLE magnetic_survey_attempts'))
            or (cut.startswith('revision_') and statement.startswith('UPDATE alembic_version'))):
            raise ValueError('union_injected_cut')
    config.attributes['m11_successor_failure_cut']=fail
    event_name='after_cursor_execute' if cut=='revision_after' else 'before_cursor_execute'
    if revision==R7: event.listen(Engine,event_name,sql_fail)
    try:
        with pytest.raises(ValueError,match='union_injected_cut'): command.upgrade(config,revision)
    finally:
        if revision==R7: event.remove(Engine,event_name,sql_fail)
    assert snapshot(path)==before


def test_emitted_parent_mount_patch_preserves_every_literal_source(tmp_path):
    packet=tmp_path/'mount-packet';mount_packet(packet)
    manifest=json.loads((packet/'manifest.json').read_bytes())
    patch=packet/'migration-mount.patch'
    assert hashlib.sha256(patch.read_bytes()).hexdigest()==manifest['patch_sha256']
    target=tmp_path/'private-union-mount';target.mkdir()
    subprocess.run(['git','-c','core.autocrlf=false','apply','--check',str(patch)],cwd=target,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','apply',str(patch)],cwd=target,check=True,capture_output=True)
    for record in manifest['records']:
        body=(target/record['target']).read_bytes()
        assert len(body)==record['bytes'] and hashlib.sha256(body).hexdigest()==record['sha256']
