"""Retained diagnostics survive owner deletion; no raw/science deletion lane."""

import json
from uuid import uuid4

import pytest

from app.physical_contract import byte_sha, canonical
from app.profile_archive_custody import retained_inventory, deletion_entries, attach_deletion_entries


class Files:
    """Real ordinary fixture bytes, not a native exclusion/durability proof."""
    def __init__(self, root):
        self.root = root

    def names(self, key, *, limit):
        path = self.root/key
        if path.is_symlink():
            raise ValueError('linked_fixture')
        names = [p.name for p in path.iterdir()]
        if len(names) > limit:
            raise ValueError('fixture_count')
        return names

    def read(self, key, *, cap, expected_bytes=None, expected_sha256=None):
        path = self.root/key
        body = path.read_bytes()
        if path.is_symlink() or path.stat().st_nlink != 1 or len(body)>cap:
            raise ValueError('fixture_identity')
        if expected_bytes is not None and len(body)!=expected_bytes:
            raise ValueError('fixture_bytes')
        if expected_sha256 is not None and byte_sha(body)!=expected_sha256:
            raise ValueError('fixture_hash')
        return body

    def directory_identity(self, key):
        value = (self.root/key).stat()
        return dict(device=value.st_dev, inode=value.st_ino)


def archive_fixture(tmp_path):
    from app.profile_archive_custody import SOURCE_FILES, EXECUTION
    owner,project,job,dataset,raw,source = [str(uuid4()) for _ in range(6)]
    installation = dict(configuration_sha256='1'*64,python_sha256='2'*64,environment_sha256='3'*64,
        invocation_sha256='4'*64,source_hashes={name:'5'*64 for name in SOURCE_FILES})
    relation = dict(id=job,owner_id=owner,project_id=project,dataset_id=dataset,dataset_sha256='6'*64,
        raw_asset_id=raw,source_id=source,raw_sha256='7'*64,request_sha256='8'*64,method_id='ert.topographic-profile/v1',state='cancelled')
    files=Files(tmp_path); stage=tmp_path/f'.profile-retained/{job}'; stage.mkdir(parents=True)
    identity=files.directory_identity(f'.profile-retained/{job}')
    execution=dict.fromkeys(EXECUTION.split())
    execution.update(schema='geophysics.profile-linux-execution/v1',job_id=job,request_sha256='8'*64,
        dataset_sha256='6'*64,raw_sha256='7'*64,retained_stage_identity=identity,retained={'stderr.txt':dict(bytes=10,sha256=byte_sha(b'diagnostic'))},
        **installation)
    members={'linux-execution.json':canonical(execution),'linux-stderr.txt':b'diagnostic'}
    recovery=dict(schema='geophysics.profile-linux-recovery/v1',job_id=job,receipt_sha256=byte_sha(members['linux-execution.json']),
        intent_sha256='9'*64,installation=installation,retained_stage_identity=identity,known_root_copies_removed=True,
        terminal={f'geophysics-profile-{job}.service':dict(MainPID='0',ActiveState='inactive',SubState='dead',ControlGroup=''),
                  f'geophysics-profile-guardian-{job}.scope':dict(ActiveState='inactive',SubState='dead',ControlGroup='')})
    manifest=dict(schema='geophysics.profile-retained-stage/v2',job_id=job,request_sha256='8'*64,installation=installation,
        stage_identity=identity,members={name:dict(bytes=len(body),sha256=byte_sha(body)) for name,body in members.items()},
        recovery=recovery,uncommitted_duplicate=None,method_id=relation['method_id'],terminal_state=relation['state'],
        **{k:relation[k] for k in ('owner_id','project_id','dataset_id','raw_asset_id','source_id','dataset_sha256','raw_sha256')})
    for name,body in members.items():
        (stage/name).write_bytes(body)
    def write():
        body=canonical(manifest); (stage/'manifest.json').write_bytes(body); (stage.parent/f'{job}.intent.json').write_bytes(body)
    write()
    return files,relation,manifest,installation,write


def test_live_custody_transfers_without_copy_or_charge_loss(tmp_path):
    files,relation,manifest,installation,_=archive_fixture(tmp_path)
    records=retained_inventory(files,[relation],[],approved_installations={relation['id']:installation})
    record=records[0]
    assert record['charged_bytes']==2*len(canonical(manifest))+sum(x['bytes'] for x in manifest['members'].values())
    assert record['owner_id']==relation['owner_id'] and record['terminal_state']=='cancelled'
    entries=deletion_entries(records,owner_id=relation['owner_id'],project_id=relation['project_id'])
    receipt=dict(id=str(uuid4()),owner_id=relation['owner_id'],project_id=relation['project_id'],derived_manifest=entries)
    assert retained_inventory(files,[],[receipt],approved_installations={relation['id']:installation})==records


@pytest.mark.parametrize('field', ['owner_id','project_id','dataset_id','raw_asset_id','source_id','dataset_sha256','raw_sha256','request_sha256','job_id','method_id','terminal_state'])
def test_rehashed_foreign_identity_never_transfers(field,tmp_path):
    files,relation,manifest,installation,write=archive_fixture(tmp_path)
    manifest[field]=str(uuid4()) if field.endswith('_id') else 'a'*64
    write()
    with pytest.raises(ValueError):
        retained_inventory(files,[relation],[],approved_installations={relation['id']:installation})


@pytest.mark.parametrize('damage',['unknown','missing','intent-only','archive-only','authority','active','duplicate','saved-owner','orphan'])
def test_unknown_incomplete_or_unbound_custody_preserves_bytes(damage,tmp_path):
    files,relation,manifest,installation,_=archive_fixture(tmp_path)
    saved=[]; live=[relation]
    if damage=='unknown': (files.root/f'.profile-retained/{relation["id"]}/unknown').write_bytes(b'preserve')
    elif damage=='missing': (files.root/f'.profile-retained/{relation["id"]}/linux-stderr.txt').unlink()
    elif damage=='intent-only': (files.root/f'.profile-retained/{relation["id"]}').rename(files.root/'outside-archive')
    elif damage=='archive-only': (files.root/f'.profile-retained/{relation["id"]}.intent.json').unlink()
    elif damage=='authority': installation['python_sha256']='a'*64
    elif damage=='active': relation['state']='running'
    elif damage=='orphan': live=[]
    else:
        records=retained_inventory(files,live,[],approved_installations={relation['id']:installation})
        receipt=dict(id=str(uuid4()),owner_id=relation['owner_id'],project_id=relation['project_id'],derived_manifest=deletion_entries(records,owner_id=relation['owner_id'],project_id=relation['project_id']))
        saved=[receipt]; live=[]
        if damage=='duplicate': live=[relation]
        else: receipt['owner_id']=str(uuid4())
    before={str(p.relative_to(files.root)):p.read_bytes() for p in files.root.rglob('*') if p.is_file()}
    with pytest.raises((ValueError,FileNotFoundError)):
        retained_inventory(files,live,saved,approved_installations={relation['id']:installation})
    assert before=={str(p.relative_to(files.root)):p.read_bytes() for p in files.root.rglob('*') if p.is_file()}


def test_other_owner_never_receives_archive(tmp_path):
    files,relation,_,installation,_=archive_fixture(tmp_path)
    records=retained_inventory(files,[relation],[],approved_installations={relation['id']:installation})
    assert deletion_entries(records,owner_id=str(uuid4()),project_id=relation['project_id'])==[]


def test_real_sql_receipt_attachment_rolls_back_with_deletion(tmp_path):
    import sqlite3
    files,relation,_,installation,_=archive_fixture(tmp_path/'files')
    records=retained_inventory(files,[relation],[],approved_installations={relation['id']:installation})
    entries=deletion_entries(records,owner_id=relation['owner_id'],project_id=relation['project_id'])
    db=sqlite3.connect(tmp_path/'cut.sqlite',isolation_level=None)
    db.execute('CREATE TABLE deletion_receipts (id TEXT PRIMARY KEY,owner_id TEXT,project_id TEXT,derived_manifest JSON)')
    receipt=str(uuid4()); db.execute('INSERT INTO deletion_receipts VALUES (?,?,?,?)',(receipt,relation['owner_id'],relation['project_id'],'[]'))
    db.execute('BEGIN IMMEDIATE')
    attach_deletion_entries(db,receipt_id=receipt,owner_id=relation['owner_id'],project_id=relation['project_id'],entries=entries)
    assert json.loads(db.execute('SELECT derived_manifest FROM deletion_receipts').fetchone()[0])==entries
    db.rollback()
    assert db.execute('SELECT derived_manifest FROM deletion_receipts').fetchone()==('[]',)
    db.close()


def test_historical_v1_requires_live_binding_before_first_transfer(tmp_path):
    from app.profile_archive_custody import IDENTITY
    files,relation,manifest,installation,write=archive_fixture(tmp_path)
    manifest['schema']='geophysics.profile-retained-stage/v1'
    for key in (*IDENTITY.split(),'method_id','terminal_state'):
        del manifest[key]
    write()
    approved={relation['id']:installation}
    records=retained_inventory(files,[relation],[],approved_installations=approved)
    receipt=dict(id=str(uuid4()),owner_id=relation['owner_id'],project_id=relation['project_id'],
                 derived_manifest=deletion_entries(records,owner_id=relation['owner_id'],project_id=relation['project_id']))
    assert retained_inventory(files,[],[receipt],approved_installations=approved)==records
    with pytest.raises(ValueError,match='unknown_name'):
        retained_inventory(files,[],[],approved_installations=approved)


@pytest.mark.parametrize('damage',['schema','extra','missing','bool-inode','negative-inode','large-inode',
    'extra-member','member-bytes','member-hash','recovery-hash','recovery-installation','active-unit','duplicate-key','trailing'])
def test_closed_v2_fields_native_domain_and_recovery_negatives(damage,tmp_path):
    files,relation,manifest,installation,write=archive_fixture(tmp_path)
    if damage=='schema': manifest['schema']='geophysics.profile-retained-stage/v3'
    elif damage=='extra': manifest['extra']='future'
    elif damage=='missing': del manifest['source_id']
    elif damage=='bool-inode': manifest['stage_identity']['inode']=True
    elif damage=='negative-inode': manifest['stage_identity']['inode']=-1
    elif damage=='large-inode': manifest['stage_identity']['inode']=2**64
    elif damage=='extra-member': manifest['members']['original']=dict(bytes=1,sha256='a'*64)
    elif damage=='member-bytes': manifest['members']['linux-stderr.txt']['bytes']+=1
    elif damage=='member-hash': manifest['members']['linux-stderr.txt']['sha256']='a'*64
    elif damage=='recovery-hash': manifest['recovery']['receipt_sha256']='a'*64
    elif damage=='recovery-installation': manifest['recovery']['installation']['python_sha256']='a'*64
    elif damage=='active-unit': next(iter(manifest['recovery']['terminal'].values()))['ActiveState']='active'
    write()
    if damage=='duplicate-key':
        target=files.root/f'.profile-retained/{relation["id"]}.intent.json'
        target.write_bytes(b'{"schema":"duplicate",'+target.read_bytes()[1:])
    elif damage=='trailing':
        target=files.root/f'.profile-retained/{relation["id"]}.intent.json'
        target.write_bytes(target.read_bytes()+b'{}')
    with pytest.raises(ValueError):
        retained_inventory(files,[relation],[],approved_installations={relation['id']:installation})


def test_existing_http_delete_refuses_unregistered_archive_before_any_move(harness):
    import sqlite3
    from tests.api.conftest import GRAVITY_CSV
    harness.account(); project=harness.project(); asset=harness.upload(project['id']).json()
    owner=harness.client.get('/api/auth/me').json()['id']
    root=harness.settings.data_dir/'.profile-retained'; root.mkdir()
    diagnostic=root/'unknown.intent.json'; diagnostic.write_bytes(b'preserve private diagnostic')
    raw=harness.settings.data_dir/f'projects/{owner}/{project["id"]}/{asset["asset_id"]}'
    response=harness.request('DELETE',f'/api/projects/{project["id"]}')
    assert response.status_code==409 and response.json()['code']=='profile_archive_custody_unresolved'
    assert raw.read_bytes()==GRAVITY_CSV and diagnostic.read_bytes()==b'preserve private diagnostic'
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute('SELECT count(*) FROM projects').fetchone()==(1,)
        assert db.execute('SELECT count(*) FROM deletion_receipts').fetchone()==(0,)
        assert db.execute('SELECT raw_bytes FROM account_usage').fetchone()==(len(GRAVITY_CSV),)
    assert not (harness.settings.data_dir/'.deleting').exists()
