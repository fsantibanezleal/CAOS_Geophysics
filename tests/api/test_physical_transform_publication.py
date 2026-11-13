"""Full original transform SCI bytes, candidate SQL/cuts, no telemetry approval."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

import pytest

from app.physical_contract import M, byte_sha, canonical, digest
from app.physical_forest import reserve_child_intent
from app.physical_publication import publish_correction, publish_transform, audit_transform_producer
from tests.api.test_physical_forest import connect
from tests.ops.physical_sql_fixture import insert, inventory as sql_inventory
from tests.api.test_physical_publication import decoded, publication
from tests.api.test_physical_successor import successor as successor

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture(scope='session')
def actual_transforms(tmp_path_factory):
    root=tmp_path_factory.mktemp('actual-transform-science'); target=root/'packet.json'
    result=subprocess.run([os.environ['GEOPHYSICS_SCIENCE_TEST_PYTHON'],'-I','-B',
        str(ROOT/'tests/ops/physical_transform_fixture.py'),str(target)],cwd=root,capture_output=True,timeout=120)
    assert result.returncode==0,result.stderr.decode()
    return decoded(json.loads(target.read_bytes()))


@pytest.fixture(params=[False,True], ids=['original-pass','original-height-non-pass'])
def transform_publication(successor,actual_transforms,request):
    packet=deepcopy(actual_transforms[str(request.param)])
    path,files,correction_values,_=publication.__wrapped__(successor,packet['correction'])
    with connect(path) as db:
        publish_correction(db,files,**correction_values)
    transform=packet['transform']
    req=json.loads(transform['request_bytes']); child=json.loads(transform['child_bytes'])
    job_id,owner,project=(req[k] for k in ('job_id','owner_id','project_id'))
    batch,intent=str(uuid4()),str(uuid4())
    complete=dict(schema='geophysics.physical-child-completion/v1',job_id=job_id,method_id=req['method_id'],
        scientific_request_sha256=req['scientific_request_sha256'],scientific_result_sha256=child['scientific_payload_sha256'],
        output_bytes=len(canonical(child['payload'],scientific=True)),output_sha256=byte_sha(canonical(child['payload'],scientific=True)),
        scientific_verdict=child['production']['scientific_verdict'])
    staged=[('input_spool',None,'input.json',transform['input_bytes'],16*M),
        ('request_spool',None,'request.json',transform['request_bytes'],34*M),
        ('dataset_copy',child['dataset_id'],'dataset.json',transform['child_bytes'],64*M),
        ('result_copy',job_id,'result.json',transform['result_bytes'],64*M),
        ('scientific_output',None,'scientific.json',canonical(child['payload'],scientific=True),64*M),
        ('completion',None,'complete.json',canonical(complete),4096)]
    slots=[]
    for ordinal,(role,artifact,leaf,body,cap) in enumerate(staged,1):
        target=files.root/f'.job-staging/{job_id}'/leaf; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(body)
        slots.append(dict(ordinal=ordinal,role=role,location='stage',artifact_id=artifact,leaf=leaf,max_bytes=cap,
            actual_bytes=len(body),actual_sha256=byte_sha(body)))
    targets=[]
    for kind,identifier,lane,body in (('dataset',child['dataset_id'],'datasets',transform['child_bytes']),('result',job_id,'results',transform['result_bytes'])):
        key=f'derived/{owner}/{project}/{lane}/{identifier}.json'
        targets.append(dict(kind=kind,artifact_id=identifier,storage_key=key,bytes=len(body),sha256=byte_sha(body)))
        (files.root/key).write_bytes(body)
    inv=dict(schema='geophysics.physical-custody/v1',batch_id=batch,owner_id=owner,project_id=project,origin_kind='job_stage',
        origin_id=job_id,stage_id=job_id,deletion_receipt_id=None,raw_asset_id=req['raw_asset_id'],raw_sha256=req['raw_sha256'],
        raw_bytes=req['raw_bytes'],parser_version='gravity-stations-json/v1',method_id=req['method_id'],capacity_bytes=512*M,
        initial_files=slots,removed_ordinals=[])
    with connect(path) as db:
        insert(db,'processing_jobs',dict(transform['job'],state='running',finished_at=None,result_key=None,result_sha256=None,result_bytes=None,
            wall_ms=None,physical_cpu_ms=None,peak_rss_bytes=None,scratch_bytes=None,physical_fingerprint='e'*64,cancel_requested=0,
            created_at='2026-10-08 01:00:00',request_json=transform['request_bytes'].decode(),preflight='{"fixture_only":true}'))
        insert(db,'physical_job_controls',dict(job_id=job_id,owner_id=owner,project_id=project,dataset_id=req['dataset_id'],
            dataset_sha256=req['dataset_sha256'],root_dataset_id=req['root_dataset_id'],raw_asset_id=req['raw_asset_id'],raw_sha256=req['raw_sha256'],
            raw_bytes=req['raw_bytes'],stage_id=job_id,method_id=req['method_id'],request_sha256=digest(req),request_bytes=transform['request_bytes'],
            submitted_parameters_sha256=req['submitted_parameters_sha256'],scientific_request_sha256=req['scientific_request_sha256'],
            module_manifest_bytes=canonical(req['module_manifest']),module_manifest_sha256=req['module_manifest_sha256'],
            parent_production_bytes=canonical(req['parent_production']),permanent_reservation_bytes=128*M,
            admission_receipt_sha256=req['admission_receipt_sha256'],created_us=1))
        insert(db,'physical_custody_batches',dict({k:v for k,v in inv.items() if k not in ('schema','initial_files','removed_ordinals')},
            state='sealed',charged_bytes=sum(s['actual_bytes'] for s in slots),inventory_bytes=canonical(inv),inventory_sha256=digest(inv),created_us=1,sealed_us=2,removed_us=None))
        for slot in slots:
            insert(db,'physical_custody_files',dict(slot,batch_id=batch,state='present'))
        reserve_child_intent(db,owner_id=owner,project_id=project,parent_dataset_id=req['dataset_id'],parent_dataset_sha256=req['dataset_sha256'],
            job_id=job_id,stage_id=job_id,child_dataset_id=child['dataset_id'],intent_id=intent,created_us=2,targets=targets)
    values=dict(correction_values,intent_id=intent)
    values['approved_manifests']=dict(values['approved_manifests'],**{digest(transform['approved_manifest']):transform['approved_manifest']})
    return path,files,values,transform


def test_original_transform_co_commit_and_readonly_saved_audit(transform_publication):
    path,files,values,packet=transform_publication
    with connect(path) as db:
        child=publish_transform(db,files,**values)
        assert child==json.loads(packet['child_bytes'])
        cursor=db.execute('SELECT * FROM observation_datasets WHERE id=?',(child['dataset_id'],))
        row=dict(zip((c[0] for c in cursor.description),cursor.fetchone()))
        assert audit_transform_producer(db,files,row,approved_manifests=values['approved_manifests'])==child
        assert db.execute('SELECT published_count,reserved_count,next_ordinal FROM physical_dataset_families').fetchone()==(3,0,4)
        assert db.execute('SELECT permanent_reservation_bytes FROM physical_job_controls WHERE job_id=?',(packet['job']['id'],)).fetchone()==(0,)
        assert db.execute('SELECT scientific_verdict,adapter_result_sha256,adapter_receipt_bytes FROM physical_dataset_productions WHERE child_dataset_id=?',(child['dataset_id'],)).fetchone()==(child['production']['scientific_verdict'],None,None)
        assert db.execute('SELECT state FROM physical_custody_batches WHERE stage_id=?',(packet['job']['id'],)).fetchone()==('cleanup_pending',)
        assert not db.execute('SELECT 1 FROM physical_publication_intents').fetchone()
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]


@pytest.mark.parametrize('cut',['child','production','terminal','retired'])
def test_transform_every_terminal_cut_preserves_rows_bytes_charge(transform_publication,cut):
    path,files,values,packet=transform_publication
    with connect(path) as db:
        before=sql_inventory(db); bodies={str(p.relative_to(files.root)):p.read_bytes() for p in files.root.rglob('*') if p.is_file()}
        def fail(point):
            if point==cut:
                raise RuntimeError('original_transform_cut')
        with pytest.raises(RuntimeError,match='original_transform_cut'):
            publish_transform(db,files,**values,failure_cut=fail)
        assert sql_inventory(db)==before
        assert {str(p.relative_to(files.root)):p.read_bytes() for p in files.root.rglob('*') if p.is_file()}==bodies


@pytest.mark.parametrize('damage',['cancel','unregistered','telemetry','native_request','saved_parent','completion'])
def test_transform_refusals_keep_original_and_nonpass(transform_publication,damage):
    path,files,values,packet=transform_publication; values=deepcopy(values)
    with connect(path) as db:
        job_id=packet['job']['id']
        if damage=='cancel':
            db.execute('UPDATE processing_jobs SET cancel_requested=1 WHERE id=?',(job_id,))
        elif damage=='unregistered':
            values['approved_manifests']={}
        elif damage=='telemetry':
            values['metrics']['cpu_ms']+=1
        elif damage=='native_request':
            db.execute('UPDATE processing_jobs SET request_json=? WHERE id=?',('{"changed":true}',job_id))
        elif damage=='saved_parent':
            db.execute('UPDATE physical_job_controls SET parent_production_bytes=? WHERE job_id=?',(b'{"wrong":true}',job_id))
        elif damage=='completion':
            (files.root/f'.job-staging/{job_id}/complete.json').write_bytes(b'original retained bad completion')
        before=sql_inventory(db); bodies={str(p.relative_to(files.root)):p.read_bytes() for p in files.root.rglob('*') if p.is_file()}
        with pytest.raises((ValueError,OSError,AssertionError)):
            publish_transform(db,files,**values)
        assert sql_inventory(db)==before
        assert {str(p.relative_to(files.root)):p.read_bytes() for p in files.root.rglob('*') if p.is_file()}==bodies
        assert db.execute('SELECT permanent_reservation_bytes FROM physical_job_controls WHERE job_id=?',(job_id,)).fetchone()==(128*M,)


def test_emit_prepared_original_transform_native_fixture(transform_publication,tmp_path):
    path,files,values,packet=transform_publication
    record=dict(database=str(path),private_root=str(files.root),values=values,child=json.loads(packet['child_bytes']))
    (tmp_path/'native-transform-input.json').write_bytes(canonical(record))
    with connect(path) as db:
        assert db.execute('SELECT count(*) FROM observation_datasets').fetchone()==(2,)
        assert db.execute('SELECT count(*) FROM physical_publication_targets').fetchone()==(2,)
