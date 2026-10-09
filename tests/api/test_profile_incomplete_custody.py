"""Source-bound q13 constructor and new portable copies, NOT native admission.

Explicit authentic receipt stays outside Git. Its bytes are never rewritten.
Copied fixture identities and authored diagnostic bytes are new evidence only.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import threading
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.physical_contract import byte_sha, canonical
from app.profile_archive_custody import (
    archive_inventory, archive_limits, deletion_entries, validate_saved_entry,
)
from app.profile_incomplete_custody import _record
from tests.api.test_profile_archive_custody import Files, archive_fixture
from tests.ops.profile_incomplete_source_fixture import owner_source
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey

RECEIPT_SHA='5a13e2c51abcd5c4ec90661d237f421e0c3a363b61ed6e5aa7bfc9fe43dccb89'


@pytest.fixture(scope='module',autouse=True)
def exact_owner(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        with owner_source(tmp_path_factory.mktemp('incomplete-owner')/'source',patch): yield


@pytest.fixture(scope='module')
def q13():
    path=Path(os.environ['GEOPHYSICS_PROFILE_INCOMPLETE_RECEIPT'])
    assert path.is_absolute() and all(not (p/'.git').exists() for p in (path.parent,*path.parents))
    body=path.read_bytes()
    assert byte_sha(body)==RECEIPT_SHA
    value=json.loads(body)
    assert value['source_commit']=='637f4aa873bf73187f1c88d452fd4bf49b2d61ee'
    assert value['all_probes_passed'] is True and value['science_admitted'] is False
    assert value['restart_delete_assembly']=='NOT_ESTABLISHED' and value['production_activated'] is False
    return value


class PrivateFixture(Files):
    """Real fixture byte/identity census; Windows modes are NOT POSIX proof."""
    def private_directory_identity(self,key):
        assert not (self.root/key).is_symlink()
        return self.directory_identity(key)

    def private_member(self,key,**kwargs):
        body=self.read(key,**kwargs)
        info=(self.root/key).stat()
        return body,dict(device=info.st_dev,inode=info.st_ino,bytes=len(body),sha256=byte_sha(body))


def relation_of(manifest):
    relation=deepcopy(manifest['ownership'])
    relation['id']=relation.pop('job_id'); relation['state']=relation.pop('terminal_state')
    return relation


def incomplete_fixture(root,q13,*,owner=None,relation=None,partial=False):
    files=PrivateFixture(root)
    manifest=deepcopy(q13['archive'])
    if relation is None:
        relation=relation_of(manifest)
        for key in ('id','owner_id','project_id','dataset_id','raw_asset_id','source_id'): relation[key]=str(uuid4())
        if owner is not None: relation['owner_id']=owner
    manifest['ownership']=dict(job_id=relation['id'],terminal_state=relation['state'],
                              **{k:v for k,v in relation.items() if k not in ('id','state')})
    manifest['job_id']=relation['id'];manifest['request_sha256']=relation['request_sha256']
    stage=root/'.profile-incomplete'/relation['id'];stage.mkdir(parents=True)
    manifest['stage_identity']=files.directory_identity(f'.profile-incomplete/{relation["id"]}')
    recovery=manifest['recovery'];recovery['job_id']=relation['id']
    recovery['retained_stage_identity']=deepcopy(manifest['stage_identity'])
    states=list(recovery['terminal'].values())
    units=[f'geophysics-profile-{relation["id"]}.service',f'geophysics-profile-guardian-{relation["id"]}.scope']
    recovery['terminal']={unit:state for unit,state in zip(units,states)}
    for unit,state in recovery['terminal'].items():
        if state['manager']['ControlGroup']: state['manager']['ControlGroup']='/system.slice/'+unit
        state['kernel']['path']='/sys/fs/cgroup/system.slice/'+unit
    manifest['members']={}
    if partial:
        for name,body in [('stderr.txt',b'new authored diagnostic'),('result.json',b'')]:
            (stage/name).write_bytes(body)
            _,manifest['members'][name]=files.private_member(f'.profile-incomplete/{relation["id"]}/{name}',cap=1024)
    def write():
        body=canonical(manifest)
        (stage/'manifest.json').write_bytes(body)
        (stage.parent/(relation['id']+'.intent.json')).write_bytes(body)
    write()
    return files,relation,manifest,deepcopy(manifest['installation']),write


def inventory(fixture,*,saved=False):
    files,relation,manifest,approved,_=fixture
    entries=[_record(manifest,relation,approved)]
    receipts=[dict(id=str(uuid4()),owner_id=relation['owner_id'],project_id=relation['project_id'],derived_manifest=entries)] if saved else []
    return archive_inventory(files,[] if saved else [relation],receipts,approved_installations={relation['id']:approved})


def test_exact_q13_descriptor_is_consumed_without_rewriting_or_science(q13):
    manifest=q13['archive'];relation=relation_of(manifest)
    assert _record(manifest,relation,manifest['installation'])==q13['descriptor']
    assert q13['descriptor']['charged_bytes']==9754 and q13['descriptor']['manifest_bytes']==4877
    assert q13['descriptor']['manifest_sha256']=='26a1097a340420f9314246a36201afa814f645849588d023632128d457e7397f'
    assert not manifest['members'] and manifest['recovery']['execution_receipt']=='absent'


@pytest.mark.parametrize('partial',[False,True])
def test_distinct_real_copies_transfer_exactly_to_saved_receipt(q13,tmp_path,partial):
    fixture=incomplete_fixture(tmp_path,q13,partial=partial)
    records=inventory(fixture)
    assert inventory(fixture,saved=True)==records
    manifest=fixture[2]
    assert records[0]['charged_bytes']==2*len(canonical(manifest))+sum(m['bytes'] for m in manifest['members'].values())
    assert deletion_entries(records,owner_id=str(uuid4()),project_id=fixture[1]['project_id'])==[]


@pytest.mark.parametrize('field',['owner_id','project_id','job_id','dataset_id','raw_asset_id','source_id',
    'method_id','terminal_state','dataset_sha256','raw_sha256','request_sha256'])
def test_all_eleven_nested_identity_mismatches_refuse(q13,tmp_path,field):
    fixture=incomplete_fixture(tmp_path,q13)
    fixture[2]['ownership'][field]=str(uuid4()) if field.endswith('_id') else 'a'*64
    fixture[4]()
    with pytest.raises(ValueError): inventory(fixture)


@pytest.mark.parametrize('damage',['unknown','missing','pair','member-hash','member-inode','stage-inode',
    'authority','execution','active','populated','extra','schema','succeeded','trailing','duplicate-key','live-plus-saved','missing-saved'])
def test_incomplete_custody_damage_never_adopts_or_releases(q13,tmp_path,damage):
    fixture=incomplete_fixture(tmp_path,q13,partial=True)
    files,relation,manifest,approved,write=fixture
    stage=files.root/'.profile-incomplete'/relation['id']
    intent=stage.parent/(relation['id']+'.intent.json')
    if damage=='unknown': (stage/'original.raw').write_bytes(b'never admit')
    elif damage=='missing': (stage/'stderr.txt').unlink()
    elif damage=='pair': intent.unlink()
    elif damage=='member-hash': manifest['members']['stderr.txt']['sha256']='a'*64
    elif damage=='member-inode': manifest['members']['stderr.txt']['inode']+=1
    elif damage=='stage-inode': manifest['stage_identity']['inode']+=1
    elif damage=='authority': approved['configuration_sha256']='a'*64
    elif damage=='execution': manifest['recovery']['execution_receipt']='present'
    elif damage=='active': next(iter(manifest['recovery']['terminal'].values()))['manager']['ActiveState']='active'
    elif damage=='populated': next(iter(manifest['recovery']['terminal'].values()))['kernel']['state']='populated'
    elif damage=='extra': manifest['future']=True
    elif damage=='schema': manifest['schema']='geophysics.profile-retained-stage/v2'
    elif damage=='succeeded': manifest['ownership']['terminal_state']=relation['state']='succeeded'
    if damage not in ('pair','live-plus-saved','missing-saved'): write()
    if damage=='trailing': intent.write_bytes(intent.read_bytes()+b'{}')
    elif damage=='duplicate-key': intent.write_bytes(b'{"schema":"duplicate",'+intent.read_bytes()[1:])
    records=[]
    if damage in ('live-plus-saved','missing-saved'):
        records=inventory(fixture)
        if damage=='missing-saved': stage.rename(tmp_path/'outside-known-archive');intent.unlink()
    before={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    with pytest.raises((ValueError,OSError)):
        if records:
            receipts=[dict(id=str(uuid4()),owner_id=relation['owner_id'],project_id=relation['project_id'],derived_manifest=records)]
            archive_inventory(files,[relation] if damage=='live-plus-saved' else [],receipts,
                              approved_installations={relation['id']:approved})
        else: inventory(fixture)
    assert before=={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def test_successful_v2_and_incomplete_remain_distinct_and_share_allowance(q13,tmp_path):
    fixture=incomplete_fixture(tmp_path,q13)
    files,relation,_,approved,_=fixture
    _,success,_,installation,_=archive_fixture(tmp_path)
    records=archive_inventory(files,[relation,success],[],approved_installations={relation['id']:approved,success['id']:installation})
    assert len(records)==2 and len({r['schema'] for r in records})==2
    assert all(validate_saved_entry(r,owner_id=r['owner_id'],project_id=r['project_id'],
        approved_installations={relation['id']:approved,success['id']:installation}) for r in records)
    retained=next(r for r in records if r['job_id']==success['id'])
    with pytest.raises(ValueError,match='retained_count'): archive_limits([retained]*64)
    with pytest.raises(ValueError,match='count'): archive_limits([records[0]]*129)
    changed=deepcopy(records);changed[0]['charged_bytes']=256*1048576
    with pytest.raises(ValueError,match='global_cap'): archive_limits(changed)


def test_read_thread_is_drained_across_repeated_cancellation():
    from app.profile_archive_delete import excluded_read
    started,finish=threading.Event(),threading.Event()
    def read():
        started.set();assert finish.wait(10);return 'closed'
    async def run():
        task=asyncio.create_task(excluded_read(read))
        while not started.is_set(): await asyncio.sleep(.001)
        task.cancel();await asyncio.sleep(.01);task.cancel();await asyncio.sleep(.01)
        assert not task.done()
        finish.set()
        with pytest.raises(asyncio.CancelledError): await task
    try: asyncio.run(run())
    finally: finish.set()


@pytest.mark.parametrize('damage',[None,'missing','saved-charge','authority','owner','unknown','member','missing-census'])
def test_saved_incomplete_charge_and_full_restart_snapshot(q13,root_case,damage):
    from tests.api.test_physical_deleted_inventory import case,POLICY
    from tests.api.test_physical_forest import connect
    from tests.api.test_physical_classifier import CensusFiles
    from app.physical_classifier import classify_snapshot
    from app.physical_accounting import account_private_charge
    case(root_case)
    path,original,values,*_=root_case
    fixture=incomplete_fixture(original.root,q13,owner=values['owner_id'],partial=True)
    files,relation,manifest,approved,_=fixture
    records=inventory(fixture)
    saved=deepcopy(records)
    if damage=='saved-charge': saved[0]['charged_bytes']-=1
    if damage=='owner': saved[0]['owner_id']=str(uuid4())
    if damage=='authority': approved['python_sha256']='a'*64
    if damage=='unknown': (files.root/'.profile-incomplete'/'unknown').write_bytes(b'preserve')
    if damage=='member': (files.root/f'.profile-incomplete/{relation["id"]}/stderr.txt').write_bytes(b'changed')
    if damage=='missing': (files.root/f'.profile-incomplete/{relation["id"]}/manifest.json').unlink()
    class Census(CensusFiles):
        def private_directory_identity(self,key): return files.private_directory_identity(key)
        def private_member(self,key,**kwargs): return files.private_member(key,**kwargs)
    registry={relation['id']:approved}
    with connect(path) as db:
        db.execute('''INSERT INTO deletion_receipts(id,project_id,owner_id,deleted_at,asset_hashes,asset_manifest,
            derived_manifest,backup_purge_status) VALUES(?,?,?,?,?,?,?,?)''',
            (str(uuid4()),relation['project_id'],values['owner_id'],'2026-10-08 12:00:00','[]','[]',canonical(saved).decode(),'not_attempted'))
        before=db.execute('SELECT * FROM deletion_receipts').fetchall()
        db.execute('BEGIN IMMEDIATE')
        if damage=='missing-census':
            with pytest.raises(ValueError,match='census_required'):
                account_private_charge(db,values['owner_id'])
        else:
            result=classify_snapshot(db,Census(original),approved_manifests={},approved_installations=registry,
                                    native_metadata={},expected_source_policy_sha256=POLICY)
            assert result.runtime is False
            if damage is None:
                assert result.classification=='coherent_committed',result.reason
                assert result.account_charges[values['owner_id']]['profile_retained']==records[0]['charged_bytes']
                again=classify_snapshot(db,Census(original),approved_manifests={},approved_installations=registry,
                                       native_metadata={},expected_source_policy_sha256=POLICY)
                assert again.inventory_sha256==result.inventory_sha256
            else:
                assert result.classification=='inconsistent',result.reason
                assert not result.operations and not result.account_charges and result.inventory_sha256 is None
        assert db.execute('SELECT * FROM deletion_receipts').fetchall()==before
        db.rollback()


def test_original_plural_http_delete_transfers_distinct_incomplete_receipt(q13,make_harness):
    """Actual SQL/auth/route and fixture locks, NOT native lock/durability proof."""
    import sqlite3
    from app.profile_archive_delete import ProfileArchiveDeletion
    from app.physical_participation import WriterParticipation
    from tests.api.test_physical_participation import TransportLease,TransportWorker
    from tests.api.test_profile_jobs import owned_dataset,profile_harness
    from tests.api.test_local_auth import provision,login
    harness=profile_harness(make_harness)
    project,asset,dataset,meta=owned_dataset(harness)
    base=f'/api/projects/{project["id"]}'
    response=harness.request('POST',base+'/jobs',json=dict(dataset_id=dataset['dataset_id'],method_id=meta['method'],parameters={}))
    assert response.status_code==202,response.text
    job=response.json()['job_id']
    assert harness.request('POST',base+'/jobs/'+job+'/cancel').status_code==200
    with sqlite3.connect(harness.settings.database_path) as db:
        db.row_factory=sqlite3.Row
        row=dict(db.execute('''SELECT j.id,j.owner_id,j.project_id,j.dataset_id,j.dataset_sha256,j.request_sha256,
            j.method_id,j.state,d.raw_asset_id,r.source_id,r.sha256 raw_sha256 FROM processing_jobs j
            JOIN observation_datasets d ON d.id=j.dataset_id JOIN raw_assets r ON r.id=d.raw_asset_id WHERE j.id=?''',(job,)).fetchone())
    fixture=incomplete_fixture(harness.settings.data_dir,q13,relation=row,partial=True)
    files,relation,_,approved,_=fixture
    records=inventory(fixture)
    files.root_path=files.root
    leases=TransportLease();leases.files=files
    class Worker(TransportWorker):
        def require_held(self):
            self.leases.require_held(exclusive=True)
            assert self.held
    worker=Worker(leases)
    harness.app.state.profile_archive_deletion=ProfileArchiveDeletion(leases,worker_exclusion=worker,
        approved_installations={job:approved})
    harness.app.middleware_stack=WriterParticipation(harness.app.middleware_stack,leases=leases,worker_exclusion=worker)
    raw=files.root/f'projects/{row["owner_id"]}/{project["id"]}/{asset["asset_id"]}'
    original=raw.read_bytes()
    archive_before={p.relative_to(files.root).as_posix():p.read_bytes() for p in (files.root/'.profile-incomplete').rglob('*') if p.is_file()}
    provision(harness,username='another-owner@example.org')
    assert login(harness,username='another-owner@example.org').status_code==204
    assert harness.request('DELETE',base).status_code==404 and raw.read_bytes()==original
    assert login(harness).status_code==204
    response=harness.request('DELETE',base)
    assert response.status_code==200,response.text
    assert response.json()['retained_profile_archives']==1
    assert not raw.exists() and not harness.messages
    assert archive_before=={p.relative_to(files.root).as_posix():p.read_bytes() for p in (files.root/'.profile-incomplete').rglob('*') if p.is_file()}
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute('SELECT count(*) FROM processing_jobs').fetchone()==(0,)
        entries=json.loads(db.execute('SELECT derived_manifest FROM deletion_receipts').fetchone()[0])
        saved=[r for r in entries if r.get('schema')==records[0]['schema']]
        assert saved==records and db.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert db.execute('SELECT raw_bytes FROM account_usage WHERE user_id=?',(row['owner_id'],)).fetchone()==(0,)
        receipts=[dict(id=str(uuid4()),owner_id=row['owner_id'],project_id=project['id'],derived_manifest=entries)]
        assert archive_inventory(files,[],receipts,approved_installations={job:approved})==records
    assert harness.request('DELETE',base).status_code==404


@pytest.mark.parametrize('outcome',['terminal','error','cancel','busy','foreign-root'])
def test_distinct_recovery_wrapper_keeps_both_lifetime_guards(tmp_path,monkeypatch,outcome):
    """Delegation/lifetime flow only; native helper drain has separate evidence."""
    from app.physical_participation import recover_incomplete_participating
    from tests.api.test_physical_participation import TransportLease,TransportWorker
    async def run():
        leases=TransportLease();leases.files.root_path=tmp_path
        worker=TransportWorker(leases,busy=outcome=='busy')
        calls=[]
        async def original(settings,identifier):
            leases.require_held(exclusive=True)
            assert worker.held
            calls.append(identifier)
            await asyncio.sleep(0)
            leases.require_held(exclusive=True)
            assert worker.held
            if outcome=='error': raise RuntimeError('original-recovery-error')
            if outcome=='cancel': raise asyncio.CancelledError()
            return 'closed-distinct-recovery'
        monkeypatch.setattr('app.profile_incomplete_recovery.recover_incomplete_job',original)
        settings=SimpleNamespace(data_dir=tmp_path/'foreign' if outcome=='foreign-root' else tmp_path)
        identifier=str(uuid4())
        if outcome=='terminal':
            assert await recover_incomplete_participating(settings,identifier,worker)=='closed-distinct-recovery'
        else:
            error=RuntimeError if outcome=='error' else asyncio.CancelledError if outcome=='cancel' else ValueError
            with pytest.raises(error): await recover_incomplete_participating(settings,identifier,worker)
        assert calls==([] if outcome in ('busy','foreign-root') else [identifier])
        assert not leases.held and not worker.held
    asyncio.run(run())
