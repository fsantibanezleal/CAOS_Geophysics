"""Actual science bytes with isolated SQL/publication cuts, not native approval."""

import base64
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from alembic import command
import pytest

from app.physical_contract import byte_sha, canonical, digest
from app.physical_forest import reserve_child_intent
from app.physical_publication import publish_correction, audit_correction_ancestry
from app.physical_successor import REVISION
from tests.api.test_physical_forest import connect
from tests.ops.physical_sql_fixture import insert, inventory as sql_inventory
from tests.api.test_physical_roots import FixtureFiles
from tests.api.test_physical_successor import successor as successor


ROOT=Path(__file__).resolve().parents[2]
M=1048576


def decoded(value):
    if type(value) is dict:
        if set(value)=={'__fixture_bytes__'}:
            return base64.b64decode(value['__fixture_bytes__'],validate=True)
        return {key:decoded(item) for key,item in value.items()}
    return value


@pytest.fixture(scope='session')
def actual_science(tmp_path_factory):
    interpreter=os.environ['GEOPHYSICS_SCIENCE_TEST_PYTHON']
    root=tmp_path_factory.mktemp('actual-science')
    target=root/'packet.json'
    result=subprocess.run([interpreter,'-I','-B',str(ROOT/'tests/ops/physical_science_fixture.py'),str(target)],
                          cwd=root,capture_output=True,timeout=120)
    assert result.returncode==0, result.stderr.decode()
    return decoded(json.loads(target.read_bytes()))


@pytest.fixture
def publication(successor,actual_science):
    config,path=successor
    command.upgrade(config,REVISION)
    packet=deepcopy(actual_science)
    parent=json.loads(packet['input_bytes'])
    child=json.loads(packet['child_bytes'])
    req=json.loads(packet['request_bytes'])
    owner,project,raw,root,job_id=(req[k] for k in ('owner_id','project_id','raw_asset_id','root_dataset_id','job_id'))
    source_id,batch,intent=[str(uuid4()) for _ in range(3)]
    raw_body=canonical(parent['payload'])
    assert len(raw_body)==req['raw_bytes'] and byte_sha(raw_body)==req['raw_sha256']
    private=path.parent/'private'
    private.mkdir()
    files=FixtureFiles(private)
    complete=dict(schema='geophysics.physical-child-completion/v1',job_id=job_id,method_id=req['method_id'],
                  scientific_request_sha256=req['scientific_request_sha256'],scientific_result_sha256=child['scientific_payload_sha256'],
                  output_bytes=len(canonical(child['payload'],scientific=True)),output_sha256=byte_sha(canonical(child['payload'],scientific=True)),scientific_verdict='passed')
    staged=[('input_spool',None,'input.json',packet['input_bytes'],16*M),
            ('request_spool',None,'request.json',packet['request_bytes'],34*M),
            ('dataset_copy',child['dataset_id'],'dataset.json',packet['child_bytes'],16*M),
            ('result_copy',job_id,'result.json',packet['result_bytes'],64*M),
            ('scientific_output',None,'scientific.json',canonical(child['payload'],scientific=True),16*M),
            ('completion',None,'complete.json',canonical(complete),4096)]
    slots=[]
    for ordinal,(role,artifact,leaf,body,cap) in enumerate(staged,1):
        target=private/f'.job-staging/{job_id}'/leaf
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(body)
        slots.append(dict(ordinal=ordinal,role=role,location='stage',artifact_id=artifact,leaf=leaf,
                          max_bytes=cap,actual_bytes=len(body),actual_sha256=byte_sha(body)))
    raw_key=f'projects/{owner}/{project}/{raw}'
    root_key=f'derived/{owner}/{project}/datasets/{root}.json'
    targets=[]
    for kind,identifier,lane,body in (('dataset',child['dataset_id'],'datasets',packet['child_bytes']),('result',job_id,'results',packet['result_bytes'])):
        key=f'derived/{owner}/{project}/{lane}/{identifier}.json'
        targets.append(dict(kind=kind,artifact_id=identifier,storage_key=key,bytes=len(body),sha256=byte_sha(body)))
        target=private/key
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(body)
    for key,body in ((raw_key,raw_body),(root_key,packet['input_bytes'])):
        target=private/key
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(body)
    inv=dict(schema='geophysics.physical-custody/v1',batch_id=batch,owner_id=owner,project_id=project,
             origin_kind='job_stage',origin_id=job_id,stage_id=job_id,deletion_receipt_id=None,
             raw_asset_id=raw,raw_sha256=req['raw_sha256'],raw_bytes=len(raw_body),parser_version='gravity-stations-json/v1',
             method_id=req['method_id'],capacity_bytes=256*M,initial_files=slots,removed_ordinals=[])
    body=canonical(inv)
    with connect(path) as db:
        db.execute('INSERT INTO user VALUES(?,?,?,1,0,1)',(owner,owner+'@example.org','fixture-not-a-login'))
        insert(db,'projects',dict(id=project,owner_id=owner,name='Actual science control',description='',created_at='2026-10-08 01:00:00',updated_at='2026-10-08 01:00:00'))
        insert(db,'source_records',dict(parent['source'],id=source_id,project_id=project,owner_id=owner,original_filename='survey.json',version=1,
               retrieved_at='2026-10-08 01:00:00',declared_format='gravity_stations_json',private_storage_permission='attested',sha256=req['raw_sha256'],expected_bytes=len(raw_body)))
        insert(db,'raw_assets',dict(id=raw,owner_id=owner,project_id=project,source_id=source_id,filename='survey.json',client_mime='application/json',
               detected_format='gravity_stations_json',byte_count=len(raw_body),sha256=req['raw_sha256'],storage_key=raw_key,physical_metadata='{}',validation_status='raw_metadata_checked',created_at='2026-10-08 01:00:00'))
        insert(db,'account_usage',dict(user_id=owner,raw_bytes=len(raw_body)))
        insert(db,'physical_dataset_families',dict(root_dataset_id=root,raw_asset_id=raw,owner_id=owner,project_id=project,parser_version='gravity-stations-json/v1',
               state='published',next_ordinal=2,published_count=1,reserved_count=0,created_us=1))
        insert(db,'observation_datasets',dict(id=root,owner_id=owner,project_id=project,raw_asset_id=raw,version=1,parser_version='gravity-stations-json/v1',
               modality='gravity_physical_station',row_count=len(parent['payload']['stations']),raw_sha256=req['raw_sha256'],sha256=req['dataset_sha256'],
               byte_count=len(packet['input_bytes']),storage_key=root_key,created_at='2026-10-08 01:00:00',kind='root',root_dataset_id=root,parent_dataset_id=None,payload_schema='gravity-stations-1'))
        running=dict(packet['job'],state='running',finished_at=None,result_key=None,result_sha256=None,result_bytes=None,wall_ms=None,
                     physical_cpu_ms=None,peak_rss_bytes=None,scratch_bytes=None,physical_fingerprint='d'*64,cancel_requested=0,
                     created_at='2026-10-08 01:00:00',request_json=packet['request_bytes'].decode(),preflight='{"fixture_only":true}')
        insert(db,'processing_jobs',running)
        insert(db,'physical_job_controls',dict(job_id=job_id,owner_id=owner,project_id=project,dataset_id=root,dataset_sha256=req['dataset_sha256'],root_dataset_id=root,
               raw_asset_id=raw,raw_sha256=req['raw_sha256'],raw_bytes=len(raw_body),stage_id=job_id,method_id=req['method_id'],request_sha256=digest(req),
               request_bytes=packet['request_bytes'],submitted_parameters_sha256=req['submitted_parameters_sha256'],scientific_request_sha256=req['scientific_request_sha256'],
               module_manifest_bytes=canonical(req['module_manifest']),module_manifest_sha256=req['module_manifest_sha256'],parent_production_bytes=None,
               permanent_reservation_bytes=80*M,admission_receipt_sha256=req['admission_receipt_sha256'],created_us=1))
        header={k:v for k,v in inv.items() if k not in ('schema','initial_files','removed_ordinals')}
        insert(db,'physical_custody_batches',dict(header,state='sealed',charged_bytes=sum(s['actual_bytes'] for s in slots),
               inventory_bytes=body,inventory_sha256=byte_sha(body),created_us=1,sealed_us=2,removed_us=None))
        for slot in slots:
            insert(db,'physical_custody_files',dict(slot,batch_id=batch,state='present'))
        reserve_child_intent(db,owner_id=owner,project_id=project,parent_dataset_id=root,parent_dataset_sha256=req['dataset_sha256'],job_id=job_id,stage_id=job_id,
                             child_dataset_id=child['dataset_id'],intent_id=intent,created_us=2,targets=targets)
    metrics=dict(wall_ms=20,cpu_ms=10,peak_rss_bytes=1048576,scratch_bytes=4096)
    values=dict(owner_id=owner,project_id=project,intent_id=intent,approved_manifests={digest(packet['approved_manifest']):packet['approved_manifest']},
                metrics=metrics,finished_at=packet['job']['finished_at'])
    return path,files,values,packet


def test_actual_correction_same_commit_all_public_rows_and_retained_debt(publication):
    path,files,values,packet=publication
    with connect(path) as db:
        assert publish_correction(db,files,**values)==packet['snapshot']
        child=db.execute('SELECT * FROM observation_datasets WHERE kind="derived"')
        row=dict(zip((c[0] for c in child.description),child.fetchone()))
        body,snapshot=audit_correction_ancestry(db,files,row,approved_manifests=values['approved_manifests'])
        assert body==packet['child_bytes'] and snapshot==packet['snapshot']
        assert db.execute('SELECT state,wall_ms,physical_cpu_ms FROM processing_jobs').fetchone()==('succeeded',20,10)
        assert db.execute('SELECT permanent_reservation_bytes FROM physical_job_controls').fetchone()==(0,)
        assert db.execute('SELECT published_count,reserved_count,next_ordinal FROM physical_dataset_families').fetchone()==(2,0,3)
        assert db.execute('SELECT state,charged_bytes FROM physical_custody_batches').fetchone()[0]=='cleanup_pending'
        assert not db.execute('SELECT 1 FROM physical_publication_intents').fetchone()
        assert not db.execute('SELECT 1 FROM physical_publication_targets').fetchone()
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]


@pytest.mark.parametrize('cut',['child','production','terminal','retired'])
def test_every_terminal_cut_rolls_back_all_rows_and_keeps_both_installed_copies(publication,cut):
    path,files,values,_=publication
    with connect(path) as db:
        before=sql_inventory(db)
        bodies={str(p.relative_to(files.root)):p.read_bytes() for p in files.root.rglob('*') if p.is_file()}
        def fail(point):
            if point==cut:
                raise RuntimeError('original_publication_cut')
        with pytest.raises(RuntimeError,match='original_publication_cut'):
            publish_correction(db,files,**values,failure_cut=fail)
        assert sql_inventory(db)==before
        assert {str(p.relative_to(files.root)):p.read_bytes() for p in files.root.rglob('*') if p.is_file()}==bodies
        assert db.execute('SELECT state FROM processing_jobs').fetchone()==('running',)


@pytest.mark.parametrize('damage',['cancel','unregistered','telemetry','missing_result','wrong_dataset','extra_stage','stale_control','forged_original',
                                    'native_request_changed','control_raw_hash','control_raw_bytes'])
def test_cancellation_partial_or_forged_bytes_never_publish_or_release(publication,damage):
    path,files,values,packet=publication
    values=deepcopy(values)
    with connect(path) as db:
        if damage=='cancel':
            db.execute('UPDATE processing_jobs SET cancel_requested=1')
        elif damage=='unregistered':
            values['approved_manifests']={}
        elif damage=='telemetry':
            values['metrics']['cpu_ms']+=1
        elif damage=='missing_result':
            target=files.root/packet['job']['result_key']
            target.rename(target.with_name('retained-original-result'))
        elif damage=='wrong_dataset':
            parent=json.loads(packet['child_bytes'])
            target=files.root/f"derived/{values['owner_id']}/{values['project_id']}/datasets/{parent['dataset_id']}.json"
            target.write_bytes(b'wrong preserved target')
        elif damage=='extra_stage':
            (files.root/f".job-staging/{packet['job']['id']}/unknown").write_bytes(b'unknown retained')
        elif damage=='stale_control':
            db.execute("UPDATE physical_job_controls SET module_manifest_sha256=?",('0'*64,))
        elif damage=='forged_original':
            root=json.loads(packet['input_bytes'])
            (files.root/f"projects/{values['owner_id']}/{values['project_id']}/{root['raw_asset_id']}").write_bytes(b'wrong original retained')
        elif damage=='native_request_changed':
            db.execute("UPDATE processing_jobs SET request_json=?",('{"forged":true}',))
        elif damage=='control_raw_hash':
            db.execute('UPDATE physical_job_controls SET raw_sha256=?',('0'*64,))
        elif damage=='control_raw_bytes':
            db.execute('UPDATE physical_job_controls SET raw_bytes=raw_bytes+1')
        before=sql_inventory(db)
        bodies={str(p.relative_to(files.root)):p.read_bytes() for p in files.root.rglob('*') if p.is_file()}
        with pytest.raises((ValueError,OSError,AssertionError)):
            publish_correction(db,files,**values)
        assert sql_inventory(db)==before
        assert {str(p.relative_to(files.root)):p.read_bytes() for p in files.root.rglob('*') if p.is_file()}==bodies
        assert db.execute('SELECT permanent_reservation_bytes FROM physical_job_controls').fetchone()==(80*M,)


def test_emit_exact_prepared_native_fixture(publication,tmp_path):
    """External trusted drill input; no scientific/runtime receipt invented."""
    path,files,values,packet=publication
    record=dict(database=str(path),private_root=str(files.root),values=values,snapshot=packet['snapshot'])
    (tmp_path/'native-derived-input.json').write_bytes(canonical(record))
    with connect(path) as db:
        assert db.execute('SELECT state FROM processing_jobs').fetchone()==('running',)
        assert db.execute('SELECT count(*) FROM physical_publication_targets').fetchone()==(2,)
